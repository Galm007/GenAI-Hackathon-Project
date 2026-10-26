from pathlib import Path
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parents[1]
ROOT = API_DIR.parents[1]


class Settings(BaseSettings):
    # Repo-root .env (README), with services/api/.env as an override; independent of the working directory.
    # hide_input_in_errors: a failed check must never echo keys from .env into logs.
    model_config = SettingsConfigDict(env_file=(ROOT / ".env", API_DIR / ".env"), extra="ignore",
                                      hide_input_in_errors=True)

    anthropic_api_key: str | None = None        # the SDK also reads ANTHROPIC_API_KEY directly
    tavily_api_key: str | None = None
    supabase_url: str
    supabase_service_role_key: str
    scorecard_api_key: str | None = None

    reasoning_model: str = "claude-opus-5-5"
    ollama_url: str = "http://localhost:11434"   # local Gemma models (app/local_llm.py also reads these)
    etl_model: str = "gemma4:e2b"                # local Reddit extraction (Ollama)
    cds_model: str = "gemma4:e2b"                # local CDS PDF extraction (A10)
    embedding_model: str = "embeddinggemma"
    embedding_dim: int = 768
    demo_mode: bool = False

    # §4.3
    cors_origins: list[str] = ["http://localhost:3000"]
    fake_llm: bool = False
    max_concurrent_runs: int = 6           # protects the API budget and rate limits during judging
    max_runs_per_day: int = 400
    run_idle_cancel_s: int = 180           # cancel a run if nobody has watched it for 3 minutes
    prewarm_schools: list[str] = ["uiuc", "cmu", "umich", "georgia_tech", "uc_berkeley"]

    # §2.10.5
    zetaris_url: str = "http://localhost:3000"            # the UI's API proxy; "http://ui:3000" inside compose
    zetaris_agent_email: str = "adcom-agent@adcom.local"
    zetaris_agent_password: str                           # .env only
    zetaris_admin_email: str = "admin@zetaris.com"        # setup scripts only
    zetaris_admin_password: str | None = None
    zetaris_gold_profile: str = "ADCOM_LAKE.gold.school_profile"
    zetaris_enabled: bool = True                          # False → every read falls back to Supabase (§2.10.10)

    # §1.7.2, D-043: Meterless primary, Gemini's free tier as the alternative, Claude paid and off by default
    llm_provider: Literal["meterless", "gemini", "anthropic"] = "meterless"
    allow_paid_providers: bool = False
    meterless_base_url: str = "http://127.0.0.1:8088/v1"
    meterless_runtime_token: str | None = None            # Nightshift Console; never the NVIDIA key
    meterless_model: str = "meterless/auto"
    meterless_app: str = "adcom"
    gemini_api_key: str | None = None                     # AI Studio key from a Cloud project with no billing account
    gemini_model: str = "gemini-3.8-flash"                # extraction, grading, briefs, delta
    gemini_fast_model: str = "gemini-3.5-flash-lite"      # effort="low": debate turns and the SQL loop

    @model_validator(mode="after")
    def _paid_provider_needs_consent(self) -> Self:
        if self.llm_provider == "anthropic" and not self.allow_paid_providers:
            raise ValueError("LLM_PROVIDER=anthropic is paid: set ALLOW_PAID_PROVIDERS=true only after the team "
                             "agrees (AGENTS.md §4), or use meterless or gemini")
        return self


settings = Settings()
