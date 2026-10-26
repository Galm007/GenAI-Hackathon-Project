"use client";

import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { useEffect, useRef } from "react";
import { DebateBubble } from "./DebateBubble";
import { RecommendationStamp } from "./RecommendationStamp";
import { FactCheckStrip } from "./FactCheckStrip";
import { ToolTicker } from "@/components/room/ToolTicker";
import { runFailure, useActiveRun, type RunView } from "@/store/run-store";
import { schoolName } from "@/lib/format";
import { cn } from "@/lib/utils";

const VOICE_NAMES = {
  advocate: "Regional Admissions Officer",
  chair: "Committee Chair",
};

function TypingIndicator({ speaker }: { speaker: "advocate" | "chair" }) {
  const name = VOICE_NAMES[speaker];

  return (
    <div
      className={cn(
        "flex items-center gap-1.5 rounded-full border border-[var(--color-line)] bg-[var(--color-panel)] px-3.5 py-2 text-xs text-[var(--color-muted)]",
        speaker === "advocate" ? "self-start" : "self-end"
      )}
    >
      <span>{name} is thinking</span>
      <div className="flex items-center gap-1 ml-1">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-[var(--color-advocate)]"
            animate={{ opacity: [0.2, 1, 0.2] }}
            transition={{ repeat: Infinity, duration: 1, delay: i * 0.15 }}
          />
        ))}
      </div>
    </div>
  );
}

function PreMeeting({ run }: { run: RunView }) {
  const lines = Object.entries(run.progress);

  return (
    <div className="mx-auto my-auto max-w-md space-y-3 text-center text-sm text-[var(--color-muted)]">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-panel-2)] text-[var(--color-advocate)]">
        <span className="font-display text-lg font-bold">AdCom</span>
      </div>
      <p className="font-display text-lg text-[var(--color-ink)]">
        The committee is assembling.
      </p>
      {lines.map(([node, msg]) => (
        <motion.p
          key={node}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-xs font-mono text-[var(--color-advocate)]"
        >
          ⚙ {msg}
        </motion.p>
      ))}
    </div>
  );
}

function RunFailed({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="mx-auto my-auto w-full max-w-md space-y-3 rounded-xl border border-[var(--color-deny)]/40 bg-[var(--color-panel)] px-6 py-5 text-center text-sm"
    >
      <p className="font-display text-lg text-[var(--color-ink)]">The committee couldn&apos;t meet.</p>
      <p className="text-[var(--color-muted)]">{message}</p>
      <div className="flex flex-wrap justify-center gap-2 pt-1">
        <Link
          href="/"
          className="rounded-full border border-[var(--color-line)] px-4 py-1.5 text-[var(--color-ink)] transition hover:bg-[var(--color-panel-2)]"
        >
          Start a new evaluation
        </Link>
        <Link
          href="/room/demo/maya-uiuc"
          className="rounded-full border border-[var(--color-advocate)]/30 bg-[var(--color-advocate)]/10 px-4 py-1.5 text-[var(--color-ink)] transition hover:bg-[var(--color-advocate)]/20"
        >
          Watch the demo replay
        </Link>
      </div>
    </div>
  );
}

export function CommitteeRoom() {
  const run = useActiveRun((r) => r);
  const scroller = useRef<HTMLDivElement>(null);
  const pinned = useRef(true); // auto-scroll unless user scrolled up

  useEffect(() => {
    const el = scroller.current;
    if (el && pinned.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [run.debate, run.progress]);

  const last = run.debate.at(-1);
  const final = run.debate.find((t) => t.recommendation)?.recommendation;
  const failure = runFailure(run);

  const displaySchool =
    run.rubric?.name ?? (run.schoolSlug ? schoolName(run.schoolSlug) : "UIUC");
  const majorDetail =
    run.rubric?.major_college ??
    run.rubric?.major_category?.replaceAll("_", " ") ??
    "Admissions Review";

  return (
    <section className="flex h-full flex-col bg-[var(--color-room)]">
      <header className="border-b border-[var(--color-line)] bg-[var(--color-panel)] px-6 py-3.5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display text-xl font-bold text-[var(--color-ink)]">
              Committee Room · {displaySchool}
            </h2>
            <p className="text-xs text-[var(--color-muted)]">
              {majorDetail} · CDS {run.rubric ? "loaded" : "loading"}
            </p>
          </div>
        </div>

        <ToolTicker />
        <FactCheckStrip />
      </header>

      <div
        ref={scroller}
        onScroll={(e) => {
          const el = e.currentTarget;
          pinned.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        }}
        className="flex flex-1 flex-col gap-4 overflow-y-auto px-6 py-6"
      >
        {run.debate.length === 0 && !failure && <PreMeeting run={run} />}

        <AnimatePresence initial={false}>
          {run.debate.map((t) => (
            <DebateBubble key={t.turn} turn={t} run={run} />
          ))}
        </AnimatePresence>

        {!failure && last?.streaming && last.content === "" && (
          <TypingIndicator speaker={last.speaker} />
        )}

        {final && <RecommendationStamp value={final} />}

        {failure && <RunFailed message={failure} />}
      </div>
    </section>
  );
}
