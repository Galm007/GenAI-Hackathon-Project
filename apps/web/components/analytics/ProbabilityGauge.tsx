"use client";

import { animate, motion, useMotionValue, useReducedMotion, useTransform } from "framer-motion";
import { useEffect } from "react";
import { PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer } from "recharts";
import type { ProbabilityData, SimulationData } from "./data";
import { pct, validProbability } from "./math";

const COLOR = {
  ADMIT: "var(--color-admit)", "LIKELY ADMIT": "var(--color-admit)", WAITLIST: "var(--color-waitlist)",
  "LIKELY DENY": "var(--color-deny)", DENY: "var(--color-deny)",
};

export function ProbabilityGauge({ probability, simulation }: {
  probability: ProbabilityData | null; simulation?: SimulationData | null;
}) {
  const reduced = useReducedMotion();
  const simulated = !!simulation?.applied.length;
  const shown = simulated ? simulation!.simulated : probability;
  const ready = !!shown && validProbability(shown.p_final);
  const target = ready ? shown!.p_final * 100 : 0;
  const value = useMotionValue(0);
  const label = useTransform(value, (v) => `${v.toFixed(v < 10 ? 1 : 0)}%`);
  useEffect(() => {
    const controls = animate(value, target, { duration: reduced ? 0 : 1.1, ease: [0.16, 1, 0.3, 1] });
    return () => controls.stop();
  }, [target, value, reduced]);
  if (!ready || !shown) return (
    <div className="grid h-64 place-items-center rounded-xl bg-panel-2 text-sm text-muted" aria-busy="true">
      Waiting for an estimate
    </div>
  );
  const range = shown.p_low !== null && shown.p_high !== null && validProbability(shown.p_low)
    && validProbability(shown.p_high) && shown.p_low <= shown.p_final && shown.p_final <= shown.p_high;
  const color = shown.disposition ? COLOR[shown.disposition] : "var(--color-advocate)";
  return (
    <figure aria-label={`Estimated admission probability ${pct(shown.p_final)}${simulated ? ", simulated" : ""}`}>
      <div className="relative h-64" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart innerRadius="80%" outerRadius="100%" startAngle={210} endAngle={-30} data={[{ value: target }]}>
            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
            <RadialBar dataKey="value" cornerRadius={12} background={{ fill: "var(--color-panel-2)" }}
              fill={color} isAnimationActive={!reduced} animationDuration={1100} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
          <div>
            <p className="text-[11px] uppercase tracking-[0.2em] text-muted">Estimated admission</p>
            <motion.p className="font-display text-6xl font-semibold tabular-nums">{label}</motion.p>
            <p className="mt-1 font-mono text-xs text-muted">
              {range ? `80% range ${pct(shown.p_low!)}–${pct(shown.p_high!)}` : "Range unavailable"}
            </p>
            {shown.disposition && <p className="mt-2 text-sm font-semibold" style={{ color }}>{shown.disposition}</p>}
          </div>
        </div>
      </div>
      <figcaption className="text-center text-xs text-muted" aria-live="polite">
        <span className="sr-only">{pct(shown.p_final)}. {range ? `80% range ${pct(shown.p_low!)} to ${pct(shown.p_high!)}` : "Range unavailable"}. </span>
        {simulated && <span className="mb-2 inline-block rounded-full bg-advocate/15 px-3 py-1 font-mono text-advocate">
          Simulated {simulation!.delta_pp >= 0 ? "+" : ""}{simulation!.delta_pp.toFixed(1)} pp
        </span>}
        <p>A model estimate, with uncertainty. Admission decisions remain with the university.</p>
      </figcaption>
    </figure>
  );
}
