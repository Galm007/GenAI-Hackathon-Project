import type { RadarData, TwinData, BaselineData, ComparisonData } from "./data";

// Fictional UI samples. Radar normalization follows plan section 4.7; no live statistics are claimed.

export const sampleRadar: RadarData = {
  "n_admitted": 2,
  "axes": [
    {
      "key": "gpa",
      "label": "GPA",
      "you": 88.0,
      "admitted_median": 86.0,
      "you_raw": 3.94,
      "admitted_raw": 3.9299999999999997,
      "assumed": false
    },
    {
      "key": "test",
      "label": "Testing",
      "you": 73.3,
      "admitted_median": 71.7,
      "you_raw": 1520,
      "admitted_raw": 1515.0,
      "assumed": false
    },
    {
      "key": "rigor",
      "label": "Rigor",
      "you": 78.6,
      "admitted_median": 82.1,
      "you_raw": 11,
      "admitted_raw": 11.5,
      "assumed": false
    },
    {
      "key": "activities",
      "label": "Activities",
      "you": 57.8,
      "admitted_median": 49.4,
      "you_raw": 2.9,
      "admitted_raw": 3.275,
      "assumed": false
    },
    {
      "key": "spike",
      "label": "Spike",
      "you": 25.0,
      "admitted_median": 25.0,
      "you_raw": 1,
      "admitted_raw": 1,
      "assumed": false
    },
    {
      "key": "personal",
      "label": "Personal",
      "you": 60.0,
      "admitted_median": 60.0,
      "you_raw": 3.0,
      "admitted_raw": 3.0,
      "assumed": true
    }
  ]
};

export const sampleTwins: TwinData[] = [
  {
    "index": 1,
    "id": "00000000-0000-4000-8000-000000000001",
    "source_url": "",
    "cycle_year": 2025,
    "outcome": "rejected",
    "headline": "3.90 UW \u00b7 1500 SAT \u00b7 computer science (fixture)",
    "gpa_uw": 3.9,
    "sat_score": 1500,
    "act_score": null,
    "spike_summary": "Competition-focused profile (fictional sample).",
    "semantic_similarity": 0.9,
    "stat_proximity": 0.88,
    "hybrid_score": 0.89,
    "top_activities": [
      {
        "description": "Weekly programming practice with a school team.",
        "role": "Programming captain",
        "tier": 2
      }
    ]
  },
  {
    "index": 2,
    "id": "00000000-0000-4000-8000-000000000002",
    "source_url": "",
    "cycle_year": 2025,
    "outcome": "accepted",
    "headline": "3.92 UW \u00b7 1510 SAT \u00b7 computer science (fixture)",
    "gpa_uw": 3.92,
    "sat_score": 1510,
    "act_score": null,
    "spike_summary": "Programming plus a shipped tool (fictional sample).",
    "semantic_similarity": 0.87,
    "stat_proximity": 0.86,
    "hybrid_score": 0.86,
    "top_activities": [
      {
        "description": "Built a scheduling prototype for fictional school clubs.",
        "role": "Project lead",
        "tier": 2
      }
    ]
  },
  {
    "index": 3,
    "id": "00000000-0000-4000-8000-000000000003",
    "source_url": "",
    "cycle_year": 2025,
    "outcome": "accepted",
    "headline": "3.94 UW \u00b7 1520 SAT \u00b7 computer science (fixture)",
    "gpa_uw": 3.94,
    "sat_score": 1520,
    "act_score": null,
    "spike_summary": "Robotics and mentoring (fictional sample).",
    "semantic_similarity": 0.8400000000000001,
    "stat_proximity": 0.84,
    "hybrid_score": 0.8300000000000001,
    "top_activities": [
      {
        "description": "Wrote robot-control routines and mentored new club members.",
        "role": "Controls lead",
        "tier": 2
      }
    ]
  },
  {
    "index": 4,
    "id": "00000000-0000-4000-8000-000000000004",
    "source_url": "",
    "cycle_year": 2025,
    "outcome": "waitlisted",
    "headline": "3.96 UW \u00b7 1530 SAT \u00b7 computer science (fixture)",
    "gpa_uw": 3.96,
    "sat_score": 1530,
    "act_score": null,
    "spike_summary": "Practical experience (fictional sample).",
    "semantic_similarity": 0.81,
    "stat_proximity": 0.8200000000000001,
    "hybrid_score": 0.8,
    "top_activities": [
      {
        "description": "Helped a community center document routine device setup.",
        "role": "IT support volunteer",
        "tier": 3
      }
    ]
  },
  {
    "index": 5,
    "id": "00000000-0000-4000-8000-000000000005",
    "source_url": "",
    "cycle_year": 2025,
    "outcome": "rejected",
    "headline": "3.98 UW \u00b7 1540 SAT \u00b7 computer science (fixture)",
    "gpa_uw": 3.98,
    "sat_score": 1540,
    "act_score": null,
    "spike_summary": "Academic competitions (fictional sample).",
    "semantic_similarity": 0.78,
    "stat_proximity": 0.8,
    "hybrid_score": 0.77,
    "top_activities": [
      {
        "description": "Led peer practice and a small school coding project.",
        "role": "Math club organizer",
        "tier": 2
      }
    ]
  }
];

export const sampleBaseline: BaselineData = {
  "n_neighbors": 40,
  "n_accepted": 14,
  "n_waitlisted": 4,
  "n_rejected": 22,
  "n_effective": 31.5,
  "odds_inflation": 2.4,
  "widened_to_peers": false
};

export const sampleComparisons: ComparisonData[] = [
  {
    "twin_index": 1,
    "key_similarity": "Same GPA band and CS spike.",
    "key_difference": "Twin had no research.",
    "plausible_deciding_factor": "Unknown. An outcome alone does not establish why a committee decided."
  },
  {
    "twin_index": 2,
    "key_similarity": "Programming-focused activities and a similar test-score band.",
    "key_difference": "This fictional profile emphasizes a delivered tool.",
    "plausible_deciding_factor": "Project impact is a possible discussion point, not a proven cause of admission."
  }
];
