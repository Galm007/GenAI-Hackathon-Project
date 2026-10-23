from etl.common import append_jsonl, read_jsonl
from etl.reddit_archive import KEEP_FIELDS, MIN_INTERVAL_S, keep


def test_keep_filters_short_removed_and_stickied():
    long_text = "x" * 500
    assert keep({"selftext": long_text})
    assert not keep({"selftext": "short"})
    assert not keep({"selftext": "[removed]"})
    assert not keep({"selftext": long_text, "stickied": True})
    assert not keep({"selftext": long_text, "removed_by_category": "moderator"})


def test_no_author_field_is_kept():
    assert "author" not in KEEP_FIELDS
    assert MIN_INTERVAL_S >= 4.0


def test_jsonl_roundtrip(tmp_path):
    path = tmp_path / "a.jsonl"
    append_jsonl(path, [{"id": "1"}, {"id": "2"}])
    assert [r["id"] for r in read_jsonl(path)] == ["1", "2"]
    assert list(read_jsonl(tmp_path / "missing.jsonl")) == []


async def test_get_page_waits_for_ratelimit_reset(monkeypatch):
    import httpx

    from etl import reddit_archive

    sleeps: list[float] = []

    async def fake_sleep(s):
        sleeps.append(s)

    monkeypatch.setattr(reddit_archive.asyncio, "sleep", fake_sleep)
    replies = [
        httpx.Response(429, headers={"x-ratelimit-reset": "38"}),
        httpx.Response(200, json={"data": [{"id": "a"}]}),
    ]

    def handler(request):
        return replies.pop(0)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        assert await reddit_archive.get_page(http, {}) == [{"id": "a"}]
    assert sleeps == [39]
