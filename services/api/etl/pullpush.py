"""Scrape r/collegeresults and r/TransferToTop25 submissions from PullPush into raw JSONL.

PullPush mirrors Reddit submissions; `size` is capped at 100 and we paginate backwards in time with
`before=<min created_utc of previous page>`. Be a good citizen: one request every 4 s, exponential backoff
on 429/5xx, and a checkpoint file so a crash never re-fetches pages.
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from .common import RAW_DIR, log

PULLPUSH_URL = "https://api.pullpush.io/reddit/search/submission/"
PAGE_SIZE = 100
MIN_INTERVAL_S = 4.0
MIN_SELFTEXT_CHARS = 400
SUBREDDITS = ("collegeresults", "TransferToTop25")
KEEP_FIELDS = ("id", "title", "selftext", "created_utc", "permalink", "link_flair_text", "score", "num_comments")
USER_AGENT = "adcom-hackathon/0.1 (academic research; contact: team@example.com)"


def keep(post: dict) -> bool:
    text = post.get("selftext") or ""
    if text in ("[removed]", "[deleted]") or len(text) < MIN_SELFTEXT_CHARS:
        return False
    if post.get("stickied") or post.get("removed_by_category"):
        return False
    return True


async def get_page(http: httpx.AsyncClient, params: dict) -> list[dict]:
    for attempt in range(7):
        try:
            resp = await http.get(PULLPUSH_URL, params=params)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise httpx.HTTPStatusError(f"retryable {resp.status_code}", request=resp.request, response=resp)
            resp.raise_for_status()
            return resp.json().get("data", [])
        except (httpx.HTTPStatusError, httpx.TransportError, json.JSONDecodeError) as exc:
            wait = min(180, 5 * 2**attempt)
            log.warning("pullpush %s (attempt %d) → sleeping %ss", exc, attempt + 1, wait)
            await asyncio.sleep(wait)
    raise RuntimeError(f"PullPush failed repeatedly for params={params}")


async def scrape(subreddit: str, since: datetime) -> Path:
    out = RAW_DIR / f"{subreddit}.jsonl"
    ckpt = RAW_DIR / f"{subreddit}.checkpoint.json"
    since_epoch = int(since.timestamp())

    seen: set[str] = set()
    if out.exists():
        with out.open() as f:
            seen = {json.loads(line)["id"] for line in f if line.strip()}
    before = json.loads(ckpt.read_text())["before"] if ckpt.exists() else int(time.time())

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": USER_AGENT}) as http:
        with out.open("a") as f:
            while before > since_epoch:
                params = {
                    "subreddit": subreddit,
                    "size": PAGE_SIZE,
                    "before": before,
                    "after": since_epoch,
                    "sort": "desc",
                    "sort_type": "created_utc",
                }
                posts = await get_page(http, params)
                if not posts:
                    break
                kept = 0
                for p in posts:
                    if p["id"] in seen or not keep(p):
                        continue
                    seen.add(p["id"])
                    row = {k: p.get(k) for k in KEEP_FIELDS} | {"subreddit": subreddit}   # no author field: privacy
                    f.write(json.dumps(row) + "\n")
                    kept += 1
                f.flush()
                before = min(int(float(p["created_utc"])) for p in posts)
                ckpt.write_text(json.dumps({"before": before}))
                log.info("%s: page kept %d/%d, cursor=%s, total=%d",
                         subreddit, kept, len(posts),
                         datetime.fromtimestamp(before, tz=UTC).date(), len(seen))
                await asyncio.sleep(MIN_INTERVAL_S)
    return out


async def scrape_all(since: datetime) -> None:
    # Sequential on purpose: one polite request stream to PullPush.
    for sub in SUBREDDITS:
        await scrape(sub, since)
