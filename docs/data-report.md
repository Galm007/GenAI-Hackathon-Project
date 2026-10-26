# Data report (A15)

Run date: 2026-10-26 · Author: Jmar L. Pineda via Claude Code · All figures come from the live Supabase and Zetaris stack, queried at the end of the run. Plan §2.9.11, §7.5.

## Headline

| Item | Value |
|---|---|
| Applicant twins loaded | **947** (830 first-year from r/collegeresults, 117 transfer from r/TransferToTop25); 925 are from the 2026 cycle |
| Roadmap target | ≥ 10,000. **Not met.** See "Why not 10K" |
| Universities loaded | 265 (College Scorecard, admit rate ≤ 0.60) |
| Schools with CDS rubric (C7) | **5** (CMU, UMich, Georgia Tech, UIUC, UC Berkeley, 2024-25) |
| Zetaris `v_school_profile` | 5 rows from CDS, 260 from IPEDS fallback |
| Brier score, base-rate Brier | **0.232**, 0.303 (held out, n = 2341; see A16) |

## Why not 10K

Arctic Shift returned 3,579 posts for the two subreddits; 1,487 of them mention a decision and fall inside the extraction cap (`CAPS`, 3,000). Of those, 540 were rejected (525 are not results posts, 12 had no resolvable school, 3 hit the model's output limit) and 947 became twins. The ceiling for this source is therefore about 1,000 twins, not 10,000. Reaching 10K needs more source data, not a larger cap. That is a scope decision for the team (D-037).

Throughput measured on `gemma4:e2b`: **8.9 s per post**, about 3.4 h for the 1,487 posts, at zero API cost. Zetaris paused and restarted itself around each run.

## Extraction quality

- Kept 947 of 1,487 posts (64%). The newest 200 posts kept 86%; older posts are mostly not results posts.
- The database matches the final extraction file exactly: 3 rows left over from an earlier smoke run were deleted (2026-10-26) and stats and the Zetaris gold table refreshed.
- School resolution: the first full run lost decisions at schools such as Cornell, Columbia, USC and NYU because their short names were not aliased, and two entries pointed at slugs that do not exist (`upenn`, `washu`). `data/school_aliases.yaml` now maps 87 schools (302 → 447 aliases in the database) and posts rejected for "no resolved school" fell from 95 to 12. Still unresolved, because the schools are not in the 265: Caltech, Penn State, UC Santa Cruz, RIT, UC Riverside, Harvey Mudd, UC Merced, CU Boulder, Ohio State.
- Applicant detail: SAT present on 646 twins, unweighted GPA on 520.

## Demo-school coverage

Target: at least 80 first-year outcomes per demo school and at least 15 in the demo major (computer science).

| School | First-year outcomes | Computer science | Official admit rate | Reddit admit rate | Odds inflation |
|---|---|---|---|---|---|
| UIUC | 191 | 132 | 0.424 | 0.539 | 1.59 |
| CMU | 182 | 139 | 0.117 | 0.291 | 3.11 |
| UMich | 254 | 126 | 0.156 | 0.350 | 2.91 |
| Georgia Tech | 212 | 163 | 0.141 | 0.429 | 4.59 |
| UC Berkeley | 288 | 160 | 0.110 | 0.309 | 3.60 |

All five meet both targets. The official admit rates come from the 2024-25 CDS for these five schools.

## Calibration

`school_reddit_calibration` has 157 schools. For the 88 with at least 15 Reddit outcomes, **odds inflation** (Reddit odds divided by official odds, clamped to [1, 8]) has median **3.24** (min 1.12, max 8.0). Reddit applicants are admitted at roughly three times the official odds, which is the self-selection effect Node 3 divides out. 43 schools have at least 80 outcomes; `school_major_stats` has 119 (school, major) rows with n ≥ 15.

## Activity tier distribution

Across the 947 twins, the extractor tiered 6,088 activities with the Node 1 rubric:

| Tier | Activities | Share |
|---|---|---|
| 1 | 765 | 12.6% |
| 2 | 2,231 | 36.6% |
| 3 | 2,411 | 39.6% |
| 4 | 681 | 11.2% |

Median activity score is 9.75. Top majors: computer science 422, pre-health 110, political science 90, undecided 75, humanities 47, business 46.

## Federated sources (Zetaris)

- `ADCOM.v_school_profile`: c7_source = cds for 5 schools, ipeds for 260.
- `ADCOM_LAKE.gold.school_profile` refreshed after the final load (`run_etl zetaris-refresh`).
- The agent role cannot read `ADCOM_PUBLIC.scorecard_institutions` directly (by design, D-031), so the Scorecard row count above comes from Supabase.

## CDS verification

C7 factors for all five schools were compared with the source PDFs and spreadsheets (A10, D-034): 18 of 18 factors match for each school.

## Caveats for the pitch

- Reddit outcomes are self-reported and self-selected; the calibration step exists to correct for that, and it is rough.
- With 947 twins and 5 CDS schools, say exactly that. Do not use "10,000+" anywhere. `data/data-report.json` (Track D's file, read by the About-the-data panel) still holds nulls; it can now be filled with n_twins 947, n_schools 265 and n_cds_schools 5.

<!-- backtest:begin -->

## Backtest and bias audit (A16)

Run date: 2026-10-26 · `uv run python -m scripts.backtest --write` · plan §6.2, §7.3 Q1. No language model was called: every number comes from `app/scoring/` on fields extracted from the post.

### Setup

- **7801** first-year admit/deny decisions (2015 waitlists left out, because they are neither outcome).
- Held out: the latest 30% of posts (2341 decisions, posted 2026-04-28 to 2026-10-18). The earlier 5460 are the only twin evidence a held-out row may use. Plan wording is "hold out the latest cycle", but 925 of 947 twins are the 2026 cycle (D-044).
- Ratings use the statistical anchors Node 1 clamps to. Personal and athletic ratings are neutral (a Reddit post has no essay or letters), so the pillar signal is academic and extracurricular only.
- The major multiplier is held at 1.0 (the stored multiplier is learned from these same posts, so it would leak).
- Twin neighbours are chosen by GPA and SAT proximity at the same school, not by embedding, because embeddings are not pulled into the backtest. The live app's retrieval is better than this stand-in.

### Held-out scores (n = 2341)

| Predictor | Mean predicted | Observed admit rate | Brier ↓ | AUC ↑ | AUC within a school ↑ |
|---|---|---|---|---|---|
| Official admit rate (CDS), same for everyone | 16.4% | 46.0% | 0.303 | 0.723 | 0.500 |
| Earlier Reddit admit rate at that school | 39.9% | 46.0% | 0.216 | 0.720 | 0.500 |
| Rubric model (no twins) | 51.4% | 46.0% | 0.241 | 0.677 | 0.529 |
| Rubric model + twin evidence (what the app shows) | 32.4% | 46.0% | 0.232 | 0.716 | 0.535 |

Brier: the app's probability scores 0.232, the official-rate baseline 0.303, the earlier Reddit rate at the school 0.216. Plain AUC mixes schools, so the school's own admit rate already gets most of it; the last column ranks applicants inside one school, where a constant rate scores 0.5. The rubric scores 0.529 there and the app 0.535.

### Reliability (held out, five equal-count bins)

| Bin | n | Mean predicted | Observed | Mean predicted (no twins) | Observed (no twins) |
|---|---|---|---|---|---|
| 1 | 468 | 9.1% | 27.6% | 15.1% | 29.3% |
| 2 | 468 | 17.9% | 30.1% | 31.9% | 34.6% |
| 3 | 468 | 26.8% | 35.5% | 50.8% | 42.1% |
| 4 | 468 | 41.0% | 59.8% | 69.9% | 50.0% |
| 5 | 469 | 67.4% | 77.2% | 89.2% | 74.2% |

### Bias audit: calibration by subgroup

Income bracket and first-generation status are self-reported and sparse. They are used here only to audit calibration; income is never a model input and first-gen enters only through the extractor's hook flag. The audit groups use explicit self-report only: the extractor sets a first_gen hook on far more twins than ever state it, so that flag is not used to define the group. Groups with n < 30 are marked and should not be read.

**Held out, app probability · Income bracket**

| Group | n | Mean predicted | Observed | Gap (pred − obs) | Brier | AUC |
|---|---|---|---|---|---|---|
| 150-250k | 646 | 32.8% | 41.8% | -9.0 pp | 0.206 | 0.745 |
| 30-60k | 571 | 33.5% | 48.9% | -15.3 pp | 0.246 | 0.686 |
| 60-80k | 68 | 38.7% | 44.1% | -5.4 pp | 0.211 | 0.742 |
| 80-150k | 51 | 31.9% | 25.5% | +6.4 pp | 0.238 | 0.583 |
| <30k | 121 | 27.6% | 58.7% | -31.1 pp | 0.320 | 0.688 |
| >250k | 99 | 34.8% | 40.4% | -5.6 pp | 0.198 | 0.779 |
| unknown | 785 | 31.3% | 47.8% | -16.5 pp | 0.234 | 0.736 |

**Held out, app probability · First-generation (self-reported)**

| Group | n | Mean predicted | Observed | Gap (pred − obs) | Brier | AUC |
|---|---|---|---|---|---|---|
| no | 33 | 32.1% | 39.4% | -7.3 pp | 0.197 | 0.735 |
| not stated | 2004 | 33.0% | 46.1% | -13.1 pp | 0.225 | 0.729 |
| yes | 304 | 28.8% | 46.7% | -17.9 pp | 0.280 | 0.654 |

**All decisions, rubric model (no training rows needed) · Income bracket**

| Group | n | Mean predicted | Observed | Gap (pred − obs) | Brier | AUC |
|---|---|---|---|---|---|---|
| 150-250k | 2367 | 52.5% | 42.4% | +10.1 pp | 0.233 | 0.705 |
| 30-60k | 1350 | 51.9% | 47.5% | +4.4 pp | 0.216 | 0.730 |
| 60-80k | 158 | 52.3% | 44.3% | +8.0 pp | 0.197 | 0.779 |
| 80-150k | 140 | 47.4% | 28.6% | +18.9 pp | 0.278 | 0.537 |
| <30k | 607 | 38.2% | 47.4% | -9.3 pp | 0.252 | 0.627 |
| >250k | 337 | 57.0% | 43.0% | +14.0 pp | 0.230 | 0.734 |
| unknown | 2842 | 45.1% | 44.9% | +0.2 pp | 0.219 | 0.715 |

**All decisions, rubric model (no training rows needed) · First-generation (self-reported)**

| Group | n | Mean predicted | Observed | Gap (pred − obs) | Brier | AUC |
|---|---|---|---|---|---|---|
| no | 106 | 42.7% | 64.2% | -21.4 pp | 0.343 | 0.505 |
| not stated | 6741 | 50.2% | 43.2% | +7.1 pp | 0.220 | 0.721 |
| yes | 954 | 38.4% | 50.8% | -12.4 pp | 0.254 | 0.669 |

### How to read this

- **Weak, and stated plainly.** Inside a school, the profile ranks applicants only slightly better than chance (within-school AUC near 0.53). The app's Brier beats the official-rate baseline mainly because the twin term moves the level toward the Reddit admit rate, and it does not beat simply using the earlier Reddit rate at that school. Ranking skill from a GPA, SAT and activity-tier profile is modest; the essays, letters and school context that decide close calls are not in a Reddit post.
- Reddit applicants are self-selected, so observed admit rates are far above the official ones. A model anchored on official rates will under-predict on this sample. The twin term is meant to close part of that gap; the Mean predicted and Observed columns show how much it does.
- Subgroup gaps larger than a few points on groups with enough rows are a calibration problem, not a feature. They are reported as they came out.

<!-- backtest:end -->
