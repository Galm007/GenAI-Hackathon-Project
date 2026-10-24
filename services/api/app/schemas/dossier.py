from typing import Literal

from pydantic import BaseModel, Field

from .common import ECTier, HarvardRating, MajorCategory, PlusMinus

SubjectArea = Literal["english", "math", "science", "social_studies", "world_language",
                      "computer_science", "arts", "other"]
CourseLevel = Literal["regular", "honors", "ap", "ib_sl", "ib_hl", "dual_enrollment", "post_ap"]
Letter = Literal["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F", "P"]
GradeLevel = Literal[9, 10, 11, 12]


# ---------- extraction (LLM call 1: faithful transcription) ----------
class Course(BaseModel):
    title: str
    subject_area: SubjectArea
    level: CourseLevel
    grade_level: GradeLevel | None
    term: str | None = Field(description="e.g. 'S1', 'Full year', 'Fall 2025'")
    grade_as_shown: str | None
    letter_grade: Letter | None = Field(description="Only when the mapping is unambiguous from the transcript legend.")
    in_progress: bool


class APExam(BaseModel):
    subject: str
    score: Literal[1, 2, 3, 4, 5]


class TestScores(BaseModel):
    sat_total: int | None
    sat_math: int | None
    sat_ebrw: int | None
    act_composite: int | None
    ap_exams: list[APExam]
    other: list[str]


class Activity(BaseModel):
    name: str
    role: str | None
    organization: str | None
    description: str
    category: Literal["academic_competition", "research", "arts", "athletics", "community_service",
                      "leadership_government", "work", "entrepreneurship", "stem_project",
                      "family_responsibility", "advocacy", "media_writing", "other"]
    grades: list[GradeLevel]
    hours_per_week: float | None
    weeks_per_year: int | None


class Award(BaseModel):
    name: str
    level: Literal["school", "regional", "state", "national", "international", "unknown"]
    grade: GradeLevel | None


class HighSchool(BaseModel):
    name: str | None
    state: str | None
    country: str | None
    school_type: Literal["public", "private", "charter", "magnet", "boarding", "religious",
                         "homeschool", "international", "unknown"]
    class_rank_text: str | None


class ReportedGPA(BaseModel):
    value: float
    scale: float
    weighted: bool | None


class ParsedDossier(BaseModel):
    high_school: HighSchool
    reported_gpas: list[ReportedGPA]
    courses: list[Course]
    test_scores: TestScores
    activities: list[Activity]
    awards: list[Award]
    essay_text: str | None
    additional_info: str | None
    pii_strings: list[str] = Field(description="Exact identifying strings (names, address, IDs, email, phone) "
                                               "found anywhere; used for redaction, then discarded.")
    extraction_warnings: list[str]


# ---------- deterministic metrics (no LLM) ----------
class ComputedMetrics(BaseModel):
    gpa_uw_4: float | None
    gpa_w_5: float | None
    core_course_count: int
    advanced_course_count: int
    rigor_index: float | None                  # advanced core / core, grades 10–12
    grade_trend: Literal["upward", "flat", "downward", "insufficient_data"]
    sat_equivalent: int | None                 # SAT, or ACT concorded
    proxy_academic_rating: float               # 2.0–6.0 statistical anchor
    tier_derived_ec_rating: float              # 1.0–5.5 statistical anchor (filled after grading)
    ec_score: float


# ---------- grading (LLM call 2: judgment) ----------
class ActivityGrade(BaseModel):
    activity_index: int
    rationale: str
    tier: ECTier
    spike_role: Literal["core", "supporting", "peripheral"]


class PillarRating(BaseModel):
    rationale: str
    evidence: list[str] = Field(description="Dossier paths, e.g. 'activities.2', 'awards.0', 'essay', "
                                            "'metrics.gpa_uw_4'")
    rating: HarvardRating
    modifier: PlusMinus

    @property
    def numeric(self) -> float:
        """Lower is stronger; '+' pulls toward 1, '-' toward 6."""
        return self.rating + {"+": -0.33, "": 0.0, "-": 0.33}[self.modifier]


class HarvardScorecard(BaseModel):
    academic: PillarRating
    extracurricular: PillarRating
    personal: PillarRating
    athletic: PillarRating


class Spike(BaseModel):
    label: str
    description: str
    strength: Literal["strong", "moderate", "emerging", "none"]


class EssayAssessment(BaseModel):
    themes: list[str]
    voice: Literal["distinctive", "competent", "generic"]
    strengths: list[str]
    weaknesses: list[str]
    red_flags: list[str]
    strongest_line: str | None = Field(description="Quoted verbatim from the essay.")


class DossierGrade(BaseModel):
    major_category: MajorCategory
    rigor_label: Literal["most_demanding", "very_demanding", "demanding", "average", "below_average"]
    activity_grades: list[ActivityGrade]
    spike: Spike
    essay: EssayAssessment | None
    harvard: HarvardScorecard
    reader_comments: str = Field(description="2–4 sentence reader summary comment.")
    grader_warnings: list[str]
