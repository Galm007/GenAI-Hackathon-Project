"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { Highlight, ProbabilityData } from "./data";
import { breakdownDifference, buildWaterfallRows } from "./math";

export function Waterfall({ probability, highlight }: { probability: ProbabilityData | null; highlight?: Highlight | null }) {
  const reduced = useReducedMotion();
  const rows = buildWaterfallRows(probability?.components ?? []);
  if (!rows.length) return <div className="grid h-64 place-items-center rounded-xl bg-panel-2/50 text-sm text-muted" aria-busy="true">Waiting for a breakdown</div>;
  if (rows.some((r) => !Number.isFinite(r.end))) return <p role="status">The breakdown is unavailable.</p>;
  const lo = Math.min(0, ...rows.flatMap((r) => [r.start, r.end]));
  const hi = Math.max(100, ...rows.flatMap((r) => [r.start, r.end]));
  const x = (value: number) => 8 + (value - lo) / (hi - lo) * 344;
  const height = rows.length * 49 + 30;
  const ticks = [lo, lo + (hi - lo) / 4, (hi + lo) / 2, hi - (hi - lo) / 4, hi];
  const mismatch = !!probability && Math.abs(breakdownDifference(probability)) > 0.5;
  return <figure aria-label="Admission estimate breakdown, in percentage points">
    <svg viewBox={`0 0 360 ${height}`} className="w-full" aria-hidden="true">
      {rows.map((row, i) => {
        const y = 17 + i * 49;
        const color = row.sign === "base" ? "var(--color-advocate)" : row.sign === "up" ? "var(--color-admit)" : "var(--color-deny)";
        const active = highlight?.kind === "model" && highlight.ref === row.key;
        return <g key={row.key} data-highlighted={active || undefined}>
          <title>{row.label}: {row.delta_pp >= 0 ? "+" : ""}{row.delta_pp.toFixed(1)} percentage points. {row.detail}</title>
          {active && <rect x="0" y={y - 13} width="360" height="45" rx="6" fill="var(--color-tier1)" fillOpacity="0.08" stroke="var(--color-tier1)" strokeOpacity="0.7" />}
          <text x="8" y={y} fill="var(--color-ink)" fontSize="11">{row.label}</text>
          <text x="352" y={y} textAnchor="end" fill={color} fontSize="10" fontFamily="var(--font-mono)">{row.delta_pp >= 0 ? "+" : ""}{row.delta_pp.toFixed(1)} pp</text>
          <line x1="8" x2="352" y1={y + 16} y2={y + 16} stroke="var(--color-line)" strokeWidth="1" />
          {i > 0 && <line x1={x(row.start)} x2={x(row.start)} y1={y - 33} y2={y + 16} stroke="var(--color-muted)" strokeDasharray="2 3" strokeOpacity="0.4" />}
          <motion.rect x={x(row.offset)} y={y + 11} width={row.value / (hi - lo) * 344} height="10" rx="3" fill={color}
            initial={reduced ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: reduced ? 0 : i * 0.05 }} />
          <circle cx={x(row.end)} cy={y + 16} r="2.5" fill="var(--color-ink)" />
        </g>;
      })}
      {ticks.map((tick, i) => <text key={i} x={x(tick)} y={height - 5} textAnchor={i === 0 ? "start" : i === 4 ? "end" : "middle"} fill="var(--color-muted)" fontSize="9">{tick.toFixed(0)}%</text>)}
    </svg>
    <figcaption className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted"><span><span className="text-admit">+ </span>Increases estimate</span><span><span className="text-deny">− </span>Decreases estimate</span><span>Dot = running total</span></figcaption>
    {mismatch && <p role="status" className="mt-3 text-xs leading-relaxed text-waitlist">The supplied contributions differ from the final estimate; this breakdown needs verification.</p>}
    <details className="mt-4 text-xs">
      <summary className="cursor-pointer text-muted hover:text-ink">Read the numbers and evidence</summary>
      <div className="mt-3 overflow-x-auto"><table className="w-full text-left leading-relaxed"><caption className="sr-only">Contribution details</caption>
        <thead><tr className="text-muted"><th className="py-2 pr-3">Factor</th><th className="pr-3">Change</th><th>Evidence</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.key} className="border-t border-line"><th scope="row" className="py-2 pr-3 font-medium">{r.label}</th>
          <td className="whitespace-nowrap pr-3 font-mono">{r.delta_pp >= 0 ? "+" : ""}{r.delta_pp.toFixed(1)} pp</td><td className="min-w-[150px] py-2 text-muted">{r.detail}</td></tr>)}</tbody>
      </table></div>
    </details>
  </figure>;
}
