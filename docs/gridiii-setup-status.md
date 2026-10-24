# gridiii: setup and Track D status

Done by gridiii via Codex, 2026-10-24.

The local development tools and standalone Zetaris platform work. The complete
AdCom application is not integrated yet. This audit covers this machine and the
current repository, not another teammate's machine or database.

Reviewed upstream `main` at `8f5efba` and Track D commits `e615c71` (D01),
`9c6cd80` (D02), and `eafea02` (D03). The feature branch is
`gridiii/d01-demo-dossiers`; merging into `main` is a separate team action.

## Verified locally

| Area | Result |
|---|---|
| Tools | Node 24.12.0, pnpm 11.25.0, uv 0.13.5, API Python 3.13.7, Java 11 used for the JDBC check, Docker Engine 29.7.2 and Compose 5.4.0 available. |
| Python dependencies | Locked dependency sync passed; ruff passed; **101 tests passed**. |
| Web | Frozen-lockfile install, lint, TypeScript checks and production build passed. The analytics preview responds with HTTP 200 on port 3001. |
| Analytics helpers | **7 tests passed**, including waterfall conservation/mismatch, missing scores, and safe source URLs. Prior component browser checks also covered loading, simulation, keyboard expansion and highlights. |
| Demo dossiers | All 12 files present; existing schemas accepted all three intakes; PDF-derived GPAs matched printed values; all three multipart uploads returned 202. The PDFs were previously rendered and visually checked. |
| Zetaris | Preflight passed all required checks; **all 9 running checks passed**, including admin login and a query through the platform. |
| Direct JDBC | The supplied Lightning JDBC jar and driver connected from this machine; **`SELECT 1` returned 1**. No local Spark process or alternate JDBC driver was started. |
| Ollama | Service responds; `gemma4:e2b` and `embeddinggemma` are installed. No models were loaded during this audit. A prior embedding check confirmed 768 dimensions. Extraction quality is not verified by installation. |
| Private configuration | Both environment files are ignored by Git and have mode 600. Newly added Nightshift defaults match the current example; its token remains a placeholder. |

Docker reports 14 CPUs and about 7.75 GiB usable memory for the configured 8 GB
allocation. Preflight rounds this down to 7 GB and emits a recommendation warning.
It also warns about Apple Silicon emulation and existing persistent volumes.
The existing data is reused and authentication works; no volume reset is needed.
Rosetta was enabled during the earlier setup. Approximately 48 GiB of host disk
space was free at the audit.

The web checks have nonblocking warnings about an unrelated parent lockfile,
`next lint` deprecation, and Node's native TypeScript module detection. These did
not fail the checks.

## Still required for the full application

| Dependency | Current evidence and next action | Owner / step |
|---|---|---|
| Shared AdCom Supabase | URL, service-role key, pooler credentials and reader password remain placeholders locally. Confirm the team's project, then verify migrations 0001–0009 and RPCs on that real project. The unrelated local project's containers are not an AdCom database. | Track A, with team agreement |
| Real institutional and applicant data | Scorecard key remains a placeholder; no public CSV files are present locally. Extraction, loading, school coverage and calibration still need their acceptance runs. | A07–A11, A15–A16 |
| AdCom semantic layer in Zetaris | Standalone health and JDBC pass, but `ADCOM.v_school_profile`, gold refresh and service-user access restrictions are not verified. The agent password is still a placeholder. Finish data prerequisites and apply/check the SQL before marking A12 complete. | A12 / A14 |
| Application database and Zetaris clients | `app/db.py`, `app/zetaris.py` and `app/zetaris_repo.py` are absent. The current API health route does not probe either service. Direct JDBC success does not complete these steps. | B07 / A13 / B15 |
| Meterless / Nemotron | No matching Nightshift app was found in the standard Applications folders; its default Runtime port is closed and its token is a placeholder. Install/configure Nightshift, add NVIDIA in its Providers tab, and run the three-check smoke test. No live or paid request was made during this audit. | S03, demo-machine owner |
| Live providers and World Model | Meterless wrapper and World Model service are absent. Nightshift installation alone will not complete their integration or judging evidence. | B17 / B18 / D10 |
| Live evaluation and UI | The API still replays scripted events; the live graph, C02 store/client/stream and integrated room are pending. An accepted upload is not a live evaluation of that persona. | B06–B14 / C02 onward |
| Local web/API connection | Zetaris uses port 3000 and this preview uses 3001. Before live integration, configure local API CORS for the chosen web origin; the current default allows only `http://localhost:3000`. | Local configuration with C02 integration |
| Admin password rotation | Deferred at gridiii's earlier request. Coordinate the new password with private local configuration when rotating it. | gridiii |

## Are we following the plan?

Yes for Track D: D01 supplies the fictional demo inputs. D02 and D03 satisfy their
sample-data component checks using the explicit static-JSON schedule in plan
section 6.2. They accept compatible presentation props and leave shared contracts,
the store, existing routes, and other tracks' source files alone. Their numbers
are labeled fictional; they are not evidence of model accuracy or calibration.
Live C02/C03 integration remains pending.

The next D04 step depends on C02 and B06. Coordinate those interfaces with their
owners before wiring the what-if panel. The proposed country/school discovery,
CV-interest matching and memory features remain proposals; they are outside the
current implementation and should be agreed with the team before adding scope.

Two shared documentation issues need team attention:

- The README still says the web app does not exist, although C01 is committed.
  Use the roadmap and actual source to assess current progress.
- A15 and later plan milestones still ask for 5K/10K+ loaded twins, while D-008
  caps extraction at 3,000 posts. Track A and the team should reconcile these
  acceptance targets with the approved cap before declaring the data run done.

The local foundation is ready for contribution. The full live demo and partner
integration gates remain open; this audit does not tick their roadmap boxes.
