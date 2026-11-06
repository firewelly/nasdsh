# NasDSH — DeepSeek Harness Workbench for NAS

[简体中文](README.md) | [English](README_EN.md)

> NasDSH is a **one-click packaged distribution of
> [DeepSeek Harness (dsh)](https://github.com/deepseek-ai/deepseek-harness)**
> for two NAS operating systems: **UGreen UGOS Pro** and **fnOS** (both x86_64).
> Goal: turn "install, run, and keep using dsh on a NAS" from a pile of manual
> sysadmin work into a single click in the app center.

Once installed, open the workbench in a browser or the remote app and use it in
two ways:

- **WEB (default)**: one shared `dsh web` instance; the browser shows the full
  dsh GUI, and projects are added/switched through dsh's own **Workspaces**.
  Closing the tab keeps the process alive — reopen and continue.
- **CLI**: one tmux session per project running
  [`dsh-TUI`](https://github.com/ccch1mneyyy/dsh-TUI); sessions survive closing
  the window and reconnect seamlessly; `exit` ends them.

Ships with dsh `0.2.1-rc.5` and dsh-TUI `0.18.0`, preconfigured for the
BigModel GLM Coding Plan (`/coding/` subscription endpoint) or the DeepSeek
official route.

## Why NasDSH exists (pain points)

dsh is a CLI tool written for developers — it assumes a machine with a proper
Node.js runtime, SSH access, and the ability to debug dependencies yourself.
NAS usage is nothing like that. This is what NasDSH solves:

| # | Pain point of installing dsh on a NAS directly | What NasDSH does |
|---|---|---|
| 1 | **Dependency hell** — stock Node on fnOS/UGOS is 18 or an old 25.x, while dsh needs a newer runtime (and uses the experimental `node:sqlite`); swapping system Node touches the NAS OS itself | Everything is packaged in a container: node:24 + dsh + dsh-TUI + all dependencies, installed once. The NAS system is never touched |
| 2 | **Can't even install** — NAS boxes often have no proxy; hitting npm registry directly times out, and every machine needs mirror tinkering | The fnOS fpk **ships an offline Docker image** — installation needs zero network. The UGOS upk image is built locally on the NAS |
| 3 | **No "app" form** — after installing you only get a CLI: no desktop icon, no declared port, no autostart, invisible to the app center | upk/fpk app packages: click the desktop icon, fixed port 12704, starts with the system, upgrades/uninstall managed by the app center |
| 4 | **Access friction** — dsh web listens on loopback with a launch token by default; after SSH you still have to hand-roll a reverse proxy to use it from a phone/browser | sessiond launches dsh web automatically and reverse-proxies it under a `/w/` prefix — open the browser and the full UI is there; phone apps / UGREENlink remote access work too |
| 5 | **Sessions die** — disconnect SSH and dsh is gone; switching terminals means losing the conversation | WEB runs as a resident process and CLI runs under tmux: **close the window, come back later, everything is still there** |
| 6 | **Multi-project chaos** — `cd`-ing between project dirs in one terminal; the web UI only knows the directory it was started in | Per-project tabs in the UI / dsh Workspaces for switching; a path allowlist only exposes project volumes |
| 7 | **No security story** — a web service on the NAS is exposed to the whole LAN by default | Optional access PIN (challenge-response + HttpOnly cookie); dsh's own token/cookie and browser-trust fence are preserved as-is |
| 8 | **Credential hygiene** — API keys pasted into shell history / profile files, re-entered on every machine | Filled in the install wizard → runtime credential store (0600). **Packages contain no keys whatsoever**, verified automatically at build time |
| 9 | **Painful upgrades** — global npm upgrades pollute the system and fragment versions | `nasdsh-update` upgrades inside the container, or upgrade the whole package by swapping the image; the data volume survives |
| 10 | **Missing CJK locale** — NAS systems often lack zh_CN locales; vim/less turn into mojibake | Image ships zh_CN.UTF-8 plus vim/nano/tmux config; browser IME input passes straight through |

In one sentence: **NasDSH turns "operating an AI coding agent on a NAS" into
"installing an app from an app center."**

> Regular Linux hosts don't need this project: `npm i -g @deepseek-ai/dsh
> @deepseek-harness-tui/dsh-tui` gives you dsh directly. NasDSH's value is the
> NAS-app-shaped workbench around it.

## Architecture

```
┌─ Browser / UGREEN App (LAN hits 12704; remote goes through UGREENlink app domain) ─┐
│  index.html   tab bar + "new workbench" dialog (Web / CLI, Web default)             │
│  term.html    xterm.js (CLI sessions, WS → tmux)                                    │
│  iframe       /w/ (shared dsh web; projects switch via Workspaces inside the UI)    │
└──────────────────────────────┬──────────────────────────────────────────────────────┘
                               │ HTTP 8080 (upk declares port 12704 → container 8080)
┌──────────────────────────────▼──────────────────────────────────────────────────────┐
│ sessiond.py (single process, Python 3 stdlib only, ThreadingHTTPServer)             │
│  • tab management / session API / directory browser                                 │
│  • CLI: WS → PTY → `tmux new -A -s <name>` (running dsh-TUI)                        │
│  • Web: launches one shared `dsh web --host 127.0.0.1 --port <random>`              │
│  • /w/ prefix reverse proxy (HTTP + WebSocket), Host passed through untouched       │
└──────────────────────────────┬──────────────────────────────────────────────────────┘
                               │ docker-compose (is_docker_app upk)
┌──────────────────────────────▼──────────────────────────────────────────────────────┐
│ node:24-bookworm-slim                                                               │
│  dsh 0.2.1-rc.5 + dsh-TUI 0.18.0 + tmux + git/vim/ripgrep…                          │
│  Persistent data: ${DATA_PATH}:/data (profiles/credentials/sessions/logs)           │
│  Project dirs: mounted at identical paths (install parameter PATH)                  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Why a prefix reverse proxy instead of exposing dsh web's port directly

The dsh web frontend uses `<base href="./">` with relative asset paths, and the
launch-token exchange does `303 → ./`. Stripping the `/w/` prefix and
forwarding to the local dsh keeps the browser origin identical
(`host:12704`), so:

- dsh's signed cookies (bound to host + port) work unchanged;
- `Host` / `Origin` pass through untouched, satisfying dsh's browser-trust fence;
- no HTML/JS rewriting, and no extra ports opened on the NAS;
- WebSockets (`/w/api/remote.mux`) are relayed verbatim by sessiond.

dsh's launch token only ever appears in the iframe's first-hop URL; dsh
immediately exchanges it for an HttpOnly cookie and redirects to a clean path.

## Repository layout

```
nas-dsh/
├── core/                     # platform-agnostic core (Docker build context)
│   ├── Dockerfile            #   node:24 + dsh + dsh-TUI + tmux
│   ├── sessiond.py           #   backend: UI/API/WS→tmux/dsh web proxy
│   ├── www/                  #   frontend (xterm.js vendored)
│   ├── dsh-home-template/    #   DSH_HOME template (profiles + provider patch)
│   ├── entrypoint.sh         #   data dirs/PIN/profile seeding, privilege drop
│   ├── bin/nasdsh-update     #   in-container dsh / dsh-TUI upgrade
│   └── tmux.conf / profile.d/
├── src/                      # UGOS Pro packaging project (ugcli → upk)
│   ├── project.yaml          #   spec 2.1, is_docker_app, port 12704
│   ├── rootfs_common/        #   docker-compose.yaml + icon.png
│   ├── rootfs_amd64/images/  #   build output (nasdsh-*.tar)
│   └── build.sh              #   run on the NAS
├── fnos/                     # fnOS packaging project (fpk, offline image inside)
│   ├── build_fpk.py
│   └── fpk_root/             #   manifest / cmd / wizard / config
├── tools/
│   ├── upload.sh             #   Mac → NAS source transfer
│   ├── verify_no_keys.py     #   package privacy check (scans for real secrets)
│   ├── test_web.py           #   web proxy + token + WebSocket tests
│   └── test_ws.py            #   CLI terminal bridge tests
└── store/                    # app-center icons etc.
```

## Deployment (pick one)

Both NAS app packages share the same `core/`; only the delivery shell differs.

| Method | Target | Artifact | Notes |
|---|---|---|---|
| **UGOS Pro app** (upk) | UGOS Pro (x86) | `src/build_dir/pkgs/upk/*.upk` | installs from the app center, port 12704 |
| **fnOS app** (fpk) | fnOS ≥ 0.8.1 (x86) | `fnos/dist/nasdsh-fnos-*.fpk` | installs from the app center, ships an offline image, port 12704 |

### UGOS Pro (upk)

UGreen requires packaging on Linux to preserve file permissions, so the
**build runs on the NAS**.

```bash
# 1) Mac: upload sources (requires sshpass)
cd nas-dsh/tools
NASDSH_PASS='your-ssh-password' NASDSH_HOST=<nas-alias-or-ip> bash upload.sh

# 2) NAS (ssh <user>@<nas-ip>): build + pack
cd ~/nasdsh-src/src
bash build.sh 1          # build number must increment if the version is unchanged
# artifact: src/build_dir/pkgs/upk/amd64_nasync_com.firewell.nasdsh_0.1.0.0001.upk
```

The first build installs dsh / dsh-TUI from an npm mirror (the image ships
them, but the build itself needs network). If the NAS needs a proxy for
outbound traffic, export `HTTP_PROXY` / `HTTPS_PROXY` before building, or:

```bash
docker build --build-arg NPM_REGISTRY=https://registry.npmmirror.com \
             -f core/Dockerfile -t nasdsh:0.1.0 core
```

Install: App Center → Settings → Developer settings (upload `ugdev.sig` the
first time) → manual install, pick the upk → desktop icon "NasDSH" → open in
browser/App.

### fnOS (fpk)

```bash
# on the fnOS box (or any x86_64 Docker machine):
docker build -f core/Dockerfile -t nasdsh:0.1.0 core
python3 fnos/build_fpk.py            # artifact: fnos/dist/nasdsh-fnos-0.1.0.fpk
# install: app center manual install, or sudo appcenter-cli install-fpk <fpk>
```

The install wizard configures project roots, the data directory (use a data
volume), the access PIN and model keys; see `fnos/README.md` for details. On
fnOS project paths look like `/vol1/...` — sessiond allows them via
`NASDSH_ROOTS` (the fpk scripts derive it from the project roots).

## Usage

1. Open the app; a privacy notice shows on first run; consent to continue.
2. Click **＋** → pick **Web workbench** (default) or **CLI terminal**.
   - Web: opens the shared instance directly (first start takes a few seconds
     to launch dsh web). Then click **Workspaces → +** in the sidebar; the
     picker starts at **Home → projects → volume1** (entrypoint symlinks every
     mounted volume under `$HOME/projects`). Use "Edit path" to type an
     absolute path directly. Switch projects inside the same UI.
   - CLI: enter a name, pick a project directory, and you land in dsh-TUI;
     a first-run account/model wizard appears once.
3. Closing the browser tab does not end sessions:
   - CLI tmux sessions survive; reopening the tab re-attaches;
   - the shared dsh web process keeps running; reopening the tab continues.
4. Closed tabs can be reopened from the top **Sessions** button (type,
   directory, running state). The DSH Web row also has **Restart** (use after
   changing the access address / trusted hosts) and **Stop**.
5. Right-click a tab → "End session" is what actually kills the process /
   tmux session.

## Model configuration

Providers live in `$DSH_HOME/cordis.patch.yml` (copied from the image template
on first start), shared by all three profiles (web / headless / dsh-tui).
Built-in:

| provider | endpoint | API key env |
|---|---|---|
| `deepseek-official` | DeepSeek official (built into dsh) | `DEEPSEEK_API_KEY` |
| `bigmodel-coding-plan` | `https://open.bigmodel.cn/api/coding/paas/v4` | `BIGMODEL_API_KEY` |
| `bailian-coding-plan` | `https://coding.dashscope.aliyuncs.com/v1` | `BAILIAN_API_KEY` |
| `token-plan` | `https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1` | `TOKENPLAN_API_KEY` |
| `volcengine-coding-plan` | `https://ark.cn-beijing.volces.com/api/coding/v3` | `VOLCENGINE_API_KEY` |
| `opencode-go` | `https://opencode.ai/zen/go/v1` | `OPENCODE_GO_API_KEY` |
| `xiaomi-mimo` | `https://api.xiaomimimo.com/v1` | `XIAOMI_MIMO_API_KEY` |

- **API keys never touch the install path** — no key fields in the install
  wizard, upk parameters, or anything inside a package. After install, open
  the workbench and fill them in **Settings → Models**; credentials persist in
  `/data/dsh-home/.credentials.yaml` (on the data volume, 0600);
  on NAS/remote setups prefer plain API keys — OAuth callbacks hit `localhost`
  on whatever machine runs the browser and may not reach you;
- default model: `bigmodel-coding-plan/glm-5.3-flash` when `BIGMODEL_API_KEY`
  is present, otherwise `deepseek-official/deepseek-flash`;
- **BigModel must use the `/coding/` subscription endpoint** — never switch it
  to the pay-per-token `/api/paas/v4/chat/completions`.

## Data & persistence

```
${DATA_PATH}/                     # DATA_PATH install parameter (SSD volume recommended)
├── dsh-home/                     # DSH_HOME
│   ├── cordis.patch.yml          #   providers / default model (editable)
│   ├── profiles/web|headless|dsh-tui/
│   ├── .credentials.yaml         #   model credentials (written by dsh, 0600)
│   └── sessions/                 #   session JSONL
├── home/                         # HOME (dsh-TUI settings etc.)
│   └── projects/                 #   workspace-picker shortcuts (→ /volume*, /home)
├── cache/                        # XDG_CACHE_HOME
├── logs/web.log                  # shared dsh web stdout/stderr
├── .term_pin                     # access PIN (0600)
└── proxy.env                     # optional: HTTP_PROXY / NPM_CONFIG_REGISTRY /
                                  #   advanced: KEY=value env injection (file on
                                  #   the data volume, never part of a package)
```

App upgrades/rebuilds keep data. Container restarts end all running Web/CLI
processes, but session records remain under `dsh-home/sessions` and reopening
a tab continues from there.

## Security

- LAN access is unauthenticated by default (same policy as NasOC); the
  optional `TERMINAL_PIN` install parameter is recommended for UGREENlink
  remote access.
- PIN login uses challenge-response + HttpOnly cookie — never in URLs, never
  resident in process environment variables.
- dsh web listens on `127.0.0.1` only; the only external path is sessiond's
  `/w/` prefix. `Host`/`Origin` pass through untouched and are validated by
  dsh's own browser-trust fence.
- API keys are never baked into images. Install parameters inject them as
  environment variables, or dsh's credential store persists them.
- The container runs as uid 1000 / gid 10; data directory ownership is fixed
  at startup.
- **Credentials never touch the install path**: the install wizard, upk
  parameters, fpk payloads and images contain no key fields or key files;
  keys exist only at runtime (dsh credential store / proxy.env on the data
  volume).
  `fnos/build_fpk.py` automatically runs `tools/verify_no_keys.py` on the
  artifact — a layered scan comparing against the real runtime secrets; any
  hit fails the build and deletes the artifact. Startup logs redact `-e`
  arguments.

## Testing

```bash
# local start (Mac/Linux; requires dsh and dsh-tui installed)
NASDSH_DATA=/tmp/nasdsh-data \
NASDSH_WWW=$PWD/core/www \
NASDSH_ROOTS=/tmp \
NASDSH_PORT=18080 \
python3 -I core/sessiond.py

# web reverse proxy / token / WebSocket
NASDSH_TEST_PORT=18080 python3 -I tools/test_web.py

# CLI terminal bridge (script creates its own bash tmux session)
NASDSH_TEST_PORT=18080 NASDSH_TEST_PATH=/tmp python3 -I tools/test_ws.py
```

## Known limitations

- The shared Web runs a single dsh web process (~250–400MB idle); each CLI
  tab's dsh-TUI is another Node process.
- Web and CLI share the same `DSH_HOME`; dsh workspace/settings writes are
  last-writer-wins — avoid concurrently editing global settings from Web and
  CLI.
- dsh's browser cookie is bound to the accessing `host:port`. sessiond adds
  the machine's LAN IPs to dsh's `--trusted-host` at web startup; for
  UGREENlink domains / reverse-proxy hostnames, list them in
  `NASDSH_TRUSTED_HOSTS` inside `proxy.env` (comma-separated) and restart the
  app — or use Sessions → DSH Web → Restart to pick up the new address.
- The reverse proxy listener is plain HTTP; behind an external TLS proxy some
  advertised links (`DSH_WEB_URL`) may still say `http://` — main interactions
  are unaffected.
- dsh is still in preview; upgrades may change config/plugin compatibility.
  After `nasdsh-update`, verify with a fresh tab.
- The fpk for fnOS embeds an offline Docker image (that is fnOS's app delivery
  mechanism — fnOS boxes have no bundled Node). Plain Linux users should
  install dsh directly instead of using this project.

## License & third-party components

- Original code: **MIT** (see `LICENSE`)
- Aggregated components: dsh (MIT), dsh-TUI (MIT), xterm.js / addon-fit (MIT),
  tmux (ISC), Node.js (MIT-style), Debian base image (multi-license). All are
  separate processes/static files — no copyleft contamination. See
  `THIRD_PARTY_NOTICES.md`.
- "DeepSeek Harness / dsh" is DeepSeek's project name. This is not an official
  DeepSeek product; the MIT license grants no trademark rights. For public
  distribution, clarify "bundles DeepSeek Harness" in the app name.
