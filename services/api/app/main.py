from __future__ import annotations

import base64
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from .api_models import IntakeForm
from .config import settings
from .runs import RateLimited, RunManager, script_frames, sse_frames

MAX_PDF_BYTES = 10 * 1024 * 1024
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}

runs = RunManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Later steps add: fake_llm.install() (B14), register_demo_runs (B14), Supabase warm-up (B07),
    # Zetaris prewarm (B15) — plan §4.3.
    yield
    await runs.shutdown()


app = FastAPI(title="AdCom API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,           # ["http://localhost:3000", "https://adcom.vercel.app"]
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["Last-Event-ID"],
)


async def _read_pdf(f: UploadFile | None) -> str | None:
    if f is None:
        return None
    data = await f.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, f"{f.filename} exceeds 10 MB")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(415, f"{f.filename} is not a PDF")
    return base64.standard_b64encode(data).decode()       # held in memory only; never written to disk or DB


def _start_after(request: Request, after: int) -> int:
    last_id = request.headers.get("last-event-id")
    return int(last_id) if last_id and last_id.isdigit() else after


@app.post("/api/evaluate", status_code=202)
async def create_evaluation(
    request: Request,
    intake: Annotated[str, Form()],
    transcript: Annotated[UploadFile | None, File()] = None,
    resume: Annotated[UploadFile | None, File()] = None,
):
    form = IntakeForm.model_validate_json(intake)
    inputs = form.to_inputs(transcript_pdf_b64=await _read_pdf(transcript), resume_pdf_b64=await _read_pdf(resume))
    if not (inputs.transcript_pdf_b64 or inputs.activities_text or inputs.resume_text):
        raise HTTPException(422, "Upload a transcript or paste an activities list.")
    try:
        run = await runs.start(session_id=form.session_id, inputs=inputs, school_slug=form.target_schools[0])
    except RateLimited as exc:
        raise HTTPException(429, str(exc)) from exc
    return {"run_id": run.run_id, "school_slug": run.school_slug,
            "stream_url": f"/api/evaluate/{run.run_id}/stream"}


@app.get("/api/evaluate/{run_id}/stream")
async def stream_evaluation(run_id: str, request: Request, after: int = Query(-1)):
    run = runs.get(run_id)
    if run is None:
        raise HTTPException(404, "unknown or expired run")
    return EventSourceResponse(sse_frames(run, _start_after(request, after), request), ping=15,
                               headers=SSE_HEADERS)


@app.get("/api/evaluate/{run_id}")
async def get_snapshot(run_id: str):
    snap = await runs.snapshot(run_id)
    if snap is None:
        raise HTTPException(404, "unknown or expired run")
    return snap


@app.get("/api/dev/fake-stream")                   # scripted SSE for Tracks C/D (plan §6.3); delete before H33
async def fake_stream(request: Request, after: int = Query(-1), speed: float = Query(1.0, ge=0.25, le=8.0)):
    return EventSourceResponse(script_frames(_start_after(request, after), speed, request), ping=15,
                               headers=SSE_HEADERS)


@app.get("/api/health")
async def health():
    # B07/A13 add the db and zetaris probes (plan §4.3).
    return {"ok": True, "anthropic_key": bool(settings.anthropic_api_key) or settings.fake_llm,
            "tavily": bool(settings.tavily_api_key), "demo_mode": settings.demo_mode,
            "fake_llm": settings.fake_llm, "ts": time.time()}
