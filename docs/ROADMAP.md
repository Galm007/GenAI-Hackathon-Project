# ROADMAP: the step queue

**How to use this file:** read `AGENTS.md` §3 first. Each step below is **one commit**. Take the first unchecked step in your track whose dependencies are all checked. When it's done, flip `[ ]` to `[x]` and append ` — done by <human> via <tool>, YYYY-MM-DD` in the same commit.

- **Plan refs** are `MASTER_PLAN.md` sections. Find one with `grep -n "^### 3.7" MASTER_PLAN.md`.
- **Deps** must be checked before you start. Each blocked step lists the fallback that lets you start anyway.
- **Done when** describes the verification you run and report. Report anything you couldn't run as not run.

Milestones follow plan §6.2: **H6** fake SSE drives the UI · **H12** real probability via CLI · **H18** integration on the deployed stack · **H24** recorded replay · **H28** feature freeze · **H33** code freeze.

---

## S: Shared foundations (do these first)

- [x] **S01 — Python service scaffold** · Plan §0.3–0.5, §0.4 · Deps: none · Owner: Track B — done by Jmar L. Pineda via Claude Code, 2026-10-23
  Creates `services/api/` with `pyproject.toml` (§0.5), `uv.lock`, the `app/`, `etl/`, `scripts/` and `tests/` packages (empty `__init__.py`), ruff and pytest config, a root `.env.example` with every §0.3 key as a placeholder, and a README quickstart.
  *Done when:* `uv sync && uv run ruff check . && uv run pytest -q` all succeed (zero tests is fine).

- [x] **S02 — Shared modules used by several tracks** · Plan §2.9.7 (`profile_text.py`, `embeddings.py`), §3.4.1 (`prompts/rubrics.py`) · Deps: S01 · Owner: Track A — done by Jmar L. Pineda via Claude Code, 2026-10-23
  Creates `app/profile_text.py`, `app/embeddings.py` and `app/agents/prompts/rubrics.py` exactly as specified (the ETL and Node 1 must share them byte for byte).
  *Done when:* a unit test builds the profile text for a fixture and its output is deterministic; `embed_texts` is mocked in the test.

- [ ] **S03 — Meterless Nightshift setup + smoke test** · Plan §1.7.1, §1.7.4 · Deps: S01 · Owner: whoever runs the demo machine
  `docs/meterless-setup.md` and `scripts/smoke_meterless.py` exist (tests pass). A human must install Nightshift (Windows, Mac or DGX; no Linux edition), add the NVIDIA key in its Providers tab, configure a Nemotron lane and copy the Console URL and token into `.env`.
  *Done when:* `uv run python -m scripts.smoke_meterless` prints three PASS lines and Nightshift's run details show a Nemotron model answered.

## A: Data, RAG & Zetaris

- [x] **A01 — Migrations 0001–0003 (types, universities, twins)** · §2.2–2.4 · Deps: none — done by galm via Claude Code, 2026-10-23
  *Done when:* the files apply cleanly to a fresh database; `\d applicant_twins` shows the HNSW, GIN and generated `applied_schools` column.
- [x] **A02 — Migrations 0004–0005 (stats views, runtime tables)** · §2.5–2.6 · Deps: A01 — done by Jmar L. Pineda via Claude Code, 2026-10-23
  *Done when:* they apply cleanly and `select refresh_twin_stats()` runs on an empty DB.
- [x] **A03 — Migrations 0006–0008 (hybrid-search RPCs, RLS/cron, radar RPC)** · §2.7, §2.8, §4.7 (SQL) · Deps: A02 — done by Jmar L. Pineda via Claude Code, 2026-10-23
  *Done when:* with 3 hand-inserted twins, `match_applicant_twins` returns ranked rows with an outcome; anon can't select `applicant_twins`.
- [x] **A04 — Migration 0009 (Zetaris export schema)** · §2.10.3 · Deps: A03 — done by Jmar L. Pineda via Claude Code, 2026-10-23
  *Done when:* `refresh_twin_stats()` fills the three `zetaris_export` tables; the `zetaris_reader` role can read only that schema.
- [x] **A05 — ETL foundations + Reddit archive scraper (Arctic Shift)** · §2.9.1–2.9.2 · Deps: S01 — done by Jmar L. Pineda via Claude Code, 2026-10-23
  *Done when:* one page scraped from each subreddit lands in `data/raw/*.jsonl` with a checkpoint file; there are ≥4 s between requests; no author field is stored.
- [x] **A06 — School seed data + resolver** · §2.9.5, §2.9.8 (seed CSV) · Deps: S01 — done by Jmar L. Pineda via Claude Code, 2026-10-23
  Writes `data/schools_seed.csv` (verify every unitid), `data/school_aliases.yaml` and `etl/school_resolver.py`.
  *Done when:* resolver tests pass: "UMich" → `umich`, "CMU SCS" → `cmu`, "UW" → `None` (ambiguous), unknown names land in the unresolved counter.
- [ ] **A07 — Reddit structured extraction** · §2.9.3, §2.9.4, §2.9.6 · Deps: A05, A06, S02, B02, B05 (B01 no longer needed: extraction uses local Gemma, DECISIONS D-007)
  *Done when:* `--limit 20` on local `gemma4:e2b` with the short schema (cap 3,000 posts, Zetaris auto-paused by `etl/resources.py::zetaris_paused`, already built) (free, but it loads the GPU and RAM: tell your human first so they can close their browser) produces rows in `data/processed/twins.jsonl` and `rejects.jsonl` with reasons; quality gates are unit-tested on two synthetic records.
- [ ] **A08 — Embeddings + twin loader** · §2.9.7 (`load_twins.py`) · Deps: A07, A03
  *Done when:* the 20 smoke rows are upserted with 768-d vectors, and `match_applicant_twins` returns them for a school they applied to.
- [ ] **A09 — College Scorecard API loader** · §2.9.8 · Deps: A01, A06
  *Done when:* ≥200 schools and their aliases are in Supabase; `resolve_school('michigan')` returns `umich`.
- [ ] **A10 — CDS PDF loader (5 demo schools)** · §2.9.9 · Deps: A09 (B01 no longer needed: local Gemma, D-010; swap the local `C7Level` for `app.schemas.common.C7Level` once B02 lands). Code and tests exist; needs real `data/cds_sources.yaml` URLs and a model run (tell your human first).
  *Done when:* the 5 demo schools have `c7_weights` populated; a human has spot-checked C7 against the PDFs (note it in the commit body); `data/cds_sources.yaml` has real URLs only.
- [ ] **A11 — Stats refresh, major overrides, `run_etl` CLI** · §2.9.10 · Deps: A02, A08
  *Done when:* `python -m etl.run_etl refresh-stats` updates `major_competitiveness`; the data-quality SQL from §2.9.10 runs.
- [ ] **A12 — Zetaris bring-up + Lightning SQL files** · §2.10.2, §2.10.4 · Deps: A04 — files committed, DDL not applied yet (see commit)
  Commits `zetaris/sql/01_sources.sql` through `04_security.sql` and `docs/zetaris-setup.md` (steps only, no secrets). Resolve every "(verify at Hour 1)" marker against the running stack and correct the plan text.
  *Done when:* `./verify.sh` passes; `SELECT * FROM ADCOM.v_school_profile WHERE slug='uiuc'` returns a row in the Zetaris SQL editor; `adcom_agent` is denied on `ADCOM_PG.*`.
- [ ] **A13 — Zetaris client + repository** · §2.10.5 (incl. config additions) · Deps: B01, B07
  `app/zetaris.py`, `app/zetaris_repo.py`, and `tests/test_zetaris_guard.py` (cases from §3.10).
  *Done when:* the guard tests pass; `zetaris.query("SELECT 7 AS seven")` works against local Zetaris; with `ZETARIS_ENABLED=false`, `school_profile` falls back to Supabase.
- [ ] **A14 — `zetaris_setup.py` + CLI stages** · §2.10.6 · Deps: A11, A12, A13
  *Done when:* `run_etl zetaris-setup` is idempotent (a second run logs "exists"); `run_etl zetaris-refresh` rewrites the gold table.
- [ ] **A15 — Full data run → `docs/data-report.md`** · §2.9.10–2.9.11, §7.5 · Deps: A08–A14 · **needs your human's spend approval**
  *Done when:* ≥10K twins are loaded, the stats and Zetaris gold are refreshed, and the report has corpus size, demo-school coverage (≥80 each), calibration and tier distribution. Updated aliases are committed.
- [ ] **A16 — Backtest + bias audit** · §6.2 (H16–24), §7.3 Q1 · Deps: A15, B06
  `scripts/backtest.py`: hold out the latest cycle and compute Brier score and AUC versus a base-rate baseline, a reliability curve, and calibration by income bracket and first-gen status.
  *Done when:* results are appended to `docs/data-report.md`, honestly, even if weak.
- [ ] **A17 — (stretch) Coefficient fitting** · §3.9.3 · Deps: A15
  *Done when:* fitted values are logged; adopt them only if they pass the sanity bounds, and record the decision in `DECISIONS.md`.

## B: Agents & API

- [x] **B01 — Config, LLM wrapper, stream events** · §3.5.1–3.5.3 (+ settings from §4.3, §2.10.5) · Deps: S01 — done by Aron via Claude Code, 2026-10-23
  *Done when:* tests with a mocked `AsyncAnthropic` cover `parse` refusal → `LLMRefusal`, `max_tokens` → `LLMTruncated`, and fallback-block handling in `stream_text`; `emit()` is a no-op outside a graph.
- [x] **B02 — Pydantic schemas (CONTRACT)** · §3.3 · Deps: S01 — done by Aron via Claude Code, 2026-10-23
  *Done when:* every model imports; `model_json_schema()` works for every LLM output model; no LLM output model uses `dict[str, X]`.
- [x] **B03 — API skeleton + RunManager + scripted fake SSE** · §4.1–4.5, §6.3 · Deps: B02 — done by Aron via Claude Code, 2026-10-23
  Real `runs.py`/`sse_frames` and `/api/dev/fake-stream` replaying `data/fixtures/fake_stream.json` (a hand-written, minimal version is fine; D06 replaces it). `/api/evaluate` may drive the scripted stream until B13.
  *Done when:* `curl -N` on the fake stream shows `id:`/`event:` frames, and reconnecting with `Last-Event-ID` resumes without duplicates. **This unblocks Tracks C and D (target H4).**
- [x] **B04 — System prompts** · §3.4.2–3.4.6 · Deps: B02, S02 — done by Aron via Claude Code, 2026-10-24
  *Done when:* the prompt modules import; a test asserts every citation form in `COMMITTEE_SYSTEM` matches `CITATION_RE`.
- [x] **B05 — Scoring: metrics + school rubric** · §3.6.1–3.6.2 · Deps: B02 — done by Aron via Claude Code, 2026-10-24
  *Done when:* tests cover GPA normalization, the tier→EC anchor, every grade guardrail (§3.10 "Grade guardrails") and C7 → pillar weights.
- [ ] **B06 — Probability, counterfactuals, what-if** · §3.6.3–3.6.4, §4.6 · Deps: B05
  *Done when:* §3.10 tests pass (monotonicity, waterfall within 0.5 pp, `cf.overrides` reproducing `p_new` exactly); `db.major_arbitrage` is mocked.
- [ ] **B07 — Supabase helpers + web research** · §3.5.4–3.5.5, §4.3 (`db.py` additions), §4.4 (school cache) · Deps: B01
  *Done when:* functions are unit-tested with a mocked client; with A03 available, `match_twins` hits the real RPC.
- [ ] **B08 — Node 1: dossier parser + rubric grader** · §3.7.1 · Deps: B04, B05, S02
  *Done when:* guardrail and redaction tests pass; a real run on Maya's dossier (D01) produces a sensible `DossierGrade`, or the report notes "not run" without keys.
- [ ] **B09 — Node 2: institutional + Zetaris SQL tool** · §3.7.2, §2.10.7 · Deps: B04, B05, B07, A13 (fallback until then: `ZETARIS_ENABLED=false`)
  *Done when:* the tool loop is tested with a mocked client (budget of 3, `is_error` on rejected SQL); a real run emits `zetaris_queries`.
- [ ] **B10 — Node 3: twins + radar** · §3.7.3, §4.7 (`radar.py` + node addition) · Deps: B05, B06, B07, A13 (fallback: Supabase)
  *Done when:* `select_contrastive` and `compute_baseline` are unit-tested; a real run returns 5 cards with ≥1 accepted and ≥1 rejected.
- [ ] **B11 — Committee docket + debate nodes** · §3.8.1–3.8.3 · Deps: B04, B06
  *Done when:* citation-validator tests pass (incl. `sql:` refs); the fallback turn path is tested; docket bytes are identical across turns.
- [ ] **B12 — Node 5: delta engine** · §3.8.4 · Deps: B06, B11
  *Done when:* `bind_report` tests pass (unknown counterfactual IDs nulled, percentages scrubbed, disposition taken from the chair).
- [ ] **B13 — Graph assembly + CLI + real `/api/evaluate`** · §3.9.1–3.9.2, §4.3–4.4 · Deps: B03, B08–B12
  *Done when:* `get_graph().draw_mermaid()` matches §3.1; the CLI completes for Maya at UIUC; the browser stream from `/api/evaluate` comes from the real graph. **H12 milestone.**
- [ ] **B14 — Demo replay + `FAKE_LLM` mode** · §4.8–4.9 · Deps: B13
  *Done when:* `FAKE_LLM=1 ZETARIS_ENABLED=false` runs the whole graph offline; `/api/demo/<name>/stream` replays a recording; `/api/what-if` works on `demo-<name>`.
- [ ] **B15 — Hardening** · §4.3 (health, prewarm), §4.4 (rate limits, watchdog), §7.4 (dossier cache + replaying Node 1 outputs for cached runs) · Deps: B13
  *Done when:* a second identical upload skips Node 1 but still fills the dossier panel; `/api/health` reports DB and Zetaris; the 429 paths are tested.
- [ ] **B16 — API container + co-located compose** · §4.10 · Deps: B13
  *Done when:* `docker compose -f zetaris-platform/docker-compose.yml -f docker-compose.adcom.yml up -d adcom-api` serves `/api/health` with `zetaris: true`.
- [ ] **B17 — Meterless provider in the LLM wrapper** · §1.7.2, §3.5.2 · Deps: B01, S03
  Adds `app/meterless.py` and the `LLM_PROVIDER` switch (default `meterless`, `anthropic` stays selectable); `/api/health` reports `"meterless"`.
  *Done when:* tests with a mocked Runtime cover chat, structured output (and its retry), `length` → `LLMTruncated`, refusal → `LLMRefusal`, and auth errors; a real committee turn answers through Nightshift (needs S03).
- [ ] **B18 — World Model engine sidecar + committee integration** · §1.7.3, §3.8.1 · Deps: B11, B17
  `services/world-model/` (TypeScript, upstream interface), `app/world_model.py`, and `agents/docket.py` reading the engine's context builder; Nodes 1–3 and the debate append observations.
  *Done when:* the upstream conformance suite is green (scorecard saved to `docs/meterless-evidence/world-model-conformance.txt`), an integration test shows Nodes 2 and 3 appending concurrently without loss, and the sidecar being down degrades to the in-state docket.

## C: War Room UI

- [x] **C01 — Next.js scaffold + design tokens** · §5.1–5.3 · Deps: none — done by egli3 via Gemini CLI, 2026-10-24
  *Done when:* `pnpm build` passes; the tokens, the 4 fonts and the shadcn components from §5.3 are installed; routes exist as stubs.
- [ ] **C02 — Types, API client, store, stream (CONTRACT)** · §5.4 · Deps: C01, B02
  *Done when:* `tsc --noEmit` passes; reducer unit tests cover idempotent replay (`seq ≤ lastSeq` ignored) and token batching.
- [ ] **C03 — War Room shell, top bar, pipeline stepper, tool ticker** · §5.8, §5.2, §5.5.3 (ticker notes) · Deps: C02, B03
  *Done when:* `/room/<id>` driven by the fake SSE shows the 3-column layout, live stepper states and tool chips. **H6 milestone (with C04/C05 skeletons).**
- [ ] **C04 — Committee room** · §5.5 · Deps: C03
  *Done when:* streaming bubbles render citations without flashing raw `[[…`; the stamp lands; cross-panel highlight fires on chip hover; the Zetaris chip shows SQL.
- [ ] **C05 — Dossier panel** · §5.7 · Deps: C03
  *Done when:* the metrics strip, Harvard scorecard flip-in, tier tags and reader note render from fake-SSE data.
- [ ] **C06 — Intake wizard** · §5.8, §5.7.2 (dropzone) · Deps: C02, B03
  *Done when:* the 4-step wizard posts multipart to `/api/evaluate` and routes to the room; the 413/415/429 errors show toasts.
- [ ] **C07 — School tabs, child runs, degraded states, data-fabric drawer** · §5.8, §5.9 · Deps: C04, B13
  *Done when:* switching tabs starts a child run (Node 1 skipped); degraded nodes show amber rings; the drawer lists Zetaris queries.
- [ ] **C08 — Responsive, projector mode, accessibility, performance** · §5.2, §5.10 · Deps: C04–C07
  *Done when:* the tabs layout works below 1440 px; `?projector=1` works; reduced motion is honored; Lighthouse accessibility ≥ 90 on the room page.

## D: Viz, Demo & Integration

- [ ] **D01 — Fictional demo personas** · §6.2 (H1–2), §7 · Deps: none
  Writes `data/demo_dossiers/{maya,backup1,backup2}/` (transcript PDF, `activities.txt`, `essay.txt`, `intake.json`). All of it must be fictional.
  *Done when:* each persona has every file, and Maya is a CS applicant to UIUC.
- [ ] **D02 — Probability gauge + waterfall** · §5.6.1–5.6.2 · Deps: C02
  *Done when:* both render from fixture data, animate, and show the what-if "simulated" state.
- [ ] **D03 — Radar + twin cards** · §5.6.3–5.6.4 · Deps: C02
  *Done when:* the assumed Personal axis is dashed and labeled; twin cards expand and pulse on a `twin:` highlight.
- [ ] **D04 — What-if panel** · §5.6.5 · Deps: C02, B03, B06
  *Done when:* sliders debounce and abort stale requests against `/api/what-if`; warnings render; "Reset" restores the baseline.
- [ ] **D05 — Pivots, essay edits, arbitrage hero, `AnalyticsPanel`** · §5.6.6 · Deps: D02–D04
  *Done when:* "Try it" maps a counterfactual into the what-if draft and the gauge moves.
- [ ] **D06 — Realistic fixtures** · §4.9, §6.3 · Deps: B08 (fallback: hand-written)
  Real per-node fixtures in `data/fixtures/` + a realistic `fake_stream.json` recorded from a real run.
  *Done when:* the UI runs end to end on `FAKE_LLM=1` with no keys.
- [ ] **D07 — Demo route, `Shift+R`, recorded replays** · §4.8, §5.3 · Deps: B14, C04
  *Done when:* `/room/demo/maya-uiuc` plays like live; `Shift+R` swaps a live room to its replay.
- [ ] **D08 — Deploy** · §4.10 · Deps: B16, C06
  *Done when:* the web app is on Vercel, the API is co-located with Zetaris (VM or laptop + tunnel), and a live run works from a phone. **H18 milestone with X01.**
- [ ] **D09 — Pitch assets** · §5.9 ("About the data"), §7.5 · Deps: A15, A16
  *Done when:* the About-the-data modal shows real numbers, and `docs/pitch.md` has every §7.5 placeholder filled from real data (never invented).
- [ ] **D10 — Meterless judging evidence** · §1.7, §7.4 · Deps: B17, B18, D07
  *Done when:* a short recorded demo shows the app, its Meterless provider connection, and one real request through Nightshift answered by a Nemotron lane (all keys and tokens hidden), plus the World Model conformance scorecard.

## X: Integration & release

- [ ] **X01 — Integration gate (H18)** · §3.10, §6.2 · Deps: B13, C07, D05, D08
  Runs every row of the §3.10 checklist on the deployed stack and commits the results to `docs/integration-report.md`.
- [ ] **X02 — Freeze & release (H32–33)** · §6.2, §7.4 · Deps: everything not marked stretch
  Final demo replays re-recorded on production, the backup video path noted, the pre-demo checklist ticked in `docs/pitch.md`. The human tags `v1.0`.
