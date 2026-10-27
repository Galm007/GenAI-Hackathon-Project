# AdCom

An autonomous multi-agent university admissions committee simulator, built in 36 hours by four people. Upload a transcript, activities list and essay, pick a school, and watch a committee of AI agents grade the dossier, check it against the school's own data, compare it with real applicants who posted their results, argue the case, and say which changes would move the odds most.

Every probability and delta on screen comes from deterministic scoring code (`services/api/app/scoring/`), never from a model. The spec is [`MASTER_PLAN.md`](MASTER_PLAN.md); the work queue is [`docs/ROADMAP.md`](docs/ROADMAP.md). How we work with AI coding agents is in [`AGENTS.md`](AGENTS.md); read it before you start a step.

## How it works

```
intake (web) ──► Node 1: dossier parser + rubric grader
                    │
          ┌─────────┴─────────┐                (in parallel)
          ▼                   ▼
   Node 2: institutional   Node 3: applicant twins
   (Zetaris SQL tool,      (pgvector hybrid search over
    CDS + IPEDS facts)      947 real Reddit outcomes, radar)
          └─────────┬─────────┘
                    ▼
   committee docket (World Model shared case file)
                    ▼
   debate: advocate ⇄ chair (4 turns)
                    ▼
   Node 5: delta engine (counterfactuals, pivots, what-if)
                    ▼
   live SSE stream ──► War Room UI (gauge, waterfall, radar, twin cards, what-if sliders)
```

| Part | Where | Notes |
|---|---|---|
| API and agent graph | `services/api/` | FastAPI, LangGraph, Pydantic v2, Python 3.12 |
| War Room UI | `apps/web/` | Next.js, TypeScript; same-origin proxy to the API |
| World Model sidecar | `services/world-model/` | Meterless World Model engine, Node 24, no dependencies; passes the upstream conformance suite 8/8 |
| Database | `supabase/migrations/` | Supabase Postgres with pgvector (768-d vectors) |
| Data fabric | `zetaris/sql/` | Zetaris Lightning views over Supabase, IPEDS and CDS data (hackathon partner) |
| Live-agent models | `app/llm.py`, `app/openai_compat.py` | `LLM_PROVIDER=meterless` (Nightshift, Nemotron lanes) or `gemini` (free tier). Claude is in code but refused unless `ALLOW_PAID_PROVIDERS=true` |
| Offline ETL models | `app/local_llm.py` | Local Gemma through Ollama: Reddit and CDS extraction, embeddings. No key, no cost |

## Status (2026-10-26)

| Area | State |
|---|---|
| Roadmap | 56 of 62 steps done. Open: B17c, D08, D10, X01, X02 (required) and A18 (optional) |
| Live evaluation | A full live Maya at UIUC run completes on Gemini's free tier (`docs/live-verification-2026-10-26.json`) and on Meterless (`data/demo_runs/maya-uiuc-live.json`, D-054) |
| Nightshift committee turn | Discovery, auth and chat work. A streamed committee turn through a pinned Nemotron lane is not yet confirmed (D-056), so B17c and D10 are open |
| Hosting | Web app on Vercel (`adcom-orpin.vercel.app`). The API runs on a teammate's machine beside Zetaris behind a temporary tunnel, so the hosted app works only while that machine and tunnel are up. Hosted live run and phone check still open (D08) |
| Data | 947 twins (target 10K not met, D-037), 265 universities, 5 schools with CDS rubrics. Held-out Brier 0.232 vs 0.303 base rate; ranking within a school is weak (D-044). See [`docs/data-report.md`](docs/data-report.md) |

## Quick start: the offline demo (no keys, about 5 minutes)

Needs [uv](https://docs.astral.sh/uv/getting-started/installation/), Node.js 24 and pnpm.

```bash
git clone https://github.com/Galm007/GenAI-Hackathon-Project.git
cd GenAI-Hackathon-Project
cp .env.example .env

# terminal 1: the API in fake mode (fixtures instead of model calls, no Zetaris)
cd services/api
uv sync
FAKE_LLM=1 ZETARIS_ENABLED=false uv run uvicorn app.main:app --host 127.0.0.1 --port 8000

# terminal 2: the web app
cd apps/web
pnpm install --frozen-lockfile
pnpm dev --hostname 127.0.0.1 --port 3001
```

Open `http://127.0.0.1:3001/room/demo/maya-uiuc` for the recorded fictional replay, or `/room/demo/maya-uiuc-live` for the live-run recording. `Shift+R` restarts a replay. Port 3001 leaves 3000 free for Zetaris. A new evaluation from the intake page needs the Supabase data even in fake mode.

## What you need installed

| Tool | Why | Needed by |
|---|---|---|
| Git | clone and push | everyone |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Python 3.12+ and dependencies for `services/api` | Tracks A, B, D |
| Node.js 24 and pnpm | the web app and the World Model sidecar | Tracks B, C, D |
| [Ollama](https://ollama.com/download) | the local Gemma models (extraction, embeddings; Node 1 also embeds the applicant) | Track A, and anyone running live evaluations |
| Docker with Compose | the Zetaris bundle and the co-located API | Track A, and the demo host |
| A Supabase project | Postgres with pgvector; the team shares one | Tracks A, B |
| Meterless Nightshift | the primary live-agent provider | the demo machine |

Hardware for the local models: about 8 GB of GPU memory is comfortable, and 16 GB of RAM is tight if Zetaris is also running.

## 1. Configure `.env`

`.env` lives at the repo root and is git-ignored; never commit it or paste its values into chat, issues or commits.

| Variable | You provide it? | Where it comes from |
|---|---|---|
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | yes | The shared Supabase project's settings. Server-side only, never in the web app |
| `LLM_PROVIDER` | yes | `meterless` (default) or `gemini`. `anthropic` is paid and refused unless the team agrees (AGENTS.md §4) |
| `METERLESS_BASE_URL`, `METERLESS_RUNTIME_TOKEN`, `METERLESS_MODEL` | the demo machine | Nightshift's Console; see [`docs/meterless-setup.md`](docs/meterless-setup.md). The NVIDIA key goes only inside Nightshift. Pin `METERLESS_MODEL` to a Nemotron lane for award evidence |
| `GEMINI_API_KEY` | for `LLM_PROVIDER=gemini` | [Google AI Studio](https://aistudio.google.com/apikey), from a Cloud project with **no billing account** so it stays free |
| `TAVILY_API_KEY` | live agents | Tavily's free plan (no card) |
| `SCORECARD_API_KEY` | Track A | Free key from [api.data.gov](https://api.data.gov/signup/) |
| `ZETARIS_*`, `SUPABASE_POOLER_HOST` | Zetaris steps | See [`docs/zetaris-setup.md`](docs/zetaris-setup.md). `ZETARIS_ENABLED=false` falls back to Supabase |
| `MAX_RUNS_PER_DAY`, `MAX_CONCURRENT_RUNS` | on a public host | Keep the `.env.example` values (30 and 2) so a public tunnel can't drain the free-tier quota. The code defaults are higher |
| `WORLD_MODEL_URL` | no | The sidecar's address. If it is unreachable, the docket comes from run state and the run still completes |
| `ANTHROPIC_API_KEY` | no | Leave unset |
| `ETL_MODEL`, `CDS_MODEL`, `EMBEDDING_MODEL`, `OLLAMA_URL`, `DEMO_MODE`, ... | no | Leave the defaults |

## 2. Python service

```bash
cd services/api
uv sync                # Python 3.12+ and all dependencies
uv run ruff check .    # lint
uv run pytest -q       # tests: no network, keys or models needed
```

Both should pass on a fresh clone. If they don't, stop and ask before changing anything.

`/api/health` reports `db`, `zetaris` and `meterless` (each `true` or `false`), plus `llm_provider`, `llm_key`, `fake_llm` and `demo_mode`. When `LLM_PROVIDER=meterless`, the API also checks Nightshift's `/v1/models` at startup and logs whether `METERLESS_MODEL` is listed. If Nightshift is down at demo time, switch to `LLM_PROVIDER=gemini`. If Gemini's daily quota is also used up, serve a recorded replay.

## 3. Database (Supabase)

Apply `supabase/migrations/` in numeric order, **0001 to 0010**, through the SQL editor or psql:

```bash
psql "$DATABASE_URL" -f supabase/migrations/0001_extensions_types.sql   # then 0002 ... 0010
```

They enable `vector`, `pg_trgm` and `pg_cron`, and create the tables, hybrid-search and radar RPCs, row-level security, the Zetaris export schema and its read policies. The shared project already has them, and the data from the A15 run is loaded.

## 4. Local models

```bash
ollama pull gemma4:e2b        # extraction, about 3.5 GB
ollama pull embeddinggemma    # embeddings, about 0.6 GB (768-d)
ollama serve                  # leave running (the desktop app starts it for you)
```

`gemma4:e4b` (about 6.6 GB) is an optional, more accurate extraction model; set `ETL_MODEL` or `CDS_MODEL` to use it.

Loading a model takes several GB of GPU and RAM, so **close your browser and other heavy apps first, and tell the team if you share a machine**. Extraction pauses the Zetaris containers while it runs and restarts them afterwards (`ADCOM_KEEP_ZETARIS=1` keeps them up).

## 5. Zetaris data fabric

The Zetaris bundle is **not in this repo**: it contains secrets and a large JDBC jar. Download it from the Zetaris Cloud page, unzip it into `zetaris-platform/` at the repo root, then follow [`docs/zetaris-setup.md`](docs/zetaris-setup.md):

```bash
cd zetaris-platform
docker login zetarishackathon.azurecr.io    # command from the Zetaris Cloud download page
./preflight.sh && docker compose pull && docker compose up -d
./verify.sh                                  # expect 9 PASS lines
cd ../services/api && uv run python -m etl.run_etl zetaris-setup   # Lightning SQL, idempotent
```

**Never run `docker compose down -v` in `zetaris-platform/`.** It destroys the metastore and the encryption keypair. Use `docker compose stop` and `start`.

## 6. Meterless Nightshift (the demo machine)

The hackathon requires Meterless to run on your machine, and the live agents use it as their primary provider. Nightshift ships for Windows, Mac (M1+) and DGX Spark. On Linux it runs under Wine (D-043; ask the organizers whether that counts for judging). Follow [`docs/meterless-setup.md`](docs/meterless-setup.md), then check it:

```bash
cd services/api && uv run python -m scripts.smoke_meterless   # three PASS lines
```

## 7. World Model sidecar

The committee's shared case file. Nodes 1–3 and the debate write observations to it, and the docket is built from its read surface.

```bash
cd services/world-model
npm test     # engine and HTTP tests
npm start    # serves 127.0.0.1:8790
```

The conformance scorecard against the upstream Meterless suite is in [`docs/meterless-evidence/`](docs/meterless-evidence/).

## 8. Web app

```bash
cd apps/web
pnpm install --frozen-lockfile
pnpm lint && pnpm exec tsc --noEmit && pnpm test && pnpm build
pnpm dev --hostname 127.0.0.1 --port 3001
```

Routes: `/` (intake), `/room/<run_id>` (live War Room), `/room/demo/<name>` (recorded replay), `/r/<run_id>` (share link). The app proxies `/api/*` to `ADCOM_API_URL` (default `http://127.0.0.1:8000`). Never put backend or model keys in the web app's environment.

## Running a live evaluation

With `.env` filled in, Supabase reachable, Ollama running and a provider configured (live runs use the provider's quota, so agree with your human first):

```bash
cd services/api
uv run python -m scripts.run_graph_cli --school uiuc --major "Computer Science" \
  --transcript ../../data/demo_dossiers/maya/transcript.pdf \
  --activities ../../data/demo_dossiers/maya/activities.txt \
  --essay ../../data/demo_dossiers/maya/essay.txt
```

To see it in the UI, start the API without `FAKE_LLM` and submit from the intake page, or post a pack from `data/demo_dossiers/` (see its README). A live run takes about 10–15 minutes, so the pitch uses recorded replays. Save a completed fictional run with `uv run python -m scripts.record_demo RUN_ID NAME --fictional`.

All demo applicants (Maya, Leo, Sam) are **fictional**. Never put real student data in fixtures, recordings or commits.

## Deploying

The API stays co-located with Zetaris, and the web app goes on Vercel. From the repo root, with Zetaris running:

```bash
docker compose --env-file zetaris-platform/.env -f zetaris-platform/docker-compose.yml -f docker-compose.adcom.yml up -d --no-deps world-model adcom-api
```

This builds and starts the API and the World Model sidecar on the Zetaris network without recreating the running Zetaris services, with the API on `127.0.0.1:8000` only. Publish it through a tunnel, set Vercel's `ADCOM_API_URL` to the tunnel's origin and redeploy. A quick tunnel's URL changes on every restart, so update `ADCOM_API_URL` each time. The full runbook, Vercel settings and release gates are in [`docs/deployment.md`](docs/deployment.md).

## Data pipeline

One CLI, run from `services/api`. Always start with a small run (`--limit 20`) and read the output before running more:

```bash
uv run python -m etl.run_etl <stage> [--limit N] [--since YYYY-MM-DD]
```

| Stage | Does | Needs |
|---|---|---|
| `scorecard` | College Scorecard school list (265 schools) | Supabase, `SCORECARD_API_KEY` |
| `cds` | CDS rubric (C7 weights) for the 5 demo schools | Supabase, `data/cds_sources.yaml` |
| `scrape` | Reddit results posts from Arctic Shift (free; keep the 4 s spacing) | nothing |
| `extract` | Structured outcomes from posts with local Gemma (capped at 3,000 posts) | Ollama |
| `load-twins` | Embed and load twins | Ollama, Supabase |
| `refresh-stats` | Stats views and major competitiveness | Supabase |
| `zetaris-setup`, `zetaris-refresh` | Lightning SQL and the gold tables | Zetaris |
| `all` | Every stage in order | all of the above |

`scripts/backtest.py` reproduces the held-out calibration audit (A16). Never guess CDS URLs: copy each from the school's Institutional Research page.

## Docs

| File | What's in it |
|---|---|
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Every step, its status and what "done" means |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Every deviation from the plan and why (D-001 onwards) |
| [`docs/deployment.md`](docs/deployment.md) | Hosting runbook and production acceptance |
| [`docs/data-report.md`](docs/data-report.md) | Corpus size, coverage, calibration, backtest |
| [`docs/pitch.md`](docs/pitch.md) | Three-minute pitch, real figures, pre-demo checklist |
| [`docs/meterless-setup.md`](docs/meterless-setup.md), [`docs/meterless-evidence/`](docs/meterless-evidence/) | Nightshift setup and judging evidence |
| [`docs/zetaris-setup.md`](docs/zetaris-setup.md) | Zetaris bring-up |

## Working on the project

- One step at a time, one commit per step. Your agent follows [`AGENTS.md`](AGENTS.md) §3; with Claude Code the command is `/next-step` (or `/next-step B08`).
- Your track decides your steps: A Data/RAG/Zetaris, B Agents/API, C War Room UI, D Viz/Demo/Integration. Don't edit another track's files; describe the change in your report instead.
- Event names, Pydantic schemas and TypeScript types are frozen contracts. Change them only in a commit that updates both sides and `docs/DECISIONS.md`.
- Don't commit secrets, the Zetaris bundle, `.env`, or real student data.
- Pull before you start (`git pull --rebase`) and keep a clean working tree.

## Repository map

```
MASTER_PLAN.md            the spec (about 8,400 lines; read only the sections you need)
AGENTS.md                 rules for every AI agent on the team (CLAUDE.md and GEMINI.md import it)
apps/web/                 Next.js War Room UI
services/api/             Python backend: app/ (API, agents, scoring), etl/, scripts/, tests/, Dockerfile
services/world-model/     Meterless World Model engine sidecar (TypeScript, Node 24)
docker-compose.adcom.yml  joins the API and sidecar to the Zetaris Compose network
supabase/migrations/      SQL 0001–0010, applied in order
zetaris/sql/              Zetaris Lightning SQL (sources, views, gold, security)
data/                     seed lists, aliases, CDS sources, data report, fixtures/, demo_dossiers/, demo_runs/
                          (raw/ and processed/ are git-ignored)
docs/                     roadmap, decisions, deployment, data report, pitch, partner setup
zetaris-platform/         the Zetaris bundle (git-ignored; you download it)
```
