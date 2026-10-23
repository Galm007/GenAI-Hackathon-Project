from etl.common import append_jsonl, read_jsonl
from etl.pullpush import KEEP_FIELDS, MIN_INTERVAL_S, keep


def test_keep_filters_short_removed_and_stickied():
    long_text = "x" * 500
    assert keep({"selftext": long_text})
    assert not keep({"selftext": "short"})
    assert not keep({"selftext": "[removed]"})
    assert not keep({"selftext": long_text, "stickied": True})
    assert not keep({"selftext": long_text, "removed_by_category": "moderator"})


def test_no_author_field_is_kept():
    assert "author" not in KEEP_FIELDS
    assert MIN_INTERVAL_S >= 4.0


def test_jsonl_roundtrip(tmp_path):
    path = tmp_path / "a.jsonl"
    append_jsonl(path, [{"id": "1"}, {"id": "2"}])
    assert [r["id"] for r in read_jsonl(path)] == ["1", "2"]
    assert list(read_jsonl(tmp_path / "missing.jsonl")) == []
