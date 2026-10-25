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
