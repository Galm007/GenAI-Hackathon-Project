"use client";

import { useActiveRun } from "@/store/run-store";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { BarChart3, Target, History, Sparkles } from "lucide-react";
import { pct, pp } from "@/lib/format";

export function AnalyticsPanel() {
  const probability = useActiveRun((r) => r.probability);
  const twins = useActiveRun((r) => r.twins);
  const baseline = useActiveRun((r) => r.baseline);
  const counterfactuals = useActiveRun((r) => r.counterfactuals);
  const nodes = useActiveRun((r) => r.nodes);

  const isDocketsLoading = nodes.committee_docket !== "done";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-[var(--color-line)] pb-3">
        <h2 className="font-display text-sm font-bold uppercase tracking-wider text-[var(--color-ink)] flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-[var(--color-advocate)]" />
          Analytics & Simulation
        </h2>
        {probability?.disposition && (
          <Badge
            variant="outline"
            className={`text-xs ${
              probability.disposition.includes("ADMIT")
                ? "border-[var(--color-admit)] text-[var(--color-admit)]"
                : probability.disposition.includes("WAITLIST")
                ? "border-[var(--color-waitlist)] text-[var(--color-waitlist)]"
                : "border-[var(--color-deny)] text-[var(--color-deny)]"
            }`}
          >
            {probability.disposition}
          </Badge>
        )}
      </div>

      {/* 1. Probability Gauge */}
      <div className="rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)] p-5 text-center">
        <div className="text-xs font-mono uppercase tracking-wider text-[var(--color-muted)]">
          P(Admit) Estimate
        </div>
        {probability ? (
          <div className="mt-2 space-y-1">
            <div className="font-display text-4xl font-extrabold text-[var(--color-ink)]">
              {pct(probability.p_final)}
            </div>
            <div className="text-xs text-[var(--color-muted)] font-mono">
              80% Range: {pct(probability.p_low)} – {pct(probability.p_high)}
            </div>
            <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-[var(--color-panel)] px-2.5 py-0.5 text-xs text-[var(--color-muted)]">
              <span>Base rate: {pct(probability.base_admit_rate)}</span>
            </div>
          </div>
        ) : (
          <div className="mt-3 flex flex-col items-center gap-2">
            <Skeleton className="h-10 w-24 rounded-lg bg-[var(--color-panel)]" />
            <Skeleton className="h-4 w-36 rounded bg-[var(--color-panel)]" />
          </div>
        )}
      </div>

      {/* 2. Waterfall Components */}
      <div className="rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)] p-4">
        <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wider text-[var(--color-muted)] mb-3">
          <span className="flex items-center gap-1.5">
            <Target className="h-3.5 w-3.5" />
            Factor Waterfall
          </span>
        </div>
        {probability?.components ? (
          <div className="space-y-2 text-xs">
            {probability.components.map((comp) => (
              <div key={comp.key} className="flex items-center justify-between rounded bg-[var(--color-panel)] p-2">
                <span className="text-[var(--color-ink)]">{comp.label}</span>
                <span
                  className={`font-mono font-semibold ${
                    comp.delta_pp >= 0 ? "text-[var(--color-admit)]" : "text-[var(--color-deny)]"
                  }`}
                >
                  {pp(comp.delta_pp)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full rounded bg-[var(--color-panel)]" />
            <Skeleton className="h-8 w-full rounded bg-[var(--color-panel)]" />
            <Skeleton className="h-8 w-full rounded bg-[var(--color-panel)]" />
          </div>
        )}
      </div>

      {/* 3. The 5 Historical Twins */}
      <div className="rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)] p-4">
        <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wider text-[var(--color-muted)] mb-3">
          <span className="flex items-center gap-1.5">
            <History className="h-3.5 w-3.5" />
            Historical Twins ({twins.length})
          </span>
          {baseline && (
            <span className="text-[10px] lowercase text-[var(--color-muted)]">
              {baseline.n_neighbors} matched
            </span>
          )}
        </div>
        {twins.length > 0 ? (
          <div className="space-y-2 text-xs">
            {twins.map((t) => (
              <div
                key={t.id}
                className="flex items-center justify-between rounded border border-[var(--color-line)] bg-[var(--color-panel)] p-2.5"
              >
                <div>
                  <div className="font-semibold text-[var(--color-ink)] flex items-center gap-1.5">
                    <span
                      className={
                        t.outcome === "accepted"
                          ? "text-[var(--color-admit)]"
                          : t.outcome === "waitlisted"
                          ? "text-[var(--color-waitlist)]"
                          : "text-[var(--color-deny)]"
                      }
                    >
                      {t.outcome === "accepted" ? "✓" : t.outcome === "waitlisted" ? "◐" : "✕"}
                    </span>
                    <span>Twin #{t.index}</span>
                  </div>
                  <div className="text-[10px] text-[var(--color-muted)] font-mono">
                    GPA {t.gpa_uw?.toFixed(2) ?? "—"} · SAT {t.sat_score ?? "—"}
                  </div>
                </div>
                <Badge variant="outline" className="text-[10px] font-mono">
                  {Math.round(t.hybrid_score * 100)}% match
                </Badge>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            <Skeleton className="h-12 w-full rounded bg-[var(--color-panel)]" />
            <Skeleton className="h-12 w-full rounded bg-[var(--color-panel)]" />
          </div>
        )}
      </div>

      {/* 4. Counterfactual Pivots */}
      {counterfactuals.length > 0 && (
        <div className="rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)] p-4">
          <div className="text-xs font-mono uppercase tracking-wider text-[var(--color-muted)] mb-3 flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-[var(--color-advocate)]" />
            High-Impact Pivots
          </div>
          <div className="space-y-2 text-xs">
            {counterfactuals.slice(0, 3).map((cf) => (
              <div key={cf.id} className="rounded border border-[var(--color-line)] bg-[var(--color-panel)] p-2.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-[var(--color-ink)]">{cf.label}</span>
                  <span className="font-mono text-[var(--color-admit)] font-bold">
                    {pp(cf.delta_pp)}
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-[var(--color-muted)] line-clamp-2">{cf.evidence}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
