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

### D-021 production breakpoint follow-up
- Production browser testing at exactly 1440px exposed overlapping desktop/laptop layout variants. The laptop grid now applies only within its explicit 1024–1439px range. A rebuilt production page verifies one visible dossier, one analytics sidebar and no horizontal body overflow at 1440px. Lint, types and production build pass after the correction.
- The final narrow-sidebar radar review exposed a clipped Personal label and crowded raw values. Long axis labels now wrap onto two lines and numeric columns have fixed, right-aligned widths. The rebuilt production chart was visually checked with the complete assumed label visible and separate comparison columns.
