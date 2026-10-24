"use client";

import * as React from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { useActiveRun } from "@/store/run-store";
import { Database, Table, CheckCircle2, AlertCircle, Copy, Check } from "lucide-react";
import { schoolName } from "@/lib/format";
import { cn } from "@/lib/utils";

interface DataFabricDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DataFabricDrawer({ open, onOpenChange }: DataFabricDrawerProps) {
  const sqlQueries = useActiveRun((r) => r.sqlQueries);
  const schoolSlug = useActiveRun((r) => r.schoolSlug);
  const [copiedId, setCopiedId] = React.useState<string | null>(null);

  const handleCopySql = (id: string, sql: string) => {
    navigator.clipboard.writeText(sql);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-xl overflow-y-auto border-l border-[var(--color-line)] bg-[var(--color-panel)] p-6 text-[var(--color-ink)]"
      >
        <SheetHeader className="space-y-2 pb-4 border-b border-[var(--color-line)]">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--color-advocate)]/20 text-[var(--color-advocate)]">
              <Database className="h-4 w-4" />
            </div>
            <div>
              <SheetTitle className="font-display text-lg font-bold text-[var(--color-ink)]">
                Zetaris Data Fabric
              </SheetTitle>
              <span className="font-mono text-[11px] text-[var(--color-advocate)]">
                Governed Federated SQL Engine
              </span>
            </div>
          </div>
          <SheetDescription className="text-xs text-[var(--color-muted)] leading-relaxed">
            Institutional facts and cross-source benchmarks queried live across PostgreSQL metastores, Iceberg gold tables, and Common Data Set filestores for {schoolName(schoolSlug)}.
          </SheetDescription>
        </SheetHeader>

        {/* Status Strip */}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)]/60 p-3 text-xs">
          <div className="flex items-center gap-1.5 font-mono text-[11px]">
            <span className="inline-block h-2 w-2 rounded-full bg-[var(--color-admit)] animate-pulse" />
            <span className="text-[var(--color-ink)] font-medium">Metastore Connected</span>
          </div>
          <div className="flex items-center gap-3 font-mono text-[11px] text-[var(--color-muted)]">
            <span>
              Queries: <strong className="text-[var(--color-ink)]">{sqlQueries.length}</strong>
            </span>
            <span>Datasource: <strong className="text-[var(--color-ink)]">ADCOM_PG</strong></span>
          </div>
        </div>

        {/* Queries List */}
        <div className="mt-6 space-y-5">
          {sqlQueries.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[var(--color-line)] p-8 text-center">
              <Database className="mx-auto h-8 w-8 text-[var(--color-muted)]/50" />
              <p className="mt-3 text-sm font-medium text-[var(--color-ink)]">
                No Zetaris queries executed yet
              </p>
              <p className="mt-1 text-xs text-[var(--color-muted)] max-w-xs mx-auto">
                As Node 2 (Institution) runs, federated SQL queries against CDS tables and major multipliers will appear here in real time.
              </p>
            </div>
          ) : (
            sqlQueries.map((query) => {
              const columns =
                query.rows && query.rows.length > 0
                  ? Object.keys(query.rows[0])
                  : [];

              return (
                <div
                  key={query.id}
                  className="rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)]/40 p-4 space-y-3 transition-colors hover:border-[var(--color-advocate)]/40"
                >
                  {/* Query Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center rounded-md border border-[var(--color-advocate)]/50 bg-[var(--color-advocate)]/10 px-2 py-0.5 font-mono text-xs font-bold text-[var(--color-advocate)]">
                        {query.id}
                      </span>
                      <h4 className="text-sm font-medium text-[var(--color-ink)]">
                        {query.purpose}
                      </h4>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleCopySql(query.id, query.sql)}
                      title="Copy SQL"
                      className="rounded p-1 text-[var(--color-muted)] hover:bg-[var(--color-panel-2)] hover:text-white transition-colors"
                    >
                      {copiedId === query.id ? (
                        <Check className="h-3.5 w-3.5 text-[var(--color-admit)]" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>

                  {/* SQL Code Block */}
                  <div className="relative rounded-lg border border-[var(--color-line)] bg-[var(--color-room)] p-3">
                    <pre className="font-mono text-xs text-emerald-400 overflow-x-auto leading-relaxed whitespace-pre-wrap">
                      <code>{query.sql}</code>
                    </pre>
                  </div>

                  {/* Error or Rows Preview */}
                  {query.error ? (
                    <div className="flex items-center gap-2 rounded-lg border border-[var(--color-deny)]/50 bg-[var(--color-deny)]/10 p-2.5 text-xs text-[var(--color-deny)]">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      <span>{query.error}</span>
                    </div>
                  ) : query.rows && query.rows.length > 0 ? (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs font-mono text-[var(--color-muted)]">
                        <span className="flex items-center gap-1">
                          <Table className="h-3.5 w-3.5" /> Result Rows
                        </span>
                        <span className="rounded bg-[var(--color-panel)] px-1.5 py-0.5 text-[10px]">
                          {query.rows.length} {query.rows.length === 1 ? "row" : "rows"}
                        </span>
                      </div>

                      <div className="max-h-48 overflow-x-auto overflow-y-auto rounded-lg border border-[var(--color-line)] bg-[var(--color-room)]">
                        <table className="w-full text-left text-xs font-mono">
                          <thead>
                            <tr className="border-b border-[var(--color-line)] bg-[var(--color-panel-2)]/60 text-[var(--color-muted)]">
                              {columns.map((col) => (
                                <th key={col} className="px-2.5 py-1.5 font-semibold">
                                  {col}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {query.rows.slice(0, 10).map((row, rIdx) => (
                              <tr
                                key={rIdx}
                                className="border-b border-[var(--color-line)]/50 last:border-b-0 hover:bg-[var(--color-panel-2)]/30 transition-colors"
                              >
                                {columns.map((col) => (
                                  <td
                                    key={col}
                                    className="px-2.5 py-1 text-[var(--color-ink)] truncate max-w-xs"
                                  >
                                    {row[col] ?? "NULL"}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-xs font-mono text-[var(--color-muted)]">
                      <CheckCircle2 className="h-3.5 w-3.5 text-[var(--color-admit)]" />
                      <span>Query executed successfully (0 rows returned)</span>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
