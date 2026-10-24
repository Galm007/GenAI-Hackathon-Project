import assert from "node:assert/strict";
import test from "node:test";
import { buildWaterfallRows, breakdownDifference, validProbability } from "./math.ts";

const contribution = (key, delta_pp) => ({ key, label: key, delta_pp, delta_logit: 0, detail: "fixture" });
test("a decrease floats between the previous and next totals", () => {
  const rows = buildWaterfallRows([contribution("base", 44), contribution("major", -22.4)]);
  assert.ok(Math.abs(rows[1].offset - 21.6) < 1e-9);
  assert.equal(rows[1].start, 44);
  assert.equal(rows[1].value, 22.4);
});
test("small contributions remain in the total and negative totals retain their offset", () => {
  const rows = buildWaterfallRows([contribution("base", 1), contribution("test", 0.05), contribution("major", -2)]);
  assert.equal(rows.length, 3);
  assert.ok(Math.abs(rows[2].end + 0.95) < 1e-9);
  assert.equal(rows[2].offset, rows[2].end);
});
test("inconsistent supplied totals are detectable rather than silently corrected", () => {
  const data = { p_final: 0.214, components: [contribution("base", 44), contribution("major", -22.4)] };
  assert.ok(Math.abs(breakdownDifference(data) - 0.2) < 1e-9);
  assert.ok(Math.abs(breakdownDifference({ ...data, p_final: 0.5 })) > 0.5);
});
test("empty data stays empty and invalid probabilities are rejected", () => {
  assert.deepEqual(buildWaterfallRows([]), []);
  for (const x of [NaN, Infinity, -0.1, 1.1]) assert.equal(validProbability(x), false);
  for (const x of [0, 0.214, 1]) assert.equal(validProbability(x), true);
});
