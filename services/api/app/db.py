from __future__ import annotations

import hashlib
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from supabase import AsyncClient, acreate_client

from .config import settings

_sb: AsyncClient | None = None


async def sb() -> AsyncClient:
    global _sb
    if _sb is None:
        _sb = await acreate_client(settings.supabase_url, settings.supabase_service_role_key)
    return _sb


_school_cache: dict[str, tuple[float, dict]] = {}
SCHOOL_TTL_S = 600


async def get_school(slug: str) -> dict[str, Any]:
    hit = _school_cache.get(slug)
    if hit and time.monotonic() - hit[0] < SCHOOL_TTL_S:
        return hit[1]
    res = await (await sb()).table("universities_cds").select("*").eq("slug", slug).maybe_single().execute()
    if res is None or not res.data:
        raise ValueError(f"unknown school slug: {slug}")
    _school_cache[slug] = (time.monotonic(), res.data)
    return res.data


async def peer_schools(slug: str, peer_group: str, limit: int = 6) -> list[str]:
    res = await (await sb()).table("universities_cds").select("slug").eq("peer_group", peer_group) \
        .neq("slug", slug).limit(limit).execute()
    return [r["slug"] for r in res.data]


async def match_twins(embedding: list[float], schools: list[str], *, k: int, gpa: float | None,
                      sat: int | None, kind: str = "first_year", outcome: str = "any") -> list[dict]:
    res = await (await sb()).rpc("match_applicant_twins", {
        "query_embedding": embedding, "target_schools": schools, "match_count": k,
        "applicant_kind": kind, "query_gpa_uw": gpa, "query_sat": sat, "outcome_filter": outcome,
    }).execute()
    return res.data or []


async def neighborhood_stats(embedding: list[float], schools: list[str], *, k: int, gpa: float | None,
                             sat: int | None, kind: str = "first_year") -> dict:
    res = await (await sb()).rpc("twin_neighborhood_stats", {
        "query_embedding": embedding, "target_schools": schools, "k": k,
        "applicant_kind": kind, "query_gpa_uw": gpa, "query_sat": sat,
    }).execute()
    return (res.data or [{}])[0]


async def school_calibration(slug: str) -> float:
    res = await (await sb()).table("school_reddit_calibration").select("odds_inflation") \
        .eq("slug", slug).maybe_single().execute()
    return float(res.data["odds_inflation"]) if res is not None and res.data else 1.0


async def major_arbitrage(embedding: list[float], slug: str, *, gpa: float | None, sat: int | None) -> list[dict]:
    res = await (await sb()).rpc("major_arbitrage_candidates", {
        "query_embedding": embedding, "target_school": slug, "query_gpa_uw": gpa, "query_sat": sat,
    }).execute()
    return res.data or []


def _qhash(slug: str, query: str) -> str:
    return hashlib.sha256(f"{slug}|{query}".encode()).hexdigest()


async def research_cache_get(slug: str, query: str, max_age_days: int = 7) -> list[dict] | None:
    cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).isoformat()
    res = await (await sb()).table("web_research_cache").select("results") \
        .eq("query_hash", _qhash(slug, query)).gte("fetched_at", cutoff).maybe_single().execute()
    return res.data["results"] if res is not None and res.data else None


async def research_cache_put(slug: str, query: str, results: list[dict]) -> None:
    await (await sb()).table("web_research_cache").upsert({
        "query_hash": _qhash(slug, query), "school_slug": slug, "query": query, "results": results,
        "fetched_at": datetime.now(UTC).isoformat(),
    }).execute()


async def save_run(row: dict[str, Any]) -> None:
    await (await sb()).table("evaluation_runs").upsert(row).execute()


async def resolve_school(q: str) -> list[dict]:
    res = await (await sb()).rpc("resolve_school", {"q": q, "max_results": 8}).execute()
    return res.data or []


async def twin_detail(twin_id: str) -> dict:
    cols = ("id,source_url,cycle_year,applicant_type,gpa_uw,gpa_w,sat_score,act_score,ap_count,ib_diploma,"
            "intended_major,major_category,hooks,ec_tier_summary,activities,awards,spike_summary,headline,"
            "decisions_detail,rigor_label")          # demographics deliberately excluded
    res = await (await sb()).table("applicant_twins").select(cols).eq("id", twin_id).single().execute()
    return res.data


async def admitted_medians(slug: str) -> dict:
    res = await (await sb()).rpc("admitted_profile_medians", {"target_school": slug}).execute()
    return (res.data or [{}])[0]


async def append_event_log(run_id: str, events: list[dict], status: str) -> None:
    await (await sb()).table("evaluation_runs").update({"event_log": events, "status": status}) \
        .eq("id", run_id).execute()


async def load_run(run_id: str) -> dict | None:
    res = await (await sb()).table("evaluation_runs").select("*").eq("id", run_id).maybe_single().execute()
    return res.data if res is not None else None
