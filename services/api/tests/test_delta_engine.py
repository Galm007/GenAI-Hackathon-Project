"""Node 5 (§3.8.4) on the fictional fixtures, with counterfactuals, llm.parse and db.save_run mocked."""
import pytest

from app.agents.nodes import delta_engine as N
from app.agents.prompts.delta import DELTA_SYSTEM
from app.schemas.debate import DebateTurn
from app.schemas.delta import Counterfactual, DeltaReport, Pivot
from app.scoring.probability import compute_probability

from . import test_debate as T


def cf(id_: str = "cf_major_math_stats", delta_pp: float = 8.33) -> Counterfactual:
    return Counterfactual(id=id_, kind="major_switch", label="Explore math & statistics", p_new=0.42,
                          delta_pp=delta_pp, confidence="model_estimate", evidence="Major multiplier ×1.12.",
                          overrides={"major_multiplier": 1.12})


def pivot(cf_id: str | None, title: str = "Apply through math", why: str = "A wider door.") -> Pivot:
    return Pivot(counterfactual_id=cf_id, title=title, why_it_works=why, concrete_steps=["Check transfer rules"],
                 effort="days", tradeoffs="Moving into CS later is not guaranteed.")


def report(**kw) -> DeltaReport:
    return DeltaReport.model_validate(T.fixture("DeltaReport")).model_copy(update=kw)


def turn(n: int, speaker: str, rec: str | None = None) -> DebateTurn:
    return DebateTurn(turn=n, speaker=speaker, content="…", citations=[], recommendation=rec)


@pytest.fixture
def state() -> dict:
    s = T.base_state(run_id="run-1", session_id="sess-1", profile_embedding=[0.0] * 768)
    s["inputs"] = s["inputs"].model_copy(update={"transcript_pdf_b64": "JVBERi0=", "essay_text": "An essay.",
                                                 "application_deadline": "2026-11-01"})
    x = T.D.build_scoring_inputs(s)
    prob = compute_probability(x)
    docket, index = T.D.build_docket(s, prob)
    return {**s, "scoring_inputs": x, "probability": prob, "docket": docket, "docket_index": index,
            "debate": [turn(1, "advocate"), turn(2, "chair"), turn(3, "advocate"), turn(4, "chair", "LIKELY DENY")]}


# ---------- bind_report ----------
def test_bind_report_nulls_unknown_counterfactual_ids(state):
    r = report(ranked_pivots=[pivot("cf_major_math_stats"), pivot("cf_invented"), pivot(None)])
    out = N.bind_report(r, [cf()], state)
    assert [p.counterfactual_id for p in out.ranked_pivots] == ["cf_major_math_stats", None, None]


@pytest.mark.parametrize("claim", ["12%", "+8.3 pp", "-4pp", "3 percentage points", "1 Percentage Point", "50 %"])
def test_bind_report_scrubs_percentages_the_llm_wrote(state, claim):
    r = report(headline_verdict=f"Odds rise {claim} here.", major_arbitrage_note=f"Math adds {claim}.",
               ranked_pivots=[pivot("cf_major_math_stats", title=f"Gain {claim}", why=f"Worth {claim}.")])
    out = N.bind_report(r, [cf()], state)
    p = out.ranked_pivots[0]
    for text in (out.headline_verdict, out.major_arbitrage_note, p.title, p.why_it_works):
        assert "(see model)" in text and claim not in text


def test_bind_report_keeps_plain_numbers_and_untouched_fields(state):
    r = report(headline_verdict="Take 2 more APs and a 1530 SAT.", major_arbitrage_note=None,
               ranked_pivots=[pivot(None, why="Five ppl agree; the top 25 programs.")])
    out = N.bind_report(r, [], state)
    assert out.headline_verdict == "Take 2 more APs and a 1530 SAT." and out.major_arbitrage_note is None
    assert out.ranked_pivots[0].why_it_works == "Five ppl agree; the top 25 programs."
    assert (out.essay_adjustments, out.risks_to_watch, out.disclaimer) == (r.essay_adjustments, r.risks_to_watch,
                                                                         r.disclaimer)


def test_bind_report_takes_disposition_from_the_chair(state):
    r = report(committee_disposition="ADMIT")                        # the LLM's own pick is overridden
    assert N.bind_report(r, [], state).committee_disposition == "LIKELY DENY"
    no_rec = {**state, "debate": state["debate"][:3]}
    assert N.bind_report(r, [], no_rec).committee_disposition == state["probability"].disposition
    assert N.bind_report(r, [], {**state, "debate": []}).committee_disposition == state["probability"].disposition


# ---------- the node ----------
@pytest.fixture
def run_node(monkeypatch):
    calls: dict[str, list] = {"cf": [], "parse": [], "save": []}
    events: list[tuple[str, dict]] = []

    def install(cfs: list[Counterfactual], reply: DeltaReport, save_error: Exception | None = None):
        async def generate(x, **kw):
            calls["cf"].append((x, kw))
            return cfs

        async def parse(schema, **kw):
            calls["parse"].append({"schema": schema, **kw})
            return reply

        async def save_run(row):
            calls["save"].append(row)
            if save_error:
                raise save_error

        monkeypatch.setattr(N, "generate_counterfactuals", generate)
        monkeypatch.setattr(N.llm, "parse", parse)
        monkeypatch.setattr(N.db, "save_run", save_run)
        monkeypatch.setattr(N, "emit", lambda event, **d: events.append((event, d)))
        monkeypatch.setattr(N, "tool_call", lambda node, tool, status, **d: events.append(("tool_call", {
            "tool": tool, "status": status, **d})))
        return calls, events
    return install


async def test_node_binds_emits_and_persists(run_node, state):
    reply = report(ranked_pivots=[pivot("cf_major_math_stats", why="Adds 8.3 pp."), pivot("cf_nope")])
    calls, events = run_node([cf()], reply)
    out = await N.delta_engine_node(state)

    [(x, kw)] = calls["cf"]
    assert x is state["scoring_inputs"] and kw["gpa"] == state["metrics"].gpa_uw_4
    assert kw["embedding"] == state["profile_embedding"] and kw["rubric"] is state["school_rubric"]

    [p] = calls["parse"]
    assert (p["schema"], p["system"], p["effort"], p["max_tokens"]) == (DeltaReport, DELTA_SYSTEM, "medium", 8000)
    docket_block, ask = p["messages"][0]["content"]
    assert docket_block["text"] == f"<docket>\n{state['docket']}\n</docket>"
    assert "[Turn 4 — chair]" in ask["text"] and '"id":"cf_major_math_stats"' in ask["text"]
    assert '"p_new"' not in ask["text"] and '"overrides"' not in ask["text"]           # menu shows only safe fields
    assert "<application_deadline>2026-11-01</application_deadline>" in ask["text"]
    assert ask["text"].endswith("Write the final report.")

    r = out["delta_report"]
    assert [pv.counterfactual_id for pv in r.ranked_pivots] == ["cf_major_math_stats", None]
    assert r.ranked_pivots[0].why_it_works == "Adds (see model)." and r.committee_disposition == "LIKELY DENY"
    assert out["counterfactuals"] == [cf()] and out["warnings"] == []

    names = [e for e, _ in events]
    assert names == ["node_start", "tool_call", "tool_call", "counterfactuals", "final_report", "node_end"]
    assert dict(events)["final_report"]["report"] == r.model_dump()
    assert [d for e, d in events if e == "tool_call"][1]["result_count"] == 1

    [row] = calls["save"]
    assert (row["id"], row["session_id"], row["status"], row["school_slug"]) == ("run-1", "sess-1", "complete", "uiuc")
    for secret in ("transcript_pdf_b64", "resume_pdf_b64", "essay_text", "recommendation_text"):
        assert secret not in row["intake"]                                    # raw uploads are never stored
    assert row["intake"]["has_recommendations"] is False and row["intake"]["intended_major"] == "CS"
    assert row["delta_report"] == r.model_dump(mode="json") and len(row["debate"]) == 4
    assert row["probability"]["p_final"] == state["probability"].p_final and len(row["twins"]) == 5


async def test_persist_failure_becomes_a_warning(run_node, state):
    _, events = run_node([], report(), save_error=RuntimeError("supabase down"))
    out = await N.delta_engine_node({**state, "institutional_brief": None})
    assert out["warnings"] == ["persist failed: RuntimeError"] and [e for e, _ in events][-1] == "node_end"
