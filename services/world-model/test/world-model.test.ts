import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { after, before, test } from "node:test";

import { WorldModel } from "../src/index.ts";
import { createWorldModelServer } from "../src/server.ts";

const src = (at: string) => ({ kind: "node", at });
const obs = (node: string, i: number) => ({
  externalId: `${node}:${i}`, title: `${node} fact ${i}`, at: "2026-10-26T00:00:00.000Z",
  source: src("2026-10-26T00:00:00.000Z"), entities: [{ type: "school", externalKey: { system: "adcom", id: "uiuc" } }],
});

test("concurrent writers lose nothing: the FIFO queue serializes un-awaited writes", async () => {
  const world = new WorldModel({ storage: "memory", namespace: "run:test" });
  const nodeA = Array.from({ length: 50 }, (_, i) => world.ingest([obs("institutional", i)]));
  const nodeB = Array.from({ length: 50 }, (_, i) => world.ingest([obs("twins", i)]));
  await Promise.all([...nodeA, ...nodeB]);
  assert.equal(world.observationsSince().length, 100);
  const seqs = world.audit().map((a) => a.seq);
  assert.deepEqual(seqs, seqs.map((_, i) => i + 1));
});

test("a failed write does not block the queue", async () => {
  const world = new WorldModel({ storage: "memory", namespace: "run:test" });
  await assert.rejects(world.upsertEntity({ type: "school", name: "No Source" }), /provenance/);
  const { id } = await world.upsertEntity({ type: "school", name: "UIUC", source: src("2026-10-26T00:00:00.000Z") });
  assert.ok(world.entity(id));
});

test("relate with supersede: false keeps both edges open", async () => {
  const world = new WorldModel({ storage: "memory", namespace: "run:test" });
  await world.relate({ from: "run:1", type: "cites", to: "Z1", validFrom: "2026-10-26T00:00:00.000Z",
                       source: src("2026-10-26T00:00:00.000Z"), supersede: false });
  await world.relate({ from: "run:1", type: "cites", to: "Z2", validFrom: "2026-10-26T00:01:00.000Z",
                       source: src("2026-10-26T00:01:00.000Z"), supersede: false });
  assert.deepEqual(world.view("graph").neighborsOf("run:1", { via: "cites" }).map((e) => e.id).sort(), ["Z1", "Z2"]);
});

// ---------- HTTP wrapper ----------
let base = "";
const server = createWorldModelServer();
before(async () => {
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});
after(() => server.close());

const post = (path: string, body: unknown) =>
  fetch(`${base}${path}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });

test("http: ingest, state, observations, audit, delete", async () => {
  assert.deepEqual(await (await fetch(`${base}/health`)).json(), { ok: true, worlds: 0 });
  const first = await (await post("/v1/run%3Aabc/ingest", { observations: [obs("institutional", 1)] })).json();
  assert.deepEqual(first, { changed: true, ids: ["institutional:1"] });
  const again = await (await post("/v1/run%3Aabc/ingest", { observations: [obs("institutional", 1)] })).json();
  assert.equal(again.changed, false);

  const state = await (await fetch(`${base}/v1/run%3Aabc/state`)).json();
  assert.equal(state.observations.length, 1);
  assert.deepEqual(state.entities.map((e: { id: string }) => e.id), ["school:adcom:uiuc"]);
  const since = await (await fetch(`${base}/v1/run%3Aabc/observations?since=0`)).json();
  assert.equal(since[0].title, "institutional fact 1");
  assert.ok((await (await fetch(`${base}/v1/run%3Aabc/audit`)).json()).length >= 2);

  assert.deepEqual(await (await fetch(`${base}/v1/run%3Aabc`, { method: "DELETE" })).json(), { deleted: true });
});

test("http: context returns one kind in append order and honours the budget", async () => {
  const section = (name: string, payload: unknown) => ({ externalId: `section:${name}`, kind: "docket.section",
    section: name, payload, at: "2026-10-26T00:00:00.000Z", source: src("2026-10-26T00:00:00.000Z") });
  await post("/v1/run%3Actx/ingest", { observations: [section("applicant", { a: 1 }), obs("debate", 1),
                                                      section("twins", [1, 2, 3])] });
  const all = await (await fetch(`${base}/v1/run%3Actx/context?kind=docket.section`)).json();
  assert.deepEqual(all.observations.map((o: { section: string }) => o.section), ["applicant", "twins"]);
  assert.equal(all.truncated, false);
  const cut = await (await fetch(`${base}/v1/run%3Actx/context?kind=docket.section&budget=200`)).json();
  assert.equal(cut.truncated, true);
  assert.equal(cut.observations.length, 1);
});

test("http: relate and neighbors", async () => {
  const s = src("2026-10-26T00:00:00.000Z");
  await post("/v1/run%3Ag/entities", { type: "school", externalKey: { system: "adcom", id: "uiuc" }, source: s });
  await post("/v1/run%3Ag/relate", { from: "applicant:adcom:maya", type: "targets", to: "school:adcom:uiuc", source: s });
  const res = await fetch(`${base}/v1/run%3Ag/neighbors?id=applicant%3Aadcom%3Amaya&via=targets`);
  assert.deepEqual((await res.json()).map((e: { id: string }) => e.id), ["school:adcom:uiuc"]);
});

test("http: bad input is a 4xx with a message, never a crash", async () => {
  const noSource = await post("/v1/run%3Ax/entities", { type: "school", name: "UIUC" });
  assert.equal(noSource.status, 400);
  assert.match((await noSource.json()).error, /provenance/);
  assert.equal((await post("/v1/run%3Ax/ingest", { observations: "nope" })).status, 400);
  const badJson = await fetch(`${base}/v1/run%3Ax/ingest`, { method: "POST", body: "{" });
  assert.equal(badJson.status, 400);
  assert.equal((await fetch(`${base}/v1/bad%20ns/state`)).status, 400);
  assert.equal((await fetch(`${base}/nope`)).status, 404);
});
