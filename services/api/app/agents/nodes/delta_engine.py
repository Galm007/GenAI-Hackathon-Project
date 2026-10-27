from __future__ import annotations

import re
import time

import orjson

from app import db, llm
from app.schemas.delta import Counterfactual, DeltaReport
from app.scoring.counterfactuals import generate_counterfactuals

from ..events import emit, tool_call
from ..prompts.delta import DELTA_SYSTEM
from ..state import AdComState

NODE = "delta_engine"
NUMBER_CLAIM = re.compile(r"[+\-]?\d+(\.\d+)?\s?(%|pp\b|percentage points?)", re.IGNORECASE)


def _scrub(text: str) -> str:
    """Belt and braces: strip any percentage the LLM wrote anyway; the UI shows computed numbers."""
    return NUMBER_CLAIM.sub("(see model)", text)


def bind_report(report: DeltaReport, cfs: list[Counterfactual], state: AdComState) -> DeltaReport:
    known = {c.id for c in cfs}
    pivots = [p.model_copy(update={
        "counterfactual_id": p.counterfactual_id if p.counterfactual_id in known else None,
        "why_it_works": _scrub(p.why_it_works),
        "title": _scrub(p.title),
    }) for p in report.ranked_pivots]
    chair = next((t.recommendation for t in reversed(state.get("debate", [])) if t.recommendation), None)
    return report.model_copy(update={
        "ranked_pivots": pivots,
        "committee_disposition": chair or state["probability"].disposition,
        "headline_verdict": _scrub(report.headline_verdict),
        "major_arbitrage_note": _scrub(report.major_arbitrage_note) if report.major_arbitrage_note else None,
    })


async def _persist(state: AdComState, cfs: list[Counterfactual], report: DeltaReport) -> None:
    dump = lambda v: v.model_dump(mode="json") if hasattr(v, "model_dump") else v  # noqa: E731
    await db.save_run({
        "id": state["run_id"], "session_id": state["session_id"], "status": "complete",
        "school_slug": state["school_slug"], "intended_major": state["inputs"].intended_major,
        "major_category": state["grade"].major_category,
        "intake": state["inputs"].model_dump(mode="json", exclude={"transcript_pdf_b64", "resume_pdf_b64",
                                                                  "essay_text", "recommendation_text"})
                  | {"has_recommendations": bool(state["inputs"].recommendation_text)},
        **{k: dump(state.get(k)) for k in ("dossier", "grade", "metrics", "school_rubric", "institutional_brief",
                                           "baseline", "twin_analysis", "probability", "scoring_inputs")},
        "twins": [t.model_dump(mode="json") for t in state["twins"]],
        "debate": [t.model_dump(mode="json") for t in state.get("debate", [])],
        "counterfactuals": [c.model_dump(mode="json") for c in cfs],
        "delta_report": report.model_dump(mode="json"),
        "profile_embedding": state["profile_embedding"],
    })


async def delta_engine_node(state: AdComState) -> dict:
    t0 = time.perf_counter()
    emit("node_start", node=NODE, label="Actionable Delta & Major Arbitrage")
    x = state["scoring_inputs"]

    tool_call(NODE, "rpc.major_arbitrage_candidates", "started", school=state["school_slug"])
    cfs = await generate_counterfactuals(
        x, rubric=state["school_rubric"], grade=state["grade"], dossier=state["dossier"],
        school=state["school"], embedding=state["profile_embedding"], gpa=state["metrics"].gpa_uw_4,
    )
    tool_call(NODE, "rpc.major_arbitrage_candidates", "done", result_count=len(cfs))
    emit("counterfactuals", counterfactuals=[c.model_dump() for c in cfs])

    menu = [c.model_dump(include={"id", "kind", "label", "delta_pp", "confidence", "evidence"}) for c in cfs]
    transcript = "\n\n".join(f"[Turn {t.turn} — {t.speaker}]\n{t.content}" for t in state.get("debate", []))
    report = await llm.parse(
        DeltaReport, system=DELTA_SYSTEM,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": f"<docket>\n{state['docket']}\n</docket>"},
            {"type": "text", "text": (
                f"<transcript>\n{transcript}\n</transcript>\n\n"
                f"<counterfactual_menu>\n{orjson.dumps(menu).decode()}\n</counterfactual_menu>\n\n"
                f"<application_deadline>{state['inputs'].application_deadline or 'unknown'}</application_deadline>\n\n"
                "Write the final report."
            )},
        ]}],
        effort="medium", max_tokens=8000,
    )
    report = bind_report(report, cfs, state)
    emit("final_report", report=report.model_dump())

    warnings: list[str] = []
    try:
        await _persist(state, cfs, report)
    except Exception as exc:          # persistence must never break the demo
        warnings.append(f"persist failed: {type(exc).__name__}")
    emit("node_end", node=NODE, elapsed_ms=int((time.perf_counter() - t0) * 1000))
    return {"counterfactuals": cfs, "delta_report": report, "warnings": warnings}
