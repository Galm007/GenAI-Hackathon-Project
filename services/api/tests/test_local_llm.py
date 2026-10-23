import json

import httpx
import pytest
from pydantic import BaseModel

from app.local_llm import LocalLLMError, chat_structured


class Out(BaseModel):
    answer: int


def client_returning(content: str, done_reason: str = "stop"):
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": content}, "done_reason": done_reason})

    return seen, httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_chat_structured_sends_schema_and_parses():
    seen, http = client_returning('{"answer": 4}')
    out = await chat_structured(Out, "sys", "usr", client=http)
    assert out == Out(answer=4)
    assert seen[0]["format"]["properties"]["answer"]["type"] == "integer"
    assert seen[0]["options"]["temperature"] == 0 and seen[0]["think"] is False


async def test_truncated_output_raises():
    _, http = client_returning('{"answer": ', done_reason="length")
    with pytest.raises(LocalLLMError):
        await chat_structured(Out, "sys", "usr", client=http)
