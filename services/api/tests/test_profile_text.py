from app import embeddings
from app.agents.prompts.rubrics import HARVARD_RUBRIC, TIER_RUBRIC
from app.profile_text import ProfileFacts, build_profile_text


def fixture_facts(**over) -> ProfileFacts:
    base = dict(
        applicant_type="first_year", intended_major="CS + Math", major_category="computer_science",
        gpa_uw=3.95, gpa_w=4.5, college_gpa=None, sat=1550, act=None, advanced_courses=12,
        rigor_label="most_demanding", spike="USACO Platinum",
        activities=[(3, "Robotics captain"), (2, "USACO Platinum; founded school CS club")],
        awards=[("national", "USACO Platinum")], hooks=["rural", "first_gen"],
        school_type="public", residency_state="IL", income_bracket="80-150k", first_gen=True,
    )
    return ProfileFacts(**(base | over))


def test_profile_text_is_deterministic():
    a = build_profile_text(fixture_facts())
    b = build_profile_text(fixture_facts(hooks=["first_gen", "rural"]))     # hook order must not matter
    assert a == b
    assert a.startswith("Applicant type: first-year\nIntended major: CS + Math [computer_science]")
    assert "Hooks: first_gen, rural" in a
    assert a.index("[Tier 2]") < a.index("[Tier 3]")                         # strongest tiers first


def test_profile_text_handles_missing_values():
    text = build_profile_text(fixture_facts(gpa_uw=None, sat=None, first_gen=None, hooks=[], spike=None))
    assert "UW GPA —" in text and "SAT —" in text
    assert "first-gen unknown" in text and "Hooks: none" in text and "Spike: none stated" in text


def test_rubrics_present():
    assert "Harvard-style reader ratings" in HARVARD_RUBRIC
    assert "Tier 1" in TIER_RUBRIC


async def test_embed_texts_batches_and_orders(monkeypatch):
    calls: list[list[str]] = []

    class Item:
        def __init__(self, index, embedding):
            self.index, self.embedding = index, embedding

    class FakeEmbeddings:
        async def create(self, model, input):
            calls.append(list(input))
            return type("R", (), {"data": [Item(i, [float(len(t))]) for i, t in reversed(list(enumerate(input)))]})()

    fake = type("C", (), {"embeddings": FakeEmbeddings()})()
    monkeypatch.setattr(embeddings, "_get_client", lambda: fake)
    monkeypatch.setitem(__import__("sys").modules, "app.config",
                        type("M", (), {"settings": type("S", (), {"embedding_model": "m"})()}))
    out = await embeddings.embed_texts(["a", "bb", "ccc"], batch_size=2)
    assert out == [[1.0], [2.0], [3.0]]
    assert [len(c) for c in calls] == [2, 1]
