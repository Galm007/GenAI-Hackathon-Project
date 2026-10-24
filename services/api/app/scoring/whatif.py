from __future__ import annotations

from app.api_models import WhatIfRequest, WhatIfResponse

from .metrics import ec_rating_from_tiers
from .probability import compute_probability

ROUND_FLAGS = {"ED": "ed", "ED2": "ed2", "EA": "ea", "REA": "rea"}


def run_what_if(ctx, req: WhatIfRequest) -> WhatIfResponse:
    x = ctx.scoring_inputs
    over: dict = {}
    applied: list[str] = []
    warnings: list[str] = []
    confidence = "data_backed"
    ratings = dict(x.ratings)

    # Testing
    if req.withhold_sat:
        if x.test_policy == "required":
            warnings.append("This school requires test scores, so withholding isn't an option.")
        else:
            over["sat"] = None
            applied.append("Withhold test score")
    elif req.sat is not None and req.sat != x.sat:
        over["sat"] = req.sat
        applied.append(f"SAT {req.sat}")

    # Major: reuse Node 5's data-backed counterfactual when one exists
    if req.major_category and req.major_category != ctx.major_category:
        cf = next((c for c in ctx.counterfactuals if c.id == f"cf_major_{req.major_category}"), None)
        if cf:
            over.update(cf.overrides)
            applied.append(cf.label)
        else:
            mc = (ctx.school.get("major_competitiveness") or {}).get(req.major_category) or {}
            over["major_multiplier"] = min(max(float(mc.get("multiplier") or 1.0), 0.25), 2.0)
            applied.append(f"Apply as {req.major_category.replace('_', ' ')}")
            confidence = "model_estimate"
            if not mc:
                warnings.append("No major-specific data for this school; using the school-wide rate.")

    # Hypothetical new activities shift the EC rating by the change in its tier anchor
    if req.add_activities:
        shift = ec_rating_from_tiers(ctx.tiers + list(req.add_activities)) - ec_rating_from_tiers(ctx.tiers)
        ratings["extracurricular"] = max(1.0, ratings["extracurricular"] + shift)
        applied.append("Add " + ", ".join(f"Tier {t}" for t in req.add_activities) + " activity")
        confidence = "model_estimate"

    # Essay improvement
    if req.essay_steps:
        floor = 1.0 if ctx.has_recommendations else 2.0
        ratings["personal"] = max(floor, ratings["personal"] - req.essay_steps)
        applied.append(f"Essay +{req.essay_steps} step{'s' if req.essay_steps > 1 else ''}")
        confidence = "model_estimate"

    if ratings != x.ratings:
        over["ratings"] = ratings

    # Round
    if req.early_round and req.early_round != (x.early_round or "RD"):
        plans = ctx.school.get("early_plans") or {}
        if req.early_round == "RD" or plans.get(ROUND_FLAGS[req.early_round]):
            over["early_round"] = req.early_round
            applied.append(f"Apply {req.early_round}")
        else:
            warnings.append(f"{ctx.school['name']} doesn't offer {req.early_round}.")

    # Demonstrated interest
    if req.demonstrated_interest is not None and req.demonstrated_interest != x.demonstrated_interest:
        over["demonstrated_interest"] = req.demonstrated_interest
        if req.demonstrated_interest and x.applicant_interest_weight == 0:
            warnings.append("This school doesn't consider demonstrated interest (CDS C7), so it has no effect.")
        else:
            applied.append("Demonstrate interest")

    base = compute_probability(x)
    sim = compute_probability(x.with_overrides(**over)) if over else base
    return WhatIfResponse(baseline=base, simulated=sim, delta_pp=round((sim.p_final - base.p_final) * 100, 2),
                          applied=applied, warnings=warnings, confidence=confidence)
