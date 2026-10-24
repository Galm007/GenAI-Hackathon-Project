import { describe, it, expect } from "vitest";
import { tokenize, chipLabel } from "./citations";
import { emptyRun } from "../store/run-store";
import type { Citation, TwinCard, WebSnippet } from "./types";

describe("lib/citations.ts", () => {
  describe("tokenize", () => {
    it("hides unterminated [[... tail while streaming without flashing raw brackets", () => {
      const streamedIncomplete = "Grainger weighs rigor [[cds:c7.ri";
      const segs = tokenize(streamedIncomplete, true);
      expect(segs).toHaveLength(1);
      expect(segs[0]).toEqual({ type: "text", text: "Grainger weighs rigor " });
    });

    it("parses completed citations when stream token delivers ]]", () => {
      const streamedComplete = "Grainger weighs rigor [[cds:c7.rigor]] and GPA [[cds:c7.academic_gpa]].";
      const segs = tokenize(streamedComplete, true);
      expect(segs).toHaveLength(5);
      expect(segs[0]).toEqual({ type: "text", text: "Grainger weighs rigor " });
      expect(segs[1]).toEqual({ type: "cite", kind: "cds", ref: "c7.rigor", valid: undefined });
      expect(segs[2]).toEqual({ type: "text", text: " and GPA " });
      expect(segs[3]).toEqual({ type: "cite", kind: "cds", ref: "c7.academic_gpa", valid: undefined });
      expect(segs[4]).toEqual({ type: "text", text: "." });
    });

    it("attaches validity to citations when streaming is false", () => {
      const content = "Look at [[twin:2]] and [[web:s1]]";
      const citations: Citation[] = [
        { kind: "twin", ref: "2", valid: true, span: [8, 17] },
        { kind: "web", ref: "s1", valid: false, span: [22, 30] },
      ];
      const segs = tokenize(content, false, citations);
      expect(segs[1]).toEqual({ type: "cite", kind: "twin", ref: "2", valid: true });
      expect(segs[3]).toEqual({ type: "cite", kind: "web", ref: "s1", valid: false });
    });

    it("strips RECOMMENDATION: line because the stamp renders it", () => {
      const content = "Strong applicant.\nRECOMMENDATION: ADMIT";
      const segs = tokenize(content, false);
      expect(segs).toHaveLength(1);
      expect(segs[0]).toEqual({ type: "text", text: "Strong applicant." });
    });
  });

  describe("chipLabel", () => {
    const run = emptyRun("run-1");
    run.twins = [
      {
        index: 2,
        id: "twin-2",
        outcome: "accepted",
        headline: "CS admit",
        spike_summary: "USACO",
      } as TwinCard,
    ];
    run.snippets = [
      {
        id: "s1",
        title: "CS stats",
        url: "https://www.cs.illinois.edu/admissions",
        content: "...",
      } as WebSnippet,
    ];

    it("formats twin chip with outcome symbol", () => {
      expect(chipLabel("twin", "2", run)).toBe("Twin 2 ✓");
      expect(chipLabel("twin", "99", run)).toBe("Twin 99");
    });

    it("formats C7 and CDS chips", () => {
      expect(chipLabel("cds", "c7.rigor", run)).toBe("C7 · Rigor");
      expect(chipLabel("cds", "c7.academic_gpa", run)).toBe("C7 · GPA");
    });

    it("formats web snippet chips with clean hostname", () => {
      expect(chipLabel("web", "s1", run)).toBe("s1 · cs.illinois.edu");
    });

    it("formats Zetaris SQL query chips", () => {
      expect(chipLabel("sql", "Z1", run)).toBe("Zetaris Z1");
    });
  });
});
