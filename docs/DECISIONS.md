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

## D-008 — gemma4:e2b, capped run, short output schema, Zetaris auto-pause
- Step: A07 prep · Date: 2026-10-23 · By: Jmar L. Pineda via Claude Code (human decisions: use e2b, cap the run, shorten the schema, stop Zetaris automatically during extraction)
- Plan said (after D-007): `gemma4:e4b`, extract everything, full `RedditApplicantRecord`, Zetaris left running.
- We did:
  - `ETL_MODEL` default is `gemma4:e2b` (code, `.env.example`, plan). Pulled with Ollama; not yet run.
  - Run capped at 3,000 posts (`CAPS`: 2,400 r/collegeresults + 600 r/TransferToTop25, newest first; the cap counts already-processed posts so resumes do not exceed it) and posts that never mention a decision are skipped before the model sees them (`select_posts`, plan §2.9.6).
  - Short schema (plan §2.9.3/§2.9.4): dropped `tier_rationale`, `gpa_raw_text`, `class_rank_text`, `ap_scores`, `essay_notes`, `lor_notes`, `major_if_different`; activities ≤ 8 at ≤ 120 chars, awards ≤ 4, `extraction_issues` ≤ 2, spike ≤ 8 words; `num_predict=900`. Matching `applicant_twins` columns stay unfilled (nullable/defaulted); no migration change.
  - `etl/resources.py::zetaris_paused()` (built and unit-tested with a mocked docker) runs `docker compose stop` on the services that are running before extraction and `docker compose start` on the same services afterwards, also if extraction crashes. It never uses `down`/`-v`. `ADCOM_KEEP_ZETARIS=1` disables it. The restart afterwards is an addition: say so if you want Zetaris left stopped.
- Not done: `etl/reddit_schema.py`, `etl/prompts.py`, `etl/extract_reddit.py` are still unwritten; they import `app.schemas.common` (B02) and `app.scoring.metrics` (B05). The plan text above is their spec. The auto-pause therefore takes effect only once A07 exists.
- Not measured: e2b speed and accuracy on the real schema. The 20-post read-through is still required before any larger run.
- Impact on other tracks: none. `AGENTS.md` §4 spend rule ("hundreds of dollars on Opus") is now obsolete for the ETL; it is human-owned.

## D-009 — Separate `CDS_MODEL`; documentation sweep after D-006/D-007/D-008
- Step: docs · Date: 2026-10-23 · By: Jmar L. Pineda via Claude Code
- Problem found: the plan's CDS PDF loader (A10, §2.9.9) read `settings.etl_model`, which is now a local Gemma tag, while it calls the Anthropic PDF API.
- We did: added `cds_model` (env `CDS_MODEL`, default `claude-opus-5-5`) to the plan's `Settings` (B01), §0.3 and `.env.example`, and pointed the CDS loader at it. Whether CDS extraction should also move to a local model is still a human decision (A10).
- Stale text fixed: `AGENTS.md` §4 (not everything uses Claude; spend/heads-up rule now covers local model runs; PullPush rate-limit note replaced with Arctic Shift), plan schedule rows and risk row (Opus-vs-Haiku comparison, 200-post smoke test, ~2 h full extraction), `services/api/README.md` (local models section), `docs/zetaris-setup.md` (auto-pause note), `docs/ROADMAP.md` (A10 note). `AGENTS.md` is human-owned; the edits were made at the human's explicit request.

## D-010 — CDS extraction moves to local Gemma (supersedes the CDS part of D-009)
- Step: A10 · Date: 2026-10-23 · By: Jmar L. Pineda via Claude Code (human decision: "Move the CDS extraction to Gemma")
- Plan said: send the CDS PDF to Claude as a base64 document and parse into `CDSExtract` (`CDS_MODEL=claude-opus-5-5`).
- We did: `CDS_MODEL=gemma4:e2b` through `app/local_llm.py`. Ollama has no PDF input, so `etl/load_cds.py` extracts layout-preserving text per section with `pypdf` (replacing the page slicer), asks three small questions (counts, tests/GPA, the C7 grid) instead of one 40-field form, and runs `sanity_check()` (impossible values are nulled and noted in `data_quality.notes`; "63" becomes 0.63). Runs inside `zetaris_paused()`. `data_quality.extractor` records the model. `CDSExtract` and `to_update` keep the plan's shape. `C7Level` is defined locally (and unit-tested against the migration's enum) until B02 provides the shared type.
- Limits: scanned PDFs (no text layer) are skipped with a warning and must be hand-entered; this replaces "Claude reads scanned pages". A 2B-class model can misread a numeric grid, so the Hour-12 human spot-check of C7 for the 5 demo schools is now essential, and `CDS_MODEL=gemma4:e4b` is the first thing to try if it misreads.
- Not run: no real CDS PDF was available (never guess URLs), so only synthetic PDFs, mocked model calls and the sanity checks are tested. Accuracy on real CDS pages is unmeasured.
- Impact on other tracks: none. `ANTHROPIC_API_KEY` is now needed only by the live agents (Track B).

## D-011 — Meterless Nightshift (primary provider) and the World Model engine
- Step: S03 / B17 / B18 / D10 · Date: 2026-10-23 · By: Jmar L. Pineda via Claude Code (human decisions: World Model as the engine; Nightshift primary with Claude kept selectable)
- Source: Open Agent Hackathon 2026 Participant Setup Guide (21 Oct 2026, read from the PDF) plus meterless.ai and the Meterless repo's `engines/world-model/AGENTS.md`.
- Plan said: Claude (`claude-opus-5-5`) is the only live-agent provider (§0.2, §3.5.2).
- We did: plan §1.7 (rules, provider contract, World Model design, Nemotron lanes, risks), §0.2/§0.3/§0.4 rows, §3.5.2 note, §6.3 ladder rung, §6.4 risks, §7.4 checklist; `LLM_PROVIDER=meterless` becomes the default with `anthropic` selectable; new env vars `METERLESS_BASE_URL`, `METERLESS_RUNTIME_TOKEN`, `METERLESS_MODEL`; `docs/meterless-setup.md`; `scripts/smoke_meterless.py` with tests; roadmap S03, B17, B18, D10. Offline ETL (Reddit/CDS extraction, embeddings) stays on local Ollama. Probabilities still come only from `app/scoring/`.
- Not done (needs a human or Track B): installing Nightshift (account email verification and a download; no Linux edition), entering the NVIDIA key in Nightshift, pinning a Nemotron lane, `app/meterless.py`, the World Model sidecar and its conformance run. Provider details marked **(verify)** in §1.7 are unconfirmed until run against a real Runtime.
- Risks: the dev machine is Linux and Nightshift has no Linux edition, so eligibility ("Meterless running on your machine") needs a Windows/Mac/DGX machine or an answer from the organizers; the guide also tells teams to check the rules on how much code may be prepared before kickoff. Both need a human to ask.
- Impact on other tracks: Track B owns B17/B18 (they change `llm.py` and the docket builder, B01/B11 territory). `AGENTS.md` §4 updated to say the live agents default to Nightshift.

## D-012 — `llm.parse` reads the unparsed message; `Settings` reads the repo-root `.env`
- Step: B01 · Date: 2026-10-23 · By: Aron via Claude Code (small and obvious fixes, AGENTS.md §7)
- Plan said: `resp = await client.beta.messages.parse(...)`, then branch on `resp.stop_reason` and return `resp.parsed_output` (§3.5.2); `env_file=".env"` (§3.5.1).
- Found: the installed SDK (`anthropic` 2.2.0) validates every text block against the schema inside `parse()`, whatever the stop reason. A `max_tokens` cut raises a bare pydantic `ValidationError` before our check, so `LLMTruncated` was unreachable; and with `fallbacks="default"` the declined model's partial text before the `fallback` block is validated too (a rescued call would fail, or `parsed_output` could return the wrong model's answer). Reproduced with a mocked transport in `tests/test_llm.py`.
- We did: same request through `client.beta.messages.with_raw_response.parse(...)` (identical parameters, betas and fallbacks), build a `BetaMessage` from the raw JSON, branch on `stop_reason`, then `schema.model_validate_json()` on the text after the last fallback block (the same rule `stream_text` already used, now shared as `_final_text`). `parse` uses PEP 695 generics for ruff. `env_file` is the repo-root `.env` plus `services/api/.env`, matching `app/local_llm.py`, because the README puts `.env` at the root and the API runs from `services/api`. Plan §3.5.1/§3.5.2 updated.
- Impact on other tracks: none; signatures and exceptions are unchanged.

## D-013 — B03 ships the API skeleton on a scripted stream; session lock moves into `start()`
- Step: B03 · Date: 2026-10-23 · By: Aron via Claude Code
- Plan said: §4.3 `main.py` imports `db`, `zetaris_repo`, `zetaris`, `demo`, `scoring.whatif`, `fake_llm`; §4.4 `runs.py` drives `graph.astream` and persists with `db.append_event_log`. None of those modules exist yet (B06, B07, B13, B14, A13).
- We did: `main.py` has the routes whose dependencies exist (`POST /api/evaluate`, `GET /api/evaluate/{id}/stream`, `GET /api/evaluate/{id}`, `GET /api/health` without the db/zetaris probes) plus `GET /api/dev/fake-stream` (§6.3). `runs.py` is the plan's `Run`/`RunManager`/`sse_frames`, but `_drive` replays `data/fixtures/fake_stream.json` instead of the graph (marked "B13 replaces this loop"); `ScoringContext`, `scoring_context`, `start_child`, the snapshot's DB fallback and event-log persistence wait for B06/B07/B13. `/api/dev/fake-stream` streams the script directly (`script_frames`, `?speed=`, resumes from `Last-Event-ID`) without creating a run. The fixture has the same shape as a recorded `event_log` (`{"name", "school_slug", "events": [envelope…]}`), so D06 can drop in a real recording; it is fictional (Maya at UIUC), validated against the §3.3 schemas in `tests/test_runs.py`, and covers every §1.6 event except `radar` (RadarData arrives with B10). `probability.scoring_inputs` is `{}` until B06 defines `ScoringInputs`.
- Fixed in the plan too (§4.4): `_active_sessions.add` moved from `_drive` into `start()`. In the plan's version two quick submits from one session both passed `_admit` before the task started, so the second ran (and billed) a duplicate. `sse_frames` binds `i` as a lambda default (ruff B023; same behavior).
- Impact on other tracks: C/D can build against `POST /api/evaluate` → `/stream` (the real path) or `/api/dev/fake-stream`. The envelope and event names follow §1.6/§4.2 unchanged.

## D-014 — Probability waterfall and interval stay consistent at the clamps
- Step: B06 · Date: 2026-10-24 · By: Aron via Claude Code (small and obvious fixes, AGENTS.md §7)
- Plan said (§3.6.3): the twins component is `p_final − p_model`, where `p_model` is `sigmoid(L)` clamped to [0.005, 0.97]; `p_low`/`p_high` are the raw posterior percentiles.
- Found (tests/test_probability.py): when `p_model` hits a clamp (e.g. base 0.80, ×2.0 multiplier, strong ratings), the bars before twins sum to the unclamped `sigmoid(L)`, so the waterfall missed `p_final` by 1.5 pp, failing §3.10 "Waterfall integrity" (≤ 0.5 pp). The interval was also unclamped, so the UI could show "up to 99.96%" next to a capped 97% or a 0% lower bound.
- We did: the twins bar is measured from the last bar (`p_final − sigmoid(L)`, `logit(p_final) − L`), which is identical to the plan whenever no clamp fires; `p_low`/`p_high` are clamped to [P_FLOOR, P_CEIL]. `with_overrides` lost its quoted annotation (ruff UP037). Plan §3.6.3 synced. Counterfactual reproducibility is unaffected.
- Not in this step: the `/api/what-if` route itself. `run_what_if` is done and tested with a stand-in context, but the route needs `RunManager.scoring_context` (deferred in D-013 until db/zetaris land). `counterfactuals.py` keeps the plan's `from app import db`; the tests register a placeholder `app.db` until B07 and mock `major_arbitrage`.

## D-015 — `app/agents/state.py` (§3.2) lands with B08
- Step: B08 · Date: 2026-10-24 · By: Aron via Claude Code
- Gap: no roadmap step lists §3.2, but every node imports `AdComState` from `app/agents/state.py`.
- We did: added `state.py` verbatim from §3.2 in B08, its first consumer (all of its imports exist after B02/B06). No other change.
- Also noted, not changed: the plan's `PHONE` regex starts at the first digit, so "(217) 555-0142" redacts to "([phone]". The number is fully removed; only the opening parenthesis remains, so it was left as written.

## D-016 — Track D charts use the planned static-data fallback until C02 lands
- Step: D02 · Date: 2026-10-24 · By: gridiii via Codex
- Plan: section 5.6 examples read the C02 store; section 6.2 explicitly schedules Track D charts against static JSON while C builds that store.
- We did: implement prop-driven gauge and waterfall components and an isolated `/dev/analytics` preview. Component input fields remain structurally compatible with the Python outputs. No shared type, store, existing route, backend, or original scripted fixture was changed. C02 can pass its data and highlight directly when ready.
- Sample arithmetic: the existing scripted waterfall ends at 23.2% while its final estimate is 21.4%. The isolated preview derives the academic contribution as the residual to the script's pre-twin estimate (2.3 pp), preserving the supplied final estimate. Its simulated delta comes from the existing scripted counterfactual. Unsupplied simulation intervals/dispositions stay unavailable. These are explicitly fictional development figures.
- Verified: four arithmetic/edge-case tests, lint, TypeScript, production build, and browser checks for baseline, simulation, loading, evidence details, and model highlighting.
- Impact: D02's component-specific fixture acceptance checks are complete. Live store wiring and the integrated War Room remain pending C02/C03; their checkboxes stay unchanged.

## D-017 — Radar and twin cards follow the same isolated Track D boundary
- Step: D03 · Date: 2026-10-24 · By: gridiii via Codex
- Plan: section 5.6.3-5.6.4 uses shared store and dossier components that do not exist yet; section 6.2 schedules radar/cards on static data first.
- We did: accept compatible presentation props, render a truly dashed and labeled assumed Personal spoke, and add accessible expandable cards with citation-index highlighting and a pulse. Tier labels live inside the card, avoiding changes to Track C. Missing radar comparisons are omitted visibly rather than converted to zero. Missing source links remain unavailable, and usable links must be credential-free HTTPS.
- Samples: five fictional cards preserve the scripted numeric profiles and add original illustrative activities. They have no original-post URLs. Radar normalization follows section 4.7; its admitted count is two sample profiles and its reference data is explicitly fictional. Personal uses the plan's assumed 3.0 reference, not an invented essay median.
- Verified: seven helper/edge-case tests, lint, TypeScript, production build, keyboard expansion, loading and missing-score states, one dashed assumed spoke, one highlighted card, and no production-browser console errors. Tooltip and raw-number formatting were visually reviewed.
- Impact: D03's sample-data acceptance checks are complete; live C02/C03 wiring is still pending. Implementation commits stay local at the human's request; a separate documentation-only branch reports that distinction.

### D-017 publication update (2026-10-24)
- gridiii subsequently authorized publishing the implementation commits to `gridiii/d01-demo-dossiers` only. This supersedes the local-only publication instruction above. Shared `main`, other tracks' source files, and the earlier documentation-only branch remain unchanged.
- The local setup audit is recorded in `docs/gridiii-setup-status.md`. No additional implementation step is claimed complete by publishing the branch.

Publication note: Track D entries originally numbered D-014/D-015 were renumbered D-016/D-017 while merging the newer Track B entries, preserving both tracks’ decisions.

## D-018 — Track D integration after C02–C08 land
- Date: 2026-10-24 · By: gridiii via Codex · User scope: complete Track D, improve charts, and merge the verified result into main.
- D04 keeps drafts and errors per run, debounces requests, aborts stale transports, and refuses late responses even if a transport ignores cancellation. One controller is mounted in WarRoom because its responsive layout mounts more than one analytics panel. The shared event/types/store contracts remain unchanged.
- The current backend has deterministic what-if math but no HTTP route or live scoring context. Component lifecycle tests pass; D04's HTTP/browser acceptance is left open until replay integration is verified. Live graph, real data, hosting and Meterless evidence must not be claimed complete from fictional samples.

## D-019 — Reproducible fictional fixtures use the scoring implementation
- Step: D06 · Date: 2026-10-24 · By: gridiii via Codex.
- The earlier hand-written stream's waterfall did not sum to its final probability. D06 now builds probabilities, intervals, dispositions and four counterfactuals through the real B06 scoring code. The original residual workaround in D-016 is superseded by these generated fixtures.
- Per-schema inputs are explicitly fictional; B08 runs offline with the fixture provider. A four-turn, 100-event stream includes radar, complete dossier courses, accessible missing-source states and exact citation spans. Source URLs are absent rather than pointing to an unrelated subreddit listing.
- The full War Room runs without provider keys using the plan's hand-written fallback. It is not a live graph recording, corpus validation, or partner judging evidence. A real graph recording remains a release gate after B13/B14. Shared store tests were adjusted for the new four-turn fixture; the analytics tests now use the team's Vitest runner.

## D-020 — Portable replay and what-if HTTP adapter
- Step: D07 / D04 acceptance · Date: 2026-10-24 · By: gridiii via Codex.
- B14 is not implemented yet. The plan's portable replay in `app/demo.py` is mounted with minimal `main.py` lifecycle/route wiring. It provides resume by event ID, explicit fictional provenance, registered snapshots and saved deterministic scoring context. The fixture provider is installed only in explicit FAKE_LLM mode.
- `/api/what-if` runs the existing B06 math on a saved replay context. For live run IDs it delegates to `RunManager.scoring_context` when Track B adds that method; until then it returns 503. Real input is never replaced with Maya's fixture. No event or Python/TypeScript schema contract is changed.
- Shift+R and restart create a fresh replay; editable controls ignore the shortcut. Only available replay school tabs are shown. Responsive header overflow and Unix-second timer display were fixed while integrating the room. HTTP tests and browser replay/pivot/reset/phone checks passed. Real graph recordings remain pending, with a recorder supplied for the team.

## D-021 — Integrated charts and actionable analytics
- Step: D05, D02/D03 integration · Date: 2026-10-24 · By: gridiii via Codex.
- Replaced Track C's temporary analytics summary with the prop-driven Track D components, using the existing shared store unchanged. Pivots bind to numeric counterfactual IDs; Try it starts a fresh draft, opens the controls and moves the gauge. Essay copy success is shown only after the clipboard operation succeeds.
- The gauge and waterfall use responsive SVG geometry. Floating contributions use actual start/end coordinates rather than a positive/negative stacked-bar offset; decreases, zero values and totals below zero retain their scale. Evidence tables remain accessible. Radar keeps its dashed assumed Personal spoke and explicit missing values.
- Browser checks passed on the wide room, laptop drawer and 390px phone layout, including no horizontal body overflow, pivot/reset and replay restart. The separate preview imports the same Python-generated fictional fixtures, avoiding a second set of hand-entered probabilities. Full live data remains a separate integration gate.

## D-022 — Same-origin web proxy and deployment preparation
- Step: D08 preparation · Date: 2026-10-24 · By: gridiii via Codex.
- Zetaris occupies port 3000, while the local web app uses 3001 and the API's default CORS allows only 3000. The web now defaults to relative API URLs and rewrites `/api/*` to the server-side `ADCOM_API_URL` origin (local default port 8000). Explicit `NEXT_PUBLIC_API_URL` remains supported for deployments using direct API access and configured CORS.
- Added the Vercel web settings, frontend environment example and deployment handoff. No private keys are exposed in frontend configuration; no public tunnel, cloud resource or account was created. The Next tracing root is pinned to the web project, removing the unrelated home-directory lockfile warning.
- D08 remains open: the user does not yet know the hosting project, B16/live graph are unfinished, and no hosted live run from a phone was verified. A production deployment is not claimed from a local build.

## D-023 — Pitch and data disclosure distinguish verified metrics from fixtures
- Step: D09 preparation · Date: 2026-10-24 · By: gridiii via Codex.
- Added an accessible About-the-data panel and `data/data-report.json`. Unknown real corpus, coverage and calibration results remain null and display "Not verified yet". The landing page's unsupported 10,000+ applicant claim was removed; a direct fictional-demo link was added.
- `docs/pitch.md` is a complete rehearsal script for the current prototype, with calculated fixture figures labeled illustrative and all live proof gates explicit. It does not present an authored replay as a live provider run. D09 remains open until A15/A16 deliver real figures and the final live pitch can be verified.

## D-024 — Track D release evidence remains an explicit gate
- Step: D10 preparation / final Track D verification · Date: 2026-10-24 · By: gridiii via Codex.
- The user authorized completing Track D and merging the verified work into main. They confirmed hosting and the Meterless demo machine are not set up or known. Code, fixtures, replay, charts, pitch and deployment handoffs were completed within that available scope.
- Final checks: 171 API tests and ruff pass; 43 web tests, lint, TypeScript and production build pass; fixture rebuilds are byte-for-byte deterministic. Browser checks cover the integrated replay, pivot/reset, restart, keyboard cards, copy feedback, data disclosure and responsive layouts.
- D08–D10 stay unchecked until actual hosted live acceptance, verified A15/A16 metrics and real Nightshift/Nemotron plus World Model evidence exist. No paid calls, model loads, public tunnel or cloud account setup was performed. B13/B14/B16/B17/B18 are not claimed complete by Track D.

## D-025 — Scorecard school filter widened from admit rate ≤ 40% to ≤ 60%
- Step: A09 · Date: 2026-10-24 · By: Jmar L. Pineda via Claude Code
- Plan said: `latest.admissions.admission_rate.overall__range` of `0..0.40` and "~250 schools" (§2.9.8, §2.9.1 table). Measured against the live API (enrollment ≥ 1,000) that matches only 125 schools, plus the seeded ones: 126 loaded, under the step's ≥200 target.
- We did: raised the cap to `0..0.60` (about 265 schools; 0.50 gives 183, still short) and fixed both plan lines. Also silenced the `httpx` INFO logger in `etl/common.py`, because request URLs print the Scorecard `api_key`.
- Impact on other tracks: more schools and aliases in `universities_cds` and `school_aliases`. Mid-selectivity schools will have fewer Reddit twins.

## D-026 — A07 extraction token cap raised; smoke-run findings
- Step: A07 · Date: 2026-10-24 · By: Jmar L. Pineda via Claude Code
- Plan said: `num_predict=900` and "about 400 output tokens" per record (§2.9.6, §2.9.4). On `gemma4:e2b` Ollama pretty-prints the JSON, and one record took 1,236 tokens, so 14 of the first 20 posts were rejected as truncated.
- We did: `num_predict=2500` in `etl/extract_reddit.py` and the plan's code block. Re-run: 13 kept, 7 rejected (5 not a results post, 1 no resolved school, 1 still truncated).
- Measured speed: ~9 s per post on an RTX 4070 Laptop (7.7 GiB), so 3,000 posts is about 7.5 h. `CAPS` unchanged.
- Open quality issues found reading the 13 rows against their posts (not fixed here, awaiting a human decision): (1) `applicant_type` was "transfer" for 11 of 13 r/collegeresults posts that never mention transferring; (2) `demographics.residency_state` is a region or free text ("Northeast", "bay area") in 12 of 13 rows, not a two-letter code. Numbers (GPA, SAT, ACT) all appeared verbatim in the posts.
- Impact on other tracks: none yet. A08 will embed whatever is in `twins.jsonl`, so settle (1) and (2) first.

## D-027 — Applicant type from the subreddit; residency_state normalized in code
- Step: A07 · Date: 2026-10-24 · By: Jmar L. Pineda via Claude Code
- Plan said: the model fills `applicant_type` and `demographics.residency_state` (§2.9.3, §2.9.6). On `gemma4:e2b` it marked 11 of 13 r/collegeresults rows "transfer" with no mention in the posts, and gave a region or free text instead of a state code in 12 of 13 rows (D-026).
- We did: in `to_row`, `applicant_type` is "transfer" for r/TransferToTop25 and "first_year" otherwise; `residency_state` keeps only a two-letter code or a full state name (mapped to the code) and is otherwise null. The schema and prompt are unchanged.
- Known edge: a transfer applicant who posts in r/collegeresults is now labeled first_year (1 of the 13 smoke posts says "Transfer applicant"). Accepted as the cheaper error; revisit if the twin pool needs it.
- Re-run of the 20 smoke posts: 13 kept, 7 rejected, all kept rows first_year, residency 3 codes and 10 nulls.
- Impact on other tracks: none. A08 can embed `twins.jsonl`.

## D-028 — Extraction number gates aligned with the applicant_twins CHECK constraints
- Step: A08 · Date: 2026-10-24 · By: Jmar L. Pineda via Claude Code
- Plan said: `_clean_numbers` validates GPA, SAT total, ACT and rank only (§2.9.6). The first live upsert failed on `gpa_w_scale = 100.0` (`numeric(3,1)`); the row also had `gpa_w = 97.5`, a 100-point grade put in the weighted field.
- We did: `_clean_numbers` now also nulls `gpa_w` outside 0–6 (with `gpa_w_scale`), `gpa_w_scale` outside 0–10, `college_gpa` outside 0–4, `sat_math`/`sat_ebrw` outside 200–800 and `ap_count` outside 0–30, recording an issue for dropped weighted GPAs. `class_rank_pct` must now be strictly between 0 and 1: a rank of 1.0 (bottom of the class) was the model misreading "top 1%". One bad value no longer fails a 500-row upsert batch.
- Re-extracted the 20 smoke posts (13 kept, 7 rejected) and loaded them: `match_applicant_twins` returns UCLA neighbors, the query's own row first.
- Impact on other tracks: none.

## D-029 — `run_etl` imports the Zetaris stages lazily; no override entries yet
- Step: A11 · Date: 2026-10-24 · By: Jmar L. Pineda via Claude Code
- Plan said: `run_etl.py` imports `setup`/`refresh_gold` from `.zetaris_setup` at module top (§2.9.10). That module is A14, so the whole CLI would fail to import until then.
- We did: `zetaris-setup` and `zetaris-refresh` import `etl.zetaris_setup` when run; all other stages work now. `data/major_overrides.yaml` contains only comments and the shape, because overrides must come from an official admissions page and none has been checked.
- Verified: `refresh-stats` ran against the 13 smoke twins (0 schools updated: no major reaches n ≥ 15). The five data-quality queries were run through the REST API with aggregation in Python, since no direct SQL connection is configured; run the original SQL in the dashboard for the Hour-8 and Hour-14 checks.
- Impact on other tracks: none.

## D-032 — Migration 0010: read policies on zetaris_export for zetaris_reader
- Renumbered from D-030, which B13 (`8909f16`) had already taken; commit `ce5de69` still cites it as D-030.
- Step: A12 · Date: 2026-10-25 · By: Jmar L. Pineda via Claude Code
- Plan said: grant `select` on the `zetaris_export` tables to `zetaris_reader` (§2.10.3, migration 0009). On this Supabase project RLS is enabled on new tables automatically, so with no policy the reader saw 0 rows although `refresh_twin_stats()` filled the tables (confirmed: `relrowsecurity = t`, no policies, 0 rows via the pooler login).
- We did: `supabase/migrations/0010_zetaris_export_rls.sql` adds a `for select to zetaris_reader using (true)` policy per export table. RLS stays on for every other role.
- Impact on other tracks: none. Anyone rebuilding the database applies 0010 after 0009.

## D-031 — Zetaris DDL confirmed against the running stack; plan SQL corrected
- Step: A12 · Date: 2026-10-25 · By: Jmar L. Pineda via Claude Code
- Plan said: `currentSchema=zetaris_export` in the JDBC URL selects the export schema; `CREATE ROLE x`, `ASSIGN USER email`, `GRANT SELECT ON ADCOM.view`; DDL via the query route (§2.10.4, §2.10.5).
- Found and fixed: (1) `REGISTER DATASOURCE TABLES` ignored `currentSchema` (and the pooler ignores role-level `search_path`) and listed `public` tables; the datasource option `schema "zetaris_export"` selects the right ones. (2) The query route accepts only `SELECT`; DDL goes to `/api/proxy/sql-editor/sqls/run`. (3) Descriptions cannot contain `+` or `:`. (4) `CREATE ROLE`/`ASSIGN USER` take quoted names; grants are `ON VIEW TABLE ADCOM.<view>` and `ON DATALAKE TABLE ...`. (5) The agent password needs a special character from `$@!%*?&`. (6) `v_peer_benchmarks` self-joined `v_school_profile`, which Spark rejects; rewritten with window functions, same output. (7) `v_school_profile.admit_rate_source` said `cds` for Scorecard values; it now says `cds` only when a CDS year exists, else `scorecard`.
- Removed every "(verify at Hour 1)" marker; plan SQL blocks, `zetaris/sql/*.sql` and `docs/zetaris-setup.md` now match what ran. Views are granted one by one; `v_ipeds_c7` stays internal.
- Verified live: as `adcom_agent`, `ADCOM.v_school_profile` (uiuc), `ADCOM_LAKE.gold.school_profile` and `v_peer_benchmarks` read fine; `ADCOM_PG.universities`, `ADCOM.v_ipeds_c7` and `ADCOM_PUBLIC.scorecard_institutions` are denied; `zetaris_repo.school_profile('uiuc')` returns `data_source: zetaris`; `./verify.sh` 9 PASS.
- Impact on other tracks: A14's `zetaris_setup.py` must use the DDL route above. Track B's Zetaris tool needs nothing new.

### D-021 production breakpoint follow-up
- Production browser testing at exactly 1440px exposed overlapping desktop/laptop layout variants. The laptop grid now applies only within its explicit 1024–1439px range. A rebuilt production page verifies one visible dossier, one analytics sidebar and no horizontal body overflow at 1440px. Lint, types and production build pass after the correction.
- The final narrow-sidebar radar review exposed a clipped Personal label and crowded raw values. Long axis labels now wrap onto two lines and numeric columns have fixed, right-aligned widths. The rebuilt production chart was visually checked with the complete assumed label visible and separate comparison columns.

## D-030 — CLI runner reads and prints UTF-8; file reads moved out of the async main
- Step: B13 · Date: 2026-10-25 · By: Aron via Claude Code
- Plan said: `scripts/run_graph_cli.py` reads dossier files with `Path.read_text()` and prints ✔ ━ · ⚙ ◆ ⚠ (§3.9.2).
- We did: files are read with `encoding="utf-8"`, and `main()` calls `sys.stdout.reconfigure(encoding="utf-8")`. On a Windows console the default cp1252 codec raises `UnicodeEncodeError` on the first ✔ and can mis-read essays (the same failure as the earlier `[fix]` commit for fixture JSON). The input building moved into a sync `_inputs()` helper because ruff `ASYNC240` rejects blocking `Path` reads inside an async function. Behaviour is otherwise identical; the plan text is updated.
- Also in B13: `tests/test_demo.py::test_unavailable_live_context_is_never_substituted_with_maya` (Track D) asserted the pre-B13 503 "not integrated yet". With `RunManager.scoring_context` in place an unknown run is a 404; the test now mocks `db.load_run` and asserts 404, keeping its never-substitute-Maya intent.
- Impact on other tracks: Track D's test above changed expectation (503 → 404).

## D-033 — Fixture generation is independent of the machine's text encoding
- Step: D06 handoff fixes (Aron D-1/D-3) · Date: 2026-10-25 · By: gridiii via Codex.
- Fixture tests and the generator still relied on the platform's default text encoding. On Windows this changed the probability-detail strings; writing the Unicode fixture output could fail as well. Both reads and writes now specify UTF-8.
- A subprocess regression rebuilds the copied fixture tree with an ASCII locale and Python UTF-8 mode disabled, then checks the generated bytes against the checked-in artifacts. The targeted fixture/encoding suite also passes under that locale.
- The fake chair's closing content now includes `RECOMMENDATION:` from the computed disposition. Regenerated authored replay artifacts retain their fictional provenance; no live recording is implied. Frozen events and schemas are unchanged.
- Verified: 298 API tests, ruff, 43 web tests, lint, types and production build pass. A production proxy replay completes all 101 events and the real scoring-based what-if still gives the same fictional result.

## D-034 — CDS loader accepts the Excel template (.xlsx and Google Sheets), not only PDFs
- Step: A10 · Date: 2026-10-25 · By: Jmar L. Pineda via Claude Code
- Plan said: `cds_sources.yaml` holds PDF links and every section goes through `pypdf` text and the local model (§2.9.9).
- Found: UIUC and UC Berkeley publish only the official CDS Excel template (a Box `.xlsx` and a Google Sheet). Both have one sheet per section, with item codes (`C701`…) in column A and answers as plain cells.
- We did: `etl/load_cds.py` detects an `.xlsx` (zip magic), turns a Google Sheets share link into its `/export?format=xlsx` URL, reads C7 deterministically from `C701`–`C718` (no model call, so no misread "Very Important"), and feeds the counts and tests sections to the same two model questions as `code | question | answer` rows (C1 totals, C21/C22, D1–D2; C8, C9, C11, C12). Adds the `openpyxl` dependency. Also: the xlsx test policy comes from item C802, and `cds_year` is an optional field in `cds_sources.yaml` because the spreadsheets print no year.
- Also found in the first live run: gemma4:e2b misread the PDF C7 grids (CMU came back all "Very Important", Georgia Tech all "Important"). `pdf_c7()` now reads the grid by the column of each X, or by the level text at the end of a form-field row (UMich), and only falls back to the model when fewer than 14 rows parse. The bigger-model fix suggested in D-010 was not needed. `cds_sources.yaml` keeps the original share link as the source URL.
- Second verification pass (the spot-check against the sources found more model errors): Georgia Tech applicants/admits were a men-only figure and a transfer figure (40,022 / 846 instead of 59,789 / 8,413), CMU kept stale Scorecard SAT/ACT values, and Berkeley carried an invented top-10% and 0% submission. So the loader now reads these without the model: first-year applied/admitted/enrolled totals in PDFs (`pdf_c1_totals`), C9 percentile rows in PDFs (`pdf_percentiles`), and every C9/C10/C12 field in spreadsheets by row label (`xlsx_tests`; a blank or 0 row clears the field). `cds_sources.yaml` also takes an `overrides:` map for hand-curated values (CMU `test_policy: optional`, from its C8A "Consider if Submitted"). The model still handles the remaining PDF fields (GPA, top-10%, early plans, transfers).
- Impact on other tracks: none.

## D-035 — API container: `--no-dev` start command, host Ollama for embeddings, repo-root `.dockerignore`
- Step: B16 · Date: 2026-10-25 · By: Aron via Claude Code
- Plan said: `CMD ["uv", "run", "uvicorn", …]` after `uv sync --frozen --no-dev`, and an overlay that only sets `ZETARIS_URL` (§4.10).
- We did: (1) the command is `uv run --frozen --no-dev uvicorn …`. A bare `uv run` re-syncs the default groups, so the container would try to download pytest and ruff at start and fail offline. (2) The overlay sets `OLLAMA_URL: http://host.docker.internal:11434` plus `extra_hosts: host.docker.internal:host-gateway`. Since D-007/D-010, Node 1 embeds the profile with `embeddinggemma` on the host's Ollama, and `localhost` inside the container is the container itself, so every live run would fail at Node 1. (3) A repo-root `.dockerignore`: the build context is the repo root, which would otherwise send `zetaris-platform/` (keypair `.env`, 27 MB jar), `.env`, `.venv` and `node_modules` to the daemon. Plan §4.10 is updated to match.
- Also in B16: `/api/health` now uses the plan's §4.3 handler (DB and Zetaris probes), because B16's done-when checks `zetaris: true`. B15 keeps prewarm, rate limits and the dossier cache.
- Impact on other tracks: the demo host needs Ollama running with `embeddinggemma` pulled (D08). Not needed for `FAKE_LLM=1`, which replaces the embedder.

## D-036 — Dossier cache key includes hooks and context; startup prewarm runs in the background
- Step: B15 · Date: 2026-10-25 · By: Aron via Claude Code
- Plan said: `dossier_key` hashes the uploads, the pasted texts and `intended_major` (§7.4), and `lifespan` awaits the Supabase warm-up and three Zetaris reads per prewarm school before the app starts (§4.3).
- We did: (1) the key also hashes `hooks` and `context`. Node 1 sends both to the grader and builds the embedded profile text from `context` (first-gen, income, residency), so the plan's key would hand a cached grade and embedding to the same files submitted with a different context. Field order is fixed and fields are separated by a NUL byte, so moving text between fields changes the key. (2) The prewarm runs as a background task and is skipped when `ZETARIS_ENABLED=false`. Awaited before startup, every unreachable read waits out the 5 s connect timeout (15 reads for the five schools), and with the A-1 gap the reads try Zetaris even when it is disabled. Measured: startup 0.57 s with Zetaris enabled but unreachable. (3) The watchdog's 15 s poll is the module constant `WATCHDOG_INTERVAL_S`, so tests can shorten it. Plan §4.3 and §7.4 are updated to match.
- Impact on other tracks: none. The demo still warms the cache by running Maya's exact files once (§7.4); a different `context` on stage would not hit it.

## D-037 — A15 closes at 947 twins, not 10,000; alias list rebuilt
- Step: A15 · Date: 2026-10-26 · By: Jmar L. Pineda via Claude Code
- Plan said: at least 10K twins loaded (roadmap A15, §2.9.11, §7.5).
- Found: the capped Reddit source holds 3,579 posts, 1,487 of which mention a decision; extraction at 8.9 s per post kept 947 (the database holds exactly those). More twins need another source or a wider scrape, which is a scope call for the team; the human made it optional step A18 in `docs/ROADMAP.md`, to be done only if time remains before the submission deadline.
- We did: ran the full capped extraction, loaded the twins, refreshed stats and the Zetaris gold table, and wrote `docs/data-report.md` with the real numbers. The first run lost many decisions to unaliased school names (Cornell, Columbia, USC, NYU…) and two alias entries pointed at slugs that do not exist (`upenn`, `washu`); `data/school_aliases.yaml` now covers 87 schools and the extraction was re-run (95 → 12 posts rejected for no resolved school).
- Impact on other tracks: Track D can fill `data/data-report.json` with n_twins 947, n_schools 265, n_cds_schools 5 and must not claim 10,000+. Track B's calibration now rests on 947 twins.

## D-038 — Report the real corpus without implying a completed accuracy backtest
- Step: D09 data disclosure / pitch · Date: 2026-10-26 · By: gridiii via Codex.
- A15 now supplies real corpus, school coverage and an approximate Reddit odds adjustment. The public manifest records those reported figures, its date and an immutable source-report link, with partial status; Brier values stay null until A16 exists.
- The About-the-data panel displays 947 profiles, 265 universities, five CDS schools, the five demo-school coverage rows, and the scoped 3.24× median odds inflation. Its fictional-replay notice appears on the authored replay, and it explicitly distinguishes those profiles from the real dataset. An odds adjustment is not presented as predictive accuracy.
- The panel uses the existing dialog trigger for keyboard focus restoration. Production checks verify the reported figures, unmeasured Brier labels, Escape returning focus, and a 390px layout without horizontal panel overflow. The pitch includes the same evidence and leaves live-run/backtest claims open.
- Verified: 340 API tests and ruff; 43 web tests, lint, TypeScript and production build pass. Frozen event and schema contracts are unchanged. D09 remains open for A16 and the final recorded-run figures.


## D-039 — Zetaris-off fallback fixed in Track A's repository (A-1); fake mode never reaches the paid client
- Step: B14 · Date: 2026-10-26 · By: Aron via Claude Code, with the human's explicit OK to edit Track A's file. **@Jmar: please review the `zetaris_repo.py` change.**
- Plan said: with `ZETARIS_ENABLED=false` "every Zetaris read falls back to Supabase" (§2.10.10, §4.9), and `FAKE_LLM=1` lets developers run without keys (§4.9).
- Found: only `school_profile` checked the flag. `peer_schools`, `reddit_calibration` and `admitted_medians` always called Zetaris, and every fallback caught only `ZetarisError`, while a stopped stack raises `httpx.ConnectError` from the client's login. Node 3 crashed on any machine without Zetaris (handoff item A-1). Node 2's SQL tool loop had the same gap. Separately, `fake_llm.install()` replaced `llm.parse` and `llm.stream_text`, but the SQL tool loop calls `llm.client` directly, so `FAKE_LLM=1` with Zetaris enabled would have made real, paid Anthropic calls. The CLI never installed fake mode at all.
- We did: `zetaris_repo.py` gains `UNAVAILABLE = (ZetarisError, httpx.HTTPError)`, used by all four fallbacks, and the three reads return the Supabase copy straight away when the flag is off. Other exceptions still surface. `agents/zetaris_tool.py` treats an unreachable stack as a failed query. `fake_llm.install()` also replaces `run_zetaris_research` with a no-op, and `scripts/run_graph_cli.py` installs fake mode when `FAKE_LLM=1`. Plan §2.10.5, §2.10.7 and §4.9 are updated to match.
- Verified: new `tests/test_zetaris_fallback.py` (flag off, connect error, read timeout, `ZetarisError`, and a non-connectivity error that must surface); the real graph completes in fake mode with Zetaris disabled and with it enabled but unreachable, with the Anthropic client replaced by a guard that fails on any use; the CLI completes in fake mode.
- Impact on other tracks: Track A owns `zetaris_repo.py` (review requested above). Track C/D developers can run `FAKE_LLM=1 ZETARIS_ENABLED=false` without the Zetaris stack; Supabase is still needed for twins.

## D-040 — `llm.parse` passes an explicit timeout so Node 1's long requests are allowed
- Step: fix (found on the first live attempt) · Date: 2026-10-26 · By: Aron via Claude Code
- Found: every live evaluation failed in Node 1 with `ValueError: Streaming is required for operations that may take longer than 10 minutes`. When a non-streamed request sets no `timeout`, the Anthropic SDK (2.2.0) estimates 3600 s × `max_tokens` / 128,000 and refuses anything over 10 minutes, i.e. above about 21,300 tokens. Node 1 asks for 32,000 (extractor) and 24,000 (grader). The error is raised before any request is sent, so nothing was billed. B01's tests replaced the client, and the transport-level test used the default 16,000, so they never reached the check.
- Plan said: `client.beta.messages.with_raw_response.parse(...)` with no timeout (§3.5.2), with the max_tokens values above (§3.7.1).
- We did: `llm.parse` passes `timeout=parse_timeout(max_tokens)`, the SDK's own estimate with a 10-minute floor (900 s for 32,000) and a 5 s connect timeout. The call keeps the plan's shape (structured output, raw-response handling from D-012, fallbacks) and its max_tokens values. Streaming was the alternative, but it would change the parse path and its D-012 handling. Plan §3.5.2 is updated to match.
- Verified: a new transport-level test runs the real SDK with 32,000, 24,000 and 16,000; without the fix the first two fail with this exact `ValueError`. The debate (`stream_text`) already streams and the other parse calls are at or under 16,000.
- Impact on other tracks: none. Live runs can now get past Node 1; they still need `ANTHROPIC_API_KEY` and spend approval.

## D-041 — The committee room shows a failed run instead of "assembling" forever
- Step: fix in Track C's files (C04/C07 area), with the human's explicit OK · Date: 2026-10-26 · By: Aron via Claude Code. **@egli3: please review `CommitteeRoom.tsx` and the new `runFailure` helper in `store/run-store.ts`.**
- Found: when a run fails before the debate starts, the API sends an unrecoverable `error` and then `done` with status `failed`. The store already recorded both (`errors`, `status`), but no room component read them, so `CommitteeRoom` kept showing "The committee is assembling." indefinitely. That is what the first live attempt looked like (the D-040 bug).
- We did: `runFailure(run)` in `store/run-store.ts` returns the latest unrecoverable error's message, a generic message when the run ended `failed` without one, or null. Recoverable node errors, which only mark a node degraded, don't count. `CommitteeRoom` shows a "The committee couldn't meet." panel (`role="alert"`) with that message and links to start a new evaluation (`/`) or watch the demo replay (`/room/demo/maya-uiuc`). The panel replaces the pre-meeting text before the debate, or appears under the turns if the debate had begun, and the typing indicator is hidden once the run has failed.
- Verified: 5 new vitest cases in `store/run-store.test.ts` (48 web tests pass), lint, `tsc --noEmit` and `pnpm build`. In the browser, a run that failed at Node 2 (Supabase unreachable, fake LLM, separate test servers on ports 8010/3010, since stopped) shows the panel with "Evaluation failed (ConnectError)." and both links.
- Impact on other tracks: none on contracts. Event names and payloads are unchanged.

## D-042 — Intake links to the Maya replay use the recording's real name
- Fix in Track C's files, with the human's explicit OK · Date: 2026-10-26 · By: Aron via Claude Code. **@egli3: FYI, two-line change in `IntakeWizard.tsx`.**
- Found: the "Load Maya's file" button and the rate-limit toast's "Replay Maya Demo" action pushed `/room/demo/maya`, but the only recording is `data/demo_runs/maya-uiuc.json`, so both led to "Replay not found". The landing page and the committee room already link to `maya-uiuc`.
- We did: both now push `/room/demo/maya-uiuc`. Verified: 48 web tests, lint, `tsc --noEmit` and `pnpm build` pass.
- Impact on other tracks: none. If a second recording is added later, these links still point at Maya at UIUC.

## D-043 — S03 on Linux: Nightshift runs under Wine
- Step: S03 · Date: 2026-10-26 · By: Jmar L. Pineda via Claude Code
- Plan said: Nightshift has no Linux edition, so the demo machine must be Windows, Mac or DGX Spark (§1.7.1, §1.7.5).
- Found: the Windows edition runs on the Linux dev machine under Wine 11.19 Staging once Microsoft's WebView2 standalone runtime and `vcrun2022` are installed in an isolated prefix. The runtime serves `127.0.0.1:8088` on the host, the NVIDIA and Gemini keys were added in Nightshift's Providers tab, and the Runtime API key went into `.env` only. `scripts.smoke_meterless` prints three PASS lines and the chat answer came from `nvidia/nemotron-3.5-lightning-30b-a3b`. Nightshift also has a built-in Gemini provider, so a free Gemini lane needs no change to `llm.py`.
- We did: documented the Wine route in `docs/meterless-setup.md`. No code changed.
- Open: whether the organizers accept Wine as "running on your machine", and the visual check of Nightshift's run details (the smoke test names the model that answered, but the app's own run view was not inspected). Cosmetic quirks: invisible mouse cursor over the window under Wayland.
- Impact on other tracks: B17 and B18 are unblocked on this machine; the provider keys stay in Nightshift and the app only needs `METERLESS_RUNTIME_TOKEN`.


## D-044 — A16 backtest holds out the latest posts, not the latest cycle
- Step: A16 · Date: 2026-10-26 · By: Jmar L. Pineda via Claude Code
- Plan said: hold out the latest cycle and compare Brier and AUC with a base-rate baseline (§6.2 H16-24).
- Found: 925 of 947 twins are the 2026 cycle, so a cycle split leaves 22 training rows. The ratings the live app gets from Node 1 (an LLM) do not exist for a Reddit post either.
- We did: `services/api/scripts/backtest.py` holds out the latest 30% of posts by `post_created_at` and gives each held-out row twin evidence from earlier posts only. Ratings come from the same statistical anchors Node 1 clamps to (no LLM, no spend); personal and athletic are neutral; the stored major multiplier is held at 1.0 because it is learned from these same posts. Twin neighbours are chosen by GPA and SAT proximity, not embeddings. It adds a within-school AUC, because plain AUC is mostly the school's admit rate. First-gen audit groups use explicit self-report only: the extractor sets a `first_gen` hook on 507 of 947 twins but only 125 state it.
- Result, written to `docs/data-report.md` and `data/backtest.json` as it came out: held-out Brier 0.232 for the app, 0.303 for the official admit rate, 0.216 for the earlier Reddit rate at the school; within-school AUC 0.535. The profile ranks applicants only slightly better than chance, and subgroup gaps are large (for example <$30k income: predicted 28% vs observed 59%).
- Impact on other tracks: Track D can fill `data/data-report.json` Brier fields from `data/backtest.json` (`models.rubric_plus_twins.brier` = 0.232, `models.official_rate.brier` = 0.303) and should describe the result as weak at ranking. Track B should know the first_gen hook flag is probably over-set by the extractor (an A07 follow-up, not changed here).

## D-045 — A17 coefficient fit rejected; priors stay
- Step: A17 · Date: 2026-10-26 · By: Jmar L. Pineda via Claude Code
- Plan said: refit `K_PILLAR`, `K_TEST` and hook effects with a GLM and adopt them only if they pass the §3.9.3 bounds.
- Found: only 538 admit/deny rows qualify (first-year twins at the 5 schools that have real C7 weights; the plan's filter drops the other 260). Fit with the school's base rate and major multiplier as offset: K_PILLAR·academic 2.47 ± 0.43 (inside [1, 4]), K_PILLAR·extracurricular −0.61 ± 0.44, K_TEST −0.45 ± 0.38, first_gen 0.10 ± 0.19; no twin at those schools carries a legacy hook, so that column is empty. Priors are K_PILLAR 2.0, K_TEST 0.5.
- We did: kept every prior. Extracurricular and test coefficients came out negative and are not significantly different from zero, which the Reddit sample cannot be trusted to show (self-selection, stats-only ratings with neutral personal pillar, tiers and test scores that correlate with school choice). The academic estimate supports the prior of 2.0. `etl/fit_coefficients.py` differs from the plan code in dropping waitlists, using `ec_rating_from_tiers` and `sat_equivalent` (the plan's `tier_derived_ec_rating` key is not stored in the twin rows), and dropping all-zero columns so the fit is not singular. No scoring constants changed.
- Impact on other tracks: none. If a judge asks, the honest answer is that the coefficients are priors, and the one coefficient the data could test (academic) is consistent with them.

## D-046 — Zero-cost deployment: Gemini's free tier replaces Claude as the alternative provider; B17 split into B17a–c
- Step: plan change (no code) · Date: 2026-10-26 · By: Aron via Claude Code (human decision: the team agreed on a $0 deployment, recorded in AGENTS.md §4 "Plan B")
- Plan said: Meterless Nightshift primary, with Claude (`claude-opus-5-5`, about $0.60–$1.00 per evaluation, §1.5) as the selectable alternative (§0.2, §1.7.2, D-011). This supersedes the model line of D-001.
- Found: the provider switch (B17) was never built, so every live call still goes to the paid Anthropic API. Every other service fits a free tier: Supabase, Vercel Hobby, Tavily (1,000 credits a month, no card), NVIDIA's trial credits through Nightshift, local Ollama, Zetaris, Scorecard and Arctic Shift.
- We did: plan §0.2, §0.3, §0.4, §1.4, §1.5, §1.7.1, §1.7.2, the §3.5.2 intro, the §1.1 and §1.2 diagram labels, §6.3, §6.4, the budget-guard row and the pitch's privacy answer now describe `LLM_PROVIDER=meterless | gemini | anthropic`. Meterless and Gemini share one OpenAI-compatible client, `app/openai_compat.py`, which replaces the planned `app/meterless.py`. Gemini uses `GEMINI_MODEL` for medium/high effort and `GEMINI_FAST_MODEL` for low effort. Claude stays in code, but the API refuses it unless `ALLOW_PAID_PROVIDERS=true`. Roadmap B17 becomes B17a (provider layer + Gemini, no S03 needed), B17b (Zetaris tool loop) and B17c (real Nightshift check); B18 now depends on B17a and D10 on B17c. README's key table is updated. The code blocks in §3.5.2, the nodes and `/api/health` change with B17a/B17b, not here.
- Why: the team requires zero cost. Gemini's free tier returns 429 instead of billing as long as the key's Cloud project has no billing account.
- Open: per-model free-tier quotas are unverified (published figures range from 20 to 1,500 requests a day; read them in AI Studio). Whether Gemini's compatibility layer accepts the plan's schemas as strict `json_schema` is marked (verify). Google may use free-tier prompts to improve its products, so the intake page needs a notice before real users upload.
- Impact on other tracks: no frozen contract changes. Track C: the intake notice. Track D: `docs/deployment.md` and `docs/meterless-evidence/README.md` still name Claude and B17, and D10 now waits on B17c.

## D-047 — B17a: details of the OpenAI-compatible provider layer
- Step: B17a · Date: 2026-10-26 · By: Aron via Claude Code
- Plan said: §1.7.2 (as rewritten in D-046) lists four provider errors, falls back to the prompt and retries once on `ValidationError`, and maps `effort` to `reasoning_effort`.
- We did: (1) two more exceptions, `LLMBadRequest` (any other 4xx; it triggers the prompt fallback) and `LLMInvalidOutput` (a reply that still fails validation after the retry), so nodes 2 and 3 degrade on bad output instead of crashing; both are in `llm.PROVIDER_ERRORS`. (2) `llm.key_configured()` feeds `/api/health`'s `llm_key`. (3) `openai_compat.py` imports `llm` back for the exceptions; each module only reads the other's attributes at call time, so the cycle is safe and avoids a separate errors module. (4) `reasoning_effort` is sent to Meterless too, with the same retry-without-it on a 400 that names it. (5) Requests use `max_tokens`, not `max_completion_tokens` (verify on both providers). (6) Daily-quota 429s are recognised by "PerDay" in Gemini's quota id (verify against a real 429). (7) `Settings` sets `hide_input_in_errors=True`: the paid-provider check's error otherwise echoed part of the `.env` values. (8) The plan's §3.5.2 block is now the built `llm.py`; `openai_compat.py` is described there rather than copied.
- Not verified: a real `LLM_PROVIDER=gemini` run (no `GEMINI_API_KEY` on this machine yet) and the fake-mode CLI past Node 1 (Supabase is not reachable from this machine; `test_graph` covers the whole graph in fake mode).
- Impact on other tracks: `/api/health` now returns `llm_provider` and `llm_key` instead of `anthropic_key`; the web app does not read it. No frozen contract changes.

## D-048 — Gemini: an overloaded main model falls back to the fast model; first real-run results
- Step: fix after B17a's real run · Date: 2026-10-26 · By: Aron via Claude Code (human decision: add the fallback)
- Found on the free tier: `gemini-3.8-flash` (the default `GEMINI_MODEL`) answered 503 "This model is currently experiencing high demand" on every attempt across four checks. `gemini-3.6-flash` extracted Maya's dossier, then returned 503 three times on the grader. `gemini-3.5-flash-lite` answered every request. With 3.8-flash as the main model, every live evaluation would have failed at Node 1.
- We did: a call whose main Gemini model still returns 503 after its three attempts is sent once to `GEMINI_FAST_MODEL` with the same request otherwise; a stream does this only if no token has been sent. Meterless, other 5xx, connection errors and calls already on the fast model are unchanged. `LLMUnavailable` carries the HTTP `status`. The cost is about 3 s of backoff before the fallback while the main model is overloaded. Defaults are unchanged; `GEMINI_MODEL=gemini-3.5-flash-lite` in `.env` skips the wait.
- Verified against real Gemini (2026-10-26, free tier, about a dozen requests): strict `json_schema` output is accepted for `ParsedDossier` and `DossierGrade` (no prompt fallback was needed); Maya's transcript PDF converted to text gave 30 courses, SAT 1520 and an unweighted GPA of 3.94; the grade came back with no guardrail warnings; `stream_text` streamed a debate turn; `reasoning_effort` low/medium/high and `max_tokens` were accepted. This settles D-047 item (5) for Gemini (Meterless still open). Still unverified: the "PerDay" daily-quota match (item 6) and the whole graph against real Gemini, which needs real Supabase settings.
- Seen in the real fallback check: with the default `gemini-3.8-flash`, two attempts returned 503 and the call moved to `gemini-3.5-flash-lite`, which answered. The check took over 180 s and only two responses were logged, so the first attempt most likely got no answer until the 180 s read timeout. A timeout is not a 503 and does not trigger the fallback by itself; on Node 1's 32K-token calls the read timeout is 900 s. Open for the team: make `gemini-3.5-flash-lite` the default `GEMINI_MODEL`, or treat timeouts on the main model like 503.
- Impact on other tracks: none.

## D-049 — `gemini-3.5-flash-lite` becomes the default `GEMINI_MODEL`
- Step: fix after D-048 · Date: 2026-10-26 · By: Aron via Claude Code (human decision)
- Plan said: `GEMINI_MODEL` defaults to `gemini-3.8-flash` for medium/high effort, with `gemini-3.5-flash-lite` as `GEMINI_FAST_MODEL` (D-046).
- Why: on the free tier `gemini-3.8-flash` returned 503 on every attempt and most likely left one request unanswered until the 180 s read timeout (D-048). A timeout does not trigger the fast-model fallback, and Node 1's 32K-token calls wait up to 900 s, so one stalled request could freeze an evaluation. `gemini-3.5-flash-lite` answered every request and produced a clean dossier and grade for Maya.
- We did: the default in `app/config.py`, `.env.example` and the plan (§0.2, §0.3, §1.5, §1.7.2, §3.5.1) is now `gemini-3.5-flash-lite`. `GEMINI_FAST_MODEL` is unchanged, so with the defaults both roles use one model, all of an evaluation's 10–14 requests count against that model's daily quota, and the 503 fallback has nothing to switch to. Setting `GEMINI_MODEL=gemini-3.8-flash` (or `gemini-3.6-flash`) in `.env` brings back the split and the fallback. The provider tests pin `gemini-3.8-flash` as the main model so the fallback stays covered.
- Impact on other tracks: none.

## D-050 — Run limits sized to the Gemini free tier
- Step: fix after D-049 · Date: 2026-10-26 · By: Aron via Claude Code (human decision)
- Found: AI Studio lists the project's free-tier limits as 15 requests/minute, 250K tokens/minute and 500 requests/day for `gemini-3.5-flash-lite`, and 5/minute and 20/day for `gemini-3.8-flash` and `gemini-3.6-flash`. The app's defaults (`max_runs_per_day=400`, `max_concurrent_runs=6`, §4.3) were sized for the paid Claude budget.
- We did: `.env.example` and plan §0.3 set `MAX_RUNS_PER_DAY=30` (an evaluation makes about 9 requests today and up to 13 after B17b, so 500 a day covers 38–55, less retries and team testing) and `MAX_CONCURRENT_RUNS=2` (one evaluation sends 9–13 requests in about a minute; extra 429s are retried after `Retry-After`). §1.5 records the limits. The code defaults stay as they are for Meterless and future paid use; deployments set the values in their env.
- Impact on other tracks: Track D's deployment should copy both values into the API host's env, ideally with a Gemini key from a separate free project used only by the deployed host.

## D-051 — B17b: provider-neutral tool loop
- Step: B17b · Date: 2026-10-26 · By: Aron via Claude Code
- Plan said: `llm.chat_with_tools(...)` runs one tool-calling round in a provider-neutral shape; the Claude loop becomes its `anthropic` branch (§1.7.2, roadmap B17b).
- We did: (1) `ZETARIS_SQL_TOOL` is a neutral `{name, description, parameters}`; the Claude branch adds `strict: true` and `input_schema`, the OpenAI branch wraps it as `{"type": "function", "function": ...}` without `strict`, which Gemini's compatibility layer and Nightshift may not accept (unverified). (2) Loop messages are neutral (`user`, `assistant` with a `ToolTurn`, `tool_results`) and each branch converts them; the assistant turn is replayed in its native shape, which keeps Claude's thinking blocks and Gemini's thought signatures. (3) On OpenAI providers there is no `is_error`, so failed results rely on their "Query rejected: …" text. (4) Malformed tool-call arguments become `{}`, which the SQL guard rejects, instead of crashing the loop. (5) `openai_compat._complete` is split so `_choice` (send, retries, effort and overload fallbacks) serves both `parse` and `chat_with_tools`. (6) The fake-mode guard in `test_graph.py` now also fails on any `openai_compat.http` use.
- Verified against real Gemini (free tier, 4 requests, Zetaris unreachable): `gemini-3.5-flash-lite` called the tool with valid SQL against the listed views, every call carried a thought signature that the next round replayed and Gemini accepted, the model tried a new query after each "Query rejected", and it ended with a plain-text summary after the fourth round (`MAX_QUERIES + 1`). Not verified: a real `[Zetaris Z#]` finding, which needs the Zetaris stack (not running on this machine).
- Impact on other tracks: none. Event names and payloads are unchanged.

## D-052 — B18 split; B18a ships the World Model engine with no build step
- Step: B18a · Date: 2026-10-26 · By: Aron via Claude Code (human decisions: the split, and cloning upstream to run its suite)
- Plan said: one step B18 for the TypeScript sidecar, the Python client, the docket integration and the node appends (§1.7.3).
- We did: (1) split into B18a (engine + HTTP wrapper + conformance) and B18b (client, appends, docket, compose), because the whole was about 800 lines. D10 now depends on B18b. (2) Our own engine in one file, not a copy of upstream's Apache-2.0 reference; it passes 8/8 against upstream `1742dec`, as the reference does. (3) No npm dependencies and no compile step: Node 24 runs the TypeScript directly, tests use `node --test`, and `tsconfig.json` (`erasableSyntaxOnly`) exists for editors. `tsc` was not run, since TypeScript is not installed and no new download was approved. (4) `relate` closes the open edge with the same `from` and `type` by default (what `bitemp-001` checks); `supersede: false` keeps both, for multi-valued relations such as citations. (5) The idempotency shape covers entities, observation hashes and edges, never the audit log or the clock. (6) The upstream clone lives at `C:\Users\heva2\meterless-upstream\repo`, outside this repo.
- Impact on other tracks: none yet. The sidecar is a new service on the API host in B18b (Track D's compose).
