from __future__ import annotations

from collections import defaultdict

import yaml

from .common import DATA_DIR, fetch_all, log, supabase

MIN_N = 15        # below this, a per-major multiplier is noise


async def refresh_stats() -> None:
    sb = await supabase()
    await sb.rpc("refresh_twin_stats", {}).execute()
    stats = await fetch_all(sb, "school_major_stats")
    overrides = yaml.safe_load((DATA_DIR / "major_overrides.yaml").read_text()) or {}

    by_school: dict[str, dict] = defaultdict(dict)
    for r in stats:
        if r["n"] >= MIN_N:
            by_school[r["slug"]][r["major_category"]] = {
                "multiplier": round(r["smoothed_multiplier"], 3),
                "n": r["n"],
                "reddit_admit_rate": round(r["reddit_admit_rate"], 3),
                "source": "reddit_smoothed",
            }
    for slug, majors in overrides.items():
        for cat, o in majors.items():
            entry = by_school[slug].get(cat, {"n": 0, "source": "default", "multiplier": 1.0})
            entry |= {k: v for k, v in o.items() if v is not None}
            if o.get("multiplier") is not None:
                entry["source"] = "override"
            by_school[slug][cat] = entry

    for slug, mc in by_school.items():
        await sb.table("universities_cds").update({"major_competitiveness": mc}).eq("slug", slug).execute()
    log.info("major_competitiveness updated for %d schools", len(by_school))
