import { describe, it, expect, beforeEach } from "vitest";
import { emptyRun, reduce, useRunStore } from "./run-store";
import type { Envelope, ToolCall } from "@/lib/types";

describe("run-store reducer", () => {
  it("initializes an empty run with pending nodes and status connecting", () => {
    const run = emptyRun("run-1");
    expect(run.runId).toBe("run-1");
    expect(run.status).toBe("connecting");
    expect(run.lastSeq).toBe(-1);
    expect(run.nodes.dossier_parser).toBe("pending");
    expect(run.debate).toEqual([]);
    expect(run.tools).toEqual([]);
  });

  describe("idempotent replay (seq <= lastSeq ignored)", () => {
    it("ignores events where seq <= lastSeq", () => {
      let run = emptyRun("run-1");
      const ev1: Envelope = {
        seq: 5,
        run_id: "run-1",
        ts: 1000,
        event: "run_started",
        school_slug: "uiuc",
      };
      run = reduce(run, ev1);
      expect(run.lastSeq).toBe(5);
      expect(run.status).toBe("running");
      expect(run.schoolSlug).toBe("uiuc");

      // Replay of same seq
      const evReplay: Envelope = {
        seq: 5,
        run_id: "run-1",
        ts: 1005,
        event: "run_started",
        school_slug: "cmu",
      };
      const unchanged = reduce(run, evReplay);
      expect(unchanged).toBe(run);
      expect(unchanged.schoolSlug).toBe("uiuc");

      // Stale earlier event seq < lastSeq
      const evStale: Envelope = {
        seq: 2,
        run_id: "run-1",
        ts: 900,
        event: "node_start",
        node: "dossier_parser",
      };
      const stillUnchanged = reduce(run, evStale);
      expect(stillUnchanged).toBe(run);
      expect(stillUnchanged.nodes.dossier_parser).toBe("pending");
    });
  });

  describe("debate streaming and token batching", () => {
    it("accumulates tokens across debate_token events for the active turn", () => {
      let run = emptyRun("run-1");

      // Start turn 1
      run = reduce(run, {
        seq: 1,
        run_id: "run-1",
        ts: 100,
        event: "debate_turn_start",
        turn: 1,
        speaker: "advocate",
      });
      expect(run.debate.length).toBe(1);
      expect(run.debate[0].content).toBe("");
      expect(run.debate[0].streaming).toBe(true);
      expect(run.nodes.advocate).toBe("running");

      // Stream tokens
      run = reduce(run, {
        seq: 2,
        run_id: "run-1",
        ts: 110,
        event: "debate_token",
        turn: 1,
        delta: "Maya's spike ",
      });
      run = reduce(run, {
        seq: 3,
        run_id: "run-1",
        ts: 120,
        event: "debate_token",
        turn: 1,
        delta: "is competitive programming.",
      });

      expect(run.debate[0].content).toBe("Maya's spike is competitive programming.");

      // End turn 1
      run = reduce(run, {
        seq: 4,
        run_id: "run-1",
        ts: 130,
        event: "debate_turn_end",
        turn: 1,
        speaker: "advocate",
        content: "Maya's spike is competitive programming.",
        citations: [],
        recommendation: "ADMIT",
        degraded: false,
      });

      expect(run.debate[0].streaming).toBe(false);
      expect(run.debate[0].recommendation).toBe("ADMIT");
    });

    it("resets debate tokens on debate_reset event", () => {
      let run = emptyRun("run-1");
      run = reduce(run, {
        seq: 1,
        run_id: "run-1",
        ts: 100,
        event: "debate_turn_start",
        turn: 1,
        speaker: "chair",
      });
      run = reduce(run, {
        seq: 2,
        run_id: "run-1",
        ts: 110,
        event: "debate_token",
        turn: 1,
        delta: "Bad draft",
      });
      expect(run.debate[0].content).toBe("Bad draft");

      run = reduce(run, {
        seq: 3,
        run_id: "run-1",
        ts: 115,
        event: "debate_reset",
        turn: 1,
      });
      expect(run.debate[0].content).toBe("");
    });
  });

  describe("batch application (applyMany)", () => {
    beforeEach(() => {
      useRunStore.setState({ runs: {}, activeRunId: undefined, highlight: null, whatIf: {} });
    });

    it("applies a batch of token frames efficiently via useRunStore.applyMany", () => {
      const store = useRunStore.getState();
      store.ensureRun("batch-run");

      const batch: Envelope[] = [
        { seq: 1, run_id: "batch-run", ts: 10, event: "run_started", school_slug: "uiuc" },
        { seq: 2, run_id: "batch-run", ts: 20, event: "node_start", node: "advocate" },
        { seq: 3, run_id: "batch-run", ts: 30, event: "debate_turn_start", turn: 1, speaker: "advocate" },
        { seq: 4, run_id: "batch-run", ts: 40, event: "debate_token", turn: 1, delta: "Token A " },
        { seq: 5, run_id: "batch-run", ts: 50, event: "debate_token", turn: 1, delta: "Token B " },
        { seq: 6, run_id: "batch-run", ts: 60, event: "debate_token", turn: 1, delta: "Token C" },
      ];

      store.applyMany("batch-run", batch);

      const state = useRunStore.getState().runs["batch-run"];
      expect(state.lastSeq).toBe(6);
      expect(state.status).toBe("running");
      expect(state.debate[0].content).toBe("Token A Token B Token C");
    });
  });

  describe("node and artifact lifecycle", () => {
    it("handles cached dossier optimization", () => {
      let run = emptyRun("run-cached");
      run = reduce(run, {
        seq: 1,
        run_id: "run-cached",
        ts: 10,
        event: "run_started",
        school_slug: "uiuc",
        cached_dossier: true,
      });
      expect(run.nodes.dossier_parser).toBe("done");
    });

    it("caps tools history at 40 items", () => {
      let run = emptyRun("run-tools");
      for (let i = 1; i <= 50; i++) {
        run = reduce(run, {
          seq: i,
          run_id: "run-tools",
          ts: i * 10,
          event: "tool_call",
          node: "institutional",
          tool: `tool_${i}`,
          status: "done",
        });
      }
      expect(run.tools.length).toBe(41);
      expect((run.tools[0] as ToolCall).tool).toBe("tool_10");
      expect((run.tools[40] as ToolCall).tool).toBe("tool_50");
    });

    it("marks node degraded on recoverable error and does not overwrite with done", () => {
      let run = emptyRun("run-err");
      run = reduce(run, {
        seq: 1,
        run_id: "run-err",
        ts: 10,
        event: "error",
        node: "institutional",
        message: "Timeout reaching Tavily",
        recoverable: true,
      });
      expect(run.nodes.institutional).toBe("degraded");
      expect(run.errors.length).toBe(1);

      // Subsequent node_complete should not overwrite degraded
      run = reduce(run, {
        seq: 2,
        run_id: "run-err",
        ts: 20,
        event: "node_complete",
        node: "institutional",
      });
      expect(run.nodes.institutional).toBe("degraded");
    });

    it("completes debate turns and sets both advocate and chair done at turn 4", () => {
      let run = emptyRun("run-debate-end");
      run = reduce(run, {
        seq: 1,
        run_id: "run-debate-end",
        ts: 100,
        event: "debate_turn_end",
        turn: 4,
        speaker: "chair",
        content: "Final verdict rendered",
        citations: [],
        recommendation: "WAITLIST",
        degraded: false,
      });
      expect(run.nodes.advocate).toBe("done");
      expect(run.nodes.chair).toBe("done");
    });
  });
});
