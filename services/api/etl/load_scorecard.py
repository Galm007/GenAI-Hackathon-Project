from __future__ import annotations

import csv
import re

import httpx
import yaml

from .common import DATA_DIR, log, supabase

SCORECARD_URL = "https://api.data.gov/ed/collegescorecard/v1/schools"
FIELD_MAP = {
    "id": "unitid",
    "school.name": "name",
    "school.city": "city",
    "school.state": "state",
    "school.ownership": "control",
    "school.school_url": "website",
    "latest.admissions.admission_rate.overall": "admit_rate",
    "latest.admissions.sat_scores.25th_percentile.critical_reading": "sat_ebrw_25",
    "latest.admissions.sat_scores.75th_percentile.critical_reading": "sat_ebrw_75",
    "latest.admissions.sat_scores.25th_percentile.math": "sat_math_25",
    "latest.admissions.sat_scores.75th_percentile.math": "sat_math_75",
    "latest.admissions.act_scores.25th_percentile.cumulative": "act_composite_25",
    "latest.admissions.act_scores.75th_percentile.cumulative": "act_composite_75",
    "latest.admissions.test_requirements": "test_requirements",
}
OWNERSHIP = {1: "public", 2: "private_nonprofit", 3: "private_forprofit"}
# IPEDS ADMCON7: 1 required, 2 recommended, 3 neither required nor recommended, 5 considered but not required
TEST_POLICY = {1: "required", 2: "optional", 3: "blind", 5: "optional"}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


async def _fetch(http: httpx.AsyncClient, params: dict) -> list[dict]:
    results, page = [], 0
    while True:
        resp = await http.get(SCORECARD_URL, params=params | {"page": page, "per_page": 100})
        resp.raise_for_status()
        body = resp.json()
        results.extend(body["results"])
        if (page + 1) * 100 >= body["metadata"]["total"]:
            return results
        page += 1


def _to_row(r: dict, seed: dict[int, dict]) -> dict:
    row = {col: r.get(field) for field, col in FIELD_MAP.items()}
    s = seed.get(row["unitid"], {})
    imputed = []
    if row["sat_ebrw_25"] and row["sat_math_25"]:
        row["sat_composite_25"] = row["sat_ebrw_25"] + row["sat_math_25"]     # approximation; CDS C9 overrides
        row["sat_composite_75"] = row["sat_ebrw_75"] + row["sat_math_75"]
        imputed += ["sat_composite_25", "sat_composite_75"]
    row["control"] = OWNERSHIP.get(row["control"])
    row["test_policy"] = TEST_POLICY.get(row.pop("test_requirements"), "unknown")
    row["slug"] = s.get("slug") or slugify(row["name"])
    row["short_name"] = s.get("short_name")
    row["peer_group"] = s.get("peer_group", "other")
    row["source_urls"] = {"scorecard": f"https://collegescorecard.ed.gov/school/?{row['unitid']}"}
    row["data_quality"] = {"imputed": imputed, "base_source": "scorecard"}
    return row


async def load_scorecard() -> None:
    from app.config import settings  # lazy: app.config (B01) needs API keys at import time

    with (DATA_DIR / "schools_seed.csv").open() as f:
        seed = {int(r["unitid"]): r for r in csv.DictReader(f)}
    fields = ",".join(FIELD_MAP)
    async with httpx.AsyncClient(timeout=60) as http:
        base = {"api_key": settings.scorecard_api_key, "fields": fields}
        selective = await _fetch(http, base | {
            "latest.admissions.admission_rate.overall__range": "0..0.40",
            "latest.student.size__range": "1000..",
        })
        seeded = await _fetch(http, base | {"id": ",".join(map(str, seed))})
    by_id = {r["id"]: r for r in selective + seeded}
    rows = [_to_row(r, seed) for r in by_id.values()]

    sb = await supabase()
    # Scorecard runs BEFORE load_cds; CDS values overwrite these columns afterwards.
    await sb.table("universities_cds").upsert(rows, on_conflict="slug").execute()

    aliases: dict[str, str] = {}
    for r in rows:
        aliases[r["name"].lower()] = r["slug"]
        if r["short_name"]:
            aliases[r["short_name"].lower()] = r["slug"]
    for s in seed.values():
        for a in s["aliases"].split("|"):
            aliases[a.strip().lower()] = s["slug"]
    for slug, names in yaml.safe_load((DATA_DIR / "school_aliases.yaml").read_text()).items():
        for a in names:
            aliases[a.lower()] = slug
    valid = {r["slug"] for r in rows}
    await sb.table("school_aliases").upsert(
        [{"alias": a, "slug": s} for a, s in aliases.items() if s in valid], on_conflict="alias"
    ).execute()
    log.info("loaded %d schools, %d aliases", len(rows), len(aliases))
