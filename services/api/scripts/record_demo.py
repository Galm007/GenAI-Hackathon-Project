"""Save a completed evaluation of a fictional persona for a portable demo replay.

uv run python -m scripts.record_demo RUN_ID NAME --fictional
Requires B13's saved event log and a configured team database. Makes no LLM calls.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

from app import db

OUT = Path(__file__).resolve().parents[3] / "data/demo_runs"


def without_reset_text(events: list[dict]) -> list[dict]:
    """A lane that leaks its reasoning is corrected live with `debate_reset`. A replay should show only the final text,
    so drop each turn's tokens that came before its last reset and the resets themselves, then renumber `seq`."""
    last_reset = {e["turn"]: i for i, e in enumerate(events) if e["event"] == "debate_reset"}
    leaked = lambda i, e: e["event"] == "debate_token" and i < last_reset.get(e["turn"], -1)  # noqa: E731
    kept = [e for i, e in enumerate(events) if e["event"] != "debate_reset" and not leaked(i, e)]
    return [e | {"seq": n} for n, e in enumerate(kept)]


async def record(run_id: str, name: str, *, fictional: bool) -> Path:
    if not fictional or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name):
        raise ValueError("Use a safe replay name and confirm that the applicant is fictional")
    row = await db.load_run(run_id)
    if not row or row.get("status") != "complete" or not row.get("event_log"):
        raise ValueError("A completed, persisted run is required")
    events = row["event_log"]
    if events[-1]["event"] != "done" or events[-1].get("status") != "complete":
        raise ValueError("The saved stream must end with a successful done event")
    if [e["seq"] for e in events] != list(range(len(events))):
        raise ValueError("The saved event log is incomplete")
    events = without_reset_text(events)
    by = {e["event"]: e for e in events}
    school = await db.get_school(row["school_slug"])
    if not school:
        raise ValueError("The school's saved data is required")
    grade = by["scorecard"]["grade"]
    context = {"scoring_inputs": by["probability"]["scoring_inputs"], "school": school,
               "major_category": grade["major_category"], "tiers": [a["tier"] for a in grade["activity_grades"]],
               "has_recommendations": row.get("has_recommendations", False),
               "counterfactuals": by.get("counterfactuals", {}).get("counterfactuals", [])}
    target = OUT / f"{name}.json"
    if target.exists():
        raise ValueError("That recording already exists; choose another name to preserve it")
    OUT.mkdir(parents=True, exist_ok=True)
    bundle = {"name": name, "school_slug": row["school_slug"], "school": school, "events": events,
              "context": context, "fictional": True, "provenance": "Recorded completed run of a fictional persona"}
    target.write_text(json.dumps(bundle, indent=2) + "\n")
    return target


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("name")
    parser.add_argument("--fictional", action="store_true", required=True)
    args = parser.parse_args()
    path = await record(args.run_id, args.name, fictional=args.fictional)
    print(f"Saved fictional-persona recording: {path.name}. Review for secrets before committing.")


if __name__ == "__main__":
    asyncio.run(main())
