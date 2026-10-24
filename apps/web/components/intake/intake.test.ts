import { describe, it, expect } from "vitest";
import { countWords } from "@/lib/format";
import { getAvailableRounds, SEED_SCHOOLS } from "@/lib/schools";
import { ApiError } from "@/lib/api";

describe("IntakeWizard helper functions and models", () => {
  it("counts words accurately", () => {
    expect(countWords("")).toBe(0);
    expect(countWords("   ")).toBe(0);
    expect(countWords(null)).toBe(0);
    expect(countWords(undefined)).toBe(0);
    expect(countWords("Hello world")).toBe(2);
    expect(countWords("  The   quick brown fox\njumps over   \t the lazy dog  ")).toBe(9);
  });

  it("determines available rounds from school early plans", () => {
    const uiuc = SEED_SCHOOLS.find((s) => s.slug === "uiuc");
    expect(uiuc).toBeDefined();
    const uiucRounds = getAvailableRounds(uiuc);
    expect(uiucRounds).toContain("EA");
    expect(uiucRounds).toContain("RD");

    const harvard = SEED_SCHOOLS.find((s) => s.slug === "harvard");
    expect(harvard).toBeDefined();
    const harvardRounds = getAvailableRounds(harvard);
    expect(harvardRounds).toContain("REA");
    expect(harvardRounds).toContain("RD");

    const cmu = SEED_SCHOOLS.find((s) => s.slug === "cmu");
    expect(cmu).toBeDefined();
    const cmuRounds = getAvailableRounds(cmu);
    expect(cmuRounds).toContain("ED");
    expect(cmuRounds).toContain("ED2");
    expect(cmuRounds).toContain("RD");

    const berkeley = SEED_SCHOOLS.find((s) => s.slug === "uc_berkeley");
    expect(berkeley).toBeDefined();
    const berkeleyRounds = getAvailableRounds(berkeley);
    expect(berkeleyRounds).toEqual(["RD"]);
  });

  it("contains demo schools in SEED_SCHOOLS", () => {
    const slugs = SEED_SCHOOLS.map((s) => s.slug);
    expect(slugs).toContain("uiuc");
    expect(slugs).toContain("mit");
    expect(slugs).toContain("harvard");
    expect(slugs).toContain("stanford");
    expect(slugs).toContain("cmu");
  });

  it("identifies ApiError statuses properly (413, 415, 429)", () => {
    const err413 = new ApiError(413, "transcript.pdf exceeds 10 MB");
    expect(err413.status).toBe(413);

    const err415 = new ApiError(415, "resume.doc is not a PDF");
    expect(err415.status).toBe(415);

    const err429 = new ApiError(429, "Rate limit reached for session");
    expect(err429.status).toBe(429);
  });
});
