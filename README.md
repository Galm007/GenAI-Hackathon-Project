# AdCom

An autonomous multi-agent university admissions committee simulator, built in 36 hours by four people. The full spec is [`MASTER_PLAN.md`](MASTER_PLAN.md); the work queue is [`docs/ROADMAP.md`](docs/ROADMAP.md).

This README gets a teammate from a fresh clone to a working local setup. How we work with AI coding agents is in [`AGENTS.md`](AGENTS.md); read it before you start a step.

## What you need installed

| Tool | Why | Needed by |
|---|---|---|
| Git | clone and push | everyone |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Python 3.12+ and dependencies for `services/api` | Tracks A, B, D |
| [Ollama](https://ollama.com/download) | runs the local Gemma models (Reddit/CDS extraction, embeddings) | Track A |
| Docker with Compose | the Zetaris data-fabric bundle | Track A (and anyone running the full stack) |
| Node.js and pnpm | the web app (`apps/web`, not created yet) | Track C |
| A Supabase project | Postgres with pgvector, the database for everything | Tracks A, B |

Hardware for the local models: about 8 GB of GPU memory is comfortable, and 16 GB of RAM is tight if Zetaris is also running (see [Running the models](#running-the-local-models)).

## 1. Clone and configure

```bash
git clone https://github.com/Galm007/GenAI-Hackathon-Project.git
cd GenAI-Hackathon-Project
cp .env.example .env
```

Edit `.env`. It is git-ignored; never commit it or paste its values into chat, issues or commits. Most values already have working defaults:

| Variable | You provide it? | Where it comes from |
|---|---|---|
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | yes | Your Supabase project settings. The service-role key is server-side only. |
| `SCORECARD_API_KEY` | yes (Track A) | Free key from [api.data.gov](https://api.data.gov/signup/) |
| `ZETARIS_ADMIN_PASSWORD` | yes (Zetaris steps) | The admin password you set after first sign-in to Zetaris |
| `ZETARIS_AGENT_PASSWORD` | yes (Zetaris steps) | Any password you choose for the `adcom_agent` service user |
| `ZETARIS_PG_USER`, `ZETARIS_PG_PASSWORD`, `SUPABASE_POOLER_HOST` | yes (Zetaris steps) | The `zetaris_reader` login on Supabase and your project's session-pooler host |
| `METERLESS_BASE_URL`, `METERLESS_RUNTIME_TOKEN` | the person running the demo | Nightshift's Console; see [`docs/meterless-setup.md`](docs/meterless-setup.md). The NVIDIA key goes only inside Nightshift. |
| `ANTHROPIC_API_KEY`, `TAVILY_API_KEY` | only Track B (live agents) | Anthropic Console (optional: Claude is the selectable alternative to Nightshift), Tavily |
| `ETL_MODEL`, `CDS_MODEL`, `EMBEDDING_MODEL`, `OLLAMA_URL`, `ZETARIS_URL`, ... | no | Leave the defaults |

Reddit extraction, CDS extraction and embeddings run locally, so they need **no API key**. Each person fills in their own `.env`; the Supabase project can be shared if the team agrees on one.

## 2. Python service

```bash
cd services/api
uv sync                # installs Python 3.12+ and all dependencies
uv run ruff check .    # lint
uv run pytest -q       # tests (no network, no keys, no models needed)
```

All of that should pass on a fresh clone. If it does not, stop and ask before changing anything.

## 3. Database (Supabase)

Apply the migrations in `supabase/migrations/` to your Supabase project **in numeric order, 0001 to 0009**. Either of these works:

```bash
# SQL editor in the Supabase dashboard: paste each file, in order, or
psql "$DATABASE_URL" -f supabase/migrations/0001_extensions_types.sql   # then 0002 ... 0009
```

They enable `vector`, `pg_trgm` and `pg_cron`, create the tables, search functions and security rules, and use **768-dimension** vectors to match the local embedding model.

Migrations 0001 to 0009 were tested against a scratch Postgres with stand-ins for pgvector and pg_cron. They have not yet run on a real Supabase project, so tell the team if anything fails.

## 4. Local models (Track A)

Install Ollama, then pull the two models:

```bash
ollama pull gemma4:e2b        # extraction, about 3.5 GB
ollama pull embeddinggemma    # embeddings, about 0.6 GB
ollama serve                  # leave running (the desktop app starts it for you)
```

`gemma4:e4b` (about 6.6 GB) is an optional, more accurate extraction model; set `ETL_MODEL` or `CDS_MODEL` to it if `e2b` misreads data.

### Running the local models

Loading a model takes several GB of GPU and RAM, so **close your browser and other heavy apps first, and tell the team if you share a machine**. Extraction pauses the Zetaris containers while it runs (to free RAM) and restarts them afterwards. Set `ADCOM_KEEP_ZETARIS=1` if you have RAM to spare. The first run of any model is slow while it loads.

Extraction is capped at 3,000 posts (see `CAPS` in the plan, §2.9.6). Always start with a 20-post run and read the output against the posts before running more.

## 5. Zetaris data fabric (Track A)

Zetaris is the hackathon partner's federated query platform. Its bundle is **not in this repo** (it contains secrets and a large JDBC jar). Download it from the Zetaris Cloud page, unzip it into `zetaris-platform/` at the repo root, then follow [`docs/zetaris-setup.md`](docs/zetaris-setup.md). The short version:

```bash
cd zetaris-platform
docker login zetarishackathon.azurecr.io    # command from the Zetaris Cloud download page
./preflight.sh && docker compose pull && docker compose up -d
./verify.sh                                  # expect 9 PASS lines
```

**Never run `docker compose down -v` in `zetaris-platform/`.** It destroys the metastore and the encryption keypair. Use `docker compose stop` and `start`.

Zetaris is optional for most work: set `ZETARIS_ENABLED=false` and everything falls back to Supabase.

## 6. Meterless Nightshift (the demo machine)

The hackathon requires Meterless to be running on your machine, and the live agents use it as their primary model provider. Nightshift has no Linux edition (Windows, Mac or DGX Spark only). Follow [`docs/meterless-setup.md`](docs/meterless-setup.md), then check it:

```bash
cd services/api && uv run python -m scripts.smoke_meterless   # three PASS lines
```

## 7. Web app (Track C)

`apps/web` has not been created yet (it is a Track C step in the roadmap). Once it exists, from that folder run `pnpm install` and `pnpm dev`.

## Data pipeline: what exists so far

The `run_etl` command-line entry point does not exist yet (step A11). For now these are modules under `services/api`; check `docs/ROADMAP.md` for what has landed:

| Stage | File | Needs |
|---|---|---|
| Scrape Reddit results posts (Arctic Shift, free, no key) | `etl/reddit_archive.py` | nothing; polite 4 s spacing |
| School list and name resolver | `data/schools_seed.csv`, `etl/school_resolver.py` | nothing |
| Scorecard loader | `etl/load_scorecard.py` | Supabase, `SCORECARD_API_KEY` |
| CDS PDF extraction | `etl/load_cds.py` | Ollama, Supabase, real URLs in `data/cds_sources.yaml` |
| Reddit extraction (A07) | not written yet | waits on Track B schemas |

Never guess CDS URLs: copy each from the school's Institutional Research page.

## Working on the project

- One step at a time, one commit per step. Your agent follows [`AGENTS.md`](AGENTS.md) §3; with Claude Code the command is `/next-step` (or `/next-step B08`).
- Your track decides your steps: A Data/RAG/Zetaris, B Agents/API, C War Room UI, D Viz/Demo/Integration. Don't edit another track's files; describe the change in your report instead.
- Event names, Pydantic schemas and TypeScript types are frozen contracts. Change them only in a commit that updates both sides and `docs/DECISIONS.md`.
- Deviating from the plan means an entry in [`docs/DECISIONS.md`](docs/DECISIONS.md). Read it: several choices differ from the original plan (local Gemma instead of paid APIs, Arctic Shift instead of PullPush, 768-dim vectors).
- Don't commit secrets, the Zetaris bundle, `.env`, or real student data. All demo data is fictional.
- Pull before you start (`git pull --rebase`) and keep a clean working tree.

## Repository map

```
MASTER_PLAN.md        the spec (about 8,400 lines; read only the sections you need)
AGENTS.md             rules for every AI agent on the team
docs/                 ROADMAP.md (work queue), DECISIONS.md (deviations), zetaris-setup.md
services/api/         Python backend: app/ (service), etl/ (data pipeline), scripts/, tests/
supabase/migrations/  SQL, applied in order
zetaris/sql/          Zetaris Lightning SQL files
data/                 seed lists; raw/ and processed/ are git-ignored
zetaris-platform/     the Zetaris bundle (git-ignored, you download it)
```
