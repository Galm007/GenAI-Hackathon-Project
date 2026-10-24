from __future__ import annotations

import asyncio

from tavily import AsyncTavilyClient

from . import db
from .agents.events import tool_call
from .config import settings
from .schemas.institution import WebSnippet

_tavily = AsyncTavilyClient(api_key=settings.tavily_api_key) if settings.tavily_api_key else None
TIMEOUT_S = 12


def _queries(school: dict, major_label: str, cycle: int) -> list[str]:
    name = school["name"]
    return [
        f"{name} undergraduate admissions {cycle} test policy SAT ACT requirement",
        f"{name} {major_label} major admission direct admit capped internal transfer",
        f"{name} admissions class of {cycle + 4} profile priorities dean announcement",
    ]


async def _search(slug: str, q: str) -> list[dict]:
    if (hit := await db.research_cache_get(slug, q)) is not None:
        tool_call("institutional", "tavily.search", "cache_hit", query=q, result_count=len(hit))
        return hit
    tool_call("institutional", "tavily.search", "started", query=q)
    resp = await asyncio.wait_for(
        _tavily.search(query=q, search_depth="advanced", max_results=4), timeout=TIMEOUT_S
    )
    results = [
        {"url": r["url"], "title": r.get("title", ""), "content": r.get("content", "")[:1200],
         "published": r.get("published_date")}
        for r in resp.get("results", [])
    ]
    await db.research_cache_put(slug, q, results)
    tool_call("institutional", "tavily.search", "done", query=q, result_count=len(results))
    return results


async def research_school(school: dict, major_label: str, cycle: int) -> list[WebSnippet]:
    if _tavily is None:
        return []
    batches = await asyncio.gather(
        *(_search(school["slug"], q) for q in _queries(school, major_label, cycle)), return_exceptions=True
    )
    seen: set[str] = set()
    snippets: list[WebSnippet] = []
    for batch in batches:
        if isinstance(batch, BaseException):
            tool_call("institutional", "tavily.search", "failed", error=str(batch))
            continue
        for r in batch:
            if r["url"] in seen:
                continue
            seen.add(r["url"])
            snippets.append(WebSnippet(id=f"W{len(snippets) + 1}", **r))
    # Official sources first: .edu admissions pages outrank news and forums.
    snippets.sort(key=lambda s: (".edu" not in s.url, "reddit.com" in s.url))
    return [s.model_copy(update={"id": f"W{i + 1}"}) for i, s in enumerate(snippets[:10])]
