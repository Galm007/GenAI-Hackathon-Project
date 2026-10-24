from __future__ import annotations

import math
from statistics import mean

from app.schemas.dossier import ActivityGrade, ComputedMetrics, Course, DossierGrade, ParsedDossier, PillarRating
from app.schemas.inputs import RawApplicantInputs

LETTER_POINTS = {"A+": 4.0, "A": 4.0, "A-": 3.7, "B+": 3.3, "B": 3.0, "B-": 2.7, "C+": 2.3, "C": 2.0,
                 "C-": 1.7, "D+": 1.3, "D": 1.0, "D-": 0.7, "F": 0.0}
LEVEL_BONUS = {"regular": 0.0, "honors": 0.5, "ib_sl": 0.5, "ap": 1.0, "ib_hl": 1.0,
               "dual_enrollment": 1.0, "post_ap": 1.0}
ADVANCED = {"ap", "ib_sl", "ib_hl", "dual_enrollment", "post_ap"}
CORE = {"english", "math", "science", "social_studies", "world_language", "computer_science"}
ACT_TO_SAT = {36: 1590, 35: 1540, 34: 1500, 33: 1460, 32: 1430, 31: 1400, 30: 1370, 29: 1340,
              28: 1310, 27: 1280, 26: 1240, 25: 1210, 24: 1180, 23: 1140, 22: 1110}
TIER_POINTS = {1: 4.0, 2: 2.0, 3: 0.75, 4: 0.2}


def _graded(courses: list[Course]) -> list[Course]:
    return [c for c in courses
            if c.subject_area in CORE and c.letter_grade in LETTER_POINTS and not c.in_progress]


def normalize_gpa(courses: list[Course]) -> tuple[float | None, float | None]:
    graded = _graded(courses)
    if len(graded) < 6:
        return None, None
    uw = [LETTER_POINTS[c.letter_grade] for c in graded]
    w = [min(5.0, p + (LEVEL_BONUS[c.level] if p >= 2.0 else 0.0)) for c, p in zip(graded, uw, strict=True)]
    return round(mean(uw), 2), round(mean(w), 2)


def rigor(courses: list[Course]) -> tuple[int, int, float | None]:
    core = [c for c in courses if c.subject_area in CORE]
    upper = [c for c in core if (c.grade_level or 12) >= 10]
    advanced = sum(1 for c in courses if c.level in ADVANCED)
    adv_upper = sum(1 for c in upper if c.level in ADVANCED)
    return len(core), advanced, (round(adv_upper / len(upper), 3) if upper else None)


def grade_trend(courses: list[Course]) -> str:
    early, late = [], []
    for c in _graded(courses):
        if c.grade_level in (9, 10):
            early.append(LETTER_POINTS[c.letter_grade])
        elif c.grade_level in (11, 12):
            late.append(LETTER_POINTS[c.letter_grade])
    if len(early) < 4 or len(late) < 4:
        return "insufficient_data"
    d = mean(late) - mean(early)
    return "upward" if d >= 0.15 else "downward" if d <= -0.15 else "flat"


def sat_equivalent(sat: int | None, act: int | None) -> int | None:
    return sat or (ACT_TO_SAT.get(act) if act else None)


def proxy_academic_rating(gpa_uw: float | None, sat_eq: int | None, advanced: int) -> float:
    """Statistical anchor on the 1–6 scale (2.0 best; a 1 needs evidence of scholarly distinction)."""
    def band(v, cuts):          # cuts: [(threshold, points), ...] descending
        return next((pts for thr, pts in cuts if v >= thr), -1)
    pts = 1 if gpa_uw is None else band(gpa_uw, [(3.95, 3), (3.85, 2), (3.70, 1), (3.50, 0)])
    pts += 1 if sat_eq is None else band(sat_eq, [(1550, 3), (1500, 2), (1450, 1), (1380, 0)])
    pts += band(advanced, [(10, 2), (6, 1), (3, 0)])
    return max(2.0, min(6.0, 5.0 - 0.4 * pts))


def ec_score(tiers: list[int]) -> float:
    return sum(TIER_POINTS[t] for t in tiers)


def ec_rating_from_tiers(tiers: list[int]) -> float:
    """Continuous EC anchor: one Tier 2 ≈ −1.1 rating points; below 1.6 requires a Tier 1."""
    floor = 1.0 if 1 in tiers else 1.6
    return max(floor, min(5.5, 5.2 - 0.55 * ec_score(tiers)))


def compute_metrics(d: ParsedDossier) -> ComputedMetrics:
    uw, w = normalize_gpa(d.courses)
    if uw is None:   # fall back to a printed 4.0-scale unweighted GPA
        uw = next((g.value for g in d.reported_gpas if g.scale == 4.0 and g.weighted is False), None)
    core, advanced, rigor_index = rigor(d.courses)
    sat_eq = sat_equivalent(d.test_scores.sat_total, d.test_scores.act_composite)
    return ComputedMetrics(
        gpa_uw_4=uw, gpa_w_5=w, core_course_count=core, advanced_course_count=advanced,
        rigor_index=rigor_index, grade_trend=grade_trend(d.courses), sat_equivalent=sat_eq,
        proxy_academic_rating=proxy_academic_rating(uw, sat_eq, advanced),
        tier_derived_ec_rating=5.2, ec_score=0.0,      # filled after grading
    )


def _clamp(p: PillarRating, lo: float, hi: float, name: str, warnings: list[str]) -> PillarRating:
    lo_i, hi_i = max(1, math.ceil(lo)), min(6, math.floor(hi))
    if lo_i <= p.rating <= hi_i:
        return p
    new = min(max(p.rating, lo_i), hi_i)
    warnings.append(f"{name} rating {p.rating} clamped to {new} (allowed {lo_i}–{hi_i})")
    return p.model_copy(update={"rating": new, "modifier": ""})


def enforce_grade_invariants(
    d: ParsedDossier, g: DossierGrade, m: ComputedMetrics, inputs: RawApplicantInputs
) -> tuple[DossierGrade, ComputedMetrics, list[str]]:
    warnings = list(g.grader_warnings)

    # 1) every activity graded exactly once
    by_idx = {ag.activity_index: ag for ag in g.activity_grades if 0 <= ag.activity_index < len(d.activities)}
    for i in range(len(d.activities)):
        if i not in by_idx:
            warnings.append(f"activity {i} ungraded → defaulted to Tier 4")
            by_idx[i] = ActivityGrade(activity_index=i, rationale="Not graded; defaulted.",
                                      tier=4, spike_role="peripheral")
    grades = [by_idx[i] for i in sorted(by_idx)]
    tiers = [ag.tier for ag in grades]

    m = m.model_copy(update={"ec_score": ec_score(tiers), "tier_derived_ec_rating": ec_rating_from_tiers(tiers)})
    h = g.harvard

    # 2) academic within ±1 of anchor; a 1 requires national/international academic distinction
    academic = _clamp(h.academic, m.proxy_academic_rating - 1, m.proxy_academic_rating + 1, "academic", warnings)
    distinguished = any(a.level in ("national", "international") for a in d.awards)
    if academic.rating == 1 and not distinguished:
        academic = _clamp(academic, 2, 6, "academic (no national distinction)", warnings)

    # 3) EC within ±1 of tier-derived anchor
    ec = _clamp(h.extracurricular, m.tier_derived_ec_rating - 1, m.tier_derived_ec_rating + 1,
                "extracurricular", warnings)

    # 4) personal best = 2 without recommendations
    personal = h.personal if inputs.recommendation_text else _clamp(h.personal, 2, 6, "personal (essay only)", warnings)

    # 5) athletic: 1 needs the recruited hook; 5–6 unused
    athletic = _clamp(h.athletic, 1 if "recruited_athlete" in inputs.hooks else 2, 4, "athletic", warnings)

    g = g.model_copy(update={
        "activity_grades": grades,
        "harvard": h.model_copy(update={"academic": academic, "extracurricular": ec,
                                        "personal": personal, "athletic": athletic}),
        "grader_warnings": warnings,
    })
    return g, m, warnings
