"use client";

import { useEffect } from "react";
import { create } from "zustand";
import { ApiError, whatIf } from "@/lib/api";
import type { WhatIfRequest, WhatIfResponse } from "@/lib/types";
import { useActiveRun, useRunStore } from "@/store/run-store";

export type Draft = Omit<WhatIfRequest, "run_id">;
export const EMPTY_DRAFT: Draft = Object.freeze({});
export const useWhatIfDraft = create<{
  drafts: Record<string, Draft>;
  pending: Record<string, boolean>;
  errors: Record<string, string | undefined>;
  set: (id: string, patch: Partial<Draft>) => void;
  reset: (id: string) => void;
}>((set) => ({
  drafts: {}, pending: {}, errors: {},
  set: (id, patch) => set((s) => ({ drafts: { ...s.drafts, [id]: { ...s.drafts[id], ...patch } } })),
  reset: (id) => {
    useRunStore.getState().setWhatIf(id, undefined);
    set((s) => ({ drafts: { ...s.drafts, [id]: EMPTY_DRAFT }, errors: { ...s.errors, [id]: undefined } }));
  },
}));

// The cleanup invalidates even a transport that resolves after being aborted.
export function debounceSimulation(
  request: (signal: AbortSignal) => Promise<WhatIfResponse>,
  accept: (value: WhatIfResponse) => void,
  reject: (error: unknown) => void,
  delay = 180,
) {
  const controller = new AbortController();
  let current = true;
  const timer = setTimeout(() => {
    request(controller.signal).then((value) => { if (current) accept(value); })
      .catch((error) => { if (current && !controller.signal.aborted) reject(error); });
  }, delay);
  return () => { current = false; clearTimeout(timer); controller.abort(); };
}

// Mount once in the room, not in each responsive copy of the analytics panel.
export function useWhatIfSimulation() {
  const id = useRunStore((s) => s.activeRunId);
  const probability = useActiveRun((r) => r.probability);
  const draft = useWhatIfDraft((s) => id ? s.drafts[id] ?? EMPTY_DRAFT : EMPTY_DRAFT);
  useEffect(() => {
    if (!id || !probability) return;
    const current = () => useRunStore.getState().activeRunId === id
      && (useWhatIfDraft.getState().drafts[id] ?? EMPTY_DRAFT) === draft;
    const status = (pending: boolean, error?: string) => useWhatIfDraft.setState((s) => ({
      pending: { ...s.pending, [id]: pending }, errors: { ...s.errors, [id]: error },
    }));
    useRunStore.getState().setWhatIf(id, undefined);
    status(Object.keys(draft).length > 0);
    if (!Object.keys(draft).length) return;
    return debounceSimulation((signal) => whatIf({ ...draft, run_id: id }, signal), (value) => {
      if (!current()) return;
      useRunStore.getState().setWhatIf(id, value);
      status(false);
    }, (error) => {
      if (!current()) return;
      status(false, error instanceof ApiError && [404, 503].includes(error.status)
        ? "Simulation is not ready for this run. Try the fictional demo or reset your changes."
        : "The simulation could not be updated. Change a control to retry, or reset.");
    });
  }, [id, draft, probability]);
}

export function cfToDraft(cf: import("@/lib/types").Counterfactual): Partial<Draft> {
  switch (cf.kind) {
    case "major_switch": return { major_category: cf.id.replace(/^cf_major_/, "") };
    case "test_score": return cf.overrides.sat === null ? { withhold_sat: true }
      : typeof cf.overrides.sat === "number" ? { sat: cf.overrides.sat, withhold_sat: false } : {};
    case "add_activity": return { add_activities: [2] };
    case "early_round": return { early_round: cf.overrides.early_round as Draft["early_round"] };
    case "demonstrated_interest": return { demonstrated_interest: true };
    case "essay": return { essay_steps: 1 };
  }
}
