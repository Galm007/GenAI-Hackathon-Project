"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ExternalLink } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import type { ComparisonData, TwinData } from "./data";
import { safeSourceUrl } from "./math";

const OUTCOME = {
  accepted: { label: "Accepted", icon: "✓", color: "text-admit bg-admit/10" },
  waitlisted: { label: "Waitlisted", icon: "◐", color: "text-waitlist bg-waitlist/10" },
  rejected: { label: "Rejected", icon: "✕", color: "text-deny bg-deny/10" },
};

export function TwinCard({ twin, highlighted = false, comparison }: {
  twin: TwinData; highlighted?: boolean; comparison?: ComparisonData;
}) {
  const [open, setOpen] = useState(false);
  const reduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const detailsId = useId();
  const outcome = OUTCOME[twin.outcome];
  const source = safeSourceUrl(twin.source_url);
  useEffect(() => {
    if (highlighted) ref.current?.scrollIntoView({ block: "nearest", behavior: reduced ? "auto" : "smooth" });
  }, [highlighted, reduced]);
  return (
    <motion.div ref={ref} data-highlighted={highlighted}
      className={`rounded-xl border bg-panel transition-shadow ${highlighted ? "border-tier1 ring-2 ring-tier1" : "border-line"}`}
      animate={{ boxShadow: highlighted && !reduced ? ["0 0 0px #e8c26800", "0 0 22px #e8c26870", "0 0 8px #e8c26830"] : "0 0 0px #e8c26800" }}
      transition={{ duration: reduced ? 0 : 0.8 }}>
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-controls={detailsId}
        className="flex w-full flex-wrap items-center gap-2 rounded-xl p-3 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-advocate">
        <span className="grid size-7 place-items-center rounded-full bg-panel-2 font-mono text-xs">{twin.index}</span>
        <span className={`rounded px-2 py-1 font-mono text-[10px] font-bold ${outcome.color}`}>{outcome.icon} {outcome.label}</span>
        <span className="min-w-0 flex-1 text-xs">{twin.headline ?? "Comparable applicant"}</span>
        <span className="font-mono text-[10px] text-muted">{Math.round(twin.hybrid_score * 100)}% similarity</span>
        {highlighted && <span className="sr-only">Highlighted evidence</span>}
      </button>
      <AnimatePresence initial={false}>
        {open && <motion.div id={detailsId} initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }} transition={{ duration: reduced ? 0 : 0.2 }} className="overflow-hidden">
          <div className="space-y-3 border-t border-line p-3 text-xs">
            <dl className="flex flex-wrap gap-x-5 gap-y-1 font-mono text-muted">
              <div><dt className="inline">GPA: </dt><dd className="inline">{twin.gpa_uw ?? "Unknown"}</dd></div>
              <div><dt className="inline">SAT: </dt><dd className="inline">{twin.sat_score ?? "Unknown"}</dd></div>
              <div><dt className="inline">ACT: </dt><dd className="inline">{twin.act_score ?? "Unknown"}</dd></div>
            </dl>
            {twin.spike_summary && <p><span className="text-muted">Spike: </span>{twin.spike_summary}</p>}
            <ul className="space-y-2">{twin.top_activities.map((a, i) => <li key={i} className="flex items-start gap-2">
              <span className="shrink-0 rounded bg-panel-2 px-2 py-1 font-mono text-[10px] text-tier1">Tier {a.tier}</span>
              <span>{a.role && <strong>{a.role}: </strong>}{a.description}</span>
            </li>)}</ul>
            {comparison && <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-2">
              <dt className="text-muted">Similar</dt><dd>{comparison.key_similarity}</dd>
              <dt className="text-muted">Different</dt><dd>{comparison.key_difference}</dd>
              <dt className="text-muted">Possible factor</dt><dd>{comparison.plausible_deciding_factor}</dd>
            </dl>}
            <p className="text-muted">Cycle {twin.cycle_year ?? "unknown"} · Semantic {Math.round(twin.semantic_similarity * 100)}% · Statistics {Math.round(twin.stat_proximity * 100)}%</p>
            {source ? <a href={source} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-advocate underline">
              Original post <ExternalLink className="size-3" aria-hidden="true" />
            </a> : <p className="text-muted">Source unavailable</p>}
          </div>
        </motion.div>}
      </AnimatePresence>
    </motion.div>
  );
}
