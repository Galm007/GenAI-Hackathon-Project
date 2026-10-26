"""app.llm against a real AsyncAnthropic whose HTTP transport is mocked (no network, no key)."""
import json

import httpx2
import pytest
from anthropic import AsyncAnthropic, DefaultAsyncHttpxClient
from pydantic import BaseModel

from app import llm


class Verdict(BaseModel):
    label: str


def _message(content: list[dict], stop_reason: str, stop_details: dict | None = None) -> dict:
    return {"id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
            "content": content, "stop_reason": stop_reason, "stop_details": stop_details,
            "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 5}}


def _sse(events: list[dict]) -> bytes:
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()


@pytest.fixture
def mock_api(monkeypatch):
    """Install a client whose responses come from `reply(request) -> httpx2.Response`; returns the request log."""
    requests: list[httpx2.Request] = []

    def install(reply):
        def handler(request: httpx2.Request) -> httpx2.Response:
            requests.append(request)
            return reply(request)

        client = AsyncAnthropic(api_key="test", max_retries=0,
                                http_client=DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler)))
        monkeypatch.setattr(llm, "client", client)
        return requests

    return install


def _json(body: dict):
    return lambda _req: httpx2.Response(200, json=body)


# ---------- parse ----------
@pytest.mark.parametrize("max_tokens", [32000, 24000, 16000], ids=["node1_extract", "node1_grade", "default"])
async def test_parse_long_requests_pass_the_sdks_own_streaming_check(mock_api, max_tokens):
    # The real SDK (only its transport is mocked) refuses a non-streamed request over ~21K max_tokens unless the
    # call sets a timeout. Node 1 asks for 32K and 24K; before D-040 every live run failed here with a ValueError.
    requests = mock_api(_json(_message([{"type": "text", "text": '{"label": "admit"}'}], "end_turn")))
    out = await llm.parse(Verdict, system="sys", messages=[{"role": "user", "content": "hi"}], max_tokens=max_tokens)
    assert out == Verdict(label="admit")
    assert json.loads(requests[0].content)["max_tokens"] == max_tokens
    sent = requests[0].extensions["timeout"]
    assert sent["read"] == pytest.approx(max(600.0, 3600.0 * max_tokens / 128_000)) and sent["connect"] == 5.0


def test_parse_timeout_follows_the_sdk_estimate():
    assert llm.parse_timeout(128_000).read == 3600.0
    assert llm.parse_timeout(32_000).read == 900.0
    assert llm.parse_timeout(4_000).read == 600.0          # never below the SDK's 10-minute default
async def test_parse_returns_validated_model_and_sends_plan_shapes(mock_api):
    requests = mock_api(_json(_message([{"type": "text", "text": '{"label": "admit"}'}], "end_turn")))
    out = await llm.parse(Verdict, system="sys", messages=[{"role": "user", "content": "hi"}], effort="high")

    assert out == Verdict(label="admit")
    body = json.loads(requests[0].content)
    assert llm.FALLBACK_BETA in requests[0].headers["anthropic-beta"]
    assert body["fallbacks"] == "default"
    assert body["model"] == "claude-opus-5-5"
    assert body["output_config"]["effort"] == "high"
    assert body["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert not {"temperature", "thinking", "tool_choice"} & body.keys()


async def test_parse_refusal_raises_llm_refusal(mock_api):
    mock_api(_json(_message([], "refusal", {"type": "refusal", "category": "cyber", "explanation": None})))
    with pytest.raises(llm.LLMRefusal, match="category=cyber"):
        await llm.parse(Verdict, system="sys", messages=[{"role": "user", "content": "hi"}])


async def test_parse_max_tokens_raises_llm_truncated(mock_api):
    mock_api(_json(_message([{"type": "text", "text": '{"label": "adm'}], "max_tokens")))
    with pytest.raises(llm.LLMTruncated, match="max_tokens=50"):
        await llm.parse(Verdict, system="sys", messages=[{"role": "user", "content": "hi"}], max_tokens=50)


async def test_parse_validates_only_the_fallback_models_answer(mock_api):
    fallback = {"type": "fallback", "from": {"model": "claude-opus-5-5"}, "to": {"model": "claude-opus-5"},
                "trigger": {"type": "refusal", "category": "cyber"}}
    mock_api(_json(_message([{"type": "text", "text": '{"label": "decl'}, fallback,
                             {"type": "text", "text": '{"label": "waitlist"}'}], "end_turn")))
    out = await llm.parse(Verdict, system="sys", messages=[{"role": "user", "content": "hi"}])
    assert out == Verdict(label="waitlist")


# ---------- stream_text ----------
def _stream_events(stop_reason: str, *, with_fallback: bool) -> list[dict]:
    msg = _message([], None) | {"usage": {"input_tokens": 10, "output_tokens": 0}}
    ev: list[dict] = [{"type": "message_start", "message": msg}]
    idx = 0

    def text_block(text: str):
        nonlocal idx
        ev.extend([
            {"type": "content_block_start", "index": idx, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": idx, "delta": {"type": "text_delta", "text": text}},
            {"type": "content_block_stop", "index": idx},
        ])
        idx += 1

    text_block("Partial from the first model")
    if with_fallback:
        block = {"type": "fallback", "from": {"model": "claude-opus-5-5"}, "to": {"model": "claude-opus-5"},
                 "trigger": {"type": "refusal", "category": "cyber"}}
        ev.extend([{"type": "content_block_start", "index": idx, "content_block": block},
                   {"type": "content_block_stop", "index": idx}])
        idx += 1
        text_block("Answer from the fallback")
    ev.extend([{"type": "message_delta", "delta": {"stop_reason": stop_reason, "stop_sequence": None},
                "usage": {"output_tokens": 12}},
               {"type": "message_stop"}])
    return ev


def _sse_reply(events: list[dict]):
    return lambda _req: httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=_sse(events))


async def test_stream_text_without_fallback(mock_api):
    mock_api(_sse_reply(_stream_events("end_turn", with_fallback=False)))
    chunks: list[str] = []
    resets: list[None] = []
    text = await llm.stream_text(system="sys", messages=[{"role": "user", "content": "hi"}],
                                 on_text=chunks.append, on_reset=lambda: resets.append(None))
    assert text == "Partial from the first model"
    assert "".join(chunks) == text
    assert resets == []


async def test_stream_text_fallback_resets_and_keeps_only_post_handoff_text(mock_api):
    requests = mock_api(_sse_reply(_stream_events("end_turn", with_fallback=True)))
    chunks: list[str] = []
    resets: list[int] = []
    text = await llm.stream_text(system="sys", messages=[{"role": "user", "content": "hi"}],
                                 on_text=chunks.append, on_reset=lambda: resets.append(len(chunks)))
    assert text == "Answer from the fallback"
    assert resets == [1]                      # reset fired after the first model's text, before the fallback's
    assert chunks == ["Partial from the first model", "Answer from the fallback"]
    assert json.loads(requests[0].content)["fallbacks"] == "default"


async def test_stream_text_refusal_raises(mock_api):
    mock_api(_sse_reply(_stream_events("refusal", with_fallback=True)))
    with pytest.raises(llm.LLMRefusal):
        await llm.stream_text(system="sys", messages=[{"role": "user", "content": "hi"}], on_text=lambda _t: None)
