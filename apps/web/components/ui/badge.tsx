import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground shadow hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow hover:bg-destructive/80",
        outline: "text-foreground",
        tier1: "border-[var(--color-tier1)] text-[var(--color-tier1)] bg-[var(--color-tier1)]/10",
        tier2: "border-[var(--color-tier2)] text-[var(--color-tier2)] bg-[var(--color-tier2)]/10",
        tier3: "border-[var(--color-tier3)] text-[var(--color-tier3)] bg-[var(--color-tier3)]/10",
        tier4: "border-[var(--color-tier4)] text-[var(--color-tier4)] bg-[var(--color-tier4)]/10",
        admit: "border-[var(--color-admit)] text-[var(--color-admit)] bg-[var(--color-admit)]/10",
        waitlist: "border-[var(--color-waitlist)] text-[var(--color-waitlist)] bg-[var(--color-waitlist)]/10",
        deny: "border-[var(--color-deny)] text-[var(--color-deny)] bg-[var(--color-deny)]/10",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
