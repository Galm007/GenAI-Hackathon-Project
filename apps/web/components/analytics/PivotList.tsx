"use client";

import { ArrowUpRight, Sparkles } from "lucide-react";
import { useActiveRun, useRunStore } from "@/store/run-store";
import type { Counterfactual } from "@/lib/types";
import { cfToDraft, useWhatIfDraft } from "./what-if";

export function PivotList({ onTry }: { onTry?: () => void }) {
  const id = useRunStore((s) => s.activeRunId);
  const report = useActiveRun((r) => r.report);
  const cfs = useActiveRun((r) => r.counterfactuals);
  const tryIt = (cf: Counterfactual) => {
    if (!id) return;
    useWhatIfDraft.getState().reset(id);
    useWhatIfDraft.getState().set(id, cfToDraft(cf));
    onTry?.();
  };
  const cards = report?.ranked_pivots ?? cfs.map((cf) => ({ counterfactual_id: cf.id, title: cf.label,
    why_it_works: cf.evidence, concrete_steps: [], effort: null, tradeoffs: "" }));
  if (!cards.length) return null;
  return <section aria-label="Potential improvements" className="space-y-3">
    <h3 className="flex items-center gap-2 font-display text-lg"><Sparkles className="size-4 text-tier1" />Your next moves</h3>
    {cards.map((pivot, i) => {
      const cf = cfs.find((c) => c.id === pivot.counterfactual_id);
      const hero = i === 0 && cf?.kind === "major_switch";
      return <article key={`${pivot.counterfactual_id}-${i}`} className={`space-y-3 rounded-xl border p-4 ${hero ? "border-advocate/40 bg-gradient-to-br from-advocate/10 to-panel" : "border-line bg-panel-2/40"}`}>
        {hero && <p className="text-[10px] uppercase tracking-[0.2em] text-advocate">Major arbitrage</p>}
        <div className="flex items-start justify-between gap-3"><h4 className="text-sm font-semibold leading-relaxed">{pivot.title}</h4>
          {cf && <span className={`shrink-0 rounded-md px-2 py-1 font-mono text-xs ${cf.delta_pp >= 0 ? "bg-admit/10 text-admit" : "bg-deny/10 text-deny"}`}>{cf.id === "cf_promote_t3" && "≈"}{cf.delta_pp >= 0 ? "+" : ""}{cf.delta_pp.toFixed(1)} pp</span>}
        </div>
        <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-wider text-muted">
          {cf && <span className={cf.confidence === "data_backed" ? "text-admit" : "text-waitlist"}>{cf.confidence === "data_backed" ? "Data-backed" : "Model estimate"}</span>}
          {pivot.effort && <span>· {pivot.effort}</span>}
        </div>
        <p className="text-xs leading-relaxed text-muted">{pivot.why_it_works}</p>
        {pivot.concrete_steps.length > 0 && <ol className="list-decimal space-y-1.5 pl-4 text-xs leading-relaxed">{pivot.concrete_steps.map((step) => <li key={step}>{step}</li>)}</ol>}
        {pivot.tradeoffs && <p className="border-l-2 border-line pl-3 text-xs italic leading-relaxed text-muted">{pivot.tradeoffs}</p>}
        {hero && report?.major_arbitrage_note && <p className="text-xs leading-relaxed text-muted">{report.major_arbitrage_note}</p>}
        {cf ? <button type="button" onClick={() => tryIt(cf)} className="inline-flex items-center gap-1 rounded-lg border border-advocate/30 px-3 py-2 text-xs font-semibold text-advocate hover:bg-advocate/10">Try it<ArrowUpRight className="size-3.5" /></button>
          : <p className="text-xs text-muted">No computed scenario available for this suggestion.</p>}
      </article>;
    })}
  </section>;
}
