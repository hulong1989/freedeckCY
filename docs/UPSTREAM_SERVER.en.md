> English | [中文](UPSTREAM_SERVER.md)

# Reverse Engineering the Upstream Server Dependency: panyiwei.xyz

> Bottom line up front: **NewFreedeck hard-depends on `http://panyiwei.xyz/freedeck-catalog/` and has no local catalog fallback whatsoever**; this document records its protocol, caching, failure modes, and alternatives. **freedeckCY does not depend on that server** (catalog, covers, and emulators are all local or from official sources).

## 1. Dependency Inventory

| Purpose | URL | Consumer | Consequence of Failure |
|---|---|---|---|
| Full catalog | `http://panyiwei.xyz/freedeck-catalog/all.json` | `main.py:_refresh_catalog_async` | Fresh install with no cache → empty game library |
| Platform catalog | `http://panyiwei.xyz/freedeck-catalog/platform/{platform}.json` | `main.py:_fetch_platform_remote`, `py_modules/catalog_cache.py` | Empty platform tab |
| Curated | `http://panyiwei.xyz/freedeck-catalog/curated/{platform}.json` | `main.py:get_curated_shelf` | Curated shelf falls back to `_catalog_items` (empty if those are empty too) |
| Emulator download source | `http://panyiwei.xyz/freedeck-catalog/emu.json` | `py_modules/emulator_registry.py` | Cannot download/deploy emulators; `fetch_emulator_sources()` returns empty |
| Cover fallback | `cover_url` in catalog data (third-party image host/Steam/libretro) | `_enrich_one` through the local `/proxy/cover` proxy | Missing images; not hosted by panyiwei itself |

- `platform` values: `switch / ps1 / ps2 / ps3 / psp / 3ds / gba / nds / fc / md`; `curated` supports the `ns ↔ switch` alias.
- The server is **plaintext HTTP** with no authentication, no signatures, and no version endpoint (`get_catalog_version` returns the local "本地CSV" and does not contact the server).
- The Tianyi download signature in `sign_download` is computed **locally in Rust/Python** (`nfc_sign`); it is **not** a panyiwei dependency.

## 2. Catalog Data Schema (reconstructed from NewFreedeck's parsing code)

`all.json` / `platform/*.json` / `curated/*.json` are all **arrays** (the platform endpoint also accepts a `{"games": [...]}` or `{"items": [...]}` wrapper):

```json
{
  "game_id": "104143",
  "title": "行走的贸易/The Walking Trade",
  "title_zh": "行走的贸易",
  "title_en": "The Walking Trade",
  "platform": "pc",
  "cover_url": "https://.../header.jpg",
  "size_text": "2.5 GB",
  "genre": "动作冒险",
  "down_url": "https://cloud.189.cn/t/...",
  "file_name": "game.zip",
  "size_bytes": 2674349793,
  "pwd": "jl4z",
  "server": "t",
  "version": "",
  "validity": "",
  "install_size_text": "",
  "install_size_bytes": 0
}
```

Multiple versions of the same game are merged into a single entry by `_group_catalog_items()`, with the following fields added:

```json
{
  "grouped": true,
  "variant_count": 3,
  "multi_disc": false,
  "disc_count": 1,
  "variants": [ { ...same schema... } ]
}
```

Requirements: `down_url` must be a downloadable Tianyi share link (the frontend takes it directly to resolve/download); `game_id` is used for deduplication/favorites; `cover_url` must be an absolute URL or empty.

## 3. `emu.json` Schema

```json
{
  "switch": { "share_url": "https://cloud.189.cn/...", "pwd": "abcd", "file_name": "eden.7z" },
  "gba":    { "share_url": "https://cloud.189.cn/...", "pwd": "efgh", "file_name": "mGBA.7z" },
  "ps1":    { "share_url": "...", "pwd": "...", "file_name": "..." }
}
```

- Keys may be platform names (`switch/gba/...`) or adapter names (`eden/mgba/duckstation/pcsx2/rpcs3/ppsspp/lime3ds/melonds/nestopia/blastem`); `_parse_json()` adds an adapter alias for each platform name.
- Entry fields: `share_url` (also accepts `link`), `pwd` (also accepts `code`), `file_name` (optional).
- Cache: `~/.local/share/NewFreedeck/emu_cache.json`, TTL **600 seconds**; on network failure the stale cache is used, and with no cache it returns empty (without blocking the UI).

## 4. Caching and the Truth About the "Local Fallback"

| File | Written By | Contents | Present on Fresh Install |
|---|---|---|---|
| `~/.local/share/NewFreedeck/catalog_cache.json` | `main.py:_refresh_catalog_async` | the complete array from `all.json` | **No** |
| `~/.local/share/NewFreedeck/emu_cache.json` | `emulator_registry._save_cache` | `{entries, fetched_at}` | **No** |
| `cache/catalog/<platform>.json` | `py_modules/catalog_cache.py` | platform arrays (this class is **never used** in main.py) | No |

The order of `_load_catalog_async()` is: **read `catalog_cache.json` (which may not exist) → mark loaded → request all.json in the background**. There is no first-run fallback path to a "local CSV/built-in catalog" in the code; `game_id`/catalog data comes entirely from the server. So when the server is unavailable, a brand-new installation of NewFreedeck has an empty game library.

## 5. Measured Results (2026-11-16)

- `panyiwei.xyz` resolves via DNS to `114.55.3.101`;
- `http://panyiwei.xyz/freedeck-catalog/{all,emu,platform/gba,curated/gba,version}.json` all **TCP connection timeout** (20s), and HTTPS is equally unresponsive;
- `web.archive.org` CDX has no 200 snapshot for that path;
- There is no copy of `catalog_cache.json` / `emu_cache.json` anywhere in the local catalog/cache.

In other words: this is not a "theoretical risk" but a single point of failure that **has already happened**.

## 6. Security Issues

1. **Plaintext HTTP + certificate verification disabled**: `main.py` sets `ssl.CERT_NONE` for platform/curated requests, so any man-in-the-middle can replace the catalog/download links.
2. **No integrity checks**: there are no signatures, hashes, or version numbers; changes to server content flow straight into the user's library.
3. **Arbitrary URL delivery**: `down_url`/`cover_url` are decided by the server and requested directly by the frontend; a malicious entry could perform SSRF/phishing/traffic hijacking (covers go through the local `/proxy/cover`, meaning the plugin makes the request on the user's behalf).
4. **Supply-chain single point**: the catalog, emulator packages, and curated lists are all controlled by one individual's server; if that server goes down, gets blocked, or gets reported, everything collapses at once.
5. **Compliance**: the `share_url`s in `emu.json` are cloud-drive transfer links for emulator installer packages, and the catalog consists of piracy resource links; self-hosting a mirror carries the same distribution risk.

## 7. Alternatives (Half Already Implemented)

### 7.1 Catalog: Export from Our Own CSV

```bash
make catalog-json
# equivalent to:
python3 scripts/export_remote_catalog.py \
  --catalog defaults/tianyi_catalog/freedeckcy_catalog.csv \
  --out catalog-json
```

Output (a snapshot is already committed in the repo and can be read directly):

```
catalog-json/
  all.json                 # 7084 entries, NewFreedeck-compatible
  platform/<platform>.json # split by platform
  curated/<platform>.json  # curated per platform (cover first / size descending, 60 by default)
  manifest.json            # total count, platform distribution, sha256 of each file
```

Mapping: `categories → genre`, `openpath basename → file_name`, `filesize_z → size_bytes`, `title` split into `title_zh/title_en`; `install_size_*` left empty (our catalog has no reliable install size).

Self-hosting (any static server / GitHub Pages / release asset):

```bash
cd catalog-json
python3 -m http.server 8000
# all:     http://127.0.0.1:8000/all.json
# platform:http://127.0.0.1:8000/platform/gba.json
# curated: http://127.0.0.1:8000/curated/gba.json
```

freedeckCY itself can also read this JSON directly at runtime via `FREEDECKCY_CATALOG_JSON=/path/to/all.json` or `FREEDECKCY_CATALOG_JSON=https://.../all.json` (remote cache for 6 hours, reads from GitHub raw by default, automatically falls back to CSV on failure).

To point NewFreedeck at this data, you would need to change its constants/URLs (the `all.json`, `platform/...`, `curated/...` URLs in `main.py`, plus `_CATALOG_BASE` in `catalog_cache.py`); our repo does not modify third-party code directly — it only provides the data format and export tools.

### 7.2 Emulator Download Sources: Switch to Official Releases

Do not mirror the author's cloud-drive transfer packages. Use official/upstream releases per platform instead:

| Platform | Recommended Source |
|---|---|
| GBA | mGBA official GitHub Releases (**not bundled since v0.10.0; first install downloads the 0.10.5 AppImage**) |
| PS1 | DuckStation official GitHub Releases |
| PS2 | PCSX2 official GitHub Releases |
| PS3 | RPCS3 official site/GitHub |
| PSP | PPSSPP official GitHub Releases |
| 3DS | Lime3DS / Azahar official GitHub Releases |
| NDS | melonDS official GitHub Releases |
| FC | Nestopia / libretro official sources |
| MD | BlastEm official sources |
| Switch | upstream project Releases such as Eden |

Use `emu.json` only as an **optional local manifest** for users, with the following template (do not commit real share links):

```json
{
  "gba": { "share_url": "", "pwd": "", "file_name": "" },
  "ps1": { "share_url": "", "pwd": "", "file_name": "" }
}
```

### 7.3 Covers

Our catalog ships its own `cover_url` / `cover_index.csv` (after merging, 6823/7084 have covers), and the plugin caches them on disk; this does not depend on `panyiwei.xyz`. Where `cover_url` points to a third-party image host/Steam/libretro, availability must be assessed on your own.

### 7.4 Signing

The Tianyi download signature `sign_download` is a local algorithm (Rust `nfc_sign` / Python MD5 fallback), unrelated to the server; no reverse engineering or mirroring is needed.

## 8. Recommendations

1. Do **not** restore a hard dependency on `panyiwei.xyz` in the plugin; our existing local catalog + official emulator sources are already sufficient.
2. If a NewFreedeck-style remote catalog is needed in the future, prefer the static JSON generated by `export_remote_catalog.py`, and verify the sha256 in `manifest.json` on the client.
3. Always serve remote data over HTTPS, validate the schema, limit size/timeouts, and keep a **local snapshot fallback** (at least one `catalog_cache.json` shipped with the package or written on first install).
4. The cloud-drive links in `emu.json` are third-party transfers; self-hosting a mirror or distributing them publicly is not recommended.
