from __future__ import annotations

import re

import orjson

from app.schemas.common import PILLARS
from app.schemas.debate import Citation
from app.schemas.delta import ProbabilityBreakdown
from app.scoring.probability import ScoringInputs
from app.scoring.rubric import C7_WEIGHT

from .state import AdComState

CITATION_RE = re.compile(r"\[\[(dossier|cds|twin|web|model|sql):([^\]\s]+)\]\]")
DOSSIER_ROOTS = {"activities", "awards", "metrics", "harvard", "spike", "essay", "essay_assessment",
                 "test_scores", "high_school", "courses", "reader_comments", "context", "hooks"}
ESSAY_CHARS = 4000


def build_scoring_inputs(state: AdComState) -> ScoringInputs:
    r, g, b, m, inputs = (state["school_rubric"], state["grade"], state["baseline"], state["metrics"],
                          state["inputs"])
    hooks = set(inputs.hooks)
    if inputs.context.first_gen:
        hooks.add("first_gen")
    if inputs.context.low_income:
        hooks.add("low_income")
    return ScoringInputs(
        base_admit_rate=r.base_admit_rate,
        major_multiplier=r.major_multiplier,
        pillar_weights=r.pillar_weights,
        ratings={p: getattr(g.harvard, p).numeric for p in PILLARS},
        test_weight=r.test_weight, test_policy=r.test_policy,
        sat=m.sat_equivalent, sat_25=r.sat_25, sat_75=r.sat_75,
        hooks=tuple(sorted(hooks)), hook_effects=r.hook_effects, residency_effect=r.residency_effect,
        early_round=inputs.early_round.get(state["school_slug"]),
        ed_admit_rate=r.ed_admit_rate, rd_admit_rate=r.rd_admit_rate,
        ea_admit_rate=state["school"].get("ea_admit_rate"),
        applicant_interest_weight=C7_WEIGHT[r.factor_levels["applicant_interest"]],
        twin_sum_w=b.sum_w, twin_sum_w2=b.sum_w2, twin_sum_w_admit=b.sum_w_admit, odds_inflation=b.odds_inflation,
    )


def build_docket(state: AdComState, prob: ProbabilityBreakdown) -> tuple[str, dict[str, list[str]]]:
    school, r, g, d, m = state["school"], state["school_rubric"], state["grade"], state["dossier"], state["metrics"]
    brief, snippets = state.get("institutional_brief"), state.get("web_snippets", [])
    zq = [f for f in state.get("zetaris_queries", []) if not f.get("error")]
    twins, b, ta = state["twins"], state["baseline"], state.get("twin_analysis")

    cds = {
        "name": school["name"], "cds_year": school.get("cds_year"), "admit_rate": school.get("admit_rate"),
        "ed_admit_rate": school.get("ed_admit_rate"), "rd_admit_rate": school.get("rd_admit_rate"),
        "sat_25": r.sat_25, "sat_75": r.sat_75, "test_policy": r.test_policy,
        "early_plans": school.get("early_plans"),
        "c7": r.factor_levels,
        "major": {r.major_category: {"multiplier": r.major_multiplier, "source": r.major_multiplier_source,
                                     "n": r.major_n, "college": r.major_college, "direct_admit": r.direct_admit}},
        "pillar_weights": r.pillar_weights, "rubric_notes": r.notes,
    }
    applicant = {
        "intended_major": state["inputs"].intended_major, "major_category": g.major_category,
        "metrics": m.model_dump(),
        "harvard": {p: {"rating": getattr(g.harvard, p).rating, "modifier": getattr(g.harvard, p).modifier,
                        "rationale": getattr(g.harvard, p).rationale} for p in PILLARS},
        "spike": g.spike.model_dump(),
        "activities": [{"index": ag.activity_index, "tier": ag.tier, "spike_role": ag.spike_role,
                        "name": d.activities[ag.activity_index].name,
                        "description": d.activities[ag.activity_index].description} for ag in g.activity_grades],
        "awards": [{"index": i, "name": a.name, "level": a.level} for i, a in enumerate(d.awards)],
        "essay_assessment": g.essay.model_dump() if g.essay else None,
        "essay": (d.essay_text or "")[:ESSAY_CHARS],
        "reader_comments": g.reader_comments,
        "hooks": state["inputs"].hooks,
        "context": state["inputs"].context.model_dump(),
    }
    packet = {
        "school_cds": cds,
        "fact_checks": [fc.model_dump() for fc in brief.fact_checks] if brief else [],
        "priorities": [p.model_dump() for p in brief.strategic_priorities] if brief else [],
        "fit_signals": brief.fit_signals if brief else [],
        "misalignment_signals": brief.misalignment_signals if brief else [],
        "web": [{"id": s.id, "title": s.title, "url": s.url} for s in snippets],
        "zetaris_queries": [{"id": f["id"], "purpose": f["purpose"], "sql": f["sql"], "rows": f["rows"][:8]}
                            for f in zq],
        "applicant": applicant,
        "twins": [t.model_dump(include={"index", "outcome", "gpa_uw", "sat_score", "ap_count", "major_category",
                                        "ec_tier_summary", "top_activities", "spike_summary", "cycle_year",
                                        "hooks"}) for t in twins],
        "twin_baseline": b.model_dump(exclude={"sum_w", "sum_w2", "sum_w_admit"}),
        "twin_analysis": ta.model_dump() if ta else None,
        "model": {"p_final": prob.p_final, "p_low": prob.p_low, "p_high": prob.p_high, "p_model": prob.p_model,
                  "base": prob.base_admit_rate, "disposition": prob.disposition,
                  "components": {c.key: {"delta_pp": c.delta_pp, "detail": c.detail} for c in prob.components}},
    }
    # Sorted keys → byte-identical across all four turns → prompt-cache hits on turns 2–4.
    docket = orjson.dumps(packet, option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_2).decode()

    index = {
        "cds": ["name", "cds_year", "admit_rate", "ed_admit_rate", "rd_admit_rate", "sat_25", "sat_75",
                "test_policy", "early_plans", "pillar_weights",
                *(f"c7.{f}" for f in r.factor_levels), f"major.{r.major_category}"],
        "twin": [str(t.index) for t in twins],
        "web": [s.id for s in snippets],
        "sql": [f["id"] for f in zq],
        "model": ["p_final", "p_low", "p_high", "p_model", "base", "disposition",
                  *(c.key for c in prob.components)],
        "dossier_roots": sorted(DOSSIER_ROOTS),
        "dossier.activities": [str(ag.activity_index) for ag in g.activity_grades],
        "dossier.awards": [str(i) for i in range(len(d.awards))],
    }
    return docket, index


def _valid(kind: str, ref: str, idx: dict[str, list[str]]) -> bool:
    if kind == "dossier":
        root, _, rest = ref.partition(".")
        if root in ("activities", "awards"):
            return rest.split(".")[0] in idx[f"dossier.{root}"]
        return root in idx["dossier_roots"]
    return ref in idx.get(kind, [])


def validate_citations(text: str, idx: dict[str, list[str]]) -> list[Citation]:
    return [Citation(kind=mt.group(1), ref=mt.group(2), valid=_valid(mt.group(1), mt.group(2), idx),
                     span=(mt.start(), mt.end()))
            for mt in CITATION_RE.finditer(text)]
