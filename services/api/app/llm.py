from __future__ import annotations

from collections.abc import Callable

from anthropic import AsyncAnthropic
from anthropic.types.beta import BetaMessage
from pydantic import BaseModel

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


def cached_system(text: str) -> list[dict]:
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


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
