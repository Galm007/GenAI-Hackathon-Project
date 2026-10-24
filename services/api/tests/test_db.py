"""app.db against a real postgrest client whose HTTP transport is mocked (no Supabase needed)."""
import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs

import httpx
import pytest
from postgrest import AsyncPostgrestClient

from app import db

MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase" / "migrations"


def sql_params(fn: str) -> set[str]:
    """Parameter names of a SQL function, read from the migrations, so RPC bodies can't drift from the schema."""
    sql = "\n".join(p.read_text(encoding="utf-8") for p in sorted(MIGRATIONS.glob("*.sql")))
    m = re.search(rf"create or replace function public\.{fn}\((.*?)\)\s*returns", sql, re.S | re.I)
    assert m, fn
    args = re.sub(r"--[^\n]*", "", m.group(1))
    return {a.split()[0] for a in args.split(",") if a.strip()}


class FakeSupabase:
    def __init__(self, reply):
        self.requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            status, body = reply(request)
            return httpx.Response(status, json=body)

        pg = AsyncPostgrestClient("http://sb.test/rest/v1",
                                  http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        self.client = SimpleNamespace(table=pg.from_, rpc=pg.rpc)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]

    def params(self, i: int = -1) -> dict[str, list[str]]:
        return parse_qs(self.requests[i].url.query.decode())

    def body(self, i: int = -1):
        return json.loads(self.requests[i].content)


@pytest.fixture
def fake(monkeypatch):
    def install(reply=lambda req: (200, [])):
        f = FakeSupabase(reply)

        async def sb():
            return f.client
        monkeypatch.setattr(db, "sb", sb)
        monkeypatch.setattr(db, "_school_cache", {})
        return f
    return install


# ---------- schools ----------
async def test_get_school_queries_by_slug_and_caches(fake):
    f = fake(lambda req: (200, [{"slug": "uiuc", "name": "UIUC"}]))
    assert (await db.get_school("uiuc"))["name"] == "UIUC"
    assert f.last.url.path == "/rest/v1/universities_cds" and f.params()["slug"] == ["eq.uiuc"]
    await db.get_school("uiuc")
    assert len(f.requests) == 1                                   # served from the 10-minute cache
    stamp, row = db._school_cache["uiuc"]
    db._school_cache["uiuc"] = (stamp - db.SCHOOL_TTL_S - 1, row)
    await db.get_school("uiuc")
    assert len(f.requests) == 2                                   # expired after SCHOOL_TTL_S


async def test_get_school_unknown_slug_raises(fake):
    fake(lambda req: (200, []))
    with pytest.raises(ValueError, match="unknown school slug: nope"):
        await db.get_school("nope")


async def test_peer_schools(fake):
    f = fake(lambda req: (200, [{"slug": "cmu"}, {"slug": "gatech"}]))
    assert await db.peer_schools("uiuc", "t20_public") == ["cmu", "gatech"]
    p = f.params()
    assert (p["peer_group"], p["slug"], p["limit"]) == (["eq.t20_public"], ["neq.uiuc"], ["6"])


async def test_resolve_school(fake):
    f = fake(lambda req: (200, [{"slug": "uiuc", "name": "UIUC", "score": 0.9}]))
    assert (await db.resolve_school("illinois"))[0]["slug"] == "uiuc"
    assert f.last.url.path == "/rest/v1/rpc/resolve_school"
    assert f.body() == {"q": "illinois", "max_results": 8} and set(f.body()) <= sql_params("resolve_school")


# ---------- twins RPCs ----------
EMB = [0.01] * 768


async def test_match_twins_calls_the_rpc_with_schema_params(fake):
    f = fake(lambda req: (200, [{"id": "t1"}]))
    rows = await db.match_twins(EMB, ["uiuc"], k=5, gpa=3.94, sat=1520, outcome="accepted")
    assert rows == [{"id": "t1"}] and f.last.url.path == "/rest/v1/rpc/match_applicant_twins"
    body = f.body()
    assert set(body) <= sql_params("match_applicant_twins")
    assert (body["target_schools"], body["match_count"], body["applicant_kind"], body["outcome_filter"]) == \
        (["uiuc"], 5, "first_year", "accepted")
    assert len(body["query_embedding"]) == 768


async def test_neighborhood_stats_returns_first_row_or_empty(fake):
    f = fake(lambda req: (200, [{"n_neighbors": 50, "sum_w": 33.1}]))
    assert (await db.neighborhood_stats(EMB, ["uiuc"], k=50, gpa=None, sat=None))["n_neighbors"] == 50
    assert set(f.body()) <= sql_params("twin_neighborhood_stats") and f.body()["k"] == 50
    fake(lambda req: (200, []))
    assert await db.neighborhood_stats(EMB, ["uiuc"], k=50, gpa=None, sat=None) == {}


async def test_major_arbitrage(fake):
    f = fake(lambda req: (200, [{"major_category": "math_stats", "n_neighbors": 41}]))
    rows = await db.major_arbitrage(EMB, "uiuc", gpa=3.9, sat=1500)
    assert rows[0]["major_category"] == "math_stats"
    assert f.last.url.path == "/rest/v1/rpc/major_arbitrage_candidates"
    assert set(f.body()) <= sql_params("major_arbitrage_candidates") and f.body()["target_school"] == "uiuc"


async def test_admitted_medians(fake):
    f = fake(lambda req: (200, [{"gpa_uw": 3.9}]))
    assert await db.admitted_medians("uiuc") == {"gpa_uw": 3.9}
    assert set(f.body()) <= sql_params("admitted_profile_medians")
    fake(lambda req: (200, []))
    assert await db.admitted_medians("uiuc") == {}


async def test_school_calibration_defaults_to_1(fake):
    f = fake(lambda req: (200, [{"odds_inflation": "2.4"}]))
    assert await db.school_calibration("uiuc") == 2.4
    assert f.last.url.path == "/rest/v1/school_reddit_calibration" and f.params()["slug"] == ["eq.uiuc"]
    fake(lambda req: (200, []))
    assert await db.school_calibration("nowhere") == 1.0


async def test_twin_detail_never_selects_demographics(fake):
    f = fake(lambda req: (200, {"id": "t1", "headline": "h"}))
    assert (await db.twin_detail("t1"))["headline"] == "h"
    cols = set(f.params()["select"][0].split(","))
    assert "headline" in cols and not cols & {"race", "ethnicity", "gender", "demographics", "reddit_username"}
    assert f.params()["id"] == ["eq.t1"]


# ---------- web research cache ----------
async def test_research_cache_get_hit_and_miss(fake):
    f = fake(lambda req: (200, [{"results": [{"url": "u"}]}]))
    assert await db.research_cache_get("uiuc", "q") == [{"url": "u"}]
    p = f.params()
    assert p["query_hash"] == ["eq." + hashlib.sha256(b"uiuc|q").hexdigest()]
    assert p["fetched_at"][0].startswith("gte.20")                # 7-day freshness cutoff
    fake(lambda req: (200, []))
    assert await db.research_cache_get("uiuc", "q") is None


async def test_research_cache_put_upserts(fake):
    f = fake(lambda req: (201, []))
    await db.research_cache_put("uiuc", "q", [{"url": "u"}])
    assert f.last.method == "POST" and "merge-duplicates" in f.last.headers["prefer"]
    assert f.body()["query_hash"] == hashlib.sha256(b"uiuc|q").hexdigest() and f.body()["results"] == [{"url": "u"}]


# ---------- runs ----------
async def test_save_append_and_load_run(fake):
    f = fake(lambda req: (200, [{"id": "r1", "status": "complete"}]))
    await db.save_run({"id": "r1", "session_id": "s", "status": "running"})
    assert f.last.method == "POST" and f.last.url.path == "/rest/v1/evaluation_runs"
    await db.append_event_log("r1", [{"seq": 0}], "complete")
    assert f.last.method == "PATCH" and f.params()["id"] == ["eq.r1"]
    assert f.body() == {"event_log": [{"seq": 0}], "status": "complete"}
    assert (await db.load_run("r1"))["status"] == "complete"
    fake(lambda req: (200, []))
    assert await db.load_run("missing") is None
