import { create } from "zustand";
import type {
  Baseline, Counterfactual, DebateTurn, DeltaReport, Dossier, DossierGrade, Envelope, InstitutionalBrief,
  Metrics, NodeName, ProbabilityBreakdown, RadarData, SchoolRubric, ToolCall, TwinAnalysis, TwinCard,
  WebSnippet, WhatIfResponse, ZetarisQuery,
} from "@/lib/types";

export type NodeStatus = "pending" | "running" | "done" | "degraded";
export const NODES: NodeName[] = [
  "dossier_parser", "institutional", "twins", "committee_docket", "advocate", "chair", "delta_engine",
];

export interface RunView {
  runId: string;
  schoolSlug?: string;
  status: "connecting" | "running" | "complete" | "failed";
  lastSeq: number;
  startedAt?: number;
  finishedAt?: number;
  nodes: Record<NodeName, NodeStatus>;
  progress: Partial<Record<NodeName, string>>;
  tools: ToolCall[];
  dossier?: Dossier;
  metrics?: Metrics;
  grade?: DossierGrade;
  rubric?: SchoolRubric;
  brief?: InstitutionalBrief | null;
  snippets: WebSnippet[];
  sqlQueries: ZetarisQuery[];                       // Zetaris evidence Z1…Zn
  twins: TwinCard[];
  baseline?: Baseline;
  radar?: RadarData;
  twinAnalysis?: TwinAnalysis | null;
  probability?: ProbabilityBreakdown;
  debate: DebateTurn[];
  citationWarnings: string[];
  counterfactuals: Counterfactual[];
  report?: DeltaReport;
  errors: { node: string | null; message: string; recoverable: boolean }[];
}

export const emptyRun = (runId: string): RunView => ({
  runId, status: "connecting", lastSeq: -1,
  nodes: Object.fromEntries(NODES.map((n) => [n, "pending"])) as Record<NodeName, NodeStatus>,
  progress: {}, tools: [], snippets: [], sqlQueries: [], twins: [], debate: [], citationWarnings: [], counterfactuals: [], errors: [],
});

const upsertTurn = (turns: DebateTurn[], t: DebateTurn) =>
  turns.some((x) => x.turn === t.turn) ? turns.map((x) => (x.turn === t.turn ? t : x)) : [...turns, t];

export function reduce(r: RunView, ev: Envelope): RunView {
  if (ev.seq <= r.lastSeq) return r;                                   // idempotent replay
  const n: RunView = { ...r, lastSeq: ev.seq };
  const setNode = (node: NodeName, s: NodeStatus) => {
    if (n.nodes[node] === "degraded" && s === "done") return;
    n.nodes = { ...n.nodes, [node]: s };
  };
  switch (ev.event) {
    case "run_started":
      n.status = "running"; n.schoolSlug = ev.school_slug; n.startedAt = ev.ts;
      if (ev.cached_dossier) setNode("dossier_parser", "done");
      break;
    case "node_start": setNode(ev.node, "running"); break;
    case "node_end":
    case "node_complete": setNode(ev.node, "done"); break;
    case "progress": n.progress = { ...n.progress, [ev.node]: ev.message }; break;
    case "tool_call": n.tools = [...n.tools.slice(-40), ev as unknown as ToolCall]; break;
    case "dossier_parsed": n.dossier = ev.dossier; n.metrics = ev.metrics; break;
    case "scorecard": n.grade = ev.grade; n.metrics = ev.metrics; break;
    case "school_rubric": n.rubric = ev.rubric; break;
    case "fact_checks": n.brief = ev.brief; n.snippets = ev.snippets; n.sqlQueries = ev.zetaris_queries ?? []; break;
    case "twins": n.twins = ev.twins; break;
    case "baseline": n.baseline = ev.baseline; break;
    case "radar": n.radar = ev.radar; break;
    case "twin_analysis": n.twinAnalysis = ev.analysis; break;
    case "probability": n.probability = ev.probability; setNode("committee_docket", "done"); break;
    case "debate_turn_start":
      setNode(ev.speaker, "running");
      n.debate = upsertTurn(n.debate, { turn: ev.turn, speaker: ev.speaker, content: "", citations: [],
                                        recommendation: null, degraded: false, streaming: true });
      break;
    case "debate_token":
      n.debate = n.debate.map((t) => (t.turn === ev.turn ? { ...t, content: t.content + ev.delta } : t));
      break;
    case "debate_reset":
      n.debate = n.debate.map((t) => (t.turn === ev.turn ? { ...t, content: "" } : t));
      break;
    case "debate_turn_end":
      n.debate = upsertTurn(n.debate, {
        turn: ev.turn, speaker: ev.speaker, content: ev.content, citations: ev.citations,
        recommendation: ev.recommendation, degraded: ev.degraded, streaming: false,
      });
      if (ev.turn === 4) { setNode("advocate", "done"); setNode("chair", "done"); }
      break;
    case "citation_warning": n.citationWarnings = [...n.citationWarnings, ...ev.refs]; break;
    case "counterfactuals": n.counterfactuals = ev.counterfactuals; break;
    case "final_report": n.report = ev.report; break;
    case "error":
      n.errors = [...n.errors, { node: ev.node, message: ev.message, recoverable: ev.recoverable }];
      if (ev.node && ev.recoverable) n.nodes = { ...n.nodes, [ev.node]: "degraded" };
      break;
    case "done":
      n.status = ev.status === "complete" ? "complete" : "failed"; n.finishedAt = ev.ts;
      break;
  }
  return n;
}

export type Highlight = { kind: "dossier" | "cds" | "twin" | "web" | "model" | "sql"; ref: string } | null;

export interface RunStore {
  runs: Record<string, RunView>;
  activeRunId?: string;
  highlight: Highlight;
  whatIf: Record<string, WhatIfResponse | undefined>;
  ensureRun: (id: string) => void;
  setActive: (id: string) => void;
  applyMany: (id: string, evs: Envelope[]) => void;
  setHighlight: (h: Highlight) => void;
  setWhatIf: (id: string, r: WhatIfResponse | undefined) => void;
}

export const useRunStore = create<RunStore>((set) => ({
  runs: {},
  highlight: null,
  whatIf: {},
  ensureRun: (id) => set((s) => (s.runs[id] ? s : { runs: { ...s.runs, [id]: emptyRun(id) } })),
  setActive: (id) => set({ activeRunId: id }),
  applyMany: (id, evs) =>
    set((s) => ({ runs: { ...s.runs, [id]: evs.reduce(reduce, s.runs[id] ?? emptyRun(id)) } })),
  setHighlight: (highlight) => set({ highlight }),
  setWhatIf: (id, r) => set((s) => ({ whatIf: { ...s.whatIf, [id]: r } })),
}));

// Narrow selectors: components re-render only when their slice changes.
const EMPTY = emptyRun("");                       // stable fallback → no new references per render
export const useActiveRun = <T,>(pick: (r: RunView) => T) =>
  useRunStore((s) => pick(s.runs[s.activeRunId ?? ""] ?? EMPTY));
