from typing import Literal

HarvardRating = Literal[1, 2, 3, 4, 5, 6]          # 1 = strongest (SFFA v. Harvard reader scale)
PlusMinus = Literal["+", "", "-"]
ECTier = Literal[1, 2, 3, 4]                         # 1 = strongest (Harberson-style)
C7Level = Literal["very_important", "important", "considered", "not_considered"]
Outcome = Literal["accepted", "waitlisted", "rejected"]
EarlyRound = Literal["ED", "ED2", "EA", "REA", "RD"]
Hook = Literal["first_gen", "low_income", "legacy", "recruited_athlete", "faculty_staff_child",
               "rural", "veteran", "questbridge_finalist"]
MajorCategory = Literal[
    "computer_science", "computer_engineering", "electrical_engineering", "mechanical_aerospace",
    "other_engineering", "math_stats", "data_science", "physics_astro", "chemistry", "biology",
    "neuroscience", "pre_health", "economics", "business", "political_science", "psychology",
    "social_sciences_other", "humanities", "arts_design", "architecture", "undecided", "other",
]
Pillar = Literal["academic", "extracurricular", "personal", "athletic"]
PILLARS: tuple[Pillar, ...] = ("academic", "extracurricular", "personal", "athletic")

C7_FACTORS = (
    "rigor", "class_rank", "academic_gpa", "test_scores", "essay", "recommendations", "interview",
    "extracurriculars", "talent_ability", "character", "first_generation", "alumni_relation",
    "geographic_residence", "state_residency", "religious_affiliation", "volunteer_work",
    "work_experience", "applicant_interest",
)
