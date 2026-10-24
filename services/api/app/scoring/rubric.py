from __future__ import annotations

import math
from statistics import mean

from app.schemas.common import C7_FACTORS
from app.schemas.institution import InstitutionalBrief, SchoolRubric

C7_WEIGHT = {"very_important": 1.0, "important": 0.66, "considered": 0.33, "not_considered": 0.0}
DEFAULT_LEVEL = "considered"
PILLAR_FACTORS = {
    "academic": ("rigor", "class_rank", "academic_gpa", "test_scores"),
    "extracurricular": ("extracurriculars", "talent_ability", "volunteer_work", "work_experience"),
    "personal": ("essay", "recommendations", "character", "interview"),
}
# hook → (gating C7 factor or None, max logit effect at "very_important"). Donations are never modeled.
HOOK_RULES: dict[str, tuple[str | None, float]] = {
    "recruited_athlete": ("talent_ability", 3.0),
    "legacy": ("alumni_relation", 1.4),
    "faculty_staff_child": ("alumni_relation", 1.0),
    "first_gen": ("first_generation", 0.5),
    "rural": ("geographic_residence", 0.3),
    "low_income": (None, 0.3),
    "questbridge_finalist": (None, 0.4),
    "veteran": (None, 0.3),
}
MAJOR_MULT_BOUNDS = (0.25, 2.0)


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def build_school_rubric(school: dict, major_category: str, residency_state: str | None) -> SchoolRubric:
    notes: list[str] = []
    c7 = school.get("c7_weights") or {}
    if not c7:
        notes.append("C7 weights unavailable; every factor defaulted to 'considered'.")
    levels = {f: c7.get(f, DEFAULT_LEVEL) for f in C7_FACTORS}
    w = lambda f: C7_WEIGHT[levels[f]]  # noqa: E731

    raw = {p: mean(w(f) for f in fs) for p, fs in PILLAR_FACTORS.items()}
    raw["athletic"] = 0.5 * w("talent_ability")
    total = sum(raw.values()) or 1.0
    pillar_weights = {p: round(v / total, 4) for p, v in raw.items()}

    test_policy = school.get("test_policy") or "unknown"
    test_weight = 0.0 if test_policy == "blind" else w("test_scores")

    hook_effects = {h: round(eff * (w(f) if f else 1.0), 3) for h, (f, eff) in HOOK_RULES.items()}

    base = float(school.get("admit_rate") or 0.10)
    if not school.get("admit_rate"):
        notes.append("Admit rate missing; defaulted to 10%.")

    residency_effect = 0.0
    if school.get("control") == "public" and school.get("state") and residency_state:
        in_state = residency_state.upper() == school["state"]
        ins, outs = school.get("in_state_admit_rate"), school.get("out_state_admit_rate")
        if ins and outs:
            residency_effect = _logit(float(ins if in_state else outs)) - _logit(base)
        else:
            sw = w("state_residency")
            residency_effect = 0.8 * sw if in_state else -0.4 * sw
        notes.append(f"{'In' if in_state else 'Out-of'}-state applicant at a public university.")

    mc = (school.get("major_competitiveness") or {}).get(major_category) or {}
    mult = float(mc.get("multiplier") or 1.0)
    mult = min(max(mult, MAJOR_MULT_BOUNDS[0]), MAJOR_MULT_BOUNDS[1])

    return SchoolRubric(
        slug=school["slug"], name=school["name"], base_admit_rate=base,
        ed_admit_rate=school.get("ed_admit_rate"), rd_admit_rate=school.get("rd_admit_rate"),
        pillar_weights=pillar_weights, factor_levels=levels, test_weight=test_weight,
        test_policy=test_policy, sat_25=school.get("sat_composite_25"), sat_75=school.get("sat_composite_75"),
        hook_effects=hook_effects, residency_effect=round(residency_effect, 3),
        major_category=major_category, major_multiplier=round(mult, 3),
        major_multiplier_source=mc.get("source", "default") if mc else "default",
        major_n=int(mc.get("n", 0)), major_college=mc.get("college"), direct_admit=mc.get("direct_admit"),
        notes=notes,
    )


def apply_brief_adjustments(r: SchoolRubric, brief: InstitutionalBrief | None) -> SchoolRubric:
    """Fact-checked web findings may correct exactly two things: test policy and the major's admit model."""
    if brief is None:
        return r
    upd: dict = {"notes": list(r.notes)}
    tp = next((fc for fc in brief.fact_checks if fc.field == "test_policy" and fc.verdict == "updated"), None)
    if tp and brief.current_test_policy != "unknown" and brief.current_test_policy != r.test_policy:
        upd["test_policy"] = brief.current_test_policy
        if brief.current_test_policy == "blind":
            upd["test_weight"] = 0.0
        upd["notes"].append(f"Test policy updated from web ({', '.join(tp.source_ids)}).")
    if r.direct_admit is None and brief.major_admission_model == "direct_admit_capped":
        upd["direct_admit"] = True
        upd["notes"].append("Major confirmed as capped direct-admit by fact-checker.")
    return r.model_copy(update=upd)
