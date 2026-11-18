> English | [中文](ROADMAP.md)

# freedeckCY Roadmap (ROADMAP)

> This document lists the directions that are worth continuing — after **three rounds of engineering completion in 2026-11, the v0.1.1 four-piece set, v0.2.0 catalog/covers, v0.3.0 full data/platform filters, v0.3.1 category cleanup/data health check, v0.4.0 DroidDeck adaptation, v0.5.0 first tier, v0.6.0 GBA loop, v0.7.0 emulator registry, v0.8.0 automatic cloud saves, v0.9.0 six emulator platforms, v0.10.0 all emulators downloadable online, v0.11.0 ten platforms + architecture capability matrix, v0.12.0 emulator BIOS/firmware deployment, v0.13.0 repository game submissions, v0.14.0 official Baidu Netdisk OpenAPI, v0.14.1 3DS SteamOS compatibility fix, v0.15.0 emulator saves included in cloud saves, v0.16.0 emulator save restore/per-game split/PS1 multi-disc, v0.17.0 Baidu QR-code/Cookie main path, v0.18.0 scan installed/QR diagnostics, v0.19.0 SD card selection, v0.20.0 native game library, v0.21.0 scan migration/automatic Steam shortcut recovery, v0.22.0 diagnostics self-check, v0.23.0 native library fallback/QR timeout, v0.24.0 back-navigation fix, v0.25.0 playtime isolation, v0.26.x architecture split/stability, v0.27.0–v0.27.20 game library visual overhaul/gamepad and touch controls/detail and filter alignment** (v0.1.1 delivered compatdata cleanup and `7z t` verification; v0.2.0 platform field/cover cache/category filters; v0.3.0 full catalog and platform filter UI; v0.3.1 category cleanup + data health-check CI; v0.4.0 DroidDeck adaptation for Android/ARM64; v0.5.0 catalog browsing/pagination/sorting/installed tab/diagnostics export/update check; v0.6.0 GBA emulator loop; v0.6.1/v0.6.2 remote JSON catalog; v0.7.0 generic emulator registry + PSP/NDS; v0.8.0 Ludusavi + gamewatch automatic cloud saves; v0.9.0 emulators extended to PS1/FC/MD; v0.10.0 all emulators downloaded online, no emulators bundled in the plugin package; v0.11.0 added 3DS/PS2/PS3/Switch, 10 platforms + architecture allowlist; v0.12.0 emulator BIOS/firmware deployment + portable configuration; v0.13.0 repository game submissions (Issue/PR → catalog); v0.14.0 official Baidu Netdisk OpenAPI; v0.14.1 3DS (Azahar) SteamOS compatibility fix (prefer the official Flatpak); v0.15.0 emulator saves included in cloud save uploads; v0.16.0 emulator save restore + per-game split + PS1 multi-disc m3u; v0.17.0 Baidu Netdisk switched to the QR-code/Cookie main path (OpenAPI as optional fallback); v0.18.0 scan installed games + Baidu QR error diagnostics; v0.19.0 download/install directories support SD card selection; v0.20.0 Decky native game library (no longer web-dependent); v0.21.0 scan installed moved to settings + automatic Steam shortcut recovery; v0.22.0 diagnostics self-check + one-click diagnostics bundle; v0.23.0 native library fallback + Baidu QR click feedback/timeout; v0.26.51 removed the UI version label; v0.24.0 native library back/close fix; v0.25.0 games already in Steam no longer show the plugin's playtime block) — as well as the directions we explicitly advise against. The current version is **v0.28.11**. This is not a commitment and is not tied to any version; each item states its current status, motivation, cost, and acceptance criteria, so that secondary developers can pick items up as needed.

> **Current state (v0.28.11)**: the Decky native game library has completed its cover-grid/Hero/category-shelf/detail-page/skeleton-screen redesign; search, filters, update button, and the detail action bar are all aligned; the top toolbar is a single row; the category-shelf white bar is hidden; the focus ring on the leftmost/rightmost cards and the top safe area are complete; D-pad/left stick, A/B, L1/R1, L2/R2, trackpad/touch scrolling are wired up. Task progress still lives on the QAM home page; the old local web library is only for desktop debugging/fallback; the standalone web submission/management system is not in this repository.
>
> Background: the upstream author has stopped maintaining the project, `main` is only an early version, and the Baidu Netdisk / emulator / resource-pool implementations in **upstream Freedeck** Releases are not in this repository; this repository has independent Baidu/emulator implementations, and only the "resource pool" has not been ported (see [ARCHITECTURE.en.md](ARCHITECTURE.en.md) §2).
>
> ⚠️ Compliance notice: the resource links distributed by this project come from the Internet; this is distribution of pirated resources, which violates cloud-drive terms of service and involves copyright risks. This roadmap discusses **engineering improvements** only; deploying or using the project is not recommended, and expanding resource distribution capabilities is even less recommended.
>
> **Delivered (history; see the v0.27.20 summary at the top for current state)**: v0.1.1 — optional Proton prefix reclaim on uninstall (§9.2), best-effort `7z t` verification + automatic re-download (§9.4), "retry" for failed tasks, `make doctor`; v0.2.0/v0.3.0 — catalog platform field + `cover_index.csv` + on-disk cover cache + **full catalog (7,084 entries / 11 platforms) + platform/category dual-filter UI** (§9.6); v0.3.1 — category cleanup (606 rows, "Emulator" 606 entries) + `validate_catalog --strict` in CI; v0.4.0 — **DroidDeck (Android/ARM64) adaptation**: ARM64 runtime/ARM Proton resolution/dual Steam roots/`PACKAGE_ARCH` packaging (see [DROIDDECK.en.md](DROIDDECK.en.md), not yet verified on real hardware); v0.5.0 — **first tier**: catalog browsing/pagination/sorting, installed tab (launch/open directory/uninstall), diagnostics JSON+zip export (redacted), GitHub update check (1 h cache); v0.6.0 — **GBA emulator loop**: bundled mGBA AppImage, find ROMs via share pagination, launch script + native Steam shortcut (no Proton writes); v0.6.1/v0.6.2 — **remote JSON catalog**: `FREEDECKCY_CATALOG_JSON` reads a local/HTTP JSON file (remote cache 6 h, falls back to CSV on failure, off by default); v0.7.0 — **generic emulator registry**: `EmulatorSpec` wired up for GBA/PSP/NDS; GBA bundled, PSP/NDS download the official AppImage on demand at first install, launch scripts are generated per platform with its arguments; v0.8.0 — **automatic cloud saves**: bundled Ludusavi manifest (53,549 games) + gamewatch process detection; after a game exits only that game is uploaded (30 s debounce, fingerprint dedupe `reason=unchanged`, setting `cloud_save_auto_upload` on by default); v0.9.0 — **emulators extended to 6 platforms**: PS1 (DuckStation, requires a user-supplied BIOS, copied into the DuckStation directory at install), FC/MD (Mesen2, shared cache, executable inside the zip); v0.10.0 — **all emulators downloaded online**: removed `fetch_emulator.sh`/`make emulator-runtime` and the bundled mGBA; all 6 platforms (including GBA) download from the official release on first install, package size drops from ~68 MB to ~45 MB, cache can be pre-seeded manually for offline use; v0.11.0 — **10 platforms + architecture capability matrix**: added 3DS (Azahar)/PS2 (PCSX2)/PS3 (RPCS3)/Switch (Eden); 3DS/PS2/PS3 are x86_64-only and are hidden automatically by the catalog allowlist on aarch64 (entries/filter bar do not appear); Switch has both x64/arm64 packages; PS2 BIOS is copied into two PCSX2 directories, setup hints are given for 3DS/PS3/Switch; v0.12.0 — **BIOS/firmware deployment + portable configuration**: added `emulator_setup.py`, which deploys `bios/<platform>/` (including archives) into emulator directories, writes DuckStation/PCSX2 INI and fullscreen settings for mGBA/PPSSPP, and makes RPCS3 run `--installfw` automatically; deployment messages are merged into the install-complete message; v0.13.0 — **repository game submissions**: Issue form + `submissions/*.json` PR, `submission.py` validates/normalizes platform aliases/rejects duplicate shareCode, `merge_submissions.py` merges entries into the catalog CSV and archives them under `submissions/merged/`; web library "Submit game" button, CI validation, `make validate-submissions`; v0.14.0 — **official Baidu Netdisk OpenAPI**: OAuth oob authorization + automatic token refresh, transfer of public shares to `/FreedeckTmp`, dlink download (dedicated Referer/UA), cleanup after install; `provider/share_ctx` task routing (from v0.17.0 this became the QR/Cookie main path with OpenAPI demoted to an optional fallback; no CDP); repository submissions/catalog support Baidu (`server=b`); v0.14.1 — **3DS SteamOS compatibility fix**: the Azahar AppImage hits upstream issues #127/#953; on SteamOS 3.9.5 prefer Flathub `org.azahar_emu.Azahar` (automatic remote-add/install, fall back to the AppImage on failure); the 3DS wrapper forces XWayland; existing 3DS shortcuts are rewritten automatically in the background (no reinstall needed); Flatpak data directories are added to system files; v0.15.0 — **emulator saves included in cloud saves**: added `emulator_saves.py`, which discovers saves in standard/portable/Flatpak directories for 10 platforms; GBA/FC/MD/NDS match per-game saves by ROM, PSP/PS1/PS2/3DS/PS3/Switch shared directories dedupe by signature; setting `cloud_save_include_emulators` on by default (upload only at that time; restore landed in v0.16.0); v0.16.0 — **emulator save restore + per-game split + PS1 multi-disc**: `restore_roots`/`build_restore_targets` allowlisted restore (original parent directory on the same machine/first root on another machine, conflict confirmation, `*.freedeckcy-bak-*` backups); PSP/PS3 split by PARAM.SFO, 3DS by NCSD title id (PS1/PS2/Switch still shared); PS1 prefers `.m3u`, and multiple `.cue/.chd` files automatically generate `freedeckcy-multidisc.m3u`; v0.17.0 — **Baidu QR-code/Cookie main path**: Passport QR code (`getqrcode` → `unicast` → `qrbdusslogin`) exchanged for `BDUSS/STOKEN/PTOKEN`, Cookie stored in `state.json` under `baidu_login`; install prefers Cookie, OpenAPI is an optional fallback; aria2 tasks carry Baidu Cookie/Referer/UA; **no CDP/web reverse engineering**; v0.18.0 — **scan installed + QR error diagnostics**: `scan_installed_games()` scans one level of the install directory, matches catalog entries by directory name, backfills appid/emulator ROM; web library "Scan installed" button + `POST /api/tianyi/installed/scan`; Baidu QR adds a BAIDUID CookieJar and HTTP status/error reasons (no longer stuck in waiting); v0.19.0 — **SD card selection**: added `storage_options.py`, which parses `/proc/mounts` and recognizes writable mounts such as `/run/media` (SteamOS SD) and `/storage` (DroidDeck); the QAM "Paths" page switches download/install directories with one click and shows suggested subdirectories and free space; v0.20.0 — **Decky native game library**: QAM route `LibraryPage` (`/freedeckcy/library`), Game Library/Installed/Refresh tabs, search + platform/category/sort dropdowns, 20 items per page with pagination, install confirmation and launch/directory/uninstall/scan actions for installed games; everything goes through callables and does not depend on the web page or local HTTP; the web library remains as a backup; v0.21.0 — **scan migration + automatic Steam shortcut recovery**: "Scan installed games" moves to QAM Settings → Install; `scan_installed_games()` dedupes and then automatically creates Steam shortcuts (finds the exe for PC games, generates a wrapper for emulators, never downloads automatically), a second pass backfills existing records, returns `steam_added`/`steam_recovered_count`/`shortcut_error`; v0.22.0 — **diagnostics self-check + one-click diagnostics bundle**: the QAM Settings "Diagnostics" page runs the self-check (plugin/catalog/runtime/Steam/storage/network/Baidu QR/tasks/logs, ok/warn/fail/skip + fix), exports a zip containing `self-check.json` to the download directory (0600); v0.23.0 — **native library fallback + QR timeout**: QAM "Game Library" now prefers `showModal(<LibraryPage />)` and only falls back to the full-screen route on failure; the home/library pages show the `QAM native UI v0.23.0`/`native UI · v0.23.0` label; Baidu QR click shows an immediate toast, front-end/back-end timeouts (20s/12s, 15s) and `Baidu QR` logs; v0.24.0 — **back/close fix**: `LibraryPage` supports `onClose` (modal close), route mode uses `Navigation.NavigateBack()`; top sticky bar "Back/Steam Library/Refresh" + title bar "Back"; "Steam Library" goes through `Router.NavigateToLibraryTab()`; v0.25.0 — **playtime isolation**: `LibraryTimeBlock` renders only when `managed===true`, otherwise `return null` immediately; the backend matches by AppID first and then by title, and returns `managed=false` without querying HLTB when there is no match; v0.26.x — backend architecture split (`update_flow`, etc.) and stability fixes; v0.27.0–v0.27.20 — game library visual overhaul (cover grid/Hero/category shelves/skeleton screens/detail page), QAM layout and top bar/search/filter/update-button alignment, focus ring/safe area/horizontal scrolling, full Steam Deck gamepad and trackpad adaptation.

---

## Priority Overview

| # | Item | Priority | Estimate | One-line benefit |
|---|---|---|---|---|
| 1 | Split `tianyi_service.py` | P0 (engineering health) | Large | Make the 8,200-line mega-class maintainable and testable |
| 2 | Add `ruff` / `mypy` to CI | P0 (engineering health) | Medium | Catch low-level mistakes and type drift |
| 3 | Cloud-save plan/apply and HTTP handler tests | P1 (data safety) | Medium | Cover the paths most likely to lose saves |
| 4 | Remove the node dependency (pure Python implementation) | P1 (deployability) | Medium | Drop the ~90 MB node runtime and cross-architecture issues |
| 5 | Release automation workflow | P1 (release quality) | Small | Reproducibly build installable zips |
| 6 | Resource catalog update mechanism | P2 (content operations) | Medium | Fix broken links without shipping a release |
| 7 | ~~Diagnostics page~~ ✅ (v0.22.0) | ~~P2~~ | ~~Medium~~ | Users can self-diagnose "why won't it install" — delivered via the QAM "Diagnostics" page |
| 8 | i18n | P2 (maintainability) | Medium | Switchable Chinese/English and centralized copy |
| — | Port the release's resource pool / upstream proprietary implementation | **Explicitly out of scope** | — | Baidu/emulators are already implemented independently; resource-pool compliance and maintenance risks outweigh the benefits |

> There are also 9 candidate capabilities from the author's v0.6 (Range probing, `7z t`, SQLite task store, emulators, etc.); see **§9** for a ranking by "cost-effectiveness + effort"; approaches explicitly not adopted are in **§10.2**.

---

## 1. Split `tianyi_service.py` (P0, currently ~8,200 lines)

**Current state**: `py_modules/tianyi_service.py` is about 8,200 lines, with a single `TianyiService` class and 100+ methods covering independent responsibilities such as installation, cloud saves, login capture, playtime, and panel caching; in addition, long functions such as `_post_process_completed_task` / `_collect_cloud_save_candidates` are still growing.

**Why**: a mega-class makes changes risky and review difficult, and tests can only instantiate the whole object; the second round's "grouped install / restart recovery" was layered onto this same file, and the longer the split is delayed, the higher the cost becomes.

**Cost**: large-scale moves carry regression risk, so the work must be staged while keeping the external interface unchanged; short-term diffs are large; all `tianyi_service.py:line` references in the docs must be updated in sync.

**Acceptance criteria**:

- Split out at least 4 modules (suggested: `install_flow.py`, `cloud_save_flow.py`, `login_flow.py`, `playtime.py`), with `TianyiService` only orchestrating and holding state;
- The call surface of `main.py` / `tianyi_http.py` stays unchanged (RPC and HTTP contracts unchanged);
- `make test` (currently 555 test cases) stays fully green, with new cases covering the moved modules (the native library counts as front-end build verification);
- A single Python file < 1,500 lines; references and the module diagram in `docs/ARCHITECTURE.md` are updated in sync.

**Files involved**: `py_modules/tianyi_service.py`, `py_modules/tianyi_http.py`, `docs/ARCHITECTURE.md`.

---

## 2. Add `ruff` / `mypy` to CI (P0)

**Current state**: CI only runs pytest + the front-end build; the Python side has no static checks and no type checks (`ARCHITECTURE.md` P2-21 already records this).

**Why**: the code contains many `Any` / dynamic dictionaries, and `decky` is an injected module; static checks can catch undefined names, typos, and type drift without changing behavior (for example, undefined variables, missing imports, and unused variables are exactly the kinds of issues ruff catches directly).

**Cost**: existing warnings must be worked through first, so they cannot all be enabled at once; `decky` needs a stub (the repository root already has a reusable `decky.pyi`); `aiohttp` / dynamic JSON need localized `Any` or ignore rules; it is recommended to proceed "ruff first, then mypy gradually".

**Acceptance criteria**:

- CI gains a `ruff check` step: the first version may enable only a high-confidence rule set (e.g. `E9,F63,F7,F82` + unused imports), with a baseline of 0 errors;
- CI gains a `mypy` step: only check modules in `py_modules/` that already have type annotations, allow `--ignore-missing-imports`, use a gradual allowlist, and do not require all green at once;
- A local `make lint` (new target) matches the CI command;
- The docs (DEVELOPMENT.md pre-commit checklist) are updated in sync.

**Files involved**: `.github/workflows/ci.yml`, `Makefile`, `docs/DEVELOPMENT.md`, `pyproject.toml` (new).

---

## 3. Cloud-save plan / apply and HTTP handler tests (P1)

**Current state**: unit tests already cover cloud-save version time parsing, part of the models, and the install pipeline, but the cloud-save restore `plan` / `apply` (which actually overwrite files) and the local HTTP handlers are **essentially untested**; this is the path in the whole project that comes closest to "losing data".

**Why**: `plan` relies on the manifest's `source_path` to infer Proton relative paths and counts conflicts, and `apply` backs up before overwriting; a regression in path inference, boundary validation, or failure rollback would destroy user saves, and manual verification is not reliable.

**Cost**: it is necessary to construct manifests, temporary directories, fake 7z/downloaders, and an aiohttp test client; file IO may need to be further abstracted into injectable dependencies, and the test code volume is substantial (an estimated 30–50 new cases).

**Acceptance criteria**:

- `plan_cloud_save_restore` covers: normal path inference, rejection of manifest path escape (`../`), conflict counting, `selected_entry_ids` filtering;
- `apply_cloud_save_restore` covers: backup naming `*.freedeckcy-bak-<timestamp>` before overwrite, count of files already restored on failure, playtime merged by taking the larger value;
- `tianyi_http.py`'s `handle_cloud_save_*` / `handle_install_*` cover normal and error responses (including 4xx/5xx and redacted fields);
- Everything runs offline (no network, no writes to the real Steam directory), and `make test` is fully green.

**Files involved**: `tests/`, `py_modules/tianyi_service.py`, `py_modules/tianyi_http.py`.

---

## 4. Remove the node dependency (P1)

**Current state**: the share-parsing fallback (`backend/tianyi_share_resolver.js`) and cloud-save upload (`backend/tianyi_cloud_upload.js`) run as Node subprocesses; `make runtime` bundles Node v20 into the zip (~94 MB for a single x86_64 file, with a separate download needed for aarch64).

**Why**: the Node runtime is the largest source of package size and cross-architecture complexity; SteamOS does not ship Node by default, so users who do not run `make runtime` will fail during cloud saves; Node ESM/ABI compatibility issues are also a known pitfall.

**Cost**: the Python side needs AES-128-ECB encryption, RSA public-key encryption, MD5/HMAC signing, and 10 MB chunked upload; the Python bundled with Decky does not guarantee `cryptography` / `pycryptodome`, so either a self-contained pure-Python implementation (performance/complexity) or a vendored library is required; the Node fallback should be kept behind a switch for comparison and rollback.

**Acceptance criteria**:

- In an environment **without node**, cloud-save upload / version listing / download and the share-parsing fallback all work (implemented in Python, with the Node implementation retained as a fallback such as `FREEDECKCY_CLOUD_IMPL=node`);
- Upload results match the existing Node implementation (same test account: filenames, chunks, and `sliceMd5` verification pass);
- `make runtime` can optionally skip downloading node (`--only aria2,7z`), and the zip size drops noticeably;
- The new implementation has offline unit tests (crypto/signing with fixed vectors).

**Files involved**: `py_modules/tianyi_client.py`, `backend/*.js`, `scripts/fetch_runtime.sh`, `docs/DEVELOPMENT.md`.

---

## 5. Release automation workflow (P1)

**Current state**: releases are produced manually with `make runtime && make package`, yielding `dist-artifacts/freedeckCY-v<version>.zip`; the repository has no tag/release CI (this completion only added CI for tests and the front-end build).

**Why**: the runtime binaries are large and come from external networks, so manual packaging easily misses `defaults/runtime/` or forgets to rebuild `dist/index.js`; automation can produce reproducible installers with checksums.

**Cost**: the GitHub Actions runner must be able to download aria2/7z/node (external network and size, requiring a caching strategy); version numbers/release notes need conventions; artifact verification (sha256) and the signing strategy must be decided.

**Acceptance criteria**:

- Pushing a `v*` tag (or manual `workflow_dispatch`) triggers: pytest → `pnpm build` → `make runtime` → `make package` → upload zip + `sha256sum` to the GitHub Release;
- The artifact structure is verified with `unzip -l` (`main.py`, `plugin.json`, `dist/`, `py_modules/`, `backend/`, `defaults/` all present; `docs/`, `tests/` not in the package);
- The produced package can be installed and started on a Steam Deck via Decky Loader (manual acceptance once);
- The version number is linked to `package.json`, and release notes are templated.

**Files involved**: `.github/workflows/`, `Makefile`, `scripts/package.sh`, `docs/DEVELOPMENT.md`.

---

## 6. Resource catalog update mechanism (P2)

**Current state**: the resource catalog `defaults/tianyi_catalog/*.csv` is distributed with the plugin, so updating links requires editing the repository, repackaging, and publishing a release; broken links can only be fixed manually after users report errors.

**Why**: share links expire or change extraction codes, and the catalog is the plugin's core data; a verifiable and rollback-capable update mechanism can significantly reduce maintenance costs.

**Cost**: a trusted distribution channel and integrity verification (signature/hash) must be defined, otherwise the plugin gains an attack surface for "remotely delivering arbitrary links"; caching, concurrent updates, and rollback also need handling; automatic fetching would further amplify copyright and compliance risks.

**Acceptance criteria (pragmatic version)**:

- Support "manually import a local CSV": validate the header / `down_url` domain / duplicate `game_id` → after passing, atomically replace the current catalog and keep a backup of the old version;
- Optional "fetch from a fixed URL": must include `sha256` verification, roll back to the old catalog automatically on failure, off by default and requiring the user to explicitly enable it;
- The update process has logs and UI result feedback; no background persistent network requests are introduced;
- The docs clearly state the compliance risks, and the default behavior does not change from "distributed with the package".

**Files involved**: `py_modules/game_catalog.py`, `py_modules/tianyi_service.py`, `py_modules/tianyi_http.py`, `defaults/tianyi_catalog/`.

---

## 7. ~~Diagnostics page~~ (✅ completed in v0.22.0)

**Current state**: the QAM settings page has a new "Diagnostics" tab — "Run self-check" calls `run_tianyi_diagnostics` (`run_diagnostics()`, returning a summary + label/status/detail/fix for each item), and "Export diagnostics bundle" calls `export_tianyi_diagnostics_file` (writes a 0600 zip to the download directory); the HTTP `POST /api/tianyi/diagnostics/run` is still kept; the existing `GET /api/tianyi/diagnostics` + `/diagnostics/export` and `make doctor` remain usable.

**Check items**: plugin version/catalog, state directory writability/permissions, download/install directory writability/free space (<2 GB warns), aria2c/7zz/node executable + version, catalog entry count/platforms/covers, Steam root + shortcut count, SD/external mounts, Tianyi network, Baidu QR (only the sign length is output), failed/installed tasks, log error line count.

**Acceptance criteria (completion status)**:

- ✅ Graphical self-check in QAM (no browser/local web page needed), showing ok/warn/fail/skip + fix;
- ✅ The exported zip contains `diagnostics.json`/`self-check.json`/`log-tail.txt`/`README.txt` and is written to the download directory (0600);
- ✅ Redaction: cookie/token replaced, HOME→~; Baidu QR does not output sign/cookie;
- ✅ `tests/test_diagnostics.py` covers the structure with `include_network=False`;
- ✅ DEVELOPMENT.md gains a "Diagnostics" troubleshooting flow (§6.15).

**Remaining (not done)**: enhancements such as viewing logs online and automatically uploading the diagnostics bundle (as an issue attachment).

**Files involved**: `py_modules/tianyi_service.py`, `main.py`, `src/index.tsx`, `tests/test_diagnostics.py`, `docs/`.

---

## 8. i18n (P2)

**Current state**: the UI and error messages are all hardcoded in Chinese in `src/index.tsx`, `defaults/tianyi_library_ui/`, Python return values, and logs (`ARCHITECTURE.md` P2-22).

**Why**: English users cannot use the plugin; centralized copy is also easier to maintain and keep terminology consistent.

**Cost**: the React front-end can adopt something like `i18next`, while the build-free Vue pages need a lightweight dictionary; Chinese messages returned from Python to the front end should become "error code + parameters" and be translated by the front end, otherwise both sides maintain their own copy; the effort is large and must be kept in sync continuously.

**Acceptance criteria**:

- At least two sets of copy, `zh-CN` / `en-US`; the language can be configured/auto-follow the system and is persisted to settings;
- All user-visible front-end copy comes from the dictionary (`src/index.tsx` and `defaults/tianyi_library_ui/` contain no hardcoded Chinese);
- Python key errors provide stable `reason` error codes that the front end can translate; unknown errors fall back to the original text;
- Docs and tests are updated in sync (at least covering language switching and missing-key fallback).

**Files involved**: `src/index.tsx`, `defaults/tianyi_library_ui/`, `py_modules/tianyi_http.py`, `py_modules/tianyi_service.py`, `docs/`.

---

## 9. v0.6 alignment candidates (9.2 / 9.4 delivered; 9.6 completed in v0.3.0; the 10-platform emulators of 9.8 completed across v0.6.0–v0.11.0; the Baidu OpenAPI of 9.9 completed in v0.14.0; the rest not done)

The author's v0.6 release (local read-only reference `0.6/freedeck-plugin`, not distributed with this repository) is much more complete in the download pipeline, emulators, and resource pool. The three completion rounds adopted only a few capabilities related to downloading/Steam writing (see [ARCHITECTURE.en.md](ARCHITECTURE.en.md) §13); **v0.1.1 delivered 9.2 (compatdata cleanup) and 9.4 (best-effort `7z t` verification); v0.2.0 started 9.6; v0.3.0 completed 9.6 (full catalog of 7,084 entries / 11 platforms + cover_index of 3,470 rows + platform/category dual-filter UI); v0.3.1 addressed data quality (category cleanup + validate_catalog --strict CI)**, and the rest are ranked from high to low by **cost-effectiveness + effort** for later pickup.

| # | Candidate | Priority | Effort | v0.6 source | One-line benefit |
|---|---|---|---|---|---|
| 9.1 | Range resume probing | P1 | Small | `_remote_supports_resume()` | Avoid useless retries against direct links that do not support resuming |
| 9.2 | ~~compatdata cleanup on uninstall~~ ✅ | ~~P1~~ | ~~Small~~ | `uninstall_installed_game(delete_compatdata=)` | **Delivered in v0.1.1**: optionally reclaim the Proton prefix on uninstall |
| 9.3 | Automatic Steam restart | P1 | Small | `main.py::restart_steam` | Takes effect right after shortcuts are written, no manual restart |
| 9.4 | ~~Full-archive `7z t` verification~~ ✅ | ~~P1~~ | ~~Medium~~ | `archive_validator.test_archive` | **Delivered in v0.1.1 (best-effort)**: detect corrupt archives before extraction and re-download automatically |
| 9.5 | SQLite task store | P2 | Large | `archive_task_db.py` | More reliable task persistence/querying and crash recovery |
| 9.6 | ~~Platform catalog + cover index~~ ✅ | ~~P2~~ | ~~Large~~ | `gba_catalog.py` etc. + `generate_*_cover_urls.py` | **Completed in v0.3.0** (7,084 entries/11 platforms + cover_index + dual filters), **v0.3.1 data cleanup/health check**; the cover generation pipeline is still not done |
| 9.7 | Resource pool, read-only | P2 | Medium | Tencent Docs smartsheet reading | Expand resources without introducing submissions/likes |
| 9.8 | ~~Single-platform emulator loop~~ ✅ (10 platforms, all downloaded online + BIOS/firmware deployment) | ~~P2~~ | ~~Large~~ | `emulator_adapters.py` | **v0.6.0 GBA, v0.7.0 PSP/NDS, v0.9.0 PS1/FC/MD, v0.10.0 all downloaded online, v0.11.0 3DS (Azahar)/PS2 (PCSX2)/PS3 (RPCS3)/Switch (Eden), v0.12.0 BIOS/firmware deployment + portable configuration (including archives, RPCS3 `--installfw`)**; the official 3DS/PS2/PS3 packages are x86_64-only (hidden automatically on aarch64); PS1/PS2 BIOS and 3DS/PS3/Switch system files are user-supplied |
| 9.9 | ~~Baidu Netdisk~~ ✅ (v0.17.0 QR/Cookie main path; v0.14.0 OpenAPI optional fallback) | ~~P3~~ | ~~Large~~ | `baidu_qr.py` / `baidu_openapi_client.py` | **v0.17.0**: Passport QR code → Cookie, QAM QR sign-in/sign-out, installs prefer Cookie, tasks carry Baidu Cookie/Referer/UA; **v0.14.0**: OpenAPI (self-built app OAuth/transfer/dlink) as the cookie-less fallback; **no CDP/web reverse engineering**; repository submissions/catalog support Baidu (`server=b`) |

### 9.1 Range resume probing (P1, effort: small)

**v0.6 reference**: `_remote_supports_resume()` sends `Range: bytes=0-0` to direct links and only considers resuming supported if it gets back 206 / `Content-Range` / `Accept-Ranges: bytes`.

**Why**: the current "direct link expired → re-addUri" assumes the server supports resuming by default; routes that do not support it keep retrying the same segment, wasting time and requests.

**Cost**: each task that needs recovery incurs one extra probe request; when the probe fails, it must conservatively assume "supported" to avoid re-downloads caused by misjudgment.

**Acceptance criteria**:

- Add `probe_resume_support(direct_url, headers)`: parse 206 / `Content-Range` / `Accept-Ranges`, return True on exceptions (conservative resume);
- Call it only once on the **recovery/link-switch path**; normal downloads do not probe extra; results go to the log;
- Offline unit tests cover the four cases: 206 / 200+Accept-Ranges / 200 without the header / exception;
- DEVELOPMENT troubleshooting gains a line: "`resume unsupported` in the log means that route does not support resuming".

**Files involved**: `py_modules/tianyi_service.py`, `py_modules/tianyi_client.py`, `tests/`, `docs/DEVELOPMENT.md`.

### 9.2 ~~compatdata cleanup on uninstall~~ (✅ delivered in v0.1.1)

**Delivered implementation (v0.1.1)**:

- `steam_shortcuts.find_compatdata_dirs(app_id)` locates `<library>/steamapps/compatdata/<appid>` across all Steam libraries;
- `tianyi_service.preview_uninstall()` + the `preview_tianyi_uninstall` RPC return the install directory and Proton prefix usage; the QAM uninstall confirmation shows both sizes with three buttons: cancel / delete game files only / delete the Proton prefix too (default: not deleted);
- `uninstall_installed_game(delete_compatdata=...)` returns `compatdata: {requested, app_id, paths, removed_paths, freed_bytes}`;
- Path safety: `_can_remove_compatdata_dir()` only allows the standard `steamapps/compatdata/<appid>` structure and rejects symlinks; the appid is resolved by `_resolve_record_app_id()` from the record or the shortcut.

**Still not done**: per-appid leftovers other than `shadercache` / `compatdata` are not cleaned automatically; the "not deleted by default" semantics remain unchanged.

### 9.3 Automatic Steam restart (P1, effort: small)

**v0.6 reference**: `main.py::_restart_steam_best_effort()`, which restarts via the user session `systemctl --user restart steam-launcher.service` (with `sudo -u <user>` if necessary).

**Why**: after writing `shortcuts.vdf`, Steam must be restarted for the change to be visible; manual restarts are a high barrier for handheld users.

**Cost**: restarting Steam interrupts running games/downloads; it must be triggered explicitly by the user, check whether Steam is running, and **must not introduce root** (use the deck user session only; the `sudo` branch is not adopted).

**Acceptance criteria**:

- The QAM settings page/install-complete prompt offers a "Restart Steam" button (explicit click, not automatic);
- Use `systemctl --user restart steam-launcher.service` (setting `XDG_RUNTIME_DIR` / `DBUS_SESSION_BUS_ADDRESS`), with a "please restart manually" hint on failure;
- Refuse to run while Steam has a game running (or ask for a second confirmation);
- Unit tests cover command construction and failure branches (without actually restarting); the docs spell out the side effects.

**Files involved**: `main.py`, `py_modules/tianyi_service.py`, `src/index.tsx`, `tests/`.

### 9.4 ~~Full-archive `7z t` verification~~ (✅ delivered in v0.1.1, best-effort)

**Delivered implementation (v0.1.1)**:

- `SevenZipManager.test_archive()` runs `7z t` on the main volume before extraction (default timeout 900 s); **if 7z is missing or cannot be executed, it returns "verification skipped" and does not block the install** (a working 7z is still required for the later extraction);
- Verification failure → `_schedule_archive_repair()`: quarantine the bad archive (`*.freedeckcy-archive-invalid-*`) + automatically re-download once from the original direct link (once per task, `post_processed` is not set to true); after the re-download completes, the install is retried automatically;
- If it still fails the second time → the task goes to `failed`, and the user retries manually with the task row's "Retry" button;
- Unit tests cover: verification success / failure / skip when 7z is not executable / automatic re-download and the second-failure path.

**Still not done**: no hash/signature verification; the timeout and "skip verification by size" are not yet configurable (currently a fixed 900 s timeout, always attempted); `7z t` reads large archives one extra time, which is a known overhead.

### 9.5 SQLite task store (P2, effort: large)

**v0.6 reference**: `archive_task_db.py` (SQLite + WAL + resource/file task tables).

**Why**: `state.json` is fully rewritten and concurrent writes rely on in-memory locks; with many tasks or a crash, the last state is easily lost. SQLite can provide atomic updates, historical queries, and recovery.

**Cost**: designing a schema, migrating the existing `state.json`, keeping compatible reads; introducing database file permissions/backup/cleanup policies; the test volume increases noticeably.

**Acceptance criteria**:

- The new database `~/.local/share/freedeckCY/tianyi/tasks.db` (0700 directory / 0600 file), WAL mode;
- On first start, automatically migrate tasks and installed records from `state.json`, falling back to JSON on failure;
- Task state updates become row-level UPSERTs instead of whole-file rewrites; after a crash, a restart recovers to the most recent consistent state;
- Unit tests cover migration, concurrent updates, and fallback for a corrupt database; README/DEVELOPMENT explain the responsibilities of the two files.

**Files involved**: `py_modules/tianyi_store.py` (or a new `task_store.py`), `py_modules/tianyi_service.py`, `tests/`, `docs/`.

### 9.6 ~~Platform catalog + cover index~~ (✅ completed in v0.3.0, v0.3.1 data cleanup)

**Delivered implementation (v0.3.0 / v0.3.1)**:

- **Full catalog**: `defaults/tianyi_catalog/freedeckcy_catalog.csv` (16 columns, **7,084 valid entries / 11 platforms**: PC 2,540 / FC 1,475 / NDS 722 / PSP 575 / GBA 553 / 3DS 305 / PS2 250 / PS1 194 / PS3 194 / MD 191 / Switch 85); the old `gamebox_all_links_*.csv` is kept as a fallback;
- **Reproducible**: `scripts/merge_v06_catalog.py` generates it by merging the upstream v0.6 catalog (7,041 rows / 28 columns), adding 43 entries unique to the old catalog;
- **Cover index**: `defaults/tianyi_catalog/cover_index.csv` (3,470 rows, from v0.6), filled in by `game_id`/title without overwriting existing values; after merging, **6,823 / 7,084 resources ship with a cover**;
- **Cover cache**: `cover_cache.json` (0600, positive cache 7 days / negative cache 30 minutes), priority "catalog static → cache → Steam store → ProtonDB";
- **Platform/category dual-filter UI**: two filter bar rows on the library page (All platforms + each platform; All categories + Top 12 categories), gamepad focus order search box → search button → platform row → category row → cards;
- **Link formats**: `_is_valid_tianyi_url()` / `parse_share_url()` support both Tianyi share link forms, `/t/<code>` and `/web/share?code=`;
- **Data quality (v0.3.1)**: `normalize_categories()` cleans categories at load time (strip platform names/dedupe/emulator fallback), rewriting 606 data rows, with 606 entries labeled "Emulator"; `scripts/validate_catalog.py --strict` runs in CI, so duplicate `game_id`/invalid links/empty titles/categories mixing platform names turn CI red;
- Tests: `make test` 353 cases (including `tests/test_catalog_platform.py` / `tests/test_droiddeck.py` / `tests/test_emulator.py` / `tests/test_cloud_auto.py` / `tests/test_submissions.py` / `tests/test_baidu_integration.py` / `tests/test_emulator_saves.py` / `tests/test_storage_options.py` / `tests/test_diagnostics.py` and cases for category cleanup/default-catalog cleanliness).

**Still not done**: the **generation pipeline** for the cover index (`generate_*_cover_urls.py`-style scripts; the current index comes directly from v0.6), and a purely offline cover library when there is no network; all 10 emulator platforms are now integrated (see 9.8).

### 9.7 Resource pool, read-only (P2, effort: medium, **high compliance risk**)

**v0.6 reference**: Tencent Docs smartsheet resource pool (`get_qqdocs_login_url` / `_decode_qqdocs_smartsheet_blob` / `list_resource_pool_catalog`).

**Why**: the resource pool can supplement the catalog when links die; read-only mode is lower-risk than "submissions/likes".

**Cost**: it depends on a Tencent Docs login session and proprietary parsing; the content source is uncontrollable and compliance risks remain high; caching and filtering are needed (to prevent malicious links).

**Acceptance criteria**:

- Read-only: only fetch/parse the resource pool catalog (requires a Tencent Docs login session, or supports importing a manually exported spreadsheet), and **does not implement submissions, likes, or automatic CDP operations** (see §10.2 for rejected items);
- Off by default, explicitly enabled; parsing results first land in a local cache file for manual review; not automatically merged into the main catalog;
- Validate the `down_url` domain/duplicates; unit tests use fixed fixtures, no network;
- The docs prominently flag copyright/compliance risks.

**Files involved**: `py_modules/tianyi_service.py`, `py_modules/game_catalog.py`, `defaults/`, `tests/`, `docs/`.

### 9.8 ~~Single-platform emulator loop~~ (✅ 10 platforms completed, all downloaded online; v0.12.0 BIOS/firmware deployment completed)

**Delivered implementation (from v0.6.0 / v0.7.0 registry / v0.9.0 six platforms / v0.10.0 all downloaded online / v0.11.0 ten platforms)**:

- The `EmulatorSpec` registry in `py_modules/emulator_manager.py` currently integrates **10 platforms**:
  - GBA = mGBA 0.10.5 (x64/arm64, downloaded online on first install);
  - PSP = PPSSPP 1.20.4, NDS = melonDS 1.1, PS1 = DuckStation (requires BIOS), FC/MD = Mesen2 2.1.1 (shared cache);
  - **3DS = Azahar 2126.2 (x86_64 only, requires system files)**;
  - **PS2 = PCSX2 v2.8.2 (x86_64 only, requires BIOS)**;
  - **PS3 = RPCS3 build-8d6b42e (x86_64 only, requires firmware)**;
  - **Switch = Eden v0.2.1 (x86_64 + aarch64, requires prod.keys + firmware)**;
- **Architecture capability matrix**: `available_platforms(arch)` filters by `spec.assets` — all 10 are available on x86_64; on aarch64 (DroidDeck) only GBA/PSP/NDS/PS1/FC/MD/Switch exist, because 3DS/PS2/PS3 have **no official arm64 packages**, so entries and the platform filter bar do not appear after allowlist filtering (`emulator_status` returns "platform hidden");
- Resolution order (no bundled-package branch): `FREEDECKCY_<PLATFORM>_BIN` → downloaded/unpacked (`emulators/<state_key>/<arch>/`) → system command → Flatpak (`io.mgba.mGBA` for mGBA; `org.azahar_emu.Azahar` for 3DS, installed automatically on SteamOS); `emulator_status` can return `source=download` on demand, and `ensure_emulator` downloads and unpacks AppImage/zip separately at install time (no FUSE dependency);
- BIOS/firmware deployment (v0.12.0): `emulator_setup.setup_emulator()` scans `bios/<platform>/` (including `.zip/.7z/.rar`, unpacked by 7zz into a `_extracted/` cache), deploys into each emulator's directory, and writes portable configuration (PS1 `<AppDir>/bios` + DuckStation INI, PS2 three BIOS locations + PCSX2 INI, NDS bios/firmware, Switch keys/`.nca`, PS3 `--installfw`, 3DS sysdata, GBA/PSP fullscreen configuration); only missing files are filled in and only individual keys are changed, and deployment messages are merged into the install-complete message;
- **v0.10.0 packaging changes**: `scripts/fetch_emulator.sh` and `make emulator-runtime` are deleted, `defaults/runtime/mgba/` is no longer packaged, and the plugin package does not bundle emulators (~68 MB → ~45 MB); offline use can pre-seed the cache manually or use `FREEDECKCY_*_BIN`;
- **v0.14.1 3DS SteamOS fix**: the official Azahar AppImage has upstream compatibility issues #127/#953 on SteamOS, so on SteamOS 3.9.5 the Flathub Flatpak `org.azahar_emu.Azahar` is preferred (`_is_steamos`/`flatpak_installed`/`_ensure_flatpak`, with automatic `remote-add` + `install`, falling back to the AppImage after a retry of the system install); the 3DS wrapper forces XWayland (`QT_QPA_PLATFORM=xcb`/`SDL_VIDEODRIVER=x11`); installed 3DS records have their launch script rewritten automatically by the background `_repair_emulator_launchers`, with no reinstall needed; Flatpak data directories are added to system files; tests 330;
- Tests `tests/test_emulator.py` / `tests/test_catalog_platform.py` (architecture allowlist, catalog counts, 3DS Flatpak/wrapper, PS1 m3u); `make test` 353 cases.

**Remaining / boundaries**: 3DS Flatpak verification on real hardware (SteamOS 3.9.5/Deck), AppImage compatibility improvements for environments without Flatpak (e.g. a bundled runtime/dependencies), emulator verification on real hardware (DroidDeck/ARM64), emulator save restore/conflict mapping (upload was completed in v0.15.0), multi-disc games (`.m3u`/multiple `.cue`) and BIOS/firmware version validation; BIOS/firmware/keys are user-supplied (for copyright reasons the plugin only deploys them, never downloads them); official arm64 packages for 3DS/PS2/PS3 do not exist, so ARM devices cannot install them; all integrated platforms **do not include save management**.

**Files involved**: `py_modules/emulator_manager.py`, `py_modules/game_catalog.py` (`allowed_platforms` allowlist), `py_modules/tianyi_service.py`, `defaults/tianyi_library_ui/`, `tests/test_emulator.py`, `tests/test_catalog_platform.py`, `docs/`.

### 9.9 ~~Baidu Netdisk~~ (✅ v0.17.0 QR/Cookie main path; OpenAPI optional fallback)

**Completed**:

- **v0.17.0 main path (QR code/Cookie)**: Passport `getqrcode` → `unicast` long polling (waiting/scanned/confirmed) → `qrbdusslogin` exchanged for `BDUSS/STOKEN/PTOKEN` (v0.18.0 added the BAIDUID CookieJar and HTTP status/error diagnostics, and non-timeout network errors during polling turn into `stage=failed`); QAM "Baidu Netdisk (QR sign-in)" QR code/cancel/sign-out; the Cookie is stored in `state.json` under `baidu_login` (0600), and the QR session lives only in memory for 180 s; the install plan **prefers Cookie**, aria2 tasks carry Baidu Cookie/Referer/UA, and retries re-fetch the direct link per provider;
- **v0.14.0 OpenAPI (optional fallback)**: self-built app OAuth oob + automatic token refresh, public-share transfer to `/FreedeckTmp`, dlink download, cleanup after install; this path is used **only when there is no Cookie**;
- Repository submissions/catalog support Baidu links (`server=b`); tests 348 cases.

**Explicitly out of scope**:

- CDP/web-interface reverse engineering (the Cookie only comes from Baidu Passport's official QR-code interface);
- Public apps/built-in App Keys (OpenAPI requires a self-built app);
- Any "speed-up" capability that bypasses Baidu rate limits or transfer quotas/risk controls.

**Remaining (not done)**:

- **Real-device verification of scan confirmation/exchanging for a Cookie** (so far only the `getqrcode` PNG response and `unicast` returning waiting when unscanned have been tested);
- Automatic Cookie renewal/expiry detection and reminders, multi-account switching;
- A compatibility layer for Baidu web-interface changes (the QR/direct-link interfaces may change);
- Tiered retries and messages for OpenAPI transfer failures/full quotas.

---

## 10. Explicitly not recommended

### 10.1 Porting the release's Baidu Netdisk / emulator integration / resource pool

- **Reason 1 (compliance)**: these features would further expand the distribution surface of pirated resources (new cloud-drive sources, emulator ROM partitions, user-uploaded resource pools), and the copyright and cloud-drive terms-of-service risks are significantly higher than the status quo.
- **Reason 2 (provenance)**: Baidu Netdisk and emulators are already implemented independently in this repository; only the upstream **resource pool/proprietary implementation** exists solely in its release package, with no maintainable source baseline, so reverse engineering/rewriting would be costly and could not follow upstream fixes.
- **Reason 3 (engineering)**: the goal of this repository's completion work is to "make the existing capabilities maintainable, buildable, and testable", and adding new resource-distribution channels conflicts with that goal and would dilute the limited maintenance effort.
- **Conclusion**: do not port, do not bundle, and do not provide integration guidance; if expansion is truly needed, copyright compliance must be resolved first and it should be maintained as a separate project.

### 10.2 Specific v0.6 approaches not adopted

- **`plugin.json`'s `flags: ["root"]` + `steam_host_writer` + `sudo -u deck` for writing Steam files**: v0.6 lets the plugin run as root and then uses a helper with reduced privileges to write files. This plugin always runs as the deck user, and introducing root would widen the privilege surface and increase Decky review/misuse risks; the current "same-user atomic writes + backup before writing + read-back after writing" is sufficient (see ARCHITECTURE §13.3).
- **Likes/submissions on the Tencent Docs resource pool**: these require a Tencent Docs login session + CDP submission (`_submit_resource_pool_entry_via_cdp`, etc.) and are user-generated-content/operations features that significantly widen the compliance surface; the read-only version is retained as candidate §9.7. **Submission needs now go through the v0.13.0 repository Issue/PR channel (§9.10)**, without touching the Tencent Docs login session.
- **Baidu web-version CDP collection / undocumented interfaces**: these require reverse engineering web interfaces/collecting login sessions, with high maintenance costs and account-ban risks; v0.17.0 switched to the **official Baidu Passport QR code** to obtain the BDUSS/Cookie (main path), with OpenAPI only as an optional fallback, and **CDP/web-interface reverse engineering is still not done**.
- **Reverting to "main library only" in order to "align with v0.6"**: v0.6 does not parse `libraryfolders.vdf` and only looks for `compatdata` in the main library; this repository already supports multiple libraries/SD cards/Flatpak, and **will explicitly not regress**.

### 10.3 Other out-of-scope items

- No "speed-up" capability that bypasses cloud-drive rate limits/risk controls (the status quo is already "no cap", with no additional optimization);
- No collection of user data and no usage-statistics reporting;
- No built-in resource search/recommendation and other operations features (only the read-only bundled CSV or the read-only resource-pool cache of §9.7).

---

## Other small items (P3 candidates)

| Item | Description | Acceptance highlights |
|---|---|---|
| Decky native game library ✅ | **Since v0.20.0, visual/input overhaul in v0.27.20**: QAM `LibraryPage` (modal preferred/route fallback); cover grid, Hero, category shelves, skeleton screens, detail page, 30 items per page + load more, install source selection and installed actions; everything goes through callables. **Remaining**: native task progress page, scanning multiple directories | Done; the old web library is only for debugging/fallback |
| Game library visuals/gamepad/touch ✅ | **Delivered in v0.27.0–v0.27.20**: responsive cover grid/cards, Hero/category shelves, poster detail page, skeleton screens, focus animations; search/filter/update buttons aligned; category white bar hidden; single-row top bar; focus ring/top safe area; D-pad/left stick, A/B, L1/R1, L2/R2, trackpad scrolling | Done; verified against real-device CEF dimensions |
| SD card/external storage selection ✅ | **Delivered in v0.19.0**: `storage_options.py` parses `/proc/mounts`, recognizes `/run/media` (SteamOS SD), `/media`, `/mnt`, `/storage` (DroidDeck), and `/sdcard` writable sub-mounts (filtering system fstypes/mount roots), and returns free/total; the QAM "Paths" page switches download/install directories with one click, suggesting `freedeckCY/{downloads,installed}`. **Remaining**: custom subdirectory names, low-space warnings, same-disk Steam library detection | Done; continue with "Remaining" later |
| Library page playtime isolation ✅ | **Delivered in v0.25.0**: `LibraryTimeBlock` renders only when `data.managed===true`, and returns `null` immediately when unmatched/not loaded (no "Loading" shown); `get_library_game_time_stats()` first matches exactly by AppID via `_resolve_installed_record_by_app_id()`, then normalizes by title, and when unmatched returns `managed=false` + all zeros without calling `resolve_hltb_stats`; only affects plugin-installed/backfilled games. **Remaining**: optional manual switch (e.g. a "show playtime on library page" setting) | Done |
| Native library back/close fix ✅ | **Since v0.24.0, root-node onCancel in v0.27.12+**: modal uses `onClose→modal.Close()`, route uses `Navigation.NavigateBack()`; top bar back/Steam Library/refresh; "Steam Library" goes through `Router.NavigateToLibraryTab()`; the B button is bound to the detail/library root node. **Remaining**: fullscreen mode optimization | Done |
| Native library fallback + QR timeout ✅ | **Since v0.23.0, UI version label removed in v0.26.51**: QAM "Game Library" prefers `showModal(<LibraryPage />)` and falls back to `Navigation.Navigate(LIBRARY_ROUTE)`; Baidu QR clicks show an immediate toast, with front-end/back-end timeouts and `Baidu QR` logs (sign length only). **Remaining**: front-end hot-reload hint | Done; the version is taken from the plugin list/package.json |
| Diagnostics self-check + one-click diagnostics bundle ✅ | **Delivered in v0.22.0**: the QAM Settings "Diagnostics" page offers "Run self-check" (`run_tianyi_diagnostics`, summary + label/status/detail/fix per item) and "Export diagnostics bundle" (`export_tianyi_diagnostics_file`, writes a 0600 zip to the download directory); checks plugin/catalog/runtime/catalog data/Steam/storage/Tianyi network/Baidu QR/tasks/logs; the zip contains `diagnostics.json`/`self-check.json`/`log-tail.txt`/`README.txt`; Baidu QR only outputs the sign length. **Remaining**: online log viewing, diagnostics upload (e.g. automatic issue-attachment upload) | Done; network items depend on connectivity |
| Scan installed + automatic Steam recovery ✅ | **Delivered in v0.21.0**: the scan entry moves to **QAM Settings → Install** (the native library installed page no longer has a button); `scan_installed_games()` dedupes by name/exe with `list_all_shortcuts_sync()`, finds the exe for PC games via `_find_scanned_executable()`, and automatically recreates shortcuts for emulators via `ensure_emulator(allow_download=False)` + wrapper; a second pass backfills existing PC entries with `steam_app_id=0`; returns `steam_added`/`steam_recovered_count`/`shortcut_error`. **Remaining**: automatic Steam restart, custom exe selection | Done; Steam must be restarted/switch users/reopen the library page for new shortcuts to appear |
| Scan installed games ✅ | **Delivered in v0.18.0**: `scan_installed_games()` scans one level of `settings.install_dir` (up to 500 entries, skipping compatdata/steamapps/downloads, etc.), matches by normalized directory name and catalog title, backfills the Steam appid, uses `find_rom_file()` to find the ROM for emulators, and completes `TianyiInstalledGame`; web library "Scan installed" button + `POST /api/tianyi/installed/scan`. **Boundaries**: only one level is scanned, directory names must match, and only records are backfilled, no shortcuts are created | Done; support custom directory name aliases on demand |
| Automatic cloud saves (Ludusavi + gamewatch + emulator saves) ✅ | **Delivered in v0.8.0**: the bundled Ludusavi manifest (53,549 games, MIT) is used for title/SteamID matching and resolved to the Proton prefix, merged with the existing Proton scan; gamewatch checks for game exits every 8 s and uploads only **the game_id that just exited** (30 s debounce); a fingerprint (relative path + size + mtime, ≤5,000 files) is persisted for dedupe, with `reason=unchanged` when nothing changed; the `cloud_save_auto_upload` setting is on by default and can be disabled in QAM. **v0.15.0 emulator save upload**: `emulator_saves.py` covers 10 platforms (GBA/FC/MD/NDS match per-game saves by ROM; PSP/PS1/PS2/3DS/PS3/Switch shared memory cards/title directories dedupe by path signature), `source_strategy=emulator_saves`; the `cloud_save_include_emulators` setting is on by default. **v0.16.0 restore/split**: `restore_roots`/`build_restore_targets` allowlisted restore (original parent directory on the same machine/first root on another machine, conflict confirmation, `*.freedeckcy-bak-*` backups); PSP/PS3 (PARAM.SFO) and 3DS (NCSD title id) are split per game; PS1 multi-disc prefers `.m3u`/generates it automatically. **Remaining**: PS1/PS2 single memory cards and the Switch directory still cannot be split per game; cross-device 3DS paths may degrade to the root directory; the shared-card conflict policy (whole-card overwrite) is still coarse; trimming large 3DS/Switch directories, cross-device sync/version retention | Upload + restore/split done; continue with "Remaining" later |
| First tier: catalog browsing / pagination / sorting / installed management / diagnostics export / update check ✅ | **Delivered in v0.5.0, changed to native 30 items per page + load more/filter chips in v0.27.20**: the library page browses all resources as soon as it opens, with platform/category/sort filters, an installed tab, diagnostics export, and update check | Done |
| DroidDeck adaptation ✅ | **Delivered in v0.4.0**: ARM64 runtime selection (`make runtime ARCH=aarch64`), `is_droiddeck()` detection, automatic ARM Proton resolution (`droiddeck-proton-arm64`/`11-arm64`), dual Steam roots (x64 client preferred), `PACKAGE_ARCH` packaging (`-arm64`/`-universal`). **Not yet verified on real hardware**; on aarch64, emulators support GBA/PSP/NDS/PS1/FC/MD/Switch (v0.11.0), while 3DS/PS2/PS3 are hidden automatically by the catalog allowlist because no arm64 official packages exist (§9.8) | Return to this item after real-device verification passes; see [DROIDDECK.en.md](DROIDDECK.en.md) |
| Catalog data health check / category cleanup ✅ | **Completed in v0.3.1**: `normalize_categories` + `normalize_catalog_categories.py` cleaned 606 rows, `validate_catalog.py --strict` runs in CI (cover coverage 96.3%, total size about 39 TB) | Done; reuse `make normalize-catalog` / `make validate-catalog` only when the data changes |
| Configurable log path | Currently hardcoded to `/tmp/freedeckcy.log` (already rotated) | Support `FREEDECKCY_LOG_FILE`, fall back to the default for invalid paths; update the docs |
| Upgrade download integrity to hash | Currently only `file_size` is compared | Verify when the catalog provides sha256; keep the status quo when it does not |
| Archive enhancements beyond `7z t` | After §9.4 lands, evaluate detection of non-standard volume naming | Unify archive pre-check error codes, make them readable |
| `make doctor` self-check | Use one command to check the runtime/Steam paths/state permissions | Share the same detection functions as the diagnostics page; not run in CI (depends on the real environment) |

---

| Bilingual UI/first-launch language selection ✅ | **Delivered in v0.28.11**: the first time the QAM plugin is opened it shows a Chinese/English choice; persisted in localStorage; QAM/settings/native library/details are translated through the `data-fdc-i18n` root node and a MutationObserver, supporting dynamic counts/status; switchable from the QAM home page | Done; backend dynamic error messages may still be in Chinese |

## References

- Architecture and issue list: [ARCHITECTURE.en.md](ARCHITECTURE.en.md)
- Capability comparison with the author's v0.6: [ARCHITECTURE.en.md](ARCHITECTURE.en.md) §13
- Local development, debugging, troubleshooting: [DEVELOPMENT.en.md](DEVELOPMENT.en.md)
- Current test baseline: `make test` → 555 passed (2026-11 v0.28.11)
