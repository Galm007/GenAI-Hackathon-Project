from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents import events


class S(TypedDict):
    x: int


def test_emit_is_a_noop_outside_a_graph():
    events.emit("progress", node="n1", message="hi")
    events.progress("n1", "hi", 0.5)
    events.tool_call("n2", "zetaris_sql", "started")


def test_emit_reaches_the_custom_stream_inside_a_graph():
    def node(state: S) -> S:
        events.progress("dossier", "parsing", 0.25)
        events.tool_call("institution", "web_search", "done", hits=3)
        return state

    g = StateGraph(S)
    g.add_node("n", node)
    g.add_edge(START, "n")
    g.add_edge("n", END)
    out = list(g.compile().stream({"x": 1}, stream_mode="custom"))

    assert [e["event"] for e in out] == ["progress", "tool_call"]
    assert out[0] | {"ts": 0} == {"event": "progress", "ts": 0, "node": "dossier", "message": "parsing", "pct": 0.25}
    assert out[1]["hits"] == 3 and out[1]["status"] == "done"
