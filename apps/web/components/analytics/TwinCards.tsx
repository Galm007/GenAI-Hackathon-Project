"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useId } from "react";
import type { BaselineData, ComparisonData, Highlight, TwinData } from "./data";
import { TwinCard } from "./TwinCard";

export function TwinCards({ twins, baseline, comparisons = [], highlight }: {
  twins: TwinData[] | null; baseline?: BaselineData | null;
  comparisons?: ComparisonData[]; highlight?: Highlight | null;
}) {
  const reduced = useReducedMotion();
  const titleId = useId();
  return <section aria-labelledby={titleId} className="space-y-3">
    <h2 id={titleId} className="font-display text-xl">Comparable applicants</h2>
    {baseline && <p className="font-mono text-[11px] leading-5 text-muted">
      {baseline.n_neighbors} nearest: {baseline.n_accepted} accepted · {baseline.n_waitlisted} waitlisted · {baseline.n_rejected} rejected
      <br />Effective sample {baseline.n_effective.toFixed(1)} · Reddit bias ×{baseline.odds_inflation.toFixed(1)} corrected
      {baseline.widened_to_peers && " · Includes peer schools"}
    </p>}
    {twins === null ? <div className="grid h-64 place-items-center rounded-xl bg-panel-2 text-sm text-muted" aria-busy="true">Waiting for comparable applicants</div>
      : twins.length === 0 ? <p className="py-8 text-sm text-muted">No comparable applicants available.</p>
      : <ol className="space-y-3">{twins.map((t, i) => <motion.li key={t.id}
        initial={reduced ? false : { opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: reduced ? 0 : i * 0.1 }}>
        <TwinCard twin={t} highlighted={highlight?.kind === "twin" && highlight.ref === String(t.index)}
          comparison={comparisons.find((c) => c.twin_index === t.index)} />
      </motion.li>)}</ol>}
  </section>;
}
