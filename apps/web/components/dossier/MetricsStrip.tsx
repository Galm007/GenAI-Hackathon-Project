"use client";

import { useActiveRun } from "@/store/run-store";
import { GraduationCap, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

export function MetricsStrip() {
  const metrics = useActiveRun((r) => r.metrics);
  const dossier = useActiveRun((r) => r.dossier);

  const uw = metrics?.gpa_uw_4?.toFixed(2) ?? "—";
  const w = metrics?.gpa_w_5?.toFixed(2) ?? "—";
  const sat = metrics?.sat_equivalent ?? dossier?.test_scores.sat_total ?? "—";
  const rigor = metrics?.rigor_index != null ? metrics.rigor_index.toFixed(1) : "—";
  const trend = metrics?.grade_trend;

  let trendIcon = <Minus className="h-3.5 w-3.5 text-[var(--color-muted)]" />;
  let trendLabel = "Flat";
  if (trend === "upward") {
    trendIcon = <TrendingUp className="h-3.5 w-3.5 text-[var(--color-admit)]" />;
    trendLabel = "Upward";
  } else if (trend === "downward") {
    trendIcon = <TrendingDown className="h-3.5 w-3.5 text-[var(--color-deny)]" />;
    trendLabel = "Downward";
  }

  return (
    <div className="rounded-xl border border-[#d6cebf] bg-[var(--color-paper)] p-4 text-[var(--color-paper-ink)] shadow-md">
      <div className="flex items-center justify-between border-b border-[#e2dacb] pb-2 text-xs font-mono font-semibold uppercase text-[#5a5243]">
        <span className="flex items-center gap-1.5">
          <GraduationCap className="h-3.5 w-3.5" />
          Academic Record
        </span>
        <span className="text-[10px] text-[#7d7360]">
          {dossier?.high_school.school_type ?? "Computed from transcript"}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
        {/* GPA */}
        <div className="rounded bg-[#ebe4d6] p-2">
          <div className="text-[10px] font-mono uppercase text-[#6e6452]">GPA (UW / W)</div>
          <div className="font-mono text-base font-bold tracking-tight">
            {uw} / {w}
          </div>
        </div>

        {/* SAT */}
        <div className="rounded bg-[#ebe4d6] p-2">
          <div className="text-[10px] font-mono uppercase text-[#6e6452]">SAT / Equivalent</div>
          <div className="font-mono text-base font-bold tracking-tight">{sat}</div>
        </div>

        {/* Rigor */}
        <div className="rounded bg-[#ebe4d6] p-2">
          <div className="text-[10px] font-mono uppercase text-[#6e6452]">Rigor Index</div>
          <div className="font-mono text-base font-bold tracking-tight">{rigor}</div>
        </div>

        {/* Trend */}
        <div className="rounded bg-[#ebe4d6] p-2">
          <div className="text-[10px] font-mono uppercase text-[#6e6452]">Grade Trend</div>
          <div className="flex items-center justify-center gap-1 font-mono text-sm font-bold pt-0.5">
            {trendIcon}
            <span>{trendLabel}</span>
          </div>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between text-[11px] text-[#5a5243] border-t border-[#e2dacb]/60 pt-2 font-mono">
        <span>{metrics?.core_course_count ?? 0} Core Courses</span>
        <span>{metrics?.advanced_course_count ?? 0} Advanced / AP</span>
        <span>Proxy Acad: {metrics?.proxy_academic_rating?.toFixed(1) ?? "—"}</span>
      </div>
    </div>
  );
}
