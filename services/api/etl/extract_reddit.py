from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime

import httpx
from pydantic import ValidationError

from app.local_llm import LocalLLMError, chat_structured, settings
from app.profile_text import ProfileFacts, build_profile_text
from app.scoring.metrics import ec_rating_from_tiers, ec_score

from .common import PROCESSED_DIR, RAW_DIR, append_jsonl, log, read_jsonl, supabase
from .prompts import REDDIT_EXTRACTOR_SYSTEM, render_post
from .reddit_schema import RedditApplicantRecord
from .resources import zetaris_paused
from .school_resolver import SchoolResolver

OUT = PROCESSED_DIR / "twins.jsonl"
REJECTS = PROCESSED_DIR / "rejects.jsonl"
CAPS = {"collegeresults": 2400, "TransferToTop25": 600}   # newest posts first; ~3,000 posts (see §2.9.11)
DECISION_WORDS = re.compile(r"accept|admit|reject|denied|deny|waitlist|deferred", re.IGNORECASE)
CONCURRENCY = 1          # one local GPU; Ollama serves requests one at a time at this model size
OUTCOME_RANK = {"accepted": 3, "waitlisted": 2, "rejected": 1}


async def extract_post(post: dict, sem: asyncio.Semaphore) -> tuple[dict, RedditApplicantRecord | None, str | None]:
    async with sem:
        try:
            rec = await chat_structured(
                RedditApplicantRecord, REDDIT_EXTRACTOR_SYSTEM, render_post(post), num_predict=900
            )
            return post, rec, None
        except (LocalLLMError, ValidationError) as exc:      # truncated or schema-invalid output
            return post, None, f"{type(exc).__name__}: {exc}"
        except httpx.HTTPError as exc:                        # Ollama down or model not loaded; record and move on
            return post, None, f"ollama_error: {exc}"


def _cycle_year(rec: RedditApplicantRecord, created: datetime) -> int:
    if rec.matriculation_year and 2015 <= rec.matriculation_year <= 2035:
        return rec.matriculation_year
    # Results season is Dec–May; a post from Jan–Aug of year Y is about matriculation year Y.
    return created.year if created.month <= 8 else created.year + 1


def _clean_numbers(rec: RedditApplicantRecord, issues: list[str]) -> dict:
    gpa_uw, gpa_w = rec.gpa_uw, rec.gpa_w
    if gpa_uw is not None and gpa_uw > 4.0:          # weighted GPA mislabeled as unweighted
        issues.append(f"gpa_uw {gpa_uw} > 4.0 moved to gpa_w")
        gpa_w, gpa_uw = gpa_w or gpa_uw, None
    sat = rec.sat_total if rec.sat_total and 400 <= rec.sat_total <= 1600 else None
    act = rec.act_composite if rec.act_composite and 1 <= rec.act_composite <= 36 else None
    rank = rec.class_rank_pct if rec.class_rank_pct is not None and 0 < rec.class_rank_pct <= 1 else None
    return {"gpa_uw": gpa_uw, "gpa_w": gpa_w, "sat_score": sat, "act_score": act, "class_rank_pct": rank}


def to_row(post: dict, rec: RedditApplicantRecord, resolver: SchoolResolver) -> tuple[dict | None, str | None]:
    if not rec.is_results_post:
        return None, "not_results_post"

    # Resolve schools; on duplicates keep the strongest outcome (accepted > waitlisted > rejected).
    best: dict[str, tuple[str, str, str]] = {}
    for d in rec.decisions:
        slug = resolver.resolve(d.school_as_written)
        if slug is None:
            continue
        if slug not in best or OUTCOME_RANK[d.outcome] > OUTCOME_RANK[best[slug][0]]:
            best[slug] = (d.outcome, d.round, d.school_as_written)
    if not best:
        return None, "no_resolved_school"

    issues = list(rec.extraction_issues)
    nums = _clean_numbers(rec, issues)
    if rec.extraction_confidence == "low" and nums["gpa_uw"] is None and nums["sat_score"] is None:
        return None, "low_signal"

    tiers = [a.tier for a in rec.activities]
    created = datetime.fromtimestamp(float(post["created_utc"]), tz=UTC)
    activities = [a.model_dump() for a in rec.activities]
    awards = [a.model_dump() for a in rec.awards]
    ec_summary = {
        "tier1": tiers.count(1), "tier2": tiers.count(2), "tier3": tiers.count(3), "tier4": tiers.count(4),
        "ec_score": round(ec_score(tiers), 2),
        "tier_derived_ec_rating": round(ec_rating_from_tiers(tiers), 2),
    }
    facts = ProfileFacts(
        applicant_type=rec.applicant_type,
        intended_major=rec.intended_major_raw,
        major_category=rec.major_category,
        gpa_uw=nums["gpa_uw"], gpa_w=nums["gpa_w"], college_gpa=rec.college_gpa,
        sat=nums["sat_score"], act=nums["act_score"],
        advanced_courses=(rec.ap_count or 0) + (rec.dual_enrollment_count or 0) or None,
        rigor_label=rec.rigor_label,
        spike=rec.spike_summary,
        activities=[(a.tier, a.description) for a in rec.activities],
        awards=[(a.level, a.name) for a in rec.awards],
        hooks=list(rec.hooks),
        school_type=rec.demographics.school_type,
        residency_state=rec.demographics.residency_state,
        income_bracket=rec.demographics.income_bracket,
        first_gen=rec.demographics.first_gen,
    )
    headline = " · ".join(filter(None, [
        f"{nums['gpa_uw']:.2f} UW" if nums["gpa_uw"] else None,
        f"{nums['sat_score']} SAT" if nums["sat_score"]
        else (f"{nums['act_score']} ACT" if nums["act_score"] else "TO"),
        f"{rec.ap_count} AP" if rec.ap_count else None,
        rec.major_category.replace("_", " "),
        f"T1:{tiers.count(1)} T2:{tiers.count(2)}",
    ]))

    row = {
        "reddit_id": post["id"],
        "subreddit": post["subreddit"],
        "source_url": f"https://www.reddit.com{post['permalink']}",
        "post_created_at": created.isoformat(),
        "cycle_year": _cycle_year(rec, created),
        "applicant_type": rec.applicant_type,
        **nums,
        "gpa_w_scale": rec.gpa_w_scale,
        "college_gpa": rec.college_gpa,
        "sat_math": rec.sat_math, "sat_ebrw": rec.sat_ebrw,
        "applied_test_optional": rec.applied_test_optional,
        "ap_count": rec.ap_count, "ib_diploma": rec.ib_diploma,
        "honors_count": rec.honors_count, "dual_enrollment_count": rec.dual_enrollment_count,
        "rigor_label": rec.rigor_label,
        "intended_major": rec.intended_major_raw,
        "major_category": rec.major_category,
        "demographics": rec.demographics.model_dump(),
        "hooks": list(rec.hooks),
        "ec_tier_summary": ec_summary,
        "activities": activities,
        "awards": awards,
        "spike_summary": rec.spike_summary,
        "headline": headline,
        "accepted_schools":   sorted(s for s, v in best.items() if v[0] == "accepted"),
        "waitlisted_schools": sorted(s for s, v in best.items() if v[0] == "waitlisted"),
        "rejected_schools":   sorted(s for s, v in best.items() if v[0] == "rejected"),
        "decisions_detail": [{"slug": s, "outcome": o, "round": r, "as_written": w} for s, (o, r, w) in best.items()],
        "profile_text": build_profile_text(facts),
        "extraction_confidence": rec.extraction_confidence,
        "extraction_issues": issues,
        "extraction_model": settings.etl_model,
    }
    return row, None


def select_posts(done: set[str], limit: int | None) -> list[dict]:
    """Newest posts first, per subreddit, capped at CAPS. Posts that never mention a decision are skipped for free.
    The cap counts posts already processed, so a resumed run does not creep past it."""
    chosen: list[dict] = []
    for sub, cap in CAPS.items():
        posts = [p for p in read_jsonl(RAW_DIR / f"{sub}.jsonl") if DECISION_WORDS.search(p["selftext"])]
        posts.sort(key=lambda p: p["created_utc"], reverse=True)
        chosen += [p for p in posts[:cap] if p["id"] not in done]
    return chosen[:limit] if limit else chosen


async def run_extraction(limit: int | None = None) -> None:
    sb = await supabase()
    resolver = await SchoolResolver.load(sb)
    done = {r["reddit_id"] for r in read_jsonl(OUT)} | {r["reddit_id"] for r in read_jsonl(REJECTS)}
    posts = select_posts(done, limit)
    log.info("extracting %d posts (%d already processed)", len(posts), len(done))

    kept = rejected = 0
    async with zetaris_paused():              # frees ~12 GB of RAM for the model; restarts Zetaris afterwards
        sem = asyncio.Semaphore(CONCURRENCY)
        tasks = [asyncio.create_task(extract_post(p, sem)) for p in posts]
        for i, fut in enumerate(asyncio.as_completed(tasks), 1):
            post, rec, err = await fut
            row, reason = (None, err) if rec is None else to_row(post, rec, resolver)
            if row:
                append_jsonl(OUT, [row])
                kept += 1
            else:
                append_jsonl(REJECTS, [{"reddit_id": post["id"], "reason": reason}])
                rejected += 1
            if i % 100 == 0:
                log.info("progress %d/%d kept=%d rejected=%d", i, len(posts), kept, rejected)
    resolver.dump_unresolved(PROCESSED_DIR / "unresolved_schools.csv")
    log.info("done: kept=%d rejected=%d", kept, rejected)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Extract Reddit posts into data/processed/twins.jsonl")
    ap.add_argument("--limit", type=int, default=None, help="process at most N posts (use 20 for the smoke run)")
    asyncio.run(run_extraction(ap.parse_args().limit))
