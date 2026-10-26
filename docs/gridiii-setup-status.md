# gridiii: current setup and Track D status

Updated by gridiii via Codex, 2026-10-26. Main is integrated through `5798dbb`,
including Aron's B18a/B18b World Model implementation. Teammate work is retained.

## Verified on this Mac

- Shared AdCom Supabase access works: 265 universities and 947 applicant profiles.
  Backend credentials are in the ignored root `.env` with owner-only permissions.
- A dedicated `adcom_gridiii_reader` login inherits the existing `zetaris_reader`
  role. It has no superuser, database-creation or role-creation privileges. The
  existing team reader password was not changed.
- Track A's SQL files were applied to this Mac's Zetaris with the real pooler
  connection, official Scorecard institution CSV and IPEDS ADM2023 file. The
  local AdCom agent reads the UIUC view and gold table. Direct source-table and
  internal IPEDS-view reads are denied as intended.
- The API on the Zetaris network reports `db=true`, `zetaris=true`,
  `fake_llm=false`. The Nightshift provider check reported `meterless=true`
  when selected; with Gemini selected its status is explicitly `not_selected`. Discovery checks the configured model's
  presence; it does not pretend to prove a completed evaluation.
- Nightshift M1-M4 installed successfully through its official setup application.
  The earlier execution assessment remains a historical observation: no security
  protection was bypassed or changed. NVIDIA is saved inside Nightshift only.
- The authorized smoke test passed configuration, authenticated model discovery
  and a real reply served by `nvidia/nemotron-3.5-lightning-30b-a3b`. Nightshift's
  genuine receipt is captured privately; the UI labels it unsigned, which must
  remain disclosed when presenting that receipt.
- Local settings: `LLM_PROVIDER=gemini`, `ALLOW_PAID_PROVIDERS=false`,
  `MAX_RUNS_PER_DAY=30`, `MAX_CONCURRENT_RUNS=2`. A dedicated AdCom AI Studio
  project was created and visibly verified Free Tier. The Gemini key lives only
  in this Mac's private backend `.env`; billing was not enabled.
- The shared-database fake graph completed 244 contiguous events and what-if.
  D-056 fixes the nonsemantic demo embedding that previously yielded NaN cosine
  distances. This result is explicitly separate from real retrieval/provider proof.
- With the latest upstream integration and local health additions: 422 API tests
  and ruff pass. Aron's World Model passes all seven Node tests and the unmodified
  upstream conformance runner passes 8/8 independently on this Mac.
- Web checks earlier today: 48 tests, lint, TypeScript and production build pass.
  A16's real backtest figures are available: app Brier 0.232, official-rate baseline
  0.303, Reddit-rate baseline 0.216; weak within-school ranking and subgroup gaps
  are stated in the pitch.

## Acceptance still being checked

| Area | Current status |
|---|---|
| Live Maya evaluation | Completed through Gemini Free Tier: 97 contiguous events, four non-degraded committee turns, final report and working what-if. The earlier slow Nightshift full evaluation was stopped. Raw captures stay private because retrieved twins are real profiles. |
| D08 deployment | The real API is reachable through a temporary Cloudflare tunnel. Vercel's existing adcom project is being deployed with backend origin only, no model/database secrets. A successful hosted run and physical-phone check remain required. |
| D09 pitch | Published data/backtest figures are filled. Completed: 56.66% baseline; Tier 2 activity +1.98 pp; SAT +50 gives +0.36 pp. No eligible empirical major pivot was returned. |
| D10 judging evidence | Local Runtime setup and genuine 8/8 conformance are verified. The actual streamed committee request returned no text and a “No route completed” receipt. Blank streams now take the existing degraded fallback in the PR. B17c/D10 remain open; successful smoke/extraction requests are not substituted. |

Private credential handoff is in `.local/team-handoff/` (ignored, owner-only).
Share it privately only if needed; do not post it to GitHub or a group chat.
The public PR documents configuration names and checks, never keys.

Done by gridiii via Codex. Frozen browser/Pydantic/event contracts are unchanged.
