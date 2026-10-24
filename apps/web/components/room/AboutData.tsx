"use client";

import { useState } from "react";
import { Info } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import report from "../../../../data/data-report.json";

export function AboutData() {
  const [open, setOpen] = useState(false);
  const verified = report.status === "verified" && !!report.verified_at;
  const number = (value: number | null) => verified && value !== null ? value.toLocaleString() : "Not verified yet";
  return <>
    <button type="button" onClick={() => setOpen(true)} className="inline-flex items-center gap-1.5 rounded px-1 py-0.5 text-muted hover:text-ink"><Info className="size-3" />About the data</button>
    <Sheet open={open} onOpenChange={setOpen}><SheetContent side="right" className="w-full overflow-y-auto border-line bg-panel p-6 text-ink sm:max-w-md">
      <SheetHeader className="mb-6 text-left"><SheetTitle className="font-display text-2xl text-ink">What the evidence can tell you</SheetTitle>
        <SheetDescription className="text-sm leading-relaxed text-muted">Know which figures are verified and which are illustrative before interpreting an estimate.</SheetDescription></SheetHeader>
      <div className="space-y-6 text-sm leading-relaxed">
        <section className="rounded-xl border border-waitlist/30 bg-waitlist/5 p-4"><h3 className="mb-2 font-semibold text-waitlist">The current demo is fictional</h3>
          <p className="text-muted">Its applicant profiles, school inputs and outcomes were written for development. Its percentages come from the scoring code, using those fictional inputs. They do not measure real admissions accuracy.</p></section>
        <dl className="divide-y divide-line">{[["Verified applicant corpus", number(report.n_twins)], ["Universities loaded", number(report.n_schools)],
          ["Schools with CDS weights", number(report.n_cds_schools)], ["Model Brier score", number(report.brier)], ["Base-rate Brier score", number(report.brier_base)]].map(([label, value]) => <div key={label} className="flex justify-between gap-4 py-3"><dt className="text-muted">{label}</dt><dd className="text-right font-mono text-xs">{value}</dd></div>)}</dl>
        <section><h3 className="mb-2 font-display text-lg">Planned sources</h3><p className="text-muted">Institutional facts come from Common Data Sets, IPEDS and College Scorecard through Zetaris. Comparable outcomes come from self-reported Reddit posts retrieved through Supabase. A working local Zetaris platform does not establish that these project datasets are loaded.</p></section>
        <section><h3 className="mb-2 font-display text-lg">How to read the charts</h3><p className="text-muted">The model computes probabilities and changes; the language models explain and debate. The range shows uncertainty. Reddit outcomes are self-selected and comparisons do not establish why an applicant was admitted. The dashed Personal reference is assumed because those profiles have no essays.</p></section>
        <p className="border-t border-line pt-4 text-xs text-muted">{verified ? `Report verified ${report.verified_at}.` : report.notes} Admissions decisions remain with the university.</p>
      </div>
    </SheetContent></Sheet>
  </>;
}
