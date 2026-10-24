# D01: fictional demo applicants

Done by **gridiii via Codex, 2026-10-24**.

These are original fictional application materials for development, testing, and
the hackathon presentation. All students, secondary schools, grades, scores,
awards, and personal stories are invented. University names identify application
targets only. These files contain no real student records or admission outcomes.

| Folder | Student | Target | Demonstration case |
|---|---|---|---|
| `maya/` | Maya Chen | `uiuc`, Computer Science | Main demo: programming competitions, an applied-ML project, and library teaching |
| `backup1/` | Leo Park | `cmu`, Computer Engineering | Strong academics and hardware work; distinguish team achievements from individual awards |
| `backup2/` | Sam Rivera | `umich`, Biology | Improving grades, paid work, caregiving, and no SAT/ACT score supplied |

Each folder contains:

- `transcript.pdf`: selectable text, a complete fictional academic-course record,
  a grading legend, test scores if supplied, and clearly marked in-progress work.
- `activities.txt`: roles, grade levels, time commitments, awards, and limits on
  what each project actually claims.
- `essay.txt`: an original personal essay, approximately 475-485 words before its
  fictional-data header.
- `intake.json`: a complete request body compatible with `app.api_models.IntakeForm`.
  Its `activities_text` and `essay_text` reproduce the adjacent files exactly.

## Using a pack

With the API already running, submit from the repository root:

```bash
curl --fail-with-body -sS http://127.0.0.1:8000/api/evaluate \
  --form 'intake=<data/demo_dossiers/maya/intake.json' \
  --form 'transcript=@data/demo_dossiers/maya/transcript.pdf;type=application/pdf'
```

Replace both `maya` path segments with `backup1` or `backup2` for a backup.
The activities and essay are already in the JSON; they are not separate upload
fields. No resume or recommendation letter is supplied. The schema's `consent`
value applies to these fictional materials only.

Each pack has a different demo `session_id`. Use a fresh session ID when starting
concurrent runs of the same pack. The dates are a fixed **24 October 2026** demo
snapshot with graduation in spring 2027. Application deadlines are synthetic test
inputs, not verified institutional deadlines; adjust them deliberately when
rehearsing at a later date.

## Academic and narrative consistency

- Every listed completed course carries equal GPA weight. Unweighted points are
  A = 4.0, A- = 3.7, B+ = 3.3, B = 3.0, B- = 2.7. Honors adds 0.5; AP and dual
  enrollment add 1.0, capped at 5.0 per course. In-progress courses and AP exams
  do not enter the GPA. This matches the existing scoring module's conventions.
- Maya's printed GPAs are **3.94 unweighted / 4.52 weighted**, and her SAT is
  **1520 (790 Math + 730 EBRW)**. Her three activities, leadership of 14 CS-club
  members, USACO Gold achievement, regional fair result, and two listed AP exam
  scores agree with the main scripted demo. Her essay intentionally retains the
  improvable closing sentence cited by that demo's final report.
- Maya's full transcript expands the scripted fixture's three-course excerpt.
  Its illustrative course counts, rigor, trend, and judgment scores are not an
  expected output for these files. Recompute metrics from the full transcript;
  do not copy scripted scores into a live evaluation.
- Leo's printed GPAs are **4.00 / 4.59**, with **1560 SAT (800 + 760)**. The robotics
  award belongs to his team. His door-alert project is a prototype, not a
  certified device, publication, or commercial product.
- Sam's printed GPAs are **3.62 / 3.89**, with an upward academic trend. SAT and
  ACT must remain unknown, not zero. First-generation and low-income context is
  explicitly self-reported fictional information, not inferred from the essay.
- No probability, committee disposition, or expected admission outcome is
  prescribed by this pack. Model judgments and deterministic results are produced
  by the existing evaluation pipeline when it is available.

## Integration boundary

This step supplies input documents only. It does not modify the scripted stream,
shared schemas, API, scoring code, frontend, database, or Zetaris setup. Until B13
lands, the current API still replays its existing scripted Maya stream even when
submitted a backup pack; this validates upload acceptance, not persona-specific
AI analysis. Offline LLM fixtures and recorded replays belong to later steps.
