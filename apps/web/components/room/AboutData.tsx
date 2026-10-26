"use client";

import { useState } from "react";
import { Info } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetTrigger } from "@/components/ui/sheet";
import report from "../../../../data/data-report.json";

export function AboutData({ fictionalReplay = false }: { fictionalReplay?: boolean }) {
  const [open, setOpen] = useState(false);
  const reported = ["partial", "verified"].includes(report.status) && !!report.verified_at;
  const number = (value: number | null) => reported && value !== null ? value.toLocaleString("en-US") : "Not measured yet";
  const accuracyPending = report.brier === null || report.brier_base === null;
  return <Sheet open={open} onOpenChange={setOpen}>
    <SheetTrigger asChild><button type="button" className="inline-flex items-center gap-1.5 rounded px-1 py-0.5 text-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-advocate"><Info className="size-3" />About the data</button></SheetTrigger>
    <SheetContent side="right" className="w-full overflow-y-auto border-line bg-panel p-6 text-ink sm:max-w-md">
      <SheetHeader className="mb-6 pr-6 text-left"><SheetTitle className="font-display text-2xl text-ink">What the evidence can tell you</SheetTitle>
        <SheetDescription className="text-sm leading-relaxed text-muted">Reported dataset coverage and the limits of the estimates.</SheetDescription></SheetHeader>
      <div className="space-y-6 text-sm leading-relaxed">
        {fictionalReplay && <section className="rounded-xl border border-waitlist/30 bg-waitlist/5 p-4"><h3 className="mb-2 font-semibold text-waitlist">This replay is fictional</h3>
          <p className="text-muted">Its applicant profiles, school inputs and outcomes were written for development. Its percentages use those fictional inputs. The real corpus figures below describe the team&apos;s dataset; this replay does not use that corpus or establish admissions accuracy.</p></section>}
        <section aria-labelledby="corpus-title"><h3 id="corpus-title" className="font-display text-lg">Reported dataset</h3>
          <p className="mt-1 text-xs text-muted">{reported ? `Track A data report · ${report.verified_at}` : "Corpus figures have not been verified yet."}</p>
          <dl className="mt-2 divide-y divide-line">{[["Applicant profiles", number(report.n_twins)], ["Universities loaded", number(report.n_schools)],
            ["Schools with CDS weights", number(report.n_cds_schools)]].map(([label, value]) => <div key={label} className="flex items-baseline justify-between gap-4 py-3"><dt className="text-muted">{label}</dt><dd className="font-mono text-lg tabular-nums">{value}</dd></div>)}</dl>
          <p className="mt-2 text-xs text-muted">{number(report.n_first_year_twins)} first-year and {number(report.n_transfer_twins)} transfer profiles. Fictional replay profiles are excluded.</p>
        </section>
        {reported && <section><table className="w-full text-left text-xs">
          <caption className="mb-3 text-left font-display text-lg text-ink">Demo-school coverage</caption>
          <thead className="text-muted"><tr><th scope="col" className="pb-2 font-normal">School</th><th scope="col" className="pb-2 text-right font-normal">First-year</th><th scope="col" className="pb-2 text-right font-normal">CS</th></tr></thead>
          <tbody className="divide-y divide-line">{report.demo_school_coverage.map((school) => <tr key={school.slug}><th scope="row" className="py-2 pr-2 font-normal">{school.name}</th><td className="py-2 text-right font-mono tabular-nums">{number(school.first_year_outcomes)}</td><td className="py-2 text-right font-mono tabular-nums">{number(school.computer_science_outcomes)}</td></tr>)}</tbody>
        </table><p className="mt-2 text-xs text-muted">First-year outcomes reported for each school; CS is the computer-science subset. One applicant may have outcomes at several schools.</p></section>}
        <section><h3 className="mb-2 font-display text-lg">Self-selection and accuracy</h3>
          <p className="text-muted">The median Reddit odds inflation is <span className="font-mono text-ink">{reported ? `${report.odds_inflation_median.toFixed(2)}×` : "not measured yet"}</span> across {number(report.odds_inflation_n_schools)} schools with at least {report.odds_inflation_min_outcomes} outcomes. This describes an approximate adjustment for self-selection; it is not an accuracy score.</p>
          <dl className="mt-3 divide-y divide-line">{[["Model Brier score", number(report.brier)], ["Base-rate Brier score", number(report.brier_base)]].map(([label, value]) => <div key={label} className="flex justify-between gap-4 py-3"><dt className="text-muted">{label}</dt><dd className="text-right font-mono text-xs">{value}</dd></div>)}</dl>
          {accuracyPending && <p className="mt-2 text-xs text-waitlist">The held-out backtest and bias audit are pending. Reported dataset size does not establish predictive accuracy.</p>}
        </section>
        <section><h3 className="mb-2 font-display text-lg">Dataset sources</h3><p className="text-muted">The team&apos;s report covers Common Data Set rubrics for {number(report.n_cds_schools)} schools, with IPEDS fallback for the other {reported ? (report.n_schools - report.n_cds_schools).toLocaleString("en-US") : "unverified schools"}, and College Scorecard institutional data through Zetaris. Comparable outcomes are self-reported Reddit posts stored in Supabase.</p></section>
        <section><h3 className="mb-2 font-display text-lg">How to read the charts</h3><p className="text-muted">The model computes probabilities and changes; the language models explain and debate. The range shows uncertainty. Reddit outcomes are self-selected and comparisons do not establish why an applicant was admitted. The dashed Personal reference is assumed because those profiles have no essays.</p></section>
        <footer className="space-y-3 border-t border-line pt-4 text-xs text-muted">
          {reported && <a href={report.source_url} target="_blank" rel="noopener noreferrer" className="inline-block text-advocate underline underline-offset-4">Read the source data report</a>}
          <p>{report.notes} Admissions decisions remain with the university.</p>
        </footer>
      </div>
    </SheetContent>
  </Sheet>;
}
