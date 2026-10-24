"use client";
import { useEffect } from "react";
import { API } from "./api";
import type { Envelope } from "./types";
import { useRunStore } from "@/store/run-store";

export type RunSource = { kind: "live"; runId: string } | { kind: "demo"; name: string };

export const EVENT_TYPES = [
  "run_started", "node_start", "node_end", "node_complete", "progress", "tool_call", "dossier_parsed", "scorecard",
  "school_rubric", "fact_checks", "twins", "baseline", "radar", "twin_analysis", "probability",
  "debate_turn_start", "debate_token", "debate_reset", "debate_turn_end", "citation_warning",
  "counterfactuals", "final_report", "error", "done",
] as const;

export const runIdOf = (src: RunSource) => (src.kind === "live" ? src.runId : `demo-${src.name}`);

export function connectStream(runId: string, streamUrl?: string): () => void {
  if (typeof window === "undefined") return () => {};

  const { ensureRun, applyMany } = useRunStore.getState();
  ensureRun(runId);

  const url = streamUrl ?? `${API}/api/evaluate/${runId}/stream`;
  let es: EventSource;
  try {
    es = new EventSource(url);
  } catch {
    return () => {};
  }

  let buffer: Envelope[] = [];
  let raf = 0;
  const flush = () => {
    raf = 0;
    if (buffer.length) {
      applyMany(runId, buffer);
      buffer = [];
    }
  };

  const onEvent = (e: MessageEvent<string>) => {
    try {
      const env = JSON.parse(e.data) as Envelope;
      buffer.push(env);
      if (env.event === "done") {
        flush();
        es.close();
        return;
      }
      if (!raf) raf = requestAnimationFrame(flush);
    } catch {
      // ignore parse error
    }
  };

  EVENT_TYPES.forEach((t) => es.addEventListener(t, onEvent as EventListener));

  return () => {
    es.close();
    if (raf) cancelAnimationFrame(raf);
  };
}

export function useRunStream(src: RunSource) {
  const { ensureRun, setActive, setParentRunId } = useRunStore.getState();
  const key = src.kind === "live" ? src.runId : src.name;

  useEffect(() => {
    const runId = runIdOf(src);
    ensureRun(runId);
    setActive(runId);
    setParentRunId(runId);

    const url = src.kind === "live"
      ? `${API}/api/evaluate/${src.runId}/stream`
      : `${API}/api/demo/${src.name}/stream`;

    return connectStream(runId, url);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [src.kind, key]);
}
