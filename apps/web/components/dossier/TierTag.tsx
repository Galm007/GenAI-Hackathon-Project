import type { Tier } from "@/lib/types";
import { cn } from "@/lib/utils";

const TIER_STYLE: Record<Tier, string> = {
  1: "bg-[var(--color-tier1)] text-[var(--color-room)]",
  2: "bg-[var(--color-tier2)] text-[var(--color-room)]",
  3: "bg-[var(--color-tier3)] text-[var(--color-room)]",
  4: "bg-[var(--color-tier4)] text-[var(--color-ink)]",
};

export function TierTag({ tier, lit = false }: { tier: Tier; lit?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex h-5 min-w-8 items-center justify-center rounded-full px-1.5 font-mono text-[10px] font-bold shadow-sm",
        TIER_STYLE[tier],
        lit && "ring-2 ring-[var(--color-ink)]"
      )}
      aria-label={`Tier ${tier}`}
    >
      T{tier}
    </span>
  );
}
