"use client";

import { useRef } from "react";
import { ArrowUpRight, BarChart3, Fingerprint, ChevronDown } from "lucide-react";
import { useActiveRun, useRunStore } from "@/store/run-store";
import { ProbabilityGauge } from "./ProbabilityGauge";
import { Waterfall } from "./Waterfall";
import { RadarCompare } from "./RadarCompare";
import { TwinCards } from "./TwinCards";
import { WhatIfPanel } from "./WhatIfPanel";
import { PivotList } from "./PivotList";
import { EssayEdits } from "./EssayEdits";

export function AnalyticsPanel() {
  const id = useRunStore((s) => s.activeRunId);
  const simulation = useRunStore((s) => id ? s.whatIf[id] : undefined);
  const highlight = useRunStore((s) => s.highlight);
  const probability = useActiveRun((r) => r.probability);
  const radar = useActiveRun((r) => r.radar);
  const twins = useActiveRun((r) => r.twins);
  const baseline = useActiveRun((r) => r.baseline);
  const comparisons = useActiveRun((r) => r.twinAnalysis?.comparisons);
  const status = useActiveRun((r) => r.status);
  const shown = simulation?.applied.length ? simulation.simulated : probability;
  const controls = useRef<HTMLDetailsElement>(null);
  const openControls = () => {
    if (!controls.current) return;
    controls.current.open = true;
    controls.current.scrollIntoView({ block: "nearest", behavior: "smooth" });
  };
  return <div className="min-w-0 space-y-5 pb-6">
    <div className="flex items-center justify-between border-b border-line pb-4">
      <div><p className="mb-1 text-[9px] uppercase tracking-[0.24em] text-advocate">Evidence → possibilities</p>
        <h2 className="font-display text-xl">Your admissions outlook</h2></div>
      <ArrowUpRight className="size-5 text-muted" aria-hidden="true" />
    </div>
    <section className="rounded-2xl border border-line bg-gradient-to-b from-panel-2/70 to-panel p-4 shadow-lg shadow-black/10" aria-label="Admission estimate">
      <ProbabilityGauge probability={probability ?? null} simulation={simulation} />
    </section>
    <details ref={controls} className="group rounded-xl border border-advocate/25 bg-advocate/5">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-4 text-sm font-semibold"><span>What could change your outlook?</span><ChevronDown className="size-4 text-advocate transition group-open:rotate-180" /></summary>
      <div className="border-t border-line p-4"><WhatIfPanel /></div>
    </details>
    <section className="rounded-xl border border-line bg-panel p-4" aria-label="Probability factors">
      <h3 className="mb-4 flex items-center gap-2 font-display text-lg"><BarChart3 className="size-4 text-advocate" />Behind the estimate</h3>
      <Waterfall probability={shown ?? null} highlight={highlight} />
    </section>
    <section className="rounded-xl border border-line bg-panel p-4" aria-label="Profile comparison">
      <h3 className="flex items-center gap-2 font-display text-lg"><Fingerprint className="size-4 text-advocate" />Your profile in context</h3>
      {!radar && status === "complete" ? <p className="py-8 text-sm leading-relaxed text-muted">This run has no comparable-profile chart. Missing data is not a zero score.</p> : <RadarCompare radar={radar ?? null} />}
    </section>
    <TwinCards twins={twins.length || status === "complete" ? twins : null} baseline={baseline} comparisons={comparisons} highlight={highlight} />
    <PivotList onTry={openControls} />
    <EssayEdits />
  </div>;
}
