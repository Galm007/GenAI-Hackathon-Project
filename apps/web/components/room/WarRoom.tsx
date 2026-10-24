"use client";

import * as React from "react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useRunStream, type RunSource } from "@/lib/stream";
import { useActiveRun } from "@/store/run-store";
import { pct } from "@/lib/format";
import { TopBar } from "./TopBar";
import { DossierPanel } from "@/components/dossier/DossierPanel";
import { CommitteeRoom } from "@/components/committee/CommitteeRoom";
import { AnalyticsPanel } from "@/components/analytics/AnalyticsPanel";
import { useWhatIfSimulation } from "@/components/analytics/what-if";
import { BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";

export function WarRoom({ source }: { source: RunSource }) {
  useRunStream(source);
  useWhatIfSimulation();

  const probability = useActiveRun((r) => r.probability);
  const disposition = probability?.disposition;
  const pFinal = probability?.p_final;

  const [analyticsSheetOpen, setAnalyticsSheetOpen] = React.useState(false);

  // Disposition color badge
  let dispositionBadgeClass = "bg-[var(--color-panel-2)] text-[var(--color-muted)]";
  if (disposition === "ADMIT" || disposition === "LIKELY ADMIT") {
    dispositionBadgeClass = "bg-[var(--color-admit)]/20 text-[var(--color-admit)] border-[var(--color-admit)]/40";
  } else if (disposition === "WAITLIST") {
    dispositionBadgeClass = "bg-[var(--color-waitlist)]/20 text-[var(--color-waitlist)] border-[var(--color-waitlist)]/40";
  } else if (disposition === "DENY") {
    dispositionBadgeClass = "bg-[var(--color-deny)]/20 text-[var(--color-deny)] border-[var(--color-deny)]/40";
  }

  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex h-dvh flex-col bg-[var(--color-room)]">
        <TopBar source={source} />

        {/* ≥ 1440px: Three columns (Dossier | Committee | Analytics) */}
        <main
          role="main"
          className="hidden min-h-0 flex-1 grid-cols-[340px_minmax(0,1fr)_420px] 2xl:grid"
        >
          <aside
            aria-label="Applicant Dossier"
            className="min-h-0 overflow-y-auto border-r border-[var(--color-line)] p-4"
          >
            <DossierPanel />
          </aside>
          <div className="min-h-0">
            <CommitteeRoom />
          </div>
          <aside
            aria-label="Selection Analytics"
            className="min-h-0 overflow-y-auto border-l border-[var(--color-line)] p-4"
          >
            <AnalyticsPanel />
          </aside>
        </main>

        {/* 1024px–1439px: Two columns (Dossier | Committee) + Floating Analytics Drawer */}
        <div className="hidden min-h-0 flex-1 grid-cols-[320px_minmax(0,1fr)] lg:grid 2xl:hidden relative">
          <aside
            aria-label="Applicant Dossier"
            className="min-h-0 overflow-y-auto border-r border-[var(--color-line)] p-4"
          >
            <DossierPanel />
          </aside>
          <div className="min-h-0">
            <CommitteeRoom />
          </div>

          {/* Floating live gauge pill */}
          {probability && (
            <button
              type="button"
              onClick={() => setAnalyticsSheetOpen(true)}
              aria-label={`Open analytics panel. Current probability: ${pct(pFinal, 0)} ${disposition ?? ""}`}
              className="fixed bottom-6 right-6 z-40 flex items-center gap-2.5 rounded-full border border-[var(--color-advocate)] bg-[var(--color-panel)] px-4 py-2.5 shadow-2xl transition hover:scale-105 active:scale-95 cursor-pointer"
            >
              <BarChart3 className="h-4 w-4 text-[var(--color-advocate)]" />
              <span className="font-mono text-sm font-bold text-[var(--color-ink)]">
                {pct(pFinal, 0)}
              </span>
              <span className="text-[11px] font-mono text-[var(--color-advocate)] font-semibold">
                P(ADMIT)
              </span>
              {disposition && (
                <span
                  className={cn(
                    "rounded border px-1.5 py-0.5 text-[10px] font-bold font-mono uppercase",
                    dispositionBadgeClass
                  )}
                >
                  {disposition}
                </span>
              )}
            </button>
          )}

          {/* Analytics Sheet for 1024-1439px */}
          <Sheet open={analyticsSheetOpen} onOpenChange={setAnalyticsSheetOpen}>
            <SheetContent
              side="right"
              className="w-full sm:max-w-md overflow-y-auto p-4 bg-[var(--color-panel)] border-l border-[var(--color-line)] text-[var(--color-ink)]"
            >
              <SheetHeader className="pb-3 border-b border-[var(--color-line)] mb-4">
                <SheetTitle className="text-base font-bold text-[var(--color-ink)]">
                  Selection Analytics &amp; What-If
                </SheetTitle>
              </SheetHeader>
              <AnalyticsPanel />
            </SheetContent>
          </Sheet>
        </div>

        {/* < 1024px: Tabs layout (Committee | Dossier | Analytics) with sticky mini-gauge */}
        <div className="flex min-h-0 flex-1 flex-col lg:hidden">
          <Tabs defaultValue="committee" className="flex min-h-0 flex-1 flex-col">
            <div className="mx-4 mt-2 flex items-center justify-between gap-2">
              <TabsList className="bg-[var(--color-panel-2)] border border-[var(--color-line)]">
                <TabsTrigger value="committee">Committee</TabsTrigger>
                <TabsTrigger value="dossier">Dossier</TabsTrigger>
                <TabsTrigger value="analytics">Analytics</TabsTrigger>
              </TabsList>

              {/* Sticky mini-gauge in header */}
              {probability && (
                <div
                  aria-live="polite"
                  className="flex items-center gap-1.5 rounded-full border border-[var(--color-line)] bg-[var(--color-panel-2)] px-2.5 py-1 text-xs font-mono"
                >
                  <span className="font-bold text-[var(--color-ink)]">
                    {pct(pFinal, 0)}
                  </span>
                  <span className="text-[10px] text-[var(--color-muted)]">P(ADMIT)</span>
                  {disposition && (
                    <span
                      className={cn(
                        "rounded px-1 py-0.2 text-[9px] font-bold uppercase",
                        dispositionBadgeClass
                      )}
                    >
                      {disposition}
                    </span>
                  )}
                </div>
              )}
            </div>

            <TabsContent value="committee" className="min-h-0 flex-1">
              <CommitteeRoom />
            </TabsContent>
            <TabsContent
              value="dossier"
              className="min-h-0 flex-1 overflow-y-auto p-4"
            >
              <DossierPanel />
            </TabsContent>
            <TabsContent
              value="analytics"
              className="min-h-0 flex-1 overflow-y-auto p-4"
            >
              <AnalyticsPanel />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </TooltipProvider>
  );
}
