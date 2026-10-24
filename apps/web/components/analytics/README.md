# Track D analytics

Done by gridiii via Codex, 2026-10-24.

`AnalyticsPanel` reads the team's existing shared store. It integrates the gauge,
waterfall, radar, expandable comparable applicants, per-run what-if drafts,
ranked pivots and essay examples. Shared event names, schemas, types and store
contracts are unchanged. One simulation controller is mounted in WarRoom so its
responsive copies cannot issue duplicate requests.

The gauge displays the supplied model value and interval; hypothetical results
are labeled simulated. Floating SVG waterfall bars retain signed contributions,
running totals and zero-crossings on the same scale. Inconsistent supplied totals
are flagged. Readable evidence tables accompany the charts. Unknown scores stay
unknown. The Personal radar reference is dashed and assumed; it is not an
observed admitted-essay median.

Pivots bind to computed counterfactual IDs, never numbers extracted from prose.
Try it resets the prior draft before applying the selected scenario. Requests
debounce, abort and ignore late responses. Reset restores the baseline. Request
failures and warnings remain visible. Tier-promotion approximations are marked
with ≈, as specified in the plan.

Run the API on port 8000 in explicit FAKE_LLM mode and the web app on port 3001;
see `docs/deployment.md`. `/room/demo/maya-uiuc` plays the full fictional replay
without provider keys. `/dev/analytics` isolates loading, simulation, missing-data
and highlight states, using the same Python-generated fixtures as the replay.
No authored fixture is represented as a real model recording or corpus evidence.

Verification: `pnpm test`, `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm build`.
API tests check exact pivot reproduction and waterfall conservation. Browser checks
cover pivot/reset, replay restart, keyboard expansion, citations, desktop/drawer
layouts and the 390px phone layout. Reduced-motion preferences disable chart and
card animations.
