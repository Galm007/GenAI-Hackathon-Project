"""Node 1 with llm.parse and the local embedder mocked (no API key, no Ollama)."""
import pytest

from app.agents.nodes import dossier_parser as N
from app.agents.prompts.dossier import DOSSIER_EXTRACTOR_SYSTEM, RUBRIC_GRADER_SYSTEM
from app.schemas.dossier import DossierGrade, ParsedDossier
from app.scoring import metrics as M

from .test_scoring_metrics import S, course, dossier, grade, inputs

ESSAY = ("My name is Maya Chen and I live at 42 Elm Street. Email me at maya.chen@example.com or call "
         "(217) 555-0142. Maya taught Scratch at the library every Saturday.")
PII = ["Maya Chen", "Maya", "42 Elm Street", "MC"]


def maya_dossier(**kw) -> ParsedDossier:
    d = dossier(courses=[course("A", "ap")] * 3 + [course("B+", "ap")] * 3, sat=1350, activities=2)
    return d.model_copy(update={"essay_text": ESSAY, "pii_strings": PII, **kw})


# ---------- redaction ----------
def test_redact_removes_pii_longest_first_plus_email_and_phone():
    r = N.redact(maya_dossier())
    assert r.pii_strings == []
    assert r.essay_text == ("My name is [redacted] and I live at [redacted]. Email me at [email] or call "
                            "([phone]. [redacted] taught Scratch at the library every Saturday.")   # "(" survives
    for s in ("Maya", "Chen", "Elm", "example.com", "555", "217", "0142"):
        assert s not in r.essay_text


def test_redact_skips_short_strings_and_leaves_other_fields():
    d = maya_dossier(essay_text="MC led the MC club.", pii_strings=["MC"])
    r = N.redact(d)
    assert r.essay_text == "MC led the MC club."                   # < 3 chars: too risky to blank everywhere
    assert r.activities == d.activities and r.courses == d.courses
    assert N.redact(maya_dossier(essay_text=None)).essay_text is None


# ---------- prompt payloads ----------
def test_intake_blocks_put_documents_first_and_skip_empty_text():
    i = inputs(transcript_pdf_b64="JVBERi0=", resume_pdf_b64="JVBERi1=", activities_text="USACO Gold",
               essay_text="An essay.")
    blocks = N._intake_blocks(i)
    assert [b["type"] for b in blocks] == ["document", "document", "text"]
    assert [b["title"] for b in blocks[:2]] == ["Transcript", "Resume"]
    assert blocks[0]["source"] == {"type": "base64", "media_type": "application/pdf", "data": "JVBERi0="}
    text = blocks[2]["text"]
    assert "<activities_list>\nUSACO Gold\n</activities_list>" in text and "<common_app_essay>" in text
    assert "<resume_text>" not in text and "<recommendation_letter>" not in text
    assert text.endswith("Transcribe these materials into the dossier.")


def test_grader_payload_hides_post_grading_metrics_and_indexes_items():
    d = N.redact(maya_dossier(awards=[S.Award(name="USACO Gold", level="national", grade=11)]))
    payload = N._grader_payload(d, M.compute_metrics(d), inputs(recommendation_text="Letter."))
    assert payload.startswith("<dossier>\n") and payload.endswith("\n</dossier>")
    assert "tier_derived_ec_rating" not in payload and '"ec_score"' not in payload
    assert '"proxy_academic_rating": 5.0' in payload and '"has_recommendations": true' in payload
    assert '"index": 1' in payload and N.EC_ANCHOR_FORMULA in payload
    assert "Maya" not in payload and "maya.chen" not in payload


def test_ec_anchor_formula_text_matches_the_scoring_code():
    t = M.TIER_POINTS
    assert f"{t[1]:g}·#Tier1 + {t[2]:g}·#Tier2 + {t[3]:g}·#Tier3 + {t[4]:g}·#Tier4" in N.EC_ANCHOR_FORMULA
    assert M.ec_rating_from_tiers([]) == 5.2 and "5.2 − 0.55" in N.EC_ANCHOR_FORMULA
    assert M.ec_rating_from_tiers([2] * 5) == 1.6 and "[1.6, 5.5]" in N.EC_ANCHOR_FORMULA
    assert M.ec_rating_from_tiers([1] * 5) == 1.0 and "[1.0, 5.5]" in N.EC_ANCHOR_FORMULA


# ---------- the node ----------
@pytest.fixture
def run_node(monkeypatch):
    calls: list[dict] = []
    events: list[tuple[str, dict]] = []
    embedded: list[str] = []

    def install(extracted: ParsedDossier, graded: DossierGrade):
        replies = iter([extracted, graded])

        async def parse(schema, **kw):
            calls.append({"schema": schema, **kw})
            return next(replies)

        async def embed_one(text):
            embedded.append(text)
            return [0.1] * 768

        monkeypatch.setattr(N.llm, "parse", parse)
        monkeypatch.setattr(N, "embed_one", embed_one)
        monkeypatch.setattr(N, "emit", lambda event, **d: events.append((event, d)))
        monkeypatch.setattr(N, "progress", lambda *a, **k: None)
        return calls, events, embedded
    return install


async def test_node_extracts_redacts_grades_clamps_and_embeds(run_node):
    ag = [S.ActivityGrade(activity_index=0, rationale="r", tier=2, spike_role="core")]   # activity 1 ungraded
    calls, events, embedded = run_node(maya_dossier(), grade(academic=1, personal=1, activity_grades=ag))
    i = inputs(transcript_pdf_b64="JVBERi0=", essay_text=ESSAY)
    out = await N.dossier_parser_node({"inputs": i})

    # two calls, as the plan sets them up
    assert [c["schema"] for c in calls] == [ParsedDossier, DossierGrade]
    shape = [(c["system"], c["effort"], c["max_tokens"]) for c in calls]
    assert shape == [(DOSSIER_EXTRACTOR_SYSTEM, "medium", 32000), (RUBRIC_GRADER_SYSTEM, "high", 24000)]
    assert calls[0]["messages"][0]["content"][0]["type"] == "document"
    grader_input = calls[1]["messages"][0]["content"]
    assert "Maya" not in grader_input and "[redacted]" in grader_input        # the grader never sees PII

    # guardrails applied: academic 1 at a 5.0 anchor → 4; personal 1 without letters → 2; ungraded → Tier 4
    g = out["grade"]
    assert (g.harvard.academic.rating, g.harvard.personal.rating) == (4, 2)
    assert [a.tier for a in g.activity_grades] == [2, 4]
    assert out["metrics"].ec_score == pytest.approx(2.2) and out["warnings"] == g.grader_warnings
    assert any("academic rating 1 clamped to 4" in w for w in out["warnings"])

    # outputs and events
    assert out["dossier"].pii_strings == [] and "Maya" not in out["dossier"].essay_text
    assert out["profile_embedding"] == [0.1] * 768 and embedded == [out["profile_text"]]
    assert "Maya" not in out["profile_text"]
    names = [e for e, _ in events]
    assert names == ["node_start", "dossier_parsed", "scorecard", "node_end"]
    parsed = dict(events)["dossier_parsed"]
    assert "essay_text" not in parsed["dossier"] and parsed["metrics"]["ec_score"] == 0.0
    scorecard = dict(events)["scorecard"]
    assert scorecard["warnings"] == out["warnings"] and scorecard["grade"]["harvard"]["academic"]["rating"] == 4
    assert dict(events)["node_start"]["label"] == "Dossier Parser & Rubric Grader"


def test_facts_drop_a_none_spike_and_map_context():
    d = maya_dossier()
    g = grade().model_copy(update={"spike": S.Spike(label="none", description="", strength="none")})
    i = inputs(context={"residency_state": "IL", "low_income": True, "first_gen": True})
    f = N._facts(d, g, M.compute_metrics(d), i)
    assert f.spike is None and f.income_bracket == "<60k" and f.first_gen is True and f.residency_state == "IL"
    assert f.activities == [(3, d.activities[0].description)]
