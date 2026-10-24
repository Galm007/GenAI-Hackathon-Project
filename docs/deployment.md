# AdCom deployment handoff

Prepared by gridiii via Codex, 2026-10-24. D08 is **not deployed**. No Vercel project,
public API origin, configured team database or complete live graph was available.
Local replay success is not a production integration result.

## Verified local path

1. Start Zetaris normally and verify it; preserve its data volumes.
2. From `services/api`, run `FAKE_LLM=1 ZETARIS_ENABLED=false uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`.
3. From `apps/web`, run `pnpm install --frozen-lockfile` and `pnpm dev --hostname 127.0.0.1 --port 3001`.
4. Open `http://127.0.0.1:3001/room/demo/maya-uiuc`. The same-origin `/api` rewrite
   reaches port 8000, so Zetaris can retain port 3000 without a browser CORS conflict.
5. Test a pivot, change a slider, reset, and restart the replay with Shift+R.

## Release prerequisites

- Track B finishes B13/B14 and B16, and the API reports actual DB/Zetaris health.
- Track A supplies verified project data, semantic views and the least-privilege
  account. Keep all private values on the API host.
- The demo owner configures S03 and B17/B18 and captures D10 evidence.
- Choose the team's Vercel account/project and an API host co-located with Zetaris.
  The existing Zetaris bundle and its ports stay private. Do not deploy that bundle
  to Vercel or publish its `.env`.

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
