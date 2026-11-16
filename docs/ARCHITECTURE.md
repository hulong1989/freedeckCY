# freedeckCY 架构说明

本文面向二次开发者与维护者，说明 freedeckCY **本仓库（`main` 分支）**的实现结构，内容已同步到 freedeckCY **v0.8.0**（2026-11）的代码。文中代码引用均使用仓库内相对路径；`文件:行号` 指向当前工作区，重构后可能偏移，函数名可作稳定锚点。

---

## 1. 一句话定位

freedeckCY 是一个运行在 **Steam Deck / SteamOS** 上的 **Decky Loader 插件**：它把随插件分发的天翼云盘分享清单变成"可安装游戏库"，用 aria2 多线程下载、7zz 解压，再写入 Steam 的快捷方式与 Proton 兼容层配置，让非 Steam 游戏像正版一样出现在 Steam 游戏模式库中；此外还提供一条基于天翼云盘的**云存档备份 / 恢复**链路。

> 合规提示：项目 README 自述"仅限研发测试、资源源自互联网、24 小时内删除"，代码会解析第三方云盘分享链接并绕过官方客户端下载。这属于版权与云盘服务条款的高风险区，请自行评估后使用。

**关键事实**：它没有自建服务器。资源清单是仓库内的 CSV 文件（`defaults/tianyi_catalog/`，一条记录 = 游戏名 + 天翼云盘分享链接 + 解压后 exe 相对路径），下载直链在运行时由天翼云盘接口现取。

---

## 2. 仓库 ≠ 产品：`main` 只是早期版本

这是阅读本仓库最容易踩的坑：**GitHub Releases 里的成品功能远多于仓库代码**。

> 本仓库 **freedeckCY** 是上游 [Freedeck](https://github.com/panyiwei-home/Freedeck) 的衍生分支，版本号从 **0.1.0** 起步（与上游 0.2–0.3 不连续），当前 **0.8.0**。下面的"上游现状"描述的是上游仓库，不是本仓库已实现的功能。

| 位置 | 内容 | 说明 |
|---|---|---|
| 本仓库 `main` | `package.json` 版本 `0.8.0`，纯天翼云盘 + 多平台目录，适配 Steam Deck / DroidDeck | 从上游 Freedeck 2026-02 的早期版本（0.2）fork 而来，版本号重新从 0.1.0 起步；v0.1.1 完成"四件套"，v0.2.0 完成目录平台化/封面索引/分类筛选，v0.3.0 补齐全量目录与平台筛选 UI，v0.3.1 做分类清洗与目录数据体检，v0.4.0 做 DroidDeck（Android/ARM64）适配，v0.5.0 完成第一梯队浏览/分页/排序/已安装页签与诊断导出/更新检查，v0.6.0~v0.6.2 做 GBA 模拟器闭环与远程 JSON 目录，v0.7.0 做通用模拟器注册表并接入 PSP/NDS，v0.8.0 做 Ludusavi + gamewatch 自动云存档 |
| Releases v0.2.3 → v0.6 | 发布包约 50 MB | 增加**百度网盘**支持、**模拟器整合**、**资源池（用户上传）**、CRT 滤镜、点赞等 |
| Releases NewFreedeck v0.1 → v0.3 | 2026-08 ~ 09 重构版 | 模拟器可玩、稍后再玩 tab、分卷下载修复 |

由此得到几条直接结论：

- **仓库代码只是早期版本**：releases 里的百度网盘、模拟器、资源池等模块在 `main` 上完全不存在。不要在本仓库里寻找它们。
- **仓库缺运行时二进制**：`aria2_manager.py` / `seven_zip_manager.py` / `tianyi_client.py` 会优先查找 `defaults/runtime/` 下的 `aria2c`、`7zz`、`node`，但仓库本身不提交这些文件（已在 `.gitignore` 中）。插件可以不带它们启动，但要完整跑通下载/安装/云存档，克隆后必须先执行 `make runtime` 补齐，否则会分别报"下载组件不可用 / 解压组件不可用 / 未找到 node 运行时"。release zip 约 50 MB 与源码约 1 MB 的差值，主要就是这些二进制。
- **作者已停止维护**：NewFreedeck v0.1 的发布说明原文是"目前我没有精力与时间继续维护，抱歉，所以可以根据我整理的 skill 自行修改，最后可以给我推 pr"。
- **v0.8.0 自动云存档**：内置 **Ludusavi 存档清单**（53,549 款游戏，MIT）做标题/SteamID 匹配并把 `<winAppData>` 等模板解析到 Proton 前缀，与原有 Proton 扫描合并；`gamewatch` 每 8 秒用 `/proc/*/cmdline`（无 `/proc` 时 `pgrep -f`）检测游戏退出，**只对刚退出的游戏**自动触发云存档上传（设置 `cloud_save_auto_upload` 默认开启、30 秒防抖）；上传前用"相对路径+大小+mtime"指纹去重，未变化则 `reason=unchanged` 跳过（见 5.11）。
- **v0.7.0 通用模拟器注册表**：`EmulatorSpec` 注册表接入 **GBA（mGBA 0.10.5）/ PSP（PPSSPP 1.20.4）/ NDS（melonDS 1.1）** 三个平台——GBA 随包内置，PSP/NDS 首次安装按需下载官方 AppImage（NDS 为 zip 内 AppImage），统一 `--appimage-extract` 解包（不依赖 FUSE），生成启动脚本后以原生 Linux 快捷方式注册（不写 Proton）；PS1 因 BIOS 依赖暂缓，其它平台仍只可浏览（见 5.10 / ROADMAP 9.8）。
- **v0.6.1 / v0.6.2 远程 JSON 目录**：`FREEDECKCY_CATALOG_JSON` 支持本地文件或 HTTP(S) JSON（NewFreedeck 兼容格式），远程缓存 6 小时、失败自动回退 CSV；默认仍读内置 CSV，详见 [UPSTREAM_SERVER.md](UPSTREAM_SERVER.md)。
- **v0.5.0 第一梯队（浏览体验与运维）**：库页打开即浏览全部资源、平台/分类筛选 + 分页 + 排序，新增「已安装」页签（启动/打开目录/卸载），顶部工具条可**导出诊断 zip**（脱敏）与**检查 GitHub 更新**（1 h 缓存）；交互与快捷键见 5.8、诊断/更新见 5.9。
- **v0.4.0 DroidDeck 适配**：ARM64 运行时选择、DroidDeck 检测、ARM Proton 工具自动解析、双 Steam 根（x64 客户端优先）、`PACKAGE_ARCH` 打包 arm64/universal 包；安装、构建与排障见 [DROIDDECK.md](DROIDDECK.md)。
- **目录/封面能力（v0.3.1 起）**：内置全量目录 `freedeckcy_catalog.csv`（**7084 条有效 / 11 个平台**，16 列，分类已清洗）+ 封面索引 `cover_index.csv`（3470 行，合并后 **6823 条资源自带封面，96.3%**）；封面按"目录静态 → 磁盘缓存 → Steam 商店 → ProtonDB"解析并落盘缓存；库页有**平台 + 分类两行筛选条**（分类含「模拟器」606 条）。`make validate-catalog`（CI `--strict`）会体检目录数据。**GBA/PSP/NDS 已可安装/启动**（v0.6.0 起 GBA，v0.7.0 追加 PSP/NDS）；其它平台目前只可浏览、不可安装（见 5.10 / ROADMAP 9.8）。
- **v0.1.1 的"四件套"**：卸载可选回收 Proton 前缀（默认不删）、`7z t` 校验 + 自动重下、失败任务「重试」、`make doctor` 环境诊断（见 §6.6–§6.8 / DEVELOPMENT §6.6）。
- **本仓库由模板 / 旧项目改造而来**：`defaults/defaults.txt` 仍是 Decky 模板说明文件，`config.py` 里保留了 `Decky-send` 命名的回退路径。`package.json` 里指向上游模板的 `repository` / `bugs` / `homepage` 已移除，`license` 改为 BSD-3-Clause（与 `LICENSE` 一致）。

> 本次补全统一了源码行尾为 LF（`.gitattributes` 约束），所以用 `git diff` 看提交时可能出现“整文件重写”的假象，实际逻辑改动见各文件 diff 的 `-w` 视图。

---

## 3. 技术栈

| 层 | 选型 | 位置 |
|---|---|---|
| 插件运行时 | Decky Loader（Python 3 + asyncio） | `main.py`、`decky.pyi` |
| 本地 Web 服务 | **aiohttp**，仅监听 `127.0.0.1:59271` | `py_modules/server_manager.py` |
| 业务内核 | 单个巨型类 `TianyiService`（约 8000 行） | `py_modules/tianyi_service.py` |
| 天翼 API 客户端 | aiohttp + 自写 MD5 签名 / XML/JSONP 兼容解析 | `py_modules/tianyi_client.py` |
| 状态持久化 | 单个 JSON 全量重写；状态目录 0700 / 文件 0600 | `py_modules/tianyi_store.py` → `~/.local/share/freedeckCY/tianyi/state.json` |
| 日志 | `RotatingFileHandler`（5 MB × 3，`propagate=False`） | `py_modules/config.py` → `/tmp/freedeckcy.log` |
| 下载器 | 内置 / 系统 **aria2c**，JSON-RPC 控制 | `py_modules/aria2_manager.py` |
| 解压 | 内置 / 系统 **7zz**（`.7z/.rar` 等；解压前 `7z t` 校验，best-effort），其余走 `shutil` | `py_modules/seven_zip_manager.py` |
| Steam 集成 | 自实现 VDF 读写 + 二进制 `shortcuts.vdf` | `py_modules/steam_shortcuts.py`、`py_modules/vdf/` |
| QAM 前端 | **React 19 + TypeScript**，`@decky/api` + `@decky/ui`，Rollup 打包 | `src/index.tsx` → `dist/index.js` |
| 本地网页前端 | **Vue 3 全局构建**（无构建步骤，直接引入 `vue.global.prod.js`）：浏览/分页/排序/已安装页签/诊断与更新工具条 | `defaults/tianyi_library_ui/` |
| 游戏目录 / 封面 | CSV 目录（分类清洗）+ `cover_index.csv`；封面缓存 JSON（TTL 7 天）；`validate_catalog.py` 数据体检 | `py_modules/game_catalog.py`、`py_modules/tianyi_service.py`、`scripts/validate_catalog.py` |
| 云盘上传 / 分享兜底 | **Node ≥ 18**，子进程 stdin/stdout JSON 协议 | `backend/*.js`、`backend/*.cjs` |
| 环境诊断 | 只读 bash 脚本（运行时/Steam/state/日志/端口/网络）；另有 HTTP 诊断 JSON/zip 导出与 GitHub 更新检查（v0.5.0） | `scripts/doctor.sh`（`make doctor`）、`tianyi_service.get_diagnostics()` |
| 运行平台 | Steam Deck（x86_64）/ **DroidDeck（aarch64）**；运行时目录按 `platform.machine()` 选择 | `defaults/runtime/<arch>/`、`scripts/package.sh`、[DROIDDECK.md](DROIDDECK.md) |
| 自动云存档（v0.8.0） | **Ludusavi 清单**（本地 JSON，53,549 游戏，MIT）+ **gamewatch** 进程检测；退出后只上传该游戏，指纹去重 | `py_modules/save_manifest.py`、`py_modules/gamewatch.py`、`defaults/ludusavi/` |
| 模拟器运行时（v0.6.0 起，v0.7.0 注册表） | **GBA=mGBA 0.10.5（内置）/ PSP=PPSSPP 1.20.4（按需下载）/ NDS=melonDS 1.1（按需下载 zip）**；AppImage 首次 `--appimage-extract` 解包后原生运行（不依赖 FUSE） | `py_modules/emulator_manager.py`（`EMULATORS` 注册表）、`defaults/runtime/mgba/<arch>/` |

运行时一共会拉起 **4 类进程**：Decky 的 Python 进程、`aria2c`、`7zz`、偶尔的 `node`。

### 3.1 运行环境与平台（Steam Deck / DroidDeck，v0.4.0）

| 项 | Steam Deck | DroidDeck |
|---|---|---|
| CPU 架构 | x86_64 | **aarch64（ARM64）** |
| 运行环境 | SteamOS | Android 上的 proot SteamOS 运行时，HOME 通常 `/root` |
| Steam 根 | `~/.steam/steam` / `~/.local/share/Steam` / Flatpak | 同上；x64 客户端另有 `~/.droiddeck-x64/.local/share/Steam` |
| Proton 工具 | `proton_experimental` 等 Valve 工具 | **ARM 工具名** `droiddeck-proton-arm64` / `droiddeck-proton-11-arm64` |
| 运行时二进制 | `defaults/runtime/x86_64/` | `defaults/runtime/aarch64/` |

- **运行时架构**：aria2c / 7zz / node 都按 `platform.machine()` 归一（`x86_64`；`aarch64`/`arm64`→`aarch64`）后找 `defaults/runtime/<arch>/`，见 [aria2_manager.py:107](../py_modules/aria2_manager.py) `_resolve_binary_path()`、[seven_zip_manager.py:26](../py_modules/seven_zip_manager.py) `_resolve_binary_path()`、[tianyi_client.py:628](../py_modules/tianyi_client.py) `_runtime_arch()`。
- **DroidDeck 检测**（[steam_shortcuts.py:60](../py_modules/steam_shortcuts.py) `is_droiddeck()`）：只看文件系统标记——`DROIDDECK_ROOT` 环境变量、`~/.droiddeck-x64`、`~/.droiddeck-decky-enabled`、`~/.droiddeck`、`<steam_root>/package/droiddeck-installed`。
- **Proton 工具解析**（[steam_shortcuts.py:78](../py_modules/steam_shortcuts.py) `detect_proton_tool()`）：`FREEDECKCY_PROTON_TOOL` 优先（`none` 表示不写映射）→ DroidDeck 下 `droiddeck-proton-11-arm64`（`config.vdf` 已出现时）或 `droiddeck-proton-arm64` → 其它环境 `proton_experimental`；设置项 `proton_tool` 默认 `auto`（见 6.5）。
- **Steam 根选择**（[steam_shortcuts.py:33](../py_modules/steam_shortcuts.py) `_steam_root_candidates()`）：标准候选之外加入 `~/.droiddeck-x64/.local/share/Steam`——若其 `steam.pid` 存在则**排最前**（优先写正在运行的 x64 客户端），否则排最后；也可用 `FREEDECKCY_STEAM_ROOT` 手动锁定。
- 安装、构建与排障见 [DROIDDECK.md](DROIDDECK.md)。

---

## 4. 目录地图

```text
repo/
├── main.py                     # 插件入口：Plugin 类，24 个可调用 RPC，大部分薄转发给 TianyiService / server_manager
├── plugin.json                 # Decky 元信息（api_version=1, flags=[]，publish 描述已更新）
├── package.json                # 版本 0.7.0；build=rollup；前端依赖
├── decky.pyi                   # Decky Python API 类型存根
├── Makefile                    # runtime / package / test / doctor / clean / help 目标（见 DEVELOPMENT.md）
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
│   ├── ludusavi/              # Ludusavi 存档清单（manifest.json 53,549 游戏 / LICENSE / README，随包分发）
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
│   ├── emulator_manager.py      # 通用模拟器注册表（GBA/PSP/NDS：官方资产、按需下载、解包、ROM 查找、启动参数）
│   ├── save_manifest.py         # Ludusavi 存档清单加载/标题与 SteamID 匹配/占位符 → Proton 前缀路径解析
│   ├── gamewatch.py             # /proc 或 pgrep 的游戏进程检测（退出事件触发自动云存档）
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
│   ├── fetch_emulator.sh       # 下载 mGBA AppImage（x86_64/aarch64）到 defaults/runtime/mgba/<arch>/
│   ├── fetch_ludusavi_manifest.py  # 从上游 YAML 转换 Ludusavi 清单到 defaults/ludusavi/manifest.json.gz（需 PyYAML，仅构建时）
│   ├── package.sh              # 组装 Decky 插件 zip 到 dist-artifacts/（PACKAGE_ARCH=x86_64|aarch64|all）
│   ├── doctor.sh               # 环境诊断（只读）：运行时/Steam/state/日志/端口/网络
│   ├── merge_v06_catalog.py    # 从上游 v0.6 目录合并生成 freedeckcy_catalog.csv + cover_index.csv（可复现）
│   ├── normalize_catalog_categories.py  # 原地清洗分类（去平台名/去重/模拟器兜底，--check 只检查）
│   └── validate_catalog.py     # 目录数据体检（--strict 用于 CI：重复/非法链接/分类混平台名/封面覆盖率…）
├── tests/                      # pytest 单测（289 个用例，不联网、不碰 Steam 目录）
├── docs/                       # 项目文档（ARCHITECTURE / DEVELOPMENT / ROADMAP / DROIDDECK / UPSTREAM_SERVER）
├── .github/workflows/ci.yml    # CI：pytest + 目录数据体检（validate_catalog --strict）+ pnpm build
├── gl/                         # 作者手工囤的数据：按日期 dump 的 CSV、模拟器分享链接 emu.csv
└── assets/logo.png
```

> `gl/` 是作者囤数据的目录（如 `gl/2026-3-21.csv` 4137 行、`gl/emu.csv` 模拟器资源），**代码不读它**，运行时只读 `defaults/tianyi_catalog/`。

---

## 5. 运行时架构

### 5.1 进程与模块树

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
│        ├── EmulatorManager     ──▶ mGBA AppImage（--appimage-extract 解包后原生运行；GBA 安装）
│        ├── TianyiClient        ──▶ cloud.189.cn / api.cloud.189.cn（Cookie + MD5/AES/RSA 签名）
│        └── 封面缓存             ──▶ ~/.local/share/freedeckCY/tianyi/cover_cache.json（TTL 7 天）
│
├── aiohttp 本地服务（127.0.0.1:59271，只绑回环）
│   ├── /                            服务首页
│   ├── /_healthz                    健康检查
│   ├── /tianyi/library              Vue 游戏库橱窗  ── 由 Steam 内置浏览器打开
│   ├── /tianyi/library/login-bridge 二维码登录桥
│   └── /api/tianyi/*                38 条 REST 路由（给 Vue 页用）
│
└── 外部依赖
    ├── open.e.189.cn        二维码登录
    ├── api.cloud.189.cn     accessToken / 直链 / 分片上传
    ├── node (>=18)          分享解析兜底、云存档上传（stdin/stdout JSON 子进程）
    └── mGBA (AppImage)      GBA 模拟器（x64/arm64，内置 AppImage 或系统/Flatpak）
```

### 5.2 三条"控制面"、一条"数据面"

- **控制面 1**：QAM 面板 ↔ `@decky/api` RPC（`main.py` 的 24 个可调用方法，前端实际用到其中 20 个天翼 RPC；入口 [main.py:39](../main.py) `_main`，天翼 RPC 定义从 [main.py:147](../main.py) 起）。
- **控制面 2**：Vue 页面 ↔ 本地 HTTP API（`py_modules/tianyi_http.py` 的 38 条 `/api/tianyi/*` 路由，路由表在 [tianyi_http.py:609](../py_modules/tianyi_http.py) `setup_routes()`）。
- **控制面 3**：Python ↔ Node 子进程（stdin 一行 JSON，stdout 一行 JSON；node 解析见 [tianyi_client.py:638](../py_modules/tianyi_client.py) `_resolve_node_binary()`）。
- **数据面**：`aria2c` 从 `api.cloud.189.cn` 拿到的直链下载到本地磁盘。

### 5.3 两个前端的分工

| | QAM 面板（React） | 本地网页（Vue） |
|---|---|---|
| 路由 | 插件内容区 + `/freedeckcy/settings` | `/tianyi/library`、`/tianyi/library/login-bridge` |
| 页面 | 登录状态/入口、下载队列（最多 20 条，自绘进度条）、已安装游戏预览+卸载；设置页 4 个 tab（路径/安装/下载/账号，账号页含云存档上传与恢复） | **两个**：游戏库橱窗（打开即浏览全部资源 + 搜索/平台/分类筛选 + 分页 + 排序 + 「已安装」页签 + 诊断/更新工具条 + 安装确认弹窗）、二维码登录桥 |
| 能干什么 | 看任务、暂停/继续/移除任务、改设置、管云存档、卸载（除了卸载，**不能**自己发起下载） | **唯一能"下单"的地方**：浏览→确认→创建下载任务 |
| 交互特点 | 900 ms / 6 s / 30 s 三档轮询 | 手柄/键盘双焦点模型（160 ms 轮询、方向键导航、A/B/X/Y/L1/R1 快捷键，为掌机设计；详见 5.8） |
| 怎么打开 | 插件自带 | 调 RPC 拿 URL → `SteamClient.Browser.OpenUrl`（Steam 内置浏览器），不是 iframe/webview |

QAM 主面板由登录/操作入口、下载列表、已安装游戏预览等 `PanelSection` 组成，代码在 [src/index.tsx:2488](../src/index.tsx) `Content()` 到文件末尾；设置页是 `Tabs` 四页（路径 / 安装 / 下载 / 账号），在 [src/index.tsx:1565](../src/index.tsx) `SettingsPage()`。

### 5.4 前端调用面

**RPC（[src/index.tsx:310](../src/index.tsx) 起，全部 `callable("...")`，共 20 个天翼 RPC）**

| RPC | 用途 |
|---|---|
| `get_tianyi_panel_state` | 面板总状态（登录/任务/已装/设置），高频轮询 |
| `get_tianyi_cloud_save_upload_status` / `..._restore_status` | 云存档进度，运行中 1.2 s |
| `get_tianyi_library_game_time_stats` | 库页时长（本人/主线/总时长），2 min 或 3 s 重试 |
| `get_tianyi_library_url` / `get_tianyi_login_url` | 拿本地页面 URL |
| `set_tianyi_settings` / `clear_tianyi_login` | 设置 / 注销 |
| `start_tianyi_cloud_save_upload` / `list_..._options` / `list_..._entries` / `plan_..._restore` / `apply_..._restore` | 云存档五连 |
| `pause_tianyi_task` / `resume_tianyi_task` / `remove_tianyi_task` / `retry_tianyi_task` | 暂停 / 继续 / 移除 / 重试下载任务 |
| `uninstall_tianyi_installed_game` | 卸载（删目录 + 记录；可选 `delete_compatdata` 回收 Proton 前缀） |
| `preview_tianyi_uninstall` | 卸载预览（安装目录 / compatdata 占用） |
| `record_tianyi_game_action` | 启动/退出事件上报（计时用） |

**HTTP API 分组（`py_modules/tianyi_http.py` 的 `setup_routes()`，41 条路由）**：3 条页面/静态资源（`/tianyi/library`、`/tianyi/library/login-bridge`、静态文件兜底），以及 `login/*`（qr、capture、manual、clear）、`catalog`（`q/platform/category/page/page_size/sort`）、`catalog/cover`、**`installed`（GET 列表 + POST launch/open-folder/uninstall）**、**`diagnostics`（GET JSON + GET export zip）**、**`update-check`（GET）**、`settings`、`install/prepare|start`、`download/create|tasks|pause|resume|remove`、`cloud-save/*`、`state`。

### 5.5 目录与封面体系（v0.2.0 / v0.3.0）

**目录 CSV**（`defaults/tianyi_catalog/*.csv`，环境变量 `FREEDECKCY_GAME_CATALOG_CSV`，兼容旧 `FRIENDECK_GAME_CATALOG_CSV`；条目结构见 [game_catalog.py:37](../py_modules/game_catalog.py) `GameCatalogEntry`）：

- 16 列：`game_id,title,category_parent,categories,package_name,server,down_url,shorturl,pwd,openpath,filesize_z,list_filesize,platform,cover_url,cover_portrait_url,steam_appid`；
- `down_url` 支持两种天翼分享链接：`https://cloud.189.cn/t/<code>?pwd=...` 与 `https://cloud.189.cn/web/share?code=...`（后者必须带 `code=`）；目录校验 [game_catalog.py:123](../py_modules/game_catalog.py) `_is_valid_tianyi_url()` 与协议层 [tianyi_client.py:185](../py_modules/tianyi_client.py) `parse_share_url()` 都兼容两种形式；
- v0.2.0 新增 4 个可选列：`platform`（默认 `pc`；别名 `steam/windows/win`→`pc`、`ns/nsx`→`switch`）、`cover_url`（横版）、`cover_portrait_url`（竖版）、`steam_appid`；
- 目录文件优先级（[game_catalog.py:144](../py_modules/game_catalog.py) `resolve_default_catalog_path()`）：`FREEDECKCY_GAME_CATALOG_CSV` → 插件目录 `freedeckcy_catalog.csv` → 旧版 `gamebox_all_links_20260221_234730.csv`（回退）→ `defaults/tianyi_catalog.csv` → 当前目录下的 export 副本；
- 当前内置 `freedeckcy_catalog.csv`：**7084 条有效、11 个平台** —— PC 2540 / FC 1475 / NDS 722 / PSP 575 / GBA 553 / 3DS 305 / PS2 250 / PS1 194 / PS3 194 / MD 191 / Switch 85；
- 分类已清洗（v0.3.1，见 5.6）：Top12（计数，一条可属多分类）——动作冒险 3483、角色扮演 970、**模拟器 606**、策略战棋 535、模拟经营 371、休闲益智 352、枪战射击 272、体育竞速 258、恐怖惊悚 119、卡牌桌游 59、格斗清版 29、即时战略 14；**分类中不再出现平台名**（GBA/Switch 等已并入「模拟器」）；
- 旧 `gamebox_all_links_20260221_234730.csv` 保留为回退（2845 行 / 2685 条有效，全 PC），新目录缺失时仍能启动；
- **远程 JSON 目录（v0.6.1/v0.6.2）**：`FREEDECKCY_CATALOG_JSON` 可指向本地 JSON 或 `https://…` URL（NewFreedeck 兼容格式，[game_catalog.py:168](../py_modules/game_catalog.py) `resolve_default_catalog_json_path()`）；远程内容缓存 6 小时（[game_catalog.py:23](../py_modules/game_catalog.py) `REMOTE_CATALOG_TTL_SECONDS`），拉取失败回退本地 CSV/缓存。默认不开启，发布包行为不变；格式与自托管说明见 [UPSTREAM_SERVER.md](UPSTREAM_SERVER.md)。

**封面索引（`defaults/tianyi_catalog/cover_index.csv`，仓库已内置）**：

- 路径（[game_catalog.py:189](../py_modules/game_catalog.py) `resolve_default_cover_index_path()`）：环境变量 `FREEDECKCY_COVER_INDEX_CSV` 优先（兼容旧 `FRIENDECK_COVER_INDEX_CSV`），其次插件目录 `defaults/tianyi_catalog/cover_index.csv`；当前仓库内置 **3470 行**，缺失时自动跳过（封面走在线解析）；
- 表头：`game_id,title,steam_appid,cover_url,cover_portrait_url,platform`；
- 列名兼容：横版 `cover_url` / `landscape_cover_url` / `cover`；竖版 `cover_portrait_url` / `square_cover_url` / `portrait_url` / `portrait`；appid `steam_appid` / `app_id` / `appid`；
- 合并规则（[game_catalog.py:476](../py_modules/game_catalog.py) `_merge_cover_index()`）：先按 `game_id` 精确匹配，其次按标题（去空白、小写）匹配；**只补空值，不覆盖目录 CSV 已有值**；`platform` 也可被索引补齐；合并后 **6823 / 7084 条资源自带封面（96.3%）**；`summary()` 汇总 `cover_index_total` / `with_cover` / `platforms`。

**封面解析优先级**（[tianyi_service.py:1903](../py_modules/tianyi_service.py) `resolve_catalog_cover()`）：

1. **目录/封面索引静态封面**（[tianyi_service.py:1875](../py_modules/tianyi_service.py) `_catalog_entry_cover()`）：CSV/索引自带 `cover_url`/`cover_portrait_url` 直接用；只有 `steam_appid` 时合成 Steam CDN 图（横版 `.../apps/<appid>/header.jpg`、竖版 `.../apps/<appid>/library_600x900.jpg`），`source="catalog"`；
2. **内存 + 磁盘缓存**（[tianyi_service.py:1823](../py_modules/tianyi_service.py) `_load_cover_cache()` / [tianyi_service.py:1852](../py_modules/tianyi_service.py) `_save_cover_cache()`）：`~/.local/share/freedeckCY/tianyi/cover_cache.json`（目录 0700、文件 0600、临时文件 + `os.replace` 原子写；启动时只加载未过期项）；正结果 TTL **7 天**（`CATALOG_COVER_CACHE_TTL_SECONDS`），负结果 TTL **30 分钟**（`CATALOG_COVER_NEGATIVE_TTL_SECONDS`）；
3. **Steam 商店搜索**（`store.steampowered.com/api/storesearch`，中文/中国区，最多 8 个候选）；
4. **ProtonDB 兼容性等级**（拿到 appid 后附加查询，仅作 `protondb_tier` 展示字段）。

解析结果写回内存并落盘；`/api/tianyi/catalog/cover` 返回 `cover_url/square_cover_url/source/matched_title/app_id/protondb_tier/cached`。`cached=true` 表示来自静态封面或缓存。

**平台 / 分类筛选**：

- `GET /api/tianyi/catalog?q=&page=&page_size=&platform=&category=`（[tianyi_http.py:270](../py_modules/tianyi_http.py) `handle_catalog()`；过滤实现在 [game_catalog.py:559](../py_modules/game_catalog.py) `list()`），返回 `items/total/page/page_size/platforms/categories/platform/category`；`platforms` 为各平台计数（降序，[game_catalog.py:535](../py_modules/game_catalog.py) `platform_counts()`），`categories` 为分类 Top12（`CATEGORY_FILTER_LIMIT`，[game_catalog.py:547](../py_modules/game_catalog.py) `category_counts()`）；
- `platform` 传 `all`/`*` 视为不筛选；`category` 对 `categories` 字段做大小写不敏感子串匹配；平台与分类可组合（如 `platform=gba&category=动作冒险`）；
- 库页现状（v0.3.0）：搜索后显示**两行筛选条**——第一行「全部平台」+ 各平台（带计数），第二行「全部分类」+ Top12 分类（带计数）；手柄焦点顺序：搜索框 → 搜索按钮 → **平台条** → **分类条** → 卡片；卡片对非 `pc` 平台显示平台标签；
- **平台筛选已实现**（v0.3.0）：`platforms` 数量 > 1 时前端才显示平台条，当前 11 个平台所以可见；选择平台后请求带 `platform` 参数并刷新列表。
- **GBA 可安装、其它模拟器平台只可浏览**（v0.6.0）：前端对 GBA 卡片正常打开安装确认（弹窗显示"模拟器：mGBA"），其它非 PC 平台仍 flash 提示；后端 `_build_install_plan()` 只放行 `pc`/`gba`，其余抛"只支持 PC 与 GBA（mGBA）资源"。GBA 闭环见 5.10，其它平台见 ROADMAP 9.8。

### 5.6 分类清洗与目录数据体检（v0.3.1）

**分类清洗规则**（[game_catalog.py:89](../py_modules/game_catalog.py) `normalize_categories()`）：

- 分隔符：`,`、`，`、`/`、`、`、`;`、`；`、`|` 全部视为分类分隔符；
- 逐段去空白，**不区分大小写去重**，输出统一用英文逗号连接；
- 剔除平台名 token（[game_catalog.py:21](../py_modules/game_catalog.py) `PLATFORM_TOKENS`：`pc/fc/nds/psp/gba/3ds/ps1/ps2/ps3/md/switch/ns/arcade/psx`）以及该行自身的 `platform`；
- 模拟器行（`platform != pc`）清洗后若没有分类，自动补 **「模拟器」**；PC 行清洗后为空则保持空；
- `GameCatalog.load()` 对每行应用该清洗，`category_counts()` 用同一分隔规则统计——所以 CSV 未清洗时运行时也不会把平台名当分类展示。

**数据清洗结果（v0.3.1）**：`freedeckcy_catalog.csv` 共 **606 行** categories 被改写；平台名已全部剔除；「模拟器」分类 **606 条**（GBA 553 + Switch 42 + 11 条原本分类为空的模拟器行）；`normalize_catalog_categories.py --check` 现在是 **0 差异**（幂等）。

**脚本与命令**：

| 命令 | 作用 |
|---|---|
| `python3 scripts/normalize_catalog_categories.py <csv>` | 原地清洗 categories（临时文件 + 原子替换）；加 `--check` 只报告差异不写盘 |
| `python3 scripts/validate_catalog.py <csv> [--cover-index <csv>] [--strict]` | 目录体检：必需列/行数、重复 `game_id`、重复 `down_url`（警告）、非法天翼链接、空标题/空分类、分类混入平台名、平台分布、分类 Top10、封面覆盖率（含 cover_index）、资源总大小 |
| `make normalize-catalog` | 对内置目录执行清洗 |
| `make validate-catalog` | 对内置目录 + cover_index 执行体检（`--strict`） |

**当前体检结果**（`make validate-catalog`，2026-11 v0.3.1）：

- 7084 行 / 16 列；平台分布 11 个（PC 2540 / FC 1475 / NDS 722 / PSP 575 / GBA 553 / 3DS 305 / PS2 250 / PS1 194 / PS3 194 / MD 191 / Switch 85）；
- 自带封面 **3473/7084（49.0%）**；`cover_index.csv`（3470 行）按 `game_id` 命中 **3311**，合并覆盖 **6783/7084（95.8%）**；加载器按 `game_id` 或标题合并后 **6823/7084（96.3%）**（validate 只按 game_id 统计，故与运行时略差）；
- 资源总大小 **约 39 TB**（39098.5 GB）；
- 无错误，仅 1 条警告：46 个重复 `down_url`（同一分享多条目，属正常）。

**CI 门禁**：`.github/workflows/ci.yml` 的 python job 在 pytest 之后执行 `validate_catalog.py ... --strict`——重复 `game_id`、非法链接、空标题、分类混平台名等硬错误会让 CI 直接失败；修改目录数据后请本地先跑 `make validate-catalog`。

### 5.7 打包与部署（PACKAGE_ARCH / arm64 包，v0.4.0）

[scripts/package.sh](../scripts/package.sh) 用 `PACKAGE_ARCH` 控制目标架构（默认 `x86_64`；可选 `aarch64` / `all`）：

| 命令 | 产物 | 说明 |
|---|---|---|
| `make package` | `dist-artifacts/freedeckCY-v<version>.zip` | x86_64；自动裁剪其它架构 runtime |
| `make package-droiddeck` | `...-arm64.zip` | 等价于 `PACKAGE_ARCH=aarch64 bash scripts/package.sh` |
| `PACKAGE_ARCH=all make package` | `...-universal.zip` | 同时保留 x86_64 + aarch64 两份 runtime，体积更大 |

- 单架构打包会删掉 `defaults/runtime/{aria2,7z,node,mgba}/*/<arch>` 下其它架构目录，避免包体积翻倍；打包前可先 `make runtime ARCH=aarch64`（或 `ARCH=all`）准备 arm64 的 aria2c / 7zz / node，GBA 还要 `make emulator-runtime ARCH=...`（或 `bash scripts/fetch_emulator.sh --arch all`）准备 mGBA AppImage；
- 打包脚本会检查 `defaults/runtime/mgba/<arch>/mGBA.AppImage` 是否存在：缺失只警告（GBA 安装后无法启动），Steam Deck 包与 `-arm64.zip` 各自内置对应架构的 mGBA；**只有 GBA 的 mGBA 随包内置**，PSP（PPSSPP）/NDS（melonDS）的官方 AppImage 不打进包，首次安装时按需从 GitHub release 下载（需要网络，失败会报错可重试）；
- 产物命名后缀：`PACKAGE_ARCH=aarch64` → `-arm64`，`all` → `-universal`，`x86_64` 无后缀；
- 部署到 DroidDeck：把 `-arm64.zip` 放进手机存储，用 Decky 的 **Import plugin zip** 安装（DroidDeck 按 `plugin.json` 的 name 覆盖安装）；首次使用与排障见 [DROIDDECK.md](DROIDDECK.md)。

### 5.8 库页交互与焦点模型（v0.5.0）

**打开即浏览**：页面 `bootstrap()` 先 `GET /api/tianyi/state` 拿设置，再 `reloadList(1)` + `reloadInstalled()`；空查询不再隐藏结果，`hintText` 显示「共 N 条资源，第 x / y 页」。搜索/平台/分类/排序变化都会回到第 1 页。

**顶部工具条**（`tabindex=-1`，手柄焦点不进入工具条，用快捷键触发）：

| 工具 | 行为 |
|---|---|
| 游戏库 / 已安装（带数量 badge） | 切换 `mode`；已安装页签切换时重新拉 `GET /api/tianyi/installed` |
| 排序（仅游戏库） | 循环 `sortOptions = ["", "title", "size_desc", "size_asc"]`，显示"排序：默认/名称/大小↓/大小↑" |
| 导出诊断 | 浏览器直接下载 `GET /api/tianyi/diagnostics/export`（zip） |
| 检查更新 | `GET /api/tianyi/update-check`：有新版本弹 confirm 打开 Release URL，否则 flash"已是最新" |

**焦点序列**：搜索框(0) → 搜索按钮(1) → 平台条（`platformChipCount()` 个）→ 分类条（`categoryChipCount()` 个）→ 卡片（`cardStartIndex() = 2 + 平台数 + 分类数`）。筛选条只在对应 chip 数 > 1 时出现；已安装页签下两个 chip 计数都归 0，所以卡片从 2 开始。**v0.5.0 修复**：卡片 `focus-ring` 与点击/激活都改用 `cardStartIndex()`，筛选条存在时不再偏移。

**快捷键 / 手柄**：

| 输入 | 行为 |
|---|---|
| 方向键 / 摇杆 | 2D 焦点移动；卡片区上下按实际列数（`getCardColumns()`）跳转，筛选条与卡片之间可上下切换 |
| Enter / A | 激活焦点：搜索框/按钮→重新加载；平台/分类 chip→筛选；游戏卡片→安装确认弹窗 |
| B / Esc | 返回：先关 confirm/安装弹窗，已安装页签则回游戏库，否则回搜索框 |
| X | 切换「游戏库 / 已安装」页签 |
| Y | 游戏库：循环排序；已安装：打开当前卡片安装目录 |
| O | 仅已安装页签：打开安装目录 |
| Delete | 仅已安装页签：卸载当前卡片（弹 confirm） |
| PageUp / PageDown、L1 / R1 | 上一页 / 下一页（仅游戏库；边界会被 clamp） |
| 搜索框内输入 | 不拦截普通按键；Esc 退出搜索框 |

**已安装页签接口**：

- 列表 `GET /api/tianyi/installed`：handler [tianyi_http.py:304](../py_modules/tianyi_http.py) `handle_installed_games()` → 服务 [tianyi_service.py:5992](../py_modules/tianyi_service.py) `list_installed_games()`；返回 `{total, items[]}`，按 `updated_at` 倒序，补 `exists`（目录还在不在）、`platform`/`cover_url`/`cover_portrait_url`/`steam_appid`。
- 启动 `POST /api/tianyi/installed/launch`：handler [tianyi_http.py:313](../py_modules/tianyi_http.py) `handle_installed_launch()` → [tianyi_service.py:6017](../py_modules/tianyi_service.py) `launch_installed_game()`；用 `_launch_external("steam://rungameid/<appid>")` 拉起 Steam，AppID 缺失时报"请从 Steam 库手动启动"。
- 打开目录 `POST /api/tianyi/installed/open-folder`：handler [tianyi_http.py:323](../py_modules/tianyi_http.py) `handle_installed_open_folder()` → [tianyi_service.py:6033](../py_modules/tianyi_service.py) `open_installed_folder()`；先校验目录存在再 `_launch_external(install_path)`。
- 卸载 `POST /api/tianyi/installed/uninstall`：handler [tianyi_http.py:333](../py_modules/tianyi_http.py) `handle_installed_uninstall()`（`delete_files` 默认 true、`delete_compatdata` 默认 false）→ 复用 `uninstall_installed_game()`。

卡片显示封面、安装大小、游玩时长（缺失显示 `-`）；点击卡片启动，卡片内按钮分别打开目录/卸载；卸载走自定义 confirm，完成后刷新已安装列表 + 游戏库列表。

**自定义 confirm 弹窗**：`showConfirm()` 记录返回焦点、初始焦点在"确认"(index 1)，`confirmAction()` 关弹窗后执行回调并恢复焦点；Esc/B 等价"取消"。已安装页签的启动入口已按 `mode` 分支：鼠标点击卡片、键盘 Enter、手柄 A 都调用 `launchInstalled()`。

### 5.9 诊断与更新（v0.5.0）

**`GET /api/tianyi/diagnostics`**（JSON，本地只读；handler [tianyi_http.py:348](../py_modules/tianyi_http.py) `handle_diagnostics()` → [tianyi_service.py:6061](../py_modules/tianyi_service.py) `get_diagnostics()`）：`version / python / system / arch / paths(plugin_dir, state_file, log_file, steam_root) / runtime(aria2c,7zz,node 的存在性+大小) / steam(root_exists, proton_tool, droiddeck) / catalog(total, platforms, cover_index_total, with_cover) / tasks(counts,total) / installed(total,bytes,missing_paths) / settings / recent_errors / log_tail`。

- 脱敏：`_redact_text()` 把 HOME 替换成 `~`，并对 `cookie / authorization / token / sessionkey / accesstoken / uid / pwd` 的键值统一替换为 `<redacted>`；
- 日志：`_tail_text(/tmp/freedeckcy.log, 300)` 取末尾 300 行，再筛出含 `ERROR/Exception/失败` 的最近 20 行到 `recent_errors`。

**`GET /api/tianyi/diagnostics/export`**（handler [tianyi_http.py:357](../py_modules/tianyi_http.py) `handle_diagnostics_export()` → [tianyi_service.py:6152](../py_modules/tianyi_service.py) `export_diagnostics()`）：内存生成 zip（`Content-Disposition: attachment; filename="freedeckcy-diagnostics.zip"`），内含：

| 文件 | 内容 |
|---|---|
| `diagnostics.json` | 上面的 JSON（`log_tail` 已移出，避免与 log-tail.txt 重复） |
| `log-tail.txt` | 日志末尾 300 行（同样脱敏） |
| `README.txt` | 诊断包说明 + 提交 issue 指引 |

**`GET /api/tianyi/update-check`**（handler [tianyi_http.py:370](../py_modules/tianyi_http.py) `handle_update_check()` → [tianyi_service.py:6172](../py_modules/tianyi_service.py) `check_update()`）：请求 `https://api.github.com/repos/hulong1989/freedeckCY/releases/latest`（10 s 超时，未认证 GitHub API 有速率限制）；结果 `{ok, current, latest, has_update, url, name, published_at}`，`has_update = _parse_version(latest) > _parse_version(current)`；成功结果在内存缓存 **1 小时**（`_update_cache`），失败返回 `ok: false` + `message`（网络错误/HTTP 状态）。

**公共 helper**：[tianyi_service.py:349](../py_modules/tianyi_service.py) `_tail_text()`（读文件末尾 N 行）、[tianyi_service.py:364](../py_modules/tianyi_service.py) `_redact_text()`（脱敏）、[tianyi_service.py:373](../py_modules/tianyi_service.py) `_parse_version()`（从 `v0.5.0`/`0.5.0-pre` 提取数字元组比较）、[tianyi_service.py:379](../py_modules/tianyi_service.py) `_launch_external()`（优先 `xdg-open`，否则 `gio open`；拉起 `steam://rungameid/...` 或安装目录）。

### 5.10 模拟器注册表与接入平台（v0.6.0 起 / v0.7.0 扩展）

**注册表**：[emulator_manager.py:29](../py_modules/emulator_manager.py) `EmulatorSpec` 描述一个平台（`platform / name / adapter / repo / download_base / assets{arch: 文件名} / archive(appimage|zip) / launch_args / rom_extensions / env_var / min_bytes`），[emulator_manager.py:48](../py_modules/emulator_manager.py) `EMULATORS` 是注册表本体；[emulator_manager.py:115](../py_modules/emulator_manager.py) `get_spec()` / [emulator_manager.py:124](../py_modules/emulator_manager.py) `supported_platforms()` 供服务层与诊断使用。当前接入 3 个平台：

| 平台 | 模拟器 | 版本 / 仓库 | 官方资产（arch → 文件） | 启动参数 | ROM 扩展名 | 环境变量 |
|---|---|---|---|---|---|---|
| gba | mGBA | 0.10.5 / mgba-emu/mgba | appimage：x64 / arm64；**随包内置** | `-f {rom}` | `.gba` | `FREEDECKCY_MGBA_BIN` |
| psp | PPSSPP | 1.20.4 / hrydgard/ppsspp | appimage：anylinux-x86_64 / aarch64；**首次安装按需下载** | `--fullscreen {rom}` | `.iso` `.cso` `.pbp` `.elf` | `FREEDECKCY_PPSSPP_BIN` |
| nds | melonDS | 1.1 / melonDS-emu/melonDS | **zip 内 AppImage**：x86_64 / aarch64；**首次安装按需下载** | `{rom}` | `.nds` `.dsi` `.srl` | `FREEDECKCY_MELONDS_BIN` |

**解析顺序**（[emulator_manager.py:230](../py_modules/emulator_manager.py) `resolve_command()`）：

1. `FREEDECKCY_<PLATFORM>_BIN` 环境变量（spec.env_var，指向可执行文件或 AppImage）；
2. 已解包的 AppRun（[emulator_manager.py:174](../py_modules/emulator_manager.py) `installed_command()`）：`~/.local/share/freedeckCY/emulators/<platform>/<arch>/squashfs-root/`；GBA 兼容旧路径 `emulators/<arch>/squashfs-root/`；
3. 插件内置 AppImage（[emulator_manager.py:185](../py_modules/emulator_manager.py) `bundled_appimage()`；GBA 固定 `defaults/runtime/mgba/<arch>/mGBA.AppImage`，其它平台可放 `defaults/runtime/emulators/<platform>/<arch>/<资产名>`）；
4. 系统命令（[emulator_manager.py:200](../py_modules/emulator_manager.py) `system_command()`：`mgba/mgba-qt`、`ppsspp/PPSSPP/ppsspp-sdl`、`melonds/melonDS`）；
5. Flatpak（[emulator_manager.py:213](../py_modules/emulator_manager.py) `flatpak_command()`；**仅 mGBA** 的 `io.mgba.mGBA`）；
6. 都没有时：[emulator_manager.py:246](../py_modules/emulator_manager.py) `emulator_status()` 返回 `available=True, source="download", requires_setup=True`（附 `asset/url`）；安装时由 [emulator_manager.py:372](../py_modules/emulator_manager.py) `ensure_emulator()` 按需下载。只有该 arch 没有官方资产时才拒绝（`"<模拟器> 暂无 <arch> 官方包"`）。兼容旧接口：[emulator_manager.py:404](../py_modules/emulator_manager.py) `ensure_mgba()`。

**按需下载与解包**（不依赖 FUSE）：

- [emulator_manager.py:322](../py_modules/emulator_manager.py) `_download_asset()`：下载到 `~/.local/share/freedeckCY/emulators/<platform>/<arch>/<资产名>`（HTTP 非 200 / 文件小于 `min_bytes` 会删文件并报错，可重试）；
- zip 资产（NDS）先由 [emulator_manager.py:311](../py_modules/emulator_manager.py) `_extract_zip_appimage()` 解出 AppImage；
- 统一由 [emulator_manager.py:297](../py_modules/emulator_manager.py) `_run_appimage_extract()` 执行 `--appimage-extract` 把 `squashfs-root` 落到平台目录，[emulator_manager.py:352](../py_modules/emulator_manager.py) `_ensure_extracted()` 兜底：解包失败时退回直接运行 AppImage。下载/解包失败会写进安装消息。

**ROM 选择与启动参数**：[emulator_manager.py:409](../py_modules/emulator_manager.py) `find_rom_file()` 按平台扩展名过滤（GBA `.gba`；PSP `.iso/.cso/.pbp/.elf`；NDS `.nds/.dsi/.srl`），优先 `openpath` 同名，其次按扩展名优先级+路径长度选；[emulator_manager.py:436](../py_modules/emulator_manager.py) `create_launch_wrapper()` 按 spec.launch_args 生成 `<install_dir>/launch-freedeckcy.sh`（GBA `exec <mGBA> -f <rom>`、PSP `exec <PPSSPP> --fullscreen <rom>`、NDS `exec <melonDS> <rom>`）。

**安装链路**：计划阶段不再要求模拟器已存在——`_build_install_plan()` 用 `emulator_status(platform, plugin_dir)`，`source=download` 也放行；安装完成后按任务 `platform` 分流，`find_rom_file()` 找 ROM → `ensure_emulator(platform)`（PSP/NDS 在这里首次下载/解包）→ 生成 wrapper → Steam 快捷方式 **Exe=启动脚本、LaunchOptions 带 `freedeckcy:tianyi:<token>`、Proton=none（原生 Linux）**；已安装记录写 `platform/emulator/rom_path/launcher_path`。

**平台准入 / UI / 诊断**：

- 安装计划放行 `pc` 与注册表内平台（当前 `gba/psp/nds`）；**PS1 暂缓**——主流 PS1 模拟器（DuckStation 等）必须由用户自备 BIOS（版权/合规风险、且不同区域 BIOS 校验严格），因此不自动闭环；PS2/PS3 等同样涉及 BIOS/固件，列入 ROADMAP 9.8 待做。注册表外平台仍拒绝（当前后端错误文案仍为"当前只支持 PC 与 GBA（mGBA）资源…"，属待清理的旧文案）。
- 库页允许 `pc/gba/psp/nds` 卡片打开安装确认，弹窗显示 `emulator_info.name`（mGBA / PPSSPP / melonDS）。
- 诊断包 `emulators` 字段遍历 [emulator_manager.py:124](../py_modules/emulator_manager.py) `supported_platforms()`，逐平台输出 available/source/command/name/version/message。

**打包与网络**：只有 GBA 的 mGBA AppImage 随包内置（`make emulator-runtime`）；PSP/NDS 的官方 AppImage 不打进包，首次安装时从 GitHub release 下载（需要网络）；下载失败的安装消息会写明原因，重装/重试可再触发下载。


### 5.11 自动云存档（Ludusavi + gamewatch，v0.8.0）

**Ludusavi 存档清单**：`defaults/ludusavi/manifest.json.gz`（**53,549 款游戏**，gzip 约 2 MB / 未压缩 14 MB，**MIT**），来自 [mtkennerly/ludusavi-manifest](https://github.com/mtkennerly/ludusavi-manifest) 的 YAML，经 [scripts/fetch_ludusavi_manifest.py](../scripts/fetch_ludusavi_manifest.py) 转成精简 JSON 后随包分发（PyYAML 仅构建时需要）；运行时只读本地文件、不联网。可用 `FREEDECKCY_LUDUSAVI_MANIFEST` 覆盖路径（[save_manifest.py:35](../py_modules/save_manifest.py) `manifest_path()`），进程内缓存见 [save_manifest.py:50](../py_modules/save_manifest.py) `load_manifest()`。

**匹配规则**（[save_manifest.py:92](../py_modules/save_manifest.py) `match_manifest()`）：先按 Steam AppID（清单条目的 `steam.id`），再按标题——标题做 [save_manifest.py:31](../py_modules/save_manifest.py) `normalize_title()`（小写、去掉非字母数字/CJK 的字符）并支持用 `[/|｜丨]` 拆段后逐个匹配。

**占位符 → Proton 前缀**（[save_manifest.py:159](../py_modules/save_manifest.py) `resolve_manifest_paths()`）：

| 占位符 | 解析到（Proton 前缀内） |
|---|---|
| `<base>` | 游戏安装目录 |
| `<home>` / `<root>` | `drive_c/users/steamuser` / `drive_c` |
| `<winAppData>` / `<winLocalAppData>` | `AppData/Roaming` / `AppData/Local` |
| `<winDocuments>` / `<winSavedGames>` | `Documents` / `Saved Games` |
| `<winProgramData>` / `<winPublic>` / `<winDir>` | `drive_c/ProgramData` / `drive_c/Users/Public` / `drive_c/Windows` |

- [save_manifest.py:126](../py_modules/save_manifest.py) `_placeholder_bases()` 生成上表前缀；含 `*`/`?`/`[` 的模板用 glob 展开；结果必须存在（目录还需非空），`realpath` 去重，单游戏最多 200 条路径；
- `when` 条件：[save_manifest.py:143](../py_modules/save_manifest.py) `_when_allows_proton()` 认为"无 when 或含 `os: windows`"才处理；**只写 `os: linux`/mac 的条目跳过**（Proton 下按 Windows 路径找）。

**与原有 Proton 扫描合并**：`_collect_cloud_save_candidates()` 先按快捷方式解析出 `compat_user_dir` 与 appid，再用清单匹配/解析；命中时 `source_paths = manifest 路径 + Proton 扫描路径`（去重），`source_strategy` 取 `ludusavi`（清单命中且 Proton 未命中）/`ludusavi+proton`（两者都有）/`proton_prefix`（仅 Proton 扫描）/`install_fallback`（无前缀时按安装目录白名单兜底）；诊断里 `ludusavi = {matched, path_count}`。

**gamewatch 进程检测**（`py_modules/gamewatch.py`）：后台维护每 8 s 调用 `_poll_game_watch()`（`maintenance_tick` 内，[tianyi_service.py:4375](../py_modules/tianyi_service.py) `_poll_game_watch()`）。[gamewatch.py:74](../py_modules/gamewatch.py) `is_game_running()` 优先扫描 `/proc/*/cmdline`（[gamewatch.py:51](../py_modules/gamewatch.py) `_is_running_proc()`，判断 install_path 是否出现在命令行），没有 `/proc` 时回退 [gamewatch.py:58](../py_modules/gamewatch.py) `_is_running_pgrep()`（`pgrep -f`）；[gamewatch.py:81](../py_modules/gamewatch.py) `GameWatcher.poll()` 维护每个 game_id 的运行状态：首次 poll 只建立基线，之后只在状态切换时产出 `start`/`end` 事件，已移除的游戏清空状态（[gamewatch.py:88](../py_modules/gamewatch.py) `poll()`）。服务层**只消费 `end` 事件**（start 事件不触发上传）。

**只上传刚退出的游戏**（[tianyi_service.py:4389](../py_modules/tianyi_service.py) `_maybe_auto_cloud_upload()`）：`end` 事件 → 检查设置 `cloud_save_auto_upload`（默认 **true**）、登录态、当前无云存档上传/自动上传任务、距上次自动上传 ≥ **30 s** 防抖 → 调 [tianyi_service.py:2695](../py_modules/tianyi_service.py) `start_cloud_save_upload(game_ids=[该 game_id])`；上传任务构建候选后按 `game_ids` 过滤（诊断 `filtered_game_ids`），因此不会顺带打包其它游戏。

**指纹去重**：[tianyi_service.py:4424](../py_modules/tianyi_service.py) `_cloud_save_fingerprint()` 对每个游戏的 `source_paths` 递归取文件（最多 **5000** 个），指纹 = `sha256(相对路径|size|mtime_ns …)`；指纹按 `game_key` 持久化到 `state.json` 的 `cloud_save_fingerprints`。上传前计算并与上次比较，相同则**跳过打包/上传**（结果 `status=skipped`、`reason=unchanged`）；上传成功后写回新指纹。

**设置与 UI**：设置项 `cloud_save_auto_upload` 默认 true，贯穿 `tianyi_store`（默认/加载/set_settings）、`main.set_tianyi_settings`、`tianyi_http.handle_settings_set` 与 QAM 设置页「云存档上传 → 游戏退出后自动上传」开关（`src/index.tsx` 的 `ToggleField`）。

**边界**：只做"退出后自动上传"，**没有自动恢复/冲突策略**（恢复仍需手动在 QAM 操作、覆盖前备份）；模拟器（GBA/PSP/NDS）存档写在模拟器自身配置目录（如 `~/.local/share/PPSSPP`），目前不在 Ludusavi/Proton 扫描范围内；指纹只覆盖大小/mtime，不读文件内容；gamewatch 依赖进程命令行包含 install_path（Steam 直接启动脚本通常满足，自定义包装可能漏检）。

---

## 6. 链路 A：从点"安装"到 Steam 库里出现游戏

```text
[Vue 库页]点击卡片
   │ POST /api/tianyi/install/prepare  {game_id 或 share_url}
   ▼
_build_install_plan()
   ├─ share_url 只接受天翼域名（cloud.189.cn / *.189.cn，_is_tianyi_share_url）
   ├─ 查 CSV → share_url / openpath / title / platform
   ├─ platform 校验：pc + 注册表平台（gba/psp/nds）放行；其它平台拒绝
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
   │    │    └─ 模拟器平台：find_rom_file(platform) → ensure_emulator(platform)（PSP/NDS 首次按需下载）
   │    │         → 生成 launch-freedeckcy.sh → 快捷方式 Exe=脚本、LaunchOptions 带 token、Proton=none
   │    └─ auto_delete_package 为真则删除组内全部压缩包
   └─ 任一包失败 → 整组不注册 Steam；已解压文件保留，install_message 汇总
   ▼
Steam 库里出现游戏（写完后备份 + 回读校验；需重启 Steam 生效）
```

**落盘位置**

| 内容 | 路径 |
|---|---|
| 下载的压缩包 | `<download_dir>`（默认 `~/Downloads`） |
| 安装目录 | `<install_dir>`（默认 `<download_dir>/installed`），子目录名 = openpath 第一段 |
| 任务/已装/登录/设置 | `~/.local/share/freedeckCY/tianyi/state.json` |
| aria2 会话 | `~/.local/share/freedeckCY/tianyi/aria2/` |
| 封面缓存 | `~/.local/share/freedeckCY/tianyi/cover_cache.json`（0600，正缓存 7 天 / 负缓存 30 分钟） |
| 运行时二进制 | `defaults/runtime/{aria2,7z}/<arch>/`、`defaults/runtime/node/<arch>/bin/node`、`defaults/runtime/mgba/<arch>/mGBA.AppImage`（GBA 内置） |
| 模拟器解包产物 | `~/.local/share/freedeckCY/emulators/<platform>/<arch>/squashfs-root/`（AppRun，不依赖 FUSE；GBA 兼容旧 `emulators/<arch>/`） |
| 按需下载的模拟器资产 | `~/.local/share/freedeckCY/emulators/<platform>/<arch>/<官方资产名>`（PSP/NDS 首次安装时下载） |
| GBA 启动脚本 | `<install_dir>/launch-freedeckcy.sh`（`exec <mGBA> -f <rom>`） |
| 日志 | `/tmp/freedeckcy.log` |

**关键函数索引（安装链路）**

| 环节 | 代码位置 |
|---|---|
| HTTP 入口 prepare / start | [tianyi_http.py:513](../py_modules/tianyi_http.py) `handle_prepare_install` / [tianyi_http.py:534](../py_modules/tianyi_http.py) `handle_start_install` |
| 安装计划 + 空间探针 | [tianyi_service.py:5133](../py_modules/tianyi_service.py) `_build_install_plan()` |
| 创建下载任务 | [tianyi_service.py:5319](../py_modules/tianyi_service.py) `_create_tasks_from_plan()` |
| 任务状态同步 | [tianyi_service.py:5622](../py_modules/tianyi_service.py) `refresh_tasks()` |
| 安装调度 / 目录级互斥 | [tianyi_service.py:5733](../py_modules/tianyi_service.py) `_schedule_post_process_task()` / [tianyi_service.py:6233](../py_modules/tianyi_service.py) `_post_process_completed_task()` / [tianyi_service.py:6212](../py_modules/tianyi_service.py) `_install_lock_for()` |
| 解压 / 合并 staging | [tianyi_service.py:6936](../py_modules/tianyi_service.py) `_extract_archive_to_dir()` / [tianyi_service.py:6982](../py_modules/tianyi_service.py) `_merge_extracted_content()` |
| 写 Steam 快捷方式 / Proton / 封面 | [steam_shortcuts.py:432](../py_modules/steam_shortcuts.py) `_upsert_shortcut_sync()`、[steam_shortcuts.py:563](../py_modules/steam_shortcuts.py) `_set_proton_mapping_sync()`、[steam_shortcuts.py:813](../py_modules/steam_shortcuts.py) `_apply_grid_assets()` |
| 非 Steam appid | [steam_shortcuts.py:425](../py_modules/steam_shortcuts.py) `_generate_non_steam_app_id()` |
| aria2 下单 | [aria2_manager.py:452](../py_modules/aria2_manager.py) `add_uri()` |
| 分享解析 / 直链 | [tianyi_client.py:1078](../py_modules/tianyi_client.py) `resolve_share()`、[tianyi_client.py:1637](../py_modules/tianyi_client.py) `fetch_access_token()`、[tianyi_client.py:1680](../py_modules/tianyi_client.py) `fetch_download_url()` |
| 后台维护 | [tianyi_service.py:582](../py_modules/tianyi_service.py) `maintenance_tick()` |
| 多分卷归档识别 | [archive_bundle.py:88](../py_modules/archive_bundle.py) `detect_archive_sets()` / [archive_bundle.py:228](../py_modules/archive_bundle.py) `build_bundle_index()` |
| 解压前 settle / 预检 | [tianyi_service.py:6340](../py_modules/tianyi_service.py) `_wait_payload_settled()` / [tianyi_service.py:6384](../py_modules/tianyi_service.py) `_precheck_archive_payload()` |
| 分卷只解主卷 / bundled | [tianyi_service.py:6233](../py_modules/tianyi_service.py) `_post_process_completed_task()` / [tianyi_service.py:6427](../py_modules/tianyi_service.py) `_install_payload()` |
| 坏文件隔离 / 自愈 | [tianyi_service.py:5524](../py_modules/tianyi_service.py) `_quarantine_download_file()` |
| aria2 运行时复用（meta+flock） | [aria2_manager.py:158](../py_modules/aria2_manager.py) `_read_runtime_meta()` / [aria2_manager.py:248](../py_modules/aria2_manager.py) `_attach_existing()` / [aria2_manager.py:205](../py_modules/aria2_manager.py) `_try_acquire_owner_lock()` |
| 直链原地换链 | [aria2_manager.py:510](../py_modules/aria2_manager.py) `replace_uri()` |
| 重启恢复（gid 丢失） | [tianyi_service.py:5488](../py_modules/tianyi_service.py) `_try_recover_task()` / [tianyi_service.py:5413](../py_modules/tianyi_service.py) `_file_matches_expected_size()` / [tianyi_service.py:5544](../py_modules/tianyi_service.py) `_readd_task_download()` |
| 分卷分组安装 | [tianyi_service.py:5443](../py_modules/tianyi_service.py) `_install_group_members()` / [tianyi_service.py:5459](../py_modules/tianyi_service.py) `_maybe_schedule_group_post_process()` / [tianyi_service.py:6427](../py_modules/tianyi_service.py) `_install_payload()` / [tianyi_service.py:6522](../py_modules/tianyi_service.py) `_finalize_group_install()` |
| 下载完整性校验 | [tianyi_service.py:5424](../py_modules/tianyi_service.py) `_verify_downloaded_file()` |
| 归档 `7z t` 校验 | [seven_zip_manager.py:66](../py_modules/seven_zip_manager.py) `test_archive()` |
| 校验失败自动重下 | [tianyi_service.py:6405](../py_modules/tianyi_service.py) `_schedule_archive_repair()` / [tianyi_service.py:208](../py_modules/tianyi_service.py) `ArchiveRepairScheduled` |
| 失败任务重试 | [tianyi_service.py:5816](../py_modules/tianyi_service.py) `retry_task()` |
| 卸载预览 / compatdata 回收 | [tianyi_service.py:4851](../py_modules/tianyi_service.py) `preview_uninstall()` / [tianyi_service.py:4841](../py_modules/tianyi_service.py) `_can_remove_compatdata_dir()` / [steam_shortcuts.py:165](../py_modules/steam_shortcuts.py) `find_compatdata_dirs()` |
| aria2 全量列表（恢复用） | [aria2_manager.py:534](../py_modules/aria2_manager.py) `list_downloads()` |

**几个容易误解的点**

- **"不限速"的真相**：全仓库没有任何 `--max-*-limit`，所以是"不设上限"而不是加速。实际速度取决于天翼直链和单文件分片数（默认 `split=16`，aria2 全局并发 3）。
- **不转存**：分享资源不会保存到用户网盘，直接拿直链给 aria2 下载（这点和很多"转存类"工具不同）。
- **`freedeckcy:tianyi:<game_id>`** 只是写在 LaunchOptions 里的标记，本插件没有读取它的运行时代码（时长统计走 Steam 全局事件，见 7.3）。
- **exe 定位是启发式**：CSV 的 `openpath` 精确时靠它；不精确时靠"叶子文件名搜索"和"目录里第一个可执行文件"，这是很多"装完点了没反应"的根源。
- **写 `shortcuts.vdf` 必须重启 Steam** 才能看到。
- **error 任务不会自动重试安装**：先移除出错的任务；分卷场景下移除失败的那一包后，剩余已完成的分卷会继续安装（见 6.2）。

### 6.1 重启恢复：gid 变化与直链过期

插件重载现在会附着到仍存活的 aria2（见 6.4），**gid 通常不变**；但**设备重启**后 aria2 会话重建、gid 会变，直链也可能过期。`state.json` 里存的旧 gid 查不到时，`refresh_tasks()` 对查询失败的任务按以下顺序恢复（[tianyi_service.py:5488](../py_modules/tianyi_service.py) `_try_recover_task()` / [tianyi_service.py:5413](../py_modules/tianyi_service.py) `_file_matches_expected_size()` / [tianyi_service.py:5544](../py_modules/tianyi_service.py) `_readd_task_download()`）：

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

注意：② 只比对文件大小，不是哈希校验；③ 换链/重加后会继续走下载/续传，能复用的分片尽量复用；旧会话损坏（aria2 控制文件错误/截断）时先隔离半成品文件再重试一次。

### 6.2 分卷 / 多包安装语义

同一安装计划（`install/prepare` 返回的多个文件）在创建任务时共享一个 `group_id`，`group_total` 记录包数。**"代表任务" = 组内 `created_at` 最早的那个**（[tianyi_service.py:5443](../py_modules/tianyi_service.py) `_install_group_members()` 按 `(created_at, task_id)` 排序），Steam 注册与已安装记录都以它为准。

- **下载阶段**：`_maybe_schedule_group_post_process()` 只在整组任务全部 `complete` 后才调度安装。
  - 组内某包 `error`：不安装；已完成的包显示"同一安装计划中有分卷下载失败，移除失败任务后可继续安装"；
  - 用户移除失败任务后（`removed` 状态不参与分组），剩余的 complete 分卷会被重新调度安装。
- **安装阶段**：逐包解压到同一目标目录（目录级互斥串行），全部成功才 [tianyi_service.py:6522](../py_modules/tianyi_service.py) `_finalize_group_install()`：
  - 写一条已安装记录，`size_bytes` = 组内各包 `file_size` 之和；
  - 只注册一次 Steam 快捷方式 / Proton / 封面（用代表任务）；
  - `auto_delete_package` 为真时删除组内全部压缩包；
  - 多分卷归档只解主卷、其余标 `bundled`（见 6.3）。
- **安装阶段失败**：任一包失败则整组不注册 Steam，已解压的文件保留；`install_message` 单文件保留具体原因、多文件汇总为"x/y 个文件包出错"，用户需移除出问题的任务后重新发起安装/下载。

### 6.3 多分卷归档（.7z.001 / .part1.rar / .z01+zip …）

`py_modules/archive_bundle.py`（参考 v0.6 的 `archive_detector.py` 精简实现）识别 6 类分卷命名：

| 类型 | 示例 | 主卷（入口卷） |
|---|---|---|
| 数字后缀 7z | `game.7z.001`、`game.7z.002` | `.001` |
| 数字后缀 zip/rar | `game.zip.001`、`game.rar.001` | `.001` |
| RAR part | `game.part1.rar`、`game.part2.rar` | `.part1.rar` |
| ZIP 分卷 | `game.z01` + `game.zip` | `game.zip` |
| RAR 老式分卷 | `game.r00` + `game.rar` | `game.rar` |

安装时的处理：

- `detect_archive_sets()` 从**同一 group 的所有已下载文件**里识别分卷集合，`build_bundle_index()` 给出"路径 → (集合, 是否主卷)"；
- `missing_parts` 非空（如缺 `.002`）→ 整组安装失败，`install_message` 列出缺失文件名（最多 3 个），不会拿不完整的分卷硬解压；
- 只有主卷走解压，其余分卷任务 `install_status` 标为 **`bundled`**、消息"分卷文件，由主卷统一解压"，安装完成后保持该语义（不会改成 installed）；
- 解压时 `_extract_archive_to_dir(..., force_seven_zip=True)` 强制走 7z——分卷不能按扩展名交给 `shutil`；
- 解压前按**所有分卷大小之和**估算空间。

### 6.4 aria2 运行时复用（meta + flock）

v0.6 用 `aria2.runtime.json` 记录 aria2 的 RPC 地址/secret/pid，并用 flock 保证同目录只有一个实例负责启动；本仓库采用同样的思路（文件名 `aria2-runtime.json` / `aria2-runtime.lock`，落在 `~/.local/share/freedeckCY/tianyi/aria2/`，与 `aria2.session`、`aria2.log` 同目录）：

```text
ensure_running()
   ├─ ① 内存里有 runtime 且进程/PID 存活 → 直接 getVersion 复用
   ├─ ② 读 aria2-runtime.json：pid 存活且 getVersion 通过 → 附着（attached=true）
   │      → 插件重载后 gid 不变，在途任务继续走
   ├─ ③ 拿不到 flock（其它插件实例正在启动）→ 短暂轮询附着，不重复起进程
   └─ ④ 获得 flock 且无可用实例 → 启动 aria2 并写 meta（owned=true）
```

- `stop()` 只停**自己 owned** 的实例：插件卸载时不会杀掉仍被其它实例复用的 aria2；
- meta 写入用临时文件 + `os.replace` 原子替换；启动失败/停止时清 meta 释放锁；
- 排查：`ls ~/.local/share/freedeckCY/tianyi/aria2/` 有 `aria2-runtime.json`/`aria2-runtime.lock`、`aria2.log`（启动参数含 `--log`）；这两个文件可判断"当前实例是否可附着"。

### 6.5 Steam 写入策略（token / 增量 / 备份 / 回读）

- **token 去重**：新条目同时写 `LaunchOptions="freedeckcy:tianyi:<token>"` 与 `DevkitGameID=<token>`；匹配时读 `DevkitGameID` 或旧 `LaunchOptions` 任一（[steam_shortcuts.py:413](../py_modules/steam_shortcuts.py) `_shortcut_tokens()`），避免用户手动改启动项后重复建条目；启动前缀常量 `FREEDECKCY_LAUNCH_PREFIX`。
- **差异写入**：目标条目字段全部一致且文件存在时返回 `action="unchanged"`，不重写文件。
- **写前备份**：`shortcuts.vdf` / `config.vdf` 写入前复制为 `*.freedeckcy-bak-<YYYYmmdd_HHMMSS>`（[steam_shortcuts.py:380](../py_modules/steam_shortcuts.py) `_backup_file()`），同类备份只保留最近 **12** 份；`config.vdf` 的 Proton 映射改写同样先备份。
- **Proton 工具解析与设置（v0.4.0）**：设置项 `proton_tool`（默认 `auto`）落在 [tianyi_store.py:60](../py_modules/tianyi_store.py) `TianyiSettings`；RPC/HTTP 透传为 [main.py:210](../main.py) `set_tianyi_settings()`、[tianyi_http.py:379](../py_modules/tianyi_http.py) `handle_settings_get()` / [tianyi_http.py:388](../py_modules/tianyi_http.py) `handle_settings_set()`，服务层 [tianyi_service.py:5014](../py_modules/tianyi_service.py) `update_settings()`；`GET /api/tianyi/settings` 额外返回 `proton_tool_resolved` / `droiddeck_detected`（[tianyi_service.py:2428](../py_modules/tianyi_service.py) `get_settings()`）。写快捷方式时 [steam_shortcuts.py:1025](../py_modules/steam_shortcuts.py) `add_or_update_tianyi_shortcut(proton_tool=...)`：`auto` → `detect_proton_tool()`，`none`/`skip`/`disabled` → 跳过映射，其它值直接当工具名；最终由 `_set_proton_mapping_sync()` 写入 `config.vdf` 的 `CompatToolMapping`。
- **写后校验**：`shortcuts.vdf` 写完重新读回，确认 token 真的落盘，否则返回失败（防"以为写成功"）。
- **compatdata 用户名打分**：`find_compat_user_dir()` 先试 `steamuser` / `deck` / `root`，再对自定义 Wine 用户名按 `AppData`(+3)/`Documents`(+2)/`Saved Games`(+2) 打分挑选（参考 v0.6 同类实现）。

### 6.6 归档校验与自动重下（`7z t`，best-effort）

v0.1.1 起，解压前会先用 `7z t` 做完整性校验（`seven_zip.test_archive()`，默认超时 900 s）：

- **best-effort 边界**：7z 找不到、或 7z 无法执行（例如 macOS 上跑 Linux 版 7zz 会 `Exec format error`）时，返回 `(True, "跳过校验: …")`，**不阻断安装**——后续解压阶段才会暴露真实错误。所以"没有 7z"不等于"不能装"，但解压仍需要可用 7z。
- **只有真正校验失败才自动修复**（7z 返回非 0 或超时）→ `_schedule_archive_repair()`：
  1. `aria2.remove(gid)` 停掉旧任务；
  2. `_quarantine_download_file(task, "archive-invalid")` 把坏包改名为 `*.freedeckcy-archive-invalid-<ts>`（避免 aria2 续传垃圾数据）；
  3. 用原直链重新下载（`changeUri` 原地换链优先，失败再 `addUri`）；
  4. 任务置 `status=waiting`、`install_status=waiting`、`post_processed=false`，**不注册 Steam**。
- 每任务每进程只自动重下一次；重下完成后后台维护会再次进入安装。第二次仍校验失败 → `install_status=failed`，改用任务行「重试」按钮（见 6.7）。
- 日志关键字：`Archive validation failed, re-download scheduled`；大包 `7z t` 会多读一遍文件，属预期开销。

### 6.7 任务重试（v0.1.1）

QAM 任务行在 `status=error` 或 `install_status=failed` 时显示「重试」，走 `retry_task()`：

1. 重置状态：`post_processed=false`、`install_status=pending`、清空 `_readd_attempts` / `_task_sync_misses`，让"每任务每进程一次"的限制不再挡住人工重试；
2. **文件已完整**（`_file_matches_expected_size()` 通过）→ 直接判 `complete` 并重新调度安装，**不重新下载**；
3. **文件不完整/缺失** → 重新获取直链（`changeUri`/`addUri`）回到下载队列；取直链失败（如登录态失效）→ 任务改 `install_status=failed` 并提示"重试失败：无法重新获取下载直链"；
4. 重试是显式人工动作，后台维护不会自动触发。

### 6.8 卸载与 Proton 前缀回收（v0.1.1）

QAM 已安装列表点「卸载」时：

1. 先调 `preview_tianyi_uninstall` → `preview_uninstall()`：返回安装目录占用、`compatdata/<appid>` 占用（`find_compatdata_dirs()` 跨所有 Steam 库）、解析出的 Steam AppID（`_resolve_record_app_id()`：记录里的 appid，缺失时回查快捷方式）；
2. UI 显示"安装目录占用 / Proton 前缀另占 X"，三按钮：**取消** / **仅删游戏文件**（默认，`delete_compatdata=false`） / **连 Proton 前缀一起删**（检测到前缀时才出现，`delete_compatdata=true`）；
3. 卸载顺序：删除安装目录（`_can_remove_install_path` 安全校验）→ 可选删除 Proton 前缀 → 移除已安装记录 → 清理 Steam 快捷方式/映射/封面 → 清会话；
4. **compatdata 路径安全**：`_can_remove_compatdata_dir()` 只允许 `<library>/steamapps/compatdata/<appid>` 结构且拒绝符号链接；只删 `find_compatdata_dirs()` 返回、且 appid 与记录一致的目录；
5. 返回 `compatdata: {requested, app_id, paths, removed_paths, freed_bytes}`；未删/失败写入顶部 `warning`；
6. **默认不删**：避免"只想重装游戏"时把 Proton 前缀里的存档/配置一起删掉。

---

## 7. 链路 B：云存档

### 7.1 上传（手动触发，QAM 设置页）

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

### 7.2 恢复（四步，带冲突确认）

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

**关键函数索引（云存档）**

| 环节 | 代码位置 |
|---|---|
| 多库 compatdata 定位 | [steam_shortcuts.py:184](../py_modules/steam_shortcuts.py) `find_compat_user_dir()` / [steam_shortcuts.py:130](../py_modules/steam_shortcuts.py) `_steam_library_paths()` |
| 上传入口 | [tianyi_service.py:2695](../py_modules/tianyi_service.py) `start_cloud_save_upload()` |
| 上传后台任务 | [tianyi_service.py:4564](../py_modules/tianyi_service.py) `_run_cloud_save_upload_task()` |
| 候选目录扫描 | [tianyi_service.py:3931](../py_modules/tianyi_service.py) `_collect_cloud_save_candidates()` |
| 打包 + manifest | [tianyi_service.py:4455](../py_modules/tianyi_service.py) `_archive_single_game_saves()` |
| 云端上传 / 列版本 / 下载 | [tianyi_client.py:2076](../py_modules/tianyi_client.py) `upload_archive_to_cloud()`、[tianyi_client.py:2113](../py_modules/tianyi_client.py) `list_cloud_archives()`、[tianyi_client.py:2164](../py_modules/tianyi_client.py) `download_cloud_archive()` |
| 恢复四步 | [tianyi_service.py:2751](../py_modules/tianyi_service.py) `list_cloud_save_restore_options()`、[tianyi_service.py:2865](../py_modules/tianyi_service.py) `list_cloud_save_restore_entries()`、[tianyi_service.py:2952](../py_modules/tianyi_service.py) `plan_cloud_save_restore()`、[tianyi_service.py:3182](../py_modules/tianyi_service.py) `apply_cloud_save_restore()` |

### 7.3 游玩时长（独立小链路）

- `SteamClient.Apps.RegisterForGameActionStart/End` 全局监听 → `record_tianyi_game_action`（[src/index.tsx:836](../src/index.tsx) `installGlobalGameActionReporter()`）→ `TianyiService.record_game_action()`：重复 start 且间隔超过 5 秒视为上一局结束，单局封顶 12 小时，重启后能恢复会话。
- 库游戏详情页：用 `routerHook.addPatch("/library/app/:appid")` **patch Steam 库页面的 `renderFunc` 和组件 `type`**，把"我的游玩 / 主线 / 总时长（HowLongToBeat）"插进去（[src/index.tsx:1390](../src/index.tsx) `installLibraryPlaytimePatch()`）。这是全项目最"黑魔法"的一段，依赖 Steam UI 内部结构。

---

## 8. 登录：四种方式，UI 只走二维码

| 方式 | 实现 | 现状 |
|---|---|---|
| **二维码**（UI 唯一入口） | Python 侧 aiohttp 直接调 `open.e.189.cn` 的二维码接口，抓取二维码 PNG 代理给页面；1.6 s 轮询状态；成功后从 cookie jar 拼 cookie 串存 `state.json` | 在用，最稳 |
| **CDP 抓取** | 连 Steam 内置浏览器 / Chromium 的调试端口（8080、9222），用 DevTools 协议读 cookie | 旧方案，API 还在（`/api/tianyi/login/capture/*`），前端已不调用 |
| **Cookie DB 直读** | 读 `~/.local/share/Steam/config/htmlcache/Cookies` 等 SQLite，过滤 `189.cn` 域 | 旧方案；`v10/v11` 加密的 cookie 直接跳过 |
| 手动粘贴 cookie | `POST /api/tianyi/login/manual` | 兜底 API 保留 |

代码位置：二维码 [tianyi_service.py:1325](../py_modules/tianyi_service.py) `start_qr_login()` / [tianyi_service.py:1411](../py_modules/tianyi_service.py) `poll_qr_login()`；CDP [tianyi_service.py:7749](../py_modules/tianyi_service.py) `_collect_tianyi_cookie_from_cdp()`；Cookie DB [tianyi_service.py:7948](../py_modules/tianyi_service.py) `_collect_tianyi_cookie_from_cookie_db()`；手动 cookie [tianyi_http.py:151](../py_modules/tianyi_http.py) `handle_login_manual()`。

注意：**cookie 从不经过浏览器回传**，登录桥页面只负责显示二维码和状态，全程由 Python 侧完成。

---

## 9. 天翼云盘协议要点

| 环节 | 做法 |
|---|---|
| 下载入口校验 | `_build_install_plan` 只接受天翼域名（`cloud.189.cn`、`h5.cloud.189.cn`、`api.cloud.189.cn` 或 `*.189.cn`）的 `share_url`，防止本地页面把任意 URL 塞进下载链路 |
| 分享解析 | `checkAccessCode`（提取码换 shareId）→ `getShareInfoByCodeV2`（拿 fileId/isFolder）→ `listShareDir`（列目录，pageSize=60）。同一接口准备多套"请求画像"（host × GET/POST/form），逐个试；都失败再抓分享落地页 HTML 里抠 shareId；最后 Node 兜底。签名头只有 `Sign-Type:1`，**鉴权完全靠 Cookie** |
| 直链 | `api.cloud.189.cn/open/file/getFileDownloadUrl.action`，签名 = `MD5(AccessToken=..&Timestamp=..&dt=1&fileId=..&shareId=..)`，头带 `Accesstoken/Signature/Timestamp` |
| accessToken | 从 `ssoH5` 的 302 跳转 URL 里提取 |
| sessionKey | 先试 `getUserBriefInfo`，失败走 `getSessionForPC` |
| 上传 | **全部交给 Node**：参数用 AES-128-ECB 加密成 `params`，AES 密钥用 RSA-PKCS1 加密放进 `EncryptionText`，`SessionKey/Operate/RequestURI/Date/params` 参与签名；10 MB 分片 `initMultiUpload → getMultiUploadUrls → PUT → commitMultiUploadFile`，`sliceMd5` 是各片 MD5 大写拼接再 MD5 |
| 稳定性 | Python 失败 → Node 兜底；`node` 优先内置运行时 `defaults/runtime/node/<arch>/bin/node`，其次 PATH，且会清掉 Decky 注入的 `LD_LIBRARY_PATH/_MEIPASS2/PYTHONHOME` 避免 libcrypto 冲突 |

**风险**：全是未公开接口 + 私有签名，官方一改就整体失效，且可能触发风控 / 封号。

---

## 10. 数据与状态

`~/.local/share/freedeckCY/tianyi/state.json`（**每次全量重写**，原子替换临时文件；数据类与读写见 [tianyi_store.py:51](../py_modules/tianyi_store.py) 起、[tianyi_store.py:204](../py_modules/tianyi_store.py) `load()`、[tianyi_store.py:284](../py_modules/tianyi_store.py) `save()`）：

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

- 任务终态保留 **7 天**（`TASK_RETENTION_SECONDS`）。
- 设置另有一份备份：Decky settings + `~/.local/share/freedeckCY/settings.json`，防止插件目录被清。
- 游戏目录每次 `initialize()` 全量读 CSV 进内存（约 2800 条，开销可忽略）。
- 云存档恢复的覆盖备份是**就地改名**的 `*.freedeckcy-bak-<YYmmdd_HHMMSS>`，不会自动清理，失败后可手工找回。
- `tasks[]` 用 `group_id` 分组：同一安装计划（分卷/多包）的多个文件共享 `group_id` 与 `group_total`；`file_size` 是清单里的预期字节数，用于下载完整性校验与会话恢复。
- `install_status` 取值：`pending` / `installing` / `installed` / `failed` / **`waiting`**（`7z t` 校验失败已安排自动重下，或人工重试排队中）/ **`bundled`**（多分卷归档的非主卷，由主卷统一解压，安装完成后保持该值）。
- 状态文件含登录 Cookie：保存时状态目录 chmod **0700**、`state.json` 及临时文件 chmod **0600**（`_chmod_private()`，失败不阻断）。

---

## 11. 值得学的 6 个设计

1. **面板三档轮询 + 后端二次节流**：前端 active 900 ms / idle 6 s / background 30 s；后端再按"有无活跃任务"把任务刷新窗口分成 1 s/10 s/30 s，安装列表 20 s/60 s/120 s，并且有缓存和超时降级。轮询路径上**不做端口探测和网络校验**，耗时的刷新有窗口节流。
2. **重活全部异步化 + 后台维护 + 分组收口**：解压、aria2 控制、store 写盘都走 `asyncio.to_thread`；下载完成后的安装调度成后台任务并按 task_id 去重；`main.py` 启动时先跑一次、之后按 `config.MAINTENANCE_INTERVAL_SECONDS` 周期调用 `maintenance_tick()`，保证**面板没打开时也能自动安装**；同组任务以 `group_id` 收口（整组下完才装、只注册一次 Steam），并用任务列表指纹避免每轮维护都重写 `state.json`。
3. **两段式安装**：`prepare`（只探测：文件清单、剩余空间、Proton 评级）→ `start`（真正下单）。用户能在确认前看到"要下多大、装完多大、盘够不够"。
4. **解压到 staging 再合并**：先解到临时目录，再合并进目标目录，并自动去掉压缩包里"套一层同名文件夹"的情况。这是处理第三方打包资源非常实用的技巧。
5. **云存档带 manifest**：不裸传文件，而是打包 + `manifest.json` 记录源路径、条目、游玩时长。恢复时才能做**路径推断**、**冲突探测**、**时长合并**（取较大值，不降级覆盖）和**覆盖前自动备份**。
6. **降级链与自愈**：Python 解析失败 → Node 解析；内置运行时优先 → 系统命令兜底；7z 失败 → `shutil.unpack_archive`；缓存刷新失败 → 用旧缓存；aria2 会话丢失 → 按路径认领 / 原直链重新加入，直链过期 → `changeUri` 原地换链；文件大小不符或 `7z t` 校验失败 → 隔离坏文件后自动重下一次；仍失败可人工「重试」。

---

## 12. 问题清单

> 本清单覆盖 2026-11 三轮工程补全 + freedeckCY v0.1.1 四件套 + v0.2.0 目录/封面后的状态；标注"（已修复）"的条目已落地，其余为当前仍存在的**已知问题**。维护建议见 [ROADMAP.md](ROADMAP.md)。

### P0：会直接导致"装不上 / 丢数据 / 被利用"

1. ~~安装强依赖前端轮询~~（`main.py` 主循环原来只有 `sleep(60)`）：**本次补全已修复**——新增 `TianyiService.maintenance_tick()`，插件启动时先执行一次，之后按 `config.MAINTENANCE_INTERVAL_SECONDS`（8 s）周期执行，不依赖面板是否打开。
2. ~~`post_processed` 在解压之前就置 `True`~~：**本次补全已修复**——改为安装工作结束后才置真；解压中崩溃/插件重启后，后台维护会重新拾起未处理任务。
3. ~~多文件游戏并发解压到同一目录、`installed_games` 记录互相覆盖~~：**本次补全已修复**——按安装目录加 `asyncio.Lock` 串行，并按 `group_id` 整组一次性安装、只写一条记录（体积为各包之和）、只注册一次 Steam。
4. ~~云存档恢复先删后拷且无备份；路径包含判断用 `startswith` 可被 `../` 逃逸~~：**本次补全已修复**——覆盖前就地改名 `*.freedeckcy-bak-<时间戳>`（结果回传 `backed_up_files`），路径边界改用 `_is_within_dir()`（commonpath）。
5. ~~本地 HTTP 无鉴权、CORS 全开、请求体上限 1 GB、`share_url` 可被塞任意地址~~：**本次补全已修复**——Host/Origin 校验 + `Sec-Fetch-Site: cross-site` 拒绝；`client_max_size` 收到 **16 MB**；`share_url` 只接受天翼域名；`state.json` 目录 0700 / 文件 0600。

### P1：容易踩的坑

6. ~~空间只算压缩包、不算解压后~~：**本次补全已修复**——安装计划给出解压后体积估算，解压前硬检查剩余空间（压缩包 × 1.05，多分卷按分卷总和）。
7. ~~插件/设备重启后 aria2 gid 丢失，任务卡住或被误判失败~~：**本次补全已修复**——aria2 运行时元数据 + flock（插件重载可附着存活实例，gid 不变）+ 按路径认领 / 原直链 `changeUri` 原地换链（失败再 addUri）/ 连续 5 次才 error 的恢复链（见 6.1/6.4）。
8. ~~下载完整性无校验~~：**本次补全已修复**——按清单 `file_size` 校验；不一致先隔离坏文件并自动重下一次（自愈），仍失败才 error；解压前再做空文件 / HTML 错误页预检（见链路 A 时序图与关键函数索引）。
9. ~~多分卷归档被当成普通压缩包逐个解压~~：**本次补全已修复**——`archive_bundle.py` 识别 6 类分卷，只解主卷、其余标 `bundled`；缺分卷整组失败并列出缺失文件。
10. ~~Steam 配置写入无备份、重复条目、静默失败~~：**本次补全已修复**——`DevkitGameID` token 去重、字段无变化不重写（`unchanged`）、写前备份保留 12 份、写后 strict 回读（见 6.5）。
11. 每个文件一个 aria2 任务；aria2 全局并发 3，多任务会互相排队；没有整包 hash 校验与失败自动重试。（已知问题）
12. `backend/tianyi_cloud_upload.js` 优先于 `.cjs`，**只有文件不存在才会降级**；node 版本不满足 ESM 时直接失败（`.cjs` 只实现 upload）。（已知问题）
13. `config.vdf` 用正则文本改写，运行中的 Steam 可能回写覆盖（已写前备份，可用 `*.freedeckcy-bak-*` 找回）。（已知问题）
14. ~~Steam 根目录只认两处硬编码路径，Flatpak / SD 卡非默认库失效~~：**本次补全已修复**——`FREEDECKCY_STEAM_ROOT`、Flatpak 路径、`libraryfolders.vdf` 全库扫描（与 v0.6 的"仅主库"实现相反，不回退）。
15. ~~仓库缺 aria2/7z 二进制；云存档必须系统有 node~~：**本次补全已修复**——`make runtime` 一键补齐，代码优先 `defaults/runtime/`，系统命令仅兜底。
16. ~~前后端契约漂移：`/api/tianyi/state` 丢 settings、`panel_state.library_url` 恒为空串~~：**本次补全已修复**。
17. 分享解析只取第一页 60 条、不递归，超多文件的分享会漏。（已知问题）
18. 分卷识别只覆盖常见 6 类命名；非标准命名（如自定义 `.001` 前缀/混合分卷）仍可能被当普通文件处理。（已知问题）
19. ~~安装前没有归档完整性校验，坏包要解压到一半才失败~~：**v0.1.1 已修复**——解压前 `7z t` 校验（best-effort，7z 不可用时跳过），失败隔离并自动重下一次（见 6.6）。
20. ~~卸载只删游戏目录，Proton 前缀长期占盘~~：**v0.1.1 已修复**——卸载预览显示占用，可选"连 Proton 前缀一起删"（默认不删、路径安全校验，见 6.8）。

### P2：工程性

21. `tianyi_service.py` 约 8200 行、单类 100+ 方法；`src/index.tsx` 约 100 KB / 3000 行单文件。已补 `tests/`（289 个用例）与 GitHub Actions CI，但**仍无 Python 类型检查**（mypy/ruff 未接入，见 ROADMAP）。
22. 全硬编码中文，**无 i18n**；大量 `unknown` / `as` 断言绕过 TS 类型。（已知问题）
23. ~~`clear_freedeckcy_tasks.sh` 写死 `/home/deck`~~：**本次补全已修复**——改用 `$HOME` 并支持 `FREEDECKCY_STATE_FILE` 覆盖。
24. 日志路径仍写死 `/tmp/freedeckcy.log`，不可配置（已轮转，不再是无限增长）。（已知问题）
25. ~~日志无限增长 / `basicConfig(force=True)` 覆盖 Decky 日志配置~~：**本次补全已修复**——改为 `RotatingFileHandler`（5 MB × 3），`propagate=False`。
26. ~~`state.json` 以默认文件权限落盘（内容含登录 Cookie）~~：**本次补全已修复**——状态目录 0700、文件 0600。
27. ~~aria2 启动参数偏弱（预分配慢、无超时/重试/日志/证书）~~：**本次补全已修复**——`--file-allocation=none`、connect 10 s / read 60 s、retry-wait 5 / max-tries 10、`--log aria2.log`、自动选 `--ca-certificate`，下载请求带 UA/Referer。
28. ~~Steam 快捷方式/Proton 写入无法回滚~~：**本次补全已修复**（同第 10 条，写前备份 + 回读；但运行中的 Steam 仍可能覆盖，见第 13 条）。
29. Proton 用户目录已支持自定义用户名打分兜底，但极端布局（多前缀、非常规用户名）仍可能漏扫。（已知问题）
30. ~~失败任务只能移除后重新下载~~：**v0.1.1 已修复**——任务行「重试」按钮 + `retry_task()`（文件完整时直接重装，见 6.7）。
31. ~~排障依赖手工拼命令~~：**v0.1.1 已修复**——`make doctor` / `scripts/doctor.sh` 一条命令输出运行时、Steam、state、日志、端口、网络诊断（只读，见 DEVELOPMENT §6.6）。
32. ~~资源目录只有 PC 单列、封面每次联网解析、无分类/平台维度~~：**v0.2.0 / v0.3.0 已修复**——目录补齐到 **7084 条 / 11 平台**，内置 `cover_index.csv`（3470 行，合并后 6823 条有封面），封面按"静态 → 磁盘缓存 → Steam 商店 → ProtonDB"解析并缓存 7 天，库页有平台 + 分类双筛选条（见 5.5）。
33. ~~非 PC 资源只可浏览、无法安装~~（模拟器未集成）：**部分修复（v0.6.0 / v0.7.0）**——GBA/PSP/NDS 已可安装/启动（mGBA / PPSSPP / melonDS，原生 Linux 快捷方式，见 5.10）；其它模拟器平台（PS1/PS2/PS3/3DS/FC/MD/Switch）仍只可浏览，前端提示 + 后端拒绝（ROADMAP 9.8 剩余部分）。（已知限制）
34. ~~目录分类混入平台名（GBA/Switch…）、分类筛选里出现平台名、数据无自动体检~~：**v0.3.1 已修复**——`normalize_categories()` 加载时清洗 + 606 行数据已改写（「模拟器」606 条），`validate_catalog.py --strict` 进 CI（见 5.6）。
35. **DroidDeck 适配未真机验证**：v0.4.0 按 DroidDeck 源码/ARM64 运行时结构适配（未在真机完整验证）；FEX/ARM Proton、Android 存储映射可能影响结果；**GBA/PSP/NDS 已可安装/启动**，其它模拟器平台仍只可浏览（见 [DROIDDECK.md](DROIDDECK.md) / ROADMAP 9.8）。（已知限制）
36. **模拟器闭环的边界（v0.7.0）**：PS1 因 BIOS 依赖暂缓，PS2/PS3/3DS/FC/MD/Switch 待做；PSP/NDS **首次安装需要联网**从 GitHub release 下载官方 AppImage（失败会写进安装消息，可重试）；仅识别注册表内 ROM 扩展名，**不含 BIOS/存档管理**；所有 AppImage 都会解包到 `~/.local/share/freedeckCY/emulators/` 多占一份空间；ARM64/DroidDeck 上 PSP/NDS/mGBA 尚未真机验证。（已知限制）
37. **自动云存档的边界（v0.8.0）**：只对 gamewatch 检测到"退出"的游戏自动上传，且 gamewatch 依赖进程命令行包含 install_path（自定义 wrapper 可能漏检）；没有自动恢复/冲突策略；模拟器（GBA/PSP/NDS）存档在模拟器配置目录，暂未纳入；上传前指纹只看相对路径+size+mtime（最多 5000 文件），不读内容；`cloud_save_auto_upload` 默认开启（可在 QAM 关闭）。（已知限制）

---

## 13. 与 v0.6 的对齐

作者 v0.6 发行版（解包于本地 `0.6/freedeck-plugin`，**只读参考、不随本仓库分发**）在下载管线、Steam 写入、模拟器与资源池上比本仓库完整得多。本轮只借鉴与"稳定下载 / 安全写 Steam"直接相关的少数能力；其余能力要么不采纳、要么列入 [ROADMAP.md](ROADMAP.md)。

### 13.1 已采纳（三轮 + v0.1.1 ~ v0.6.0）

| 能力 | v0.6 出处 | 本仓库实现 |
|---|---|---|
| 多分卷归档识别（6 类命名、主卷、缺失分卷） | `archive_detector.py` | `py_modules/archive_bundle.py`；只解主卷、其余 `bundled`（见 6.3） |
| 解压前收紧 | `archive_validator.py` 预检思路 | `_wait_payload_settled()`（等 `.aria2` 释放、大小稳定两次）+ `_precheck_archive_payload()`（空文件/HTML）；v0.1.1 起再补 `7z t` best-effort 校验（见 6.6） |
| `7z t` 解压前校验 + 自动重下（v0.1.1 落地） | `archive_validator.test_archive` 思路 | `seven_zip.test_archive()`（7z 不可执行时跳过）+ `_schedule_archive_repair()`（见 6.6） |
| compatdata 卸载清理（v0.1.1 落地） | `uninstall_installed_game(delete_compatdata=)` | `preview_uninstall()` + `find_compatdata_dirs()` + `_can_remove_compatdata_dir()`（见 6.8） |
| 模拟器注册表 / GBA+PSP+NDS（v0.6.0 起，v0.7.0 扩展） | `emulator_adapters.py`（Eden/DuckStation/PCSX2/PPSSPP/RPCS3/mGBA/Lime3DS/melonDS/Nestopia/BlastEm/MAME） | `emulator_manager.py` 的 `EmulatorSpec` 注册表：GBA=mGBA（内置）、PSP=PPSSPP（按需下载）、NDS=melonDS（按需下载 zip）、解包/ROM 分页查找/启动脚本/原生 Steam 快捷方式（见 5.10）；PS1（BIOS）与其余平台未做 |
| 平台目录 + 封面索引（v0.2.0 起步，v0.3.0 完成数据与 UI） | 各平台 catalog + `generate_*_cover_urls.py` / `emulator_cover_pipeline.py` | 目录 CSV 4 个可选列 + 全量目录（7084 条 / 11 平台，来自 v0.6 数据经 `scripts/merge_v06_catalog.py` 合并）+ `cover_index.csv`（3470 行 / 合并后 6823 条有封面）+ 封面磁盘缓存 + **平台/分类双筛选 UI** + v0.3.1 分类清洗/数据体检（`normalize_categories` + `validate_catalog --strict` CI）；多平台数据已具备，模拟器安装仍未做（ROADMAP 9.8） |
| aria2 运行时复用（meta + flock） | `aria2_manager.py` 的 `aria2.runtime.json` + flock | `aria2-runtime.json` + `aria2-runtime.lock`，插件重载附着存活实例（见 6.4） |
| 直链原地换链 | `aria2.changeUri` | `Aria2Manager.replace_uri()`；直链过期保留 gid 与进度 |
| Steam 写入：DevkitGameID token 去重、unchanged、备份、回读 | `steam_shortcuts.py` | 同策略 + `*.freedeckcy-bak-*` 保留 12 份（见 6.5） |
| compatdata 自定义用户名打分 | `steam_shortcuts.py` | `find_compat_user_dir()` 按 AppData/Documents/Saved Games 打分 |
| aria2 启动参数加固 | `aria2_manager.py` | `--file-allocation=none`、超时/重试/日志/CA，UA+Referer |

### 13.2 我们更强、明确不回退

- **多游戏库 / SD 卡 / Flatpak**：v0.6 不解析 `libraryfolders.vdf`，`compatdata` 只在主库找；本仓库已支持全库扫描与 `FREEDECKCY_STEAM_ROOT`，**不为了"对齐"而回退**（见 §12 P1-14 / DEVELOPMENT §6.5）。
- **无 root 的安全模型**：见 13.3 第一条。

### 13.3 明确不采纳（附理由）

- **`plugin.json` 的 `flags: ["root"]` + `steam_host_writer` 用 `sudo -u deck` 写 Steam 文件**：v0.6 让插件以 root 运行，再由 helper 降权写文件。本插件始终以 deck 用户运行，引入 root 会扩大权限面、增加 Decky 审核/误用风险；当前"同用户原子写 + 写前备份 + 写后回读"已够用。
- **腾讯文档资源池的点赞 / 投稿**：需要腾讯文档登录态 + CDP 投稿（v0.6 有 `_submit_resource_pool_entry_via_cdp` 等），属于内容运营/用户生成内容，显著扩大合规面；"资源池只读"作为低风险候选列入 ROADMAP。
- **百度网页版 CDP 采集 / 未公开接口**：需采集网页登录态并逆向网页接口，维护成本与封号风险高；若要做百度，优先评估其 OpenAPI（见 ROADMAP）。

### 13.4 待做（详见 ROADMAP §9）

`7z t` 校验与 compatdata 卸载清理已在 v0.1.1 落地（见 13.1）。其余待做：Range 续传探测、SQLite 任务库、其它模拟器平台闭环（GBA/PSP/NDS 已在 v0.6.0/v0.7.0 落地；PS1 因 BIOS 依赖暂缓，PS2/PS3/3DS/FC/MD/Switch 待做）、资源池只读、百度 OpenAPI、自动重启 Steam；CTFile 等其它网盘来源仅作评估（接口/合规先决条件多，未列入当前优先级）。

---

## 14. 术语表


| 词 | 含义 |
|---|---|
| Decky Loader | Steam Deck 的第三方插件加载器，插件 = `main.py` + `plugin.json` + `dist/index.js` |
| QAM | Quick Access Menu，游戏模式按"…"弹出的侧边菜单，插件 UI 挂在这里 |
| Proton 前缀 / compatdata | 每个非 Linux 游戏在 `steamapps/compatdata/<appid>/pfx` 下的 Wine 容器，存档在 `drive_c/users/steamuser/...` |
| shortcuts.vdf | `userdata/<uid>/config/shortcuts.vdf`，非 Steam 游戏的快捷方式库（二进制 VDF） |
| grid | `userdata/<uid>/config/grid/`，自定义封面图目录（`p`=竖版、`_hero`、`_logo`、`_wide`） |
| 非 Steam 游戏 appid | `CRC32(exe路径+显示名) \| 0x80000000`，Steam 用它区分"手动添加的游戏" |
| HLTB | How Long To Beat，游戏时长数据库，本项目用它显示"主线 / 总时长" |
| gid | aria2 内部的下载任务 ID；本版本用运行时元数据 + flock 让插件重载后附着同一 aria2，gid 通常不变 |
| 多分卷归档 / 主卷 | 一个大压缩包被拆成多个文件（`.7z.001`、`.part1.rar`、`.z01+zip` …）；主卷是入口卷，只有它需要解压 |
| `bundled` | 任务 `install_status` 的一种：该文件属于多分卷归档但非主卷，由主卷统一解压 |
| DevkitGameID | Steam 快捷方式字段；本项目写入 freedeckCY token，作为比 LaunchOptions 更稳的去重/启动标记 |
| group_id | 同一安装计划（分卷/多包）共享的分组 ID；整组下载完成后才安装、只注册一次 Steam |
| `7z t` | 7-Zip 的归档测试子命令；本项目解压前跑它做完整性校验，7z 不可用时 best-effort 跳过 |
| compatdata 回收 | 卸载时可选删除 `<library>/steamapps/compatdata/<appid>`（默认不删，需在确认框显式选择） |
| libraryfolders.vdf | Steam 记录多游戏库（SD 卡、第二块盘）的 VDF 配置；本项目据此在所有库中扫描 `compatdata` |
| platform | 目录条目的平台标识（当前 11 种：`pc`/`fc`/`nds`/`psp`/`gba`/`3ds`/`ps2`/`ps1`/`ps3`/`md`/`switch`）；PC 行不显示平台标签，非 PC 行在卡片上显示；当前仅 GBA 可安装（mGBA），其它平台只可浏览 |
| DroidDeck | 在 Android 手机上运行 SteamOS 运行时并支持 Decky 插件的开源项目；ARM64 设备，Steam 根/Proton 工具与 Steam Deck 不同（见 3.1 / DROIDDECK.md） |
| Ludusavi | 开源存档路径清单项目（mtkennerly/ludusavi-manifest，MIT）；本项目内置其转换后的 JSON 清单（53,549 款游戏），用于把 Windows 存档路径解析到 Proton 前缀 |
| gamewatch | 后台游戏进程检测：每 8 s 扫 `/proc/*/cmdline`（无 /proc 用 `pgrep -f`），状态切换产出 start/end 事件；本项目只在 end 时触发自动云存档 |
| 存档指纹 | 对存档文件集算 sha256（相对路径 + 大小 + mtime_ns，最多 5000 文件），持久化在 `state.json` 的 `cloud_save_fingerprints`，未变化则跳过上传（reason=unchanged） |
| 模拟器注册表 / 闭环 | v0.7.0：`EmulatorSpec` 注册表接入 GBA（mGBA，内置）/ PSP（PPSSPP，按需下载）/ NDS（melonDS，按需下载 zip）；下载 ROM → 生成启动脚本 → Steam 原生快捷方式（不经 Proton）；PS1 因 BIOS 依赖暂缓 |
| EmulatorSpec | 平台注册表条目：官方资产（repo/版本/各 arch 文件名）、archive（appimage/zip）、launch_args、rom_extensions、env_var、min_bytes |
| 按需下载 | PSP/NDS 首次安装时从 GitHub release 下载官方 AppImage 到 `~/.local/share/freedeckCY/emulators/<platform>/<arch>/`；GBA 则随包内置 |
| ROM / wrapper | ROM = 安装目录里符合平台扩展名的文件（GBA `.gba`；PSP `.iso/.cso/.pbp/.elf`；NDS `.nds/.dsi/.srl`，优先 openpath 同名）；wrapper = `<install_dir>/launch-freedeckcy.sh`（按平台拼启动参数，Steam 快捷方式的 Exe） |
| `proton_tool` / `PACKAGE_ARCH` | 设置项 `proton_tool`：`auto`/`none`/具体兼容工具名；打包变量 `PACKAGE_ARCH`：`x86_64`/`aarch64`/`all`，决定产物架构与后缀 |
| cover_index.csv | 封面索引文件（仓库已内置 3470 行）：按 `game_id` 或标题补齐封面/appid/platform，不覆盖目录 CSV 已有值 |
| 平台 / 分类筛选条 | 库页搜索后的两行 chip：平台条（「全部平台」+ 各平台计数，v0.3.0 起可见）与分类条（「全部分类」+ Top12 分类计数，含「模拟器」）；都可与搜索词组合 |
| 分类清洗 / 数据体检 | v0.3.1 引入：`normalize_categories()` 在加载时剔除分类中的平台名并去重；`validate_catalog.py` 对目录做重复/非法链接/封面覆盖率等体检，`--strict` 进 CI 门禁 |
| 天翼云盘 | 中国电信 189 云盘，`cloud.189.cn`，本项目唯一的资源存储后端 |
