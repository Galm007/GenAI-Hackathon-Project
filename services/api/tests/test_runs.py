import json
from types import SimpleNamespace

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
INPUTS = RawApplicantInputs(intended_major="CS", target_schools=["uiuc"])


@pytest.fixture(autouse=True)
def no_pauses_or_db(monkeypatch):
    monkeypatch.setattr(runs_mod, "MAX_GAP_S", 0.0)
    persisted: list[tuple] = []

    async def append_event_log(run_id, events, status):
        persisted.append((run_id, len(events), status))

    monkeypatch.setattr(runs_mod.db, "append_event_log", append_event_log)
    return persisted


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


# ---------- RunManager driven by a stub graph ----------
class StubGraph:
    """Replays the scripted events as LangGraph `custom` chunks, with an `updates` chunk after each node_end."""

    def __init__(self, fail: Exception | None = None):
        self.fail, self.states = fail, []

    async def astream(self, state, config, stream_mode):
        assert stream_mode == ["updates", "custom"] and config["configurable"]["thread_id"] == state["run_id"]
        self.states.append(state)
        for ev in SCRIPT:
            if ev["event"] in ("run_started", "done", "node_complete"):   # the driver makes these itself
                continue
            yield "custom", {k: v for k, v in ev.items() if k not in ("seq", "run_id")}
            if ev["event"] == "node_end":
                yield "updates", {ev["node"]: {"warnings": []}}
            if self.fail and ev["event"] == "probability":
                raise self.fail

    async def aget_state(self, config):
        return SimpleNamespace(values={"inputs": INPUTS, "done": True})


@pytest.fixture
def stub(monkeypatch):
    def install(**kw) -> StubGraph:
        g = StubGraph(**kw)
        monkeypatch.setattr(runs_mod, "graph", g)
        return g
    return install


async def _finished_run(mgr: runs_mod.RunManager | None = None, session: str = "s1") -> runs_mod.Run:
    run = await (mgr or runs_mod.RunManager()).start(session_id=session, inputs=INPUTS, school_slug="uiuc")
    await run.task
    return run


async def test_driver_wraps_graph_chunks_in_gap_free_envelopes(stub, no_pauses_or_db):
    g = stub()
    run = await _finished_run()
    assert run.status == "complete" and run.done and run.final["done"] is True
    assert [e["seq"] for e in run.events] == list(range(len(run.events))) and {e["run_id"] for e in run.events} == {
        run.run_id}
    names = [e["event"] for e in run.events]
    assert names[0] == "run_started" and names[-1] == "done" and run.events[-1]["status"] == "complete"
    assert run.events[0]["cached_dossier"] is False
    script_names = [e["event"] for e in SCRIPT if e["event"] not in ("run_started", "done", "node_complete")]
    assert [n for n in names[1:-1] if n != "node_complete"] == script_names
    ends = [e["node"] for e in run.events if e["event"] == "node_end"]
    assert [e["node"] for e in run.events if e["event"] == "node_complete"] == ends    # one per finished node
    assert set(run.captured) == runs_mod.CAPTURED
    assert g.states[0] == {"run_id": run.run_id, "session_id": "s1", "inputs": INPUTS, "school_slug": "uiuc"}
    assert no_pauses_or_db == [(run.run_id, len(run.events), "complete")]            # event log persisted


async def test_graph_failure_ends_the_stream_cleanly(stub, no_pauses_or_db):
    stub(fail=RuntimeError("boom"))
    run = await _finished_run()
    assert run.status == "failed" and run.events[-1]["event"] == "done"
    err = run.events[-2]
    assert (err["event"], err["message"], err["recoverable"]) == ("error", "Evaluation failed (RuntimeError).", False)
    assert "probability" in run.captured and no_pauses_or_db[-1][2] == "failed"


async def test_event_log_persistence_failure_never_breaks_the_run(stub, monkeypatch):
    stub()

    async def broken(*_):
        raise httpx.ConnectError("supabase down")

    monkeypatch.setattr(runs_mod.db, "append_event_log", broken)
    run = await _finished_run()
    assert run.status == "complete" and run.done


async def test_child_run_skips_node_one_and_replays_its_outputs(stub):
    from . import test_debate as T
    g = stub()
    mgr = runs_mod.RunManager()
    parent = await _finished_run(mgr)
    s = T.base_state(profile_embedding=[0.0] * 768)
    parent.final = {"inputs": INPUTS, "profile_text": "t", **{k: s[k] for k in ("dossier", "grade", "metrics",
                                                                               "profile_embedding")}}
    child = await mgr.start_child(parent, "umich")
    await child.task
    assert child.school_slug == "umich" and child.session_id == parent.session_id
    assert set(runs_mod.PREFILL_KEYS) <= set(g.states[-1]) and g.states[-1]["school_slug"] == "umich"
    first = [e["event"] for e in child.events[:3]]
    assert first == ["run_started", "dossier_parsed", "scorecard"] and child.events[0]["cached_dossier"] is True
    assert "essay_text" not in child.events[1]["dossier"]


async def test_reconnect_resumes_without_duplicates(stub):
    stub()
    run = await _finished_run()
    first = [f async for f in runs_mod.sse_frames(run, -1, _Req())][:10]
    rest = [f async for f in runs_mod.sse_frames(run, int(first[-1]["id"]), _Req())]
    assert _seqs(first) + _seqs(rest) == list(range(len(run.events)))
    assert json.loads(rest[-1]["data"])["event"] == "done"
    assert run.subscribers == 0


async def test_live_reader_follows_a_running_run(stub):
    stub()
    mgr = runs_mod.RunManager()
    run = await mgr.start(session_id="s2", inputs=INPUTS, school_slug="uiuc")
    frames = [f async for f in runs_mod.sse_frames(run, -1, _Req())]
    assert _seqs(frames) == list(range(len(run.events))) and frames[-1]["event"] == "done"


async def test_second_submit_from_the_same_session_is_refused(stub):
    stub()
    mgr = runs_mod.RunManager()
    run = await mgr.start(session_id="s3", inputs=INPUTS, school_slug="uiuc")
    with pytest.raises(runs_mod.RateLimited):
        await mgr.start(session_id="s3", inputs=INPUTS, school_slug="uiuc")
    await run.task
    await (await mgr.start(session_id="s3", inputs=INPUTS, school_slug="uiuc")).task   # free again once done


# ---------- scoring context (feeds /api/what-if) ----------
async def test_scoring_context_from_a_live_run(stub, monkeypatch):
    stub()
    run = await _finished_run()

    async def profile(slug):
        return {"slug": slug, "name": "UIUC"}

    monkeypatch.setattr(runs_mod.zetaris_repo, "school_profile", profile)
    ctx = await runs_mod.RunManager.scoring_context(SimpleNamespace(_runs={run.run_id: run}), run.run_id)
    cap = run.captured
    assert ctx.scoring_inputs.model_dump(mode="json") == cap["probability"]["scoring_inputs"]
    assert ctx.tiers == [ag["tier"] for ag in cap["scorecard"]["grade"]["activity_grades"]]
    assert ctx.sat == cap["scorecard"]["metrics"]["sat_equivalent"] and ctx.school == {"slug": "uiuc", "name": "UIUC"}
    assert [c.id for c in ctx.counterfactuals] == [c["id"] for c in cap["counterfactuals"]["counterfactuals"]]


async def test_scoring_context_after_a_restart_reads_postgres(monkeypatch):
    by = {e["event"]: e for e in SCRIPT}
    row = {"school_slug": "uiuc", "major_category": "computer_science", "status": "complete",
           "scoring_inputs": by["probability"]["scoring_inputs"], "grade": by["scorecard"]["grade"],
           "metrics": by["scorecard"]["metrics"], "intake": {"has_recommendations": True},
           "counterfactuals": by["counterfactuals"]["counterfactuals"], "profile_embedding": "[0.5, 0.25]"}

    async def load_run(run_id):
        return row if run_id == "old" else None

    async def profile(slug):
        return {"slug": slug}

    monkeypatch.setattr(runs_mod.db, "load_run", load_run)
    monkeypatch.setattr(runs_mod.zetaris_repo, "school_profile", profile)
    mgr = runs_mod.RunManager()
    ctx = await mgr.scoring_context("old")
    assert ctx.embedding == [0.5, 0.25] and ctx.has_recommendations is True and ctx.school_slug == "uiuc"
    assert await mgr.scoring_context("missing") is None
    snap = await mgr.snapshot("old")
    assert snap["status"] == "complete" and snap["grade"] == row["grade"] and await mgr.snapshot("missing") is None


# ---------- HTTP ----------
@pytest.fixture
async def client():
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_evaluate_then_stream_with_last_event_id(client, stub):
    stub()
    r = await client.post("/api/evaluate", data={"intake": json.dumps(INTAKE)})
    assert r.status_code == 202, r.text
    body = r.json()
    from app.main import runs
    run = runs.get(body["run_id"])
    await run.task

    r = await client.get(body["stream_url"], headers={"Last-Event-ID": "40"})
    assert r.headers["content-type"].startswith("text/event-stream")
    assert r.headers["x-accel-buffering"] == "no"
    frames = _parse_sse(r.text)
    assert _seqs(frames) == list(range(41, len(run.events)))
    assert frames[-1]["event"] == "done"
    assert json.loads(frames[-1]["data"])["status"] == "complete"

    snap = (await client.get(f"/api/evaluate/{body['run_id']}")).json()
    assert snap["status"] == "complete" and "probability" in snap["captured"]


async def test_another_school_needs_a_finished_parent(client, stub):
    stub()
    assert (await client.post("/api/evaluate/nope/schools/umich")).status_code == 409
    r = await client.post("/api/evaluate", data={"intake": json.dumps(INTAKE | {"session_id": "test-session-4"})})
    from app.main import runs
    parent = runs.get(r.json()["run_id"])
    await parent.task
    parent.final = None                               # the stub's final state has no dossier to reuse
    assert (await client.post(f"/api/evaluate/{parent.run_id}/schools/umich")).status_code == 409


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


@pytest.mark.parametrize(("db_up", "zetaris_up"), [(True, True), (True, False), (False, True)])
async def test_health_probes_the_database_and_zetaris(client, monkeypatch, db_up, zetaris_up):
    from app import main

    async def get_school(slug):
        if not db_up:
            raise httpx.ConnectError("supabase down")
        return {"slug": slug}

    async def query(sql, **kw):
        if not zetaris_up:
            raise httpx.ConnectError("zetaris down")
        assert sql == "SELECT 7 AS seven" and kw == {"page_limit": 1}
        return [{"seven": "7"}]

    monkeypatch.setattr(main.db, "get_school", get_school)
    monkeypatch.setattr(main.zetaris, "query", query)
    h = (await client.get("/api/health")).json()
    assert (h["ok"], h["db"], h["zetaris"]) == (db_up, db_up, zetaris_up)
    assert {"zetaris_enabled", "anthropic_key", "tavily", "demo_mode", "fake_llm", "ts"} <= set(h)
