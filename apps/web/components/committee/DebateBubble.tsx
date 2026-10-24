"use client";

import { motion } from "framer-motion";
import { CitationText } from "./CitationText";
import type { DebateTurn } from "@/lib/types";
import type { RunView } from "@/store/run-store";
import { cn } from "@/lib/utils";

const VOICE = {
  advocate: {
    name: "Regional Admissions Officer",
    role: "Advocate",
    initial: "R",
    side: "self-start",
    borderColor: "border-[var(--color-advocate)]/40",
    avatarBg: "bg-[var(--color-advocate)]",
  },
  chair: {
    name: "Committee Chair",
    role: "Skeptic",
    initial: "C",
    side: "self-end",
    borderColor: "border-[var(--color-chair)]/40",
    avatarBg: "bg-[var(--color-chair)]",
  },
} as const;

export function DebateBubble({ turn, run }: { turn: DebateTurn; run: RunView }) {
  const v = VOICE[turn.speaker];

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 14, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 260, damping: 26 }}
      className={cn(
        "max-w-[86%] rounded-2xl border bg-[var(--color-panel)] p-4 shadow-lg",
        v.side,
        v.borderColor
      )}
      aria-live={turn.streaming ? "polite" : undefined}
    >
      <header className="mb-2 flex items-center gap-2 text-xs text-[var(--color-muted)]">
        <span
          className={cn(
            "grid h-7 w-7 place-items-center rounded-full font-display text-sm font-semibold text-[var(--color-room)]",
            v.avatarBg
          )}
        >
          {v.initial}
        </span>
        <span className="font-medium text-[var(--color-ink)]">{v.name}</span>
        <span>
          · {v.role} · Turn {turn.turn}
        </span>
        {turn.degraded && (
          <span className="ml-auto rounded bg-[var(--color-waitlist)]/15 px-1.5 py-0.5 text-[10px] text-[var(--color-waitlist)] font-mono">
            fallback
          </span>
        )}
      </header>
      <CitationText
        content={turn.content}
        streaming={turn.streaming}
        citations={turn.citations}
        run={run}
      />
    </motion.article>
  );
}
