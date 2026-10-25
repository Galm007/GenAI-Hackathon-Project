from __future__ import annotations

import yaml

import etl.refresh_stats as mod


class FakeQuery:
    def __init__(self, sb, name):
        self.sb, self.name, self.slug = sb, name, None

    def update(self, values):
        self.values = values
        return self

    def eq(self, _col, slug):
        self.slug = slug
        return self

    async def execute(self):
        self.sb.updates[self.slug] = self.values


class FakeRpc:
    async def execute(self):
        return None


class FakeSB:
    def __init__(self):
        self.updates: dict = {}

    def rpc(self, name, _params):
        assert name == "refresh_twin_stats"
        return FakeRpc()

    def table(self, name):
        assert name == "universities_cds"
        return FakeQuery(self, name)


async def test_refresh_stats_applies_min_n_and_overrides(tmp_path, monkeypatch):
    stats = [
        {"slug": "uiuc", "major_category": "computer_science", "n": 40, "smoothed_multiplier": 0.61234,
         "reddit_admit_rate": 0.4321},
        {"slug": "uiuc", "major_category": "psychology", "n": 5, "smoothed_multiplier": 1.4, "reddit_admit_rate": 0.9},
    ]
    (tmp_path / "major_overrides.yaml").write_text(yaml.dump({
        "uiuc": {"computer_science": {"multiplier": None, "direct_admit": True, "college": "Grainger"},
                 "math_stats": {"multiplier": 0.8, "direct_admit": False}},
    }))
    sb = FakeSB()

    async def fake_supabase():
        return sb

    async def fake_fetch_all(_sb, table, *_a):
        assert table == "school_major_stats"
        return stats

    monkeypatch.setattr(mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(mod, "supabase", fake_supabase)
    monkeypatch.setattr(mod, "fetch_all", fake_fetch_all)
    await mod.refresh_stats()

    mc = sb.updates["uiuc"]["major_competitiveness"]
    assert "psychology" not in mc                                     # n=5 < MIN_N is noise
    assert mc["computer_science"]["multiplier"] == 0.612              # null override keeps the Reddit estimate
    assert mc["computer_science"]["source"] == "reddit_smoothed" and mc["computer_science"]["direct_admit"] is True
    assert mc["math_stats"]["multiplier"] == 0.8 and mc["math_stats"]["source"] == "override"
