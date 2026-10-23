# AdCom API

FastAPI + LangGraph backend, ETL and scripts. Spec: `MASTER_PLAN.md` (§0.4 layout, §0.5 dependencies).

## Quickstart

```bash
cp ../../.env.example ../../.env     # fill in keys; .env is git-ignored
uv sync
uv run ruff check .
uv run pytest -q
```

No keys? Use `FAKE_LLM=1 ZETARIS_ENABLED=false` for local runs (once the LLM wrapper lands).

Layout: `app/` (service), `etl/` (data pipeline), `scripts/` (CLIs), `tests/`.
