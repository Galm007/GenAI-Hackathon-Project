"use client";

import { Toaster as Sonner } from "sonner";

type ToasterProps = React.ComponentProps<typeof Sonner>;

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="dark"
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-[var(--color-panel)] group-[.toaster]:text-[var(--color-ink)] group-[.toaster]:border-[var(--color-line)] group-[.toaster]:shadow-lg",
          description: "group-[.toast]:text-[var(--color-muted)]",
          actionButton:
            "group-[.toast]:bg-[var(--color-advocate)] group-[.toast]:text-white",
          cancelButton:
            "group-[.toast]:bg-[var(--color-panel-2)] group-[.toast]:text-[var(--color-ink)]",
        },
      }}
      {...props}
    />
  );
};

export { Toaster };
