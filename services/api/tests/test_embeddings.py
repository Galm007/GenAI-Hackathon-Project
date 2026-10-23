import json

import httpx
import pytest

from app import embeddings
from app.local_llm import LocalLLMError, settings


def fake_ollama(dim: int):
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        return httpx.Response(200, json={"embeddings": [[float(len(t))] * dim for t in body["input"]]})

    return seen, httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_embed_texts_batches_prefixes_and_keeps_order():
    seen, http = fake_ollama(settings.embedding_dim)
    out = await embeddings.embed_texts(["a", "bb", "ccc"], batch_size=2, client=http)
    assert [len(b["input"]) for b in seen] == [2, 1]
    assert all(t.startswith(embeddings.SIMILARITY_PREFIX) for b in seen for t in b["input"])
    assert len(out) == 3 and all(len(v) == 768 for v in out)
    assert out[0][0] < out[1][0] < out[2][0]


async def test_embed_texts_rejects_wrong_dimension():
    _, http = fake_ollama(384)
    with pytest.raises(LocalLLMError):
        await embeddings.embed_texts(["a"], client=http)
