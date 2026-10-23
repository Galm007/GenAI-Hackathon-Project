# CLAUDE.md

All team rules live in `AGENTS.md`, which is shared with the Codex and Gemini teammates. It's imported here so there is one source of truth:

@AGENTS.md

## Claude Code specifics

- `/next-step` (in `.claude/commands/next-step.md`) runs the step protocol from `AGENTS.md` §3. `/next-step B08` targets a specific step.
- Work queue: `docs/ROADMAP.md`. Spec: `MASTER_PLAN.md`. Read only the sections a step lists (`grep -n "^### <n>" MASTER_PLAN.md`) and never load the whole 8,400-line file.
- Before writing or changing any Anthropic SDK code, load the `claude-api` skill and keep the plan's API shapes (`AGENTS.md` §4). The plan already uses the current ones.
- Stop after the step's single commit and give the end-of-step report. Don't push unless your human asks.
