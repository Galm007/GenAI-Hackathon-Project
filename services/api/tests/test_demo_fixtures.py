import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import fake_llm
from app.agents.nodes.dossier_parser import dossier_parser_node
from app.api_models import IntakeForm, WhatIfRequest
from app.schemas.delta import Counterfactual
from app.scoring.probability import ScoringInputs, compute_probability
from app.scoring.whatif import run_what_if

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = json.loads((ROOT / "data/demo_runs/maya-uiuc.json").read_text())


def context():
    raw = BUNDLE["context"]
    return SimpleNamespace(
        **{
            **raw,
            "scoring_inputs": ScoringInputs.model_validate(raw["scoring_inputs"]),
            "counterfactuals": [Counterfactual.model_validate(c) for c in raw["counterfactuals"]],
        }
    )


def test_fictional_fixture_math_conserves_and_every_pivot_is_reproducible():
    assert BUNDLE["fictional"] and "not a recorded live" in BUNDLE["provenance"]
    ctx = context()
    by = {e["event"]: e for e in BUNDLE["events"]}
    p = compute_probability(ctx.scoring_inputs)
    assert by["probability"]["probability"] == p.model_dump()
    assert abs(sum(c.delta_pp for c in p.components) - p.p_final * 100) <= 0.5
    for cf in ctx.counterfactuals:
        assert compute_probability(ctx.scoring_inputs.with_overrides(**cf.overrides)).p_final == cf.p_new
        request = {
            "cf_major_math_stats": {"major_category": "math_stats"},
            "cf_sat_75": {"sat": 1530},
            "cf_add_tier2": {"add_activities": [2]},
            "cf_essay": {"essay_steps": 1},
        }[cf.id]
        simulated = run_what_if(ctx, WhatIfRequest(run_id="demo-maya-uiuc", **request))
        assert simulated.simulated.p_final == cf.p_new
        assert simulated.delta_pp == cf.delta_pp
    assert len(by["radar"]["radar"]["axes"]) == 6
    assert all(not t["source_url"] for t in by["twins"]["twins"])


@pytest.mark.asyncio
async def test_existing_node_one_runs_offline_without_a_model_or_embedding_service():
    intake = IntakeForm.model_validate_json((ROOT / "data/demo_dossiers/maya/intake.json").read_text())
    restore = fake_llm.install()
    try:
        result = await dossier_parser_node({"inputs": intake.to_inputs(transcript_pdf_b64=None, resume_pdf_b64=None)})
    finally:
        restore()
    assert result["metrics"].gpa_uw_4 == 3.94
    assert result["metrics"].gpa_w_5 == 4.52
    assert len(result["profile_embedding"]) == 768
    assert result["grade"].major_category == "computer_science"
