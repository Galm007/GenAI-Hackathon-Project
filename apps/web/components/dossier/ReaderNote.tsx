"use client";

import { useActiveRun } from "@/store/run-store";
import { PenTool } from "lucide-react";

export function ReaderNote() {
  const grade = useActiveRun((r) => r.grade);

  if (!grade?.reader_comments) return null;

  return (
    <div className="relative rounded-xl border border-[#d6cebf] bg-[var(--color-paper)] p-4 text-[var(--color-paper-ink)] shadow-lg rotate-[-1deg] transition-transform hover:rotate-0">
      <div className="flex items-center gap-1.5 text-xs font-mono font-semibold uppercase text-[#5a5243] border-b border-[#e2dacb] pb-1.5">
        <PenTool className="h-3.5 w-3.5 text-[#8c6d37]" />
        <span>Admissions Reader&apos;s Margin Note</span>
      </div>
      <p className="mt-2 font-hand text-lg leading-snug text-[#1d2433]">
        &ldquo;{grade.reader_comments}&rdquo;
      </p>
    </div>
  );
}
