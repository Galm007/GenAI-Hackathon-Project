from __future__ import annotations

import re
import time

import orjson

from app import llm, world_model
from app.embeddings import embed_one
from app.profile_text import ProfileFacts, build_profile_text
from app.schemas.dossier import ComputedMetrics, DossierGrade, ParsedDossier
from app.schemas.inputs import RawApplicantInputs
from app.scoring.metrics import compute_metrics, enforce_grade_invariants

from ..docket import applicant_section
from ..events import emit, progress
from ..prompts.dossier import DOSSIER_EXTRACTOR_SYSTEM, RUBRIC_GRADER_SYSTEM
from ..state import AdComState

NODE = "dossier_parser"
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
EC_ANCHOR_FORMULA = ("EC anchor = 5.2 − 0.55 × (4·#Tier1 + 2·#Tier2 + 0.75·#Tier3 + 0.2·#Tier4), "
                     "bounded to [1.6, 5.5] without a Tier 1 activity and [1.0, 5.5] with one.")


def _pdf_block(b64: str, title: str) -> dict:
    return {"type": "document", "title": title,
            "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}


def _intake_blocks(inputs: RawApplicantInputs) -> list[dict]:
    blocks: list[dict] = []                              # documents first, then text
    if inputs.transcript_pdf_b64:
        blocks.append(_pdf_block(inputs.transcript_pdf_b64, "Transcript"))
    if inputs.resume_pdf_b64:
        blocks.append(_pdf_block(inputs.resume_pdf_b64, "Resume"))
    parts = [f"<{tag}>\n{val}\n</{tag}>" for tag, val in (
        ("resume_text", inputs.resume_text), ("activities_list", inputs.activities_text),
        ("common_app_essay", inputs.essay_text), ("recommendation_letter", inputs.recommendation_text),
    ) if val]
    parts.append("Transcribe these materials into the dossier.")
    blocks.append({"type": "text", "text": "\n\n".join(parts)})
    return blocks


def redact(d: ParsedDossier) -> ParsedDossier:
    essay = d.essay_text
    if essay:
        for s in sorted(set(d.pii_strings), key=len, reverse=True):
            if len(s) >= 3:
                essay = essay.replace(s, "[redacted]")
        essay = PHONE.sub("[phone]", EMAIL.sub("[email]", essay))
    return d.model_copy(update={"essay_text": essay, "pii_strings": []})


def _grader_payload(d: ParsedDossier, m: ComputedMetrics, inputs: RawApplicantInputs) -> str:
    payload = {
        "intake": {
            "intended_major": inputs.intended_major,
            "hooks": inputs.hooks,
            "has_recommendations": bool(inputs.recommendation_text),
            "context": inputs.context.model_dump(),
        },
        "metrics": m.model_dump(exclude={"tier_derived_ec_rating", "ec_score"}),
        "ec_anchor_formula": EC_ANCHOR_FORMULA,
        "high_school": d.high_school.model_dump(),
        "courses": [c.model_dump() for c in d.courses],
        "test_scores": d.test_scores.model_dump(),
        "activities": [{"index": i, **a.model_dump()} for i, a in enumerate(d.activities)],
        "awards": [{"index": i, **a.model_dump()} for i, a in enumerate(d.awards)],
        "essay": d.essay_text,
        "recommendation": inputs.recommendation_text,
        "extraction_warnings": d.extraction_warnings,
    }
    return "<dossier>\n" + orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode() + "\n</dossier>"


def _facts(d: ParsedDossier, g: DossierGrade, m: ComputedMetrics, inputs: RawApplicantInputs) -> ProfileFacts:
    return ProfileFacts(
        applicant_type="first_year",
        intended_major=inputs.intended_major,
        major_category=g.major_category,
        gpa_uw=m.gpa_uw_4, gpa_w=m.gpa_w_5, college_gpa=None,
        sat=d.test_scores.sat_total, act=d.test_scores.act_composite,
        advanced_courses=m.advanced_course_count,
        rigor_label=g.rigor_label,
        spike=g.spike.label if g.spike.strength != "none" else None,
        activities=[(ag.tier, d.activities[ag.activity_index].description) for ag in g.activity_grades],
        awards=[(a.level, a.name) for a in d.awards],
        hooks=list(inputs.hooks),
        school_type=d.high_school.school_type,
        residency_state=inputs.context.residency_state,
        income_bracket="<60k" if inputs.context.low_income else None,
        first_gen=inputs.context.first_gen,
    )


async def dossier_parser_node(state: AdComState) -> dict:
    t0 = time.perf_counter()
    inputs = state["inputs"]
    emit("node_start", node=NODE, label="Dossier Parser & Rubric Grader")

    progress(NODE, "Reading transcript, resume and essay…", 0.05)
    dossier = await llm.parse(
        ParsedDossier, system=DOSSIER_EXTRACTOR_SYSTEM,
        messages=[{"role": "user", "content": _intake_blocks(inputs)}],
        effort="medium", max_tokens=32000,
    )
    dossier = redact(dossier)
    metrics = compute_metrics(dossier)
    emit("dossier_parsed", dossier=dossier.model_dump(exclude={"essay_text"}), metrics=metrics.model_dump())

    progress(NODE, f"Grading {len(dossier.activities)} activities and four Harvard pillars…", 0.5)
    grade = await llm.parse(
        DossierGrade, system=RUBRIC_GRADER_SYSTEM,
        messages=[{"role": "user", "content": _grader_payload(dossier, metrics, inputs)}],
        effort="high", max_tokens=24000,
    )
    grade, metrics, warnings = enforce_grade_invariants(dossier, grade, metrics, inputs)
    emit("scorecard", grade=grade.model_dump(), metrics=metrics.model_dump(), warnings=warnings)

    progress(NODE, "Embedding profile for twin search…", 0.9)
    profile_text = build_profile_text(_facts(dossier, grade, metrics, inputs))
    embedding = await embed_one(profile_text)

    emit("node_end", node=NODE, elapsed_ms=int((time.perf_counter() - t0) * 1000))
    out = {"dossier": dossier, "grade": grade, "metrics": metrics, "profile_text": profile_text,
            "profile_embedding": embedding, "warnings": warnings}
    await world_model.append(state.get("run_id"), NODE, applicant_section({**state, **out}))
    return out
