# DECISIONS: deviations from MASTER_PLAN.md

Append one entry whenever a commit deviates from the plan (a renamed field, a swapped library, a confirmed or corrected Zetaris detail, a cut feature). Keep entries short, never delete old ones, and if a decision is reversed, add a new entry that supersedes it.

```
## D-000 — <title>
- Step: <ID> · Date: YYYY-MM-DD · By: <human> via <tool>
- Plan said: …
- We did: …
- Why: …
- Impact on other tracks: … (contract change? update both Python + TS sides)
```

---

## D-001 — Decisions already baked into the plan (for reference)
- Step: — · Date: 2026-10-23 · By: planning session
- pgvector (Supabase) does twin KNN; Zetaris Lightning owns institutional facts, cross-source stats, agent SQL access and audit (plan §2.10.1).
- One target school per graph run; extra schools are child runs that skip Node 1 (plan §3.2).
- All reasoning nodes use `claude-opus-5-5` with server-side refusal fallbacks enabled (plan §0.2). Changing models is a human decision.
- No LLM ever outputs a user-visible probability or delta (plan §0.1).
