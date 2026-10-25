"""Replay and fixture JSON must be read as UTF-8: Windows defaults to cp1252, which turns "×" into "Ã—"."""
from app import demo, fake_llm, llm
from app.schemas.delta import ProbabilityBreakdown
from app.scoring.probability import ScoringInputs, compute_probability


def test_demo_replay_text_matches_the_scoring_code():
    bundle = demo.load_demo("maya-uiuc")
    saved = next(e for e in bundle["events"] if e["event"] == "probability")["probability"]
    live = compute_probability(ScoringInputs.model_validate(bundle["context"]["scoring_inputs"]))
    assert [c["detail"] for c in saved["components"]] == [c.detail for c in live.components]
    assert any("×" in c["detail"] for c in saved["components"])


async def test_fake_llm_fixtures_keep_non_ascii_text():
    restore = fake_llm.install()
    try:
        b = await llm.parse(ProbabilityBreakdown, system="", messages=[])
    finally:
        restore()
    details = " ".join(c.detail for c in b.components)
    assert "×" in details and "Ã" not in details
