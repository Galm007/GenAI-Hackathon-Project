"use client";

import { motion } from "framer-motion";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useActiveRun } from "@/store/run-store";
import type { Pillar } from "@/lib/types";
import { cn } from "@/lib/utils";

const PILLARS: { key: Pillar; label: string }[] = [
  { key: "academic", label: "Academic" },
  { key: "extracurricular", label: "Extracurricular" },
  { key: "personal", label: "Personal" },
  { key: "athletic", label: "Athletic" },
];

// 1 (strongest) → 6: emerald → coral
const RATING_BG = [
  "",
  "bg-[var(--color-admit)] text-[var(--color-room)]",
  "bg-[var(--color-admit)]/70 text-[var(--color-room)]",
  "bg-[var(--color-tier2)] text-[var(--color-room)]",
  "bg-[var(--color-waitlist)]/80 text-[var(--color-room)]",
  "bg-[var(--color-deny)]/80 text-[var(--color-room)]",
  "bg-[var(--color-deny)] text-[var(--color-room)]",
];

export function HarvardScorecard() {
  const harvard = useActiveRun((r) => r.grade?.harvard);
  const weights = useActiveRun((r) => r.rubric?.pillar_weights);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wider text-[var(--color-muted)]">
        <span>Harvard Scorecard (1 is strongest)</span>
        {harvard && <span className="text-[10px] lowercase text-[var(--color-admit)]">graded</span>}
      </div>
      <div
        className="grid grid-cols-4 gap-2"
        aria-label="Harvard-style ratings, 1 is strongest"
      >
        {PILLARS.map(({ key, label }, i) => {
          const r = harvard?.[key];
          return (
            <Tooltip key={key}>
              <TooltipTrigger asChild>
                <motion.div
                  initial={{ rotateY: 90, opacity: 0 }}
                  animate={r ? { rotateY: 0, opacity: 1 } : { rotateY: 0, opacity: 0.5 }}
                  transition={{
                    delay: i * 0.15,
                    type: "spring",
                    stiffness: 200,
                    damping: 20,
                  }}
                  className={cn(
                    "flex aspect-square flex-col items-center justify-center rounded-lg shadow-sm cursor-pointer transition-transform hover:scale-105",
                    r ? RATING_BG[r.rating] : "animate-pulse bg-[var(--color-panel-2)] text-[var(--color-muted)]"
                  )}
                >
                  <span className="font-display text-2xl sm:text-3xl font-bold leading-none">
                    {r ? `${r.rating}${r.modifier}` : "–"}
                  </span>
                  <span className="mt-1 text-[10px] font-mono uppercase tracking-wider">
                    {label.slice(0, 4)}
                  </span>
                  {weights && (
                    <span className="font-mono text-[9px] opacity-75">
                      w {(weights[key] * 100).toFixed(0)}%
                    </span>
                  )}
                </motion.div>
              </TooltipTrigger>
              {r && (
                <TooltipContent className="max-w-xs text-xs bg-[var(--color-panel)] border-[var(--color-line)] p-3 text-[var(--color-ink)]">
                  <p className="font-semibold text-[var(--color-ink)]">
                    {label}: {r.rating}{r.modifier} (1 = strongest)
                  </p>
                  <p className="mt-1 text-[11px] leading-relaxed text-[var(--color-muted)]">
                    {r.rationale}
                  </p>
                  {r.evidence.length > 0 && (
                    <p className="mt-1.5 font-mono text-[10px] text-[var(--color-muted)]">
                      Evidence: {r.evidence.join(", ")}
                    </p>
                  )}
                </TooltipContent>
              )}
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
}
