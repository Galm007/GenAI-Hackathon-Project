from pydantic import BaseModel, Field

from .common import EarlyRound, Hook


class SelfReportedContext(BaseModel):
    residency_state: str | None = Field(None, description="2-letter code")
    country: str | None = "US"
    school_type: str | None = None              # public / private / charter / ...
    first_gen: bool | None = None
    low_income: bool | None = None


class RawApplicantInputs(BaseModel):
    transcript_pdf_b64: str | None = None
    resume_pdf_b64: str | None = None
    resume_text: str | None = None
    activities_text: str | None = None
    essay_text: str | None = None
    recommendation_text: str | None = None      # optional; unlocks Personal rating of 1
    intended_major: str
    target_schools: list[str]                   # slugs, resolved client-side via resolve_school
    early_round: dict[str, EarlyRound] = {}     # {"uiuc": "EA"}
    hooks: list[Hook] = []
    context: SelfReportedContext = SelfReportedContext()
    application_deadline: str | None = None     # ISO date → Node 5 feasibility
