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
