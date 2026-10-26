# Data report (A15)

Run date: 2026-10-26 · Author: Jmar L. Pineda via Claude Code · All figures come from the live Supabase and Zetaris stack, queried at the end of the run. Plan §2.9.11, §7.5.

## Headline

| Item | Value |
|---|---|
| Applicant twins loaded | **950** (833 first-year from r/collegeresults, 117 transfer from r/TransferToTop25); 928 are from the 2026 cycle |
| Roadmap target | ≥ 10,000. **Not met.** See "Why not 10K" |
| Universities loaded | 265 (College Scorecard, admit rate ≤ 0.60) |
| Schools with CDS rubric (C7) | **5** (CMU, UMich, Georgia Tech, UIUC, UC Berkeley, 2024-25) |
| Zetaris `v_school_profile` | 5 rows from CDS, 260 from IPEDS fallback |
| Brier score, base-rate Brier | not measured (A16) |

## Why not 10K

Arctic Shift returned 3,579 posts for the two subreddits; 1,487 of them mention a decision and fall inside the extraction cap (`CAPS`, 3,000). Of those, 540 were rejected (525 are not results posts, 12 had no resolvable school, 3 hit the model's output limit) and 947 became twins. The ceiling for this source is therefore about 1,000 twins, not 10,000. Reaching 10K needs more source data, not a larger cap. That is a scope decision for the team (D-037).

Throughput measured on `gemma4:e2b`: **8.9 s per post**, about 3.4 h for the 1,487 posts, at zero API cost. Zetaris paused and restarted itself around each run.

## Extraction quality

- Kept 947 of 1,487 posts (64%). The newest 200 posts kept 86%; older posts are mostly not results posts.
- 3 rows in the database come from an earlier smoke run and are not in the final extraction file (their posts are now rejected as not results or cut off). They are left in place pending a cleanup decision.
- School resolution: the first full run lost decisions at schools such as Cornell, Columbia, USC and NYU because their short names were not aliased, and two entries pointed at slugs that do not exist (`upenn`, `washu`). `data/school_aliases.yaml` now maps 87 schools (302 → 447 aliases in the database) and posts rejected for "no resolved school" fell from 95 to 12. Still unresolved, because the schools are not in the 265: Caltech, Penn State, UC Santa Cruz, RIT, UC Riverside, Harvey Mudd, UC Merced, CU Boulder, Ohio State.
- Applicant detail: SAT present on 649 twins, unweighted GPA on 522.

## Demo-school coverage

Target: at least 80 first-year outcomes per demo school and at least 15 in the demo major (computer science).

| School | First-year outcomes | Computer science | Official admit rate | Reddit admit rate | Odds inflation |
|---|---|---|---|---|---|
| UIUC | 191 | 132 | 0.424 | 0.539 | 1.59 |
| CMU | 183 | 139 | 0.117 | 0.290 | 3.09 |
| UMich | 254 | 126 | 0.156 | 0.350 | 2.91 |
| Georgia Tech | 212 | 163 | 0.141 | 0.429 | 4.59 |
| UC Berkeley | 289 | 160 | 0.110 | 0.308 | 3.59 |

All five meet both targets. The official admit rates come from the 2024-25 CDS for these five schools.

## Calibration

`school_reddit_calibration` has 157 schools. For the 88 with at least 15 Reddit outcomes, **odds inflation** (Reddit odds divided by official odds, clamped to [1, 8]) has median **3.24** (min 1.11, max 8.0). Reddit applicants are admitted at roughly three times the official odds, which is the self-selection effect Node 3 divides out. 43 schools have at least 80 outcomes; `school_major_stats` has 119 (school, major) rows with n ≥ 15.

## Activity tier distribution

Across the 950 twins, the extractor tiered 6,105 activities with the Node 1 rubric:

| Tier | Activities | Share |
|---|---|---|
| 1 | 767 | 12.6% |
| 2 | 2,237 | 36.6% |
| 3 | 2,417 | 39.6% |
| 4 | 684 | 11.2% |

Median activity score is 9.75. Top majors: computer science 423, pre-health 110, political science 91, undecided 76, humanities 47, business 46.

## Federated sources (Zetaris)

- `ADCOM.v_school_profile`: c7_source = cds for 5 schools, ipeds for 260.
- `ADCOM_LAKE.gold.school_profile` refreshed after the final load (`run_etl zetaris-refresh`).
- The agent role cannot read `ADCOM_PUBLIC.scorecard_institutions` directly (by design, D-031), so the Scorecard row count above comes from Supabase.

## CDS verification

C7 factors for all five schools were compared with the source PDFs and spreadsheets (A10, D-034): 18 of 18 factors match for each school.

## Caveats for the pitch

- Reddit outcomes are self-reported and self-selected; the calibration step exists to correct for that, and it is rough.
- With about 950 twins and 5 CDS schools, say exactly that. Do not use "10,000+" anywhere. `data/data-report.json` (Track D's file, read by the About-the-data panel) still holds nulls; it can now be filled with n_twins 950, n_schools 265 and n_cds_schools 5.
