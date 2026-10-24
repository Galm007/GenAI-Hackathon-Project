import type { ProbabilityComponent, ProbabilityData } from "./data";

export const pct = (x: number) => `${(x * 100).toFixed(x < 0.1 ? 1 : 0)}%`;
export const validProbability = (x: number) => Number.isFinite(x) && x >= 0 && x <= 1;

export function buildWaterfallRows(components: ProbabilityComponent[]) {
  let cumulative = 0;
  return components.map((c) => {
    const start = c.key === "base" ? 0 : cumulative;
    cumulative = c.key === "base" ? c.delta_pp : start + c.delta_pp;
    return { ...c, start, end: cumulative, offset: Math.min(start, cumulative),
      value: Math.abs(cumulative - start), sign: c.key === "base" ? "base" : c.delta_pp >= 0 ? "up" : "down" };
  });
}

export function breakdownDifference(probability: ProbabilityData) {
  const rows = buildWaterfallRows(probability.components);
  return (rows.at(-1)?.end ?? 0) - probability.p_final * 100;
}
