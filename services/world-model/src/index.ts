// AdCom's Meterless World Model engine: the committee's shared case file (plan §1.7.3, step B18a).
//
// An append-only, in-memory store per aggregate (one evaluation run). Every write carries provenance, goes
// through one FIFO queue per instance, and is recorded in the audit log; reads fold over current state. It
// implements the surface the upstream conformance runner checks (engines/world-model/conformance/runner.ts):
//
//   WORLD_MODEL_IMPL=/abs/path/services/world-model/src/index.ts npx tsx conformance/runner.ts
//
// Zero runtime dependencies. Written for Node's TypeScript type stripping, so only erasable syntax is used.

import { createHash } from "node:crypto";

export type Source = { kind: string; at: string; ref?: string };
export type ExternalKey = { system: string; id: string };
export type MergeDecision = "auto-merge" | "review" | "new";

export type EntityInput = {
  type: string;
  name?: string;
  externalKey?: ExternalKey;
  attrs?: Record<string, unknown>;
  source?: Source;
};

export type Entity = {
  id: string;
  type: string;
  name?: string;
  attrs: Record<string, unknown>;
  sources: Source[];
};

export type Observation = {
  externalId: string;
  title?: string;
  at: string;
  source: Source;
  entities?: { type: string; name?: string; externalKey?: ExternalKey }[];
  [field: string]: unknown;
};

export type Edge = {
  id: string;
  from: string;
  type: string;
  to: string;
  validFrom: string;
  validTo?: string;
  source: Source;
};

export type RelateInput = {
  from: string;
  type: string;
  to: string;
  validFrom?: string;
  source?: Source;
  supersede?: boolean;               // default true: a newer edge of the same type from `from` closes the open one
};

export type AuditEntry = { seq: number; at: string; op: string; id: string; source: Source };

export type WorldModelOptions = { storage?: "memory"; namespace: string; clock?: () => Date };

// ---------- stable ids ----------
const AUTO_MERGE_AT = 0.85;
const REVIEW_AT = 0.82;

export function normalizeName(name: string): string {
  return name
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")          // strip combining marks: José -> Jose
    .replace(/\s+/gu, " ")           // NBSP and runs of whitespace -> one space
    .trim()
    .toLowerCase();
}

export function entityIdFromName(type: string, name: string): string {
  const digest = createHash("sha256").update(`${type}\u0000${normalizeName(name)}`).digest("hex");
  return `ent_${digest.slice(0, 24)}`;
}

export function entityIdFromKey(type: string, key: ExternalKey): string {
  return `${type}:${key.system}:${key.id}`;
}

/** Merge banding for a name-similarity score: >= 0.85 auto-merges, >= 0.82 queues for review. */
export function decide(similarity: number): MergeDecision {
  if (similarity >= AUTO_MERGE_AT) return "auto-merge";
  if (similarity >= REVIEW_AT) return "review";
  return "new";
}

/** JSON with sorted object keys, so equal state always serializes to equal text. */
export function canonicalJson(value: unknown): string {
  const sort = (v: unknown): unknown => {
    if (Array.isArray(v)) return v.map(sort);
    if (v && typeof v === "object") {
      return Object.fromEntries(Object.keys(v).sort().map((k) => [k, sort((v as Record<string, unknown>)[k])]));
    }
    return v;
  };
  return JSON.stringify(sort(value));
}

const sha = (text: string) => createHash("sha256").update(text).digest("hex");

function requireSource(source: Source | undefined, what: string): Source {
  if (!source || typeof source.kind !== "string" || typeof source.at !== "string") {
    throw new Error(`${what} rejected: every write needs provenance (source.kind and source.at)`);
  }
  return source;
}

function entityId(input: { type: string; name?: string; externalKey?: ExternalKey }): string {
  if (input.externalKey) return entityIdFromKey(input.type, input.externalKey);
  if (input.name) return entityIdFromName(input.type, input.name);
  throw new Error("an entity needs a name or an externalKey");
}

// ---------- the engine ----------
export class WorldModel {
  readonly namespace: string;
  private clock: () => Date;
  private entities = new Map<string, Entity>();
  private observations = new Map<string, { hash: string; observation: Observation }>();
  private edges = new Map<string, Edge>();
  private log: AuditEntry[] = [];
  private queue: Promise<unknown> = Promise.resolve();

  constructor(options: WorldModelOptions) {
    if ((options.storage ?? "memory") !== "memory") throw new Error("only storage: \"memory\" is supported");
    this.namespace = options.namespace;
    this.clock = options.clock ?? (() => new Date());
  }

  /** One running job per aggregate: writes run in arrival order, even when callers don't await each other. */
  private enqueue<T>(job: () => T): Promise<T> {
    const run = this.queue.then(job);
    this.queue = run.catch(() => undefined);
    return run;
  }

  private record(op: string, id: string, source: Source): void {
    this.log.push({ seq: this.log.length + 1, at: this.clock().toISOString(), op, id, source });
  }

  private upsertNow(input: EntityInput, source: Source): { id: string; changed: boolean } {
    const id = entityId(input);
    const existing = this.entities.get(id);
    const attrs = { ...(existing?.attrs ?? {}), ...(input.attrs ?? {}) };
    const next: Entity = { id, type: input.type, name: input.name ?? existing?.name, attrs,
                           sources: existing?.sources ?? [] };
    const changed = !existing || canonicalJson({ ...existing, sources: [] }) !== canonicalJson({ ...next, sources: [] });
    if (!changed) return { id, changed };
    next.sources = [...next.sources, source];
    this.entities.set(id, next);
    this.record(existing ? "entity.update" : "entity.create", id, source);
    return { id, changed };
  }

  upsertEntity(input: EntityInput): Promise<{ id: string; changed: boolean }> {
    return this.enqueue(() => this.upsertNow(input, requireSource(input.source, "upsertEntity")));
  }

  /** Append observations. Re-sending an identical observation is a no-op; an edited one replaces the old. */
  ingest(observations: Observation[]): Promise<{ changed: boolean; ids: string[] }> {
    return this.enqueue(() => {
      let changed = false;
      const ids: string[] = [];
      for (const observation of observations) {
        const source = requireSource(observation.source, `observation ${observation.externalId}`);
        const hash = sha(canonicalJson(observation));
        ids.push(observation.externalId);
        if (this.observations.get(observation.externalId)?.hash === hash) continue;
        this.observations.set(observation.externalId, { hash, observation });
        this.record("observation.append", observation.externalId, source);
        for (const e of observation.entities ?? []) this.upsertNow(e, source);
        changed = true;
      }
      return { changed, ids };
    });
  }

  relate(input: RelateInput): Promise<Edge> {
    return this.enqueue(() => {
      const source = requireSource(input.source, "relate");
      const validFrom = input.validFrom ?? source.at;
      const id = `rel_${sha(canonicalJson([input.from, input.type, input.to, validFrom])).slice(0, 24)}`;
      const existing = this.edges.get(id);
      if (existing) return existing;
      if (input.supersede ?? true) {
        for (const edge of this.edges.values()) {
          if (edge.from === input.from && edge.type === input.type && !edge.validTo && edge.validFrom < validFrom) {
            edge.validTo = validFrom;
            this.record("edge.close", edge.id, source);
          }
        }
      }
      const edge: Edge = { id, from: input.from, type: input.type, to: input.to, validFrom, source };
      this.edges.set(id, edge);
      this.record("edge.open", id, source);
      return edge;
    });
  }

  entity(id: string): Entity | undefined {
    return this.entities.get(id);
  }

  observationsSince(seq = 0): Observation[] {
    const ids = new Set(this.log.filter((a) => a.seq > seq && a.op === "observation.append").map((a) => a.id));
    return [...ids].map((id) => this.observations.get(id)!.observation);
  }

  view(name: "graph") {
    if (name !== "graph") throw new Error(`unknown view: ${name}`);
    return {
      /** Entities linked from `id` by `via` edges: open edges now, or the edges valid at `at`. */
      neighborsOf: (id: string, opts: { via?: string; at?: string } = {}): Entity[] => {
        const live = [...this.edges.values()].filter((e) =>
          e.from === id && (!opts.via || e.type === opts.via) &&
          (opts.at ? e.validFrom <= opts.at && (!e.validTo || opts.at < e.validTo) : !e.validTo));
        return live.map((e) => this.entities.get(e.to) ?? { id: e.to, type: "unknown", attrs: {}, sources: [] });
      },
    };
  }

  /** The state that idempotency is judged on: entities, observations and edges, never the audit log or clock. */
  stateShapeCanonical(): string {
    const byId = <T extends { id: string }>(items: Iterable<T>) => [...items].sort((a, b) => a.id.localeCompare(b.id));
    return canonicalJson({
      entities: byId(this.entities.values()).map(({ sources, ...e }) => ({ ...e, sources: sources.length })),
      observations: [...this.observations.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([id, o]) => [id, o.hash]),
      edges: byId(this.edges.values()),
    });
  }

  audit(): AuditEntry[] {
    return [...this.log];
  }
}
