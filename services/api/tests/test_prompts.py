import re

import pytest

from app.agents.docket import CITATION_RE
from app.agents.prompts import committee, delta, dossier, institutional, twins

ANY_CITATION = re.compile(r"\[\[.*?\]\]")
KINDS = {"dossier", "cds", "twin", "web", "model", "sql"}


def _citations(text: str) -> list[str]:
    return ANY_CITATION.findall(text)


def test_every_citation_form_in_committee_system_matches_citation_re():
    forms = _citations(committee.COMMITTEE_SYSTEM)
    assert len(forms) >= len(KINDS)
    for form in forms:
        assert CITATION_RE.fullmatch(form), form
    assert {CITATION_RE.fullmatch(f).group(1) for f in forms} == KINDS     # every kind is taught to the model


@pytest.mark.parametrize("text", [*(b for _, b in committee.TURN_BRIEFS.values()), twins.TWIN_ANALYST_SYSTEM],
                         ids=lambda t: t[:30])
def test_citations_in_other_prompts_also_parse(text):
    for form in _citations(text):
        assert CITATION_RE.fullmatch(form), form


def test_turn_briefs_alternate_and_close_with_a_recommendation_line():
    assert committee.MAX_TURNS == 4
    assert [committee.TURN_BRIEFS[n][0] for n in range(1, 5)] == ["advocate", "chair", "advocate", "chair"]
    assert "RECOMMENDATION: <ADMIT | LIKELY ADMIT | WAITLIST | LIKELY DENY | DENY>" in committee.TURN_BRIEFS[4][1]


def test_grader_embeds_both_rubrics_and_prompts_are_nonempty():
    from app.agents.prompts.rubrics import HARVARD_RUBRIC, TIER_RUBRIC

    assert HARVARD_RUBRIC in dossier.RUBRIC_GRADER_SYSTEM and TIER_RUBRIC in dossier.RUBRIC_GRADER_SYSTEM
    for text in (dossier.DOSSIER_EXTRACTOR_SYSTEM, dossier.RUBRIC_GRADER_SYSTEM, institutional.INSTITUTIONAL_SYSTEM,
                 twins.TWIN_ANALYST_SYSTEM, committee.COMMITTEE_SYSTEM, delta.DELTA_SYSTEM):
        assert len(text) > 500 and "{" not in text                         # no unfilled f-string fields
