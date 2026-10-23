from openai import AsyncOpenAI

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    # Lazy: app.config (B01) needs API keys at import time, so nothing is read until the first call.
    global _client
    if _client is None:
        from .config import settings

        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed_texts(texts: list[str], batch_size: int = 256) -> list[list[float]]:
    from .config import settings

    client = _get_client()
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        resp = await client.embeddings.create(model=settings.embedding_model, input=texts[i : i + batch_size])
        out.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
    return out


async def embed_one(text: str) -> list[float]:
    return (await embed_texts([text]))[0]
