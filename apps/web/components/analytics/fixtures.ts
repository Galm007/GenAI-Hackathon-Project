import probability from "../../../../data/fixtures/ProbabilityBreakdown.json";
import simulation from "../../../../data/fixtures/WhatIfResponse.json";
import type { ProbabilityData, SimulationData } from "./data";

// Fictional inputs; generated with the actual Python scoring code, schema-validated in API tests.
export const sampleProbability = probability as ProbabilityData;
export const sampleSimulation = simulation as SimulationData;
