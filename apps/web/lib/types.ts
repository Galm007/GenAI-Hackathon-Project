export type Outcome = "accepted" | "waitlisted" | "rejected";
export type Speaker = "advocate" | "chair";
export type Disposition = "ADMIT" | "LIKELY ADMIT" | "WAITLIST" | "LIKELY DENY" | "DENY";
export type Pillar = "academic" | "extracurricular" | "personal" | "athletic";
export type NodeName =
  | "dossier_parser" | "institutional" | "twins" | "committee_docket" | "advocate" | "chair" | "delta_engine";
export type NodeStatus = "pending" | "running" | "done" | "degraded";
export type Tier = 1 | 2 | 3 | 4;

export interface PillarRating {
  rationale: string; evidence: string[]; rating: 1 | 2 | 3 | 4 | 5 | 6; modifier: "+" | "" | "-";
}
export interface ActivityGrade {
  activity_index: number; rationale: string; tier: Tier; spike_role: "core" | "supporting" | "peripheral";
}
export interface DossierGrade {
  major_category: string; rigor_label: string; activity_grades: ActivityGrade[];
  spike: { label: string; description: string; strength: "strong" | "moderate" | "emerging" | "none" };
  essay: { themes: string[]; voice: string; strengths: string[]; weaknesses: string[]; red_flags: string[];
           strongest_line: string | null } | null;
  harvard: Record<Pillar, PillarRating>; reader_comments: string; grader_warnings: string[];
}
export interface Metrics {
  gpa_uw_4: number | null; gpa_w_5: number | null; core_course_count: number; advanced_course_count: number;
  rigor_index: number | null; grade_trend: "upward" | "flat" | "downward" | "insufficient_data";
  sat_equivalent: number | null; proxy_academic_rating: number; tier_derived_ec_rating: number; ec_score: number;
}
export interface Activity {
  name: string; role: string | null; organization: string | null; description: string; category: string;
  grades: number[]; hours_per_week: number | null; weeks_per_year: number | null;
}
export interface Dossier {
  high_school: { name: string | null; state: string | null; school_type: string };
  activities: Activity[]; awards: { name: string; level: string; grade: number | null }[];
  courses: { title: string; level: string; grade_level: number | null; grade_as_shown: string | null }[];
  test_scores: { sat_total: number | null; act_composite: number | null };
}
export interface SchoolRubric {
  slug: string; name: string; base_admit_rate: number; pillar_weights: Record<Pillar, number>;
  factor_levels: Record<string, "very_important" | "important" | "considered" | "not_considered">;
  test_policy: string; sat_25: number | null; sat_75: number | null; major_category: string;
  major_multiplier: number; major_multiplier_source: string; major_college: string | null;
  direct_admit: boolean | null; notes: string[];
}
export interface WebSnippet { id: string; url: string; title: string; content: string; published: string | null }
export interface FactCheck {
  field: string; db_value: string | null; web_value: string | null;
  verdict: "confirmed" | "updated" | "conflict" | "unverified"; source_ids: string[]; note: string;
}
export interface InstitutionalBrief {
  fact_checks: FactCheck[]; strategic_priorities: { claim: string; source_ids: string[]; relevance_to_applicant: string }[];
  current_test_policy: string; major_admission_model: string; major_notes: string;
  fit_signals: string[]; misalignment_signals: string[]; analyst_summary: string;
}
export interface TwinCard {
  index: number; id: string; source_url: string; cycle_year: number | null; matched_school: string; outcome: Outcome;
  gpa_uw: number | null; sat_score: number | null; act_score: number | null; ap_count: number | null;
  intended_major: string | null; major_category: string; hooks: string[];
  ec_tier_summary: { tier1?: number; tier2?: number; tier3?: number; tier4?: number };
  top_activities: { description: string; role: string | null; tier: Tier }[]; awards: { name: string; level: string }[];
  spike_summary: string | null; headline: string | null;
  semantic_similarity: number; stat_proximity: number; hybrid_score: number;
}
export interface Baseline {
  n_neighbors: number; n_accepted: number; n_waitlisted: number; n_rejected: number; n_effective: number;
  weighted_admit_rate: number | null; wilson_low: number | null; wilson_high: number | null;
  odds_inflation: number; deflated_admit_rate: number | null; widened_to_peers: boolean; peer_schools: string[];
}
export interface TwinAnalysis {
  comparisons: { twin_index: number; key_similarity: string; key_difference: string; plausible_deciding_factor: string }[];
  pattern_summary: string; pattern_strength: "strong" | "moderate" | "weak"; applicant_gaps: string[]; applicant_edges: string[];
}
export interface RadarAxis {
  key: string; label: string; you: number | null; admitted_median: number | null;
  you_raw: number | null; admitted_raw: number | null; assumed: boolean;
}
export interface RadarData { n_admitted: number; axes: RadarAxis[] }
export interface ProbabilityComponent { key: string; label: string; delta_logit: number; delta_pp: number; detail: string }
export interface ProbabilityBreakdown {
  p_final: number; p_low: number; p_high: number; p_model: number; base_admit_rate: number;
  components: ProbabilityComponent[]; disposition: Disposition;
}
export interface Citation { kind: "dossier" | "cds" | "twin" | "web" | "model" | "sql"; ref: string; valid: boolean; span: [number, number] }
export interface ZetarisQuery { id: string; purpose: string; sql: string; rows: Record<string, string | null>[]; error: string | null }
export interface DebateTurn {
  turn: number; speaker: Speaker; content: string; citations: Citation[];
  recommendation: Disposition | null; degraded: boolean; streaming: boolean;
}
export interface Counterfactual {
  id: string; kind: "major_switch" | "test_score" | "add_activity" | "early_round" | "demonstrated_interest" | "essay";
  label: string; p_new: number; delta_pp: number; confidence: "data_backed" | "model_estimate";
  evidence: string; overrides: Record<string, unknown>;
}
export interface DeltaReport {
  headline_verdict: string; committee_disposition: Disposition;
  ranked_pivots: { counterfactual_id: string | null; title: string; why_it_works: string; concrete_steps: string[];
                   effort: "hours" | "days" | "weeks" | "months"; tradeoffs: string }[];
  major_arbitrage_note: string | null;
  essay_adjustments: { issue: string; current_excerpt: string; direction: string; example_rewrite: string }[];
  risks_to_watch: string[]; disclaimer: string;
}
export interface ToolCall { seq: number; node: NodeName; tool: string; status: string; [k: string]: unknown }
export interface WhatIfRequest {
  run_id: string; sat?: number | null; withhold_sat?: boolean; major_category?: string | null;
  add_activities?: (1 | 2 | 3)[]; early_round?: "ED" | "ED2" | "EA" | "REA" | "RD" | null;
  demonstrated_interest?: boolean | null; essay_steps?: 0 | 1 | 2;
}
export interface WhatIfResponse {
  baseline: ProbabilityBreakdown; simulated: ProbabilityBreakdown; delta_pp: number;
  applied: string[]; warnings: string[]; confidence: "data_backed" | "model_estimate";
}
export interface Envelope { seq: number; run_id: string; ts: number; event: string; [k: string]: any }
