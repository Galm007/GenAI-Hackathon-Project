from __future__ import annotations

import asyncio
import base64
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from . import db, llm, meterless_health, zetaris_repo
from .api_models import IntakeForm
from .config import settings
from .demo import register_demo_runs
from .demo import router as demo_router
from .runs import RateLimited, RunManager, script_frames, sse_frames
from .zetaris import zetaris

log = logging.getLogger("main")
MAX_PDF_BYTES = 10 * 1024 * 1024
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}

runs = RunManager()


async def prewarm() -> None:
    """First Spark query after a restart is the slow one: pay it before the judges arrive (plan §4.3)."""
    try:
        await db.sb()                          # warm the Supabase client
    except Exception:
        log.warning("supabase warm-up failed")
    if not settings.zetaris_enabled:
        return
    for slug in settings.prewarm_schools:
        try:
            await zetaris_repo.school_profile(slug)
            await zetaris_repo.reddit_calibration(slug)
            await zetaris_repo.admitted_medians(slug)
        except Exception:
            log.warning("prewarm failed for %s", slug)


@asynccontextmanager
async def lifespan(app: FastAPI):
    restore = None
    register_demo_runs(runs)                   # recorded runs work even with DB/API offline (§4.8)
    if settings.fake_llm:
        from .fake_llm import install
        restore = install()                    # offline dev: fixtures instead of model calls (§4.9)
    discovery = asyncio.create_task(meterless_health.startup_check())
    warm = asyncio.create_task(prewarm())      # in the background, so a missing Zetaris never delays startup (D-036)
    try:
        yield
    finally:
        warm.cancel()
        discovery.cancel()
        if restore:
            restore()
        await runs.shutdown()
        await zetaris.aclose()


app = FastAPI(title="AdCom API", version="0.1.0", lifespan=lifespan)
app.state.run_manager = runs
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,           # ["http://localhost:3000", "https://adcom.vercel.app"]
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["Last-Event-ID"],
)
app.include_router(demo_router)


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


@app.post("/api/evaluate/{run_id}/schools/{slug}", status_code=202)
async def evaluate_another_school(run_id: str, slug: str):
    parent = runs.get(run_id)
    if parent is None or parent.final is None:
        raise HTTPException(409, "parent run must be complete before evaluating another school")
    try:
        child = await runs.start_child(parent, slug)
    except RateLimited as exc:
        raise HTTPException(429, str(exc)) from exc
    return {"run_id": child.run_id, "school_slug": slug, "stream_url": f"/api/evaluate/{child.run_id}/stream"}


@app.get("/api/evaluate/{run_id}")
async def get_snapshot(run_id: str):
    snap = await runs.snapshot(run_id)
    if snap is None:
        raise HTTPException(404, "unknown or expired run")
    return snap


# /api/what-if lives in demo.py (Track D) and calls runs.scoring_context for live runs.
@app.get("/api/twins")
async def list_twins(run_id: str, outcome: str = "any", major: str | None = None, k: int = Query(10, le=50)):
    ctx = await runs.scoring_context(run_id)
    if ctx is None:
        raise HTTPException(404, "run not found")
    rows = await db.match_twins(ctx.embedding, [ctx.school_slug], k=k, gpa=ctx.gpa, sat=ctx.sat, outcome=outcome)
    if major:
        rows = [r for r in rows if r["major_category"] == major]
    from .agents.nodes.twins import _to_card
    return [_to_card(i + 1, r).model_dump() for i, r in enumerate(rows)]


@app.get("/api/twins/{twin_id}")
async def twin_detail(twin_id: uuid.UUID):
    return await db.twin_detail(str(twin_id))


@app.get("/api/schools")
async def search_schools(q: str = Query(min_length=2)):
    return await db.resolve_school(q)


@app.get("/api/schools/{slug}")
async def school_summary(slug: str):
    s = await zetaris_repo.school_profile(slug)
    keep = ("slug", "name", "city", "state", "control", "admit_rate", "ed_admit_rate", "rd_admit_rate", "test_policy",
            "sat_composite_25", "sat_composite_75", "act_composite_25", "act_composite_75", "c7_weights",
            "early_plans", "major_competitiveness", "cds_year", "source_urls")
    return {k: s.get(k) for k in keep}


@app.get("/api/dev/fake-stream")                   # scripted SSE for Tracks C/D (plan §6.3); delete before H33
async def fake_stream(request: Request, after: int = Query(-1), speed: float = Query(1.0, ge=0.25, le=8.0)):
    return EventSourceResponse(script_frames(_start_after(request, after), speed, request), ping=15,
                               headers=SSE_HEADERS)


@app.get("/api/health")
async def health():
    ok_db = ok_zetaris = True
    try:
        await db.get_school("mit")
    except Exception:
        ok_db = False
    try:
        await zetaris.query("SELECT 7 AS seven", page_limit=1)    # the same probe verify.sh runs
    except Exception:
        ok_zetaris = False
    runtime = await meterless_health.probe()
    return {"meterless": runtime["ready"], "meterless_status": runtime["status"],
            "ok": ok_db, "db": ok_db, "zetaris": ok_zetaris, "zetaris_enabled": settings.zetaris_enabled,
            "llm_provider": settings.llm_provider, "llm_key": llm.key_configured() or settings.fake_llm,
            "tavily": bool(settings.tavily_api_key), "demo_mode": settings.demo_mode,
            "fake_llm": settings.fake_llm, "ts": time.time()}
