# Meterless evidence and remaining acceptance

Updated by gridiii via Codex, 2026-10-26. These are actual observations, not a
claim that a replay or a health check completes D10.

## Verified

- Nightshift M1-M4 installed through the official setup app on this Mac. The
  earlier `spctl` assessment was a historical installer check; no protection was
  disabled and no quarantine attribute was removed.
- NVIDIA was configured inside Nightshift. Its key is not in application source,
  coding-tool settings, the frontend or Vercel.
- `scripts.smoke_meterless` passed settings, authenticated discovery and an
  actual answer served by `nvidia/nemotron-3.5-lightning-30b-a3b`.
- Nightshift has genuine successful application extraction receipts and the
  smoke receipt. Its UI labels the captured receipts **unsigned**; do not claim
  a verified daemon signature.
- Aron's B18a/B18b implementation is integrated from main `5798dbb`. This Mac
  independently ran its seven Node tests, real-sidecar Python integration tests,
  and the unmodified upstream conformance runner: **8/8**. The committed upstream
  scorecard is `world-model-conformance.txt`; upstream revision is
  `1742dec56a66e58eef9dda2d2b865823758ca8cd`.
- The World Model Docker image builds and its container is healthy beside the
  API and Zetaris. A full real Gemini evaluation completed using it.

## Still open: B17c / D10

The real streamed advocate check returned an empty string; Nightshift's receipt
said **No route completed**. The app previously mislabeled an empty stream as a
successful non-degraded turn. D-055 fixes that with `LLMInvalidOutput`, taking the
existing visible fallback. No empty reply is evidence of a Nemotron committee.

Do not tick B17c or D10 until a real committee turn returns nonempty text through
Nightshift, its served Nemotron model is visible in request details, and the
short recording shows that successful feature with all credentials hidden.
Gemini Free Tier is configured for normal live evaluations; Claude stays off.

## Private evidence locations on gridiii's Mac

- `outputs/nightshift-smoke-receipt-2026-10-26.png` (outside the repository).
- `.local/readiness/maya-gemini-events.json`: private raw run capture; **do not
  commit or publish** because comparison profiles come from real students.
- `.local/readiness/maya-world-context.json`: private engine context, same rule.
- `.local/readiness/nemotron-committee-turn.json`: failed empty-turn diagnostic,
  not successful judging evidence.
- Public aggregate verification: `docs/live-verification-2026-10-26.json`.

Capture only the fictional applicant, aggregate results and provider metadata.
Individual retrieved profiles must not enter fixtures or a public video.
The user's private handoff contains the exact next check and current hosting
instructions. No credential is included in this public evidence record.
