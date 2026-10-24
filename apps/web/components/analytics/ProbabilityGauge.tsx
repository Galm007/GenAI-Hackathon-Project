"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { ProbabilityData, SimulationData } from "./data";
import { validProbability } from "./math";

const COLOR = { ADMIT: "var(--color-admit)", "LIKELY ADMIT": "var(--color-admit)", WAITLIST: "var(--color-waitlist)",
  "LIKELY DENY": "var(--color-deny)", DENY: "var(--color-deny)" };
const point = (p: number, r: number) => {
  const a = (150 + p * 240) * Math.PI / 180;
  return { x: 160 + r * Math.cos(a), y: 132 + r * Math.sin(a) };
};
const arc = (from: number, to: number, r: number) => {
  const a = point(from, r), b = point(to, r);
  return `M ${a.x} ${a.y} A ${r} ${r} 0 ${to - from > 0.75 ? 1 : 0} 1 ${b.x} ${b.y}`;
};
const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

export function ProbabilityGauge({ probability, simulation }: { probability: ProbabilityData | null; simulation?: SimulationData | null }) {
  const reduced = useReducedMotion();
  const simulated = !!simulation?.applied.length;
  const shown = simulated ? simulation!.simulated : probability;
  if (!shown || !validProbability(shown.p_final)) return <div className="grid h-64 place-items-center rounded-xl bg-panel-2/50 text-sm text-muted" aria-busy="true">Waiting for an estimate</div>;
  const range = shown.p_low !== null && shown.p_high !== null && validProbability(shown.p_low)
    && validProbability(shown.p_high) && shown.p_low <= shown.p_final && shown.p_final <= shown.p_high;
  const color = simulated ? "var(--color-advocate)" : shown.disposition ? COLOR[shown.disposition] : "var(--color-advocate)";
  const end = point(shown.p_final, 102);
  return <figure aria-label={`Estimated admission probability ${percent(shown.p_final)}${simulated ? ", simulated" : ""}`}>
    <svg viewBox="0 0 320 225" className="mx-auto w-full max-w-[360px] overflow-visible" aria-hidden="true">
      <path d={arc(0, 1, 102)} fill="none" stroke="var(--color-line)" strokeWidth="14" strokeLinecap="round" />
      {range && shown.p_high! > shown.p_low! && <path d={arc(shown.p_low!, shown.p_high!, 119)} fill="none" stroke={color} strokeOpacity="0.28" strokeWidth="3" strokeLinecap="round" />}
      <motion.path d={arc(0, 1, 102)} fill="none" stroke={color} strokeWidth="14" strokeLinecap="round"
        initial={reduced ? false : { pathLength: 0 }} animate={{ pathLength: shown.p_final }} transition={{ duration: reduced ? 0 : 0.9, ease: [0.16, 1, 0.3, 1] }} />
      <circle cx={end.x} cy={end.y} r="5" fill="var(--color-ink)" stroke={color} strokeWidth="3" />
      <text x="160" y="105" textAnchor="middle" fill="var(--color-muted)" fontSize="9" letterSpacing="2">ESTIMATED ADMISSION</text>
      <text x="160" y="157" textAnchor="middle" fill="var(--color-ink)" fontSize="49" fontFamily="var(--font-display)" fontWeight="600">{percent(shown.p_final)}</text>
      <text x="160" y="181" textAnchor="middle" fill={color} fontSize="10" letterSpacing="1.5">{simulated ? "SIMULATED SCENARIO" : shown.disposition ?? "MODEL ESTIMATE"}</text>
      <text x="49" y="207" fill="var(--color-muted)" fontSize="10" textAnchor="middle">0%</text>
      <text x="271" y="207" fill="var(--color-muted)" fontSize="10" textAnchor="middle">100%</text>
    </svg>
    <figcaption className="space-y-3 text-center text-xs text-muted" aria-live="polite">
      <div className="flex items-center justify-center gap-2 font-mono">
        <span className="rounded-md border border-line bg-room/40 px-2.5 py-1.5">{range ? `80% range ${percent(shown.p_low!)}–${percent(shown.p_high!)}` : "Range unavailable"}</span>
        {simulated && <span className="rounded-md border border-advocate/30 bg-advocate/10 px-2.5 py-1.5 text-advocate">{simulation!.delta_pp >= 0 ? "+" : ""}{simulation!.delta_pp.toFixed(1)} pp</span>}
      </div>
      <p className="mx-auto max-w-[30ch] leading-relaxed">An uncertain model estimate. The university makes the admission decision.</p>
    </figcaption>
  </figure>;
}
