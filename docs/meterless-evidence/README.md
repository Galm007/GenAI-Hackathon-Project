# Meterless judging evidence: pending

Updated by gridiii via Codex, 2026-10-26. No real Nightshift request or World Model
conformance result has been captured. A fictional UI replay cannot complete D10.

## Setup prepared on gridiii's Mac — 2026-10-26

The official [Mac M1+ download](https://meterless.ai/Nightshift/M1%2B/) was
downloaded for this M4 Pro Mac. The disk image was mounted read-only, its setup
application copied to `/Users/gridiii/Applications/Nightshift Setup.app`, and the
image detached. This is the installer bootstrap, **not an installed Runtime**.

| Check | Observed result |
|---|---|
| Download size | 17,778,594 bytes |
| SHA-256 | `f387ea2668ff8f767f3e95a5e5463c975e738ab9836768b09ab21ca09e336fa8` |
| Setup bundle | `ai.meterless.installer.mac-m1`, version 1.0.0, arm64 |
| macOS execution assessment | Rejected by `spctl --assess --type execute` |
| Code signature | Ad-hoc; no TeamIdentifier |
| Installer launch / Runtime installation | Not performed |

The hash identifies this download; it is not proof of publisher identity.
gridiii must review the vendor's signing/install guidance, or obtain an accepted
build, before continuing. No Gatekeeper setting or quarantine attribute was
changed. No NVIDIA connection, lane, Runtime token or model request exists here
yet. Continue with [the setup guide](../meterless-setup.md) after installation is
resolved, then capture genuine evidence below.

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
| Nightshift smoke test | Not run: installer prepared, macOS assessment rejected; Runtime and token unavailable |
| Request through the application | Pending B17 |
| Served Nemotron model | Not verified |
| World Model conformance | Pending B18 |
| Recording | Not captured |
| D10 acceptance | Open |

This preparation contains no credential or claim of partner compliance. Replace
the pending results only with evidence from the real configured services.
