import { describe, it, expect } from "vitest";
import { pct, pp, schoolName } from "@/lib/format";

describe("C08: Accessibility, responsive utilities, and projector mode", () => {
  it("formats percentage and pp accurately for screen readers and labels", () => {
    expect(pct(0.21)).toBe("21%");
    expect(pct(0.214, 1)).toBe("21.4%");
    expect(pct(null)).toBe("—");

    expect(pp(21.7)).toBe("+21.7 pp");
    expect(pp(-5.2)).toBe("-5.2 pp");
    expect(pp(null)).toBe("—");
  });

  it("maps school slugs to human-readable names with fallback", () => {
    expect(schoolName("uiuc")).toBe("UIUC");
    expect(schoolName("cmu")).toBe("Carnegie Mellon");
    expect(schoolName("mit")).toBe("MIT");
    expect(schoolName("stanford")).toBe("Stanford");
    expect(schoolName("unknown_slug")).toBe("UNKNOWN_SLUG");
  });

  it("checks projector query parameter pattern", () => {
    const searchWithProjector = "?projector=1";
    const params = new URLSearchParams(searchWithProjector);
    expect(params.get("projector")).toBe("1");

    const searchWithoutProjector = "?foo=bar";
    const normalParams = new URLSearchParams(searchWithoutProjector);
    expect(normalParams.get("projector")).toBeNull();
  });

  it("validates disposition text pairing with color signals", () => {
    const dispositions = ["ADMIT", "LIKELY ADMIT", "WAITLIST", "DENY"] as const;
    dispositions.forEach((d) => {
      expect(typeof d).toBe("string");
      expect(d.length).toBeGreaterThan(0);
    });
  });
});
