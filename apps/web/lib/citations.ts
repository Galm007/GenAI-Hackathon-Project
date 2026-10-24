import type { Citation } from "./types";
import type { RunView } from "@/store/run-store";

export type Seg =
  | { type: "text"; text: string }
  | { type: "cite"; kind: Citation["kind"]; ref: string; valid: boolean | undefined };

const RE = /\[\[(dossier|cds|twin|web|model|sql):([^\]\s]+)\]\]/g;
const REC_LINE = /\n?RECOMMENDATION:.*$/m;

export function tokenize(content: string, streaming: boolean, citations: Citation[] = []): Seg[] {
  let text = content.replace(REC_LINE, "");                 // the stamp renders the recommendation
  if (streaming) {
    const open = text.lastIndexOf("[[");
    if (open !== -1 && text.indexOf("]]", open) === -1) text = text.slice(0, open);
  }
  const validity = new Map(citations.map((c) => [`${c.kind}:${c.ref}`, c.valid]));
  const segs: Seg[] = [];
  let last = 0;
  for (const m of text.matchAll(RE)) {
    const i = m.index ?? 0;
    if (i > last) segs.push({ type: "text", text: text.slice(last, i) });
    segs.push({
      type: "cite",
      kind: m[1] as Citation["kind"],
      ref: m[2],
      valid: streaming ? undefined : (validity.get(`${m[1]}:${m[2]}`) ?? false),
    });
    last = i + m[0].length;
  }
  if (last < text.length) segs.push({ type: "text", text: text.slice(last) });
  return segs;
}

const C7_LABEL: Record<string, string> = {
  rigor: "Rigor",
  academic_gpa: "GPA",
  test_scores: "Tests",
  essay: "Essay",
  recommendations: "Recs",
  extracurriculars: "ECs",
  talent_ability: "Talent",
  character: "Character",
  applicant_interest: "Interest",
  first_generation: "First-gen",
  alumni_relation: "Legacy",
  interview: "Interview",
};

/** Human label for a chip, resolved against the run so chips read like evidence, not IDs. */
export function chipLabel(kind: Citation["kind"], ref: string, run: RunView): string {
  switch (kind) {
    case "twin": {
      const t = run.twins.find((x) => String(x.index) === ref);
      return t ? `Twin ${ref} ${t.outcome === "accepted" ? "✓" : t.outcome === "waitlisted" ? "◐" : "✕"}` : `Twin ${ref}`;
    }
    case "cds":
      if (ref.startsWith("c7.")) return `C7 · ${C7_LABEL[ref.slice(3)] ?? ref.slice(3)}`;
      if (ref.startsWith("major.")) return `Major ×${run.rubric?.major_multiplier.toFixed(2) ?? "?"}`;
      return `CDS · ${ref.replaceAll("_", " ")}`;
    case "web": {
      const s = run.snippets.find((x) => x.id === ref);
      return s ? `${ref} · ${new URL(s.url).hostname.replace("www.", "")}` : ref;
    }
    case "dossier": {
      const [root, idx] = ref.split(".");
      if (root === "activities" && run.dossier) return run.dossier.activities[Number(idx)]?.name ?? "Activity";
      return root.replaceAll("_", " ");
    }
    case "model":
      return ref === "p_final" ? "Model P(admit)" : `Model · ${ref}`;
    case "sql":
      return `Zetaris ${ref}`;
  }
}
