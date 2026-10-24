"use client";

import { useState } from "react";
import { Copy, Check, Feather } from "lucide-react";
import { useActiveRun } from "@/store/run-store";

export function EssayEdits() {
  const edits = useActiveRun((r) => r.report?.essay_adjustments);
  const [copied, setCopied] = useState<string | null>(null);
  const [error, setError] = useState("");
  if (!edits?.length) return null;
  const copy = async (index: number, text: string) => {
    try { await navigator.clipboard.writeText(text); setCopied(text); setError(""); }
    catch { setError("Copy is unavailable. You can select and copy the example text below."); }
  };
  return <section aria-label="Essay suggestions" className="space-y-3">
    <h3 className="flex items-center gap-2 font-display text-lg"><Feather className="size-4 text-tier1" />Make the essay yours</h3>
    {edits.map((edit, i) => <article key={`${i}-${edit.issue}`} className="space-y-3 rounded-xl border border-line p-4">
      <h4 className="text-sm font-semibold">{edit.issue}</h4>
      <blockquote className="rounded-lg border-l-2 border-deny bg-paper px-3 py-3 font-display text-sm leading-relaxed text-paper-ink">“{edit.current_excerpt}”</blockquote>
      <p className="text-xs leading-relaxed text-muted">{edit.direction}</p>
      <div className="space-y-3 rounded-lg border border-admit/25 bg-admit/5 p-3">
        <p className="text-[10px] uppercase tracking-wider text-admit">Illustrative direction</p>
        <p className="select-text text-xs leading-relaxed">{edit.example_rewrite}</p>
        <button type="button" aria-label={`Copy rewrite ${i + 1}`} onClick={() => copy(i, edit.example_rewrite)} className="flex items-center gap-1.5 text-xs text-admit hover:underline">
          {copied === edit.example_rewrite ? <Check className="size-3" /> : <Copy className="size-3" />}{copied === edit.example_rewrite ? "Copied" : "Copy example"}
        </button>
      </div>
    </article>)}
    <p role="status" className="text-xs text-waitlist">{error}</p>
  </section>;
}
