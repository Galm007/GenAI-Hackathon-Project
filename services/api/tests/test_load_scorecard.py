from etl.load_scorecard import FIELD_MAP, _to_row, slugify

SEED = {145637: {"slug": "uiuc", "short_name": "UIUC", "peer_group": "public_ivy"}}


def api_result(**over) -> dict:
    base = {
        "id": 145637, "school.name": "University of Illinois Urbana-Champaign", "school.city": "Champaign",
        "school.state": "IL", "school.ownership": 1, "school.school_url": "illinois.edu",
        "latest.admissions.admission_rate.overall": 0.45,
        "latest.admissions.sat_scores.25th_percentile.critical_reading": 640,
        "latest.admissions.sat_scores.75th_percentile.critical_reading": 730,
        "latest.admissions.sat_scores.25th_percentile.math": 700,
        "latest.admissions.sat_scores.75th_percentile.math": 790,
        "latest.admissions.act_scores.25th_percentile.cumulative": 28,
        "latest.admissions.act_scores.75th_percentile.cumulative": 33,
        "latest.admissions.test_requirements": 5,
    }
    return base | over


def test_seeded_school_row():
    row = _to_row(api_result(), SEED)
    assert row["slug"] == "uiuc" and row["peer_group"] == "public_ivy" and row["short_name"] == "UIUC"
    assert row["control"] == "public" and row["test_policy"] == "optional"
    assert row["sat_composite_25"] == 1340 and row["sat_composite_75"] == 1520
    assert row["data_quality"]["imputed"] == ["sat_composite_25", "sat_composite_75"]
    assert "test_requirements" not in row


def test_unseeded_school_gets_slug_and_defaults():
    row = _to_row(api_result(**{"id": 1, "school.name": "Reed College", "school.ownership": 2,
                                "latest.admissions.test_requirements": None}), {})
    assert row["slug"] == "reed_college" and row["peer_group"] == "other"
    assert row["control"] == "private_nonprofit" and row["test_policy"] == "unknown"


def test_missing_sat_is_not_imputed():
    row = _to_row(api_result(**{"latest.admissions.sat_scores.25th_percentile.math": None}), SEED)
    assert "sat_composite_25" not in row and row["data_quality"]["imputed"] == []


def test_slugify_and_field_map():
    assert slugify("Texas A&M University") == "texas_a_m_university"
    assert FIELD_MAP["id"] == "unitid"
