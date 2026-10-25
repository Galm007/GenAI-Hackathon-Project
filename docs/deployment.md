# AdCom deployment handoff

Prepared by gridiii via Codex, 2026-10-24; refreshed 2026-10-25 after the Track B
handoff. D08 is **not deployed**. B13's live graph is now implemented. A Vercel
project, public API origin and working shared-database configuration are still
unavailable on gridiii's machine. Local replay success is not a production
integration result.

## Verified local path

1. Start Zetaris normally and verify it; preserve its data volumes.
2. From `services/api`, run `FAKE_LLM=1 ZETARIS_ENABLED=false uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`.
3. From `apps/web`, run `pnpm install --frozen-lockfile` and `pnpm dev --hostname 127.0.0.1 --port 3001`.
4. Open `http://127.0.0.1:3001/room/demo/maya-uiuc`. The same-origin `/api` rewrite
   reaches port 8000, so Zetaris can retain port 3000 without a browser CORS conflict.
5. Test a pivot, change a slider, reset, and restart the replay with Shift+R.

## Release prerequisites

- Track B finishes B14 and B16, and the API reports actual DB/Zetaris health.
  B13's graph and HTTP stream are implemented; this is no longer missing code.
- Track A supplies the shared project connection and the demo-school/twin data.
  A12's semantic views and agent permissions were verified on Track A's stack;
  they must also exist on the chosen API/Zetaris host. Keep private values there.
- The demo owner configures S03 and B17/B18 and captures D10 evidence.
- Choose the team's Vercel account/project and an API host co-located with Zetaris.
  The existing Zetaris bundle and its ports stay private. Do not deploy that bundle
  to Vercel or publish its `.env`.

## gridiii's local environment

Each developer keeps their own ignored repo-root `.env`; that does not require a
separate Supabase project. gridiii chose the shared AdCom project. Its URL and
backend service-role key are not committed, and the installed Supabase CLI is not
signed in on this Mac. Obtain those values privately from Jmar or the shared
project's settings, then put them in the root `.env`, never the frontend file.

The local root `.env` is prepared with `FAKE_LLM=true`, `ZETARIS_ENABLED=false`,
`DEMO_MODE=true` and CORS for the web app on port 3001. The ignored web
`apps/web/.env.local` sets `ADCOM_API_URL=http://127.0.0.1:8000`. Both files have
mode 600. Existing credentials were preserved; no placeholder credential was
described as a working connection.

The authored replay uses no Supabase or provider calls. A new `/api/evaluate`
run still needs Supabase school/twin data even with fake LLM calls. Do not use
the unrelated local database project to stand in for AdCom. Turn Zetaris on only
after this host's semantic views and least-privilege agent login are configured.
Live model calls also need a real provider credential and human approval for
provider usage; B17 adds the planned Meterless provider switch.

| Setting | Source / status on gridiii's Mac |
|---|---|
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | Jmar/shared AdCom project; still placeholders |
| `ZETARIS_AGENT_EMAIL`, `ZETARIS_AGENT_PASSWORD` | Least-privilege user on the API host's Zetaris; local password still a placeholder |
| `SUPABASE_POOLER_HOST`, `ZETARIS_PG_USER`, `ZETARIS_PG_PASSWORD` | Shared session-pooler and reader login for configuring this host's datasource; still placeholders |
| `ANTHROPIC_API_KEY` | Optional live-provider alternative; placeholder, not used by the replay |
| `METERLESS_RUNTIME_TOKEN` | Nightshift Console after S03; placeholder, B17 still pending |

## Vercel web project

Import this repository and set **Root Directory** to `apps/web`, framework to
Next.js, and use the checked-in build/install settings. Configure
`ADCOM_API_URL=https://<reachable-api-host>` for each intended environment before
building. Its value is an API origin, not a secret token. Leave
`NEXT_PUBLIC_API_URL` unset to use the same-origin proxy; if choosing a direct API
origin instead, also configure the API's exact allowed web origins.

Do not point a hosted build at localhost: it would refer to Vercel's machine.
Do not put service-role, NVIDIA, Meterless or Anthropic keys in frontend variables.
API streams should retain `Cache-Control: no-cache` and `X-Accel-Buffering: no`.
No caching is enabled for the API rewrite.

Sources checked: [Vercel monorepos](https://vercel.com/docs/monorepos),
[external rewrites](https://vercel.com/docs/routing/rewrites), and
[Next.js rewrites](https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites).

## Production acceptance (still open)

- Open the hosted site on a phone using a separate network.
- Complete a fictional-persona live run; verify the stream, real Zetaris evidence,
  what-if, citations and source drawer.
- Disconnect the live provider and verify the recorded replay fallback.
- Save the actual URL, build revision and results in `docs/integration-report.md`.

Do not check D08 or X01 complete until that acceptance has run against the hosted
stack. The configuration in this commit is a deployable web handoff, not a claim
that the unfinished API is production-ready.
