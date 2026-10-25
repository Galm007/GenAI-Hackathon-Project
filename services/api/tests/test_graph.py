"""The real compiled graph (§3.9.1) end to end through /api/evaluate, fully offline.

LLM calls and the embedder come from `app.fake_llm` (fictional fixtures); every Supabase, Zetaris and Tavily read is
mocked. This proves the browser stream comes from graph.astream, not the B03 script."""
import json
import re

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
