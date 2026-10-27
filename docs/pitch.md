# AdCom: current prototype pitch

Prepared by gridiii via Codex, 2026-10-24; real-data update 2026-10-26.

**Status:** the fictional Maya evaluation completed live on 2026-10-26 with Gemini
Free Tier, the shared database, local Zetaris and Aron's World Model. Run
`cd712489-e9e2-4940-8e5b-6fed71adb07e`: 97 contiguous events, four non-degraded
committee turns and final report. Raw captures stay private. Hosted physical-phone
acceptance and the final Nemotron committee/capture check are recorded separately.
Do not present the authored replay as a live agent run or as a recording using
the real corpus. Its applicant comparisons and school inputs are fictional.

## Reported evidence — 2026-10-26

Sources: [Jmar's A15/A16 report](https://github.com/Galm007/GenAI-Hackathon-Project/blob/c4d0772/docs/data-report.md)
and [the held-out backtest output](https://github.com/Galm007/GenAI-Hackathon-Project/blob/bf03906/data/backtest.json).

- **947** real self-reported applicant profiles: 830 first-year and 117 transfer.
- **265** universities; **5** have 2024–25 CDS rubrics, with IPEDS fallback for
  the other 260 in the Zetaris school-profile view.
- All five demo schools meet the reported coverage targets: UIUC 191 first-year
  outcomes (132 CS), CMU 182 (139 CS), Michigan 254 (126 CS), Georgia Tech 212
  (163 CS), and UC Berkeley 288 (160 CS). One applicant can appear at several schools.
- Median Reddit odds inflation **3.24×**, measured across 88 schools with at
  least 15 outcomes. This is an approximate self-selection adjustment, not an
  accuracy score or proof that the model is calibrated.
- Held-out backtest (A16, latest 30% of posts, 2,341 admit/deny decisions): Brier
  **0.232** for the app's probability against **0.303** for the official admit rate.
  The earlier Reddit admit rate at the school scores 0.216, which is better.
  Ranking inside one school is weak (AUC about 0.53), and some groups are poorly
  calibrated, for example under-$30k income: predicted 28%, observed 59%. Present
  it as rough calibration, not as accuracy.
- Say **947**, not “10,000+”. Further corpus growth is optional A18.

## Three-minute walkthrough — gridiii hosted Gemini run

Use the figures for the chosen run consistently. Jmar's recorded Nemotron run
uses different agent grades and has its own figures below; never mix its pivots
with the separate 56.66% Gemini run.

## Walkthrough

**0:00–0:25 — The problem**

“A university application is more than a GPA. It is a file read against a
particular school's priorities, with tradeoffs that a simple ranking misses.
AdCom is our prototype for making that reasoning visible before a student applies.”

**0:25–0:55 — The file**

“This is Maya, a fictional computer-science applicant. The dossier panel keeps
grades, activities and the reader's assessment together. Our parser and grading
rules share a structured contract, so the conversation can point back to the
exact evidence it is discussing.”

Show the fictional banner, dossier and activity tiers. Keep the banner visible.

**0:55–1:35 — The committee**

“This replay demonstrates our intended committee experience: an advocate and a
skeptic challenge the same file. A citation takes you to the relevant applicant
comparison or model factor. The dialogue explains the evidence; it does not
produce the admission percentage.”

Select a twin citation and expand that card. Select a model-factor citation.

**1:35–2:15 — The auditable number**

“The scoring code starts with a school rate and accounts for major pressure,
ratings, testing and comparable outcomes. The waterfall shows those changes
adding up. The range makes uncertainty visible. In this fictional example, the
estimate is 56.66% using today's live fictional-Maya run against the shared
institutional data. It remains a rough advisory estimate, not a prediction of
a real student's admission outcome.”

Open the evidence details and the comparison chart. Explain that the dashed
Personal reference is assumed because the comparable profiles have no essays.

**2:15–2:45 — A useful next move**

“A suggestion should be something you can inspect. Adding one hypothetical Tier 2
activity changes the same deterministic calculation to 58.64%, a 1.98-point shift.
An extra 50 SAT points moves it only 0.36 points. These scenarios are estimates
about a fictional file, not promises that one change causes admission.”

On the live run, try **Add one Tier 2 activity**, then reset. The authored
`/room/demo/maya-uiuc` replay uses different illustrative inputs (33.7% baseline);
announce replay mode and use its displayed figures if presenting that fallback.

**2:45–3:00 — The engineering and remaining proof**

"Our team has loaded 947 self-reported applicant profiles, 265 universities and
five CDS rubrics. Our held-out Brier score is 0.232 versus 0.303 for official
admit rates, but ranking within a school is weak and subgroup errors remain.
The live Gemini run and World Model tests pass; the final phone and Nemotron
committee evidence are tracked explicitly in our handoff."

## Answers we can support today

- **Where do percentages come from?** Deterministic Python scoring code. Fixture
  tests verify that contributions conserve and counterfactuals reproduce.
- **Does this prove admissions accuracy?** No. The held-out backtest improves on
  official admit rates in this self-selected sample, but the earlier Reddit-rate
  baseline does better, ranking within a school is weak, and subgroup gaps remain.
- **Are these real Reddit applicants?** No. Every profile in this replay is fictional.
- **Does the prototype make admission decisions?** No. It demonstrates an advisory
  interface; universities make their own decisions.
- **Is the partner integration finished?** The standalone Zetaris platform passes
  its checks locally. Track A verified AdCom semantic views and agent permissions
  in A12 and the same setup now works on this Mac. World Model conformance is
  8/8; the final streamed Nemotron committee request remains open.

## Final pitch numbers: do not substitute fixture figures

| Required evidence | Current status | Source when available |
|---|---|---|
| Real applicant count and school coverage | 947 profiles; 265 universities; all five demo schools meet the reported coverage targets | A15 data report, 2026-10-26 |
| Real CDS and Zetaris federation coverage | 5 CDS schools, 260 IPEDS fallback; gold refreshed | A12/A15 data report |
| Team recorded Nemotron run (Jmar) | Live Maya at UIUC run, re-recorded 2026-10-27 (D-060): **55.6%** (range 44.3–66.7%, LIKELY ADMIT), base rate 42.4%. Best pivots: promote the Tier 3 crop-disease project to Tier 2, +1.95 pp; add one Tier 2 activity, +2.9 pp. SAT: Maya's 1520 is already UIUC's 75th percentile, so `{DELTA_SAT}` = 0.0 pp (1600 would add +0.74 pp). Major arbitrage: none supported, because UIUC has major data only for CS (n=132), so `{P_ARB}`, `{DELTA_MAJOR}` and `{N_MAJOR}` are not claimed | `data/demo_runs/maya-uiuc-live.json` (recorded run, Meterless/Nemotron, Zetaris on) |
| Separate local Gemini run (gridiii) | 56.66% baseline; Tier 2 activity 58.64% (+1.98 pp); SAT 1520→1570 gives 57.02% (+0.36 pp) | Live run and deterministic what-if, 2026-10-26 |
| Typical odds correction | Median 3.24× across 88 schools with at least 15 outcomes | A15 calibration table summary |
| Model and base-rate Brier scores; bias audit | Brier 0.232 vs 0.303 base rate; weak within-school ranking; subgroup gaps reported | A16 backtest, `docs/data-report.md` |
| Real Nemotron request and World Model conformance | Smoke/extraction requests captured; World Model 8/8; streamed committee check still open | D10 evidence |

`data/data-report.json` now contains the reported corpus, coverage and odds
adjustment figures, with a dated source link, and now the A16 Brier scores
(0.232 model, 0.303 base rate). The recorded-run figures come from `data/demo_runs/maya-uiuc-live.json` (see the table).

**Script change for the recorded run:** the 2:05 "major arbitrage" and 2:30 "SAT to the 75th percentile" lines must not quote numbers. Say instead: "Her best lever is turning the crop-disease project into a Tier 2 result, worth about two points; the agents say plainly that UIUC's data doesn't support a major pivot, so they don't invent one." The authored `maya-uiuc` replay still shows fixture pivots (+8.3 pp) and stays labeled illustrative.

For gridiii's separate hosted Gemini run: The final run figures above now replace illustrative pitch values. No positive empirical major pivot was returned: Math/Stats yields 57.10% (+0.44 pp) only as a model experiment, with the explicit warning that major-specific data is unavailable. Do not sell it as a data-backed arbitrage recommendation.

## Judge questions about the current data

- **How much real data do you have?** 947 self-reported applicant profiles and
  265 universities. Five demo schools have CDS rubrics. Those are the reported
  A15 counts, separate from the authored fictional replay.
- **How do you handle Reddit self-selection?** The reported median odds inflation
  is 3.24× across the 88 schools with at least 15 outcomes. The scoring pipeline
  includes an approximate correction; its presence does not establish accuracy.
- **What is your Brier score?** 0.232 on a held-out set of the latest 30% of posts,
  against 0.303 for the official admit rate alone. Plainly: our calibration is
  still rough. Ranking applicants within one school is only slightly better than
  chance, and the Reddit rate at a school does slightly better on Brier (0.216).
  That is why every number ships with an 80% range. The subgroup audit is in the
  data report, including income groups where we under-predict.
- **Is 947 enough to cover every school or student?** It does not establish that.
  Coverage is uneven, outcomes are self-reported, and the five demo schools were
  checked against explicit coverage targets. The UI shows the actual counts.

## Backup and rehearsal

Use `/room/demo/maya-uiuc`; **Shift+R** restarts the selected named replay, or
switches a live room to the default Maya replay, and leaves text inputs alone.
Projector mode is retained. The three fictional applicant packs are in `data/demo_dossiers`.
B13/B14 are implemented and the shared database is connected on this Mac.
Record two actual graph runs of the fictional personas once the provider and
host-specific Zetaris access are verified. Use `scripts.record_demo`, with human
approval for trial/provider usage. Keep raw captures private and review them:
the inputs are fictional, but retrieved comparable profiles can contain real
student data and must not enter fixtures, committed recordings or public video.
Only report aggregate run figures until a shareable capture has been reviewed.
Keep a final demo video on both presenting machines once evidence can be recorded.


## Separate hosted Gemini §7.5 values (gridiii, not the team recording)

- `P_UIUC`: **56.66%**.
- `P_ARB`: **57.10%**, Math/Stats model experiment only; no empirical major pivot was returned.
- `DELTA_MAJOR`: **+0.44 percentage points**, model estimate with the API's missing-major-data warning.
- `N_MAJOR`: **0 qualifying major-pivot candidates**; the target-major neighborhood sample size is unavailable, so no applicant count is invented.
- `DELTA_SAT`: **+0.36 percentage points** for 1520→1570, yielding 57.02%.
- The recommended live scenario used in the pitch is the returned Tier 2 activity
  counterfactual: **+1.98 percentage points**, yielding 58.64%.

All deltas come from deterministic scoring, not the language model. Captured by
gridiii via Codex, 2026-10-26. The private event log is retained outside Git.
