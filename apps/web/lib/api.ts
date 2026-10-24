import type { WhatIfRequest, WhatIfResponse } from "./types";

export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export function sessionId(): string {
  try {
    let id = localStorage.getItem("adcom.sid");
    if (!id) { id = crypto.randomUUID(); localStorage.setItem("adcom.sid", id); }
    return id;
  } catch {
    return crypto.randomUUID();                            // private mode: per-tab session
  }
}

export interface IntakeFormData {
  intended_major: string; target_schools: string[]; early_round: Record<string, string>;
  activities_text?: string; resume_text?: string; essay_text?: string; recommendation_text?: string;
  hooks: string[]; context: Record<string, unknown>; application_deadline?: string;
}

export async function createEvaluation(form: IntakeFormData, files: { transcript?: File; resume?: File }) {
  const fd = new FormData();
  fd.append("intake", JSON.stringify({ ...form, session_id: sessionId(), consent: true }));
  if (files.transcript) fd.append("transcript", files.transcript);
  if (files.resume) fd.append("resume", files.resume);
  return json<{ run_id: string; stream_url: string; school_slug: string }>(
    await fetch(`${API}/api/evaluate`, { method: "POST", body: fd }),
  );
}

export const evaluateSchool = async (runId: string, slug: string) =>
  json<{ run_id: string; stream_url: string }>(
    await fetch(`${API}/api/evaluate/${runId}/schools/${slug}`, { method: "POST" }),
  );

export const whatIf = async (req: WhatIfRequest, signal?: AbortSignal) =>
  json<WhatIfResponse>(await fetch(`${API}/api/what-if`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(req), signal,
  }));

export const searchSchools = async (q: string) =>
  json<{ slug: string; name: string; score: number }[]>(await fetch(`${API}/api/schools?q=${encodeURIComponent(q)}`));
