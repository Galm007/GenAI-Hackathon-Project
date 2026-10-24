"use client";

import { useActiveRun } from "@/store/run-store";
import { ToolTicker } from "@/components/room/ToolTicker";
import { Badge } from "@/components/ui/badge";
import { Users, AlertCircle } from "lucide-react";
import { schoolName } from "@/lib/format";

export function CommitteeRoom() {
  const rubric = useActiveRun((r) => r.rubric);
  const schoolSlug = useActiveRun((r) => r.schoolSlug);
  const debate = useActiveRun((r) => r.debate);
  const status = useActiveRun((r) => r.status);
  const nodes = useActiveRun((r) => r.nodes);
  const progress = useActiveRun((r) => r.progress);

  const displaySchool = rubric?.name ?? (schoolSlug ? schoolName(schoolSlug) : "UIUC");
  const majorDetail = rubric?.major_college ?? rubric?.major_category?.replaceAll("_", " ") ?? "Computer Science";

  return (
    <section className="flex h-full flex-col bg-[var(--color-room)]">
      {/* Header with Title and ToolTicker */}
      <header className="border-b border-[var(--color-line)] bg-[var(--color-panel)] px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display text-lg font-bold text-[var(--color-ink)] flex items-center gap-2">
              <Users className="h-4 w-4 text-[var(--color-advocate)]" />
              Committee Room · {displaySchool}
            </h2>
            <p className="text-xs text-[var(--color-muted)]">
              {majorDetail} · CDS {rubric ? "loaded" : "loading"}
            </p>
          </div>
          <Badge
            variant="outline"
            className={`text-xs ${
              status === "complete"
                ? "border-[var(--color-admit)] text-[var(--color-admit)]"
                : "border-[var(--color-advocate)] text-[var(--color-advocate)] animate-pulse"
            }`}
          >
            {status === "complete" ? "Adjourned" : "In Session"}
          </Badge>
        </div>

        {/* Live tool ticker */}
        <ToolTicker />
      </header>

      {/* Main Debate Area */}
      <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-6">
        {debate.length === 0 ? (
          <div className="mx-auto my-auto max-w-md space-y-3 text-center text-sm text-[var(--color-muted)]">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-panel-2)] text-[var(--color-advocate)]">
              <Users className="h-6 w-6" />
            </div>
            <p className="font-display text-lg text-[var(--color-ink)]">
              The committee is assembling.
            </p>
            <p className="text-xs">
              Regional Advocate and Committee Chair are reviewing the file and institutional evidence.
            </p>
            {Object.entries(progress).map(([node, msg]) => (
              <p key={node} className="text-xs font-mono text-[var(--color-advocate)]">
                ⚙ {msg}
              </p>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {debate.map((turn) => {
              const isAdvocate = turn.speaker === "advocate";
              return (
                <div
                  key={turn.turn}
                  className={`flex flex-col gap-1 rounded-xl border p-4 ${
                    isAdvocate
                      ? "border-[var(--color-advocate)]/30 bg-[var(--color-advocate)]/5 self-start mr-12"
                      : "border-[var(--color-chair)]/30 bg-[var(--color-chair)]/5 self-end ml-12"
                  }`}
                >
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span
                      className={
                        isAdvocate
                          ? "text-[var(--color-advocate)]"
                          : "text-[var(--color-chair)]"
                      }
                    >
                      {isAdvocate ? "(R) Regional AO · Advocate" : "(C) Committee Chair · Skeptic"}
                    </span>
                    {turn.recommendation && (
                      <Badge variant="outline" className="text-[10px]">
                        {turn.recommendation}
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm leading-relaxed text-[var(--color-ink)] whitespace-pre-wrap">
                    {turn.content}
                    {turn.streaming && (
                      <span className="inline-block w-1.5 h-4 ml-1 bg-[var(--color-advocate)] animate-pulse align-middle" />
                    )}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
