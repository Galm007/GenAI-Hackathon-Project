import pytest

from etl import resources


def fake_compose(calls, ps_out="postgres\ndriver\napi\nui\n", stop_code=0):
    async def run(*args):
        calls.append(args)
        if args[0] == "ps":
            return 0, ps_out
        if args[0] == "stop":
            return stop_code, ""
        return 0, ""
    return run


async def test_stops_running_services_and_restarts_them(monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(resources, "_compose", fake_compose(calls))
    monkeypatch.delenv("ADCOM_KEEP_ZETARIS", raising=False)
    async with resources.zetaris_paused() as stopped:
        assert stopped == ["postgres", "driver", "api", "ui"]
        assert calls[-1] == ("stop", "postgres", "driver", "api", "ui")
    assert calls[-1] == ("start", "postgres", "driver", "api", "ui")
    assert not any(a[0] == "down" for a in calls)


async def test_restarts_even_if_the_block_fails(monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(resources, "_compose", fake_compose(calls))
    monkeypatch.delenv("ADCOM_KEEP_ZETARIS", raising=False)
    with pytest.raises(RuntimeError):
        async with resources.zetaris_paused():
            raise RuntimeError("extraction crashed")
    assert calls[-1][0] == "start"


async def test_nothing_running_does_nothing(monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(resources, "_compose", fake_compose(calls, ps_out=""))
    monkeypatch.delenv("ADCOM_KEEP_ZETARIS", raising=False)
    async with resources.zetaris_paused() as stopped:
        assert stopped == []
    assert [c[0] for c in calls] == ["ps"]


async def test_stop_failure_does_not_block_and_does_not_restart(monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(resources, "_compose", fake_compose(calls, stop_code=1))
    monkeypatch.delenv("ADCOM_KEEP_ZETARIS", raising=False)
    async with resources.zetaris_paused() as stopped:
        assert stopped == []
    assert [c[0] for c in calls] == ["ps", "stop"]


async def test_env_switch_skips_pause(monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(resources, "_compose", fake_compose(calls))
    monkeypatch.setenv("ADCOM_KEEP_ZETARIS", "1")
    async with resources.zetaris_paused() as stopped:
        assert stopped == []
    assert calls == []

