from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

from .extract_reddit import run_extraction
from .load_cds import load_cds
from .load_scorecard import load_scorecard
from .load_twins import load_twins
from .reddit_archive import scrape_all
from .refresh_stats import refresh_stats


def _zetaris(fn: str):
    """Lazy import so the CLI works before etl/zetaris_setup.py (A14) exists."""
    async def run() -> None:
        from . import zetaris_setup

        await getattr(zetaris_setup, fn)()
    return run


def main() -> None:
    p = argparse.ArgumentParser(prog="etl")
    p.add_argument("stage", choices=["scorecard", "cds", "scrape", "extract", "load-twins", "refresh-stats",
                                     "zetaris-setup", "zetaris-refresh", "all"])
    p.add_argument("--since", default="2019-06-01", help="earliest post date for scraping")
    p.add_argument("--limit", type=int, default=None, help="extract at most N posts (smoke tests)")
    a = p.parse_args()
    since = datetime.fromisoformat(a.since).replace(tzinfo=UTC)

    stages = {
        "scorecard": load_scorecard,
        "cds": load_cds,
        "scrape": lambda: scrape_all(since),
        "extract": lambda: run_extraction(a.limit),
        "load-twins": load_twins,
        "refresh-stats": refresh_stats,
        "zetaris-setup": _zetaris("setup"),       # idempotent: "already exists" is treated as success
        "zetaris-refresh": _zetaris("refresh_gold"),
    }
    order = list(stages) if a.stage == "all" else [a.stage]
    for name in order:
        asyncio.run(stages[name]())


if __name__ == "__main__":
    main()
