from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

import orjson
from fastapi import Request

from . import db, zetaris_repo
from .agents.graph import graph
from .config import settings
from .schemas.delta import Counterfactual
from .schemas.inputs import RawApplicantInputs
from .scoring.probability import ScoringInputs

log = logging.getLogger("runs")
CAPTURED = {"scorecard", "probability", "counterfactuals", "final_report"}
PREFILL_KEYS = ("dossier", "grade", "metrics", "profile_text", "profile_embedding")
DOSSIER_TTL_S = 86_400       # same 24 h privacy window as runs (§7.4)
WATCHDOG_INTERVAL_S = 15

# `/api/dev/fake-stream` still replays this hand-written script for Tracks C/D (plan §6.3; D06 replaces it).
FAKE_STREAM = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "fake_stream.json"
MAX_GAP_S = 1.2          # compress long pauses in the script; keep token cadence natural


class RateLimited(RuntimeError):
    pass


@dataclass
class Run:
    run_id: str
    session_id: str
    school_slug: str
    has_recommendations: bool = False
    events: list[dict] = field(default_factory=list)
    captured: dict[str, dict] = field(default_factory=dict)
    cond: asyncio.Condition = field(default_factory=asyncio.Condition)
    done: bool = False
    status: str = "running"
    final: dict | None = None
    task: asyncio.Task | None = None
    subscribers: int = 0
    last_seen: float = field(default_factory=time.monotonic)
    started: float = field(default_factory=time.monotonic)
    school: dict | None = None                     # set for demo replays (works with the DB offline)


@dataclass(frozen=True)
class ScoringContext:
    run_id: str
    school_slug: str
    major_category: str
    scoring_inputs: ScoringInputs
    tiers: list[int]
    has_recommendations: bool
    school: dict
    counterfactuals: list[Counterfactual]
    embedding: list[float] | None
    gpa: float | None
    sat: int | None


@cache
def load_script() -> list[dict]:
    return orjson.loads(FAKE_STREAM.read_bytes())["events"]


def _gap(prev: dict | None, ev: dict, speed: float) -> float:
    return 0.0 if prev is None else min(max(ev["ts"] - prev["ts"], 0.0), MAX_GAP_S) / speed


def dossier_key(inputs: RawApplicantInputs) -> str:
    """Everything Node 1 reads. Hooks and context shape the grade and the embedded profile (see DECISIONS D-036)."""
    h = hashlib.sha256()
    for part in (inputs.transcript_pdf_b64, inputs.resume_pdf_b64, inputs.resume_text, inputs.activities_text,
                 inputs.essay_text, inputs.recommendation_text, inputs.intended_major,
                 ",".join(sorted(inputs.hooks)), inputs.context.model_dump_json()):
        h.update((part or "").encode())
        h.update(b"\x00")
    return h.hexdigest()


class RunManager:
    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}
        self._sem = asyncio.Semaphore(settings.max_concurrent_runs)
        self._day: tuple[date, int] = (date.today(), 0)
        self._active_sessions: set[str] = set()
        self._dossier_cache: dict[str, tuple[float, dict[str, Any]]] = {}   # dossier_key → (time, Node 1 outputs)

    # ---------- lifecycle ----------
    def get(self, run_id: str) -> Run | None:
        return self._runs.get(run_id)

    def _admit(self, session_id: str) -> None:
        today = date.today()
        if self._day[0] != today:
            self._day = (today, 0)
        if self._day[1] >= settings.max_runs_per_day:
            raise RateLimited("Today's evaluation budget is used up. Try the recorded demo.")
        if session_id in self._active_sessions:
            raise RateLimited("You already have an evaluation in progress.")
        if self._sem.locked():
            raise RateLimited("All committee rooms are busy. Retry in a minute.")
        self._day = (today, self._day[1] + 1)

    async def start(self, *, session_id: str, inputs: RawApplicantInputs, school_slug: str,
                    prefill: dict[str, Any] | None = None) -> Run:
        self._admit(session_id)
        if prefill is None:                         # identical upload: reuse its parsed dossier, skip Node 1 (§7.4)
            prefill = self._cached_dossier(dossier_key(inputs))
        run = Run(run_id=str(uuid.uuid4()), session_id=session_id, school_slug=school_slug,
                  has_recommendations=bool(inputs.recommendation_text))
        self._runs[run.run_id] = run
        self._active_sessions.add(session_id)      # before the task runs, so a double submit is refused
        state = {"run_id": run.run_id, "session_id": session_id, "inputs": inputs,
                 "school_slug": school_slug, **(prefill or {})}
        run.task = asyncio.create_task(self._drive(run, state))
        return run

    async def start_child(self, parent: Run, slug: str) -> Run:
        f = parent.final
        return await self.start(session_id=parent.session_id, inputs=f["inputs"], school_slug=slug,
                                prefill={k: f[k] for k in PREFILL_KEYS})

    def _cached_dossier(self, key: str) -> dict[str, Any] | None:
        hit = self._dossier_cache.get(key)
        if hit is None:
            return None
        if time.time() - hit[0] >= DOSSIER_TTL_S:
            del self._dossier_cache[key]
            return None
        return hit[1]

    async def shutdown(self) -> None:
        for run in self._runs.values():
            if run.task and not run.task.done():
                run.task.cancel()

    # ---------- the driver ----------
    async def publish(self, run: Run, event: str, **data: Any) -> None:
        async with run.cond:
            env = {"seq": len(run.events), "run_id": run.run_id, "ts": round(time.time(), 3), "event": event, **data}
            run.events.append(env)
            if event in CAPTURED:
                run.captured[event] = env
            run.cond.notify_all()

    async def _drive(self, run: Run, state: dict) -> None:
        config = {"configurable": {"thread_id": run.run_id}, "recursion_limit": 40}
        watchdog = asyncio.create_task(self._watchdog(run))
        try:
            async with self._sem:
                await self.publish(run, "run_started", school_slug=run.school_slug,
                                   cached_dossier="dossier" in state)
                if "dossier" in state:      # child run / cached upload: replay Node 1's outputs so the panel fills
                    await self.publish(run, "dossier_parsed", metrics=state["metrics"].model_dump(),
                                       dossier=state["dossier"].model_dump(exclude={"essay_text"}))
                    await self.publish(run, "scorecard", grade=state["grade"].model_dump(),
                                       metrics=state["metrics"].model_dump(), warnings=[])
                async for mode, chunk in graph.astream(state, config, stream_mode=["updates", "custom"]):
                    if mode == "custom":
                        payload = dict(chunk)
                        event = payload.pop("event")
                        payload.pop("ts", None)
                        await self.publish(run, event, **payload)
                    else:
                        for node in chunk:              # {node_name: partial_state}; never send state itself
                            await self.publish(run, "node_complete", node=node)
                run.final = (await graph.aget_state(config)).values
                run.status = "complete"
                if all(run.final.get(k) is not None for k in PREFILL_KEYS):
                    self._dossier_cache[dossier_key(state["inputs"])] = (
                        time.time(), {k: run.final[k] for k in PREFILL_KEYS})
        except asyncio.CancelledError:
            run.status = "failed"
            await self.publish(run, "error", node=None, message="Run cancelled: no viewers.", recoverable=False)
        except Exception as exc:                        # the stream must always end cleanly
            run.status = "failed"
            log.exception("run %s failed", run.run_id)
            await self.publish(run, "error", node=None, message=f"Evaluation failed ({type(exc).__name__}).",
                               recoverable=False)
        finally:
            watchdog.cancel()
            await self.publish(run, "done", status=run.status,
                               elapsed_ms=int((time.monotonic() - run.started) * 1000))
            async with run.cond:
                run.done = True
                run.cond.notify_all()
            self._active_sessions.discard(run.session_id)
            try:
                await db.append_event_log(run.run_id, run.events, run.status)
            except Exception:
                log.warning("could not persist event log for %s", run.run_id)

    async def _watchdog(self, run: Run) -> None:
        """Don't burn tokens on a run nobody is watching (closed tab, abandoned demo)."""
        while True:
            await asyncio.sleep(WATCHDOG_INTERVAL_S)
            if run.subscribers == 0 and time.monotonic() - run.last_seen > settings.run_idle_cancel_s:
                if run.task:
                    run.task.cancel()
                return

    # ---------- read side ----------
    async def snapshot(self, run_id: str) -> dict | None:
        run = self._runs.get(run_id)
        if run:
            return {"run_id": run_id, "status": run.status, "school_slug": run.school_slug,
                    "last_seq": len(run.events) - 1,
                    "captured": {k: v for k, v in run.captured.items()}}
        row = await db.load_run(run_id)
        if not row:
            return None
        return {"run_id": run_id, "status": row["status"], "school_slug": row["school_slug"],
                **{k: row.get(k) for k in ("grade", "metrics", "school_rubric", "twins", "baseline", "probability",
                                           "debate", "counterfactuals", "delta_report")}}

    async def scoring_context(self, run_id: str) -> ScoringContext | None:
        run = self._runs.get(run_id)
        if run and "probability" in run.captured and "scorecard" in run.captured:
            cap, f = run.captured, run.final or {}
            grade = cap["scorecard"]["grade"]
            return ScoringContext(
                run_id=run_id, school_slug=run.school_slug, major_category=grade["major_category"],
                scoring_inputs=ScoringInputs.model_validate(cap["probability"]["scoring_inputs"]),
                tiers=[ag["tier"] for ag in grade["activity_grades"]],
                has_recommendations=run.has_recommendations,
                school=run.school or await zetaris_repo.school_profile(run.school_slug),
                counterfactuals=[Counterfactual.model_validate(c)
                                 for c in cap.get("counterfactuals", {}).get("counterfactuals", [])],
                embedding=f.get("profile_embedding"),
                gpa=f["metrics"].gpa_uw_4 if f.get("metrics") else None,
                sat=cap["scorecard"]["metrics"]["sat_equivalent"],
            )
        row = await db.load_run(run_id)                 # after a restart: rebuild from Postgres
        if not row or not row.get("scoring_inputs"):
            return None
        emb = row.get("profile_embedding")
        return ScoringContext(
            run_id=run_id, school_slug=row["school_slug"], major_category=row["major_category"],
            scoring_inputs=ScoringInputs.model_validate(row["scoring_inputs"]),
            tiers=[ag["tier"] for ag in row["grade"]["activity_grades"]],
            has_recommendations=bool((row.get("intake") or {}).get("has_recommendations")),
            school=await zetaris_repo.school_profile(row["school_slug"]),
            counterfactuals=[Counterfactual.model_validate(c) for c in row.get("counterfactuals") or []],
            embedding=json.loads(emb) if isinstance(emb, str) else emb,   # PostgREST returns vector as text
            gpa=(row.get("metrics") or {}).get("gpa_uw_4"),
            sat=(row.get("metrics") or {}).get("sat_equivalent"),
        )


async def sse_frames(run: Run, after: int, request: Request) -> AsyncIterator[dict]:
    """One reader per connection. Replays everything after `after`, then follows live."""
    i = after + 1
    run.subscribers += 1
    try:
        while True:
            async with run.cond:
                await run.cond.wait_for(lambda n=i: len(run.events) > n or run.done)
                batch = run.events[i:]
            for ev in batch:
                yield {"id": str(ev["seq"]), "event": ev["event"], "data": orjson.dumps(ev).decode()}
            i += len(batch)
            run.last_seen = time.monotonic()
            if run.done and i >= len(run.events):
                return
            if await request.is_disconnected():
                return
    finally:
        run.subscribers -= 1
        run.last_seen = time.monotonic()


async def script_frames(after: int, speed: float, request: Request) -> AsyncIterator[dict]:
    """`/api/dev/fake-stream`: the script straight to the wire, no RunManager. Resumes after `after` (Last-Event-ID)."""
    prev = None
    for ev in load_script():
        if ev["seq"] <= after:
            continue
        await asyncio.sleep(_gap(prev, ev, speed))
        prev = ev
        if await request.is_disconnected():
            return
        env = {**ev, "ts": round(time.time(), 3)}
        yield {"id": str(env["seq"]), "event": env["event"], "data": orjson.dumps(env).decode()}
