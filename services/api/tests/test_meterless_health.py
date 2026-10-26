import httpx
import pytest

from app import meterless_health as M
from app.config import settings


@pytest.mark.parametrize(("status", "body", "ready", "reason"), [
    (200, {"data": [{"id": "nvidia/test-nemotron"}]}, True, "ready"),
    (200, {"data": []}, False, "model_unavailable"),
    (401, {}, False, "unauthorized"),
    (503, {}, False, "unreachable"),
])
async def test_discovery_checks_auth_and_the_pinned_model(monkeypatch, status, body, ready, reason):
    monkeypatch.setattr(settings, "llm_provider", "meterless")
    monkeypatch.setattr(settings, "meterless_runtime_token", "test-token")
    monkeypatch.setattr(settings, "meterless_model", "nvidia/test-nemotron")
    original = httpx.AsyncClient
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(status, json=body)

    monkeypatch.setattr(M.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    assert await M.probe() == {"ready": ready, "status": reason}
    assert seen[0].url.path == "/v1/models"
    assert seen[0].headers["meterless-app"] == "adcom"
    assert all(r.method == "GET" for r in seen)
