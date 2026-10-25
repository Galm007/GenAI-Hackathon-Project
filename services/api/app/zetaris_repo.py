from __future__ import annotations

import json
import re
import time
from typing import Any

from . import db
from .config import settings
from .zetaris import ZetarisError, zetaris

SLUG_RE = re.compile(r"^[a-z0-9_]+$")
ALLOWED_RELATIONS = {
    "adcom.v_school_profile", "adcom.v_school_c7_long", "adcom.v_major_stats",
    "adcom.v_reddit_calibration", "adcom.v_admitted_medians", "adcom.v_peer_benchmarks",
}
FORBIDDEN = re.compile(r"\b(insert|update|delete|merge|drop|create|alter|truncate|register|grant|revoke|upsert|"
                       r"uncache|cache|refresh|assign|load|turn|invalidate)\b", re.IGNORECASE)
RELATION_RE = re.compile(r"\b(?:from|join)\s+([`\w.]+)", re.IGNORECASE)
CTE_RE = re.compile(r"(?:\bwith|,)\s*(\w+)\s+as\s*\(", re.IGNORECASE)
LIMIT_RE = re.compile(r"\blimit\s+(\d+)\s*$", re.IGNORECASE)
MAX_AGENT_ROWS = 50
TTL_S = 600

_cache: dict[str, tuple[float, Any]] = {}


class SqlNotAllowed(ValueError):
    pass


def _f(v: str | None) -> float | None:
    return None if v in (None, "", "null", "NULL") else float(v)


def _i(v: str | None) -> int | None:
    return None if v in (None, "", "null", "NULL") else int(float(v))


def _j(v: str | None, default: Any) -> Any:
    try:
        return json.loads(v) if v else default
    except (TypeError, ValueError):
        return default


async def _cached(key: str, fn):
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < TTL_S:
        return hit[1]
    value = await fn()
    _cache[key] = (time.monotonic(), value)
    return value


def _profile_row(r: dict) -> dict:
    """Same shape as a universities_cds row (§2.3), so every consumer is source-agnostic."""
    return {
        "slug": r["slug"], "unitid": _i(r.get("unitid")), "name": r.get("name"), "city": r.get("city"),
        "state": r.get("state"), "control": r.get("control"), "peer_group": r.get("peer_group") or "other",
        "admit_rate": _f(r.get("admit_rate")), "admit_rate_source": r.get("admit_rate_source"),
        "ed_admit_rate": _f(r.get("ed_admit_rate")), "ea_admit_rate": _f(r.get("ea_admit_rate")),
        "rd_admit_rate": _f(r.get("rd_admit_rate")), "in_state_admit_rate": _f(r.get("in_state_admit_rate")),
        "out_state_admit_rate": _f(r.get("out_state_admit_rate")), "test_policy": r.get("test_policy") or "unknown",
        "sat_composite_25": _i(r.get("sat_composite_25")), "sat_composite_75": _i(r.get("sat_composite_75")),
        "act_composite_25": _i(r.get("act_composite_25")), "act_composite_75": _i(r.get("act_composite_75")),
        "c7_weights": _j(r.get("c7_weights"), {}), "c7_source": r.get("c7_source"),
        "early_plans": _j(r.get("early_plans"), {}), "major_competitiveness": _j(r.get("major_competitiveness"), {}),
        "transfer_profile": _j(r.get("transfer_profile"), {}), "cds_year": r.get("cds_year"),
        "data_source": "zetaris",
    }


async def school_profile(slug: str) -> dict:
    if not SLUG_RE.match(slug):
        raise ValueError(f"invalid slug: {slug!r}")
    if not settings.zetaris_enabled:
        return await db.get_school(slug)

    async def load() -> dict:
        try:
            rows = await zetaris.query(f"SELECT * FROM {settings.zetaris_gold_profile} WHERE slug = '{slug}' LIMIT 1")
        except ZetarisError:
            return await db.get_school(slug)                  # degrade to the operational copy
        if not rows:
            raise ValueError(f"unknown school slug: {slug}")
        return _profile_row(rows[0])

    return await _cached(f"profile:{slug}", load)


async def peer_schools(slug: str, peer_group: str, limit: int = 6) -> list[str]:
    if not SLUG_RE.match(peer_group):
        return []
    try:
        rows = await zetaris.query(f"SELECT slug FROM {settings.zetaris_gold_profile} "
                                   f"WHERE peer_group = '{peer_group}' AND slug <> '{slug}' LIMIT {int(limit)}")
        return [r["slug"] for r in rows]
    except ZetarisError:
        return await db.peer_schools(slug, peer_group, limit)


async def reddit_calibration(slug: str) -> float:
    async def load() -> float:
        try:
            rows = await zetaris.query(
                f"SELECT odds_inflation FROM ADCOM.v_reddit_calibration WHERE slug = '{slug}' LIMIT 1"
            )
            return _f(rows[0]["odds_inflation"]) or 1.0 if rows else 1.0
        except ZetarisError:
            return await db.school_calibration(slug)
    return await _cached(f"calib:{slug}", load)


async def admitted_medians(slug: str) -> dict:
    async def load() -> dict:
        try:
            rows = await zetaris.query(f"SELECT * FROM ADCOM.v_admitted_medians WHERE slug = '{slug}' LIMIT 1")
        except ZetarisError:
            return await db.admitted_medians(slug)
        if not rows:
            return {"n": 0}
        r = rows[0]
        return {"n": _i(r.get("n")) or 0, "gpa_uw": _f(r.get("gpa_uw")), "sat": _f(r.get("sat")),
                "advanced": _f(r.get("advanced")), "ec_rating": _f(r.get("ec_rating")),
                "spike_points": _f(r.get("spike_points"))}
    return await _cached(f"medians:{slug}", load)


def guard_agent_sql(sql: str) -> str:
    """Application-level guard; the Zetaris role grants (04_security.sql) are the second wall."""
    s = sql.strip().rstrip(";").strip()
    if ";" in s:
        raise SqlNotAllowed("Send exactly one statement.")
    if not re.match(r"(?is)^(select|with)\b", s):
        raise SqlNotAllowed("Only SELECT queries are allowed.")
    if FORBIDDEN.search(s):
        raise SqlNotAllowed("Read-only access: that keyword is not allowed.")
    ctes = {c.lower() for c in CTE_RE.findall(s)}
    relations = {r.strip("`").lower() for r in RELATION_RE.findall(s)} - ctes
    if not relations or not relations <= ALLOWED_RELATIONS:
        raise SqlNotAllowed("Query only these views: " + ", ".join(sorted(ALLOWED_RELATIONS)))
    m = LIMIT_RE.search(s)
    if m is None:
        return f"SELECT * FROM ({s}) q LIMIT {MAX_AGENT_ROWS}"
    if int(m.group(1)) > MAX_AGENT_ROWS:
        return s[: m.start(1)] + str(MAX_AGENT_ROWS)
    return s


async def agent_query(sql: str) -> tuple[str, list[dict]]:
    safe = guard_agent_sql(sql)
    return safe, await zetaris.query(safe, page_limit=MAX_AGENT_ROWS)
