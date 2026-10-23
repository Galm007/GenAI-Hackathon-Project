HARVARD_RUBRIC = """\
## Harvard-style reader ratings, 1–6 (lower is stronger)
These anchors paraphrase reader guidance disclosed in the SFFA v. Harvard trial record, adapted for a \
single-reader simulation. A rating of 1 is rare in every pillar.

Academic
1 — Summa potential. Top grades in the most demanding curriculum available plus genuine scholarly or creative \
    distinction beyond the classroom: national/international academic recognition (e.g., USAMO/USAPhO/USABO \
    qualifier or higher, Regeneron STS / ISEF finalist) or original research with recognized outcomes.
2 — Magna potential. Near-top grades in a most-demanding curriculum; test scores, if submitted, at or above the \
    most selective colleges' 75th percentile (roughly SAT 1530+ / ACT 35+).
3 — Cum laude potential. Excellent grades in a demanding curriculum; scores within the most selective \
    colleges' middle 50% (roughly SAT 1450–1530 / ACT 33–34).
4 — Solid. Good grades with several B's, or a moderately demanding curriculum; scores below that range.
5 — Modest preparation for highly selective colleges.
6 — Not academically competitive for highly selective admission.

Extracurricular
1 — Unusual, possibly national-level achievement or professional-level talent; likely to be a major \
    contributor in college. Normally requires at least one Tier 1 activity.
2 — Strong contribution: regional/state distinction or significant leadership with demonstrated impact \
    (Tier 2 level).
3 — Solid participation, possibly school-level leadership (Tier 3 level).
4 — Limited participation.
5–6 — Essentially none, or concerning conduct (rare; requires evidence).

Personal (from essays and, when provided, recommendations)
1 — Outstanding: uncommon maturity, insight, generosity, or courage, shown through specific evidence.
2 — Very strong: distinctive voice, clear self-reflection, evident positive effect on others.
3 — Generally positive: thoughtful and likable but not distinctive.
4 — Bland or neutral: the essay could have been written by many applicants.
5 — Somewhat negative: questionable judgment or tone.
6 — Worrisome.

Athletic
1 — Recruited-athlete caliber (requires the recruited_athlete hook or explicit evidence of college recruitment).
2 — Strong varsity contribution with distinction (all-league/all-state, captain of a competitive program).
3 — Some athletic participation.
4 — No athletic participation. (5–6 are unused for athletics.)

Modifiers: "+" when the file sits at the strong edge of its rating, "-" at the weak edge, "" otherwise.
"""

TIER_RUBRIC = """\
## Extracurricular tiers, 1–4 (Sara Harberson-style; lower is stronger)
Tier 1 — Rare and exceptional. National or international distinction, or impact at a scale few high schoolers \
  reach: national/international award winner or finalist; recruited athlete; founder of an organization with \
  substantial, verifiable reach (thousands of beneficiaries, significant funds raised, press coverage); research \
  published in a recognized venue; nationally ranked competitor; professional-level arts accomplishment.
Tier 2 — Distinction at the state or regional level, or a major leadership role with demonstrated impact: \
  state/regional awards and selections (all-state, regional science fair winner), student body president, \
  highly selective summer programs, leadership of a large organization with measurable outcomes, substantial \
  paid work or family responsibility that structures the student's week.
Tier 3 — School-level leadership and accomplishment: club president or officer, varsity captain, section \
  leader, school-level awards, multi-year commitment with a defined role.
Tier 4 — Participation or membership without leadership or distinction; short-term or low-commitment activities.

Calibration: tier inflation is the most common grading error. Most strong applicants have zero Tier 1 \
activities and one or two Tier 2s. When the evidence sits between two tiers, choose the lower one. \
"Founder" or "President" of a club with no evidence of scale or outcomes is Tier 3. Paid work and family \
caregiving are legitimate and often underrated: grade them on hours, responsibility, and duration, not prestige.
"""
