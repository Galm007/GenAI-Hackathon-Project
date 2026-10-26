"""The committee's shared case file (§1.7.3, B18b) against the real World Model sidecar (services/world-model)."""
import asyncio
import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import httpx
import orjson
import pytest

from app import world_model
from app.agents import docket as D
from app.agents.nodes import docket_node
from app.scoring.probability import compute_probability

from . import test_debate as T

SIDECAR = Path(__file__).resolve().parents[2] / "world-model" / "src" / "server.ts"
WARNING = "world model unavailable: docket built from run state"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def sidecar_url():
    """The real sidecar on a free port (needs Node 24, as the API host does)."""
    if not shutil.which("node"):
        pytest.skip("node is not installed")
    port = free_port()
    proc = subprocess.Popen(["node", str(SIDECAR)], env={**os.environ, "WORLD_MODEL_PORT": str(port)},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            httpx.get(f"{url}/health", timeout=0.5)
            break
        except httpx.HTTPError:
            if proc.poll() is not None:
                pytest.fail("the sidecar exited at startup")
            time.sleep(0.1)
    yield url
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture
def wm(monkeypatch):
    """Point the client at `url` with a fresh HTTP client and no back-off left over from another test."""
    def use(url: str | None):
        monkeypatch.setattr(world_model.settings, "world_model_url", url)
        monkeypatch.setattr(world_model, "_down_until", 0.0)
        monkeypatch.setattr(world_model, "http", httpx.AsyncClient(timeout=world_model.TIMEOUT))
    monkeypatch.setattr(docket_node, "emit", lambda *a, **k: None)
    return use


def run_state(run_id: str) -> dict:
    return {**T.base_state(), "run_id": run_id}


async def test_nodes_2_and_3_append_concurrently_without_loss(sidecar_url, wm):
    wm(sidecar_url)
    s = run_state("concurrent")
    prob = compute_probability(D.build_scoring_inputs(s))
    # Nodes 2 and 3 finish at the same moment (they run in parallel), alongside a burst of extra writers.
    results = await asyncio.gather(
        world_model.append("concurrent", "institutional", D.institutional_sections(s)),
        world_model.append("concurrent", "twins", D.twin_sections(s)),
        *(world_model.append("concurrent", node, {f"extra_{node}_{i}": i})
          for i in range(25) for node in ("institutional", "twins")))
    assert all(results)

    engine = await world_model.sections("concurrent")
    expected = {*D.institutional_sections(s), *D.twin_sections(s)} | {
        f"extra_{n}_{i}" for i in range(25) for n in ("institutional", "twins")}
    assert set(engine) == expected                               # 60 sections from two writers, none lost
    assert engine["twins"] == orjson.loads(orjson.dumps(D.twin_sections(s)["twins"]))
    audit = (await world_model.http.get(f"{sidecar_url}/v1/run:concurrent/audit")).json()
    assert [a["seq"] for a in audit] == list(range(1, len(audit) + 1))
    # Same facts, same bytes: the debate's prompt cache and citation index don't care where the docket came from.
    assert D.build_docket(s, prob, engine) == D.build_docket(s, prob)


async def test_docket_node_reads_the_sections_from_the_engine(sidecar_url, wm):
    wm(sidecar_url)
    s = run_state("reads-engine")
    await world_model.append("reads-engine", "dossier_parser", D.applicant_section(s))
    planted = {**D.twin_sections(s), "twin_analysis": {"summary": "written by Node 3 into the case file"}}
    await world_model.append("reads-engine", "twins", planted)

    out = await docket_node.committee_docket_node(s)
    packet = json.loads(out["docket"])
    assert packet["twin_analysis"] == {"summary": "written by Node 3 into the case file"}   # the engine's copy
    assert packet["school_cds"] == orjson.loads(orjson.dumps(D.institutional_sections(s)["school_cds"]))  # state
    assert out["warnings"] == []
    model = (await world_model.http.get(f"{sidecar_url}/v1/run:reads-engine/context",
                                        params={"kind": "docket.section"})).json()
    assert "model" in [o["section"] for o in model["observations"]]          # the docket node wrote its part


async def test_sidecar_down_degrades_to_the_in_state_docket(wm, monkeypatch):
    wm(f"http://127.0.0.1:{free_port()}")                                    # nothing listens there
    s = run_state("down")
    assert await world_model.append("down", "twins", D.twin_sections(s)) is False

    async def no_call(*_, **__):
        raise AssertionError("the client should back off instead of trying again")
    monkeypatch.setattr(world_model.http, "post", no_call)
    monkeypatch.setattr(world_model.http, "get", no_call)

    out = await docket_node.committee_docket_node(s)
    prob = compute_probability(D.build_scoring_inputs(s))
    assert (out["docket"], out["docket_index"]) == D.build_docket(s, prob)
    assert out["warnings"] == [WARNING]


async def test_unset_url_sends_nothing_and_warns_nothing(wm, monkeypatch):
    wm(None)

    async def no_call(*_, **__):
        raise AssertionError("WORLD_MODEL_URL is unset")
    monkeypatch.setattr(world_model.http, "post", no_call)
    monkeypatch.setattr(world_model.http, "get", no_call)
    out = await docket_node.committee_docket_node(run_state("off"))
    assert out["warnings"] == []


async def test_debate_turns_are_appended_but_stay_out_of_the_docket(sidecar_url, wm):
    wm(sidecar_url)
    await world_model.append("debate", "advocate", {"turn_1": {"content": "Admit."}}, kind="debate.turn")
    assert await world_model.sections("debate") == {}
    turns = (await world_model.http.get(f"{sidecar_url}/v1/run:debate/context", params={"kind": "debate.turn"})).json()
    assert [json.loads(o["payload"]) for o in turns["observations"]] == [{"content": "Admit."}]
