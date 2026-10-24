import pytest

from app.schemas.common import C7_FACTORS
from app.schemas.institution import FactCheck, InstitutionalBrief
from app.scoring.rubric import HOOK_RULES, apply_brief_adjustments, build_school_rubric

BASE = {"slug": "uiuc", "name": "UIUC", "admit_rate": 0.44, "control": "public", "state": "IL",
        "test_policy": "optional", "sat_composite_25": 1350, "sat_composite_75": 1530}


def school(**kw) -> dict:
    return BASE | kw


# ---------- C7 → pillar weights ----------
def test_c7_levels_map_to_pillar_weights():
    c7 = {f: "very_important" for f in ("rigor", "class_rank", "academic_gpa", "test_scores")}
    c7 |= {f: "considered" for f in ("extracurriculars", "talent_ability", "volunteer_work", "work_experience")}
    c7 |= {"essay": "important", "recommendations": "important", "character": "considered",
           "interview": "not_considered"}
    r = build_school_rubric(school(c7_weights=c7), "computer_science", None)
    # raw: academic 1.0, EC 0.33, personal mean(.66,.66,.33,0)=.4125, athletic .5×.33=.165; total 1.9075
    assert r.pillar_weights == pytest.approx({"academic": 0.5242, "extracurricular": 0.173,
                                              "personal": 0.2163, "athletic": 0.0865}, abs=1e-4)
    assert sum(r.pillar_weights.values()) == pytest.approx(1.0, abs=1e-3)
    assert r.factor_levels["essay"] == "important" and r.test_weight == 1.0
    assert set(r.factor_levels) == set(C7_FACTORS)


def test_missing_c7_defaults_every_factor_to_considered():
    r = build_school_rubric(school(), "computer_science", None)
    assert set(r.factor_levels.values()) == {"considered"}
    assert r.pillar_weights == pytest.approx({"academic": 2 / 7, "extracurricular": 2 / 7,
                                              "personal": 2 / 7, "athletic": 1 / 7}, abs=1e-4)
    assert any("C7 weights unavailable" in n for n in r.notes)


def test_test_blind_zeroes_test_weight():
    c7 = {"test_scores": "very_important"}
    assert build_school_rubric(school(c7_weights=c7, test_policy="blind"), "x", None).test_weight == 0.0
    assert build_school_rubric(school(c7_weights=c7), "x", None).test_weight == 1.0


def test_hooks_are_gated_by_their_c7_factor():
    r = build_school_rubric(school(c7_weights={"alumni_relation": "not_considered", "talent_ability":
                                               "very_important"}), "x", None)
    assert r.hook_effects["legacy"] == 0.0 and r.hook_effects["faculty_staff_child"] == 0.0
    assert r.hook_effects["recruited_athlete"] == 3.0
    assert r.hook_effects["first_gen"] == round(0.5 * 0.33, 3)              # default "considered"
    assert r.hook_effects["questbridge_finalist"] == 0.4                    # ungated
    assert set(r.hook_effects) == set(HOOK_RULES)


def test_residency_effect_for_public_universities():
    split = school(in_state_admit_rate=0.55, out_state_admit_rate=0.30)
    assert build_school_rubric(split, "x", "il").residency_effect > 0           # case-insensitive state match
    assert build_school_rubric(split, "x", "CA").residency_effect < 0
    sr = school(c7_weights={"state_residency": "very_important"})
    assert build_school_rubric(sr, "x", "IL").residency_effect == 0.8
    assert build_school_rubric(sr, "x", "CA").residency_effect == -0.4
    assert build_school_rubric(school(control="private"), "x", "IL").residency_effect == 0.0
    assert build_school_rubric(sr, "x", None).residency_effect == 0.0


def test_major_multiplier_clamped_and_sourced():
    mc = {"computer_science": {"multiplier": 0.1, "source": "override", "n": 12, "college": "Grainger",
                               "direct_admit": True}, "math_stats": {"multiplier": 9.0, "source": "reddit_smoothed"}}
    r = build_school_rubric(school(major_competitiveness=mc), "computer_science", None)
    assert (r.major_multiplier, r.major_multiplier_source, r.major_n, r.direct_admit) == (0.25, "override", 12, True)
    assert build_school_rubric(school(major_competitiveness=mc), "math_stats", None).major_multiplier == 2.0
    d = build_school_rubric(school(major_competitiveness=mc), "biology", None)
    assert (d.major_multiplier, d.major_multiplier_source) == (1.0, "default")


def test_missing_admit_rate_defaults_to_10_percent():
    r = build_school_rubric(school(admit_rate=None), "x", None)
    assert r.base_admit_rate == 0.10 and any("Admit rate missing" in n for n in r.notes)


# ---------- brief adjustments ----------
def _brief(verdict="updated", policy="blind", model="direct_admit_capped") -> InstitutionalBrief:
    return InstitutionalBrief(
        fact_checks=[FactCheck(field="test_policy", db_value="optional", web_value=policy, verdict=verdict,
                               source_ids=["W2"], note="n")],
        strategic_priorities=[], current_test_policy=policy, major_admission_model=model, major_notes="",
        fit_signals=[], misalignment_signals=[], analyst_summary="s")


def test_brief_can_update_test_policy_and_direct_admit_only():
    r = build_school_rubric(school(c7_weights={"test_scores": "important"}), "x", None)
    out = apply_brief_adjustments(r, _brief())
    assert (out.test_policy, out.test_weight, out.direct_admit) == ("blind", 0.0, True)
    assert any("W2" in n for n in out.notes) and r.notes == []              # original untouched
    assert apply_brief_adjustments(r, _brief(verdict="confirmed")).test_policy == "optional"
    assert apply_brief_adjustments(r, None) is r
