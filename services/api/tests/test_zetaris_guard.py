from __future__ import annotations

import httpx
import pytest

from app import zetaris_repo as repo
from app.zetaris import ZetarisClient, ZetarisError, _find_jwt, _find_records
from app.zetaris_repo import SqlNotAllowed, guard_agent_sql

JWT = "aaaaaaaa.bbbbbbbb.cccccccc"


@pytest.mark.parametrize("sql", [
    "DROP TABLE ADCOM.v_school_profile",
    "SELECT * FROM ADCOM_PG.universities",
    "SELECT 1 FROM adcom.v_school_profile; SELECT 2 FROM adcom.v_school_profile",
    "INSERT INTO adcom.v_school_profile VALUES (1)",
    "SELECT * FROM adcom.v_school_profile a JOIN ADCOM_PG.universities b ON a.slug = b.slug",
    "SHOW TABLES",
    "SELECT * FROM adcom.v_school_profile WHERE slug = 'x' UNION SELECT * FROM secret.t",
])
def test_guard_rejects(sql):
    with pytest.raises(SqlNotAllowed):
        guard_agent_sql(sql)


def test_guard_appends_missing_limit():
    out = guard_agent_sql("SELECT slug FROM ADCOM.v_school_profile WHERE slug = 'uiuc'")
    assert out == "SELECT * FROM (SELECT slug FROM ADCOM.v_school_profile WHERE slug = 'uiuc') q LIMIT 50"


def test_guard_clamps_large_limit_and_keeps_small():
    assert guard_agent_sql("SELECT * FROM adcom.v_major_stats LIMIT 5000;").endswith("LIMIT 50")
    assert guard_agent_sql("SELECT * FROM adcom.v_major_stats LIMIT 5").endswith("LIMIT 5")


def test_guard_allows_cte_over_allowed_view():
    sql = "WITH t AS (SELECT * FROM adcom.v_admitted_medians) SELECT * FROM t LIMIT 3"
    assert guard_agent_sql(sql) == sql


def test_find_jwt_and_records_are_shape_agnostic():
    assert _find_jwt({"data": {"token": JWT}, "orgId": 1}) == JWT
    assert _find_jwt({"token": "not-a-jwt"}) is None
    assert _find_records({"result": {"records": [{"seven": "7"}]}}) == [{"seven": "7"}]
    assert _find_records({"foo": 1}) is None


def client_with(handler) -> ZetarisClient:
    c = ZetarisClient("http://zetaris.test", "u", "p")
    c._http = httpx.AsyncClient(base_url="http://zetaris.test", transport=httpx.MockTransport(handler))
    return c


async def test_query_logs_in_then_retries_once_on_expired_jwt():
    calls: list[str] = []
    state = {"queries": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.url.path)
        if req.url.path == "/api/auth/login":
            return httpx.Response(200, json={"orgId": 7, "token": JWT})
        state["queries"] += 1
        if state["queries"] == 1:
            return httpx.Response(401)
        assert req.headers["X-Org-ID"] == "7" and req.headers["Authorization"] == f"Bearer {JWT}"
        return httpx.Response(200, json={"records": [{"seven": "7"}]})

    c = client_with(handler)
    assert await c.query("SELECT 7 AS seven") == [{"seven": "7"}]
    assert calls == ["/api/auth/login", "/api/proxy/query/sql/start", "/api/auth/login", "/api/proxy/query/sql/start"]
    await c.aclose()


async def test_query_surfaces_http_errors():
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/api/auth/login":
            return httpx.Response(200, json={"orgId": 1, "token": JWT})
        return httpx.Response(500, text="boom")

    with pytest.raises(ZetarisError, match="HTTP 500"):
        await client_with(handler).query("SELECT 1")


async def test_school_profile_falls_back_to_supabase_when_disabled(monkeypatch):
    async def fake_get_school(slug):
        return {"slug": slug, "data_source": "supabase"}

    monkeypatch.setattr(repo.settings, "zetaris_enabled", False)
    monkeypatch.setattr(repo.db, "get_school", fake_get_school)
    assert await repo.school_profile("uiuc") == {"slug": "uiuc", "data_source": "supabase"}
    with pytest.raises(ValueError):
        await repo.school_profile("x'; drop table y; --")


async def test_school_profile_degrades_to_supabase_on_zetaris_error(monkeypatch):
    async def boom(*_a, **_k):
        raise ZetarisError("down")

    async def fake_get_school(slug):
        return {"slug": slug, "data_source": "supabase"}

    monkeypatch.setattr(repo.settings, "zetaris_enabled", True)
    monkeypatch.setattr(repo.zetaris, "query", boom)
    monkeypatch.setattr(repo.db, "get_school", fake_get_school)
    repo._cache.clear()
    assert (await repo.school_profile("uiuc"))["data_source"] == "supabase"
