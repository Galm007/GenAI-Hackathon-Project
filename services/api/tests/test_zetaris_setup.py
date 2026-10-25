from __future__ import annotations

import pytest

from app.zetaris import ZetarisError
from etl import zetaris_setup as zs


def test_statements_substitute_secrets_and_drop_comments(monkeypatch):
    for k in ("SUPABASE_POOLER_HOST", "ZETARIS_PG_USER", "ZETARIS_PG_PASSWORD"):
        monkeypatch.setenv(k, f"v-{k}")
    stmts = zs.statements(zs.SQL_DIR / "01_sources.sql")
    assert stmts[0].startswith("CREATE DATASOURCE ADCOM_PG")
    assert "v-SUPABASE_POOLER_HOST" in stmts[0] and "${" not in "".join(stmts)
    assert all(not s.lstrip().startswith("--") for s in stmts)


def test_missing_secret_fails_loudly(monkeypatch):
    monkeypatch.delenv("ZETARIS_AGENT_PASSWORD", raising=False)
    monkeypatch.setattr(zs, "dotenv_values", lambda _p: {})
    with pytest.raises(KeyError):
        zs.statements(zs.SQL_DIR / "04_security.sql")


@pytest.mark.asyncio
async def test_apply_treats_already_exists_as_success_and_skips_refresh(monkeypatch):
    seen: list[str] = []

    class Fake:
        async def execute(self, sql: str) -> None:
            seen.append(sql)
            raise ZetarisError("Datasource ADCOM already exists")

        async def aclose(self) -> None: ...

    monkeypatch.setattr(zs, "_admin", lambda: Fake())
    await zs.apply(["03_gold.sql"])
    assert len(seen) == 1 and seen[0].startswith("CREATE TABLE")      # INSERT OVERWRITE is refresh-only


@pytest.mark.asyncio
async def test_apply_raises_on_real_errors(monkeypatch):
    class Fake:
        async def execute(self, sql: str) -> None:
            raise ZetarisError("syntax error")

        async def aclose(self) -> None: ...

    monkeypatch.setattr(zs, "_admin", lambda: Fake())
    with pytest.raises(ZetarisError):
        await zs.apply(["03_gold.sql"])


@pytest.mark.parametrize("msg", [
    "USER : a@b has already been assigned to the ROLE : r",
    "SELECT has already been granted to r on `ADCOM`.`v`",
])
def test_already_pattern_covers_role_and_grant_repeats(msg):
    assert zs.ALREADY.search(msg)
