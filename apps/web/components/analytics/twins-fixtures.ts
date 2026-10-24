import radar from "../../../../data/fixtures/RadarData.json";
import twins from "../../../../data/fixtures/TwinCard.json";
import baseline from "../../../../data/fixtures/EmpiricalBaseline.json";
import analysis from "../../../../data/fixtures/TwinAnalysis.json";
import type { RadarData, TwinData, BaselineData, ComparisonData } from "./data";

export const sampleRadar = radar as RadarData;
export const sampleTwins = twins as TwinData[];
export const sampleBaseline = baseline as BaselineData;
export const sampleComparisons = analysis.comparisons as ComparisonData[];
