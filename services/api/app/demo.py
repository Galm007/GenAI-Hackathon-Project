"""Portable fictional replays and deterministic what-if; no external service calls."""
from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace

from fastapi import APIRouter, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

from .api_models import WhatIfRequest, WhatIfResponse
from .schemas.delta import Counterfactual
from .scoring.probability import ScoringInputs
from .scoring.whatif import run_what_if

DEMO_DIR = Path(__file__).resolve().parents[3] / "data/demo_runs"
MAX_GAP_S = 1.2
router = APIRouter()


def load_demo(name: str) -> dict:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name):
        raise HTTPException(404, "Replay not found")
    path = DEMO_DIR / f"{name}.json"
    if not path.is_file():
        raise HTTPException(404, "Replay not found")
    return json.loads(path.read_text())


def scoring_context(bundle: dict):
    raw = bundle.get("context")
    if not raw:
        raise HTTPException(503, "This recording has no saved scoring context")
    return SimpleNamespace(**{**raw, "scoring_inputs": ScoringInputs.model_validate(raw["scoring_inputs"]),
                              "counterfactuals": [Counterfactual.model_validate(c) for c in raw["counterfactuals"]]})


async def replay_stream(bundle: dict, speed: float, after: int, request: Request) -> AsyncIterator[dict]:
    previous = None
    for event in bundle["events"]:
        if event["seq"] <= after:
            continue
        gap = min(MAX_GAP_S, max(0, event["ts"] - previous)) / speed if previous is not None else 0
        previous = event["ts"]
        if gap:
            await asyncio.sleep(gap)
        if await request.is_disconnected():
            return
        env = {**event, "run_id": f"demo-{bundle['name']}", "ts": round(time.time(), 3)}
        yield {"id": str(env["seq"]), "event": env["event"], "data": json.dumps(env)}


@router.get("/api/demo/{name}/stream")
async def demo_stream(name: str, request: Request, speed: float = Query(1, ge=0.25, le=8),
                      after: int = Query(-1, ge=-1)):
    bundle = load_demo(name)  # validate before the streaming response commits its headers
    last_id = request.headers.get("last-event-id", "")
    if last_id.isdigit():
        after = max(after, int(last_id))
    return EventSourceResponse(replay_stream(bundle, speed, after, request), ping=15,
                               headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/api/demo/{name}")
async def demo_info(name: str):
    bundle = load_demo(name)
    return {"name": bundle["name"], "fictional": bundle.get("fictional", True),
            "provenance": bundle.get("provenance", "Recorded fictional-persona evaluation"),
            "school_slug": bundle["school_slug"], "events": len(bundle["events"])}


@router.post("/api/what-if", response_model=WhatIfResponse)
async def what_if(req: WhatIfRequest, request: Request):
    if not req.run_id.startswith("demo-"):
        # B13/B14 supplies this method; never replace a real student's inputs with demo inputs.
        lookup = getattr(request.app.state.run_manager, "scoring_context", None)
        if lookup is None:
            raise HTTPException(503, "Live scoring context is not integrated yet; use the fictional demo replay")
        context = await lookup(req.run_id)
        if context is None:
            raise HTTPException(404, "Run not found or not yet scored")
        return run_what_if(context, req)
    bundle = load_demo(req.run_id.removeprefix("demo-"))
    result = run_what_if(scoring_context(bundle), req)
    if bundle.get("fictional"):
        result.confidence = "model_estimate"
        result.warnings.append("Fictional scenario inputs; this is not evidence of real admissions accuracy.")
    return result


def register_demo_runs(runs) -> None:
    from .runs import CAPTURED, Run
    for path in DEMO_DIR.glob("*.json"):
        bundle = load_demo(path.stem)
        run = Run(run_id=f"demo-{bundle['name']}", session_id="demo", school_slug=bundle["school_slug"],
                  events=bundle["events"], done=True, status="complete", school=bundle["school"])
        run.captured = {event["event"]: event for event in run.events if event["event"] in CAPTURED}
        runs._runs[run.run_id] = run
