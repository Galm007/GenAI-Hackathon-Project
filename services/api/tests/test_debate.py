"""Committee docket (§3.8.1–3.8.2) and debate nodes (§3.8.3) on the fictional fixtures, with the LLM mocked."""
import json
from pathlib import Path

import anthropic
import httpx
import pytest

from app import llm
from app.agents import docket as D
from app.agents.nodes import debate as N
from app.agents.nodes import docket_node
from app.agents.prompts.committee import COMMITTEE_SYSTEM, MAX_TURNS, TURN_BRIEFS
from app.schemas.dossier import ComputedMetrics, DossierGrade, ParsedDossier
from app.schemas.institution import InstitutionalBrief, SchoolRubric, WebSnippet
from app.schemas.twins import EmpiricalBaseline, TwinAnalysis, TwinCard
from app.scoring.probability import compute_probability

from .test_scoring_metrics import inputs

FIXTURES = Path(__file__).resolve().parents[3] / "data/fixtures"
SPEAKERS = [TURN_BRIEFS[t][0] for t in range(1, MAX_TURNS + 1)]


def fixture(name: str):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def base_state(**kw) -> dict:
    return {
        "school_slug": "uiuc",
        "inputs": inputs(early_round={"uiuc": "EA"}, context={"first_gen": True}),
        "dossier": ParsedDossier.model_validate(fixture("ParsedDossier")),
        "grade": DossierGrade.model_validate(fixture("DossierGrade")),
        "metrics": ComputedMetrics.model_validate(fixture("ComputedMetrics")),
        "school": {**fixture("scoring_context")["school"], "admit_rate": 0.44, "cds_year": "2024-2025"},
        "school_rubric": SchoolRubric.model_validate(fixture("SchoolRubric")),
        "institutional_brief": InstitutionalBrief.model_validate(fixture("InstitutionalBrief")),
        "web_snippets": [WebSnippet(id="W1", url="https://example.edu/cs", title="CS admissions", content="…",
                                    published=None)],
        "zetaris_queries": [
            {"id": "Z1", "purpose": "CS admit rate", "sql": "SELECT 1", "rows": [{"n": i} for i in range(12)]},
            {"id": "Z2", "purpose": "rejected by guard", "sql": "DROP TABLE x", "rows": [], "error": "rejected"},
        ],
        "twins": [TwinCard.model_validate(t) for t in fixture("TwinCard")],
        "baseline": EmpiricalBaseline.model_validate(fixture("EmpiricalBaseline")),
        "twin_analysis": TwinAnalysis.model_validate(fixture("TwinAnalysis")),
        **kw,
    }


@pytest.fixture
def events(monkeypatch):
    seen: list[tuple[str, dict]] = []
    record = lambda event, **d: seen.append((event, d))  # noqa: E731
    monkeypatch.setattr(N, "emit", record)
    monkeypatch.setattr(docket_node, "emit", record)
    return seen


@pytest.fixture
def docketed() -> dict:
    """State as the docket node leaves it (built directly, so sync tests can use it)."""
    s = base_state()
    prob = compute_probability(D.build_scoring_inputs(s))
    docket, index = D.build_docket(s, prob)
    return {**s, "probability": prob, "docket": docket, "docket_index": index, "debate_turn": 0}


# ---------- scoring inputs ----------
def test_scoring_inputs_add_context_hooks_and_pick_this_schools_round():
    s = base_state()
    x = D.build_scoring_inputs(s)
    assert "first_gen" in x.hooks and "low_income" not in x.hooks and x.hooks == tuple(sorted(x.hooks))
    assert x.early_round == "EA" and x.applicant_interest_weight == 0.0          # C7 "not_considered"
    assert x.ratings["academic"] == s["grade"].harvard.academic.numeric
    assert (x.twin_sum_w, x.odds_inflation) == (s["baseline"].sum_w, s["baseline"].odds_inflation)
    assert D.build_scoring_inputs(base_state(school_slug="mit")).early_round is None


# ---------- docket ----------
async def test_docket_node_emits_probability_and_resets_the_turn_counter(events, docketed):
    out = await docket_node.committee_docket_node(base_state())
    assert (out["docket"], out["docket_index"]) == (docketed["docket"], docketed["docket_index"])
    assert out["probability"] == compute_probability(out["scoring_inputs"]) and out["debate_turn"] == 0
    assert events == [("probability", {"probability": out["probability"].model_dump(),
                                       "scoring_inputs": out["scoring_inputs"].model_dump()})]


def test_docket_is_byte_stable_and_drops_errored_queries():
    s = base_state()
    prob = compute_probability(D.build_scoring_inputs(s))
    docket, index = D.build_docket(s, prob)
    # same facts, dict keys inserted in a different order → same bytes (sorted keys)
    shuffled = base_state(school=dict(reversed(list(s["school"].items()))))
    assert D.build_docket(shuffled, prob) == (docket, index)

    packet = json.loads(docket)
    assert [q["id"] for q in packet["zetaris_queries"]] == ["Z1"] and len(packet["zetaris_queries"][0]["rows"]) == 8
    assert "sum_w" not in packet["twin_baseline"] and len(packet["applicant"]["essay"]) <= D.ESSAY_CHARS
    assert packet["model"]["disposition"] == prob.disposition
    assert index["sql"] == ["Z1"] and index["web"] == ["W1"] and index["twin"] == ["1", "2", "3", "4", "5"]
    assert "major.computer_science" in index["cds"] and "c7.rigor" in index["cds"]
    assert "twins" in index["model"] and "disposition" in index["model"]


def test_docket_without_brief_or_research_still_builds():
    s = base_state(institutional_brief=None, twin_analysis=None)
    del s["web_snippets"], s["zetaris_queries"]
    docket, index = D.build_docket(s, compute_probability(D.build_scoring_inputs(s)))
    packet = json.loads(docket)
    assert packet["fact_checks"] == [] and packet["twin_analysis"] is None and packet["zetaris_queries"] == []
    assert index["sql"] == [] and index["web"] == []


# ---------- citation validator ----------
@pytest.mark.parametrize(("cite", "valid"), [
    ("[[sql:Z1]]", True),
    ("[[sql:Z2]]", False),                      # errored query: not in the docket, not citable
    ("[[sql:Z9]]", False),
    ("[[web:W1]]", True), ("[[web:W4]]", False),
    ("[[twin:3]]", True), ("[[twin:6]]", False),
    ("[[cds:major.computer_science]]", True), ("[[cds:major.math_stats]]", False),
    ("[[cds:c7.rigor]]", True), ("[[cds:c7.made_up]]", False), ("[[cds:sat_75]]", True),
    ("[[model:p_final]]", True), ("[[model:twins]]", True), ("[[model:p_secret]]", False),
    ("[[dossier:activities.2]]", True), ("[[dossier:activities.2.description]]", True),
    ("[[dossier:activities.7]]", False), ("[[dossier:awards.1]]", True), ("[[dossier:awards.2]]", False),
    ("[[dossier:metrics.gpa_uw_4]]", True), ("[[dossier:essay]]", True), ("[[dossier:ssn]]", False),
])
def test_validate_citations(docketed, cite, valid):
    [c] = D.validate_citations(f"Strong file {cite}.", docketed["docket_index"])
    assert c.valid is valid and f"[[{c.kind}:{c.ref}]]" == cite and c.span == (12, 12 + len(cite))


def test_validator_ignores_malformed_forms(docketed):
    text = "[[sql: Z1]] [[foo:bar]] [sql:Z1] [[sql:Z1]][[twin:1]]"
    assert [(c.kind, c.ref) for c in D.validate_citations(text, docketed["docket_index"])] == [
        ("sql", "Z1"), ("twin", "1")]


def test_every_example_citation_in_the_system_prompt_parses():
    kinds = {m.group(1) for m in D.CITATION_RE.finditer(COMMITTEE_SYSTEM)}
    assert kinds == {"dossier", "cds", "twin", "web", "model", "sql"}


# ---------- debate nodes ----------
def install_stream(monkeypatch, replies):
    calls: list[dict] = []
    replies = iter(replies)

    async def stream_text(**kw):
        calls.append(kw)
        reply = next(replies)
        if isinstance(reply, Exception):
            raise reply
        for chunk in (reply[: len(reply) // 2], reply[len(reply) // 2:]):
            kw["on_text"](chunk)
        return reply

    monkeypatch.setattr(N.llm, "stream_text", stream_text)
    return calls


async def run_debate(state: dict) -> dict:
    nodes = {sp: N.make_debate_node(sp) for sp in ("advocate", "chair")}
    for speaker in SPEAKERS:
        out = await nodes[speaker](state)
        state = {**state, "debate": state.get("debate", []) + out["debate"], "debate_turn": out["debate_turn"]}
    return state


async def test_four_turns_share_identical_docket_bytes_and_parse_the_recommendation(monkeypatch, docketed, events):
    replies = ["Spike [[dossier:spike]] and [[sql:Z1]].", "Bottleneck [[cds:major.computer_science]]?",
               "Twin [[twin:2]] answers it.", "We land at waitlist [[model:disposition]].\nRECOMMENDATION: WAITLIST"]
    calls = install_stream(monkeypatch, replies)
    s = await run_debate(docketed)

    docket_blocks = [c["messages"][0]["content"][0] for c in calls]
    assert len({b["text"] for b in docket_blocks}) == 1                                  # byte-identical
    assert all(b["cache_control"] == {"type": "ephemeral"} for b in docket_blocks)
    assert docket_blocks[0]["text"] == f"<docket>\n{docketed['docket']}\n</docket>"
    assert all((c["system"], c["effort"], c["max_tokens"]) == (COMMITTEE_SYSTEM, "low", 4000) for c in calls)

    tails = [c["messages"][0]["content"][1]["text"] for c in calls]
    assert "(The discussion has not started.)" in tails[0] and tails[0].endswith(TURN_BRIEFS[1][1])
    assert "[Turn 1 — Regional Admissions Officer (Advocate)]\nSpike" in tails[1]
    assert "[Turn 3 — Regional Admissions Officer (Advocate)]" in tails[3] and tails[3].endswith(TURN_BRIEFS[4][1])

    turns = s["debate"]
    assert [(t.turn, t.speaker) for t in turns] == list(enumerate(SPEAKERS, 1)) and s["debate_turn"] == MAX_TURNS
    assert [t.recommendation for t in turns] == [None, None, None, "WAITLIST"] and not any(t.degraded for t in turns)
    assert all(c.valid for t in turns for c in t.citations)

    names = [e for e, _ in events]
    assert names[:4] == ["debate_turn_start", "debate_token", "debate_token", "debate_turn_end"]
    assert "citation_warning" not in names and names.count("debate_turn_end") == MAX_TURNS
    end = [d for e, d in events if e == "debate_turn_end"][-1]
    assert end["recommendation"] == "WAITLIST" and end["content"] == replies[-1]
    assert N.route_debate(s) == "delta_engine" and N.route_debate({**s, "debate_turn": 2}) == "advocate"


async def test_bad_citations_warn_and_a_missing_recommendation_defaults_to_the_model(monkeypatch, docketed, events):
    install_stream(monkeypatch, ["[[twin:9]] and [[sql:Z2]]", "ok", "ok", "No closing line [[web:W1]]."])
    s = await run_debate(docketed)
    assert ("citation_warning", {"turn": 1, "refs": ["twin:9", "sql:Z2"]}) in events
    assert [c.valid for c in s["debate"][0].citations] == [False, False]
    assert s["debate"][-1].recommendation == docketed["probability"].disposition


@pytest.mark.parametrize("error", [
    llm.LLMRefusal("debate turn refused"),
    anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")),
    llm.LLMQuotaExhausted("gemini daily quota used up"),
], ids=["refusal", "api_error", "quota"])
async def test_fallback_turns_are_degraded_grounded_and_cited(monkeypatch, docketed, events, error):
    install_stream(monkeypatch, [error] * MAX_TURNS)
    s = await run_debate(docketed)
    turns = s["debate"]
    assert all(t.degraded for t in turns) and "citation_warning" not in [e for e, _ in events]
    assert all(t.citations and all(c.valid for c in t.citations) for t in turns)     # template cites real keys
    p, b = docketed["probability"], docketed["baseline"]
    assert f"{b.n_accepted} of the closest" in turns[0].content and f"{b.n_rejected} of the closest" in turns[1].content
    assert turns[0].content == turns[2].content == N.fallback_turn(1, "advocate", docketed)
    assert turns[-1].content.endswith(f"RECOMMENDATION: {p.disposition}") and turns[-1].recommendation == p.disposition

    first = [(e, d) for e, d in events if d.get("turn") == 1]
    assert [e for e, _ in first] == ["debate_turn_start", "debate_reset", "debate_token", "debate_turn_end"]
    assert first[2][1]["delta"] == turns[0].content            # the UI gets the whole template in one token


async def test_a_node_refuses_a_turn_that_belongs_to_the_other_speaker(docketed):
    with pytest.raises(AssertionError, match="turn 1 belongs to advocate"):
        await N.make_debate_node("chair")(docketed)
    assert N.make_debate_node("chair").__name__ == "chair_node"


def test_rec_re_takes_only_a_final_line():
    assert N.REC_RE.search("x\nRECOMMENDATION: LIKELY DENY  ").group(1) == "LIKELY DENY"
    assert N.REC_RE.search("RECOMMENDATION: ADMIT, probably") is None
