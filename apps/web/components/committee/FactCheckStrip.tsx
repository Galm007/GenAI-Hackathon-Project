"use client";

import { useActiveRun } from "@/store/run-store";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Check, RefreshCw, AlertTriangle, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export function FactCheckStrip() {
  const brief = useActiveRun((r) => r.brief);

  if (!brief?.fact_checks || brief.fact_checks.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5 pt-1 border-t border-[var(--color-line)]/50">
      <span className="text-[10px] font-mono uppercase tracking-wider text-[var(--color-muted)]">
        Fact Checks:
      </span>
      {brief.fact_checks.map((fc, i) => {
        let icon = <Check className="h-3 w-3 text-[var(--color-admit)]" />;
        let badgeColor = "border-[var(--color-admit)]/30 bg-[var(--color-admit)]/10 text-[var(--color-admit)]";

        if (fc.verdict === "updated") {
          icon = <RefreshCw className="h-3 w-3 text-[var(--color-advocate)]" />;
          badgeColor = "border-[var(--color-advocate)]/30 bg-[var(--color-advocate)]/10 text-[var(--color-advocate)]";
        } else if (fc.verdict === "conflict") {
          icon = <AlertTriangle className="h-3 w-3 text-[var(--color-waitlist)]" />;
          badgeColor = "border-[var(--color-waitlist)]/30 bg-[var(--color-waitlist)]/10 text-[var(--color-waitlist)]";
        } else if (fc.verdict === "unverified") {
          icon = <HelpCircle className="h-3 w-3 text-[var(--color-muted)]" />;
          badgeColor = "border-[var(--color-line)] bg-[var(--color-panel-2)] text-[var(--color-muted)]";
        }

        return (
          <Tooltip key={`${fc.field}-${i}`}>
            <TooltipTrigger asChild>
              <div
                className={cn(
                  "inline-flex cursor-pointer items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] font-mono transition-colors",
                  badgeColor
                )}
              >
                {icon}
                <span>{fc.field.replaceAll("_", " ")}</span>
              </div>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs text-xs bg-[var(--color-panel)] border-[var(--color-line)] p-2.5 text-[var(--color-ink)]">
              <div className="space-y-1">
                <p className="font-semibold capitalize text-[var(--color-ink)]">
                  {fc.verdict}: {fc.field}
                </p>
                <p className="text-[11px] text-[var(--color-muted)]">{fc.note}</p>
                {fc.source_ids.length > 0 && (
                  <p className="text-[10px] font-mono text-[var(--color-muted)]">
                    Sources: {fc.source_ids.join(", ")}
                  </p>
                )}
              </div>
            </TooltipContent>
          </Tooltip>
        );
      })}
    </div>
  );
}
