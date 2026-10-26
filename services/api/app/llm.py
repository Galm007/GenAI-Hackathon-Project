from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import anthropic
from anthropic import AsyncAnthropic, Timeout
from anthropic.types.beta import BetaMessage
from pydantic import BaseModel

from . import openai_compat
from .config import settings

# Server-side refusal fallback: if a safety classifier declines, the API re-runs the request on Anthropic's
# recommended fallback model inside the same call. "default" routes by refusal category. Remove these two
# arguments below to opt out.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

client = AsyncAnthropic(api_key=settings.anthropic_api_key, max_retries=4)   # SDK retries 408/409/429/5xx


class LLMRefusal(RuntimeError):
    """The model (and any fallback) declined. Branch on stop_reason, never on content shape."""


class LLMTruncated(RuntimeError):
    """Output hit max_tokens before the structured output was complete."""


class LLMProviderError(RuntimeError):
    """A failed request to an OpenAI-compatible provider (Meterless, Gemini); see openai_compat.py."""


class LLMUnavailable(LLMProviderError):
    """Connection error, timeout or 5xx (`status` is set for 5xx)."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class LLMRateLimited(LLMProviderError):
    """Per-minute 429; retried after Retry-After."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class LLMQuotaExhausted(LLMProviderError):
    """Daily free-tier quota used up; not retried."""


class LLMAuthError(LLMProviderError):
    """401/403: missing or wrong key or Runtime token."""


class LLMBadRequest(LLMProviderError):
    """Any other 4xx."""


class LLMInvalidOutput(LLMProviderError):
    """Structured output that still failed validation after the retry."""


# What a node catches to degrade instead of failing, and what the graph's node-level RetryPolicy retries.
PROVIDER_ERRORS = (anthropic.APIError, LLMProviderError)
RETRYABLE = (anthropic.APIConnectionError, anthropic.InternalServerError, anthropic.RateLimitError,
             LLMUnavailable, LLMRateLimited)


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class ToolTurn:
    """One model turn in a tool loop: its text, the calls to run (empty once it is done), and the assistant message in
    the provider's own shape, replayed unchanged next round (thinking blocks, Gemini's thought signatures)."""
    text: str
    calls: list[ToolCall]
    native: Any


def key_configured() -> bool:
    """Whether the selected provider has its credential (reported by /api/health)."""
    return bool({"meterless": settings.meterless_runtime_token, "gemini": settings.gemini_api_key,
                 "anthropic": settings.anthropic_api_key}[settings.llm_provider])


def cached_system(text: str) -> list[dict]:
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def parse_timeout(max_tokens: int) -> Timeout:
    """Explicit per-request timeout for a non-streamed parse. Without one, the SDK refuses any request whose
    max_tokens implies over 10 minutes (about 21K tokens), which Node 1's 32K/24K calls do (see DECISIONS D-040).
    Uses the SDK's own estimate: an hour for 128K output tokens, never below its 10-minute default."""
    return Timeout(max(600.0, 3600.0 * max_tokens / 128_000), connect=5.0)


async def parse[T: BaseModel](
    schema: type[T],
    *,
    system: str,
    messages: list[dict],
    effort: str = "medium",
    max_tokens: int = 16000,
    model: str | None = None,
) -> T:
    """Structured output validated into `schema`. Claude Opus 5.5 always thinks; `effort` sets the depth."""
    if settings.llm_provider != "anthropic":                 # Meterless or Gemini (§1.7.2)
        return await openai_compat.parse(schema, system=system, messages=messages, effort=effort,
                                         max_tokens=max_tokens, model=model)
    # The SDK validates every text block eagerly, which raises a bare ValidationError on truncated output and on
    # the declined model's partial text before a fallback block. Read the unparsed message instead, branch on
    # stop_reason, then validate only the final answer (see DECISIONS D-012).
    raw = await client.beta.messages.with_raw_response.parse(
        model=model or settings.reasoning_model,
        max_tokens=max_tokens,
        system=cached_system(system),
        messages=messages,
        output_format=schema,
        output_config={"effort": effort},
        betas=[FALLBACK_BETA],
        fallbacks="default",
        timeout=parse_timeout(max_tokens),
    )
    resp = BetaMessage.model_validate(raw.http_response.json())
    if resp.stop_reason == "refusal":
        category = getattr(resp.stop_details, "category", None) if resp.stop_details else None
        raise LLMRefusal(f"{schema.__name__} refused (category={category})")
    if resp.stop_reason == "max_tokens":
        raise LLMTruncated(f"{schema.__name__} hit max_tokens={max_tokens}")
    return schema.model_validate_json(_final_text(resp.content))


def _final_text(content: list) -> str:
    texts: list[str] = []
    for block in content:
        if block.type == "fallback":
            texts = []                       # keep only text produced after the last hand-off
        elif block.type == "text":
            texts.append(block.text)
    return "".join(texts)


async def stream_text(
    *,
    system: str,
    messages: list[dict],
    on_text: Callable[[str], None],
    on_reset: Callable[[], None] | None = None,
    effort: str = "low",
    max_tokens: int = 4000,
    model: str | None = None,
) -> str:
    """Stream plain text token-by-token. Returns the final text from the model that actually answered."""
    if settings.llm_provider != "anthropic":
        return await openai_compat.stream_text(system=system, messages=messages, on_text=on_text, effort=effort,
                                               max_tokens=max_tokens, model=model)
    async with client.beta.messages.stream(
        model=model or settings.reasoning_model,
        max_tokens=max_tokens,
        system=cached_system(system),
        messages=messages,
        output_config={"effort": effort},
        betas=[FALLBACK_BETA],
        fallbacks="default",
    ) as stream:
        async for event in stream:
            if event.type == "text":
                on_text(event.text)
            elif event.type == "content_block_start" and event.content_block.type == "fallback":
                # Mid-stream refusal handed off to the fallback model: the partial text before this point
                # is discarded, so the UI must clear the bubble.
                if on_reset:
                    on_reset()
        final = await stream.get_final_message()

    if final.stop_reason == "refusal":
        raise LLMRefusal("debate turn refused")
    return _final_text(final.content)


async def chat_with_tools(
    *,
    system: str,
    messages: list[dict],
    tools: list[dict],
    name: str = "tool turn",
    effort: str = "low",
    max_tokens: int = 8000,
) -> ToolTurn:
    """One round of a tool loop (Node 2's Zetaris SQL tool, §2.10.7). `messages` is provider-neutral:
    {"role": "user", "content": str}, {"role": "assistant", "turn": ToolTurn} and
    {"role": "tool_results", "results": [{"id", "content", "is_error"}]}. `tools` are
    {"name", "description", "parameters"} with a strict JSON schema."""
    if settings.llm_provider != "anthropic":
        return await openai_compat.chat_with_tools(system=system, messages=messages, tools=tools, name=name,
                                                   effort=effort, max_tokens=max_tokens)
    resp = await client.beta.messages.create(
        model=settings.reasoning_model,
        max_tokens=max_tokens,
        system=cached_system(system),
        tools=[{"name": t["name"], "description": t["description"], "strict": True, "input_schema": t["parameters"]}
               for t in tools],
        messages=[_anthropic_message(m) for m in messages],
        output_config={"effort": effort},
        betas=[FALLBACK_BETA],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        raise LLMRefusal(f"{name} refused")
    calls = [ToolCall(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"]
    return ToolTurn(text=_final_text(resp.content), calls=calls if resp.stop_reason == "tool_use" else [],
                    native=resp.content)


def _anthropic_message(m: dict) -> dict:
    if m["role"] == "assistant":
        return {"role": "assistant", "content": m["turn"].native}
    if m["role"] == "tool_results":                       # all results go back in ONE user message
        return {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": r["id"], "content": r["content"],
             **({"is_error": True} if r.get("is_error") else {})} for r in m["results"]]}
    return m
