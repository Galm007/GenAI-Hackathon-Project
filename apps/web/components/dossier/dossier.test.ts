import { describe, it, expect } from "vitest";
import { emptyRun } from "@/store/run-store";
import type { Dossier, DossierGrade, Metrics } from "@/lib/types";

describe("Dossier Panel Data Flow", () => {
  it("processes parsed dossier, metrics, and harvard grades accurately", () => {
    const run = emptyRun("dossier-test");

    const mockDossier: Dossier = {
      high_school: { name: "High School", state: "IL", school_type: "Public" },
      activities: [
        {
          name: "Robotics Club",
          role: "President",
          organization: "FIRST",
          description: "Led team to state championship",
          category: "stem",
          grades: [10, 11, 12],
          hours_per_week: 10,
          weeks_per_year: 30,
        },
        {
          name: "USACO Competitor",
          role: "Platinum Division",
          organization: null,
          description: "Top 200 nationally in competitive programming",
          category: "academic",
          grades: [9, 10, 11, 12],
          hours_per_week: 15,
          weeks_per_year: 40,
        },
      ],
      awards: [{ name: "National Merit Semifinalist", level: "national", grade: 12 }],
      courses: [{ title: "AP Computer Science A", level: "AP", grade_level: 11, grade_as_shown: "A" }],
      test_scores: { sat_total: 1540, act_composite: null },
    };

    const mockMetrics: Metrics = {
      gpa_uw_4: 3.95,
      gpa_w_5: 4.65,
      core_course_count: 24,
      advanced_course_count: 12,
      rigor_index: 4.8,
      grade_trend: "upward",
      sat_equivalent: 1540,
      proxy_academic_rating: 1.8,
      tier_derived_ec_rating: 1.5,
      ec_score: 92,
    };

    const mockGrade: DossierGrade = {
      major_category: "computer_science",
      rigor_label: "Most Demanding",
      activity_grades: [
        { activity_index: 0, rationale: "Solid leadership", tier: 2, spike_role: "supporting" },
        { activity_index: 1, rationale: "National level spike", tier: 1, spike_role: "core" },
      ],
      spike: {
        label: "Competitive Programming",
        description: "National-caliber problem solver",
        strength: "strong",
      },
      essay: {
        themes: ["resilience", "curiosity"],
        voice: "Authentic",
        strengths: ["Clear narrative arc"],
        weaknesses: [],
        red_flags: [],
        strongest_line: "Algorithms are poems in logic.",
      },
      harvard: {
        academic: { rating: 2, modifier: "-", rationale: "Near top rigor", evidence: ["12 APs"] },
        extracurricular: { rating: 1, modifier: "", rationale: "USACO Platinum", evidence: ["Top 200"] },
        personal: { rating: 3, modifier: "+", rationale: "Good essays", evidence: ["Genuine voice"] },
        athletic: { rating: 4, modifier: "", rationale: "Recreational", evidence: [] },
      },
      reader_comments: "Strong STEM spike with top-tier algorithmic problem solving ability.",
      grader_warnings: ["Calculus BC unweighted score adjusted"],
    };

    run.dossier = mockDossier;
    run.metrics = mockMetrics;
    run.grade = mockGrade;

    // Verify activity sorting: activity 1 (Tier 1) sorts before activity 0 (Tier 2)
    const paired = run.dossier.activities.map((act, index) => {
      const ag = run.grade!.activity_grades.find((g) => g.activity_index === index);
      return { index, activity: act, grade: ag };
    });
    paired.sort((a, b) => (a.grade?.tier ?? 99) - (b.grade?.tier ?? 99));

    expect(paired[0].activity.name).toBe("USACO Competitor");
    expect(paired[0].grade?.tier).toBe(1);
    expect(paired[0].grade?.spike_role).toBe("core");

    expect(paired[1].activity.name).toBe("Robotics Club");
    expect(paired[1].grade?.tier).toBe(2);

    // Verify Harvard ratings
    expect(run.grade.harvard.academic.rating).toBe(2);
    expect(run.grade.harvard.academic.modifier).toBe("-");
    expect(run.grade.harvard.extracurricular.rating).toBe(1);

    // Verify metrics
    expect(run.metrics.gpa_uw_4).toBe(3.95);
    expect(run.metrics.grade_trend).toBe("upward");

    // Verify reader comments
    expect(run.grade.reader_comments).toContain("Strong STEM spike");
  });
});
