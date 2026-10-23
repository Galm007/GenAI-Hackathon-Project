from __future__ import annotations

import io
import re
from typing import Literal

import httpx
import yaml
from pydantic import BaseModel, ValidationError
from pypdf import PdfReader

from app.local_llm import LocalLLMError, chat_structured, settings

from .common import DATA_DIR, log, supabase
from .resources import zetaris_paused

# Mirrors the `c7_level` enum in migration 0001 (swap for app.schemas.common.C7Level once B02 lands).
C7Level = Literal["very_important", "important", "considered", "not_considered"]

# A small local model does better on three narrow questions than on one 40-field form.
SECTION_MARKERS = {
    "counts": ("C1", "C21", "C22", "D1", "D2"),
    "tests": ("C8", "C9", "C11", "C12"),
    "c7": ("C7",),
}
MAX_SECTION_CHARS = 12_000          # ~3.5K tokens, inside the 8K context with room for the answer


class C7Factors(BaseModel):
    rigor: C7Level | None
    class_rank: C7Level | None
    academic_gpa: C7Level | None
    test_scores: C7Level | None
    essay: C7Level | None
    recommendations: C7Level | None
    interview: C7Level | None
    extracurriculars: C7Level | None
    talent_ability: C7Level | None
    character: C7Level | None
    first_generation: C7Level | None
    alumni_relation: C7Level | None
    geographic_residence: C7Level | None
    state_residency: C7Level | None
    religious_affiliation: C7Level | None
    volunteer_work: C7Level | None
    work_experience: C7Level | None
    applicant_interest: C7Level | None


class GPABucket(BaseModel):
    bucket: str
    pct: float


class EarlyPlans(BaseModel):
    ed: bool | None
    ed2: bool | None
    ea: bool | None
    rea: bool | None


class TransferProfile(BaseModel):
    accepts_transfers: bool | None
    applicants: int | None
    admits: int | None
    enrolled: int | None
    min_college_gpa: float | None


class CDSCounts(BaseModel):
    cds_year: str | None
    applicants_total: int | None
    admits_total: int | None
    enrolled_total: int | None
    ed_applicants: int | None
    ed_admits: int | None
    early_plans: EarlyPlans
    transfer: TransferProfile


class CDSTests(BaseModel):
    test_policy: Literal["required", "optional", "blind", "unknown"]
    sat_composite_25: int | None
    sat_composite_50: int | None
    sat_composite_75: int | None
    sat_ebrw_25: int | None
    sat_ebrw_75: int | None
    sat_math_25: int | None
    sat_math_75: int | None
    act_composite_25: int | None
    act_composite_75: int | None
    pct_submitting_sat: float | None
    pct_submitting_act: float | None
    gpa_distribution: list[GPABucket]
    avg_hs_gpa: float | None
    pct_top10_class: float | None


class CDSExtract(CDSCounts, CDSTests):
    c7: C7Factors
    extraction_notes: list[str]


COMMON_RULES = """\
Rules
- Copy numbers exactly as printed. If a field is blank, "N/A", or not in the text, return null. Never guess.
- Percentages become fractions (63% → 0.63). Keep every answer short.
"""

COUNTS_SYSTEM = f"""\
You read text from a U.S. college's Common Data Set (CDS): C1 (applications, admissions, enrollment), \
C21–C22 (early decision / early action) and Section D (transfer admission). Fill the fields from that text.

{COMMON_RULES}- C1: use the totals for first-time, first-year students (men + women + another gender, if split).
- C21/C22: whether ED, ED2, EA, or restrictive EA is offered; ED applicants and admits if printed.
- Section D: whether transfers are accepted; transfer applicants, admits, enrolled; minimum college GPA if printed.
- Report the CDS year printed on the form, e.g. "2024-2025".
"""

TESTS_SYSTEM = f"""\
You read text from a U.S. college's Common Data Set (CDS): C8 (testing policy), C9 (test score percentiles) and \
C11–C12 (high school GPA, class rank). Fill the fields from that text.

{COMMON_RULES}- C8 test policy: "required" if tests are required for some or all applicants by default; "optional" if \
considered when submitted; "blind" if not used in admission decisions; otherwise "unknown".
- C9: newer forms list SAT composite percentiles; older forms list only sections, so leave composite null then.
- C11: one bucket per printed GPA band with its label as printed. C12: average high school GPA.
"""

C7_SYSTEM = """\
You read text from section C7 of a U.S. college's Common Data Set: a grid in which each admission factor has a mark \
(X) in one of four columns: Very Important, Important, Considered, Not Considered. The text keeps the page layout, \
so the column of the mark tells you the level. Map each row to very_important, important, considered, or \
not_considered using these keys: Rigor of secondary school record → rigor; Class rank → class_rank; Academic GPA → \
academic_gpa; Standardized test scores → test_scores; Application Essay → essay; Recommendation(s) → \
recommendations; Interview → interview; Extracurricular activities → extracurriculars; Talent/ability → \
talent_ability; Character/personal qualities → character; First generation → first_generation; Alumni/ae relation \
→ alumni_relation; Geographical residence → geographic_residence; State residency → state_residency; Religious \
affiliation/commitment → religious_affiliation; Volunteer work → volunteer_work; Work experience → work_experience; \
Level of applicant's interest → applicant_interest. Ignore racial/ethnic status rows on older forms. A row without \
a clear mark is null.
"""


def section_texts(pdf: bytes) -> dict[str, str]:
    """Layout-preserving text of the pages that mention each section (+ the next page for grids that spill over)."""
    reader = PdfReader(io.BytesIO(pdf))
    pages = [p.extract_text(extraction_mode="layout") or "" for p in reader.pages]
    out: dict[str, str] = {}
    for name, markers in SECTION_MARKERS.items():
        idx: set[int] = set()
        for i, text in enumerate(pages):
            if any(re.search(rf"\b{m}\b", text) for m in markers):
                idx.update({i, i + 1})
        text = "\n\n".join(pages[i] for i in sorted(idx) if i < len(pages))
        if name != "c7":                                   # C7 needs its padding: the mark's column is the answer
            text = re.sub(r"[ \t]{3,}", "   ", text)
        out[name] = text[:MAX_SECTION_CHARS]
    return out


def _frac(v: float | None) -> float | None:
    if v is None:
        return None
    if 1 < v <= 100:                       # "63" instead of 0.63
        v = v / 100
    return v if 0 <= v <= 1 else None


def _ordered(vals: list[int | None], lo: int, hi: int) -> bool:
    given = [v for v in vals if v is not None]
    return all(lo <= v <= hi for v in given) and given == sorted(given)


def sanity_check(x: CDSExtract) -> CDSExtract:
    """Deterministic guard for a small model's arithmetic and unit slips: drop what cannot be right, say so."""
    notes = list(x.extraction_notes)

    def drop(reason: str, **fields: object) -> None:
        for k, v in fields.items():
            setattr(x, k, v)
        notes.append(f"dropped: {reason}")

    if x.applicants_total is not None and x.admits_total is not None and x.admits_total > x.applicants_total:
        drop("admits > applicants", applicants_total=None, admits_total=None)
    if x.admits_total is not None and x.enrolled_total is not None and x.enrolled_total > x.admits_total:
        drop("enrolled > admits", enrolled_total=None)
    if x.ed_applicants is not None and x.ed_admits is not None and x.ed_admits > x.ed_applicants:
        drop("ED admits > ED applicants", ed_applicants=None, ed_admits=None)
    if not _ordered([x.sat_composite_25, x.sat_composite_50, x.sat_composite_75], 400, 1600):
        drop("SAT composite out of range or unordered",
             sat_composite_25=None, sat_composite_50=None, sat_composite_75=None)
    if not _ordered([x.sat_ebrw_25, x.sat_ebrw_75], 200, 800):
        drop("SAT EBRW out of range or unordered", sat_ebrw_25=None, sat_ebrw_75=None)
    if not _ordered([x.sat_math_25, x.sat_math_75], 200, 800):
        drop("SAT math out of range or unordered", sat_math_25=None, sat_math_75=None)
    if not _ordered([x.act_composite_25, x.act_composite_75], 1, 36):
        drop("ACT out of range or unordered", act_composite_25=None, act_composite_75=None)
    for field in ("pct_submitting_sat", "pct_submitting_act", "pct_top10_class"):
        setattr(x, field, _frac(getattr(x, field)))
    buckets = [(b, _frac(b.pct)) for b in x.gpa_distribution]
    if any(p is None for _, p in buckets):
        notes.append("dropped: GPA buckets with an impossible percentage")
    x.gpa_distribution = [GPABucket(bucket=b.bucket, pct=p) for b, p in buckets if p is not None]
    if x.avg_hs_gpa is not None and not 0 < x.avg_hs_gpa <= 5:
        drop("average GPA out of range", avg_hs_gpa=None)
    x.extraction_notes = notes
    return x


def _rate(num: int | None, den: int | None) -> float | None:
    return round(num / den, 4) if num is not None and den else None


def to_update(x: CDSExtract, url: str) -> dict:
    rd_apps = (x.applicants_total - x.ed_applicants) if x.applicants_total and x.ed_applicants else None
    rd_admits = (x.admits_total - x.ed_admits) if x.admits_total and x.ed_admits else None
    upd = {
        "cds_year": x.cds_year,
        "applicants": x.applicants_total, "admits": x.admits_total, "enrolled": x.enrolled_total,
        "admit_rate": _rate(x.admits_total, x.applicants_total),
        "ed_applicants": x.ed_applicants, "ed_admits": x.ed_admits,
        "ed_admit_rate": _rate(x.ed_admits, x.ed_applicants),
        "rd_admit_rate": _rate(rd_admits, rd_apps),
        "yield_rate": _rate(x.enrolled_total, x.admits_total),
        "test_policy": x.test_policy,
        "sat_composite_25": x.sat_composite_25, "sat_composite_50": x.sat_composite_50,
        "sat_composite_75": x.sat_composite_75,
        "sat_ebrw_25": x.sat_ebrw_25, "sat_ebrw_75": x.sat_ebrw_75,
        "sat_math_25": x.sat_math_25, "sat_math_75": x.sat_math_75,
        "act_composite_25": x.act_composite_25, "act_composite_75": x.act_composite_75,
        "pct_submitting_sat": x.pct_submitting_sat, "pct_submitting_act": x.pct_submitting_act,
        "gpa_distribution": [b.model_dump() for b in x.gpa_distribution],
        "avg_hs_gpa": x.avg_hs_gpa, "pct_top10_class": x.pct_top10_class,
        "c7_weights": {k: v for k, v in x.c7.model_dump().items() if v is not None},
        "early_plans": x.early_plans.model_dump(),
        "transfer_profile": x.transfer.model_dump(),
    }
    # Only overwrite Scorecard values with non-null CDS values.
    upd = {k: v for k, v in upd.items() if v not in (None, [], {})}
    upd["source_urls"] = {"cds": url}
    upd["data_quality"] = {"base_source": "cds", "extractor": settings.cds_model, "notes": x.extraction_notes}
    return upd


async def extract_cds(pdf: bytes, slug: str) -> CDSExtract | None:
    """Three narrow calls to the local model. None when the PDF has no usable text layer (hand-enter those)."""
    texts = section_texts(pdf)
    if not all(texts.values()):
        log.warning("%s: no text found for %s; scanned PDF? enter by hand",
                    slug, ", ".join(k for k, v in texts.items() if not v))
        return None
    ask = f"Extract the CDS fields for school slug '{slug}' from this text:\n\n<cds>\n{{}}\n</cds>"
    kw = {"model": settings.cds_model, "num_ctx": 8192, "num_predict": 1200}
    try:
        counts = await chat_structured(CDSCounts, COUNTS_SYSTEM, ask.format(texts["counts"]), **kw)
        tests = await chat_structured(CDSTests, TESTS_SYSTEM, ask.format(texts["tests"]), **kw)
        c7 = await chat_structured(C7Factors, C7_SYSTEM, ask.format(texts["c7"]), **kw)
    except (LocalLLMError, ValidationError, httpx.HTTPError) as exc:
        log.warning("%s: CDS extraction failed (%s: %s)", slug, type(exc).__name__, exc)
        return None
    return sanity_check(CDSExtract(**counts.model_dump(), **tests.model_dump(), c7=c7, extraction_notes=[]))


async def load_cds() -> None:
    sources = yaml.safe_load((DATA_DIR / "cds_sources.yaml").read_text())
    sb = await supabase()
    async with zetaris_paused(), httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
        for src in sources:
            slug, url = src["slug"], src["cds_url"]
            pdf = (await http.get(url)).raise_for_status().content
            extract = await extract_cds(pdf, slug)
            if extract is None:
                continue
            upd = to_update(extract, url)
            row = await sb.table("universities_cds").select("source_urls").eq("slug", slug).single().execute()
            current = row.data
            upd["source_urls"] = (current.get("source_urls") or {}) | upd["source_urls"]
            await sb.table("universities_cds").update(upd).eq("slug", slug).execute()
            log.info("%s: CDS %s, C7 factors=%d", slug, extract.cds_year, len(upd.get("c7_weights", {})))
