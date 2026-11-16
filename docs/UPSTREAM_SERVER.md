# 上游服务器依赖逆向：panyiwei.xyz

> 结论先行：**NewFreedeck 强依赖 `http://panyiwei.xyz/freedeck-catalog/`，且没有任何本地目录兜底**；本文记录其协议、缓存、失败模式与替代方案。**freedeckCY 不依赖该服务器**（目录/封面/模拟器均本地或官方源）。

## 1. 依赖点清单

| 用途 | URL | 使用方 | 失败后果 |
|---|---|---|---|
| 全量目录 | `http://panyiwei.xyz/freedeck-catalog/all.json` | `main.py:_refresh_catalog_async` | 首次安装无缓存 → 游戏库为空 |
| 平台目录 | `http://panyiwei.xyz/freedeck-catalog/platform/{platform}.json` | `main.py:_fetch_platform_remote`、`py_modules/catalog_cache.py` | 平台 tab 空 |
| 精选 | `http://panyiwei.xyz/freedeck-catalog/curated/{platform}.json` | `main.py:get_curated_shelf` | 精选 shelf 回退到 `_catalog_items`（若也为空则空） |
| 模拟器下载源 | `http://panyiwei.xyz/freedeck-catalog/emu.json` | `py_modules/emulator_registry.py` | 无法下载/部署模拟器，`fetch_emulator_sources()` 返回空 |
| 封面兜底 | 目录数据里的 `cover_url`（第三方图床/Steam/libretro） | `_enrich_one` 经本地 `/proxy/cover` 代理 | 缺图；不是 panyiwei 自身托管 |

- `platform` 取值：`switch / ps1 / ps2 / ps3 / psp / 3ds / gba / nds / fc / md`；`curated` 支持 `ns ↔ switch` 别名。
- 服务器是 **HTTP 明文**，无鉴权、无签名、无版本号接口（`get_catalog_version` 返回本地 "本地CSV"，并不请求服务器）。
- `sign_download` 的天翼下载签名是 **本地 Rust/Python 计算**（`nfc_sign`），**不是** panyiwei 依赖。

## 2. 目录数据 schema（根据 NewFreedeck 解析代码还原）

`all.json` / `platform/*.json` / `curated/*.json` 都是**数组**（平台接口也兼容 `{"games": [...]}` 或 `{"items": [...]}` 包裹）：

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

同款多版本会被 `_group_catalog_items()` 合并成一条，并附加：

```json
{
  "grouped": true,
  "variant_count": 3,
  "multi_disc": false,
  "disc_count": 1,
  "variants": [ { ...同 schema... } ]
}
```

要求：`down_url` 必须是可下载的天翼分享链接（前端直接拿它去解析/下载）；`game_id` 用于去重/收藏；`cover_url` 必须是绝对 URL 或空。

## 3. `emu.json` schema

```json
{
  "switch": { "share_url": "https://cloud.189.cn/...", "pwd": "abcd", "file_name": "eden.7z" },
  "gba":    { "share_url": "https://cloud.189.cn/...", "pwd": "efgh", "file_name": "mGBA.7z" },
  "ps1":    { "share_url": "...", "pwd": "...", "file_name": "..." }
}
```

- 键可以是平台名（`switch/gba/...`），也可以是适配器名（`eden/mgba/duckstation/pcsx2/rpcs3/ppsspp/lime3ds/melonds/nestopia/blastem`）；`_parse_json()` 会给平台名补一份适配器别名。
- 条目字段：`share_url`（也接受 `link`）、`pwd`（也接受 `code`）、`file_name`（可选）。
- 缓存：`~/.local/share/NewFreedeck/emu_cache.json`，TTL **600 秒**；网络失败时用旧缓存，没缓存返回空（不阻塞 UI）。

## 4. 缓存与“本地兜底”的真相

| 文件 | 写入方 | 内容 | 首次安装是否存在 |
|---|---|---|---|
| `~/.local/share/NewFreedeck/catalog_cache.json` | `main.py:_refresh_catalog_async` | `all.json` 的完整数组 | **否** |
| `~/.local/share/NewFreedeck/emu_cache.json` | `emulator_registry._save_cache` | `{entries, fetched_at}` | **否** |
| `cache/catalog/<platform>.json` | `py_modules/catalog_cache.py` | 平台数组（该类在 main.py 中**未被使用**） | 否 |

`_load_catalog_async()` 的顺序是：**读 `catalog_cache.json`（可能不存在）→ 标记 loaded → 后台请求 all.json**。代码里没有“本地 CSV/内置目录”的首次回退路径；`game_id/目录` 完全来自服务器。所以服务器不可用时，全新安装的 NewFreedeck 游戏库就是空的。

## 5. 实测（2026-11-16）

- `panyiwei.xyz` DNS 可解析：`114.55.3.101`；
- `http://panyiwei.xyz/freedeck-catalog/{all,emu,platform/gba,curated/gba,version}.json` 全部 **TCP 连接超时**（20s），HTTPS 同样无响应；
- `web.archive.org` CDX 没有该路径的 200 快照；
- 本地目录/缓存里没有任何 `catalog_cache.json` / `emu_cache.json` 副本。

也就是说：这不是“理论风险”，而是**当前已发生**的单点故障。

## 6. 安全问题

1. **明文 HTTP + 关闭证书校验**：`main.py` 对平台/精选请求设置 `ssl.CERT_NONE`，任意中间人可替换目录/下载链接。
2. **无完整性校验**：没有签名、hash、版本号；服务器内容变更会直接进入用户库。
3. **任意 URL 下发**：`down_url`/`cover_url` 由服务器决定，前端会直接请求；恶意条目可做 SSRF/钓鱼/流量劫持（封面走本地 `/proxy/cover`，等于由插件代请求）。
4. **供应链单点**：目录、模拟器包、精选全部由个人服务器控制；服务器下线/被墙/被举报即全灭。
5. **合规**：`emu.json` 的 `share_url` 是模拟器安装包的网盘转存链接，目录是盗版资源链接；自建镜像同样承担分发风险。

## 7. 替代方案（已落地一半）

### 7.1 目录：从我们自己的 CSV 导出

```bash
make catalog-json
# 等价于：
python3 scripts/export_remote_catalog.py \
  --catalog defaults/tianyi_catalog/freedeckcy_catalog.csv \
  --out catalog-json
```

输出（仓库内已提交一份快照，可直接读取）：

```
catalog-json/
  all.json                 # 7084 条，NewFreedeck 兼容
  platform/<platform>.json # 按平台拆分
  curated/<platform>.json  # 每平台精选（封面优先/体积降序，默认 60）
  manifest.json            # 总数、平台分布、每个文件的 sha256
```

映射关系：`categories → genre`、`openpath basename → file_name`、`filesize_z → size_bytes`、`title` 拆 `title_zh/title_en`；`install_size_*` 留空（我们目录没有可靠安装体积）。

自托管（任意静态服务器 / GitHub Pages / Release 资产）：

```bash
cd catalog-json
python3 -m http.server 8000
# all:     http://127.0.0.1:8000/all.json
# platform:http://127.0.0.1:8000/platform/gba.json
# curated: http://127.0.0.1:8000/curated/gba.json
```

freedeckCY 自身也可以用 `FREEDECKCY_CATALOG_JSON=/path/to/all.json` 或 `FREEDECKCY_CATALOG_JSON=https://.../all.json` 在运行时直接读这份 JSON（远程缓存 6 小时，默认仍读 CSV，失败自动回退）。

要把 NewFreedeck 指到这份数据，需要改它的常量/URL（`main.py` 的 `all.json`、`platform/...`、`curated/...`，以及 `catalog_cache.py` 的 `_CATALOG_BASE`）；我们仓库不直接改第三方代码，只提供数据格式与导出工具。

### 7.2 模拟器下载源：改用官方发行版

不要镜像作者的网盘转存包。建议按平台使用官方/上游发布：

| 平台 | 推荐来源 |
|---|---|
| GBA | mGBA 官方 GitHub Releases（**freedeckCY 已内置 0.10.5 AppImage**） |
| PS1 | DuckStation 官方 GitHub Releases |
| PS2 | PCSX2 官方 GitHub Releases |
| PS3 | RPCS3 官方站点/GitHub |
| PSP | PPSSPP 官方 GitHub Releases |
| 3DS | Lime3DS / Azahar 官方 GitHub Releases |
| NDS | melonDS 官方 GitHub Releases |
| FC | Nestopia / libretro 官方源 |
| MD | BlastEm 官方源 |
| Switch | Eden 等上游项目 Releases |

`emu.json` 只作为**用户可选的本地清单**使用，模板如下（不要提交真实分享链接）：

```json
{
  "gba": { "share_url": "", "pwd": "", "file_name": "" },
  "ps1": { "share_url": "", "pwd": "", "file_name": "" }
}
```

### 7.3 封面

我们的目录自带 `cover_url` / `cover_index.csv`（合并后 6823/7084 有封面），并由插件磁盘缓存；不依赖 `panyiwei.xyz`。`cover_url` 指向第三方图床/Steam/libretro 时需要自行评估可用性。

### 7.4 签名

天翼下载签名 `sign_download` 是本地算法（Rust `nfc_sign` / Python MD5 回退），与服务器无关，不需要逆向或镜像。

## 8. 建议

1. **不要**在插件里恢复对 `panyiwei.xyz` 的硬依赖；我们现有本地目录 + 官方模拟器源已经足够。
2. 如果未来要接 NewFreedeck 式远程目录，优先用 `export_remote_catalog.py` 生成的静态 JSON，并在客户端校验 `manifest.json` 的 sha256。
3. 远程数据一律走 HTTPS、做 schema 校验、限制大小/超时，并保留**本地快照兜底**（至少一份 `catalog_cache.json` 随包或首次安装写入）。
4. `emu.json` 里的网盘链接属于第三方转存，不建议自建镜像或公开分发。
