> English | [中文](DEVELOPMENT.md)

# freedeckCY Development Guide

This document is for secondary developers and corresponds to freedeckCY **v0.28.16**: how to run it locally, change code, apply patches, and troubleshoot. For installing, building, and troubleshooting DroidDeck (Android/ARM64), see [DROIDDECK.en.md](DROIDDECK.en.md) separately. For architecture and protocol details see [ARCHITECTURE.en.md](ARCHITECTURE.en.md); for a capability comparison with the author's v0.6 see [ARCHITECTURE.en.md](ARCHITECTURE.en.md) §13; for follow-up work see [ROADMAP.en.md](ROADMAP.en.md).

> Prerequisite: this project supports **SteamOS / Linux** only. The development machine can be a Steam Deck, or a Linux desktop with Decky Loader installed; on Windows / macOS you can only edit code, not run it fully.

---

## 1. Module Responsibilities at a Glance

| Path | Responsibility (one sentence) |
|---|---|
| `main.py` | Decky plugin entry: the `Plugin` class holds Python-side state and thin-forwards the 24 callable RPCs to `TianyiService` / `server_manager`; the main loop periodically calls background maintenance |
| `py_modules/config.py` | Path constants (download directory, `~/.local/share/freedeckCY`), background-maintenance interval, and logger (`/tmp/freedeckcy.log`, `RotatingFileHandler` 5 MB × 3) |
| `py_modules/tianyi_service.py` | **Business core**: install plans, download tasks, background installs, cloud saves, login, playtime, panel-state cache, cover resolution and caching, GBA/mGBA registration; key functions `maintenance_tick` (background maintenance), `refresh_tasks` (state sync), `_try_recover_task` / `_readd_task_download` (restart recovery + in-place relinking via `changeUri`), `_maybe_schedule_group_post_process` / `_finalize_group_install` (volume grouping), `_verify_downloaded_file` / `_quarantine_download_file` (integrity verification and self-healing), `_wait_payload_settled` / `_precheck_archive_payload` / `_schedule_archive_repair` (pre-extraction settling and automatic re-download when `7z t` fails), `retry_task` (retry failed tasks), `preview_uninstall` / `uninstall_installed_game` (uninstall preview and Proton prefix reclamation), `resolve_catalog_cover` (cover priority chain), `_load_cover_cache` / `_save_cover_cache` (disk cache), `_auto_register_task_to_steam` / `_auto_register_emulator_to_steam` (GBA launch scripts and native shortcuts) |
| `py_modules/tianyi_client.py` | **Tianyi Cloud Drive protocol client**: share resolution (`resolve_share(target_name, max_pages)` supports paging to find the target ROM), accessToken, direct download links, upload (calls Node), sessionKey |
| `py_modules/tianyi_http.py` | Local HTTP routes and handlers (**41 routes / 38 REST**): Vue pages, REST API, diagnostics zip, update check, unified JSON responses |
| `py_modules/server_manager.py` | aiohttp lifecycle, local API security boundary (Host/Origin validation), settings backup, `/_healthz` |
| `py_modules/tianyi_store.py` | Data classes (login/settings/tasks/installed games, including `file_size` / `group_id` / `group_total`) plus atomic `state.json` reads/writes; on write the directory is 0700 / files are 0600 |
| `py_modules/aria2_manager.py` | aria2 subprocess management (runtime metadata `aria2-runtime.json` + `flock` so a plugin reload can attach to a live instance) plus JSON-RPC (`addUri` / `changeUri` / `tellStatus` / `listDownloads` …) |
| `py_modules/seven_zip_manager.py` | 7z extraction / compression (with progress callbacks); `test_archive()` runs `7z t` as a pre-extraction check (skipped best-effort when 7z is unavailable) |
| `py_modules/save_manifest.py` | **Ludusavi save manifest (v0.8.0)**: loads the local JSON, matches by title/SteamID, resolves `<base>/<winAppData>/...` placeholders against the Proton prefix, expands globs (up to 200 paths); no network access at runtime |
| `py_modules/gamewatch.py` | **Game process detection (v0.8.0)**: scans `/proc/*/cmdline` every 8 s in the background (falls back to `pgrep -f` when `/proc` is unavailable); state transitions emit start/end events (auto cloud save is triggered only on end) |
| `py_modules/emulator_manager.py` | **Generic emulator registry (v0.14.1, all 10 platforms downloaded online)**: `EmulatorSpec`/`EMULATORS` describe GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch (3DS carries `flatpak_id=org.azahar_emu.Azahar`); `available_platforms(arch)` implements the architecture allowlist; official asset resolution, on-demand download on first install, AppImage/zip unpacking, 3DS prefers Flatpak on SteamOS (`_is_steamos`/`flatpak_installed`/`_ensure_flatpak`), `find_rom_file()`, 3DS wrapper forces XWayland, `emulator_status()`; the old `prepare_bios()` is kept for compatibility |
| `py_modules/emulator_saves.py` | **Emulator save discovery/restore (v0.15.0; restore/splitting in v0.16.0)**: `STANDARD_SAVE_DIRS`/`PORTABLE_SUBDIRS` cover 10 platforms; GBA/FC/MD/NDS match per game by ROM name, PSP/PS3 split via PARAM.SFO and 3DS via NCSD title id, while PS1/PS2/Switch remain shared; `restore_roots`/`build_restore_targets` provide the restore allowlist |
| `py_modules/param_sfo.py` | Minimal `PARAM.SFO` parsing (v0.16.0): `read_param_sfo()` reads key/value pairs, `find_param_sfo()` searches save directories recursively, used to split PSP/PS3 saves by TITLE |
| `py_modules/emulator_setup.py` | **Post-install BIOS/firmware deployment (v0.12.0; Flatpak path for 3DS added in v0.14.1)**: `setup_emulator(platform, command, seven_zip)` deploys files/archives under `bios/<platform>/` into the emulator directory and writes portable config; 3DS sysdata is also deployed to `~/.var/app/org.azahar_emu.Azahar/data/{azahar,azahar-emu}/sysdata`; only fills gaps / changes individual keys, never downloads |
| `py_modules/storage_options.py` | **Removable storage detection (v0.19.0)**: parses `/proc/mounts` to find writable submounts under `/run/media` (SteamOS SD) / `/media` / `/mnt` / `/storage` (DroidDeck) / `/sdcard`, filtering system fstypes and mount roots; returns `internal/external/options`, free/total, and the suggested `freedeckCY/{downloads,installed}` |
| `py_modules/submission.py` | **Repository game submissions (v0.13.0)**: `normalize_platform()` platform aliases, `validate_submission()`/`validate_submission_files()` validation, `build_catalog_row()` generates catalog rows, `merge_submissions()` merges (dry-run/`--apply`); pure standard library, directly importable by the CLI |
| `py_modules/baidu_qr.py` | **Baidu Passport QR login (v0.17.0, primary path)**: `request_qr()` fetches the QR sign/imgurl, `fetch_qr_image()` downloads the PNG, `poll_qr()` long-polls waiting/scanned/confirmed, `complete_login()` exchanges v for `BDUSS/STOKEN/PTOKEN` |
| `py_modules/baidu_client.py` | **Baidu share URL resolution/direct links (v0.17.0)**: `resolve_baidu_share(share_url, cookie)` resolves the share/file list via the Cookie primary path, `fetch_baidu_download_url()` obtains direct links; the OpenAPI fallback also reuses its public-share metadata |
| `py_modules/baidu_openapi_client.py` | **Baidu official OpenAPI (v0.14.0, optional fallback since v0.17.0)**: OAuth oob authorization (`build_baidu_oauth_authorize_url`/`exchange_baidu_oauth_code`/`refresh_baidu_oauth_token`), public-share transfer, `fetch_baidu_openapi_download_url`, `delete_baidu_openapi_transfer_file`; used only when there is no Cookie |
| `py_modules/steam_shortcuts.py` | Writes `shortcuts.vdf` (`DevkitGameID` token dedupe, no rewrite when unchanged, 12 backups before writing, read-back after writing), edits the Proton mapping in `config.vdf`, downloads `grid` covers, resolves appids; Steam multi-library / Flatpak / **DroidDeck** detection (`is_droiddeck` / `_steam_root_candidates` / `detect_proton_tool`), custom-username scoring; `find_compatdata_dirs()` locates Proton prefixes to clean up across libraries |
| `py_modules/game_catalog.py` | Reads the CSV resource catalog (16 columns / 7084 entries / 11 platforms, new catalog preferred with fallback to the old one): validation, search, pagination, lookup by `game_id`; `normalize_categories()` cleans categories at load time (strip platform names / dedupe / emulator fallback); supports merging `cover_index.csv` (without overwriting existing values); `list()` supports platform/category filters and returns `platforms`/Top12 `categories`; `_is_valid_tianyi_url()` accepts both `/t/` and `/web/share?code=` |
| `py_modules/archive_bundle.py` | Multi-volume archive detection (6 kinds such as `.7z.001`/`.partN.rar`/`.z01+zip`/`.r00+rar`): `detect_archive_sets` / `build_bundle_index` / `looks_like_multi_volume_name` |
| `py_modules/utils.py` | Port occupancy checks, waiting for port release, LAN IP probing (legacy) |
| `py_modules/vdf/` | Third-party VDF library (text + binary formats); `py_modules/vdf/__init__.py` provides `parse/loads/dumps/binary_dumps`, etc. |
| `backend/tianyi_share_resolver.js` | Node fallback implementation of share-link resolution (one line of JSON on stdin → one line of JSON on stdout) |
| `backend/tianyi_cloud_upload.js` | ESM implementation of cloud-drive upload (`upload`), version listing (`list_versions`), and download (`download_file`) |
| `backend/tianyi_cloud_upload.cjs` | CommonJS version of the same logic, **implementing only `upload`**; enabled only when the `.js` file is absent |
| `src/index.tsx` | All React code: QAM main panel, settings page, playtime injection into the Steam library page, global game event listeners |
| `defaults/tianyi_library_ui/` | Local Vue game library (browse on open, platform/category filters, **pagination/sorting**, **installed tab**, diagnostics export / update-check toolbar, gamepad focus sequence, non-PC platforms only prompt instead of installing) and the QR login bridge (no build step; edit directly) |
| `defaults/tianyi_catalog/gamebox_all_links_*.csv` | Resource catalog shipped with the plugin (`game_id,title,categories,down_url,pwd,openpath,filesize_z`, etc.) |
| `scripts/fetch_runtime.sh` | Downloads aria2c / 7zz / node into `defaults/runtime/` (invoked by `make runtime`) |
| `scripts/package.sh` | Assembles the Decky plugin zip into `dist-artifacts/` (invoked by `make package`); `PACKAGE_ARCH=x86_64|aarch64|all` controls the target architecture and artifact suffix |
| `scripts/fetch_ludusavi_manifest.py` | Downloads the upstream YAML and converts the Ludusavi save manifest to `defaults/ludusavi/manifest.json.gz` (invoked by `make ludusavi-manifest`; PyYAML is needed only at build time) |
| `scripts/doctor.sh` | Environment diagnostics (read-only, invoked by `make doctor`): system/Python/runtime/Steam/state/logs/ports/network |
| `scripts/normalize_catalog_categories.py` | Cleans catalog `categories` in place (strip platform names / dedupe / emulator fallback; `--check` only reports differences) |
| `scripts/validate_catalog.py` | Catalog data health check (duplicates/invalid links/empty titles/platform names mixed into categories/cover coverage/platform distribution/total size; `--strict` used by CI) |
| `tests/` | pytest unit tests (587 cases; native-library paths are verified by the frontend build): **gamewatch state machine / Ludusavi matching and parsing / auto-upload triggers and fingerprints / emulator save discovery (per-game vs shared, toggles) / restore plans / PSP-PS3-3DS splitting / PS1 multi-disc m3u**, catalog parsing/platform filters/sorting, installed list/diagnostics export/update check, **10-platform plans/ROM lookup/wrappers/registry/BIOS/architecture allowlist/BIOS deployment and portable config, submission validation/merging, Baidu QR login/Cookie + OpenAPI fallback (source detection/QR/plans/headers/auth-code exchange)**, category cleanup, DroidDeck detection/Proton parsing/dual Steam roots, VDF, state store, cloud-save versions, install pipeline, grouping semantics, restart recovery, multi-volume detection, aria2 runtime, multi-library detection, uninstall/compatdata, **install reliability (environment preflight/verify/repair/health/diagnostics/source fallback)**, security boundary, and other offline logic |
| `clear_freedeckcy_tasks.sh` | Ops script: clears the `tasks` in `state.json` (uses `$HOME`; the path can be overridden with `FREEDECKCY_STATE_FILE`) |
| `docs/DROIDDECK.md` | DroidDeck (Android/ARM64) install, build, feature support, and troubleshooting guide (v0.4.0) |
| `gl/` | Data hand-collected by the author (historical CSV, emulator share links); **not read by the code**, can be ignored |

---

## 2. Local Development

### 2.1 Mounting the Repository into Decky

Decky Loader loads plugins from `~/homebrew/plugins/`. For development a **symbolic link** is recommended, so that changing the repository means changing the running plugin:

```bash
# Back up and remove an installed plugin of the same name (if any)
mv ~/homebrew/plugins/freedeckCY ~/homebrew/plugins/freedeckCY.bak 2>/dev/null || true

# Point a symlink at your development repository
ln -s /path/to/freedeckCY ~/homebrew/plugins/freedeckCY
```

Then reload the plugin in Decky Loader (or restart the plugin loader/Steam). The plugin should appear in Game Mode's sidebar (QAM).

> A plugin installed from a zip is copied into the plugin directory, so repository changes do not take effect automatically; during development use the symlink approach above.

### 2.2 Python Side: Just Reload After Changes

`py_modules/*.py` and `main.py` are interpreted, so **no build is needed after editing**:

1. Modify the code;
2. Reload freedeckCY in Decky Loader (or restart the plugin loader);
3. Watch the log to confirm a successful reload: `tail -f /tmp/freedeckcy.log`.

Note: the plugin main loop calls `TianyiService.maintenance_tick()` once every `config.MAINTENANCE_INTERVAL_SECONDS` (8 s by default), which syncs download progress and finishes interrupted installs; it also runs once at startup. When debugging the download/install pipeline, first check whether this loop is running.

### 2.3 React / QAM Frontend

```bash
pnpm install
pnpm build      # rollup → dist/index.js (committed build artifact)
pnpm watch      # optional during development: auto-rebundle on file changes
```

- After changing `src/index.tsx` or `src/types.d.ts` you must run `pnpm build` again before the change takes effect on reload.
- Commit only `dist/index.js` and `dist/index.js.map`; `node_modules/` is not committed.

### 2.4 Legacy Vue Local Page (desktop debugging/fallback only)

> The current main entry is the Decky native React game library (see §6.14); `defaults/tianyi_library_ui/` is no longer opened from QAM "Game Library".

The `index.html`, `app.js`, `app.css`, `login_bridge.*`, and `vue.global.prod.js` under `defaults/tianyi_library_ui/` are **served straight to the browser** as static files, with no build step:

- Edit these files directly and refresh the page in Steam's built-in browser (reload the plugin if needed so that Python re-discovers the resource directory);
- The local page URL is still returned by `get_tianyi_library_url`, in the form `http://127.0.0.1:59271/tianyi/library`; it is only for desktop browsers/debugging; QAM "Game Library" has switched to a native React page.
- For debugging, open the above address directly in an incognito window of a desktop browser (it listens only on the loopback address, so it must be accessed on the local machine).

### 2.5 Catalog Data, Cover Index, and Filtering

**Catalog file priority** (`game_catalog.resolve_default_catalog_path()`): `FREEDECKCY_GAME_CATALOG_CSV` → `defaults/tianyi_catalog/freedeckcy_catalog.csv` (primary since v0.3.1, **7084 valid entries / 11 platforms, categories already cleaned**) → legacy `gamebox_all_links_20260221_234730.csv` (fallback, 2845 rows / 2685 entries) → `defaults/tianyi_catalog.csv`. Reload the plugin after editing the CSV (`initialize()` reads everything into memory).

**16 catalog CSV columns**:

```text
game_id,title,category_parent,categories,package_name,server,down_url,shorturl,
pwd,openpath,filesize_z,list_filesize,platform,cover_url,cover_portrait_url,steam_appid
```

- `down_url` supports `https://cloud.189.cn/t/<code>?pwd=...` and `https://cloud.189.cn/web/share?code=...` (the latter must include `code=`; commonly used for FC/GBA/MD resources); rows missing `title` or a link are counted as invalid;
- `platform` current values: `pc` / `fc` / `nds` / `psp` / `gba` / `3ds` / `ps2` / `ps1` / `ps3` / `md` / `switch` (missing values normalize to `pc`; aliases `steam/windows/win`→`pc`, `ns/nsx`→`switch`);
- Platform distribution: PC 2540, FC 1475, NDS 722, PSP 575, GBA 553, 3DS 305, PS2 250, PS1 194, PS3 194, MD 191, Switch 85.

**Merging the catalog from upstream v0.6 (reproducible)**: the data comes from v0.6's `freedeck_catalog.csv` (7041 rows / 28 columns) plus entries unique to the old catalog, generated with `scripts/merge_v06_catalog.py` at the repository root:

```bash
# Requires a local unpacked copy of upstream v0.6 (this project does not ship that data)
python3 scripts/merge_v06_catalog.py \
  --v06-dir ../0.6/freedeck-plugin/defaults/tianyi_catalog \
  --base defaults/tianyi_catalog/gamebox_all_links_20260221_234730.csv \
  --out defaults/tianyi_catalog/freedeckcy_catalog.csv \
  --cover-out defaults/tianyi_catalog/cover_index.csv
```

Script rules: the v0.6 catalog takes precedence, only Tianyi links are kept, entries are deduped by `game_id`, old-catalog rows missing from v0.6 are appended afterwards (43 entries, `platform=pc`), and the cover index is normalized to 6 columns. Reload the plugin after output to see the new data; the platform/category filter bars are generated automatically from the data, with no code changes.

**Optional remote JSON catalog (v0.6.2)**: `FREEDECKCY_CATALOG_JSON` may point to a local JSON file or an `https://…` URL (NewFreedeck-compatible); remote results are cached for 6 hours and fall back to the local CSV on failure; disabled by default, enabled only when set explicitly; the default catalog is downloaded from the settings page as a server CSV. Format/self-hosting notes in [UPSTREAM_SERVER.en.md](UPSTREAM_SERVER.en.md).

**Catalog data workflow (fixed three steps since v0.3.1)**:

```bash
# 1) merge from upstream v0.6 (optional; skip if a catalog already exists)
python3 scripts/merge_v06_catalog.py --v06-dir ../0.6/freedeck-plugin/defaults/tianyi_catalog

# 2) clean categories (strip platform names / dedupe / emulator fallback; --check only checks, does not write)
python3 scripts/normalize_catalog_categories.py defaults/tianyi_catalog/freedeckcy_catalog.csv
python3 scripts/normalize_catalog_categories.py defaults/tianyi_catalog/freedeckcy_catalog.csv --check

# 3) health check (CI runs the same command with --strict)
python3 scripts/validate_catalog.py defaults/tianyi_catalog/freedeckcy_catalog.csv \
  --cover-index defaults/tianyi_catalog/cover_index.csv --strict
```

Makefile shortcuts are also available: `make normalize-catalog`, `make validate-catalog`. **Steps 2 and 3 must be run after modifying/adding catalog data**: the CI python job runs `validate_catalog.py ... --strict` after pytest, so dirty data (duplicate game_id / invalid links / empty titles / platform names mixed into categories) turns the build red immediately.

**Category cleaning rules** (`game_catalog.normalize_categories()`, also applied to every row at load time):

- Separators: `,`, `，`, `/`, `、`, `;`, `；`, `|`; each segment is trimmed, deduped case-insensitively, and output is comma-separated;
- Platform-name tokens are stripped: `pc/fc/nds/psp/gba/3ds/ps1/ps2/ps3/md/switch/ns/arcade/psx` as well as the row's own `platform`;
- Emulator rows (`platform != pc`) that become empty after cleaning get **"Emulator"** filled in; PC rows stay empty;
- v0.3.1 data-cleanup result: **606 rows** had categories rewritten, no platform names remain in categories, and the "Emulator" category has 606 entries; `--check` now reports 0 differences (idempotent).

**Catalog health-check metrics** (`validate_catalog.py`, measured in v0.3.1): 7084 rows / 16 columns; 3473/7084 entries carry their own cover (49.0%); `cover_index.csv` (3470 rows) matches 3311 by `game_id`, and merged coverage is 6783/7084 (95.8%); after loader merging by `game_id` or title it is 6823/7084 (96.3%); total resource size is about 39 TB (39098.5 GB); only 1 warning (46 duplicate `down_url` values, which is normal for multiple entries pointing at the same share).

**Cover index** `defaults/tianyi_catalog/cover_index.csv` (**3470 rows** built into the repository; `FREEDECKCY_COVER_INDEX_CSV` can override it):

```csv
game_id,title,steam_appid,cover_url,cover_portrait_url,platform
18194,出行路线/横冲直撞/TRAIL OUT,1234567,https://example.com/trailout-header.jpg,https://example.com/trailout-portrait.jpg,pc
```

- Column-name aliases: landscape `cover_url` / `landscape_cover_url` / `cover`; portrait `cover_portrait_url` / `square_cover_url` / `portrait_url` / `portrait`; appid `steam_appid` / `app_id` / `appid`;
- Match order: exact `game_id` match first, then title (whitespace-stripped, lowercased); **only empty values are filled, existing catalog CSV values are never overwritten**; after merging **6823 / 7084 entries carry their own covers**;
- When only `steam_appid` is present, the plugin synthesizes Steam CDN covers (landscape `header.jpg`, portrait `library_600x900.jpg`); no cover URL needs to be filled in.

**Cover resolution order** (`resolve_catalog_cover`): static cover from catalog/index → memory/disk cache → Steam Store search → ProtonDB rating. Cache file `~/.local/share/freedeckCY/tianyi/cover_cache.json` (0600, atomic writes), positive cache 7 days, negative cache 30 minutes; delete it and reload the plugin to force re-resolution.

**Platform / category filtering (wired into the UI in v0.3.0)**:

- After searching, two filter rows appear: the platform row ("All platforms" + per-platform counts) and the category row ("All categories" + Top12 category counts); the platform row is shown only when the number of `platforms` is > 1 (currently 11 platforms, so it is visible);
- Gamepad focus order: search box → search button → platform row → category row → cards;
- Requests carry both `platform` and `category` parameters (`/api/tianyi/catalog`), and the two can be combined;
- **10 platforms are installable, trimmed automatically by architecture** (v0.11.0): cards for GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch open the install confirmation normally on supported architectures (the dialog shows the emulator name; a warning appears when BIOS/setup files are required); 3DS/PS2/PS3 are **x86_64 only** — on aarch64 the catalog query hides entries and filter rows for those platforms per the `available_platforms()` allowlist, and the backend `_build_install_plan()` likewise only allows `pc` plus platforms available on the current architecture. For emulator debugging see §6.8.

---

## 3. Preparing Runtime Binaries (`make runtime`)

The repository **does not commit** runtime binaries (`.gitignore` excludes `defaults/runtime/`). Fetch them first after cloning:

```bash
make runtime                      # download aria2c + 7zz + node for the local architecture into defaults/runtime/
make runtime ARCH=all             # download both x86_64 and aarch64
make help                         # list all make targets and variables
bash scripts/fetch_runtime.sh --help   # view script-level options
```

`scripts/fetch_runtime.sh` supports downloading by component/architecture individually (refer to the `--help` output):

```bash
bash scripts/fetch_runtime.sh --only 7z                  # download 7zz only
bash scripts/fetch_runtime.sh --only aria2 --arch x86_64 # download aria2c only
bash scripts/fetch_runtime.sh --only node --arch aarch64 # download node only
bash scripts/fetch_runtime.sh --force                    # ignore existing files and force re-download
bash scripts/fetch_runtime.sh --dest /tmp/runtime        # custom output directory (default <repo>/defaults/runtime)
```

On-disk layout (the code looks them up in this order, highest priority first):

```text
defaults/runtime/aria2/<arch>/aria2c            # <arch> = x86_64 | aarch64
defaults/runtime/7z/<arch>/7zz
defaults/runtime/node/<arch>/bin/node
```

**Emulator runtimes (10 platforms, v0.11.0)**: the `EMULATORS` registry in `py_modules/emulator_manager.py` describes each platform's official assets, launch arguments, ROM extensions, and optional fields (`state_key` cache-directory name, `executables` executable name inside the zip, `bios_required`, `setup_required/setup_hint`); `available_platforms(arch)` returns the platforms with official packages for the current architecture (3DS/PS2/PS3 are x86_64 only and are hidden by the catalog allowlist on aarch64):

| Platform | Emulator (version) | Official asset (arch → file) | Format | ROM extension | Environment variable |
|---|---|---|---|---|---|
| gba | mGBA 0.10.5 | `mGBA-0.10.5-appimage-{x64,arm64}.appimage` | AppImage, **downloaded on demand at first install** (x64 ~25MB / arm64 ~24.6MB) | `.gba` | `FREEDECKCY_MGBA_BIN` |
| psp | PPSSPP 1.20.4 | `PPSSPP-v1.20.4-anylinux-{x86_64,aarch64}.AppImage` | AppImage, downloaded on demand | `.iso/.cso/.pbp/.elf` | `FREEDECKCY_PPSSPP_BIN` |
| nds | melonDS 1.1 | `melonDS-1.1-appimage-{x86_64,aarch64}.zip` | AppImage inside a zip, downloaded on demand | `.nds/.dsi/.srl` | `FREEDECKCY_MELONDS_BIN` |
| ps1 | DuckStation `latest` | `DuckStation-{x64,arm64}.AppImage` | AppImage, downloaded on demand; **BIOS must be supplied by the user** | `.m3u/.cue/.chd/.iso/.pbp/.bin` | `FREEDECKCY_DUCKSTATION_BIN` |
| fc | Mesen2 2.1.1 | `Mesen_2.1.1_Linux_{x64,ARM64}.zip` | single `Mesen` file inside a zip, downloaded on demand | `.nes/.fds/.unf/.unif` | `FREEDECKCY_MESEN_BIN` |
| md | Mesen2 2.1.1 | same as above (**shares the cache with FC** at `emulators/mesen/<arch>/`) | single `Mesen` file inside a zip, downloaded on demand | `.md/.gen/.smd/.bin/.32x` | `FREEDECKCY_MESEN_BIN` |
| 3ds | Azahar 2126.2 | **SteamOS prefers Flathub `org.azahar_emu.Azahar`**; otherwise `azahar.AppImage` (**x86_64 only**) | 3DS system files (setup); Flatpak auto-installed or AppImage fallback | `.3ds/.cci/.cxi/.app` (`.cia` via `--install`) | `FREEDECKCY_AZAHAR_BIN` (highest priority) |
| ps2 | PCSX2 v2.8.2 | `pcsx2-v2.8.2-linux-appimage-x64-Qt.AppImage`, **x86_64 only** | AppImage, downloaded on demand; requires a PS2 BIOS | `.iso/.chd/.cue/.bin/.gz` | `FREEDECKCY_PCSX2_BIN` |
| ps3 | RPCS3 build-8d6b42e | `rpcs3-v0.0.43-20606-8d6b42e7_linux64.AppImage`, **x86_64 only** | AppImage, downloaded on demand; requires PS3 firmware (setup) | `.iso/.pkg/.elf/.self` | `FREEDECKCY_RPCS3_BIN` |
| switch | Eden v0.2.1 | x86_64 + aarch64 AppImage from `stable.eden-emu.dev/v0.2.1/` | AppImage, downloaded on demand; requires prod.keys + firmware (setup) | `.nsp/.xci` | `FREEDECKCY_EDEN_BIN` |

Launch arguments: GBA `-f <rom>`, PSP `--fullscreen <rom>`, NDS/3DS/Switch `<rom>`, PS1/PS2 `-batch -fullscreen <rom>`, PS3 `--no-gui <rom>`, FC/MD `/fullscreen <rom>`.

**Architecture allowlist**: `available_platforms(arch)` filters by whether `spec.assets` contains the current arch; `TianyiService.list_catalog()` passes `["pc", *available_platforms()]` to `GameCatalog.list(allowed_platforms=...)`, so x86_64 shows 10 platforms while aarch64 shows only GBA/PSP/NDS/PS1/FC/MD/Switch (3DS/PS2/PS3 entries and platform filter rows do not appear at all).

Resolution order (since v0.10.0 there is **no bundled-package branch**): `FREEDECKCY_<PLATFORM>_BIN` → already downloaded/unpacked emulator (`~/.local/share/freedeckCY/emulators/<state_key>/<arch>/`; GBA also accepts the legacy `<arch>/squashfs-root`) → system command → Flatpak (`io.mgba.mGBA` for mGBA; `org.azahar_emu.Azahar` for 3DS, auto-installed on SteamOS). If none is found, `emulator_status` returns `source=download` (true for all 10 platforms; when there is no asset for the current architecture it returns `available=false` + "platform hidden"), and on install `ensure_emulator` downloads from the GitHub release into `emulators/<state_key>/<arch>/`: AppImages go through `--appimage-extract` (no FUSE dependency, so it works under proot/DroidDeck), while zips are extracted first to find the executable named by `executables` (Mesen2's `Mesen`), otherwise the AppImage inside the zip. Only when the current architecture has no official asset is the plan rejected at plan stage.

**Offline provisioning**: put the official package in advance under `~/.local/share/freedeckCY/emulators/<platform>/<arch>/` (AppImages need `chmod +x`; zips can be left as-is and are extracted at install time), or point `FREEDECKCY_*_BIN` at a local executable/AppImage (GBA `FREEDECKCY_MGBA_BIN`, PSP `FREEDECKCY_PPSSPP_BIN`, NDS `FREEDECKCY_MELONDS_BIN`, PS1 `FREEDECKCY_DUCKSTATION_BIN`, FC/MD `FREEDECKCY_MESEN_BIN`).

**BIOS / firmware deployment (v0.12.0; supplied by the user, the plugin only deploys/prompts)**:

- Unified source directory: `~/.local/share/freedeckCY/bios/<platform>/`; after installation `setup_emulator(platform, command, seven_zip=self.seven_zip)` recursively scans that directory (`.bin/.rom/.bios/.keys/.pup/.nca`), and archives (`.zip/.7z/.rar/.tar/.gz/.tgz/.xz/.bz2`) are extracted with 7zz and copied to `bios/<platform>/_extracted/` as a persistent cache;
- **PS1**: BIOS is copied to `<AppDir>/bios` + the legacy `~/.local/share/duckstation/bios`; writes `portable.txt` and `portable_data/settings/settings.ini` (`[BIOS] SearchDirectory=./bios`, `[Display] Fullscreen=true`; if an INI already exists only these two keys are changed);
- **PS2**: BIOS is copied to `<AppDir>/bios`, `~/.local/share/PCSX2/bios`, and `~/.config/PCSX2/bios`; writes `portable.ini` and `inis/PCSX2.ini` (`[Folders] Bios`, `[UI] Fullscreen=true`);
- **NDS**: `bios7.bin/bios9.bin/firmware.bin/dsi_firmware.bin` and similar files are copied to `<AppDir>` and `~/.local/share/melonDS`;
- **Switch**: `prod.keys`/`title.keys` → `~/.local/share/eden/keys/`; the `.nca` directories unpacked from firmware → `~/.local/share/eden/nand/system/Contents/registered/`;
- **PS3**: `bios/ps3/PS3UPDAT.PUP`; if `~/.config/rpcs3/dev_flash` is empty, runs `rpcs3 --installfw <pup>` (600 s timeout; the failure reason is written into the message);
- **3DS**: system files → `~/.local/share/azahar-emu/sysdata` (also compatible with legacy `azahar`/`citra`);
- **GBA / PSP**: portable config only (mGBA `portable.ini` + `qt.ini` fullscreen; PPSSPP `portable.txt` + `memstick/PSP/SYSTEM/ppsspp.ini` fullscreen);
- `<AppDir>` is the directory of the executable returned by `ensure_emulator()` (after AppImage extraction it is `squashfs-root/`); if the directory is not writable, only the user data directory is written and a notice is shown;
- The deployment message is folded into the **installation-complete message** (no separate `warning` is sent any more); `emulator_status`/plan still return `bios_required/bios_present/bios_dir` and `setup_required/setup_hint`. Missing files **do not block installation**, but an install that cannot be played directly usually means the files were not placed correctly or deployment was not triggered. See §6.8 for details.

**ARM64 / DroidDeck**: the runtime directory is chosen from `platform.machine()` normalized to `x86_64` (`aarch64`/`arm64`→`aarch64`), so DroidDeck uses `defaults/runtime/aarch64/`. Prepare the arm64 runtime with `make runtime ARCH=aarch64` (or `ARCH=all` for both), see §4.1 and [DROIDDECK.en.md](DROIDDECK.en.md) for details.

The code prefers these bundled runtimes and falls back to system commands (`aria2c`, `7zz/7zr/7z`, `node`) only when they are absent. They can also be forced with environment variables:

| Environment variable | Effect |
|---|---|
| `FREEDECKCY_ARIA2_BIN` | aria2c executable path (legacy spelling `FRIENDECK_ARIA2_BIN` also supported) |
| `FREEDECKCY_7Z_BIN` | 7zz executable path |
| `FREEDECKCY_NODE_BIN` | node executable path (must be ≥ 18) |
| `FREEDECKCY_GAME_CATALOG_CSV` | overrides the resource catalog CSV path (legacy spelling `FRIENDECK_GAME_CATALOG_CSV` supported) |
| `FREEDECKCY_COVER_INDEX_CSV` | overrides the cover index CSV path (legacy spelling `FRIENDECK_COVER_INDEX_CSV` supported; the file is optional) |
| `FREEDECKCY_LUDUSAVI_MANIFEST` | overrides the Ludusavi save manifest JSON path (default `defaults/ludusavi/manifest.json.gz`) |
| `FREEDECKCY_STEAM_ROOT` | overrides the Steam root directory (for Flatpak / custom installs / multiple drives / dual clients on DroidDeck) |
| `FREEDECKCY_PROTON_TOOL` | overrides the Proton compatibility tool name; `none` means no mapping is written (DroidDeck defaults to `droiddeck-proton-arm64`) |
| `FREEDECKCY_CATALOG_JSON` | at runtime read NewFreedeck-compatible JSON instead (CSV by default, falls back on failure) |
| `FREEDECKCY_MGBA_BIN` | overrides the mGBA executable/AppImage path (uses the downloaded cache by default; may also point to a system mGBA or a manually provisioned AppImage) |
| `FREEDECKCY_PPSSPP_BIN` | overrides the PPSSPP executable/AppImage path (uses the downloaded/system version by default) |
| `FREEDECKCY_MELONDS_BIN` | overrides the melonDS executable/AppImage path (uses the downloaded/system version by default) |
| `FREEDECKCY_DUCKSTATION_BIN` | overrides the DuckStation executable/AppImage path (PS1; uses the downloaded/system version by default) |
| `FREEDECKCY_MESEN_BIN` | overrides the Mesen2 executable/AppImage path (shared by FC/MD; uses the downloaded/system version by default) |
| `FREEDECKCY_AZAHAR_BIN` | overrides the Azahar path (3DS; x86_64 only; uses the downloaded/system version by default) |
| `FREEDECKCY_PCSX2_BIN` | overrides the PCSX2 path (PS2; x86_64 only; uses the downloaded/system version by default) |
| `FREEDECKCY_RPCS3_BIN` | overrides the RPCS3 path (PS3; x86_64 only; uses the downloaded/system version by default) |
| `FREEDECKCY_EDEN_BIN` | overrides the Eden path (Switch; x86_64/aarch64; uses the downloaded/system version by default) |
| `FREEDECKCY_BAIDU_OPENAPI_APP_KEY` | Baidu Open Platform App Key (for headless environments; the value saved in state takes priority) |
| `FREEDECKCY_BAIDU_OPENAPI_SECRET_KEY` | Baidu Open Platform Secret Key (for headless environments; the value in state takes priority) |
| `FREEDECKCY_BAIDU_OPENAPI_REFRESH_TOKEN` | Baidu refresh_token override (used when state is empty; authorizing via QAM is still recommended) |
| `FREEDECKCY_STATE_FILE` | for `clear_freedeckcy_tasks.sh` only: overrides the `state.json` path |

> All three runtimes are only used on demand: skipping the download does not make the plugin fail to start, but downloads/extraction/cloud saves will respectively report "download component unavailable", "extraction component unavailable", and "node runtime not found".

---

## 4. Packaging (`make package`)

```bash
make package                            # → dist-artifacts/freedeckCY-v<version>.zip
make package PACKAGE_ARGS=--build-ui    # run pnpm build first, then package
make package PACKAGE_ARGS="--out-dir /tmp/freedeckcy-build"
bash scripts/package.sh --help          # view all options
```

- The version comes from the `version` field in `package.json` (currently `0.28.16`);
- The zip's **top-level directory must be the plugin directory `freedeckCY/`** (Decky local install looks for `top-level-dir/plugin.json`; files placed directly at the root are silently ignored); underneath are `main.py`, `plugin.json`, `package.json`, `LICENSE`, `README.md`, plus `dist/`, `py_modules/`, `backend/`, `defaults/`;
- The packaging script excludes `__pycache__`, `*.pyc`, `.DS_Store`, `node_modules`, `.git`, `tests`, `scripts`, `.github`, `docs`, `gl`, `dist-artifacts` (anything outside the whitelist is not packaged);
- By default it reuses the committed `dist/index.js` and does not force a `pnpm build`; use `bash scripts/package.sh --build-ui` when the frontend needs rebuilding (requires pnpm on PATH);
- If `make runtime` has been run, `defaults/runtime/` is packed into the zip as well (this is the key to offline installation); therefore `make clean` **keeps** `defaults/runtime/` by default, and `make clean CLEAN_RUNTIME=1` is needed to delete it;
- Custom output directory: `bash scripts/package.sh --out-dir /tmp/freedeckcy-build`;
- If `defaults/runtime/` is not prepared, the script only warns and does not fail — but the resulting package will still lack runtimes on the target machine, so run `make runtime` first; a missing `defaults/ludusavi/manifest.json.gz` also only warns (auto cloud save falls back to scanning plain Proton directories), but release packages should include it (`make ludusavi-manifest`);
- Installation: Decky Loader → Settings → Developer → install plugin from zip (wording differs slightly between Decky versions), or extract to `~/homebrew/plugins/freedeckCY/` and restart the plugin loader.

### 4.1 ARM64 / DroidDeck Packaging and Debugging (v0.4.0)

DroidDeck is an ARM64 environment on Android, so the plugin package must include the `aarch64` runtime:

```bash
make runtime ARCH=aarch64      # defaults/runtime/{aria2,7z,node}/aarch64/… (or ARCH=all to download both)
make package-droiddeck         # = PACKAGE_ARCH=aarch64 bash scripts/package.sh
                               # → dist-artifacts/freedeckCY-v<version>-arm64.zip

# equivalent low-level invocations (PACKAGE_ARGS can be passed additionally)
PACKAGE_ARCH=aarch64 bash scripts/package.sh
PACKAGE_ARCH=all     bash scripts/package.sh   # → ...-universal.zip (both x86_64 + aarch64 kept)
```

- `PACKAGE_ARCH` values: `x86_64` (default, no suffix) / `aarch64` (`-arm64`) / `all` (`-universal`); single-architecture packaging trims `defaults/runtime/{aria2,7z,node}/*/<other arch>` so the package size does not double; the plugin package does not include emulators — they are downloaded online on first install;
- **The plugin package contains no emulator** (`make emulator-runtime` / `scripts/fetch_emulator.sh` were removed in v0.10.0): the official packages for GBA/PSP/NDS/PS1/FC/MD are all downloaded from the GitHub release on first install (network required), and the package is about 45MB (about 68MB when mGBA was included earlier); the PS1 BIOS is not bundled either and must be supplied by the user (place it under `~/.local/share/freedeckCY/bios/ps1/`);
- Confirm the arm64 binaries: `file defaults/runtime/aria2/aarch64/aria2c` (should show `ELF 64-bit … ARM aarch64`), `ls defaults/runtime/7z/aarch64/7zz defaults/runtime/node/aarch64/bin/node`; rerun `make runtime ARCH=aarch64` for whichever is missing (emulators are not packaged, so nothing to prepare);
- Before packaging you can fetch a single component with `bash scripts/fetch_runtime.sh --only 7z --arch aarch64 --force`;
- Deployment: transfer `...-arm64.zip` to DroidDeck and install it with Decky's **Import plugin zip**; for first use, dual Steam roots, and ARM Proton troubleshooting see [DROIDDECK.en.md](DROIDDECK.en.md).

`make` also provides `test` (runs pytest), `clean` (cleans build artifacts and `__pycache__`), and `help` (lists all targets).

---

## 5. Tests

The repository uses pytest to cover offline-testable logic (no network, no writing to the Steam directory):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q

# or (requires .venv to be ready)
make test
```

Notes:

- `requirements-dev.txt` lives at the repository root and only needs dev dependencies such as `pytest` / `pytest-asyncio` / `aiohttp`; **runtime dependencies follow the Python shipped with Decky**, so do not install them into the plugin environment.
- If the system Python is too old (e.g. 3.9), use `python3.12 -m venv .venv` (CI uses 3.12). The `test` script in `package.json` is also `python3 -m pytest -q`.
- There are currently **587 cases** (`make test` measured `587 passed`). `tests/test_droiddeck.py` covers DroidDeck detection, ARM Proton resolution, dual Steam root ordering, and settings read/write; `tests/test_install_reliability.py` covers the pre-install preflight, installed-game verify/repair, health report, failure diagnostics/source fallback and batch retry of failed tasks; `tests/test_resume_probe.py` covers Range resume probing and the recovery/restart branches; the port-related cases in `tests/test_utils.py` rely on real sockets and timing and may occasionally time out under heavy machine load — just rerun.
- CI runs two jobs in `.github/workflows/ci.yml`: `python` (3.12, pytest) and `ui` (Node 20 + pnpm, `pnpm build` plus verifying that `dist/index.js` exists), triggered on push / pull_request.
- Advice for new changes: when changing the recovery/grouping logic in `tianyi_service.py`, prefer reusing the existing fake-aria2 scaffolding in `tests/test_install_pipeline.py`.

---

## 6. Debugging

### 6.1 The Three Essentials

| Target | Location / Command |
|---|---|
| Log | `/tmp/freedeckcy.log` (hard-coded in `config.py`; `RotatingFileHandler` 5 MB × 3 rotation; `tail -f /tmp/freedeckcy.log`) |
| State | `~/.local/share/freedeckCY/tianyi/state.json` |
| Health check | `curl -s http://127.0.0.1:59271/_healthz` → `{"status": "ok"}` |

### 6.2 Common Commands

```bash
# health check / is it running
curl -s http://127.0.0.1:59271/_healthz
ss -ltnp | grep 59271

# view download tasks (local HTTP API, bound to loopback only)
curl -s http://127.0.0.1:59271/api/tianyi/download/tasks | python3 -m json.tool

# view panel state (HTTP path; QAM goes through RPC)
curl -s http://127.0.0.1:59271/api/tianyi/state | python3 -m json.tool

# view settings and Proton resolution results (on DroidDeck focus on these fields)
curl -s http://127.0.0.1:59271/api/tianyi/settings | python3 -m json.tool
#   proton_tool          setting value (auto / none / a specific tool name)
#   proton_tool_resolved the tool name eventually written into config.vdf
#   droiddeck_detected   whether DroidDeck was detected

# manually verify the install plan (no download, probing only; requires being logged in to a Tianyi account first)
curl -s -X POST http://127.0.0.1:59271/api/tianyi/install/prepare \
  -H 'Content-Type: application/json' -d '{"game_id":"18194"}' | python3 -m json.tool

# filter for errors
grep -nE "ERROR|Traceback|失败" /tmp/freedeckcy.log | tail -50
```

### 6.3 Caveats When Editing `state.json` Directly

- **Exit the plugin / stop the Decky plugin loader before editing**, otherwise the in-memory state will overwrite your changes wholesale (every `state.json` save rewrites the whole file).
- Back it up before editing: `cp state.json state.json.bak`.
- Common fields: `settings.download_dir`, `settings.install_dir`, `tasks` (may be cleared), `installed_games` (keep records consistent with the on-disk directories when deleting manually).
- Permissions: the state directory defaults to 0700 and `state.json` to 0600 (it contains login cookies); after manually copying/replacing the file, run `chmod 600 state.json` to keep the permissions.
- To clear the task list you can also use the bundled script: `./clear_freedeckcy_tasks.sh` (reads `$HOME/.local/share/freedeckCY/tianyi/state.json` by default; can be overridden with `FREEDECKCY_STATE_FILE`; chmod 600 is applied after clearing).

### 6.4 Processes and Ports

- The plugin spawns `aria2c` (random RPC port + random secret) and `7zz` (exists briefly during extraction); cloud saves briefly spawn `node`.
- aria2 runtime state lives under `~/.local/share/freedeckCY/tianyi/aria2/`: `aria2-runtime.json` (RPC address/secret/pid), `aria2-runtime.lock` (flock, ensuring only one instance is started), `aria2.session`, `aria2.log`. On plugin reload it reads the metadata and attaches to a still-live aria2, so the gid/progress is usually not lost; to check "whether the current instance can be attached to", look at these two runtime files plus whether the pid is alive in `ps`.
- RPC/download errors are visible in `aria2.log` (the startup arguments include `--log`); errors of the download tasks themselves are also recorded in `state.json` under `tasks[].error_reason`.
- Since v0.28.15, recovery/rechain probes Range first: `resume unsupported` in the log means the route does not support resumable downloads, so the plugin quarantines the partial file (`*.freedeckcy-noresume-*`) and restarts from zero; `resume supported` means progress is kept while switching links.
- If `ps aux | grep aria2c` shows leftovers after the plugin has reloaded, simply reload the plugin again; `_unload()` in `main.py` stops aria2 and the local service.
- The local web service listens on a fixed `127.0.0.1:59271`; runtime state and port are persisted to Decky settings, but there is no UI to change the port, and it usually needs no change.

### 6.5 Steam Multiple Libraries / Custom Root Directory

Steam root lookup order (`steam_shortcuts._steam_root_candidates()`):

1. The directory specified by `FREEDECKCY_STEAM_ROOT` (highest priority);
2. `~/.steam/steam`;
3. `~/.local/share/Steam`;
4. `~/.steam/root`;
5. Flatpak: `~/.var/app/com.valvesoftware.Steam/.local/share/Steam`, `~/.var/app/com.valvesoftware.Steam/.steam/steam`.

Game libraries (SD card / second drive) come from `libraryfolders.vdf` (compatible with both the new `"path"` format and the old `{ "1": "/path" }` format); `compatdata` is located across all libraries via `find_compat_user_dir()`, no longer only in the main library.

- Shortcuts / `config.vdf` / covers are still written to the **main Steam root's** `userdata/` and `config/` (this is how Steam itself organizes them); only Proton prefixes (`compatdata`) are located across libraries.
- For debugging, temporarily export `FREEDECKCY_STEAM_ROOT=/path/to/Steam` and then reload the plugin; to make it permanent, add the variable to the environment of the Decky plugin loader process (e.g. `Environment=` in its systemd unit, then restart the plugin loader).
- For the `compatdata` user directory, `steamuser` / `deck` / `root` are tried first; if not found, custom Wine usernames are scored by their `AppData` / `Documents` / `Saved Games` directories (repacks often change the username).
- Before writing `shortcuts.vdf` / `config.vdf`, a backup `*.freedeckcy-bak-<YYYYmmdd_HHMMSS>` is created (the latest 12 per kind are kept); after writing `shortcuts.vdf` it is read back for verification.
- Related code: `_find_steam_root()` / `_steam_library_paths()` / `find_compat_user_dir()` / `_backup_file()` / `_shortcut_tokens()` in [steam_shortcuts.py](../py_modules/steam_shortcuts.py).

### 6.6 `make doctor` Environment Diagnostics (v0.1.1)

A single read-only command that collects all environment information needed for troubleshooting; suitable for users to run directly on a Steam Deck:

```bash
make doctor                               # equivalent to bash scripts/doctor.sh
bash scripts/doctor.sh --plugin-dir /path/to/freedeckCY   # diagnose a specific plugin directory
bash scripts/doctor.sh --help             # view options
```

The output is divided into 8 sections (`system / Python / runtime binaries / Steam / state file / logs / local service / network`):

| Section | What to look at |
|---|---|
| System | `plugin_dir`, kernel, architecture (runtime directories use `x86_64` / `aarch64`) |
| Python | whether `python3` is ≥ 3.10 (Decky requirement) |
| Runtime binaries | bundled paths and sizes of aria2c / 7zz / node, and their `file` type; if missing, hints whether to fall back to system commands or to run `make runtime` |
| Steam | Steam root, library paths in `libraryfolders.vdf`, `userdata` user directories |
| State file | `state.json` size/permissions, login state, task counts (error/waiting), installed records, download/install directories |
| Logs | size of `/tmp/freedeckcy.log` and the latest 5 `ERROR/Exception/失败` (failure) entries |
| Local service | whether port 59271 is listening, whether `/_healthz` returns 200 |
| Network | connectivity to `cloud.189.cn` and its HTTP status code |

Notes: the script is **read-only** and does not change any file; it supports `FREEDECKCY_STATE_FILE` / `FREEDECKCY_STEAM_ROOT` / `FREEDECKCY_PORT` / `DECKY_PLUGIN_DIR` to override the default paths. A suggested troubleshooting flow is to have the user attach the `make doctor` output first, then ask for logs.

### 6.7 Legacy Web Library, Installed, and Diagnostics Debugging (historical, v0.5.0)

> The current main entry is the Decky native library in §6.14; this section is kept for debugging the legacy Vue web library / HTTP API.

**New API debugging examples**:

```bash
# browse all resources (empty q) + sorting ("" / title / size_desc / size_asc / platform)
curl -s 'http://127.0.0.1:59271/api/tianyi/catalog?q=&page=1&page_size=5&sort=size_desc' | python3 -m json.tool
# can also filter by platform/category
curl -s 'http://127.0.0.1:59271/api/tianyi/catalog?q=&platform=fc&category=%E6%A8%A1%E6%8B%9F%E5%99%A8&page=1&page_size=5' | python3 -m json.tool

# installed list (includes exists/platform/cover/steam_appid)
curl -s http://127.0.0.1:59271/api/tianyi/installed | python3 -m json.tool
# launch / open folder / uninstall (POST JSON)
curl -s -X POST http://127.0.0.1:59271/api/tianyi/installed/launch      -H 'Content-Type: application/json' -d '{"game_id":"18194"}'
curl -s -X POST http://127.0.0.1:59271/api/tianyi/installed/open-folder -H 'Content-Type: application/json' -d '{"game_id":"18194"}'
curl -s -X POST http://127.0.0.1:59271/api/tianyi/installed/uninstall   -H 'Content-Type: application/json' -d '{"game_id":"18194","delete_files":true}'

# diagnostics JSON / diagnostics zip / update check
curl -s http://127.0.0.1:59271/api/tianyi/diagnostics | python3 -m json.tool
curl -s -OJ http://127.0.0.1:59271/api/tianyi/diagnostics/export   # saves freedeckcy-diagnostics.zip
curl -s http://127.0.0.1:59271/api/tianyi/update-check | python3 -m json.tool
```

**Library page shortcuts** (equivalent for browser / Steam Deck gamepad):

| Input | Game Library tab | Installed tab |
|---|---|---|
| D-pad / analog stick | search box→search button→platform row→category row→cards, 2D movement | search box/button→cards (no filter rows) |
| Enter / A | search/filter/open install confirmation | launch game (`launchInstalled()`, supported since v0.5.0) |
| B / Esc | close dialog / back to search box | close dialog / back to Game Library tab |
| X | switch to Installed | switch back to Game Library |
| Y | cycle sorting | open the installation directory of the current card |
| O | — | open installation directory |
| Delete | — | uninstall current card (confirm dialog) |
| PageUp / PageDown, L1 / R1 | previous page / next page | — |
| Click a card with the mouse | open install confirmation | launch the game through Steam |

**How to read the diagnostics bundle**: after extracting `freedeckcy-diagnostics.zip`:

- `diagnostics.json`: `version/python/system/arch/paths/runtime/steam/catalog/tasks/installed/settings/recent_errors` (`log_tail` has moved to a separate file);
- `log-tail.txt`: the last 300 lines of `/tmp/freedeckcy.log`;
- `README.txt`: explanation and issue-submission guidance.

All text has been redacted: HOME is replaced with `~`, and the values of `cookie/authorization/token/sessionkey/accesstoken/uid/pwd` are replaced with `<redacted>`; the latest 20 errors filtered from the log by keyword are in `recent_errors`. Check `runtime.*.exists`, `steam.proton_tool`, `droiddeck`, and `installed.missing_paths` first, then cross-reference `log-tail.txt`.

### 6.8 Emulator Installation Debugging (10 platforms, v0.11.0)

**Platforms and assets** (full fields in ARCH §5.10; **all 10 platforms are downloaded on demand from the official GitHub release at first install**, and no emulator is bundled in the plugin package; 3DS/PS2/PS3 are x86_64 only and are hidden by the catalog allowlist on aarch64):

| Platform | Emulator | Official asset URL (relative to `download_base`) | Architecture | Format | Launch arguments | ROM extension |
|---|---|---|---|---|---|---|
| gba | mGBA 0.10.5 | `mGBA-0.10.5-appimage-x64.appimage` / `-arm64` | x64 / arm64 | AppImage (downloaded on demand, x64 ~25MB / arm64 ~24.6MB) | `-f <rom>` | `.gba` |
| psp | PPSSPP 1.20.4 | `PPSSPP-v1.20.4-anylinux-x86_64.AppImage` / `-aarch64` | x64 / arm64 | AppImage | `--fullscreen <rom>` | `.iso/.cso/.pbp/.elf` |
| nds | melonDS 1.1 | `melonDS-1.1-appimage-x86_64.zip` / `-aarch64` | x64 / arm64 | AppImage inside a zip | `<rom>` | `.nds/.dsi/.srl` |
| ps1 | DuckStation `latest` | `DuckStation-x64.AppImage` / `DuckStation-arm64.AppImage` | x64 / arm64 | AppImage | `-batch -fullscreen <rom>` | `.m3u/.cue/.chd/.iso/.pbp/.bin` |
| fc | Mesen2 2.1.1 | `Mesen_2.1.1_Linux_x64.zip` / `_ARM64.zip` | x64 / arm64 | single `Mesen` file inside a zip | `/fullscreen <rom>` | `.nes/.fds/.unf/.unif` |
| md | Mesen2 2.1.1 | same as FC (shares `emulators/mesen/<arch>/`) | x64 / arm64 | single `Mesen` file inside a zip | `/fullscreen <rom>` | `.md/.gen/.smd/.bin/.32x` |
| 3ds | Azahar 2126.2 | `azahar.AppImage` | **x64 only** | AppImage (requires system files setup) | `<rom>` | `.3ds/.cci/.cxi/.app` (`.cia` via `--install`) |
| ps2 | PCSX2 v2.8.2 | `pcsx2-v2.8.2-linux-appimage-x64-Qt.AppImage` | **x64 only** | AppImage (requires PS2 BIOS) | `-batch -fullscreen <rom>` | `.iso/.chd/.cue/.bin/.gz` |
| ps3 | RPCS3 build-8d6b42e | `rpcs3-v0.0.43-20606-8d6b42e7_linux64.AppImage` | **x64 only** | AppImage (requires PS3 firmware setup) | `--no-gui <rom>` | `.iso/.pkg/.elf/.self` |
| switch | Eden v0.2.1 | amd64/aarch64 AppImage from `stable.eden-emu.dev/v0.2.1/` | x64 / arm64 | AppImage (requires prod.keys + firmware setup) | `<rom>` | `.nsp/.xci` |

Corresponding repositories: mgba-emu/mgba, hrydgard/ppsspp, melonDS-emu/melonDS, stenzek/duckstation, SourMesen/Mesen2, azahar-emu/azahar, PCSX2/pcsx2, RPCS3/rpcs3-binaries-linux, eden-emu/eden (Switch uses `stable.eden-emu.dev`). File sizes follow the official release (each platform's `min_bytes` verifies download integrity).

**Pre-checks / diagnostics**:

```bash
# since v0.10.0 make emulator-runtime is no longer needed: the first install downloads automatically;
# for offline provisioning, put the official AppImage in the cache directory and chmod +x, or simply set *_BIN to override
ls -l ~/.local/share/freedeckCY/emulators/gba/<arch>/ 2>/dev/null

curl -s http://127.0.0.1:59271/api/tianyi/diagnostics | python3 -m json.tool
# look at data.emulators.{gba,psp,nds,ps1,fc,md,3ds,ps2,ps3,switch}:
#   available / source (extracted/download/system/flatpak/env) / name / version
#   ps1/ps2 additionally have bios_required / bios_present / bios_dir; 3ds/ps3/switch have setup_required / setup_hint
#   on aarch64 the available of 3ds/ps2/ps3 is false ("platform hidden")

# confirm the catalog is trimmed by architecture (on aarch64 only 7 emulator platforms + pc should be visible)
curl -s 'http://127.0.0.1:59271/api/tianyi/catalog?q=&page=1&page_size=1' | python3 -c \
  'import json,sys; d=json.load(sys.stdin)["data"]; print([p["value"] for p in d["platforms"]])'
```

**Install-plan debugging** (all platforms page through the share using the filename in openpath):

```bash
for gid in "<GBA game_id>" "<PSP game_id>" "<NDS game_id>" "<PS1 game_id>" "<FC game_id>" "<MD game_id>"; do
  curl -s -X POST http://127.0.0.1:59271/api/tianyi/install/prepare \
    -H 'Content-Type: application/json' -d "{\"game_id\":\"$gid\"}" | python3 -m json.tool
done
# pay attention to platform, emulator (mgba/ppsspp/melonds/duckstation/mesen), emulator_info,
# emulator_info.source (download means auto-download at install time), rom_target, files[] (should contain only 1 target file)
# for ps1 also check emulator_info.bios_required / bios_present / bios_dir
```

**PS1/PS2 BIOS placement, archives, and manual deployment**:

```bash
mkdir -p ~/.local/share/freedeckCY/bios/ps1 ~/.local/share/freedeckCY/bios/ps2
cp /path/to/scph5501.bin ~/.local/share/freedeckCY/bios/ps1/     # region/version as needed
cp /path/to/scph39001.bin ~/.local/share/freedeckCY/bios/ps2/
# archives are also supported: at install time they are extracted with 7zz to bios/<platform>/_extracted/ and then deployed
cp /path/to/ps1-bios.zip ~/.local/share/freedeckCY/bios/ps1/

# check the deployment result after installation (the setup message is also folded into the installation-complete message)
ls -l ~/.local/share/freedeckCY/emulators/<state_key>/<arch>/squashfs-root/bios/ 2>/dev/null
ls -l ~/.local/share/duckstation/bios/ ~/.local/share/PCSX2/bios/ ~/.config/PCSX2/bios/ 2>/dev/null
cat ~/.local/share/freedeckCY/emulators/<state_key>/<arch>/squashfs-root/portable.txt 2>/dev/null
# DuckStation: portable_data/settings/settings.ini
# PCSX2: inis/PCSX2.ini ([Folders] Bios / [UI] Fullscreen)
# manual repair (example; existing files are not overwritten):
cp -n ~/.local/share/freedeckCY/bios/ps1/*.bin ~/.local/share/duckstation/bios/ 2>/dev/null || true
cp -n ~/.local/share/freedeckCY/bios/ps2/*.bin ~/.local/share/PCSX2/bios/ 2>/dev/null || true
```

A missing BIOS does not block installation: the install message / library-page dialog prompts "PS1 BIOS required: please put scph*.bin into …"; after adding the BIOS, reinstall or copy it manually (you can first run `bash launch-freedeckcy.sh` to verify whether DuckStation recognizes it).

**3DS (Azahar) Flatpak-specific (v0.14.1)**: on SteamOS 3.9.5 the Azahar AppImage has known issues (upstream #127 won't open, #953 crashes in Game Mode), so the official Flatpak is preferred:

```bash
# install the Flatpak manually (the plugin also does this automatically on SteamOS; if it fails, try a system install)
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y --user flathub org.azahar_emu.Azahar
flatpak run org.azahar_emu.Azahar

# confirm the plugin is using the Flatpak:
flatpak info org.azahar_emu.Azahar
curl -s http://127.0.0.1:59271/api/tianyi/diagnostics | python3 -m json.tool
# data.emulators.3ds.source == "flatpak"; there are also flatpak_id / flatpak_available / flatpak_installed
```

- Selection order: `FREEDECKCY_AZAHAR_BIN` > installed Flatpak > Flatpak auto-installed on SteamOS > AppImage download/unpack; pointing `FREEDECKCY_AZAHAR_BIN` at an AppImage forces the fallback;
- The 3DS wrapper writes `export QT_QPA_PLATFORM=xcb` + `export SDL_VIDEODRIVER=x11` (XWayland) to avoid Game Mode/Wayland crashes;
- Besides `~/.local/share/azahar-emu/sysdata`, system files are also deployed to `~/.var/app/org.azahar_emu.Azahar/data/azahar-emu/sysdata` (`nand/sdmc/sysdata` under `bios/3ds/`, or archives; the directory tree is preserved);
- **Automatic repair of existing games**: the first background-maintenance tick scans installed 3DS records and rewrites `launch-freedeckcy.sh` (old AppImage command → `flatpak run`), with no reinstall needed; log keywords `Repaired 3DS launcher for ...` / `Repair 3DS launcher failed`.

**Post-install checks**:

```bash
ls -l "<install_dir>/<game dir>/launch-freedeckcy.sh"
cat "<install_dir>/<game dir>/launch-freedeckcy.sh"
# gba: exec <mGBA> -f <rom>
# psp: exec <PPSSPP> --fullscreen <rom>
# nds: exec <melonDS> <rom>
# ps1: exec <DuckStation> -batch -fullscreen <rom>
# fc/md: exec <Mesen> /fullscreen <rom>

# on-demand download/unpack directories (fc/md share mesen; ps1/psp/nds each have their own platform directory)
ls -l ~/.local/share/freedeckCY/emulators/{psp,nds,duckstation,mesen}/<arch>/
ls -l ~/.local/share/freedeckCY/emulators/<platform>/<arch>/squashfs-root/AppRun

bash "<install_dir>/<game dir>/launch-freedeckcy.sh"   # manual verification outside Steam
cat ~/.local/share/freedeckCY/tianyi/state.json | python3 -m json.tool | grep -A4 rom_path
# installed_games: platform, emulator, rom_path, launcher_path, steam_app_id
```

The Steam entry's Exe is `launch-freedeckcy.sh`, `LaunchOptions` carries `freedeckcy:tianyi:<token>`, and the **Proton mapping is none** (native Linux). Log keywords: `Auto add emulator game to Steam failed`, `Auto add emulator game to Steam exception`, `Resolve emulator cover failed`. **All emulators are outside the package**; the first install requires a network download (failures surface the HTTP status or unpacking error in the install message/log).

### 6.9 Auto Cloud Save Debugging (Ludusavi + gamewatch, v0.8.0)

**Manifest**: `defaults/ludusavi/manifest.json.gz` (53,549 games, ~2 MB gzipped / 14 MB uncompressed, MIT; source mtkennerly/ludusavi-manifest). At runtime it only reads the local file and **does not go online**.

```bash
# regenerate the manifest (requires PyYAML, build time only; already included in requirements-dev.txt)
pip install pyyaml            # or .venv/bin/pip install -r requirements-dev.txt
make ludusavi-manifest        # = python3 scripts/fetch_ludusavi_manifest.py

# override the manifest path (for debugging/replacement)
FREEDECKCY_LUDUSAVI_MANIFEST=/path/to/manifest.json ...
```

The manifest conversion script also updates `defaults/ludusavi/{README.md,LICENSE}` (the README records the upstream URL, entry count, byte size, and sha256).

**Matching and diagnostics**: when collecting upload candidates, the `compat_user_dir`/appid is first obtained from the shortcut, then the manifest is consulted; `diagnostics.collect` in the upload state gives each game's `source_strategy`:

| source_strategy | Meaning |
|---|---|
| `ludusavi` | manifest hit and the Proton directory scan missed |
| `ludusavi+proton` | both hit (paths already deduped and merged) |
| `proton_prefix` | only the pre-existing Proton directory scan hit (manifest missed/disabled) |
| `install_fallback` | no Proton prefix; falls back to the install-directory whitelist |

`diagnostics.ludusavi = {matched, path_count}` confirms whether the title/SteamID matched; search the log for `Ludusavi 清单已加载: N 款游戏` (Ludusavi manifest loaded: N games).

**gamewatch debugging**: background maintenance checks the running state of installed games every 8 s.

```bash
# inspect a process command line manually (when Steam launches directly via a script, install_path appears in cmdline)
cat /proc/<pid>/cmdline | tr '\0' ' '
# or search directly for the install directory
grep -l "<install_path>" /proc/*/cmdline 2>/dev/null

# when the container/proot has no /proc, the code falls back to pgrep -f (the system needs pgrep)
pgrep -af "<install_path>"
```

State machine: the first poll only establishes a baseline; only a subsequent "running→exited" transition produces an `end` event; removing a game from the installed list clears its state. Log keywords: `auto cloud save upload after exit game=... accepted=...`, `gamewatch poll failed`.

**Auto-upload switch**: the `cloud_save_auto_upload` setting defaults to **true**; the QAM "Cloud Save Upload" page has an "Auto-upload after game exit" switch; HTTP also works:

```bash
curl -s -X POST http://127.0.0.1:59271/api/tianyi/settings -H 'Content-Type: application/json' \
  -d '{"cloud_save_auto_upload": false}'
curl -s http://127.0.0.1:59271/api/tianyi/settings | python3 -m json.tool | grep cloud_save_auto_upload
```

Trigger conditions: setting enabled + logged in + no cloud-save upload/auto-upload task currently running + ≥ 30 s since the last auto upload; only **that game_id** is passed to `start_cloud_save_upload(game_ids=[...])`.

**Fingerprint and reset**: the fingerprint = `sha256(relative path|size|mtime_ns …)` (at most 5000 files per game), persisted in `state.json` under `cloud_save_fingerprints`. If it is unchanged before upload, the upload is skipped and the result is `reason=unchanged`. To force a re-upload: exit the plugin, edit `state.json` to delete the fingerprint for the corresponding `game_key` (or delete the whole `cloud_save_fingerprints` field), then reload the plugin.

**Emulator saves (v0.15.0)**: for non-PC platforms, saves are discovered by `py_modules/emulator_saves.py`, and candidates join with `source_strategy="emulator_saves"`.

- **Standard directories** (`STANDARD_SAVE_DIRS`): mGBA `~/.local/share/mgba/saves` (including Flatpak `~/.var/app/io.mgba.mGBA/...`), PPSSPP `PSP/SAVEDATA`, melonDS `saves`, DuckStation `memcards`, Mesen2 `Saves`, PCSX2 `memcards`, RPCS3 `dev_hdd0/home`, Eden `nand/user/save`, 3DS `sdmc`/`nand/user/save` + Azahar Flatpak `~/.var/app/org.azahar_emu.Azahar/data/azahar/{sdmc,nand/user/save}`;
- **portable directories** (`PORTABLE_SUBDIRS`): relative to the install root, ROM directory, launch-script directory, and unpacked emulator directory, e.g. `saves`/`memcards`/`memstick/PSP/SAVEDATA`/`sdmc`;
- **Per-game** (gba/fc/md/nds): in candidate directories, find `.sav/.srm/.dsv/...` or a directory with the same name as the ROM filename stem; if not found, returns `game_save_not_found` and **does not degrade to the whole directory**;
- **Shared** (psp/ps1/ps2/3ds/ps3/switch): returns the whole directory (empty directories skipped); the service layer dedupes by the `tuple(source_paths)` signature and records duplicates as `emulator_saves_shared`;
- **Debugging**: for each entry in the upload-state `diagnostics.collect`, `diagnostics.emulator_saves = {paths, platform, emulator, per_game, searched, reason}`; skip reasons are `save_dir_missing` / `game_save_not_found` / `emulator_saves_shared` / `emulator_saves_disabled`;
- **Switch**: the `cloud_save_include_emulators` setting defaults to true; QAM "Cloud Save Upload → Include emulator saves", or HTTP:

```bash
curl -s -X POST http://127.0.0.1:59271/api/tianyi/settings -H 'Content-Type: application/json' \
  -d '{"cloud_save_include_emulators": false}'
curl -s http://127.0.0.1:59271/api/tianyi/settings | python3 -m json.tool | grep include_emulators
```

- **Privacy/size**: 3DS (`sdmc`/`nand`) and Switch (`nand/user/save`) directories can be large and are subject to the 5000-file fingerprint limit and upload-size limits; shared memory cards include other games on the same card, so confirm the directory contents before uploading;
- **Restore**: supported since v0.16.0 (see the next section); PS1/PS2 single memory cards and Switch directories cannot be split per game; backups are made before overwriting and conflicts require confirmation.

**Emulator save restore (v0.16.0)**:

- Restore planning: when `plan_cloud_save_restore` encounters manifest `source_strategy="emulator_saves"` → `_plan_emulator_save_restore()`; `copy_pairs`/`plan_items` are generated from the platform roots of installed records; target conflicts carry `conflict_count`/`conflict_samples` and `requires_confirmation`;
- **Target whitelist**: `restore_roots(record)` returns the platform's standard/portable roots; `build_restore_targets(record, entries)` only allows writing into those roots — if the same machine's `source_path` parent directory is inside a root, it restores to that original parent directory, while cross-machine restores land in the first root; arbitrary HOME paths from the manifest are rejected;
- **Backups**: apply follows the existing restore flow and creates `*.freedeckcy-bak-<YYYYmmdd_HHMMSS>` before overwriting;
- State/diagnostic fields: `stage=ready`, `requires_confirmation`, `conflict_count`, `conflict_samples`, `target_candidates`, `entry_target_dirs`;
- Boundaries: PS1/PS2 single memory cards and Switch directories cannot be split per game; 3DS may degrade to the root directory across devices; overwriting a shared card requires confirmation.

**Per-game splitting debugging (v0.16.0)**:

```bash
# PSP/PS3: the save directory should contain PARAM.SFO; TITLE is matched against the game title after normalization
find ~/.local/share/ppsspp ~/.config/rpcs3 -name PARAM.SFO 2>/dev/null
python3 - <<'PY'
import sys; sys.path.insert(0, "py_modules")
from param_sfo import read_param_sfo
print(read_param_sfo("<PARAM.SFO path>").get("TITLE"))
PY

# 3DS: the NCSD header is 16 bytes starting at 0x100, with the Program ID at 0x108 (8 bytes little-endian)
xxd -s 0x100 -l 16 "<game>.3ds"
# directory: .../title/00040000/<low8>/
```

In upload candidates, `emulator_saves.per_game=True` means the split succeeded; `False` means it fell back to the shared directory. Split failure reasons are in `searched`/`reason` (missing PARAM.SFO / TITLE mismatch / unreadable NCSD all cause a fallback, which is not an error).

**PS1 multi-disc m3u (v0.16.0)**: `find_rom_file()` looks for an `.m3u` first for PS1 (uses it if present); if there is none and there is more than one `.cue/.chd`, it generates `<common parent dir>/freedeckcy-multidisc.m3u` in natural sort order (relative paths, `#EXTM3U`); a single disc still returns the `.cue`; you can inspect/reorder it manually:

```bash
cat "<install_dir>/<game>/freedeckcy-multidisc.m3u"
# if the order is wrong, edit it directly, or delete it so the plugin regenerates it in natural order; an existing m3u is not overwritten
```

### 6.10 Game Submission Validation and Merging (v0.13.0)

**Main document**: [submissions/README.md](../submissions/README.md) (field table, rules, and the two ways: Issue/PR); this section only lists commands for developers/maintainers and troubleshooting.

**Entry points**: the GitHub Issue form [.github/ISSUE_TEMPLATE/submit-game.yml](../.github/ISSUE_TEMPLATE/submit-game.yml), or `submissions/*.json` (copy `submissions/examples/example-pc.json` / `example-switch.json` and fill them in per [schema.json](../submissions/schema.json)); the web library toolbar's "Submit Game" button opens the issue template directly.

**Commands**:

```bash
make validate-submissions                  # equivalent to python3 scripts/validate_submissions.py
python scripts/validate_submissions.py --json
python scripts/merge_submissions.py --dry-run          # dry-run by default, writes no files
python scripts/merge_submissions.py --apply            # writes the CSV + moves JSON to submissions/merged/
python scripts/merge_submissions.py --apply --json
python -m pytest tests/test_submissions.py -q
make validate-catalog                      # run the catalog health check after merging
```

**Validation rules** (`py_modules/submission.py`; see the source/README for details):

- Platform aliases: `windows/win→pc`, `ns→switch`, `3d→3ds`, `psx/playstation→ps1`, `genesis→md`, etc.; only the 11 platforms are ultimately accepted;
- Required: `name/platform/share_url/openpath`; `openpath` must be a relative path within the share and must not contain `..`;
- `share_url` supports Tianyi `https://cloud.189.cn/...` (`/t/<shareCode>`, `/web/share?code=`) or Baidu share links; `access_code` is 4–8 letters/digits (may be empty if the link already has `pwd=`);
- `filesize_z` is a non-negative integer; `executable_name` is PC-only (leaving it empty for emulators only produces a warning);
- Duplicate shareCode: checked against both existing catalog CSV rows and other submissions in the batch; a duplicate is an ERROR;
- Validation passes when there are no `submissions/*.json` files (CI does not go red).

**Merge behavior**: files are written only when the whole batch has no ERROR; `--apply` atomically replaces the CSV using a temporary file + `os.replace`, `game_id` is the current maximum + 1, the title is `中文/英文` (Chinese/English), `server="t"`, the `pwd` is appended to `down_url`, and `category_parent` defaults to 5; on success the JSON files move to `submissions/merged/` and `submissions/merged/index.json` is appended.

**CI**: the `Validate game submissions` step in `.github/workflows/ci.yml` runs `python scripts/validate_submissions.py --catalog ...`; it also passes when there are no submissions.

### 6.11 Baidu Netdisk (QR/Cookie primary path, v0.17.0; optional OpenAPI fallback)

**Modules**: `py_modules/baidu_qr.py` (Passport QR), `py_modules/baidu_client.py` (Cookie share resolution/direct links), `py_modules/baidu_openapi_client.py` (OpenAPI fallback). The service layer's `_share_provider()` recognizes Baidu links; install plans **prefer Cookie, then OpenAPI, then prompt for QR scan**. **No CDP/web-interface reverse engineering is used**.

**QR login (recommended via QAM)**:

1. QAM "Baidu Netdisk (QR login)" → "Log in to Baidu Netdisk by QR code"; the plugin requests `https://passport.baidu.com/v2/api/getqrcode?lp=pc&qrloginfrom=pc` and displays the QR code (`data:image/png;base64`, session kept in memory for 180s);
2. Scan it with the Baidu App / Baidu Netdisk App; QAM goes waiting→scanned (scanned, awaiting confirmation)→success;
3. On success the Cookie is written to `baidu_login` in `state.json` (`BDUSS=...; STOKEN=...; PTOKEN=...`) and Baidu shares can be installed; "Log out of Baidu Netdisk" clears it.

**Click feedback and timeouts (v0.23.0)**: clicking "Log in to Baidu Netdisk by QR code" immediately shows the toast "Fetching Baidu QR code..."; the frontend uses `withTimeout` (start 20s, poll 15s), the backend uses `wait_for(request_qr, 12)` + image `wait_for(..., 10)`, and a timeout prompts "Timed out fetching the Baidu QR code (network/TLS may be blocked...)". To reproduce/troubleshoot: check `Baidu QR start requested`, `Baidu QR ready sign_len=`, `Baidu QR request timed out`/`failed` in `/tmp/freedeckcy.log`; only the sign length is logged, never the sign/cookie. For frontend timeouts check the QAM toast and the `withTimeout` message.

**QR scan error diagnostics (v0.18.0)**:

- `request_qr()` requests `getqrcode` directly; since v0.19.1 aiohttp tries the system certificate store first, then skips certificate verification, and falls back to urllib if that still fails (aiohttp TLS is unavailable in some Decky/SteamOS environments); since v0.19.2 `fetch_qr_image/poll_qr/complete_login` perform the same TLS fallback; error messages include the concrete exception type / HTTP status / response snippet;
- For non-200 HTTP responses the error message carries the status code/response snippet (e.g. `获取百度二维码 HTTP 403: ...`); when polling hits HTTP ≥ 400 or a **non-timeout** error such as connection reset/DNS/SSL, it returns `status=error`, the service layer converts it to `stage=failed` and shows the concrete reason in QAM instead of waiting forever; timeouts are still treated as waiting;
- Exceptions in `start_baidu_qr_login` are logged as `Baidu QR request failed: ...` and return "Failed to fetch Baidu QR code: <reason>"; the `stage` of `poll_baidu_qr_login` can be waiting/scanned/success/expired/failed;
- Debugging: check the QAM QR area/prompt, the `Baidu QR` keyword in `/tmp/freedeckcy.log`, and the `stage/message` returned by `/api/tianyi/baidu/qr/poll`.

HTTP/manual debugging (without QAM):

```bash
curl -s -X POST http://127.0.0.1:59271/api/tianyi/baidu/qr/start | python3 -m json.tool
# returns qr_data_url / qrcode_url / expires_at
curl -s http://127.0.0.1:59271/api/tianyi/baidu/qr/poll | python3 -m json.tool
# stage: waiting / scanned / success / expired / failed
curl -s -X POST http://127.0.0.1:59271/api/tianyi/baidu/qr/cancel
curl -s -X POST http://127.0.0.1:59271/api/tianyi/baidu/clear
```

Low-level endpoints (for debugging; `sign`/`v` come from the previous step):

```bash
# 1) fetch the QR code
curl -s 'https://passport.baidu.com/v2/api/getqrcode?lp=pc&qrloginfrom=pc' | python3 -m json.tool
# 2) poll (channel_id is the sign; long polling; an empty response/errno=1 means waiting)
curl -s 'https://passport.baidu.com/channel/unicast?channel_id=<sign>&tpl=pp&tt=<ms>' 
# 3) after confirming on the phone, exchange the returned v for a Cookie
curl -s 'https://passport.baidu.com/v3/login/main/qrbdusslogin?bduss=<v>&qrcode=1&tpl=pp&apiver=v3&tt=<ms>&time=<ms>&alg=v3&elapsed=1'
```

**Confirm the Cookie works**:

```bash
curl -s http://127.0.0.1:59271/api/tianyi/settings | python3 -m json.tool | grep -A3 baidu_login
# state.json should contain baidu_login.cookie (take care not to share it; the file is 0600)
# prepare a Baidu share → the install plan should return provider="baidu" and no longer require the Open Platform App Key
```

Tasks carry the Baidu Cookie + `Referer=https://pan.baidu.com/disk/home` + `UA=pan.baidu.com`; retries/re-downloads fetch a fresh direct link.

**OpenAPI fallback (optional, requires developer credentials)**: in QAM "Baidu Netdisk OpenAPI (optional)" fill in the App Key/Secret → get the authorization link → paste the authorization code; or use the env vars `FREEDECKCY_BAIDU_OPENAPI_APP_KEY` / `SECRET_KEY` / `REFRESH_TOKEN`. This path is used **only when there is no Cookie**, and share files must be transferred to `/FreedeckTmp` (cleaned up after installation).

**Tests/mocks**: `python -m pytest tests/test_baidu_integration.py tests/test_baidu_openapi_client.py tests/test_baidu_client.py -q`; the QR tests mock `request_qr`/`fetch_qr_image`/`poll_qr`/`complete_login` and never access the real Baidu.

**Troubleshooting**:

| Symptom | Handling |
|---|---|
| QR code not shown / fetch failed | Check the `/baidu/qr/start` response; the network must be able to reach `passport.baidu.com`; if the image download fails, open the returned `qrcode_url` manually |
| Stuck in waiting | The phone has not scanned the code / is not logged into the Baidu App; refresh the QR code and retry; long-poll timeouts are normal behavior |
| Failed/expired after scanned | The QR code expired after 180s or the phone did not confirm; scan again; check the failure info in the poll response |
| Scan succeeded but installing still says not logged in | Verify that `baidu_login.cookie` in `state.json` contains `BDUSS=`; `baidu_login.logged_in` in `/api/tianyi/settings` should be true; if necessary clear it and scan again |
| Cookie invalid / direct link 403 | Cookie expired/risk-controlled; scan again; aria2 already sends the Baidu Cookie/Referer/UA, so a 403 is usually an expired direct link/risk control |
| Want to use OpenAPI instead of scanning | Clear the Baidu login in QAM (or do not scan), then configure and authorize the OpenAPI app; install plans fall back to OpenAPI when there is no Cookie |
| Why not CDP | Web interfaces are not reverse-engineered; the Cookie is obtained only through the official Baidu Passport QR flow (`getqrcode/unicast/qrbdusslogin`) |

### 6.12 Scanning Installed Games (v0.18.0; entry moved and Steam auto-recovery in v0.21.0)

**Purpose**: when the plugin is reinstalled / state is lost / a game is from an old version or installed manually, add games already present in `settings.install_dir` back to the "Installed" list and automatically recover their Steam shortcuts. **Since v0.21.0 the entry is QAM Settings → Install → "Scan installed games"** (the native library's Installed page no longer has a scan button; the web library button is kept as a fallback).

**Command/API**:

```bash
curl -s -X POST http://127.0.0.1:59271/api/tianyi/installed/scan | python3 -m json.tool
# returns: scanned / added_count / added_games / skipped_count / unresolved_count / unresolved_dirs / installed_total / message
```

In the QAM settings page click "Scan installed games" (`onScanInstalledSettings`); the toast shows "Recovered N game(s)... (auto-added to Steam: M)"; the web library's Installed toolbar "Scan installed" (`scanInstalled()` in `app.js`) serves as the fallback.

**Matching rules**:

- Only **one level of subdirectories** under `settings.install_dir` is scanned (up to 500 entries), skipping hidden directories and `compatdata/steamapps/downloads/lost+found/.freedeckcy/.cache`;
- Directory names are normalized by `_normalize_scan_title()` (lowercase, strip separators) and compared with catalog entry titles (split on `[/|｜]`) by equality/prefix match, taking the longest; an already-recorded path → `already_recorded`, an already-recorded game_id → `game_id_recorded`;
- A matching Steam shortcut (`list_all_shortcuts_sync()`'s normalized app_name / same-exe realpath) backfills `steam_app_id` without adding a duplicate; emulator platforms use `find_rom_file()` to find the ROM (a record is still created if not found, with an empty `rom_path`);
- **Automatically created when a shortcut is missing** (v0.21.0):
  - PC: `_find_scanned_executable()` prefers the `.exe` from `entry.openpath`, otherwise recursively finds `.exe` files (excluding `unins/setup/redist/vcredist/crashreport/dxsetup`, sorted by title/directory name/size), then calls `add_or_update_tianyi_shortcut()`;
  - Emulator: `ensure_emulator(platform, allow_download=False)` (**no automatic download**) + `create_launch_wrapper()` generates `launch-freedeckcy.sh` and registers a native shortcut (Proton=none); if the emulator is not installed, records `shortcut_error=emulator_not_ready: ...`, and if the ROM is not found, records `rom_not_found`;
  - **Second pass**: existing PC records with `steam_app_id=0` are also recovered, with results in `steam_recovered`;
- Return fields: `added_count/added_games` (each containing `steam_added`/`shortcut_error`), `steam_recovered_count/steam_recovered`, `skipped_count/unresolved_dirs/installed_total/message`;
- Unmatched entries go into `unresolved_dirs` with reasons `catalog_no_match`/`catalog_missing_game_id`.

**Checking Steam shortcuts manually**: `shortcuts.vdf` is at `<Steam>/userdata/<id>/config/shortcuts.vdf` (binary VDF; the plugin backs up before writing and reads back after writing); search the log for `扫描补 Steam 快捷方式失败` (failed to add Steam shortcut during scan). **New shortcuts only become visible after restarting Steam / switching users / reopening the library page** — the plugin only writes the files and does not restart Steam.

**Troubleshooting/logs**:

- Nothing added after scanning: verify the install directory setting is correct, the game directory name matches the catalog title (renamed/English-name differences produce no_match), it is not a nested directory, and it is not a 0-byte directory;
- To confirm runtime details: check the `scan`/`已安装` (installed) keywords in `/tmp/freedeckcy.log` and the counts returned by the API;
- Scanning **only recovers records** and does not create Steam shortcuts; missing shortcuts require reinstalling/re-registering.

### 6.13 Storage Location Selection (SD card, v0.19.0)

**Purpose**: switch the download/install directories to the SD card/external storage with one click.

**Command/API**:

```bash
curl -s http://127.0.0.1:59271/api/tianyi/storage/options | python3 -m json.tool
# data.internal / data.external[] / data.options[] / data.download_dir / data.install_dir
# external entries: kind/label/mount/download_dir/install_dir/free_text/total_text/...
python -m pytest tests/test_storage_options.py -q
```

QAM "Settings → Paths": under the download/install directories, entries are rendered per external mount, such as "Download to SD card / external: <label> (X free)" and "Install to ... (X free)"; clicking them switches and refreshes via `savePatch`; when there is no external storage it shows "No writable SD card/external storage detected (please mount it in SteamOS/system first)"; the original "Select download directory/install directory" options are kept.

**Detection rules** (`storage_options.detect_storage_options`):

- Parses `/proc/mounts` (escapes such as `\040` are unescaped); candidate prefixes `/run/media/`, `/media/`, `/mnt/`, `/storage/`, `/sdcard`;
- Skips system fstypes such as `proc/sysfs/tmpfs/overlay/squashfs` and the mount roots `/`, `/run`, `/mnt`, `/media`, `/storage`, `/sdcard`;
- Entries must exist, be writable, and have a non-zero total in `disk_usage` to be included; deduped by realpath; capacity comes from `shutil.disk_usage`;
- Suggested external directories: `<mount>/freedeckCY/downloads`, `<mount>/freedeckCY/installed`; internal: `~/Downloads/freedeckCY`, `~/Games/freedeckCY`.

**Common issues**:

| Symptom | Handling |
|---|---|
| SD card not shown | Confirm it is mounted in SteamOS/system (`/run/media/...`) and writable, and visible in `/proc/mounts`; read-only/unmounted cards do not appear |
| `/mnt` filtered out | The mount root itself (`/mnt`) is skipped, but submounts such as `/mnt/sdcard` do appear; check manually with `mount | grep /mnt` |
| After switching, the path does not exist / is not writable | The plugin does not mkdir/mount/format automatically; first confirm the mount point is writable, and if necessary run `mkdir -p <mount>/freedeckCY/{downloads,installed}` manually |
| Capacity looks wrong | Capacity is a snapshot taken at detection time; reopen the paths page / reload the plugin to refresh |

### 6.14 Decky Native Game Library and Steam Deck Input (v0.20.0; v0.27.20)

**Entry**: QAM home "Game Library" → `Router.CloseSideMenus()` → `showModal(<LibraryPage />)`; only if the modal fails does it `Navigation.Navigate("/freedeckcy/library")`. `routerHook.addRoute` still registers the fullscreen entry, removed on unload. The legacy Vue web library is only for desktop debugging/fallback.

**Page structure (v0.27.20)**:

- Top bar: Back / Steam Library / title / Game Library / Installed / Refresh (normal flow, not sticky).
- Search: placeholder "Search games" + Search / Filter buttons; the filter panel contains platform/category/sort chips.
- By default a Hero + Recently Updated + horizontal category shelves; after searching/filtering a cover grid is shown; cards carry source/installed badges.
- Details: `GameDetailModal` + `showModal`; download-source selection and a fixed "Install/Exit" action bar.
- 30 items per page + "Load more"; cards in the Installed tab support launch/folder/uninstall.
- QAM no longer shows the `QAM 原生 UI v...` marker; the version follows the Decky plugin list and `package.json`.

**Gamepad/trackpad (v0.27)**:

| Input | Behavior |
|---|---|
| D-pad / left stick | Left/right/up/down movement within `flow-children` groups; the focused card scrolls into view automatically |
| A | Activates the current button/card/filter chip |
| B | Closes details; exits within the game library (`onCancel`) |
| L1/R1 | Switch between "Game Library / Installed" |
| L2/R2 | Scroll the library/detail content by about 0.8 screen |
| Trackpad / touch | Scrolls vertical lists and horizontal shelves; buttons/cards are clickable |
| Search box | Focus with A, then type; Enter submits |

**Layout debugging notes**:

- A fixed 60px mask at the top → cards use `scroll-margin-top:84px` so the top of the focused card / blue focus ring is not clipped.
- Shelves with `overflow-x:auto` + focus `outline:2px` → top/left/right padding 10/16px, with scroll-snap/overflow-anchor removed, so the focus ring of the leftmost card is not clipped.
- The details dialog uses `margin-top:40px` to clear the status bar, `max-height:calc(100vh - 150px)`, and a separately fixed action bar at the bottom.
- The search box must use a placeholder (not a label) so that the search/filter buttons are the same height as the input.
- Use DialogButton + a Focusable row for update buttons, not two separate ButtonItems.

**On-device CEF verification** (Steam Deck, CEF 8081):

```bash
# list targets; select "Steam Big Picture Mode"
curl -s http://<deck-ip>:8081/json/list
# Runtime.evaluate on the target page:
# document.querySelector('.gpfocus') / '.fdc-root' / '.fdc-shelf'
# send ArrowUp/Down/Left/Right with Input.dispatchKeyEvent to verify the focus ring
```

Checklist:

1. The focus ring of the leftmost card is complete on both sides;
2. The focused card's top blue frame/cover is not clipped by the status bar;
3. A/B/left/right/up/down all work;
4. The details "Install/Exit" buttons are fully visible;
5. The search/filter/update buttons are on the same row.

**callable**: `list_tianyi_catalog`, `prepare_tianyi_install`, `start_tianyi_install`, `list_tianyi_installed_games`, `launch_tianyi_installed_game`, `open_tianyi_installed_folder`, `scan_tianyi_installed_games`.

**Common issues**:

| Symptom | Handling |
|---|---|
| Clicking "Game Library" still opens the web page / shows nothing | Verify the plugin version is ≥0.27.20, the frontend dist has been updated, and Decky has been reloaded; the fallback goes to the fullscreen route |
| Left/right keys don't move focus | Check whether the horizontal area has `DFL.Focusable flow-children="row"`; a plain div is not enough |
| Leftmost card focus ring clipped | The shelf needs `padding-left:16px`, `scroll-snap-type:none`, `overflow-anchor:none`; focus cards with custom nearest-visible scrolling, not `inline:"center"` |
| Top blue frame/cover clipped | Shelf top padding 10px, cards `scroll-margin-top:84px` |
| Detail buttons clipped/overflowing | Details `margin-top:40px`, `max-height:calc(100vh - 150px)`, and the content scroll area separated from the action bar |
| B does nothing | The details root node must be `DFL.Focusable onCancel=...`; the library root node also has onCancel |
| Update buttons misaligned / left-right doesn't work | The two buttons must share one `Focusable flow-children="row"` + DialogButton, not two ButtonItems |
| Search/filter buttons sit lower | Use a placeholder in the search box, not a label; buttons use `align-items:center` |

### 6.14.1 Bilingual UI Debugging (v0.28.14)

- Language key: `localStorage["freedeckcy.language"]`, value `zh` or `en`; on first open with no value, the language picker is shown first.
- Reset the language for retesting: run `localStorage.removeItem("freedeckcy.language")` in CEF, then reload the plugin.
- Translation scope: root nodes carrying `data-fdc-i18n` (QAM content, settings, native library, details); remember to add the attribute when creating a new root node, otherwise it will not be translated.
- After changing copy, update the corresponding key in `src/i18n.en.ts`; run `pnpm build` and reload the plugin.
- Debugging: in CEF run `localStorage.setItem("freedeckcy.language","en")` + reload, then check the four places: QAM/settings/game library/details.
- Language switches are available on both the QAM home page and Settings; switching applies immediately (translate/restore).
- Diagnostic attribute: `document.documentElement[data-fdc-i18n-observer]` should be `ready`; if absent, check whether `useI18nRoot` is attached to the real root node and whether the root's `ownerDocument` is the QAM/BigPicture document.
- Toasts: `toaster.toast` translates title/body, so update-check/download/diagnostics popups should be English.
- Glossary has 434 entries (`src/i18n.en.ts` + `src/i18n.missing.ts`); after adding Chinese UI, add glossary entries at the same time, otherwise only the phrase fallback applies.

### 6.15 Diagnostics Self-Check (v0.22.0)

**QAM Settings → Diagnostics**: "Run self-check" calls the callable `run_tianyi_diagnostics`; "Export diagnostics bundle" calls `export_tianyi_diagnostics_file` (writes to the download directory and toasts the path).

**Command/API**:

```bash
curl -s -X POST http://127.0.0.1:59271/api/tianyi/diagnostics/run | python3 -m json.tool
# returns version/arch/summary{ok,warn,fail,skip}/checks[{id,label,status,detail,fix}]
```

**Checks**: plugin (version/directory), state_dir (writable/permissions), download_dir/install_dir (exists/writable/free space; <2GB is a warn), runtime_aria2/7z/node (exists + executable + `--version`/`i`, 5s), catalog (count/platforms/covers), steam (root + `list_all_shortcuts_sync` count), storage (SD/external mounts), network_tianyi (GET cloud.189.cn), baidu_qr (`request_qr()` for 12s, only outputs the sign length), tasks (failed/installed), log (count of ERROR/Exception/失败 in the last 300 lines).

**Export bundle** (`export_diagnostics_to_downloads`): `diagnostics.json` + `self-check.json` + `log-tail.txt` + `README.txt`, written to `settings.download_dir` (if empty, the plugin downloads directory, then `~/Downloads`), file name `freedeckcy-diagnostics-YYYYmmdd-HHMMSS.zip`, permissions 0600.

**Common failure items**:

| Check | Handling |
|---|---|
| runtime_* fail | `defaults/runtime/<component>/<arch>/` inside the package is missing/not executable; reinstall the plugin package, or run `make runtime` and repackage |
| steam warn/fail | Steam not logged in / `userdata` unreadable; verify that `FREEDECKCY_STEAM_ROOT` points to the running client |
| state_dir fail | `~/.local/share/freedeckCY` permissions/disk; fix and rerun |
| download/install warn | Less than 2GB free or not writable; free space / switch SD card / choose another directory |
| baidu_qr fail | Network/DNS/certificate; v0.19.2+ has a TLS fallback; check the exception type in detail |
| network_tianyi warn | Network/proxy/DNS; local features are unaffected, but installation requires network access |

**Tests**: `python -m pytest tests/test_diagnostics.py -q` (`include_network=False` structural cases); the self-check does not auto-repair.

### 6.16 Library Page Playtime Block Isolation (v0.25.0)

**Goal**: Steam's native game details pages no longer show freedeckCY's "Played / Main Story / Total" block; only games installed/recovered by the plugin show it.

**Verification method**:

1. **Steam's own games**: open the details page of a Steam game not installed by freedeckCY → the playtime block should not appear (nor should a brief "Loading");
2. **Plugin-installed games**: open the details page of a game installed/recorded via install/scan → the "My Playtime / Main Story / Total" block should appear;
3. **API layer**: `get_library_game_time_stats(app_id=<native game>, title=...)` should return `managed=false`, `reason="not_managed"`, all values 0, and no HLTB query in the log; `app_id=<plugin game>` returns `managed=true`.

**Match order**: `_resolve_installed_record_by_app_id()` does an exact AppID match first → only if that misses does it normalize by title (`_normalize_cover_text`, bidirectional containment); AppID takes priority to avoid misjudging same-named Steam games.

**Tests**: `python -m pytest tests/test_diagnostics.py -q` (`test_library_time_stats_unmanaged_games_get_no_hltb`: unmanaged → `managed=false` and no HLTB query).

**Troubleshooting**: the block still appears for native games → verify the frontend `dist` is v0.25.0+ and whether the Steam library page caches the old patch (restart Steam/reload the plugin); the block does not appear for plugin games → check whether the game is in `installed_games` and whether the AppID/title matches; an HLTB query failure only affects the values inside the block.

---

## 7. Common Troubleshooting---

## 7. Common Troubleshooting

| Symptom | Cause / Handling |
|---|---|
| Download reports **"download component unavailable: no bundled aria2c or system aria2c found"** | aria2c is missing. Run `make runtime` (or `bash scripts/fetch_runtime.sh --only aria2`), or install the system aria2; you can also point `FREEDECKCY_ARIA2_BIN` at a path. Check whether `defaults/runtime/aria2/<arch>/aria2c` is executable |
| Extraction reports **"extraction component unavailable"** | 7zz is missing. Run `make runtime` (or `--only 7z`), or install the system 7z; you can also point `FREEDECKCY_7Z_BIN` at a path |
| Cloud save reports **missing node / node runtime not found** | Run `bash scripts/fetch_runtime.sh --only node` (equivalent to fetching only node; `make runtime` fetches all); or install node ≥ 18, or point `FREEDECKCY_NODE_BIN` at a path. Note that cloud-save upload **always goes through node**, and SteamOS does not ship node by default |
| After installation the game is **not in the Steam library** | ① You must **restart Steam** after `shortcuts.vdf` is written; ② if Steam was running during installation, exiting Steam may write back and overwrite `shortcuts.vdf` — reinstall the game once (a pre-write backup is at `shortcuts.vdf.freedeckcy-bak-<timestamp>`, which can be restored manually); ③ open `/tmp/freedeckcy.log` and search for `Steam 导入失败` (Steam import failed) or `回读校验失败` (read-back verification failed) for the concrete reason; ④ on multi-drive / Flatpak setups, use `FREEDECKCY_STEAM_ROOT` to specify the root directory |
| After installation, clicking launch **does nothing** | exe resolution is heuristic (openpath → leaf-name search → first executable in the directory). Check whether the exe in the install directory is correct; if necessary change `openpath` in the CSV or edit the Steam target manually |
| **Port 59271 is in use** | The local service fails to start and reports "port already in use". First find the occupying process: `ss -ltnp \| grep 59271`; commonly the previous plugin instance did not exit cleanly — reload/restart the plugin; or stop the other occupying process |
| **Games on the SD card / second drive are not recognized** | The current version scans `libraryfolders.vdf` and Flatpak paths; if it still fails: ① confirm `steamapps/compatdata/<appid>/pfx` exists on the target drive; ② specify the Steam root with `FREEDECKCY_STEAM_ROOT`; ③ look for `读取 libraryfolders.vdf 失败` (failed to read libraryfolders.vdf) in the log |
| Cloud-save restore overwrote the wrong thing / want to roll back | Restore first renames the same-named file/directory to `*.freedeckcy-bak-<YYmmdd_HHMMSS>`; just rename it back manually in the corresponding directory |
| After uninstall the **Proton prefix still takes up disk space** | Uninstall deletes only the game files by default. When uninstalling again, choose "Also delete the Proton prefix" in the confirmation dialog; if the button does not appear, the AppID/prefix was not resolved (first check the Steam section of `make doctor` and `steam_app_id` in `state.json`) |
| Uninstall reports **Proton prefix path validation failed / only partially cleaned** | It only auto-deletes the `<library>/steamapps/compatdata/<appid>` structure; symlinks, cross-library leftovers, or AppID mismatches are skipped and explained in `warning`; verify manually and delete |
| Extraction reports **archive validation failed** | A `7z t` failure first quarantines the bad archive and automatically re-downloads once (once per task), then continues installing; if it fails again the task is marked failed — use the "Retry" button on the task row. Log keyword `Archive validation failed, re-download scheduled` |
| **7z not executable / validation skipped** | `7z t` is best-effort: if 7z cannot be found (or running a Linux 7zz on macOS reports `Exec format error`), it returns "validation skipped" and **does not block installation**; but real extraction still needs a working 7z, otherwise the extraction stage reports "extraction component unavailable" |
| Failed task **needs another try** | Task rows with `status=error` or `install_status=failed` have a "Retry" button: if the file is already complete it reinstalls directly (no re-download), otherwise it fetches a fresh direct link; failing to get a direct link usually means the login expired — log in by QR again first |
| After a plugin restart, **download tasks are stuck / marked failed** | A plugin reload usually attaches to the still-live aria2 (gid unchanged, see 6.4 Processes and Ports); after a **device reboot** the aria2 session is rebuilt and the gid changes. Recovery chain: re-claim the gid by file path → if the file is already complete, mark it complete → if the session is lost, replace the URI in place with `changeUri` on the original direct link / re-`addUri` (once per task per process) → only 5 consecutive failures mark it error. If it still fails: remove the task and re-download from the library page (resume supported) |
| Download completes but it **never installs** | The current version has background maintenance (runs once at startup, then every 8 s), so it progresses even without the QAM panel open. If stuck: ① for volume/multi-package cases **the whole group must be complete** before installing — check the other tasks with the same `group_id`; ② check `Maintenance` / extraction errors in the log; ③ tasks with `post_processed=false` and `status=complete` retry on the next maintenance; if necessary stop the plugin, set that field back to `false`, and reload to trigger it |
| Download completes but reports **"file size verification failed"** | The catalog's `file_size` does not match the actual on-disk size (incomplete download/file replaced). The current version self-heals once first: it quarantines the bad file as `*.freedeckcy-size-mismatch-<timestamp>` and re-downloads from the original direct link; only if that fails is it marked error — then remove the task and re-download. If it recurs, the files in the share have changed and the resource catalog needs updating |
| Extraction reports **"downloaded content looks like a web error page"** | When the Tianyi login expires, the direct link may return an HTML login page. The pre-check refuses to extract and prompts; log in by QR again, remove the task, and re-download |
| Extraction reports **"incomplete volumes, missing: …"** | The multi-volume archive is missing parts (e.g. only `.7z.001`, no `.002`). The whole group will not install; add/re-download the missing volumes as prompted (if the resource itself is missing parts, the catalog needs updating) |
| Reports **aria2 control-file error / file truncated** | A half-finished or corrupt old session. The code first quarantines the bad file (`*.freedeckcy-stale-<timestamp>`) and auto-retries once; if it still fails, remove the task and re-download |
| Multi-volume game **volumes not recognized** | Only the 6 common naming schemes are supported; non-standard names are treated as ordinary files. Rename the volumes to a standard form manually, or file an issue (see ROADMAP "7z t validation/archive detection enhancement") |
| **Only part of the volumes/multi-package downloaded before an error** | When one package in the group is in `error` state, the whole group will not install, and completed volumes report "a volume download failed in the same install plan; remove the failed task to continue installation". After removing the failed task, the remaining volumes continue installing automatically; if the failure is at the extraction stage, already-extracted files are kept and re-initiated after removing the task |
| Library page **does not show the platform filter row** | The platform row appears only when the number of `platforms` is > 1; confirm it is loading `freedeckcy_catalog.csv` (7084 entries / 11 platforms) rather than the fallback old catalog (all PC). Check the log for `已加载游戏目录 total=… platforms=…` (game catalog loaded) or inspect the `platforms` field with `curl '127.0.0.1:59271/api/tianyi/catalog?q=&page=1'` |
| **QAM game library won't open / list not shown** | Since v0.20.0 the game library is the native route `/freedeckcy/library`; verify the plugin is reloaded and the Decky log has no route errors; if the list is empty, check catalog loading and filter parameters; install progress is shown in the home page task area |
| **SD card/external storage doesn't appear** | Only mounted and writable submounts under `/run/media`, `/media`, `/mnt`, `/storage`, `/sdcard` are shown; mount roots are skipped; read-only/unmounted entries do not show; check `external` from `curl /api/tianyi/storage/options` and `/proc/mounts` |
| **Scan installed did not recover games / add Steam shortcuts** | Since v0.21.0 the entry is Settings → Install; it scans only one level under `settings.install_dir`, and directory names must match titles (renames may produce `catalog_no_match`); PC exe lookup failures give `exe_not_found`, emulator-not-installed gives `emulator_not_ready` (no automatic download), and missing ROM gives `rom_not_found`; check the returned `unresolved_dirs`/`steam_added`/`steam_recovered_count`; Steam must be restarted / user switched / library page reopened to show new shortcuts |
| **Baidu QR scan errors / stuck in waiting** | Since v0.18.0 errors carry the HTTP status/reason (`stage=failed`); check the QAM prompt and `Baidu QR` in `/tmp/freedeckcy.log`; the network must reach `passport.baidu.com`; the QR code expires after 180s; retry or switch to the OpenAPI fallback |
| **Clicking a non-PC card only shows a prompt and cannot install** | Platforms with official packages for the current architecture (x86_64: 10; aarch64: GBA/PSP/NDS/PS1/FC/MD/Switch) should install normally (see §6.8); otherwise it is expected: 3DS/PS2/PS3 have no official package on aarch64 and are hidden by the catalog allowlist/rejected by the backend. Errors are usually a missing emulator, a ROM name mismatch, or unconfigured BIOS/setup files |
| In the catalog, **`/web/share?code=` links are not loaded** | Since v0.3.0 both `_is_valid_tianyi_url()` and `tianyi_client.parse_share_url()` support this form; check that the link carries `code=` and the domain is `cloud.189.cn`. Old-version catalogs require a plugin reload to take effect |
| **Launching from a card in the Installed tab fails** | ① Check the toast: `该游戏缺少 Steam AppID` (the game lacks a Steam AppID) means the record has no appid — launch it manually from the Steam library; ② `当前环境没有 xdg-open/gio` (no xdg-open/gio in this environment) means the backend cannot spawn an external program (the DroidDeck desktop needs xdg-open); ③ use `curl /api/tianyi/installed` to confirm `steam_appid` and `exists` |
| **Auto cloud save did not trigger** | ① Confirm the `cloud_save_auto_upload` setting is true (QAM switch/settings API); ② a logged-in Tianyi account is required and there must be no upload task in progress; ③ gamewatch needs the process command line to contain install_path (a custom wrapper may not satisfy this; when the container has no `/proc` it falls back to `pgrep -f`, which requires pgrep on the system); ④ auto-upload has a 30 s debounce, so when several games exit in a row only the first uploads immediately; ⑤ check the log for `auto cloud save upload after exit` / `gamewatch poll failed` |
| **Emulator saves not uploaded / not found** | Check `diagnostics.collect[*].diagnostics.emulator_saves.reason` in the upload state: `save_dir_missing` (not installed into the standard/portable directory), `game_save_not_found` (GBA/FC/MD/NDS must match the ROM name; renames/custom save names will not match), `emulator_saves_shared` (the shared memory card was already uploaded by a previous game), `emulator_saves_disabled` (switch off); confirm QAM "Include emulator saves" is on |
| **Emulator save restore target is not in the whitelist** | Restores can only go to platform standard/portable roots (`restore_roots`); cross-device 3DS may degrade to the root directory; do not manually point the manifest's `source_path` to other HOME locations — the plugin rejects it / redirects it to the first root |
| **Restoring a shared memory card overwrote other games** | PS1/PS2 single memory cards and Switch directories cannot be split per game; restore overwrites the whole card/directory, creates `*.freedeckcy-bak-<timestamp>` before overwriting, and conflicts require confirmation; back up/verify before restoring |
| **PS1 m3u order wrong / not generated** | An existing `.m3u` takes priority and is not overwritten; only when absent and there are multiple `.cue/.chd` files is `freedeckcy-multidisc.m3u` generated (natural filename sort); a single disc does not generate one. If the order is wrong, edit it manually or delete it so the plugin regenerates it |
| **3DS title id unreadable / not split** | Only `.3ds/.cci/.cxi` with the NCSD header at `0x100` are supported; if it cannot be read it falls back to the shared `title` directory (not an error). Check `xxd -s 0x100 -l 16` and whether `.../title/00040000/<low8>/` exists |
| **3DS/Switch uploads are large / slow** | These two platforms use shared title directories (`sdmc`/`nand/user/save`), which can be large; turn off "Include emulator saves" or clean the directory manually and retry; the fingerprint covers at most 5000 files |
| **Upload skipped (reason=unchanged)** | The save fingerprint matches the last upload (relative path + size + mtime unchanged). This is expected when nothing changed; to force an upload: exit the plugin, delete the `cloud_save_fingerprints` entry for that game in `state.json` (or delete the whole field), then reload the plugin |
| **Ludusavi manifest missed (falls back to proton_prefix/install_fallback)** | ① Confirm `defaults/ludusavi/manifest.json.gz` exists (`make ludusavi-manifest`; shipped in release packages); ② check `ludusavi.matched/path_count` and `source_strategy` in the upload-state `diagnostics.collect`; ③ when titles differ a lot, only Steam AppID matching can help (first check whether the shortcut resolves an appid); ④ when covers/titles contain special characters, `normalize_title()` strips non-alphanumeric/CJK characters |
| **Submission validation reports unsupported platform** | Only `pc/gba/psp/nds/ps1/fc/md/3ds/ps2/ps3/switch` are supported; aliases only accept common spellings (windows→pc, ns→switch, 3d→3ds, psx→ps1, etc.), other spellings fail directly. Fix `platform` in the JSON and rerun `make validate-submissions` |
| **Submission validation reports the link is not cloud.189.cn** | `share_url` supports Tianyi `https://cloud.189.cn/...` (`/t/<shareCode>`, `/web/share?code=`) or Baidu share links (`pan.baidu.com`); for other domains/short links, first expand them into the corresponding cloud drive's original share link |
| **openpath missing/contains ..** | `openpath` is the relative path of the game file or archive under the share root (e.g. `Stardew Valley/Stardew Valley.7z`); it must not start with `/` or contain `..`; the installer uses it to page through the share and locate the file |
| **Submission reports duplicate shareCode** | The same share link already exists in the catalog CSV or another JSON in this batch; use `python scripts/validate_submissions.py --json` to see the specific shareCode, then change the link or remove the duplicate file |
| **Some diagnostics self-check items fail** | Settings → Diagnostics "Run self-check" shows status/detail/fix; runtime_* checks `defaults/runtime/<component>/<arch>/` inside the package, steam checks login/`FREEDECKCY_STEAM_ROOT`, network/baidu_qr check connectivity; the self-check does not auto-repair |
| **Export diagnostics does nothing/download fails** | The diagnostics zip is downloaded by the browser via `GET /api/tianyi/diagnostics/export`; if the browser blocks the download, save it manually with `curl -s -OJ http://127.0.0.1:59271/api/tianyi/diagnostics/export`; if the endpoint itself fails, check the traceback in `/tmp/freedeckcy.log` |
| **Update check fails** | `update-check` depends on `api.github.com`: no network, a blocked proxy, or the unauthenticated GitHub API rate limit (60/hour/IP) all return `ok:false` + message; wait a bit or open the Release page manually; successful results are cached for 1 hour, so there is no need to click repeatedly |
| **GBA plan reports "mGBA not found"** | Since v0.10.0 GBA too is **downloaded automatically** at first install; on failure check the network/proxy first, or set `FREEDECKCY_MGBA_BIN=/path/to/mgba` to a system/manually provisioned mGBA, or install the Flatpak `io.mgba.mGBA`; the diagnostics `emulators.gba` shows available/source/message |
| **Downloading the official package during emulator installation fails/is very slow** | All 10 platforms (including GBA) access the GitHub release on first install (`api.github.com`/`objects.githubusercontent.com`); check the network/system proxy; reinstalling after a failure triggers the download again. You can point `FREEDECKCY_PPSSPP_BIN` / `FREEDECKCY_MELONDS_BIN` / `FREEDECKCY_DUCKSTATION_BIN` / `FREEDECKCY_MESEN_BIN` / `FREEDECKCY_MGBA_BIN` at system or manually downloaded packages in advance; the diagnostics show the platform's source/url/message |
| **Want fully offline emulator installation** | The plugin package contains no emulators. For offline use, manually put the official package under `~/.local/share/freedeckCY/emulators/<platform>/<arch>/` (AppImage `chmod +x`; zips can stay as-is), or point `FREEDECKCY_*_BIN` at a local executable/AppImage; PS1 additionally needs a user-supplied BIOS. When the cache already exists, no network download is attempted |
| **Emulator plan reports "ROM not found in share"** | The `openpath` filename in the catalog CSV does not match the filename inside the share (or the resource package was updated): verify the CSV/share filenames, matching case and extension (gba `.gba`; psp `.iso/.cso/.pbp/.elf`; nds `.nds/.dsi/.srl`; ps1 `.cue/.m3u/.chd/.iso/.pbp/.bin`; fc `.nes/.fds/.unf/.unif`; md `.md/.gen/.smd/.bin/.32x`); API errors include examples of the scanned files |
| **Emulator unpacking fails (AppImage / Mesen2 zip)** | AppImages run `--appimage-extract` on first use; Mesen2 is a single `Mesen` file inside a zip (executable directly after extraction, not via AppImage). On failure check the log and the permissions/space of `~/.local/share/freedeckCY/emulators/<state_key>/<arch>/`; delete that directory and retry, or point the corresponding `FREEDECKCY_*_BIN` at the already-extracted `squashfs-root/AppRun` / `Mesen`. An incomplete download (smaller than each platform's `min_bytes`) deletes the file and reports "<emulator> download incomplete" |
| **Clicking the emulator shortcut does not start it** | Check that `launch-freedeckcy.sh` and the ROM are both in the install directory (`find_rom_file` only recognizes the registry extensions); run `bash launch-freedeckcy.sh` manually; the Steam entry's Exe must be the script path, LaunchOptions must carry the token (used to locate it on uninstall), and Proton must have no mapping. Except for GBA, also confirm the first download/unpack finished; for PS1 check the BIOS (see below) |
| **3DS launch reports Flatpak not found / installation fails** | First confirm the system has `flatpak` (SteamOS ships it); manually run `flatpak remote-add --user --if-not-exists flathub ...` + `flatpak install -y --user flathub org.azahar_emu.Azahar`; if it still fails, retry/check the install message — the plugin falls back to the AppImage (or set `FREEDECKCY_AZAHAR_BIN` to a local AppImage) |
| **3DS crashes / black screen in Game Mode** | Confirm it is using the Flatpak (diagnostics `emulators.3ds.source=flatpak`); the wrapper should contain `QT_QPA_PLATFORM=xcb`/`SDL_VIDEODRIVER=x11`; old shortcuts are rewritten automatically in the background, or triggered by reinstalling/re-registering |
| **3DS system files not recognized** | Place them in `~/.local/share/freedeckCY/bios/3ds/sysdata/` (the whole directory); after installation they are copied to azahar/citra and the Flatpak's `~/.var/app/org.azahar_emu.Azahar/data/{azahar,azahar-emu}/sysdata`; confirm the target directories are non-empty |
| **PS1 black screen / reports no BIOS** | DuckStation requires a user-supplied BIOS: put `scph*.bin` into `~/.local/share/freedeckCY/bios/ps1/`; at install time it is copied to `~/.local/share/duckstation/bios/`; a missing BIOS **does not block installation** but warns, and the game may show a black screen at runtime. Check `emulators.ps1.bios_present/bios_dir` via `curl /api/tianyi/diagnostics`, or manually `cp -n ~/.local/share/freedeckCY/bios/ps1/*.bin ~/.local/share/duckstation/bios/` |
| **On DroidDeck / aarch64, 3DS/PS2/PS3 are not visible** | Expected behavior: official packages for these three platforms are x86_64 only, `available_platforms("aarch64")` returns only 7 platforms, and catalog queries filter by the allowlist, so neither the entries nor the platform filter rows appear; `emulator_status` returns "platform hidden". Using them on ARM requires an official arm64 package; environment variables cannot bypass this |
| **Where to put the PS2 BIOS / PCSX2 reports no BIOS** | Put `*.bin` (e.g. `scph39001.bin`) into `~/.local/share/freedeckCY/bios/ps2/`; at install time v0.12.0 deploys it to three places — `<AppDir>/bios`, `~/.local/share/PCSX2/bios`, and `~/.config/PCSX2/bios` — and writes `portable.ini` + `inis/PCSX2.ini` (`[Folders] Bios`/`[UI] Fullscreen`). You can also copy manually; check `emulators.ps2.bios_present/bios_dir` in diagnostics |
| **BIOS/firmware archive does not take effect** | Put the archive under `~/.local/share/freedeckCY/bios/<platform>/`; at install time 7zz extracts it to `_extracted/` in the same directory and then deploys it; confirm the system/plugin has 7zz (`FREEDECKCY_7Z_BIN`) — extraction failures are reported in the install message. If you only want to place files manually, put the already-extracted files directly under `bios/<platform>/` (extraction is skipped) |
| **BIOS path wrong / emulator still cannot find the BIOS** | The deployment targets are `<AppDir>/bios` (`squashfs-root/` after AppImage extraction) and each emulator's user directory; check `~/.local/share/freedeckCY/emulators/<state_key>/<arch>/squashfs-root/bios/`, `~/.local/share/duckstation/bios/`, `~/.local/share/PCSX2/bios/`, `~/.config/PCSX2/bios/`. When a portable config exists the emulator reads `<AppDir>/bios`, otherwise it reads the user directory |
| **PS3 firmware installation fails** | The firmware must be `bios/ps3/PS3UPDAT.PUP`; if `~/.config/rpcs3/dev_flash` is already non-empty the plugin skips it; on failure check the `--installfw` error in the install message, and run `rpcs3 --installfw <pup>` manually. If RPCS3 is not executable the plugin only prompts and does not install |
| **Switch keys/firmware not recognized** | Put `prod.keys`/`title.keys` under `bios/switch/`; at install time they are copied to `~/.local/share/eden/keys/`; put the firmware in an archive — the extracted `.nca` directories are deployed to `~/.local/share/eden/nand/system/Contents/registered/`; confirm the directories are non-empty and restart Eden if necessary |
| **3DS / PS3 / Switch cannot be played right after installation** | These platforms need user-supplied system files: 3DS needs Azahar system files, PS3 needs firmware (`PS3UPDAT.PUP`), and Switch needs `prod.keys` + firmware. The install message/library-page dialog carries `setup_hint`; configure them on the emulator's first launch as prompted — the plugin neither bundles nor downloads these files |
| **Mesen2 (FC/MD) does not start / arguments wrong** | Mesen2 is a single `Mesen` file inside a zip; its launch argument is `/fullscreen <rom>` (not `-f`); FC and MD share the `emulators/mesen/<arch>/` cache, so deleting the cache affects both. Check whether `cat launch-freedeckcy.sh` contains `exec <Mesen> /fullscreen <rom>` and try running it manually |
| **Why can't PS2/PS3/3DS/Switch be installed** | These platforms are integrated. On x86_64 they install (PS2 needs BIOS, 3DS needs system files, PS3 needs firmware, Switch needs keys); on aarch64 3DS/PS2/PS3 have no official arm64 package and are hidden by the catalog allowlist; Switch has an arm64 package available |
| **PSP/NDS/PS1/FC/MD saves not found / cannot manage saves** | Since v0.12.0 `bios/<platform>/` is deployed automatically; since v0.15.0 emulator saves are included in cloud-save upload; since v0.16.0 restore is supported; there is no standalone save-management UI |
| **After installing a game on DroidDeck, no shortcut appears in Steam** | DroidDeck may run two Steam clients at once: `~/.droiddeck-x64/.local/share/Steam` (x64) and `~/.local/share/Steam` (standard/ARM). The plugin prefers the running one (its `steam.pid` exists), but if it guesses wrong you can lock the target root with `FREEDECKCY_STEAM_ROOT`, then reinstall the game once and restart Steam; `GET /api/tianyi/settings` confirms `droiddeck_detected` |
| **Game won't launch / reports a missing compatibility tool (DroidDeck)** | ARM Proton is required: confirm `droiddeck-proton-arm64` (or version 11) is installed in Steam. The plugin writes `droiddeck-proton-arm64` by default; on a version mismatch use `FREEDECKCY_PROTON_TOOL=droiddeck-proton-11-arm64`, or set it to `none` and pick the compatibility tool manually in Steam; `proton_tool_resolved` in the `settings` API is the value actually written |
| **Download/extraction reports "binary not found" (ARM devices)** | `ls -l defaults/runtime/{aria2,7z,node}/aarch64/…` to check whether the arm64 runtimes are packed; if missing, run `make runtime ARCH=aarch64` and then `make package-droiddeck` again; you can also point `FREEDECKCY_ARIA2_BIN` / `FREEDECKCY_7Z_BIN` / `FREEDECKCY_NODE_BIN` at the system arm64 builds |
| **Platform names such as GBA / Switch appear** in the category filter row | Since v0.3.1 they are cleaned automatically at load time (`normalize_categories`), but it is still recommended to clean the data on disk: `make normalize-catalog` (`--check` shows the differences first); CI's `validate_catalog --strict` fails on "platform names mixed into categories" |
| `make validate-catalog` reports **duplicate game_id / invalid links / empty titles** | Fix `freedeckcy_catalog.csv` per the reported rows: merge duplicate ids or change the id; links may only be `cloud.189.cn/t/…` or `cloud.189.cn/web/share?code=…`; fill in empty titles. Rerun `make validate-catalog` after fixing |
| Cover index **misses (covers still rely on online resolution)** | ① Confirm `cover_index.csv` exists in the repository/path is correct; ② the index matches by `game_id` or title, and the title must match the catalog (compared after whitespace normalization); ③ delete `cover_cache.json` and reload the plugin so the new index takes effect |
| Cover **not shown / shows the wrong image** | ① Check whether `cover_index.csv` exists and whether the header contains `game_id` or `title` (the file is optional; if absent, online resolution is used); ② a wrong `steam_appid` synthesizes a wrong CDN image — delete that row or fix the appid; ③ a failed online resolution writes a 30-minute negative cache; delete `~/.local/share/freedeckCY/tianyi/cover_cache.json` and reload the plugin to retry immediately |
| Changed the cover index but **it does not take effect** | The index is merged only when `initialize()` loads the catalog; it takes effect after reloading the plugin (or re-entering the plugin). Verify the file path (`FREEDECKCY_COVER_INDEX_CSV` or `defaults/tianyi_catalog/cover_index.csv`) and column-name compatibility |
| Cover cache **too large / want to clear it** | The cache is plain JSON; just delete `~/.local/share/freedeckCY/tianyi/cover_cache.json` and reload the plugin; positive cache 7 days, negative cache 30 minutes, expired entries are dropped automatically at startup |
| After installation, **the target exe in Steam is wrong** | When the catalog's `openpath` is inaccurate, heuristic resolution is used (relative path → leaf name → first executable in the directory). Fix `openpath` in the CSV and reinstall, or edit the shortcut target in Steam manually |

---

## 8. Known Limitations

- **Library page playtime block (v0.25.0)**: the block is inserted only when `managed=true` (AppID or title matched to `installed_games`); unmatched native Steam games `return null` directly and no HLTB lookup is made; AppID priority reduces same-name false positives but is not absolute; an HLTB failure only affects the data inside the block; it still depends on Steam's library page internals, so a Steam update may invalidate the patch.

- **Diagnostics self-check (v0.22.0)**: a one-shot snapshot; network items depend on connectivity; it does not auto-repair, only provides detail/fix; `baidu_qr` outputs only the sign length (no sign/cookie); the export bundle writes a 0600 zip to the download directory containing 300 lines of logs (already redacted) — review it yourself before submitting; there is no online log viewing / diagnostics-bundle uploading.

- **Decky native game library (since v0.20.0; v0.27.20)**: cover grid/Hero/category shelves/details page, 30 per page + load more, dual cloud-drive source selection; task progress is still in the QAM home task area; the scan entry is in settings and still only recognizes one level of `settings.install_dir`; uninstall is fixed to `delete_files=true` (no compatdata-reclamation prompt); the legacy web library is debug/fallback only.
- **Steam shortcut recovery during scan (v0.21.0)**: PC games need a findable .exe (common installers/runtimes excluded), emulators must already be installed (no automatic download), otherwise `shortcut_error` is recorded; only `shortcuts.vdf` is written, so Steam must be restarted / user switched / library page reopened for shortcuts to appear; existing shortcuts with the same name and exe are not overwritten.

- **Storage location selection (v0.19.0)**: shows only mounted and writable external submounts (mount roots skipped); capacity is a snapshot; it does not auto-create/mount/format, nor does it check whether the Steam library is on the same drive; the suggested subdirectories are fixed at `freedeckCY/{downloads,installed}`.

- **Resource sources**: Tianyi Cloud Drive + Baidu Netdisk QR/Cookie (optional OpenAPI fallback) are both implemented; emulator assets are downloaded on demand at first install; a standalone web submission/management system is not in this repository and not in the plugin package.
- **SteamOS / Linux only (including DroidDeck's proot environment)**: depends on `7zz`, Proton, and Steam's Linux directory structure; it cannot run on Windows / macOS. The Steam root supports native / Flatpak / **DroidDeck dual clients**, and SD cards/second drives are scanned through `libraryfolders.vdf`.
- **The author has stopped maintaining it**: upstream no longer updates, so broken interfaces must be fixed by yourself; there is a generation gap between the upstream release and this repository's version; this repository is currently at 0.27.20 and already ahead of upstream.
- **This repository is the fully maintained version**: `package.json` version 0.27.20, and features follow this repository's documentation; upstream v0.6 is only a historical reference.
- **DroidDeck support is not verified on real devices**: the ARM64 runtime environment, FEX/ARM Proton, and Android storage mapping may all differ; when real-device testing fails, refer first to the troubleshooting and log-collection guidance in [DROIDDECK.en.md](DROIDDECK.en.md).
- **Catalog data must stay clean**: after adding/merging catalog data you must run `make normalize-catalog` and `make validate-catalog` (CI runs `--strict` on the bundled catalog); "Emulator" is a post-cleaning fallback category, not a real game category.
- **Emulator save restore/splitting (v0.16.0)**: PSP/PS3 split via PARAM.SFO and 3DS via NCSD title id, while PS1/PS2/Switch remain whole-card/whole-directory; restore targets are limited by the `restore_roots` allowlist, and cross-device 3DS may degrade to the root directory; a `*.freedeckcy-bak-<timestamp>` backup is made before overwriting, and shared-card conflicts require confirmation; automatic PS1 multi-disc m3u needs multiple `.cue/.chd` files, and an existing m3u takes priority.
- **Emulator save upload (v0.15.0)**: PSP/PS1/PS2/3DS/PS3/Switch shared memory cards are uploaded as whole directories without per-game splitting (other games on the same card are included); GBA/FC/MD/NDS match by ROM filename, so a rename causes `game_save_not_found`; 3DS/Switch directories can be large; `cloud_save_include_emulators` defaults to on and can be turned off.
- **3DS (Azahar) SteamOS compatibility** (v0.14.1): SteamOS 3.9.5 prefers the Flathub Flatpak (the AppImage has upstream issues #127/#953), requiring flatpak on the system with access to Flathub; if the Flatpak installation fails it falls back to the AppImage (which may still fail to open); 3DS is x86_64 only (hidden on aarch64); system files must be supplied by the user and deployed to `~/.var/app/org.azahar_emu.Azahar/data/...`; existing shortcuts are rewritten automatically, but real-device verification is still pending.
- **Baidu Netdisk (v0.17.0)**: the primary path is QR login (BDUSS/Cookie); the Cookie is equivalent to account credentials, expires/is risk-controlled, and must be re-scanned when invalid; the QR session lives only in memory for 180s, and **scan confirmation / Cookie exchange has not been verified on real devices**; OpenAPI is an optional fallback (requires a self-built app, transfers to `/FreedeckTmp`); no CDP/web reverse engineering; Baidu interface changes may affect QR login/direct links.
- **Baidu Netdisk OpenAPI (v0.14.0, optional fallback)**: a self-built app + OAuth authorization are required (no public app); share files must be transferred to `/FreedeckTmp` before a dlink can be fetched, which consumes the user's cloud drive space (cleaned up after installation, kept on failure); official errors such as `errno=-6`/dlink 403 go into the install message; since v0.17.0 the primary path is QR/Cookie and OpenAPI only falls back when there is no Cookie; **still no CDP/web reverse engineering**; changes to public-share metadata/QR interfaces may affect resolution.
- **10 platforms installable, trimmed by architecture, with automatic BIOS/firmware deployment** (v0.12.0): on x86_64 all 10 platforms (including 3DS/PS2/PS3/Switch) can be installed/launched; on aarch64 3DS/PS2/PS3 have no official arm64 package and are hidden by the catalog allowlist per `available_platforms()` (neither entries nor filter rows appear), while Switch has an arm64 package. **The plugin package bundles no emulator, so the first install of each requires a network download** (package size about 45MB); PS1/PS2 need BIOS, and 3DS/PS3/Switch need system files/firmware/keys (since v0.12.0 these are automatically deployed from `bios/<platform>/` into the emulator directory with portable config after installation, including archives; missing files do not block installation but the game cannot be played right after); emulators only recognize the extensions in the registry and there is no save management; downloading/unpacking takes an extra copy of space; these platforms have not been verified on real ARM64/DroidDeck devices.
- **Integrity verification is "size + header pre-check + `7z t` (best-effort)"**: validation is skipped automatically when 7z is unavailable; there is no hash/signature verification; volume detection covers only common naming; cloud saves still depend on `node`.
- **Writes can still be overwritten while Steam is running**: backups are taken before writing and read back after, but a running Steam cannot be prevented from overwriting `shortcuts.vdf`/`config.vdf`; restarting Steam after installation is recommended (automatic Steam restart is in ROADMAP §9).
- **compatdata cleanup is off by default**: uninstall only deletes game files by default; "also delete the Proton prefix" requires an explicit choice to avoid deleting saves by mistake.
- **Quarantined files and backups are not cleaned automatically**: `*.freedeckcy-archive-invalid-*`, `*.freedeckcy-size-mismatch-*`, and `*.freedeckcy-bak-*` remain in the original directory and must be cleaned up manually (or by a future ROADMAP item).
- **Limits of update check/diagnostics**: `update-check` is unauthenticated on GitHub (rate limit 60/hour/IP), and failures only return a message without caching the failure; the diagnostics bundle only redacts common keys/values (cookie/token/HOME), so reviewing it yourself before filing an issue is still recommended.
- **Auto cloud save boundaries**: v0.8.0 covered PC only; since v0.15.0 emulator saves (GBA/PSP/NDS/PS1/FC/MD/Switch) are included, and since v0.16.0 restore is supported (conflict confirmation, backup before overwrite); PS1/PS2/Switch still overwrite whole cards/whole directories; the fingerprint only looks at relative path + size + mtime (at most 5000 files); `cloud_save_auto_upload` is on by default; gamewatch relies on the process command line containing install_path, using `pgrep -f` when `/proc` is unavailable.
- **No i18n**: the UI is entirely hard-coded in Chinese, with copy scattered across `src/index.tsx`, `defaults/tianyi_library_ui/`, and Python return values.
- **No Python type checking**: only pytest unit tests + CI, with no mypy/ruff-style gate.
- **Tianyi interfaces are not public**: signatures, endpoints, and risk control may change at any time; on failure, look first at the protocol diagnostics in `/tmp/freedeckcy.log`.
- **Compliance risk**: the resource links distributed by the project come from the internet, and the README states they are for R&D testing only; assess copyright and cloud-drive terms of service yourself.

---

## 9. Secondary Development Entry Points

| What you want to change | Where to go |
|---|---|
| Resource catalog / adding games | `defaults/tianyi_catalog/*.csv` (fields in `GameCatalog.load` in `game_catalog.py`; new optional columns `platform`/`cover_url`/`cover_portrait_url`/`steam_appid`) |
| Platform/category filtering | `list()` (platform/category), `platform_counts()`, `category_counts()` in `py_modules/game_catalog.py`; the HTTP entry `tianyi_http.handle_catalog`; `platformChips` / `filterChips` / `selectPlatform` / `selectCategory` in the frontend `defaults/tianyi_library_ui/app.js` |
| Updating/extending catalog data | `scripts/merge_v06_catalog.py` (generates from the v0.6 catalog) or edit `defaults/tianyi_catalog/freedeckcy_catalog.csv` directly (16 columns); add covers in `cover_index.csv`; run `make normalize-catalog && make validate-catalog` afterwards |
| Category cleaning / catalog health-check rules | `normalize_categories` / `PLATFORM_TOKENS` in `py_modules/game_catalog.py`; `scripts/normalize_catalog_categories.py`; `scripts/validate_catalog.py` (CI gate) |
| Cover resolution/caching | `resolve_catalog_cover` / `_catalog_entry_cover` / `_load_cover_cache` / `_save_cover_cache` in `py_modules/tianyi_service.py`; index merging in `game_catalog._merge_cover_index` |
| Switching resource sources / integrating another cloud drive | `py_modules/tianyi_client.py` (protocol layer) + `backend/` (Node fallback); the link validation in `game_catalog.py` must be changed as well |
| Extraction / install-directory rules | `_resolve_install_target_dir` / `_extract_archive_to_dir` / `_merge_extracted_content` in `py_modules/tianyi_service.py` |
| Multi-volume detection rules | `detect_archive_sets` (new naming formats/main-volume rules) / `build_bundle_index` in `py_modules/archive_bundle.py` |
| aria2 runtime reuse | `_read_runtime_meta` / `_attach_existing` / `_try_acquire_owner_lock` / `replace_uri` in `py_modules/aria2_manager.py` |
| Download behavior (sharding, concurrency, resume) | `py_modules/aria2_manager.py` (`add_uri` options and startup arguments) |
| Steam shortcuts / covers / Proton | `py_modules/steam_shortcuts.py` (appid, `shortcuts.vdf`, `config.vdf`, `grid`) |
| Restart recovery / grouping semantics / integrity verification | `_try_recover_task` / `_readd_task_download` / `_maybe_schedule_group_post_process` / `_finalize_group_install` / `_verify_downloaded_file` in `py_modules/tianyi_service.py` |
| Archive validation / automatic re-download | `test_archive` in `py_modules/seven_zip_manager.py` + `_schedule_archive_repair` / `ArchiveRepairScheduled` in `py_modules/tianyi_service.py` |
| Ludusavi manifest/matching | `scripts/fetch_ludusavi_manifest.py` (regenerate), `py_modules/save_manifest.py` (`match_manifest` / `resolve_manifest_paths` / `_placeholder_bases`) |
| gamewatch / auto upload | `py_modules/gamewatch.py` (`GameWatcher.poll` / `is_game_running`), `tianyi_service._poll_game_watch` / `_maybe_auto_cloud_upload` / `_cloud_save_fingerprint`, the `cloud_save_auto_upload` setting |
| Native game library | `LIBRARY_ROUTE`/`LibraryPage`/`routerHook.addRoute` in `src/index.tsx`; for callables see `list/prepare/start_tianyi_*` in `main.py` and the corresponding `tianyi_service` methods; the web library is the fallback |
| Library page playtime block | `LibraryTimeBlock` (the `managed` gate)/`installLibraryPlaytimePatch` in `src/index.tsx`; `tianyi_service.get_library_game_time_stats()` (AppID→title matching, no HLTB lookup when unmatched) |
| Diagnostics self-check | `tianyi_service.run_diagnostics()` / `export_diagnostics_to_downloads()`; `run_tianyi_diagnostics`/`export_tianyi_diagnostics_file` in `main.py`; the QAM Settings "Diagnostics" page |
| Storage location selection | `py_modules/storage_options.py` (`detect_storage_options`/mount prefixes/filtering), `tianyi_service.get_storage_options`, `GET /api/tianyi/storage/options`, the QAM paths-page buttons |
| Uninstall / Proton prefix reclamation | `preview_uninstall` / `uninstall_installed_game` / `_can_remove_compatdata_dir` in `py_modules/tianyi_service.py` + `find_compatdata_dirs` in `py_modules/steam_shortcuts.py` |
| Task retry semantics | `retry_task` in `py_modules/tianyi_service.py` + `src/index.tsx` (the "Retry" button on task rows) |
| Extending environment diagnostics | `scripts/doctor.sh` (read-only; add `section`/`ok`/`warn` for new checks) |
| Steam multi-library / Flatpak / DroidDeck detection | `_steam_root_candidates` / `is_droiddeck` / `_steam_library_paths` / `find_compat_user_dir` in `py_modules/steam_shortcuts.py` |
| Proton tool resolution / settings | `detect_proton_tool` / `add_or_update_tianyi_shortcut(proton_tool=)` in `py_modules/steam_shortcuts.py`; the `proton_tool` setting runs through `tianyi_store` / `tianyi_service.update_settings` / `main.set_tianyi_settings` / `tianyi_http.handle_settings_*` |
| Packaging architecture / ARM64 artifacts | `PACKAGE_ARCH` in `scripts/package.sh`; `package-droiddeck` / `runtime ARCH=` in the `Makefile` (emulators are not in the package, so packaging is unaffected) |
| Emulator support / adding a platform | `EmulatorSpec` / `EMULATORS` in `py_modules/emulator_manager.py` (official assets, launch_args, rom_extensions, env_var, state_key, executables, bios_required, setup_required/setup_hint); `available_platforms(arch)` determines the architecture allowlist; `tianyi_service.list_catalog` passes `allowed_platforms`; the emulator fields of `_build_install_plan`/`_auto_register_emulator_to_steam`; for BIOS see `bios_dir`/`bios_present`/`prepare_bios` |
| Emulator save restore/splitting | `emulator_saves.py` (`restore_roots`/`build_restore_targets`/`_split_param_sfo`/`_split_3ds`/`_read_3ds_title_id`), `param_sfo.py`, `tianyi_service._plan_emulator_save_restore`; for PS1 multi-disc see `emulator_manager.find_rom_file` |
| Emulator save discovery | `py_modules/emulator_saves.py` (`STANDARD_SAVE_DIRS`/`PORTABLE_SUBDIRS`/`PER_GAME_PLATFORMS`/`collect_emulator_save_paths`); the `emulator_saves` branch and dedupe in `tianyi_service._collect_cloud_save_candidates`; the `cloud_save_include_emulators` setting |
| 3DS Flatpak/repair behavior | `_is_steamos`/`flatpak_installed`/`_ensure_flatpak`/`ensure_emulator`/`create_launch_wrapper` in `emulator_manager.py`; `emulator_setup._deploy_3ds`; `tianyi_service._maybe_schedule_launcher_repair`/`_repair_emulator_launchers` |
| Baidu QR/Cookie | `py_modules/baidu_qr.py` (request_qr/fetch_qr_image/poll_qr/complete_login), `baidu_client.py` (Cookie resolution/direct links), `start/poll/cancel/clear_baidu_*` and `_share_provider` plus the task header in `tianyi_service`; for OpenAPI see `baidu_openapi_client.py` |
| Baidu OpenAPI | `py_modules/baidu_openapi_client.py` (OAuth/refresh/transfer/dlink/cleanup), `py_modules/baidu_client.py` (public-share metadata), `_share_provider`/`_build_install_plan`/`_fetch_baidu_direct_url`/`_cleanup_baidu_transfer_files` in `tianyi_service`, the QAM Baidu section; do not introduce BDUSS/Cookie |
| Repository submission validation/merging | `py_modules/submission.py` (`normalize_platform`/`validate_submission`/`build_catalog_row`/`merge_submissions`), `submissions/schema.json`, `scripts/validate_submissions.py` / `merge_submissions.py`, the submission-validation step in `.github/workflows/ci.yml` |
| BIOS/firmware deployment | `py_modules/emulator_setup.py`: `setup_emulator`, `_source_files`/`_extract_archives` (archives), `_set_ini_value` (single-key fixes only), per-platform `_write_*`/`_deploy_*`; `tianyi_service._auto_register_emulator_to_steam` calls it and consumes `setup_messages` |
| Emulator download/cache | `_download_asset` / `_extract_zip_emulator` / `_ensure_extracted` in `py_modules/emulator_manager.py` (cache directory `~/.local/share/freedeckCY/emulators/<state_key>/<arch>/`); the plugin package no longer bundles emulators |
| QAM panel UI | `src/index.tsx` (`Content` / `SettingsPage`) |
| Game library showcase / login bridge | `defaults/tianyi_library_ui/{index.html,app.js,app.css,login_bridge.*}` |
| Local HTTP endpoints | `py_modules/tianyi_http.py` (`setup_routes` and the various `handle_*`; newer endpoints: installed / diagnostics / update-check) |
| Library-page browsing/pagination/sorting/installed tab | `reloadList` / `gotoPage` / `cycleSort` / `switchMode` / `reloadInstalled` / `showConfirm` in `defaults/tianyi_library_ui/{app.js,index.html,app.css}`; backend `game_catalog.list(sort=...)`, `tianyi_service.list_installed_games/launch_installed_game/open_installed_folder` |
| Diagnostics export / update check | `get_diagnostics` / `export_diagnostics` / `check_update` / `_redact_text` / `_parse_version` / `_tail_text` / `_launch_external` in `py_modules/tianyi_service.py`; routes are in `tianyi_http.py` |
| Background tasks / periodic logic | `maintenance_tick` in `py_modules/tianyi_service.py` + the main loop in `main.py` |
| Adding unit tests | `tests/` (using the fake `decky` module injected by `tests/conftest.py`) |

---

## 10. Pre-Submit Checklist

- [ ] `make test` (or `.venv/bin/pytest -q`) is all green (currently 587 cases);
- [ ] After changing runtime/Steam/uninstall-related code, run `make doctor` once to confirm the environment self-check is normal;
- [ ] After changing catalog data, run `make normalize-catalog` and `make validate-catalog` (CI runs `--strict`);
- [ ] After changing Ludusavi-manifest-related code, confirm `defaults/ludusavi/manifest.json.gz` exists and ships with the package (release packages should bundle it), and run `tests/test_cloud_auto.py` locally;
- [ ] When changing packaging/runtime, verify both architectures: `make package` (x86_64) and `make package-droiddeck` (aarch64), confirming the artifact suffix and that `defaults/runtime/<arch>/` inside the package contains only aria2c/7zz/node (**no emulators at all**); emulators are downloaded online on first install, while PS1/PS2 BIOS and 3DS/PS3/Switch system files are supplied by the user;
- [ ] After changing BIOS/firmware deployment, verify copying from `bios/<platform>/` (including archives) to `<AppDir>`/user directories and that the portable INI only changes the target keys; regression-test with the setup cases in `tests/test_emulator.py`;
- [ ] After changing emulator save discovery/restore, run `pytest tests/test_emulator_saves.py -q`: per-game saves do not degrade to the whole directory, shared directories are deduped, PARAM.SFO/3DS splitting, restore-target allowlist, switch disabled; for PS1 multi-disc run the m3u cases in `tests/test_emulator.py`;
- [ ] After changing 3DS Flatpak/launch scripts, run the flatpak/wrapper cases in `tests/test_emulator.py -q`; confirm `emulators.3ds.source` and the wrapper's XWayland env; existing 3DS records are rewritten by the background repair;
- [ ] After changing library-page playtime logic, verify: native Steam game details pages show no block while plugin games show it; `get_library_game_time_stats` returns `managed=false` for unmanaged games without an HLTB lookup; `pytest tests/test_diagnostics.py -q`;
- [ ] After changing native-library back logic, verify all three paths: modal "Back", modal "Steam Library", and route "Back"; since v0.27.3 the top toolbar is not sticky, so verifying the back button / button behavior after scrolling suffices; if necessary verify the fallback with `Navigation.NavigateBack`;
- [ ] After changing the native-library entry / Baidu QR, run `pnpm build` and reload the plugin: confirm the plugin version is 0.27.20 and that clicking the game library opens the modal; QR timeout logs contain `Baidu QR ...`;
- [ ] After changing native-library layout/input, use on-device CEF to verify the left/right focus ring of the leftmost card, the top blue frame, A/B/directional keys, trackpad scrolling, and that the details action bar is fully visible;
- [ ] After changing diagnostics, run `pytest tests/test_diagnostics.py -q` and confirm the checks structure/summary; the export contains `self-check.json` with 0600 permissions;
- [ ] After changing the native library, run `pnpm build` and reload the plugin; confirm the `/freedeckcy/library` route, search/filter/pagination, install confirmation, and installed actions; `make test` is still 587;
- [ ] After changing storage detection, run `pytest tests/test_storage_options.py -q` and confirm system-mount filtering and the external directory/capacity fields; the QAM paths-page buttons switch and refresh;
- [ ] After changing scan-installed, run `pytest tests/test_install_pipeline.py -q` (scan backfill/auto-shortcut cases), confirming single-level scanning, path/game_id dedupe, no duplicates for same-name same-exe, PC exe lookup, and emulator wrappers; re-check `shortcuts.vdf` after restarting Steam;
- [ ] After changing Baidu-related code, run `python -m pytest tests/test_baidu_integration.py tests/test_baidu_openapi_client.py tests/test_baidu_client.py -q` (HTTP/QR mocked, no network); confirm the QR Cookie is stored only in state and is not written to logs/diagnostics;
- [ ] After changing submission validation/merging, run `make validate-submissions` and `python scripts/merge_submissions.py --dry-run`, confirming CI passes even with no JSON; use `make validate-catalog` to confirm the merged CSV is valid;
- [ ] After changing the emulator registry, verify `available_platforms()`: x86_64 should have 10 platforms and aarch64 only 7 (3DS/PS2/PS3 have no package), and confirm the `platforms` count from `/api/tianyi/catalog` is trimmed accordingly;
- [ ] If you changed `src/` → run `pnpm build` and commit `dist/index.js(.map)`;
- [ ] No new artifacts such as `__pycache__` / `*.pyc` / `.DS_Store` / `node_modules`;
- [ ] The large binaries under `defaults/runtime/` are not committed (they are in `.gitignore`);
- [ ] After changing `py_modules/*.py`, reload the plugin at least once and exercise both paths: "open the panel" + "open the game library";
- [ ] Commands/paths in the docs match reality (update this file when changing the `Makefile`, `scripts/`, or `maintenance_tick`).
