import type { ProbabilityData, SimulationData } from "./data";

// Fictional values from the existing script; see README for arithmetic reconciliation.
export const sampleProbability: ProbabilityData = {
  "p_final": 0.214,
  "p_low": 0.129,
  "p_high": 0.315,
  "disposition": "WAITLIST",
  "components": [
    {
      "key": "base",
      "label": "School admit rate",
      "delta_logit": 0.0,
      "delta_pp": 44.0,
      "detail": "Fictional sample: CDS"
    },
    {
      "key": "major",
      "label": "Major competitiveness",
      "delta_logit": -1.05,
      "delta_pp": -22.4,
      "detail": "Fictional sample: Grainger CS \u00d70.38"
    },
    {
      "key": "academic",
      "label": "Academic rating",
      "delta_logit": 0.2,
      "delta_pp": 2.3,
      "detail": "Fictional sample: Academic 2-"
    },
    {
      "key": "twins",
      "label": "Applicant-twin evidence",
      "delta_logit": -0.15,
      "delta_pp": -2.5,
      "detail": "Fictional sample: n_eff 31.5"
    }
  ]
};

export const sampleSimulation: SimulationData = {
  "simulated": {
    "p_final": 0.431,
    "p_low": null,
    "p_high": null,
    "disposition": null,
    "components": [
      {
        "key": "base",
        "label": "School admit rate",
        "delta_logit": 0.0,
        "delta_pp": 44.0,
        "detail": "Fictional sample: CDS"
      },
      {
        "key": "major",
        "label": "Major competitiveness",
        "delta_logit": -1.05,
        "delta_pp": -22.4,
        "detail": "Fictional sample: Grainger CS \u00d70.38"
      },
      {
        "key": "academic",
        "label": "Academic rating",
        "delta_logit": 0.2,
        "delta_pp": 2.3,
        "detail": "Fictional sample: Academic 2-"
      },
      {
        "key": "twins",
        "label": "Applicant-twin evidence",
        "delta_logit": -0.15,
        "delta_pp": -2.5,
        "detail": "Fictional sample: n_eff 31.5"
      },
      {
        "key": "major_scenario",
        "label": "Major scenario",
        "delta_logit": 0,
        "delta_pp": 21.7,
        "detail": "Fictional counterfactual from the scripted demo; interval not supplied."
      }
    ]
  },
  "applied": [
    "cf_major_math_stats"
  ],
  "delta_pp": 21.7
};
