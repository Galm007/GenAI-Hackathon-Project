"""The real compiled graph (§3.9.1) end to end through /api/evaluate, fully offline.

LLM calls and the embedder come from `app.fake_llm` (fictional fixtures); every Supabase, Zetaris and Tavily read is
mocked. This proves the browser stream comes from graph.astream, not the B03 script."""
import json
import re
from pathlib import Path

import httpx
import pytest

from app import db, fake_llm, zetaris_repo
from app.agents import graph as G
from app.agents.nodes import institutional
from app.agents.prompts.committee import MAX_TURNS
from app.config import settings

from . import test_debate as T
from .test_runs import INTAKE, _parse_sse
from .test_scoring_rubric import school
from .test_twins import MEDIANS, STATS

MAYA = Path(__file__).resolve().parents[3] / "data/demo_dossiers/maya"
NODES = ["dossier_parser", "institutional", "twins", "committee_docket", "advocate", "chair", "delta_engine"]
PLAN_EDGES = {  # plan §3.1: solid = fixed edge, dotted = conditional
    ("__start__", "-.->", "dossier_parser"), ("__start__", "-.->", "institutional"), ("__start__", "-.->", "twins"),
    ("dossier_parser", "-->", "institutional"), ("dossier_parser", "-->", "twins"),
    ("institutional", "-->", "committee_docket"), ("twins", "-->", "committee_docket"),
    ("committee_docket", "-->", "advocate"), ("advocate", "-->", "chair"),
    ("chair", "-.->", "advocate"), ("chair", "-.->", "delta_engine"), ("delta_engine", "-->", "__end__"),
}


def test_mermaid_matches_the_plan_diagram():
    mermaid = G.graph.get_graph().draw_mermaid()
    edges = set(re.findall(r"^\s*(\w+) (-->|-\.->) (\w+);", mermaid, re.MULTILINE))
    assert edges == PLAN_EDGES
    assert all(f"\t{n}({n})" in mermaid for n in NODES)


def test_route_entry_skips_node_one_only_with_a_full_cached_dossier():
    full = {k: object() for k in G.DOSSIER_KEYS}
    assert G.route_entry(full) == ["institutional", "twins"]
    assert G.route_entry({**full, "profile_embedding": None}) == "dossier_parser"
    assert G.route_entry({}) == "dossier_parser"


def twin_rows() -> list[dict]:
    return [{**t, "activities": t["top_activities"]} for t in T.fixture("TwinCard")]


@pytest.fixture
def offline(monkeypatch):
    restore = fake_llm.install()
    seen: dict[str, list] = {"saved": [], "logged": []}

    async def returning(value):
        return value

    def const(value):
        async def f(*_, **__):
            return value
        return f

    async def save_run(row):
        seen["saved"].append(row)

    async def append_event_log(run_id, events, status):
        seen["logged"].append((run_id, status))

    monkeypatch.setattr(settings, "zetaris_enabled", False)
    monkeypatch.setattr(zetaris_repo, "school_profile", const(school(name="University of Illinois",
                                                                      peer_group="big_ten_public")))
    monkeypatch.setattr(zetaris_repo, "reddit_calibration", const(2.4))
    monkeypatch.setattr(zetaris_repo, "admitted_medians", const(MEDIANS))
    monkeypatch.setattr(institutional, "research_school", const([]))
    monkeypatch.setattr(db, "match_twins", const(twin_rows()))
    monkeypatch.setattr(db, "neighborhood_stats", const(STATS))
    monkeypatch.setattr(db, "major_arbitrage", const([]))
    monkeypatch.setattr(db, "save_run", save_run)
    monkeypatch.setattr(db, "append_event_log", append_event_log)
    yield seen
    restore()


@pytest.fixture
async def client():
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_evaluate_streams_the_real_graph_offline(client, offline):
    intake = INTAKE | {"session_id": "graph-session-1"}
    r = await client.post("/api/evaluate", data={"intake": json.dumps(intake)})
    assert r.status_code == 202, r.text
    from app.main import runs
    run = runs.get(r.json()["run_id"])
    await run.task

    frames = _parse_sse((await client.get(r.json()["stream_url"])).text)
    events = [json.loads(f["data"]) for f in frames]
    names = [e["event"] for e in events]
    assert names[0] == "run_started" and names[-1] == "done" and events[-1]["status"] == "complete", events[-3:]
    assert [int(f["id"]) for f in frames] == list(range(len(frames)))

    completed = [e["node"] for e in events if e["event"] == "node_complete"]
    assert completed[0] == "dossier_parser" and set(completed[1:3]) == {"institutional", "twins"}
    assert completed[3:] == ["committee_docket", "advocate", "chair", "advocate", "chair", "delta_engine"]
    for ev in ("dossier_parsed", "scorecard", "school_rubric", "fact_checks", "twins", "baseline", "radar",
               "twin_analysis", "probability", "counterfactuals", "final_report"):
        assert ev in names, ev
    assert names.count("debate_turn_end") == MAX_TURNS and names.count("debate_token") > MAX_TURNS
    assert set(run.captured) >= {"scorecard", "probability", "counterfactuals", "final_report"}

    final = run.final
    assert len(final["debate"]) == MAX_TURNS and final["delta_report"].committee_disposition
    assert final["probability"].p_final == events[names.index("probability")]["probability"]["p_final"]
    assert offline["saved"][0]["id"] == run.run_id and offline["logged"] == [(run.run_id, "complete")]

    # what-if on the live run goes through runs.scoring_context (route in demo.py)
    w = await client.post("/api/what-if", json={"run_id": run.run_id, "sat": 1560})
    assert w.status_code == 200, w.text
    assert w.json()["baseline"]["p_final"] == final["probability"].p_final

    # a second school reuses Node 1's outputs
    c = await client.post(f"/api/evaluate/{run.run_id}/schools/umich")
    assert c.status_code == 202, c.text
    child = runs.get(c.json()["run_id"])
    await child.task
    child_names = [e["event"] for e in child.events]
    assert child.status == "complete" and child.events[0]["cached_dossier"] is True
    assert child_names[1:3] == ["dossier_parsed", "scorecard"]
    assert "dossier_parser" not in [e["node"] for e in child.events if e["event"] == "node_complete"]


# ---------- B14: FAKE_LLM=1 with the real Zetaris repository (only Supabase is stood in) ----------
@pytest.fixture
def fake_mode(monkeypatch):
    """Fake mode as a developer gets it: fixtures for the model, the real zetaris_repo, Supabase stood in."""
    from app import llm
    monkeypatch.setattr(settings, "fake_llm", True)
    for name in ("parse", "stream_text"):                       # let monkeypatch restore what install() replaces
        monkeypatch.setattr(llm, name, getattr(llm, name))
    monkeypatch.setattr(institutional, "run_zetaris_research", institutional.run_zetaris_research)
    from app.agents.nodes import dossier_parser
    monkeypatch.setattr(dossier_parser, "embed_one", dossier_parser.embed_one)

    class NoProviderCalls:
        def __init__(self, label: str):
            self.label = label

        def __getattr__(self, name):
            raise AssertionError(f"fake mode reached a real model provider ({self.label}.{name})")

    from app import openai_compat
    monkeypatch.setattr(llm, "client", NoProviderCalls("llm.client"))
    monkeypatch.setattr(openai_compat, "http", NoProviderCalls("openai_compat.http"))
    monkeypatch.setattr(zetaris_repo, "_cache", {})

    def const(value):
        async def f(*_, **__):
            return value
        return f

    for name, value in {"get_school": school(name="University of Illinois", peer_group="big_ten_public"),
                        "peer_schools": ["purdue"], "school_calibration": 2.4, "admitted_medians": MEDIANS,
                        "match_twins": twin_rows(), "neighborhood_stats": STATS, "major_arbitrage": [],
                        "save_run": None, "append_event_log": None}.items():
        monkeypatch.setattr(db, name, const(value))
    monkeypatch.setattr(institutional, "research_school", const([]))       # no Tavily key in fake mode
    return monkeypatch


@pytest.mark.parametrize("zetaris", ["disabled", "enabled_but_down"])
async def test_fake_mode_runs_the_whole_graph_offline(client, fake_mode, zetaris):
    from app.zetaris import zetaris as client_
    calls: list[str] = []

    async def query(sql, **_):
        calls.append(sql)
        raise httpx.ConnectError("no Zetaris on this machine")

    fake_mode.setattr(settings, "zetaris_enabled", zetaris == "enabled_but_down")
    fake_mode.setattr(client_, "query", query)
    restore = fake_llm.install()
    try:
        from app.main import runs
        r = await client.post("/api/evaluate", data={"intake": json.dumps(INTAKE | {"session_id": f"b14-{zetaris}"})})
        run = runs.get(r.json()["run_id"])
        await run.task
    finally:
        restore()
    names = [e["event"] for e in run.events]
    assert run.status == "complete", [e for e in run.events if e["event"] == "error"]
    assert names.count("debate_turn_end") == MAX_TURNS and "final_report" in names
    assert run.final["zetaris_queries"] == []                       # fake mode never runs the SQL tool loop
    if zetaris == "disabled":
        assert calls == []                                          # not one Zetaris call
    else:
        assert calls                                                # tried, failed, fell back to Supabase
    assert run.final["baseline"].odds_inflation == 2.4              # the Supabase calibration was used


async def test_cli_runs_in_fake_mode(fake_mode, monkeypatch, capsys):
    from scripts import run_graph_cli
    monkeypatch.setattr(settings, "zetaris_enabled", False)
    root = MAYA
    monkeypatch.setattr("sys.argv", ["run_graph_cli", "--transcript", str(root / "transcript.pdf"),
                                     "--activities", str(root / "activities.txt"), "--essay", str(root / "essay.txt"),
                                     "--major", "Computer Science", "--school", "uiuc"])
    await run_graph_cli.main()
    out = capsys.readouterr().out
    assert "◆ P(admit)" in out and "━━ Turn 4 · CHAIR ━━" in out and "✔ delta_engine" in out
    assert '"committee_disposition"' in out


def node_one_ran(run) -> bool:
    return "dossier_parser" in [e["node"] for e in run.events if e["event"] == "node_complete"]


async def test_identical_upload_skips_node_one_but_still_fills_the_dossier_panel(client, offline):
    from app.main import runs
    intake = INTAKE | {"activities_text": "Robotics captain; cache-test file", "session_id": "graph-cache-1"}

    async def evaluate(body: dict):
        r = await client.post("/api/evaluate", data={"intake": json.dumps(body)})
        assert r.status_code == 202, r.text
        run = runs.get(r.json()["run_id"])
        await run.task
        assert run.status == "complete"
        return run

    first = await evaluate(intake)
    second = await evaluate(intake | {"session_id": "graph-cache-2"})   # same files, another tab or device
    assert node_one_ran(first) and not node_one_ran(second)
    assert second.events[0]["cached_dossier"] is True
    assert [e["event"] for e in second.events[1:3]] == ["dossier_parsed", "scorecard"]
    by = {e["event"]: e for e in first.events}
    replayed = {e["event"]: e for e in second.events[1:3]}
    assert replayed["scorecard"]["grade"] == by["scorecard"]["grade"]           # same panel content as live
    assert replayed["scorecard"]["metrics"] == by["scorecard"]["metrics"]       # live sends graded metrics here
    assert replayed["dossier_parsed"]["dossier"] == by["dossier_parsed"]["dossier"]
    assert "essay_text" not in replayed["dossier_parsed"]["dossier"]
    assert second.final["probability"].p_final == first.final["probability"].p_final

    # a different context changes what Node 1 grades and embeds, so it is not a cache hit
    other = await evaluate(intake | {"session_id": "graph-cache-3", "context": {"first_gen": True}})
    assert node_one_ran(other)
