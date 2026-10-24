"use client";

import { useActiveRun, useRunStore } from "@/store/run-store";
import { schoolName } from "@/lib/format";
import { cn } from "@/lib/utils";

interface SchoolTabsProps {
  onSelectSchool?: (slug: string) => void;
}

export function SchoolTabs({ onSelectSchool }: SchoolTabsProps) {
  const activeRunId = useRunStore((s) => s.activeRunId);
  const runs = useRunStore((s) => s.runs);
  const activeRun = useActiveRun((r) => r);

  const activeSlug = activeRun.schoolSlug ?? "uiuc";
  const status = activeRun.status;
  const disposition = activeRun.probability?.disposition;

  // Collect all known school runs from the store
  const allRuns = Object.values(runs).filter((r) => r.schoolSlug);
  const slugs = Array.from(
    new Set([activeSlug, ...allRuns.map((r) => r.schoolSlug!)])
  );

  return (
    <div className="flex items-center gap-1.5" role="tablist">
      {slugs.map((slug) => {
        const isCurrent = slug === activeSlug;
        const isLive = isCurrent && (status === "running" || status === "connecting");
        const isDone = isCurrent && status === "complete";

        let dotColor = "border border-[var(--color-muted)] bg-transparent"; // not started / hollow
        if (isLive) {
          dotColor = "bg-[var(--color-advocate)] animate-pulse";
        } else if (isDone) {
          if (disposition === "ADMIT" || disposition === "LIKELY ADMIT") {
            dotColor = "bg-[var(--color-admit)]";
          } else if (disposition === "WAITLIST") {
            dotColor = "bg-[var(--color-waitlist)]";
          } else {
            dotColor = "bg-[var(--color-deny)]";
          }
        }

        return (
          <button
            key={slug}
            type="button"
            role="tab"
            aria-selected={isCurrent}
            onClick={() => onSelectSchool?.(slug)}
            className={cn(
              "inline-flex items-center gap-2 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors",
              isCurrent
                ? "bg-[var(--color-panel-2)] text-[var(--color-ink)] shadow-sm"
                : "text-[var(--color-muted)] hover:bg-[var(--color-panel-2)]/50 hover:text-[var(--color-ink)]"
            )}
          >
            <span className={cn("inline-block h-2 w-2 rounded-full", dotColor)} />
            <span>{schoolName(slug)}</span>
            {isLive && (
              <span className="text-[10px] font-mono text-[var(--color-advocate)]">
                ● live
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
