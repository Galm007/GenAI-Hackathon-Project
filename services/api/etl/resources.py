"""Free memory for the local extraction model by pausing the Zetaris Docker stack while it runs.

Gemma plus the Zetaris containers do not fit in 15 GB of RAM together: the host starts swapping and
generation drops from ~70 tokens/s to ~1. `zetaris_paused()` stops only the services that are running
(`docker compose stop`: containers and volumes are kept, never `down -v`, which would destroy the Zetaris
metastore and keypair) and starts the same services again afterwards.

Set ADCOM_KEEP_ZETARIS=1 to skip the pause, e.g. on a machine with plenty of RAM.
"""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from .common import ROOT, log

ZETARIS_DIR = ROOT / "zetaris-platform"


async def _compose(*args: str) -> tuple[int, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", *args, cwd=ZETARIS_DIR,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
    except (FileNotFoundError, NotADirectoryError):          # no docker, or no zetaris-platform/ checkout
        return 127, ""
    out, _ = await proc.communicate()
    return proc.returncode or 0, out.decode(errors="replace")


@asynccontextmanager
async def zetaris_paused(*, restore: bool = True) -> AsyncIterator[list[str]]:
    """Stop the running Zetaris services for the duration of the block; yields the services it stopped."""
    if os.environ.get("ADCOM_KEEP_ZETARIS") == "1":
        log.info("zetaris pause skipped (ADCOM_KEEP_ZETARIS=1)")
        yield []
        return
    code, out = await _compose("ps", "--services", "--status", "running")
    running = out.split() if code == 0 else []
    if not running:
        log.info("zetaris not running (or docker unavailable): nothing to pause")
        yield []
        return
    code, out = await _compose("stop", *running)
    if code != 0:
        log.warning("could not stop zetaris (%s); continuing, expect slow generation: %s", code, out.strip()[-300:])
        yield []
        return
    log.info("zetaris paused: %s", ", ".join(running))
    try:
        yield running
    finally:
        if restore:
            code, out = await _compose("start", *running)
            if code == 0:
                log.info("zetaris restarted: %s (give it ~1 min to become healthy)", ", ".join(running))
            else:
                log.error("FAILED to restart zetaris (%s). Run: cd zetaris-platform && docker compose start. %s",
                          code, out.strip()[-300:])
