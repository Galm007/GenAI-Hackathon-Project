from __future__ import annotations

import pytest

from scripts import backtest as bt


def ex(i: int, y: int, slug: str = "uiuc", gpa: float | None = 3.9, sat: int | None = 1500) -> bt.Example:
    return bt.Example(twin_id=f"t{i}", slug=slug, y=y, posted=f"2026-01-{i + 1:02d}", gpa=gpa, sat=sat)


def test_brier_and_auc_known_values():
    assert bt.brier([0.5, 0.5], [1, 0]) == pytest.approx(0.25)
    assert bt.auc([0.1, 0.4, 0.35, 0.8], [0, 0, 1, 1]) == pytest.approx(0.75)
    assert bt.auc([0.3, 0.3, 0.3, 0.3], [0, 1, 0, 1]) == pytest.approx(0.5)      # ties count half
    assert bt.auc([0.2, 0.9], [1, 1]) is None


def test_within_school_auc_ignores_between_school_level():
    rows = [ex(i, y, slug=s) for s, off in (("a", 0), ("b", 10)) for i, y in enumerate([0, 1, 0, 1], off)]
    # constant per school → 0.5 within school even though the schools differ, perfect ranking → 1.0
    flat = [bt.Example(**{**r.__dict__, "p_base": 0.9 if r.slug == "a" else 0.1}) for r in rows]
    ranked = [bt.Example(**{**r.__dict__, "p_base": 0.2 + 0.5 * r.y}) for r in rows]
    assert bt.within_school_auc(flat, "p_base", min_n=4) == pytest.approx(0.5)
    assert bt.within_school_auc(ranked, "p_base", min_n=4) == pytest.approx(1.0)


def test_reliability_bins_are_equal_count_and_ordered():
    ps = [i / 20 for i in range(20)]
    bins = bt.reliability(ps, [i % 2 for i in range(20)], bins=5)
    assert [b["n"] for b in bins] == [4] * 5
    assert [b["mean_pred"] for b in bins] == sorted(b["mean_pred"] for b in bins)


def test_split_holds_out_the_latest_posts_only():
    rows = [ex(i, i % 2) for i in range(10)]
    train, test = bt.split(rows[::-1])
    assert len(test) == 3 and max(e.posted for e in train) < min(e.posted for e in test)


def test_twin_sums_use_nearest_neighbours_and_deflate_inflation():
    target = ex(0, 1)
    train = [ex(i, 1 if i % 2 else 0, gpa=3.9 - 0.01 * i) for i in range(1, 30)]
    sw, sw2, swa = bt.twin_sums(target, train)
    assert 0 < swa < sw and sw2 <= sw
    assert bt.reddit_inflation(train[:5], 0.2) == 1.0                    # too few rows → no correction
    assert bt.reddit_inflation(train, 0.1) > 1.0                         # ~50% Reddit rate vs 10% official


def test_scoring_inputs_never_use_the_stored_major_multiplier_or_race():
    school = {"slug": "uiuc", "name": "UIUC", "admit_rate": 0.42, "control": "public", "state": "IL",
              "c7_weights": {}, "test_policy": "optional",
              "major_competitiveness": {"cs": {"multiplier": 0.3, "source": "reddit_smoothed"}}}
    twin = {"major_category": "cs", "gpa_uw": 3.95, "sat_score": 1540, "ap_count": 9, "hooks": ["first_gen"],
            "demographics": {"residency_state": "IL", "race_ethnicity_raw": "x", "income_bracket": "<30k"},
            "ec_tier_summary": {"tier2": 1, "tier3": 2}}
    x = bt.scoring_inputs(twin, {"round": "RD"}, school)
    assert x.major_multiplier == 1.0 and x.base_admit_rate == 0.42
    assert x.ratings["personal"] == 3.5 and "first_gen" in x.hooks
    assert x.ratings["academic"] < 3.0 < x.ratings["extracurricular"] + 1.5
