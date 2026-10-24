import pytest

from app.scoring import probability as P

PILLAR_WEIGHTS = {"academic": 0.45, "extracurricular": 0.25, "personal": 0.2, "athletic": 0.1}


def inputs(**kw) -> P.ScoringInputs:
    base = dict(
        base_admit_rate=0.44, major_multiplier=0.38, pillar_weights=PILLAR_WEIGHTS,
        ratings={"academic": 2.33, "extracurricular": 2.67, "personal": 3.0, "athletic": 4.0},
        test_weight=0.66, test_policy="optional", sat=1450, sat_25=1350, sat_75=1530, hooks=(),
        hook_effects={"first_gen": 0.165, "legacy": 0.0}, residency_effect=0.35, early_round=None,
        ed_admit_rate=0.35, rd_admit_rate=0.20, ea_admit_rate=0.30, applicant_interest_weight=0.33,
        twin_sum_w=33.1, twin_sum_w2=34.8, twin_sum_w_admit=11.9, odds_inflation=2.4,
    )
    return P.ScoringInputs(**(base | kw))


def better(x: P.ScoringInputs, pillar: str) -> P.ScoringInputs:
    return x.with_overrides(ratings={**x.ratings, pillar: x.ratings[pillar] - 1})


CASES = [
    inputs(),
    inputs(base_admit_rate=0.04, major_multiplier=1.0, twin_sum_w=0.0, twin_sum_w2=0.0, twin_sum_w_admit=0.0),
    inputs(base_admit_rate=0.30, major_multiplier=1.4, sat=1580, hooks=("first_gen",)),   # strong, unsaturated
    inputs(ratings={"academic": 5.0, "extracurricular": 5.0, "personal": 4.67, "athletic": 4.0}, sat=1200),
    inputs(test_policy="blind", sat=None, residency_effect=-0.4, early_round="ED"),
]


# ---------- §3.10 scoring monotonicity ----------
@pytest.mark.parametrize("x", CASES)
def test_p_final_strictly_increases_with_each_improvement(x):
    p0 = P.compute_probability(x).p_final
    for pillar in P.PILLARS:
        assert P.compute_probability(better(x, pillar)).p_final > p0, pillar
    if x.test_policy != "blind":
        assert P.compute_probability(x.with_overrides(sat=(x.sat or 1300) + 60)).p_final > p0
    if x.early_round != "ED":
        assert P.compute_probability(x.with_overrides(early_round="ED")).p_final > p0


@pytest.mark.parametrize("x", CASES + [
    inputs(base_admit_rate=0.99, major_multiplier=2.0, ratings=dict.fromkeys(PILLAR_WEIGHTS, 1.0), sat=1600,
           hooks=("first_gen",), twin_sum_w_admit=33.1, odds_inflation=1.0),
    inputs(base_admit_rate=0.001, major_multiplier=0.25, ratings=dict.fromkeys(PILLAR_WEIGHTS, 6.0), sat=900,
           twin_sum_w_admit=0.0),
])
def test_all_probabilities_stay_in_bounds(x):
    b = P.compute_probability(x)
    for v in (b.p_final, b.p_model, b.p_low, b.p_high):
        assert P.P_FLOOR <= v <= P.P_CEIL
    assert b.p_low <= b.p_final <= b.p_high


# ---------- §3.10 waterfall integrity ----------
SATURATED = [
    inputs(base_admit_rate=0.80, major_multiplier=2.0, sat=1580, hooks=("first_gen",)),       # p_model at the ceiling
    inputs(base_admit_rate=0.001, major_multiplier=0.25, ratings=dict.fromkeys(PILLAR_WEIGHTS, 6.0), sat=900),
]


@pytest.mark.parametrize("x", CASES + SATURATED)
def test_waterfall_sums_to_p_final(x):
    b = P.compute_probability(x)
    assert [c.key for c in b.components] == ["base", "major", *P.PILLARS, "test", "hooks", "residency", "early",
                                             "interest", "twins"]
    assert sum(c.delta_pp for c in b.components) == pytest.approx(b.p_final * 100, abs=0.5)


# ---------- pieces ----------
def test_twin_posterior_without_twins_is_the_model():
    b = P.compute_probability(CASES[1])
    assert b.p_final == b.p_model and b.components[-1].delta_pp == 0
    assert b.components[-1].detail == "No comparable twins; model only."


def test_twins_pull_toward_the_deflated_neighbourhood_rate_with_capped_weight():
    x = inputs(twin_sum_w=0.0, twin_sum_w2=0.0, twin_sum_w_admit=0.0)
    p_model = P.compute_probability(x).p_final
    # 100 equal-weight twins, all admitted, no inflation: n_eff is capped at 20 against κ=12
    strong = P.compute_probability(x.with_overrides(twin_sum_w=100.0, twin_sum_w2=100.0, twin_sum_w_admit=100.0,
                                                    odds_inflation=1.0)).p_final
    assert strong == pytest.approx((P.KAPPA * p_model + 20 * 0.99) / (P.KAPPA + 20), abs=1e-3)
    inflated = P.compute_probability(x.with_overrides(twin_sum_w=100.0, twin_sum_w2=100.0, twin_sum_w_admit=100.0,
                                                      odds_inflation=4.0)).p_final
    assert inflated < strong


def test_test_position_and_blind_policy():
    assert P.test_position(1440, 1350, 1530) == 0.0
    assert P.test_position(2000, 1350, 1530) == 1.5 and P.test_position(400, 1350, 1530) == -2.5
    assert P.test_position(None, 1350, 1530) == 0.0 and P.test_position(1500, 1500, 1400) == 0.0
    blind = inputs(test_policy="blind")
    assert P.compute_probability(blind) == P.compute_probability(blind.with_overrides(sat=1600))


def test_early_round_credit_is_capped():
    assert P.early_effect(inputs(early_round="ED", ed_admit_rate=0.9, rd_admit_rate=0.05)) == 1.0
    assert P.early_effect(inputs(early_round="EA", ea_admit_rate=0.9, rd_admit_rate=0.05)) == 0.4
    assert P.early_effect(inputs(early_round="ED", ed_admit_rate=None)) == 0.0
    assert P.early_effect(inputs(early_round=None)) == 0.0


def test_hooks_are_capped_and_interest_needs_c7_weight():
    x = inputs(hooks=("a", "b"), hook_effects={"a": 3.0, "b": 3.0})
    assert next(c for c in P.compute_probability(x).components if c.key == "hooks").delta_logit == P.HOOK_CAP
    no_weight = inputs(applicant_interest_weight=0.0)
    shown = no_weight.with_overrides(demonstrated_interest=True)
    assert P.compute_probability(no_weight) == P.compute_probability(shown)


@pytest.mark.parametrize(("p", "label"), [(0.7, "ADMIT"), (0.45, "LIKELY ADMIT"), (0.2, "WAITLIST"),
                                          (0.08, "LIKELY DENY"), (0.0799, "DENY")])
def test_disposition_thresholds(p, label):
    assert P.disposition(p) == label
