# AdCom: current prototype pitch

Prepared by gridiii via Codex, 2026-10-24; real-data update 2026-10-26.

**Status:** ready to rehearse with the fictional replay. This is not the final
live-demo pitch: A15's real corpus and coverage figures are available, while
A16's held-out backtest/bias audit, deployment and Meterless proof remain open.
Do not present the authored replay as a live agent run or as a recording using
the real corpus. Its applicant comparisons and school inputs are fictional.

## Reported evidence — 2026-10-26

Source: [Jmar's A15 data report](https://github.com/Galm007/GenAI-Hackathon-Project/blob/b6b3d37dd3b40c95c74b3f7d069947c60dc7cf7b/docs/data-report.md).

- **947** real self-reported applicant profiles: 830 first-year and 117 transfer.
- **265** universities; **5** have 2024–25 CDS rubrics, with IPEDS fallback for
  the other 260 in the Zetaris school-profile view.
- All five demo schools meet the reported coverage targets: UIUC 191 first-year
  outcomes (132 CS), CMU 182 (139 CS), Michigan 254 (126 CS), Georgia Tech 212
  (163 CS), and UC Berkeley 288 (160 CS). One applicant can appear at several schools.
- Median Reddit odds inflation **3.24×**, measured across 88 schools with at
  least 15 outcomes. This is an approximate self-selection adjustment, not an
  accuracy score or proof that the model is calibrated.
- Brier scores, held-out accuracy and group bias results remain **not measured**.
- Say **947**, not “10,000+”. Further corpus growth is optional A18.

## Three-minute walkthrough

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
estimate is about 33.7%; that is a calculation from illustrative inputs, not a
claim about a real student's chances.”

Open the evidence details and the comparison chart. Explain that the dashed
Personal reference is assumed because the comparable profiles have no essays.

**2:15–2:45 — A useful next move**

“A suggestion should be something you can inspect. Trying the alternative-major
scenario recalculates the same model, rather than asking an AI to invent a better
percentage. Reset brings us back to the original file. Choosing that major still
requires genuine interest and checking the university's curriculum and rules.”

Click **Try it**, show the fictional result around 42.0% (+8.3 pp), then **Reset**.
Use the currently displayed calculation if fixture inputs change.

**2:45–3:00 — The engineering and remaining proof**

"Our team has loaded 947 self-reported applicant profiles, 265 universities and
five CDS rubrics. The graph and governed Zetaris views are implemented.
Backtesting, deployment and Meterless evidence remain open."

## Answers we can support today

- **Where do percentages come from?** Deterministic Python scoring code. Fixture
  tests verify that contributions conserve and counterfactuals reproduce.
- **Does this prove admissions accuracy?** No. A real held-out backtest and bias
  audit are not available yet.
- **Are these real Reddit applicants?** No. Every profile in this replay is fictional.
- **Does the prototype make admission decisions?** No. It demonstrates an advisory
  interface; universities make their own decisions.
- **Is the partner integration finished?** The standalone Zetaris platform passes
  its checks locally. Track A verified AdCom semantic views and agent permissions
  in A12 on its stack; the chosen demo host still needs its own working connection.
  Meterless/World Model proof remains open.

## Final pitch numbers: do not substitute fixture figures

| Required evidence | Current status | Source when available |
|---|---|---|
| Real applicant count and school coverage | 947 profiles; 265 universities; all five demo schools meet the reported coverage targets | A15 data report, 2026-10-26 |
| Real CDS and Zetaris federation coverage | 5 CDS schools, 260 IPEDS fallback; gold refreshed | A12/A15 data report |
| Calibrated demo probability and pivot sizes | No live recording yet | Recorded fictional-persona run with real institutional data |
| Typical odds correction | Median 3.24× across 88 schools with at least 15 outcomes | A15 calibration table summary |
| Model and base-rate Brier scores; bias audit | Not measured | A16 held-out backtest |
| Real Nemotron request and World Model conformance | Not captured | D10 evidence |

`data/data-report.json` now contains the reported corpus, coverage and odds
adjustment figures, with a dated source link. Brier scores remain null and the
About-the-data panel says "Not measured yet". These counts do not complete D09:
the held-out backtest/bias audit and final recorded-run figures are still missing.

## Judge questions about the current data

- **How much real data do you have?** 947 self-reported applicant profiles and
  265 universities. Five demo schools have CDS rubrics. Those are the reported
  A15 counts, separate from the authored fictional replay.
- **How do you handle Reddit self-selection?** The reported median odds inflation
  is 3.24× across the 88 schools with at least 15 outcomes. The scoring pipeline
  includes an approximate correction; its presence does not establish accuracy.
- **What is your Brier score?** Not measured yet. A16's held-out comparison and
  bias audit remain open, so we cannot claim a numerical accuracy result.
- **Is 947 enough to cover every school or student?** It does not establish that.
  Coverage is uneven, outcomes are self-reported, and the five demo schools were
  checked against explicit coverage targets. The UI shows the actual counts.

## Backup and rehearsal

Use `/room/demo/maya-uiuc`; **Shift+R** restarts the selected named replay, or
switches a live room to the default Maya replay, and leaves text inputs alone.
Projector mode is retained. The three fictional applicant packs are in `data/demo_dossiers`.
B13 is implemented. Record two real fictional-persona runs once the shared
database/demo data and provider setup are available, with human approval for
provider usage, using `scripts.record_demo`; review the files before committing.
B14 remains responsible for the complete fake-mode graph path. Keep a final demo
video on both presenting machines once live evidence can be recorded.
