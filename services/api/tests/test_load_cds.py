import re
from pathlib import Path
from typing import get_args

from etl import load_cds
from etl.load_cds import (
    C7Factors,
    C7Level,
    CDSCounts,
    CDSExtract,
    CDSTests,
    EarlyPlans,
    GPABucket,
    TransferProfile,
    extract_cds,
    sanity_check,
    section_texts,
    to_update,
)

MIGRATION = Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "0001_extensions_types.sql"


def make_pdf(pages: list[list[tuple[int, int, str]]]) -> bytes:
    """Minimal PDF with a text layer: each page is a list of (x, y, text) runs in Helvetica 10."""
    objs: list[bytes] = []
    n_pages = len(pages)
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(n_pages))
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode())
    for i, runs in enumerate(pages):
        content = "BT /F1 10 Tf " + " ".join(f"1 0 0 1 {x} {y} Tm ({t}) Tj" for x, y, t in runs) + " ET"
        font = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {4 + 2 * i} 0 R "
                    f"/Resources << /Font << /F1 {font} >> >> >>".encode())
        objs.append(f"<< /Length {len(content)} >>\nstream\n{content}\nendstream".encode())
    out = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


CDS_PDF = make_pdf([
    [(72, 700, "General information and cover page")],
    [(72, 700, "C1 Applications"), (72, 680, "Total first-time applicants 50000")],
    [(72, 700, "Spillover page for C1")],
    [(72, 700, "C7 Relative importance"), (72, 680, "Factor"), (250, 680, "Very Important"), (400, 680, "Important"),
     (72, 660, "Rigor of secondary school record"), (260, 660, "X"), (72, 640, "Essay"), (410, 640, "X")],
    [(72, 700, "C9 SAT percentiles"), (72, 680, "C12 Average GPA 3.9")],
    [(72, 700, "Footer page")],
])


def test_section_texts_pick_marker_pages_and_next_page():
    t = section_texts(CDS_PDF)
    assert "Total first-time applicants 50000" in t["counts"] and "Spillover page" in t["counts"]
    assert "Rigor of secondary school record" in t["c7"] and "Average GPA" not in t["c7"].split("C9")[0]
    assert "C9 SAT percentiles" in t["tests"]


def test_layout_text_keeps_mark_columns_apart():
    c7 = section_texts(CDS_PDF)["c7"]
    rigor = next(line for line in c7.splitlines() if "Rigor" in line)
    essay = next(line for line in c7.splitlines() if "Essay" in line)
    assert rigor.index("X") < essay.index("X")             # "Very Important" column is left of "Important"


def mk_counts(**over):
    base = dict(cds_year="2024-2025", applicants_total=50000, admits_total=20000, enrolled_total=7000,
                ed_applicants=None, ed_admits=None, early_plans=EarlyPlans(ed=None, ed2=None, ea=True, rea=None),
                transfer=TransferProfile(accepts_transfers=True, applicants=None, admits=None, enrolled=None,
                                         min_college_gpa=None))
    return CDSCounts(**(base | over))


def mk_tests(**over):
    base = dict(test_policy="optional", sat_composite_25=1340, sat_composite_50=1430, sat_composite_75=1520,
                sat_ebrw_25=650, sat_ebrw_75=740, sat_math_25=690, sat_math_75=790, act_composite_25=30,
                act_composite_75=34, pct_submitting_sat=0.55, pct_submitting_act=0.30,
                gpa_distribution=[GPABucket(bucket="3.75-3.99", pct=0.5)], avg_hs_gpa=3.9, pct_top10_class=0.8)
    return CDSTests(**(base | over))


def mk_c7(**over):
    keys = list(C7Factors.model_fields)
    base = dict.fromkeys(keys)
    return C7Factors(**(base | {"rigor": "very_important", "essay": "important"} | over))


def extract(c=None, t=None, k=None):
    both = {**(c or mk_counts()).model_dump(), **(t or mk_tests()).model_dump()}
    return CDSExtract(**both, c7=k or mk_c7(), extraction_notes=[])


def test_sanity_check_keeps_good_data():
    x = sanity_check(extract())
    assert x.admits_total == 20000 and x.sat_composite_75 == 1520 and x.extraction_notes == []


def test_sanity_check_drops_impossible_values():
    x = sanity_check(extract(
        mk_counts(applicants_total=100, admits_total=900, enrolled_total=50),
        mk_tests(sat_composite_25=1500, sat_composite_75=1300, act_composite_75=40, pct_submitting_sat=63,
              pct_top10_class=-1, avg_hs_gpa=39.0, gpa_distribution=[GPABucket(bucket="4.0", pct=7000)]),
    ))
    assert x.applicants_total is None and x.admits_total is None
    assert x.sat_composite_25 is None and x.sat_composite_75 is None
    assert x.act_composite_25 is None and x.act_composite_75 is None
    assert x.pct_submitting_sat == 0.63 and x.pct_top10_class is None
    assert x.avg_hs_gpa is None and x.gpa_distribution == []
    assert len(x.extraction_notes) >= 5


def test_to_update_skips_nulls_and_keeps_c7():
    upd = to_update(sanity_check(extract(t=mk_tests(sat_composite_50=None))), "http://cds.pdf")
    assert upd["admit_rate"] == 0.4 and upd["c7_weights"] == {"rigor": "very_important", "essay": "important"}
    assert "sat_composite_50" not in upd and upd["source_urls"] == {"cds": "http://cds.pdf"}
    assert upd["data_quality"]["extractor"] == load_cds.settings.cds_model


async def test_extract_cds_makes_three_calls_and_assembles(monkeypatch):
    seen = []

    async def fake_chat(model_cls, system, user, **kw):
        seen.append((model_cls, kw["model"]))
        return {CDSCounts: mk_counts(), CDSTests: mk_tests(), C7Factors: mk_c7()}[model_cls]

    monkeypatch.setattr(load_cds, "chat_structured", fake_chat)
    x = await extract_cds(CDS_PDF, "uiuc")
    assert [m for m, _ in seen] == [CDSCounts, CDSTests, C7Factors]
    assert x is not None and x.c7.rigor == "very_important" and x.admits_total == 20000


async def test_pdf_without_text_layer_is_skipped(monkeypatch):
    async def boom(*a, **k):
        raise AssertionError("model must not be called")

    monkeypatch.setattr(load_cds, "chat_structured", boom)
    assert await extract_cds(make_pdf([[]]), "uiuc") is None


def test_c7_levels_match_the_database_enum():
    enum = re.search(r"c7_level\s+as enum \(([^)]*)\)", MIGRATION.read_text()).group(1)
    assert set(get_args(C7Level)) == set(re.findall(r"'(\w+)'", enum))
