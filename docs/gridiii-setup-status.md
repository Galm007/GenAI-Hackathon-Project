# gridiii: current setup and Track D status

Updated by gridiii via Codex, 2026-10-24. This supersedes the earlier pre-integration
audit on the same date. Track B's B06–B08 and Track C's C02–C08 have since landed.

The local development tools, standalone Zetaris platform and complete fictional
UI replay work. The full live AdCom stack and release evidence are still pending.

## Verified

- Node 24.12.0, pnpm 11.25.0, uv 0.13.5 and API Python 3.13.7 are available.
- Locked dependencies and ruff pass; **171 API tests** pass.
- **43 web tests**, lint, TypeScript and the production build pass.
- The three D01 applicant packs pass schema, PDF-derived GPA and multipart-upload checks.
- Zetaris previously passed **all 9 vendor checks** and direct Lightning JDBC
  `SELECT 1` returned 1 using the supplied jar and Java 11. Its private bundle and
  environment files remain outside Git.
- Ollama responds; `gemma4:e2b` and `embeddinggemma` are installed. The earlier
  embedding check confirmed 768 dimensions. No model was loaded for this work.
- The integrated room's charts, simulations and four-turn fictional replay work
  without provider keys. The same-origin proxy avoids the local 3000/3001 CORS conflict.
- Private environment files are ignored by Git with mode 600. Nightshift defaults
  are present, but the Runtime token remains a placeholder.

Docker reports 14 CPUs and about 7.75 GiB usable memory for its configured 8 GB
allocation. Preflight rounds down and warns about memory, emulation and retained
volumes; the existing platform authenticates and runs. Rosetta was enabled during
setup. Approximately 48 GiB of host disk was free at the hardware audit. No volume
reset or unrelated project-container changes were made.

## Still missing

| Area | Current state |
|---|---|
| Shared AdCom database | Supabase project/credentials, pooler/reader values and real migration/RPC acceptance are not verified here. The unrelated local Supabase project is not used. |
| Real data and Zetaris semantic layer | Scorecard key and agent credentials are placeholders; real datasets, ADCOM views/gold and least-privilege checks remain pending Track A. |
| Live graph | B09–B14 and A13 are unfinished. `app/db.py` now exists, but the Zetaris client/repository and real graph are not integrated. |
| Live simulation | The route delegates to Track B's scoring-context method when available. Until then non-demo runs get 503; they are never evaluated using Maya's fictional inputs. |
| Meterless / World Model | Nightshift installation/token and S03/B17/B18 evidence are unavailable. No paid/provider request was made. |
| Deployment | Vercel/project access and a public API host are not known. Web configuration and handoff exist; D08 live phone acceptance has not run. |
| Real-data pitch and judging proof | D09 awaits A15/A16 metrics; D10 awaits real Nemotron/World Model evidence. Their preparation files exist, but their checkboxes remain open. |
| Password rotation | Deferred at gridiii's earlier request. Coordinate private configuration when rotating it. |

## Direction

D01–D07's components and explicit authored-replay fallback follow Track D's plan.
The original static chart previews are now integrated with the team's shared
store. Frozen event, Python schema and TypeScript contracts remain unchanged.
The demo's numbers come from the real deterministic scoring implementation, using
fictional inputs. They do not establish real admissions accuracy.

Focus the next team work on live data, graph/provider integration and release
proof. Country/school discovery, CV-interest matching and persistent memory remain
unapproved expansion proposals. Track A should also reconcile the approved
3,000-post extraction cap with the later 5K/10K corpus milestones.

See [Track D verification](track-d-verification.md), [deployment handoff](deployment.md),
[prototype pitch](pitch.md) and [Meterless evidence handoff](meterless-evidence/README.md).
