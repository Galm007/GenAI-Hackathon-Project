"use client";

import { useEffect, useState } from "react";
import { useActiveRun } from "@/store/run-store";
import { SchoolTabs } from "./SchoolTabs";
import { PipelineStepper } from "./PipelineStepper";
import { DataFabricDrawer } from "./DataFabricDrawer";
import { Button } from "@/components/ui/button";
import { Monitor, Clock, Database } from "lucide-react";
import type { RunSource } from "@/lib/stream";
import Link from "next/link";

interface TopBarProps {
  source: RunSource;
  onSelectSchool?: (slug: string) => void;
}

export function TopBar({ source, onSelectSchool }: TopBarProps) {
  const startedAt = useActiveRun((r) => r.startedAt);
  const finishedAt = useActiveRun((r) => r.finishedAt);
  const status = useActiveRun((r) => r.status);
  const sqlQueries = useActiveRun((r) => r.sqlQueries);

  // Elapsed timer state
  const [elapsedSec, setElapsedSec] = useState(0);
  const [isProjector, setIsProjector] = useState(false);
  const [isFabricOpen, setIsFabricOpen] = useState(false);

  // Timer update loop
  useEffect(() => {
    if (!startedAt) {
      setElapsedSec(0);
      return;
    }

    if (finishedAt) {
      setElapsedSec(Math.max(0, Math.floor((finishedAt - startedAt) / 1000)));
      return;
    }

    const interval = setInterval(() => {
      const now = Date.now();
      setElapsedSec(Math.max(0, Math.floor((now - startedAt) / 1000)));
    }, 1000);

    return () => clearInterval(interval);
  }, [startedAt, finishedAt]);

  // Projector query param and toggle
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("projector") === "1") {
      setIsProjector(true);
      document.body.classList.add("projector");
    }
  }, []);

  const toggleProjector = () => {
    setIsProjector((prev) => {
      const next = !prev;
      if (next) {
        document.body.classList.add("projector");
      } else {
        document.body.classList.remove("projector");
      }
      return next;
    });
  };

  const minutes = Math.floor(elapsedSec / 60);
  const seconds = elapsedSec % 60;
  const timeFormatted = `${minutes}:${seconds.toString().padStart(2, "0")}`;

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--color-line)] bg-[var(--color-room)] px-4 sm:px-6">
      {/* Left: Wordmark & School Tabs */}
      <div className="flex items-center gap-4 sm:gap-6">
        <Link
          href="/"
          className="flex items-center gap-2 transition-opacity hover:opacity-80"
        >
          <span className="font-display text-base font-bold tracking-tight text-[var(--color-ink)]">
            ADCOM
          </span>
          <span className="text-[var(--color-muted)]">▸</span>
          <span className="font-sans text-xs font-semibold uppercase tracking-wider text-[var(--color-muted)]">
            War Room
          </span>
        </Link>

        <SchoolTabs onSelectSchool={onSelectSchool} />
      </div>

      {/* Center: Pipeline Stepper */}
      <PipelineStepper />

      {/* Right: Elapsed timer & Projector mode */}
      <div className="flex items-center gap-3">
        {startedAt && (
          <div className="flex items-center gap-1.5 font-mono text-xs text-[var(--color-muted)]">
            <Clock className="h-3.5 w-3.5" />
            <span>⏱ {timeFormatted}</span>
          </div>
        )}

        {/* Data Fabric Drawer Button */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsFabricOpen(true)}
          className="h-7 px-2.5 text-xs font-mono text-[var(--color-muted)] hover:text-white hover:border-[var(--color-advocate)] transition-colors"
          title="Inspect Zetaris federated SQL queries"
        >
          <Database className="mr-1.5 h-3.5 w-3.5 text-[var(--color-advocate)]" />
          <span>Data Fabric</span>
          {sqlQueries.length > 0 && (
            <span className="ml-1 rounded-full bg-[var(--color-advocate)]/20 px-1.5 py-0.2 text-[10px] font-bold text-[var(--color-advocate)]">
              {sqlQueries.length}
            </span>
          )}
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={toggleProjector}
          className={`h-7 px-2.5 text-xs font-mono transition-colors ${
            isProjector
              ? "border-[var(--color-advocate)] bg-[var(--color-advocate)]/20 text-[var(--color-advocate)]"
              : "text-[var(--color-muted)]"
          }`}
          title="Toggle high-contrast projector mode (?projector=1)"
        >
          <Monitor className="mr-1.5 h-3.5 w-3.5" />
          Projector
        </Button>
      </div>

      {/* Zetaris Data Fabric Drawer */}
      <DataFabricDrawer
        open={isFabricOpen}
        onOpenChange={setIsFabricOpen}
      />
    </header>
  );
}
