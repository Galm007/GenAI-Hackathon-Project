"use client";

import { useReducedMotion } from "framer-motion";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Highlight, ProbabilityData } from "./data";
import { breakdownDifference, buildWaterfallRows } from "./math";

export function Waterfall({ probability, highlight }: { probability: ProbabilityData | null; highlight?: Highlight | null }) {
  const reduced = useReducedMotion();
  const rows = buildWaterfallRows(probability?.components ?? []);
  if (!rows.length) return <div className="grid h-72 place-items-center rounded-xl bg-panel-2 text-sm text-muted" aria-busy="true">Waiting for a breakdown</div>;
  if (rows.some((r) => !Number.isFinite(r.end))) return <p role="status">The breakdown is unavailable.</p>;
  const mismatch = probability && Math.abs(breakdownDifference(probability)) > 0.5;
  return (
    <figure aria-label="Admission estimate breakdown, in percentage points">
      <div className="h-72" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ left: 0, right: 20, top: 8, bottom: 8 }}>
            <XAxis type="number" domain={[Math.min(0, ...rows.map((r) => r.end)), "dataMax"]}
              tickFormatter={(v: number) => `${v}%`} stroke="var(--color-muted)" fontSize={11} />
            <YAxis type="category" dataKey="label" width={125} stroke="var(--color-muted)" fontSize={11} tickLine={false} />
            <Tooltip cursor={{ fill: "var(--color-panel-2)" }} wrapperStyle={{ maxWidth: 240 }}
              contentStyle={{ background: "var(--color-panel)", borderColor: "var(--color-line)", borderRadius: 12, whiteSpace: "normal", fontSize: 12 }}
              labelStyle={{ color: "var(--color-ink)" }} itemStyle={{ color: "var(--color-ink)", whiteSpace: "normal" }}
              formatter={(_value, _name, item) => [`${item.payload.delta_pp >= 0 ? "+" : ""}${item.payload.delta_pp.toFixed(1)} pp · ${item.payload.detail}`, item.payload.label]} />
            <Bar dataKey="offset" stackId="waterfall" fill="transparent" isAnimationActive={false} tooltipType="none" />
            <Bar dataKey="value" stackId="waterfall" radius={4} isAnimationActive={!reduced} animationDuration={700}>
              {rows.map((r) => <Cell key={r.key} fill={r.sign === "base" ? "var(--color-muted)" : r.sign === "up" ? "var(--color-admit)" : "var(--color-deny)"}
                stroke={highlight?.kind === "model" && highlight.ref === r.key ? "var(--color-tier1)" : undefined} strokeWidth={3} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="text-xs text-muted">School base rate, then each contribution. Green increases and coral decreases the estimate.</figcaption>
      {mismatch && <p role="status" className="mt-2 text-xs text-waitlist">The supplied contributions differ from the final estimate; the breakdown needs verification.</p>}
      <details className="mt-3 text-xs">
        <summary className="cursor-pointer text-muted">Read the numbers and evidence</summary>
        <table className="mt-2 w-full text-left"><caption className="sr-only">Contribution details</caption>
          <thead><tr><th className="py-2">Factor</th><th>Change</th><th>Evidence</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.key} className="border-t border-line">
            <th scope="row" className="py-2 pr-2 font-medium">{r.label}</th>
            <td className="pr-3 font-mono">{r.delta_pp >= 0 ? "+" : ""}{r.delta_pp.toFixed(1)} pp</td><td>{r.detail}</td>
          </tr>)}</tbody>
        </table>
      </details>
    </figure>
  );
}
