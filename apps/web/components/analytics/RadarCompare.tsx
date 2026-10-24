"use client";

import { useReducedMotion } from "framer-motion";
import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts";
import type { RadarData } from "./data";
import { comparableAxes, formatRaw } from "./math";

interface AxisTick { x?: number; y?: number; cx?: number; cy?: number; textAnchor?: "start" | "middle" | "end"; payload?: { value: string } }

export function RadarCompare({ radar }: { radar: RadarData | null }) {
  const reduced = useReducedMotion();
  if (!radar) return <div className="grid h-72 place-items-center rounded-xl bg-panel-2 text-sm text-muted" aria-busy="true">Waiting for comparable profiles</div>;
  const complete = comparableAxes(radar);
  const omitted = radar.axes.filter((a) => !complete.includes(a));
  const data = complete.map((a) => ({ ...a, axis: a.assumed ? `${a.label}*` : a.label, admitted: a.admitted_median }));
  const tick = ({ x = 0, y = 0, cx = 0, cy = 0, textAnchor, payload }: AxisTick) => {
    const assumed = data.find((a) => a.axis === payload?.value)?.assumed;
    const label = payload?.value ?? "";
    const lines = label.startsWith("Essay & Personal") ? ["Essay &", "Personal*"]
      : label === "Spike (T1/T2)" ? ["Spike", "(T1/T2)"] : [label];
    return <g>
      <line x1={cx} y1={cy} x2={x} y2={y} stroke={assumed ? "var(--color-waitlist)" : "var(--color-line)"}
        strokeDasharray={assumed ? "4 4" : undefined} data-assumed-axis={assumed || undefined} />
      <text x={x} y={y} dy={lines.length > 1 ? -2 : 4} textAnchor={textAnchor} fill={assumed ? "var(--color-waitlist)" : "var(--color-muted)"} fontSize={11}>
        {lines.map((line, i) => <tspan key={line} x={x} dy={i ? 12 : 0}>{line}</tspan>)}
      </text>
    </g>;
  };
  return (
    <figure aria-label="Applicant compared with admitted applicant medians">
      {complete.length >= 3 ? <div className="h-80" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} outerRadius="65%" margin={{ left: 22, right: 22 }}>
            <PolarGrid stroke="var(--color-line)" radialLines={false} />
            <PolarAngleAxis dataKey="axis" tick={tick} tickLine={false} axisLine={false} />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            <Radar name="Admitted median" dataKey="admitted" stroke="var(--color-tier2)" strokeDasharray="4 3"
              fill="var(--color-tier2)" fillOpacity={0.08} isAnimationActive={!reduced} animationDuration={900} />
            <Radar name="You" dataKey="you" stroke="var(--color-advocate)" fill="var(--color-advocate)"
              fillOpacity={0.25} isAnimationActive={!reduced} animationDuration={900} />
            <Tooltip wrapperStyle={{ maxWidth: 200 }} contentStyle={{ background: "var(--color-panel)", borderColor: "var(--color-line)", borderRadius: 12, fontSize: 12 }}
              labelStyle={{ color: "var(--color-ink)" }} itemStyle={{ color: "var(--color-ink)" }}
              formatter={(_value, name, item) => [formatRaw(name === "You" ? item.payload.you_raw : item.payload.admitted_raw), name]} />
          </RadarChart>
        </ResponsiveContainer>
      </div> : <p className="grid h-72 place-items-center text-sm text-muted">At least three comparable axes are needed for the chart.</p>}
      <figcaption className="space-y-2 text-xs text-muted">
        <p><span className="text-advocate">● You</span> <span className="ml-3 text-tier2">┄ Admitted median</span> · {radar.n_admitted} admitted profiles</p>
        <p><span className="text-waitlist">*Dashed Personal axis: assumed reference.</span> Twins have no essays; its reference rating is 3.0, not an observed admitted median.</p>
        {omitted.length > 0 && <p role="status">Not plotted: {omitted.map((a) => a.label).join(", ")} (missing comparable values).</p>}
      </figcaption>
      <details className="mt-3 text-xs"><summary className="cursor-pointer text-muted">Read the comparison values</summary>
        <table className="mt-2 w-full table-fixed text-left"><caption className="sr-only">Raw comparison values; chart uses normalized 0-100 scores</caption>
          <colgroup><col className="w-1/2" /><col className="w-1/4" /><col className="w-1/4" /></colgroup>
          <thead><tr><th className="py-2">Axis</th><th className="text-right">You</th><th className="text-right">Reference</th></tr></thead>
          <tbody>{radar.axes.map((a) => <tr key={a.key} className="border-t border-line">
            <th scope="row" className="py-2 pr-2 font-medium">{a.label}{a.assumed ? " (assumed)" : ""}</th>
            <td className="text-right font-mono">{formatRaw(a.you_raw)}</td><td className="text-right font-mono">{formatRaw(a.admitted_raw)}</td>
          </tr>)}</tbody>
        </table>
      </details>
    </figure>
  );
}
