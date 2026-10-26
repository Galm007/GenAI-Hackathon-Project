from __future__ import annotations

import asyncio
import math

import numpy as np
import statsmodels.api as sm

from app.scoring.metrics import ec_rating_from_tiers, proxy_academic_rating, sat_equivalent
from app.scoring.probability import K_PILLAR, K_TEST, REF, logit, test_position
from app.scoring.rubric import build_school_rubric

from .common import fetch_all, log, supabase

NAMES = ["const(discard)", "K_PILLAR·academic", "K_PILLAR·extracurricular", "K_TEST", "legacy", "first_gen"]
BOUNDS = {"K_PILLAR": (1.0, 4.0), "K_TEST": (0.2, 1.2)}      # plan §3.9.3; hook effects only need to be positive


def design_row(t: dict, r, sat: int | None) -> list[float]:
    """One (twin, school) feature row. Twins have no essay, so `personal` stays at its prior."""
    tiers = [n for k, n in (("tier1", 1), ("tier2", 2), ("tier3", 3), ("tier4", 4))
             for _ in range(int((t["ec_tier_summary"] or {}).get(k) or 0))]
    acad = proxy_academic_rating(float(t["gpa_uw"]), sat, t["ap_count"] or 0)
    hooks = t["hooks"] or []
    return [
        r.pillar_weights["academic"] * (REF["academic"] - acad),
        r.pillar_weights["extracurricular"] * (REF["extracurricular"] - ec_rating_from_tiers(tiers)),
        r.test_weight * test_position(sat, r.sat_25, r.sat_75),
        float(r.hook_effects["legacy"] > 0 and "legacy" in hooks),
        float(r.hook_effects["first_gen"] > 0 and "first_gen" in hooks),
    ]


def sanity(params: dict[str, float | None]) -> list[str]:
    """Reasons the fitted values must not be adopted; empty means they pass."""
    bad = [f"{n} has no variation in the training rows, so it cannot be fitted" for n in NAMES[1:]
           if params.get(n) is None]
    params = {k: v for k, v in params.items() if v is not None}
    for name, (lo, hi) in (("K_PILLAR·academic", BOUNDS["K_PILLAR"]), ("K_PILLAR·extracurricular", BOUNDS["K_PILLAR"]),
                           ("K_TEST", BOUNDS["K_TEST"])):
        if name in params and not lo <= params[name] <= hi:
            bad.append(f"{name} = {params[name]:.3f} is outside [{lo}, {hi}]")
    bad += [f"{n} = {params[n]:.3f} is not positive" for n in ("legacy", "first_gen") if n in params and params[n] <= 0]
    return bad


async def fit() -> dict:
    sb = await supabase()
    schools = {s["slug"]: s for s in await fetch_all(sb, "universities_cds")}
    twins = await fetch_all(sb, "applicant_twins",
                            "gpa_uw,sat_score,act_score,ap_count,major_category,hooks,ec_tier_summary,"
                            "accepted_schools,rejected_schools,applicant_type")
    rows, y, offset = [], [], []
    for t in twins:
        if t["applicant_type"] != "first_year" or t["gpa_uw"] is None:
            continue
        sat = sat_equivalent(t["sat_score"], t["act_score"])
        for outcome, slugs in (("accepted", t["accepted_schools"]), ("rejected", t["rejected_schools"])):
            for slug in slugs:
                s = schools.get(slug)
                if not s or not s.get("admit_rate") or not s.get("c7_weights"):
                    continue
                r = build_school_rubric(s, t["major_category"], None)
                offset.append(logit(r.base_admit_rate) + math.log(r.major_multiplier))
                rows.append(design_row(t, r, sat))
                y.append(1.0 if outcome == "accepted" else 0.0)
    feats = np.asarray(rows, dtype=float)
    # an all-zero column makes the fit singular
    used = [i for i in range(feats.shape[1]) if np.any(feats[:, i] != 0)]
    X = sm.add_constant(feats[:, used])
    res = sm.GLM(np.asarray(y), X, family=sm.families.Binomial(), offset=np.asarray(offset)).fit()
    log.info("n=%d (waitlists excluded)\n%s", len(y), res.summary())
    names = [NAMES[0]] + [NAMES[1 + i] for i in used]
    fitted: dict[str, float | None] = dict.fromkeys(NAMES)
    for n, v, se in zip(names, res.params, res.bse, strict=True):
        fitted[n] = float(v)
        log.info("%-26s %7.3f ± %.3f", n, v, se)
    log.info("priors: K_PILLAR=%.2f K_TEST=%.2f", K_PILLAR, K_TEST)
    problems = sanity(fitted)
    log.info("ADOPT: %s", "yes" if not problems else "NO — " + "; ".join(problems))
    return {"n": len(y), "params": fitted, "problems": problems}


if __name__ == "__main__":
    asyncio.run(fit())
