export function pct(n: number | null | undefined, decimals = 0): string {
  if (n == null || isNaN(n)) return "—";
  return `${(n * 100).toFixed(decimals)}%`;
}

export function pp(n: number | null | undefined, decimals = 1): string {
  if (n == null || isNaN(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(decimals)} pp`;
}

const SCHOOL_NAMES: Record<string, string> = {
  uiuc: "UIUC",
  cmu: "Carnegie Mellon",
  umich: "Michigan",
  cal: "UC Berkeley",
  gatech: "Georgia Tech",
  mit: "MIT",
  stanford: "Stanford",
  harvard: "Harvard",
  cornell: "Cornell",
  columbia: "Columbia",
  upenn: "Penn",
  princeton: "Princeton",
  yale: "Yale",
  brown: "Brown",
  dartmouth: "Dartmouth",
  northwestern: "Northwestern",
  uchicago: "UChicago",
  duke: "Duke",
  jhu: "Johns Hopkins",
  vanderbilt: "Vanderbilt",
  rice: "Rice",
  notredame: "Notre Dame",
  ucla: "UCLA",
  usc: "USC",
  nyu: "NYU",
  utaustin: "UT Austin",
  uw: "UW Seattle",
  purdue: "Purdue",
  wisconsin: "Wisconsin",
  umd: "Maryland",
};

export function schoolName(slug: string | null | undefined): string {
  if (!slug) return "Unknown School";
  return SCHOOL_NAMES[slug.toLowerCase()] ?? slug.toUpperCase();
}

export function countWords(str: string | null | undefined): number {
  if (!str) return 0;
  const words = str.trim().split(/\s+/).filter(Boolean);
  return words.length;
}
