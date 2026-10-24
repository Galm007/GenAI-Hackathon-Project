from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ECTier, Hook, MajorCategory


class ExtractedActivity(BaseModel):
    description: str = Field(description="The poster's own wording, at most 120 characters.")
    role: str | None = Field(description="Leadership title if stated, e.g. 'President', 'Founder', 'Captain'.")
    tier: ECTier


class ExtractedAward(BaseModel):
    name: str
    level: Literal["school", "regional", "state", "national", "international", "unknown"]


class Demographics(BaseModel):
    gender: str | None
    race_ethnicity_raw: str | None = Field(description="Verbatim self-report; used only for aggregate bias audits.")
    residency_state: str | None = Field(description="Two-letter US state code if stated.")
    country: str | None
    income_bracket: Literal["<30k", "30-60k", "60-80k", "80-150k", "150-250k", ">250k", "unknown"]
    school_type: Literal["public", "private", "charter", "magnet", "boarding", "religious",
                         "homeschool", "international", "unknown"]
    first_gen: bool | None


class SchoolDecision(BaseModel):
    school_as_written: str = Field(description="Exactly as the poster wrote it, e.g. 'UMich', 'CMU SCS'.")
    outcome: Literal["accepted", "waitlisted", "rejected"]
    round: Literal["ED", "ED2", "EA", "REA", "RD", "rolling", "unknown"]


class RedditApplicantRecord(BaseModel):
    is_results_post: bool
    applicant_type: Literal["first_year", "transfer"]
    matriculation_year: int | None = Field(description="'Class of 2029' → 2025. Null if not stated.")

    gpa_uw: float | None = Field(description="Unweighted GPA on a 4.0 scale only.")
    gpa_w: float | None
    gpa_w_scale: float | None
    college_gpa: float | None = Field(description="Transfer applicants' college GPA.")
    class_rank_pct: float | None = Field(description="0.05 = top 5%. Only if computable from what is stated.")

    sat_total: int | None
    sat_math: int | None
    sat_ebrw: int | None
    act_composite: int | None
    applied_test_optional: bool | None
    ap_count: int | None
    honors_count: int | None
    dual_enrollment_count: int | None
    ib_diploma: bool | None
    rigor_label: Literal["most_demanding", "very_demanding", "demanding", "average", "below_average", "unknown"]

    intended_major_raw: str | None
    major_category: MajorCategory

    demographics: Demographics
    hooks: list[Hook]
    activities: list[ExtractedActivity] = Field(max_length=8)    # the 8 strongest; fewer output tokens
    awards: list[ExtractedAward] = Field(max_length=4)
    spike_summary: str | None = Field(description="At most 8 words naming the applicant's most distinctive theme.")

    decisions: list[SchoolDecision]
    extraction_confidence: Literal["high", "medium", "low"]
    extraction_issues: list[str] = Field(max_length=2)   # short phrases
