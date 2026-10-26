"""Runtime readiness uses authenticated discovery, never a billable completion."""
import logging

import httpx

from .config import settings

log = logging.getLogger(__name__)


async def probe() -> dict:
    if settings.llm_provider != "meterless":
        return {"ready": False, "status": "not_selected"}
    if not settings.meterless_runtime_token or settings.meterless_runtime_token == "rt-local":
        return {"ready": False, "status": "missing_token"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.meterless_base_url.rstrip('/')}/models", headers={
                "Authorization": f"Bearer {settings.meterless_runtime_token}",
                "meterless-app": settings.meterless_app, "meterless-scope": "user"})
        if response.status_code in (401, 403):
            return {"ready": False, "status": "unauthorized"}
        response.raise_for_status()
        body = response.json()
        models = body.get("data", []) if isinstance(body, dict) else []
        ids = {row["id"] for row in models if isinstance(row, dict) and isinstance(row.get("id"), str)}
        ready = settings.meterless_model in ids
        return {"ready": ready, "status": "ready" if ready else "model_unavailable"}
    except (httpx.HTTPError, ValueError, TypeError):
        return {"ready": False, "status": "unreachable"}


async def startup_check() -> None:
    result = await probe()
    log.info("Meterless discovery: %s", result["status"])
