# AdCom: current prototype pitch

Prepared by gridiii via Codex, 2026-10-24.

**Status:** ready to rehearse with the fictional replay. This is not the final
live-demo pitch: real corpus, calibration, deployment and Meterless proof are
still pending their owners. Do not present the replay as a live agent run.

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

“Our target architecture uses Zetaris for governed institutional data, Supabase
for comparable-applicant search, and Meterless for the committee models. The local
Zetaris platform and direct JDBC connection work. The real-data integration,
deployment and Meterless judging evidence are our remaining gates.”

## Answers we can support today

- **Where do percentages come from?** Deterministic Python scoring code. Fixture
  tests verify that contributions conserve and counterfactuals reproduce.
- **Does this prove admissions accuracy?** No. A real held-out backtest and bias
  audit are not available yet.
- **Are these real Reddit applicants?** No. Every profile in this replay is fictional.
- **Does the prototype make admission decisions?** No. It demonstrates an advisory
  interface; universities make their own decisions.
- **Is the partner integration finished?** The Zetaris platform and JDBC check
  work locally. AdCom semantic views and the Meterless/World Model proof remain open.

## Final pitch numbers: do not substitute fixture figures

| Required evidence | Current status | Source when available |
|---|---|---|
| Real applicant count and school coverage | Not verified | Track A data report / database counts |
| Real CDS and Zetaris federation coverage | Not verified | A12/A15 source audit |
| Calibrated demo probability and pivot sizes | No live recording yet | Recorded fictional-persona run with real institutional data |
| Typical odds correction | Not measured on loaded corpus | Calibration table |
| Model and base-rate Brier scores; bias audit | Not measured | A16 held-out backtest |
| Real Nemotron request and World Model conformance | Not captured | D10 evidence |

`data/data-report.json` deliberately contains nulls until these facts are verified.
The About-the-data panel displays “Not verified yet”, rather than a fabricated
zero or the earlier unsupported 10,000+ corpus claim.

## Backup and rehearsal

Use `/room/demo/maya-uiuc`; **Shift+R** switches to/restarts its replay and leaves
text inputs alone. The three fictional applicant packs are in `data/demo_dossiers`.
Record two real fictional-persona runs once B13/B14 is available, using
`scripts.record_demo`; review the files before committing. Keep a final demo video
on both presenting machines once live evidence can be recorded.
