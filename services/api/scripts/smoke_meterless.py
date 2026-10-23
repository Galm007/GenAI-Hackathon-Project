"""Check the Meterless Nightshift connection: python -m scripts.smoke_meterless  (run from services/api).

Three checks against the Runtime contract in plan §1.7.2: settings present, GET /v1/models authorizes and lists
models, and one real POST /v1/chat/completions answers. The Runtime token is never printed.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parents[1]
ROOT = API_DIR.parents[1]
PLACEHOLDERS = {"", "...", "rt-local", "your-real-nightshift-runtime-token", "<your-real-nightshift-runtime-token>"}
TIMEOUT_S = 180            # the Runtime may load a model on the first request


class MeterlessSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / ".env", API_DIR / ".env"), extra="ignore")

    meterless_base_url: str = "http://127.0.0.1:8088/v1"
    meterless_runtime_token: str = ""
    meterless_model: str = "meterless/auto"
    meterless_app: str = "adcom"


def headers(cfg: MeterlessSettings) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {cfg.meterless_runtime_token}",
        "meterless-app": cfg.meterless_app,
        "meterless-scope": "user",
        "X-Request-ID": str(uuid.uuid4()),
    }


def check_config(cfg: MeterlessSettings) -> str:
    if cfg.meterless_runtime_token.strip() in PLACEHOLDERS:
        raise AssertionError(
            "METERLESS_RUNTIME_TOKEN is missing or a placeholder: copy the real key from Nightshift's Console")
    return cfg.meterless_base_url


async def check_models(http: httpx.AsyncClient, cfg: MeterlessSettings) -> str:
    resp = await http.get(f"{cfg.meterless_base_url.rstrip('/')}/models", headers=headers(cfg))
    if resp.status_code in (401, 403):
        raise AssertionError(f"unauthorized ({resp.status_code}): the Runtime token does not match this Nightshift")
    resp.raise_for_status()
    ids = [m.get("id", "?") for m in resp.json().get("data", [])]
    if not ids:
        raise AssertionError("authorized, but /v1/models lists no models: add a lane in Nightshift (NIGHT > LANES)")
    shown = ", ".join(ids[:6]) + (" ..." if len(ids) > 6 else "")
    return f"{len(ids)} models: {shown}"


async def check_chat(http: httpx.AsyncClient, cfg: MeterlessSettings) -> str:
    resp = await http.post(
        f"{cfg.meterless_base_url.rstrip('/')}/chat/completions",
        headers=headers(cfg) | {"Content-Type": "application/json"},
        json={
            "model": cfg.meterless_model,
            "messages": [{"role": "user", "content": "Reply with one sentence confirming this connection works."}],
        },
    )
    resp.raise_for_status()
    body = resp.json()
    text = (body.get("choices") or [{}])[0].get("message", {}).get("content")
    if not text:
        raise AssertionError("the Runtime answered but returned no message")
    served_by = body.get("model", "unknown")          # which model actually answered: the Nemotron evidence
    return f"answered by {served_by}: {text.strip()[:80]}"


async def run(cfg: MeterlessSettings, http: httpx.AsyncClient | None = None) -> list[tuple[str, str, str]]:
    results: list[tuple[str, str, str]] = []
    owns = http is None
    http = http or httpx.AsyncClient(timeout=TIMEOUT_S)
    try:
        for name, fn in (("Meterless settings", None), ("Nightshift lists models", check_models),
                         ("Nightshift answers a chat request", check_chat)):
            try:
                detail = check_config(cfg) if fn is None else await fn(http, cfg)
                results.append(("PASS", name, detail))
            except (AssertionError, httpx.HTTPError) as exc:
                results.append(("FAIL", name, str(exc)[:200]))
                break                                        # later checks depend on this one
    finally:
        if owns:
            await http.aclose()
    return results


def main() -> int:
    results = asyncio.run(run(MeterlessSettings()))
    for status, name, detail in results:
        print(f"{status} {name}: {detail}")
    return 0 if results and all(s == "PASS" for s, _, _ in results) and len(results) == 3 else 1


if __name__ == "__main__":
    sys.exit(main())
