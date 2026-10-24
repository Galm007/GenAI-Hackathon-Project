"use client";

import { useActiveRun } from "@/store/run-store";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { MetricsStrip } from "./MetricsStrip";
import { HarvardScorecard } from "./HarvardScorecard";
import { ActivityList } from "./ActivityList";
import { ReaderNote } from "./ReaderNote";
import { FileText, Zap, Trophy, AlertTriangle } from "lucide-react";

export function DossierPanel() {
  const dossier = useActiveRun((r) => r.dossier);
  const grade = useActiveRun((r) => r.grade);
  const nodes = useActiveRun((r) => r.nodes);

  const isLoading = nodes.dossier_parser === "running" || nodes.dossier_parser === "pending";

  return (
    <div className="space-y-6">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-[var(--color-line)] pb-3">
        <h2 className="font-display text-sm font-bold uppercase tracking-wider text-[var(--color-ink)] flex items-center gap-2">
          <FileText className="h-4 w-4 text-[var(--color-advocate)]" />
          Applicant Dossier
        </h2>
        {nodes.dossier_parser === "done" && (
          <Badge
            variant="outline"
            className="text-[10px] text-[var(--color-admit)] border-[var(--color-admit)]/40 font-mono"
          >
            Verified File
          </Badge>
        )}
      </div>

      {isLoading && !dossier ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full rounded-xl bg-[var(--color-panel-2)]" />
          <Skeleton className="h-28 w-full rounded-xl bg-[var(--color-panel-2)]" />
          <Skeleton className="h-48 w-full rounded-xl bg-[var(--color-panel-2)]" />
        </div>
      ) : (
        <div className="space-y-5">
          {/* 1. Academic Metrics Strip */}
          <MetricsStrip />

          {/* 2. Harvard Scorecard */}
          <HarvardScorecard />

          {/* 3. Spike Banner */}
          {grade?.spike && (
            <div className="rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)] p-3.5">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="flex items-center gap-1.5 font-semibold text-[var(--color-ink)]">
                  <Zap className="h-3.5 w-3.5 text-[var(--color-tier1)]" />
                  Spike: {grade.spike.label}
                </span>
                <span
                  className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                    grade.spike.strength === "strong"
                      ? "bg-[var(--color-admit)]/20 text-[var(--color-admit)]"
                      : grade.spike.strength === "moderate"
                      ? "bg-[var(--color-advocate)]/20 text-[var(--color-advocate)]"
                      : "bg-[var(--color-muted)]/20 text-[var(--color-muted)]"
                  }`}
                >
                  {grade.spike.strength} spike
                </span>
              </div>
              {grade.spike.description && (
                <p className="mt-1 text-xs text-[var(--color-muted)] leading-relaxed">
                  {grade.spike.description}
                </p>
              )}
            </div>
          )}

          {/* 4. Activities List with T1-T4 tags */}
          <ActivityList />

          {/* 5. Honors & Awards */}
          {dossier?.awards && dossier.awards.length > 0 && (
            <div className="space-y-2 rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)] p-4">
              <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wider text-[var(--color-muted)]">
                <span className="flex items-center gap-1.5">
                  <Trophy className="h-3.5 w-3.5" />
                  Honors & Awards ({dossier.awards.length})
                </span>
              </div>
              <div className="space-y-1.5 pt-1 text-xs">
                {dossier.awards.map((award, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between rounded bg-[var(--color-panel)] px-2.5 py-1.5"
                  >
                    <span className="font-medium text-[var(--color-ink)]">{award.name}</span>
                    <Badge variant="outline" className="text-[10px] capitalize font-mono">
                      {award.level.replaceAll("_", " ")}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 6. Admissions Reader Note (Caveat handwriting) */}
          <ReaderNote />

          {/* 7. Grader Warnings / Guardrails */}
          {grade?.grader_warnings && grade.grader_warnings.length > 0 && (
            <div className="rounded-xl border border-[var(--color-waitlist)]/30 bg-[var(--color-waitlist)]/5 p-3 text-xs">
              <div className="flex items-center gap-1.5 font-semibold text-[var(--color-waitlist)] mb-1">
                <AlertTriangle className="h-3.5 w-3.5" />
                <span>Guardrail Adjustments ({grade.grader_warnings.length})</span>
              </div>
              <ul className="list-disc pl-4 space-y-0.5 text-[11px] text-[var(--color-muted)]">
                {grade.grader_warnings.map((warn, i) => (
                  <li key={i}>{warn}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
