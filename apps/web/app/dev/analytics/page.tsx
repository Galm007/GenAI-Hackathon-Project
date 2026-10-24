"use client";

import { useState } from "react";
import { ProbabilityGauge } from "@/components/analytics/ProbabilityGauge";
import { Waterfall } from "@/components/analytics/Waterfall";
import { sampleProbability, sampleSimulation } from "@/components/analytics/fixtures";

export default function AnalyticsPreview() {
  const [simulate, setSimulate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [highlight, setHighlight] = useState(false);
  const shown = loading ? null : simulate ? sampleSimulation.simulated : sampleProbability;
  return (
    <main className="mx-auto min-h-screen max-w-6xl space-y-8 px-5 py-10 text-ink">
      <header className="space-y-3">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-advocate">AdCom / component preview</p>
        <h1 className="font-display text-4xl">The evidence behind the estimate</h1>
        <p className="max-w-2xl text-sm text-muted">Fictional sample data for development. These figures are illustrative; this page does not evaluate an application.</p>
        <div className="flex flex-wrap gap-3 text-sm">
          {[{ label: "Show simulated result", value: simulate, set: setSimulate },
            { label: "Show loading state", value: loading, set: setLoading },
            { label: "Highlight major contribution", value: highlight, set: setHighlight }].map((control) => (
              <label key={control.label} className="flex cursor-pointer items-center gap-2 rounded-lg border border-line bg-panel px-3 py-2">
                <input type="checkbox" checked={control.value} onChange={(e) => control.set(e.target.checked)} />{control.label}
              </label>
            ))}
        </div>
      </header>
      <div className="grid gap-6 md:grid-cols-2">
        <section className="rounded-2xl border border-line bg-panel p-5">
          <h2 className="font-display text-xl">Admission estimate</h2>
          <ProbabilityGauge probability={loading ? null : sampleProbability} simulation={!loading && simulate ? sampleSimulation : null} />
        </section>
        <section className="rounded-2xl border border-line bg-panel p-5">
          <h2 className="font-display text-xl">What moves the number</h2>
          <Waterfall probability={shown} highlight={highlight ? { kind: "model", ref: "major" } : null} />
        </section>
      </div>
      <footer className="text-xs text-muted">Done by gridiii via Codex. Live data wiring belongs to C02 and the War Room integration.</footer>
    </main>
  );
}
