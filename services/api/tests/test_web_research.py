import asyncio

import pytest

from app import web_research as W

SCHOOL = {"slug": "uiuc", "name": "UIUC"}


class FakeTavily:
    def __init__(self, by_query):
        self.by_query, self.calls = by_query, []

    async def search(self, *, query, search_depth, max_results):
        self.calls.append((query, search_depth, max_results))
        result = self.by_query(query)
        if isinstance(result, BaseException):
            raise result
        return {"results": result}


def hit(url: str, content: str = "c") -> dict:
    return {"url": url, "title": f"t {url}", "content": content, "published_date": "2026-09-01"}


@pytest.fixture
def env(monkeypatch):
    cache: dict[str, list[dict]] = {}
    events: list[tuple] = []

    async def get(slug, q):
        return cache.get(q)

    async def put(slug, q, results):
        cache[q] = results

    monkeypatch.setattr(W.db, "research_cache_get", get)
    monkeypatch.setattr(W.db, "research_cache_put", put)
    monkeypatch.setattr(W, "tool_call", lambda node, tool, status, **d: events.append((status, d)))

    def install(by_query):
        t = FakeTavily(by_query)
        monkeypatch.setattr(W, "_tavily", t)
        return t
    return install, cache, events


async def test_no_key_means_no_research(monkeypatch):
    monkeypatch.setattr(W, "_tavily", None)
    assert await W.research_school(SCHOOL, "computer science", 2026) == []


async def test_dedupes_ranks_official_sources_and_renumbers(env):
    install, cache, events = env
    q1, q2, q3 = W._queries(SCHOOL, "computer science", 2026)
    t = install(lambda q: {q1: [hit("https://news.example.com/a"), hit("https://admissions.illinois.edu/policy")],
                           q2: [hit("https://www.reddit.com/r/x"), hit("https://news.example.com/a")],
                           q3: [hit("https://cs.illinois.edu/admit", "x" * 5000)]}[q])
    snippets = await W.research_school(SCHOOL, "computer science", 2026)
    assert [s.url for s in snippets] == ["https://admissions.illinois.edu/policy", "https://cs.illinois.edu/admit",
                                         "https://news.example.com/a", "https://www.reddit.com/r/x"]
    assert [s.id for s in snippets] == ["W1", "W2", "W3", "W4"]
    assert len(snippets[1].content) == 1200 and snippets[0].published == "2026-09-01"
    assert {c[1:] for c in t.calls} == {("advanced", 4)} and len(t.calls) == 3
    assert set(cache) == {q1, q2, q3}
    assert [e[0] for e in events].count("done") == 3


async def test_cache_hit_skips_tavily(env):
    install, cache, events = env
    queries = W._queries(SCHOOL, "cs", 2026)
    for q in queries:
        cache[q] = [{"url": f"https://u.edu/{q[:5]}", "title": "", "content": "", "published": None}]
    t = install(lambda q: pytest.fail("should not call Tavily"))
    assert len(await W.research_school(SCHOOL, "cs", 2026)) == 1           # same URL from every query → one
    assert t.calls == [] and [e[0] for e in events] == ["cache_hit"] * 3


async def test_a_failing_query_degrades_gracefully(env):
    install, _, events = env
    q1, _, _ = W._queries(SCHOOL, "cs", 2026)
    install(lambda q: [hit("https://ok.edu")] if q == q1 else RuntimeError("tavily down"))
    snippets = await W.research_school(SCHOOL, "cs", 2026)
    assert [s.url for s in snippets] == ["https://ok.edu"]
    assert [e[0] for e in events].count("failed") == 2


async def test_timeout_is_treated_as_a_failure(env, monkeypatch):
    install, _, events = env
    monkeypatch.setattr(W, "TIMEOUT_S", 0.01)

    class Slow(FakeTavily):
        async def search(self, **kw):
            await asyncio.sleep(1)

    monkeypatch.setattr(W, "_tavily", Slow(lambda q: []))
    assert await W.research_school(SCHOOL, "cs", 2026) == []
    assert [e[0] for e in events].count("failed") == 3


async def test_at_most_ten_snippets(env):
    install, _, _ = env
    install(lambda q: [hit(f"https://s{i}-{hash(q) % 997}.edu") for i in range(4)])
    snippets = await W.research_school(SCHOOL, "cs", 2026)
    assert len(snippets) == 10 and snippets[-1].id == "W10"
