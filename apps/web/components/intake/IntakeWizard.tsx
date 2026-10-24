"use client";

export function IntakeWizard() {
  return (
    <div className="w-full max-w-2xl rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] p-8 shadow-xl">
      <div className="mb-6 space-y-2 text-center">
        <h2 className="font-display text-2xl font-bold tracking-tight text-[var(--color-ink)]">
          Applicant Dossier Intake
        </h2>
        <p className="text-sm text-[var(--color-muted)]">
          Upload an applicant file (transcript, activities, essay) to convene the committee.
        </p>
      </div>
      <div className="rounded-lg border border-dashed border-[var(--color-line)] p-12 text-center hover:border-[var(--color-advocate)] transition-colors cursor-pointer bg-[var(--color-panel-2)]/50">
        <p className="text-sm font-medium text-[var(--color-ink)]">
          Drag & drop PDF dossier, or click to browse
        </p>
        <p className="mt-1 text-xs text-[var(--color-muted)]">
          PDF up to 10MB
        </p>
      </div>
    </div>
  );
}
