import assert from "node:assert/strict";
import { test } from "vitest";
import { buildWaterfallRows, breakdownDifference, validProbability, comparableAxes, safeSourceUrl, formatRaw } from "./math";

const contribution = (key: string, delta_pp: number) => ({ key, label: key, delta_pp, delta_logit: 0, detail: "fixture" });
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
  const data = { p_final: 0.214, p_low: null, p_high: null, disposition: null, components: [contribution("base", 44), contribution("major", -22.4)] };
  assert.ok(Math.abs(breakdownDifference(data) - 0.2) < 1e-9);
  assert.ok(Math.abs(breakdownDifference({ ...data, p_final: 0.5 })) > 0.5);
});
test("empty data stays empty and invalid probabilities are rejected", () => {
  assert.deepEqual(buildWaterfallRows([]), []);
  for (const x of [NaN, Infinity, -0.1, 1.1]) assert.equal(validProbability(x), false);
  for (const x of [0, 0.214, 1]) assert.equal(validProbability(x), true);
});
test("unknown radar values are omitted while genuine zero remains comparable", () => {
  const axes = [{ key: "zero", you: 0, admitted_median: 0 }, { key: "missing", you: null, admitted_median: 50 },
    { key: "invalid", you: NaN, admitted_median: 70 }, { key: "range", you: 101, admitted_median: 50 }];
  const complete = axes.map((a) => ({ ...a, label: a.key, you_raw: a.you, admitted_raw: a.admitted_median, assumed: false }));
  assert.deepEqual(comparableAxes({ n_admitted: 2, axes: complete }).map((a) => a.key), ["zero"]);
});
test("source links accept HTTPS and reject executable, relative, and credential-bearing URLs", () => {
  assert.equal(safeSourceUrl("https://www.reddit.com/r/collegeresults/"), "https://www.reddit.com/r/collegeresults/");
  for (const url of ["", "/post", "javascript:alert(1)", "data:text/html,bad", "http://example.com", "https://user:pass@example.com"])
    assert.equal(safeSourceUrl(url), null);
});
test("raw comparison values do not expose floating-point artifacts or invent missing scores", () => {
  assert.equal(formatRaw(3.9299999999999997), "3.93");
  assert.equal(formatRaw(null), "Unknown");
  assert.equal(formatRaw(0), "0");
});
