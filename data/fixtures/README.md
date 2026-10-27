# Fictional offline fixtures

Done by gridiii via Codex, 2026-10-24.

All applicants, school inputs, outcomes and reference cohorts here are fictional.
They are not admissions evidence, current university policies, calibration results
or proof that Zetaris/Nightshift answered a request. Missing original-post URLs
are intentional. `profile_embedding.json` is a fixed, nonzero shape fixture.
It keeps cosine-distance RPC smoke checks finite, but is not a semantic embedding
or evidence that retrieved applicants are similar to Maya. Real runs must use
the local embedding model.

The per-schema JSON inputs support the plan's hand-written fallback. From
`services/api`, run `uv run python -m scripts.build_demo_fixtures` to rebuild the
four-turn stream and portable `data/demo_runs/maya-uiuc.json` replay. All displayed
probabilities and counterfactual deltas are calculated by `app/scoring/`; tests
check that the waterfall conserves and each what-if reproduces its pivot exactly.
The six-axis radar follows plan section 4.7; Personal remains an assumed reference.

`FAKE_LLM=1 ZETARIS_ENABLED=false` installs the offline parse/debate/embedding
fixtures in the API. The existing B08 parser is tested through this path. B13's
complete graph is now implemented, but its database reads still require a
configured Supabase project and school/twin data; fake model calls do not replace
that database. B14's CLI/direct-client fake-mode support is implemented.
For the self-contained UI replay, use `/room/demo/maya-uiuc`.

This replay was authored and generated, not recorded from a live graph, so
replacing it with a real fictional-persona recording remains a release gate.

Handoff fixes done by gridiii via Codex, 2026-10-25: fixture inputs and outputs
use UTF-8 explicitly, including under Windows or an ASCII process locale. A
regression check rebuilds the artifacts with Python's UTF-8 mode disabled and
compares their bytes. The final chair turn includes `RECOMMENDATION:` with the
disposition from the scoring code, matching the live debate contract.
