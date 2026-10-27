from scripts.record_demo import without_reset_text


def _tok(turn, text):
    return {"event": "debate_token", "turn": turn, "speaker": "advocate", "delta": text}


def test_replay_keeps_only_the_text_after_a_reset_and_renumbers():
    events = [{"event": "run_started"}, {"event": "debate_turn_start", "turn": 3},
              _tok(3, "Let me analyze…"), _tok(3, " plan"), {"event": "debate_reset", "turn": 3},
              _tok(3, "The answer."), {"event": "debate_turn_end", "turn": 3}, {"event": "done"}]
    out = without_reset_text([e | {"seq": i} for i, e in enumerate(events)])
    assert [e["event"] for e in out] == ["run_started", "debate_turn_start", "debate_token", "debate_turn_end", "done"]
    assert [e["seq"] for e in out] == list(range(5)) and out[2]["delta"] == "The answer."


def test_other_turns_and_runs_without_resets_are_untouched():
    events = [{"event": "debate_token", "turn": 1, "delta": "a"}, {"event": "debate_token", "turn": 2, "delta": "b"},
              {"event": "debate_reset", "turn": 2}, {"event": "debate_token", "turn": 2, "delta": "c"}]
    out = without_reset_text([e | {"seq": i} for i, e in enumerate(events)])
    assert [e["delta"] for e in out] == ["a", "c"]
    clean = [{"event": "debate_token", "turn": 1, "delta": "x", "seq": 0}]
    assert without_reset_text(clean) == clean
