"""OpenAI-compatible chat providers for the live agents: Meterless Nightshift (primary) and Gemini's free tier.

`llm.parse` / `llm.stream_text` dispatch here unless LLM_PROVIDER=anthropic, and callers see the same exceptions
as on the Anthropic path (plan §1.7.2, DECISIONS D-046).
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, ValidationError
from pypdf import PdfReader

from . import llm  # circular on purpose: llm dispatches here, and these raise llm's exceptions
from .config import settings

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
ATTEMPTS = 3                          # per-minute 429s, 5xx and connection errors
MAX_WAIT_S = 30.0
MODELS_TIMEOUT = httpx.Timeout(5.0)   # discovery loads no model, so a slow answer means an unhealthy Runtime

log = logging.getLogger("openai_compat")
http = httpx.AsyncClient()
_sleep = asyncio.sleep                # replaced in tests


@dataclass(frozen=True)
class Profile:
    name: str
    base_url: str
    headers: dict[str, str]
    model: str                        # medium/high effort
    fast_model: str                   # effort="low": debate turns and the SQL loop, to save free-tier quota


def meterless_profile() -> Profile:
    return Profile(
        "meterless", settings.meterless_base_url.rstrip("/"),
        {"Authorization": f"Bearer {settings.meterless_runtime_token or ''}",
         "meterless-app": settings.meterless_app, "meterless-scope": "user"},
        settings.meterless_model, settings.meterless_model)


def profile() -> Profile:
    if settings.llm_provider == "meterless":
        return meterless_profile()
    return Profile("gemini", GEMINI_BASE_URL, {"Authorization": f"Bearer {settings.gemini_api_key or ''}"},
                   settings.gemini_model, settings.gemini_fast_model)


def timeout(max_tokens: int) -> httpx.Timeout:
    """Room for a model load (§1.7.2) and for long outputs: the same budget llm.parse_timeout gives Claude."""
    return httpx.Timeout(max(180.0, 3600.0 * max_tokens / 128_000), connect=5.0)


# ---------- messages ----------
def _pdf_text(block: dict) -> str:
    # Gemini's compatibility layer documents no PDF input and Nemotron lanes are text-only, so PDFs become text.
    reader = PdfReader(io.BytesIO(base64.b64decode(block["source"]["data"])))
    text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if not text:
        text = ("[No text layer could be extracted from this PDF; it may be a scan. "
                "Add an extraction warning saying so.]")
    return f'<document title="{block.get("title") or "Document"}">\n{text}\n</document>'


def _text(content: str | list[dict]) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:                                     # cache_control is dropped: Gemini caches implicitly
        if block["type"] == "text":
            parts.append(block["text"])
        elif block["type"] == "document":
            parts.append(_pdf_text(block))
        else:
            raise ValueError(f"{block['type']} blocks are not supported on OpenAI-compatible providers")
    return "\n\n".join(parts)


def to_chat(system: str, messages: list[dict]) -> list[dict]:
    return [{"role": "system", "content": system},
            *({"role": m["role"], "content": _text(m["content"])} for m in messages)]


# ---------- transport ----------
def _raise_for(resp: httpx.Response, p: Profile) -> None:
    status, detail = resp.status_code, resp.text[:300]
    if status < 400:
        return
    if status in (401, 403):
        raise llm.LLMAuthError(f"{p.name} rejected the credentials ({status})")
    if status == 429:
        # Gemini names the exhausted quota, e.g. GenerateRequestsPerDayPerProjectPerModel-FreeTier (verify)
        if "perday" in resp.text.lower().replace(" ", "").replace("_", ""):
            raise llm.LLMQuotaExhausted(f"{p.name} daily quota used up: {detail}")
        try:
            retry_after = float(resp.headers.get("retry-after", ""))
        except ValueError:
            retry_after = None
        raise llm.LLMRateLimited(f"{p.name} rate limit: {detail}", retry_after=retry_after)
    if status >= 500:
        raise llm.LLMUnavailable(f"{p.name} returned {status}: {detail}", status=status)
    raise llm.LLMBadRequest(f"{p.name} returned {status}: {detail}")


async def _retrying[T](call: Callable[[], Awaitable[T]], may_retry: Callable[[], bool] = lambda: True) -> T:
    for attempt in range(ATTEMPTS):
        try:
            return await call()
        except (llm.LLMRateLimited, llm.LLMUnavailable) as exc:
            if attempt == ATTEMPTS - 1 or not may_retry():
                raise
            wait = getattr(exc, "retry_after", None) or 2.0 ** attempt
            await _sleep(min(wait, MAX_WAIT_S))
    raise AssertionError("unreachable")


def _overloaded_main(p: Profile, body: dict, exc: llm.LLMUnavailable) -> bool:
    """Gemini's free tier answers 503 "high demand" on the bigger Flash models while the fast model still has
    capacity (D-048), so a call that still gets 503 after its retries moves to the fast model once."""
    return p.name == "gemini" and exc.status == 503 and body["model"] != p.fast_model


def _headers(p: Profile) -> dict[str, str]:
    return p.headers | ({"X-Request-ID": str(uuid.uuid4())} if p.name == "meterless" else {})


NEMOTRON_LANES = {"meterless/fast", "meterless/cheap", "meterless/local"}     # all serve nemotron-3.5-bolt-e4b (D-058)


def _body(p: Profile, chat: list[dict], *, effort: str, max_tokens: int, model: str | None) -> dict:
    model = model or (p.fast_model if effort == "low" else p.model)
    body = {"model": model, "messages": chat, "max_tokens": max_tokens, "reasoning_effort": effort}
    if p.name == "meterless" and effort == "low" and model in NEMOTRON_LANES:
        # effort="low" means no thinking on the Nemotron lanes: 1-2 s instead of 12-15 s for the same request. The model
        # may still write a [[scratchpad]] into its answer, which strip_reasoning removes (D-060). Lane-gated because
        # other lanes may reject the field.
        body["chat_template_kwargs"] = {"enable_thinking": False}
    return body


REASONING_OPENERS = ("[[scratchpad]]", "<scratchpad>", "<think>")
REASONING_CLOSERS = ("</scratchpad>", "</think>")


def strip_reasoning(text: str) -> str:
    """Some Nemotron lanes write their reasoning into the content, as <think>…</think> or a [[scratchpad]] block
    (or only the closing tag): keep what follows the last closer."""
    end = max((text.rfind(c) + len(c) for c in REASONING_CLOSERS if c in text), default=0)
    return text[end:].lstrip() if end else text


def _holding_reasoning(text: str) -> bool:
    """True while the text so far is (the start of) an opener that has not been closed yet: show nothing."""
    s = text.lstrip()
    closed = any(c in text for c in REASONING_CLOSERS)
    return not closed and any(s.startswith(o) or o.startswith(s) for o in REASONING_OPENERS)


async def _choice(p: Profile, body: dict, name: str) -> dict:
    """One non-streamed completion's first choice. A rejected `reasoning_effort` level is retried once without it,
    and an overloaded Gemini main model hands the call to the fast model."""
    async def call() -> httpx.Response:
        try:
            resp = await http.post(f"{p.base_url}/chat/completions", json=body, headers=_headers(p),
                                   timeout=timeout(body["max_tokens"]))
        except httpx.TransportError as exc:
            raise llm.LLMUnavailable(f"{p.name} unreachable: {type(exc).__name__}") from exc
        _raise_for(resp, p)
        return resp

    async def send() -> httpx.Response:
        nonlocal body
        try:
            return await _retrying(call)
        except llm.LLMBadRequest as exc:
            if "reasoning_effort" not in body or "reasoning" not in str(exc):
                raise
            body = {k: v for k, v in body.items() if k != "reasoning_effort"}
            return await _retrying(call)

    try:
        resp = await send()
    except llm.LLMUnavailable as exc:
        if not _overloaded_main(p, body, exc):
            raise
        log.warning("%s overloaded for %s; retrying on %s", body["model"], name, p.fast_model)
        body = body | {"model": p.fast_model}
        resp = await send()
    return resp.json()["choices"][0]


async def meterless_models() -> list[str]:
    """GET /v1/models on the Nightshift Runtime: its health check (§1.7.2). Returns the listed model and route ids;
    401/403 raises LLMAuthError, no answer raises LLMUnavailable. Checked whatever LLM_PROVIDER is selected."""
    p = meterless_profile()
    try:
        resp = await http.get(f"{p.base_url}/models", headers=_headers(p), timeout=MODELS_TIMEOUT)
    except httpx.TransportError as exc:
        raise llm.LLMUnavailable(f"{p.name} unreachable: {type(exc).__name__}") from exc
    _raise_for(resp, p)
    try:
        return [m["id"] for m in resp.json()["data"] if m.get("id")]
    except (ValueError, KeyError, TypeError, AttributeError) as exc:   # something else is listening on that port
        raise llm.LLMUnavailable(f"{p.name} /models did not return a model list") from exc


async def _complete(p: Profile, body: dict, name: str) -> str:
    choice = await _choice(p, body, name)
    message = choice.get("message") or {}
    if choice.get("finish_reason") == "length":
        raise llm.LLMTruncated(f"{name} hit max_tokens={body['max_tokens']}")
    if choice.get("finish_reason") == "content_filter" or message.get("refusal"):
        raise llm.LLMRefusal(f"{name} refused ({p.name})")
    return strip_reasoning(message.get("content") or "")


# ---------- parse ----------
def _json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    return text.strip()


async def parse[T: BaseModel](
    schema: type[T], *, system: str, messages: list[dict], effort: str, max_tokens: int, model: str | None,
) -> T:
    """Strict JSON schema first; if the provider rejects it or the reply doesn't validate, the schema goes in the
    system prompt and a reply that still fails validation is retried once (§1.7.2)."""
    p = profile()
    chat = await asyncio.to_thread(to_chat, system, messages)
    base = _body(p, chat, effort=effort, max_tokens=max_tokens, model=model)
    try:
        strict = base | {"response_format": {"type": "json_schema", "json_schema": {
            "name": schema.__name__, "schema": schema.model_json_schema(), "strict": True}}}
        return schema.model_validate_json(_json_text(await _complete(p, strict, schema.__name__)))
    except (llm.LLMBadRequest, ValidationError):
        pass

    prompted = [{"role": "system", "content": (
        f"{system}\n\nReply with one JSON object that validates against this JSON Schema, and nothing else "
        f"(no prose, no code fence):\n{json.dumps(schema.model_json_schema())}")}, *chat[1:]]
    reply = await _complete(p, base | {"messages": prompted}, schema.__name__)
    try:
        return schema.model_validate_json(_json_text(reply))
    except ValidationError as exc:
        retry = [*prompted, {"role": "assistant", "content": reply}, {"role": "user", "content": (
            f"That reply did not validate against the schema:\n{exc}\nReply again with only the corrected JSON.")}]
        reply = await _complete(p, base | {"messages": retry}, schema.__name__)
    try:
        return schema.model_validate_json(_json_text(reply))
    except ValidationError as exc:
        raise llm.LLMInvalidOutput(f"{schema.__name__} failed validation twice ({p.name})") from exc


# ---------- stream_text ----------
async def stream_text(
    *, system: str, messages: list[dict], on_text: Callable[[str], None], effort: str, max_tokens: int,
    model: str | None, on_reset: Callable[[], None] | None = None,
) -> str:
    """Server-sent events. There are no fallback blocks here; `on_reset` fires only when a lane leaks its reasoning
    into the stream and the text shown so far has to be dropped. A failure is retried only before the first token
    reaches the browser."""
    p = profile()
    body = _body(p, to_chat(system, messages), effort=effort, max_tokens=max_tokens, model=model) | {"stream": True}
    parts: list[str] = []
    shown = [""]                                  # the text the browser currently has for this turn

    async def call() -> str | None:
        finish = None
        try:
            async with http.stream("POST", f"{p.base_url}/chat/completions", json=body, headers=_headers(p),
                                   timeout=timeout(max_tokens)) as resp:
                if resp.status_code >= 400:
                    await resp.aread()
                    _raise_for(resp, p)
                async for line in resp.aiter_lines():
                    data = line.removeprefix("data:").strip()
                    if not line.startswith("data:") or not data:
                        continue
                    if data == "[DONE]":
                        break
                    for choice in json.loads(data).get("choices", []):
                        if text := (choice.get("delta") or {}).get("content"):
                            parts.append(text)
                            acc = "".join(parts)
                            visible = "" if _holding_reasoning(acc) else strip_reasoning(acc)
                            if not visible.startswith(shown[0]):         # reasoning that was already on screen
                                shown[0] = ""
                                if on_reset:
                                    on_reset()
                            if len(visible) > len(shown[0]):
                                on_text(visible[len(shown[0]):])
                                shown[0] = visible
                        finish = choice.get("finish_reason") or finish
        except httpx.TransportError as exc:
            raise llm.LLMUnavailable(f"{p.name} unreachable: {type(exc).__name__}") from exc
        return finish

    try:
        finish = await _retrying(call, may_retry=lambda: not parts)
    except llm.LLMUnavailable as exc:
        if parts or not _overloaded_main(p, body, exc):
            raise
        log.warning("%s overloaded for a stream; retrying on %s", body["model"], p.fast_model)
        body = body | {"model": p.fast_model}
        finish = await _retrying(call, may_retry=lambda: not parts)
    if finish == "content_filter":
        raise llm.LLMRefusal("debate turn refused")
    text = strip_reasoning("".join(parts))
    if not text.strip() or _holding_reasoning(text):
        raise llm.LLMInvalidOutput(f"{p.name} returned an empty debate stream (or only reasoning)")
    return text


# ---------- chat_with_tools ----------
def _arguments(call: dict) -> dict:
    try:
        args = json.loads(call["function"].get("arguments") or "{}")
    except json.JSONDecodeError:
        return {}                                          # the tool rejects it and the model can try again
    return args if isinstance(args, dict) else {}


async def chat_with_tools(
    *, system: str, messages: list[dict], tools: list[dict], name: str, effort: str, max_tokens: int,
) -> llm.ToolTurn:
    """OpenAI function calling. Assistant turns are replayed as returned, so Gemini's thought signatures on its tool
    calls survive; tool results have no error flag here, and their text says when a query was rejected."""
    p = profile()
    chat: list[dict] = [{"role": "system", "content": system}]
    for m in messages:
        if m["role"] == "assistant":
            chat.append(m["turn"].native)
        elif m["role"] == "tool_results":
            chat.extend({"role": "tool", "tool_call_id": r["id"], "content": r["content"]} for r in m["results"])
        else:
            chat.append({"role": m["role"], "content": _text(m["content"])})
    body = _body(p, chat, effort=effort, max_tokens=max_tokens, model=None) | {
        "tools": [{"type": "function", "function": t} for t in tools]}

    choice = await _choice(p, body, name)
    message = choice.get("message") or {}
    if choice.get("finish_reason") == "content_filter" or message.get("refusal"):
        raise llm.LLMRefusal(f"{name} refused ({p.name})")
    raw_calls = message.get("tool_calls") or []
    native = {"role": "assistant", "content": message.get("content"),
              **({"tool_calls": raw_calls} if raw_calls else {})}
    calls = [llm.ToolCall(c["id"], c["function"]["name"], _arguments(c)) for c in raw_calls]
    return llm.ToolTurn(text=message.get("content") or "", native=native,
                        calls=[] if choice.get("finish_reason") == "length" else calls)
