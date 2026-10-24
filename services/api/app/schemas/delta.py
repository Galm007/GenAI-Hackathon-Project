from typing import Literal

from pydantic import BaseModel


# ---------- deterministic ----------
class ProbabilityComponent(BaseModel):
    key: str                                       # "base", "major", "academic", "test", "twins", ...
    label: str
    delta_logit: float
    delta_pp: float                                # percentage-point change at this step of the waterfall
    detail: str


class ProbabilityBreakdown(BaseModel):
    p_final: float
    p_low: float                                   # 10th percentile of posterior
    p_high: float                                  # 90th percentile
    p_model: float                                 # before the twin update
    base_admit_rate: float
    components: list[ProbabilityComponent]
    disposition: Literal["ADMIT", "LIKELY ADMIT", "WAITLIST", "LIKELY DENY", "DENY"]


class Counterfactual(BaseModel):
    id: str                                        # "cf_major_math_stats", "cf_sat_75", ...
    kind: Literal["major_switch", "test_score", "add_activity", "early_round",
                  "demonstrated_interest", "essay"]
    label: str
    p_new: float
    delta_pp: float
    confidence: Literal["data_backed", "model_estimate"]
    evidence: str
    overrides: dict                                # exact ScoringInputs overrides → reproducible in /api/what-if


# ---------- LLM output ----------
class Pivot(BaseModel):
    counterfactual_id: str | None = None           # None only for unquantified pivots
    title: str
    why_it_works: str
    concrete_steps: list[str]
    effort: Literal["hours", "days", "weeks", "months"]
    tradeoffs: str


class EssayEdit(BaseModel):
    issue: str
    current_excerpt: str                           # ≤ 25 words, verbatim
    direction: str
    example_rewrite: str


class DeltaReport(BaseModel):
    headline_verdict: str
    committee_disposition: Literal["ADMIT", "LIKELY ADMIT", "WAITLIST", "LIKELY DENY", "DENY"]
    ranked_pivots: list[Pivot]
    major_arbitrage_note: str | None
    essay_adjustments: list[EssayEdit]
    risks_to_watch: list[str]
    disclaimer: str
