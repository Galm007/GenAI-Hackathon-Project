# Track D verification — 2026-10-24

Done by gridiii via Codex. This is a local component/offline-replay report, not the
deployed X01 integration report or real partner judging evidence.

| Check | Actual result |
|---|---|
| API locked dependencies / ruff | Passed |
| API tests | 171 passed, including real HTTP replay/what-if and the existing B08 node in fixture mode |
| Web tests | 43 passed, including stale-request cancellation and per-run reset |
| Web lint / TypeScript / production build | Passed |
| Fixture generation | Byte-for-byte deterministic rebuild; 100 fictional events |
| Probability source | Existing Python scoring code; waterfall conservation and exact counterfactual reproduction tested |
| Pivot → controls → gauge | Verified in browser: alternative major gives 42.0% from a 33.7% fictional baseline; Reset restores baseline |
| Replay / Shift+R | Fresh stream starts and completes; no old sequence state blocks restart |
| Charts | Correct signed waterfall, model range, six-axis radar, dashed assumed Personal axis, readable evidence tables |
| Comparable cards | Expand by keyboard; missing test/source data stays unavailable; citation highlighting retained |
| Essay copy | Browser shows success only after the clipboard write resolves; independent automation clipboard readback was unavailable |
| Responsive checks | Wide three-column room, laptop drawer, and 390px phone analytics; phone body width equals viewport width. At exactly 1440px, only one dossier and one analytics sidebar render visibly, with no body overflow. |
| Data disclosure | Unknown real metrics display "Not verified yet"; fictional corpus is excluded |

The same-origin local API proxy was exercised on port 3001 → 8000. Zetaris remains
on port 3000. An existing Node `next lint` deprecation notice is nonblocking; the
unrelated parent-lockfile warning was removed by setting the web tracing root.

## Remaining acceptance gates

- **D08:** choose hosting/project access; finish B13/B14/B16; verify a hosted live
  run from a phone against the co-located API/Zetaris stack.
- **D09:** A15/A16 supply real corpus, coverage, calibration and backtest results;
  then update the data manifest and final pitch with those verified figures.
- **D10:** complete S03/B17/B18 and capture a real app request served by Nemotron
  plus the genuine World Model conformance scorecard.
- Replace the authored replay with two real recordings of fictional-persona runs
  once the graph and provider are available. The recorder is supplied.

No additional Track A/B implementation step is marked complete by this work.

## Handoff verification — 2026-10-25

Done by gridiii via Codex after syncing through `e4db91f` (Track B B01–B13 and
Track A A12/A13). Aron's D-1 fixture-encoding blocker and D-3 chair-format note
are addressed in D-033. All fixture reads/writes use UTF-8 explicitly, and the
closing recommendation comes from the computed probability disposition.

- Locked Python dependencies and ruff: passed; **298 API tests passed**.
- Non-UTF-8 locale with Python UTF-8 mode disabled: **6 fixture/encoding tests
  passed**, including byte-identical generation in a separate process.
- **43 web tests**, lint, TypeScript and production build: passed.
- Production web proxy: the updated **101-event** authored replay reaches a
  successful `done` event; the chair content and recommendation agree.
- The alternative-major what-if still computes **42.0%** from the unchanged
  fictional scoring inputs.

No live provider request or actual graph recording is included in these results.
Track A's flag/fallback fixes and demo-school/twin data, plus Track B's B14 work,
remain separate handoff items.

## Reported-data disclosure — 2026-10-26

Done by gridiii via Codex. The manifest and pitch now use A15's real reported
947 profiles, 265 universities, five CDS schools, per-school coverage and median
3.24× odds inflation across 88 qualifying schools. The source report is pinned
to `b6b3d37`; the manifest is partial and both Brier fields remain null.

- Locked Python dependencies / ruff: passed; **340 API tests passed**.
- **43 web tests**, lint, TypeScript and production build: passed.
- Production browser: the panel shows the reported counts and all five school
  rows, a dated source link, and both Brier values as **Not measured yet**.
- The fictional notice is scoped to the authored replay. The real dataset is
  never described as the source of that replay's invented comparisons.
- Phone layout at **390px**: dialog client width and scroll width both **389px**;
  the table stays readable. Escape closes the dialog and returns focus to
  **About the data**. The temporary viewport override was reset.
- Screenshot: `outputs/track-d-real-data-2026-10-26.png` in gridiii's workspace
  (outside this repository).

D09's actual completion still requires A16 and final real-run figures. The
reported corpus snapshot is not a claim of live credentials, deployed phone
acceptance, model accuracy or provider judging evidence.

## Named replay restart — 2026-10-26

Done by gridiii via Codex. Previously every restart navigated to `maya-uiuc`,
which would silently leave any future alternate recording. The controls now
retain the selected recording name for demo sources, while live sources keep
the default Maya fallback. The callback is stable across render updates.

- In the production browser, both the button and Shift+R retained an alternate
  recording's route and `?projector=1` instead of switching to Maya.
- The check used a temporary, clearly authored fictional fixture in the local
  container. It was removed afterwards and is not judging evidence or a live run.
- 43 web tests, lint, TypeScript and production build passed after the fix.

## Co-located API deployment preparation — 2026-10-26

Done by gridiii via Codex, using Aron's B16 implementation without changing its
source files. The arm64 image `zetaris-adcom-api:latest` built successfully
(`sha256:3195a560a2fa412740be06101b6be7b0e4906d9deaca3a381fa228d58dd97f9c`).
Container `zetaris-adcom-api-1` runs on the existing Zetaris network and exposes
only `127.0.0.1:8000` to the host.

- In-container HTTP request to `http://ui:3000/api/config`: **200**.
- Container replay: **101 events**, successful `done`; what-if: **42.0%** for
  the unchanged fictional alternative-major scenario.
- Private root/API `.env` files: absent from the image filesystem.
- Standalone Zetaris `./verify.sh`: **all 9 PASS** after API bring-up.
- Actual project health: **ok=false, db=false, zetaris=false**;
  **fake_llm=true, demo_mode=true**. Working authored replays do not verify live
  data access. Team database and local agent credentials still need configuring.

The temporary navigation-test recording was removed. No public tunnel, live
model call, database mutation or volume reset was part of these checks. D08/X01
and B16's live Zetaris acceptance are still open.
