"""Build fictional UI fixtures with the real scoring math; no network, model or keys.

Run from services/api: uv run python -m scripts.build_demo_fixtures
The authored schema inputs are fictional, not observations or a live graph recording.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from statistics import median
from types import SimpleNamespace

from app.api_models import WhatIfRequest
from app.schemas.delta import Counterfactual, DeltaReport
from app.schemas.dossier import DossierGrade, ParsedDossier
from app.schemas.inputs import RawApplicantInputs
from app.schemas.institution import SchoolRubric
from app.schemas.twins import EmpiricalBaseline, TwinAnalysis, TwinCard
from app.scoring.metrics import compute_metrics, ec_rating_from_tiers, enforce_grade_invariants
from app.scoring.probability import ScoringInputs, compute_probability
from app.scoring.whatif import run_what_if

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "data/fixtures"


def read(name: str):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build() -> dict:
    dossier = ParsedDossier.model_validate(read("ParsedDossier"))
    grade = DossierGrade.model_validate(read("DossierGrade"))
    inputs = RawApplicantInputs(
        intended_major="Computer Science", target_schools=["uiuc"], essay_text=dossier.essay_text
    )
    grade, metrics, warnings = enforce_grade_invariants(dossier, grade, compute_metrics(dossier), inputs)
    rubric = SchoolRubric.model_validate(read("SchoolRubric"))
    baseline = EmpiricalBaseline.model_validate(read("EmpiricalBaseline"))
    twins = [TwinCard.model_validate(t) for t in read("TwinCard")]
    analysis = TwinAnalysis.model_validate(read("TwinAnalysis"))
    x = ScoringInputs(
        base_admit_rate=rubric.base_admit_rate,
        major_multiplier=rubric.major_multiplier,
        pillar_weights=rubric.pillar_weights,
        ratings={p: getattr(grade.harvard, p).numeric for p in rubric.pillar_weights},
        test_weight=rubric.test_weight,
        test_policy=rubric.test_policy,
        sat=metrics.sat_equivalent,
        sat_25=rubric.sat_25,
        sat_75=rubric.sat_75,
        hooks=(),
        hook_effects={},
        residency_effect=rubric.residency_effect,
        early_round="EA",
        ed_admit_rate=None,
        rd_admit_rate=None,
        ea_admit_rate=None,
        applicant_interest_weight=0,
        twin_sum_w=baseline.sum_w,
        twin_sum_w2=baseline.sum_w2,
        twin_sum_w_admit=baseline.sum_w_admit,
        odds_inflation=baseline.odds_inflation,
    )
    probability = compute_probability(x)
    tiers = [a.tier for a in grade.activity_grades]
    school = {
        "slug": "uiuc",
        "name": rubric.name,
        "early_plans": {"ea": True},
        "major_competitiveness": {"computer_science": {"multiplier": 0.38}, "math_stats": {"multiplier": 1.12}},
    }
    ctx = SimpleNamespace(
        scoring_inputs=x,
        major_category="computer_science",
        school=school,
        tiers=tiers,
        has_recommendations=False,
        counterfactuals=[],
    )
    cfs = []
    for cid, kind, label, request, overrides in [
        (
            "cf_major_math_stats",
            "major_switch",
            "Explore math & statistics",
            {"major_category": "math_stats"},
            {"major_multiplier": 1.12},
        ),
        (
            "cf_sat_75",
            "test_score",
            "Raise SAT to the school reference",
            {"sat": rubric.sat_75},
            {"sat": rubric.sat_75},
        ),
        (
            "cf_add_tier2",
            "add_activity",
            "Build a Tier 2 activity",
            {"add_activities": [2]},
            {
                "ratings": {
                    **x.ratings,
                    "extracurricular": max(
                        1,
                        x.ratings["extracurricular"] + ec_rating_from_tiers(tiers + [2]) - ec_rating_from_tiers(tiers),
                    ),
                }
            },
        ),
        (
            "cf_essay",
            "essay",
            "Strengthen your personal essay",
            {"essay_steps": 1},
            {"ratings": {**x.ratings, "personal": max(2, x.ratings["personal"] - 1)}},
        ),
    ]:
        result = run_what_if(ctx, WhatIfRequest(run_id="demo-maya-uiuc", **request))
        cfs.append(
            Counterfactual(
                id=cid,
                kind=kind,
                label=label,
                p_new=result.simulated.p_final,
                delta_pp=result.delta_pp,
                confidence="model_estimate",
                overrides=overrides,
                evidence="Fictional scenario calculated by app/scoring; no real cohort evidence.",
            )
        )
    cfs.sort(key=lambda c: c.delta_pp, reverse=True)
    report = DeltaReport.model_validate(read("DeltaReport")).model_copy(
        update={"committee_disposition": probability.disposition}
    )
    admitted = [t for t in twins if t.outcome == "accepted"]
    axes = [
        ("gpa", "GPA", metrics.gpa_uw_4, median(t.gpa_uw for t in admitted), 3.5, 4),
        ("test", "Testing", metrics.sat_equivalent, median(t.sat_score for t in admitted), 1300, 1600),
        ("rigor", "Rigor", metrics.advanced_course_count, median(t.ap_count for t in admitted), 0, 14),
        ("activities", "Activities", metrics.tier_derived_ec_rating, ec_rating_from_tiers([2, 3, 3]), 5.5, 1),
        ("spike", "Spike (T1/T2)", 2 * tiers.count(1) + tiers.count(2), 1, 0, 4),
        ("personal", "Essay & Personal", grade.harvard.personal.numeric, 3, 6, 1),
    ]
    radar = {
        "n_admitted": len(admitted),
        "axes": [
            {
                "key": key,
                "label": label,
                "you_raw": you,
                "admitted_raw": ref,
                "you": round(100 * min(1, max(0, (you - lo) / (hi - lo))), 1),
                "admitted_median": round(100 * min(1, max(0, (ref - lo) / (hi - lo))), 1),
                "assumed": key == "personal",
            }
            for key, label, you, ref, lo, hi in axes
        ],
    }
    events: list[dict] = []

    def emit(event: str, **payload) -> None:
        events.append(
            {
                "seq": len(events),
                "run_id": "demo-maya-uiuc",
                "ts": round(1_792_800_000 + len(events) * 0.13, 3),
                "event": event,
                **payload,
            }
        )

    emit("run_started", school_slug="uiuc", target_schools=["uiuc"], cached_dossier=False, fictional=True)
    emit("node_start", node="dossier_parser")
    emit("progress", node="dossier_parser", message="Reading the fictional applicant pack", pct=0.2)
    emit("dossier_parsed", dossier=dossier.model_dump(exclude={"essay_text"}), metrics=metrics.model_dump())
    emit("scorecard", grade=grade.model_dump(), metrics=metrics.model_dump(), warnings=warnings)
    emit("node_complete", node="dossier_parser")
    for node in ("institutional", "twins"):
        emit("node_start", node=node)
        emit("progress", node=node, message="Preparing illustrative evidence", pct=0.3)
    emit("school_rubric", stage="fact_checked", rubric=rubric.model_dump())
    emit("tool_call", node="institutional", tool="fixture.school_profile", status="done", source="fictional")
    emit("fact_checks", brief=read("InstitutionalBrief"), snippets=[], zetaris_queries=[])
    emit("node_complete", node="institutional")
    emit("twins", twins=[t.model_dump() for t in twins], widened_to_peers=False, peer_schools=[])
    emit("baseline", baseline=baseline.model_dump())
    emit("radar", radar=radar)
    emit("twin_analysis", analysis=analysis.model_dump())
    emit("node_complete", node="twins")
    emit("node_start", node="committee_docket")
    emit("probability", probability=probability.model_dump(), scoring_inputs=x.model_dump())
    emit("node_complete", node="committee_docket")
    turns = [
        (
            "advocate",
            "Her sustained programming work gives this application a coherent story "
            "[[dossier:activities.0]]. Twin 2 also connects technical work with a delivered community "
            "project [[twin:2]]. These fictional comparisons give us useful questions to ask about "
            "impact, not a reason to promise an outcome.",
        ),
        (
            "chair",
            "The major constraint deserves equal attention [[model:major]]. Similar grades did not "
            "produce identical outcomes among these examples [[twin:1]]. We should distinguish the "
            "strength of her file from capacity pressure, keep the model range visible, and avoid "
            "turning a small illustrative cohort into certainty.",
        ),
        (
            "advocate",
            "Her independent classifier points toward a way to make that impact tangible "
            "[[dossier:activities.1]]. I would ask for evidence of who used it, what changed, and what "
            "she learned from failure. The activity rating is a starting point for that conversation "
            "[[model:extracurricular]], not a substitute for reading her work.",
        ),
        (
            "chair",
            "I agree that a clearer account of learning would strengthen the essay [[dossier:essay]]. "
            "The simulated alternatives should help her explore a major she actually wants to study, "
            "with curriculum and transfer restrictions checked separately. My recommendation follows "
            "the computed model disposition, with its uncertainty and the fictional status of this "
            f"replay clearly stated [[model:twins]].\nRECOMMENDATION: {probability.disposition}",
        ),
    ]
    for number, (speaker, content) in enumerate(turns, 1):
        emit("debate_turn_start", turn=number, speaker=speaker)
        pieces = re.findall(r"\S+\s*", content)
        for j in range(0, len(pieces), 3):
            emit("debate_token", turn=number, speaker=speaker, delta="".join(pieces[j : j + 3]))
        citations = [
            {"kind": m[1], "ref": m[2], "valid": True, "span": list(m.span())}
            for m in re.finditer(r"\[\[(\w+):([^\]]+)\]\]", content)
        ]
        emit(
            "debate_turn_end",
            turn=number,
            speaker=speaker,
            content=content,
            citations=citations,
            recommendation=probability.disposition if number == 4 else None,
            degraded=False,
        )
    for speaker in ("advocate", "chair"):
        emit("node_complete", node=speaker)
    emit("node_start", node="delta_engine")
    emit("counterfactuals", counterfactuals=[c.model_dump() for c in cfs])
    emit("final_report", report=report.model_dump())
    emit("node_complete", node="delta_engine")
    emit("done", status="complete", elapsed_ms=round(len(events) * 130))
    context = {
        "scoring_inputs": x.model_dump(),
        "major_category": "computer_science",
        "school": school,
        "tiers": tiers,
        "has_recommendations": False,
        "counterfactuals": [c.model_dump() for c in cfs],
    }
    ctx.counterfactuals = cfs
    simulation = run_what_if(ctx, WhatIfRequest(run_id="demo-maya-uiuc", major_category="math_stats"))
    bundle = {
        "name": "maya-uiuc",
        "school_slug": "uiuc",
        "school": school,
        "fictional": True,
        "provenance": "Hand-written fictional replay, deterministic scoring; not a recorded live graph run.",
        "credit": "Done by gridiii via Codex, 2026-10-24",
        "context": context,
        "events": events,
    }
    for name, value in {
        "ComputedMetrics": metrics.model_dump(),
        "DossierGrade": grade.model_dump(),
        "ProbabilityBreakdown": probability.model_dump(),
        "Counterfactual": [c.model_dump() for c in cfs],
        "RadarData": radar,
        "DeltaReport": report.model_dump(),
        "scoring_context": context,
        "WhatIfResponse": simulation.model_dump(),
        "debate": {str(i): content for i, (_, content) in enumerate(turns, 1)},
        # Cosine-distance RPCs require a nonzero vector, even for a shape-only fixture.
        "profile_embedding": [1.0] + [0.0] * 767,
    }.items():
        save(FIXTURES / f"{name}.json", value)
    save(FIXTURES / "fake_stream.json", bundle)
    save(ROOT / "data/demo_runs/maya-uiuc.json", bundle)
    return bundle


if __name__ == "__main__":
    result = build()
    print(f"Built {len(result['events'])} fictional events; all shown probabilities come from app/scoring.")
