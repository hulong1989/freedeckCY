> English | [中文](README.md)

# freedeckCY

[![CI](https://github.com/hulong1989/freedeckCY/actions/workflows/ci.yml/badge.svg)](https://github.com/hulong1989/freedeckCY/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hulong1989/freedeckCY)](https://github.com/hulong1989/freedeckCY/releases)
[![License](https://img.shields.io/github/license/hulong1989/freedeckCY)](LICENSE)

> **About this project**: freedeckCY is a derivative fork of [Freedeck](https://github.com/panyiwei-home/Freedeck);
> its version numbers start at **0.1.0** and are currently at **0.28.13**, which is not continuous with the original repository's 0.2–0.3 versions; the upstream author has stopped maintaining the project.
> Differences from upstream (already aligned / stronger here / not adopted) are documented in [docs/ARCHITECTURE.en.md](docs/ARCHITECTURE.en.md) §13.
>
> QQ group: **1136434612** (usage discussion / issue reports; please mention freedeckCY when joining)

A **Decky Loader plugin** for the Steam Deck: using resource catalogs from Tianyi Cloud Drive / Baidu Netdisk, it turns "download → extract → install into the Steam library" into a few buttons in the Decky plugin panel, and also provides cloud saves, playtime, emulators and diagnostics.

> ⚠️ **Disclaimer**
> This project collects game resource share links from the Internet; it constitutes **distribution of pirated resources**, violates cloud-drive terms of service, and involves copyright risk. The engineering work in this repository only covers dependencies, packaging, bug fixes, documentation and tests, and does **not recommend or endorse** deploying or using it on actual devices. Please support genuine copies.

---

## Current Status

| | Description |
|---|---|
| Current version | **0.28.13** (see [CHANGELOG.md](CHANGELOG.md) / [English summary](CHANGELOG.en.md)) |
| Code baseline | Forked from upstream Freedeck's early version (0.2) dated 2026-02; upstream is no longer maintained |
| Tests | **555 passed**, covering offline logic for catalog, installation, cloud saves, Baidu, emulators, storage, updates and more |
| CI | Python tests / UI build / frontend hooks scope check / x86_64 and aarch64 runtime smoke tests |
| Data directory | `~/.local/share/freedeckCY/` (`state.json` permissions 0600, directory 0700) |
| Resource catalog | `defaults/tianyi_catalog/freedeckcy_catalog.csv` (7084 entries) |
| Web system | A separate project, not in this repository and not included in the plugin package; the plugin only pulls and verifies the server CSV via `catalog_url` |

### Documentation Index

| Document | Contents |
|---|---|
| [docs/ARCHITECTURE.en.md](docs/ARCHITECTURE.en.md) | Implementation structure, native game library/input model, protocols, data and boundaries |
| [docs/DEVELOPMENT.en.md](docs/DEVELOPMENT.en.md) | Local development, on-device CEF debugging, testing, troubleshooting, submission checklist |
| [docs/DROIDDECK.en.md](docs/DROIDDECK.en.md) | Android/ARM64 installation, feature support, input and troubleshooting |
| [docs/ROADMAP.en.md](docs/ROADMAP.en.md) | Future directions and what has landed |
| [docs/UPSTREAM_SERVER.en.md](docs/UPSTREAM_SERVER.en.md) | Analysis of upstream server dependencies (freedeckCY does not depend on it) |
| [CHANGELOG.md](CHANGELOG.md) | Per-version change log |

## Core Features

### Game Library and Downloads

- **Decky native game library**: browse, search, platform/category filtering, sorting, pagination, load more and an installed page inside the plugin, with no web page required.
- **Three-stage visual overhaul of the game library**: responsive cover grid, Hero recommendation area, card source/installed badges, collapsible filter toolbar, category shelves, poster-style detail page, installed cards, skeleton screens and focus animations.
- **Bilingual UI**: choose Chinese / English on first launch, and the choice is stored locally; it can be switched at any time from the QAM home page or Settings, and QAM, settings, library, details, common dynamic states, and update-check toasts go through the English translation layer; Steam-owned/backend dynamic messages may still appear in Chinese.
- **Steam Deck native input**: D-pad/left-stick focus navigation, A to select, B to close details/library, L1/R1 to switch pages, L2/R2 to scroll about 0.8 screen; touchpad/touch scrolling for vertical lists and horizontal shelves; the focused card automatically scrolls into view, with the focus ring/top safe area fully visible.
- **Single/dual cloud-drive resources**:
  - A single Tianyi entry or a single Baidu entry can both go directly into the catalog.
  - When the same game exists on both Tianyi and Baidu, the entries are merged automatically, and the detail page lets the user choose "Tianyi Cloud Drive / Baidu Netdisk".
  - Cards show the source: `size · Tianyi Cloud Drive / Baidu Netdisk`.
- **Download and install pipeline**: aria2 multi-connection download (16 segments by default) → 7zz extraction → automatically write the Steam shortcut, Proton compatibility mapping and cover art.
- **Multi-volume/multi-part archives**: recognizes common multi-volume schemes such as `.7z.001` / `.part1.rar` / `.z01+zip`; installs only after all parts are downloaded, extracts only the main volume, and registers the Steam shortcut only once.
- **Resume and recovery**: aria2 runtime metadata is persisted; the plugin reattaches to the existing process on reload, and when the session is lost it claims tasks by file path and refreshes the original direct link to resume.
- **Integrity protection**: compares on-disk results against catalog sizes; anomalies are quarantined first and re-downloaded for self-healing. `7z t` validation (best-effort) before extraction; corrupted archives are automatically re-downloaded once.
- **Extraction protection**: waits for `.aria2` files to be released and sizes to stabilize before extracting; empty files/HTML error pages are intercepted early.
- **Steam config safety**: timestamped backups (12 kept) are made before writing `shortcuts.vdf` / `config.vdf`; files are not rewritten when unchanged.
- **Download management**: pause/resume all, global speed limit, retry failed tasks; task progress is shown on the plugin home page.
- **Storage locations**:
  - The download directory supports one-tap switching between "internal drive / SD card / external storage".
  - The internal drive is fixed to `~/Downloads`; external storage uses `<SD>/freedeckCY/downloads` and shows the free space.
  - The install directory likewise supports switching between "internal drive / SD card / external storage"; the internal install directory is fixed to `~/Games/freedeckCY`.
- **Optional launch file**: the catalog `executable_name` specifies the main PC exe / ROM; leave it empty for auto-detection.
- **Refresh without restart**: attempts SteamClient Refresh after installation, and prompts to restart Steam if that fails.

### Baidu Netdisk

- **QR-code login to Baidu Netdisk**: Passport `getqrcode → unicast → qrbdusslogin`, saving `BDUSS/STOKEN/PTOKEN` and the QR-login session cookies.
- **Login health check**: the settings page checks BDUSS, STOKEN, account info, bdstoken and the `/FreedeckTmp` transfer directory.
- **Share parsing**: `share/verify` obtains `BDCLND` → opens the `/s/1...` page → `share/list` paginated at 100 entries per page.
- **Transfer and download**: create `/FreedeckTmp` → `share/transfer` (`ondup=overwrite`) → `filemetas` → dlink 302, then clean up temporary files after installation.
- **Optional OpenAPI fallback**: when QR-login cookies are unavailable, a Baidu Open Platform app can be configured; the primary path is still web cookies.
- **Cookie storage**: `baidu_login` in `state.json`, file permissions 0600; cleared on logout.

### Catalog and Updates

- **Server CSV catalog**: "Check and update game list" on the settings page uses ETag / Last-Modified + SHA256 to decide; downloads only when there are changes and reports the number of new entries.
- **Ed25519 signatures**: both the catalog CSV and the update manifest are verified; if verification fails, the old catalog is kept.
- **Built-in catalog server**:
  - The default address is encoded into the build, and the real address is not shown on the settings page.
  - Leave the settings field empty → use the built-in server.
  - Enter a URL manually → overrides the built-in address; clear and save → restores the built-in one.
  - Catalog updates are checked automatically at startup.
- **Plugin updates via our own server**:
  - The catalog server is queried first (Web 1.3.0+):
    ```text
    GET /api/update/latest
    GET /api/update/latest.json.sig
    GET /api/update/asset/<file>.zip
    ```
  - The version manifest is Ed25519-verified, and the update package is SHA256-checked.
  - Falls back to GitHub Releases when the server is unavailable.
  - Clicking "Check for updates" manually forces a cache bypass; automatic checks are cached for 2 minutes.
  - Update packages are always saved to the internal drive at `~/Downloads` and no longer follow the SD-card download directory.
- **In-plugin update**: check, download and verify via "Diagnostics → Plugin Update" in the plugin settings; upgrade using Decky's "Install plugin from file".
- **Diagnostics and self-check**: checks plugin version, catalog, runtime, Steam, SD card, network, Baidu QR login, tasks and logs; one-tap export of a redacted zip.

### Cloud Saves, Emulators and Playtime

- **Automatic cloud saves**: Ludusavi manifest (53k+ games) + gamewatch process detection; after a game exits, only that game is uploaded, and unchanged saves are skipped automatically.
- **Cloud save restore**: conflict detection and in-place backup before overwriting; supports save restore for PC Proton and emulators.
- **10 emulator platforms**: GBA (mGBA) / PSP (PPSSPP) / NDS (melonDS) / PS1 (DuckStation) / FC, MD (Mesen2) / 3DS (Azahar) / PS2 (PCSX2) / PS3 (RPCS3) / Switch (Eden).
  - Official packages are downloaded online on first installation; emulators are not bundled in the plugin package.
  - 3DS/PS2/PS3 are x86_64 only; automatically hidden on aarch64.
  - BIOS/firmware deployment: PS1/PS2 BIOS, PS3 firmware, 3DS system files and Switch keys must be provided by the user.
- **PS1 multi-disc**: multiple `.cue/.chd` files automatically generate `freedeckcy-multidisc.m3u`.
- **Playtime**: accumulated by listening to Steam launch/exit events; displayed only on the detail pages of games managed by freedeckCY.

### Engineering and Security

- **Frontend hooks scope check**: `scripts/check-ui-scope.mjs` checks for undefined identifiers in `useMemo/useCallback/useEffect` dependency arrays; run in CI and by `make check-ui` to prevent settings-page `ReferenceError`s from shipping again.
- **Update flow extracted**: `UpdateFlowMixin` in `py_modules/update_flow.py` handles server/GitHub update checks and downloads, while `TianyiService` only orchestrates; the install/cloud-save/login flows will continue to be extracted.
- **Local HTTP service**: listens only on `127.0.0.1:59271`, validates Host/Origin, and caps the request body size.
- **Cookie/token redaction**: logs, diagnostic bundles and error messages redact BDUSS/STOKEN/cookies.
- **Bundled CA**: `py_modules/cacert.pem` takes precedence over system CAs, avoiding certificate errors caused by an incomplete Decky Python CA bundle.
- **CI**: pytest, UI build, hooks scope check, x86_64/aarch64 runtime smoke tests, catalog data validation and packaging smoke tests.

## Requirements

- SteamOS or another Linux (x86_64 / aarch64)
- [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader)
- A Tianyi Cloud Drive account; the Baidu Netdisk feature requires a Baidu account for QR-code login
- External dependencies fetched by the plugin itself: `aria2c`, `7zz`, `node` (prepared with `make runtime`; already included in packaged builds)

## Installation

### Option A: Release package (recommended)

Releases provide installation packages with bundled runtime binaries:

| Package | Applicable device |
|---|---|
| `freedeckCY-v0.28.13.zip` | Steam Deck / x86_64 Linux |
| `freedeckCY-v0.28.13-arm64.zip` | DroidDeck / Android ARM64 |

After downloading, use **Decky → Developer → Install plugin from file**, select the corresponding zip, and restart Decky Loader.
Checksums are available in the `.sha256` files attached to the Release.

### Option B: Build from source

```bash
git clone <this-repo> freedeckCY && cd freedeckCY
make runtime              # download aria2c / 7zz / node to defaults/runtime/
make package              # produces dist-artifacts/freedeckCY-v0.28.13.zip
```

### Option C: DroidDeck / ARM64

```bash
make runtime ARCH=aarch64
make package-droiddeck    # produces dist-artifacts/freedeckCY-v<version>-arm64.zip
```

Use **Import plugin zip** in DroidDeck's Decky menu. See [docs/DROIDDECK.en.md](docs/DROIDDECK.en.md) for details on paths, Proton and Android storage.

## First Use

1. Install the plugin and restart Decky Loader.
2. Decky quick access menu → freedeckCY → Settings:
   - Paths → Download directory: choose "Internal drive" or SD card.
   - Paths → Install directory: choose internal or external.
   - Game catalog: the built-in server is used by default; no input is needed.
3. Account → QR-code login to Tianyi Cloud Drive / Baidu Netdisk (as needed).
4. Game Library → select a game → choose a download source (when both cloud drives are available) → install.
5. Settings → Diagnostics → run self-check / export diagnostic bundle.

## Developing from Source

### Python side

After changing `py_modules/`, simply reload the Decky plugin; no build is required.

### React plugin panel

```bash
pnpm install
pnpm build          # produces dist/index.js
pnpm check:ui       # hooks dependency scope check
```

### Tests and checks

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q          # or make test; currently 555 cases
make check-ui                # frontend hooks scope check
make doctor                  # environment diagnostics (read-only)
make package-droiddeck       # ARM64 package
```

CI also runs catalog data validation, commit validation, packaging smoke tests and x86_64/aarch64 runtime smoke tests.

More details:

- [docs/ARCHITECTURE.en.md](docs/ARCHITECTURE.en.md) — architecture, sequences, interfaces, issue list
- [docs/DEVELOPMENT.en.md](docs/DEVELOPMENT.en.md) — development, debugging, troubleshooting
- [docs/DROIDDECK.en.md](docs/DROIDDECK.en.md) — Android / ARM64
- [docs/ROADMAP.en.md](docs/ROADMAP.en.md) — future plans
- [docs/UPSTREAM_SERVER.en.md](docs/UPSTREAM_SERVER.en.md) — reverse-engineering notes on the upstream server dependency

## Common Environment Variables

| Variable | Purpose |
|---|---|
| `FREEDECKCY_CATALOG_CSV_URL` | Overrides the built-in catalog server address (for headless/automated deployments) |
| `FREEDECKCY_GAME_CATALOG_CSV` | Overrides the resource catalog CSV path |
| `FREEDECKCY_COVER_INDEX_CSV` | Overrides the cover index CSV path |
| `FREEDECKCY_CATALOG_JSON` | Reads NewFreedeck-compatible JSON instead (local path or `https://`, disabled by default) |
| `FREEDECKCY_ARIA2_BIN` | Specifies the aria2c path |
| `FREEDECKCY_7Z_BIN` | Specifies the 7zz path |
| `FREEDECKCY_NODE_BIN` | Specifies the node path |
| `FREEDECKCY_PROTON_TOOL` | Overrides the Proton compatibility tool name; `none` means no mapping is written |
| `FREEDECKCY_STEAM_ROOT` | Overrides the Steam root directory (Flatpak / custom installs) |
| `FREEDECKCY_STATE_FILE` | Path to the state.json used by `clear_freedeckcy_tasks.sh` |
| `FREEDECKCY_PORT` | Local service port checked by `make doctor` (default 59271) |
| `FREEDECKCY_TLS_CA_FILE` | Overrides the TLS CA file (the bundled `cacert.pem` takes precedence by default) |
| `FREEDECKCY_LUDUSAVI_MANIFEST` | Overrides the Ludusavi save manifest path |
| `FREEDECKCY_BAIDU_OPENAPI_APP_KEY` | Baidu Open Platform App Key (optional fallback) |
| `FREEDECKCY_BAIDU_OPENAPI_SECRET_KEY` | Baidu Open Platform Secret Key (optional fallback) |
| `FREEDECKCY_BAIDU_OPENAPI_REFRESH_TOKEN` | Baidu refresh_token (headless environments) |

Emulator path variables (`FREEDECKCY_MGBA_BIN`, `FREEDECKCY_PPSSPP_BIN`, etc.) are described in [docs/DEVELOPMENT.en.md](docs/DEVELOPMENT.en.md).

## How It Works (One-Screen Overview)

```text
Catalog: built-in/custom CSV (Ed25519 signature verification)
        │
        ▼
Resolve share link (Tianyi / Baidu cookies) → direct link + cookies
        │
        ▼
aria2c multi-connection download ──▶ 7zz extraction ──▶ Steam shortcut/Proton/cover
        │
        ▼
Game appears in the Steam library (try refresh without restart; restart Steam on failure)

Plugin update: own server /api/update/latest (signed manifest)
        │
        ▼
Download package to ~/Downloads → SHA256 → Decky install from file
```

Cloud saves take a different route: `Proton prefix save directory → 7z + manifest.json → cloud drive freedeckCYCloudSaves/`; restoring reverses the steps and asks for conflict confirmation.

## Directory at a Glance

```text
main.py                     Decky plugin entry (thin RPC forwarding + background maintenance loop)
py_modules/
  tianyi_service.py         Business orchestration: install/cloud saves/login/playtime/diagnostics
  update_flow.py            Plugin update checks and downloads (UpdateFlowMixin)
  tianyi_client.py          Tianyi Cloud Drive protocol, TLS, direct links, upload
  baidu_client.py           Baidu web protocol: verify/list/transfer/direct link/cleanup/health check
  baidu_qr.py               Baidu Passport QR login (BDUSS/STOKEN/PTOKEN)
  catalog_signature.py      Ed25519 verification of catalog/update manifests
  game_catalog.py           Catalog parsing, platform/category, provider merge, cover index
  storage_options.py        Internal drive / SD / external storage detection
  tianyi_http.py            Local HTTP routing
  tianyi_store.py           state.json data model and read/write
  server_manager.py         aiohttp lifecycle, Host/Origin validation
  aria2_manager.py          aria2 runtime reuse, JSON-RPC, resume
  seven_zip_manager.py      7zz extraction/compression, `7z t` validation
  emulator_manager.py       Emulator registry and online download (10 platforms)
  emulator_setup.py         BIOS/firmware deployment, portable configuration
  save_manifest.py          Ludusavi save matching
  gamewatch.py              Game process detection (automatic cloud saves)
  steam_shortcuts.py        Steam shortcuts/Proton/cover art/backups
  archive_bundle.py         Multi-volume detection
  cacert.pem                Bundled CA bundle
src/index.tsx               Decky panel (build output in dist/)
scripts/check-ui-scope.mjs  Frontend hooks scope check
defaults/tianyi_catalog     Resource catalog (7084 entries) and cover index
defaults/ludusavi           Save manifest (53,549 games)
submissions/                Repository game submission JSON / schema
backend/*.js                Node helper scripts (share-parsing fallback, cloud-save upload)
scripts/                    Runtime fetching/packaging/diagnostics/catalog validation/submission merging
docs/                       Architecture/development/roadmap/DroidDeck
tests/                      pytest cases (555)
CHANGELOG.md                Version changes
Makefile                    runtime / package / package-droiddeck / test / check-ui / doctor / ...
```

## Security Notes

- The local service listens only on `127.0.0.1`, and Host must be a loopback address; write requests validate Origin and reject cross-site requests.
- It never returns `Access-Control-Allow-Origin: *`.
- `share_url` only accepts `cloud.189.cn` / `*.189.cn` / `pan.baidu.com`.
- `state.json` contains login cookies; directory 0700, file 0600.
- Update manifests are Ed25519-verified, and update packages are SHA256-checked.
- Cloud saves are backed up in place as `*.freedeckcy-bak-<timestamp>` before being overwritten.

## Standalone Web Submission System

The player submission website + admin/reviewer backend + SQLite + server CSV form a **separate project**, not in this repository and not inside the plugin package.

The plugin is only responsible for:

- downloading the catalog CSV via `catalog_url`;
- checking for plugin updates through its own server's update API;
- signature verification and SHA256 checks.

Since Web 1.4.0, the submission form supports separate Tianyi Cloud Drive and Baidu Netdisk links; once approved, it generates one or two catalog records (`server=t` / `server=b`).

## Game Submissions (Repository)

Two ways:

1. **Issue form**: "Submit game" in the web library, or open the [Issue form](https://github.com/hulong1989/freedeckCY/issues/new?template=submit-game.yml) directly. Maintainers merge immediately after adding the `auto-merge` label; there is also a scheduled task every 6 hours.
2. **PR**: copy `submissions/examples/example-pc.json` to `submissions/<platform>-<game-name>.json`, run `python scripts/validate_submissions.py`, and then open a PR.

Submit share links only; do not upload game files. Field definitions and rules are in [submissions/README.md](https://github.com/hulong1989/freedeckCY/blob/main/submissions/README.md).

## Known Issues

- **Download directory not writable**: when the directory saved on the settings page has no write permission, the plugin automatically falls back to `~/Downloads`, avoiding the "Tianyi service not initialized" error.

- **Unstable cloud-drive APIs**: Tianyi's private signatures and Baidu's web APIs may both break as the official implementations change.
- **Baidu login**: after the cookie expires, the QR code must be scanned again; transfers are affected by account space/API quotas/security verification; failure to delete temporary files does not affect already-downloaded files.
- **Cloud saves**: upload/restore depends on `node` (included in packaged builds); PS1/PS2 memory cards and Switch save directories may still not be splittable per game.
- **Emulators**: first installation requires downloading official packages online; PS1/PS2 BIOS, PS3 firmware, 3DS system files and Switch keys must be provided by the user; 3DS/PS2/PS3 are x86_64 only.
- **DroidDeck**: ARM64 support has not yet been fully verified on real devices.
- **Updates**: requires Web 1.3.0+ to publish a signed manifest; falls back to GitHub only when the server is unavailable. Update packages are always written to `~/Downloads`.
- **Catalog merge**: only entries with "same title + same platform + different cloud drive" are merged; duplicate entries on the same cloud drive remain separate.
- **Engineering debt**: `tianyi_service.py` is still large; the update flow has been extracted, and the install/cloud-save/login flows are still being split out.
- **No i18n**: the UI and error messages are all hard-coded in Chinese.

See the "Issue List" section of [docs/ARCHITECTURE.en.md](docs/ARCHITECTURE.en.md) for the complete issue list and priorities.

## License

[BSD 3-Clause](LICENSE) (from the Decky plugin template, original copyright notices retained).
