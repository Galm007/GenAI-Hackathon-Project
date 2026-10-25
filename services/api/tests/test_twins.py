"""Node 3 (§3.7.3) and the radar (§4.7), with the twin RPCs, Zetaris reads and llm.parse mocked."""
import anthropic
import httpx
import pytest

from app.agents.nodes import twins as N
from app.agents.prompts.twins import TWIN_ANALYST_SYSTEM
from app.schemas.dossier import ComputedMetrics, DossierGrade
from app.schemas.twins import TwinAnalysis, TwinComparison
from app.scoring.probability import from_odds, odds
from app.scoring.radar import AXES, POOL_PERSONAL, build_radar

from . import test_debate as T


def row(i: int, outcome: str = "accepted", score: float | None = None, **kw) -> dict:
    return {"id": f"00000000-0000-4000-8000-{i:012d}", "source_url": f"https://reddit.com/r/x/{i}", "cycle_year": 2025,
            "matched_school": "uiuc", "outcome": outcome, "gpa_uw": 3.9, "sat_score": 1500, "ap_count": 9,
            "major_category": "computer_science", "semantic_similarity": 0.8, "stat_proximity": 0.7,
            "hybrid_score": score if score is not None else 1 - i / 100, **kw}


def outcomes(rows: list[dict]) -> list[str]:
    return [r["outcome"] for r in rows]


# ---------- select_contrastive ----------
def test_top_k_kept_when_it_already_has_both_outcomes():
    pool = [row(1), row(2, "rejected"), row(3), row(4), row(5), row(6, "rejected")]
    assert [r["id"] for r in N.select_contrastive(pool)] == [r["id"] for r in pool[:5]]


def test_all_admits_swaps_the_weakest_majority_member_for_the_best_reject():
    pool = [row(i) for i in range(1, 6)] + [row(6, "waitlisted"), row(7, "rejected"), row(8, "rejected")]
    out = N.select_contrastive(pool)
    assert len(out) == 5 and outcomes(out).count("rejected") == 1
    assert {r["id"] for r in out} == {row(i)["id"] for i in (1, 2, 3, 4, 7)}             # row 5 was the victim
    assert [r["hybrid_score"] for r in out] == sorted((r["hybrid_score"] for r in out), reverse=True)


def test_all_rejects_gets_an_admit():
    pool = [row(i, "rejected") for i in range(1, 6)] + [row(6, "accepted")]
    out = N.select_contrastive(pool)
    assert outcomes(out).count("accepted") == 1 and row(5)["id"] not in {r["id"] for r in out}


def test_waitlists_only_get_both_an_admit_and_a_reject():
    pool = [row(i, "waitlisted") for i in range(1, 6)] + [row(6, "rejected"), row(7, "accepted")]
    out = N.select_contrastive(pool)
    assert sorted(outcomes(out)) == ["accepted", "rejected", "waitlisted", "waitlisted", "waitlisted"]


def test_victim_never_removes_the_only_admit_it_just_added():
    pool = [row(i, "waitlisted") for i in range(1, 5)] + [row(5, "accepted"), row(6, "rejected")]
    out = N.select_contrastive(pool)
    assert sorted(outcomes(out)) == ["accepted", "rejected", "waitlisted", "waitlisted", "waitlisted"]


@pytest.mark.parametrize("pool", [[], [row(1)], [row(i) for i in range(1, 8)]], ids=["empty", "one", "no_rejects"])
def test_short_or_one_sided_pools_return_what_exists(pool):
    out = N.select_contrastive(pool)
    assert out == pool[:5] and len(out) == min(len(pool), 5)


# ---------- compute_baseline ----------
STATS = {"n": 50, "n_accepted": 14, "n_waitlisted": 4, "n_rejected": 32, "weighted_admit_rate": 0.36,
         "sum_w": 33.1, "sum_w2": 34.8, "sum_w_admit": 11.9}


def test_baseline_effective_n_wilson_band_and_deflation():
    b = N.compute_baseline(STATS, 2.4, False, [])
    assert b.n_effective == round(33.1**2 / 34.8, 2) and (b.n_neighbors, b.n_accepted, b.n_rejected) == (50, 14, 32)
    assert b.wilson_low < 0.36 < b.wilson_high and (b.wilson_low, b.wilson_high) == N.wilson(0.36, 33.1**2 / 34.8)
    assert b.deflated_admit_rate == pytest.approx(from_odds(odds(0.36) / 2.4)) and b.deflated_admit_rate < 0.36
    assert (b.sum_w, b.sum_w2, b.sum_w_admit, b.odds_inflation) == (33.1, 34.8, 11.9, 2.4)


def test_wilson_matches_the_closed_form():
    lo, hi = N.wilson(0.5, 100)
    assert (lo, hi) == pytest.approx((0.4364, 0.5636), abs=1e-4)                          # z = 1.2816
    assert N.wilson(0.0, 10)[0] == pytest.approx(0.0, abs=1e-12) and N.wilson(1.0, 10)[1] == pytest.approx(1.0)


def test_baseline_with_an_empty_neighborhood():
    b = N.compute_baseline({}, 1.0, True, ["purdue"])
    assert (b.n_neighbors, b.n_effective, b.weighted_admit_rate, b.wilson_low, b.deflated_admit_rate) == (
        0, 0.0, None, None, None)
    assert b.widened_to_peers and b.peer_schools == ["purdue"] and b.sum_w == 0.0


def test_baseline_skips_the_band_below_one_effective_neighbor_and_clamps_extreme_rates():
    b = N.compute_baseline({"n": 1, "weighted_admit_rate": 1.0, "sum_w": 0.5, "sum_w2": 0.5}, 2.0, False, [])
    assert b.n_effective == 0.5 and (b.wilson_low, b.wilson_high) == (None, None)
    assert b.deflated_admit_rate == pytest.approx(from_odds(odds(0.99) / 2.0))           # 1.0 clamped to 0.99


def test_baseline_tolerates_null_sums_from_the_rpc():
    b = N.compute_baseline({"n": 3, "weighted_admit_rate": None, "sum_w": None, "sum_w2": None}, 1.0, False, [])
    assert (b.sum_w, b.n_effective, b.wilson_low) == (0.0, 0.0, None)


# ---------- radar ----------
def metrics() -> ComputedMetrics:
    return ComputedMetrics.model_validate(T.fixture("ComputedMetrics"))


def grade() -> DossierGrade:
    return DossierGrade.model_validate(T.fixture("DossierGrade"))


def test_radar_reproduces_the_contract_fixture():
    expected = T.fixture("RadarData")
    keys = ("gpa_uw", "sat", "advanced", "ec_rating", "spike_points")
    raw = [a["admitted_raw"] for a in expected["axes"][:len(keys)]]
    medians = {"n": expected["n_admitted"], **dict(zip(keys, raw, strict=True))}
    assert build_radar(metrics(), grade(), medians) == expected


def test_radar_normalizes_clamps_and_marks_personal_assumed():
    r = build_radar(metrics(), grade(), {"n": 0})
    assert r["n_admitted"] == 0 and [a["key"] for a in r["axes"]] == [k for k, *_ in AXES]
    by = {a["key"]: a for a in r["axes"]}
    assert all(a["admitted_median"] is None for k, a in by.items() if k != "personal")   # no medians → no ring
    assert by["personal"]["assumed"] and by["personal"]["admitted_raw"] == POOL_PERSONAL
    assert by["personal"]["admitted_median"] == 60.0                                    # 3.0 on a 6→1 scale
    assert not any(a["assumed"] for k, a in by.items() if k != "personal")

    from app.scoring.radar import _norm
    assert (_norm(4.3, 3.5, 4.0), _norm(3.0, 3.5, 4.0), _norm(1.0, 5.5, 1.0)) == (100.0, 0.0, 100.0)


def test_radar_spike_points_count_tier_one_double():
    g = grade()
    tiers = [ag.tier for ag in g.activity_grades]
    spike = next(a for a in build_radar(metrics(), g, {})["axes"] if a["key"] == "spike")
    assert spike["you_raw"] == 2 * tiers.count(1) + tiers.count(2)


# ---------- the node ----------
POOL = [row(i) for i in range(1, 6)] + [row(6, "rejected")]
MEDIANS = {"n": 40, "gpa_uw": 3.93, "sat": 1515.0, "advanced": 11.5, "ec_rating": 2.4, "spike_points": 1.0}


@pytest.fixture
def node(monkeypatch):
    calls: dict[str, list] = {"match": [], "stats": [], "peers": [], "parse": []}
    events: list[tuple[str, dict]] = []

    def install(*pools, analysis=None, parse_error=None):
        pools = iter(pools)

        async def match_twins(emb, schools, **kw):
            calls["match"].append((schools, kw))
            return next(pools)

        async def neighborhood_stats(emb, schools, **kw):
            calls["stats"].append((schools, kw))
            return STATS

        async def school_profile(slug):
            return {"slug": slug, "peer_group": "big_ten_public"}

        async def peer_schools(slug, group):
            calls["peers"].append((slug, group))
            return ["purdue", "umich"]

        async def calibration(slug):
            return 2.4

        async def medians(slug):
            return MEDIANS

        async def parse(schema, **kw):
            calls["parse"].append({"schema": schema, **kw})
            if parse_error:
                raise parse_error
            return analysis

        monkeypatch.setattr(N.db, "match_twins", match_twins)
        monkeypatch.setattr(N.db, "neighborhood_stats", neighborhood_stats)
        monkeypatch.setattr(N.zetaris_repo, "school_profile", school_profile)
        monkeypatch.setattr(N.zetaris_repo, "peer_schools", peer_schools)
        monkeypatch.setattr(N.zetaris_repo, "reddit_calibration", calibration)
        monkeypatch.setattr(N.zetaris_repo, "admitted_medians", medians)
        monkeypatch.setattr(N.llm, "parse", parse)
        monkeypatch.setattr(N, "emit", lambda event, **d: events.append((event, d)))
        monkeypatch.setattr(N, "tool_call", lambda node, tool, status, **d: events.append(("tool_call", {
            "tool": tool, "status": status, **d})))
        return calls, events
    return install


def node_state() -> dict:
    s = T.base_state(profile_embedding=[0.0] * 768)
    return {k: s[k] for k in ("school_slug", "inputs", "grade", "dossier", "metrics", "profile_embedding")}


def analysis(*indexes: int) -> TwinAnalysis:
    return TwinAnalysis(comparisons=[TwinComparison(twin_index=i, key_similarity="s", key_difference="d",
                                                    plausible_deciding_factor="f") for i in indexes],
                        pattern_summary="p", pattern_strength="moderate", applicant_gaps=[], applicant_edges=[])


async def test_node_returns_five_contrastive_cards_baseline_radar_and_analysis(node):
    calls, events = node(POOL, analysis=analysis(1, 3, 9))
    s = node_state()
    out = await N.twins_node(s)

    cards = out["twins"]
    assert [c.index for c in cards] == [1, 2, 3, 4, 5]
    assert {"accepted", "rejected"} <= {c.outcome for c in cards}                     # ≥1 admit and ≥1 reject
    [(schools, kw)] = calls["match"]
    m = s["metrics"]
    assert schools == ["uiuc"] and kw == {"k": N.CONTRAST_POOL, "gpa": m.gpa_uw_4, "sat": m.sat_equivalent}
    assert calls["stats"] == [(["uiuc"], {"k": N.NEIGHBORHOOD_K, "gpa": m.gpa_uw_4, "sat": m.sat_equivalent})]
    assert out["baseline"].odds_inflation == 2.4 and not out["baseline"].widened_to_peers

    [p] = calls["parse"]
    assert (p["schema"], p["system"], p["effort"], p["max_tokens"]) == (TwinAnalysis, TWIN_ANALYST_SYSTEM,
                                                                        "medium", 10000)
    text = p["messages"][0]["content"]
    assert text.endswith("School: uiuc. Write the twin analysis.") and "<neighborhood_stats>" in text
    assert "source_url" not in text and "semantic_similarity" not in text
    assert [c.twin_index for c in out["twin_analysis"].comparisons] == [1, 3]         # unknown twin 9 dropped
    assert out["warnings"] == []

    names = [e for e, _ in events]
    assert names == ["node_start", "tool_call", "tool_call", "twins", "tool_call", "tool_call", "baseline", "radar",
                     "twin_analysis", "node_end"]
    assert dict(events)["radar"]["radar"] == build_radar(s["metrics"], s["grade"], MEDIANS)
    assert dict(events)["twins"]["widened_to_peers"] is False


async def test_sparse_school_widens_to_its_peer_group(node):
    calls, events = node([row(1)], POOL, analysis=analysis(1))
    out = await N.twins_node(node_state())
    assert [sch for sch, _ in calls["match"]] == [["uiuc"], ["uiuc", "purdue", "umich"]]
    assert calls["peers"] == [("uiuc", "big_ten_public")] and calls["stats"][0][0] == ["uiuc", "purdue", "umich"]
    assert out["baseline"].widened_to_peers and out["baseline"].peer_schools == ["purdue", "umich"]
    assert len(out["twins"]) == 5 and dict(events)["twins"]["peer_schools"] == ["purdue", "umich"]


async def test_no_twins_skips_the_analysis(node):
    calls, events = node([], [])
    out = await N.twins_node(node_state())
    assert out["twins"] == [] and out["twin_analysis"] is None and calls["parse"] == []
    assert dict(events)["twin_analysis"] == {"analysis": None}


@pytest.mark.parametrize("error", [
    N.llm.LLMRefusal("refused"), N.llm.LLMTruncated("TwinAnalysis hit max_tokens=10000"),
    anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")),
], ids=["refusal", "truncated", "api_error"])
async def test_analysis_failure_degrades_but_keeps_cards_and_baseline(node, error):
    node(POOL, parse_error=error)
    out = await N.twins_node(node_state())
    assert out["twin_analysis"] is None and out["warnings"] == [f"twin analysis degraded: {type(error).__name__}"]
    assert len(out["twins"]) == 5 and out["baseline"].n_neighbors == 50


def test_card_keeps_four_strongest_activities_and_awards():
    acts = [{"tier": t, "name": f"a{t}"} for t in (4, 2, 3, 1, 2)]
    card = N._to_card(1, row(1, activities=acts, awards=[{"name": f"w{i}"} for i in range(6)], hooks=None))
    assert [a["tier"] for a in card.top_activities] == [1, 2, 2, 3] and len(card.awards) == 4 and card.hooks == []
