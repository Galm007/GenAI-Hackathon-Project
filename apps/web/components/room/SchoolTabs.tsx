"use client";

import * as React from "react";
import { useActiveRun, useRunStore } from "@/store/run-store";
import { schoolName } from "@/lib/format";
import { connectStream } from "@/lib/stream";
import { cn } from "@/lib/utils";

interface SchoolTabsProps {
  onSelectSchool?: (slug: string) => void;
}

export function SchoolTabs({ onSelectSchool }: SchoolTabsProps) {
  const activeRunId = useRunStore((s) => s.activeRunId);
  const runs = useRunStore((s) => s.runs);
  const tabs = useRunStore((s) => s.tabs);
  const targetSchools = useRunStore((s) => s.targetSchools);
  const setActive = useRunStore((s) => s.setActive);
  const startChildRun = useRunStore((s) => s.startChildRun);
  const setTabRun = useRunStore((s) => s.setTabRun);

  const activeRun = useActiveRun((r) => r);
  const activeSlug = activeRun.schoolSlug ?? "uiuc";

  // Register active run into tabs if not yet registered
  React.useEffect(() => {
    if (activeRunId && activeSlug && !tabs[activeSlug]) {
      setTabRun(activeSlug, activeRunId);
    }
  }, [activeRunId, activeSlug, tabs, setTabRun]);

  // Combine target schools from intake, active run, and all evaluated runs
  const runSlugs = Object.values(runs)
    .map((r) => r.schoolSlug)
    .filter((s): s is string => Boolean(s));

  const allSlugs = Array.from(
    new Set([activeSlug, ...targetSchools, ...runSlugs])
  );

  const handleTabClick = async (slug: string) => {
    if (onSelectSchool) {
      onSelectSchool(slug);
    }

    if (slug === activeSlug) return;

    // 1. If run exists for this slug, switch to it
    const existingRunId =
      tabs[slug] ?? Object.values(runs).find((r) => r.schoolSlug === slug)?.runId;

    if (existingRunId) {
      setActive(existingRunId);
      return;
    }

    // 2. Otherwise start child run (Node 1 skipped, begins Node 2)
    try {
      const childRunId = await startChildRun(slug);
      connectStream(childRunId);
    } catch {
      // Handled in startChildRun
    }
  };

  return (
    <div className="flex items-center gap-1.5" role="tablist">
      {allSlugs.map((slug) => {
        const isCurrent = slug === activeSlug;
        const runIdForSlug =
          tabs[slug] ?? Object.values(runs).find((r) => r.schoolSlug === slug)?.runId;
        const schoolRun = runIdForSlug ? runs[runIdForSlug] : null;

        const isLive =
          schoolRun &&
          (schoolRun.status === "running" || schoolRun.status === "connecting");
        const isDone = schoolRun && schoolRun.status === "complete";
        const disposition = schoolRun?.probability?.disposition;

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
            onClick={() => handleTabClick(slug)}
            className={cn(
              "inline-flex items-center gap-2 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer",
              isCurrent
                ? "bg-[var(--color-panel-2)] text-[var(--color-ink)] shadow-sm"
                : "text-[var(--color-muted)] hover:bg-[var(--color-panel-2)]/50 hover:text-[var(--color-ink)]"
            )}
          >
            <span
              className={cn(
                "inline-block h-2 w-2 rounded-full transition-colors",
                dotColor
              )}
            />
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
