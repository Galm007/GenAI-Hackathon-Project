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
export interface RadarAxis {
  key: string; label: string; you: number | null; admitted_median: number | null;
  you_raw: number | null; admitted_raw: number | null; assumed: boolean;
}
export interface RadarData { n_admitted: number; axes: RadarAxis[] }
export interface TwinData {
  index: number; id: string; source_url: string; cycle_year: number | null;
  outcome: "accepted" | "waitlisted" | "rejected"; headline: string | null;
  gpa_uw: number | null; sat_score: number | null; act_score: number | null;
  spike_summary: string | null; semantic_similarity: number; stat_proximity: number; hybrid_score: number;
  top_activities: { description: string; role: string | null; tier: 1 | 2 | 3 | 4 }[];
}
export interface BaselineData {
  n_neighbors: number; n_accepted: number; n_waitlisted: number; n_rejected: number;
  n_effective: number; odds_inflation: number; widened_to_peers: boolean;
}
export interface ComparisonData {
  twin_index: number; key_similarity: string; key_difference: string; plausible_deciding_factor: string;
}
