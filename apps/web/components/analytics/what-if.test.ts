import { afterEach, describe, expect, it, vi } from "vitest";
import type { Counterfactual, WhatIfResponse } from "@/lib/types";
import { useRunStore } from "@/store/run-store";
import { cfToDraft, debounceSimulation, useWhatIfDraft } from "./what-if";

afterEach(() => vi.useRealTimers());
describe("scenario request lifecycle", () => {
  it("debounces requests and cancels work before the delay", async () => {
    vi.useFakeTimers();
    const request = vi.fn();
    const cancel = debounceSimulation(request, vi.fn(), vi.fn());
    cancel();
    await vi.runAllTimersAsync();
    expect(request).not.toHaveBeenCalled();
  });
  it("aborts in-flight work and ignores a response from a transport that resolves late", async () => {
    vi.useFakeTimers();
    let resolve!: (value: WhatIfResponse) => void;
    let signal!: AbortSignal;
    const accept = vi.fn();
    const cancel = debounceSimulation((s) => { signal = s; return new Promise((r) => { resolve = r; }); }, accept, vi.fn());
    await vi.advanceTimersByTimeAsync(180);
    cancel();
    resolve({ delta_pp: 99 } as WhatIfResponse);
    await vi.runAllTimersAsync();
    expect(signal.aborted).toBe(true);
    expect(accept).not.toHaveBeenCalled();
  });
  it("reports a current failure so an old simulation is never silently presented as current", async () => {
    vi.useFakeTimers();
    const reject = vi.fn();
    debounceSimulation(() => Promise.reject(new Error("offline")), vi.fn(), reject);
    await vi.runAllTimersAsync();
    expect(reject).toHaveBeenCalledOnce();
  });
  it("keeps school drafts separate and resets only the selected result", () => {
    useWhatIfDraft.getState().set("uiuc", { sat: 1500 });
    useWhatIfDraft.getState().set("cmu", { essay_steps: 1 });
    useRunStore.getState().setWhatIf("uiuc", { delta_pp: 8 } as WhatIfResponse);
    useWhatIfDraft.getState().reset("uiuc");
    expect(useWhatIfDraft.getState().drafts.uiuc).toEqual({});
    expect(useWhatIfDraft.getState().drafts.cmu).toEqual({ essay_steps: 1 });
    expect(useRunStore.getState().whatIf.uiuc).toBeUndefined();
  });
  it("a score pivot turns off withholding and a test-optional pivot does not invent a score", () => {
    const cf: Counterfactual = { id: "cf_test", kind: "test_score", label: "Test", p_new: 0.2,
      delta_pp: 0, confidence: "model_estimate", evidence: "Fictional test", overrides: { sat: 1550 } };
    expect(cfToDraft(cf))
      .toEqual({ sat: 1550, withhold_sat: false });
    expect(cfToDraft({ ...cf, overrides: { sat: null } })).toEqual({ withhold_sat: true });
  });
});
