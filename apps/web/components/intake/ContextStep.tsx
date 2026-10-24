"use client";

import * as React from "react";
import { Info, ShieldCheck, Sparkles } from "lucide-react";
import { Switch } from "@/components/ui/switch";

export const US_STATES = [
  { code: "", label: "Select State (Optional)" },
  { code: "AL", label: "Alabama (AL)" },
  { code: "AK", label: "Alaska (AK)" },
  { code: "AZ", label: "Arizona (AZ)" },
  { code: "AR", label: "Arkansas (AR)" },
  { code: "CA", label: "California (CA)" },
  { code: "CO", label: "Colorado (CO)" },
  { code: "CT", label: "Connecticut (CT)" },
  { code: "DE", label: "Delaware (DE)" },
  { code: "FL", label: "Florida (FL)" },
  { code: "GA", label: "Georgia (GA)" },
  { code: "HI", label: "Hawaii (HI)" },
  { code: "ID", label: "Idaho (ID)" },
  { code: "IL", label: "Illinois (IL)" },
  { code: "IN", label: "Indiana (IN)" },
  { code: "IA", label: "Iowa (IA)" },
  { code: "KS", label: "Kansas (KS)" },
  { code: "KY", label: "Kentucky (KY)" },
  { code: "LA", label: "Louisiana (LA)" },
  { code: "ME", label: "Maine (ME)" },
  { code: "MD", label: "Maryland (MD)" },
  { code: "MA", label: "Massachusetts (MA)" },
  { code: "MI", label: "Michigan (MI)" },
  { code: "MN", label: "Minnesota (MN)" },
  { code: "MS", label: "Mississippi (MS)" },
  { code: "MO", label: "Missouri (MO)" },
  { code: "MT", label: "Montana (MT)" },
  { code: "NE", label: "Nebraska (NE)" },
  { code: "NV", label: "Nevada (NV)" },
  { code: "NH", label: "New Hampshire (NH)" },
  { code: "NJ", label: "New Jersey (NJ)" },
  { code: "NM", label: "New Mexico (NM)" },
  { code: "NY", label: "New York (NY)" },
  { code: "NC", label: "North Carolina (NC)" },
  { code: "ND", label: "North Dakota (ND)" },
  { code: "OH", label: "Ohio (OH)" },
  { code: "OK", label: "Oklahoma (OK)" },
  { code: "OR", label: "Oregon (OR)" },
  { code: "PA", label: "Pennsylvania (PA)" },
  { code: "RI", label: "Rhode Island (RI)" },
  { code: "SC", label: "South Carolina (SC)" },
  { code: "SD", label: "South Dakota (SD)" },
  { code: "TN", label: "Tennessee (TN)" },
  { code: "TX", label: "Texas (TX)" },
  { code: "UT", label: "Utah (UT)" },
  { code: "VT", label: "Vermont (VT)" },
  { code: "VA", label: "Virginia (VA)" },
  { code: "WA", label: "Washington (WA)" },
  { code: "WV", label: "West Virginia (WV)" },
  { code: "WI", label: "Wisconsin (WI)" },
  { code: "WY", label: "Wyoming (WY)" },
  { code: "INTL", label: "International" },
];

export const SCHOOL_TYPES = [
  { value: "", label: "Select School Type (Optional)" },
  { value: "Public", label: "Public High School" },
  { value: "Private", label: "Private Independent School" },
  { value: "Charter", label: "Charter School" },
  { value: "Magnet", label: "Magnet / Selective Public School" },
  { value: "Homeschool", label: "Homeschooled" },
  { value: "International", label: "International School" },
];

export interface ContextStepProps {
  residencyState: string;
  onSetResidencyState: (state: string) => void;
  schoolType: string;
  onSetSchoolType: (type: string) => void;
  firstGen: boolean;
  onSetFirstGen: (firstGen: boolean) => void;
  lowIncome: boolean;
  onSetLowIncome: (lowIncome: boolean) => void;
  hooks: string[];
  onToggleHook: (hook: string) => void;
  consent: boolean;
  onSetConsent: (consent: boolean) => void;
  onLoadMayaDemo: () => void;
}

export function ContextStep({
  residencyState,
  onSetResidencyState,
  schoolType,
  onSetSchoolType,
  firstGen,
  onSetFirstGen,
  lowIncome,
  onSetLowIncome,
  hooks,
  onToggleHook,
  consent,
  onSetConsent,
  onLoadMayaDemo,
}: ContextStepProps) {
  return (
    <div className="space-y-6">
      {/* Background & School Context */}
      <div>
        <h3 className="text-sm font-semibold text-[var(--color-ink)] mb-3">
          School & Geographic Context
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-mono text-[var(--color-muted)] mb-1.5">
              Residency State
            </label>
            <select
              value={residencyState}
              onChange={(e) => onSetResidencyState(e.target.value)}
              aria-label="Residency State"
              className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-panel-2)] px-3 py-2 text-sm text-[var(--color-ink)] focus:border-[var(--color-advocate)] focus:outline-none"
            >
              {US_STATES.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-mono text-[var(--color-muted)] mb-1.5">
              High School Type
            </label>
            <select
              value={schoolType}
              onChange={(e) => onSetSchoolType(e.target.value)}
              aria-label="High School Type"
              className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-panel-2)] px-3 py-2 text-sm text-[var(--color-ink)] focus:border-[var(--color-advocate)] focus:outline-none"
            >
              {SCHOOL_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Equity & Hooks Switches */}
      <div className="space-y-4 rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)]/50 p-4">
        <h3 className="text-sm font-semibold text-[var(--color-ink)]">
          Applicant Background & Institutional Hooks
        </h3>

        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[var(--color-ink)]">
              First-Generation College Student
            </p>
            <p className="text-xs text-[var(--color-muted)]">
              Neither parent completed a four-year college degree.
            </p>
          </div>
          <Switch
            checked={firstGen}
            onCheckedChange={onSetFirstGen}
            aria-label="First-Generation Student toggle"
          />
        </div>

        <div className="flex items-center justify-between gap-4 pt-2 border-t border-[var(--color-line)]">
          <div>
            <p className="text-sm font-medium text-[var(--color-ink)]">
              Low-Income / Pell-Eligible
            </p>
            <p className="text-xs text-[var(--color-muted)]">
              Eligible for federal Pell Grants or application fee waivers.
            </p>
          </div>
          <Switch
            checked={lowIncome}
            onCheckedChange={onSetLowIncome}
            aria-label="Low-Income toggle"
          />
        </div>

        <div className="pt-2 border-t border-[var(--color-line)] space-y-2">
          <p className="text-xs font-mono text-[var(--color-muted)]">Institutional Hooks:</p>
          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 text-sm text-[var(--color-ink)] cursor-pointer">
              <input
                type="checkbox"
                checked={hooks.includes("legacy")}
                onChange={() => onToggleHook("legacy")}
                className="rounded border-[var(--color-line)] bg-[var(--color-panel)] text-[var(--color-advocate)] focus:ring-0"
              />
              <span>Legacy (parent/grandparent attended)</span>
            </label>

            <label className="flex items-center gap-2 text-sm text-[var(--color-ink)] cursor-pointer">
              <input
                type="checkbox"
                checked={hooks.includes("recruited_athlete")}
                onChange={() => onToggleHook("recruited_athlete")}
                className="rounded border-[var(--color-line)] bg-[var(--color-panel)] text-[var(--color-advocate)] focus:ring-0"
              />
              <span>Recruited Athlete</span>
            </label>
          </div>
        </div>
      </div>

      {/* Race Non-Consideration Notice */}
      <div className="flex items-start gap-3 rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)]/30 p-3.5 text-xs text-[var(--color-muted)]">
        <Info className="h-4 w-4 shrink-0 text-[var(--color-advocate)] mt-0.5" />
        <p className="leading-relaxed">
          Race and ethnicity are not asked. Race-conscious admissions ended in 2023, and our model never uses them.
        </p>
      </div>

      {/* Consent & Demo File Loader */}
      <div className="space-y-4 pt-2 border-t border-[var(--color-line)]">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <label className="flex items-start gap-2.5 text-sm text-[var(--color-ink)] cursor-pointer">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => onSetConsent(e.target.checked)}
              aria-label="Consent to materials processing"
              className="mt-0.5 rounded border-[var(--color-line)] bg-[var(--color-panel-2)] text-[var(--color-advocate)] focus:ring-0"
            />
            <span className="leading-snug">
              <strong className="font-semibold text-white">Required:</strong> These are my own materials. Delete everything within 24 hours.
            </span>
          </label>

          <button
            type="button"
            onClick={onLoadMayaDemo}
            className="inline-flex items-center gap-1.5 self-start sm:self-auto rounded-lg border border-[var(--color-line)] bg-[var(--color-panel-2)] px-3 py-1.5 text-xs font-medium text-[var(--color-advocate)] hover:bg-[var(--color-advocate)]/10 transition-colors"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Load Maya&apos;s demo file</span>
          </button>
        </div>

        <div className="flex items-center gap-2 text-[11px] font-mono text-[var(--color-muted)]">
          <ShieldCheck className="h-3.5 w-3.5 text-[var(--color-admit)]" />
          <span>In-memory evaluation only. No database storage of student documents.</span>
        </div>
      </div>
    </div>
  );
}
