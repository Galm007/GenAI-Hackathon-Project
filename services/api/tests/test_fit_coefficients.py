from __future__ import annotations

from app.scoring.rubric import build_school_rubric
from etl import fit_coefficients as fc

OK = {"const(discard)": 1.0, "K_PILLAR·academic": 2.2, "K_PILLAR·extracurricular": 1.8, "K_TEST": 0.6,
      "legacy": 0.8, "first_gen": 0.2}


def test_sanity_accepts_values_inside_the_plan_bounds():
    assert fc.sanity(OK) == []


def test_sanity_rejects_out_of_range_negative_and_unfitted_values():
    bad = fc.sanity(OK | {"K_TEST": -0.4, "K_PILLAR·extracurricular": -0.6, "legacy": None})
    assert len(bad) == 3
    assert any("K_TEST" in b for b in bad) and any("legacy" in b and "cannot be fitted" in b for b in bad)


def test_design_row_signs_and_gates():
    school = {"slug": "x", "name": "X", "admit_rate": 0.2, "test_policy": "required", "c7_weights": {
        "academic_gpa": "very_important", "test_scores": "very_important", "alumni_relation": "very_important"},
        "sat_composite_25": 1400, "sat_composite_75": 1550}
    r = build_school_rubric(school, "cs", None)
    twin = {"gpa_uw": 3.98, "ap_count": 10, "hooks": ["legacy"], "ec_tier_summary": {"tier2": 2}}
    acad, ec, test, legacy, first_gen = fc.design_row(twin, r, 1570)
    assert acad > 0 and ec > 0 and test > 0           # stronger than the pool → positive logit pushes
    assert legacy == 1.0 and first_gen == 0.0
