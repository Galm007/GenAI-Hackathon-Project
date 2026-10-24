# Meterless judging evidence: pending

Prepared by gridiii via Codex, 2026-10-24. No real Nightshift request or World Model
conformance result has been captured. A fictional UI replay cannot complete D10.

## Required inputs

- S03: Nightshift installed and running, NVIDIA connected inside its Providers
  tab, and a Nemotron-backed lane pinned. Keep the NVIDIA key there.
- B17: the application routes a real committee request through Nightshift.
- B18: the actual World Model engine passes its upstream conformance suite, with
  its scorecard saved as `world-model-conformance.txt` in this directory.
- D07: a tested replay fallback for the fictional demo persona.

## Capture the proof

1. Run `uv run python -m scripts.smoke_meterless` and retain its three PASS lines.
   This makes a real provider request; get the human's approval for provider usage.
2. Confirm the responding model in Nightshift's request details is the selected
   Nemotron lane. A routing label such as `meterless/auto` alone is not proof.
3. Record a short walkthrough that shows the app, the provider connection and that
   request's served-model details. Hide keys/tokens, terminal environment values,
   private account details and unrelated applications before capture.
4. Run the upstream World Model conformance suite against the actual sidecar.
   Save its genuine output; do not create a substitute scorecard from a mock.
5. Add the video location, request time, served model, source revision and genuine
   scorecard path below. Review the capture once before sharing.

## Evidence record

| Item | Result |
|---|---|
| Nightshift smoke test | Not run here: Runtime token and installation unavailable |
| Request through the application | Pending B17 |
| Served Nemotron model | Not verified |
| World Model conformance | Pending B18 |
| Recording | Not captured |
| D10 acceptance | Open |

This preparation contains no credential or claim of partner compliance. Replace
the pending results only with evidence from the real configured services.
