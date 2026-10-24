"use client";

import { TooltipProvider } from "@/components/ui/tooltip";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRunStream, type RunSource } from "@/lib/stream";
import { TopBar } from "./TopBar";
import { DossierPanel } from "@/components/dossier/DossierPanel";
import { CommitteeRoom } from "@/components/committee/CommitteeRoom";
import { AnalyticsPanel } from "@/components/analytics/AnalyticsPanel";

export function WarRoom({ source }: { source: RunSource }) {
  useRunStream(source);

  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex h-dvh flex-col bg-[var(--color-room)]">
        <TopBar source={source} />

        {/* ≥1440px: three columns */}
        <main className="hidden min-h-0 flex-1 grid-cols-[340px_minmax(0,1fr)_420px] 2xl:grid">
          <aside className="min-h-0 overflow-y-auto border-r border-[var(--color-line)] p-4">
            <DossierPanel />
          </aside>
          <div className="min-h-0">
            <CommitteeRoom />
          </div>
          <aside className="min-h-0 overflow-y-auto border-l border-[var(--color-line)] p-4">
            <AnalyticsPanel />
          </aside>
        </main>

        {/* <1440px: tabs, Committee first */}
        <Tabs defaultValue="committee" className="flex min-h-0 flex-1 flex-col 2xl:hidden">
          <TabsList className="mx-4 mt-2 self-start bg-[var(--color-panel-2)] border border-[var(--color-line)]">
            <TabsTrigger value="committee">Committee</TabsTrigger>
            <TabsTrigger value="dossier">Dossier</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>
          <TabsContent value="committee" className="min-h-0 flex-1">
            <CommitteeRoom />
          </TabsContent>
          <TabsContent value="dossier" className="min-h-0 flex-1 overflow-y-auto p-4">
            <DossierPanel />
          </TabsContent>
          <TabsContent value="analytics" className="min-h-0 flex-1 overflow-y-auto p-4">
            <AnalyticsPanel />
          </TabsContent>
        </Tabs>
      </div>
    </TooltipProvider>
  );
}
