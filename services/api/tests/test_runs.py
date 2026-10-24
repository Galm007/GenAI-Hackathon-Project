import json

import httpx
import pytest

from app import runs as runs_mod
from app.schemas.debate import DebateTurn
from app.schemas.delta import Counterfactual, DeltaReport, ProbabilityBreakdown
from app.schemas.dossier import ComputedMetrics, DossierGrade, ParsedDossier
from app.schemas.inputs import RawApplicantInputs
from app.schemas.institution import InstitutionalBrief, SchoolRubric
from app.schemas.twins import EmpiricalBaseline, TwinAnalysis, TwinCard

SCRIPT = runs_mod.load_script()
INTAKE = {"session_id": "test-session-1", "intended_major": "Computer Science", "target_schools": ["uiuc"],
          "activities_text": "USACO Gold; crop-disease classifier", "consent": True}


@pytest.fixture(autouse=True)
def no_pauses(monkeypatch):
    monkeypatch.setattr(runs_mod, "MAX_GAP_S", 0.0)


class _Req:
    async def is_disconnected(self) -> bool:
        return False


def _seqs(frames: list[dict]) -> list[int]:
    return [int(f["id"]) for f in frames]


def _parse_sse(body: str) -> list[dict]:
    frames = []
    for block in body.replace("\r\n", "\n").split("\n\n"):
        f = dict(line.split(": ", 1) for line in block.split("\n") if line and not line.startswith(":"))
        if f:
            frames.append(f)
    return frames


# ---------- the fixture honours the frozen event contract (§1.6, §4.2) ----------
def test_script_is_gap_free_and_contract_valid():
    assert [e["seq"] for e in SCRIPT] == list(range(len(SCRIPT)))
    assert SCRIPT[0]["event"] == "run_started" and SCRIPT[-1]["event"] == "done"
    by = {e["event"]: e for e in SCRIPT}
    ParsedDossier.model_validate(by["dossier_parsed"]["dossier"] | {"essay_text": None})
    DossierGrade.model_validate(by["scorecard"]["grade"])
    ComputedMetrics.model_validate(by["scorecard"]["metrics"])
    SchoolRubric.model_validate(by["school_rubric"]["rubric"])
    InstitutionalBrief.model_validate(by["fact_checks"]["brief"])
    [TwinCard.model_validate(t) for t in by["twins"]["twins"]]
    EmpiricalBaseline.model_validate(by["baseline"]["baseline"])
    TwinAnalysis.model_validate(by["twin_analysis"]["analysis"])
    ProbabilityBreakdown.model_validate(by["probability"]["probability"])
    for e in SCRIPT:
        if e["event"] == "debate_turn_end":
            turn = DebateTurn.model_validate(e)
            assert all(turn.content[c.span[0]:c.span[1]].startswith("[[") for c in turn.citations)
    [Counterfactual.model_validate(c) for c in by["counterfactuals"]["counterfactuals"]]
    DeltaReport.model_validate(by["final_report"]["report"])


# ---------- RunManager + sse_frames ----------
async def _finished_run() -> runs_mod.Run:
    mgr = runs_mod.RunManager()
    run = await mgr.start(session_id="s1", inputs=RawApplicantInputs(intended_major="CS", target_schools=["uiuc"]),
                          school_slug="uiuc")
    await run.task
    return run


async def test_scripted_run_publishes_gap_free_envelopes():
    run = await _finished_run()
    assert run.status == "complete" and run.done
    assert [e["seq"] for e in run.events] == list(range(len(SCRIPT)))
    assert [e["event"] for e in run.events] == [e["event"] for e in SCRIPT]
    assert {e["run_id"] for e in run.events} == {run.run_id}
    assert set(run.captured) == runs_mod.CAPTURED


async def test_reconnect_resumes_without_duplicates():
    run = await _finished_run()
    first = [f async for f in runs_mod.sse_frames(run, -1, _Req())][:10]
    rest = [f async for f in runs_mod.sse_frames(run, int(first[-1]["id"]), _Req())]
    assert _seqs(first) + _seqs(rest) == list(range(len(run.events)))
    assert json.loads(rest[-1]["data"])["event"] == "done"
    assert run.subscribers == 0


async def test_live_reader_follows_a_running_run(monkeypatch):
    monkeypatch.setattr(runs_mod, "MAX_GAP_S", 0.002)
    mgr = runs_mod.RunManager()
    run = await mgr.start(session_id="s2", inputs=RawApplicantInputs(intended_major="CS", target_schools=["uiuc"]),
                          school_slug="uiuc")
    frames = [f async for f in runs_mod.sse_frames(run, -1, _Req())]
    assert _seqs(frames) == list(range(len(SCRIPT)))


async def test_second_submit_from_the_same_session_is_refused():
    mgr = runs_mod.RunManager()
    inputs = RawApplicantInputs(intended_major="CS", target_schools=["uiuc"])
    run = await mgr.start(session_id="s3", inputs=inputs, school_slug="uiuc")
    with pytest.raises(runs_mod.RateLimited):
        await mgr.start(session_id="s3", inputs=inputs, school_slug="uiuc")
    await run.task
    await mgr.start(session_id="s3", inputs=inputs, school_slug="uiuc")    # free again once the first is done


# ---------- HTTP ----------
@pytest.fixture
async def client():
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_evaluate_then_stream_with_last_event_id(client):
    r = await client.post("/api/evaluate", data={"intake": json.dumps(INTAKE)})
    assert r.status_code == 202, r.text
    body = r.json()
    from app.main import runs
    await runs.get(body["run_id"]).task

    r = await client.get(body["stream_url"], headers={"Last-Event-ID": "40"})
    assert r.headers["content-type"].startswith("text/event-stream")
    assert r.headers["x-accel-buffering"] == "no"
    frames = _parse_sse(r.text)
    assert _seqs(frames) == list(range(41, len(SCRIPT)))
    assert frames[-1]["event"] == "done"
    assert json.loads(frames[-1]["data"])["status"] == "complete"

    snap = (await client.get(f"/api/evaluate/{body['run_id']}")).json()
    assert snap["status"] == "complete" and "probability" in snap["captured"]


async def test_evaluate_rejects_non_pdf_and_empty_dossiers(client):
    intake = json.dumps(INTAKE | {"session_id": "test-session-2"})
    r = await client.post("/api/evaluate", data={"intake": intake}, files={"transcript": ("t.pdf", b"hello")})
    assert r.status_code == 415
    empty = json.dumps({k: v for k, v in INTAKE.items() if k != "activities_text"} | {"session_id": "test-session-3"})
    assert (await client.post("/api/evaluate", data={"intake": empty})).status_code == 422
    assert (await client.get("/api/evaluate/nope/stream")).status_code == 404


async def test_dev_fake_stream_resumes_from_last_event_id(client):
    r = await client.get("/api/dev/fake-stream", headers={"Last-Event-ID": "60"}, params={"speed": 8})
    frames = _parse_sse(r.text)
    assert _seqs(frames) == list(range(61, len(SCRIPT)))
    assert frames[-1]["event"] == "done"


async def test_health(client):
    assert (await client.get("/api/health")).json()["ok"] is True
