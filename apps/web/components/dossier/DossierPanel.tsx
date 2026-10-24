"use client";

import { useActiveRun, useRunStore } from "@/store/run-store";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { FileText, Award, GraduationCap, PenTool } from "lucide-react";
import { cn } from "@/lib/utils";

export function DossierPanel() {
  const dossier = useActiveRun((r) => r.dossier);
  const metrics = useActiveRun((r) => r.metrics);
  const grade = useActiveRun((r) => r.grade);
  const nodes = useActiveRun((r) => r.nodes);
  const highlight = useRunStore((s) => s.highlight);

  const isLoading = nodes.dossier_parser === "running" || nodes.dossier_parser === "pending";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-[var(--color-line)] pb-3">
        <h2 className="font-display text-sm font-bold uppercase tracking-wider text-[var(--color-ink)] flex items-center gap-2">
          <FileText className="h-4 w-4 text-[var(--color-advocate)]" />
          Applicant Dossier
        </h2>
        {nodes.dossier_parser === "done" && (
          <Badge variant="outline" className="text-[10px] text-[var(--color-admit)] border-[var(--color-admit)]/40">
            Parsed
          </Badge>
        )}
      </div>

      {isLoading && !dossier ? (
        <div className="space-y-4">
          <Skeleton className="h-28 w-full rounded-xl bg-[var(--color-paper)]/10" />
          <Skeleton className="h-32 w-full rounded-xl bg-[var(--color-panel-2)]" />
          <Skeleton className="h-40 w-full rounded-xl bg-[var(--color-panel-2)]" />
        </div>
      ) : (
        <div className="space-y-5">
          {/* Paper card: GPA / SAT / Rigor */}
          <div className="rounded-xl border border-[#d6cebf] bg-[var(--color-paper)] p-4 text-[var(--color-paper-ink)] shadow-md">
            <div className="flex items-center justify-between border-b border-[#e2dacb] pb-2 text-xs font-mono font-semibold uppercase text-[#5a5243]">
              <span>Academic Metrics</span>
              <span>{dossier?.high_school.school_type ?? "Public"}</span>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-3 text-center">
              <div className="rounded bg-[#ebe4d6] p-2">
                <div className="text-[10px] uppercase text-[#6e6452]">GPA (UW / W)</div>
                <div className="font-mono text-base font-bold">
                  {metrics?.gpa_uw_4?.toFixed(2) ?? "—"} / {metrics?.gpa_w_5?.toFixed(2) ?? "—"}
                </div>
              </div>
              <div className="rounded bg-[#ebe4d6] p-2">
                <div className="text-[10px] uppercase text-[#6e6452]">SAT / Equivalent</div>
                <div className="font-mono text-base font-bold">
                  {metrics?.sat_equivalent ?? dossier?.test_scores.sat_total ?? "—"}
                </div>
              </div>
            </div>
            <div className="mt-2 text-center text-xs font-medium text-[#5a5243]">
              {metrics?.core_course_count ?? 0} Core Courses · {metrics?.advanced_course_count ?? 0} Advanced/AP
            </div>
          </div>

          {/* Harvard Scorecard preview */}
          {grade?.harvard && (
            <div className="space-y-2 rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)] p-4">
              <h3 className="text-xs font-mono uppercase tracking-wider text-[var(--color-muted)] flex items-center gap-1.5">
                <GraduationCap className="h-3.5 w-3.5" />
                Harvard 1–6 Rubric Ratings
              </h3>
              <div className="grid grid-cols-4 gap-2 pt-1 text-center">
                {(["academic", "extracurricular", "personal", "athletic"] as const).map((pillar) => {
                  const rating = grade.harvard[pillar];
                  return (
                    <div key={pillar} className="rounded-lg bg-[var(--color-panel)] p-2">
                      <div className="font-display text-lg font-bold text-[var(--color-ink)]">
                        {rating ? `${rating.rating}${rating.modifier}` : "—"}
                      </div>
                      <div className="text-[10px] font-mono capitalize text-[var(--color-muted)]">
                        {pillar.slice(0, 4)}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Activities list preview */}
          <div className="space-y-2 rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)] p-4">
            <h3 className="text-xs font-mono uppercase tracking-wider text-[var(--color-muted)] flex items-center gap-1.5">
              <Award className="h-3.5 w-3.5" />
              Activities & Extracurriculars
            </h3>
            <div className="space-y-2 pt-1 text-xs">
              {dossier?.activities?.slice(0, 4).map((act, i) => {
                const isHighlighted =
                  highlight?.kind === "dossier" &&
                  (highlight.ref === `activities.${i}` || highlight.ref === "activities");
                return (
                  <div
                    key={i}
                    className={cn(
                      "rounded border border-[var(--color-line)] bg-[var(--color-panel)] p-2 transition-all duration-200",
                      isHighlighted &&
                        "border-[var(--color-advocate)] bg-[var(--color-advocate)]/15 shadow-[0_0_12px_rgba(76,125,255,0.4)] ring-1 ring-[var(--color-advocate)]"
                    )}
                  >
                    <div className="font-medium text-[var(--color-ink)]">{act.name}</div>
                    <div className="text-[11px] text-[var(--color-muted)] line-clamp-1">{act.description}</div>
                  </div>
                );
              }) ?? (
                <p className="text-xs text-[var(--color-muted)] italic">Awaiting dossier parsing...</p>
              )}
            </div>
          </div>

          {/* Reader comments */}
          {grade?.reader_comments && (
            <div className="rounded-xl border border-[#d6cebf] bg-[var(--color-paper)] p-4 text-[var(--color-paper-ink)]">
              <div className="flex items-center gap-1 text-xs font-mono text-[#5a5243]">
                <PenTool className="h-3 w-3" />
                <span>Reader Note:</span>
              </div>
              <p className="mt-1 font-hand text-base leading-snug">
                &ldquo;{grade.reader_comments}&rdquo;
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
