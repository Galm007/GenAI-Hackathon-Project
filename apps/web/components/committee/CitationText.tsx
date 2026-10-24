"use client";

import { tokenize } from "@/lib/citations";
import { CitationChip } from "./CitationChip";
import type { Citation } from "@/lib/types";
import type { RunView } from "@/store/run-store";

export function CitationText({
  content,
  streaming,
  citations,
  run,
}: {
  content: string;
  streaming: boolean;
  citations: Citation[];
  run: RunView;
}) {
  const segments = tokenize(content, streaming, citations);

  return (
    <div className="whitespace-pre-wrap text-[15px] leading-7 text-[var(--color-ink)]">
      {segments.map((seg, i) =>
        seg.type === "text" ? (
          <span key={i}>{seg.text}</span>
        ) : (
          <CitationChip
            key={i}
            kind={seg.kind}
            refId={seg.ref}
            valid={seg.valid}
            run={run}
          />
        )
      )}
      {streaming && (
        <span className="ml-0.5 inline-block h-4 w-[2px] animate-pulse bg-[var(--color-ink)] align-middle" />
      )}
    </div>
  );
}
