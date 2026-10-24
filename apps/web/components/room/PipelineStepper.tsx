"use client";

import { useActiveRun, type NodeStatus } from "@/store/run-store";
import type { NodeName } from "@/lib/types";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Check, AlertTriangle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface StepDef {
  key: string;
  label: string;
  nodes: NodeName[];
}

const STEPS: StepDef[] = [
  { key: "dossier", label: "Dossier", nodes: ["dossier_parser"] },
  { key: "institution", label: "Institution", nodes: ["institutional"] },
  { key: "twins", label: "Twins", nodes: ["twins"] },
  { key: "committee", label: "Committee", nodes: ["committee_docket", "advocate", "chair"] },
  { key: "delta", label: "Delta", nodes: ["delta_engine"] },
];

function resolveStepStatus(
  step: StepDef,
  nodes: Record<NodeName, NodeStatus>
): { status: NodeStatus; detail?: string } {
  // If any node is degraded
  if (step.nodes.some((n) => nodes[n] === "degraded")) {
    return { status: "degraded" };
  }
  // If any node is running
  if (step.nodes.some((n) => nodes[n] === "running")) {
    return { status: "running" };
  }
  // If all nodes are done
  if (step.nodes.every((n) => nodes[n] === "done")) {
    return { status: "done" };
  }
  return { status: "pending" };
}

export function PipelineStepper() {
  const nodes = useActiveRun((r) => r.nodes);
  const debate = useActiveRun((r) => r.debate);
  const errors = useActiveRun((r) => r.errors);

  // Active committee turn
  const committeeTurn = debate.length > 0 ? debate[debate.length - 1]?.turn : null;

  return (
    <nav
      aria-label="Pipeline progress"
      className="hidden items-center gap-1.5 md:flex"
    >
      {STEPS.map((step, idx) => {
        const { status } = resolveStepStatus(step, nodes);
        const err = errors.find((e) => step.nodes.some((n) => n === e.node));

        let indicator = (
          <span className="flex h-5 w-5 items-center justify-center rounded-full border border-[var(--color-line)] bg-[var(--color-panel-2)] text-[11px] font-mono text-[var(--color-muted)]">
            {idx + 1}
          </span>
        );

        if (status === "done") {
          indicator = (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-admit)]/20 text-[var(--color-admit)]">
              <Check className="h-3 w-3 stroke-[3]" />
            </span>
          );
        } else if (status === "running") {
          indicator = (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-advocate)]/20 text-[var(--color-advocate)]">
              <Loader2 className="h-3 w-3 animate-spin stroke-[2.5]" />
            </span>
          );
        } else if (status === "degraded") {
          indicator = (
            <span className="flex h-5 w-5 items-center justify-center rounded-full border border-amber-500 bg-amber-500/20 text-amber-400 ring-2 ring-amber-500/50">
              <AlertTriangle className="h-3 w-3" />
            </span>
          );
        }

        const stepLabel =
          step.key === "committee" && committeeTurn
            ? `Committee (${committeeTurn}/4)`
            : step.label;

        const content = (
          <div
            className={cn(
              "flex items-center gap-1.5 rounded-md px-2 py-1 text-xs transition-colors",
              status === "running" && "bg-[var(--color-panel-2)] text-[var(--color-ink)] font-medium",
              status === "done" && "text-[var(--color-ink)]",
              status === "pending" && "text-[var(--color-muted)]",
              status === "degraded" &&
                "border border-amber-500/60 bg-amber-500/10 text-amber-300 ring-1 ring-amber-500/50"
            )}
          >
            {indicator}
            <span className="font-sans">{stepLabel}</span>
            {status === "degraded" && (
              <span className="rounded bg-amber-500/20 px-1 py-0.5 text-[9px] font-mono font-semibold uppercase text-amber-300">
                fallback
              </span>
            )}
          </div>
        );

        if (status === "degraded") {
          return (
            <Tooltip key={step.key}>
              <TooltipTrigger asChild>{content}</TooltipTrigger>
              <TooltipContent className="border border-amber-500/50 bg-[var(--color-panel)] text-xs text-[var(--color-ink)]">
                <p className="font-semibold text-amber-400">Degraded Fallback Active</p>
                <p className="text-[var(--color-muted)]">
                  {err?.message ?? "Service error encountered. Operating with deterministic fallback facts."}
                </p>
              </TooltipContent>
            </Tooltip>
          );
        }

        return <div key={step.key}>{content}</div>;
      })}
    </nav>
  );
}
