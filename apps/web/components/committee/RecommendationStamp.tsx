"use client";

import { motion } from "framer-motion";
import type { Disposition } from "@/lib/types";
import { cn } from "@/lib/utils";

const STAMP_COLOR: Record<Disposition, string> = {
  "ADMIT": "text-[var(--color-admit)] border-[var(--color-admit)] bg-[var(--color-admit)]/10 shadow-[0_0_30px_rgba(52,211,153,0.3)]",
  "LIKELY ADMIT": "text-[var(--color-admit)] border-[var(--color-admit)] bg-[var(--color-admit)]/10 shadow-[0_0_30px_rgba(52,211,153,0.3)]",
  "WAITLIST": "text-[var(--color-waitlist)] border-[var(--color-waitlist)] bg-[var(--color-waitlist)]/10 shadow-[0_0_30px_rgba(251,191,36,0.3)]",
  "LIKELY DENY": "text-[var(--color-deny)] border-[var(--color-deny)] bg-[var(--color-deny)]/10 shadow-[0_0_30px_rgba(248,113,113,0.3)]",
  "DENY": "text-[var(--color-deny)] border-[var(--color-deny)] bg-[var(--color-deny)]/10 shadow-[0_0_30px_rgba(248,113,113,0.3)]",
};

export function RecommendationStamp({ value }: { value: Disposition }) {
  return (
    <motion.div
      initial={{ scale: 2.4, opacity: 0, rotate: -18 }}
      animate={{ scale: 1, opacity: 1, rotate: -8 }}
      transition={{ type: "spring", stiffness: 420, damping: 18 }}
      className={cn(
        "my-6 self-center rounded-lg border-4 px-8 py-3 font-display text-3xl sm:text-4xl font-black tracking-widest uppercase",
        STAMP_COLOR[value]
      )}
      role="status"
      aria-label={`Committee recommendation: ${value}`}
    >
      {value}
    </motion.div>
  );
}
