from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict
from scipy.stats import beta as beta_dist

from app.schemas.common import PILLARS
from app.schemas.delta import ProbabilityBreakdown, ProbabilityComponent

REF = {"academic": 3.0, "extracurricular": 3.5, "personal": 3.5, "athletic": 4.0}   # typical applicant-pool rating
K_PILLAR = 2.0
K_TEST = 0.5
HOOK_CAP = 3.5
KAPPA = 12.0            # prior strength of the rubric model, in pseudo-applicants
N_EFF_CAP = 20.0        # twins can never outvote the model by more than this many pseudo-applicants
P_FLOOR, P_CEIL = 0.005, 0.97
INTEREST_EFFECT = 0.15


class ScoringInputs(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_admit_rate: float
    major_multiplier: float
    pillar_weights: dict[str, float]
    ratings: dict[str, float]                 # pillar → numeric Harvard rating (with ±0.33 modifiers)
    test_weight: float
    test_policy: str
    sat: int | None
    sat_25: int | None
    sat_75: int | None
    hooks: tuple[str, ...]
    hook_effects: dict[str, float]
    residency_effect: float
    early_round: str | None
    ed_admit_rate: float | None
    rd_admit_rate: float | None
    ea_admit_rate: float | None
    applicant_interest_weight: float
    demonstrated_interest: bool = False
    twin_sum_w: float = 0.0
    twin_sum_w2: float = 0.0
    twin_sum_w_admit: float = 0.0
    odds_inflation: float = 1.0

    def with_overrides(self, **kw) -> ScoringInputs:
        return self.model_copy(update=kw)


def _clamp(v: float, lo: float, hi: float) -> float:
    return min(max(v, lo), hi)


def logit(p: float) -> float:
    p = _clamp(p, 1e-4, 1 - 1e-4)
    return math.log(p / (1 - p))


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def odds(p: float) -> float:
    return p / (1 - p)


def from_odds(o: float) -> float:
    return o / (1 + o)


def test_position(sat: int | None, sat25: int | None, sat75: int | None) -> float:
    """z-score inside the school's middle 50% (IQR/1.349 ≈ σ), clipped to [−2.5, 1.5]."""
    if sat is None or sat25 is None or sat75 is None or sat75 <= sat25:
        return 0.0
    mid, sigma = (sat25 + sat75) / 2, (sat75 - sat25) / 1.349
    return _clamp((sat - mid) / sigma, -2.5, 1.5)


def early_effect(x: ScoringInputs) -> float:
    if x.early_round in ("ED", "ED2") and x.ed_admit_rate and x.rd_admit_rate:
        # ED pools are stronger than RD pools; credit only half the raw gap, cap at +1.0 logit.
        return min(1.0, 0.5 * (logit(x.ed_admit_rate) - logit(x.rd_admit_rate)))
    if x.early_round in ("EA", "REA") and x.ea_admit_rate and x.rd_admit_rate:
        return min(0.4, 0.3 * (logit(x.ea_admit_rate) - logit(x.rd_admit_rate)))
    return 0.0


def twin_posterior(p_model: float, sum_w: float, sum_w2: float, sum_w_admit: float,
                   odds_inflation: float) -> tuple[float, float, float, str]:
    a0, b0 = KAPPA * p_model, KAPPA * (1 - p_model)
    if sum_w <= 0 or sum_w2 <= 0:
        return p_model, beta_dist.ppf(0.1, a0, b0), beta_dist.ppf(0.9, a0, b0), "No comparable twins; model only."
    n_eff = min(N_EFF_CAP, sum_w**2 / sum_w2)
    r_raw = _clamp(sum_w_admit / sum_w, 0.01, 0.99)
    r = from_odds(odds(r_raw) / max(1.0, odds_inflation))
    a, b = a0 + n_eff * r, b0 + n_eff * (1 - r)
    detail = (f"{n_eff:.1f} effective twins; raw Reddit admit rate {r_raw:.0%} deflated ×{odds_inflation:.1f} "
              f"odds → {r:.0%}")
    return a / (a + b), beta_dist.ppf(0.1, a, b), beta_dist.ppf(0.9, a, b), detail


def disposition(p: float) -> str:
    if p >= 0.70:
        return "ADMIT"
    if p >= 0.45:
        return "LIKELY ADMIT"
    if p >= 0.20:
        return "WAITLIST"
    if p >= 0.08:
        return "LIKELY DENY"
    return "DENY"


def compute_probability(x: ScoringInputs) -> ProbabilityBreakdown:
    base = _clamp(x.base_admit_rate, P_FLOOR, 0.95)
    L = logit(base)
    comps: list[ProbabilityComponent] = []

    def step(key: str, label: str, dl: float, detail: str) -> None:
        nonlocal L
        before = sigmoid(L)
        L += dl
        comps.append(ProbabilityComponent(key=key, label=label, delta_logit=round(dl, 4),
                                          delta_pp=round((sigmoid(L) - before) * 100, 2), detail=detail))

    comps.append(ProbabilityComponent(key="base", label="School admit rate", delta_logit=0.0,
                                      delta_pp=round(base * 100, 2), detail=f"Overall admit rate {base:.1%}"))
    step("major", "Major competitiveness", math.log(_clamp(x.major_multiplier, 0.25, 2.0)),
         f"multiplier ×{x.major_multiplier:.2f}")
    for p in PILLARS:
        w, r = x.pillar_weights.get(p, 0.0), x.ratings[p]
        step(p, f"{p.capitalize()} rating", K_PILLAR * w * (REF[p] - r),
             f"rating {r:.2f} vs pool {REF[p]:.1f}, school weight {w:.2f}")
    z = 0.0 if x.test_policy == "blind" else test_position(x.sat, x.sat_25, x.sat_75)
    step("test", "Test score position", K_TEST * x.test_weight * z,
         f"z={z:+.2f} in school's 25–75 band" if x.sat else "No score submitted")
    hooks_total = min(HOOK_CAP, sum(x.hook_effects.get(h, 0.0) for h in x.hooks))
    step("hooks", "Hooks (C7-gated)", hooks_total, ", ".join(x.hooks) or "none")
    step("residency", "Residency", x.residency_effect, "public-university residency effect")
    step("early", "Application round", early_effect(x), x.early_round or "RD")
    step("interest", "Demonstrated interest",
         INTEREST_EFFECT * x.applicant_interest_weight if x.demonstrated_interest else 0.0,
         "counts only where C7 considers applicant interest")

    p_model = _clamp(sigmoid(L), P_FLOOR, P_CEIL)
    p_final, lo, hi, detail = twin_posterior(p_model, x.twin_sum_w, x.twin_sum_w2, x.twin_sum_w_admit,
                                             x.odds_inflation)
    p_final = _clamp(p_final, P_FLOOR, P_CEIL)
    # Measured from the waterfall's last bar (unclamped), so the bars always sum to p_final.
    comps.append(ProbabilityComponent(key="twins", label="Applicant-twin evidence",
                                      delta_logit=round(logit(p_final) - L, 4),
                                      delta_pp=round((p_final - sigmoid(L)) * 100, 2), detail=detail))
    lo, hi = _clamp(float(lo), P_FLOOR, P_CEIL), _clamp(float(hi), P_FLOOR, P_CEIL)
    return ProbabilityBreakdown(
        p_final=round(p_final, 4), p_low=round(lo, 4), p_high=round(hi, 4),
        p_model=round(p_model, 4), base_admit_rate=base, components=comps, disposition=disposition(p_final),
    )
