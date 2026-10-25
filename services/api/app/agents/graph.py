from __future__ import annotations

import anthropic
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from .nodes.debate import make_debate_node, route_debate
from .nodes.delta_engine import delta_engine_node
from .nodes.docket_node import committee_docket_node
from .nodes.dossier_parser import dossier_parser_node
from .nodes.institutional import institutional_node
from .nodes.twins import twins_node
from .state import AdComState

# The SDK already retries 429/5xx/connection errors 4×; this is a second, node-level safety net.
# Not applied to debate nodes: tokens already streamed to the browser can't be un-sent.
LLM_RETRY = RetryPolicy(
    max_attempts=2,
    retry_on=(anthropic.APIConnectionError, anthropic.InternalServerError, anthropic.RateLimitError),
)
DOSSIER_KEYS = ("dossier", "grade", "metrics", "profile_embedding")


def route_entry(state: AdComState) -> str | list[str]:
    """Skip Node 1 when the dossier is already parsed (second target school, what-if re-run, demo cache)."""
    if all(state.get(k) is not None for k in DOSSIER_KEYS):
        return ["institutional", "twins"]
    return "dossier_parser"


def build_graph(checkpointer=None):
    g = StateGraph(AdComState)

    g.add_node("dossier_parser", dossier_parser_node, retry_policy=LLM_RETRY)
    g.add_node("institutional", institutional_node, retry_policy=LLM_RETRY)
    g.add_node("twins", twins_node, retry_policy=LLM_RETRY)
    g.add_node("committee_docket", committee_docket_node)
    g.add_node("advocate", make_debate_node("advocate"))
    g.add_node("chair", make_debate_node("chair"))
    g.add_node("delta_engine", delta_engine_node, retry_policy=LLM_RETRY)

    g.add_conditional_edges(START, route_entry, ["dossier_parser", "institutional", "twins"])
    g.add_edge("dossier_parser", "institutional")                      # fan-out
    g.add_edge("dossier_parser", "twins")
    g.add_edge(["institutional", "twins"], "committee_docket")          # fan-in: waits for BOTH
    g.add_edge("committee_docket", "advocate")
    g.add_edge("advocate", "chair")
    g.add_conditional_edges("chair", route_debate, ["advocate", "delta_engine"])   # the debate cycle
    g.add_edge("delta_engine", END)

    return g.compile(checkpointer=checkpointer or InMemorySaver())


graph = build_graph()
