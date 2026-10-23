# DECISIONS: deviations from MASTER_PLAN.md

Append one entry whenever a commit deviates from the plan (a renamed field, a swapped library, a confirmed or corrected Zetaris detail, a cut feature). Keep entries short, never delete old ones, and if a decision is reversed, add a new entry that supersedes it.

```
## D-000 — <title>
- Step: <ID> · Date: YYYY-MM-DD · By: <human> via <tool>
- Plan said: …
- We did: …
- Why: …
- Impact on other tracks: … (contract change? update both Python + TS sides)
```

---

## D-001 — Decisions already baked into the plan (for reference)
- Step: — · Date: 2026-10-23 · By: planning session
- pgvector (Supabase) does twin KNN; Zetaris Lightning owns institutional facts, cross-source stats, agent SQL access and audit (plan §2.10.1).
- One target school per graph run; extra schools are child runs that skip Node 1 (plan §3.2).
- All reasoning nodes use `claude-opus-5-5` with server-side refusal fallbacks enabled (plan §0.2). Changing models is a human decision.
- No LLM ever outputs a user-visible probability or delta (plan §0.1).

## D-002 — `etl/common.py` imports `app.config` lazily
- Step: A05 · Date: 2026-10-23 · By: Jmar L. Pineda via Claude Code
- Plan said: `from app.config import settings` at the top of `etl/common.py` (§2.9.1).
- We did: import `settings` inside `supabase()` instead.
- Why: `app/config.py` is B01's and its `Settings` requires `OPENAI_API_KEY` and Supabase keys at import time, so the scraper (which needs only paths and logging) would fail without a populated `.env`. Behavior is otherwise identical.
- Impact on other tracks: none.

## D-003 — PullPush refuses automated scraping (resolved by D-006)
- Step: A05 · Date: 2026-10-23 · By: Jmar L. Pineda via Claude Code
- Plan said: scrape r/collegeresults and r/TransferToTop25 from `api.pullpush.io` at one request per 4 s (§2.9.2).
- We found: the API answers 429 with the body "Rate limit exceeded. This website does not provide free scraping resources for agents. Please contact the administrator on Discord if you're interested in a paid scraping service." The same happens for a plain `size=1` request, so it is not a pacing problem.
- We did: committed `etl/pullpush.py` as specified (its backoff worked as designed) and left A05 unchecked, because the "done when" live scrape could not run. We did not try to evade the block.
- Options for the team: ask the PullPush administrator for access, use another source (the official Reddit API with the team's own credentials, or an academic dump), or run on pre-collected raw JSONL. This is a design choice for the humans.
- Impact on other tracks: A07 (extraction) and everything after it need `data/raw/*.jsonl`.

## D-004 — `app/embeddings.py` builds its OpenAI client lazily; one line in `profile_text.py` split
- Step: S02 · Date: 2026-10-23 · By: Jmar L. Pineda via Claude Code
- Plan said: module-level `_client = AsyncOpenAI(api_key=settings.openai_api_key)` with `from .config import settings` at the top (§2.9.7).
- We did: create the client and import `settings` on first call (`_get_client()`), same public API (`embed_texts`, `embed_one`). In `build_profile_text` the first-gen text moved into a local variable to satisfy ruff's line-length rule; the output string is byte-identical.
- Why: `app/config.py` (B01) does not exist yet and requires API keys at import, so an eager import would break S02's tests and every module that imports `embeddings`.
- Impact on other tracks: none; anything that patches `app.embeddings._client` should patch `_get_client` instead.

## D-005 — `etl/load_scorecard.py` imports `app.config` lazily
- Step: A09 · Date: 2026-10-23 · By: Jmar L. Pineda via Claude Code
- Plan said: `from app.config import settings` at module top (§2.9.8).
- We did: import inside `load_scorecard()`, as in D-002, so `_to_row`/`slugify` are importable and unit-testable before B01 lands.
- Impact on other tracks: none.

## D-006 — Reddit source switched from PullPush to Arctic Shift
- Step: A05 · Date: 2026-10-23 · By: Jmar L. Pineda via Claude Code
- Plan said: scrape `api.pullpush.io` (§2.9.2, plus mentions in §0.4, §1.1, §2.1, §2.9.11, §7 schedule, risk table and pitch text).
- We did: use Arctic Shift (`https://arctic-shift.photon-reddit.com/api/posts/search`), a free keyless archive whose docs impose no restriction on automated access beyond "be considerate". Module renamed `etl/pullpush.py` → `etl/reddit_archive.py` (same functions: `keep`, `get_page`, `scrape`, `scrape_all`). Differences: query param `limit` instead of `size`, no `sort_type`, and on 429 it waits for the `X-RateLimit-Reset` seconds the service returns. Response shape (`{"data": [...]}`, same post fields, integer `created_utc`) and the kept fields are unchanged, and the `author` field is still not stored. Plan text updated to match; the plan's own risk table already named Arctic Shift as the fallback.
- Verified: a live scrape of the last day for both subreddits wrote `data/raw/*.jsonl` plus checkpoints. The first request returned a transient 422 and succeeded on retry.
- Fallback if the API is unavailable: Watchful1's per-subreddit `.zst` dumps on Academic Torrents (noted in the plan's risk table).
- Impact on other tracks: A11 imports `scrape_all` from `etl.reddit_archive`. `AGENTS.md` §4 still says "PullPush allows one request per 4 s"; it is human-owned, so it needs a one-word edit by a human.

## D-007 — Local Gemma models for extraction and embeddings (no OpenAI key, no Anthropic key for the ETL)
- Step: S02 / A01–A03 / A07 / A08 prep · Date: 2026-10-23 · By: Jmar L. Pineda via Claude Code (human decision: "Use Gemma for both extraction and embedding")
- Plan said: Reddit extraction with `claude-opus-5-5` (`ETL_MODEL`), embeddings with OpenAI `text-embedding-3-small` as `vector(1536)`.
- We did:
  - Extraction: `gemma4:e4b` served by Ollama (`app/local_llm.py::chat_structured`, schema-constrained via Ollama's `format`, temperature 0, thinking off). `etl/extract_reddit.py` (A07) calls it instead of `app.llm.parse`; concurrency drops from 12 to 1.
  - Embeddings: `embeddinggemma` (300M, 768-d) via Ollama `/api/embed`, with the "task: sentence similarity | query: " prefix on both twins and live applicants so they share one space. The `openai` dependency is removed.
  - Dimension: `vector(1536)` → `vector(768)` in migrations 0003, 0005 and 0006 (edited in place; none have been applied to any database yet), the plan's SQL, `embedding_dim` and the storage estimate.
  - Runtime: the Ollama binary lives in git-ignored `.local/ollama/` (downloaded from ollama.com, no sudo); models in `.local/ollama/models/`.
  - Plan text updated in §0.2 stack table, §0.3 env, §0.4, §1.1 diagrams, §2.4/§2.6/§2.7 SQL, §2.9.6, §2.9.7, §2.9.11, §3.5.1 settings, §7 risk table. Settings fields `ollama_url`, `etl_model`, `embedding_model`, `embedding_dim` are the same in `app/local_llm.py` (usable now) and in B01's `Settings` (per the plan).
- Not changed: the live agents (Track B, Claude) and CDS PDF extraction (A10), which still need a human decision.
- Risks: Gemma 4 E4B is much smaller than the model the plan assumed, so extraction accuracy (GPA scale, tiers, round/outcome) is unproven. A07's first run is a 20-post smoke test that gets read by a human before any full run. The embedding swap changes retrieval behaviour, which hasn't been measured against the old model either.
- Impact on other tracks: Track B's code that calls `match_applicant_twins` or embeds a live applicant must use `app.embeddings.embed_one` (768-d). Anything hard-coding 1536 must change. `AGENTS.md` §4 still describes Opus-priced extraction and `OPENAI` assumptions; it is human-owned.

### D-007 addendum — smoke test results (2026-10-23)
- Embeddings: `embeddinggemma` returned 768-d vectors (3 profiles in 2.7 s warm). Cosine for a CS profile vs another CS profile was 0.987 and vs a Biology profile 0.832, so the ordering is sensible.
- Extraction: `gemma4:e4b` with schema-constrained output filled a 5-field stand-in schema from one synthetic post and got every value right, including "waitlisted then rejected" and "deferred then rejected" resolving to `rejected`. This is one post and a small schema, not evidence for the full `RedditApplicantRecord` with tier grading.
- Speed: ~71 tokens/s generation when warm, GPU 91% busy, 3 GB on the GPU plus a 2.7 GB pinned host buffer. With the Zetaris stack holding ~12 GB of the 15 GB RAM and swap in use, a cold request ran at ~1 token/s and the first schema request returned a 500 after 60 s; once warm the same request took 19 s. Stop the Zetaris containers (`docker compose stop`, never `down -v`) or free RAM before the real extraction run.
- Consequence: the full 12K-post run is not feasible in the 36-hour window (70–130 h estimated). Options for the humans: cap the run (~1,000 posts per 8 h), use `gemma4:e2b` for speed at some accuracy cost, or shorten the output schema. A07's first run is still a 20-post read-through.
