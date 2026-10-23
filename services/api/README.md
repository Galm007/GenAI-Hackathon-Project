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

## Local models (Reddit extraction and embeddings)

Both run on this machine through [Ollama](https://ollama.com), with no API key: `gemma4:e2b` (Reddit and CDS extraction) and `embeddinggemma` (768-d embeddings). Settings and the client are in `app/local_llm.py`; `ETL_MODEL`, `EMBEDDING_MODEL` and `OLLAMA_URL` come from `.env`.

```bash
# one-time: install Ollama (any method), then
ollama pull gemma4:e2b && ollama pull embeddinggemma
ollama serve                         # leave running; models load on first use
```

Loading a model uses the GPU and several GB of RAM, so close heavy apps first. Extraction pauses the Zetaris containers and restarts them afterwards (`etl/resources.py`); set `ADCOM_KEEP_ZETARIS=1` to disable that. The Claude API (`ANTHROPIC_API_KEY`) is only needed for the live agents (Track B).
