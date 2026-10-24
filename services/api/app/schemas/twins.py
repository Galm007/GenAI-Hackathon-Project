from typing import Literal

from pydantic import BaseModel

from .common import Outcome


class TwinCard(BaseModel):                         # from the RPC; race withheld
    index: int                                     # 1..5, citation handle [[twin:N]]
    id: str
    source_url: str
    cycle_year: int | None
    matched_school: str
    outcome: Outcome
    gpa_uw: float | None
    sat_score: int | None
    act_score: int | None
    ap_count: int | None
    intended_major: str | None
    major_category: str
    hooks: list[str]
    ec_tier_summary: dict
    top_activities: list[dict]                     # up to 4, strongest tiers first
    awards: list[dict]
    spike_summary: str | None
    headline: str | None
    semantic_similarity: float
    stat_proximity: float
    hybrid_score: float


class EmpiricalBaseline(BaseModel):
    n_neighbors: int
    n_accepted: int
    n_waitlisted: int
    n_rejected: int
    n_effective: float                             # (Σw)² / Σw²
    weighted_admit_rate: float | None              # raw Reddit rate in the neighborhood
    wilson_low: float | None
    wilson_high: float | None
    odds_inflation: float                          # Reddit self-selection factor for this school
    deflated_admit_rate: float | None              # after dividing odds by inflation
    widened_to_peers: bool
    peer_schools: list[str]
    sum_w: float                                   # raw similarity-weight sums → ScoringInputs
    sum_w2: float
    sum_w_admit: float


# ---------- LLM output ----------
class TwinComparison(BaseModel):
    twin_index: int
    key_similarity: str
    key_difference: str
    plausible_deciding_factor: str


class TwinAnalysis(BaseModel):
    comparisons: list[TwinComparison]
    pattern_summary: str
    pattern_strength: Literal["strong", "moderate", "weak"]
    applicant_gaps: list[str]
    applicant_edges: list[str]
