import { IntakeWizard } from "@/components/intake/IntakeWizard";
import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 md:p-12 bg-[radial-gradient(ellipse_at_top,_var(--color-panel)_0%,_var(--color-room)_70%)]">
      <div className="z-10 max-w-5xl w-full flex flex-col items-center gap-8">
        <header className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[var(--color-line)] bg-[var(--color-panel-2)] text-xs text-[var(--color-muted)] font-mono">
            <span className="inline-block w-2 h-2 rounded-full bg-[var(--color-admit)] animate-pulse" />
            AdCom Admissions War Room
          </div>
          <h1 className="font-display text-4xl sm:text-6xl font-bold tracking-tight text-[var(--color-ink)]">
            Autonomous Admissions Committee
          </h1>
          <p className="max-w-2xl text-base sm:text-lg text-[var(--color-muted)]">
            Explore how an admissions committee could read your application, discuss the evidence, and compare possible next steps.
          </p>
        </header>

        <IntakeWizard />
        <Link href="/room/demo/maya-uiuc" className="inline-flex items-center gap-2 rounded-full border border-[var(--color-advocate)]/30 bg-[var(--color-advocate)]/10 px-5 py-2.5 text-sm text-[var(--color-ink)] transition hover:bg-[var(--color-advocate)]/20">Explore the fictional demo <span aria-hidden="true">↗</span></Link>
      </div>
    </main>
  );
}
