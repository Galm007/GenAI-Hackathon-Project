"use client";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { chipLabel } from "@/lib/citations";
import type { Citation } from "@/lib/types";
import { useRunStore, type RunView } from "@/store/run-store";
import { cn } from "@/lib/utils";

const KIND_STYLE: Record<Citation["kind"], string> = {
  dossier: "bg-[var(--color-paper)]/90 text-[var(--color-paper-ink)]",
  cds: "bg-[var(--color-advocate)]/15 text-[var(--color-advocate)] ring-1 ring-[var(--color-advocate)]/40",
  twin: "bg-[var(--color-tier1)]/15 text-[var(--color-tier1)] ring-1 ring-[var(--color-tier1)]/40",
  web: "bg-[var(--color-muted)]/15 text-[var(--color-ink)] ring-1 ring-[var(--color-line)]",
  model: "bg-[var(--color-admit)]/15 text-[var(--color-admit)] ring-1 ring-[var(--color-admit)]/40",
  sql: "bg-[var(--color-chair)]/10 text-[var(--color-ink)] ring-1 ring-[var(--color-chair)]/40 font-semibold", // Zetaris evidence
};

export function CitationChip({
  kind,
  refId,
  valid,
  run,
}: {
  kind: Citation["kind"];
  refId: string;
  valid: boolean | undefined;
  run: RunView;
}) {
  const setHighlight = useRunStore((s) => s.setHighlight);
  const label = chipLabel(kind, refId, run);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          onMouseEnter={() => setHighlight({ kind, ref: refId })}
          onMouseLeave={() => setHighlight(null)}
          onFocus={() => setHighlight({ kind, ref: refId })}
          onBlur={() => setHighlight(null)}
          className={cn(
            "mx-0.5 inline-flex translate-y-[-1px] items-center rounded-md px-1.5 py-0.5 font-mono text-[11px] leading-none transition-colors",
            KIND_STYLE[kind],
            valid === false &&
              "bg-[var(--color-waitlist)]/10 text-[var(--color-waitlist)] line-through ring-1 ring-[var(--color-waitlist)]/40"
          )}
          aria-label={`Evidence: ${label}${valid === false ? " (unverified)" : ""}`}
        >
          {label}
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs bg-[var(--color-panel)] border-[var(--color-line)] p-2.5 text-[var(--color-ink)]">
        {valid === false ? (
          "The validator couldn't match this citation to the docket. Treat it as unverified."
        ) : (
          <EvidencePreview kind={kind} refId={refId} run={run} />
        )}
      </TooltipContent>
    </Tooltip>
  );
}

function EvidencePreview({
  kind,
  refId,
  run,
}: {
  kind: Citation["kind"];
  refId: string;
  run: RunView;
}) {
  if (kind === "web") {
    const s = run.snippets.find((x) => x.id === refId);
    return s ? (
      <div className="space-y-1">
        <p className="font-semibold text-[var(--color-ink)]">{s.title}</p>
        <p className="text-[11px] text-[var(--color-muted)]">{s.content.slice(0, 220)}…</p>
      </div>
    ) : null;
  }

  if (kind === "twin") {
    const t = run.twins.find((x) => String(x.index) === refId);
    return t ? (
      <div className="space-y-1">
        <p className="font-semibold text-[var(--color-ink)]">{t.headline ?? `Twin #${t.index}`}</p>
        <p className="text-[11px] text-[var(--color-muted)]">{t.spike_summary}</p>
      </div>
    ) : null;
  }

  if (kind === "sql") {
    const q = run.sqlQueries.find((x) => x.id === refId);
    return q ? (
      <div className="space-y-1.5">
        <p className="font-semibold text-[var(--color-ink)]">
          Zetaris Lightning · {q.id}: {q.purpose}
        </p>
        <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded bg-[var(--color-room)] p-2 font-mono text-[10px] text-[var(--color-muted)]">
          {q.sql}
        </pre>
        <p className="text-[10px] text-[var(--color-muted)]">
          {q.rows.length} row{q.rows.length === 1 ? "" : "s"} · federated over CDS, Scorecard, IPEDS and Reddit outcomes
        </p>
      </div>
    ) : null;
  }

  if (kind === "cds" && refId.startsWith("c7.")) {
    const level = run.rubric?.factor_levels[refId.slice(3)];
    return (
      <p>
        Common Data Set C7:{" "}
        <strong className="text-[var(--color-advocate)]">{level?.replaceAll("_", " ")}</strong> (
        {run.rubric?.name})
      </p>
    );
  }

  return <p className="font-mono text-[11px]">{kind}:{refId}</p>;
}
