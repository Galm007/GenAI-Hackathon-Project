from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Iterator
from pathlib import Path

from supabase import AsyncClient, acreate_client

ROOT = Path(__file__).resolve().parents[3]          # adcom/
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
for d in (RAW_DIR, PROCESSED_DIR):
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("etl")


def read_jsonl(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with path.open() as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def append_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("a") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")


async def supabase() -> AsyncClient:
    from app.config import settings  # lazy: app.config (B01) needs API keys at import time

    return await acreate_client(settings.supabase_url, settings.supabase_service_role_key)


async def fetch_all(sb: AsyncClient, table: str, columns: str = "*", page: int = 1000) -> list[dict]:
    """PostgREST caps responses at 1000 rows by default; page through with .range()."""
    out: list[dict] = []
    start = 0
    while True:
        res = await sb.table(table).select(columns).range(start, start + page - 1).execute()
        out.extend(res.data)
        if len(res.data) < page:
            return out
        start += page
