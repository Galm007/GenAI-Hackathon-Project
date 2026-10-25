from __future__ import annotations

import asyncio
import math
import time
from collections import Counter

import anthropic
import orjson

from app import db, llm, zetaris_repo
from app.schemas.twins import EmpiricalBaseline, TwinAnalysis, TwinCard
from app.scoring.probability import from_odds, odds
from app.scoring.radar import build_radar

from ..events import emit, tool_call
from ..prompts.twins import TWIN_ANALYST_SYSTEM
from ..state import AdComState

NODE = "twins"
CONTRAST_POOL = 25
NEIGHBORHOOD_K = 50
Z80 = 1.2816      # 80% interval, matching the 10th/90th percentile band on the gauge


def select_contrastive(pool: list[dict], k: int = 5) -> list[dict]:
    """Top-k by hybrid score, but guarantee at least one admit and one reject when the pool has them —
    a contrast set teaches far more than five identical outcomes."""
    top = list(pool[:k])
    for needed in ("accepted", "rejected"):
        if any(r["outcome"] == needed for r in top):
            continue
        alt = next((r for r in pool[k:] if r["outcome"] == needed), None)
        if alt is None or not top:
            continue
        counts = Counter(r["outcome"] for r in top)
        victim = max(range(len(top)), key=lambda i: (counts[top[i]["outcome"]], -top[i]["hybrid_score"]))
        top[victim] = alt
    return sorted(top, key=lambda r: -r["hybrid_score"])


def _to_card(index: int, r: dict) -> TwinCard:
    acts = sorted(r.get("activities") or [], key=lambda a: a.get("tier", 4))[:4]
    return TwinCard(
        index=index, id=str(r["id"]), source_url=r["source_url"], cycle_year=r.get("cycle_year"),
        matched_school=r["matched_school"], outcome=r["outcome"], gpa_uw=r.get("gpa_uw"),
        sat_score=r.get("sat_score"), act_score=r.get("act_score"), ap_count=r.get("ap_count"),
        intended_major=r.get("intended_major"), major_category=r["major_category"], hooks=r.get("hooks") or [],
        ec_tier_summary=r.get("ec_tier_summary") or {}, top_activities=acts, awards=(r.get("awards") or [])[:4],
        spike_summary=r.get("spike_summary"), headline=r.get("headline"),
        semantic_similarity=r["semantic_similarity"], stat_proximity=r["stat_proximity"],
        hybrid_score=r["hybrid_score"],
    )


def wilson(p: float, n: float, z: float = Z80) -> tuple[float, float]:
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def compute_baseline(stats: dict, inflation: float, widened: bool, peers: list[str]) -> EmpiricalBaseline:
    sum_w, sum_w2, sum_wa = (float(stats.get(k) or 0.0) for k in ("sum_w", "sum_w2", "sum_w_admit"))
    n_eff = (sum_w**2 / sum_w2) if sum_w2 > 0 else 0.0
    rate = stats.get("weighted_admit_rate")
    lo, hi = wilson(rate, n_eff) if rate is not None and n_eff >= 1 else (None, None)
    deflated = from_odds(odds(min(max(rate, 0.01), 0.99)) / inflation) if rate is not None else None
    return EmpiricalBaseline(
        n_neighbors=int(stats.get("n") or 0), n_accepted=int(stats.get("n_accepted") or 0),
        n_waitlisted=int(stats.get("n_waitlisted") or 0), n_rejected=int(stats.get("n_rejected") or 0),
        n_effective=round(n_eff, 2), weighted_admit_rate=rate, wilson_low=lo, wilson_high=hi,
        odds_inflation=inflation, deflated_admit_rate=deflated, widened_to_peers=widened, peer_schools=peers,
        sum_w=sum_w, sum_w2=sum_w2, sum_w_admit=sum_wa,
    )


def _analysis_payload(state: AdComState, cards: list[TwinCard], baseline: EmpiricalBaseline) -> str:
    g, m, d = state["grade"], state["metrics"], state["dossier"]
    applicant = {
        "major_category": g.major_category, "gpa_uw": m.gpa_uw_4, "sat_equivalent": m.sat_equivalent,
        "advanced_courses": m.advanced_course_count, "rigor": g.rigor_label, "spike": g.spike.label,
        "activities": [{"tier": ag.tier, "name": d.activities[ag.activity_index].name} for ag in g.activity_grades],
        "awards": [a.name for a in d.awards], "hooks": state["inputs"].hooks,
    }
    twins = [c.model_dump(include={"index", "outcome", "gpa_uw", "sat_score", "ap_count", "major_category",
                                   "hooks", "ec_tier_summary", "top_activities", "awards", "spike_summary",
                                   "cycle_year", "matched_school"}) for c in cards]
    return ("<applicant>\n" + orjson.dumps(applicant).decode() + "\n</applicant>\n\n"
            "<twins>\n" + orjson.dumps(twins).decode() + "\n</twins>\n\n"
            "<neighborhood_stats>\n" + baseline.model_dump_json() + "\n</neighborhood_stats>\n\n"
            f"School: {state['school_slug']}. Write the twin analysis.")


async def twins_node(state: AdComState) -> dict:
    t0 = time.perf_counter()
    emb, m, slug = state["profile_embedding"], state["metrics"], state["school_slug"]
    gpa, sat = m.gpa_uw_4, m.sat_equivalent
    emit("node_start", node=NODE, label="Applicant Twins (Hybrid RAG)")

    tool_call(NODE, "rpc.match_applicant_twins", "started", schools=[slug], k=CONTRAST_POOL)
    pool = await db.match_twins(emb, [slug], k=CONTRAST_POOL, gpa=gpa, sat=sat)
    schools, widened, peers = [slug], False, []
    if len(pool) < 5:                                    # sparse school → widen to its peer group
        school = await zetaris_repo.school_profile(slug)
        peers = await zetaris_repo.peer_schools(slug, school["peer_group"])
        schools, widened = [slug, *peers], True
        pool = await db.match_twins(emb, schools, k=CONTRAST_POOL, gpa=gpa, sat=sat)
    tool_call(NODE, "rpc.match_applicant_twins", "done", result_count=len(pool), widened=widened)

    cards = [_to_card(i + 1, r) for i, r in enumerate(select_contrastive(pool, 5))]
    emit("twins", twins=[c.model_dump() for c in cards], widened_to_peers=widened, peer_schools=peers)

    tool_call(NODE, "rpc.twin_neighborhood_stats", "started", k=NEIGHBORHOOD_K)
    stats, inflation, medians = await asyncio.gather(
        db.neighborhood_stats(emb, schools, k=NEIGHBORHOOD_K, gpa=gpa, sat=sat),
        zetaris_repo.reddit_calibration(slug),      # Zetaris v_reddit_calibration
        zetaris_repo.admitted_medians(slug),        # Zetaris v_admitted_medians
    )
    baseline = compute_baseline(stats, inflation, widened, peers)
    tool_call(NODE, "rpc.twin_neighborhood_stats", "done", n=baseline.n_neighbors)
    emit("baseline", baseline=baseline.model_dump())
    emit("radar", radar=build_radar(state["metrics"], state["grade"], medians))

    analysis: TwinAnalysis | None = None
    warnings: list[str] = []
    if cards:
        try:
            analysis = await llm.parse(
                TwinAnalysis, system=TWIN_ANALYST_SYSTEM,
                messages=[{"role": "user", "content": _analysis_payload(state, cards, baseline)}],
                effort="medium", max_tokens=10000,
            )
            valid = {c.index for c in cards}
            analysis = analysis.model_copy(
                update={"comparisons": [c for c in analysis.comparisons if c.twin_index in valid]})
        except (llm.LLMRefusal, llm.LLMTruncated, anthropic.APIError) as exc:
            warnings.append(f"twin analysis degraded: {type(exc).__name__}")
    emit("twin_analysis", analysis=analysis.model_dump() if analysis else None)
    emit("node_end", node=NODE, elapsed_ms=int((time.perf_counter() - t0) * 1000))
    return {"twins": cards, "baseline": baseline, "twin_analysis": analysis, "warnings": warnings}
