> English | [中文](ARCHITECTURE.md)

# freedeckCY Architecture

This document is aimed at secondary developers and maintainers. It describes the implementation structure of **this repository (the `main` branch)** of freedeckCY, and its content is synchronized with the freedeckCY **v0.28.14** (2026-11) code. Code references use repository-relative paths; `file:line` points to the current workspace and may drift after refactoring, while function names serve as stable anchors.

---

## 1. One-sentence positioning

freedeckCY is a **Decky Loader plugin** running on **Steam Deck / SteamOS**: it turns the Tianyi Cloud Drive / Baidu Netdisk share listings distributed with the plugin into an "installable game library", uses aria2 for multi-threaded downloads and 7zz for extraction, then writes Steam shortcuts and Proton compatibility-layer configuration so that non-Steam games appear in the Steam Game Mode library just like genuine ones; it additionally provides a **cloud save backup / restore** pipeline built on Tianyi Cloud Drive.

> Compliance note: the project README describes itself as "for R&D testing only, resources come from the Internet, delete within 24 hours"; the code parses third-party cloud drive share links and bypasses the official client for downloads. This is a high-risk area for copyright and cloud drive terms of service; evaluate it yourself before use.

**Key fact**: by default the catalog is pulled from the built-in server and signature-verified; when the server is unavailable it falls back to the in-repo CSV (`defaults/tianyi_catalog/`; one record = game name + Tianyi or Baidu share link + relative path of the exe after extraction), while the download direct link is fetched at runtime from the corresponding cloud drive API.

---

## 2. Repository ≠ product: `main` is only an early version

This is the easiest trap when reading this repository: **the finished releases on GitHub have far more features than the repository code**.

> This repository **freedeckCY** is a derivative fork of the upstream [Freedeck](https://github.com/panyiwei-home/Freedeck); the version number starts at **0.1.0** (discontinuous with upstream 0.2–0.3) and is currently **0.27.20**. The "upstream status" below describes the upstream repository, not features already implemented in this repository.

| Location | Content | Notes |
|---|---|---|
| This repo, `main` | `package.json` version `0.28.14`, Tianyi Cloud Drive + Baidu Netdisk + multi-platform catalog, adapted to Steam Deck / DroidDeck | Forked from the early 2026-02 upstream Freedeck version (0.2), with version numbers restarting from 0.1.0; v0.1.1 completed the "four-piece set"; v0.2.0 completed catalog platformization / cover index / category filtering; v0.3.0 completed the full catalog and platform filtering UI; v0.3.1 did category cleanup and catalog data health checks; v0.4.0 did DroidDeck (Android/ARM64) adaptation; v0.5.0 completed first-tier browsing/paging/sorting/installed tab plus diagnostics export/update check; v0.6.0~v0.6.2 did the GBA emulator closed loop and remote JSON catalog; v0.7.0 built the generic emulator registry and integrated PSP/NDS; v0.8.0 did Ludusavi + gamewatch automatic cloud saves; v0.9.0 expanded the emulator registry to PS1/FC/MD (6 platforms); v0.10.0 switched all emulators to online download (no emulator bundled in the plugin); v0.11.0 completed 10 platforms + architecture capability matrix; v0.12.0 did emulator BIOS/firmware deployment + portable config; v0.13.0 did repository game submission (Issue/PR → catalog); v0.14.0 integrated the Baidu Netdisk official OpenAPI; v0.14.1 fixed 3DS (Azahar) compatibility on SteamOS 3.9.5 (prefer official Flatpak); v0.15.0 brought emulator saves into cloud save upload; v0.16.0 did emulator save restore + per-game splitting + PS1 multi-disc m3u; v0.17.0 changed Baidu Netdisk to QR-code login (BDUSS/Cookie main path, OpenAPI optional fallback); v0.18.0 did installed game scanning + Baidu QR error diagnostics; v0.19.0 made download/install directories support SD card selection; v0.20.0 did the Decky native game library (no longer depending on the web page); v0.21.0 moved "scan installed" to settings and auto-added Steam shortcuts; v0.22.0 did diagnostics self-check + one-click diagnostics bundle; v0.23.0 did native library fallback + Baidu QR timeout/click feedback; v0.24.0 fixed native library back/close; v0.25.0 stopped showing the plugin playtime block for existing Steam games; v0.26.x did architecture splitting and stability fixes; v0.27.0–v0.27.20 did the game library visual refactor, detail page/search/filter/update button alignment, and Steam Deck controller/trackpad adaptation; v0.28.14 added Chinese/English bilingual UI, first-run language selection, and install-reliability improvements (installed-game check/repair, health check, failure diagnostics/source fallback, pre-install environment preflight) |
| Releases v0.2.3 → v0.6 | Release packages about 50 MB | Add **Baidu Netdisk** support, **emulator integration**, **resource pool (user uploads)**, CRT filter, likes, and more |
| Releases NewFreedeck v0.1 → v0.3 | 2026-08 ~ 09 refactored versions | Emulators playable, "play later" tab, multi-volume download fix |

This leads to several direct conclusions:

- **A big gap between the upstream Freedeck releases and main**: modules such as Baidu Netdisk, emulators, and the resource pool in upstream releases are not in upstream main; Baidu Netdisk and emulators in this repository are independent implementations (see 5.10 / 5.13) — do not confuse them with upstream.
- **The repository lacks runtime binaries**: `aria2_manager.py` / `seven_zip_manager.py` / `tianyi_client.py` prefer to look for `aria2c`, `7zz`, `node` under `defaults/runtime/`, but the repository itself does not commit these files (they are in `.gitignore`). The plugin can start without them, but to run download/install/cloud save end to end you must first run `make runtime` after cloning, otherwise you will see "download component unavailable / extraction component unavailable / node runtime not found" respectively. The difference between the ~50 MB release zip and the ~1 MB source is mainly these binaries.
- **The author has stopped maintaining it**: the original release note for NewFreedeck v0.1 reads "I currently don't have the energy and time to continue maintaining it, sorry, so you can modify it yourself based on the skill I put together, and you can send me a PR at the end."
- **v0.25.0 keeps the library detail playtime block isolated by managed**: `LibraryTimeBlock` only renders when `data.managed === true`; when unmatched/unloaded it directly `return null` (no longer inserting "played / main story / total time" into existing Steam games, and no longer showing "Loading" first); the backend `get_library_game_time_stats()` matches **first by AppID** via `_resolve_installed_record_by_app_id`, then by title, returning `managed=false` + all zeros and **not calling `resolve_hltb_stats`** when unmatched; this only affects games installed by the plugin (see 7.3).
- **v0.24.0 native library back/close fix**: `LibraryPage` adds `onClose?` — modal mode `showModal(<LibraryPage onClose={() => modal.Close()} />)`; in route mode without `onClose`, `handleClose` uses `Navigation.NavigateBack()`; a new **Back / Steam Library / Refresh toolbar** at the top (since v0.27.3 changed from QAM sticky offset to normal flow, moving with the page on scroll), and the title bar also keeps "Back"; "Steam Library" closes the modal/returns and then `Router.NavigateToLibraryTab()` back to the Steam library (falling back to `NavigateBack` on failure) (see 5.16).
- **v0.23.0 native library fallback + Baidu QR timeout/feedback** (history): QAM "Game Library" changed to **`showModal(<LibraryPage />)` first**, falling back to `Navigation.Navigate(LIBRARY_ROUTE)` only on failure (the full-screen route is retained); at that time a home/library page version marker was used to confirm whether the frontend had updated, removed in v0.26.51; Baidu QR click shows a toast immediately, the frontend uses `withTimeout` and the backend `wait_for`, and timeouts produce clear text plus a `Baidu QR ...` log entry (see 5.13 / 5.16).
- **v0.22.0 diagnostics self-check + one-click diagnostics bundle**: QAM settings adds a "Diagnostics" page (run self-check / export diagnostics bundle); `run_diagnostics()` checks the plugin/catalog/runtime/catalog data/Steam/storage/Tianyi network/Baidu QR/tasks/logs, each item with `ok|warn|fail|skip` + detail/fix; `export_diagnostics()`'s zip adds `self-check.json`, and `export_diagnostics_to_downloads()` writes into the downloads directory (0600, `freedeckcy-diagnostics-<time>.zip`); the Baidu QR self-check only returns the sign length and never outputs sign/cookie (see 5.17).
- **v0.21.0 installed-scan migration + auto-added Steam shortcuts**: "Scan installed games" moved from the native library's "Installed" page to **QAM settings → Install**; `scan_installed_games()` adds `list_all_shortcuts_sync()` duplicate checks by same name/same exe; for PC it uses `_find_scanned_executable()` to find the exe, and for emulators uses `ensure_emulator(allow_download=False)` + wrapper to **auto-create Steam shortcuts** (if the emulator is not installed it only records `shortcut_error` and does not auto-download); a second pass creates them for existing PC records with `steam_app_id=0`; returns `steam_added`/`steam_recovered_count`/`shortcut_error` (see 5.14 / 5.16).
- **v0.20.0 Decky native game library (history)**: QAM adds `LibraryPage` (route `/freedeckcy/library`), and the home "Game Library" becomes the native entry; at the time it was a list + search/dropdown filters + 20 items per page; everything went through Decky callables. Since v0.26.4 cover cards / 30 items per page, v0.27.0–v0.27.20 did the visual refactor (see 5.16).
- **v0.19.0 download/install directories support the SD card**: adds `py_modules/storage_options.py` — parses `/proc/mounts` to recognize writable mounts such as `/run/media` (SteamOS SD), `/media`, `/mnt`, `/storage` (DroidDeck), filters system fstypes such as proc/sysfs/tmpfs/overlay and the root mount, and `shutil.disk_usage` returns free/total; each external mount gets suggested `freedeckCY/downloads` and `freedeckCY/installed` directories; `GET /api/tianyi/storage/options` + a one-click switch on the QAM "Paths" page (with a hint when there is no external storage) (see 5.15).
- **v0.18.0 installed-game scan + Baidu QR error diagnostics**: `scan_installed_games()` scans **one level of subdirectories** under `settings.install_dir`, matches catalog entries by directory name/title, skips already-recorded path/game_id, backfills the Steam appid, and uses `find_rom_file()` to find ROMs for emulator platforms; HTTP `POST /api/tianyi/installed/scan` + the web library "Scan installed" button; Baidu QR adds a **BAIDUID CookieJar**, HTTP status/response-snippet errors, and polling network errors with `stage=failed` (no longer staying in waiting forever) (see 5.13 / 5.14).
- **v0.17.0 Baidu QR login (main path)**: adds `py_modules/baidu_qr.py` (Passport `getqrcode` → `unicast` long polling → `qrbdusslogin` exchange for `BDUSS/STOKEN/PTOKEN`); QAM "Baidu Netdisk (QR login)" shows the QR code, and the Cookie is persisted to `state.json`'s `baidu_login`; Baidu install plans **prefer Cookie** and only use OpenAPI when there is none (optional fallback), otherwise prompting to scan; task aria2 carries the Baidu Cookie/Referer/UA; **still no CDP/web reverse engineering** (see 5.13).
- **v0.16.0 emulator save restore + per-game split + PS1 multi-disc**: `restore_roots()`/`build_restore_targets()` use a **known save-root whitelist** to constrain restore targets (a restore on the same machine goes to the original parent directory, while a cross-machine restore falls to the first root), the plan stage counts conflicts and requires confirmation, and apply reuses `*.freedeckcy-bak-<timestamp>` backups; PSP/PS3 use `PARAM.SFO`'s `TITLE` and 3DS uses the NCSD header `0x108` Program ID for **per-game splitting** (falling back to the shared directory when unmatched); PS1 `find_rom_file()` **prefers `.m3u`**, multiple `.cue/.chd` files auto-generate `freedeckcy-multidisc.m3u` (natural sort, relative paths), and a single disc still returns `.cue` (see 5.10 / 5.11).
- **v0.15.0 emulator saves included in cloud saves**: adds `py_modules/emulator_saves.py` — discovers saves by the 10 platforms' standard directories + portable/Flatpak directories; GBA/FC/MD/NDS do **per-game** matching by ROM file name (returns `game_save_not_found` when not found and never degrades to the whole directory), while PSP/PS1/PS2/3DS/PS3/Switch return the **shared** memory card/title directories and dedupe by path signature (`emulator_saves_shared`); setting `cloud_save_include_emulators` (default true) controls whether they participate in uploads; uploads are wired in with `source_strategy="emulator_saves"`; restore at the time (v0.15.0) only supported PC/Proton; **emulator save restore is supported since v0.16.0** (see 5.11).
- **v0.14.1 fixed 3DS (Azahar) SteamOS compatibility**: Azahar's official AppImage has known issues on SteamOS (upstream #127: the AppImage won't open; #953: Game Mode crashes); on SteamOS 3.9.5 it prefers the **Flathub official Flatpak `org.azahar_emu.Azahar`**; `ensure_emulator()` selects the path as "env → installed Flatpak → SteamOS auto-install Flatpak → AppImage fallback"; the 3DS launch script forces XWayland (`QT_QPA_PLATFORM=xcb`, `SDL_VIDEODRIVER=x11`); installed 3DS games have their **launch scripts rewritten automatically** by background maintenance, with no reinstall needed; system files are additionally deployed to the Flatpak data directory (see 5.10).
- **v0.14.0 Baidu Netdisk (official OpenAPI)**: adds `py_modules/baidu_openapi_client.py` (OAuth oob authorization/refresh, share transfer, dlink, cleanup) and `py_modules/baidu_client.py` (**only** for parsing metadata of public share URLs, without Cookie); Baidu links go through an independent provider (`baidu_openapi`) and do not require a Tianyi login; install plans/tasks/retries are split by provider, download headers use `Referer=https://pan.baidu.com/disk/home` and `UA=pan.baidu.com`; after installation it cleans up the `/FreedeckTmp` transfer; since v0.17.0 it uses the QR/Cookie main path with OpenAPI as an optional fallback (see 5.13; still no CDP/web reverse engineering).
- **v0.13.0 repository game submission**: adds `.github/ISSUE_TEMPLATE/submit-game.yml` (Issue form) and `submissions/` (JSON + schema + examples); `py_modules/submission.py` validates fields/platform aliases/share links/openpath/duplicate shareCode; `merge_submissions()` merges into the catalog CSV and archives to `submissions/merged/`; the web library adds a "Submit game" button; CI validation and `make validate-submissions` (see 5.12 / [submissions/README.md](../submissions/README.md)).
- **v0.12.0 emulator BIOS/firmware deployment + portable config**: adds `py_modules/emulator_setup.py` — after installation it deploys the BIOS/firmware/keys in `~/.local/share/freedeckCY/bios/<platform>/` to where the emulator actually reads them (archives are extracted with 7zz and persistently cached), and writes a minimal portable config (DuckStation/PCSX2 INI, mGBA/PPSSPP fullscreen); when PS3's `dev_flash` is empty it runs `rpcs3 --installfw` automatically; the deployment message is merged into the install-complete message (see 5.10 - Emulator BIOS/firmware deployment).
- **v0.11.0 completed 10 platforms + architecture capability matrix**: the emulator registry adds **3DS (Azahar) / PS2 (PCSX2) / PS3 (RPCS3) / Switch (Eden)**, for **10 platforms** in total; the 3DS/PS2/PS3 official packages are **x86_64 only**, and on aarch64 (including DroidDeck) catalog queries **automatically hide platform entries and filter bars** via the `available_platforms()` whitelist; Switch has both x64 and arm64 packages; 3DS/PS3/Switch need system files/firmware/keys (`setup_hint` prompts) and PS2 needs a BIOS (`bios/ps2/*.bin` copied to the PCSX2 directory) (see 5.10).
- **v0.10.0 all emulators downloaded online**: the plugin package **no longer bundles any emulator** (removed `scripts/fetch_emulator.sh` and `make emulator-runtime`, dropping package size from ~68 MB to ~45 MB); the official packages for the 6 platforms (including GBA) are all downloaded from GitHub releases to `~/.local/share/freedeckCY/emulators/<platform>/<arch>/` on first install; offline environments can pre-place the cache or set `FREEDECKCY_*_BIN` (see 5.10 / 5.7).
- **v0.9.0 emulators expanded to 6 platforms**: the registry adds **PS1 (DuckStation, BIOS required by the user)/FC (Mesen2)/MD (Mesen2, sharing the cache with FC)**; the PS1 BIOS goes in `~/.local/share/freedeckCY/bios/ps1/` and is copied to `~/.local/share/duckstation/bios/` at install, with a missing BIOS only warning and not blocking; FC/MD's Mesen2 is a single executable inside a zip; PS2/PS3/3DS/Switch are not yet integrated because of x64-only official packages or firmware/keys requirements (see 5.10).
- **v0.8.0 automatic cloud saves**: bundles the **Ludusavi save manifest** (53,549 games, MIT) for title/SteamID matching and resolves templates such as `<winAppData>` into the Proton prefix, merged with the existing Proton scan; `gamewatch` uses `/proc/*/cmdline` every 8 seconds (or `pgrep -f` when there is no `/proc`) to detect game exit and **only automatically triggers cloud save upload for the game that just exited** (setting `cloud_save_auto_upload` enabled by default, 30-second debounce); before uploading it dedupes by a "relative path + size + mtime" fingerprint and skips with `reason=unchanged` when nothing changed (see 5.11).
- **v0.7.0 generic emulator registry**: the `EmulatorSpec` registry integrates three platforms — **GBA (mGBA 0.10.5)/PSP (PPSSPP 1.20.4)/NDS (melonDS 1.1)** — (GBA was bundled at the time, **since v0.10.0 everything is downloaded online**); PSP/NDS download the official AppImage on demand at first install (NDS is an AppImage inside a zip), unpacking uniformly via `--appimage-extract` (no FUSE dependency), and after generating launch scripts they are registered as native Linux shortcuts (no Proton); PS1 was deferred because of the BIOS dependency, and other platforms are still browse-only (see 5.10 / ROADMAP 9.8).
- **v0.6.1 / v0.6.2 remote JSON catalog**: `FREEDECKCY_CATALOG_JSON` supports a local file or an HTTP(S) JSON (NewFreedeck-compatible format); remote content is cached for 6 hours and falls back to CSV on failure; the default is still the bundled CSV — see [UPSTREAM_SERVER.md](UPSTREAM_SERVER.en.md).
- **v0.5.0 first tier (browsing experience and operations)**: the library page browses all resources as soon as it opens, with platform/category filters + paging + sorting, plus a new "Installed" tab (launch/open folder/uninstall); the top toolbar can **export a diagnostics zip** (redacted) and **check GitHub updates** (1 h cache); interactions and shortcuts see 5.8, diagnostics/update see 5.9.
- **v0.4.0 DroidDeck adaptation**: ARM64 runtime selection, DroidDeck detection, automatic ARM Proton tool resolution, dual Steam roots (x64 client preferred), and `PACKAGE_ARCH` packaging of arm64/universal packages; installation, building, and troubleshooting see [DROIDDECK.md](DROIDDECK.en.md).
- **Catalog/cover capability (since v0.3.1)**: the bundled full catalog `freedeckcy_catalog.csv` (**7084 valid / 11 platforms**, 16 columns, categories cleaned) + cover index `cover_index.csv` (3470 rows; after merging, **6823 resources have built-in covers, 96.3%**); covers are resolved by "catalog static → disk cache → Steam store → ProtonDB" and cached on disk; the library page has **two filter rows, platform + category** (categories include "Emulator" with 606 entries). `make validate-catalog` (CI `--strict`) checks the catalog data. **GBA/PSP/NDS are installable/launchable** (GBA since v0.6.0, PSP/NDS added in v0.7.0); v0.6.0–v0.11.0 integrated 10 emulator platforms (3DS/PS2/PS3 x86_64 only, see 5.10 / ROADMAP 9.8).
- **v0.1.1's "four-piece set"**: optional Proton prefix reclamation on uninstall (not deleted by default), `7z t` validation + automatic re-download, the "Retry" action for failed tasks, and `make doctor` environment diagnostics (see §6.6–§6.8 / DEVELOPMENT §6.6).
- **This repository was converted from a template / old project**: `defaults/defaults.txt` is still the Decky template readme, and `config.py` keeps a fallback path named `Decky-send`. The `repository` / `bugs` / `homepage` fields pointing to the upstream template have been removed from `package.json`, and `license` was changed to BSD-3-Clause (consistent with `LICENSE`).

> This completion normalized source line endings to LF (enforced by `.gitattributes`), so `git diff` may show an "entire file rewritten" illusion when looking at commits; actual logic changes are visible in each file's diff `-w` view.

---

## 3. Technology stack

| Layer | Choice | Location |
|---|---|---|
| Plugin runtime | Decky Loader (Python 3 + asyncio) | `main.py`, `decky.pyi` |
| Local web service | **aiohttp**, listening only on `127.0.0.1:59271` | `py_modules/server_manager.py` |
| Business core | A single giant class `TianyiService` (about 8000 lines) | `py_modules/tianyi_service.py` |
| Tianyi API client | aiohttp + hand-written MD5 signature / XML/JSONP-compatible parsing | `py_modules/tianyi_client.py` |
| State persistence | Single JSON rewritten in full; state directory 0700 / files 0600 | `py_modules/tianyi_store.py` → `~/.local/share/freedeckCY/tianyi/state.json` |
| Logging | `RotatingFileHandler` (5 MB × 3, `propagate=False`) | `py_modules/config.py` → `/tmp/freedeckcy.log` |
| Downloader | Bundled / system **aria2c**, controlled via JSON-RPC | `py_modules/aria2_manager.py` |
| Extraction | Bundled / system **7zz** (`.7z/.rar` etc.; `7z t` validation before extraction, best-effort), everything else via `shutil` | `py_modules/seven_zip_manager.py` |
| Steam integration | Self-implemented VDF read/write + binary `shortcuts.vdf` | `py_modules/steam_shortcuts.py`, `py_modules/vdf/` |
| QAM frontend | **React 19 + TypeScript**, `@decky/api` + `@decky/ui`, bundled with Rollup | `src/index.tsx` → `dist/index.js` |
| Local web frontend | **Vue 3 global build** (no build step, includes `vue.global.prod.js` directly): browsing/paging/sorting/installed tab/diagnostics and update toolbar | `defaults/tianyi_library_ui/` |
| Game catalog / covers | CSV catalog (categories cleaned) + `cover_index.csv`; cover cache JSON (TTL 7 days); `validate_catalog.py` data health checks | `py_modules/game_catalog.py`, `py_modules/tianyi_service.py`, `scripts/validate_catalog.py` |
| Cloud drive upload / share fallback | **Node ≥ 18**, child process with a stdin/stdout JSON protocol | `backend/*.js`, `backend/*.cjs` |
| Environment diagnostics | Read-only bash script (runtime/Steam/state/logs/ports/network); plus HTTP diagnostics JSON/zip export and GitHub update check (v0.5.0) | `scripts/doctor.sh` (`make doctor`), `tianyi_service.get_diagnostics()` |
| Runtime platforms | Steam Deck (x86_64) / **DroidDeck (aarch64)**; runtime directories selected by `platform.machine()` | `defaults/runtime/<arch>/`, `scripts/package.sh`, [DROIDDECK.md](DROIDDECK.en.md) |
| Automatic cloud saves (v0.8.0; v0.15.0 emulator saves; v0.16.0 restore/split) | **Ludusavi manifest** + **gamewatch** process detection; after a game exits, only that game is uploaded, with fingerprint dedupe; since v0.15.0 non-PC platforms use `emulator_saves.py` to discover emulator saves (per-game/shared directories), and the `cloud_save_include_emulators` setting can disable them; v0.16.0 supports restore (whitelist targets/backup/conflict confirmation) and per-game splitting for PSP/PS3/3DS | `py_modules/save_manifest.py`, `py_modules/gamewatch.py`, `py_modules/emulator_saves.py`, `defaults/ludusavi/` |
| Baidu Netdisk (v0.17.0, QR/Cookie main path) | Passport QR login (`getqrcode` → `unicast` → `qrbdusslogin`) exchanging for `BDUSS/STOKEN/PTOKEN`, Cookie stored in `state.json`'s `baidu_login`; share parsing/downloading use the Cookie, and aria2 carries the Baidu Cookie/Referer/UA; **OpenAPI is only an optional fallback** (self-built app OAuth, v0.14.0); no CDP/web reverse engineering | `py_modules/baidu_qr.py`, `py_modules/baidu_client.py`, `py_modules/baidu_openapi_client.py`, `tianyi_store.BaiduLoginState` |
| Repository game submission (v0.13.0) | GitHub Issue form / `submissions/*.json` PR → `submission.py` validation → `merge_submissions.py` writes to the catalog CSV → `submissions/merged/` archive; pure standard-library CLI, no runtime dependencies | `py_modules/submission.py`, `submissions/`, `.github/ISSUE_TEMPLATE/submit-game.yml`, `scripts/{validate,merge}_submissions.py` |
| Emulator runtimes (since v0.6.0, v0.7.0 registry, v0.9.0 six platforms, v0.10.0 all downloaded online, v0.11.0 ten platforms, v0.12.0 BIOS/firmware deployment) | **GBA=mGBA / PSP=PPSSPP / NDS=melonDS / PS1=DuckStation / FC,MD=Mesen2 / 3DS=Azahar / PS2=PCSX2 / PS3=RPCS3 / Switch=Eden**; **the plugin package does not bundle emulators** — the first install downloads and unpacks the official release on demand; after installation `emulator_setup.setup_emulator()` deploys BIOS/firmware/keys and writes portable config; 3DS/PS2/PS3 official packages are x86_64 only and hidden on aarch64 | `py_modules/emulator_manager.py` (registry/download), `py_modules/emulator_setup.py` (deployment/portable config), `~/.local/share/freedeckCY/{emulators,bios}/<...>/` |

At runtime the plugin spawns **4 kinds of processes** in total: Decky's Python process, `aria2c`, `7zz`, and occasionally `node`.

### 3.1 Runtime environment and platforms (Steam Deck / DroidDeck, v0.4.0)

| Item | Steam Deck | DroidDeck |
|---|---|---|
| CPU architecture | x86_64 | **aarch64 (ARM64)** |
| Runtime environment | SteamOS | proot SteamOS runtime on Android, HOME usually `/root` |
| Steam root | `~/.steam/steam` / `~/.local/share/Steam` / Flatpak | Same as above; the x64 client additionally has `~/.droiddeck-x64/.local/share/Steam` |
| Proton tool | Valve tools such as `proton_experimental` | **ARM tool names** `droiddeck-proton-arm64` / `droiddeck-proton-11-arm64` |
| Runtime binaries | `defaults/runtime/x86_64/` | `defaults/runtime/aarch64/` |

- **Runtime architecture**: aria2c / 7zz / node are all normalized from `platform.machine()` (`x86_64`; `aarch64`/`arm64`→`aarch64`) before looking under `defaults/runtime/<arch>/`; see [aria2_manager.py:107](../py_modules/aria2_manager.py) `_resolve_binary_path()`, [seven_zip_manager.py:26](../py_modules/seven_zip_manager.py) `_resolve_binary_path()`, [tianyi_client.py:631](../py_modules/tianyi_client.py) `_runtime_arch()`.
- **DroidDeck detection** ([steam_shortcuts.py:60](../py_modules/steam_shortcuts.py) `is_droiddeck()`): only looks at filesystem markers — the `DROIDDECK_ROOT` environment variable, `~/.droiddeck-x64`, `~/.droiddeck-decky-enabled`, `~/.droiddeck`, `<steam_root>/package/droiddeck-installed`.
- **Proton tool resolution** ([steam_shortcuts.py:78](../py_modules/steam_shortcuts.py) `detect_proton_tool()`): `FREEDECKCY_PROTON_TOOL` takes priority (`none` means don't write a mapping) → on DroidDeck `droiddeck-proton-11-arm64` (when it already appears in `config.vdf`) or `droiddeck-proton-arm64` → in other environments `proton_experimental`; the `proton_tool` setting defaults to `auto` (see 6.5).
- **Steam root selection** ([steam_shortcuts.py:33](../py_modules/steam_shortcuts.py) `_steam_root_candidates()`): on top of the standard candidates it adds `~/.droiddeck-x64/.local/share/Steam` — if its `steam.pid` exists it is **placed first** (preferring the running x64 client), otherwise last; `FREEDECKCY_STEAM_ROOT` can also be used to pin it manually.
- Installation, building, and troubleshooting see [DROIDDECK.md](DROIDDECK.en.md).

---

## 4. Directory map

```text
repo/
├── main.py                     # 插件入口：Plugin 类，24 个可调用 RPC，大部分薄转发给 TianyiService / server_manager
├── plugin.json                 # Decky 元信息（api_version=1, flags=[]，publish 描述已更新）
├── package.json                # 版本 0.27.20；build=rollup；前端依赖
├── decky.pyi                   # Decky Python API 类型存根
├── Makefile                    # runtime / package / test / doctor / validate-catalog / validate-submissions / clean / help 目标（见 DEVELOPMENT.md）
├── requirements-dev.txt        # 开发与 CI 依赖（pytest 等，运行期依赖由 Decky 自带）
├── .gitignore                  # 忽略 __pycache__、defaults/runtime/、node_modules、dist-artifacts 等
├── .gitattributes              # 行尾统一为 LF，二进制资源按原样处理
├── clear_freedeckcy_tasks.sh     # 运维脚本：清空 state.json 里的 tasks（支持 $HOME / FREEDECKCY_STATE_FILE）
├── dist/index.js(.map)         # 已提交的构建产物（约 100 KB / 1.6 MB sourcemap）
├── src/
│   ├── index.tsx               # 全部 React 代码：Content(QAM) / SettingsPage / 库页面注入补丁
│   └── types.d.ts
├── defaults/                   # 随插件分发的静态资源（打包时复制到插件根目录）
│   ├── tianyi_catalog/freedeckcy_catalog.csv    # 全量目录（7084 条有效 / 11 平台，16 列，分类已清洗，主用）
│   ├── tianyi_catalog/gamebox_all_links_*.csv   # 旧版 PC 目录（2845 行，保留为回退）
│   ├── tianyi_catalog/cover_index.csv            # 封面索引（3470 行，仓库已内置；格式见 5.5）
│   ├── tianyi_library_ui/      # Vue 游戏库（平台/分类筛选、分页、排序、已安装页签、诊断/更新工具条）+ 二维码登录桥（6 个文件）
│   ├── ludusavi/              # Ludusavi 存档清单（manifest.json.gz 53,549 游戏 / LICENSE / README，随包分发）
│   ├── runtime/                # 运行期二进制（不提交，由 make runtime 下载到 .gitignore 的目录）
│   └── defaults.txt            # Decky 模板说明文件（原样保留）
├── py_modules/
│   ├── tianyi_service.py       # ★ 业务内核：下载/安装（分卷、校验、自愈、重试）/卸载/云存档/登录/时长/封面缓存与解析
│   ├── tianyi_client.py        # ★ 天翼云盘协议：分享解析、直链、token、上传（调 Node）
│   ├── tianyi_http.py          # 本地 HTTP 路由与 handler（41 条路由）
│   ├── tianyi_store.py         # 数据类 + state.json 读写（目录 0700 / 文件 0600）
│   ├── server_manager.py       # aiohttp 生命周期 + 本地 API 安全边界（Host/Origin）+ 设置备份 + /_healthz
│   ├── aria2_manager.py        # aria2 子进程 + 运行时元数据/flock 复用 + JSON-RPC（addUri/changeUri/listDownloads…）
│   ├── seven_zip_manager.py    # 7z 解压 / 压缩 / `7z t` 校验（test_archive）
│   ├── emulator_manager.py      # 通用模拟器注册表（10 平台：官方资产、架构白名单 available_platforms、按需下载、解包、ROM 查找、启动参数、setup 提示）
│   ├── emulator_setup.py        # 安装后部署 BIOS/固件/keys（压缩包 7zz 解压缓存）+ portable 配置（DuckStation/PCSX2 INI、mGBA/PPSSPP 全屏、RPCS3 --installfw）
│   ├── submission.py            # 仓库游戏提交：平台别名/字段校验/JSON Schema 对应/merge 进目录 CSV（纯标准库）
│   ├── baidu_qr.py              # 百度 Passport 扫码登录（getqrcode/unicast/qrbdusslogin → BDUSS/Cookie）
│   ├── baidu_client.py          # 百度分享 URL 解析/直链（Cookie 主链路 + OpenAPI 回退共用）
│   ├── baidu_openapi_client.py  # 百度网盘官方 OpenAPI：OAuth 授权/刷新、分享转存、dlink、转存清理
│   ├── save_manifest.py         # Ludusavi 存档清单加载/标题与 SteamID 匹配/占位符 → Proton 前缀路径解析
│   ├── gamewatch.py             # /proc 或 pgrep 的游戏进程检测（退出事件触发自动云存档）
│   ├── emulator_saves.py        # 模拟器存档发现（10 平台标准/portable/Flatpak 目录；单游戏 vs 共享记忆卡）
│   ├── storage_options.py       # 可移动存储检测（/proc/mounts → 可写挂载 → 建议 download/install 子目录 + 容量）
│   ├── steam_shortcuts.py      # shortcuts.vdf / config.vdf / grid 封面；多库/Flatpak/DroidDeck、ARM Proton 解析、写前备份、DevkitGameID 去重、find_compatdata_dirs
│   ├── game_catalog.py         # CSV → 内存目录（校验、搜索、分页、平台/分类筛选、可选封面索引合并）
│   ├── archive_bundle.py       # 多分卷归档识别（.7z.001 / .partN.rar / .z01+zip / .r00+rar）
│   ├── utils.py                # 端口占用检测、局域网 IP 探测
│   ├── config.py               # 路径常量、后台维护间隔、日志（轮转 5 MB × 3）
│   └── vdf/                    # 第三方 VDF 库（文本 + 二进制格式）
├── backend/
│   ├── tianyi_share_resolver.js    # 分享链接解析兜底（Node ESM）
│   ├── tianyi_cloud_upload.js      # 云盘上传 / 列版本 / 下载（ESM，3 个 action）
│   └── tianyi_cloud_upload.cjs     # 同上，CommonJS 版，只实现 upload
├── scripts/
│   ├── fetch_runtime.sh        # 下载 aria2c / 7zz / node 到 defaults/runtime/
│   ├── fetch_ludusavi_manifest.py  # 从上游 YAML 转换 Ludusavi 清单到 defaults/ludusavi/manifest.json.gz（需 PyYAML，仅构建时）
│   ├── validate_submissions.py  # 校验 submissions/*.json（CI，无提交也通过）
│   ├── merge_submissions.py     # 合并 submissions/*.json 到目录 CSV（--dry-run 默认 / --apply）
│   ├── package.sh              # 组装 Decky 插件 zip 到 dist-artifacts/（PACKAGE_ARCH=x86_64|aarch64|all）
│   ├── doctor.sh               # 环境诊断（只读）：运行时/Steam/state/日志/端口/网络
│   ├── merge_v06_catalog.py    # 从上游 v0.6 目录合并生成 freedeckcy_catalog.csv + cover_index.csv（可复现）
│   ├── normalize_catalog_categories.py  # 原地清洗分类（去平台名/去重/模拟器兜底，--check 只检查）
│   └── validate_catalog.py     # 目录数据体检（--strict 用于 CI：重复/非法链接/分类混平台名/封面覆盖率…）
├── tests/                      # pytest 单测（575 个用例，不联网、不碰 Steam 目录；模拟器下载/部署/存档发现/恢复计划/已安装扫描/挂载检测/自检走 mock；提交校验用临时 CSV；百度 HTTP/扫码走 mock；原生库/超时为前端构建验证）
├── docs/                       # 项目文档（ARCHITECTURE / DEVELOPMENT / ROADMAP / DROIDDECK / UPSTREAM_SERVER）
├── .github/workflows/ci.yml    # CI：pytest + 目录数据体检（validate_catalog --strict）+ pnpm build
├── gl/                         # 作者手工囤的数据：按日期 dump 的 CSV、模拟器分享链接 emu.csv
└── assets/logo.png
```

> `gl/` is the directory where the author stockpiles data (e.g. `gl/2026-3-21.csv` with 4137 rows, `gl/emu.csv` with emulator resources); **the code does not read it** — at runtime only `defaults/tianyi_catalog/` is read.

---

## 5. Runtime architecture

### 5.1 Process and module tree

```text
Steam Deck (Game Mode)
│
├── Decky Loader 进程（Python）
│   ├── main.py :: Plugin  ──── 22 个 RPC ────▶  src/index.tsx（React，QAM 面板 + 设置页）
│   └── TianyiService（业务内核）
│        ├── 后台维护（main.py 启动时先跑一次，此后按 config.MAINTENANCE_INTERVAL_SECONDS 周期调用 maintenance_tick）
│        ├── TianyiStateStore    ──▶ ~/.local/share/freedeckCY/tianyi/state.json
│        ├── GameCatalog         ──▶ defaults/tianyi_catalog/*.csv + 可选 cover_index.csv（封面合并）
│        ├── ArchiveBundle       ──▶ 多分卷归档识别（主卷 / 缺失分卷 / bundled）
│        ├── Aria2Manager        ──▶ aria2c 子进程（运行时元数据 + flock 复用，JSON-RPC 控制）
│        ├── SevenZipManager     ──▶ 7zz 子进程（解压/打包；解压前 `7z t` 校验）
│        ├── SteamShortcuts      ──▶ ~/.steam/.../shortcuts.vdf、config.vdf、userdata/*/grid/
│        ├── EmulatorManager     ──▶ 10 平台注册表（首次在线下载，AppImage/zip 解包后原生运行）
│        ├── TianyiClient        ──▶ cloud.189.cn / api.cloud.189.cn（Cookie + MD5/AES/RSA 签名）
│        └── 封面缓存             ──▶ ~/.local/share/freedeckCY/tianyi/cover_cache.json（TTL 7 天）
│
├── aiohttp 本地服务（127.0.0.1:59271，只绑回环）
│   ├── /                            服务首页
│   ├── /_healthz                    健康检查
│   ├── /tianyi/library              Vue 游戏库橱窗  ── 由 Steam 内置浏览器打开
│   ├── /tianyi/library/login-bridge 二维码登录桥
│   └── /api/tianyi/*                REST 路由（旧网页/脚本用；原生库走 callable）
│
└── 外部依赖
    ├── open.e.189.cn        二维码登录
    ├── api.cloud.189.cn     accessToken / 直链 / 分片上传
    ├── node (>=18)          分享解析兜底、云存档上传（stdin/stdout JSON 子进程）
    └── 模拟器官方 release   10 平台首次安装在线下载（插件包不集成）
```

### 5.2 Three "control planes", one "data plane"

- **Control plane 1**: QAM panel ↔ `@decky/api` RPC (the 24 callable methods in `main.py`; the frontend actually uses 20 of the Tianyi RPCs; entry point [main.py:39](../main.py) `_main`, Tianyi RPC definitions start at [main.py:147](../main.py)).
- **Control plane 2**: legacy web library ↔ local HTTP API (the `/api/tianyi/*` routes in `py_modules/tianyi_http.py`, route table in `setup_routes()`; the native library goes through callables and does not depend on this plane).
- **Control plane 3**: Python ↔ Node child process (one line of JSON on stdin, one line of JSON on stdout; node resolution see [tianyi_client.py:641](../py_modules/tianyi_client.py) `_resolve_node_binary()`).
- **Data plane**: `aria2c` downloads the direct links obtained from `api.cloud.189.cn` to the local disk.

### 5.3 Division of labor between the two frontends

| | QAM panel (React) | Local web page (Vue) |
|---|---|---|
| Routes | Plugin content area + `/freedeckcy/settings` + native library `/freedeckcy/library` (modal preferred) | `/tianyi/library`, `/tianyi/library/login-bridge` (legacy local web page, fallback/debug only) |
| Pages | Login status/entry, download queue, installed preview + uninstall; settings page with 4 tabs (Paths/Install/Download/Account); game library is the native React cover grid/Hero/filters/detail | Legacy local web library, desktop debugging/fallback only |
| What it can do | View tasks, pause/resume/remove tasks, change settings, manage cloud saves, uninstall; **the native game library handles browsing/filtering/detail/install** | Legacy web fallback, no longer the main entry |
| Interaction model | QAM polling + native library controller/trackpad navigation (A/B, D-pad, L1/R1, L2/R2, touch scrolling) | Legacy web page keyboard/mouse model, see 5.8 (history) |
| How to open | Bundled with the plugin | Local HTTP service, desktop/debug fallback only |

The QAM main panel consists of `PanelSection`s such as the login/action entry, download list, and installed-game preview; the code is in `src/index.tsx` from `Content()` to the end of the file; the settings page is a `Tabs` with four pages (Paths / Install / Download / Account), entered via `SettingsPage()`.

### 5.4 Frontend call surface

**RPC (all `callable("...")` in `src/index.tsx`; called by the native library/home page on demand)**

| RPC | Purpose |
|---|---|
| `get_tianyi_panel_state` | Overall panel state (login/tasks/installed/settings), polled frequently |
| `get_tianyi_cloud_save_upload_status` / `..._restore_status` | Cloud save progress, 1.2 s while running |
| `get_tianyi_library_game_time_stats` | Library page playtime (mine/main story/total), every 2 min or retried after 3 s |
| `get_tianyi_library_url` / `get_tianyi_login_url` | Get local page URLs |
| `set_tianyi_settings` / `clear_tianyi_login` | Settings / sign out |
| `start_tianyi_cloud_save_upload` / `list_..._options` / `list_..._entries` / `plan_..._restore` / `apply_..._restore` | The cloud save five-step chain |
| `pause_tianyi_task` / `resume_tianyi_task` / `remove_tianyi_task` / `retry_tianyi_task` | Pause / resume / remove / retry a download task |
| `uninstall_tianyi_installed_game` | Uninstall (delete directory + record; optionally `delete_compatdata` to reclaim the Proton prefix) |
| `preview_tianyi_uninstall` | Uninstall preview (install directory / compatdata usage) |
| `record_tianyi_game_action` | Report start/exit events (for playtime tracking) |

**HTTP API groups (`setup_routes()` in `py_modules/tianyi_http.py`, 41 routes)**: 3 page/static-resource routes (`/tianyi/library`, `/tianyi/library/login-bridge`, static-file fallback), plus `login/*` (qr, capture, manual, clear), `catalog` (`q/platform/category/page/page_size/sort`), `catalog/cover`, **`installed` (GET list + POST launch/open-folder/uninstall)**, **`diagnostics` (GET JSON + GET export zip)**, **`update-check` (GET)**, `settings`, `install/prepare|start`, `download/create|tasks|pause|resume|remove`, `cloud-save/*`, `state`.

### 5.5 Catalog and cover system (v0.2.0 / v0.3.0)

**Catalog CSV** (`defaults/tianyi_catalog/*.csv`, env var `FREEDECKCY_GAME_CATALOG_CSV`, compatible with the legacy `FRIENDECK_GAME_CATALOG_CSV`; entry structure see [game_catalog.py:37](../py_modules/game_catalog.py) `GameCatalogEntry`):

- 16 columns: `game_id,title,category_parent,categories,package_name,server,down_url,shorturl,pwd,openpath,filesize_z,list_filesize,platform,cover_url,cover_portrait_url,steam_appid`;
- `down_url` supports two forms of Tianyi share links: `https://cloud.189.cn/t/<code>?pwd=...` and `https://cloud.189.cn/web/share?code=...` (the latter must carry `code=`); both catalog validation [game_catalog.py:138](../py_modules/game_catalog.py) `_is_valid_tianyi_url()` and the protocol layer [tianyi_client.py:188](../py_modules/tianyi_client.py) `parse_share_url()` accept both forms;
- v0.2.0 adds 4 optional columns: `platform` (default `pc`; aliases `steam/windows/win`→`pc`, `ns/nsx`→`switch`), `cover_url` (landscape), `cover_portrait_url` (portrait), `steam_appid`;
- catalog file priority ([game_catalog.py:159](../py_modules/game_catalog.py) `resolve_default_catalog_path()`): `FREEDECKCY_GAME_CATALOG_CSV` → plugin directory `freedeckcy_catalog.csv` → legacy `gamebox_all_links_20260221_234730.csv` (fallback) → `defaults/tianyi_catalog.csv` → export copy in the current directory;
- the currently bundled `freedeckcy_catalog.csv`: **7084 valid rows, 11 platforms** — PC 2540 / FC 1475 / NDS 722 / PSP 575 / GBA 553 / 3DS 305 / PS2 250 / PS1 194 / PS3 194 / MD 191 / Switch 85;
- categories cleaned (v0.3.1, see 5.6): Top12 (counts; one entry may belong to multiple categories) — Action Adventure 3483, Role-Playing 970, **Emulator 606**, Strategy/SRPG 535, Simulation 371, Casual/Puzzle 352, Shooter 272, Sports/Racing 258, Horror 119, Card/Board 59, Beat 'em up/Fighting 29, RTS 14; **platform names no longer appear in categories** (GBA/Switch etc. merged into "Emulator");
- the legacy `gamebox_all_links_20260221_234730.csv` is retained as a fallback (2845 rows / 2685 valid, all PC); the plugin can still start when the new catalog is missing;
- **Remote JSON catalog (v0.6.1/v0.6.2)**: `FREEDECKCY_CATALOG_JSON` can point to a local JSON file or an `https://…` URL (NewFreedeck-compatible format, [game_catalog.py:183](../py_modules/game_catalog.py) `resolve_default_catalog_json_path()`); remote content is cached for 6 hours ([game_catalog.py:23](../py_modules/game_catalog.py) `REMOTE_CATALOG_TTL_SECONDS`), and on fetch failure it falls back to the local CSV/cache. Disabled by default and enabled only when `FREEDECKCY_CATALOG_JSON` is explicitly set; by default the game catalog is downloaded from the server CSV via the settings page to local.

**Cover index (`defaults/tianyi_catalog/cover_index.csv`, already bundled in the repository)**:

- Path ([game_catalog.py:204](../py_modules/game_catalog.py) `resolve_default_cover_index_path()`): env `FREEDECKCY_COVER_INDEX_CSV` first (compatible with legacy `FRIENDECK_COVER_INDEX_CSV`), then plugin directory `defaults/tianyi_catalog/cover_index.csv`; the repository currently bundles **3470 rows**; when missing it is skipped automatically (covers fall back to online resolution);
- Header: `game_id,title,steam_appid,cover_url,cover_portrait_url,platform`;
- Column-name compatibility: landscape `cover_url` / `landscape_cover_url` / `cover`; portrait `cover_portrait_url` / `square_cover_url` / `portrait_url` / `portrait`; appid `steam_appid` / `app_id` / `appid`;
- Merge rules ([game_catalog.py:491](../py_modules/game_catalog.py) `_merge_cover_index()`): first an exact match by `game_id`, then by title (whitespace removed, lowercased); **only fills empty values and never overwrites values already present in the catalog CSV**; `platform` can also be filled by the index; after merging, **6823 / 7084 resources have built-in covers (96.3%)**; `summary()` reports `cover_index_total` / `with_cover` / `platforms`.

**Cover resolution priority** ([tianyi_service.py:2279](../py_modules/tianyi_service.py) `resolve_catalog_cover()`):

1. **Catalog/cover-index static cover** ([tianyi_service.py:2251](../py_modules/tianyi_service.py) `_catalog_entry_cover()`): use `cover_url`/`cover_portrait_url` from the CSV/index directly; when only `steam_appid` is present, synthesize the Steam CDN image (landscape `.../apps/<appid>/header.jpg`, portrait `.../apps/<appid>/library_600x900.jpg`), `source="catalog"`;
2. **Memory + disk cache** ([tianyi_service.py:2199](../py_modules/tianyi_service.py) `_load_cover_cache()` / [tianyi_service.py:2228](../py_modules/tianyi_service.py) `_save_cover_cache()`): `~/.local/share/freedeckCY/tianyi/cover_cache.json` (directory 0700, file 0600, temp file + `os.replace` atomic write; only unexpired entries loaded at startup); positive-result TTL **7 days** (`CATALOG_COVER_CACHE_TTL_SECONDS`), negative-result TTL **30 minutes** (`CATALOG_COVER_NEGATIVE_TTL_SECONDS`);
3. **Steam store search** (`store.steampowered.com/api/storesearch`, Chinese/China region, up to 8 candidates);
4. **ProtonDB compatibility tier** (queried additionally once an appid is found, only used as the `protondb_tier` display field).

The resolved result is written back into memory and to disk; `/api/tianyi/catalog/cover` returns `cover_url/square_cover_url/source/matched_title/app_id/protondb_tier/cached`. `cached=true` means it came from a static cover or the cache.

**Platform / category filtering**:

- `GET /api/tianyi/catalog?q=&page=&page_size=&platform=&category=` ([tianyi_http.py:270](../py_modules/tianyi_http.py) `handle_catalog()`; filtering implemented in [game_catalog.py:578](../py_modules/game_catalog.py) `list()`), returning `items/total/page/page_size/platforms/categories/platform/category`; `platforms` holds per-platform counts (descending, [game_catalog.py:550](../py_modules/game_catalog.py) `platform_counts()`), and `categories` holds the Top12 categories (`CATEGORY_FILTER_LIMIT`, [game_catalog.py:562](../py_modules/game_catalog.py) `category_counts()`);
- `platform` set to `all`/`*` means no filtering; `category` does a case-insensitive substring match against the `categories` field; platform and category can be combined (e.g. `platform=gba&category=动作冒险`);
- the legacy web library library page (history, v0.3.0): after searching it displays two filter rows; the current native library has changed to placeholder search + collapsible filter chips + cover shelves, see 5.16;
- **platform filtering is implemented** (v0.3.0): the frontend shows the platform row only when `platforms` count > 1, which is true for the current 11 platforms; selecting a platform sends the `platform` parameter and refreshes the list.
- **Emulator install (history: v0.6.0, extended later)**: at v0.6.0 only PC/GBA were allowed; since v0.11.0 all 10 emulator platforms are integrated, with 3DS/PS2/PS3 x86_64 only and hidden on aarch64 by the whitelist (see 5.10).

### 5.6 Category cleanup and catalog data health checks (v0.3.1)

**Category cleanup rules** ([game_catalog.py:89](../py_modules/game_catalog.py) `normalize_categories()`):

- Separators: `,`, `，`, `/`, `、`, `;`, `；`, `|` are all treated as category separators;
- each segment is trimmed, **deduped case-insensitively**, and the output is joined with English commas;
- remove platform-name tokens ([game_catalog.py:25](../py_modules/game_catalog.py) `PLATFORM_TOKENS`: `pc/fc/nds/psp/gba/3ds/ps1/ps2/ps3/md/switch/ns/arcade/psx`) as well as the row's own `platform`;
- emulator rows (`platform != pc`) with no categories after cleanup automatically get **"Emulator"**; PC rows stay empty if empty after cleanup;
- `GameCatalog.load()` applies this cleanup to every row, and `category_counts()` uses the same separator rules — so even if the CSV is not cleaned, the runtime will not display platform names as categories.

**Data cleanup results (v0.3.1)**: in `freedeckcy_catalog.csv`, **606 rows** have their categories rewritten; platform names are all removed; the "Emulator" category has **606 entries** (GBA 553 + Switch 42 + 11 emulator rows that originally had empty categories); `normalize_catalog_categories.py --check` now reports **0 differences** (idempotent).

**Scripts and commands**:

| Command | Purpose |
|---|---|
| `python3 scripts/normalize_catalog_categories.py <csv>` | Clean categories in place (temp file + atomic replacement); with `--check` only reports differences without writing to disk |
| `python3 scripts/validate_catalog.py <csv> [--cover-index <csv>] [--strict]` | Catalog health check: required columns/row count, duplicate `game_id`, duplicate `down_url` (warning), invalid Tianyi links, empty title/empty category, platform names mixed into categories, platform distribution, category Top10, cover coverage (including cover_index), total resource size |
| `make normalize-catalog` | Run cleanup on the bundled catalog |
| `make validate-catalog` | Run the health check on the bundled catalog + cover_index (`--strict`) |

**Current health-check results** (`make validate-catalog`, 2026-11 v0.3.1):

- 7084 rows / 16 columns; 11 platforms (PC 2540 / FC 1475 / NDS 722 / PSP 575 / GBA 553 / 3DS 305 / PS2 250 / PS1 194 / PS3 194 / MD 191 / Switch 85);
- built-in covers **3473/7084 (49.0%)**; `cover_index.csv` (3470 rows) matches **3311** by `game_id`, merged coverage **6783/7084 (95.8%)**; after the loader merges by `game_id` or title, **6823/7084 (96.3%)** (validate only counts by game_id, hence the small difference from runtime);
- total resource size **about 39 TB** (39098.5 GB);
- no errors, only 1 warning: 46 duplicate `down_url`s (one share with multiple entries, which is normal).

**CI gate**: the python job in `.github/workflows/ci.yml` runs `validate_catalog.py ... --strict` after pytest — hard errors such as duplicate `game_id`, invalid links, empty titles, or platform names mixed into categories fail CI directly; after modifying catalog data, run `make validate-catalog` locally first.

### 5.7 Packaging and deployment (`PACKAGE_ARCH` / arm64 packages, v0.4.0)

[scripts/package.sh](../scripts/package.sh) uses `PACKAGE_ARCH` to control the target architecture (default `x86_64`; optional `aarch64` / `all`):

| Command | Artifact | Notes |
|---|---|---|
| `make package` | `dist-artifacts/freedeckCY-v<version>.zip` | x86_64; automatically trims runtimes for other architectures |
| `make package-droiddeck` | `...-arm64.zip` | Equivalent to `PACKAGE_ARCH=aarch64 bash scripts/package.sh` |
| `PACKAGE_ARCH=all make package` | `...-universal.zip` | Keeps both x86_64 and aarch64 runtimes, larger size |

- Single-architecture packaging deletes the other architecture directories under `defaults/runtime/{aria2,7z,node}/*/<arch>` to avoid doubling the package size; before packaging run `make runtime ARCH=aarch64` (or `ARCH=all`) to prepare arm64 aria2c / 7zz / node (**emulators do not participate in packaging**; `make emulator-runtime` and `scripts/fetch_emulator.sh` were removed in v0.10.0);
- **the plugin package contains no emulators**: the official packages for all 10 platforms are downloaded on demand at first install (network required; failure reports an error and can be retried), which dropped the package size from about 68 MB to about 45 MB; for offline environments you can pre-place the official packages under `~/.local/share/freedeckCY/emulators/<platform>/<arch>/` (the AppImage must be executable) or point `FREEDECKCY_*_BIN` at a local build; the PS1 BIOS is still supplied by the user;
- artifact naming suffix: `PACKAGE_ARCH=aarch64` → `-arm64`, `all` → `-universal`, `x86_64` → no suffix;
- deploying to DroidDeck: put the `-arm64.zip` on phone storage and install it with Decky's **Import plugin zip** (DroidDeck overwrites by the `plugin.json` name); first use and troubleshooting see [DROIDDECK.md](DROIDDECK.en.md).

### 5.8 Legacy web library interaction and focus model (history, v0.5.0)

> This section describes the legacy web library in `defaults/tianyi_library_ui/`; the current main entry is the Decky native library in 5.16.

**Browse on open**: the page's `bootstrap()` first `GET /api/tianyi/state` to get settings, then `reloadList(1)` + `reloadInstalled()`; an empty query no longer hides results, and `hintText` shows "N resources in total, page x / y". Changes to search/platform/category/sort all return to page 1.

**Top toolbar** (`tabindex=-1`; controller focus does not enter the toolbar, it is triggered by shortcuts):

| Tool | Behavior |
|---|---|
| Game Library / Installed (with count badge) | Switches `mode`; switching to the installed tab re-fetches `GET /api/tianyi/installed` |
| Sort (game library only) | Cycles `sortOptions = ["", "title", "size_desc", "size_asc"]`, displaying "Sort: default/name/size↓/size↑" |
| Export diagnostics | The browser downloads `GET /api/tianyi/diagnostics/export` (zip) directly |
| Check updates | `GET /api/tianyi/update-check`: if a new version exists, a confirm dialog opens the Release URL; otherwise flash "Already up to date" |

**Focus order**: search box (0) → search button (1) → platform row (`platformChipCount()` items) → category row (`categoryChipCount()` items) → cards (`cardStartIndex() = 2 + platform count + category count`). Filter rows appear only when the corresponding chip count > 1; on the installed tab both chip counts are 0, so cards start at 2. **v0.5.0 fix**: the card `focus-ring` and click/activate both use `cardStartIndex()`, so they no longer shift when filter rows are present.

**Shortcuts / controller**:

| Input | Behavior |
|---|---|
| D-pad / stick | 2D focus movement; in the card area up/down jumps by actual column count (`getCardColumns()`); up/down switches between the filter rows and the cards |
| Enter / A | Activate focus: search box/button → reload; platform/category chip → filter; game card → install confirmation dialog |
| B / Esc | Back: close the confirm/install dialog first; on the installed tab return to the game library, otherwise return to the search box |
| X | Switch between "Game Library / Installed" tabs |
| Y | Game library: cycle sort; installed: open the current card's install directory |
| O | Installed tab only: open the install directory |
| Delete | Installed tab only: uninstall the current card (shows a confirm) |
| PageUp / PageDown, L1 / R1 | Previous / next page (game library only; boundaries are clamped) |
| Typing in the search box | Does not intercept normal keys; Esc exits the search box |

**Installed tab interfaces**:

- List `GET /api/tianyi/installed`: handler [tianyi_http.py:304](../py_modules/tianyi_http.py) `handle_installed_games()` → service [tianyi_service.py:6710](../py_modules/tianyi_service.py) `list_installed_games()`; returns `{total, items[]}`, sorted by `updated_at` descending, with `exists` (whether the directory still exists), `platform`/`cover_url`/`cover_portrait_url`/`steam_appid` added.
- Launch `POST /api/tianyi/installed/launch`: handler [tianyi_http.py:313](../py_modules/tianyi_http.py) `handle_installed_launch()` → [tianyi_service.py:6735](../py_modules/tianyi_service.py) `launch_installed_game()`; uses `_launch_external("steam://rungameid/<appid>")` to bring up Steam; when the AppID is missing it reports "Please launch manually from the Steam library".
- Open folder `POST /api/tianyi/installed/open-folder`: handler [tianyi_http.py:323](../py_modules/tianyi_http.py) `handle_installed_open_folder()` → [tianyi_service.py:7091](../py_modules/tianyi_service.py) `open_installed_folder()`; validates that the directory exists before `_launch_external(install_path)`.
- Uninstall `POST /api/tianyi/installed/uninstall`: handler [tianyi_http.py:350](../py_modules/tianyi_http.py) `handle_installed_uninstall()` (`delete_files` defaults to true, `delete_compatdata` defaults to false) → reuses `uninstall_installed_game()`.

Cards show the cover, install size, and playtime (showing `-` when missing); clicking a card launches it, and the buttons inside the card open the directory/uninstall respectively; uninstall uses a custom confirm and on completion refreshes both the installed list and the game library list.

**Custom confirm dialog**: `showConfirm()` records the return focus, with initial focus on "Confirm" (index 1); `confirmAction()` closes the dialog, runs the callback, and restores focus; Esc/B is equivalent to "Cancel". The installed tab's launch entry already branches by `mode`: clicking a card with the mouse, pressing Enter on the keyboard, and pressing A on the controller all call `launchInstalled()`.

### 5.9 Diagnostics and updates (v0.5.0)

**`GET /api/tianyi/diagnostics`** (JSON, local read-only; handler [tianyi_http.py:365](../py_modules/tianyi_http.py) `handle_diagnostics()` → [tianyi_service.py:7119](../py_modules/tianyi_service.py) `get_diagnostics()`): `version / python / system / arch / paths(plugin_dir, state_file, log_file, steam_root) / runtime(aria2c,7zz,node existence+size) / steam(root_exists, proton_tool, droiddeck) / catalog(total, platforms, cover_index_total, with_cover) / tasks(counts,total) / installed(total,bytes,missing_paths) / settings / recent_errors / log_tail`.

- Redaction: `_redact_text()` replaces HOME with `~`, and replaces the values of `cookie / authorization / token / sessionkey / accesstoken / uid / pwd` keys uniformly with `<redacted>`;
- Logs: `_tail_text(/tmp/freedeckcy.log, 300)` takes the last 300 lines, then filters the latest 20 lines containing `ERROR/Exception/失败` (failure) into `recent_errors`.

**`GET /api/tianyi/diagnostics/export`** (handler [tianyi_http.py:382](../py_modules/tianyi_http.py) `handle_diagnostics_export()` → [tianyi_service.py:7423](../py_modules/tianyi_service.py) `export_diagnostics()`): generates the zip in memory (`Content-Disposition: attachment; filename="freedeckcy-diagnostics.zip"`), containing:

| File | Content |
|---|---|
| `diagnostics.json` | The JSON above (`log_tail` moved out to avoid duplication with log-tail.txt) |
| `log-tail.txt` | The last 300 lines of the log (redacted the same way) |
| `README.txt` | Diagnostics bundle description + issue submission guide |

**`GET /api/tianyi/update-check`** (handler [tianyi_http.py:395](../py_modules/tianyi_http.py) `handle_update_check()` → [tianyi_service.py:7466](../py_modules/tianyi_service.py) `check_update()`): requests `https://api.github.com/repos/hulong1989/freedeckCY/releases/latest` (10 s timeout; unauthenticated GitHub API has rate limits); result `{ok, current, latest, has_update, url, name, published_at}` with `has_update = _parse_version(latest) > _parse_version(current)`; successful results are cached in memory for **1 hour** (`_update_cache`), failures return `ok: false` + `message` (network error/HTTP status).

**Shared helpers**: [tianyi_service.py:394](../py_modules/tianyi_service.py) `_tail_text()` (read the last N lines of a file), [tianyi_service.py:419](../py_modules/tianyi_service.py) `_redact_text()` (redaction), [tianyi_service.py:428](../py_modules/tianyi_service.py) `_parse_version()` (extract and compare numeric tuples from `v0.5.0`/`0.5.0-pre`), [tianyi_service.py:434](../py_modules/tianyi_service.py) `_launch_external()` (prefer `xdg-open`, else `gio open`; bring up `steam://rungameid/...` or the install directory).

### 5.10 Emulator registry and integrated platforms (since v0.6.0 / v0.7.0 registry / v0.9.0 six platforms / v0.10.0 all downloaded online / v0.11.0 ten platforms + architecture matrix)

**Registry**: [emulator_manager.py:30](../py_modules/emulator_manager.py) `EmulatorSpec` describes one platform (`platform / name / adapter / repo / download_base / assets{arch: filename} / archive(appimage|zip) / launch_args / rom_extensions / env_var / min_bytes / state_key / executables / bios_required / setup_required / setup_hint`), [emulator_manager.py:55](../py_modules/emulator_manager.py) `EMULATORS` is the registry itself; [emulator_manager.py:238](../py_modules/emulator_manager.py) `available_platforms(arch)` returns the platforms "for which the current architecture has official packages", and [emulator_manager.py:256](../py_modules/emulator_manager.py) `get_spec()` / [emulator_manager.py:265](../py_modules/emulator_manager.py) `supported_platforms()` serve the service layer and diagnostics. Currently **10 platforms are integrated, all downloaded online at first install**:

| Platform | Emulator | Version / repository | Official assets (architecture) | Launch args | ROM extensions | Dependencies / env vars |
|---|---|---|---|---|---|---|
| gba | mGBA | 0.10.5 / mgba-emu/mgba | appimage: x64 (about 25MB) / arm64 (about 24.6MB) | `-f {rom}` | `.gba` | `FREEDECKCY_MGBA_BIN` |
| psp | PPSSPP | 1.20.4 / hrydgard/ppsspp | appimage: x86_64 / aarch64 | `--fullscreen {rom}` | `.iso` `.cso` `.pbp` `.elf` | `FREEDECKCY_PPSSPP_BIN` |
| nds | melonDS | 1.1 / melonDS-emu/melonDS | AppImage inside a zip: x86_64 / aarch64 | `{rom}` | `.nds` `.dsi` `.srl` | `FREEDECKCY_MELONDS_BIN` |
| ps1 | DuckStation | `latest` / stenzek/duckstation | appimage: x64 / arm64 | `-batch -fullscreen {rom}` | `.cue` `.m3u` `.chd` `.iso` `.pbp` `.bin` | PS1 BIOS; `FREEDECKCY_DUCKSTATION_BIN` |
| fc | Mesen2 | 2.1.1 / SourMesen/Mesen2 | single executable `Mesen` inside a zip: x86_64 / ARM64 | `/fullscreen {rom}` | `.nes` `.fds` `.unf` `.unif` | `FREEDECKCY_MESEN_BIN` |
| md | Mesen2 | 2.1.1 / SourMesen/Mesen2 | same as above, sharing the cache with FC | `/fullscreen {rom}` | `.md` `.gen` `.smd` `.bin` `.32x` | same as FC |
| 3ds | Azahar | 2126.2 / azahar-emu/azahar | **SteamOS prefers the Flathub Flatpak `org.azahar_emu.Azahar`**; otherwise appimage (**x86_64 only**, `azahar.AppImage`) | `{rom}` | `.3ds` `.cci` `.cxi` `.app` (`.cia` goes through `--install`) | 3DS system files (setup); `FREEDECKCY_AZAHAR_BIN`; Flatpak `flatpak_id` |
| ps2 | PCSX2 | v2.8.2 / PCSX2/pcsx2 | appimage: **x86_64 only** | `-batch -fullscreen {rom}` | `.iso` `.chd` `.cue` `.bin` `.gz` | PS2 BIOS; `FREEDECKCY_PCSX2_BIN` |
| ps3 | RPCS3 | build-8d6b42e / RPCS3/rpcs3-binaries-linux | appimage: **x86_64 only** | `--no-gui {rom}` | `.iso` `.pkg` `.elf` `.self` | PS3 firmware (setup); `FREEDECKCY_RPCS3_BIN` |
| switch | Eden | v0.2.1 / stable.eden-emu.dev | appimage: **x86_64 + aarch64** | `{rom}` | `.nsp` `.xci` | prod.keys + firmware (setup); `FREEDECKCY_EDEN_BIN` |

**Architecture capability matrix** ([emulator_manager.py:238](../py_modules/emulator_manager.py) `available_platforms()` decides by whether `spec.assets` contains the current arch):

| Architecture | Available platforms | Notes |
|---|---|---|
| x86_64 | all 10 | GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch |
| aarch64 (DroidDeck/ARM) | **GBA/PSP/NDS/PS1/FC/MD/Switch** (7) | 3DS/PS2/PS3 have no official arm64 packages → **catalog queries filter by whitelist, so neither entries nor the platform filter bar appear**; `emulator_status()` returns `available=false` for them (the message includes "platform hidden") |

**Catalog whitelist**: `TianyiService.list_catalog()` passes `["pc", *available_platforms()]`, and `GameCatalog.list(..., allowed_platforms=...)` first filters entries by the whitelist, then computes `platforms`/`categories` counts and paging — so on aarch64 there are no hidden platform entries that "you can open but cannot install".

**Resolution order** ([emulator_manager.py:456](../py_modules/emulator_manager.py) `resolve_command()`, without the bundled-package branch):

1. The `FREEDECKCY_<PLATFORM>_BIN` environment variable (spec.env_var, pointing at an executable/AppImage);
2. The downloaded and unpacked emulator ([emulator_manager.py:320](../py_modules/emulator_manager.py) `installed_command()`): `~/.local/share/freedeckCY/emulators/<state_key>/<arch>/` ([emulator_manager.py:306](../py_modules/emulator_manager.py) `_find_spec_executable()` finds non-AppImage executables such as Mesen2 by `executables`; for AppImage unpack directories it also looks for `squashfs-root/`); GBA keeps compatibility with the legacy path `emulators/<arch>/squashfs-root/`;
3. System commands ([emulator_manager.py:334](../py_modules/emulator_manager.py) `system_command()`: `mgba/ppsspp/melonds/duckstation/Mesen` etc., see the implementation);
4. Flatpak ([emulator_manager.py:349](../py_modules/emulator_manager.py) `flatpak_command()`; mGBA's `io.mgba.mGBA`); **the 3DS exception**: the registry's `flatpak_id=org.azahar_emu.Azahar`, and when installed it directly returns `flatpak run org.azahar_emu.Azahar` (on SteamOS it is installed automatically by `_ensure_flatpak()`, see the end of this section);
5. When none is available: [emulator_manager.py:540](../py_modules/emulator_manager.py) `emulator_status()` returns `available=True, source="download", requires_setup=True` (with `asset/url/bios_*/setup_*`; no `source=bundled`); at install time [emulator_manager.py:689](../py_modules/emulator_manager.py) `ensure_emulator()` chooses the source: for 3DS the **env `FREEDECKCY_AZAHAR_BIN` takes priority**, otherwise **an installed Flatpak or SteamOS (and downloads allowed) prefers Flatpak**, and only when Flatpak is unavailable/installation fails does it fall back to AppImage download/unpacking. **If the current arch has no official asset**, it returns `available=false` (the message includes "platform hidden") and the frontend/catalog whitelist hides it. Legacy-compatible interface: [emulator_manager.py:729](../py_modules/emulator_manager.py) `ensure_mgba()`.

**On-demand download and unpacking** (no FUSE dependency):

- [emulator_manager.py:639](../py_modules/emulator_manager.py) `_download_asset()`: downloads to `~/.local/share/freedeckCY/emulators/<state_key>/<arch>/<asset name>` (HTTP non-200 / file smaller than `min_bytes` deletes the file and reports an error, retryable); **FC/MD share `state_key="mesen"`**;
- zip assets: NDS is an AppImage inside a zip; [emulator_manager.py:623](../py_modules/emulator_manager.py) `_extract_zip_emulator()` unpacks and then looks for the executable specified by `executables` (Mesen2's `Mesen`), otherwise for an `.appimage`; the AppImage then goes through [emulator_manager.py:609](../py_modules/emulator_manager.py) `_run_appimage_extract()` to unpack into the platform directory, and [emulator_manager.py:669](../py_modules/emulator_manager.py) `_ensure_extracted()` falls back to running the AppImage directly when extraction fails. Download/unpack failures are written into the install message.

**ROM selection and launch args**: [emulator_manager.py:750](../py_modules/emulator_manager.py) `find_rom_file()` filters by platform extension (table above; PS1 prefers `.m3u`, PS2 prefers `.iso` etc.), preferring the same name from `openpath`, then selecting by extension priority + path length; **PS1 multi-disc**: an existing `.m3u` is returned directly; otherwise, with multiple `.cue/.chd` files, `freedeckcy-multidisc.m3u` is generated in natural order (relative paths, `#EXTM3U`), and a single disc still returns `.cue`; [emulator_manager.py:800](../py_modules/emulator_manager.py) `create_launch_wrapper()` generates `<install_dir>/launch-freedeckcy.sh` from spec.launch_args (GBA `-f`, PSP `--fullscreen`, PS1/PS2 `-batch -fullscreen`, PS3 `--no-gui`, FC/MD `/fullscreen`, NDS/3DS/Switch take the ROM directly). **The 3DS wrapper additionally injects `QT_QPA_PLATFORM=xcb` and `SDL_VIDEODRIVER=x11`** to force XWayland and avoid Azahar crashing in Game Mode/Wayland.

**Emulator BIOS / firmware deployment (v0.12.0, `py_modules/emulator_setup.py`)**:

- After installation, [emulator_setup.py:383](../py_modules/emulator_setup.py) `setup_emulator(platform, command, seven_zip=...)` performs the deployment: first [emulator_setup.py:177](../py_modules/emulator_setup.py) `_source_files()` recursively scans `~/.local/share/freedeckCY/bios/<platform>/`, collecting `.bin/.rom/.bios/.keys/.pup/.nca`; archives such as zip/7z/rar/tar/gz/tgz/xz/bz2 are extracted with 7zz via [emulator_setup.py:152](../py_modules/emulator_setup.py) `_extract_archives()`, and the output is copied to `bios/<platform>/_extracted/` as a **persistent cache** (not extracted again next time);
- **Only create missing items / only modify a single key**: [emulator_setup.py:61](../py_modules/emulator_setup.py) `_set_ini_value()` fixes only the target key in an existing INI and keeps other configuration; existing config files are not overwritten;
- **No automatic downloading** of BIOS/firmware/keys (copyright reasons); when missing it returns a user-facing hint, and `bios_required` platforms additionally get a "BIOS not detected" message;
- Target paths and portable configs per platform:

| Platform | Deployed content | Target path / portable config |
|---|---|---|
| PS1 | BIOS (`scph*.bin`) | [emulator_setup.py:216](../py_modules/emulator_setup.py) `_write_duckstation()`: `<AppDir>/portable.txt` + `portable_data/settings/settings.ini` (`[BIOS] SearchDirectory=./bios`, `[Display] Fullscreen=true`; if already present, `_set_ini_value` repairs these two keys); the BIOS is copied to `<AppDir>/bios`, while the old `prepare_bios()` still copies it to `~/.local/share/duckstation/bios` |
| PS2 | BIOS (`*.bin`) | [emulator_setup.py:245](../py_modules/emulator_setup.py) `_write_pcsx2()`: `<AppDir>/portable.ini` + `inis/PCSX2.ini` (`[Folders] Bios=<AppDir>/bios`, `[UI] Fullscreen=true`); the BIOS is copied to three places: `<AppDir>/bios`, `~/.local/share/PCSX2/bios`, `~/.config/PCSX2/bios` |
| NDS | `bios7.bin/bios9.bin/firmware.bin/dsi_firmware.bin` etc. | [emulator_setup.py:295](../py_modules/emulator_setup.py) `_deploy_nds()`: copies to `<AppDir>` and `~/.local/share/melonDS` |
| Switch | `prod.keys`/`title.keys` + firmware `.nca` | [emulator_setup.py:304](../py_modules/emulator_setup.py) `_deploy_switch()`: keys → `~/.local/share/eden/keys/`; the `.nca` directory extracted from the firmware archive → `~/.local/share/eden/nand/system/Contents/registered/` |
| PS3 | `PS3UPDAT.PUP` | [emulator_setup.py:337](../py_modules/emulator_setup.py) `_install_rpcs3_firmware()`: if `~/.config/rpcs3/dev_flash` is empty and the RPCS3 executable is available, runs `rpcs3 --installfw <pup>` (600 s timeout; the failure reason is written into the message) |
| 3DS | system files (`sysdata`) | [emulator_setup.py:362](../py_modules/emulator_setup.py) `_deploy_3ds()`: copies to `~/.local/share/azahar-emu/sysdata` (compatible with legacy `azahar`/`citra`), and to the Flatpak data directory `~/.var/app/org.azahar_emu.Azahar/data/azahar-emu/sysdata`; `nand/`, `sdmc/`, `sysdata/` or archives under `bios/3ds/` are deployed according to their layout, preserving the directory tree and not overwriting existing files |
| GBA | portable config | [emulator_setup.py:272](../py_modules/emulator_setup.py) `_write_mgba_config()`: `portable.ini` + `qt.ini` (`[General] fullScreen=true`) |
| PSP | portable config | [emulator_setup.py:285](../py_modules/emulator_setup.py) `_write_ppsspp_config()`: `portable.txt` + `memstick/PSP/SYSTEM/ppsspp.ini` (`[General] FullScreen=True`) |

- `<AppDir>` is the directory of the executable returned by `ensure_emulator()` (after AppImage extraction it is `squashfs-root/`); if the directory is not writable, only the user data directory is written and a hint is shown;
- The deployment message is returned by `setup_emulator()`, and the service layer merges it into the **install-complete message** (it no longer sends a separate `warning` field); `emulator_status()`/plan still return `bios_required/bios_present/bios_dir` and `setup_required/setup_hint`; (a missing BIOS does not block installation; if the game still cannot be played after installing, it is usually because the files were not placed correctly / deployment was not reached)
- The legacy [emulator_manager.py:485](../py_modules/emulator_manager.py) `prepare_bios()` is retained (PS1/PS2 copy directly), and `emulator_setup.setup_emulator()` also calls it internally for compatibility with old tests/callers.

**Install chain / platform admission / UI / diagnostics**: the plan stage does not require the emulator to exist (`source=download` is allowed; platforms without assets for the current architecture are hidden); after installation `find_rom_file()` → `ensure_emulator(platform)` (first download/unpack) → `setup_emulator(platform, command, seven_zip)` (deploy BIOS/firmware/keys, write portable config) → wrapper → Steam shortcut with **Exe=launch script, LaunchOptions carrying the token, Proton=none**; the installed record writes `platform/emulator/rom_path/launcher_path`. The library page's `emulatorPlatforms` covers 10 platforms + pc, and the dialog shows the emulator name, BIOS warnings, and setup hints; the diagnostics bundle's `emulators` iterates [emulator_manager.py:265](../py_modules/emulator_manager.py) `supported_platforms()`, giving availability/hints for platforms without assets for the current architecture.

**3DS (Azahar) SteamOS-specific chain (v0.14.1)**:

- **Root cause**: Azahar's official AppImage has known compatibility issues on SteamOS (upstream issues #127: the AppImage won't open; #953: occasional Game Mode crashes), so on SteamOS 3.9.5 it prefers the **Flathub official Flatpak `org.azahar_emu.Azahar`**, bypassing AppImage/glibc/dependency issues;
- **Flatpak install/resolve chain**:
  1. [emulator_manager.py:369](../py_modules/emulator_manager.py) `_is_steamos()` reads `/etc/os-release` to detect SteamOS;
  2. [emulator_manager.py:381](../py_modules/emulator_manager.py) `flatpak_installed()` detects with `flatpak info <app_id>` (result cached for 30 s);
  3. [emulator_manager.py:422](../py_modules/emulator_manager.py) `_ensure_flatpak()`: installed → `flatpak run org.azahar_emu.Azahar`; not installed and downloads allowed → `flatpak remote-add --user --if-not-exists flathub …` + `flatpak install -y --user flathub org.azahar_emu.Azahar` (retry with a system install on failure; [emulator_manager.py:404](../py_modules/emulator_manager.py) `_run_flatpak()` with timeout/output);
  4. Path priority: **`FREEDECKCY_AZAHAR_BIN` env > installed Flatpak > SteamOS auto-install Flatpak > AppImage download/unpack**; on non-SteamOS without an installed Flatpak it still uses AppImage;
- **Status/hints**: `emulator_status()` returns `flatpak_id/flatpak_available/flatpak_installed`; when a flatpak exists the download hint changes to "install Azahar via the official Flatpak";
- **XWayland**: the 3DS wrapper fixes `QT_QPA_PLATFORM=xcb`, `SDL_VIDEODRIVER=x11` (avoiding Game Mode/Wayland crashes);
- **system files**: `~/.local/share/azahar-emu/sysdata` (compatible with legacy `azahar`/`citra`) and the Flatpak `~/.var/app/org.azahar_emu.Azahar/data/azahar-emu/sysdata`;
- **Automatic repair of existing games**: background maintenance calls [tianyi_service.py:4916](../py_modules/tianyi_service.py) `_maybe_schedule_launcher_repair()` on its first tick, creating a repair task for installed 3DS records; [tianyi_service.py:4935](../py_modules/tianyi_service.py) `_repair_emulator_launchers()` calls `ensure_emulator("3ds")` again and rewrites `launch-freedeckcy.sh` (AppImage command → Flatpak command), saves state/refreshes the installed cache; plugin shutdown cancels the task; the user does not need to reinstall the game.

### 5.11 Automatic cloud saves (Ludusavi + gamewatch, v0.8.0; v0.15.0 emulator saves)

**Ludusavi save manifest**: `defaults/ludusavi/manifest.json.gz` (**53,549 games**, gzip about 2 MB / uncompressed 14 MB, **MIT**), derived from the YAML of [mtkennerly/ludusavi-manifest](https://github.com/mtkennerly/ludusavi-manifest) and converted into compact JSON by [scripts/fetch_ludusavi_manifest.py](../scripts/fetch_ludusavi_manifest.py) before being distributed with the package (PyYAML is only needed at build time); at runtime it only reads local files and does not go online. `FREEDECKCY_LUDUSAVI_MANIFEST` can override the path ([save_manifest.py:35](../py_modules/save_manifest.py) `manifest_path()`); the in-process cache is in [save_manifest.py:50](../py_modules/save_manifest.py) `load_manifest()`.

**Matching rules** ([save_manifest.py:98](../py_modules/save_manifest.py) `match_manifest()`): first by Steam AppID (the manifest entry's `steam.id`), then by title — titles go through [save_manifest.py:31](../py_modules/save_manifest.py) `normalize_title()` (lowercase, strip non-alphanumeric/CJK characters) and support splitting on `[/|｜丨]` followed by matching each segment.

**Placeholders → Proton prefix** ([save_manifest.py:165](../py_modules/save_manifest.py) `resolve_manifest_paths()`):

| Placeholder | Resolves to (inside the Proton prefix) |
|---|---|
| `<base>` | The game install directory |
| `<home>` / `<root>` | `drive_c/users/steamuser` / `drive_c` |
| `<winAppData>` / `<winLocalAppData>` | `AppData/Roaming` / `AppData/Local` |
| `<winDocuments>` / `<winSavedGames>` | `Documents` / `Saved Games` |
| `<winProgramData>` / `<winPublic>` / `<winDir>` | `drive_c/ProgramData` / `drive_c/Users/Public` / `drive_c/Windows` |

- [save_manifest.py:132](../py_modules/save_manifest.py) `_placeholder_bases()` generates the prefixes in the table above; templates containing `*`/`?`/`[` are expanded with glob; results must exist (and directories must also be non-empty), deduped by `realpath`, with at most 200 paths per game;
- `when` conditions: [save_manifest.py:149](../py_modules/save_manifest.py) `_when_allows_proton()` only processes entries that have no `when` or contain `os: windows`; **entries that only write `os: linux`/mac are skipped** (under Proton, Windows paths are used).

**Merged with the existing Proton scan**: `_collect_cloud_save_candidates()` first resolves `compat_user_dir` and appid from the shortcut, then matches/resolves with the manifest; on a hit, `source_paths = manifest paths + Proton scan paths` (deduped), and `source_strategy` takes `ludusavi` (manifest hit and Proton miss)/`ludusavi+proton` (both)/`proton_prefix` (Proton scan only)/`install_fallback` (whitelist fallback under the install directory when there is no prefix); in diagnostics, `ludusavi = {matched, path_count}`.

**gamewatch process detection** (`py_modules/gamewatch.py`): background maintenance calls `_poll_game_watch()` every 8 seconds (inside `maintenance_tick`, [tianyi_service.py:4968](../py_modules/tianyi_service.py) `_poll_game_watch()`). [gamewatch.py:74](../py_modules/gamewatch.py) `is_game_running()` first scans `/proc/*/cmdline` ([gamewatch.py:51](../py_modules/gamewatch.py) `_is_running_proc()`, checking whether install_path appears in the command line), and falls back to [gamewatch.py:58](../py_modules/gamewatch.py) `_is_running_pgrep()` (`pgrep -f`) when there is no `/proc`; [gamewatch.py:81](../py_modules/gamewatch.py) `GameWatcher.poll()` maintains each game_id's running state: the first poll only establishes a baseline, after which `start`/`end` events are only produced on state transitions, and removed games have their state cleared ([gamewatch.py:88](../py_modules/gamewatch.py) `poll()`). The service layer **only consumes `end` events** (start events do not trigger uploads).

**Only upload the game that just exited** ([tianyi_service.py:4982](../py_modules/tianyi_service.py) `_maybe_auto_cloud_upload()`): `end` event → check the `cloud_save_auto_upload` setting (default **true**), login state, no current cloud save upload/auto-upload task, and at least **30 s** since the last auto upload (debounce) → call [tianyi_service.py:3071](../py_modules/tianyi_service.py) `start_cloud_save_upload(game_ids=[that game_id])`; after building candidates the upload task filters by `game_ids` (diagnostics `filtered_game_ids`), so it will not package other games along the way.

**Fingerprint dedupe**: [tianyi_service.py:5017](../py_modules/tianyi_service.py) `_cloud_save_fingerprint()` recursively collects files (up to **5000**) for each game's `source_paths`, and the fingerprint = `sha256(relative path|size|mtime_ns …)`; fingerprints are persisted by `game_key` in `state.json`'s `cloud_save_fingerprints`. Before uploading it is computed and compared with the previous one; if identical, **packaging/uploading is skipped** (result `status=skipped`, `reason=unchanged`); the new fingerprint is written back after a successful upload.

**Settings and UI**: the `cloud_save_auto_upload` (default true) and `cloud_save_include_emulators` (default true) settings run through `tianyi_store` (defaults/load/set_settings), `main.set_tianyi_settings`, `tianyi_http.handle_settings_set`, and the two switches under "Cloud save upload" on the QAM settings page (`ToggleField` in `src/index.tsx`).

**Emulator saves (v0.15.0, `py_modules/emulator_saves.py`)**:

- [emulator_saves.py:23](../py_modules/emulator_saves.py) `STANDARD_SAVE_DIRS`: the 10 platforms' standard directories (mGBA `~/.local/share/mgba/saves` and Flatpak `~/.var/app/io.mgba.mGBA/...`, PPSSPP `PSP/SAVEDATA`, melonDS `saves`, DuckStation `memcards`, Mesen2 `Saves`, PCSX2 `memcards`, RPCS3 `dev_hdd0/home`, Eden `nand/user/save`, 3DS's `sdmc`/`nand/user/save` and the Azahar Flatpak directory);
- [emulator_saves.py:76](../py_modules/emulator_saves.py) `PORTABLE_SUBDIRS`: portable paths relative to the install root/ROM directory/launch script directory/unpacked emulator directory (such as `saves`, `memcards`, `memstick/PSP/SAVEDATA`, `sdmc`, `nand/user/save`);
- **Per-game platforms**: [emulator_saves.py:90](../py_modules/emulator_saves.py) `PER_GAME_PLATFORMS = {gba, fc, md, nds}` — [emulator_saves.py:274](../py_modules/emulator_saves.py) `collect_emulator_save_paths()` matches by the ROM file name stem in the candidate directories ([emulator_saves.py:174](../py_modules/emulator_saves.py) `_per_game_entries()`, `.sav/.srm/.dsv/...` or a same-named directory); **if not found it returns `game_save_not_found` and never degrades to the whole directory**, avoiding uploading other games on the same platform together;
- **Shared/splittable platforms**: PSP/PS1/PS2/3DS/PS3/Switch return the whole memory card/title directory by default (empty directories are skipped), and the result is [emulator_saves.py:99](../py_modules/emulator_saves.py) `EmulatorSaveResult(per_game=False)`; **since v0.16.0 PSP/PS3/3DS first try per-game splitting** (see below) and only fall back to the shared directory when unmatched; the service layer's `_collect_cloud_save_candidates()` dedupes by the `tuple(source_paths)` signature, marking duplicate records `emulator_saves_shared` and skipping them;
- **Integration**: candidates for non-PC platforms come directly from `collect_emulator_save_paths()`, with `source_strategy="emulator_saves"` and `diagnostics.emulator_saves` carrying platform/emulator/per_game/searched/reason; when no path is found the skip_reason is `save_dir_missing` / `game_save_not_found`;
- **Switch**: the `cloud_save_include_emulators` setting defaults to **true** (store/service/main/HTTP/QAM "Include emulator saves"); when disabled, non-PC records get `emulator_saves_disabled` and do not participate in uploads;
- Platform list and path coverage see [emulator_saves.py:23](../py_modules/emulator_saves.py); 3DS/Switch directories can be large, so before uploading they are truncated/deduped by `_MAX_PATHS`/fingerprint (up to 5000 files).

**Per-game splitting (v0.16.0)**:

- **PSP/PS3**: [emulator_saves.py:91](../py_modules/emulator_saves.py) `PARAM_SFO_PLATFORMS`; uses [param_sfo.py:12](../py_modules/param_sfo.py) `read_param_sfo()` ([param_sfo.py:46](../py_modules/param_sfo.py) `find_param_sfo()` looks for `PARAM.SFO` in the save directory) to read `TITLE`, and [emulator_saves.py:92](../py_modules/emulator_saves.py) `_split_param_sfo()` normalizes and matches the game title: PSP matches `SAVEDATA/<id>/PARAM.SFO`, PS3 matches `dev_hdd0/home/<user>/savedata/<id>/PARAM.SFO`; on a match `per_game=True` and only that save directory is uploaded;
- **3DS**: [emulator_saves.py:256](../py_modules/emulator_saves.py) `TITLE_ID_PLATFORMS`; [emulator_saves.py:218](../py_modules/emulator_saves.py) `_read_3ds_title_id()` reads 16 bytes after NCSD header `0x100` in `.3ds/.cci/.cxi` (the Program ID is at `0x108`), and [emulator_saves.py:239](../py_modules/emulator_saves.py) `_split_3ds()` looks for the title directory under `title/00040000/<low8>`; on a match only that directory is uploaded;
- **Still shared**: PS1/PS2 single memory cards and the Switch `nand/user/save` directory cannot be split per game, so they keep whole-directory uploads (deduped by signature);
- Splitting failure (no PARAM.SFO / TITLE mismatch / NCSD unreadable) automatically falls back to the shared directory and does not block the upload.

**Emulator save restore (v0.16.0)**:

- `plan_cloud_save_restore()` no longer rejects manifest `source_strategy="emulator_saves"`; it goes to [tianyi_service.py:3328](../py_modules/tianyi_service.py) `_plan_emulator_save_restore()`: it finds the platform root from installed records, builds `copy_pairs`/`plan_items`, counts conflicts (`conflict_count`/`conflict_samples`), and sets `requires_confirmation`;
- **Restore root whitelist**: [emulator_saves.py:326](../py_modules/emulator_saves.py) `restore_roots(record)` returns the platform standard directories + portable roots; [emulator_saves.py:344](../py_modules/emulator_saves.py) `build_restore_targets(record, entries)` only allows files to be written inside these roots — on the same machine, if the `source_path`'s parent directory is still inside one of the roots, the restore goes to the **original parent directory**; across devices or when the path does not exist, it falls to the **first root**; **arbitrary HOME paths from the manifest are never used as targets**;
- **Conflicts and backups**: when the target already exists it counts as a conflict and requires confirmation (QAM confirm); apply reuses the existing restore flow and automatically generates `*.freedeckcy-bak-<timestamp>` backups before overwriting;
- Boundaries: cross-device 3DS restores may degrade to the root directory (when title directory structures differ); PS1/PS2/Switch are still whole-card/whole-directory overwrites and cannot pick a single game.

**Boundaries**: only auto-uploads games that gamewatch detected as "exited", and gamewatch depends on the process command line containing install_path (custom wrappers may be missed); the fingerprint only covers size/mtime and does not read file contents; PS1/PS2 single memory cards and the Switch directory are still shared (cannot be split per game).

**Boundaries**: only auto-uploads games that gamewatch detected as "exited", depending on the process command line containing install_path; since v0.16.0 restore is supported (whitelist targets, conflict confirmation, backup before overwrite); the fingerprint only covers size/mtime and does not read file contents; PS1/PS2 single memory cards and the Switch directory are still shared.

### 5.12 Game submission (repository, v0.13.0)

**Positioning**: adds catalog entries to the repository (corresponding to the original resource pool submission fields), **does not require a cloud account login**, and does not upload game files; it only collects share links and in-drive paths, merges them into `defaults/tianyi_catalog/freedeckcy_catalog.csv`, and then uses the existing "catalog → install" chain. **Since v0.14.0 both Tianyi Cloud Drive and Baidu Netdisk share links are supported** (`server=t` / `server=b` when merging). The main documentation is [submissions/README.md](../submissions/README.md) (field table/rules/commands); this section only covers the implementation and data flow.

**Two entry points**:

| Entry | File / location | Suitable for |
|---|---|---|
| GitHub Issue form | [.github/ISSUE_TEMPLATE/submit-game.yml](../.github/ISSUE_TEMPLATE/submit-game.yml) (fields name/english_name/platform/share_url/access_code/share_user_version/executable_name/openpath/categories/filesize_z/notes; 11 platforms in the dropdown) | A single entry, without opening a PR |
| JSON PR | `submissions/*.json` (copy `submissions/examples/example-pc.json` / `example-switch.json` / `example-baidu.json` and fill in per [schema.json](../submissions/schema.json)) | Batch/long-term/validatable |

- The web library toolbar's "Submit game" button (`submitGame()` in `defaults/tianyi_library_ui/app.js`) opens the Issue template above directly (`https://github.com/hulong1989/freedeckCY/issues/new?template=submit-game.yml`);
- Field correspondence with the original resource pool submission: `name/english_name/platform/share_url/access_code/share_user_version/executable_name` are kept as-is, with the additional requirement of `openpath` (needed by the installer to locate files); `categories/filesize_z/category_parent/list_filesize/notes` are catalog supplements.

**Validation chain** ([submission.py:173](../py_modules/submission.py) `validate_submission()`; batch mode [submission.py:276](../py_modules/submission.py) `validate_submission_files()`):

1. [submission.py:66](../py_modules/submission.py) `normalize_platform()`: platform alias normalization (windows/win→pc, ns→switch, 3d→3ds, psx/playstation→ps1, genesis→md, etc.), only the 11 platforms are accepted;
2. Required `name/platform/share_url/openpath`; [submission.py:72](../py_modules/submission.py) `normalize_categories()` cleans categories (remove platform names, dedupe, add "Emulator" for emulators);
3. The share link must be `https://cloud.189.cn/...` or `https://pan.baidu.com/...` / `yun.baidu.com` / `eyun.baidu.com` ([submission.py:120](../py_modules/submission.py) `_parse_share_url()` parses Tianyi `/t/<shareCode>`, `/web/share?code=` and Baidu `/s/<surl>`, `/share/init?surl=`, extracting `pwd` / `access_code`); [submission.py:156](../py_modules/submission.py) `_with_access_code()` appends `pwd=` when merging; Baidu rows use `server=b`;
4. `openpath` must not contain `..` and must not be an absolute path; `filesize_z` must be a non-negative integer; `access_code` must be 4–8 letters/digits (missing, with no `pwd` in the link, is only a warning); `executable_name` is only required for PC (a warning when left empty for emulators);
5. Duplicate shareCode: compared against both **existing catalog rows** and **other submissions in the batch**; duplicates are errors;
6. With no submission files `ok=True` (CI does not go red).

**Merge chain** ([submission.py:326](../py_modules/submission.py) `build_catalog_row()` / [submission.py:363](../py_modules/submission.py) `merge_submissions()`):

- dry-run (default) only returns the rows to write; `--apply` first confirms that all submissions have no errors, otherwise the whole batch is rejected;
- Row generation: `title = Chinese/English` (if the English is already inside the Chinese name, only the Chinese is kept), `server="t"` (Tianyi) or `"b"` (Baidu), `down_url` with `pwd` appended, `shorturl=shareCode`, `pwd`, `platform`, `category_parent` defaulting to `5`, `categories` after cleaning falling back to `未分类` when empty, `openpath/filesize_z/list_filesize` as-is;
- game_id: [submission.py:316](../py_modules/submission.py) `_next_game_id()` takes the current maximum number in the catalog + 1 and increments per row;
- Writing: write a temp CSV then atomically replace with `os.replace`; on success move the JSON to `submissions/merged/` and append to `submissions/merged/index.json` (file/game_id/title/merged_at); `submissions/merged/` is created at runtime, and not committing the merge artifacts is fine.

**CI / commands / relation to installation**:

- The `Validate game submissions` step in `.github/workflows/ci.yml` runs `python scripts/validate_submissions.py` (passes with no submissions too);
- Locally: `make validate-submissions`, `python scripts/merge_submissions.py --dry-run` / `--apply` (supports `--json`);
- Merged rows are fully isomorphic with hand-written catalog entries, and the library page/installer resolve by `platform/openpath/share_url` — i.e. "submission → review → merge into CSV → appears on the library page → install".

### 5.13 Baidu Netdisk (QR/Cookie main path, v0.17.0; OpenAPI optional fallback)

**Positioning and priority**: since v0.17.0 Baidu Netdisk uses **web QR-code login (BDUSS/Cookie)** as its main path — users do not need developer credentials/App Key and can scan a QR code in QAM to install Baidu shares; the **official OpenAPI from v0.14.0 is kept as an optional fallback** (self-built app + OAuth, see the end of this section). It still **does not use CDP or reverse-engineer web APIs**; the Cookie is only obtained through Baidu Passport's official QR interface.

**QR login chain (`py_modules/baidu_qr.py`)**:

1. [baidu_qr.py:80](../py_modules/baidu_qr.py) `request_qr()`: GETs `https://passport.baidu.com/v2/api/getqrcode?lp=pc&qrloginfrom=pc`, returning `sign` + `imgurl`;
2. [baidu_qr.py:123](../py_modules/baidu_qr.py) `fetch_qr_image()` downloads the QR PNG; the service layer's `start_baidu_qr_login()` converts it to `data:image/png;base64,...` for QAM, and **the session is kept only in memory and expires after 180 seconds** (`expires_at`);
3. [baidu_qr.py:143](../py_modules/baidu_qr.py) `poll_qr(sign)` long-polls `https://passport.baidu.com/channel/unicast`: an empty response/`errno=1` counts as waiting, `status=1` in `channel_v` is scanned, and a `v` means confirmed;
4. [baidu_qr.py:222](../py_modules/baidu_qr.py) `complete_login(v)`: GETs `https://passport.baidu.com/v3/login/main/qrbdusslogin?bduss=<v>...`, parses `data.session.bduss/stoken/ptoken`, assembles the `BDUSS=...; STOKEN=...; PTOKEN=...` Cookie, and tries to obtain the username;
5. Service layer [tianyi_service.py:922](../py_modules/tianyi_service.py) `start_baidu_qr_login()` / [tianyi_service.py:957](../py_modules/tianyi_service.py) `poll_baidu_qr_login()`: waiting→scanned→confirmed→success; on success it writes `baidu_login` in `state.json` and clears the in-memory session; [tianyi_service.py:994](../py_modules/tianyi_service.py) `cancel_baidu_qr_login()` cancels; [tianyi_service.py:999](../py_modules/tianyi_service.py) `clear_baidu_login()` signs out (clears cookie/account);
6. State persistence: [tianyi_store.py:60](../py_modules/tianyi_store.py) `BaiduLoginState(cookie, user_account, updated_at)`, and `logged_in` checks whether the Cookie contains `BDUSS=`; `state.json` has 0600 permissions, and diagnostics/logging use the same cookie/token redaction so the Cookie never enters the diagnostics bundle.

**Provider priority and install chain**:

- [tianyi_service.py:245](../py_modules/tianyi_service.py) `_share_provider()` recognizes `pan.baidu.com`/`yun.baidu.com`/`eyun.baidu.com` → `"baidu"`; in the install plan:
  1. If `store.baidu_login.cookie` contains `BDUSS=` → `provider="baidu"` (Cookie chain);
  2. Otherwise if `store.baidu_openapi.configured` → `provider="baidu_openapi"` (optional fallback);
  3. Otherwise → report "Please scan the QR code to log in to Baidu Netdisk first (Settings → Baidu Netdisk QR login)";
- Cookie chain: [baidu_client.py:477](../py_modules/baidu_client.py) `resolve_baidu_share(share_url, cookie)` parses the share/file list, and `fetch_baidu_download_url(cookie, ctx, file_id)` fetches the direct link; task aria2 uses `cookie=<Baidu Cookie>`, `referer=https://pan.baidu.com/disk/home`, `user_agent=pan.baidu.com`; tasks have `provider="baidu"`, and retry/re-download `_readd_task_download()` re-fetches the direct link by provider (an expired Cookie fails and requires scanning again);
- **OpenAPI fallback** (self-built app): [baidu_openapi_client.py:1540](../py_modules/baidu_openapi_client.py) `resolve_baidu_openapi_share_url()` + [baidu_openapi_client.py:1987](../py_modules/baidu_openapi_client.py) `fetch_baidu_openapi_download_url()`, OAuth flow [baidu_openapi_client.py:359](../py_modules/baidu_openapi_client.py) `build_baidu_oauth_authorize_url()` / [baidu_openapi_client.py:387](../py_modules/baidu_openapi_client.py) `exchange_baidu_oauth_code()` / [baidu_openapi_client.py:418](../py_modules/baidu_openapi_client.py) `refresh_baidu_oauth_token()`; tasks have `provider="baidu_openapi"`, aria2 with an empty cookie + the same Referer/UA; after installation [tianyi_service.py:7635](../py_modules/tianyi_service.py) `_cleanup_baidu_transfer_files()` calls [baidu_openapi_client.py:1285](../py_modules/baidu_openapi_client.py) `delete_baidu_openapi_transfer_file()` to clean up the `/FreedeckTmp` transfer (the Cookie chain does no transfer);
- QAM: adds a "Baidu Netdisk (QR login)" section (QR code/waiting/scanned/cancel/sign out); the original "Baidu Netdisk OpenAPI" is changed to "(optional, developer credentials required)" and kept; panel state includes `baidu_login`; HTTP `/api/tianyi/baidu/qr/{start,poll,cancel}` and `/api/tianyi/baidu/clear`, plus 4 same-named callables in `main.py`.

**Error diagnostics (since v0.18.0, v0.19.1 enhanced TLS/urllib fallback)**:

- `request_qr()` requests `getqrcode` directly; since v0.19.1/v0.19.2 the QR code, image, polling, and Cookie exchange all try the system certificate, then skip certificate verification/urllib fallback in order (compatible with SteamOS certificate chain issues), and error messages carry the concrete exception/HTTP status/response snippet;
- HTTP non-200 throws a `BaiduQrError` with status code/response snippet (e.g. `获取百度二维码 HTTP 403: ...`); during polling, HTTP ≥400 or non-timeout errors such as connection reset/DNS/SSL return `{"status":"error"}`, the service layer turns it into `stage=failed` and writes the real exception into the QAM message instead of showing waiting forever; timeouts still count as waiting;
- `start_baidu_qr_login()` logs any QR-fetch exception and returns "Failed to get Baidu QR code: <reason>"; the `stage` of `poll_baidu_qr_login()` is waiting/scanned/success/expired/failed, with `failed` carrying the concrete reason; `complete_login()` throws `BaiduQrError` on non-200/missing BDUSS.

**Click feedback and timeouts (v0.23.0)**:

- Clicking "Scan QR code to log in to Baidu Netdisk" in QAM immediately toasts "Getting Baidu QR code...";
- The frontend uses `withTimeout(startBaiduQrLogin(), 20000)` and polling `withTimeout(pollBaiduQrLogin(), 15000)`; on timeout it prompts "Timed out getting the Baidu QR code (network/TLS may be blocked; try again later or run diagnostics)";
- The backend `start_baidu_qr_login()` uses `asyncio.wait_for(request_qr(), 12)` for the QR fetch and `wait_for(fetch_qr_image(...), 10)` for the image download; timeout/exception log `Baidu QR request timed out`/`Baidu QR request failed`, and success logs `Baidu QR start requested`/`Baidu QR ready sign_len=...` (only the length, never sign/cookie);
- Timeouts/failures show the real reason as a toast, no longer "nothing happens when clicked".

**Security and boundaries**:

- The Cookie is equivalent to account credentials: it is only stored in `state.json` (0600), never written to logs/diagnostics, never handed to third parties; signing out clears it;
- The QR session exists only in memory for 180 s and becomes invalid when the plugin restarts; an expired QR code must be re-fetched; **QR confirmation/Cookie exchange has not yet been verified on a real device** (it has been verified that `getqrcode` returns a PNG and that `unicast` returns waiting when unscanned);
- The Cookie expires/is subject to risk-control restrictions, and needs re-scanning after invalidation; some shares require account permissions (access code/transfer), and the Cookie chain resolves directly under the user account's permissions;
- The OpenAPI fallback requires a self-built app/authorization; there is no public App Key; both chains **do not use CDP/web reverse engineering**; changes to Baidu interfaces may affect QR login/direct links.

### 5.14 Scanning installed games (v0.18.0; v0.21.0 entry migration + auto-added Steam shortcuts)

**Problem**: with older versions/manual installs/or when `state.json` is lost after reinstalling the plugin, the catalog already contains games but the "Installed" tab is empty. **Since v0.21.0 the entry is in QAM settings → Install → "Scan installed games"** (the native library's installed page no longer has a scan button); [tianyi_service.py:6838](../py_modules/tianyi_service.py) `scan_installed_games()` adds games in the install directory back to the installed list and automatically fills in Steam shortcuts.

**Scan logic**:

- Scope: **one level of subdirectories** under `settings.install_dir` (`os.listdir`, at most 500 entries); skips hidden directories and `compatdata/steamapps/downloads/lost+found/.freedeckcy/.cache` etc.;
- Matching: the subdirectory name is normalized ([tianyi_service.py:6780](../py_modules/tianyi_service.py) `_normalize_scan_title()`: lowercase, remove separators/special characters) and then **prefix/equality** matched against catalog entry titles (split on `[/|｜]`), taking the longest match; catalog entries are deduped by `game_id`;
- Already existing: install path already recorded → `already_recorded`; game_id already recorded → `game_id_recorded` (counted as skipped, not added again);
- Backfill: when a Steam shortcut matches (by normalized app_name/same exe realpath) it writes `steam_app_id`; emulator platforms use `find_rom_file(install_path, entry.openpath, platform)` to find the ROM; new records are written as `TianyiInstalledGame` and saved;
- **Auto-added Steam shortcuts (v0.21.0)**:
  - `steam_shortcuts.list_all_shortcuts_sync()` reads all entries in `shortcuts.vdf` and indexes them by normalized AppName + `Exe` realpath; when a same-name or same-exe appid already exists it only backfills and does not add a duplicate;
  - When there is no shortcut: for PC it first [tianyi_service.py:6790](../py_modules/tianyi_service.py) `_find_scanned_executable()` finds the exe (preferring the .exe pointed at by `entry.openpath`, otherwise recursively looking for .exe, excluding `unins/setup/redist/vcredist/crashreport/dxsetup`, sorted by title/directory name/size), then calls `add_or_update_tianyi_shortcut()` (with `freedeckcy:tianyi:<token>`, Proton settings, cover); if not found it records `shortcut_error="exe_not_found"`;
  - Emulators: `ensure_emulator(platform, allow_download=False)` (**no auto-download**) + `create_launch_wrapper()` generates `launch-freedeckcy.sh`, then registers a native shortcut (Proton=none); ROM not found → `rom_not_found`; emulator not ready → `emulator_not_ready: ...`;
  - **Second pass**: for existing PC records with `steam_app_id=0`, create the shortcut by the same rules and write the result into `steam_recovered`; return the summary `steam_added` (successfully created for new records), `steam_recovered_count`, `shortcut_error`;
  - **Steam needs a restart/user switch/reopening the library page** to see the new shortcuts (the plugin only writes `shortcuts.vdf` and does not restart Steam).
- Return: `scanned/added_count/added_games/skipped_count/skipped/unresolved_count/unresolved_dirs/installed_total/message`; unmatched directories go into `catalog_no_match` (or `catalog_missing_game_id`).

**API / UI**: the main entry is **QAM settings → Install → "Scan installed games"** (`onScanInstalledSettings` in `src/index.tsx`, with a toast "Auto-added to Steam: N"); HTTP `POST /api/tianyi/installed/scan` (`tianyi_http.handle_installed_scan`) → `main.scan_tianyi_installed_games` is still retained; the web library "Installed" toolbar's "Scan installed" (`scanInstalled()` in `app.js`) is a backup entry; the native library's installed page no longer has a scan button since v0.21.0.

**Boundaries**: only scans **one level** (nested directories/multi-level subdirectories are not recognized); the directory name must be matchable to a catalog title (renames/English name differences may yield `catalog_no_match`); it only backfills records and **does not create Steam shortcuts** (nor modify `shortcuts.vdf`); when the emulator ROM is not found, `rom_path` is empty but the record is still created; empty directories/0-byte directories are skipped.

### 5.15 Storage location selection (v0.19.0)

**Purpose**: after a Steam Deck SD card / DroidDeck external storage is mounted, let the user switch the download/install directories over with one click on the QAM "Paths" page, without typing paths manually.

**Detection (`py_modules/storage_options.py`)**:

- [storage_options.py:66](../py_modules/storage_options.py) `detect_storage_options(mounts_text, home, disk_usage)` parses `/proc/mounts` ([storage_options.py:39](../py_modules/storage_options.py) `_unescape_mount()` handles escapes such as `\040`);
- Candidate mount prefixes: [storage_options.py:9](../py_modules/storage_options.py) `_MOUNT_PREFIXES = /run/media/ (SteamOS SD) / /media/ /mnt/ /storage/ (DroidDeck) / /sdcard`; skips [storage_options.py:16](../py_modules/storage_options.py) `_SKIP_FSTYPES` (system fstypes such as proc/sysfs/tmpfs/overlay/squashfs) and [storage_options.py:36](../py_modules/storage_options.py) `_SKIP_MOUNTS` (the mount points themselves: `/`, `/run`, `/mnt`, `/media`, `/storage`, `/sdcard`);
- It must exist, be **writable**, and have a total size in `disk_usage` to be included; the same realpath is deduped; each external option provides:
  - `label` (`SD 卡 / 外置：<目录名>`, SD card / external: <directory name>), `mount`, `free_bytes/total_bytes`, `free_text/total_text`;
  - `download_dir=<mount>/freedeckCY/downloads`, `install_dir=<mount>/freedeckCY/installed`;
- Built-in options: `~/Downloads/freedeckCY` / `~/Games/freedeckCY` (home capacity); returns `{internal, external, options}`;
- The service layer [tianyi_service.py:6783](../py_modules/tianyi_service.py) `get_storage_options()` appends the current `settings.download_dir/install_dir`.

**API / UI**: `GET /api/tianyi/storage/options` (`tianyi_http.handle_storage_options`, `main.get_tianyi_storage_options`); on the QAM "Paths" page, under the download/install directories it renders "Download to <label> (X free)" and "Install to <label> (X free)" buttons per external mount; clicking one calls `savePatch` to switch the directory and refresh; with no external mount it shows "No writable SD card/external storage detected"; the original "Choose download directory/install directory" remains.

**Boundaries**: only mounted and **writable** mounts are shown (unmounted/read-only/insufficient permissions do not appear); the **mount points themselves** of `/mnt`, `/media`, `/storage` are skipped (sub-mounts such as `/mnt/sdcard` can be shown); capacity is a snapshot at detection time; it never automatically `mkdir`/formats/mounts; **it does not check whether the Steam library is on the same disk** (whether the Steam library is on the same disk after switching is up to the user); the suggested subdirectories are fixed as `freedeckCY/{downloads,installed}` (custom names are not yet supported).

### 5.16 Decky native game library (since v0.20.0, v0.27.20 visual/input refactor)

**Entry**: QAM home "Game Library" → `Router.CloseSideMenus()` → `showModal(<LibraryPage />)`; only on modal failure `Navigation.Navigate("/freedeckcy/library")`. The native page connects directly to Python through Decky callables, without depending on local HTTP, CORS, or a browser. QAM no longer shows a version marker; the version in the Decky plugin list and `package.json` is authoritative.

**Page structure**:

- **Top bar**: Back / Steam Library / title and total count / Game Library / Installed / Refresh; horizontal `Focusable flow-children="row"`.
- **Search and filters**: the search box uses a placeholder (no extra label), and the search/filter buttons share the same height and row; the filter panel renders chips by platform / category / sort, and the chips can move horizontally.
- **Hero**: the first resource with a cover as the featured slot (falling back to the first entry when there is no cover), containing "View details"; `全部游戏` (All games) opens the filter panel when there is more than one entry.
- **Category shelves**: recently updated and category sections with horizontally scrolling cards; shelves hide the default scrollbar.
- **Cards**: portrait cover, source badge (Tianyi Cloud Drive / Baidu Netdisk), installed badge, title and size/source; both grid and shelf layouts.
- **Detail modal**: `GameDetailModal` is opened via `showModal`; poster + title + tags, download source selection, a fixed bottom "Install/Exit"; the top is pushed down 40px to avoid the Steam status bar, `max-height: calc(100vh - 150px)`.
- **Installed**: launch/directory/uninstall cards; the scan entry is still in QAM settings → Install.
- **Paging**: 30 items per page with "Load more" at the bottom; shown when `catalog.items.length < catalog.total`.

**Steam Deck input model (v0.27)**:

- The root node is `Focusable flow-children="column"`; the top bar, search row, filter row, Hero actions, shelves, grid, and detail download-source/action bars are all `flow-children="row"`, so left/right moves within the same row.
- A: activate the current control; B: close the detail → exit the game library; L1/R1: switch between "Game Library / Installed"; L2/R2: scroll about 0.8 screen; D-pad up/down: scroll long lists.
- When a card gains focus it automatically does horizontal/vertical `scrollIntoView({block:"nearest", inline:"nearest"})`, and additionally corrects the shelf's horizontal position with a 14px margin; cards have `scroll-margin-top:84px` so the top focus ring is not clipped by the 60px Steam overlay.
- Shelves/grid have 16px left/right padding and 10px top padding; `scroll-snap` and `overflow-anchor` are disabled to avoid clipping the leftmost card's focus ring.
- Trackpad/touch: the root list scrolls vertically and shelves scroll horizontally, with `touch-action: pan-y/pan-x`; buttons and cards have `cursor:pointer`.
- The detail modal root node is likewise bound with `onCancel` so B can exit; the content scroll area and the action bar are separated.

**Callable chain**: `list_tianyi_catalog`, `prepare_tianyi_install`, `start_tianyi_install`, `list_tianyi_installed_games`, `launch_tianyi_installed_game`, `open_tianyi_installed_folder`, `scan_tianyi_installed_games`, etc.; install progress still appears in the QAM home task area.

**Boundaries**: the detail modal depends on `showModal`; task progress is not on the library page; uninstall always uses `delete_files=true`; scanning still only recognizes one level under `settings.install_dir`. The legacy local web library `defaults/tianyi_library_ui/` is only for desktop debugging/fallback and is not the main entry; the standalone web submission/management system is not in this repository and is not in the plugin package.

### 5.16.1 Bilingual UI and language selection (v0.28.14)

- The first time the QAM plugin is opened, `Content` checks `localStorage["freedeckcy.language"]`; if unset it renders `LanguageChooser` (Chinese / English), and the choice is saved and re-rendered immediately.
- `LanguageSection` is rendered on both the QAM home page and the Settings page and can be switched at any time; language is pure frontend state with no backend settings field; switching translates/restores the current DOM immediately.
- `src/i18n.ts` provides `getLanguage/hasLanguage/setLanguage/useLanguage`, `translateString()`, and a DOM translation layer.
- `src/i18n.en.ts` is the English mapping for 235 Chinese UI terms; the root nodes of QAM, settings, native library, and detail modal carry `data-fdc-i18n`, and a MutationObserver translates text and the placeholder/title/aria-label when the language is en, restoring the original text when switching back to Chinese.
- Supports regex translation of dynamic counts (`N 款游戏`, `N installed`, `剩余`, `已显示`, etc.); when a term is not in the dictionary, a longest-phrase-first phrase fallback is used.
- **Toasts are outside the DOM translation scope**: `toaster.toast` is wrapped and applies `translateString` to title/body, so update-check/download/diagnostics popups are translated.
- The translation observer is not started at module load: Decky components run in a shared JS context, and QAM/BigPicture belong to different documents/realms. `useI18nRoot(ref)` starts from the real root node's `ownerDocument` after Content/Settings/Library/Detail mount; the TreeWalker/MutationObserver/timer all use `defaultView`, and `nodeType` is used instead of the cross-realm-unreliable `instanceof`.
- The dictionary actually has 434 entries (235 directly authored Chinese + 199 decoded from `\uXXXX` escapes); the language choice only affects the plugin UI; Steam's own UI and backend dynamic error messages may still be in Chinese.

### 5.16.2 Install reliability: verify / repair / health / diagnostics / source fallback / preflight (v0.28.14)

**Installed-game verify**: callable `verify_tianyi_installed_game` → [tianyi_service.py:7876](../py_modules/tianyi_service.py) `verify_installed_game(game_id)`.

- PC: install folder exists and an `.exe` can be located from `openpath`/`executable_name`;
- Emulator: `rom_path` exists and `launcher_path` launcher script exists;
- Common: `resolve_tianyi_shortcut_sync()` finds the Steam shortcut (returns `appid`).

It returns `{ok, needs_reinstall, checks[{id,ok,message,path,appid}]}`. `ok` only covers critical items (folder/main executable/ROM/launcher); a missing shortcut is repairable and does not force a reinstall. A missing folder or main executable/ROM sets `needs_reinstall=true`, and the UI clearly says a re-download is required.

**One-click repair**: callable `repair_tianyi_installed_game` → `repair_installed_game()`. It verifies first and returns immediately (without pretending success) when `needs_reinstall=true`; otherwise it rebuilds the Steam shortcut, Proton mapping and four-piece artwork (`add_or_update_tianyi_shortcut`, falling back from logo to portrait/landscape), writes back the new `steam_app_id`, verifies again and returns `before/after/actions`. The "Verify" button on installed cards shows per-item results and repair actions.

**Full health check**: callable `get_tianyi_installed_health` → `installed_health_report()`. It walks `store.installed_games` and verifies each game (one failure does not abort the run), returning `{total, ok, needs_repair, needs_reinstall, items[]}`; the library top-bar "Health Check" button summarizes OK/issues/reinstall-required and lists abnormal games (up to 12); when repairable items exist the button becomes "Repair Repairable Items", calling `repair_installed_game()` for each and refreshing the installed list with a success/failure summary, while `needs_reinstall` items only prompt a re-download.

**Failed-task diagnostics**: callable `diagnose_tianyi_task` → `diagnose_task(task_id)`. It infers the stage (`resolve`/`download`/`extract`/`install`) from `error_reason`/`install_message`/status, returns fixed suggestions, and computes `can_retry` and `can_fallback` (`_has_alternate_source()` matches same title/platform but a different provider). The QAM "Diagnostics" button on failed tasks shows stage, reason and suggestions.

**Source fallback**: callable `retry_tianyi_task_with_fallback` → `retry_task_with_fallback(task_id)`: finds another catalog entry with the same title/platform and a non-empty `down_url` on a different provider, then calls `start_install()` to create a new task; the old task is kept for comparison. When `retry_task()` cannot re-fetch the direct link it calls fallback once automatically and marks the result `auto_fallback=true`; without an alternate source it keeps the old failure path and reports "no alternate source".

**Pre-install environment preflight**: callable `preflight_tianyi_install` → `preflight_install()`:

- Download/install folders: if they exist, check `os.access(W_OK)`; if missing, walk up to the nearest existing ancestor and check writability, returning `message="folder does not exist; it will be created automatically"`. **Preflight itself never creates folders**;
- Disk space: read `shutil.disk_usage().free` for the download/install folder (or nearest ancestor) separately; below `PREFLIGHT_MIN_FREE_BYTES=512MB` is an issue;
- Returns `{ok, checks[{id,ok,path,exists,free_bytes,message}], min_free_bytes}`.

There are two UI entry points: a new "Environment" Tab in settings (`InstallPreflightSection`, manual check with per-item path/status/advice), and an automatic call before the install confirmation modal (15s timeout). On issues the failed items are appended to the plan description and the button becomes "Download Anyway", without blocking a deliberate install. The real size-based check remains in `_build_install_plan()`'s `can_install`.

**Tests**: `tests/test_install_reliability.py` covers preflight (writable/creatable/not-writable/low-space/read failure), PC and emulator verification, repair skip and rebuild, health aggregation and per-item errors, diagnostics stage/fallback detection, and retry auto-fallback/no-fallback/active-task rejection.

### 5.17 Diagnostics self-check (v0.22.0)

**QAM entry**: the settings page adds a "Diagnostics" Tab (`src/index.tsx`, `onRunDiagnostics`/`onExportDiagnostics`):

- "Run self-check" calls the callable `run_tianyi_diagnostics` (`main.py`) → [tianyi_service.py:7234](../py_modules/tianyi_service.py) `run_diagnostics(include_network=True)`; returns `{generated_at, version, arch, summary{ok,warn,fail,skip}, checks[{id,label,status,detail,fix}]}`; QAM colors by status (ok/warn/fail/skip) and shows `建议：fix` (Suggestion: fix);
- "Export diagnostics bundle" calls `export_tianyi_diagnostics_file` → [tianyi_service.py:7446](../py_modules/tianyi_service.py) `export_diagnostics_to_downloads()`: writes `freedeckcy-diagnostics-YYYYmmdd-HHMMSS.zip` (**0600**) into `settings.download_dir` (if empty, `plugin.downloads_dir`, then falling back to `~/Downloads`), and returns `path/filename/size/message`, with QAM toasting the path;
- HTTP retains `POST /api/tianyi/diagnostics/run` (`tianyi_http.handle_diagnostics_run`) for web pages/scripts.

**Checks** (each carries `status`/`detail`/`fix`):

| Check | Content |
|---|---|
| `plugin` | Plugin version/directory (warn when missing) |
| `state_dir` | `state.json` directory writable, state permissions |
| `download_dir` / `install_dir` | Exists/writable/free space; **< 2 GB warns** |
| `runtime_aria2` / `runtime_7z` / `runtime_node` | The bundled `defaults/runtime/<component>/<arch>/` has an executable and runs `--version` (7zz uses `i`, 5s timeout) |
| `catalog` | Catalog entry count/platform count/cover index count |
| `steam` | Steam root + `list_all_shortcuts_sync()` shortcut count (warn when not logged in/unreadable) |
| `storage` | The number and labels of SD/external mounts from `detect_storage_options()` |
| `network_tianyi` | GET `https://cloud.189.cn/` (HTTP <500 is ok, otherwise warn) |
| `baidu_qr` | `request_qr()` (12s timeout) **only outputs the sign length**, never sign/cookie; on failure the fix hints at TLS/certificate/connectivity |
| `tasks` | Task count/failure count/installed count (warn when there are failed tasks) |
| `log` | The number of `ERROR/Exception/失败` (failure) lines in the last 300 lines of `/tmp/freedeckcy.log` (warn when any) |

**Diagnostics bundle content**: `diagnostics.json` (version/paths/runtime/tasks/installed stats, cookie/token redacted, HOME→~), `self-check.json` (the self-check results above), `log-tail.txt` (300 lines, redacted the same way), `README.txt` (description); when packaging it runs the self-check once more (`export_diagnostics()`). **Network checks can be skipped**: `run_diagnostics(include_network=False)` sends no network requests and records Baidu QR as `skip`; the self-check **never repairs automatically**, it only gives suggestions; the exported bundle is only written to the local downloads directory and never uploaded.

---

## 6. Chain A: from clicking "Install" to the game appearing in the Steam library

```text
[Decky 原生库]点击卡片
   │ callable prepare_tianyi_install  {game_id 或 share_url}
   ▼
_build_install_plan()
   ├─ share_url 接受天翼（cloud.189.cn / *.189.cn）或百度（pan.baidu.com / yun.baidu.com / eyun.baidu.com）
   ├─ 查 CSV → share_url / openpath / title / platform
   ├─ platform 校验：pc + available_platforms(arch)（10 个模拟器平台，按架构裁剪）放行
   ├─ 模拟器平台：emulator_status(platform) 判断（未安装也可返回 source=download）
   │    └─ 用 openpath 的 ROM 文件名 resolve_share(target_name, max_pages=40) 分页查找
   │         └─ 分享里找不到目标 ROM → 报错（附已扫描文件示例）
   ├─ resolve_share(cookie)                ← PC：拿文件清单 fileId + size
   └─ 空间探针：下载/安装目录可用空间判定 + 解压后体积估算
   │ 返回 plan（含 can_install / files[] / platform / emulator / emulator_info / rom_target / 空间与估算字段）
   ▼ 用户确认（弹窗里显示体积、ProtonDB 评级）
   │ POST /api/tianyi/install/start
   ▼
start_install()                              ← 全局互斥，避免重复下单
   ├─ _create_tasks_from_plan()
   │    ├─ 本次计划共用一个 group_id，group_total = 文件数
   │    ├─ aria2.ensure_running()（优先附着仍存活的 aria2 实例，见 6.4）
   │    ├─ fetch_access_token(cookie)
   │    └─ 每个文件：fetch_download_url() → aria2.addUri(...) →
   │         写 TianyiTaskRecord（file_size = 清单里的预期大小）
   ▼
[QAM 每 900ms 轮询 / 后台维护每 8s] refresh_tasks()
   ├─ aria2.tellStatus(gid) 查进度（含 errorCode）
   ├─ 查询失败 → 进入重启恢复链（见 6.1）
   └─ status=="complete" → 文件大小校验（_verify_downloaded_file）
        ├─ 不一致 → 先自愈一次：隔离坏文件（*.freedeckcy-size-mismatch-<ts>）
        │             + 原直链重下；仍失败才 error
        └─ 一致 → _maybe_schedule_group_post_process()：等整组都 complete
   ▼
_post_process_completed_task()               ← 按安装目录加锁，整组一次性处理
   ├─ 识别多分卷归档（.7z.001 / .part1.rar / .z01+zip ...，见 6.3）
   │    ├─ 缺分卷 → 整组失败，列出缺失文件名
   │    └─ 只解主卷；其余任务标记 install_status="bundled"
   ├─ 每个要解压的包：等 .aria2 释放且大小稳定两次（_wait_payload_settled）
   │    → 预检空文件/HTML 错误页（_precheck_archive_payload）
   │    → `7z t` 完整性校验（best-effort：7z 缺失/不可执行时跳过，见 6.6）
   │         └─ 失败 → 隔离坏包 + 原直链自动重下一次（每任务一次）；
   │                  不置 post_processed，重下完成后自动重新安装
   │    → 空间检查 → 7zz 强制解压（分卷必须走 7z）→ staging 合并
   ├─ 全部成功 → _finalize_group_install()
   │    ├─ 写 TianyiInstalledGame 记录（体积 = 组内各包之和；gba 另存 platform/emulator/rom_path/launcher_path）
   │    ├─ 只以"代表任务"（created_at 最早）注册一次 Steam（见 6.5）
   │    │    └─ 模拟器平台：find_rom_file(platform) → ensure_emulator(platform)（模拟器首次按需下载）
   │    │         → 生成 launch-freedeckcy.sh → 快捷方式 Exe=脚本、LaunchOptions 带 token、Proton=none
   │    └─ auto_delete_package 为真则删除组内全部压缩包
   └─ 任一包失败 → 整组不注册 Steam；已解压文件保留，install_message 汇总
   ▼
Steam 库里出现游戏（写完后备份 + 回读校验；需重启 Steam 生效）
```

**On-disk locations**

| Content | Path |
|---|---|
| Downloaded archives | `<download_dir>` (default `~/Downloads`) |
| Install directory | `<install_dir>` (default `<download_dir>/installed`); subdirectory name = first segment of openpath |
| Tasks/installed/login/settings | `~/.local/share/freedeckCY/tianyi/state.json` |
| aria2 session | `~/.local/share/freedeckCY/tianyi/aria2/` |
| Cover cache | `~/.local/share/freedeckCY/tianyi/cover_cache.json` (0600, positive cache 7 days / negative cache 30 minutes) |
| Runtime binaries | `defaults/runtime/{aria2,7z}/<arch>/`, `defaults/runtime/node/<arch>/bin/node` (emulators are not in the package) |
| Emulator unpacked output | `~/.local/share/freedeckCY/emulators/<platform>/<arch>/squashfs-root/` (AppRun, no FUSE; FC/MD share `mesen/`; GBA compatible with the legacy `emulators/<arch>/`) |
| Emulator assets downloaded on demand | `~/.local/share/freedeckCY/emulators/<platform>/<arch>/<official asset name>` (all emulators download at first install) |
| GBA launch script | `<install_dir>/launch-freedeckcy.sh` (`exec <mGBA> -f <rom>`) |
| Logs | `/tmp/freedeckcy.log` |

**Key function index (install chain)**

| Stage | Code location |
|---|---|
| HTTP entry prepare / start | [tianyi_http.py:608](../py_modules/tianyi_http.py) `handle_prepare_install` / [tianyi_http.py:629](../py_modules/tianyi_http.py) `handle_start_install` |
| Install plan + space probe | [tianyi_service.py:1612](../py_modules/tianyi_service.py) `_build_install_plan()` |
| Create download tasks | [tianyi_service.py:1344](../py_modules/tianyi_service.py) `_create_tasks_from_plan()` |
| Task status sync | [tianyi_service.py:5727](../py_modules/tianyi_service.py) `refresh_tasks()` |
| Install scheduling / directory-level mutex | [tianyi_service.py:5990](../py_modules/tianyi_service.py) `_schedule_post_process_task()` / [tianyi_service.py:6340](../py_modules/tianyi_service.py) `_post_process_completed_task()` / [tianyi_service.py:6451](../py_modules/tianyi_service.py) `_install_lock_for()` |
| Extraction / staging merge | [tianyi_service.py:7527](../py_modules/tianyi_service.py) `_extract_archive_to_dir()` / [tianyi_service.py:7506](../py_modules/tianyi_service.py) `_merge_extracted_content()` |
| Write Steam shortcut / Proton / cover | [steam_shortcuts.py:432](../py_modules/steam_shortcuts.py) `_upsert_shortcut_sync()`, [steam_shortcuts.py:563](../py_modules/steam_shortcuts.py) `_set_proton_mapping_sync()`, [steam_shortcuts.py:813](../py_modules/steam_shortcuts.py) `_apply_grid_assets()` |
| Non-Steam appid | [steam_shortcuts.py:425](../py_modules/steam_shortcuts.py) `_generate_non_steam_app_id()` |
| aria2 order placement | [aria2_manager.py:452](../py_modules/aria2_manager.py) `add_uri()` |
| Share resolution / direct link | [tianyi_client.py:1081](../py_modules/tianyi_client.py) `resolve_share()`, [tianyi_client.py:1640](../py_modules/tianyi_client.py) `fetch_access_token()`, [tianyi_client.py:1683](../py_modules/tianyi_client.py) `fetch_download_url()` |
| Background maintenance | [tianyi_service.py:8270](../py_modules/tianyi_service.py) `maintenance_tick()` |
| Multi-volume archive detection | [archive_bundle.py:88](../py_modules/archive_bundle.py) `detect_archive_sets()` / [archive_bundle.py:228](../py_modules/archive_bundle.py) `build_bundle_index()` |
| Settle / precheck before extraction | [tianyi_service.py:8316](../py_modules/tianyi_service.py) `_wait_payload_settled()` / [tianyi_service.py:650](../py_modules/tianyi_service.py) `_precheck_archive_payload()` |
| Only extract main volume / bundled | [tianyi_service.py:7653](../py_modules/tianyi_service.py) `_post_process_completed_task()` / [tianyi_service.py:7697](../py_modules/tianyi_service.py) `_install_payload()` |
| Bad-file quarantine / self-healing | [tianyi_service.py:7527](../py_modules/tianyi_service.py) `_quarantine_download_file()` |
| aria2 runtime reuse (meta+flock) | [aria2_manager.py:158](../py_modules/aria2_manager.py) `_read_runtime_meta()` / [aria2_manager.py:248](../py_modules/aria2_manager.py) `_attach_existing()` / [aria2_manager.py:205](../py_modules/aria2_manager.py) `_try_acquire_owner_lock()` |
| In-place direct-link replacement | [aria2_manager.py:510](../py_modules/aria2_manager.py) `replace_uri()` |
| Restart recovery (gid lost) | [tianyi_service.py:7740](../py_modules/tianyi_service.py) `_try_recover_task()` / [tianyi_service.py:6226](../py_modules/tianyi_service.py) `_file_matches_expected_size()` / [tianyi_service.py:6190](../py_modules/tianyi_service.py) `_readd_task_download()` |
| Multi-volume group install | [tianyi_service.py:6115](../py_modules/tianyi_service.py) `_install_group_members()` / [tianyi_service.py:6246](../py_modules/tianyi_service.py) `_maybe_schedule_group_post_process()` / [tianyi_service.py:6145](../py_modules/tianyi_service.py) `_install_payload()` / [tianyi_service.py:6161](../py_modules/tianyi_service.py) `_finalize_group_install()` |
| Download integrity check | [tianyi_service.py:7740](../py_modules/tianyi_service.py) `_verify_downloaded_file()` |
| Archive `7z t` validation | [seven_zip_manager.py:66](../py_modules/seven_zip_manager.py) `test_archive()` |
| Auto re-download on validation failure | [tianyi_service.py:7835](../py_modules/tianyi_service.py) `_schedule_archive_repair()` / [tianyi_service.py:6126](../py_modules/tianyi_service.py) `ArchiveRepairScheduled` |
| Failed task retry | [tianyi_service.py:7718](../py_modules/tianyi_service.py) `retry_task()` |
| Uninstall preview / compatdata reclamation | [tianyi_service.py:253](../py_modules/tianyi_service.py) `preview_uninstall()` / [tianyi_service.py:6534](../py_modules/tianyi_service.py) `_can_remove_compatdata_dir()` / [steam_shortcuts.py:165](../py_modules/steam_shortcuts.py) `find_compatdata_dirs()` |
| aria2 full list (for recovery) | [aria2_manager.py:534](../py_modules/aria2_manager.py) `list_downloads()` |

**A few commonly misunderstood points**

- **The truth about "no speed limit"**: there is no `--max-*-limit` anywhere in the repository, so it is "no cap set" rather than acceleration. Actual speed depends on the Tianyi direct link and the per-file split count (default `split=16`, aria2 global concurrency 3).
- **No transfer**: shared resources are not saved to the user's cloud drive; the direct link is handed to aria2 for download (this differs from many "transfer-type" tools).
- **`freedeckcy:tianyi:<game_id>`** is only a marker written into LaunchOptions; this plugin has no runtime code that reads it (playtime tracking goes through Steam global events, see 7.3).
- **exe locating is heuristic**: when the CSV's `openpath` is accurate it is relied upon; when not, it relies on "leaf filename search" and "the first executable in the directory", which is the root cause of many "nothing happens after clicking install".
- **Writing `shortcuts.vdf` requires restarting Steam** to see it.
- **error tasks will not automatically retry installation**: remove the errored task first; in multi-volume scenarios, removing the failed package lets the remaining completed volumes continue installing (see 6.2).

### 6.1 Restart recovery: gid changes and direct-link expiration

Plugin reload now attaches to a still-alive aria2 (see 6.4), so **the gid usually does not change**; but after a **device restart** the aria2 session is rebuilt, the gid changes, and the direct link may expire. When the old gid stored in `state.json` cannot be found, `refresh_tasks()` recovers tasks whose query failed in the following order ([tianyi_service.py:5444](../py_modules/tianyi_service.py) `_try_recover_task()` / [tianyi_service.py:5434](../py_modules/tianyi_service.py) `_file_matches_expected_size()` / [tianyi_service.py:6190](../py_modules/tianyi_service.py) `_readd_task_download()`):

```text
aria2.tellStatus(旧 gid) 失败（GID not found / aria2 未运行）
   │
   ├─ ① 按文件路径重新认领：aria2.listDownloads() 建「落盘路径 → gid」索引，
   │     找到同一路径的新任务 → 更新 gid，继续查进度
   ├─ ② 文件其实已下完：本地文件大小 == 清单 file_size → 直接判 complete，
   │     并调度该分组的安装
   ├─ ③ 直链过期 / 会话丢失：先 `aria2.changeUri` 原地换链（保留 gid 与进度），
   │     换链失败再 addUri（continue=true 可续传）；每任务每进程只尝试一次
   └─ ④ 以上都不行：连续 TASK_SYNC_ERROR_THRESHOLD（5）轮查询失败才标 error
```

Note: ② only compares file sizes, not a hash check; ③ continues downloading/resuming after the link change/re-add, reusing as many pieces as possible; when the old session is corrupted (aria2 control file error/truncation) it quarantines the partial file before retrying once.

### 6.2 Multi-volume / multi-package install semantics

The same install plan (the multiple files returned by `install/prepare`) shares one `group_id` when tasks are created, with `group_total` recording the package count. **The "representative task" = the one with the earliest `created_at` in the group** ([tianyi_service.py:6115](../py_modules/tianyi_service.py) `_install_group_members()` sorts by `(created_at, task_id)`), and both Steam registration and the installed record are based on it.

- **Download stage**: `_maybe_schedule_group_post_process()` only schedules installation after all tasks in the group are `complete`.
  - If a package in the group is `error`: no installation; completed packages show "A volume in the same install plan failed to download; remove the failed task to continue installation";
  - After the user removes the failed task (`removed` status does not participate in grouping), the remaining complete volumes are rescheduled for installation.
- **Install stage**: extract package by package into the same target directory (serialized by directory-level mutex); only when all succeed does [tianyi_service.py:6246](../py_modules/tianyi_service.py) `_finalize_group_install()`:
  - Write one installed record, `size_bytes` = the sum of the group packages' `file_size`;
  - Register the Steam shortcut / Proton / cover only once (using the representative task);
  - When `auto_delete_package` is true, delete all archives in the group;
  - Multi-volume archives only extract the main volume, marking the rest `bundled` (see 6.3).
- **Install-stage failure**: if any package fails, the whole group does not register Steam, and already-extracted files are kept; `install_message` keeps the concrete reason for a single file and summarizes as "x/y file packages errored" for multiple files, and the user must remove the problematic task and re-initiate install/download.

### 6.3 Multi-volume archives (.7z.001 / .part1.rar / .z01+zip …)

`py_modules/archive_bundle.py` (a simplified implementation referencing v0.6's `archive_detector.py`) recognizes 6 kinds of volume naming:

| Type | Example | Main volume (entry volume) |
|---|---|---|
| Numeric-suffix 7z | `game.7z.001`, `game.7z.002` | `.001` |
| Numeric-suffix zip/rar | `game.zip.001`, `game.rar.001` | `.001` |
| RAR part | `game.part1.rar`, `game.part2.rar` | `.part1.rar` |
| ZIP volumes | `game.z01` + `game.zip` | `game.zip` |
| Legacy RAR volumes | `game.r00` + `game.rar` | `game.rar` |

Handling at install time:

- `detect_archive_sets()` recognizes volume sets from **all downloaded files in the same group**, and `build_bundle_index()` provides "path → (set, is main volume)";
- When `missing_parts` is non-empty (e.g. `.002` is missing) → the whole group installation fails, and `install_message` lists the missing filenames (up to 3); it never force-extracts an incomplete volume set;
- Only the main volume is extracted; the other volume tasks have `install_status` marked **`bundled`** with the message "volume file, extracted together by the main volume", and keep that semantic after installation completes (not changed to installed);
- Extraction uses `_extract_archive_to_dir(..., force_seven_zip=True)` to force 7z — volumes cannot be handed to `shutil` by extension;
- Space is estimated **from the sum of all volume sizes** before extraction.

### 6.4 aria2 runtime reuse (meta + flock)

v0.6 recorded aria2's RPC address/secret/pid in `aria2.runtime.json` and used flock to ensure only one instance per directory is responsible for starting it; this repository follows the same idea (filenames `aria2-runtime.json` / `aria2-runtime.lock`, placed in `~/.local/share/freedeckCY/tianyi/aria2/`, the same directory as `aria2.session` and `aria2.log`):

```text
ensure_running()
   ├─ ① 内存里有 runtime 且进程/PID 存活 → 直接 getVersion 复用
   ├─ ② 读 aria2-runtime.json：pid 存活且 getVersion 通过 → 附着（attached=true）
   │      → 插件重载后 gid 不变，在途任务继续走
   ├─ ③ 拿不到 flock（其它插件实例正在启动）→ 短暂轮询附着，不重复起进程
   └─ ④ 获得 flock 且无可用实例 → 启动 aria2 并写 meta（owned=true）
```

- `stop()` only stops instances it **owns**: uninstalling the plugin will not kill an aria2 still being reused by other instances;
- Meta writing uses a temp file + `os.replace` atomic replacement; on start failure/stop it clears the meta and releases the lock;
- Troubleshooting: `ls ~/.local/share/freedeckCY/tianyi/aria2/` should show `aria2-runtime.json`/`aria2-runtime.lock`, `aria2.log` (the start args include `--log`); these two files tell you "whether the current instance can be attached to".

### 6.5 Steam write strategy (token / incremental / backup / read-back)

- **Token dedupe**: a new entry writes both `LaunchOptions="freedeckcy:tianyi:<token>"` and `DevkitGameID=<token>`; matching reads either `DevkitGameID` or the legacy `LaunchOptions` ([steam_shortcuts.py:413](../py_modules/steam_shortcuts.py) `_shortcut_tokens()`), avoiding duplicate entries after the user manually edits launch options; the launch prefix constant is `FREEDECKCY_LAUNCH_PREFIX`.
- **Diff-based write**: when all target entry fields match and the file exists, returns `action="unchanged"` and does not rewrite the file.
- **Backup before write**: `shortcuts.vdf` / `config.vdf` are copied to `*.freedeckcy-bak-<YYYYmmdd_HHMMSS>` before writing ([steam_shortcuts.py:380](../py_modules/steam_shortcuts.py) `_backup_file()`), keeping only the most recent **12** backups of each kind; the `config.vdf` Proton mapping rewrite is backed up the same way.
- **Proton tool resolution and settings (v0.4.0)**: the `proton_tool` setting (default `auto`) lives in [tianyi_store.py:94](../py_modules/tianyi_store.py) `TianyiSettings`; RPC/HTTP pass it through [main.py:282](../main.py) `set_tianyi_settings()`, [tianyi_http.py:473](../py_modules/tianyi_http.py) `handle_settings_get()` / [tianyi_http.py:482](../py_modules/tianyi_http.py) `handle_settings_set()`, and the service layer [tianyi_service.py:6145](../py_modules/tianyi_service.py) `update_settings()`; `GET /api/tianyi/settings` additionally returns `proton_tool_resolved` / `droiddeck_detected` ([tianyi_service.py:7835](../py_modules/tianyi_service.py) `get_settings()`). When writing the shortcut, [steam_shortcuts.py:1068](../py_modules/steam_shortcuts.py) `add_or_update_tianyi_shortcut(proton_tool=...)`: `auto` → `detect_proton_tool()`, `none`/`skip`/`disabled` → skip mapping, any other value is used directly as the tool name; finally `_set_proton_mapping_sync()` writes it into `config.vdf`'s `CompatToolMapping`.
- **Read-back after write**: after writing `shortcuts.vdf` it is read back to confirm the token really landed on disk, otherwise failure is returned (preventing "assuming it was written successfully").
- **compatdata username scoring**: `find_compat_user_dir()` first tries `steamuser` / `deck` / `root`, then scores and picks custom Wine usernames by `AppData` (+3)/`Documents` (+2)/`Saved Games` (+2) (referencing a similar implementation in v0.6).

### 6.6 Archive validation and automatic re-download (`7z t`, best-effort)

Since v0.1.1, integrity validation with `7z t` runs before extraction (`seven_zip.test_archive()`, default timeout 900 s):

- **best-effort boundary**: when 7z is not found, or 7z cannot be executed (e.g. running the Linux 7zz on macOS gives `Exec format error`), it returns `(True, "跳过校验: …")` and **does not block installation** — the real error will only surface in the later extraction stage. So "no 7z" does not equal "cannot install", but extraction still needs a working 7z.
- **Only a real validation failure triggers automatic repair** (7z returns non-zero or times out) → `_schedule_archive_repair()`:
  1. `aria2.remove(gid)` stops the old task;
  2. `_quarantine_download_file(task, "archive-invalid")` renames the bad package to `*.freedeckcy-archive-invalid-<ts>` (avoiding aria2 resuming garbage data);
  3. Re-download with the original direct link (`changeUri` in-place link replacement first, `addUri` on failure);
  4. The task is set to `status=waiting`, `install_status=waiting`, `post_processed=false`, and **does not register Steam**.
- Each task is automatically re-downloaded only once per process; after the re-download completes, background maintenance enters installation again. If the second validation still fails → `install_status=failed`, and the task row's "Retry" button must be used (see 6.7).
- Log keyword: `Archive validation failed, re-download scheduled`; `7z t` reads large packages once more, which is expected overhead.

### 6.7 Task retry (v0.1.1)

The QAM task row shows "Retry" when `status=error` or `install_status=failed`, going through `retry_task()`:

1. Reset state: `post_processed=false`, `install_status=pending`, clear `_readd_attempts` / `_task_sync_misses`, so that the "once per task per process" limit no longer blocks manual retries;
2. **The file is already complete** (`_file_matches_expected_size()` passes) → mark `complete` directly and reschedule installation, **without re-downloading**;
3. **The file is incomplete/missing** → re-fetch the direct link (`changeUri`/`addUri`) and return to the download queue; if fetching the direct link fails (e.g. login state expired) → automatically try an alternate provider for the same game once (`retry_task_with_fallback`, result marked `auto_fallback=true`); only when there is no alternate source does the task change to `install_status=failed` with the prompt "Retry failed: unable to re-fetch the download direct link (and no alternate source)";
4. Retry is an explicit manual action; background maintenance never triggers it automatically.

### 6.8 Uninstall and Proton prefix reclamation (v0.1.1)

When "Uninstall" is clicked in the QAM installed list:

1. First calls `preview_tianyi_uninstall` → `preview_uninstall()`: returns the install directory usage, `compatdata/<appid>` usage (`find_compatdata_dirs()` across all Steam libraries), and the resolved Steam AppID (`_resolve_record_app_id()`: the record's appid, looking it up from the shortcut when missing);
2. The UI shows "install directory usage / Proton prefix additionally uses X" with three buttons: **Cancel** / **Delete game files only** (default, `delete_compatdata=false`) / **Delete Proton prefix too** (only shown when a prefix is detected, `delete_compatdata=true`);
3. Uninstall order: delete the install directory (`_can_remove_install_path` safety check) → optionally delete the Proton prefix → remove the installed record → clean up the Steam shortcut/mapping/cover → clear the session;
4. **compatdata path safety**: `_can_remove_compatdata_dir()` only allows a `<library>/steamapps/compatdata/<appid>` structure and rejects symlinks; it only deletes directories returned by `find_compatdata_dirs()` whose appid matches the record;
5. Returns `compatdata: {requested, app_id, paths, removed_paths, freed_bytes}`; anything not deleted/failed is written into the top `warning`;
6. **Not deleted by default**: avoiding deleting saves/configuration inside the Proton prefix when the user "just wants to reinstall the game".

---

## 7. Chain B: cloud saves

### 7.1 Upload (manually triggered, QAM settings page)

```text
start_cloud_save_upload()
 └─ 后台 _run_cloud_save_upload_task()
      ├─ _collect_cloud_save_candidates()
      │    ├─ 逐条已安装记录 → resolve shortcut 拿 appid → find_compat_user_dir() 在**所有 Steam 库**
      │    │   定位 steamapps/compatdata/<appid>/pfx/drive_c/users/{steamuser,deck,root}
      │    ├─ 扫 Documents/My Games、Saved Games、AppData/{Roaming,Local,LocalLow}（深度≤6）
      │    └─ 用 game_id/标题/安装目录名生成 token 匹配；无 compatdata 时回退扫安装目录 save/saves/userdata/profiles
      ├─ _archive_single_game_saves()
      │    └─ 7z 打包 {game_key}_{YYYYmmdd_HHMMSS}.7z + manifest.json（entries/源路径/游玩时长/manifest_version=2）
      └─ upload_archive_to_cloud()
           └─ Node：10 MB 分片 → /freedeckCYCloudSaves/<game_key>/<timestamp>.7z
```

### 7.2 Restore (four steps, with conflict confirmation)

```text
list_versions  → 云端各游戏目录下的 .7z，按时间戳排序
     ↓ 选游戏/版本
list_entries   → 下载整包解压读 manifest，列出可选存档项
     ↓ 勾选
plan           → 依 manifest 的 source_path 推断 Proton 相对路径（或扫描候选目录），
                 生成 copy_pairs，统计冲突数（同名文件）
     ↓ 有冲突则弹 ConfirmModal
apply          → 校验 plan_id + confirm → 覆盖前把同名文件/目录就地改名为
                 `*.freedeckcy-bak-<YYmmdd_HHMMSS>`（自动备份）→ 逐文件 copy2 →
                 playtime 取较大值合并 → 清理临时目录
```

**Key function index (cloud saves)**

| Stage | Code location |
|---|---|
| Multi-library compatdata locating | [steam_shortcuts.py:184](../py_modules/steam_shortcuts.py) `find_compat_user_dir()` / [steam_shortcuts.py:130](../py_modules/steam_shortcuts.py) `_steam_library_paths()` |
| Upload entry | [tianyi_service.py:5607](../py_modules/tianyi_service.py) `start_cloud_save_upload()` |
| Upload background task | [tianyi_service.py:2804](../py_modules/tianyi_service.py) `_run_cloud_save_upload_task()` |
| Candidate directory scan | [tianyi_service.py:3071](../py_modules/tianyi_service.py) `_collect_cloud_save_candidates()` |
| Packaging + manifest | [tianyi_service.py:5157](../py_modules/tianyi_service.py) `_archive_single_game_saves()` |
| Cloud upload / list versions / download | [tianyi_client.py:2079](../py_modules/tianyi_client.py) `upload_archive_to_cloud()`, [tianyi_client.py:2116](../py_modules/tianyi_client.py) `list_cloud_archives()`, [tianyi_client.py:2167](../py_modules/tianyi_client.py) `download_cloud_archive()` |
| Restore four steps | [tianyi_service.py:4426](../py_modules/tianyi_service.py) `list_cloud_save_restore_options()`, [tianyi_service.py:5048](../py_modules/tianyi_service.py) `list_cloud_save_restore_entries()`, [tianyi_service.py:3127](../py_modules/tianyi_service.py) `plan_cloud_save_restore()`, [tianyi_service.py:3241](../py_modules/tianyi_service.py) `apply_cloud_save_restore()` |

### 7.3 Playtime (independent small chain, v0.25.0 adds the managed gate)

- `SteamClient.Apps.RegisterForGameActionStart/End` global listeners → `record_tianyi_game_action` ([src/index.tsx:616](../src/index.tsx) `installGlobalGameActionReporter()`) → `TianyiService.record_game_action()`: a duplicate start more than 5 seconds apart is treated as the end of the previous session, a single session is capped at 12 hours, and the session can be recovered after a restart.
- **Library page injection**: `routerHook.addPatch("/library/app/:appid")` patches the Steam library detail page's `renderFunc` and component `type`, inserting "My playtime / main story / total playtime (HowLongToBeat)" ([src/index.tsx:1125](../src/index.tsx) `installLibraryPlaytimePatch()`, `LibraryTimeBlock`). This is the most "black magic" part of the whole project and depends on Steam UI internals.

**managed gate (v0.25.0)**:

- The frontend `LibraryTimeBlock` only renders when `data.managed === true`; unmatched/unloaded/request failure directly `return null`, **no longer inserting any playtime block into existing Steam games, and no longer showing "Loading" first**;
- The backend [tianyi_service.py:3434](../py_modules/tianyi_service.py) `get_library_game_time_stats()`: **first by AppID** [tianyi_service.py:3677](../py_modules/tianyi_service.py) `_resolve_installed_record_by_app_id()` exact-matches installed records, and if not hit then matches by normalized title (`_normalize_cover_text`, bidirectional containment); **avoiding misjudgment when existing Steam games share a name with plugin games**;
- No match → directly returns `{managed:false, reason:"not_managed", ...all zeros}`, **does not call `resolve_hltb_stats`, does not return HLTB data**;
- Only records matched in `store.installed_games` return `managed:true` + playtime/HLTB, and only then does the frontend insert the block.

**Boundaries**: only affects "games installed/backfilled by the plugin"; the detail page of a Steam game bought/installed by Steam itself **will not show** the plugin's playtime block (unless it is scanned/backfilled as a plugin record); title matching may misjudge a same-named Steam game as a plugin game (AppID priority reduces, but does not eliminate, this); HLTB query failure only affects data inside the block, not the library page itself.

## 8. Login: four ways, the UI only uses QR codes

| Way | Implementation | Status |
|---|---|---|
| **QR code** (the only UI entry) | The Python side uses aiohttp to call the QR interface of `open.e.189.cn` directly, grabs the QR PNG and proxies it to the page; polls status every 1.6 s; on success assembles the cookie string from the cookie jar and stores it in `state.json` | In use, most stable |
| **CDP capture** | Connects to the debug port (8080, 9222) of the Steam built-in browser / Chromium, reads cookies with the DevTools protocol | Legacy scheme; the API still exists (`/api/tianyi/login/capture/*`), but the frontend no longer calls it |
| **Cookie DB direct read** | Reads SQLite files such as `~/.local/share/Steam/config/htmlcache/Cookies`, filtering the `189.cn` domain | Legacy scheme; `v10/v11` encrypted cookies are skipped directly |
| Manual cookie paste | `POST /api/tianyi/login/manual` | Fallback API retained |

Code locations: QR code [tianyi_service.py:1699](../py_modules/tianyi_service.py) `start_qr_login()` / [tianyi_service.py:1785](../py_modules/tianyi_service.py) `poll_qr_login()`; CDP [tianyi_service.py:9083](../py_modules/tianyi_service.py) `_collect_tianyi_cookie_from_cdp()`; Cookie DB [tianyi_service.py:9282](../py_modules/tianyi_service.py) `_collect_tianyi_cookie_from_cookie_db()`; manual cookie [tianyi_http.py:151](../py_modules/tianyi_http.py) `handle_login_manual()`.

Note: **the cookie is never sent back through the browser** — the login bridge page is only responsible for displaying the QR code and status, and everything is done on the Python side.

---

## 9. Tianyi Cloud Drive protocol essentials

| Step | Approach |
|---|---|
| Download entry validation | `_build_install_plan` accepts a Tianyi (`cloud.189.cn`, `h5.cloud.189.cn`, `api.cloud.189.cn` or `*.189.cn`) or Baidu (`pan.baidu.com`/`yun.baidu.com`/`eyun.baidu.com`) `share_url`; other domains are rejected |
| Share parsing | `checkAccessCode` (exchange access code for shareId) → `getShareInfoByCodeV2` (get fileId/isFolder) → `listShareDir` (list the directory, pageSize=60). Multiple "request profiles" (host × GET/POST/form) are prepared for the same interface and tried one by one; if all fail, it scrapes the share landing page HTML for the shareId; finally Node as a fallback. The only signature header is `Sign-Type:1`, and **authentication relies entirely on the Cookie** |
| Direct link | `api.cloud.189.cn/open/file/getFileDownloadUrl.action`, signature = `MD5(AccessToken=..&Timestamp=..&dt=1&fileId=..&shareId=..)`, with headers `Accesstoken/Signature/Timestamp` |
| accessToken | Extracted from the 302 redirect URL of `ssoH5` |
| sessionKey | Tries `getUserBriefInfo` first, falls back to `getSessionForPC` |
| Upload | **All delegated to Node**: parameters are AES-128-ECB encrypted into `params`, the AES key is RSA-PKCS1 encrypted into `EncryptionText`, and `SessionKey/Operate/RequestURI/Date/params` participate in the signature; 10 MB chunks via `initMultiUpload → getMultiUploadUrls → PUT → commitMultiUploadFile`, with `sliceMd5` being the uppercase MD5s of each chunk concatenated and then MD5'd |
| Stability | Python failure → Node fallback; `node` prefers the bundled runtime `defaults/runtime/node/<arch>/bin/node`, then PATH, and clears Decky-injected `LD_LIBRARY_PATH/_MEIPASS2/PYTHONHOME` to avoid libcrypto conflicts |

**Risks**: it is all undocumented interfaces + private signatures; any official change breaks everything, and it may trigger risk control / account bans.

---

## 10. Data and state

`~/.local/share/freedeckCY/tianyi/state.json` (**rewritten in full every time**, atomically replacing a temp file; data classes and read/write see [tianyi_store.py:51](../py_modules/tianyi_store.py) onward, [tianyi_store.py:250](../py_modules/tianyi_store.py) `load()`, [tianyi_store.py:351](../py_modules/tianyi_store.py) `save()`):

```jsonc
{
  "login":   { "cookie": "...", "user_account": "...", "updated_at": 0 },
  "settings":{ "download_dir": "~/Downloads", "install_dir": ".../installed",
               "split_count": 16, "page_size": 50,
               "auto_delete_package": false, "auto_install": true },
  "tasks":   [ { "task_id", "gid", "game_id", "game_title", "share_code", "share_id",
                 "file_id", "file_name", "download_dir", "local_path",
                 "status", "progress", "speed", "openpath",
                 "install_status", "install_message", "installed_path",
                 "post_processed", "error_reason",
                 "file_size", "group_id", "group_total",
                 "created_at", "updated_at" } ],
  "installed_games": [ { "game_id", "game_title", "install_path", "source_path",
                  "status", "size_bytes", "steam_app_id",
                  "playtime_seconds", "playtime_sessions", "playtime_last_played_at",
                  "playtime_active_started_at", "playtime_active_app_id",
                  "created_at", "updated_at" } ],
  "cloud_save_last_result": {},
  "cloud_save_restore_last_result": {}
}
```

- Task terminal states are retained for **7 days** (`TASK_RETENTION_SECONDS`).
- Settings have an additional backup: Decky settings + `~/.local/share/freedeckCY/settings.json`, preventing loss if the plugin directory is cleared.
- The game catalog is fully read from CSV into memory on every `initialize()` (about 2800 entries, negligible cost).
- Cloud save restore overwrite backups are **in-place renames** to `*.freedeckcy-bak-<YYmmdd_HHMMSS>`, are not automatically cleaned up, and can be recovered manually after a failure.
- `tasks[]` are grouped by `group_id`: multiple files of the same install plan (volumes/multi-package) share `group_id` and `group_total`; `file_size` is the expected byte count from the listing, used for download integrity checking and session recovery.
- `install_status` values: `pending` / `installing` / `installed` / `failed` / **`waiting`** (`7z t` validation failed and automatic re-download has been scheduled, or a manual retry is queued) / **`bundled`** (non-main volume of a multi-volume archive, extracted together by the main volume, keeping this value after installation completes).
- The state file contains the login Cookie: when saving, the state directory is chmod **0700**, and `state.json` and temp files chmod **0600** (`_chmod_private()`, failure does not block).

---

## 11. Six designs worth learning from

1. **Three-tier panel polling + backend secondary throttling**: the frontend uses active 900 ms / idle 6 s / background 30 s; the backend further splits the task refresh window by "whether there are active tasks" into 1 s/10 s/30 s, and the installed list into 20 s/60 s/120 s, with caching and timeout degradation. The polling path **does no port probing or network validation**, and expensive refreshes are window-throttled.
2. **All heavy work asynchronous + background maintenance + group coalescing**: extraction, aria2 control, and store disk writes all go through `asyncio.to_thread`; installation after download completion is scheduled as a background task deduped by task_id; `main.py` runs it once at startup and then periodically calls `maintenance_tick()` per `config.MAINTENANCE_INTERVAL_SECONDS`, ensuring **automatic installation even when the panel is not open**; tasks in the same group are coalesced by `group_id` (install only after the whole group is downloaded, register Steam only once), and a task-list fingerprint avoids rewriting `state.json` on every maintenance round.
3. **Two-stage install**: `prepare` (probe only: file list, free space, Proton rating) → `start` (actually place orders). Users can see "how big the download is, how big it will be after installation, whether the disk is sufficient" before confirming.
4. **Extract to staging then merge**: first extract to a temp directory, then merge into the target directory, automatically removing the "extra same-named folder wrapped inside the archive" case. This is a very practical technique for handling third-party packaged resources.
5. **Cloud saves with a manifest**: instead of transferring files naked, it packages + `manifest.json` records source paths, entries, and playtime. Only then can restore do **path inference**, **conflict detection**, **playtime merging** (take the larger value, no downgrade overwrite), and **automatic backup before overwrite**.
6. **Degradation chains and self-healing**: Python parse failure → Node parsing; bundled runtime preferred → system command fallback; 7z failure → `shutil.unpack_archive`; cache refresh failure → use the old cache; aria2 session lost → claim by path / re-add the original direct link; direct link expired → `changeUri` in-place replacement; file size mismatch or `7z t` validation failure → quarantine the bad file and automatically re-download once; if it still fails, manual "Retry".

---

## 12. Issue list

> This list covers the state after the three rounds of engineering completion in 2026-11 + freedeckCY v0.1.1's four-piece set + v0.2.0 catalog/covers; items marked "(fixed)" have landed, and the rest are **known issues** that still exist. Maintenance suggestions see [ROADMAP.md](ROADMAP.en.md).

### P0: Directly causes "can't install / data loss / being exploited"

1. ~~Installation strongly depends on frontend polling~~ (`main.py`'s main loop was originally just `sleep(60)`): **fixed in this completion** — added `TianyiService.maintenance_tick()`, executed once at plugin startup and then periodically per `config.MAINTENANCE_INTERVAL_SECONDS` (8 s), not depending on whether the panel is open.
2. ~~`post_processed` is set to `True` before extraction~~: **fixed in this completion** — changed to set it true only after the install work finishes; after a crash during extraction/a plugin restart, background maintenance picks up unprocessed tasks again.
3. ~~Multi-file games extract concurrently into the same directory and `installed_games` records overwrite each other~~: **fixed in this completion** — serialized with an `asyncio.Lock` per install directory, and the whole group is installed at once by `group_id`, writing a single record (size = sum of packages) and registering Steam only once.
4. ~~Cloud save restore deletes before copying and has no backup; the path containment check used `startswith` and could be escaped with `../`~~: **fixed in this completion** — before overwriting it renames in place to `*.freedeckcy-bak-<timestamp>` (the result returns `backed_up_files`), and path boundaries use `_is_within_dir()` (commonpath).
5. ~~Local HTTP has no authentication, CORS is fully open, the request body limit is 1 GB, and `share_url` can be stuffed with arbitrary addresses~~: **fixed in this completion** — Host/Origin validation + rejecting `Sec-Fetch-Site: cross-site`; `client_max_size` reduced to **16 MB**; `share_url` only accepts Tianyi/Baidu domains; `state.json` directory 0700 / file 0600.

### P1: Pitfalls that are easy to hit

6. ~~Space only counts archives, not the extracted size~~: **fixed in this completion** — the install plan gives an estimate of the extracted size, and free space is hard-checked before extraction (archive × 1.05, multi-volume by the sum of volumes).
7. ~~After a plugin/device restart the aria2 gid is lost, tasks get stuck or are misjudged as failed~~: **fixed in this completion** — aria2 runtime metadata + flock (plugin reload can attach to a live instance, gid unchanged) + claim by path / original direct link `changeUri` in-place replacement (addUri on failure) / recovery chain that only errors after 5 consecutive misses (see 6.1/6.4).
8. ~~No download integrity validation~~: **fixed in this completion** — validate against the listing's `file_size`; on mismatch first quarantine the bad file and automatically re-download once (self-healing), and only error if it still fails; before extraction, also precheck for empty files / HTML error pages (see the chain A sequence diagram and key function index).
9. ~~Multi-volume archives extracted one by one as ordinary archives~~: **fixed in this completion** — `archive_bundle.py` recognizes 6 kinds of volumes, extracts only the main volume and marks the rest `bundled`; missing volumes fail the whole group and list the missing files.
10. ~~Steam config writes have no backup, duplicate entries, silent failures~~: **fixed in this completion** — `DevkitGameID` token dedupe, no rewrite when fields are unchanged (`unchanged`), backup before write keeping 12 copies, strict read-back after write (see 6.5).
11. Each file is one aria2 task; aria2 global concurrency is 3, so multiple tasks queue behind each other; there is no whole-package hash validation and no automatic retry on failure. (Known issue)
12. `backend/tianyi_cloud_upload.js` takes priority over `.cjs`, and **only degrades if the file does not exist**; when the node version does not support ESM it fails directly (`.cjs` only implements upload). (Known issue)
13. `config.vdf` is rewritten as regex text, and a running Steam may write back and overwrite it (backups are made before writing; recoverable with `*.freedeckcy-bak-*`). (Known issue)
14. ~~The Steam root only recognizes two hardcoded paths, so Flatpak / non-default SD card libraries fail~~: **fixed in this completion** — `FREEDECKCY_STEAM_ROOT`, Flatpak paths, and `libraryfolders.vdf` full-library scanning (the opposite of v0.6's "main library only" implementation, with no fallback).
15. ~~The repository lacks aria2/7z binaries; cloud saves require a system node~~: **fixed in this completion** — `make runtime` fills them in with one command, the code prefers `defaults/runtime/`, and system commands are only a fallback.
16. ~~Frontend-backend contract drift: `/api/tianyi/state` loses settings, `panel_state.library_url` is always an empty string~~: **fixed in this completion**.
17. Share parsing only takes the first page of 60 items and does not recurse, so shares with very many files are missed. (Known issue)
18. Volume recognition only covers the 6 common naming kinds; non-standard naming (e.g. custom `.001` prefix/mixed volumes) may still be treated as ordinary files. (Known issue)
19. ~~No archive integrity validation before install, so bad packages only fail halfway through extraction~~: **fixed in v0.1.1** — `7z t` validation before extraction (best-effort, skipped when 7z is unavailable), with quarantine on failure and automatic re-download once (see 6.6).
20. ~~Uninstall only deletes the game directory, and Proton prefixes occupy disk long-term~~: **fixed in v0.1.1** — the uninstall preview shows usage, with an optional "delete the Proton prefix too" (not deleted by default, path safety checks, see 6.8).

### P2: Engineering quality

21. `tianyi_service.py` is about 10700 lines with a single class of 100+ methods; `src/index.tsx` is an about 3705-line single file. `tests/` (575 test cases) and GitHub Actions CI have been added, but there is **still no Python type checking** (mypy/ruff not wired in, see ROADMAP).
22. Everything is hardcoded Chinese, **no i18n**; many `unknown` / `as` assertions bypass TS types. (Known issue)
23. ~~`clear_freedeckcy_tasks.sh` hardcodes `/home/deck`~~: **fixed in this completion** — uses `$HOME` and supports `FREEDECKCY_STATE_FILE` overrides.
24. The log path still hardcodes `/tmp/freedeckcy.log` and is not configurable (rotation is in place, so it no longer grows without bound). (Known issue)
25. ~~Logs grow without bound / `basicConfig(force=True)` overrides Decky's logging configuration~~: **fixed in this completion** — changed to `RotatingFileHandler` (5 MB × 3), `propagate=False`.
26. ~~`state.json` is written with default file permissions (its content includes the login Cookie)~~: **fixed in this completion** — state directory 0700, file 0600.
27. ~~aria2 start parameters are weak (slow preallocation, no timeout/retry/log/certificate)~~: **fixed in this completion** — `--file-allocation=none`, connect 10 s / read 60 s, retry-wait 5 / max-tries 10, `--log aria2.log`, automatic `--ca-certificate` selection, and downloads carry UA/Referer.
28. ~~Steam shortcut/Proton writes cannot be rolled back~~: **fixed in this completion** (same as item 10, backup before write + read-back; but a running Steam may still overwrite, see item 13).
29. Proton user directory now has custom username scoring as a fallback, but extreme layouts (multiple prefixes, unusual usernames) may still be missed. (Known issue)
30. ~~Failed tasks can only be removed and re-downloaded~~: **fixed in v0.1.1** — task row "Retry" button + `retry_task()` (reinstall directly when files are complete, see 6.7).
31. ~~Troubleshooting relies on manually assembling commands~~: **fixed in v0.1.1** — `make doctor` / `scripts/doctor.sh` outputs runtime, Steam, state, logs, ports, and network diagnostics with one command (read-only, see DEVELOPMENT §6.6).
32. ~~The resource catalog had only PC as a single column, covers were resolved online every time, and there was no category/platform dimension~~: **fixed in v0.2.0 / v0.3.0** — the catalog was completed to **7084 entries / 11 platforms**, with a bundled `cover_index.csv` (3470 rows, 6823 entries with covers after merging), covers resolved by "static → disk cache → Steam store → ProtonDB" and cached for 7 days, and the library page has platform + category dual filter rows (see 5.5).
33. ~~Non-PC resources are browse-only and cannot be installed~~ (emulators not integrated): **fixed (v0.6.0~v0.11.0)** — **10 platforms are integrated** (GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch); the 3DS/PS2/PS3 official packages are x86_64 only and are automatically hidden on aarch64 by the catalog whitelist (see the architecture matrix in 5.10); this is not "cannot install". (Known limitation)
34. ~~Catalog categories were mixed with platform names (GBA/Switch…), category filters showed platform names, and there was no automated data health check~~: **fixed in v0.3.1** — `normalize_categories()` cleans at load time + 606 rows of data were rewritten ("Emulator" 606 entries), and `validate_catalog.py --strict` was added to CI (see 5.6).
35. **DroidDeck adaptation has limited real-device verification**: v0.4.0 adapted per the DroidDeck source/ARM64 runtime structure; FEX/ARM Proton and Android storage mapping may affect results; aarch64 can install GBA/PSP/NDS/PS1/FC/MD/Switch, while 3DS/PS2/PS3 are hidden by the whitelist (see [DROIDDECK.md](DROIDDECK.en.md) / ROADMAP 9.8). (Known limitation)
36. **Boundaries of the emulator closed loop (v0.12.0)**: the plugin package **does not bundle any emulator**, and **all platforms (including GBA) need network access at first install** to download from GitHub releases (failures are written into the install message and can be retried; offline users can manually place `~/.local/share/freedeckCY/emulators/<platform>/<arch>/` or use `FREEDECKCY_*_BIN`); 3DS (Azahar) prefers the official Flatpak on SteamOS 3.9.5 (the AppImage has known compatibility issues, see 5.10); PS1/PS2 **require the user to supply a BIOS** (`bios/ps1`, `bios/ps2`; missing does not block installation but warns/may cause a black screen; PS2 copies it to two default PCSX2 directories); 3DS needs system files, PS3 needs firmware, and Switch needs prod.keys + firmware (since v0.12.0 these are automatically deployed to the emulator directories after installation and portable config is written; missing ones still do not block installation, but the game cannot be played directly after installation); FC/MD share the Mesen2 cache (`emulators/mesen/<arch>/`), and the zip contains an executable rather than an AppImage; only ROM extensions in the registry are recognized, and there is **no BIOS/save management** (BIOS/firmware are only "deployed from bios/<platform>/ to the emulator directory", not downloaded or version-checked); downloading/unpacking takes an extra copy of disk space; these platforms have not yet been verified on real ARM64/DroidDeck hardware. (Known limitation)
37. **Boundaries of automatic cloud saves (v0.15.0)**: only games detected as "exited" by gamewatch are auto-uploaded, and gamewatch depends on the process command line containing install_path (custom wrappers may be missed); since v0.16.0 restore is supported (conflict confirmation, backup before overwrite); the pre-upload fingerprint only looks at relative path+size+mtime (up to 5000 files) and does not read contents; `cloud_save_auto_upload` is enabled by default (can be disabled in QAM). (Known limitation)
38. **Emulator architecture matrix differences (v0.11.0)**: the 3DS/PS2/PS3 official packages are x86_64 only, so on aarch64 (including DroidDeck) catalog queries hide these platforms' entries/filter bars via the `available_platforms()` whitelist, and `emulator_status` also reports "platform hidden" — this is **expected behavior**, not a bug; Switch has both x86_64 + aarch64 packages but needs keys/firmware, and first install still requires an online download. (Known limitation)
39. **Boundaries of repository submissions (v0.13.0)**: the Issue form is only a manual review entry point and is not yet automatically converted to JSON (maintainers handle it manually/by script); there are no review labels, automatic comments, automatic PRs, or automatic git commits; validation only does static fields/duplicate shareCode, **does not verify online whether the share link is reachable or whether the access code is valid**; submissions do not include covers/Steam AppID (merged rows leave them empty, later filled by cover resolution/catalog maintenance); archived files in `submissions/merged/` are not automatically committed back to the repository. (Known limitation)
40. **Boundaries of Baidu Netdisk (v0.17.0)**: the main path is **QR login (BDUSS/Cookie)**; the Cookie is equivalent to account credentials, can expire/be risk-controlled, and must be re-scanned when invalid; the QR session exists only in memory for 180 s, and **QR confirmation/Cookie exchange has not yet been verified on a real device** (`getqrcode`/`unicast` waiting has been verified); the OpenAPI is an optional fallback that requires a self-built app/authorization and transfers shared files to `/FreedeckTmp` (occupying cloud drive space, cleaned up after installation); both chains **do not use CDP/web reverse engineering**, and Baidu interface changes may affect QR login/direct links; download speed is affected by the Baidu account and official rate limits. (Known limitation)
41. **Boundaries of emulator save upload (v0.16.0)**: PSP/PS3/3DS support per-game splitting (PARAM.SFO/NCSD), but PS1/PS2 single memory cards and the Switch directory still upload whole directories (other games on the same card are included); GBA/FC/MD/NDS match by ROM file name, and renames/custom save names yield `game_save_not_found` (never degrading to the whole directory); 3DS/Switch directories may be large (limited by the 5000-file fingerprint and upload size limits); the `cloud_save_include_emulators` setting is on by default and can be disabled. (Known limitation)
42. **Boundaries of emulator save restore/multi-disc (v0.16.0)**: restore targets are constrained by the known save-root whitelist (`restore_roots`), and cross-device 3DS may degrade to the root directory; PS1/PS2/Switch shared-card/directory overwrites cannot pick a single game, and conflicts require confirmation followed by whole-file overwrites (with `*.freedeckcy-bak-<timestamp>` backups); PS1 multi-disc only auto-generates `freedeckcy-multidisc.m3u` when there are multiple `.cue/.chd` files, and single discs/existing m3u files do not generate one; the m3u sorts naturally by filename, so non-standard disc numbering may produce an unexpected order. (Known limitation)
43. **Boundaries of installed-game scanning (v0.18.0; v0.21.0 adds shortcuts)**: only scans one level of the install directory, at most 500 entries; directory names must normalize-match catalog titles (renames may yield `catalog_no_match`); it backfills installed records/appids/finds ROMs; v0.18 did not create Steam shortcuts, **v0.21.0 auto-creates them** (see 46; it does not download when the emulator is missing); when the emulator ROM is not found the record is still created but `rom_path` is empty; scanning never deletes/fixes existing records. (Known limitation)
44. **Boundaries of storage location selection (v0.19.0)**: only shows mounted and writable sub-mounts of `/run/media`, `/media`, `/mnt`, `/storage`, `/sdcard`; mount points (such as `/mnt` itself) are skipped; read-only/insufficient permissions/unmounted ones do not appear; capacity is a snapshot; it never automatically creates/mounts/formats, nor checks whether the Steam library is on the same disk; suggested subdirectories are fixed as `freedeckCY/{downloads,installed}`. (Known limitation)
45. **Boundaries of the Decky native game library (v0.20.0; v0.27.20 visual/input refactor)**: task progress is still in the QAM home task area; the native library uses a cover grid/Hero/category shelves/detail modal, with 30 items per page + load more; scanning still only recognizes one level under `settings.install_dir`; uninstall always deletes files (no compatdata reclamation option); the legacy web library is only for desktop debugging/fallback and is not the main entry. (Known limitation)
46. **Boundaries of scan-added Steam shortcuts (v0.21.0)**: only adds shortcuts for scanned/existing PC records with `steam_app_id=0`; emulator shortcuts require the emulator to be installed (`allow_download=False`, no automatic download), otherwise recording `shortcut_error=emulator_not_ready`; when the PC exe/ROM is not found it skips and records `exe_not_found`/`rom_not_found`; it only writes `shortcuts.vdf`, so **Steam must be restarted/switched user/reopened the library page to see them**; it does not overwrite existing shortcuts with the same name and same exe. (Known limitation)
47. **Boundaries of the diagnostics self-check (v0.22.0)**: the self-check is a one-time snapshot (version/directory/runtime/Steam/storage/network/Baidu QR/tasks/logs), and network items are affected by connectivity; "Run self-check" does not repair automatically, it only gives detail/fix; `baidu_qr` only outputs the sign length (never sign/cookie); exporting the diagnostics bundle writes a 0600 zip to the downloads directory containing 300 log lines (already redacted), and it is still recommended to review it yourself before submitting; there is no support for viewing logs online or uploading diagnostics bundles. (Known limitation)
48. **Boundaries of the native library entry/QR timeout (since v0.23.0; version marker removed in v0.26.51)**: only when `showModal(<LibraryPage />)` fails does it use the full-screen route, and only when both fail does it toast; whether the frontend is updated is determined by the Decky plugin list version/`package.json`; Baidu QR timeouts on both frontend and backend depend on the network/TLS, and timeouts only prompt without automatic retry; `Baidu QR` logs only record the sign length, never sign/cookie. (Known limitation)
49. **Boundaries of native library back/close (v0.24.0)**: modal mode relies on the `onClose` callback to close, while route mode uses `Navigation.NavigateBack()`; the Steam overlay's B/Esc may not be able to close the modal, so the explicit "Back"/"Steam Library" buttons are needed; when `Router.NavigateToLibraryTab()` is unavailable it only falls back to `NavigateBack`; the top toolbar scrolls with the library page (non-sticky since v0.27.3) and does not change Steam's global navigation behavior. (Known limitation)
50. **Boundaries of the library detail playtime block (v0.25.0)**: the playtime block is only inserted when `managed=true` (AppID or title matches `installed_games`); unmatched existing Steam games directly `return null` and HLTB is not queried; AppID priority reduces same-name misjudgment, but title matching may still treat a same-named Steam game as a plugin game; HLTB failure only affects data inside the block; it still depends on the Steam library page's internal structure (the patch may break with Steam updates). (Known limitation)

---

## 13. Alignment with v0.6

The author's v0.6 release (unpacked locally at `0.6/freedeck-plugin`, **read-only reference, not distributed with this repository**) is much more complete than this repository in the download pipeline, Steam writes, emulators, and the resource pool. This round only borrows a few capabilities directly related to "stable downloads / safe Steam writes"; the rest are either not adopted or listed in [ROADMAP.md](ROADMAP.en.md).

### 13.1 Adopted (three rounds + v0.1.1 ~ v0.6.0)

| Capability | v0.6 source | Implementation in this repository |
|---|---|---|
| Multi-volume archive recognition (6 naming kinds, main volume, missing volumes) | `archive_detector.py` | `py_modules/archive_bundle.py`; only extracts the main volume and marks the rest `bundled` (see 6.3) |
| Tightening before extraction | The precheck idea from `archive_validator.py` | `_wait_payload_settled()` (wait for `.aria2` to release and for the size to be stable twice) + `_precheck_archive_payload()` (empty file/HTML); since v0.1.1 also `7z t` best-effort validation (see 6.6) |
| `7z t` validation before extraction + automatic re-download (landed in v0.1.1) | The idea of `archive_validator.test_archive` | `seven_zip.test_archive()` (skipped when 7z cannot be executed) + `_schedule_archive_repair()` (see 6.6) |
| compatdata uninstall cleanup (landed in v0.1.1) | `uninstall_installed_game(delete_compatdata=)` | `preview_uninstall()` + `find_compatdata_dirs()` + `_can_remove_compatdata_dir()` (see 6.8) |
| Emulator registry / 10 platforms (since v0.6.0, expanded in v0.7.0/v0.9.0/v0.11.0, all downloaded online in v0.10.0) | `emulator_adapters.py` (Eden/DuckStation/PCSX2/PPSSPP/RPCS3/mGBA/Lime3DS/melonDS/Nestopia/BlastEm/MAME) | The `EmulatorSpec` registry in `emulator_manager.py`: GBA=mGBA, PSP=PPSSPP, NDS=melonDS, PS1=DuckStation (BIOS required), FC/MD=Mesen2, 3DS=Azahar (SteamOS prefers the official Flatpak, AppImage fallback)/PS2=PCSX2/PS3=RPCS3 (x86_64 only, needs system files/BIOS/firmware), Switch=Eden (x64/arm64, needs keys/firmware); **the plugin package does not bundle emulators, and the first install downloads them online**; architecture whitelist/BIOS copying/ROM lookup/launch scripts see 5.10 |
| Platform catalog + cover index (started in v0.2.0, data and UI completed in v0.3.0) | Per-platform catalogs + `generate_*_cover_urls.py` / `emulator_cover_pipeline.py` | Catalog CSV with 4 optional columns + full catalog (7084 entries / 11 platforms, from v0.6 data merged by `scripts/merge_v06_catalog.py`) + `cover_index.csv` (3470 rows / 6823 entries with covers after merging) + cover disk cache + **platform/category dual-filter UI** + v0.3.1 category cleanup/data health check (`normalize_categories` + `validate_catalog --strict` CI); emulator installation landed in v0.6.0–v0.12.0 (10 platforms) |
| aria2 runtime reuse (meta + flock) | `aria2.runtime.json` + flock in `aria2_manager.py` | `aria2-runtime.json` + `aria2-runtime.lock`, with plugin reload attaching to a live instance (see 6.4) |
| In-place direct-link replacement | `aria2.changeUri` | `Aria2Manager.replace_uri()`; an expired direct link keeps the gid and progress |
| Steam writes: DevkitGameID token dedupe, unchanged, backup, read-back | `steam_shortcuts.py` | The same strategy + `*.freedeckcy-bak-*` keeping 12 copies (see 6.5) |
| compatdata custom username scoring | `steam_shortcuts.py` | `find_compat_user_dir()` scores by AppData/Documents/Saved Games |
| aria2 startup parameter hardening | `aria2_manager.py` | `--file-allocation=none`, timeout/retry/log/CA, UA+Referer |

### 13.2 Where we are stronger, explicitly not regressing

- **Multiple game libraries / SD card / Flatpak**: v0.6 does not parse `libraryfolders.vdf`, and `compatdata` is only found in the main library; this repository supports full-library scanning and `FREEDECKCY_STEAM_ROOT`, and **does not regress for the sake of "alignment"** (see §12 P1-14 / DEVELOPMENT §6.5).
- **No-root security model**: see the first item of 13.3.

### 13.3 Explicitly not adopted (with reasons)

- **`plugin.json`'s `flags: ["root"]` + `steam_host_writer` writing Steam files via `sudo -u deck`**: v0.6 runs the plugin as root and then drops privileges in a helper to write files. This plugin always runs as the deck user; introducing root would expand the permission surface and increase Decky review/misuse risk; the current "same-user atomic write + backup before write + read-back after write" is sufficient.
- **Likes / submissions to the Tencent Docs resource pool**: requires a Tencent Docs login state + CDP submission (v0.6 has `_submit_resource_pool_entry_via_cdp` etc.), which is content operations/user-generated content and significantly expands the compliance surface; "resource pool read-only" is listed in ROADMAP as a low-risk candidate.
- **Baidu web CDP collection / undocumented interfaces**: requires reverse-engineering web APIs/collecting login state, with high maintenance cost and account-ban risk; v0.17.0 switched to **Baidu Passport official QR** to get BDUSS/Cookie (main path), with OpenAPI only as an optional fallback, and **still no CDP/web API reverse engineering**.

### 13.4 To do (see ROADMAP §9 for details)

`7z t` validation and compatdata uninstall cleanup have landed in v0.1.1 (see 13.1). The rest to do: Range resume probing, SQLite task store, resource pool read-only, automatic Steam restart; Baidu Netdisk landed OpenAPI in v0.14.0 and switched to the QR/Cookie main path in v0.17.0 (OpenAPI optional fallback, see 5.13; no CDP/web reverse engineering); all 10 emulator platforms are integrated (3DS/PS2/PS3 x86_64 only, automatically hidden on aarch64; BIOS/firmware/keys for each platform are supplied by the user); other cloud drive sources such as CTFile are only under evaluation (many interface/compliance prerequisites, not currently prioritized).

---

## 14. Glossary


| Term | Meaning |
|---|---|
| Decky Loader | The third-party plugin loader for Steam Deck; a plugin = `main.py` + `plugin.json` + `dist/index.js` |
| QAM | Quick Access Menu, the side menu that pops up when pressing "…" in Game Mode; the plugin UI lives here |
| Proton prefix / compatdata | The Wine container under `steamapps/compatdata/<appid>/pfx` for each non-Linux game; saves are in `drive_c/users/steamuser/...` |
| shortcuts.vdf | `userdata/<uid>/config/shortcuts.vdf`, the library of non-Steam game shortcuts (binary VDF) |
| grid | `userdata/<uid>/config/grid/`, the custom cover art directory (`p`=portrait, `_hero`, `_logo`, `_wide`) |
| Non-Steam game appid | `CRC32(exe path + display name) \| 0x80000000`; Steam uses it to distinguish "manually added games" |
| HLTB | How Long To Beat, a game playtime database; this project uses it to display "main story / total time"; since v0.25.0 it only queries `managed=true` (plugin install records) |
| managed gate | The library page playtime isolation added in v0.25.0: the frontend renders `LibraryTimeBlock` only when `data.managed===true`, and the backend returns `managed=false` and does not query HLTB when no installed record matches |
| gid | The internal aria2 download task ID; this version uses runtime metadata + flock so the plugin can attach to the same aria2 after reload, with the gid usually unchanged |
| Multi-volume archive / main volume | A large archive split into multiple files (`.7z.001`, `.part1.rar`, `.z01+zip` …); the main volume is the entry volume, and only it needs extraction |
| `bundled` | One of the task `install_status` values: the file belongs to a multi-volume archive but is not the main volume, and is extracted together by the main volume |
| DevkitGameID | A Steam shortcut field; this project writes the freedeckCY token into it as a more stable dedupe/launch marker than LaunchOptions |
| group_id | The group ID shared by the same install plan (volumes/multiple packages); the whole group must finish downloading before installation, and Steam is registered only once |
| `7z t` | 7-Zip's archive test subcommand; this project runs it before extraction for integrity validation, and skips it best-effort when 7z is unavailable |
| compatdata reclamation | Optionally deleting `<library>/steamapps/compatdata/<appid>` at uninstall (not deleted by default; must be explicitly chosen in the confirmation dialog) |
| libraryfolders.vdf | The VDF configuration where Steam records multiple game libraries (SD card, second drive); this project scans `compatdata` in all libraries based on it |
| platform | The platform identifier of a catalog entry (currently 11 kinds: `pc`/`fc`/`nds`/`psp`/`gba`/`3ds`/`ps2`/`ps1`/`ps3`/`md`/`switch`); PC rows do not show a platform label, non-PC rows show it on the card; all 10 emulator platforms are installable (3DS/PS2/PS3 x86_64 only) |
| DroidDeck | An open-source project that runs the SteamOS runtime on Android phones and supports Decky plugins; it is an ARM64 device, and its Steam root/Proton tool differ from Steam Deck (see 3.1 / DROIDDECK.md) |
| Ludusavi | An open-source save path manifest project (mtkennerly/ludusavi-manifest, MIT); this project bundles its converted JSON manifest (53,549 games) to resolve Windows save paths into the Proton prefix |
| gamewatch | Background game process detection: scans `/proc/*/cmdline` every 8 s (uses `pgrep -f` when there is no /proc), producing start/end events on state transitions; this project only triggers automatic cloud saves on end |
| Save fingerprint | Computes sha256 over the save file set (relative path + size + mtime_ns, up to 5000 files), persisted in `state.json`'s `cloud_save_fingerprints`; upload is skipped when unchanged (reason=unchanged) |
| Emulator registry / closed loop | v0.11.0: the `EmulatorSpec` registry integrates 10 platforms (GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch); **all are downloaded online at first install and no emulator is bundled in the plugin package**; download ROM → generate launch script → native Steam shortcut (without Proton) |
| Architecture capability matrix / available_platforms | Availability decided by whether the current architecture has official assets: x86_64 has all 10; aarch64 only GBA/PSP/NDS/PS1/FC/MD/Switch (3DS/PS2/PS3 have no arm64 packages → the catalog whitelist hides their entries and filter bars) |
| EmulatorSpec | A platform registry entry: official assets (repo/version/per-arch filenames), archive (appimage/zip), launch_args, rom_extensions, env_var, min_bytes, state_key (cache directory name; FC/MD share mesen), executables (executable filenames inside the zip), bios_required |
| Diagnostics self-check / run_diagnostics | The v0.22.0 self-check: plugin/catalog/runtime/catalog data/Steam/storage/network/Baidu QR/tasks/logs each with `ok|warn|fail|skip` + detail/fix; the export includes `self-check.json` |
| Native game library / LibraryPage | Since v0.20.0; as of v0.27.20 a cover grid/Hero/category shelves/detail page, 30 items per page + load more, search/filter/sort, installed launch/directory/uninstall; everything goes through callables and does not depend on the local web page |
| Storage location / storage_options | The v0.19.0 SD card selection: parses `/proc/mounts` to find writable external mounts (SteamOS `/run/media`, DroidDeck `/storage`, etc.), suggests `freedeckCY/{downloads,installed}` directories with capacity, and switches with one click on the QAM "Paths" page |
| Scan installed / scan_installed_games | The v0.18.0 backfill entry (moved to settings in v0.21.0, with automatic Steam shortcuts): scans one level of the install directory, matches catalog entries by directory name/title, backfills appid, finds ROMs for emulators, and adds `TianyiInstalledGame` records; since v0.21.0 it dedupes and auto-creates shortcuts |
| Baidu QR / BaiduLoginState | The v0.17.0 Baidu main path: Passport QR (`getqrcode` → `unicast` → `qrbdusslogin`) exchanging for BDUSS/STOKEN/PTOKEN, with the Cookie stored in `state.json`'s `baidu_login`; install plans prefer the Cookie |
| Baidu OpenAPI / BaiduOpenApiLoginState | The optional v0.14.0 fallback: OAuth oob authorization (App Key/Secret → authorization code → access/refresh token), with a top-level `baidu_openapi` in state; shared files are transferred to `/FreedeckTmp` before fetching the dlink, and cleaned up after installation |
| Repository submission / submission | The v0.13.0 contribution channel: Issue form or `submissions/*.json` PR, with fields corresponding to the original resource pool submission; `submission.py` validates and maintainers merge into the catalog CSV, archiving files to `submissions/merged/` |
| Azahar Flatpak / flatpak_id | The v0.14.1 3DS SteamOS solution: `EmulatorSpec.flatpak_id=org.azahar_emu.Azahar`; on SteamOS or with an installed Flatpak it prefers `flatpak run`, otherwise it automatically `flatpak remote-add` + `flatpak install`, falling back to AppImage on failure; the 3DS wrapper uses XWayland |
| Emulator save restore whitelist / restore_roots | The v0.16.0 safety boundary: restore is only allowed into platform standard/portable save roots; on the same machine it prefers the original parent directory, across machines it falls to the first root, and arbitrary manifest paths are rejected |
| PARAM.SFO / NCSD title id | `PARAM.SFO` in PSP/PS3 save directories (`TITLE` used to match the game); the Program ID (hex) at `0x108` of the 3DS NCSD header used to match `title/00040000/<low8>`; both are used to split shared saves into per-game ones |
| Emulator saves / emulator_saves | The v0.15.0 save discovery module: `STANDARD_SAVE_DIRS`/`PORTABLE_SUBDIRS` cover 10 platforms; GBA/FC/MD/NDS match per game by ROM file name, while PSP/PS1/PS2/3DS/PS3/Switch return shared memory cards/title directories (deduped by path signature); since v0.16.0 PSP/PS3/3DS can be split per game, and restore is supported (whitelist targets + backups + conflict confirmation) |
| emulator_setup / portable config | The deployment module added in v0.12.0: copies BIOS/firmware/keys under `bios/<platform>/` (including archives) to the directories the emulator actually reads, and writes a minimal portable config (DuckStation/PCSX2 INI, mGBA/PPSSPP fullscreen); only fills missing items/changes a single key, does not download, and does not overwrite user configuration |
| BIOS / setup files | PS1 needs the DuckStation BIOS (`bios/ps1/`), PS2 needs the PCSX2 BIOS (`bios/ps2/`, copied to `~/.local/share/PCSX2/bios` and `~/.config/PCSX2/bios`); 3DS needs system files, PS3 needs firmware, Switch needs prod.keys + firmware (`setup_hint` hints); the plugin does not bundle these files, and missing ones only prompt without blocking installation |
| On-demand download | **At first install, all 10 platforms (including GBA)** download the official package from GitHub releases to `~/.local/share/freedeckCY/emulators/<platform>/<arch>/` (FC/MD share `mesen/`); the plugin package does not bundle emulators, and offline users can manually pre-place the cache or use `FREEDECKCY_*_BIN` |
| ROM / wrapper | ROM = a file in the install directory matching the platform extensions (GBA `.gba`; PSP `.iso/.cso/.pbp/.elf`; NDS `.nds/.dsi/.srl`, preferring the same name from openpath); wrapper = `<install_dir>/launch-freedeckcy.sh` (assembles launch args per platform, the Exe of the Steam shortcut) |
| `proton_tool` / `PACKAGE_ARCH` | The `proton_tool` setting: `auto`/`none`/a concrete compatibility tool name; the packaging variable `PACKAGE_ARCH`: `x86_64`/`aarch64`/`all`, deciding the artifact architecture and suffix |
| cover_index.csv | The cover index file (3470 rows already bundled): fills covers/appid/platform by `game_id` or title without overwriting existing values in the catalog CSV |
| Platform / category filter rows | The two chip rows after a search on the library page: the platform row ("All platforms" + per-platform counts, visible since v0.3.0) and the category row ("All categories" + Top12 category counts, including "Emulator"); both can be combined with the search terms |
| Category cleanup / data health check | Introduced in v0.3.1: `normalize_categories()` strips platform names from categories and dedupes at load time; `validate_catalog.py` runs health checks for duplicates/invalid links/cover coverage etc., with `--strict` in the CI gate |
| Tianyi Cloud Drive | China Telecom's 189 cloud drive, `cloud.189.cn`, one of the resource backends of this project (the other is Baidu Netdisk) |
