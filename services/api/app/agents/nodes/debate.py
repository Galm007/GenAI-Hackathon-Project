from __future__ import annotations

import re

import anthropic

from app import llm
from app.schemas.debate import DebateTurn, Speaker

from ..docket import validate_citations
from ..events import emit
from ..prompts.committee import COMMITTEE_SYSTEM, MAX_TURNS, TURN_BRIEFS
from ..state import AdComState

REC_RE = re.compile(r"RECOMMENDATION:\s*(ADMIT|LIKELY ADMIT|WAITLIST|LIKELY DENY|DENY)\s*$", re.MULTILINE)
ROLE_LABEL = {"advocate": "Regional Admissions Officer (Advocate)", "chair": "Committee Chair"}


def _transcript(turns: list[DebateTurn]) -> str:
    return "\n\n".join(f"[Turn {t.turn} — {ROLE_LABEL[t.speaker]}]\n{t.content}" for t in turns) \
        or "(The discussion has not started.)"


def fallback_turn(turn: int, speaker: Speaker, state: AdComState) -> str:
    """Template turn used only if the API fails mid-demo. Still grounded and cited."""
    g, p, r, b = state["grade"], state["probability"], state["school_rubric"], state["baseline"]
    if speaker == "advocate":
        return (f"I'm bringing this file forward on the strength of {g.spike.label} [[dossier:spike]]. "
                f"Our reader rated it {g.harvard.academic.rating} academically and "
                f"{g.harvard.extracurricular.rating} on activities [[dossier:harvard]], and "
                f"{b.n_accepted} of the closest comparable applicants were admitted [[model:twins]].")
    if turn < MAX_TURNS:
        return (f"My concern is the bottleneck: this major carries a ×{r.major_multiplier:.2f} multiplier "
                f"[[cds:major.{r.major_category}]], and {b.n_rejected} of the closest comparable applicants were "
                f"denied [[model:twins]]. What in this file separates it from them?")
    return (f"The model places this file at {p.disposition.lower()} [[model:disposition]], and the discussion "
            f"didn't give me a reason to depart from it.\nRECOMMENDATION: {p.disposition}")


def make_debate_node(speaker: Speaker):
    async def debate_node(state: AdComState) -> dict:
        turn = state.get("debate_turn", 0) + 1
        expected, brief = TURN_BRIEFS[turn]
        assert expected == speaker, f"turn {turn} belongs to {expected}, not {speaker}"
        emit("debate_turn_start", turn=turn, speaker=speaker)

        messages = [{"role": "user", "content": [
            # identical bytes every turn → cached after turn 1
            {"type": "text", "text": f"<docket>\n{state['docket']}\n</docket>", "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": f"<transcript>\n{_transcript(state.get('debate', []))}\n</transcript>\n\n{brief}"},
        ]}]

        degraded = False
        try:
            text = await llm.stream_text(
                system=COMMITTEE_SYSTEM, messages=messages,
                on_text=lambda delta: emit("debate_token", turn=turn, speaker=speaker, delta=delta),
                on_reset=lambda: emit("debate_reset", turn=turn, speaker=speaker),
                effort="low", max_tokens=4000,
            )
        except (llm.LLMRefusal, anthropic.APIError):
            text, degraded = fallback_turn(turn, speaker, state), True
            emit("debate_reset", turn=turn, speaker=speaker)
            emit("debate_token", turn=turn, speaker=speaker, delta=text)

        citations = validate_citations(text, state["docket_index"])
        if bad := [f"{c.kind}:{c.ref}" for c in citations if not c.valid]:
            emit("citation_warning", turn=turn, refs=bad)

        recommendation = None
        if speaker == "chair" and turn == MAX_TURNS:
            m = REC_RE.search(text)
            recommendation = m.group(1) if m else state["probability"].disposition

        dt = DebateTurn(turn=turn, speaker=speaker, content=text, citations=citations,
                        recommendation=recommendation, degraded=degraded)
        emit("debate_turn_end", **dt.model_dump())
        return {"debate": [dt], "debate_turn": turn}

    debate_node.__name__ = f"{speaker}_node"
    return debate_node


def route_debate(state: AdComState) -> str:
    return "delta_engine" if state["debate_turn"] >= MAX_TURNS else "advocate"
