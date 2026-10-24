from __future__ import annotations

import asyncio
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

from .config import settings
from .schemas.inputs import RawApplicantInputs

log = logging.getLogger("runs")
CAPTURED = {"scorecard", "probability", "counterfactuals", "final_report"}

# Until B13 wires graph.astream into _drive, every run replays this hand-written script (plan §6.3; D06 replaces it).
FAKE_STREAM = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "fake_stream.json"
ENVELOPE = ("seq", "run_id", "ts", "event")
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


@cache
def load_script() -> list[dict]:
    return orjson.loads(FAKE_STREAM.read_bytes())["events"]


def _gap(prev: dict | None, ev: dict, speed: float) -> float:
    return 0.0 if prev is None else min(max(ev["ts"] - prev["ts"], 0.0), MAX_GAP_S) / speed


class RunManager:
    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}
        self._sem = asyncio.Semaphore(settings.max_concurrent_runs)
        self._day: tuple[date, int] = (date.today(), 0)
        self._active_sessions: set[str] = set()

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

    async def start(self, *, session_id: str, inputs: RawApplicantInputs, school_slug: str) -> Run:
        self._admit(session_id)
        run = Run(run_id=str(uuid.uuid4()), session_id=session_id, school_slug=school_slug,
                  has_recommendations=bool(inputs.recommendation_text))
        self._runs[run.run_id] = run
        self._active_sessions.add(session_id)      # before the task runs, so a double submit is refused
        run.task = asyncio.create_task(self._drive(run))
        return run

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

    async def _drive(self, run: Run) -> None:
        watchdog = asyncio.create_task(self._watchdog(run))
        try:
            async with self._sem:
                await self.publish(run, "run_started", school_slug=run.school_slug, cached_dossier=False)
                prev = None
                for ev in load_script():                # B13 replaces this loop with graph.astream (plan §4.4)
                    if ev["event"] in ("run_started", "done"):
                        continue                        # the driver owns the run's first and last frames
                    await asyncio.sleep(_gap(prev, ev, 1.0))
                    prev = ev
                    await self.publish(run, ev["event"], **{k: v for k, v in ev.items() if k not in ENVELOPE})
                run.status = "complete"
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
            # B13: persist run.events with db.append_event_log (needs db.py from B07).

    async def _watchdog(self, run: Run) -> None:
        """Don't burn tokens on a run nobody is watching (closed tab, abandoned demo)."""
        while True:
            await asyncio.sleep(15)
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
        return None                                     # B13: fall back to db.load_run after a restart


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
