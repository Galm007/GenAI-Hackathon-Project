# Analytics components (Track D)

Done by gridiii via Codex, 2026-10-24.

The plan's section 6.2 explicitly schedules the Track D charts against static
JSON while C builds the shared store. These components accept presentation props
compatible with the backend fields, so C02 can pass data without changing its
contract. They do not fetch data, own a store, or change the existing app routes.

Preview: run `pnpm dev --hostname 127.0.0.1 --port 3001` from `apps/web`, then
open `http://localhost:3001/dev/analytics`. Port 3000 is used by local Zetaris.
The preview exposes loading, simulation, and citation-highlight states.

Verification: `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm build`, and
`node --experimental-strip-types --test components/analytics/math.test.mjs`.

`ProbabilityGauge` accepts the baseline and an optional `simulation` with
`simulated`, `applied`, and `delta_pp`. A counterfactual-only preview has no supplied
interval or disposition: those are displayed as unavailable rather than inferred.
`Waterfall` accepts the shown probability and an optional `{kind, ref}` highlight.
It displays the exact supplied contributions and flags inconsistent totals.

The sample takes its estimate and counterfactual from the existing scripted
stream. The preview's academic contribution is the arithmetic residual between
the scripted pre-twin estimate and earlier contributions, resolving the script's
1.8-point waterfall discrepancy in this isolated fixture only. Simulation adds
the already supplied counterfactual delta. All values remain fictional.

C02 is still required for live store wiring; a working sample-data component
does not mean the live War Room is integrated. No API/model calls are made here.

`RadarCompare` accepts the plan's `radar` output fields. Missing or invalid axes
are explicitly omitted from the polygon and retained in its readable table;
zero is a valid score. The Personal spoke is dashed and marked as an assumed
reference, not a measured admitted-essay statistic. Fewer than three comparable
axes produce a text fallback. The sample's six-axis normalization follows section
4.7, using fictional reference values and two admitted sample profiles.

`TwinCards` accepts `twins`, optional `baseline` and `comparisons`, and the shared
highlight shape. Cards expand with keyboard or mouse; a `twin` highlight whose
`ref` matches the citation index scrolls to and pulses that card. The neighbor
count comes from the supplied baseline rather than a hard-coded 50. Missing
scores stay unknown. Source links require credential-free HTTPS; the fictional
samples deliberately have no original-post URLs. The preview has controls for
Twin 2 highlighting and missing testing data. Reduced-motion settings disable
chart, card-entry, expansion, and pulse animations.
