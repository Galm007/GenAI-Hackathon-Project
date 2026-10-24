from typing import Literal

from pydantic import BaseModel

from .common import C7Level


# ---------- deterministic rubric (no LLM) ----------
class SchoolRubric(BaseModel):
    slug: str
    name: str
    base_admit_rate: float
    ed_admit_rate: float | None
    rd_admit_rate: float | None
    pillar_weights: dict[str, float]              # academic/extracurricular/personal/athletic, sums to 1
    factor_levels: dict[str, C7Level]
    test_weight: float                            # 0–1 from C7 test_scores (0 if test-blind)
    test_policy: str
    sat_25: int | None
    sat_75: int | None
    hook_effects: dict[str, float]                # logit bumps permitted by C7 gating
    residency_effect: float                       # logit; publics with state_residency weight
    major_category: str
    major_multiplier: float
    major_multiplier_source: Literal["override", "reddit_smoothed", "default"]
    major_n: int
    major_college: str | None
    direct_admit: bool | None
    notes: list[str]


class WebSnippet(BaseModel):
    id: str                                       # "W1".."Wn"
    url: str
    title: str
    content: str
    published: str | None


# ---------- LLM output ----------
class FactCheck(BaseModel):
    field: Literal["test_policy", "early_plans", "major_admission_model", "admit_rate", "other"]
    db_value: str | None
    web_value: str | None
    verdict: Literal["confirmed", "updated", "conflict", "unverified"]
    source_ids: list[str]
    note: str


class Priority(BaseModel):
    claim: str
    source_ids: list[str]
    relevance_to_applicant: Literal["strong", "some", "none"]


class InstitutionalBrief(BaseModel):
    fact_checks: list[FactCheck]
    strategic_priorities: list[Priority]
    current_test_policy: Literal["required", "optional", "blind", "unknown"]
    major_admission_model: Literal["direct_admit_capped", "direct_admit_open",
                                   "admit_to_university_then_declare", "unknown"]
    major_notes: str
    fit_signals: list[str]
    misalignment_signals: list[str]
    analyst_summary: str
