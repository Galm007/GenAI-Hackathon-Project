from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
import uuid
from pathlib import Path

from app.agents.graph import graph
from app.schemas.inputs import RawApplicantInputs


def _read(path: str | None) -> str | None:
    return Path(path).read_text(encoding="utf-8") if path else None


def _inputs(a: argparse.Namespace) -> RawApplicantInputs:
    """Sync file reads, kept out of the async main (ruff ASYNC240)."""
    return RawApplicantInputs(
        transcript_pdf_b64=base64.standard_b64encode(Path(a.transcript).read_bytes()).decode()
        if a.transcript else None,
        activities_text=_read(a.activities), essay_text=_read(a.essay),
        intended_major=a.major, target_schools=[a.school],
        early_round={a.school: a.round} if a.round else {},
    )


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")      # ✔/━/⚙ glyphs on a Windows console (see DECISIONS D-030)
    p = argparse.ArgumentParser()
    p.add_argument("--transcript", help="transcript PDF")
    p.add_argument("--activities", help="activities list .txt")
    p.add_argument("--essay", help="essay .txt")
    p.add_argument("--major", required=True)
    p.add_argument("--school", required=True, help="slug, e.g. uiuc")
    p.add_argument("--round", default=None, choices=["ED", "ED2", "EA", "REA", "RD"])
    a = p.parse_args()

    inputs = _inputs(a)
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}
    state = {"run_id": run_id, "session_id": "cli", "inputs": inputs, "school_slug": a.school}

    async for mode, chunk in graph.astream(state, config, stream_mode=["updates", "custom"]):
        if mode == "updates":
            for node in chunk:
                print(f"\n✔ {node}")
            continue
        ev = chunk["event"]
        if ev == "debate_turn_start":
            print(f"\n\n━━ Turn {chunk['turn']} · {chunk['speaker'].upper()} ━━")
        elif ev == "debate_token":
            print(chunk["delta"], end="", flush=True)
        elif ev == "progress":
            print(f"\n· {chunk['node']}: {chunk['message']}")
        elif ev == "tool_call":
            print(f"\n⚙ {chunk['tool']} [{chunk['status']}]")
        elif ev == "probability":
            pb = chunk["probability"]
            print(f"\n◆ P(admit) {pb['p_final']:.1%}  [{pb['p_low']:.1%} – {pb['p_high']:.1%}]  {pb['disposition']}")
        elif ev == "citation_warning":
            print(f"\n⚠ unverified citations: {chunk['refs']}")

    final = (await graph.aget_state(config)).values
    print("\n\n" + json.dumps(final["delta_report"].model_dump(), indent=2))
    for cf in final["counterfactuals"]:
        print(f"  {cf.delta_pp:+6.1f} pp  {cf.label}  ({cf.confidence})")


if __name__ == "__main__":
    asyncio.run(main())
