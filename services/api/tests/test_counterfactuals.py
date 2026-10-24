import importlib.util
import json
import sys
import types
from types import SimpleNamespace

import pytest

from app.api_models import WhatIfRequest
from app.schemas.delta import Counterfactual
from app.scoring.probability import ScoringInputs, compute_probability
from app.scoring.rubric import build_school_rubric
from app.scoring.whatif import run_what_if

from .test_probability import inputs
from .test_scoring_metrics import S, dossier, grade

if importlib.util.find_spec("app.db") is None:       # app/db.py arrives with B07; tests mock it either way
    sys.modules["app.db"] = types.ModuleType("app.db")
from app.scoring import counterfactuals as CF  # noqa: E402

SCHOOL = {"slug": "uiuc", "name": "UIUC", "admit_rate": 0.44, "test_policy": "optional",
          "early_plans": {"ea": True}, "c7_weights": {"applicant_interest": "considered"},
          "major_competitiveness": {"computer_science": {"multiplier": 0.38, "college": "Grainger"},
                                    "math_stats": {"multiplier": 1.12, "college": "LAS"}}}


def arbitrage_rows(*rows):
    async def major_arbitrage(embedding, slug, *, gpa, sat):
        assert slug == "uiuc" and len(embedding) == 768
        return list(rows)
    return major_arbitrage


def row(cat: str, n: int = 41, rate: float = 0.58, smoothed: float = 1.0) -> dict:
    return {"major_category": cat, "n_neighbors": n, "neighbor_admit_rate": rate,
            "school_smoothed_multiplier": smoothed}


@pytest.fixture
def mock_db(monkeypatch):
    def install(*rows):
        monkeypatch.setattr(CF, "db", SimpleNamespace(major_arbitrage=arbitrage_rows(*rows)))
    return install


def maya_grade():
    ag = [S.ActivityGrade(activity_index=0, rationale="r", tier=2, spike_role="core"),
          S.ActivityGrade(activity_index=1, rationale="r", tier=3, spike_role="supporting"),
          S.ActivityGrade(activity_index=2, rationale="r", tier=4, spike_role="peripheral")]
    return grade(activity_grades=ag)


async def generate(x: ScoringInputs, school=SCHOOL) -> list[Counterfactual]:
    rubric = build_school_rubric(school, "computer_science", None)
    return await CF.generate_counterfactuals(x, rubric=rubric, grade=maya_grade(), dossier=dossier(activities=3),
                                             school=school, embedding=[0.0] * 768, gpa=3.94)


def maya(**kw) -> ScoringInputs:
    ratings = {"academic": 2.33, "extracurricular": 2.67, "personal": 3.67, "athletic": 4.0}
    return inputs(**({"ratings": ratings, "sat": 1400, "ed_admit_rate": None} | kw))


# ---------- §3.10 counterfactual reproducibility ----------
async def test_overrides_reproduce_p_new_exactly(mock_db):
    mock_db(row("math_stats"), row("data_science", rate=0.4, smoothed=0.9), row("physics_astro", rate=0.5))
    cfs = await generate(maya())
    assert {c.kind for c in cfs} >= {"test_score", "add_activity", "major_switch", "early_round",
                                     "demonstrated_interest", "essay"}
    for cf in cfs:
        # exactly what /api/what-if receives: the counterfactual as JSON, overrides re-applied to the inputs
        wire = Counterfactual.model_validate(json.loads(cf.model_dump_json()))
        assert compute_probability(maya().with_overrides(**wire.overrides)).p_final == cf.p_new, cf.id
        assert cf.delta_pp == round((cf.p_new - compute_probability(maya()).p_final) * 100, 2)


async def test_sorted_filtered_and_two_best_major_switches(mock_db):
    mock_db(row("math_stats"), row("data_science", rate=0.4, smoothed=0.9), row("physics_astro", rate=0.5),
            row("biology"), row("electrical_engineering", n=CF.MIN_ARBITRAGE_N - 1))
    cfs = await generate(maya())
    deltas = [c.delta_pp for c in cfs]
    assert deltas == sorted(deltas, reverse=True) and min(deltas) >= CF.MIN_DELTA_PP
    majors = [c.id for c in cfs if c.kind == "major_switch"]
    assert len(majors) == 2 and "cf_major_biology" not in majors                 # not adjacent to CS
    assert "cf_major_electrical_engineering" not in majors                       # too few neighbours
    ms = next(c for c in cfs if c.id == "cf_major_math_stats")
    assert ms.overrides["major_multiplier"] == 1.12 and ms.label.endswith("(LAS)") and ms.confidence == "data_backed"


async def test_no_switches_or_db_call_for_majors_without_neighbours(mock_db):
    called = []
    mock_db()
    CF.db.major_arbitrage = lambda *a, **k: called.append(1)
    rubric = build_school_rubric(SCHOOL, "humanities", None)
    cfs = await CF.generate_counterfactuals(maya(), rubric=rubric, grade=maya_grade(), dossier=dossier(activities=3),
                                            school=SCHOOL, embedding=[0.0] * 768, gpa=None)
    assert called == [] and not any(c.kind == "major_switch" for c in cfs)


# ---------- what-if (shares Node 5's code path) ----------
async def ctx_for(x: ScoringInputs, mock_db, **kw):
    mock_db(row("math_stats"))
    cfs = await generate(x)
    return SimpleNamespace(scoring_inputs=x, major_category="computer_science", counterfactuals=cfs,
                           tiers=[2, 3, 4], has_recommendations=False, school=SCHOOL, **kw), cfs


async def test_what_if_major_reuses_node5_counterfactual(mock_db):
    ctx, cfs = await ctx_for(maya(), mock_db)
    r = run_what_if(ctx, WhatIfRequest(run_id="r", major_category="math_stats"))
    cf = next(c for c in cfs if c.id == "cf_major_math_stats")
    assert r.simulated.p_final == cf.p_new and r.confidence == "data_backed" and r.applied == [cf.label]


async def test_what_if_matches_counterfactuals_for_the_same_change(mock_db):
    ctx, cfs = await ctx_for(maya(), mock_db)
    by_id = {c.id: c for c in cfs}
    assert run_what_if(ctx, WhatIfRequest(run_id="r", sat=1530)).simulated.p_final == by_id["cf_sat_75"].p_new
    assert run_what_if(ctx, WhatIfRequest(run_id="r", add_activities=[2])).simulated.p_final == \
        by_id["cf_add_tier2"].p_new
    assert run_what_if(ctx, WhatIfRequest(run_id="r", early_round="EA")).simulated.p_final == by_id["cf_ea"].p_new


async def test_what_if_no_change_and_warnings(mock_db):
    ctx, _ = await ctx_for(maya(), mock_db)
    same = run_what_if(ctx, WhatIfRequest(run_id="r"))
    assert same.simulated == same.baseline and same.delta_pp == 0 and same.applied == []
    r = run_what_if(ctx, WhatIfRequest(run_id="r", early_round="ED", major_category="humanities"))
    assert "UIUC doesn't offer ED." in r.warnings and r.confidence == "model_estimate"
    assert any("No major-specific data" in w for w in r.warnings)
    req_ctx, _ = await ctx_for(maya(test_policy="required"), mock_db)
    assert "requires test scores" in run_what_if(req_ctx, WhatIfRequest(run_id="r", withhold_sat=True)).warnings[0]
    zero = SimpleNamespace(**{**vars(ctx), "scoring_inputs": maya(applicant_interest_weight=0.0)})
    r = run_what_if(zero, WhatIfRequest(run_id="r", demonstrated_interest=True))
    assert r.delta_pp == 0 and "doesn't consider demonstrated interest" in r.warnings[0]


async def test_what_if_essay_floor_depends_on_recommendations(mock_db):
    ctx, _ = await ctx_for(maya(ratings={"academic": 2.33, "extracurricular": 2.67, "personal": 2.67,
                                         "athletic": 4.0}), mock_db)
    r = run_what_if(ctx, WhatIfRequest(run_id="r", essay_steps=2))
    assert r.simulated.p_final > r.baseline.p_final
    personal = next(c for c in r.simulated.components if c.key == "personal").detail
    assert personal.startswith("rating 2.00")                                     # floored at 2 without letters
    with_recs = SimpleNamespace(**{**vars(ctx), "has_recommendations": True})
    r2 = run_what_if(with_recs, WhatIfRequest(run_id="r", essay_steps=2))
    assert next(c for c in r2.simulated.components if c.key == "personal").detail.startswith("rating 1.00")
