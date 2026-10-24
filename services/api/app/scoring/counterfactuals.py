from __future__ import annotations

from app import db
from app.schemas.delta import Counterfactual
from app.schemas.dossier import DossierGrade, ParsedDossier
from app.schemas.institution import SchoolRubric

from .metrics import ec_rating_from_tiers
from .probability import ScoringInputs, compute_probability

ADJACENT_MAJORS: dict[str, tuple[str, ...]] = {
    "computer_science": ("math_stats", "data_science", "electrical_engineering", "physics_astro"),
    "computer_engineering": ("electrical_engineering", "computer_science", "physics_astro"),
    "electrical_engineering": ("physics_astro", "computer_engineering", "math_stats"),
    "mechanical_aerospace": ("physics_astro", "other_engineering"),
    "business": ("economics", "math_stats"),
    "economics": ("math_stats", "political_science"),
    "biology": ("neuroscience", "chemistry"),
    "pre_health": ("biology", "neuroscience", "psychology"),
    "data_science": ("math_stats", "computer_science"),
}
MIN_ARBITRAGE_N = 15
MIN_DELTA_PP = 0.3


async def generate_counterfactuals(
    x: ScoringInputs, *, rubric: SchoolRubric, grade: DossierGrade, dossier: ParsedDossier,
    school: dict, embedding: list[float], gpa: float | None,
) -> list[Counterfactual]:
    p0 = compute_probability(x).p_final
    out: list[Counterfactual] = []

    def add(cid: str, kind: str, label: str, overrides: dict, confidence: str, evidence: str) -> None:
        p = compute_probability(x.with_overrides(**overrides)).p_final
        out.append(Counterfactual(id=cid, kind=kind, label=label, p_new=p, delta_pp=round((p - p0) * 100, 2),
                                  confidence=confidence, evidence=evidence, overrides=overrides))

    # 1) Testing
    if x.test_weight > 0 and x.sat_75 and (x.sat is None or x.sat < x.sat_75):
        add("cf_sat_75", "test_score", f"Raise SAT to the school's 75th percentile ({x.sat_75})",
            {"sat": x.sat_75}, "data_backed", "CDS C9 75th percentile")
    if x.test_policy == "optional" and x.sat and x.sat_25 and x.sat < x.sat_25:
        add("cf_test_optional", "test_score", "Apply test-optional (withhold a below-25th-percentile score)",
            {"sat": None}, "model_estimate", "CDS C8 test-optional policy")

    # 2) Extracurricular tier moves
    tiers = [ag.tier for ag in grade.activity_grades]
    base_anchor = ec_rating_from_tiers(tiers)

    def ec_override(new_tiers: list[int]) -> dict:
        shift = ec_rating_from_tiers(new_tiers) - base_anchor
        return {"ratings": {**x.ratings, "extracurricular": max(1.0, x.ratings["extracurricular"] + shift)}}

    add("cf_add_tier2", "add_activity", "Add one Tier 2 activity (regional/state distinction)",
        ec_override(tiers + [2]), "model_estimate", "EC rating anchor from tier mix")
    t3 = [ag for ag in grade.activity_grades if ag.tier == 3]
    if t3:
        best = dossier.activities[t3[0].activity_index].name
        promoted = tiers.copy()
        promoted[tiers.index(3)] = 2
        add("cf_promote_t3", "add_activity", f"Elevate '{best}' from Tier 3 to Tier 2 with measurable outcomes",
            ec_override(promoted), "model_estimate", "EC rating anchor from tier mix")

    # 3) Major arbitrage (data-backed via twins who applied to this school in other majors)
    adjacent = set(ADJACENT_MAJORS.get(rubric.major_category, ()))
    if adjacent:
        rows = await db.major_arbitrage(embedding, rubric.slug, gpa=gpa, sat=x.sat)
        mc = school.get("major_competitiveness") or {}
        arb: list[Counterfactual] = []
        for r in rows:
            cat = r["major_category"]
            if cat not in adjacent or r["n_neighbors"] < MIN_ARBITRAGE_N:
                continue
            alt_mult = float((mc.get(cat) or {}).get("multiplier") or r["school_smoothed_multiplier"])
            overrides = {"major_multiplier": min(max(alt_mult, 0.25), 2.0),
                         "twin_sum_w_admit": r["neighbor_admit_rate"] * x.twin_sum_w}
            college = (mc.get(cat) or {}).get("college")
            add(f"cf_major_{cat}", "major_switch",
                f"Apply as {cat.replace('_', ' ')}" + (f" ({college})" if college else ""),
                overrides, "data_backed",
                f"{r['n_neighbors']} academically similar applicants to {rubric.name} in {cat}; "
                f"{r['neighbor_admit_rate']:.0%} admitted (Reddit, before calibration)")
            arb.append(out[-1])
        # keep only the two best major switches
        for cf in sorted(arb, key=lambda c: c.delta_pp)[:-2]:
            out.remove(cf)

    # 4) Application round
    plans = school.get("early_plans") or {}
    if x.early_round in (None, "RD"):
        if plans.get("ed") and x.ed_admit_rate and x.rd_admit_rate:
            add("cf_ed", "early_round", "Apply Early Decision (binding)", {"early_round": "ED"},
                "data_backed", "CDS C21 ED vs RD admit rates (half-credited for pool strength)")
        elif (plans.get("ea") or plans.get("rea")) and x.ea_admit_rate and x.rd_admit_rate:
            add("cf_ea", "early_round", "Apply Early Action", {"early_round": "EA"}, "data_backed",
                "EA vs RD admit rates")

    # 5) Demonstrated interest (only where C7 says it counts)
    if x.applicant_interest_weight >= 0.33 and not x.demonstrated_interest:
        add("cf_interest", "demonstrated_interest", "Demonstrate interest (visit, info session, interview)",
            {"demonstrated_interest": True}, "model_estimate", "CDS C7 applicant_interest is considered")

    # 6) Essay (personal rating one step better)
    if x.ratings["personal"] >= 3.5:
        add("cf_essay", "essay", "Rewrite the essay to raise the Personal rating one step",
            {"ratings": {**x.ratings, "personal": x.ratings["personal"] - 1.0}}, "model_estimate",
            "Personal rating sensitivity under this school's essay weight")

    return sorted((c for c in out if c.delta_pp >= MIN_DELTA_PP), key=lambda c: -c.delta_pp)
