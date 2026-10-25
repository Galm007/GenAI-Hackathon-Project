from __future__ import annotations

import json

import pytest

import etl.load_twins as mod


class FakeTable:
    def __init__(self, sink: list):
        self.sink = sink

    def upsert(self, rows, on_conflict):
        self.sink.append((rows, on_conflict))
        return self

    async def execute(self):
        return None


class FakeSB:
    def __init__(self):
        self.calls: list = []

    def table(self, name):
        assert name == "applicant_twins"
        return FakeTable(self.calls)


@pytest.mark.asyncio
async def test_load_twins_dedupes_embeds_and_upserts(tmp_path, monkeypatch):
    rows = [{"reddit_id": "a", "profile_text": "one"}, {"reddit_id": "b", "profile_text": "two"},
            {"reddit_id": "a", "profile_text": "one again"}]
    (tmp_path / "twins.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    sb = FakeSB()

    async def fake_supabase():
        return sb

    async def fake_embed(texts):
        return [[float(len(t))] * 3 for t in texts]

    monkeypatch.setattr(mod, "PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(mod, "supabase", fake_supabase)
    monkeypatch.setattr(mod, "embed_texts", fake_embed)
    await mod.load_twins()

    (batch, conflict), = sb.calls
    assert conflict == "reddit_id" and [r["reddit_id"] for r in batch] == ["a", "b"]
    assert batch[0]["embedding"] == [9.0] * 3            # last write wins ("one again")
