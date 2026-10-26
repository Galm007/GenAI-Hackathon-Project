"""Client for the World Model sidecar (`services/world-model`, plan §1.7.3): the committee's shared case file.

Nodes 1–3 append their docket sections as observations to the run's namespace (`run:<id>`) while they run, Nodes 2
and 3 in parallel; the docket node reads them back through the sidecar's read surface. Every call is best-effort:
with WORLD_MODEL_URL unset nothing is sent, and when the sidecar is down the docket is built from the run state.
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

import httpx
import orjson

from .config import settings

log = logging.getLogger("world_model")

SECTION = "docket.section"
TIMEOUT = httpx.Timeout(3.0, connect=1.0)
BACKOFF_S = 30.0                      # after a failure, skip calls for a while instead of paying the timeout per node

http = httpx.AsyncClient(timeout=TIMEOUT)
_down_until = 0.0


def enabled() -> bool:
    return bool(settings.world_model_url)


def _url(run_id: str, action: str) -> str:
    return f"{settings.world_model_url.rstrip('/')}/v1/run:{run_id}/{action}"


def _available() -> bool:
    return enabled() and time.monotonic() >= _down_until


def _failed(exc: Exception) -> None:
    global _down_until
    _down_until = time.monotonic() + BACKOFF_S
    log.warning("world model unavailable (%s); docket falls back to run state", type(exc).__name__)


async def append(run_id: str | None, node: str, sections: dict, kind: str = SECTION) -> bool:
    """Append one observation per section (`{name: payload}`); re-sending a section (a node retry) replaces it.
    Payloads travel as JSON text: JavaScript would turn 3.0 into 3 and change the docket's bytes."""
    if not run_id or not sections or not _available():
        return False
    at = datetime.now(UTC).isoformat()
    source = {"kind": "node", "ref": node, "at": at}
    try:
        observations = [{"externalId": f"{kind}:{name}", "kind": kind, "section": name, "node": node,
                         "payload": orjson.dumps(payload).decode(), "at": at, "source": source}
                        for name, payload in sections.items()]
        resp = await http.post(_url(run_id, "ingest"), content=orjson.dumps({"observations": observations}),
                               headers={"content-type": "application/json"})
        resp.raise_for_status()
        return True
    except Exception as exc:                # the case file is best-effort: it never fails a node
        _failed(exc)
        return False


async def sections(run_id: str | None) -> dict | None:
    """The run's docket sections as `{name: payload}`, or None when the sidecar is off, down or truncated."""
    if not run_id or not _available():
        return None
    try:
        resp = await http.get(_url(run_id, "context"), params={"kind": SECTION})
        resp.raise_for_status()
        body = resp.json()
        if body.get("truncated"):
            return None
        return {o["section"]: orjson.loads(o["payload"]) for o in body.get("observations", [])}
    except Exception as exc:
        _failed(exc)
        return None
