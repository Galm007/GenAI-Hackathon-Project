// Presentation inputs, structurally compatible with the frozen Python outputs.
// C02 can pass its shared types directly; these components do not own the store.
export type Disposition = "ADMIT" | "LIKELY ADMIT" | "WAITLIST" | "LIKELY DENY" | "DENY";
export interface ProbabilityComponent {
  key: string; label: string; delta_logit: number; delta_pp: number; detail: string;
}
export interface ProbabilityData {
  p_final: number; p_low: number | null; p_high: number | null;
  disposition: Disposition | null; components: ProbabilityComponent[];
}
export interface SimulationData {
  simulated: ProbabilityData; applied: string[]; delta_pp: number;
}
export interface Highlight { kind: string; ref: string }
