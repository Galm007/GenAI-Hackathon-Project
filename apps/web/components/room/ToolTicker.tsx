"use client";

import { useActiveRun } from "@/store/run-store";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { AnimatePresence, motion } from "framer-motion";
import { Settings, Database } from "lucide-react";
import { cn } from "@/lib/utils";

export function ToolTicker() {
  const tools = useActiveRun((r) => r.tools);
  const sqlQueries = useActiveRun((r) => r.sqlQueries);

  // Take the last 6 tools
  const recentTools = tools.slice(-6);

  if (recentTools.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 overflow-hidden py-1">
      <span className="text-[10px] font-mono uppercase tracking-wider text-[var(--color-muted)]">
        Tools:
      </span>
      <AnimatePresence initial={false}>
        {recentTools.map((tc, idx) => {
          const isZetaris = tc.tool.toLowerCase().includes("zetaris") || tc.tool.toLowerCase().includes("sql");
          const queryId = typeof tc.query_id === "string" ? tc.query_id : null;
          const queryDetails = queryId ? sqlQueries.find((q) => q.id === queryId) : null;

          const isDone = tc.status === "done" || tc.status === "complete" || tc.status === "success";
          const isFailed = tc.status === "failed" || tc.status === "error";
          const isRunning = !isDone && !isFailed;

          const label = tc.tool.replace(/^adcom_/, "");

          const chip = (
            <motion.div
              key={`${tc.seq ?? idx}-${tc.tool}`}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.2 }}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-mono transition-colors",
                isDone && "border-[var(--color-admit)]/40 bg-[var(--color-admit)]/10 text-[var(--color-admit)]",
                isRunning && "border-[var(--color-advocate)]/40 bg-[var(--color-advocate)]/10 text-[var(--color-advocate)] animate-pulse",
                isFailed && "border-[var(--color-waitlist)]/40 bg-[var(--color-waitlist)]/10 text-[var(--color-waitlist)]"
              )}
            >
              {isZetaris ? (
                <Database className="h-3 w-3 shrink-0" />
              ) : (
                <Settings className={cn("h-3 w-3 shrink-0", isRunning && "animate-spin")} />
              )}
              <span>{label}</span>
              {queryId && <span className="opacity-75">· {queryId}</span>}
            </motion.div>
          );

          if (queryDetails) {
            return (
              <Tooltip key={`${tc.seq ?? idx}-${tc.tool}`}>
                <TooltipTrigger asChild>{chip}</TooltipTrigger>
                <TooltipContent className="max-w-md bg-[var(--color-panel)] border-[var(--color-line)] p-3 text-xs">
                  <div className="space-y-1">
                    <p className="font-semibold text-[var(--color-ink)]">
                      Zetaris Query: {queryDetails.purpose}
                    </p>
                    <pre className="overflow-x-auto rounded bg-[var(--color-room)] p-1.5 font-mono text-[10px] text-[var(--color-muted)]">
                      {queryDetails.sql}
                    </pre>
                    <p className="text-[10px] text-[var(--color-muted)]">
                      {queryDetails.rows.length} rows returned
                      {queryDetails.error && ` · Error: ${queryDetails.error}`}
                    </p>
                  </div>
                </TooltipContent>
              </Tooltip>
            );
          }

          return <div key={`${tc.seq ?? idx}-${tc.tool}`}>{chip}</div>;
        })}
      </AnimatePresence>
    </div>
  );
}
