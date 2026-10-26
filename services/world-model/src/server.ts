// Minimal HTTP wrapper around the World Model engine (plan §1.7.3). One in-memory WorldModel per namespace (an
// evaluation run, `run:<id>`); the Python graph talks to it through app/world_model.py (step B18b), which reads
// each run's docket sections back through `/context`.
//
//   node src/server.ts                 # WORLD_MODEL_HOST (127.0.0.1), WORLD_MODEL_PORT (8790)

import { createServer, type IncomingMessage, type ServerResponse } from "node:http";

import { WorldModel } from "./index.ts";

const MAX_BODY = 2 * 1024 * 1024;
const NAMESPACE = /^[\w:.-]{1,128}$/;

class HttpError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function readJson(req: IncomingMessage): Promise<any> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > MAX_BODY) throw new HttpError(413, "request body too large");
    chunks.push(chunk);
  }
  try {
    return chunks.length ? JSON.parse(Buffer.concat(chunks).toString("utf8")) : {};
  } catch {
    throw new HttpError(400, "body is not valid JSON");
  }
}

function send(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
}

export function createWorldModelServer() {
  const worlds = new Map<string, WorldModel>();
  const world = (ns: string) => {
    if (!NAMESPACE.test(ns)) throw new HttpError(400, "namespace must be 1-128 of [A-Za-z0-9_:.-]");
    let w = worlds.get(ns);
    if (!w) worlds.set(ns, (w = new WorldModel({ storage: "memory", namespace: ns })));
    return w;
  };

  return createServer(async (req, res) => {
    try {
      const url = new URL(req.url ?? "/", "http://localhost");
      if (req.method === "GET" && url.pathname === "/health") return send(res, 200, { ok: true, worlds: worlds.size });

      const [, v1, rawNs, action] = url.pathname.split("/");
      if (v1 !== "v1" || !rawNs) throw new HttpError(404, "not found");
      const ns = decodeURIComponent(rawNs);

      if (req.method === "DELETE" && !action) return send(res, 200, { deleted: worlds.delete(ns) });
      const w = world(ns);
      const fail = (err: unknown): never => { throw new HttpError(400, (err as Error).message); };

      if (req.method === "POST" && action === "entities") {
        return send(res, 200, await w.upsertEntity(await readJson(req)).catch(fail));
      }
      if (req.method === "POST" && action === "ingest") {
        const body = await readJson(req);
        if (!Array.isArray(body.observations)) throw new HttpError(400, "body.observations must be an array");
        return send(res, 200, await w.ingest(body.observations).catch(fail));
      }
      if (req.method === "POST" && action === "relate") return send(res, 200, await w.relate(await readJson(req)).catch(fail));
      if (req.method === "GET" && action === "state") return send(res, 200, JSON.parse(w.stateShapeCanonical()));
      if (req.method === "GET" && action === "audit") return send(res, 200, w.audit());
      if (req.method === "GET" && action === "observations") {
        return send(res, 200, w.observationsSince(Number(url.searchParams.get("since") ?? 0)));
      }
      if (req.method === "GET" && action === "context") {
        const budget = url.searchParams.get("budget");
        return send(res, 200, w.context({ kind: url.searchParams.get("kind") ?? undefined,
                                          budget: budget === null ? undefined : Number(budget) }));
      }
      if (req.method === "GET" && action === "neighbors") {
        const id = url.searchParams.get("id");
        if (!id) throw new HttpError(400, "id is required");
        return send(res, 200, w.view("graph").neighborsOf(id, {
          via: url.searchParams.get("via") ?? undefined, at: url.searchParams.get("at") ?? undefined }));
      }
      throw new HttpError(404, "not found");
    } catch (err) {
      const status = err instanceof HttpError ? err.status : 500;
      send(res, status, { error: (err as Error).message });
    }
  });
}

if (import.meta.main) {
  const host = process.env.WORLD_MODEL_HOST ?? "127.0.0.1";
  const port = Number(process.env.WORLD_MODEL_PORT ?? 8790);
  createWorldModelServer().listen(port, host, () => console.log(`world-model listening on http://${host}:${port}`));
}
