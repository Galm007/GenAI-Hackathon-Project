"""Async client for the Zetaris Lightning query API.

Uses the route that the bundle's verify.sh exercises end to end:
  POST {ZETARIS_URL}/api/auth/login              {"username", "password"} → JWT + orgId
  POST {ZETARIS_URL}/api/proxy/query/sql/start   {"select": <sql>, "pageLimit": n}
       headers: Authorization: Bearer <jwt>, X-Org-ID: <orgId>, X-Request-ID: <uuid>
Rows come back as JSON objects with string values ({"seven": "7"}), so callers cast.
"""
from __future__ import annotations

import asyncio
import re
import uuid
from typing import Any

import httpx

from .config import settings

JWT_RE = re.compile(r"^[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}$")


class ZetarisError(RuntimeError):
    pass


def _find_jwt(obj: Any) -> str | None:
    """verify.sh takes the first JWT-shaped string in the login response; do the same, field-name agnostic."""
    if isinstance(obj, str):
        return obj if JWT_RE.match(obj) else None
    values = obj.values() if isinstance(obj, dict) else obj if isinstance(obj, list) else []
    for v in values:
        if tok := _find_jwt(v):
            return tok
    return None


def _find_records(body: Any) -> list[dict] | None:
    """Rows sit under `records` (possibly nested); return the first list of row objects found."""
    if isinstance(body, list):
        return body if all(isinstance(r, dict) for r in body) else None
    if isinstance(body, dict):
        for key in ("records", "result", "data", "rows"):
            if key in body and (found := _find_records(body[key])) is not None:
                return found
    return None


class ZetarisClient:
    def __init__(self, base_url: str, username: str, password: str, *, max_concurrency: int = 4):
        self._http = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=httpx.Timeout(60.0, connect=5.0))
        self._username, self._password = username, password
        self._jwt: str | None = None
        self._org_id: str | None = None
        self._login_lock = asyncio.Lock()
        self._sem = asyncio.Semaphore(max_concurrency)       # Spark on a few cores: don't stampede it

    async def _login(self, *, force: bool = False) -> None:
        async with self._login_lock:
            if self._jwt and not force:
                return
            resp = await self._http.post("/api/auth/login",
                                         json={"username": self._username, "password": self._password})
            if resp.status_code != 200:
                raise ZetarisError(f"login failed: HTTP {resp.status_code}")
            body = resp.json()
            jwt, org = _find_jwt(body), body.get("orgId") if isinstance(body, dict) else None
            if not jwt or org is None:
                raise ZetarisError("login response carried no token or orgId")
            self._jwt, self._org_id = jwt, str(org)

    async def query(self, sql: str, *, page_limit: int = 1000) -> list[dict[str, str | None]]:
        """Run one statement. Every query we issue carries a LIMIT, so one page is enough."""
        await self._login()
        async with self._sem:
            for attempt in (1, 2):
                resp = await self._http.post(
                    "/api/proxy/query/sql/start",
                    json={"select": sql, "pageLimit": page_limit},
                    headers={"Authorization": f"Bearer {self._jwt}", "X-Org-ID": self._org_id or "",
                             "X-Request-ID": str(uuid.uuid4())},
                )
                if resp.status_code in (401, 403) and attempt == 1:    # expired JWT → log in once more
                    await self._login(force=True)
                    continue
                break
        if resp.status_code != 200:
            raise ZetarisError(f"query failed: HTTP {resp.status_code}: {resp.text[:300]}")
        rows = _find_records(resp.json())
        if rows is None:
            raise ZetarisError(f"unexpected response shape: {resp.text[:200]}")
        return rows

    async def aclose(self) -> None:
        await self._http.aclose()


# Hot-path and agent reads run as the least-privilege user; setup scripts use the admin account.
zetaris = ZetarisClient(settings.zetaris_url, settings.zetaris_agent_email, settings.zetaris_agent_password)
