# gridiii: current setup and Track D status

Updated by gridiii via Codex, 2026-10-25 after Aron's Track B handoff. Synced
through `e4db91f`: B01–B13 are implemented, and Track A has checked A07–A13,
including live A12 views and agent permissions on its stack. Those team results
do not mean the same credentials or semantic layer exist on every developer Mac.

## Verified today on this Mac

- Locked Python dependencies and ruff pass; **298 API tests** pass.
- The fixture/encoding suite also passes with an ASCII locale and Python UTF-8
  mode disabled: **6 tests**, including a byte-identical fixture rebuild.
- **43 web tests**, lint, TypeScript and production build pass.
- Aron's D-1 fixture blocker is fixed: all fixture generator/test reads and
  generator writes explicitly use UTF-8. D-3 is fixed too: the fake chair ends
  with the computed recommendation. See D-033.
- Docker Desktop was started and Zetaris passed **all 9 vendor checks**,
  including authenticated SQL through the platform.
- The production web proxy serves the updated **101-event fictional replay** to
  completion. Its alternative-major what-if still calculates **42.0%** from the
  same fictional inputs. This is not a live-provider recording.
- The root `.env` imports successfully and is configured for the authored replay
  (`FAKE_LLM=true`, `ZETARIS_ENABLED=false`, `DEMO_MODE=true`). The web's local
  environment points its same-origin proxy at port 8000. Both files are ignored
  and have mode 600; existing private values were preserved.
- No paid model request, local model load, database mutation or volume reset was
  performed. The unrelated local database was not used for AdCom.

## What still needs team input

| Area | Current state / next owner |
|---|---|
| Shared AdCom database | gridiii chose the shared project. Its URL and backend service-role key remain placeholders locally. No concrete project URL or backend key is committed. The Supabase CLI is not signed in. Jmar/shared project settings must supply the values privately. |
| Zetaris on this Mac | The standalone platform works; the local agent password, pooler/reader settings and local ADCOM semantic layer are not configured. Jmar's A12 checks apply to his stack. The API host needs its own matching datasource/views and least-privilege user. |
| B14 offline graph | Track A's flag/transport fallbacks and UIUC school/twin data (Aron A-1/A-2), plus Track B's CLI/direct-client fake mode, remain required. Fake model calls alone do not replace the database. |
| Real fictional-persona recording | B13 now persists event logs, and the D07 recorder exists. A real run still needs database data, provider setup and human approval for provider usage. No live recording was fabricated. |
| D08 deployment | Frontend/proxy configuration is ready. B16, a linked Vercel project, reachable API host and live phone acceptance are still pending. |
| D09 pitch | Prototype script/data disclosure exist. A15/A16 corpus, calibration and backtest figures remain missing; the manifest keeps unknown values null. |
| D10 judging evidence | S03 Nightshift setup, B17/B18 integration, a real served Nemotron request and genuine World Model scorecard are still pending. |
| Password rotation | Deferred at gridiii's earlier request. Keep private configuration coordinated when rotating it. |

## Next steps without overlapping teammates

Aron's D-1 and D-3 items are resolved by Track D. Leave A-1/A-2 to Track A and
B14's fake-mode wiring to Track B. Once Jmar supplies the shared connection,
configure this Mac without copying secrets into Git or frontend variables.
Then recheck the demo data and chosen host before capturing a real run.

D08–D10 remain unchecked until their actual hosted/data/provider acceptance
checks pass. No event names, Python schemas or TypeScript contracts changed.

See [Track D verification](track-d-verification.md), [deployment handoff](deployment.md),
[prototype pitch](pitch.md) and [Meterless evidence handoff](meterless-evidence/README.md).
