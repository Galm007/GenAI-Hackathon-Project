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

/** A proxy that buffers SSE (Cloudflare quick tunnels do) shows nothing until the run ends. When the stream goes quiet,
 * live runs are read from the plain-JSON events endpoint instead; both sources are de-duplicated by `seq`. */
export const STALL_MS = 4000;
export const POLL_MS = 1500;

export function pollUrlFor(streamUrl: string): string | null {
  const m = streamUrl.match(/^(.*\/api\/evaluate\/[^/?#]+)\/stream(?:[?#].*)?$/);
  return m ? `${m[1]}/events` : null;
}

export function connectStream(runId: string, streamUrl?: string): () => void {
  if (typeof window === "undefined") return () => {};

  const { ensureRun, applyMany } = useRunStore.getState();
  ensureRun(runId);

  const url = streamUrl ?? `${API}/api/evaluate/${runId}/stream`;
  const pollUrl = pollUrlFor(url);
  let es: EventSource;
  try {
    es = new EventSource(url);
  } catch {
    return () => {};
  }

  let buffer: Envelope[] = [];
  let raf = 0;
  let lastSeq = -1;
  let lastSseAt = Date.now();
  let finished = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let polling = false;

  const flush = () => {
    raf = 0;
    if (buffer.length) {
      applyMany(runId, buffer);
      buffer = [];
    }
  };

  const stop = () => {
    finished = true;
    es.close();
    if (timer) clearTimeout(timer);
  };

  const ingest = (env: Envelope) => {
    if (finished || env.seq <= lastSeq) return;
    lastSeq = env.seq;
    buffer.push(env);
    if (env.event === "done") {
      flush();
      stop();
      return;
    }
    if (!raf) raf = requestAnimationFrame(flush);
  };

  const onEvent = (e: MessageEvent<string>) => {
    try {
      lastSseAt = Date.now();
      ingest(JSON.parse(e.data) as Envelope);
    } catch {
      // ignore parse error
    }
  };

  EVENT_TYPES.forEach((t) => es.addEventListener(t, onEvent as EventListener));

  const poll = async () => {
    if (finished || !pollUrl) return;
    if (!polling && Date.now() - lastSseAt > STALL_MS) {
      polling = true;
      try {
        const res = await fetch(`${pollUrl}?after=${lastSeq}`, { cache: "no-store" });
        if (res.status === 404) return stop();
        if (res.ok) ((await res.json()).events as Envelope[]).forEach(ingest);
      } catch {
        // transient network error: try again on the next tick
      } finally {
        polling = false;
      }
    }
    if (!finished) timer = setTimeout(poll, POLL_MS);
  };
  if (pollUrl) timer = setTimeout(poll, POLL_MS);

  return () => {
    finished = true;
    es.close();
    if (timer) clearTimeout(timer);
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
