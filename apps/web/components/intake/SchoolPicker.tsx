"use client";

import * as React from "react";
import { Search, X, Calendar, GraduationCap, Check } from "lucide-react";
import { searchSchools } from "@/lib/api";
import {
  type SchoolOption,
  SEED_SCHOOLS,
  getAvailableRounds,
} from "@/lib/schools";
import { cn } from "@/lib/utils";

export { type SchoolOption, SEED_SCHOOLS, getAvailableRounds };

export interface SchoolPickerProps {
  selectedSchools: string[];
  earlyRounds: Record<string, string>;
  onSelectSchool: (slug: string) => void;
  onRemoveSchool: (slug: string) => void;
  onSetRound: (slug: string, round: string) => void;
  applicationDeadline?: string;
  onSetDeadline: (date: string) => void;
}

export function SchoolPicker({
  selectedSchools,
  earlyRounds,
  onSelectSchool,
  onRemoveSchool,
  onSetRound,
  applicationDeadline,
  onSetDeadline,
}: SchoolPickerProps) {
  const [query, setQuery] = React.useState("");
  const [isOpen, setIsOpen] = React.useState(false);
  const [results, setResults] = React.useState<SchoolOption[]>([]);
  const [isSearching, setIsSearching] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement>(null);

  // Debounced search
  React.useEffect(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) {
      setResults(SEED_SCHOOLS);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const apiResults = await searchSchools(trimmed);
        if (apiResults && apiResults.length > 0) {
          // Map API results
          const mapped: SchoolOption[] = apiResults.map((r) => {
            const seed = SEED_SCHOOLS.find((s) => s.slug === r.slug);
            return {
              slug: r.slug,
              name: r.name,
              early_plans: seed?.early_plans ?? { ea: true },
            };
          });
          setResults(mapped);
        } else {
          // Local fallback filter
          const filtered = SEED_SCHOOLS.filter(
            (s) =>
              s.name.toLowerCase().includes(trimmed) ||
              s.slug.toLowerCase().includes(trimmed)
          );
          setResults(filtered);
        }
      } catch {
        // Fallback on search error
        const filtered = SEED_SCHOOLS.filter(
          (s) =>
            s.name.toLowerCase().includes(trimmed) ||
            s.slug.toLowerCase().includes(trimmed)
        );
        setResults(filtered);
      } finally {
        setIsSearching(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query]);

  // Click outside to close dropdown
  React.useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const findSchool = (slug: string): SchoolOption => {
    const found = SEED_SCHOOLS.find((s) => s.slug === slug);
    return found || { slug, name: slug.toUpperCase(), early_plans: {} };
  };

  const handleAdd = (slug: string) => {
    if (selectedSchools.length >= 8) return;
    if (selectedSchools.includes(slug)) return;
    onSelectSchool(slug);
    const school = findSchool(slug);
    const rounds = getAvailableRounds(school);
    const defaultRound = rounds.includes("EA") ? "EA" : rounds[0];
    onSetRound(slug, defaultRound);
    setQuery("");
    setIsOpen(false);
  };

  return (
    <div className="space-y-4" ref={containerRef}>
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-[var(--color-ink)]">
          Target Schools ({selectedSchools.length}/8)
        </label>
        <span className="text-xs text-[var(--color-muted)] font-mono">
          Up to 8 target institutions
        </span>
      </div>

      {/* Search Input */}
      <div className="relative">
        <div className="flex items-center rounded-lg border border-[var(--color-line)] bg-[var(--color-panel-2)] px-3 py-2 text-sm focus-within:border-[var(--color-advocate)]">
          <Search className="mr-2 h-4 w-4 shrink-0 text-[var(--color-muted)]" />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            placeholder={
              selectedSchools.length >= 8
                ? "Maximum 8 schools selected"
                : "Search universities by name or abbreviation (e.g. UIUC, MIT, CMU)..."
            }
            disabled={selectedSchools.length >= 8}
            className="w-full bg-transparent text-[var(--color-ink)] placeholder:text-[var(--color-muted)] focus:outline-none disabled:cursor-not-allowed"
          />
          {isSearching && (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--color-advocate)] border-t-transparent" />
          )}
        </div>

        {/* Dropdown Options */}
        {isOpen && selectedSchools.length < 8 && (
          <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-60 overflow-y-auto rounded-lg border border-[var(--color-line)] bg-[var(--color-panel)] py-1 shadow-2xl">
            {results.length === 0 ? (
              <div className="px-4 py-3 text-xs text-[var(--color-muted)] text-center">
                No institutions found. You can try &quot;UIUC&quot;, &quot;MIT&quot;, &quot;Stanford&quot;, etc.
              </div>
            ) : (
              results.map((school) => {
                const isSelected = selectedSchools.includes(school.slug);
                return (
                  <button
                    key={school.slug}
                    type="button"
                    onClick={() => handleAdd(school.slug)}
                    disabled={isSelected}
                    className={cn(
                      "flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors",
                      isSelected
                        ? "opacity-40 cursor-not-allowed bg-[var(--color-panel-2)]"
                        : "hover:bg-[var(--color-panel-2)] text-[var(--color-ink)]"
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <GraduationCap className="h-4 w-4 text-[var(--color-muted)]" />
                      <span>{school.name}</span>
                    </div>
                    {isSelected && (
                      <span className="flex items-center gap-1 text-xs text-[var(--color-admit)] font-mono">
                        <Check className="h-3.5 w-3.5" /> Added
                      </span>
                    )}
                  </button>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* Selected Schools List */}
      {selectedSchools.length > 0 && (
        <div className="space-y-2 pt-1">
          {selectedSchools.map((slug, idx) => {
            const school = findSchool(slug);
            const rounds = getAvailableRounds(school);
            const currentRound = earlyRounds[slug] || (rounds.includes("EA") ? "EA" : "RD");

            return (
              <div
                key={slug}
                className={cn(
                  "flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3 transition-colors",
                  idx === 0
                    ? "border-[var(--color-advocate)]/60 bg-[var(--color-advocate)]/5"
                    : "border-[var(--color-line)] bg-[var(--color-panel-2)]"
                )}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-mono text-xs font-semibold text-[var(--color-muted)]">
                    #{idx + 1}
                  </span>
                  <div className="truncate">
                    <p className="text-sm font-medium text-[var(--color-ink)] truncate">
                      {school.name}
                    </p>
                    {idx === 0 && (
                      <span className="text-[11px] font-mono text-[var(--color-advocate)]">
                        Primary target (starts Node 1 run)
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 ml-auto">
                  {/* Round Select */}
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-[var(--color-muted)] font-mono">Round:</span>
                    <select
                      value={currentRound}
                      onChange={(e) => onSetRound(slug, e.target.value)}
                      aria-label={`Select round for ${school.name}`}
                      className="rounded border border-[var(--color-line)] bg-[var(--color-panel)] px-2 py-1 text-xs font-mono font-medium text-[var(--color-ink)] focus:border-[var(--color-advocate)] focus:outline-none"
                    >
                      {rounds.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Remove Button */}
                  <button
                    type="button"
                    onClick={() => onRemoveSchool(slug)}
                    aria-label={`Remove ${school.name}`}
                    className="rounded p-1 text-[var(--color-muted)] hover:bg-[var(--color-room)] hover:text-[var(--color-deny)] transition-colors"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Deadline Picker */}
      <div className="pt-2">
        <label className="flex items-center gap-2 text-xs font-mono text-[var(--color-muted)] mb-1">
          <Calendar className="h-3.5 w-3.5" />
          Application Deadline (optional, informs feasibility)
        </label>
        <input
          type="date"
          value={applicationDeadline || ""}
          onChange={(e) => onSetDeadline(e.target.value)}
          aria-label="Application deadline"
          className="rounded-lg border border-[var(--color-line)] bg-[var(--color-panel-2)] px-3 py-1.5 text-xs font-mono text-[var(--color-ink)] focus:border-[var(--color-advocate)] focus:outline-none"
        />
      </div>
    </div>
  );
}
