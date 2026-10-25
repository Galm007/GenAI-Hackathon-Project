from __future__ import annotations

import asyncio
import time
from datetime import date

import anthropic
import orjson

from app import llm, zetaris_repo
from app.config import settings
from app.schemas.institution import InstitutionalBrief, WebSnippet
from app.scoring.rubric import apply_brief_adjustments, build_school_rubric
from app.web_research import research_school

from ..events import emit, tool_call
from ..prompts.institutional import INSTITUTIONAL_SYSTEM
from ..state import AdComState
from ..zetaris_tool import run_zetaris_research

NODE = "institutional"
ZETARIS_BUDGET_S = 12
SCHOOL_FIELDS = ("slug", "name", "state", "control", "admit_rate", "admit_rate_source", "ed_admit_rate",
                 "rd_admit_rate", "test_policy", "sat_composite_25", "sat_composite_75", "act_composite_25",
                 "act_composite_75", "c7_weights", "c7_source", "early_plans", "major_competitiveness", "cds_year",
                 "data_source")


def upcoming_matriculation_year(today: date | None = None) -> int:
    today = today or date.today()
    return today.year + 1 if today.month >= 7 else today.year


def _applicant_summary(state: AdComState, slug: str) -> dict:
    g, d = state["grade"], state["dossier"]
    return {
        "intended_major": state["inputs"].intended_major,
        "major_category": g.major_category,
        "spike": g.spike.model_dump(),
        "ratings": {p: getattr(g.harvard, p).rating for p in ("academic", "extracurricular", "personal", "athletic")},
        "top_activities": [d.activities[ag.activity_index].name
                           for ag in sorted(g.activity_grades, key=lambda a: a.tier)[:4]],
        "essay_themes": g.essay.themes if g.essay else [],
        "early_round": state["inputs"].early_round.get(slug),
        "hooks": state["inputs"].hooks,
    }


def _payload(school: dict, rubric, snippets: list[WebSnippet], findings: list[dict],
             state: AdComState) -> list[dict]:
    applicant = _applicant_summary(state, school["slug"])
    zq = "\n\n".join(f"[{f['id']}] purpose: {f['purpose']}\nSQL: {f['sql']}\n"
                     f"rows: {orjson.dumps(f['rows'][:10]).decode()}"
                     for f in findings if not f.get("error")) or "(no Zetaris queries ran)"
    web = "\n\n".join(f"[{s.id}] {s.title}\nURL: {s.url}\nPublished: {s.published or 'unknown'}\n{s.content}"
                      for s in snippets) or "(no web results available)"
    return [{"type": "text", "text": (
        "<school_record>\n" + orjson.dumps({k: school.get(k) for k in SCHOOL_FIELDS}).decode()
        + "\n</school_record>\n\n"
        "<derived_rubric>\n" + rubric.model_dump_json() + "\n</derived_rubric>\n\n"
        f"<web_snippets>\n{web}\n</web_snippets>\n\n"
        f"<zetaris_results>\n{zq}\n</zetaris_results>\n\n"
        "<applicant_summary>\n" + orjson.dumps(applicant).decode() + "\n</applicant_summary>\n\n"
        "Write the institutional brief."
    )}]


def _drop_unsourced(brief: InstitutionalBrief, valid_ids: set[str]) -> InstitutionalBrief:
    priorities = [p.model_copy(update={"source_ids": [i for i in p.source_ids if i in valid_ids]})
                  for p in brief.strategic_priorities]
    priorities = [p for p in priorities if p.source_ids]
    checks = []
    for fc in brief.fact_checks:
        ids = [i for i in fc.source_ids if i in valid_ids]
        verdict = fc.verdict if ids or fc.verdict == "unverified" else "unverified"
        checks.append(fc.model_copy(update={"source_ids": ids, "verdict": verdict}))
    return brief.model_copy(update={"strategic_priorities": priorities, "fact_checks": checks})


async def institutional_node(state: AdComState) -> dict:
    t0 = time.perf_counter()
    slug, inputs, grade = state["school_slug"], state["inputs"], state["grade"]
    emit("node_start", node=NODE, label="Institutional Rubric & Fact-Checker")

    tool_call(NODE, "zetaris.profile", "started", slug=slug, table=settings.zetaris_gold_profile)
    school = await zetaris_repo.school_profile(slug)          # Zetaris gold table; Supabase fallback inside
    tool_call(NODE, "zetaris.profile", "done", source=school.get("data_source", "supabase"),
              cds_year=school.get("cds_year"), c7_source=school.get("c7_source"))

    rubric = build_school_rubric(school, grade.major_category, inputs.context.residency_state)
    emit("school_rubric", stage="cds", rubric=rubric.model_dump())

    warnings: list[str] = []
    snippets: list[WebSnippet] = []
    findings: list[dict] = []
    brief: InstitutionalBrief | None = None

    async def zetaris_research() -> list[dict]:
        if not settings.zetaris_enabled:
            return []
        try:                                                    # time-boxed so Zetaris never stalls the node
            return await asyncio.wait_for(run_zetaris_research(
                slug=slug, major_category=grade.major_category,
                applicant_summary=orjson.dumps(_applicant_summary(state, slug)).decode()), ZETARIS_BUDGET_S)
        except (TimeoutError, llm.LLMRefusal, anthropic.APIError) as exc:
            warnings.append(f"zetaris research degraded: {type(exc).__name__}")
            return []

    try:
        # Web research and the Zetaris SQL tool loop run concurrently.
        snippets, findings = await asyncio.gather(
            research_school(school, grade.major_category.replace("_", " "), upcoming_matriculation_year()),
            zetaris_research(),
        )
        brief = await llm.parse(
            InstitutionalBrief, system=INSTITUTIONAL_SYSTEM,
            messages=[{"role": "user", "content": _payload(school, rubric, snippets, findings, state)}],
            effort="medium", max_tokens=12000,
        )
        brief = _drop_unsourced(brief, {s.id for s in snippets} | {f["id"] for f in findings})
    except (llm.LLMRefusal, llm.LLMTruncated, anthropic.APIError, TimeoutError) as exc:
        warnings.append(f"institutional research degraded: {type(exc).__name__}")
        emit("error", node=NODE, message="Live fact-check unavailable — using Common Data Set only.",
             recoverable=True)

    rubric = apply_brief_adjustments(rubric, brief)
    emit("fact_checks", brief=brief.model_dump() if brief else None, snippets=[s.model_dump() for s in snippets],
         zetaris_queries=findings)
    emit("school_rubric", stage="fact_checked", rubric=rubric.model_dump())
    emit("node_end", node=NODE, elapsed_ms=int((time.perf_counter() - t0) * 1000))
    return {"school": school, "school_rubric": rubric, "institutional_brief": brief,
            "web_snippets": snippets, "zetaris_queries": findings, "warnings": warnings}
