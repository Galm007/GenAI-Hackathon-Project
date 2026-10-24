import json
from types import SimpleNamespace

import httpx
import pytest

from app import demo
from app.api_models import WhatIfRequest
from app.main import app


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setattr(demo, "MAX_GAP_S", 0)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_replay_resumes_gap_free_and_has_fictional_provenance(client):
    info = (await client.get("/api/demo/maya-uiuc")).json()
    assert info["fictional"] and "not a recorded live" in info["provenance"]
    response = await client.get("/api/demo/maya-uiuc/stream", headers={"Last-Event-ID": "60"})
    assert response.status_code == 200
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert [e["seq"] for e in events] == list(range(61, info["events"]))
    assert events[-1]["event"] == "done"
    assert {e["run_id"] for e in events} == {"demo-maya-uiuc"}
    assert response.headers["x-accel-buffering"] == "no"


async def test_demo_what_if_reproduces_pivot_and_reset_without_external_services(client):
    bundle = demo.load_demo("maya-uiuc")
    pivot = next(c for c in bundle["context"]["counterfactuals"] if c["id"] == "cf_major_math_stats")
    response = await client.post("/api/what-if", json={"run_id": "demo-maya-uiuc", "major_category": "math_stats"})
    assert response.status_code == 200
    body = response.json()
    assert body["simulated"]["p_final"] == pivot["p_new"] and body["delta_pp"] == pivot["delta_pp"]
    assert body["warnings"] and body["confidence"] == "model_estimate"
    reset = (await client.post("/api/what-if", json={"run_id": "demo-maya-uiuc"})).json()
    assert reset["baseline"] == reset["simulated"] and reset["delta_pp"] == 0


async def test_unavailable_live_context_is_never_substituted_with_maya(client):
    response = await client.post("/api/what-if", json={"run_id": "a-real-student-run", "sat": 1500})
    assert response.status_code == 503


async def test_route_delegates_to_the_live_context_provider_when_track_b_supplies_it(client, monkeypatch):
    async def lookup(run_id):
        return demo.scoring_context(demo.load_demo("maya-uiuc")) if run_id == "live-test" else None
    monkeypatch.setattr(app.state, "run_manager", SimpleNamespace(scoring_context=lookup))
    response = await client.post("/api/what-if", json={"run_id": "live-test", "sat": 1530})
    assert response.status_code == 200 and "SAT 1530" in response.json()["applied"]
    assert (await client.post("/api/what-if", json={"run_id": "missing-test"})).status_code == 404


async def test_invalid_or_missing_recordings_fail_before_stream_headers(client):
    for name in ("not-present", "..", "Maya", "maya_uiuc"):
        response = await client.get(f"/api/demo/{name}/stream")
        assert response.status_code == 404
    assert (await client.get("/api/demo/maya-uiuc/stream?speed=0")).status_code == 422
    assert (await client.post("/api/what-if", json={"run_id": "demo-maya-uiuc", "sat": 1800})).status_code == 422


def test_registration_provides_a_snapshot_and_rejects_path_traversal():
    from app.runs import RunManager
    manager = RunManager()
    demo.register_demo_runs(manager)
    run = manager.get("demo-maya-uiuc")
    assert run.done and "probability" in run.captured
    with pytest.raises(Exception) as caught:
        demo.load_demo("../../.env")
    assert caught.value.status_code == 404
    assert WhatIfRequest(run_id="demo-maya-uiuc", withhold_sat=True).withhold_sat
