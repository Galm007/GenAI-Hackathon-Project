"""app.llm's Meterless and Gemini path (app/openai_compat.py) against a mocked HTTP transport (no network, no key)."""
import base64
import json

import httpx
import pytest
from pydantic import BaseModel, ValidationError

from app import llm, openai_compat
from app.config import Settings, settings

MSGS = [{"role": "user", "content": "hi"}]


class Verdict(BaseModel):
    label: str


def _chat(content: str | None, finish: str = "stop", **message) -> dict:
    return {"id": "c1", "object": "chat.completion", "model": "m",
            "choices": [{"index": 0, "finish_reason": finish,
                         "message": {"role": "assistant", "content": content, **message}}]}


@pytest.fixture
def api(monkeypatch):
    """Point the provider layer at Gemini with a mocked transport; `install(*replies)` returns (requests, sleeps).

    Each reply is an httpx.Response or a callable(request) -> Response, used in order (the last one repeats)."""
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "test-gemini")
    sleeps: list[float] = []

    async def fake_sleep(s: float) -> None:
        sleeps.append(s)

    monkeypatch.setattr(openai_compat, "_sleep", fake_sleep)

    def install(*replies):
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            reply = replies[min(len(requests), len(replies)) - 1]
            return reply(request) if callable(reply) else reply

        monkeypatch.setattr(openai_compat, "http", httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        return requests, sleeps

    return install


def body(request: httpx.Request) -> dict:
    return json.loads(request.content)


def ok(content: str | None, finish: str = "stop", **message) -> httpx.Response:
    return httpx.Response(200, json=_chat(content, finish, **message))


# ---------- parse ----------
async def test_gemini_parse_sends_strict_schema_and_picks_the_model_by_effort(api):
    requests, _ = api(ok('{"label": "admit"}'))
    assert await llm.parse(Verdict, system="sys", messages=MSGS, effort="high") == Verdict(label="admit")
    await llm.parse(Verdict, system="sys", messages=MSGS, effort="low")

    first, second = requests
    assert str(first.url) == f"{openai_compat.GEMINI_BASE_URL}/chat/completions"
    assert first.headers["authorization"] == "Bearer test-gemini" and "meterless-app" not in first.headers
    b = body(first)
    assert b["model"] == settings.gemini_model and body(second)["model"] == settings.gemini_fast_model
    assert b["messages"] == [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
    assert b["response_format"]["type"] == "json_schema"
    assert b["response_format"]["json_schema"]["name"] == "Verdict"
    assert b["reasoning_effort"] == "high" and b["max_tokens"] == 16000


async def test_meterless_profile_sends_runtime_headers(api, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "meterless")
    monkeypatch.setattr(settings, "meterless_runtime_token", "rt-test")
    requests, _ = api(ok('{"label": "admit"}'))
    await llm.parse(Verdict, system="sys", messages=MSGS)
    r = requests[0]
    assert str(r.url) == "http://127.0.0.1:8088/v1/chat/completions"
    assert r.headers["authorization"] == "Bearer rt-test"
    assert r.headers["meterless-app"] == "adcom" and r.headers["meterless-scope"] == "user"
    assert r.headers["x-request-id"] and body(r)["model"] == "meterless/auto"


async def test_cache_control_is_dropped_and_text_blocks_are_joined(api):
    requests, _ = api(ok('{"label": "admit"}'))
    blocks = [{"type": "text", "text": "<docket>D</docket>", "cache_control": {"type": "ephemeral"}},
              {"type": "text", "text": "brief"}]
    await llm.parse(Verdict, system="sys", messages=[{"role": "user", "content": blocks}])
    assert body(requests[0])["messages"][1] == {"role": "user", "content": "<docket>D</docket>\n\nbrief"}


async def test_code_fenced_json_still_validates(api):
    api(ok('```json\n{"label": "waitlist"}\n```'))
    assert await llm.parse(Verdict, system="sys", messages=MSGS) == Verdict(label="waitlist")


async def test_rejected_schema_falls_back_to_the_schema_in_the_prompt(api):
    requests, _ = api(httpx.Response(400, json={"error": {"message": "Invalid JSON schema: $defs"}}),
                      ok('{"label": "deny"}'))
    assert await llm.parse(Verdict, system="sys", messages=MSGS) == Verdict(label="deny")
    prompted = body(requests[1])
    assert "response_format" not in prompted
    assert prompted["messages"][0]["content"].startswith("sys\n\nReply with one JSON object")
    assert '"label"' in prompted["messages"][0]["content"]


async def test_invalid_json_is_retried_once_in_prompt_mode(api):
    requests, _ = api(ok("not json"), ok('{"lab": 1}'), ok('{"label": "admit"}'))
    assert await llm.parse(Verdict, system="sys", messages=MSGS) == Verdict(label="admit")
    retry = body(requests[2])["messages"]
    assert retry[-2] == {"role": "assistant", "content": '{"lab": 1}'}
    assert retry[-1]["content"].startswith("That reply did not validate")


async def test_output_that_never_validates_raises_invalid_output(api):
    requests, _ = api(ok("not json"))
    with pytest.raises(llm.LLMInvalidOutput, match="Verdict failed validation twice"):
        await llm.parse(Verdict, system="sys", messages=MSGS)
    assert len(requests) == 3                          # strict, prompted, one retry


async def test_length_raises_truncated_without_retrying(api):
    requests, _ = api(ok('{"label": "ad', finish="length"))
    with pytest.raises(llm.LLMTruncated, match="Verdict hit max_tokens=50"):
        await llm.parse(Verdict, system="sys", messages=MSGS, max_tokens=50)
    assert len(requests) == 1


@pytest.mark.parametrize("reply", [ok(None, finish="content_filter"), ok(None, refusal="I can't help with that.")],
                         ids=["content_filter", "refusal_field"])
async def test_refusals_raise_llm_refusal(api, reply):
    api(reply)
    with pytest.raises(llm.LLMRefusal):
        await llm.parse(Verdict, system="sys", messages=MSGS)


async def test_auth_errors_are_not_retried(api):
    requests, _ = api(httpx.Response(401, json={"error": {"message": "API key not valid"}}))
    with pytest.raises(llm.LLMAuthError, match="401"):
        await llm.parse(Verdict, system="sys", messages=MSGS)
    assert len(requests) == 1


async def test_per_minute_rate_limit_waits_for_retry_after(api):
    requests, sleeps = api(httpx.Response(429, headers={"retry-after": "7"}, json={"error": {"message": "slow down"}}),
                           ok('{"label": "admit"}'))
    assert await llm.parse(Verdict, system="sys", messages=MSGS) == Verdict(label="admit")
    assert len(requests) == 2 and sleeps == [7.0]


async def test_daily_quota_is_not_retried(api):
    quota = {"error": {"code": 429, "message": (
        "Quota exceeded for metric: generate_content_free_tier_requests, "
        "quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier")}}
    requests, sleeps = api(httpx.Response(429, json=quota))
    with pytest.raises(llm.LLMQuotaExhausted):
        await llm.parse(Verdict, system="sys", messages=MSGS)
    assert len(requests) == 1 and sleeps == []


async def test_server_errors_are_retried_then_raise_unavailable(api):
    requests, sleeps = api(httpx.Response(500, text="internal"))
    with pytest.raises(llm.LLMUnavailable, match="500"):
        await llm.parse(Verdict, system="sys", messages=MSGS)
    assert len(requests) == openai_compat.ATTEMPTS and sleeps == [1.0, 2.0]   # only 503 moves to the fast model


OVERLOADED = httpx.Response(503, json={"error": {"code": 503, "status": "UNAVAILABLE",
                                                 "message": "This model is currently experiencing high demand."}})


async def test_overloaded_main_model_hands_the_call_to_the_fast_model(api):
    requests, sleeps = api(OVERLOADED, OVERLOADED, OVERLOADED, ok('{"label": "admit"}'))
    assert await llm.parse(Verdict, system="sys", messages=MSGS, effort="high") == Verdict(label="admit")
    assert [body(r)["model"] for r in requests] == [settings.gemini_model] * 3 + [settings.gemini_fast_model]
    assert sleeps == [1.0, 2.0]
    assert body(requests[-1])["response_format"]["json_schema"]["name"] == "Verdict"   # same request otherwise


async def test_fast_model_overloaded_too_raises_unavailable(api):
    requests, _ = api(OVERLOADED)
    with pytest.raises(llm.LLMUnavailable, match="503"):
        await llm.parse(Verdict, system="sys", messages=MSGS)
    assert len(requests) == 2 * openai_compat.ATTEMPTS


async def test_calls_already_on_the_fast_model_do_not_fall_back(api):
    requests, _ = api(OVERLOADED)
    with pytest.raises(llm.LLMUnavailable):
        await llm.parse(Verdict, system="sys", messages=MSGS, effort="low")
    assert {body(r)["model"] for r in requests} == {settings.gemini_fast_model}
    assert len(requests) == openai_compat.ATTEMPTS


async def test_meterless_has_no_fast_model_fallback(api, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "meterless")
    requests, _ = api(OVERLOADED)
    with pytest.raises(llm.LLMUnavailable):
        await llm.parse(Verdict, system="sys", messages=MSGS)
    assert len(requests) == openai_compat.ATTEMPTS


async def test_connection_errors_raise_unavailable(api):
    def refuse(request):
        raise httpx.ConnectError("connection refused", request=request)

    api(refuse)
    with pytest.raises(llm.LLMUnavailable, match="ConnectError"):
        await llm.parse(Verdict, system="sys", messages=MSGS)


async def test_rejected_reasoning_effort_is_retried_without_it(api):
    requests, _ = api(httpx.Response(400, json={"error": {"message": "reasoning_effort 'medium' is not supported"}}),
                      ok('{"label": "admit"}'))
    assert await llm.parse(Verdict, system="sys", messages=MSGS, effort="medium") == Verdict(label="admit")
    assert "reasoning_effort" in body(requests[0]) and "reasoning_effort" not in body(requests[1])
    assert "response_format" in body(requests[1])      # still the strict attempt


# ---------- PDFs ----------
def _pdf(text: str | None) -> str:
    """A one-page PDF with a real xref table, so pypdf reads it like an uploaded transcript."""
    stream = f"BT /F1 12 Tf 10 50 Td ({text}) Tj ET".encode() if text else b""
    objs = [b"<</Type/Catalog/Pages 2 0 R>>", b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 100]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
            b"<</Length %d>>stream\n%s\nendstream" % (len(stream), stream),
            b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (i, obj)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return base64.b64encode(bytes(out)).decode()


def _doc(b64: str) -> dict:
    return {"type": "document", "title": "Transcript",
            "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}


async def test_pdf_blocks_become_extracted_text(api):
    requests, _ = api(ok('{"label": "admit"}'))
    content = [_doc(_pdf("GPA 3.92 UW")), {"type": "text", "text": "Transcribe these materials."}]
    await llm.parse(Verdict, system="sys", messages=[{"role": "user", "content": content}])
    sent = body(requests[0])["messages"][1]["content"]
    assert sent == '<document title="Transcript">\nGPA 3.92 UW\n</document>\n\nTranscribe these materials.'


def test_pdf_without_a_text_layer_asks_for_an_extraction_warning():
    sent = openai_compat.to_chat("sys", [{"role": "user", "content": [_doc(_pdf(None))]}])[1]["content"]
    assert "No text layer could be extracted" in sent and "extraction warning" in sent


def test_unsupported_blocks_fail_loudly():
    with pytest.raises(ValueError, match="image blocks"):
        openai_compat.to_chat("sys", [{"role": "user", "content": [{"type": "image", "source": {}}]}])


# ---------- stream_text ----------
def _sse(*chunks: dict) -> httpx.Response:
    lines = "".join(f"data: {json.dumps(c)}\n\n" for c in chunks) + "data: [DONE]\n\n"
    return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=lines.encode())


def _delta(text: str | None = None, finish: str | None = None) -> dict:
    return {"choices": [{"index": 0, "delta": {"content": text} if text else {}, "finish_reason": finish}]}


async def test_stream_text_reassembles_deltas(api):
    requests, _ = api(_sse(_delta("The file "), _delta("is strong."), _delta(finish="stop")))
    chunks: list[str] = []
    resets: list[None] = []
    text = await llm.stream_text(system="sys", messages=MSGS, on_text=chunks.append,
                                 on_reset=lambda: resets.append(None))
    assert text == "The file is strong." and chunks == ["The file ", "is strong."] and resets == []
    b = body(requests[0])
    assert b["stream"] is True and b["model"] == settings.gemini_fast_model     # debate turns run at effort="low"


async def test_stream_text_content_filter_raises_refusal(api):
    api(_sse(_delta("Partial"), _delta(finish="content_filter")))
    with pytest.raises(llm.LLMRefusal):
        await llm.stream_text(system="sys", messages=MSGS, on_text=lambda _t: None)


async def test_stream_text_falls_back_to_the_fast_model_when_overloaded(api):
    requests, _ = api(OVERLOADED, OVERLOADED, OVERLOADED, _sse(_delta("Hello"), _delta(finish="stop")))
    text = await llm.stream_text(system="sys", messages=MSGS, on_text=lambda _t: None, effort="medium")
    assert text == "Hello"
    assert [body(r)["model"] for r in requests] == [settings.gemini_model] * 3 + [settings.gemini_fast_model]


async def test_stream_text_retries_only_before_the_first_token(api):
    requests, sleeps = api(httpx.Response(503, text="overloaded"), _sse(_delta("Hello"), _delta(finish="stop")))
    assert await llm.stream_text(system="sys", messages=MSGS, on_text=lambda _t: None) == "Hello"
    assert len(requests) == 2 and sleeps == [1.0]


# ---------- settings ----------
REQUIRED = {"supabase_url": "http://localhost:54321", "supabase_service_role_key": "k", "zetaris_agent_password": "p"}


def test_paid_provider_is_refused_without_team_consent():
    with pytest.raises(ValidationError, match="ALLOW_PAID_PROVIDERS"):
        Settings(_env_file=None, llm_provider="anthropic", allow_paid_providers=False, **REQUIRED)
    assert Settings(_env_file=None, llm_provider="anthropic", allow_paid_providers=True, **REQUIRED)


@pytest.mark.parametrize(("provider", "field"), [("meterless", "meterless_runtime_token"),
                                                 ("gemini", "gemini_api_key")])
def test_key_configured_follows_the_selected_provider(monkeypatch, provider, field):
    monkeypatch.setattr(settings, "llm_provider", provider)
    monkeypatch.setattr(settings, field, None)
    assert llm.key_configured() is False
    monkeypatch.setattr(settings, field, "set")
    assert llm.key_configured() is True
