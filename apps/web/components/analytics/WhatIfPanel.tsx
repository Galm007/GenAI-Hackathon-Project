"use client";

import { useId } from "react";
import { RotateCcw, SlidersHorizontal } from "lucide-react";
import { useActiveRun, useRunStore } from "@/store/run-store";
import { EMPTY_DRAFT, useWhatIfDraft, type Draft } from "./what-if";

const MAJORS = ["computer_science", "math_stats", "data_science", "electrical_engineering", "physics_astro",
  "economics", "biology", "neuroscience", "business", "undecided"];
const human = (value: string) => value.replaceAll("_", " ");

export function WhatIfPanel() {
  const prefix = useId();
  const id = useRunStore((s) => s.activeRunId);
  const probability = useActiveRun((r) => r.probability);
  const rubric = useActiveRun((r) => r.rubric);
  const metrics = useActiveRun((r) => r.metrics);
  const cfs = useActiveRun((r) => r.counterfactuals);
  const simulation = useRunStore((s) => id ? s.whatIf[id] : undefined);
  const draft = useWhatIfDraft((s) => id ? s.drafts[id] ?? EMPTY_DRAFT : EMPTY_DRAFT);
  const pending = useWhatIfDraft((s) => id ? s.pending[id] : false);
  const error = useWhatIfDraft((s) => id ? s.errors[id] : undefined);
  const set = (patch: Partial<Draft>) => { if (id) useWhatIfDraft.getState().set(id, patch); };
  const majors = [...new Set([rubric?.major_category, ...cfs.filter((c) => c.kind === "major_switch")
    .map((c) => c.id.replace(/^cf_major_/, "")), ...MAJORS].filter(Boolean))] as string[];
  const sat = draft.sat ?? metrics?.sat_equivalent ?? 1400;
  const selectClass = "mt-2 w-full rounded-lg border border-line bg-room px-3 py-2.5 text-sm capitalize text-ink focus-visible:outline-2 focus-visible:outline-advocate";
  return <section aria-labelledby={`${prefix}-title`} className="space-y-5">
    <div className="flex items-center justify-between gap-3">
      <h3 id={`${prefix}-title`} className="flex items-center gap-2 font-display text-lg"><SlidersHorizontal className="size-4 text-advocate" />Explore a change</h3>
      <button type="button" className="flex items-center gap-1.5 rounded-lg border border-line px-2.5 py-1.5 text-xs text-muted hover:text-ink disabled:opacity-40"
        onClick={() => id && useWhatIfDraft.getState().reset(id)} disabled={!id || !Object.keys(draft).length}><RotateCcw className="size-3" />Reset</button>
    </div>
    <p className="text-xs leading-relaxed text-muted">Change one assumption at a time. The same scoring model recalculates the estimate.</p>
    <fieldset disabled={!id || !probability} className="space-y-5 disabled:opacity-45">
      <label className="block text-xs text-muted">SAT score <span className="float-right font-mono text-ink">{draft.withhold_sat ? "Withheld" : sat}</span>
        <input type="range" aria-label="SAT score" min={400} max={1600} step={10} value={sat} disabled={!!draft.withhold_sat}
          onChange={(e) => set({ sat: Number(e.target.value) })} className="mt-3 h-2 w-full cursor-pointer accent-advocate" />
        <span className="mt-1 block text-[11px]">School middle 50%: {rubric?.sat_25 ?? "unknown"}–{rubric?.sat_75 ?? "unknown"}{metrics?.sat_equivalent == null && " · Slider starts at a hypothetical 1400"}</span>
      </label>
      {rubric?.test_policy !== "required" && <label className="flex items-center justify-between gap-3 text-sm">
        Apply test-optional<input type="checkbox" checked={!!draft.withhold_sat} onChange={(e) => set({ withhold_sat: e.target.checked })} className="size-4 accent-advocate" />
      </label>}
      <label className="block text-xs text-muted">Intended major
        <select aria-label="Intended major" className={selectClass} value={draft.major_category ?? rubric?.major_category ?? "undecided"}
          onChange={(e) => set({ major_category: e.target.value })}>{majors.map((m) => {
            const cf = cfs.find((c) => c.id === `cf_major_${m}`);
            return <option key={m} value={m}>{human(m)}{cf ? ` (${cf.delta_pp >= 0 ? "+" : ""}${cf.delta_pp.toFixed(1)} pp)` : ""}</option>;
          })}</select>
      </label>
      <label className="flex items-center justify-between gap-3 text-sm">Add a Tier 2 activity
        <input type="checkbox" checked={(draft.add_activities ?? []).includes(2)} onChange={(e) => set({ add_activities: e.target.checked ? [2] : [] })} className="size-4 accent-advocate" />
      </label>
      <label className="block text-xs text-muted">Essay strength <span className="float-right font-mono text-ink">+{draft.essay_steps ?? 0} rating steps</span>
        <input type="range" aria-label="Essay strength" min={0} max={2} step={1} value={draft.essay_steps ?? 0}
          onChange={(e) => set({ essay_steps: Number(e.target.value) as 0 | 1 | 2 })} className="mt-3 h-2 w-full cursor-pointer accent-advocate" />
      </label>
      <label className="block text-xs text-muted">Application round
        <select aria-label="Application round" className={selectClass} value={draft.early_round ?? "RD"}
          onChange={(e) => set({ early_round: e.target.value as Draft["early_round"] })}>{["RD", "EA", "REA", "ED", "ED2"].map((round) => <option key={round}>{round}</option>)}</select>
      </label>
      {rubric && rubric.factor_levels.applicant_interest !== "not_considered" && <label className="flex items-center justify-between gap-3 text-sm">Demonstrated interest
        <input type="checkbox" checked={!!draft.demonstrated_interest} onChange={(e) => set({ demonstrated_interest: e.target.checked })} className="size-4 accent-advocate" />
      </label>}
    </fieldset>
    <div aria-live="polite" className="text-xs leading-relaxed">
      {pending && <p role="status" className="text-muted">Recalculating your scenario…</p>}
      {error && <p role="alert" className="rounded-lg border border-waitlist/30 bg-waitlist/5 p-3 text-waitlist">{error}</p>}
      {simulation && <div className="space-y-2 rounded-lg border border-advocate/30 bg-advocate/5 p-3">
        <p className="font-mono text-ink">{simulation.delta_pp >= 0 ? "+" : ""}{simulation.delta_pp.toFixed(1)} pp <span className="text-muted">· {simulation.confidence === "data_backed" ? "Data-backed change" : "Model estimate"}</span></p>
        {simulation.applied.length > 0 && <p className="text-muted">{simulation.applied.join(" · ")}</p>}
        {simulation.warnings.map((warning) => <p key={warning} className="text-waitlist">{warning}</p>)}
      </div>}
    </div>
  </section>;
}
