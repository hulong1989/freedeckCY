> English | [中文](DROIDDECK.md)

# Using freedeckCY on DroidDeck

[DroidDeck](https://github.com/Droid-Deck/DroidDeck) is an open-source project that runs a SteamOS runtime on Android phones: it ships a Linux desktop, Steam's game mode, and supports **[Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) plugins**. freedeckCY has supported DroidDeck since v0.4.0: v0.6.0 brought the GBA emulator loop, v0.7.0 a generic emulator registry (GBA/PSP/NDS), v0.8.0 Ludusavi + gamewatch automatic cloud saves, v0.9.0 PS1/FC/MD, v0.10.0 switched all emulators to online downloads, v0.11.0 10 platforms + an architecture capability matrix (DroidDeck automatically hides 3DS/PS2/PS3), v0.12.0 automatically deploys BIOS/firmware after installation and writes portable configs, v0.13.0 adds repository game submissions (Issue/PR) to the web library, v0.14.0 Baidu Netdisk (official OpenAPI), v0.14.1 3DS (Azahar) SteamOS compatibility fixes (prefer the official Flatpak, fall back to AppImage when Flatpak is unavailable), v0.15.0 includes emulator saves in cloud save uploads, v0.16.0 emulator save restore + per-game splitting for PSP/PS3/3DS + PS1 multi-disc m3u, v0.17.0 Baidu Netdisk QR-code login (BDUSS/Cookie as the main path, OpenAPI as an optional fallback), v0.18.0 scan installed games + Baidu QR error diagnostics, v0.19.0 download/install directory support for SD card/external storage selection, v0.20.0 Decky native game library (no longer depends on the web page), v0.21.0 scan installed moved to settings and automatically adds Steam shortcuts, v0.22.0 diagnostic self-check + one-click diagnostic bundle, v0.23.0 native library modal fallback/version label + Baidu QR timeout, v0.24.0 native library back/close fixes, v0.25.0 Steam-owned games no longer show the plugin playtime block, v0.26.x architecture/stability fixes, v0.27.0–v0.27.20 native game library visual refactor and Steam Deck controller/trackpad adaptation (DroidDeck also uses the Decky focus system, so the touch/controller logic is reusable). This document corresponds to **v0.28.14** and covers installation and troubleshooting.

> The adaptation is based on DroidDeck's source code and ARM64 runtime layout, and **has not yet been fully verified on real hardware**. If you hit problems, collect logs as described in "Troubleshooting" at the end of this document.

## 1. Differences from Steam Deck

| Item | Steam Deck | DroidDeck |
|---|---|---|
| CPU architecture | x86_64 | **aarch64 (ARM64)** |
| Runtime | SteamOS | proot Linux; HOME is usually `/root` |
| Steam root | `~/.steam/steam` / `~/.local/share/Steam` | Same; the x64 Steam client also has `~/.droiddeck-x64/.local/share/Steam` |
| Proton | Valve tools such as `proton_experimental` | **ARM tool names** `droiddeck-proton-arm64` / `droiddeck-proton-11-arm64` |
| Storage | SSD/SD card | Android internal storage; paths are mapped inside proot |

How freedeckCY handles this:

- Runtimes (aria2c, 7zz, node) are selected by `platform.machine()` from `defaults/runtime/<arch>/`; ARM devices use `aarch64`.
- When DroidDeck markers are detected (`~/.droiddeck-x64`, `~/.droiddeck-decky-enabled`, `<Steam>/package/droiddeck-installed`), the Proton mapping automatically switches to `droiddeck-proton-arm64`; if `droiddeck-proton-11-arm64` already appears in `config.vdf`, that one takes precedence.
- If DroidDeck's x64 Steam client is running (`steam.pid` exists), shortcuts are written preferentially to its `~/.droiddeck-x64/.local/share/Steam`; otherwise the standard path is used.
- The GBA loop (since v0.6.0) uses the **mGBA arm64 AppImage**: since v0.10.0 it is **no longer bundled**; on the first GBA install it is downloaded automatically from the official release and then unpacked with `--appimage-extract` into `~/.local/share/freedeckCY/emulators/gba/aarch64/squashfs-root` (GBA also accepts the legacy `emulators/aarch64/`; it **does not rely on FUSE**, so it works inside proot); the Steam shortcut's Exe is the generated `launch-freedeckcy.sh`, and **no Proton mapping is written** (native Linux launch).
- Emulator save restore (v0.16.0): cloud save restore is no longer PC-only — emulator saves are restored according to the `restore_roots` whitelist (on the same machine the original parent directory is preferred; across devices the first root for the platform is used), and a `*.freedeckcy-bak-<timestamp>` backup is created automatically before overwriting; conflicts require confirmation. **On aarch64, restore/splitting works for GBA/PSP/NDS/PS1/FC/MD (the 3DS/PS2/PS3 platforms themselves are hidden)**; PSP (PARAM.SFO) and 3DS (NCSD title id) splitting also applies on ARM (the 3DS platform is not visible); PS1 multi-disc also generates/prefers `.m3u` files on aarch64.
- Emulator save upload (v0.15.0): the QAM "Cloud save upload → Include emulator saves" toggle (`cloud_save_include_emulators`, on by default) controls whether emulator saves are uploaded; discovery paths are based on **HOME inside proot** (`~/.local/share/...`, `~/.config/...`, e.g. `~/.local/share/ppsspp/PSP/SAVEDATA`, `~/.local/share/azahar-emu/sdmc`, `~/.local/share/eden/nand/user/save`). **Flatpak's `~/.var/app/...` paths do not apply under Android/proot** (DroidDeck has no SteamOS Flatpak environment) and are not used by mistake; GBA/FC/MD/NDS find a single game's save by ROM name, while PSP/PS1/PS2/3DS/PS3/Switch upload shared memory cards/title directories; **since v0.16.0 restore is supported** (see the previous item: whitelisted targets + backups + conflict confirmation).
- 3DS (Azahar, v0.14.1): on SteamOS 3.9.5 the official Flathub Flatpak `org.azahar_emu.Azahar` is preferred (the AppImage has upstream #127/#953 compatibility issues); **DroidDeck/aarch64 has no official 3DS arm64 package, so 3DS is still not shown in the catalog** (architecture whitelist, see §9.8). If the device can run x86_64 and has flatpak installed, Flatpak is used automatically with AppImage as the fallback; the 3DS launch script forces XWayland (`QT_QPA_PLATFORM=xcb`/`SDL_VIDEODRIVER=x11`); system files go to `~/.local/share/freedeckCY/bios/3ds/sysdata/` and are deployed to azahar/citra and to `~/.var/app/org.azahar_emu.Azahar/data/{azahar,azahar-emu}/sysdata`. Existing 3DS shortcuts are rewritten automatically in the background, so no reinstall is needed.
- Library page playtime isolation (v0.25.0): Steam-owned game detail pages no longer show freedeckCY's "Played/Main Story/Total time" block — the frontend renders it only when `managed===true` and otherwise executes `return null`; the backend matches plugin install records first by AppID and then by title, and returns `managed=false` without querying HLTB when nothing matches. Only games installed/backfilled by the plugin are affected; this also applies on DroidDeck.
- Library page playtime (v0.25.0): shown only when `managed=true`; AppID matching reduces but does not eliminate false positives on same-name games; an HLTB failure only affects the values inside the block; depends on Steam's library page structure.
- Native library back (v0.24.0; v0.27.20): the library page has a "Back / Steam Library / Refresh" toolbar at the top (since v0.27.3 it uses regular flow layout instead of a QAM sticky offset); in modal mode "Back" calls `onClose` to dismiss the overlay, while in full-screen route mode it uses `Navigation.NavigateBack()`; "Steam Library" dismisses the overlay and then calls `Router.NavigateToLibraryTab()` to return to the Steam library page (falls back to `NavigateBack` when that API is unavailable on DroidDeck). The B button is bound to `onCancel` at the detail/library root node; explicit buttons are still available as a fallback.
- Native library entry point (since v0.20.0; current in v0.27.20): the QAM home page's "Game Library" first tries `showModal(<LibraryPage />)` for the native overlay and only falls back to `Navigation.Navigate("/freedeckcy/library")` on failure; since v0.27.20 the UI version label is no longer shown, and the version is determined by the Decky plugin list/`package.json`.
- Bilingual UI (v0.28.14): the first time you open QAM the plugin lets you choose Chinese / English; the choice is stored in localStorage and can be switched on the QAM home page; it also applies to the native library/settings/details.
- Controller/trackpad (v0.27): the D-pad/left stick moves within `flow-children` groups; A selects, B closes details/the game library, L1/R1 switch between game library/installed, and L2/R2 scroll about 0.8 screen; the trackpad/touch scrolls the vertical list and horizontal shelf. The focused card scrolls into view automatically, and the leftmost card's focus ring/top blue frame is not clipped.
- Baidu QR timeout (v0.23.0): clicking immediately shows the toast "Fetching Baidu QR code..."; the frontend times out at 20s/15s and the backend at 12s/10s, with the message "Timed out fetching the Baidu QR code (network/TLS may be blocked...)"; when DroidDeck/proot networking/TLS is restricted, retry as prompted or run diagnostics.
- Diagnostic self-check (v0.22.0): QAM Settings → "Diagnostics" → "Run self-check" shows a summary (OK/warning/failure/skipped) and each check (plugin/state/download and install directories/runtime/catalog data/Steam/storage/Tianyi network/Baidu QR/tasks/logs) with suggestions; "Export diagnostic bundle" writes `freedeckcy-diagnostics-<time>.zip` to the download directory inside proot (`settings.download_dir`, or the plugin download directory/`~/Downloads` if unset), with permissions 0600, and shows the path in a toast. On DroidDeck the runtime check looks at aria2c/7zz/node under `defaults/runtime/aarch64/`; the Steam check looks at the currently running client; the network/Baidu QR checks are subject to proot network restrictions.
- Scan installed (location changed in v0.21.0): the entry point is **QAM Settings → Install → "Scan installed games"** (the native library's installed page no longer has a scan button; the web library button is kept as a fallback). Scanning still uses `settings.install_dir` inside proot as the root, scans only one level, and matches directory names against titles; games without shortcuts are added automatically: PC games look for an `.exe`, emulators must already be installed (no automatic download) and a wrapper is generated; a success toast shows "Auto-added to Steam: N". **Steam must be restarted/switched user/library page reopened** before new shortcuts appear in DroidDeck.
- Decky native game library (v0.20.0; visual/input refactor in v0.27.20): QAM home page "Game Library" opens the native library (Hero + category shelves by default, grid after search/filter); it no longer opens a local web page; search + platform/category/sort filters, 30 per page + load more, dual netdisk download-source selection; the installed tab supports launch/directory/uninstall. The scan entry point is in settings; install progress is in the QAM home task area. The old local web library is only for desktop debugging/fallback.
- Storage location selection (v0.19.0): QAM "Settings → Paths" shows detected external-mount buttons under the download/install directories (e.g. `/storage/emulated/0`, `/sdcard`, `/mnt/...`; label "SD card / External: <directory name> (X free)"), and one click switches the directory to `<mount>/freedeckCY/downloads|installed`. **Only mounted sub-mounts that are writable under proot/Android are shown**; the `/storage`, `/sdcard` and `/mnt` mount points themselves are skipped; insufficient permissions/read-only/not mounted are not shown; the plugin does not create/mount/format anything automatically and does not check whether the Steam library is on the same disk. The original "choose download directory/install directory" options are still available.
- Scan installed (since v0.18.0, moved in v0.21.0): the web library's "Installed" toolbar button remains as a fallback (`POST /api/tianyi/installed/scan`); the main entry point is in QAM Settings → Install. On DroidDeck the install directory is typically a path inside proot (e.g. `/root/Games`), and the plugin scans only **one level of subdirectories** of `settings.install_dir`; directory names must match catalog titles, and since v0.21.0 Steam shortcuts are added automatically (see the previous item).
- Baidu Netdisk (v0.17.0, QR-code/Cookie main path): behaves the same on aarch64 and x86_64 (pure HTTPS API, no local binaries). QAM "Baidu Netdisk (QR login)" → "Log in to Baidu Netdisk with QR code" → scan and confirm with the Baidu app/Baidu Netdisk app on your phone; the Cookie is written to `baidu_login` in `~/.local/share/freedeckCY/tianyi/state.json` inside proot, after which Baidu shares can be installed directly without an Open Platform App Key. Cookies expire/get risk-controlled, so rescan once they fail; the QR session lives in memory for only 180s. **OpenAPI (v0.14.0) is kept as an optional fallback** (self-built app + OAuth, used only when there is no Cookie). **No CDP/web reverse engineering.** See [ARCHITECTURE.en.md](ARCHITECTURE.en.md) §5.13 / [DEVELOPMENT.en.md](DEVELOPMENT.en.md) §6.11 for details.
- Repository game submissions (v0.13.0): the web library toolbar has a "Submit game" button; clicking it opens the GitHub Issue form in the system browser/Steam's built-in browser (`https://github.com/hulong1989/freedeckCY/issues/new?template=submit-game.yml`); you can also submit a PR editing `submissions/*.json` directly. Fields match the original resource-pool submissions (name/English name/platform/share link/extraction code/version/executable name + `openpath`); **only the share link is submitted, game files are never uploaded**; this path is device-independent and needs no extra configuration on DroidDeck. See [submissions/README.md](../submissions/README.md) for details.
- Automatic cloud saves (v0.8.0): the built-in Ludusavi manifest (53,549 games) is matched by title/SteamID, and Windows save paths are resolved to the **ARM Proton prefix** (the layout inside `compatdata/.../pfx` is the same as on x86_64); `gamewatch` scans `/proc/*/cmdline` every 8 seconds (usually available under proot; falls back to `pgrep -f` when `/proc` is missing, which requires pgrep on the system), and uploads only that game after it exits. Automatic upload is **enabled by default** and can be turned off in QAM "Cloud save upload".
- The emulator registry (v0.11.0) covers **10 platforms**, but on DroidDeck/aarch64 **only 7 are available**: GBA (mGBA) / PSP (PPSSPP) / NDS (melonDS) / PS1 (DuckStation) / FC, MD (Mesen2) / **Switch (Eden, which has an official arm64 package)**; **the 3DS (Azahar) / PS2 (PCSX2) / PS3 (RPCS3) official packages are x86_64-only**, `available_platforms("aarch64")` does not return them, catalog queries are filtered by the whitelist, and **neither the entries nor the platform filter bar appear** (expected behavior, not missing data).
- **The plugin package does not bundle any emulator**: the first install of all 7 platforms above downloads the arm64 package from the official release (NDS is an AppImage inside a zip; Mesen2 is a single `Mesen` file inside a zip), and AppImages are unpacked to `~/.local/share/freedeckCY/emulators/<state_key>/aarch64/squashfs-root` without relying on FUSE; offline you can pre-place the cache manually or use `FREEDECKCY_*_BIN`.
- **BIOS / firmware deployment (v0.12.0)**: user files go into `~/.local/share/freedeckCY/bios/<platform>/` (HOME path inside proot), **archives are supported** (`.zip/.7z/.rar`, etc., unpacked at install time with 7zz into an `_extracted/` cache in the same directory); deployment happens automatically after installation:
  - PS1: BIOS → `<AppDir>/bios` + `~/.local/share/duckstation/bios`, and writes `portable.txt`/`portable_data/settings/settings.ini` (`SearchDirectory=./bios`, fullscreen);
  - PS2: x86_64 only (hidden on DroidDeck), BIOS → `<AppDir>/bios` + `~/.local/share/PCSX2/bios` + `~/.config/PCSX2/bios`;
  - NDS: `bios7/bios9/firmware` → `<AppDir>` + `~/.local/share/melonDS`;
  - Switch (Eden): `prod.keys/title.keys` → `~/.local/share/eden/keys/`, firmware `.nca` → `~/.local/share/eden/nand/system/Contents/registered/`;
  - PS3 (RPCS3): x86_64 only (hidden on DroidDeck), `PS3UPDAT.PUP` is automatically installed with `--installfw` when `dev_flash` is empty;
  - GBA/PSP: writes portable fullscreen config; 3DS is x86_64 only (hidden).
  Deployment messages are merged into the install-complete message; missing files do not block installation, but the game cannot be played right after installation.

## 2. Building the ARM64 plugin package

Run this on a development machine (Linux/macOS both work):

```bash
cd freedeckCY
make runtime ARCH=aarch64        # download ARM64 aria2c / 7zz / node
make package-droiddeck           # produce dist-artifacts/freedeckCY-v<version>-arm64.zip
```

Notes:

- `make runtime ARCH=all` can prepare both the x86_64 and aarch64 runtimes at once. **Since v0.10.0 there is no `make emulator-runtime`**: the plugin package contains no emulators (GBA also switched to an online download on first install), and the package is about 45MB (about 68MB back when mGBA was included).
- With `PACKAGE_ARCH=aarch64`, packaging automatically prunes other architectures from `defaults/runtime/{aria2,7z,node}` so the package size does not double; **emulators are not part of packaging**, and on DroidDeck all 7 platforms (including Switch) need to download the official arm64 package from the internet on first install; the PS1 BIOS must be placed in `~/.local/share/freedeckCY/bios/ps1/` yourself.
- Artifact names carry the `-arm64` suffix; the regular x86_64 package still uses `make package`.

## 3. Installation

1. Install and enable **Decky Loader** in DroidDeck (DroidDeck Settings → Decky → Install/Enable).
2. Copy `freedeckCY-v<version>-arm64.zip` to the phone storage.
3. Open DroidDeck's Decky menu → **Import plugin zip** → choose that zip.
   - DroidDeck performs an overwrite install based on the `name` in `plugin.json`; no uninstall is needed when upgrading.
4. Start/restart Steam game mode and open freedeckCY from the Decky sidebar.

First use:

- Log in to Tianyi Cloud Drive (QAM panel);
- In the download settings, change the download directory/install directory to a path with enough space (e.g. `/root/Games`);
- Open the QAM home page "Game Library" (native overlay), search/filter, then install; the local Web UI is only for desktop debugging/fallback;
- Emulators: on aarch64 you can see GBA/PSP/NDS/PS1/FC/MD/Switch (3DS/PS2/PS3 are hidden); filter and install directly — the plugin generates the launch script and registers a Steam shortcut automatically. **All platforms (including GBA) need an internet download of the official arm64 package on first install**, and how long it takes depends on the network. **Before/after installation you can put BIOS/firmware/keys (or archives) into `~/.local/share/freedeckCY/bios/<platform>/`**; they are deployed automatically on reinstall/re-registration; PS1 needs a BIOS, Switch needs `prod.keys` + firmware.

## 4. Feature support

| Feature | DroidDeck status |
|---|---|
| Tianyi login, share parsing, direct-link download | ✅ Uses ARM64 aria2c |
| 7z extraction / `7z t` verification | ✅ Uses ARM64 7zz |
| PC game install + Steam shortcut + cover art | ✅ (depends on a correct Steam root and Proton mapping) |
| Full catalog / platform and category filters / cover cache | ✅ |
| Uninstall with Proton prefix cleanup | ✅ (compatdata works the same under ARM Proton) |
| Task retry, download integrity verification, automatic re-download | ✅ |
| Cloud save upload/restore | ✅ Requires ARM64 node (bundled by `make runtime ARCH=aarch64`) |
| Automatic cloud saves (Ludusavi + gamewatch, v0.8.0) | ✅ Manifest bundled; automatically uploads that game after it exits (30 s debounce, fingerprint deduplication). `/proc` is usually available under proot; otherwise falls back to `pgrep -f`; on by default and can be turned off in QAM; ARM64 not verified on real hardware |
| GBA emulator (mGBA, since v0.6.0, online download since v0.10.0) | ✅ Installable/launchable: first install downloads the arm64 AppImage from the official release (about 24.6MB) → unpacks with `--appimage-extract` (no FUSE dependency); the Steam shortcut launches natively (no Proton mapping) |
| PSP emulator (PPSSPP, v0.7.0) | ✅ Installable/launchable: first install downloads the official arm64 AppImage from GitHub (the aarch64 asset is selected automatically); unpacking does not depend on FUSE |
| NDS emulator (melonDS, v0.7.0) | ✅ Installable/launchable: first install downloads the official zip (containing an aarch64 AppImage) → unzip → `--appimage-extract`; no FUSE dependency |
| PS1 emulator (DuckStation, v0.9.0) | ✅ Installable/launchable: the official arm64 AppImage is downloaded on demand; **you must supply your own BIOS** (`~/.local/share/freedeckCY/bios/ps1/`; copied to `~/.local/share/duckstation/bios/` at install time); missing BIOS does not block installation but warns/may cause a black screen |
| FC emulator (Mesen2, v0.9.0) | ✅ Installable/launchable: single `Mesen` file inside the official ARM64 zip (downloaded on demand) |
| MD emulator (Mesen2, v0.9.0) | ✅ Installable/launchable: shares Mesen2 with FC (`emulators/mesen/aarch64/`); only the ROM extensions differ |
| Switch emulator (Eden, v0.11.0) | ✅ Installable/launchable: has an **official arm64 AppImage**; requires `prod.keys` + firmware (prompted by `setup_hint`; missing files do not block installation but the game cannot be played right away) |
| 3DS / PS2 / PS3 (v0.11.0) | ⚠️ **x86_64 only, automatically hidden on DroidDeck**: the Azahar/PCSX2/RPCS3 official packages have no arm64 builds, and after catalog whitelist filtering neither the entries nor the platform filter bar appear (not a bug); on x86_64, 3DS prefers Flatpak since v0.14.1 and falls back to AppImage |
| Emulator BIOS/firmware deployment (v0.12.0) | ✅ Automatically deploys `bios/<platform>/` after installation (archives supported, 7zz extraction cached); on aarch64 deployment works for PS1/NDS/Switch plus fullscreen config for GBA/PSP; PS2/PS3/3DS are x86_64 only |
| Repository game submissions (v0.13.0) | ✅ The web library's "Submit game" button opens the GitHub Issue form; or submit a PR to `submissions/*.json` directly. No device-specific logic; DroidDeck behaves the same as Steam Deck |
| Emulator save upload/restore (v0.15.0 / v0.16.0) | ✅ Available on aarch64: discovers/restores GBA/PSP/NDS/PS1/FC/MD/Switch saves by HOME inside proot; restore uses whitelisted targets + `*.freedeckcy-bak-*` backups, and conflicts require confirmation; PSP splits by PARAM.SFO; PS1 multi-disc m3u works; 3DS splitting is hidden along with the platform (x86_64 only) |
| Decky native game library (v0.20.0; v0.27.20) | ✅ Available on aarch64: QAM native library (Hero + category shelves, grid after search/filter)/detail pages/installed actions; does not depend on the web page or local HTTP |
| Controller/trackpad (v0.27) | ✅ DroidDeck touch/controller input goes through the Decky focus system: A/B, directional buttons, L1/R1, L2/R2, touch scrolling; shares the same implementation as Steam Deck |
| Library page playtime isolation (v0.25.0) | ✅ Available on aarch64: only plugin-installed/backfilled games show the playtime block; Steam-owned games have `managed=false` and get neither an inserted block nor an HLTB query |
| Native library back/close (v0.24.0) | ✅ Available on aarch64: "Back / Steam Library / Refresh" toolbar (regular flow since v0.27.3) + title bar; modal uses `onClose`, route uses `NavigateBack`; "Steam Library" uses `NavigateToLibraryTab` (falls back when unavailable) |
| Native library modal fallback/QR timeout (v0.23.0) | ✅ Available on aarch64: game library prefers modal with a full-screen route fallback; since v0.27.20 the UI version label is no longer shown; Baidu QR has frontend/backend timeouts and clear messages |
| Diagnostic self-check/diagnostic bundle (v0.22.0) | ✅ Available on aarch64: QAM Settings "Diagnostics" runs a self-check and exports a 0600 zip to the proot download directory; the runtime check inspects aarch64 components, while network/Baidu QR are subject to proot restrictions |
| Scan installed + automatic Steam shortcuts (v0.21.0) | ✅ Entry point is Settings → Install; scans one level of `install_dir` inside proot and auto-creates PC/emulator shortcuts (emulators are not downloaded if not installed; recorded as `shortcut_error`); Steam must be restarted/switched user/library page reopened to show them |
| Storage location selection (v0.19.0) | ✅ Available on aarch64: the QAM paths page renders "Download/Install to … (X free)" buttons for writable mounts such as `/storage`, `/sdcard`, `/mnt`, switching with one click; read-only/not mounted are not shown |
| Baidu Netdisk (QR/Cookie, v0.17.0) | ✅ Available on aarch64: QAM shows the QR code, and after scanning with a phone the Cookie is stored in state (0600); installation prefers the Cookie and tasks carry Baidu Cookie/Referer/UA; expired Cookies require a rescan; OpenAPI is an optional fallback (self-built app/authorization); no CDP/web reverse engineering |
| `make doctor` | ⚠️ Requires a DroidDeck desktop terminal; `lsof` may not exist on Android |

## 5. Environment variables and settings

| Variable/setting | Purpose |
|---|---|
| `FREEDECKCY_STEAM_ROOT` | Specify the Steam root (manually pin it when DroidDeck has two clients) |
| `FREEDECKCY_PROTON_TOOL` | Override the Proton tool name; `none` means write no mapping |
| `FREEDECKCY_ARIA2_BIN` / `FREEDECKCY_7Z_BIN` / `FREEDECKCY_NODE_BIN` | Override runtime binary paths |
| `FREEDECKCY_MGBA_BIN` | Override the mGBA executable/AppImage path (the downloaded cache is used by default; can also point to a system mGBA or a manually pre-placed AppImage) |
| `FREEDECKCY_PPSSPP_BIN` | Override the PPSSPP path (downloaded arm64 AppImage / system PPSSPP by default) |
| `FREEDECKCY_MELONDS_BIN` | Override the melonDS path (downloaded arm64 AppImage / system melonDS by default) |
| `FREEDECKCY_DUCKSTATION_BIN` | Override the DuckStation path (PS1; downloaded arm64 AppImage / system DuckStation by default) |
| `FREEDECKCY_MESEN_BIN` | Override the Mesen2 path (shared by FC/MD; downloaded ARM64 `Mesen` / system Mesen by default) |
| `FREEDECKCY_EDEN_BIN` | Override the Eden path (Switch; downloaded arm64 AppImage / system Eden by default) |
| `FREEDECKCY_BAIDU_OPENAPI_APP_KEY` / `SECRET_KEY` | Baidu Open Platform app (headless/pure API environments; state takes precedence) |
| `FREEDECKCY_BAIDU_OPENAPI_REFRESH_TOKEN` | Baidu refresh_token fallback (when state is empty) |
| `FREEDECKCY_AZAHAR_BIN` / `FREEDECKCY_PCSX2_BIN` / `FREEDECKCY_RPCS3_BIN` | x86_64-only platforms; they never appear on aarch64; kept for cross-architecture debugging/future arm64 packages |
| Setting `proton_tool` | `auto` (default, determined automatically) / `none` / a specific tool name |
| Setting `cloud_save_auto_upload` | Automatically upload cloud saves after a game exits (default `true`; can be turned off in QAM "Cloud save upload") |

To inspect the current resolved result: `GET /api/tianyi/settings` (the local service returns `proton_tool_resolved` and `droiddeck_detected`).

## 6. Troubleshooting

**Games do not appear in Steam after installation**

- DroidDeck may have two Steam clients at the same time. Check which one is running:
  - `~/.droiddeck-x64/.local/share/Steam` (x64 client)
  - `~/.local/share/Steam` (standard/ARM client)
- Point `FREEDECKCY_STEAM_ROOT` at the running one and reinstall the game (or wait for the plugin to write shortcuts next time).
- Restart Steam so that `shortcuts.vdf` is reloaded.

**The game won't launch / a missing compatibility tool is reported**

- DroidDeck needs ARM Proton. Make sure `droiddeck-proton-arm64` (or the 11 version) is installed in Steam.
- The plugin writes `droiddeck-proton-arm64` by default; if the version does not match, use `FREEDECKCY_PROTON_TOOL=droiddeck-proton-11-arm64` or set it to `none` and select the compatibility tool manually in Steam.

**Downloading/extracting reports "binary not found"**

```bash
ls -l defaults/runtime/aria2/aarch64/aria2c \
      defaults/runtime/7z/aarch64/7zz \
      defaults/runtime/node/aarch64/bin/node \
      ~/.local/share/freedeckCY/emulators/gba/aarch64/  # emulators are not in the plugin package
```

Re-run `make runtime ARCH=aarch64` and repackage for whichever one is missing; you can also point the environment variables at arm64 builds on the system. (Emulators are no longer in the package, so nothing needs to be prepared.)

**GBA won't start after installation / mGBA not found / download failed**

- Since v0.10.0, GBA is also **downloaded automatically on first install** (mGBA is no longer bundled): check the network/system proxy; reinstalling after a failure retriggers the download.
- Download/unpack location `~/.local/share/freedeckCY/emulators/gba/aarch64/` (GBA also accepts the legacy `emulators/aarch64/`; no FUSE dependency); unpack failures are usually storage space/permission issues — delete that directory and retry, or use `FREEDECKCY_MGBA_BIN` to point at system mGBA / a manually pre-placed AppImage.
- Offline, you can put the mGBA arm64 AppImage into `~/.local/share/freedeckCY/emulators/gba/aarch64/` and `chmod +x` it, or point `FREEDECKCY_MGBA_BIN` at a local build; the same applies to PSP/NDS/PS1/FC/MD (each under its own `<state_key>/aarch64/`, with FC/MD sharing `mesen/`).
- Use `GET /api/tianyi/diagnostics` to quickly locate `emulators.gba`'s available/source/command.
- The Exe of the GBA shortcut in Steam is `<install directory>/launch-freedeckcy.sh` (`exec <mGBA> -f <rom>`); you can `bash launch-freedeckcy.sh` inside the install directory to verify it manually.

**PSP/NDS/PS1/FC/MD won't start after installation / first-install download failed**

- The official packages for these platforms are **not bundled** (same for GBA since v0.10.0): the first install needs to reach GitHub releases to download the arm64 assets; no network, a broken proxy or GitHub rate limiting all cause failure, and reinstalling after a failure retriggers the download.
- Download/unpack locations: `~/.local/share/freedeckCY/emulators/{psp,nds,duckstation,mesen}/aarch64/`; NDS/Mesen2 unzip first (Mesen2 is directly the executable `Mesen`), PSP/PS1 are AppImages (`--appimage-extract`), none of which depends on FUSE.
- Check the `source` (`download` means not yet downloaded) and `message` of `emulators.{psp,nds,ps1,fc,md}` in the diagnostic interface; you can also point `FREEDECKCY_PPSSPP_BIN` / `FREEDECKCY_MELONDS_BIN` / `FREEDECKCY_DUCKSTATION_BIN` / `FREEDECKCY_MESEN_BIN` at manually downloaded arm64 packages.
- Manually verify the wrapper: `bash "<install directory>/launch-freedeckcy.sh"` (PSP `--fullscreen`, PS1 `-batch -fullscreen`, FC/MD `/fullscreen`, NDS takes the ROM directly).

**3DS / PS2 / PS3 are missing (expected)**

- The official packages for these three platforms are **x86_64 only** while DroidDeck is aarch64: `available_platforms("aarch64")` returns only 7 platforms, and catalog queries are filtered by the whitelist, so neither game entries nor the platform filter bar appear; `emulator_status` returns `available=false` for them ("platform hidden").
- This is not missing data, nor a missing dependency; you can only wait for official arm64 packages — `FREEDECKCY_*_BIN` cannot be used to bypass this (they are not shown at the catalog layer).

**Where do PS2 BIOS files go / PCSX2 says there is no BIOS**

- Put them in `~/.local/share/freedeckCY/bios/ps2/*.bin` (or an archive); v0.12.0 deploys them at install time to three locations — `<AppDir>/bios`, `~/.local/share/PCSX2/bios`, `~/.config/PCSX2/bios` — and writes `portable.ini`/`inis/PCSX2.ini`. Note that **the PS2 platform is hidden on DroidDeck**; only x86_64 devices use this path.

**BIOS/firmware archives are not applied / paths are wrong**

- Put archives into `~/.local/share/freedeckCY/bios/<platform>/`; at install time 7zz unpacks them to `_extracted/` and then deploys; make sure the plugin has an ARM64 7zz (`make runtime ARCH=aarch64` or `FREEDECKCY_7Z_BIN`); failures are shown in the install message.
- Deployment targets: `<AppDir>/bios` (`squashfs-root/bios` after AppImage extraction) and the DuckStation/melonDS/Eden user directories; when a portable config exists, the emulator reads `<AppDir>/bios` preferentially.
- If you only want to place files manually, put the already-extracted files directly into `bios/<platform>/` (the extraction step is skipped); reinstalling or re-registering the Steam shortcut triggers deployment again.

**PS3 firmware / Switch keys are not recognized**

- PS3 (x86_64 only): firmware must be `bios/ps3/PS3UPDAT.PUP`; skipped when `~/.config/rpcs3/dev_flash` is not empty; on failure check the `--installfw` error in the install message.
- Switch (available on aarch64): put `prod.keys/title.keys` in `bios/switch/` → copied to `~/.local/share/eden/keys/`; `.nca` files extracted from a firmware archive → `~/.local/share/eden/nand/system/Contents/registered/`; if the directory is empty, restart Eden and try again.

**Switch / 3DS / PS3 cannot be played right after installation**

- Switch (Eden, available on aarch64) requires `prod.keys` and firmware; 3DS/PS3 are not available on ARM. Install messages/library popups include `setup_hint`; configure as prompted on the emulator's first launch; the plugin neither bundles nor downloads these files.

**PS1 black screen / no BIOS reported / Mesen2 (FC/MD) won't start**

- PS1: DuckStation requires a BIOS you supply. Put `scph*.bin` into `~/.local/share/freedeckCY/bios/ps1/` and reinstall (or manually `cp -n .../bios/ps1/*.bin ~/.local/share/duckstation/bios/`); check `emulators.ps1.bios_present/bios_dir` in the diagnostic interface.
- Mesen2: the official ARM64 zip contains the single file `Mesen`, and the launch argument is `/fullscreen <rom>` (not `-f`); FC and MD share the same `emulators/mesen/aarch64/`, so deleting the cache affects both.

**Cloud saves are not uploaded automatically after a game exits**

- Confirm the `cloud_save_auto_upload` setting is true (QAM "Cloud save upload → Automatically upload after game exits").
- gamewatch uses `/proc/*/cmdline` to decide whether the install_path is running; DroidDeck's proot usually provides `/proc`, otherwise it falls back to `pgrep -f` (requires pgrep on the system); both methods require **the install directory to appear in the process command line** (custom wrappers may not satisfy this).
- Automatic upload requires being logged in to a Tianyi account, no upload task currently in progress, and at least 30 seconds between two automatic uploads; when several games exit in a row, only the first is uploaded immediately.
- Search the logs for `auto cloud save upload after exit` (triggered) and `gamewatch poll failed` (detection error); `reason=unchanged` in the upload status means the save fingerprint did not change and it was skipped by design.

**Clicking "Submit game" does nothing / no browser**

- The button only opens the GitHub Issue form (it is not an in-plugin form): it is enough that DroidDeck's built-in Steam browser or the system default browser can open GitHub; if there is no browser at all, open `https://github.com/hulong1989/freedeckCY/issues/new?template=submit-game.yml` manually in a browser on a computer/phone, or submit a PR under `submissions/` directly.
- Submitting only needs the share link and fields and **does not require logging in to a Tianyi Cloud account**; for field descriptions see [submissions/README.md](../submissions/README.md).

**Baidu Netdisk not configured / authorization expired / download failed**

- "Baidu Open Platform app not configured": save the App Key/Secret in QAM (or set the `FREEDECKCY_BAIDU_OPENAPI_APP_KEY`/`SECRET_KEY` env vars).
- Authorization expired: clear the authorization and redo "Get authorization link" → log in to Baidu in the browser → paste the authorization code back into "Complete authorization"; when refresh fails you can also use `FREEDECKCY_BAIDU_OPENAPI_REFRESH_TOKEN` as a fallback.
- Installation reports `errno=-6` / transfer disabled: the Baidu account's transfer is restricted or the shared file cannot be transferred; switch accounts/retry later and handle it according to the official errno in the install message.
- dlink 403/download failure: the plugin already sends `Referer=https://pan.baidu.com/disk/home`, `UA=pan.baidu.com` and empty cookies; retries fetch a new dlink, and if it still fails check the install message (expired dlink/risk control).
- Transfer space: shared files are transferred to `/FreedeckTmp` in Baidu Netdisk and cleaned up automatically after installation; on failure they are kept, and you can delete that directory manually.
- Link formats: `pan.baidu.com/s/<surl>`, `/share/init?surl=...`, `yun.baidu.com`/`eyun.baidu.com` are supported; short links are expanded first.

**3DS-related (DroidDeck/aarch64)**

- 3DS not showing in the catalog on DroidDeck is expected: 3DS has only x86_64 official packages and `available_platforms("aarch64")` does not include it; do not try to bypass the catalog whitelist with `FREEDECKCY_AZAHAR_BIN`.
- On an x86_64 + flatpak environment (such as a SteamOS host): first `flatpak remote-add --user --if-not-exists flathub ...`, `flatpak install -y --user flathub org.azahar_emu.Azahar`; the diagnostic `emulators.3ds.source` should be `flatpak`, otherwise it falls back to AppImage.
- 3DS system files go to `~/.local/share/freedeckCY/bios/3ds/sysdata/`; in a Flatpak environment they are also copied to `~/.var/app/org.azahar_emu.Azahar/data/{azahar,azahar-emu}/sysdata`.

**Emulator save restore fails / restores to the wrong location**

- Restore targets can only be inside the platform's standard/portable roots (`restore_roots`); on the same machine the original parent directory is preferred, across devices the first root is used; any HOME path in the manifest is rejected/falls back.
- A `*.freedeckcy-bak-<timestamp>` is created before overwriting; PS1/PS2 single memory cards and the Switch directory are overwritten as a whole card/whole directory (you cannot pick just one game), and conflicts require confirmation.
- PSP/PS3 splitting relies on `PARAM.SFO` in the save directory; 3DS splitting relies on the NCSD `0x108` title id and the platform is not visible on aarch64; when splitting fails it falls back to the shared directory (not an error).
- PS1 multi-disc: an existing `.m3u` takes precedence; multiple `.cue/.chd` files generate `freedeckcy-multidisc.m3u` (natural sort); a single disc still uses `.cue`.

**Emulator saves are not uploaded / uploads are very large**

- First make sure QAM "Cloud save upload → Include emulator saves" is enabled; when disabled, non-PC records are counted in `emulator_saves_disabled`.
- Saves not found: see the upload status `diagnostics.collect[*].diagnostics.emulator_saves.reason` (`save_dir_missing`/`game_save_not_found`/`emulator_saves_shared`); GBA/FC/MD/NDS must have the same name as the ROM (`.sav/.srm/...`).
- DroidDeck paths are HOME inside proot (e.g. `~/.local/share/ppsspp/PSP/SAVEDATA`, `~/.local/share/eden/nand/user/save`); **`~/.var/app/...` Flatpak paths do not apply**.
- Shared memory cards/title directories can be large (3DS/Switch), subject to the 5000-file fingerprint limit and upload size limit; turn off the toggle or clean up manually if necessary.
- Restore supports emulator saves (v0.16.0, whitelisted targets + backups + conflict confirmation); PS1/PS2 single memory cards and the Switch directory are still overwritten as a whole.

**Baidu Netdisk QR login fails / installation says not logged in** (since v0.18.0 errors carry a specific reason):

- The QR code/polling uses the same Cookie set (visiting the passport home page first to obtain BAIDUID); a non-200 HTTP response shows the status code and a response snippet, and a polling network error shows `stage=failed` (no longer waits forever).
- Check whether the network inside DroidDeck can reach `passport.baidu.com`; the QR code expires after 180s and must be fetched again; after scanning you must confirm on the phone.

- In QAM "Baidu Netdisk (QR login)", click "Log in to Baidu Netdisk with QR code"; if the QR code does not show, check the returned `qrcode_url`, or check whether the network inside DroidDeck can reach `passport.baidu.com`.
- Stuck in waiting: the phone has not scanned/confirmed; the QR code expires after 180s, just fetch it again. scanned means it has been scanned and is waiting for phone confirmation.
- Scanning succeeds but installation still says not logged in: confirm that `state.json`'s `baidu_login.cookie` contains `BDUSS=`, and that `/api/tianyi/settings`'s `baidu_login.logged_in` is true; if necessary "Log out of Baidu Netdisk" and scan again.
- Cookie invalid/direct link 403: scan again; tasks already carry the Baidu Cookie/Referer/UA, and a 403 is usually an expired direct link/risk control.
- To use the OpenAPI fallback: do not scan (or clear the Baidu login), configure the App Key/Secret under "Baidu Netdisk OpenAPI (optional)" and authorize; shared files are transferred to `/FreedeckTmp` (cleaned up after installation).
- QR confirmation/Cookie switching has not yet been verified on real hardware; if you hit problems, attach the QAM status and install message.

**The plugin playtime block appears on Steam-owned game detail pages**

- Since v0.25.0 it is shown only for plugin-installed/backfilled games with `managed=true`; for unmatched original games the frontend directly `return null`, the backend returns `managed=false`, and no HLTB query is made.
- If it still appears, confirm that the frontend dist/plugin has been reloaded and the Steam library page reopened; same-name games may be misidentified by title matching, so first check whether `installed_games` has a same-name record.

**The game library cannot go back / stuck on the library page**

- The library page has a "Back / Steam Library / Refresh" toolbar at the top (regular flow since v0.27.3) and a title-bar back button; modal mode uses `onClose` to dismiss, full-screen route mode uses `Navigation.NavigateBack()`.
- The "Steam Library" button first closes the library page and then calls `Router.NavigateToLibraryTab()`; when that API is unavailable on DroidDeck it falls back to `NavigateBack`.
- The Steam overlay's B/Esc may not close the modal, so prefer the explicit buttons; route back depends on the navigation stack, and when the stack is empty you can only close the sidebar or reload the plugin.

**Clicking Game Library still opens the old web page / QR code does not respond when clicked**

- Since v0.20.0 the game library prefers `showModal(<LibraryPage />)`; since v0.27.20 the UI version label is no longer shown, so first confirm that the plugin version is 0.27.20, the dist has been updated, and Decky has been reloaded.
- A toast should appear immediately after clicking Baidu QR login; if it times out, the message mentions "network/TLS may be blocked" — check `/tmp/freedeckcy.log` for the `Baidu QR` keyword, or run diagnostics.

**Diagnostic self-check fails / diagnostic bundle export fails**

- Settings → Diagnostics "Run self-check" shows each item's status/detail/fix; for runtime_* failures check `defaults/runtime/aarch64/{aria2,7z,node}` (reinstall/repack), and for state/download/install directory failures check proot permissions and free space.
- Steam warn/fail: confirm the running client among DroidDeck's two Steam roots, or pin it with `FREEDECKCY_STEAM_ROOT`; for network/Baidu QR failures first confirm that proot can reach the corresponding domains.
- If export fails, check whether the download directory is writable; the diagnostic bundle has permissions 0600 and its path is shown in the toast. The self-check only gives recommendations and never fixes anything automatically.

**Scan installed does not recover games / does not add Steam shortcuts**

- Since v0.21.0 the entry point is **QAM Settings → Install → Scan installed games** (not on the native library's installed page).
- It scans only one level of `settings.install_dir` inside proot, and directory names must match titles; nested directories/0-byte directories are skipped.
- For PC, a failure to find an exe is recorded as `exe_not_found`; an emulator that is not installed is recorded as `emulator_not_ready` (no automatic download); a missing ROM is `rom_not_found`; check the `shortcut_error` and `steam_added`/`steam_recovered_count` in the toast/API response.
- Only `shortcuts.vdf` is written, so **Steam must be restarted/switched user/library page reopened** before the new shortcuts show; when DroidDeck has two Steam roots, confirm that it was written to the running one (`FREEDECKCY_STEAM_ROOT`).

**The native game library won't open / the list is empty / installation fails**

- Since v0.20.0 "Game Library" is the QAM native route `/freedeckcy/library` (not a web page); if it won't open, confirm that the plugin has been reloaded and that the Decky log has no routing errors.
- Empty list: check whether the catalog loaded and the search/platform/category/sort filters; for install failures check the plan errors in `ConfirmModal`/toasts (insufficient space, unwritable directory, emulator unavailable).
- Install progress is in the QAM home task area, not on the library page; the installed page scan still only recognizes one level of `settings.install_dir` inside proot and directory names must match.
- For advanced uninstall options such as compatdata cleanup, use the home page/web library; native library uninstall always deletes the game files.

**SD card/external storage buttons do not appear / not writable after switching**

- Only mounted and writable sub-mounts under `/run/media`, `/media`, `/mnt`, `/storage`, `/sdcard` are shown; the mount points themselves are skipped (e.g. `/storage` and `/sdcard` themselves), and only sub-mounts such as `/storage/emulated/0` appear.
- Confirm that the path is writable inside DroidDeck/proot (Android storage mapping/permissions may make some paths read-only); use `curl /api/tianyi/storage/options` to see `external` and `free_text`, or test with `touch` in a terminal.
- The plugin does not create directories/mounts; if necessary, manually `mkdir -p <mount>/freedeckCY/{downloads,installed}`.
- If installation still fails after switching directories: check the target disk's space and permissions (`df -h`), and whether the Steam library is on the same disk.

**Logs**

- Plugin log: `/tmp/freedeckcy.log`
- State: `~/.local/share/freedeckCY/tianyi/state.json`
- Health check: `curl 127.0.0.1:59271/_healthz`

## 7. Known limitations

- Not verified on real hardware: DroidDeck's FEX/ARM Proton and the storage mappings of different Android models may all affect the results.
- On aarch64, **GBA/PSP/NDS/PS1/FC/MD/Switch** — 7 platforms — can be installed (mGBA/PPSSPP/melonDS/DuckStation/Mesen2/Eden; v0.6.0~v0.12.0, all downloaded online); since v0.12.0, installation automatically deploys `bios/<platform>/` (including archives) and writes portable configs (PS1/NDS/Switch/GBA/PSP; PS2/PS3/3DS are x86_64 only); **the official packages for 3DS/PS2/PS3 are x86_64 only and are automatically hidden by the catalog whitelist on DroidDeck** (neither entries nor filter bar appear; see [ROADMAP.en.md](ROADMAP.en.md) 9.8). **The plugin package bundles no emulator; all 7 platforms (including GBA) need the internet on first install** to download the official arm64 package from the release (the package is about 45MB), and offline you can pre-place the cache manually or use `FREEDECKCY_*_BIN`; **PS1 requires your own BIOS and Switch requires keys+firmware** (prompted by setup_hint; missing files do not block installation but the game cannot be played right away); each platform only recognizes its own ROM extensions and has no save management; these platforms have not been verified on real ARM64 hardware.
- **Automatic cloud save boundaries**: v0.8.0 handled PC only; since v0.15.0 emulator saves are included (GBA/PSP/NDS/PS1/FC/MD/Switch), and since v0.16.0 restore is supported; PS1/PS2/Switch are still overwritten as a whole card/directory; fingerprints only consider relative path + size + mtime (≤5000 files); when `/proc` is unavailable it relies on `pgrep`; real-hardware verification of this path on ARM64 is limited.
- Emulator save restore (v0.16.0) restores according to the HOME allowlist under Android/proot, so Flatpak paths do not apply; PS1/PS2 single memory cards and the Switch directory cannot be split per game; 3DS restore is invisible along with the platform; shared-card overwrites require confirmation and have backups.
- Emulator saves (v0.15.0) only recognize standard/portable paths inside HOME under Android/proot, and Flatpak's `~/.var/app/...` does not apply; GBA/FC/MD/NDS require the save to have the same name as the ROM, while PSP/PS1/PS2/3DS/PS3/Switch upload shared memory cards/title directories (other games on the same card are included too); since v0.16.0 restore is supported (whitelisted targets/backups/conflict confirmation); PS1/PS2/Switch are still whole-card overwrites, and large 3DS/Switch directories hit the 5000-file limit.
- 3DS (v0.14.1) is still unavailable on DroidDeck/aarch64 (no official arm64 package, catalog hidden); on SteamOS/x86_64 Flatpak is preferred (the system must have flatpak and be able to reach Flathub), with AppImage as the fallback when there is no Flatpak (upstream #127/#953 issues may still exist); the 3DS wrapper uses XWayland; existing shortcuts are rewritten automatically but this has not been verified on real DroidDeck hardware.
- Baidu Netdisk (v0.17.0) uses QR-code login (BDUSS/Cookie) as its main path: it requires scanning with the Baidu app on a phone, Cookies expire/get risk-controlled and must be rescanned when invalid; the QR session lives in memory for only 180s; OpenAPI is an optional fallback (self-built app/authorization, transfer to `/FreedeckTmp` consumes Netdisk space); no CDP/web reverse engineering; QR confirmation/Cookie switching has not yet been verified on real hardware; behavior is the same on aarch64 and x86_64.
- Repository game submissions (v0.13.0) depend only on the web page/GitHub and have no device-specific logic; there are no extra restrictions on DroidDeck (other than needing a browser that can open GitHub).
- Upgrading DroidDeck/reinstalling Decky may clear the plugin, so the zip must be imported again.
- Native library back (v0.24.0; since v0.27.20 the B button is bound to onCancel): back logic differs between modal/route; the B button is already bound at the detail/library root node, but explicit buttons are still recommended as a fallback; route back depends on the navigation stack.
- Native library/QR timeouts: routes are only used when the modal fails; the version is determined by the Decky plugin list/`package.json`; QR timeouts depend on proot networking/TLS and only show a prompt without automatic retries.
- The diagnostic self-check (v0.22.0) is a one-time snapshot, and network items are affected by proot connectivity; `baidu_qr` only outputs the sign length (excluding sign/cookie); the export includes 300 lines of logs (already redacted) — review them yourself before submitting; online log viewing/diagnostic bundle upload are not supported.
- Native game library (v0.20.0; v0.27.20): cover grid/Hero/filters/details/installed actions are all present; task progress is in the home task area; the scan entry point is in settings and still only recognizes one level of `settings.install_dir`; uninstall always deletes files (no compatdata cleanup prompt); the old web library is only for debugging/fallback.
- Scan adding Steam shortcuts (v0.21.0) only writes `shortcuts.vdf`, so Steam must be restarted/user switched/library page reopened to see them; emulators are not downloaded automatically when not installed; when the PC exe/ROM is not found the game is skipped and `shortcut_error` is recorded.
- Storage location selection depends on `/proc/mounts` and write permissions inside proot; the visibility/writability of paths such as Android's `/storage/emulated/0` varies by device, and the plugin does not automatically mount/format; it does not check whether the Steam library is on the same disk.
- Scan installed depends on `settings.install_dir` being visible inside proot and directory names matching catalog titles; only one level is scanned; since v0.21.0 Steam shortcuts are added automatically (emulators are not downloaded if not installed and `shortcut_error` is recorded; Steam must be restarted/user switched/library page reopened to show them); Baidu QR login requires the phone app and a network that can reach `passport.baidu.com`.
- Test baseline for this version: `make test` → 575 passed (2026-11 v0.28.14).
- This plugin does not modify DroidDeck's own boot parameters or system settings; it only reads and writes the Steam user config and game directories.
