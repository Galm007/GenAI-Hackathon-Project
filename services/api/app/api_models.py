from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from .schemas.common import EarlyRound, Hook, MajorCategory
from .schemas.delta import ProbabilityBreakdown
from .schemas.inputs import RawApplicantInputs, SelfReportedContext


class IntakeForm(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)          # random id from localStorage; no accounts
    intended_major: str = Field(min_length=2, max_length=120)
    target_schools: list[str] = Field(min_length=1, max_length=8)
    early_round: dict[str, EarlyRound] = Field(default_factory=dict)
    resume_text: str | None = Field(None, max_length=20_000)
    activities_text: str | None = Field(None, max_length=20_000)
    essay_text: str | None = Field(None, max_length=15_000)
    recommendation_text: str | None = Field(None, max_length=15_000)
    hooks: list[Hook] = Field(default_factory=list)
    context: SelfReportedContext = Field(default_factory=SelfReportedContext)
    application_deadline: date | None = None
    consent: Literal[True]                                          # "These are my own materials; delete in 24h"

    def to_inputs(self, *, transcript_pdf_b64: str | None, resume_pdf_b64: str | None) -> RawApplicantInputs:
        data = self.model_dump(exclude={"session_id", "consent", "application_deadline"})
        return RawApplicantInputs(
            **data, transcript_pdf_b64=transcript_pdf_b64, resume_pdf_b64=resume_pdf_b64,
            application_deadline=self.application_deadline.isoformat() if self.application_deadline else None,
        )


class WhatIfRequest(BaseModel):
    run_id: str
    sat: int | None = Field(None, ge=400, le=1600)
    withhold_sat: bool = False
    major_category: MajorCategory | None = None
    add_activities: list[Literal[1, 2, 3]] = Field(default_factory=list, max_length=3)   # hypothetical new ECs by tier
    early_round: EarlyRound | None = None
    demonstrated_interest: bool | None = None
    essay_steps: Literal[0, 1, 2] = 0                                # Personal rating improves by N steps


class WhatIfResponse(BaseModel):
    baseline: ProbabilityBreakdown
    simulated: ProbabilityBreakdown
    delta_pp: float
    applied: list[str]
    warnings: list[str]
    confidence: Literal["data_backed", "model_estimate"]
