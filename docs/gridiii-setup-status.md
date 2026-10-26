# gridiii: current setup and Track D status

Updated by gridiii via Codex, 2026-10-26. Synced through `b6b3d37` before this
Track D update: Track A A01–A15 and Track B B01–B13/B15/B16 are checked, with
live qualifications recorded in the roadmap. Jmar's A15 report has 947 profiles;
10K is optional A18. Team data does not automatically grant this Mac access.

## Verified today on this Mac

- Locked Python dependencies and ruff pass; **340 API tests** pass.
- **43 web tests**, lint, TypeScript and production build pass.
- The data disclosure and pitch use A15's reported **947 profiles, 265
  universities, five CDS schools**, per-school coverage and scoped 3.24× median
  odds inflation. The source link is dated and immutable; Brier scores stay null.
- The production panel fits a **390px** phone viewport without horizontal panel
  overflow. Escape closes it and restores focus to its trigger.
- Alternate saved recordings now restart themselves with the button or Shift+R,
  retaining projector mode. The temporary fictional test recording was removed.
- Aron's arm64 API image was built and started on the Zetaris Compose network.
  It binds only **127.0.0.1:8000**. In-container access to the Zetaris UI returns
  HTTP 200; the 101-event replay and deterministic what-if work.
- Zetaris passed **all 9 vendor checks** after API bring-up. This admin/platform
  check does not verify an AdCom agent's curated-view access.
- The container contains no private root/API environment file. The ignored local
  configuration remains for the authored replay: `FAKE_LLM=true`,
  `ZETARIS_ENABLED=false`, `DEMO_MODE=true`. Existing private values are preserved.
- No paid model request, local model load, database mutation or volume reset was
  performed. The unrelated local database was not used for AdCom.

## What still needs input or real acceptance

| Area | Current state / next owner |
|---|---|
| Shared AdCom database | gridiii chose the shared project. Its URL/backend key remain placeholders locally. The Supabase web account is signed in, but the last check showed only gridiii's organization and five unrelated projects. Jmar must supply an invitation or the connection privately; GitHub does not contain the credentials. |
| Zetaris on this Mac | The standalone platform works. Local agent and pooler/reader credentials remain placeholders, and the AdCom semantic layer is not verified locally. Jmar's A12/A14 checks apply to his stack; the chosen API host needs matching datasource/views and a least-privilege user. |
| Actual project health | The API responds with `ok=false, db=false, zetaris=false` in the current fake/replay configuration. HTTP reachability to the UI is not proof of working project SQL/data access. |
| B14 offline graph | A15 now supplies UIUC and the other demo schools/twins on the team stack. Access is still needed here. Track B's CLI/direct-client fake-mode work and Track A's flag/transport fallbacks remain separate handoff items. |
| Real fictional-persona recording | B13 persists event logs and D07's recorder exists. A real run still needs database data, provider setup and human approval for provider usage. The authored UI replay is not substituted as a real recording. |
| D08 deployment | Local container and proxy are verified. A Vercel project/account connection, reachable public API host, green project health and a live phone run remain open. The Vercel dashboard was at sign-in when checked. |
| D09 pitch | Real A15 figures are integrated. A16 backtest/bias results and final recorded-run figures remain missing; no accuracy number was invented. |
| D10 judging evidence | The official Mac M1+ setup app is prepared in `~/Applications`, but macOS rejected its execution assessment (ad-hoc signature). It was not launched; vendor/install review is needed. S03 Runtime/NVIDIA setup, B17/B18 integration, a real served Nemotron request and a genuine World Model scorecard remain pending. |
| Password rotation | Deferred at gridiii's earlier request. Keep private configuration coordinated when rotating it. |

## Next steps without overlapping teammates

The available data-panel/pitch update, named-replay correction and local API
bring-up are complete. Keep A16 and the data-service fixes with Track A, and
B14/B17/B18 with Track B. Once project access is available, configure this Mac's
private values, apply the host-specific Zetaris setup, and verify real health
before public deployment or recording a provider-backed run.

D08–D10 remain unchecked until their hosted/data/provider acceptance checks pass.
Frozen event names, Python schemas and TypeScript contracts are unchanged.

See [Track D verification](track-d-verification.md), [deployment handoff](deployment.md),
[prototype pitch](pitch.md) and [Meterless evidence handoff](meterless-evidence/README.md).
