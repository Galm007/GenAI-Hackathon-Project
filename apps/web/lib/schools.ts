export interface SchoolOption {
  slug: string;
  name: string;
  early_plans?: {
    ed?: boolean;
    ed2?: boolean;
    ea?: boolean;
    rea?: boolean;
  };
}

export const SEED_SCHOOLS: SchoolOption[] = [
  {
    slug: "uiuc",
    name: "University of Illinois Urbana-Champaign (UIUC)",
    early_plans: { ea: true },
  },
  {
    slug: "mit",
    name: "Massachusetts Institute of Technology (MIT)",
    early_plans: { ea: true },
  },
  {
    slug: "harvard",
    name: "Harvard University",
    early_plans: { rea: true },
  },
  {
    slug: "stanford",
    name: "Stanford University",
    early_plans: { rea: true },
  },
  {
    slug: "cmu",
    name: "Carnegie Mellon University (CMU)",
    early_plans: { ed: true, ed2: true },
  },
  {
    slug: "uc_berkeley",
    name: "University of California, Berkeley",
    early_plans: {},
  },
  {
    slug: "ucla",
    name: "University of California, Los Angeles",
    early_plans: {},
  },
  {
    slug: "umich",
    name: "University of Michigan",
    early_plans: { ea: true },
  },
  {
    slug: "georgia_tech",
    name: "Georgia Institute of Technology",
    early_plans: { ea: true },
  },
  {
    slug: "ut_austin",
    name: "University of Texas at Austin",
    early_plans: { ea: true },
  },
  {
    slug: "uw_seattle",
    name: "University of Washington",
    early_plans: {},
  },
  {
    slug: "yale",
    name: "Yale University",
    early_plans: { rea: true },
  },
  {
    slug: "princeton",
    name: "Princeton University",
    early_plans: { rea: true },
  },
];

export function getAvailableRounds(school?: SchoolOption): string[] {
  if (!school || !school.early_plans) return ["RD", "EA", "ED", "REA"];
  const rounds: string[] = [];
  if (school.early_plans.ed) rounds.push("ED");
  if (school.early_plans.ed2) rounds.push("ED2");
  if (school.early_plans.ea) rounds.push("EA");
  if (school.early_plans.rea) rounds.push("REA");
  rounds.push("RD");
  return rounds;
}
