import pytest

from app.schemas import dossier as S
from app.schemas.inputs import RawApplicantInputs
from app.scoring import metrics as M


def course(letter="A", level="regular", subject="math", grade_level=11, in_progress=False) -> S.Course:
    return S.Course(title="x", subject_area=subject, level=level, grade_level=grade_level, term=None,
                  grade_as_shown=letter, letter_grade=letter, in_progress=in_progress)


def activity(i: int = 0) -> S.Activity:
    return S.Activity(name=f"a{i}", role=None, organization=None, description="d", category="other", grades=[11],
                    hours_per_week=None, weeks_per_year=None)


def dossier(courses=(), activities=1, awards=(), sat=None, act=None, gpas=()) -> S.ParsedDossier:
    return S.ParsedDossier(
        high_school=S.HighSchool(name=None, state=None, country=None, school_type="public", class_rank_text=None),
        reported_gpas=list(gpas), courses=list(courses),
        test_scores=S.TestScores(sat_total=sat, sat_math=None, sat_ebrw=None, act_composite=act, ap_exams=[], other=[]),
        activities=[activity(i) for i in range(activities)], awards=list(awards), essay_text=None,
        additional_info=None, pii_strings=[], extraction_warnings=[])


def pr(rating: int, modifier: str = "+") -> S.PillarRating:
    return S.PillarRating(rationale="r", evidence=[], rating=rating, modifier=modifier)


def grade(academic=3, ec=3, personal=3, athletic=4, activity_grades=None) -> S.DossierGrade:
    return S.DossierGrade(
        major_category="computer_science", rigor_label="demanding",
        activity_grades=activity_grades if activity_grades is not None else
        [S.ActivityGrade(activity_index=0, rationale="r", tier=3, spike_role="core")],
        spike=S.Spike(label="s", description="d", strength="moderate"), essay=None,
        harvard=S.HarvardScorecard(academic=pr(academic), extracurricular=pr(ec), personal=pr(personal),
                                 athletic=pr(athletic)),
        reader_comments="c", grader_warnings=[])


def inputs(**kw) -> RawApplicantInputs:
    return RawApplicantInputs(intended_major="CS", target_schools=["uiuc"], **kw)


def guarded(d: S.ParsedDossier, g: S.DossierGrade, i: RawApplicantInputs | None = None):
    return M.enforce_grade_invariants(d, g, M.compute_metrics(d), i or inputs())


# ---------- GPA normalization ----------
def test_gpa_needs_six_graded_core_courses():
    assert M.normalize_gpa([course()] * 5) == (None, None)
    # non-core, in-progress and pass/fail courses don't count toward the six
    noise = [course(subject="arts"), course(in_progress=True), course(letter="P")]
    assert M.normalize_gpa([course()] * 5 + noise) == (None, None)


def test_gpa_unweighted_and_weighted():
    courses = [course("A", "ap")] * 2 + [course("B+", "honors")] * 2 + [course("A-")] * 2
    uw, w = M.normalize_gpa(courses)
    assert uw == round((4.0 * 2 + 3.3 * 2 + 3.7 * 2) / 6, 2)
    assert w == round((5.0 * 2 + 3.8 * 2 + 3.7 * 2) / 6, 2)


def test_weighted_bonus_capped_at_5_and_withheld_below_c():
    uw, w = M.normalize_gpa([course("A+", "ap")] * 3 + [course("D", "ap")] * 3)
    assert w == round((5.0 * 3 + 1.0 * 3) / 6, 2)           # A+ AP caps at 5.0; a D in AP earns no bonus


def test_compute_metrics_falls_back_to_reported_unweighted_gpa():
    d = dossier(courses=[course()] * 3, gpas=[S.ReportedGPA(value=4.6, scale=5.0, weighted=True),
                                              S.ReportedGPA(value=3.81, scale=4.0, weighted=False)])
    m = M.compute_metrics(d)
    assert m.gpa_uw_4 == 3.81 and m.gpa_w_5 is None


def test_rigor_trend_and_act_concordance():
    courses = ([course(level="ap", grade_level=11)] * 4 + [course(grade_level=9)] * 2
               + [course(subject="arts", level="ap", grade_level=12)])
    core, advanced, idx = M.rigor(courses)
    assert (core, advanced, idx) == (6, 5, 1.0)              # arts AP counts as advanced, not core
    early, late = [course("B", grade_level=9)] * 4, [course("A", grade_level=11)] * 4
    assert M.grade_trend(early + late) == "upward"
    assert M.grade_trend(late[:3] + early) == "insufficient_data"
    assert M.sat_equivalent(None, 34) == 1500 and M.sat_equivalent(1480, 34) == 1480
    assert M.sat_equivalent(None, 15) is None


def test_proxy_academic_rating_bounds():
    assert M.proxy_academic_rating(4.0, 1580, 12) == 2.0     # best possible anchor is 2, never 1
    assert M.proxy_academic_rating(2.5, 1000, 0) == 6.0
    assert M.proxy_academic_rating(None, None, 3) == pytest.approx(4.2)


# ---------- tier → EC anchor ----------
@pytest.mark.parametrize(("tiers", "expected"), [
    ([], 5.2),
    ([4], 5.2 - 0.55 * 0.2),
    ([2], 5.2 - 0.55 * 2.0),                                 # one Tier 2 ≈ −1.1 rating points
    ([2, 2, 2, 3], 1.6),                                     # floor 1.6 without a Tier 1
    ([1, 2], 1.9),
    ([1, 1, 2], 1.0),                                        # a Tier 1 unlocks the 1.0 floor
])
def test_ec_rating_from_tiers(tiers, expected):
    assert M.ec_rating_from_tiers(tiers) == pytest.approx(expected)


# ---------- grade guardrails (§3.10) ----------
def test_plan_fixture_academic_1_with_36_gpa_and_1350_sat_clamps_to_4():
    d = dossier(courses=[course("A", "ap")] * 3 + [course("B+", "ap")] * 3, sat=1350)
    assert M.compute_metrics(d).gpa_uw_4 == 3.65                          # GPA band 0, SAT band −1, 6 APs +1
    g, m, warnings = guarded(d, grade(academic=1))
    assert m.proxy_academic_rating == 5.0
    assert g.harvard.academic.rating == 4 and g.harvard.academic.modifier == ""
    assert any(w.startswith("academic rating 1 clamped to 4") for w in warnings)


def test_ungraded_activities_default_to_tier_4_and_bad_indices_are_dropped():
    ag = [S.ActivityGrade(activity_index=1, rationale="r", tier=2, spike_role="core"),
          S.ActivityGrade(activity_index=9, rationale="r", tier=1, spike_role="core")]
    g, m, warnings = guarded(dossier(activities=3), grade(ec=4, activity_grades=ag))
    assert [(a.activity_index, a.tier) for a in g.activity_grades] == [(0, 4), (1, 2), (2, 4)]
    assert m.ec_score == pytest.approx(2.4) and m.tier_derived_ec_rating == pytest.approx(5.2 - 0.55 * 2.4)
    assert sum("ungraded" in w for w in warnings) == 2


def test_academic_1_requires_national_distinction():
    strong = [course("A", "ap")] * 12
    g, _, warnings = guarded(dossier(courses=strong, sat=1580), grade(academic=1))
    assert g.harvard.academic.rating == 2
    assert any("no national distinction" in w for w in warnings)
    award = S.Award(name="USAMO qualifier", level="national", grade=11)
    g, _, warnings = guarded(dossier(courses=strong, sat=1580, awards=[award]), grade(academic=1))
    assert g.harvard.academic.rating == 1 and not any("academic" in w for w in warnings)


def test_extracurricular_within_one_of_tier_anchor():
    g, m, warnings = guarded(dossier(), grade(ec=1))         # one Tier 3 → anchor 4.79 → allowed 4–5
    assert m.tier_derived_ec_rating == pytest.approx(4.7875)
    assert g.harvard.extracurricular.rating == 4 and any("extracurricular" in w for w in warnings)


def test_personal_best_is_2_without_recommendations():
    g, _, warnings = guarded(dossier(), grade(personal=1))
    assert g.harvard.personal.rating == 2 and any("essay only" in w for w in warnings)
    g, _, _ = guarded(dossier(), grade(personal=1), inputs(recommendation_text="Glowing letter."))
    assert g.harvard.personal.rating == 1


def test_athletic_1_needs_recruited_hook_and_5_6_are_unused():
    assert guarded(dossier(), grade(athletic=1))[0].harvard.athletic.rating == 2
    assert guarded(dossier(), grade(athletic=1), inputs(hooks=["recruited_athlete"]))[0].harvard.athletic.rating == 1
    assert guarded(dossier(), grade(athletic=6))[0].harvard.athletic.rating == 4


def test_in_range_ratings_pass_through_untouched():
    d = dossier(courses=[course("A", "ap")] * 8, sat=1500)
    g, m, warnings = guarded(d, grade(academic=3, ec=4, personal=3, athletic=4))
    assert warnings == [] and g.harvard.academic.modifier == "+"
    assert isinstance(m, S.ComputedMetrics) and m.ec_score == pytest.approx(0.75)
