"""ZETARIS_ENABLED=false and an unreachable stack both fall back to Supabase (D-039, handoff item A-1)."""
import httpx
import pytest

from app import zetaris_repo as repo

SUPABASE = {
    "get_school": {"slug": "uiuc", "name": "UIUC (Supabase)"},
    "peer_schools": ["purdue"],
    "school_calibration": 2.4,
    "admitted_medians": {"n": 40, "gpa_uw": 3.9},
}
CALLS = {  # repo function → (args, the db function it falls back to)
    "school_profile": (("uiuc",), "get_school"),
    "peer_schools": (("uiuc", "big_ten_public"), "peer_schools"),
    "reddit_calibration": (("uiuc",), "school_calibration"),
    "admitted_medians": (("uiuc",), "admitted_medians"),
}


@pytest.fixture
def supabase(monkeypatch):
    used: list[str] = []
    for name, value in SUPABASE.items():
        async def f(*_, _name=name, _value=value, **__):
            used.append(_name)
            return _value
        monkeypatch.setattr(repo.db, name, f)
    monkeypatch.setattr(repo, "_cache", {})
    return used


@pytest.mark.parametrize("fn", list(CALLS))
async def test_disabled_reads_go_straight_to_supabase(supabase, monkeypatch, fn):
    async def never(*_, **__):
        raise AssertionError("Zetaris must not be called when ZETARIS_ENABLED=false")

    monkeypatch.setattr(repo.settings, "zetaris_enabled", False)
    monkeypatch.setattr(repo.zetaris, "query", never)
    args, db_fn = CALLS[fn]
    assert await getattr(repo, fn)(*args) == SUPABASE[db_fn] and supabase == [db_fn]


@pytest.mark.parametrize("error", [
    httpx.ConnectError("connection refused"), httpx.ReadTimeout("spark is cold"), repo.ZetarisError("HTTP 500"),
], ids=["connect", "timeout", "zetaris"])
@pytest.mark.parametrize("fn", list(CALLS))
async def test_unreachable_stack_degrades_to_supabase(supabase, monkeypatch, fn, error):
    async def down(*_, **__):
        raise error

    monkeypatch.setattr(repo.settings, "zetaris_enabled", True)
    monkeypatch.setattr(repo.zetaris, "query", down)
    args, db_fn = CALLS[fn]
    assert await getattr(repo, fn)(*args) == SUPABASE[db_fn] and supabase == [db_fn]


async def test_other_errors_still_surface(supabase, monkeypatch):
    async def bug(*_, **__):
        raise KeyError("not a connectivity problem")

    monkeypatch.setattr(repo.settings, "zetaris_enabled", True)
    monkeypatch.setattr(repo.zetaris, "query", bug)
    with pytest.raises(KeyError):
        await repo.reddit_calibration("uiuc")
