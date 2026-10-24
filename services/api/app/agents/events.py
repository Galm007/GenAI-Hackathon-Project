from __future__ import annotations

import time
from typing import Any

from langgraph.config import get_stream_writer


def emit(event: str, **data: Any) -> None:
    """Push a custom event onto LangGraph's `custom` stream (forwarded to SSE by the API, Part II §4)."""
    try:
        writer = get_stream_writer()
    except RuntimeError:          # called outside a graph run (unit tests, /api/what-if)
        return
    writer({"event": event, "ts": time.time(), **data})


def progress(node: str, message: str, pct: float | None = None) -> None:
    emit("progress", node=node, message=message, pct=pct)


def tool_call(node: str, tool: str, status: str, **data: Any) -> None:
    emit("tool_call", node=node, tool=tool, status=status, **data)
