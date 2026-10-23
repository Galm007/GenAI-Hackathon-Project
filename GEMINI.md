# GEMINI.md

All team rules live in `AGENTS.md`, which is shared with the Claude Code and Codex teammates. It's imported here so there is one source of truth:

@./AGENTS.md

If the import above didn't load, read `AGENTS.md` in full before doing anything else.

## Gemini CLI specifics

- `/next-step` (in `.gemini/commands/next-step.toml`) runs the step protocol from `AGENTS.md` §3. `/next-step B08` targets a specific step.
- Work queue: `docs/ROADMAP.md`. Spec: `MASTER_PLAN.md`. Read only the sections a step lists (`grep -n "^### <n>" MASTER_PLAN.md`) and never load the whole 8,400-line file.
- The plan's Anthropic (Claude) SDK code is current and intentional: model `claude-opus-5-5`, `messages.parse(output_format=…)`, `output_config={"effort": …}`, `fallbacks="default"`. Don't rewrite it to older API shapes or other model names (`AGENTS.md` §4).
- Stop after the step's single commit and give the end-of-step report. Don't push unless your human asks.
