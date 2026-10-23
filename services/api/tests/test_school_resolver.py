import csv
from pathlib import Path

import yaml

from etl.school_resolver import SchoolResolver, normalize

DATA = Path(__file__).resolve().parents[3] / "data"


def build_aliases() -> dict[str, str]:
    """Same alias merge as etl/load_scorecard.py: seed CSV short names + aliases, then the YAML."""
    aliases: dict[str, str] = {}
    with (DATA / "schools_seed.csv").open() as f:
        for row in csv.DictReader(f):
            aliases[row["short_name"].lower()] = row["slug"]
            for a in row["aliases"].split("|"):
                aliases[a.strip().lower()] = row["slug"]
    for slug, names in yaml.safe_load((DATA / "school_aliases.yaml").read_text()).items():
        for a in names:
            aliases[a.lower()] = slug
    return aliases


def test_normalize_strips_noise():
    assert normalize("CMU (SCS)") == "cmu"
    assert normalize("The University of Michigan") == "university of michigan"
    assert normalize("MIT ED") == "mit"


def test_known_names_resolve():
    r = SchoolResolver(build_aliases())
    assert r.resolve("UMich") == "umich"
    assert r.resolve("CMU SCS") == "cmu"
    assert r.resolve("UC Berkeley") == "uc_berkeley"
    assert r.resolve("Georgia Tech") == "georgia_tech"
    assert not r.unresolved


def test_ambiguous_and_unknown_are_unresolved():
    r = SchoolResolver(build_aliases())
    assert r.resolve("UW") is None
    assert r.resolve("Hogwarts") is None
    assert r.unresolved["uw"] == 1
    assert r.unresolved["hogwarts"] == 1


def test_seed_slugs_are_valid_and_unitids_unique():
    with (DATA / "schools_seed.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len({r["unitid"] for r in rows}) == len(rows)
    assert all(r["slug"].replace("_", "").isalnum() and r["slug"] == r["slug"].lower() for r in rows)


def test_dump_unresolved(tmp_path):
    r = SchoolResolver({"mit": "mit"})
    r.resolve("nowhere u")
    out = tmp_path / "u.csv"
    r.dump_unresolved(out)
    assert out.read_text().splitlines()[1] == "nowhere u,1"
