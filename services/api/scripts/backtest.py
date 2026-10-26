"""A16: backtest + bias audit (plan §6.2 H16-24, §7.3 Q1).

Replays every first-year Reddit decision (admit/deny only) through the deterministic scorer in
`app/scoring/` and compares it with the outcome. No LLM is called and nothing is paid for: ratings come
from the same statistical anchors Node 1 clamps to (`proxy_academic_rating`, `ec_rating_from_tiers`).

Held out = the latest 30% of posts by `post_created_at` (D-044: 98% of twins are one cycle, so a cycle split
would leave 22 training rows). Twin evidence for a held-out row comes from earlier posts only.

    uv run python -m scripts.backtest                # print the results
    uv run python -m scripts.backtest --write        # also write data/backtest.json + docs/data-report.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.scoring.metrics import ec_rating_from_tiers, proxy_academic_rating, sat_equivalent
from app.scoring.probability import REF, ScoringInputs, compute_probability, odds
from app.scoring.rubric import C7_WEIGHT, build_school_rubric

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs" / "data-report.md"
RESULTS = ROOT / "data" / "backtest.json"
HOLDOUT_FRAC = 0.30
NEIGHBORS = 50
MIN_SUBGROUP = 30         # smaller groups are listed but flagged as too small to read
BEGIN, END = "<!-- backtest:begin -->", "<!-- backtest:end -->"


@dataclass(frozen=True)
class Example:
    twin_id: str
    slug: str
    y: int                       # 1 = admitted, 0 = denied
    posted: str
    gpa: float | None
    sat: int | None
    p_base: float = 0.0
    p_model: float = 0.0
    p_final: float = 0.0
    p_reddit: float = 0.0
    income: str = "unknown"
    first_gen: str = "not stated"      # explicit self-report only: yes / no / not stated


# ── metrics ──────────────────────────────────────────────────────────────────────────────────────

def brier(ps: list[float], ys: list[int]) -> float:
    return sum((p - y) ** 2 for p, y in zip(ps, ys, strict=True)) / len(ys)


def auc(ps: list[float], ys: list[int]) -> float | None:
    """Mann-Whitney U with average ranks for ties; None when one class is missing."""
    pos = sum(ys)
    neg = len(ys) - pos
    if pos == 0 or neg == 0:
        return None
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    ranks = [0.0] * len(ps)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and ps[order[j + 1]] == ps[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    rank_sum = sum(r for r, y in zip(ranks, ys, strict=True) if y)
    return (rank_sum - pos * (pos + 1) / 2) / (pos * neg)


def within_school_auc(rows: list[Example], field: str, min_n: int = 20) -> float | None:
    """Ranking skill inside each school (pairs-weighted). The between-school part of plain AUC is carried
    by the admit rate alone, so this is the number that says whether the profile adds anything."""
    by: dict[str, list[Example]] = defaultdict(list)
    for e in rows:
        by[e.slug].append(e)
    num = den = 0.0
    for es in by.values():
        pos = sum(e.y for e in es)
        a = auc([getattr(e, field) for e in es], [e.y for e in es]) if len(es) >= min_n else None
        if a is not None:
            num += a * pos * (len(es) - pos)
            den += pos * (len(es) - pos)
    return num / den if den else None


def reliability(ps: list[float], ys: list[int], bins: int = 5) -> list[dict]:
    """Equal-count bins by predicted probability: mean predicted vs observed admit rate."""
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    out = []
    for b in range(bins):
        idx = order[b * len(order) // bins:(b + 1) * len(order) // bins]
        if idx:
            out.append({"n": len(idx), "mean_pred": sum(ps[i] for i in idx) / len(idx),
                        "observed": sum(ys[i] for i in idx) / len(idx)})
    return out


def summarize(ps: list[float], ys: list[int]) -> dict:
    return {"n": len(ys), "mean_pred": sum(ps) / len(ps), "observed": sum(ys) / len(ys),
            "brier": brier(ps, ys), "auc": auc(ps, ys)}


# ── feature mapping (mirrors agents/docket.py::build_scoring_inputs, minus the LLM) ───────────────

def _tiers(summary: dict) -> list[int]:
    return [t for k, n in (("tier1", 1), ("tier2", 2), ("tier3", 3), ("tier4", 4))
            for t in [n] * int(summary.get(k) or 0)]


def scoring_inputs(twin: dict, decision: dict, school: dict) -> ScoringInputs:
    demo = twin.get("demographics") or {}
    rubric = build_school_rubric({k: v for k, v in school.items() if k != "major_competitiveness"},
                                 twin["major_category"], demo.get("residency_state"))
    sat = sat_equivalent(twin.get("sat_score"), twin.get("act_score"))
    ratings = {
        "academic": proxy_academic_rating(float(twin["gpa_uw"]) if twin.get("gpa_uw") is not None else None,
                                          sat, int(twin.get("ap_count") or 0)),
        "extracurricular": ec_rating_from_tiers(_tiers(twin.get("ec_tier_summary") or {})),
        "personal": REF["personal"],         # no essay or letters in a Reddit post: neutral
        "athletic": REF["athletic"],         # a recruited athlete is carried by the hook term
    }
    hooks = set(twin.get("hooks") or [])
    hooks |= {h for h in ("first_gen", "low_income") if demo.get(h)}
    return ScoringInputs(
        base_admit_rate=rubric.base_admit_rate, major_multiplier=1.0,       # Reddit-derived multiplier would leak
        pillar_weights=rubric.pillar_weights, ratings=ratings, test_weight=rubric.test_weight,
        test_policy=rubric.test_policy, sat=sat, sat_25=rubric.sat_25, sat_75=rubric.sat_75,
        hooks=tuple(sorted(hooks)), hook_effects=rubric.hook_effects, residency_effect=rubric.residency_effect,
        early_round=decision.get("round"), ed_admit_rate=rubric.ed_admit_rate, rd_admit_rate=rubric.rd_admit_rate,
        ea_admit_rate=school.get("ea_admit_rate"),
        applicant_interest_weight=C7_WEIGHT[rubric.factor_levels["applicant_interest"]],
    )


def proximity(a: Example, b: Example) -> float:
    """Stat-only stand-in for the RPC's hybrid score (the backtest has no embeddings): 1 = identical."""
    dg = 0.0 if a.gpa is None or b.gpa is None else (a.gpa - b.gpa) / 0.15
    ds = 0.0 if a.sat is None or b.sat is None else (a.sat - b.sat) / 100
    return math.exp(-0.5 * (dg * dg + ds * ds))


def twin_sums(target: Example, train: list[Example]) -> tuple[float, float, float]:
    near = sorted(((proximity(target, t), t.y) for t in train), reverse=True)[:NEIGHBORS]
    ws = [(math.exp(10.0 * (p - 1.0)), y) for p, y in near]
    return sum(w for w, _ in ws), sum(w * w for w, _ in ws), sum(w * y for w, y in ws)


def reddit_inflation(train: list[Example], official: float) -> float:
    """Odds ratio of the training Reddit admit rate to the official one, clamped like school_reddit_calibration."""
    if len(train) < 15:
        return 1.0
    r = min(max(sum(t.y for t in train) / len(train), 0.01), 0.99)
    return min(8.0, max(1.0, odds(r) / odds(min(max(official, 0.005), 0.95))))


def split(examples: list[Example]) -> tuple[list[Example], list[Example]]:
    ordered = sorted(examples, key=lambda e: (e.posted, e.twin_id))
    cut = int(len(ordered) * (1 - HOLDOUT_FRAC))
    return ordered[:cut], ordered[cut:]


def score(examples: list[Example], twins: dict[str, dict], decisions: dict[tuple[str, str], dict],
          schools: dict[str, dict]) -> tuple[list[Example], list[Example]]:
    """Fills p_base / p_model / p_final / p_reddit on every example; twin evidence uses earlier posts only."""
    train, test = split(examples)
    by_school: dict[str, list[Example]] = defaultdict(list)
    for e in train:
        by_school[e.slug].append(e)
    out: dict[str, list[Example]] = {"train": [], "test": []}
    for name, rows in (("train", train), ("test", test)):
        for e in rows:
            school = schools[e.slug]
            x = scoring_inputs(twins[e.twin_id], decisions[(e.twin_id, e.slug)], school)
            peers = [t for t in by_school[e.slug] if t.twin_id != e.twin_id and t.posted <= e.posted]
            sw, sw2, swa = twin_sums(e, peers)
            infl = reddit_inflation(peers, x.base_admit_rate)
            p_model = compute_probability(x).p_model
            p_final = compute_probability(x.with_overrides(twin_sum_w=sw, twin_sum_w2=sw2, twin_sum_w_admit=swa,
                                                           odds_inflation=infl)).p_final
            rate = (sum(t.y for t in peers) / len(peers)) if len(peers) >= 15 else x.base_admit_rate
            demo = twins[e.twin_id].get("demographics") or {}
            out[name].append(Example(
                twin_id=e.twin_id, slug=e.slug, y=e.y, posted=e.posted, gpa=e.gpa, sat=e.sat,
                p_base=x.base_admit_rate, p_model=p_model, p_final=p_final, p_reddit=rate,
                income=demo.get("income_bracket") or "unknown",
                first_gen={True: "yes", False: "no"}.get(demo.get("first_gen"), "not stated")))
    return out["train"], out["test"]


# ── report ───────────────────────────────────────────────────────────────────────────────────────

def subgroup_table(rows: list[Example], key, field: str) -> list[dict]:
    groups: dict[str, list[Example]] = defaultdict(list)
    for e in rows:
        groups[str(key(e))].append(e)
    return [{"group": g, **summarize([getattr(e, field) for e in es], [e.y for e in es])}
            for g, es in sorted(groups.items())]


def run(examples: list[Example], twins, decisions, schools, n_waitlist: int) -> dict:
    train, test = score(examples, twins, decisions, schools)
    ys = [e.y for e in test]
    cols = {"official_rate": "p_base", "reddit_rate": "p_reddit", "rubric_model": "p_model",
            "rubric_plus_twins": "p_final"}
    models = {name: summarize([getattr(e, f) for e in test], ys) | {"auc_within": within_school_auc(test, f)}
              for name, f in cols.items()}
    # Rubric-only needs no training rows, so the subgroup audit can use every example.
    everyone = train + test
    audit = {
        "held_out_final": {
            "income": subgroup_table(test, lambda e: e.income, "p_final"),
            "first_gen": subgroup_table(test, lambda e: e.first_gen, "p_final"),
        },
        "all_rubric_model": {
            "income": subgroup_table(everyone, lambda e: e.income, "p_model"),
            "first_gen": subgroup_table(everyone, lambda e: e.first_gen, "p_model"),
        },
    }
    return {
        "generated": datetime.now(UTC).strftime("%Y-%m-%d"),
        "n_decisions": len(examples), "n_waitlist_excluded": n_waitlist,
        "n_train": len(train), "n_test": len(test),
        "test_from": min(e.posted for e in test), "test_to": max(e.posted for e in test),
        "models": models,
        "reliability": {"rubric_plus_twins": reliability([e.p_final for e in test], ys),
                        "rubric_model": reliability([e.p_model for e in test], ys)},
        "audit": audit,
    }


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.1%}"


def _f(v: float | None, d: int = 3) -> str:
    return "n/a" if v is None else f"{v:.{d}f}"


def render(r: dict) -> str:
    m = r["models"]
    labels = {"official_rate": "Official admit rate (CDS), same for everyone",
              "reddit_rate": "Earlier Reddit admit rate at that school",
              "rubric_model": "Rubric model (no twins)",
              "rubric_plus_twins": "Rubric model + twin evidence (what the app shows)"}
    L = [BEGIN, "", "## Backtest and bias audit (A16)", "",
         f"Run date: {r['generated']} · `uv run python -m scripts.backtest --write` · plan §6.2, §7.3 Q1. "
         "No language model was called: every number comes from `app/scoring/` on fields extracted from the post.", "",
         "### Setup", "",
         f"- **{r['n_decisions']}** first-year admit/deny decisions ({r['n_waitlist_excluded']} waitlists left out, "
         "because they are neither outcome).",
         f"- Held out: the latest {HOLDOUT_FRAC:.0%} of posts ({r['n_test']} decisions, posted {r['test_from'][:10]} "
         f"to {r['test_to'][:10]}). The earlier {r['n_train']} are the only twin evidence a held-out row may use. "
         "Plan wording is \"hold out the latest cycle\", but 925 of 947 twins are the 2026 cycle (D-044).",
         "- Ratings use the statistical anchors Node 1 clamps to. Personal and athletic ratings are neutral "
         "(a Reddit post has no essay or letters), so the pillar signal is academic and extracurricular only.",
         "- The major multiplier is held at 1.0 (the stored multiplier is learned from these same posts, so it would "
         "leak).",
         "- Twin neighbours are chosen by GPA and SAT proximity at the same school, not by embedding, because "
         "embeddings are not pulled into the backtest. The live app's retrieval is better than this stand-in.", "",
         f"### Held-out scores (n = {r['n_test']})", "",
         "| Predictor | Mean predicted | Observed admit rate | Brier ↓ | AUC ↑ | AUC within a school ↑ |",
         "|---|---|---|---|---|---|"]
    for k, lab in labels.items():
        L.append(f"| {lab} | {_pct(m[k]['mean_pred'])} | {_pct(m[k]['observed'])} | {_f(m[k]['brier'])} | "
                 f"{_f(m[k]['auc'])} | {_f(m[k]['auc_within'])} |")
    base, fin, rub = m["official_rate"], m["rubric_plus_twins"], m["rubric_model"]
    L += ["", f"Brier: the app's probability scores {_f(fin['brier'])}, the official-rate baseline "
          f"{_f(base['brier'])}, "
          f"the earlier Reddit rate at the school {_f(m['reddit_rate']['brier'])}. Plain AUC mixes schools, so the "
          "school's own admit rate already gets most of it; the last column ranks applicants inside one school, "
          f"where a constant rate scores 0.5. The rubric scores {_f(rub['auc_within'])} there and the app "
          f"{_f(fin['auc_within'])}.", "",
          ]
    L += [
          "### Reliability (held out, five equal-count bins)", "",
          "| Bin | n | Mean predicted | Observed | Mean predicted (no twins) | Observed (no twins) |",
          "|---|---|---|---|---|---|"]
    a, b = r["reliability"]["rubric_plus_twins"], r["reliability"]["rubric_model"]
    for i, (x, y) in enumerate(zip(a, b, strict=False), 1):
        L.append(f"| {i} | {x['n']} | {_pct(x['mean_pred'])} | {_pct(x['observed'])} | "
                 f"{_pct(y['mean_pred'])} | {_pct(y['observed'])} |")
    L += ["", "### Bias audit: calibration by subgroup", "",
          "Income bracket and first-generation status are self-reported and sparse. They are used here only to "
          "audit calibration; income is never a model input and first-gen enters only through the extractor's "
          "hook flag. "
          "The audit groups use explicit self-report only: the extractor sets a first_gen hook on far more twins "
          "than ever state it, so that flag is not used to define the group. "
          f"Groups with n < {MIN_SUBGROUP} are marked and should not be read.", ""]
    for title, key in (("Held out, app probability", "held_out_final"),
                       ("All decisions, rubric model (no training rows needed)", "all_rubric_model")):
        for dim, label in (("income", "Income bracket"), ("first_gen", "First-generation (self-reported)")):
            L += [f"**{title} · {label}**", "",
                  "| Group | n | Mean predicted | Observed | Gap (pred − obs) | Brier | AUC |",
                  "|---|---|---|---|---|---|---|"]
            for g in r["audit"][key][dim]:
                flag = " (too small)" if g["n"] < MIN_SUBGROUP else ""
                L.append(f"| {g['group']}{flag} | {g['n']} | {_pct(g['mean_pred'])} | {_pct(g['observed'])} | "
                         f"{(g['mean_pred'] - g['observed']) * 100:+.1f} pp | {_f(g['brier'])} | {_f(g['auc'])} |")
            L.append("")
    L += ["### How to read this", "",
          "- **Weak, and stated plainly.** Inside a school, the profile ranks applicants only slightly better than "
          "chance (within-school AUC near 0.53). The app's Brier beats the official-rate baseline mainly because "
          "the twin term moves the level toward the Reddit admit rate, and it does not beat simply using the "
          "earlier Reddit rate at that school. Ranking skill from a GPA, SAT and activity-tier profile is modest; "
          "the essays, letters and school context that decide close calls are not in a Reddit post.",
          "- Reddit applicants are self-selected, so observed admit rates are far above the official ones. A model "
          "anchored on official rates will under-predict on this sample. The twin term is meant to close part of "
          "that gap; the Mean predicted and Observed columns show how much it does.",
          "- Subgroup gaps larger than a few points on groups with enough rows are a calibration problem, not a "
          "feature. They are reported as they came out.", "", END]
    return "\n".join(L) + "\n"


def write_report(r: dict) -> None:
    section = render(r)
    text = REPORT.read_text(encoding="utf-8")
    if BEGIN in text:
        text = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", lambda _: section, text, flags=re.S)
    else:
        text = text.rstrip("\n") + "\n\n" + section
    f = r["models"]
    text = re.sub(r"\| Brier score, base-rate Brier \|[^\n]*\|",
                  f"| Brier score, base-rate Brier | **{_f(f['rubric_plus_twins']['brier'])}**, "
                  f"{_f(f['official_rate']['brier'])} (held out, n = {r['n_test']}; see A16) |", text)
    REPORT.write_text(text, encoding="utf-8")
    RESULTS.write_text(json.dumps(r, indent=2), encoding="utf-8")


# ── data ─────────────────────────────────────────────────────────────────────────────────────────

async def load() -> tuple[list[Example], dict, dict, dict, int]:
    from etl.common import fetch_all, supabase

    sb = await supabase()
    cols = ("id,post_created_at,gpa_uw,sat_score,act_score,ap_count,major_category,hooks,demographics,"
            "ec_tier_summary,decisions_detail,applicant_type")
    rows = [r for r in await fetch_all(sb, "applicant_twins", cols) if r["applicant_type"] == "first_year"]
    schools = {s["slug"]: s for s in await fetch_all(sb, "universities_cds")}
    twins = {r["id"]: r for r in rows}
    decisions: dict[tuple[str, str], dict] = {}
    examples: list[Example] = []
    waitlist = 0
    for r in rows:
        for d in r["decisions_detail"] or []:
            slug, outcome = d.get("slug"), d.get("outcome")
            if slug not in schools or not schools[slug].get("admit_rate"):
                continue
            if outcome == "waitlisted":
                waitlist += 1
                continue
            if outcome not in ("accepted", "rejected") or (r["id"], slug) in decisions:
                continue
            decisions[(r["id"], slug)] = d
            sat = sat_equivalent(r.get("sat_score"), r.get("act_score"))
            examples.append(Example(twin_id=r["id"], slug=slug, y=int(outcome == "accepted"),
                                    posted=r["post_created_at"],
                                    gpa=float(r["gpa_uw"]) if r.get("gpa_uw") is not None else None, sat=sat))
    return examples, twins, decisions, schools, waitlist


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--write", action="store_true", help="write data/backtest.json and docs/data-report.md")
    a = p.parse_args()
    examples, twins, decisions, schools, waitlist = await load()
    result = run(examples, twins, decisions, schools, waitlist)
    print(render(result))
    if a.write:
        write_report(result)
        print(f"wrote {RESULTS.relative_to(ROOT)} and {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
