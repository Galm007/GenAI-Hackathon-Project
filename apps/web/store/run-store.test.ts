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

  describe("fake_stream.json replay", () => {
    it("drives full run to completion from fake stream fixture", async () => {
      const fs = await import("fs");
      const path = await import("path");
      const fixturePath = path.resolve(__dirname, "../../../data/fixtures/fake_stream.json");
      const raw = fs.readFileSync(fixturePath, "utf-8");
      const fixture = JSON.parse(raw);

      useRunStore.setState({ runs: {}, activeRunId: undefined, highlight: null, whatIf: {} });
      const store = useRunStore.getState();
      store.ensureRun("fake");

      // Apply the 72 events from the fake stream
      store.applyMany("fake", fixture.events);

      const run = useRunStore.getState().runs["fake"];
      expect(run).toBeDefined();
      expect(run.schoolSlug).toBe("uiuc");
      expect(run.status).toBe("complete");
      expect(run.nodes.dossier_parser).toBe("done");
      expect(run.nodes.institutional).toBe("done");
      expect(run.nodes.twins).toBe("done");
      expect(run.nodes.committee_docket).toBe("done");
      expect(run.nodes.advocate).toBe("done");
      expect(run.nodes.chair).toBe("done");
      expect(run.tools.length).toBeGreaterThan(0);
      expect(run.twins.length).toBe(5);
      expect(run.debate.length).toBe(2);
      expect(run.probability).toBeDefined();
      expect(run.probability?.disposition).toBe("WAITLIST");
      expect(run.counterfactuals.length).toBeGreaterThan(0);
      expect(run.report).toBeDefined();
    });
  });

  describe("C07: child runs, degraded states, and Zetaris queries", () => {
    it("marks dossier_parser as done immediately when cached_dossier is true", () => {
      let run = emptyRun("child-run");
      run = reduce(run, {
        seq: 0,
        run_id: "child-run",
        ts: 1000,
        event: "run_started",
        school_slug: "cmu",
        cached_dossier: true,
      });

      expect(run.nodes.dossier_parser).toBe("done");
      expect(run.status).toBe("running");
      expect(run.schoolSlug).toBe("cmu");
    });

    it("preserves degraded node status when node_complete arrives later", () => {
      let run = emptyRun("run-deg");
      // Node starts
      run = reduce(run, { seq: 0, run_id: "run-deg", ts: 1000, event: "node_start", node: "institutional" });
      expect(run.nodes.institutional).toBe("running");

      // Recoverable error occurs -> degraded
      run = reduce(run, {
        seq: 1,
        run_id: "run-deg",
        ts: 1001,
        event: "error",
        node: "institutional",
        message: "Zetaris query timeout; falling back to local CDS",
        recoverable: true,
      });
      expect(run.nodes.institutional).toBe("degraded");
      expect(run.errors.length).toBe(1);

      // Subsequent node_complete should NOT overwrite degraded to done
      run = reduce(run, { seq: 2, run_id: "run-deg", ts: 1002, event: "node_complete", node: "institutional" });
      expect(run.nodes.institutional).toBe("degraded");
    });

    it("populates sqlQueries on fact_checks event", () => {
      let run = emptyRun("run-zetaris");
      const mockQuery = {
        id: "Z1",
        purpose: "QueryGraingerAcceptanceRate",
        sql: "SELECT admit_rate FROM ADCOM_PG.universities_cds WHERE slug = 'uiuc'",
        rows: [{ admit_rate: "0.22" }],
        error: null,
      };

      run = reduce(run, {
        seq: 5,
        run_id: "run-zetaris",
        ts: 1005,
        event: "fact_checks",
        brief: null,
        snippets: [],
        zetaris_queries: [mockQuery],
      });

      expect(run.sqlQueries.length).toBe(1);
      expect(run.sqlQueries[0]?.id).toBe("Z1");
      expect(run.sqlQueries[0]?.rows).toEqual([{ admit_rate: "0.22" }]);
    });

    it("startChildRun sets up child run with skipped Node 1, copied dossier, and tabs map", async () => {
      useRunStore.setState({
        runs: {},
        tabs: {},
        activeRunId: undefined,
        parentRunId: undefined,
        targetSchools: ["uiuc", "cmu", "umich"],
      });

      const store = useRunStore.getState();
      const parentRun = emptyRun("parent-1");
      parentRun.schoolSlug = "uiuc";
      parentRun.dossier = {
        high_school: { name: "Central High", state: "IL", school_type: "Public" },
        activities: [],
        awards: [],
        courses: [],
        test_scores: { sat_total: 1520, act_composite: null },
      };
      parentRun.grade = {
        harvard: {} as any,
        spike: { label: "USACO", description: "Competitive coding", strength: "strong" },
        activity_grades: [],
        reader_comments: "Strong applicant",
        grader_warnings: [],
        major_category: "computer_science",
        rigor_label: "most_demanding",
        essay: null,
      };
      useRunStore.setState({
        runs: { "parent-1": parentRun },
        activeRunId: "parent-1",
        parentRunId: "parent-1",
        tabs: { uiuc: "parent-1" },
      });

      // Start child run for CMU
      const childRunId = await useRunStore.getState().startChildRun("cmu");
      expect(childRunId).toBeDefined();

      const state = useRunStore.getState();
      expect(state.activeRunId).toBe(childRunId);
      expect(state.tabs["cmu"]).toBe(childRunId);

      const childRun = state.runs[childRunId];
      expect(childRun).toBeDefined();
      expect(childRun.schoolSlug).toBe("cmu");
      expect(childRun.status).toBe("running");
      // Node 1 skipped:
      expect(childRun.nodes.dossier_parser).toBe("done");
      // Node 2 running:
      expect(childRun.nodes.institutional).toBe("running");
      // Dossier & grade copied:
      expect(childRun.dossier?.test_scores.sat_total).toBe(1520);
      expect(childRun.grade?.spike?.strength).toBe("strong");
    });
  });
});
