from __future__ import annotations

from app.schemas.dossier import ComputedMetrics, DossierGrade

# key, label, value at 0, value at 100 (reversed ranges for "lower is better" ratings)
AXES = (
    ("gpa", "GPA", 3.5, 4.0),
    ("test", "Testing", 1300, 1600),
    ("rigor", "Rigor", 0, 14),
    ("activities", "Activities", 5.5, 1.0),
    ("spike", "Spike (T1/T2)", 0, 4),
    ("personal", "Essay & Personal", 6.0, 1.0),
)
POOL_PERSONAL = 3.0


def _norm(v: float | None, lo: float, hi: float) -> float | None:
    if v is None:
        return None
    return round(100 * min(max((v - lo) / (hi - lo), 0.0), 1.0), 1)


def build_radar(m: ComputedMetrics, g: DossierGrade, medians: dict) -> dict:
    tiers = [ag.tier for ag in g.activity_grades]
    you = {"gpa": m.gpa_uw_4, "test": m.sat_equivalent, "rigor": m.advanced_course_count,
           "activities": m.tier_derived_ec_rating, "spike": 2 * tiers.count(1) + tiers.count(2),
           "personal": g.harvard.personal.numeric}
    adm = {"gpa": medians.get("gpa_uw"), "test": medians.get("sat"), "rigor": medians.get("advanced"),
           "activities": medians.get("ec_rating"), "spike": medians.get("spike_points"), "personal": POOL_PERSONAL}
    return {
        "n_admitted": medians.get("n", 0),
        "axes": [{"key": k, "label": label, "you": _norm(you[k], lo, hi), "admitted_median": _norm(adm[k], lo, hi),
                  "you_raw": you[k], "admitted_raw": adm[k], "assumed": k == "personal"}
                 for k, label, lo, hi in AXES],
    }
