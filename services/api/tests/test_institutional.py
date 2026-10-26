"""Node 2 (§3.7.2) and its Zetaris SQL tool loop (§2.10.7), with the Anthropic client, Zetaris and Tavily mocked."""
import asyncio
from datetime import date
from types import SimpleNamespace

import anthropic
import httpx
import pytest

from app import llm
from app.agents import zetaris_tool as Z
from app.agents.nodes import institutional as N
from app.agents.prompts.institutional import INSTITUTIONAL_SYSTEM
from app.schemas.institution import FactCheck, InstitutionalBrief, Priority, WebSnippet
from app.zetaris import ZetarisError

from . import test_debate as T
from .test_scoring_rubric import school

GOOD_SQL = "SELECT n FROM ADCOM.v_major_stats WHERE slug = 'uiuc' AND major_category = 'computer_science'"


# ---------- fake Anthropic responses ----------
def use(i: int, sql: str = GOOD_SQL, purpose: str = "CS sample size") -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=f"toolu_{i}", name="zetaris_sql", input={"sql": sql, "purpose": purpose})


def reply(*blocks, stop: str = "tool_use") -> SimpleNamespace:
    return SimpleNamespace(stop_reason=stop, content=list(blocks))


def done(text: str = "Summary.") -> SimpleNamespace:
    return reply(SimpleNamespace(type="text", text=text), stop="end_turn")


@pytest.fixture
def loop(monkeypatch):
    """Scripts the model's replies and Zetaris's rows; records requests, queries and tool-ticker events."""
    seen: dict[str, list] = {"requests": [], "queries": [], "ticker": []}

    def install(*replies, rows=None, zetaris_error: str | None = None):
        replies = iter(replies)

        async def create(**kw):
            seen["requests"].append({**kw, "messages": list(kw["messages"])})   # snapshot: the loop mutates it
            return next(replies)

        async def query(sql, **kw):
            seen["queries"].append((sql, kw))
            if zetaris_error:
                raise ZetarisError(zetaris_error)
            return rows if rows is not None else [{"n": "42"}]

        monkeypatch.setattr(Z.llm, "client", SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(
            create=create))))
        monkeypatch.setattr(Z.zetaris_repo.zetaris, "query", query)
        monkeypatch.setattr(Z, "tool_call", lambda node, tool, status, **d: seen["ticker"].append((status, d)))
        return seen
    return install


def research():
    return Z.run_zetaris_research(slug="uiuc", major_category="computer_science", applicant_summary='{"a": 1}')


def tool_results(request: dict) -> list[dict]:
    return request["messages"][-1]["content"]


# ---------- the tool loop ----------
async def test_loop_request_shape_and_one_finding(loop):
    seen = loop(reply(use(1)), done())
    findings = await research()

    assert findings == [{"id": "Z1", "purpose": "CS sample size", "rows": [{"n": "42"}], "error": None,
                         "sql": f"SELECT * FROM ({GOOD_SQL}) q LIMIT 50"}]          # guard added the LIMIT
    first = seen["requests"][0]
    assert first["tools"] == [Z.ZETARIS_SQL_TOOL] and Z.ZETARIS_SQL_TOOL["strict"] is True
    assert "tool_choice" not in first                                     # Opus 5.5 rejects forced tool use
    assert (first["model"], first["output_config"], first["fallbacks"]) == ("claude-opus-5-5", {"effort": "low"},
                                                                           "default")
    assert first["betas"] == [llm.FALLBACK_BETA] and first["system"] == llm.cached_system(Z.INSTITUTIONAL_SQL_SYSTEM)
    assert "'uiuc'" in first["messages"][0]["content"] and "'computer_science'" in first["messages"][0]["content"]
    assert seen["queries"][0][1] == {"page_limit": 50}

    [result] = tool_results(seen["requests"][1])
    assert result == {"type": "tool_result", "tool_use_id": "toolu_1", "content": '[{"n": "42"}]'}
    assert seen["requests"][1]["messages"][1] == {"role": "assistant", "content": [use(1)]}
    assert [s for s, _ in seen["ticker"]] == ["started", "done"] and seen["ticker"][1][1]["result_count"] == 1


async def test_budget_of_three_queries(loop):
    seen = loop(reply(use(1), use(2)), reply(use(3), use(4)), done())
    findings = await research()
    assert [f["id"] for f in findings] == ["Z1", "Z2", "Z3"] and len(seen["queries"]) == 3

    second = tool_results(seen["requests"][1])                            # both results in ONE user message
    assert [r["tool_use_id"] for r in second] == ["toolu_1", "toolu_2"] and not any("is_error" in r for r in second)
    over = tool_results(seen["requests"][2])
    assert over[0]["tool_use_id"] == "toolu_3" and "is_error" not in over[0]
    assert over[1] == {"type": "tool_result", "tool_use_id": "toolu_4", "is_error": True,
                       "content": "Query budget used up. Summarize what you found."}


async def test_loop_stops_after_max_queries_plus_one_calls(loop):
    seen = loop(*(reply(use(i)) for i in range(1, 10)))                   # a model that never stops calling
    findings = await research()
    assert len(seen["requests"]) == Z.MAX_QUERIES + 1 and len(findings) == Z.MAX_QUERIES


@pytest.mark.parametrize("bad_sql", [
    "DROP TABLE ADCOM.v_major_stats",
    "SELECT * FROM ADCOM_LAKE.gold.school_profile",                       # not a listed view
    "SELECT 1 FROM ADCOM.v_major_stats; SELECT 2 FROM ADCOM.v_major_stats",
])
async def test_rejected_sql_is_an_error_result_and_not_evidence(loop, bad_sql):
    seen = loop(reply(use(1, sql=bad_sql)), reply(use(2)), done())
    findings = await research()

    [rejected] = tool_results(seen["requests"][1])
    assert rejected["is_error"] is True and rejected["content"].startswith("Query rejected: ")
    assert [q for q, _ in seen["queries"]] == [f"SELECT * FROM ({GOOD_SQL}) q LIMIT 50"]   # never reached Zetaris
    assert [f["id"] for f in findings] == ["Z1"] and findings[0]["purpose"] == "CS sample size"
    assert [s for s, _ in seen["ticker"]] == ["started", "failed", "started", "done"]


async def test_zetaris_failure_is_an_error_result(loop):
    seen = loop(reply(use(1)), done(), zetaris_error="502 from Lightning")
    assert await research() == []
    [r] = tool_results(seen["requests"][1])
    assert r["is_error"] is True and "502 from Lightning" in r["content"]
    assert seen["ticker"][-1] == ("failed", {"id": "Z1", "error": "502 from Lightning"})


async def test_rows_are_capped_for_the_model_and_the_docket(loop):
    seen = loop(reply(use(1)), done(), rows=[{"n": str(i)} for i in range(50)])
    [f] = await research()
    assert len(f["rows"]) == 20 and tool_results(seen["requests"][1])[0]["content"].count('"n"') == 50


async def test_refusal_raises(loop):
    loop(reply(stop="refusal"))
    with pytest.raises(llm.LLMRefusal):
        await research()


# ---------- node helpers ----------
@pytest.mark.parametrize(("today", "year"), [(date(2026, 10, 25), 2027), (date(2026, 6, 30), 2026),
                                             (date(2026, 7, 1), 2027)])
def test_upcoming_matriculation_year(today, year):
    assert N.upcoming_matriculation_year(today) == year


def brief(**kw) -> InstitutionalBrief:
    return InstitutionalBrief.model_validate(T.fixture("InstitutionalBrief")).model_copy(update=kw)


def test_drop_unsourced_keeps_only_known_ids():
    b = brief(
        strategic_priorities=[Priority(claim="a", source_ids=["W1", "W9"], relevance_to_applicant="strong"),
                              Priority(claim="b", source_ids=["W9"], relevance_to_applicant="some"),
                              Priority(claim="c", source_ids=["Z1"], relevance_to_applicant="some")],
        fact_checks=[FactCheck(field="test_policy", db_value="optional", web_value="blind", verdict="updated",
                               source_ids=["W7"], note=""),
                     FactCheck(field="admit_rate", db_value="0.44", web_value="0.43", verdict="confirmed",
                               source_ids=["Z1", "W8"], note="")])
    out = N._drop_unsourced(b, {"W1", "Z1"})
    assert [(p.claim, p.source_ids) for p in out.strategic_priorities] == [("a", ["W1"]), ("c", ["Z1"])]
    assert [(fc.verdict, fc.source_ids) for fc in out.fact_checks] == [("unverified", []), ("confirmed", ["Z1"])]


# ---------- the node ----------
@pytest.fixture
def node(monkeypatch):
    calls: dict[str, list] = {"parse": [], "research": [], "web": []}
    events: list[tuple[str, dict]] = []

    def install(*, zetaris_enabled=True, findings=None, research_error=None, parse_result=None, parse_error=None,
                snippets=None):
        async def profile(slug):
            return school(data_source="zetaris", cds_year="2024-2025", c7_source="cds")

        async def run_research(**kw):
            calls["research"].append(kw)
            if research_error:
                raise research_error
            return findings or []

        async def web(sch, major_label, cycle):
            calls["web"].append((sch["slug"], major_label, cycle))
            return snippets or []

        async def parse(schema, **kw):
            calls["parse"].append({"schema": schema, **kw})
            if parse_error:
                raise parse_error
            return parse_result or brief()

        monkeypatch.setattr(N.settings, "zetaris_enabled", zetaris_enabled)
        monkeypatch.setattr(N.zetaris_repo, "school_profile", profile)
        monkeypatch.setattr(N, "run_zetaris_research", run_research)
        monkeypatch.setattr(N, "research_school", web)
        monkeypatch.setattr(N.llm, "parse", parse)
        monkeypatch.setattr(N, "emit", lambda event, **d: events.append((event, d)))
        monkeypatch.setattr(N, "tool_call", lambda node, tool, status, **d: events.append(("tool_call", {
            "tool": tool, "status": status, **d})))
        return calls, events
    return install


def node_state() -> dict:
    s = T.base_state()
    return {k: s[k] for k in ("school_slug", "inputs", "grade", "dossier")}


ZQ = [{"id": "Z1", "purpose": "CS sample size", "sql": "SELECT …", "rows": [{"n": "42"}], "error": None}]
SNIPPETS = [WebSnippet(id="W1", url="https://admissions.illinois.edu", title="Admissions", content="Test-optional.",
                       published=None)]


async def test_node_runs_research_and_brief_and_emits_in_order(node):
    calls, events = node(findings=ZQ, snippets=SNIPPETS)
    out = await N.institutional_node(node_state())

    assert out["zetaris_queries"] == ZQ and out["web_snippets"] == SNIPPETS and out["warnings"] == []
    assert out["school"]["data_source"] == "zetaris" and out["institutional_brief"] is not None
    assert calls["web"] == [("uiuc", "computer science", N.upcoming_matriculation_year())]
    assert calls["research"][0]["slug"] == "uiuc" and calls["research"][0]["major_category"] == "computer_science"

    [p] = calls["parse"]
    assert (p["schema"], p["system"], p["effort"], p["max_tokens"]) == (InstitutionalBrief, INSTITUTIONAL_SYSTEM,
                                                                        "medium", 12000)
    text = p["messages"][0]["content"][0]["text"]
    assert "[Z1] purpose: CS sample size\nSQL: SELECT …\nrows: [{\"n\":\"42\"}]" in text
    assert "[W1] Admissions\nURL: https://admissions.illinois.edu" in text
    assert text.endswith("Write the institutional brief.")
    assert '"data_source":"zetaris"' in text and "<applicant_summary>" in text

    names = [e for e, _ in events]
    assert names == ["node_start", "tool_call", "tool_call", "school_rubric", "fact_checks", "school_rubric",
                     "node_end"]
    assert [d["stage"] for e, d in events if e == "school_rubric"] == ["cds", "fact_checked"]
    assert dict(events)["fact_checks"]["zetaris_queries"] == ZQ


async def test_zetaris_disabled_skips_the_sql_loop(node):
    calls, _ = node(zetaris_enabled=False)
    out = await N.institutional_node(node_state())
    assert calls["research"] == [] and out["zetaris_queries"] == [] and out["warnings"] == []
    assert "(no Zetaris queries ran)" in calls["parse"][0]["messages"][0]["content"][0]["text"]


@pytest.mark.parametrize("error", [
    TimeoutError(), llm.LLMRefusal("zetaris research refused"),
    anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")),
    llm.LLMUnavailable("gemini unreachable"),
], ids=["timeout", "refusal", "api_error", "unavailable"])
async def test_zetaris_failure_degrades_but_the_brief_still_runs(node, error):
    calls, _ = node(research_error=error)
    out = await N.institutional_node(node_state())
    assert out["warnings"] == [f"zetaris research degraded: {type(error).__name__}"]
    assert out["zetaris_queries"] == [] and out["institutional_brief"] is not None and len(calls["parse"]) == 1


async def test_zetaris_loop_is_time_boxed(node, monkeypatch):
    node()

    async def slow(**_):
        await asyncio.sleep(5)

    monkeypatch.setattr(N, "run_zetaris_research", slow)
    monkeypatch.setattr(N, "ZETARIS_BUDGET_S", 0.01)
    out = await N.institutional_node(node_state())
    assert out["warnings"] == ["zetaris research degraded: TimeoutError"]


async def test_brief_failure_falls_back_to_cds_only(node):
    _, events = node(findings=ZQ, parse_error=llm.LLMTruncated("InstitutionalBrief hit max_tokens=12000"))
    out = await N.institutional_node(node_state())
    assert out["institutional_brief"] is None and out["warnings"] == ["institutional research degraded: LLMTruncated"]
    assert ("error", {"node": "institutional", "message": "Live fact-check unavailable — using Common Data Set only.",
                      "recoverable": True}) in events
    assert dict(events)["fact_checks"]["brief"] is None


async def test_brief_adjustments_apply_after_fact_checking(node):
    updated = brief(current_test_policy="blind", fact_checks=[FactCheck(
        field="test_policy", db_value="optional", web_value="blind", verdict="updated", source_ids=["W1"], note="")])
    node(snippets=SNIPPETS, parse_result=updated)
    out = await N.institutional_node(node_state())
    assert out["school_rubric"].test_policy == "blind" and out["school_rubric"].test_weight == 0.0
