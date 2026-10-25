from __future__ import annotations

import io
import re
from typing import Literal

import httpx
import openpyxl
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

# The official Excel CDS template (UIUC, Berkeley publish this instead of a PDF): one sheet per lettered section,
# column A holds the item code, B the question, C onward the answers.
XLSX_SECTION_CODES = {
    "counts": re.compile(r"^(C11[789]|C2[12]\d\d|D[12]\d\d)$"),         # C1 totals only; skip the per-gender rows
    "tests": re.compile(r"^(C8\w*|C9\d\d|C11\d\d|C12\d\d)$"),
    "c7": re.compile(r"^C7\d\d$"),
}
# C701..C718 in the template's order = the C7Factors field order.
C7_KEYS = list(C7Factors.model_fields)
C7_LEVELS: dict[str, C7Level] = {"very important": "very_important", "important": "important",
                                 "considered": "considered", "not considered": "not_considered"}
XLSX_CELL_CHARS = 90
# C802 ("SAT or ACT") answers → CDSTests.test_policy
TEST_POLICY_BY_C802 = {
    "required to be considered for admission": "required", "required for some": "required",
    "recommended": "optional", "not required for admission, but considered if submitted": "optional",
    "not considered for admission, even if submitted": "blind",
}


def is_xlsx(data: bytes) -> bool:
    return data[:2] == b"PK"                      # an .xlsx is a zip; a PDF starts with %PDF


def download_url(url: str) -> str:
    """A Google Sheets share link becomes its .xlsx export; every other URL is fetched as is."""
    m = re.match(r"https://docs\.google\.com/spreadsheets/d/([\w-]+)", url)
    return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=xlsx" if m else url


def _cell(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return " ".join(str(v).split())[:XLSX_CELL_CHARS]


def _xlsx_rows(data: bytes) -> list[list[str]]:
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    rows = []
    for ws in wb.worksheets:
        if ws.title.startswith(("CDS Definitions", "Answer")):
            continue
        rows += [[_cell(c) for c in r] for r in ws.iter_rows(values_only=True)]
    return rows


def xlsx_section_texts(data: bytes) -> dict[str, str]:
    """Rows of each section as `code | question | answers`, with the uncoded header row above a hit for context."""
    rows = _xlsx_rows(data)
    out: dict[str, str] = {}
    for name, pattern in XLSX_SECTION_CODES.items():
        lines: list[str] = []
        header = ""
        for r in rows:
            cells = [c for c in r if c]
            if r and pattern.match(r[0]):
                if header:
                    lines.append(header)
                    header = ""
                if len(cells) > 2:                          # drop template rows nobody filled in
                    lines.append(" | ".join(cells))
            elif cells and not re.match(r"^[A-Z]\d", r[0] or ""):
                header = " | ".join(cells)
        out[name] = "\n".join(lines)[:MAX_SECTION_CHARS]
    return out


C7_ROW_LABELS = {"rigor": ("rigor",), "class_rank": ("class rank",),
                 "academic_gpa": ("academic gpa", "grade point average"), "test_scores": ("standardized test",),
                 "essay": ("essay",), "recommendations": ("recommendation",), "interview": ("interview",),
                 "extracurriculars": ("extracurricul",), "talent_ability": ("talent",),
                 "character": ("character",), "first_generation": ("first generation", "first-generation"),
                 "alumni_relation": ("alumni",), "geographic_residence": ("geographic",),
                 "state_residency": ("state residency",), "religious_affiliation": ("religious",),
                 "volunteer_work": ("volunteer",), "work_experience": ("work experience",),
                 "applicant_interest": ("interest",)}
C7_HEADERS = (("very important", "very_important"), ("important", "important"),
              ("considered", "considered"), ("not considered", "not_considered"))
C7_LEVEL_AT_END = re.compile(r"(very important|not considered|important|considered)\s*$", re.IGNORECASE)
MIN_PDF_C7_ROWS = 14                  # fewer parsed rows than this = unusual layout; ask the model instead


def pdf_c7(layout_text: str) -> C7Factors | None:
    """Read C7 without a model: either the column each X sits in (layout text keeps the page's columns) or the
    level printed at the end of the row (form-field PDFs). None if too few rows parse; the model takes over."""
    levels: dict[str, C7Level | None] = dict.fromkeys(C7_KEYS)
    cols: list[tuple[float, C7Level]] = []

    def row_key(text: str) -> str | None:
        return next((k for k, labels in C7_ROW_LABELS.items() if any(lb in text for lb in labels)), None)

    for line in layout_text.splitlines():
        low = line.lower()
        if "very important" in low and "not considered" in low:                 # header row: where each column sits
            cols = []
            for phrase, level in C7_HEADERS:
                pattern = rf"(?<!not )(?<!very ){phrase}" if phrase in ("important", "considered") else phrase
                if at := re.search(pattern, low):
                    cols.append((at.start() + len(phrase) / 2, level))
            continue
        marks = [m.start() for m in re.finditer(r"\bX\b", line, re.IGNORECASE)]
        if len(cols) == 4 and len(marks) == 1:
            key, level = row_key(low[:marks[0]]), min(cols, key=lambda c: abs(c[0] - marks[0]))[1]
        elif (end := C7_LEVEL_AT_END.search(line)) and not marks:
            key, level = row_key(low[:end.start()]), C7_LEVELS[end.group(1).lower()]
        else:
            continue
        if key and levels[key] is None:
            levels[key] = level
    return C7Factors(**levels) if sum(v is not None for v in levels.values()) >= MIN_PDF_C7_ROWS else None


def pdf_c1_totals(text: str) -> tuple[int, int, int] | None:
    """First-year applied/admitted/enrolled totals, read from the first unsplit C1 rows. The total is the largest
    number on its row in every layout seen (total first, total last, or a single column); a model took a men-only
    figure for Georgia Tech. None unless all three rows are found and admits <= applicants."""
    found: dict[str, int] = {}
    for line in text.splitlines():
        low = line.lower()
        if "first-time" not in low or any(w in low for w in ("men", "women", "gender", "part-time", "transfer")):
            continue
        kind = next((k for k in ("applied", "admitted", "enrolled") if k in low), None)
        nums = [int(n.replace(",", "")) for n in re.findall(r"\b\d{1,3}(?:,\d{3})+\b|\b\d+\b", line.split(":")[-1])]
        if kind and nums and kind not in found:
            found[kind] = max(nums)
    if len(found) == 3 and found["admitted"] <= found["applied"] and found["enrolled"] <= found["admitted"]:
        return found["applied"], found["admitted"], found["enrolled"]
    return None


PERCENTILE_FIELDS = {"SAT Composite": "sat_composite", "SAT Evidence-Based Reading and Writing": "sat_ebrw",
                     "SAT Math": "sat_math", "ACT Composite": "act_composite"}
PERCENTILE_COLUMNS = {"25": "_25", "50": "_50", "75": "_75"}
XLSX_TEST_FIELDS = [f + c for f in PERCENTILE_FIELDS.values() for c in PERCENTILE_COLUMNS.values()
                    if f + c in CDSTests.model_fields] + ["pct_submitting_sat", "pct_submitting_act",
                                                          "pct_top10_class", "avg_hs_gpa"]


def _number(v: str) -> float | None:
    try:
        return float(v.replace(",", "").rstrip("%"))
    except ValueError:
        return None


def xlsx_tests(data: bytes) -> dict[str, float | None]:
    """C9 percentiles and submission rates, C10 top-tenth and C12 GPA, read by row label. Blank or 0 means the school
    did not report it, so the field is None (not whatever a model guessed)."""
    out: dict[str, float | None] = {}
    for r in _xlsx_rows(data):
        if len(r) < 3 or not re.match(r"^C(9|10|12)\d*", r[0]):
            continue
        label, value = r[1], _number(r[2]) or None                           # 0 and blank both mean "not reported"
        if m := re.match(r"^(.+): (25|50|75)th Percentile$", label):
            if field := PERCENTILE_FIELDS.get(m.group(1)):
                out.setdefault(field + PERCENTILE_COLUMNS[m.group(2)], value)
        elif label in ("Submitting SAT Scores", "Submitting ACT Scores") and value is not None and value <= 1:
            out.setdefault("pct_submitting_" + label.split()[1].lower(), value)
        elif label.startswith("Percent in top tenth"):
            out.setdefault("pct_top10_class", value)
        elif label.startswith("Average high school GPA"):
            out.setdefault("avg_hs_gpa", value)
    return out


def pdf_percentiles(text: str) -> dict[str, int]:
    """C9 percentile rows: `SAT Composite   1510   1540   1560` (25th / 50th / 75th). First table in the text wins."""
    out: dict[str, int] = {}
    for line in text.splitlines():
        for label, field in PERCENTILE_FIELDS.items():
            row = rf"^\s*{re.escape(label)}(?:\s*\([^)]*\))?" + r"\s+(\d{2,4})\s+(\d{2,4})\s+(\d{2,4})\s*$"
            m = re.match(row, line, re.IGNORECASE)
            if m and field + "_25" not in out:
                out.update(zip((field + c for c in PERCENTILE_COLUMNS.values()), map(int, m.groups()), strict=True))
    return out


def xlsx_test_policy(data: bytes) -> str | None:
    """C802 is a fixed list of answers, so read it directly; None when the sheet leaves it blank."""
    for r in _xlsx_rows(data):
        if r and r[0] == "C802":
            return TEST_POLICY_BY_C802.get(r[2].lower() if len(r) > 2 else "")
    return None


def xlsx_c7(data: bytes) -> C7Factors:
    """C7 is a column of answers keyed by item code, so read it directly instead of asking a model."""
    levels: dict[str, C7Level | None] = dict.fromkeys(C7_KEYS)
    for r in _xlsx_rows(data):
        m = re.fullmatch(r"C7(\d\d)", r[0]) if r else None
        if m and 1 <= int(m.group(1)) <= len(C7_KEYS):
            levels[C7_KEYS[int(m.group(1)) - 1]] = C7_LEVELS.get(r[2].lower() if len(r) > 2 else "")
    return C7Factors(**levels)


def section_texts(pdf: bytes) -> dict[str, str]:
    """Layout-preserving text of the pages that mention each section (+ the next page for grids that spill over)."""
    if is_xlsx(pdf):
        return xlsx_section_texts(pdf)
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
    """Counts and tests via the local model; C7 is parsed from the grid (model only if it will not parse)."""
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
        c7 = xlsx_c7(pdf) if is_xlsx(pdf) else pdf_c7(texts["c7"])
        if c7 is None:
            c7 = await chat_structured(C7Factors, C7_SYSTEM, ask.format(texts["c7"]), **kw)
    except (LocalLLMError, ValidationError, httpx.HTTPError) as exc:
        log.warning("%s: CDS extraction failed (%s: %s)", slug, type(exc).__name__, exc)
        return None
    if not is_xlsx(pdf) and (totals := pdf_c1_totals(texts["counts"])):
        counts.applicants_total, counts.admits_total, counts.enrolled_total = totals
    if is_xlsx(pdf):
        found = xlsx_tests(pdf)
        for field in XLSX_TEST_FIELDS:                      # a missing row is "not reported", not a guess
            value = found.get(field)
            setattr(tests, field, int(value) if value is not None and field.startswith(("sat_", "act_")) else value)
    else:
        for field, value in pdf_percentiles(texts["tests"]).items():
            if field in CDSTests.model_fields:
                setattr(tests, field, value)
    if is_xlsx(pdf) and (policy := xlsx_test_policy(pdf)):
        tests.test_policy = policy                     # type: ignore[assignment]
    return sanity_check(CDSExtract(**counts.model_dump(), **tests.model_dump(), c7=c7, extraction_notes=[]))


async def load_cds() -> None:
    sources = yaml.safe_load((DATA_DIR / "cds_sources.yaml").read_text())
    sb = await supabase()
    async with zetaris_paused(), httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
        for src in sources:
            slug, url = src["slug"], src["cds_url"]
            pdf = (await http.get(download_url(url))).raise_for_status().content
            extract = await extract_cds(pdf, slug)
            if extract is None:
                continue
            extract.cds_year = extract.cds_year or src.get("cds_year")      # a spreadsheet does not print its year
            upd = to_update(extract, url)
            if is_xlsx(pdf):                                    # the sheet is authoritative: clear what it leaves blank
                upd |= {f: None for f in XLSX_TEST_FIELDS if f not in upd}
            upd |= src.get("overrides") or {}                   # hand-curated, see the yaml
            row = await sb.table("universities_cds").select("source_urls").eq("slug", slug).single().execute()
            current = row.data
            upd["source_urls"] = (current.get("source_urls") or {}) | upd["source_urls"]
            await sb.table("universities_cds").update(upd).eq("slug", slug).execute()
            log.info("%s: CDS %s, C7 factors=%d", slug, extract.cds_year, len(upd.get("c7_weights", {})))
