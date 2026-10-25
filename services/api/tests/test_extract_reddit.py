from __future__ import annotations

from etl.extract_reddit import _state_code, select_posts, to_row
from etl.reddit_schema import Demographics, ExtractedActivity, RedditApplicantRecord, SchoolDecision
from etl.school_resolver import SchoolResolver

POST = {"id": "abc123", "subreddit": "collegeresults", "permalink": "/r/collegeresults/comments/abc123/x/",
        "created_utc": 1773000000, "title": "t", "selftext": "accepted", "link_flair_text": None}   # 2026-03


def resolver() -> SchoolResolver:
    return SchoolResolver({"umich": "umich", "university of michigan": "umich", "cmu": "cmu", "mit": "mit"})


def record(**kw) -> RedditApplicantRecord:
    base = dict(
        is_results_post=True, applicant_type="first_year", matriculation_year=None,
        gpa_uw=3.9, gpa_w=None, gpa_w_scale=None, college_gpa=None, class_rank_pct=None,
        sat_total=1520, sat_math=780, sat_ebrw=740, act_composite=None, applied_test_optional=False,
        ap_count=8, honors_count=3, dual_enrollment_count=None, ib_diploma=None, rigor_label="very_demanding",
        intended_major_raw="CS", major_category="computer_science",
        demographics=Demographics(gender=None, race_ethnicity_raw=None, residency_state="MI", country=None,
                                  income_bracket="unknown", school_type="public", first_gen=None),
        hooks=[], activities=[ExtractedActivity(description="Founded a robotics club", role="Founder", tier=3)],
        awards=[], spike_summary="robotics",
        decisions=[SchoolDecision(school_as_written="UMich", outcome="accepted", round="RD")],
        extraction_confidence="high", extraction_issues=[],
    )
    return RedditApplicantRecord(**{**base, **kw})


def test_good_record_becomes_row_with_resolved_schools():
    row, reason = to_row(POST, record(decisions=[
        SchoolDecision(school_as_written="UMich", outcome="rejected", round="EA"),
        SchoolDecision(school_as_written="University of Michigan", outcome="accepted", round="RD"),
        SchoolDecision(school_as_written="CMU SCS", outcome="waitlisted", round="RD"),
    ]), resolver())
    assert reason is None and row is not None
    assert row["accepted_schools"] == ["umich"]        # duplicate keeps the strongest outcome
    assert row["waitlisted_schools"] == ["cmu"] and row["rejected_schools"] == []
    assert row["cycle_year"] == 2026 and row["sat_score"] == 1520
    assert "Applicant type: first-year" in row["profile_text"]


def test_quality_gates_reject_with_reasons():
    assert to_row(POST, record(is_results_post=False), resolver())[1] == "not_results_post"
    unknown = [SchoolDecision(school_as_written="Hogwarts", outcome="accepted", round="RD")]
    assert to_row(POST, record(decisions=unknown), resolver())[1] == "no_resolved_school"
    low = record(extraction_confidence="low", gpa_uw=None, sat_total=None)
    assert to_row(POST, low, resolver())[1] == "low_signal"


def test_number_cleaning_moves_weighted_gpa_and_nulls_bad_scores():
    row, _ = to_row(POST, record(gpa_uw=4.5, sat_total=2100, act_composite=40, class_rank_pct=5), resolver())
    assert row["gpa_uw"] is None and row["gpa_w"] == 4.5
    assert row["sat_score"] is None and row["act_score"] is None and row["class_rank_pct"] is None
    assert any("moved to gpa_w" in i for i in row["extraction_issues"])


def test_select_posts_skips_posts_without_decisions_and_done_ids(tmp_path, monkeypatch):
    import etl.extract_reddit as mod

    (tmp_path / "collegeresults.jsonl").write_text(
        '{"id":"a","selftext":"I got accepted","created_utc":2}\n'
        '{"id":"b","selftext":"chance me pls","created_utc":3}\n'
        '{"id":"c","selftext":"waitlisted","created_utc":1}\n')
    monkeypatch.setattr(mod, "RAW_DIR", tmp_path)
    assert [p["id"] for p in select_posts(set(), None)] == ["a", "c"]
    assert [p["id"] for p in select_posts({"a"}, None)] == ["c"]
    assert [p["id"] for p in select_posts(set(), 1)] == ["a"]


def test_applicant_type_comes_from_subreddit_not_the_model():
    row, _ = to_row(POST, record(applicant_type="transfer"), resolver())
    assert row["applicant_type"] == "first_year"
    row, _ = to_row(POST | {"subreddit": "TransferToTop25"}, record(applicant_type="first_year"), resolver())
    assert row["applicant_type"] == "transfer" and "Applicant type: transfer" in row["profile_text"]


def test_residency_state_is_normalized_or_dropped():
    assert [_state_code(v) for v in ("MI", "mi", "Michigan", "New York", "Northeast", "bay area", None, "")] == [
        "MI", "MI", "MI", "NY", None, None, None, None]
    demo = record().demographics.model_copy(update={"residency_state": "Northeast"})
    row, _ = to_row(POST, record(demographics=demo), resolver())
    assert row["demographics"]["residency_state"] is None
