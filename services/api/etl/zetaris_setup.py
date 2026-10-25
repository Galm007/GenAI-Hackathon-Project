"""Apply zetaris/sql/*.sql to the running Zetaris stack and refresh the gold table (plan §2.10.6, D-031)."""
from __future__ import annotations

import os
import re
import string
import uuid
from pathlib import Path

from dotenv import dotenv_values

from app.config import settings
from app.zetaris import ZetarisClient, ZetarisError

from .common import ROOT, log

SQL_DIR = ROOT / "zetaris" / "sql"
ALREADY = re.compile(r"already exist|already registered|already been (assigned|granted)|duplicate", re.IGNORECASE)


class AdminClient(ZetarisClient):
    """The query route accepts only SELECT; DDL goes to the SQL editor's run route (D-031)."""

    async def execute(self, sql: str) -> None:
        await self._login()
        resp = await self._http.post(
            "/api/proxy/sql-editor/sqls/run",
            json={"queryId": str(uuid.uuid4()), "sql": sql, "source": "SqlEditor"},
            headers={"Authorization": f"Bearer {self._jwt}", "X-Org-ID": self._org_id or "",
                     "X-Request-ID": str(uuid.uuid4())},
        )
        if resp.status_code != 200:
            raise ZetarisError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        body = resp.json()
        if isinstance(body, dict) and (body.get("success") is False or body.get("error")):
            raise ZetarisError(str(body.get("msg") or body.get("message") or body.get("error") or body)[:300])


def _admin() -> AdminClient:
    return AdminClient(settings.zetaris_url, settings.zetaris_admin_email, settings.zetaris_admin_password or "")


def statements(path: Path) -> list[str]:
    """Split on semicolons at line ends, drop comments, then substitute ${VARS} from the environment."""
    text = "\n".join(line for line in path.read_text().splitlines() if not line.lstrip().startswith("--"))
    env = {**dotenv_values(ROOT / ".env"), **os.environ}      # secrets live in .env, which pydantic doesn't export
    text = string.Template(text).substitute(env)              # KeyError on a missing secret = loud failure
    return [s.strip() for s in re.split(r";\s*\n", text.rstrip() + "\n") if s.strip()]


async def apply(files: list[str]) -> None:
    admin = _admin()
    try:
        for name in files:
            for stmt in statements(SQL_DIR / name):
                head = " ".join(stmt.split())[:80]
                if stmt.upper().startswith("INSERT OVERWRITE") and name == "03_gold.sql":
                    continue                                    # refresh-only statement; see refresh_gold()
                try:
                    await admin.execute(stmt)
                    log.info("zetaris ✓ %s", head)
                except ZetarisError as exc:
                    if ALREADY.search(str(exc)):
                        log.info("zetaris = %s (exists)", head)
                    else:
                        log.error("zetaris ✗ %s → %s", head, exc)
                        raise
    finally:
        await admin.aclose()


async def refresh_gold() -> None:
    admin = _admin()
    try:
        await admin.execute(f"INSERT OVERWRITE {settings.zetaris_gold_profile} SELECT * FROM ADCOM.v_school_profile")
        log.info("zetaris gold.school_profile refreshed")
    finally:
        await admin.aclose()


async def setup() -> None:
    await apply(["01_sources.sql", "02_views.sql", "03_gold.sql", "04_security.sql"])
