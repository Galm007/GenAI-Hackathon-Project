# AGENTS.md — how AI coding agents work in this repo

This file is the **single source of truth for every AI agent** on the team (Claude Code, Codex, Gemini CLI, or anything else). `CLAUDE.md` and `GEMINI.md` import it. If your tool didn't load it automatically, read it in full before doing anything.

## 1. What we're building

**AdCom**, an autonomous multi-agent university admissions committee simulator, built in 36 hours by four people. The full spec is `MASTER_PLAN.md`, which is about 8,400 lines. **We build the plan one step at a time, one commit per step, until every step in `docs/ROADMAP.md` is checked off.**

| File | Role | Who edits it |
|---|---|---|
| `MASTER_PLAN.md` | **The spec.** Architecture, schemas, SQL, prompts, code, UI, schedule. Code in it is the intended implementation. | Only for factual corrections found while building (see §7) |
| `docs/ROADMAP.md` | **The work queue.** Every step: ID, plan sections, dependencies, "done when". Checkboxes show progress. | The agent finishing a step checks it off in that step's commit |
| `docs/DECISIONS.md` | Log of every deviation from the plan and why | The agent that deviated, in the same commit |
| `AGENTS.md` (this file) | How to work | Humans only |

## 2. Team and tracks

Each human owns one track, and their agent works **only on that track's steps** (plus shared `S` steps when assigned). Fill in names on day one:

| Track | Scope | Human | AI tool |
|---|---|---|---|
| **A: Data, RAG & Zetaris** | Supabase migrations, ETL, pgvector RPCs, Zetaris data fabric, backtest | Jmar L. Pineda | Claude Code |
| **B: Agents & API** | LLM wrapper, schemas, prompts, scoring, LangGraph nodes, FastAPI/SSE | _name_ | _tool_ |
| **C: War Room UI** | Next.js shell, store/stream, committee room, dossier panel, intake | _name_ | _tool_ |
| **D: Viz, Demo & Integration** | Charts, twin cards, what-if, demo personas/fixtures/replays, deploy, pitch assets | _name_ | _tool_ |

## 3. The step protocol (follow it exactly, every time)

When your human says "next step", "continue", "do A07", or similar:

1. **Sync.** `git pull --rebase`. Make sure the working tree is clean; if it isn't, stop and ask.
2. **Pick the step.** Open `docs/ROADMAP.md`. Take the step your human named, or else the **first unchecked step in your track whose dependencies are all checked**. If every remaining step in your track is blocked, say which dependency blocks it and suggest the mock or fallback from the plan (§6.3 of the plan) instead of building around it silently.
3. **Announce it.** In one or two lines, tell your human the step ID, its title and the plan sections you'll read.
4. **Read only what you need.** Read the plan sections the step lists, not the whole file. Find them with `grep -n "^### 2.10" MASTER_PLAN.md` and read from that line to the next heading. Also read any existing code the step touches.
5. **Implement exactly that step.** Follow the plan's code and names: file paths from plan §0.4, identifiers and SQL as written. Don't start the next step. Don't refactor other tracks' files. Don't add features the step doesn't list.
6. **Verify.** Run the step's "done when" checks and the area's commands (§6 below). If a check needs a service you don't have running (Supabase, Zetaris, API keys), say so explicitly. Never claim a check passed if you didn't run it.
7. **Update the roadmap.** Change the step's `- [ ]` to `- [x]` and append ` — done by <human> via <tool>, YYYY-MM-DD`. If you deviated from the plan, add an entry to `docs/DECISIONS.md`.
8. **Commit once.** Stage only this step's files plus the roadmap/decisions edits (no `git add -A` that sweeps in stray files). Use the message format in §5.
9. **Stop and report.** Use the format in §8. **Do not push unless your human says to push.** Do not start the next step until asked.

One step = one commit. If a step turns out too big for one reviewable commit (roughly 600+ changed lines of hand-written code), stop after step 4. Propose a split (`B08a`, `B08b`) and wait for your human to approve it before editing the roadmap.

## 4. Rules that matter

**Scope and ownership**
- Touch only files your step creates or modifies. If you need a change in another track's file, describe it in your report instead of making it, unless the step says otherwise.
- **Frozen contracts:** event names and payloads (plan §1.6, §4.2), Pydantic schemas (`services/api/app/schemas/`, plan §3.3) and TS types (`apps/web/lib/types.ts`, plan §5.4.1). Change them only in a commit that updates **both** the Python and TypeScript sides and logs the change in `docs/DECISIONS.md`.

**Plan A: Claude API code: do not "fix" it from memory**
- The plan's Anthropic SDK usage is current and deliberate. It uses model `claude-opus-5-5`, `client.beta.messages.parse(..., output_format=Model, output_config={"effort": ...})`, `fallbacks="default"` with beta `server-side-fallback-2026-07-01`, and adaptive thinking with **no** `budget_tokens`, `temperature` or forced `tool_choice`. Your training data may suggest older shapes or model names. **Keep the plan's versions.** Changing models or removing fallbacks is a human decision.
- **Not everything uses Claude.** Reddit extraction and embeddings run locally on Gemma through Ollama (`app/local_llm.py`, `gemma4:e2b` and `embeddinggemma`, 768-d vectors): no API key, no per-token cost, and the plan's `vector(768)` columns depend on it. CDS PDF extraction (A10) also runs locally (`CDS_MODEL`). The live agents (Track B) use **Meterless Nightshift** as the primary provider (`LLM_PROVIDER=meterless`, plan §1.7) with Gemini as the selectable alternative. The NVIDIA key lives only in Nightshift's Providers tab; never put it or the Meterless Runtime token in a coding tool's settings. See D-011. See `docs/DECISIONS.md` D-007, D-008 and D-010.
- Probabilities and deltas come only from `app/scoring/` (deterministic code). Never let an LLM output a number that is shown to the user (plan §0.1).

**Plan B: Gemini's Free tier API**
- Since the team agrees to proceed with a "no cost" deployment plan, I am including this entry to take note that Gemini's free tier API is permitted to be used in the project and deployment.
- Claude API may be kept, however not used until an explicit team consensus.

**Secrets, data and safety**
- Never commit or print secrets. Keep `.env` out of git and maintain `.env.example` with placeholders only. **Never commit `zetaris-platform/`** or its zip: it contains the Zetaris `.env` keypair password and a 27 MB JDBC jar. `.gitignore` already covers it.
- Never run `docker compose down -v` in `zetaris-platform/`. It destroys the metastore and the encryption keypair.
- **Spending money or hogging the machine needs your human's explicit OK.** Paid calls: live-agent runs (repeated full graph runs, Claude credit or NVIDIA free-tier limits). Local runs cost nothing but load the GPU and RAM: **tell your human before loading a model** (they close their browser), start with `--limit 20`, and never exceed the extraction cap (`CAPS`, 3,000 posts). Extraction pauses the Zetaris containers automatically (`etl/resources.py`) and restarts them afterwards.
- The demo persona (Maya) and all fixtures are **fictional**. Never put real student data in fixtures, recordings or commits.
- Be polite to external APIs: Arctic Shift (our Reddit source, replacing PullPush, which blocks automated clients; see D-006) is a free volunteer service, so keep the 4 s spacing between requests and honor `X-RateLimit-Reset` (already in `etl/reddit_archive.py`). Never try to get around a block or rate limit.

**Zetaris (hackathon partner)**
- Zetaris is the data plane for institutional facts and cross-source stats (plan §2.10). pgvector stays for twin KNN. Keep the Supabase fallbacks in `zetaris_repo.py` working.
- Plan lines marked **"(verify at Hour 1)"** are unconfirmed Zetaris details. When you confirm or correct one against the running stack, fix the plan text in the same commit and remove the marker.

**Code style**
- Python 3.12, async throughout, type hints, Pydantic v2, `ruff` clean. TypeScript strict, React Server Components for the shell and client components for interactive parts. Match the surrounding code's density of comments and naming. Don't add speculative abstractions.

## 5. Commit messages

```
[B08] Node 1: dossier parser + rubric grader

- Implements plan §3.7.1 (extract → metrics → grade → guardrails → embed)
- Adds tests for grade clamping
Plan: §3.7.1, §3.6.1
```

- The subject line starts with the step ID in brackets. Use the imperative mood, at most 72 characters.
- The body says what was built, references plan sections, and notes any deviation ("see DECISIONS D-007").
- Keep whatever attribution trailer your tool adds by default.
- Never amend or rebase commits that are already pushed. Never force-push. If `git pull --rebase` conflicts in `docs/ROADMAP.md`, keep both sides' checkmarks.

## 6. Verification commands by area

| Area | Commands |
|---|---|
| Python (`services/api`) | `uv sync` · `uv run ruff check .` · `uv run pytest -q` |
| Web (`apps/web`) | `pnpm install` · `pnpm lint` · `pnpm exec tsc --noEmit` · `pnpm build` |
| Migrations (`supabase/migrations`) | Apply to a scratch DB: `supabase db reset` locally, or `psql "$DATABASE_URL" -f <file>`. Confirm objects with `\d`, `\df`. |
| Zetaris | `cd zetaris-platform && ./verify.sh` (nine PASS lines) · `/api/health` shows `"zetaris": true` |
| ETL | Run the stage with `--limit 20`, then inspect `data/processed/*.jsonl` |
| Graph end to end | `uv run python -m scripts.run_graph_cli … --school uiuc` (needs keys; with no keys use `FAKE_LLM=1 ZETARIS_ENABLED=false`) |

If tooling for an area doesn't exist yet (for example, before `S01`), say so in your report rather than inventing a substitute.

## 7. When the plan is wrong or unclear

- **Small and obvious** (typo, wrong import, an API that doesn't exist): fix the code, fix the plan text, and log it in `docs/DECISIONS.md`.
- **A design choice** (changing a schema, swapping a library, cutting a feature): stop and ask your human. Don't decide alone.
- **Blocked by another track:** use the fallback the plan specifies (scripted fake SSE, `FAKE_LLM` fixtures, Supabase fallback) and note it in your report.

## 8. End-of-step report (what you tell your human)

```
Step:      B08 — Node 1: dossier parser + rubric grader   ✅ committed <short-hash> (not pushed)
Changed:   services/api/app/agents/nodes/dossier_parser.py, tests/test_guardrails.py, docs/ROADMAP.md
Verified:  ruff ✓  pytest 14 passed ✓  CLI run on Maya's dossier — NOT run (no ANTHROPIC_API_KEY here)
Deviations: none   (or: D-007 — …)
Next in track: B09 — Node 2 (blocked on A13 zetaris client; can start with ZETARIS_ENABLED=false)
Push now?
```
