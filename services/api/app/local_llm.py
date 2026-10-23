"""Local Gemma models served by Ollama: settings plus a thin client for structured chat and embeddings.

Everything runs on this machine (http://localhost:11434 by default); no API key is involved.
"""
from __future__ import annotations

from pathlib import Path

import httpx
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parents[1]
ROOT = API_DIR.parents[1]

class OllamaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / ".env", API_DIR / ".env"), extra="ignore")

    ollama_url: str = "http://localhost:11434"
    etl_model: str = "gemma4:e2b"                 # structured extraction of Reddit posts
    cds_model: str = "gemma4:e2b"                 # Common Data Set extraction (A10); bump to gemma4:e4b if C7 misreads
    embedding_model: str = "embeddinggemma"       # 768-d, must match vector(768) in the migrations
    embedding_dim: int = 768


settings = OllamaSettings()


class LocalLLMError(RuntimeError):
    pass


async def chat_structured[M: BaseModel](
    model_cls: type[M],
    system: str,
    user: str,
    *,
    model: str | None = None,
    num_ctx: int = 8192,
    num_predict: int = 4096,
    client: httpx.AsyncClient | None = None,
) -> M:
    """One deterministic chat turn whose output is constrained to `model_cls`'s JSON schema (Ollama `format`)."""
    body = {
        "model": model or settings.etl_model,
        "stream": False,
        "think": False,
        "format": model_cls.model_json_schema(),
        "options": {"temperature": 0, "num_ctx": num_ctx, "num_predict": num_predict},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    owns = client is None
    http = client or httpx.AsyncClient(timeout=600)
    try:
        resp = await http.post(f"{settings.ollama_url}/api/chat", json=body)
        resp.raise_for_status()
        payload = resp.json()
    finally:
        if owns:
            await http.aclose()
    if payload.get("done_reason") == "length":
        raise LocalLLMError("output hit num_predict before the JSON closed; raise num_predict or shorten the post")
    return model_cls.model_validate_json(payload["message"]["content"])
