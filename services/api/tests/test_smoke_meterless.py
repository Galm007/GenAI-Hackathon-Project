import httpx
import pytest

from scripts import smoke_meterless as sm

GOOD = sm.MeterlessSettings(meterless_runtime_token="real-token", meterless_base_url="http://nightshift.test/v1")


def runtime(models=None, chat=None, status=200):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if status != 200:
            return httpx.Response(status)
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": models if models is not None else [{"id": "meterless/auto"}]})
        default = {"model": "nvidia/nemotron", "choices": [{"message": {"content": "ok"}}]}
        return httpx.Response(200, json=chat or default)

    return seen, httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_all_checks_pass_and_send_the_contract_headers():
    seen, http = runtime()
    results = await sm.run(GOOD, http)
    assert [r[0] for r in results] == ["PASS", "PASS", "PASS"]
    assert "nvidia/nemotron" in results[2][2]
    for req in seen:
        assert req.headers["authorization"] == "Bearer real-token"
        assert req.headers["meterless-app"] == "adcom" and req.headers["meterless-scope"] == "user"
    assert all("real-token" not in " ".join(r) for r in results)          # the token is never printed


@pytest.mark.parametrize("token", ["", "...", "rt-local"])
async def test_placeholder_token_fails_before_any_request(token):
    seen, http = runtime()
    results = await sm.run(sm.MeterlessSettings(meterless_runtime_token=token), http)
    assert results[0][0] == "FAIL" and len(results) == 1 and seen == []


async def test_unauthorized_is_reported_clearly():
    _, http = runtime(status=401)
    results = await sm.run(GOOD, http)
    assert results[-1][0] == "FAIL" and "unauthorized" in results[-1][2] and len(results) == 2


async def test_no_models_is_a_failure():
    _, http = runtime(models=[])
    results = await sm.run(GOOD, http)
    assert results[-1][0] == "FAIL" and "lists no models" in results[-1][2]


async def test_empty_chat_reply_fails():
    _, http = runtime(chat={"model": "m", "choices": [{"message": {"content": ""}}]})
    results = await sm.run(GOOD, http)
    assert [r[0] for r in results] == ["PASS", "PASS", "FAIL"]
