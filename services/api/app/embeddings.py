import httpx

from .local_llm import LocalLLMError, settings

# EmbeddingGemma is prompt-conditioned. Twins and live applicants must be embedded identically so that
# their vectors share one space, so both sides use the symmetric "sentence similarity" task prefix.
SIMILARITY_PREFIX = "task: sentence similarity | query: "


async def embed_texts(
    texts: list[str], batch_size: int = 32, client: httpx.AsyncClient | None = None
) -> list[list[float]]:
    owns = client is None
    http = client or httpx.AsyncClient(timeout=300)
    out: list[list[float]] = []
    try:
        for i in range(0, len(texts), batch_size):
            batch = [SIMILARITY_PREFIX + t for t in texts[i : i + batch_size]]
            resp = await http.post(
                f"{settings.ollama_url}/api/embed",
                json={"model": settings.embedding_model, "input": batch, "truncate": True, "keep_alive": "5m"},
            )
            resp.raise_for_status()
            vectors = resp.json()["embeddings"]
            if len(vectors) != len(batch) or any(len(v) != settings.embedding_dim for v in vectors):
                raise LocalLLMError(f"expected {len(batch)} vectors of {settings.embedding_dim} dims")
            out.extend(vectors)
    finally:
        if owns:
            await http.aclose()
    return out


async def embed_one(text: str) -> list[float]:
    return (await embed_texts([text]))[0]
