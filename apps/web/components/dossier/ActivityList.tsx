"use client";

import { useActiveRun, useRunStore } from "@/store/run-store";
import { TierTag } from "./TierTag";
import { Star, Award, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

export function ActivityList() {
  const dossier = useActiveRun((r) => r.dossier);
  const grade = useActiveRun((r) => r.grade);
  const highlight = useRunStore((s) => s.highlight);

  const activities = dossier?.activities ?? [];
  const activityGrades = grade?.activity_grades ?? [];

  // Pair activity with its grade if available
  const paired = activities.map((act, index) => {
    const ag = activityGrades.find((g) => g.activity_index === index);
    return {
      index,
      activity: act,
      grade: ag,
    };
  });

  // Sort by tier ascending (Tier 1 first), then unranked
  paired.sort((a, b) => {
    const tierA = a.grade?.tier ?? 99;
    const tierB = b.grade?.tier ?? 99;
    return tierA - tierB;
  });

  return (
    <div className="space-y-2 rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)] p-4">
      <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wider text-[var(--color-muted)]">
        <span className="flex items-center gap-1.5">
          <Award className="h-3.5 w-3.5" />
          Extracurricular Activities ({activities.length})
        </span>
        {grade && <span className="text-[10px] lowercase text-[var(--color-admit)]">T1–T4 graded</span>}
      </div>

      <div className="space-y-2.5 pt-1 text-xs">
        {paired.length === 0 ? (
          <p className="text-xs text-[var(--color-muted)] italic">
            Awaiting activities extraction...
          </p>
        ) : (
          paired.map(({ index, activity, grade: ag }) => {
            const isHighlighted =
              highlight?.kind === "dossier" &&
              (highlight.ref === `activities.${index}` || highlight.ref === "activities");
            const isCore = ag?.spike_role === "core";

            return (
              <div
                key={index}
                className={cn(
                  "rounded-lg border border-[var(--color-line)] bg-[var(--color-panel)] p-3 transition-all duration-200",
                  isHighlighted &&
                    "border-[var(--color-advocate)] bg-[var(--color-advocate)]/15 shadow-[0_0_15px_rgba(76,125,255,0.4)] ring-1 ring-[var(--color-advocate)] scale-[1.01]"
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-0.5">
                    <div className="font-semibold text-[var(--color-ink)] flex items-center gap-1.5">
                      <span>{activity.name}</span>
                      {isCore && (
                        <span
                          title="Core spike activity"
                          className="inline-flex items-center gap-0.5 rounded bg-[var(--color-tier1)]/15 px-1 py-0.2 text-[9px] font-mono text-[var(--color-tier1)]"
                        >
                          <Star className="h-2.5 w-2.5 fill-current" />
                          core
                        </span>
                      )}
                    </div>
                    {activity.role && (
                      <p className="text-[11px] text-[var(--color-advocate)] font-medium">
                        {activity.role}
                        {activity.organization && ` · ${activity.organization}`}
                      </p>
                    )}
                  </div>

                  <div className="shrink-0">
                    {ag ? (
                      <TierTag tier={ag.tier} />
                    ) : (
                      <span className="inline-flex items-center rounded-full bg-[var(--color-panel-2)] px-2 py-0.5 text-[9px] font-mono text-[var(--color-muted)] animate-pulse">
                        grading…
                      </span>
                    )}
                  </div>
                </div>

                <p className="mt-1 text-[11px] leading-relaxed text-[var(--color-muted)]">
                  {activity.description}
                </p>

                {(activity.hours_per_week || activity.weeks_per_year) && (
                  <div className="mt-2 flex items-center gap-2 text-[10px] font-mono text-[var(--color-muted)] border-t border-[var(--color-line)]/50 pt-1.5">
                    <Clock className="h-3 w-3" />
                    <span>
                      {activity.hours_per_week ?? "?"} hrs/wk · {activity.weeks_per_year ?? "?"} wks/yr
                    </span>
                    {activity.category && (
                      <span className="capitalize ml-auto">
                        {activity.category.replaceAll("_", " ")}
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
