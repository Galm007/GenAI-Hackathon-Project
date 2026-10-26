# Meterless Nightshift setup

Steps only; no secrets in this file. Sources: the Open Agent Hackathon 2026 Participant Setup Guide (21 Oct 2026) and meterless.ai. Design and decisions: `MASTER_PLAN.md` §1.7 and `docs/DECISIONS.md` D-011.

**Eligibility:** the hackathon requires Zetaris **and Meterless to be running on your machine**. Nightshift has no Linux edition, so whoever demos runs it on Windows, Mac or a DGX Spark, or on Linux through Wine (see the Linux section in step 1; ask the organizers whether Wine counts as "running on your machine" before relying on it for judging).

## 1. Install Nightshift

1. Go to meterless.ai and scroll to the install cards.
2. Pick your edition: **Windows** (10/11, CUDA for NVIDIA GPUs), **Mac M1+** (older Macs, M1 to M4) or **Mac M5+** (Tahoe, M5 and later), or **DGX Spark**. There is no Linux x86 edition. The free **Web** edition is only for trying it out: it does not expose the local Runtime our app needs.
3. Enter your email at the access gate and complete the verification email, then download, install and launch. Leave Nightshift running while you test the app.

### Linux: run the Windows edition under Wine (tested 2026-10-26, Arch Linux x86_64)

There is no Linux edition, but the Windows edition runs under Wine. It is a Tauri app, so it needs Microsoft's WebView2 runtime inside the Wine prefix. What worked (Wine 11.19 Staging, Nightshift 1.2.7):

1. Make an isolated prefix: `export WINEPREFIX=$HOME/.local/share/wine-nightshift WINEARCH=win64; wineboot -u`.
2. Install the Visual C++ runtimes: `winetricks -q vcrun2022`.
3. Download Microsoft's **WebView2 standalone x64 installer** (`https://go.microsoft.com/fwlink/?linkid=2124701`, about 215 MB; the 2 MB link is only a bootstrapper) and run `wine MicrosoftEdgeWebView2RuntimeInstallerX64.exe /silent /install`. Without it the Nightshift installer shows an error and closes.
4. Download `Nightshift-Setup-Windows.exe` from meterless.ai (email gate, about 660 MB) and run it with `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS="--disable-gpu --no-sandbox"`.
5. Start the app with `wine 'C:\users\<you>\AppData\Local\Nightshift\meterless-runtime.exe'` (same environment variable). Do not pass `--help`: it starts the runtime without a window.

What to expect: the runtime listens on `127.0.0.1:8088` (the URL `.env` already uses), because Wine shares the host network. The window may look empty in the Live field (a demo canvas), and the mouse cursor can be invisible over the window under Wayland; clicks still work. The app also serves a phone page on `0.0.0.0:8089`, protected by a pairing code. The Runtime API key is in the app (Setup, Quick Connect); the runtime's own error message says so.

## 2. Connect NVIDIA (Nemotron)

1. Open build.nvidia.com/models, sign in, and pick a Nemotron model that offers an API endpoint. Generate an NVIDIA API key.
2. In Nightshift: **Setup > Providers > Cloud Providers > NVIDIA**. Paste the key and save. Confirm NVIDIA shows as connected.
3. **The NVIDIA key goes only in Nightshift's Providers tab.** Not in `.env`, not in the Console, and not in your coding tool's model settings.

## 3. Configure lanes

**NIGHT > LANES**, then **Add** (or load a fleet from **Fleets**). Start with one lane you can test:

| Lane | Example model (pick the exact name from your catalog) | Job |
|---|---|---|
| 1 Fast worker | `nvidia/nemotron-3.5-lightning-30b-a3b` | quick turns, tool use |
| 2 Deep worker | `nvidia/nemotron-3.5-super-vl-120b-a12b` | the committee debate, harder reasoning |
| Optional judge | any available Nemotron | check outputs |

These are the guide's examples, not guaranteed entitlements. At least one active lane must use Nemotron. Run a short test inside Nightshift and confirm which model answered.

## 4. Put the Console values in `.env`

In Nightshift, open **Console** (top right) and copy the **Nightshift URL** and **API key** (Runtime access token):

```
LLM_PROVIDER=meterless
METERLESS_BASE_URL=http://127.0.0.1:8088/v1      # the Console's URL; use the reachable URL if Nightshift is on another machine
METERLESS_RUNTIME_TOKEN=<the Console's API key>   # never the NVIDIA key, never the placeholder rt-local
METERLESS_MODEL=meterless/auto                    # a routing mode, not a model id
```

`meterless/auto` may route to a non-NVIDIA model when several lanes qualify. To show Nemotron in the demo, pin a Nemotron-backed lane (or use the explicit `meterless/<...>` route that `/v1/models` lists for it).

## 5. Verify

```bash
cd services/api
uv run python -m scripts.smoke_meterless
```

Expected: three `PASS` lines (settings, model discovery, a real chat answer that names the model that served it). The token is never printed. Then check Nightshift's run details to confirm the request was handled by a Nemotron lane.

| Symptom | Likely cause | Fix |
|---|---|---|
| `METERLESS_RUNTIME_TOKEN is missing` | `.env` not in the repo root, or placeholder left in | copy the real key from the Console |
| `unauthorized (401/403)` | token from a different Nightshift, or the NVIDIA key pasted by mistake | copy the Console's API key again |
| connection refused | Nightshift not running, or it is on another machine | start it; use its reachable URL |
| authorized but no models | no lanes configured | NIGHT > LANES > Add |
| 404 / model not found | model id not in the lane list | copy the id from `GET /v1/models` |
| credit or rate-limit error | NVIDIA free-tier limit | wait, or switch lanes |

## 6. World Model engine (Build rule)

The engine integration is a separate step (roadmap B18): a TypeScript sidecar checked with the upstream conformance suite from a clone of github.com/Meterless/Meterless. See plan §1.7.3.
