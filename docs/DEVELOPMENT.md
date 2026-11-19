# freedeckCY 开发指南

> [English](DEVELOPMENT.en.md) | 中文

本文面向二次开发者，对应 freedeckCY **v0.28.15**：如何在本地跑起来、改代码、打补丁、排查故障。DroidDeck（Android/ARM64）的安装、构建与排障单独见 [DROIDDECK.md](DROIDDECK.md)。架构与协议细节见 [ARCHITECTURE.md](ARCHITECTURE.md)，与作者 v0.6 的能力对照见 [ARCHITECTURE.md](ARCHITECTURE.md) §13，后续可做项见 [ROADMAP.md](ROADMAP.md)。

> 前提：本项目只支持 **SteamOS / Linux**。开发机可以是 Steam Deck，也可以是装了 Decky Loader 的 Linux 桌面环境；Windows / macOS 只能改代码，不能完整运行。

---

## 1. 模块职责速查

| 路径 | 职责（一句话） |
|---|---|
| `main.py` | Decky 插件入口：`Plugin` 类持有 Python 侧状态，把 24 个可调用 RPC 薄转发给 `TianyiService` / `server_manager`；主循环周期调用后台维护 |
| `py_modules/config.py` | 路径常量（下载目录、`~/.local/share/freedeckCY`）、后台维护间隔与日志器（`/tmp/freedeckcy.log`，`RotatingFileHandler` 5 MB × 3） |
| `py_modules/tianyi_service.py` | **业务内核**：安装计划、下载任务、后台安装、云存档、登录、游玩时长、面板状态缓存、封面解析与缓存、GBA/mGBA 注册；关键函数 `maintenance_tick`（后台维护）、`refresh_tasks`（状态同步）、`_try_recover_task` / `_readd_task_download`（重启恢复 + `changeUri` 原地换链）、`_maybe_schedule_group_post_process` / `_finalize_group_install`（分卷分组）、`_verify_downloaded_file` / `_quarantine_download_file`（完整性校验与自愈）、`_wait_payload_settled` / `_precheck_archive_payload` / `_schedule_archive_repair`（解压前收紧与 `7z t` 失败自动重下）、`retry_task`（失败任务重试）、`preview_uninstall` / `uninstall_installed_game`（卸载预览与 Proton 前缀回收）、`resolve_catalog_cover`（封面优先级链）、`_load_cover_cache` / `_save_cover_cache`（磁盘缓存）、`_auto_register_task_to_steam` / `_auto_register_emulator_to_steam`（GBA 启动脚本与原生快捷方式） |
| `py_modules/tianyi_client.py` | **天翼云盘协议客户端**：分享解析（`resolve_share(target_name, max_pages)` 支持分页找目标 ROM）、accessToken、下载直链、上传（调 Node）、sessionKey |
| `py_modules/tianyi_http.py` | 本地 HTTP 路由与 handler（**41 条路由 / 38 条 REST**）：Vue 页面、REST API、诊断 zip、更新检查、统一 JSON 响应 |
| `py_modules/server_manager.py` | aiohttp 生命周期、本地 API 安全边界（Host/Origin 校验）、设置备份、`/_healthz` |
| `py_modules/tianyi_store.py` | 数据类（登录/设置/任务/已装游戏，含 `file_size` / `group_id` / `group_total`）+ `state.json` 原子读写；写入时目录 0700 / 文件 0600 |
| `py_modules/aria2_manager.py` | aria2 子进程管理（运行时元数据 `aria2-runtime.json` + `flock` 让插件重载可附着存活实例）+ JSON-RPC（`addUri` / `changeUri` / `tellStatus` / `listDownloads` …） |
| `py_modules/seven_zip_manager.py` | 7z 解压 / 压缩（带进度回调）；`test_archive()` 跑 `7z t` 做解压前校验（7z 不可用时 best-effort 跳过） |
| `py_modules/save_manifest.py` | **Ludusavi 存档清单（v0.8.0）**：加载本地 JSON、标题/SteamID 匹配、`<base>/<winAppData>/...` 占位符解析到 Proton 前缀、glob 展开（最多 200 路径）；运行时不联网 |
| `py_modules/gamewatch.py` | **游戏进程检测（v0.8.0）**：后台每 8 s 扫 `/proc/*/cmdline`（无 `/proc` 回退 `pgrep -f`），状态切换产出 start/end 事件（自动云存档只在 end 触发） |
| `py_modules/emulator_manager.py` | **通用模拟器注册表（v0.14.1，10 平台全部在线下载）**：`EmulatorSpec`/`EMULATORS` 描述 GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch（3DS 带 `flatpak_id=org.azahar_emu.Azahar`）；`available_platforms(arch)` 做架构白名单；官方资产解析、首次安装按需下载、AppImage/zip 解包、SteamOS 上 3DS 优先 Flatpak（`_is_steamos`/`flatpak_installed`/`_ensure_flatpak`）、`find_rom_file()`、3DS wrapper 强制 XWayland、`emulator_status()`；旧 `prepare_bios()` 保留兼容 |
| `py_modules/emulator_saves.py` | **模拟器存档发现/恢复（v0.15.0；v0.16.0 恢复/拆分）**：`STANDARD_SAVE_DIRS`/`PORTABLE_SUBDIRS` 覆盖 10 平台；GBA/FC/MD/NDS 按 ROM 名称单游戏匹配，PSP/PS3 用 PARAM.SFO、3DS 用 NCSD title id 拆分，PS1/PS2/Switch 仍共享；`restore_roots`/`build_restore_targets` 提供恢复白名单 |
| `py_modules/param_sfo.py` | 最小 `PARAM.SFO` 解析（v0.16.0）：`read_param_sfo()` 读 key/value、`find_param_sfo()` 在存档目录递归查找，用于 PSP/PS3 按 TITLE 拆分存档 |
| `py_modules/emulator_setup.py` | **安装后 BIOS/固件部署（v0.12.0；v0.14.1 3DS 加 Flatpak 路径）**：`setup_emulator(platform, command, seven_zip)` 把 `bios/<platform>/` 下文件/压缩包部署到模拟器目录并写 portable 配置；3DS sysdata 同时部署到 `~/.var/app/org.azahar_emu.Azahar/data/{azahar,azahar-emu}/sysdata`；只补缺失/只改单个键，不下载 |
| `py_modules/storage_options.py` | **可移动存储检测（v0.19.0）**：解析 `/proc/mounts` 找 `/run/media`（SteamOS SD）/`/media`/`/mnt`/`/storage`（DroidDeck）/`/sdcard` 可写子挂载，过滤系统 fstype 与挂载根；返回 `internal/external/options`、free/total 与建议 `freedeckCY/{downloads,installed}` |
| `py_modules/submission.py` | **仓库游戏提交（v0.13.0）**：`normalize_platform()` 平台别名、`validate_submission()`/`validate_submission_files()` 校验、`build_catalog_row()` 生成目录行、`merge_submissions()` 合并（dry-run/`--apply`）；纯标准库，可被 CLI 直接 import |
| `py_modules/baidu_qr.py` | **百度 Passport 扫码登录（v0.17.0，主链路）**：`request_qr()` 取二维码 sign/imgurl、`fetch_qr_image()` 下载 PNG、`poll_qr()` 长轮询 waiting/scanned/confirmed、`complete_login()` 用 v 换 `BDUSS/STOKEN/PTOKEN` |
| `py_modules/baidu_client.py` | **百度分享 URL 解析/直链（v0.17.0）**：`resolve_baidu_share(share_url, cookie)` 走 Cookie 主链路解析分享/文件列表，`fetch_baidu_download_url()` 取直链；OpenAPI 回退也复用其公开分享元数据 |
| `py_modules/baidu_openapi_client.py` | **百度官方 OpenAPI（v0.14.0，v0.17.0 起可选回退）**：OAuth oob 授权（`build_baidu_oauth_authorize_url`/`exchange_baidu_oauth_code`/`refresh_baidu_oauth_token`）、公开分享转存、`fetch_baidu_openapi_download_url`、`delete_baidu_openapi_transfer_file`；没有 Cookie 时才使用 |
| `py_modules/steam_shortcuts.py` | 写 `shortcuts.vdf`（`DevkitGameID` token 去重、无变化不重写、写前备份 12 份、写后回读）、改 `config.vdf` 的 Proton 映射、下载 `grid` 封面、解析 appid；Steam 多库 / Flatpak / **DroidDeck** 识别（`is_droiddeck` / `_steam_root_candidates` / `detect_proton_tool`）、自定义用户名打分；`find_compatdata_dirs()` 跨库定位待清理的 Proton 前缀 |
| `py_modules/game_catalog.py` | 读 CSV 资源清单（16 列 / 7084 条 / 11 平台，新目录优先、旧目录回退）：校验、搜索、分页、按 `game_id` 查找；`normalize_categories()` 加载时清洗分类（去平台名/去重/模拟器兜底）；支持 `cover_index.csv` 合并（不覆盖已有值）；`list()` 支持 platform/category 过滤并返回 `platforms`/Top12 `categories`；`_is_valid_tianyi_url()` 兼容 `/t/` 与 `/web/share?code=` |
| `py_modules/archive_bundle.py` | 多分卷归档识别（`.7z.001`/`.partN.rar`/`.z01+zip`/`.r00+rar` 等 6 类）：`detect_archive_sets` / `build_bundle_index` / `looks_like_multi_volume_name` |
| `py_modules/utils.py` | 端口占用检测、等待端口释放、局域网 IP 探测（历史遗留） |
| `py_modules/vdf/` | 第三方 VDF 库（文本 + 二进制格式），`py_modules/vdf/__init__.py` 提供 `parse/loads/dumps/binary_dumps` 等 |
| `backend/tianyi_share_resolver.js` | 分享链接解析的 Node 兜底实现（stdin 一行 JSON → stdout 一行 JSON） |
| `backend/tianyi_cloud_upload.js` | 云盘上传（`upload`）、列版本（`list_versions`）、下载（`download_file`）的 ESM 实现 |
| `backend/tianyi_cloud_upload.cjs` | 同一逻辑的 CommonJS 版，**只实现 `upload`**；仅在 `.js` 不存在时启用 |
| `src/index.tsx` | 全部 React 代码：QAM 主面板、设置页、Steam 库页时长注入、全局游戏事件监听 |
| `defaults/tianyi_library_ui/` | 本地 Vue 游戏库（打开即浏览、平台/分类筛选、**分页/排序**、**已安装页签**、诊断导出/更新检查工具条、手柄焦点序列、非 PC 只提示不安装）与二维码登录桥（免构建，直接改） |
| `defaults/tianyi_catalog/gamebox_all_links_*.csv` | 随插件分发的资源清单（`game_id,title,categories,down_url,pwd,openpath,filesize_z` 等） |
| `scripts/fetch_runtime.sh` | 下载 aria2c / 7zz / node 到 `defaults/runtime/`（`make runtime` 调用它） |
| `scripts/package.sh` | 组装 Decky 插件 zip 到 `dist-artifacts/`（`make package` 调用它）；`PACKAGE_ARCH=x86_64|aarch64|all` 控制目标架构与产物后缀 |
| `scripts/fetch_ludusavi_manifest.py` | 从上游 YAML 下载并转换 Ludusavi 存档清单到 `defaults/ludusavi/manifest.json.gz`（`make ludusavi-manifest` 调用；PyYAML 仅构建时需要） |
| `scripts/doctor.sh` | 环境诊断（只读，`make doctor` 调用）：系统/Python/运行时/Steam/state/日志/端口/网络 |
| `scripts/normalize_catalog_categories.py` | 原地清洗目录 `categories`（去平台名/去重/模拟器兜底；`--check` 只报告差异） |
| `scripts/validate_catalog.py` | 目录数据体检（重复/非法链接/空标题/分类混平台名/封面覆盖率/平台分布/总大小；`--strict` 用于 CI） |
| `tests/` | pytest 单测（585 个用例；原生库为前端构建验证）：**gamewatch 状态机 / Ludusavi 匹配解析 / 自动上传触发与指纹 / 模拟器存档发现（单游戏 vs 共享、开关）/ 恢复计划 / PSP-PS3-3DS 拆分 / PS1 多碟 m3u**、目录解析/平台筛选/排序、已安装列表/诊断导出/更新检查、**10 平台计划/ROM 查找/wrapper/注册表/BIOS/架构白名单/BIOS 部署与 portable 配置、提交校验/合并、百度扫码/Cookie + OpenAPI 回退（来源识别/二维码/计划/header/授权码交换）**、分类清洗、DroidDeck 检测/Proton 解析/双 Steam 根、VDF、状态存储、云存档版本、安装链路、分组语义、重启恢复、多分卷识别、aria2 运行时、多库识别、卸载/compatdata、**安装可靠性（环境自检/校验/修复/体检/诊断/换源）**、安全边界等离线逻辑 |
| `clear_freedeckcy_tasks.sh` | 运维脚本：清空 `state.json` 的 `tasks`（用 `$HOME`，可用 `FREEDECKCY_STATE_FILE` 覆盖路径） |
| `docs/DROIDDECK.md` | DroidDeck（Android/ARM64）安装、构建、功能支持与排障指南（v0.4.0） |
| `gl/` | 作者手工囤的数据（历史 CSV、模拟器分享链接），**代码不读**，可忽略 |

---

## 2. 本地开发

### 2.1 把仓库挂进 Decky

Decky Loader 从 `~/homebrew/plugins/` 加载插件。开发时推荐**符号链接**，这样改仓库 = 改运行中的插件：

```bash
# 备份并移除已安装的同名插件（如有）
mv ~/homebrew/plugins/freedeckCY ~/homebrew/plugins/freedeckCY.bak 2>/dev/null || true

# 用符号链接指向你的开发仓库
ln -s /path/to/freedeckCY ~/homebrew/plugins/freedeckCY
```

然后在 Decky Loader 中重载插件（或重启插件加载器/Steam）。插件应出现在游戏模式侧边栏（QAM）里。

> 用 zip 安装的插件是复制到插件目录的，改仓库不会自动生效；开发时请用上面的符号链接方式。

### 2.2 Python 侧：改完重载即可

`py_modules/*.py` 与 `main.py` 都是解释执行的，**改完不需要构建**：

1. 修改代码；
2. 在 Decky Loader 中重载 freedeckCY（或重启插件加载器）；
3. 看日志确认加载成功：`tail -f /tmp/freedeckcy.log`。

注意：插件主循环会每 `config.MAINTENANCE_INTERVAL_SECONDS`（默认 8 s）调用一次 `TianyiService.maintenance_tick()`，负责同步下载进度与补做中断的安装；启动时也会先执行一次。调试下载/安装链路时优先看这个循环有没有在跑。

### 2.3 React / QAM 前端

```bash
pnpm install
pnpm build      # rollup → dist/index.js（已提交的构建产物）
pnpm watch      # 开发时可选：文件变化自动重打包
```

- 改了 `src/index.tsx` 或 `src/types.d.ts` 后必须重新 `pnpm build`，然后重载插件才会生效。
- 只提交 `dist/index.js` 与 `dist/index.js.map`，`node_modules/` 不提交。

### 2.4 旧版 Vue 本地页面（仅桌面调试/回退）

> 当前主入口是 Decky 原生 React 游戏库（见 §6.14）；`defaults/tianyi_library_ui/` 不再由 QAM「游戏库」打开。

`defaults/tianyi_library_ui/` 下的 `index.html`、`app.js`、`app.css`、`login_bridge.*`、`vue.global.prod.js` 是**浏览器直出**的静态文件，没有构建步骤：

- 直接编辑这些文件，刷新 Steam 内置浏览器里的页面即可（必要时重载插件让 Python 重新识别资源目录）；
- 本地网页地址仍由 `get_tianyi_library_url` 返回，形如 `http://127.0.0.1:59271/tianyi/library`，仅用于桌面浏览器/调试；QAM「游戏库」已改为原生 React 页面。
- 建议在桌面浏览器的无痕窗口里直接访问上述地址调试（只在回环地址监听，必须在本机访问）。

### 2.5 目录数据、封面索引与筛选

**目录文件优先级**（`game_catalog.resolve_default_catalog_path()`）：`FREEDECKCY_GAME_CATALOG_CSV` → `defaults/tianyi_catalog/freedeckcy_catalog.csv`（v0.3.1 主用，**7084 条有效 / 11 平台，分类已清洗**）→ 旧版 `gamebox_all_links_20260221_234730.csv`（回退，2845 行 / 2685 条）→ `defaults/tianyi_catalog.csv`。改完 CSV 后重载插件生效（`initialize()` 全量读入内存）。

**目录 CSV 16 列**：

```text
game_id,title,category_parent,categories,package_name,server,down_url,shorturl,
pwd,openpath,filesize_z,list_filesize,platform,cover_url,cover_portrait_url,steam_appid
```

- `down_url` 支持 `https://cloud.189.cn/t/<code>?pwd=...` 和 `https://cloud.189.cn/web/share?code=...`（后者必须带 `code=`，FC/GBA/MD 等资源常用）；`title` 或链接缺失的行会被计为 invalid；
- `platform` 当前取值：`pc` / `fc` / `nds` / `psp` / `gba` / `3ds` / `ps2` / `ps1` / `ps3` / `md` / `switch`（缺省归一为 `pc`，别名 `steam/windows/win`→`pc`、`ns/nsx`→`switch`）；
- 平台分布：PC 2540、FC 1475、NDS 722、PSP 575、GBA 553、3DS 305、PS2 250、PS1 194、PS3 194、MD 191、Switch 85。

**从上游 v0.6 合并目录（可复现）**：数据来自 v0.6 的 `freedeck_catalog.csv`（7041 行 / 28 列）+ 旧目录独有条目，用仓库根 `scripts/merge_v06_catalog.py` 生成：

```bash
# 需要本地有上游 v0.6 解包（本项目不随仓库分发该数据）
python3 scripts/merge_v06_catalog.py \
  --v06-dir ../0.6/freedeck-plugin/defaults/tianyi_catalog \
  --base defaults/tianyi_catalog/gamebox_all_links_20260221_234730.csv \
  --out defaults/tianyi_catalog/freedeckcy_catalog.csv \
  --cover-out defaults/tianyi_catalog/cover_index.csv
```

脚本规则：以 v0.6 目录为主、只保留天翼链接、按 `game_id` 去重、v0.6 缺失的旧目录条目补在后面（43 条，`platform=pc`），cover index 归一为 6 列。输出后重载插件即可看到新数据；平台/分类筛选条按数据自动生成，无需改代码。

**可选远程 JSON 目录（v0.6.2）**：`FREEDECKCY_CATALOG_JSON` 可指向本地 JSON 或 `https://…` URL（NewFreedeck 兼容），远程缓存 6 小时、失败回退本地 CSV；默认关闭，显式设置才启用；默认目录由设置页下载服务器 CSV。格式/自托管说明见 [UPSTREAM_SERVER.md](UPSTREAM_SERVER.md)。

**目录数据工作流（v0.3.1 起固定三步）**：

```bash
# 1) 从上游 v0.6 合并（可选；已有目录可跳过）
python3 scripts/merge_v06_catalog.py --v06-dir ../0.6/freedeck-plugin/defaults/tianyi_catalog

# 2) 清洗 categories（去平台名/去重/模拟器兜底；--check 只检查不写）
python3 scripts/normalize_catalog_categories.py defaults/tianyi_catalog/freedeckcy_catalog.csv
python3 scripts/normalize_catalog_categories.py defaults/tianyi_catalog/freedeckcy_catalog.csv --check

# 3) 体检（CI 用同一命令 + --strict）
python3 scripts/validate_catalog.py defaults/tianyi_catalog/freedeckcy_catalog.csv \
  --cover-index defaults/tianyi_catalog/cover_index.csv --strict
```

也可以用 Makefile 快捷方式：`make normalize-catalog`、`make validate-catalog`。**修改/新增目录数据后必须跑第 2、3 步**：CI 的 python job 会在 pytest 后执行 `validate_catalog.py ... --strict`，数据脏（重复 game_id/非法链接/空标题/分类混平台名）会直接红。

**分类清洗规则**（`game_catalog.normalize_categories()`，加载时也会对每行应用）：

- 分隔符：`,`、`，`、`/`、`、`、`;`、`；`、`|`；逐段去空白、不区分大小写去重、输出统一逗号分隔；
- 剔除平台名 token：`pc/fc/nds/psp/gba/3ds/ps1/ps2/ps3/md/switch/ns/arcade/psx` 以及该行自身 `platform`；
- 模拟器行（`platform != pc`）清洗后为空时补 **「模拟器」**；PC 行保持空；
- v0.3.1 数据清洗结果：**606 行** categories 改写，分类中已无平台名，「模拟器」分类 606 条；`--check` 现在 0 差异（幂等）。

**目录体检口径**（`validate_catalog.py`，v0.3.1 实测）：7084 行 / 16 列；自带封面 3473/7084（49.0%）；`cover_index.csv`（3470 行）按 `game_id` 命中 3311，合并覆盖 6783/7084（95.8%）；加载器按 `game_id` 或标题合并后 6823/7084（96.3%）；资源总大小约 39 TB（39098.5 GB）；仅 1 条警告（46 个重复 `down_url`，同一分享多条目正常）。

**封面索引** `defaults/tianyi_catalog/cover_index.csv`（仓库已内置 **3470 行**，`FREEDECKCY_COVER_INDEX_CSV` 可覆盖）：

```csv
game_id,title,steam_appid,cover_url,cover_portrait_url,platform
18194,出行路线/横冲直撞/TRAIL OUT,1234567,https://example.com/trailout-header.jpg,https://example.com/trailout-portrait.jpg,pc
```

- 列名兼容：横版 `cover_url` / `landscape_cover_url` / `cover`；竖版 `cover_portrait_url` / `square_cover_url` / `portrait_url` / `portrait`；appid `steam_appid` / `app_id` / `appid`；
- 匹配顺序：先 `game_id` 精确匹配，其次标题（去空白、小写）；**只补空值，不覆盖目录 CSV 已有值**；合并后 **6823 / 7084 条资源自带封面**；
- 只有 `steam_appid` 时，插件合成 Steam CDN 封面（横版 `header.jpg`、竖版 `library_600x900.jpg`），无需填 cover URL。

**封面解析顺序**（`resolve_catalog_cover`）：目录/索引静态封面 → 内存/磁盘缓存 → Steam 商店搜索 → ProtonDB 等级。缓存文件 `~/.local/share/freedeckCY/tianyi/cover_cache.json`（0600、原子写），正缓存 7 天、负缓存 30 分钟；删掉它并重载插件即可强制重新解析。

**平台 / 分类筛选（v0.3.0 UI 已接）**：

- 搜索后显示两行筛选条：平台条（「全部平台」+ 各平台计数）和分类条（「全部分类」+ Top12 分类计数）；平台条只在 `platforms` 数量 > 1 时显示（当前 11 个平台，所以可见）；
- 手柄焦点顺序：搜索框 → 搜索按钮 → 平台条 → 分类条 → 卡片；
- 请求同时带 `platform` 与 `category` 参数（`/api/tianyi/catalog`），可组合；
- **10 平台可安装，按架构自动裁剪**（v0.11.0）：GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch 的卡片在可用架构上会正常打开安装确认（弹窗显示模拟器名；BIOS/setup 需要文件时显示警告）；3DS/PS2/PS3 **仅 x86_64**——在 aarch64 上目录查询按 `available_platforms()` 白名单隐藏这些平台的条目与筛选条，后端 `_build_install_plan()` 也只放行 `pc` + 当前架构可用平台。模拟器调试见 §6.8。

---

## 3. 运行时二进制准备（`make runtime`）

仓库**不提交**运行时二进制（`.gitignore` 已排除 `defaults/runtime/`）。克隆后先补齐：

```bash
make runtime                      # 下载本机架构的 aria2c + 7zz + node 到 defaults/runtime/
make runtime ARCH=all             # 同时下载 x86_64 与 aarch64
make help                         # 列出全部 make 目标与变量
bash scripts/fetch_runtime.sh --help   # 查看脚本级参数
```

`scripts/fetch_runtime.sh` 支持按组件/架构单独下载（以 `--help` 输出为准）：

```bash
bash scripts/fetch_runtime.sh --only 7z                  # 只下 7zz
bash scripts/fetch_runtime.sh --only aria2 --arch x86_64 # 只下 aria2c
bash scripts/fetch_runtime.sh --only node --arch aarch64 # 只下 node
bash scripts/fetch_runtime.sh --force                    # 忽略已存在，强制重下
bash scripts/fetch_runtime.sh --dest /tmp/runtime        # 自定义输出目录（默认 <repo>/defaults/runtime）
```

落盘结构（代码按此顺序查找，优先级从高到低）：

```text
defaults/runtime/aria2/<arch>/aria2c            # <arch> = x86_64 | aarch64
defaults/runtime/7z/<arch>/7zz
defaults/runtime/node/<arch>/bin/node
```

**模拟器运行时（10 平台，v0.11.0）**：`py_modules/emulator_manager.py` 的 `EMULATORS` 注册表描述每个平台的官方资产、启动参数、ROM 扩展名与可选字段（`state_key` 缓存目录名、`executables` zip 内可执行文件名、`bios_required`、`setup_required/setup_hint`）；`available_platforms(arch)` 返回当前架构有官方包的平台（3DS/PS2/PS3 仅 x86_64，aarch64 上会被目录白名单隐藏）：

| 平台 | 模拟器（版本） | 官方资产（arch → 文件） | 格式 | ROM 扩展名 | 环境变量 |
|---|---|---|---|---|---|
| gba | mGBA 0.10.5 | `mGBA-0.10.5-appimage-{x64,arm64}.appimage` | AppImage，**首次安装按需下载**（x64 约 25MB / arm64 约 24.6MB） | `.gba` | `FREEDECKCY_MGBA_BIN` |
| psp | PPSSPP 1.20.4 | `PPSSPP-v1.20.4-anylinux-{x86_64,aarch64}.AppImage` | AppImage，按需下载 | `.iso/.cso/.pbp/.elf` | `FREEDECKCY_PPSSPP_BIN` |
| nds | melonDS 1.1 | `melonDS-1.1-appimage-{x86_64,aarch64}.zip` | zip 内 AppImage，按需下载 | `.nds/.dsi/.srl` | `FREEDECKCY_MELONDS_BIN` |
| ps1 | DuckStation `latest` | `DuckStation-{x64,arm64}.AppImage` | AppImage，按需下载；**需要自备 BIOS** | `.m3u/.cue/.chd/.iso/.pbp/.bin` | `FREEDECKCY_DUCKSTATION_BIN` |
| fc | Mesen2 2.1.1 | `Mesen_2.1.1_Linux_{x64,ARM64}.zip` | zip 内单文件 `Mesen`，按需下载 | `.nes/.fds/.unf/.unif` | `FREEDECKCY_MESEN_BIN` |
| md | Mesen2 2.1.1 | 同上（**与 FC 共享缓存** `emulators/mesen/<arch>/`） | zip 内单文件 `Mesen`，按需下载 | `.md/.gen/.smd/.bin/.32x` | `FREEDECKCY_MESEN_BIN` |
| 3ds | Azahar 2126.2 | **SteamOS 优先 Flathub `org.azahar_emu.Azahar`**；否则 `azahar.AppImage`（**仅 x86_64**） | 3DS system files（setup）；Flatpak 自动安装或 AppImage 回退 | `.3ds/.cci/.cxi/.app`（`.cia` 通过 `--install`） | `FREEDECKCY_AZAHAR_BIN`（最高优先） |
| ps2 | PCSX2 v2.8.2 | `pcsx2-v2.8.2-linux-appimage-x64-Qt.AppImage`，**仅 x86_64** | AppImage，按需下载；需要 PS2 BIOS | `.iso/.chd/.cue/.bin/.gz` | `FREEDECKCY_PCSX2_BIN` |
| ps3 | RPCS3 build-8d6b42e | `rpcs3-v0.0.43-20606-8d6b42e7_linux64.AppImage`，**仅 x86_64** | AppImage，按需下载；需要 PS3 固件（setup） | `.iso/.pkg/.elf/.self` | `FREEDECKCY_RPCS3_BIN` |
| switch | Eden v0.2.1 | `stable.eden-emu.dev/v0.2.1/` 的 x86_64 + aarch64 AppImage | AppImage，按需下载；需要 prod.keys + 固件（setup） | `.nsp/.xci` | `FREEDECKCY_EDEN_BIN` |

启动参数：GBA `-f <rom>`、PSP `--fullscreen <rom>`、NDS/3DS/Switch `<rom>`、PS1/PS2 `-batch -fullscreen <rom>`、PS3 `--no-gui <rom>`、FC/MD `/fullscreen <rom>`。

**架构白名单**：`available_platforms(arch)` 按 `spec.assets` 是否含当前 arch 过滤；`TianyiService.list_catalog()` 把 `["pc", *available_platforms()]` 传给 `GameCatalog.list(allowed_platforms=...)`，因此 x86_64 显示 10 平台，aarch64 只显示 GBA/PSP/NDS/PS1/FC/MD/Switch（3DS/PS2/PS3 的条目和平台筛选条都不出现）。

解析顺序（v0.10.0 起**没有内置包分支**）：`FREEDECKCY_<PLATFORM>_BIN` → 已下载/已解包的模拟器（`~/.local/share/freedeckCY/emulators/<state_key>/<arch>/`；GBA 兼容旧 `<arch>/squashfs-root`）→ 系统命令 → Flatpak（mGBA 的 `io.mgba.mGBA`；3DS 用 `org.azahar_emu.Azahar`，SteamOS 上自动安装）。都没有时 `emulator_status` 返回 `source=download`（10 平台都如此；无当前架构资产时返回 `available=false` + "已隐藏该平台"），安装时 `ensure_emulator` 从 GitHub release 下载到 `emulators/<state_key>/<arch>/`：AppImage 走 `--appimage-extract`（不依赖 FUSE，proot/DroidDeck 可用），zip 先解压找 `executables` 指定的可执行文件（Mesen2 的 `Mesen`），否则找 zip 内 AppImage。只有当前架构没有官方资产时才会在计划阶段拒绝。

**离线预置**：把官方包提前放到 `~/.local/share/freedeckCY/emulators/<platform>/<arch>/`（AppImage 需 `chmod +x`；zip 可留原样，安装时会解），或用 `FREEDECKCY_*_BIN` 指向本地可执行文件/AppImage（GBA `FREEDECKCY_MGBA_BIN`、PSP `FREEDECKCY_PPSSPP_BIN`、NDS `FREEDECKCY_MELONDS_BIN`、PS1 `FREEDECKCY_DUCKSTATION_BIN`、FC/MD `FREEDECKCY_MESEN_BIN`）。

**BIOS / 固件部署（v0.12.0，用户自备，插件只部署/提示）**：

- 统一来源目录：`~/.local/share/freedeckCY/bios/<platform>/`；安装完成后 `setup_emulator(platform, command, seven_zip=self.seven_zip)` 递归扫描该目录（`.bin/.rom/.bios/.keys/.pup/.nca`），压缩包（`.zip/.7z/.rar/.tar/.gz/.tgz/.xz/.bz2`）用 7zz 解压后复制到 `bios/<platform>/_extracted/` 作持久缓存；
- **PS1**：BIOS 复制到 `<AppDir>/bios` + 旧 `~/.local/share/duckstation/bios`；写 `portable.txt` 与 `portable_data/settings/settings.ini`（`[BIOS] SearchDirectory=./bios`、`[Display] Fullscreen=true`，已有 INI 只修这两个键）；
- **PS2**：BIOS 复制到 `<AppDir>/bios`、`~/.local/share/PCSX2/bios`、`~/.config/PCSX2/bios`；写 `portable.ini` 与 `inis/PCSX2.ini`（`[Folders] Bios`、`[UI] Fullscreen=true`）；
- **NDS**：`bios7.bin/bios9.bin/firmware.bin/dsi_firmware.bin` 等复制到 `<AppDir>` 与 `~/.local/share/melonDS`；
- **Switch**：`prod.keys`/`title.keys` → `~/.local/share/eden/keys/`；固件解出的 `.nca` 目录 → `~/.local/share/eden/nand/system/Contents/registered/`；
- **PS3**：`bios/ps3/PS3UPDAT.PUP`；若 `~/.config/rpcs3/dev_flash` 为空则执行 `rpcs3 --installfw <pup>`（600s 超时，失败原因写进消息）；
- **3DS**：system files → `~/.local/share/azahar-emu/sysdata`（兼容旧 `azahar`/`citra`）；
- **GBA / PSP**：只写 portable 配置（mGBA `portable.ini`+`qt.ini` 全屏；PPSSPP `portable.txt`+`memstick/PSP/SYSTEM/ppsspp.ini` 全屏）；
- `<AppDir>` 是 `ensure_emulator()` 返回的可执行文件目录（AppImage 解包后是 `squashfs-root/`）；目录不可写时只写用户数据目录并提示；
- 部署消息并入**安装完成消息**（不再单独发 `warning`）；`emulator_status`/plan 仍返回 `bios_required/bios_present/bios_dir` 与 `setup_required/setup_hint`。缺失**不阻断安装**，但装完不能直接玩通常是文件没放对/没触发部署。详见 §6.8。

**ARM64 / DroidDeck**：运行时目录按 `platform.machine()` 归一（`x86_64`；`aarch64`/`arm64`→`aarch64`）选择，DroidDeck 上取 `defaults/runtime/aarch64/`。准备 arm64 运行时用 `make runtime ARCH=aarch64`（或 `ARCH=all` 同时两份），详见 §4.1 与 [DROIDDECK.md](DROIDDECK.md)。

代码会优先使用这些内置运行时，只有不存在时才回退系统命令（`aria2c`、`7zz/7zr/7z`、`node`）。也可以用环境变量强制指定：

| 环境变量 | 作用 |
|---|---|
| `FREEDECKCY_ARIA2_BIN` | aria2c 可执行文件路径（另有历史拼写 `FRIENDECK_ARIA2_BIN` 兼容） |
| `FREEDECKCY_7Z_BIN` | 7zz 可执行文件路径 |
| `FREEDECKCY_NODE_BIN` | node 可执行文件路径（需 ≥ 18） |
| `FREEDECKCY_GAME_CATALOG_CSV` | 覆盖资源清单 CSV 路径（兼容旧拼写 `FRIENDECK_GAME_CATALOG_CSV`） |
| `FREEDECKCY_COVER_INDEX_CSV` | 覆盖封面索引 CSV 路径（兼容旧拼写 `FRIENDECK_COVER_INDEX_CSV`；文件可选） |
| `FREEDECKCY_LUDUSAVI_MANIFEST` | 覆盖 Ludusavi 存档清单 JSON 路径（默认 `defaults/ludusavi/manifest.json.gz`） |
| `FREEDECKCY_STEAM_ROOT` | 覆盖 Steam 根目录（Flatpak / 自定义安装 / 多盘位 / DroidDeck 双客户端时用） |
| `FREEDECKCY_PROTON_TOOL` | 覆盖 Proton 兼容工具名；`none` 表示不写映射（DroidDeck 默认 `droiddeck-proton-arm64`） |
| `FREEDECKCY_CATALOG_JSON` | 运行时改读 NewFreedeck 兼容 JSON（默认 CSV，失败回退） |
| `FREEDECKCY_MGBA_BIN` | 覆盖 mGBA 可执行文件/AppImage 路径（默认用已下载的缓存；也可指向系统 mGBA 或手工预置的 AppImage） |
| `FREEDECKCY_PPSSPP_BIN` | 覆盖 PPSSPP 可执行文件/AppImage 路径（默认用已下载/系统版本） |
| `FREEDECKCY_MELONDS_BIN` | 覆盖 melonDS 可执行文件/AppImage 路径（默认用已下载/系统版本） |
| `FREEDECKCY_DUCKSTATION_BIN` | 覆盖 DuckStation 可执行文件/AppImage 路径（PS1；默认用已下载/系统版本） |
| `FREEDECKCY_MESEN_BIN` | 覆盖 Mesen2 可执行文件/AppImage 路径（FC/MD 共用；默认用已下载/系统版本） |
| `FREEDECKCY_AZAHAR_BIN` | 覆盖 Azahar 路径（3DS；仅 x86_64；默认用已下载/系统版本） |
| `FREEDECKCY_PCSX2_BIN` | 覆盖 PCSX2 路径（PS2；仅 x86_64；默认用已下载/系统版本） |
| `FREEDECKCY_RPCS3_BIN` | 覆盖 RPCS3 路径（PS3；仅 x86_64；默认用已下载/系统版本） |
| `FREEDECKCY_EDEN_BIN` | 覆盖 Eden 路径（Switch；x86_64/aarch64；默认用已下载/系统版本） |
| `FREEDECKCY_BAIDU_OPENAPI_APP_KEY` | 百度开放平台 App Key（无头环境用；state 里保存的值优先） |
| `FREEDECKCY_BAIDU_OPENAPI_SECRET_KEY` | 百度开放平台 Secret Key（无头环境用；state 里的值优先） |
| `FREEDECKCY_BAIDU_OPENAPI_REFRESH_TOKEN` | 百度 refresh_token 覆盖（state 为空时用；仍建议走 QAM 授权） |
| `FREEDECKCY_STATE_FILE` | 仅供 `clear_freedeckcy_tasks.sh`：覆盖 `state.json` 路径 |

> 三个运行时都只在需要时才用到：不下载也不会导致插件启动失败，但会在下载/解压/云存档时分别报"下载组件不可用""解压组件不可用""未找到 node 运行时"。

---

## 4. 打包（`make package`）

```bash
make package                            # → dist-artifacts/freedeckCY-v<version>.zip
make package PACKAGE_ARGS=--build-ui    # 先 pnpm build 再打包
make package PACKAGE_ARGS="--out-dir /tmp/freedeckcy-build"
bash scripts/package.sh --help          # 查看全部参数
```

- 版本号取自 `package.json` 的 `version` 字段（当前为 `0.28.15`）；
- zip **顶层目录必须是插件目录 `freedeckCY/`**（Decky 本地安装会查找 `顶层目录/plugin.json`，根目录直接放文件会被静默忽略）；其下是 `main.py`、`plugin.json`、`package.json`、`LICENSE`、`README.md`，以及 `dist/`、`py_modules/`、`backend/`、`defaults/`；
- 打包脚本会排除 `__pycache__`、`*.pyc`、`.DS_Store`、`node_modules`、`.git`、`tests`、`scripts`、`.github`、`docs`、`gl`、`dist-artifacts`（白名单之外的一律不打包）；
- 默认复用已提交的 `dist/index.js`，不会强制跑 `pnpm build`；需要重新构建前端时用 `bash scripts/package.sh --build-ui`（要求 PATH 里有 pnpm）；
- 如果此前跑过 `make runtime`，`defaults/runtime/` 会被一起打进 zip（这是能离线安装的关键）；因此 `make clean` 默认**保留** `defaults/runtime/`，要删需 `make clean CLEAN_RUNTIME=1`；
- 自定义输出目录：`bash scripts/package.sh --out-dir /tmp/freedeckcy-build`；
- 如果 `defaults/runtime/` 还没准备，脚本只警告不失败——但这样打出来的包在目标机上仍会缺运行时，请先 `make runtime`；`defaults/ludusavi/manifest.json.gz` 缺失时也只警告（自动云存档会退回纯 Proton 目录扫描），发布包应包含它（`make ludusavi-manifest`）；
- 安装：Decky Loader → 设置 → 开发者 → 从压缩包安装插件（不同 Decky 版本措辞略有差异），或解压到 `~/homebrew/plugins/freedeckCY/` 后重启插件加载器。

### 4.1 ARM64 / DroidDeck 打包与调试（v0.4.0）

DroidDeck 是 Android 上的 ARM64 环境，插件包必须带 `aarch64` 运行时：

```bash
make runtime ARCH=aarch64      # defaults/runtime/{aria2,7z,node}/aarch64/…（或 ARCH=all 两份都下）
make package-droiddeck         # = PACKAGE_ARCH=aarch64 bash scripts/package.sh
                               # → dist-artifacts/freedeckCY-v<version>-arm64.zip

# 等价的底层调用（可额外传 PACKAGE_ARGS）
PACKAGE_ARCH=aarch64 bash scripts/package.sh
PACKAGE_ARCH=all     bash scripts/package.sh   # → ...-universal.zip（x86_64 + aarch64 都保留）
```

- `PACKAGE_ARCH` 取值：`x86_64`（默认，无后缀）/ `aarch64`（`-arm64`）/ `all`（`-universal`）；单架构打包会裁剪 `defaults/runtime/{aria2,7z,node}/*/<其它arch>`，避免包体积翻倍；插件包不包含模拟器，模拟器首次安装在线下载；
- **插件包不包含任何模拟器**（v0.10.0 起删除 `make emulator-runtime` / `scripts/fetch_emulator.sh`）：GBA/PSP/NDS/PS1/FC/MD 的官方包都首次安装时从 GitHub release 下载（需要网络），包体积约 45MB（此前含 mGBA 时约 68MB）；PS1 的 BIOS 也不随包，由用户自备（放 `~/.local/share/freedeckCY/bios/ps1/`）；
- 确认 arm64 二进制：`file defaults/runtime/aria2/aarch64/aria2c`（应显示 `ELF 64-bit … ARM aarch64`）、`ls defaults/runtime/7z/aarch64/7zz defaults/runtime/node/aarch64/bin/node`；缺哪个就重跑 `make runtime ARCH=aarch64`（模拟器不打包，无需准备）；
- 打包前可先用 `bash scripts/fetch_runtime.sh --only 7z --arch aarch64 --force` 单独补一个组件；
- 部署：把 `...-arm64.zip` 传到 DroidDeck，用 Decky 的 **Import plugin zip** 安装；首次使用、双 Steam 根与 ARM Proton 排障见 [DROIDDECK.md](DROIDDECK.md)。

`make` 还提供 `test`（跑 pytest）、`clean`（清理构建产物与 `__pycache__`）、`help`（列出全部目标）。

---

## 5. 测试

仓库用 pytest 覆盖离线可测逻辑（不联网、不写 Steam 目录）：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q

# 或者（要求 .venv 已就绪）
make test
```

说明：

- `requirements-dev.txt` 在仓库根目录，只需 `pytest` / `pytest-asyncio` / `aiohttp` 等开发依赖；**运行期依赖以 Decky 自带 Python 为准**，不要装进插件环境。
- 系统 Python 太老（如 3.9）时请用 `python3.12 -m venv .venv`（CI 使用 3.12）。`package.json` 里的 `test` 脚本也是 `python3 -m pytest -q`。
- 当前共 **585 个用例**（`make test` 实测 `585 passed`）。`tests/test_droiddeck.py` 覆盖 DroidDeck 检测、ARM Proton 解析、双 Steam 根排序与设置项读写；`tests/test_install_reliability.py` 覆盖安装前自检、已安装校验/修复、体检、失败诊断与换源；`tests/test_resume_probe.py` 覆盖 Range 续传探测与恢复重下分支；`tests/test_utils.py` 的端口相关用例依赖真实 socket 与计时，在机器高负载时可能偶发超时失败，重跑即可。
- CI 在 `.github/workflows/ci.yml` 中运行两个 job：`python`（3.12，pytest）与 `ui`（Node 20 + pnpm，`pnpm build` 并校验 `dist/index.js` 存在），触发条件为 push / pull_request。
- 新增改动建议：改 `tianyi_service.py` 的恢复/分组逻辑时，优先复用 `tests/test_install_pipeline.py` 里已有的假 aria2 脚手架。

---

## 6. 调试

### 6.1 三件套

| 目标 | 位置 / 命令 |
|---|---|
| 日志 | `/tmp/freedeckcy.log`（`config.py` 写死；`RotatingFileHandler` 5 MB × 3 轮转；`tail -f /tmp/freedeckcy.log`） |
| 状态 | `~/.local/share/freedeckCY/tianyi/state.json` |
| 健康检查 | `curl -s http://127.0.0.1:59271/_healthz` → `{"status": "ok"}` |

### 6.2 常用命令

```bash
# 健康检查 / 是否在跑
curl -s http://127.0.0.1:59271/_healthz
ss -ltnp | grep 59271

# 看下载任务（本地 HTTP API，只绑回环）
curl -s http://127.0.0.1:59271/api/tianyi/download/tasks | python3 -m json.tool

# 看面板状态（HTTP 路径，QAM 走的是 RPC）
curl -s http://127.0.0.1:59271/api/tianyi/state | python3 -m json.tool

# 看设置与 Proton 解析结果（DroidDeck 上重点看这两个字段）
curl -s http://127.0.0.1:59271/api/tianyi/settings | python3 -m json.tool
#   proton_tool          设置值（auto / none / 具体工具名）
#   proton_tool_resolved 最终会写入 config.vdf 的工具名
#   droiddeck_detected   是否检测到 DroidDeck

# 手动验证安装计划（不会下载，只探测；需先登录天翼账号）
curl -s -X POST http://127.0.0.1:59271/api/tianyi/install/prepare \
  -H 'Content-Type: application/json' -d '{"game_id":"18194"}' | python3 -m json.tool

# 过滤错误
grep -nE "ERROR|Traceback|失败" /tmp/freedeckcy.log | tail -50
```

### 6.3 直接改 `state.json` 的注意事项

- **先退出插件/停止 Decky 插件加载，再编辑**，否则内存状态会全量覆盖你的改动（`state.json` 每次保存都是整文件重写）。
- 编辑前先备份：`cp state.json state.json.bak`。
- 常用字段：`settings.download_dir`、`settings.install_dir`、`tasks`（可清空）、`installed_games`（手工删除记录时注意与磁盘目录保持一致）。
- 权限：状态目录默认 0700、`state.json` 默认 0600（内含登录 Cookie）；手工复制/替换文件后建议 `chmod 600 state.json` 保持权限。
- 想清空任务列表也可以用仓库自带脚本：`./clear_freedeckcy_tasks.sh`（默认读 `$HOME/.local/share/freedeckCY/tianyi/state.json`，可用 `FREEDECKCY_STATE_FILE` 指定，清空后自动 chmod 600）。

### 6.4 进程与端口

- 插件会拉起 `aria2c`（随机 RPC 端口 + 随机 secret）和 `7zz`（解压时短暂存在），云存档会短暂拉起 `node`。
- aria2 运行时状态在 `~/.local/share/freedeckCY/tianyi/aria2/`：`aria2-runtime.json`（RPC 地址/secret/pid）、`aria2-runtime.lock`（flock，保证只起一个实例）、`aria2.session`、`aria2.log`。插件重载时会读 meta 并附着到仍存活的 aria2，所以 gid/进度通常不丢；判断"当前实例能否被附着"就看这两个 runtime 文件 + `ps` 里 pid 是否存活。
- `aria2.log` 里能看到 RPC/下载错误（启动参数带 `--log`）；下载任务本身的错误同时记录在 `state.json` 的 `tasks[].error_reason`。
- v0.28.15 起恢复/换链前会探测 Range：日志出现 `resume unsupported` 表示该线路不支持断点续传，插件会隔离半成品（`*.freedeckcy-noresume-*`）并从 0 重下；`resume supported` 表示会保留进度换链。
- 如果 `ps aux | grep aria2c` 有残留但插件已重载，重启插件即可；`main.py` 的 `_unload()` 会停掉 aria2 和本地服务。
- 本地 Web 服务固定监听 `127.0.0.1:59271`；运行状态与端口会持久化到 Decky settings，但没有 UI 改端口，通常不需要动。

### 6.5 Steam 多库 / 自定义根目录

Steam 根目录的查找顺序（`steam_shortcuts._steam_root_candidates()`）：

1. `FREEDECKCY_STEAM_ROOT` 指定的目录（优先级最高）；
2. `~/.steam/steam`；
3. `~/.local/share/Steam`；
4. `~/.steam/root`；
5. Flatpak：`~/.var/app/com.valvesoftware.Steam/.local/share/Steam`、`~/.var/app/com.valvesoftware.Steam/.steam/steam`。

游戏库（SD 卡 / 第二块盘）来自 `libraryfolders.vdf`（同时兼容新格式 `"path"` 与旧格式 `{ "1": "/path" }`），`compatdata` 会通过 `find_compat_user_dir()` 在所有库里找，不再只认主库。

- 快捷方式 / `config.vdf` / 封面仍写入**主 Steam 根**的 `userdata/` 与 `config/`（Steam 本身就是这样组织的）；只有 Proton 前缀（`compatdata`）会跨库定位。
- 调试时可临时 export `FREEDECKCY_STEAM_ROOT=/path/to/Steam` 后重载插件；要长期生效，需要把变量加到 Decky 插件加载器进程的环境里（例如其 systemd unit 的 `Environment=`，改完重启插件加载器）。
- `compatdata` 的用户目录先找 `steamuser` / `deck` / `root`，找不到再对自定义 Wine 用户名按 `AppData` / `Documents` / `Saved Games` 目录打分（整合包常改用户名）。
- 写 `shortcuts.vdf` / `config.vdf` 前会生成备份 `*.freedeckcy-bak-<YYYYmmdd_HHMMSS>`（同类保留最近 12 份）；写 `shortcuts.vdf` 后还会回读校验。
- 相关代码：[steam_shortcuts.py](../py_modules/steam_shortcuts.py) 的 `_find_steam_root()` / `_steam_library_paths()` / `find_compat_user_dir()` / `_backup_file()` / `_shortcut_tokens()`。

### 6.6 `make doctor` 环境诊断（v0.1.1）

一条只读命令收集排障需要的全部环境信息，适合让用户在 Steam Deck 上直接跑：

```bash
make doctor                               # 等价于 bash scripts/doctor.sh
bash scripts/doctor.sh --plugin-dir /path/to/freedeckCY   # 诊断指定插件目录
bash scripts/doctor.sh --help             # 查看参数
```

输出分 8 段（`系统 / Python / 运行时二进制 / Steam / 状态文件 / 日志 / 本地服务 / 网络`）：

| 段 | 看什么 |
|---|---|
| 系统 | `plugin_dir`、kernel、架构（运行时目录用 `x86_64` / `aarch64`） |
| Python | `python3` 版本是否 ≥ 3.10（Decky 要求） |
| 运行时二进制 | aria2c / 7zz / node 的内置路径与大小、`file` 类型；缺失时提示是否回退系统命令或需 `make runtime` |
| Steam | Steam 根目录、`libraryfolders.vdf` 里的库路径、`userdata` 用户目录 |
| 状态文件 | `state.json` 大小/权限、登录态、任务数（error/waiting）、已安装记录、下载/安装目录 |
| 日志 | `/tmp/freedeckcy.log` 大小与最近 5 条 `ERROR/Exception/失败` |
| 本地服务 | 端口 59271 是否监听、`/_healthz` 是否 200 |
| 网络 | `cloud.189.cn` 连通性与 HTTP 状态码 |

说明：脚本**只读**，不改任何文件；支持 `FREEDECKCY_STATE_FILE` / `FREEDECKCY_STEAM_ROOT` / `FREEDECKCY_PORT` / `DECKY_PLUGIN_DIR` 覆盖默认路径。排障流程建议先让用户附上 `make doctor` 输出，再要日志。

### 6.7 旧版网页库、已安装与诊断调试（历史，v0.5.0）

> 当前主入口是 §6.14 的 Decky 原生库；本节保留给旧版 Vue 网页库/HTTP API 调试。

**新接口调试示例**：

```bash
# 浏览全部资源（空 q）+ 排序（"" / title / size_desc / size_asc / platform）
curl -s 'http://127.0.0.1:59271/api/tianyi/catalog?q=&page=1&page_size=5&sort=size_desc' | python3 -m json.tool
# 同时可按 platform/category 过滤
curl -s 'http://127.0.0.1:59271/api/tianyi/catalog?q=&platform=fc&category=%E6%A8%A1%E6%8B%9F%E5%99%A8&page=1&page_size=5' | python3 -m json.tool

# 已安装列表（含 exists/platform/cover/steam_appid）
curl -s http://127.0.0.1:59271/api/tianyi/installed | python3 -m json.tool
# 启动 / 打开目录 / 卸载（POST JSON）
curl -s -X POST http://127.0.0.1:59271/api/tianyi/installed/launch      -H 'Content-Type: application/json' -d '{"game_id":"18194"}'
curl -s -X POST http://127.0.0.1:59271/api/tianyi/installed/open-folder -H 'Content-Type: application/json' -d '{"game_id":"18194"}'
curl -s -X POST http://127.0.0.1:59271/api/tianyi/installed/uninstall   -H 'Content-Type: application/json' -d '{"game_id":"18194","delete_files":true}'

# 诊断 JSON / 诊断 zip / 更新检查
curl -s http://127.0.0.1:59271/api/tianyi/diagnostics | python3 -m json.tool
curl -s -OJ http://127.0.0.1:59271/api/tianyi/diagnostics/export   # 保存 freedeckcy-diagnostics.zip
curl -s http://127.0.0.1:59271/api/tianyi/update-check | python3 -m json.tool
```

**库页快捷键**（浏览器/Steam Deck 手柄等价）：

| 输入 | 游戏库页签 | 已安装页签 |
|---|---|---|
| 方向键 / 摇杆 | 搜索框→搜索按钮→平台条→分类条→卡片，2D 移动 | 搜索框/按钮→卡片（无筛选条） |
| Enter / A | 搜索/筛选/打开安装确认 | 启动游戏（`launchInstalled()`，v0.5.0 起支持） |
| B / Esc | 关弹窗 / 回到搜索框 | 关弹窗 / 返回游戏库页签 |
| X | 切到已安装 | 切回游戏库 |
| Y | 循环排序 | 打开当前卡片安装目录 |
| O | — | 打开安装目录 |
| Delete | — | 卸载当前卡片（confirm 弹窗） |
| PageUp / PageDown、L1 / R1 | 上一页 / 下一页 | — |
| 鼠标点击卡片 | 打开安装确认 | 通过 Steam 启动游戏 |

**诊断包怎么读**：`freedeckcy-diagnostics.zip` 解压后：

- `diagnostics.json`：`version/python/system/arch/paths/runtime/steam/catalog/tasks/installed/settings/recent_errors`（`log_tail` 已移到单独文件）；
- `log-tail.txt`：`/tmp/freedeckcy.log` 末尾 300 行；
- `README.txt`：说明与提交 issue 指引。

所有文本已脱敏：HOME 替换为 `~`，`cookie/authorization/token/sessionkey/accesstoken/uid/pwd` 的值替换为 `<redacted>`；日志关键字筛出的最近 20 条错误在 `recent_errors`。先看 `runtime.*.exists`、`steam.proton_tool`、`droiddeck`、`installed.missing_paths`，再对照 `log-tail.txt`。

### 6.8 模拟器安装调试（10 平台，v0.11.0）

**平台与资产**（完整字段见 ARCH §5.10；**10 个平台全部是首次安装按需从官方 GitHub release 下载**，插件包不集成模拟器；3DS/PS2/PS3 仅 x86_64，aarch64 上目录白名单会隐藏）：

| 平台 | 模拟器 | 官方资产 URL（相对 `download_base`） | 架构 | 格式 | 启动参数 | ROM 扩展名 |
|---|---|---|---|---|---|---|
| gba | mGBA 0.10.5 | `mGBA-0.10.5-appimage-x64.appimage` / `-arm64` | x64 / arm64 | AppImage（按需下载，x64 约 25MB / arm64 约 24.6MB） | `-f <rom>` | `.gba` |
| psp | PPSSPP 1.20.4 | `PPSSPP-v1.20.4-anylinux-x86_64.AppImage` / `-aarch64` | x64 / arm64 | AppImage | `--fullscreen <rom>` | `.iso/.cso/.pbp/.elf` |
| nds | melonDS 1.1 | `melonDS-1.1-appimage-x86_64.zip` / `-aarch64` | x64 / arm64 | zip 内 AppImage | `<rom>` | `.nds/.dsi/.srl` |
| ps1 | DuckStation `latest` | `DuckStation-x64.AppImage` / `DuckStation-arm64.AppImage` | x64 / arm64 | AppImage | `-batch -fullscreen <rom>` | `.m3u/.cue/.chd/.iso/.pbp/.bin` |
| fc | Mesen2 2.1.1 | `Mesen_2.1.1_Linux_x64.zip` / `_ARM64.zip` | x64 / arm64 | zip 内单文件 `Mesen` | `/fullscreen <rom>` | `.nes/.fds/.unf/.unif` |
| md | Mesen2 2.1.1 | 同 FC（共享 `emulators/mesen/<arch>/`） | x64 / arm64 | zip 内单文件 `Mesen` | `/fullscreen <rom>` | `.md/.gen/.smd/.bin/.32x` |
| 3ds | Azahar 2126.2 | `azahar.AppImage` | **仅 x64** | AppImage（需 system files setup） | `<rom>` | `.3ds/.cci/.cxi/.app`（`.cia` 通过 `--install`） |
| ps2 | PCSX2 v2.8.2 | `pcsx2-v2.8.2-linux-appimage-x64-Qt.AppImage` | **仅 x64** | AppImage（需 PS2 BIOS） | `-batch -fullscreen <rom>` | `.iso/.chd/.cue/.bin/.gz` |
| ps3 | RPCS3 build-8d6b42e | `rpcs3-v0.0.43-20606-8d6b42e7_linux64.AppImage` | **仅 x64** | AppImage（需 PS3 固件 setup） | `--no-gui <rom>` | `.iso/.pkg/.elf/.self` |
| switch | Eden v0.2.1 | `stable.eden-emu.dev/v0.2.1/` 的 amd64/aarch64 AppImage | x64 / arm64 | AppImage（需 prod.keys+固件 setup） | `<rom>` | `.nsp/.xci` |

对应仓库：mgba-emu/mgba、hrydgard/ppsspp、melonDS-emu/melonDS、stenzek/duckstation、SourMesen/Mesen2、azahar-emu/azahar、PCSX2/pcsx2、RPCS3/rpcs3-binaries-linux、eden-emu/eden（Switch 走 `stable.eden-emu.dev`）。文件大小以官方 release 为准（各平台 `min_bytes` 会校验下载完整性）。

**前置检查 / 诊断**：

```bash
# v0.10.0 起不再需要 make emulator-runtime：首次安装会自动下载；
# 离线预置时把官方 AppImage 放到缓存目录并 chmod +x，或直接设 *_BIN 覆盖
ls -l ~/.local/share/freedeckCY/emulators/gba/<arch>/ 2>/dev/null

curl -s http://127.0.0.1:59271/api/tianyi/diagnostics | python3 -m json.tool
# 看 data.emulators.{gba,psp,nds,ps1,fc,md,3ds,ps2,ps3,switch}：
#   available / source（extracted/download/system/flatpak/env）/ name / version
#   ps1/ps2 另有 bios_required / bios_present / bios_dir；3ds/ps3/switch 有 setup_required / setup_hint
#   aarch64 上 3ds/ps2/ps3 的 available=false（"已隐藏该平台"）

# 确认目录是否按架构裁剪（aarch64 只应看到 7 个模拟器平台 + pc）
curl -s 'http://127.0.0.1:59271/api/tianyi/catalog?q=&page=1&page_size=1' | python3 -c \
  'import json,sys; d=json.load(sys.stdin)["data"]; print([p["value"] for p in d["platforms"]])'
```

**安装计划调试**（所有平台都用 openpath 的文件名在分享里分页查找）：

```bash
for gid in "<GBA game_id>" "<PSP game_id>" "<NDS game_id>" "<PS1 game_id>" "<FC game_id>" "<MD game_id>"; do
  curl -s -X POST http://127.0.0.1:59271/api/tianyi/install/prepare \
    -H 'Content-Type: application/json' -d "{\"game_id\":\"$gid\"}" | python3 -m json.tool
done
# 关注 platform、emulator（mgba/ppsspp/melonds/duckstation/mesen）、emulator_info、
# emulator_info.source（download 表示安装时自动下载）、rom_target、files[]（应只有 1 个目标文件）
# ps1 还要看 emulator_info.bios_required / bios_present / bios_dir
```

**PS1/PS2 BIOS 放置、压缩包与手工部署**：

```bash
mkdir -p ~/.local/share/freedeckCY/bios/ps1 ~/.local/share/freedeckCY/bios/ps2
cp /path/to/scph5501.bin ~/.local/share/freedeckCY/bios/ps1/     # 区域版本按需
cp /path/to/scph39001.bin ~/.local/share/freedeckCY/bios/ps2/
# 也支持压缩包：安装时会用 7zz 解到 bios/<platform>/_extracted/ 再部署
cp /path/to/ps1-bios.zip ~/.local/share/freedeckCY/bios/ps1/

# 安装后检查部署结果（setup 消息也会并入安装完成消息）
ls -l ~/.local/share/freedeckCY/emulators/<state_key>/<arch>/squashfs-root/bios/ 2>/dev/null
ls -l ~/.local/share/duckstation/bios/ ~/.local/share/PCSX2/bios/ ~/.config/PCSX2/bios/ 2>/dev/null
cat ~/.local/share/freedeckCY/emulators/<state_key>/<arch>/squashfs-root/portable.txt 2>/dev/null
# DuckStation: portable_data/settings/settings.ini
# PCSX2: inis/PCSX2.ini（[Folders] Bios / [UI] Fullscreen）
# 手工修复（示例，已存在文件不会被覆盖）：
cp -n ~/.local/share/freedeckCY/bios/ps1/*.bin ~/.local/share/duckstation/bios/ 2>/dev/null || true
cp -n ~/.local/share/freedeckCY/bios/ps2/*.bin ~/.local/share/PCSX2/bios/ 2>/dev/null || true
```

BIOS 缺失不阻断安装：安装消息/库页弹窗会提示"需要 PS1 BIOS：请把 scph*.bin 放到 …"；补上 BIOS 后重装或手工复制即可（可先 `bash launch-freedeckcy.sh` 验证 DuckStation 是否识别）。

**3DS（Azahar）Flatpak 专用（v0.14.1）**：SteamOS 3.9.5 上 Azahar AppImage 有已知问题（上游 #127 打不开、#953 Game Mode 崩溃），优先官方 Flatpak：

```bash
# 手动装 Flatpak（插件在 SteamOS 上也会自动做，失败再试 system 安装）
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y --user flathub org.azahar_emu.Azahar
flatpak run org.azahar_emu.Azahar

# 确认插件用了 Flatpak：
flatpak info org.azahar_emu.Azahar
curl -s http://127.0.0.1:59271/api/tianyi/diagnostics | python3 -m json.tool
# data.emulators.3ds.source == "flatpak"；另有 flatpak_id / flatpak_available / flatpak_installed
```

- 选路：`FREEDECKCY_AZAHAR_BIN` > 已装 Flatpak > SteamOS 自动装 Flatpak > AppImage 下载/解包；把 `FREEDECKCY_AZAHAR_BIN` 指向 AppImage 可强制回退；
- 3DS wrapper 会写 `export QT_QPA_PLATFORM=xcb` + `export SDL_VIDEODRIVER=x11`（XWayland），避免 Game Mode/Wayland 崩溃；
- system files 除 `~/.local/share/azahar-emu/sysdata` 外，还部署到 `~/.var/app/org.azahar_emu.Azahar/data/azahar-emu/sysdata`（`bios/3ds/` 的 `nand/sdmc/sysdata` 或压缩包，保留目录树）；
- **已有游戏自动修复**：后台维护首次 tick 会扫已安装 3DS 记录并重写 `launch-freedeckcy.sh`（旧 AppImage 命令 → `flatpak run`），无需重装；日志关键字 `Repaired 3DS launcher for ...` / `Repair 3DS launcher failed`。

**安装完成后检查**：

```bash
ls -l "<install_dir>/<游戏目录>/launch-freedeckcy.sh"
cat "<install_dir>/<游戏目录>/launch-freedeckcy.sh"
# gba: exec <mGBA> -f <rom>
# psp: exec <PPSSPP> --fullscreen <rom>
# nds: exec <melonDS> <rom>
# ps1: exec <DuckStation> -batch -fullscreen <rom>
# fc/md: exec <Mesen> /fullscreen <rom>

# 按需下载/解包目录（fc/md 共用 mesen；ps1/psp/nds 各自平台目录）
ls -l ~/.local/share/freedeckCY/emulators/{psp,nds,duckstation,mesen}/<arch>/
ls -l ~/.local/share/freedeckCY/emulators/<platform>/<arch>/squashfs-root/AppRun

bash "<install_dir>/<游戏目录>/launch-freedeckcy.sh"   # 脱离 Steam 手工验证
cat ~/.local/share/freedeckCY/tianyi/state.json | python3 -m json.tool | grep -A4 rom_path
# installed_games: platform、emulator、rom_path、launcher_path、steam_app_id
```

Steam 条目 Exe 是 `launch-freedeckcy.sh`，`LaunchOptions` 带 `freedeckcy:tianyi:<token>`，**Proton 映射为 none**（原生 Linux）。日志关键字：`Auto add emulator game to Steam failed`、`Auto add emulator game to Steam exception`、`Resolve emulator cover failed`。**所有模拟器都不在包内**，首次安装需要联网下载（失败会在安装消息/日志里给出 HTTP 状态或解包错误）。

### 6.9 自动云存档调试（Ludusavi + gamewatch，v0.8.0）

**清单**：`defaults/ludusavi/manifest.json.gz`（53,549 款游戏，gzip 约 2 MB / 未压缩 14 MB，MIT；来源 mtkennerly/ludusavi-manifest）。运行时只读本地文件，**不联网**。

```bash
# 重新生成清单（需要 PyYAML，仅构建时；requirements-dev.txt 已含）
pip install pyyaml            # 或 .venv/bin/pip install -r requirements-dev.txt
make ludusavi-manifest        # = python3 scripts/fetch_ludusavi_manifest.py

# 覆盖清单路径（调试/替换用）
FREEDECKCY_LUDUSAVI_MANIFEST=/path/to/manifest.json ...
```

清单转换脚本会同时更新 `defaults/ludusavi/{README.md,LICENSE}`（README 记录上游 URL、条目数、字节数、sha256）。

**匹配与诊断**：上传候选收集时先用快捷方式拿到 `compat_user_dir`/appid，再查清单；上传状态里的 `diagnostics.collect` 会给出每款游戏的 `source_strategy`：

| source_strategy | 含义 |
|---|---|
| `ludusavi` | 清单命中且 Proton 目录扫描未命中 |
| `ludusavi+proton` | 两者都命中（路径已经去重合并） |
| `proton_prefix` | 仅原有 Proton 目录扫描命中（清单未命中/未启用） |
| `install_fallback` | 无 Proton 前缀，按安装目录白名单兜底 |

`diagnostics.ludusavi = {matched, path_count}` 可确认标题/SteamID 是否命中；日志里搜 `Ludusavi 清单已加载: N 款游戏`。

**gamewatch 调试**：后台维护每 8 s 检查一次已安装游戏的运行状态。

```bash
# 手工看进程命令行（Steam 直接用脚本启动时，install_path 会出现在 cmdline 里）
cat /proc/<pid>/cmdline | tr '\0' ' '
# 或直接搜安装目录
grep -l "<install_path>" /proc/*/cmdline 2>/dev/null

# 容器/proot 没有 /proc 时，代码回退 pgrep -f（需要系统有 pgrep）
pgrep -af "<install_path>"
```

状态机：首次 poll 只建立基线，之后"运行→退出"才产 `end` 事件；游戏从已安装列表移除会清掉状态。日志关键字：`auto cloud save upload after exit game=... accepted=...`、`gamewatch poll failed`。

**自动上传开关**：设置项 `cloud_save_auto_upload` 默认 **true**；QAM「云存档上传」页有「游戏退出后自动上传」开关；也可以走 HTTP：

```bash
curl -s -X POST http://127.0.0.1:59271/api/tianyi/settings -H 'Content-Type: application/json' \
  -d '{"cloud_save_auto_upload": false}'
curl -s http://127.0.0.1:59271/api/tianyi/settings | python3 -m json.tool | grep cloud_save_auto_upload
```

触发条件：设置开启 + 已登录 + 当前没有云存档上传/自动上传任务 + 距上次自动上传 ≥ 30 s；只会把**该 game_id** 传给 `start_cloud_save_upload(game_ids=[...])`。

**指纹与重置**：指纹 = `sha256(相对路径|size|mtime_ns …)`（每个游戏最多 5000 个文件），持久化在 `state.json` 的 `cloud_save_fingerprints`。上传前相同则跳过，结果 `reason=unchanged`。想强制重新上传：退出插件后编辑 `state.json` 删除对应 `game_key` 的指纹（或删除整个 `cloud_save_fingerprints` 字段），再重载插件。

**模拟器存档（v0.15.0）**：非 PC 平台由 `py_modules/emulator_saves.py` 发现存档，接入候选 `source_strategy="emulator_saves"`。

- **标准目录**（`STANDARD_SAVE_DIRS`）：mGBA `~/.local/share/mgba/saves`（含 Flatpak `~/.var/app/io.mgba.mGBA/...`）、PPSSPP `PSP/SAVEDATA`、melonDS `saves`、DuckStation `memcards`、Mesen2 `Saves`、PCSX2 `memcards`、RPCS3 `dev_hdd0/home`、Eden `nand/user/save`、3DS `sdmc`/`nand/user/save` + Azahar Flatpak `~/.var/app/org.azahar_emu.Azahar/data/azahar/{sdmc,nand/user/save}`；
- **portable 目录**（`PORTABLE_SUBDIRS`）：相对安装根、ROM 目录、启动脚本目录、已解包模拟器目录，如 `saves`/`memcards`/`memstick/PSP/SAVEDATA`/`sdmc`；
- **单游戏**（gba/fc/md/nds）：在候选目录按 ROM 文件名 stem 找 `.sav/.srm/.dsv/...` 或同名目录；找不到返回 `game_save_not_found`，**不会退化成整目录**；
- **共享**（psp/ps1/ps2/3ds/ps3/switch）：返回整目录（空目录跳过），服务层按 `tuple(source_paths)` 签名去重，重复记录 `emulator_saves_shared`；
- **调试**：上传状态 `diagnostics.collect` 中每条的 `diagnostics.emulator_saves = {paths, platform, emulator, per_game, searched, reason}`；跳过原因 `save_dir_missing` / `game_save_not_found` / `emulator_saves_shared` / `emulator_saves_disabled`；
- **开关**：设置 `cloud_save_include_emulators` 默认 true；QAM「云存档上传 → 包含模拟器存档」，或 HTTP：

```bash
curl -s -X POST http://127.0.0.1:59271/api/tianyi/settings -H 'Content-Type: application/json' \
  -d '{"cloud_save_include_emulators": false}'
curl -s http://127.0.0.1:59271/api/tianyi/settings | python3 -m json.tool | grep include_emulators
```

- **隐私/大小**：3DS（`sdmc`/`nand`）与 Switch（`nand/user/save`）目录可能很大，会受指纹 5000 文件与上传体积限制；共享记忆卡会包含同卡其它游戏，上传前确认目录内容；
- **恢复**：v0.16.0 起支持（见下节）；PS1/PS2 单片记忆卡、Switch 目录不能按游戏拆，覆盖前有备份、冲突需确认。

**模拟器存档恢复（v0.16.0）**：

- 恢复计划：`plan_cloud_save_restore` 遇到 manifest `source_strategy="emulator_saves"` → `_plan_emulator_save_restore()`；按已安装记录的平台根生成 `copy_pairs`/`plan_items`，目标冲突会带 `conflict_count`/`conflict_samples` 与 `requires_confirmation`；
- **目标白名单**：`restore_roots(record)` 返回平台标准/portable 根；`build_restore_targets(record, entries)` 只允许写入这些根——同机 `source_path` 父目录在根内则恢复到原父目录，跨机落到第一个根；拒绝 manifest 任意 HOME 路径；
- **备份**：apply 沿用现有恢复流程，覆盖前生成 `*.freedeckcy-bak-<YYYYmmdd_HHMMSS>`；
- 状态/诊断字段：`stage=ready`、`requires_confirmation`、`conflict_count`、`conflict_samples`、`target_candidates`、`entry_target_dirs`；
- 边界：PS1/PS2 单片记忆卡、Switch 目录不能按游戏拆；3DS 跨设备可能退化到根目录；共享卡覆盖需要确认。

**按游戏拆分调试（v0.16.0）**：

```bash
# PSP/PS3：存档目录里应有 PARAM.SFO；TITLE 与游戏标题做归一化匹配
find ~/.local/share/ppsspp ~/.config/rpcs3 -name PARAM.SFO 2>/dev/null
python3 - <<'PY'
import sys; sys.path.insert(0, "py_modules")
from param_sfo import read_param_sfo
print(read_param_sfo("<PARAM.SFO 路径>").get("TITLE"))
PY

# 3DS：NCSD 头 0x100 起 16 字节，Program ID 在 0x108（小端 8 字节）
xxd -s 0x100 -l 16 "<game>.3ds"
# 目录：.../title/00040000/<low8>/
```

上传候选里 `emulator_saves.per_game=True` 表示拆分成功；`False` 表示回退共享目录。拆分失败原因看 `searched`/`reason`（无 PARAM.SFO/TITLE 不匹配/NCSD 读不到都会回退，不是错误）。

**PS1 多碟 m3u（v0.16.0）**：`find_rom_file()` 对 PS1 先找 `.m3u`（已有直接用）；没有且多于一张 `.cue/.chd` 时按自然排序生成 `<共同父目录>/freedeckcy-multidisc.m3u`（相对路径、`#EXTM3U`），单碟仍返回 `.cue`；可手工检查/重排：

```bash
cat "<install_dir>/<游戏>/freedeckcy-multidisc.m3u"
# 顺序不对可直接编辑，或删掉让插件按自然排序重新生成；已存在的 m3u 不会被覆盖
```

### 6.10 游戏提交校验与合并（v0.13.0）

**主文档**：[submissions/README.md](../submissions/README.md)（字段表、规则、Issue/PR 两种方式）；本节只列开发/维护者命令与排查。

**入口**：GitHub Issue 表单 [.github/ISSUE_TEMPLATE/submit-game.yml](../.github/ISSUE_TEMPLATE/submit-game.yml)，或 `submissions/*.json`（复制 `submissions/examples/example-pc.json` / `example-switch.json`，按 [schema.json](../submissions/schema.json) 填）；网页库工具栏「提交游戏」按钮直接打开 Issue 模板。

**命令**：

```bash
make validate-submissions                  # 等价 python3 scripts/validate_submissions.py
python scripts/validate_submissions.py --json
python scripts/merge_submissions.py --dry-run          # 默认就是 dry-run，不写文件
python scripts/merge_submissions.py --apply            # 写 CSV + 移动 JSON 到 submissions/merged/
python scripts/merge_submissions.py --apply --json
python -m pytest tests/test_submissions.py -q
make validate-catalog                      # 合并后再跑目录体检
```

**校验规则**（`py_modules/submission.py`，详见源码/README）：

- 平台别名：`windows/win→pc`、`ns→switch`、`3d→3ds`、`psx/playstation→ps1`、`genesis→md` 等；最终只接受 11 个平台；
- 必填 `name/platform/share_url/openpath`；`openpath` 必须是分享内相对路径、不能含 `..`；
- `share_url` 支持天翼 `https://cloud.189.cn/...`（`/t/<shareCode>`、`/web/share?code=`）或百度分享链接；`access_code` 4–8 位字母/数字（链接已有 `pwd=` 可空）；
- `filesize_z` 非负整数；`executable_name` 仅 PC（模拟器留空只会 warning）；
- 重复 shareCode：同时对比目录 CSV 已有行与本批其它提交；重复是 ERROR；
- 没有 `submissions/*.json` 时校验通过（CI 不红）。

**合并行为**：只有整批无 ERROR 才写；`--apply` 用临时文件 + `os.replace` 原子替换 CSV，`game_id` 取当前最大 +1，标题为 `中文/英文`，`server="t"`、`down_url` 补 `pwd`、`category_parent` 默认 5；成功后 JSON 移到 `submissions/merged/`，并追加 `submissions/merged/index.json`。

**CI**：`.github/workflows/ci.yml` 的 `Validate game submissions` 步骤跑 `python scripts/validate_submissions.py --catalog ...`，无提交也通过。

### 6.11 百度网盘（扫码/Cookie 主链路，v0.17.0；OpenAPI 可选回退）

**模块**：`py_modules/baidu_qr.py`（Passport 扫码）、`py_modules/baidu_client.py`（Cookie 分享解析/直链）、`py_modules/baidu_openapi_client.py`（OpenAPI 回退）。服务层 `_share_provider()` 识别百度链接；安装计划**优先 Cookie，其次 OpenAPI，再提示扫码**。**不接 CDP/网页接口逆向**。

**扫码登录（QAM 推荐）**：

1. QAM「百度网盘（扫码登录）」→「扫码登录百度网盘」，插件请求 `https://passport.baidu.com/v2/api/getqrcode?lp=pc&qrloginfrom=pc` 并显示二维码（`data:image/png;base64`，session 内存 180s）；
2. 用百度 App/百度网盘 App 扫码，QAM 会从 waiting→scanned（已扫码待确认）→success；
3. 成功后 Cookie 写入 `state.json` 的 `baidu_login`（`BDUSS=...; STOKEN=...; PTOKEN=...`），可安装百度分享；「退出百度网盘」清空。

**点击反馈与超时（v0.23.0）**：点击「扫码登录百度网盘」立即 toast「正在获取百度二维码...」；前端 `withTimeout`（start 20s、poll 15s），后端 `wait_for(request_qr, 12)` + 图片 `wait_for(..., 10)`，超时提示"获取百度二维码超时（网络/TLS 可能受阻...）"。复现/排查：看 `/tmp/freedeckcy.log` 的 `Baidu QR start requested`、`Baidu QR ready sign_len=`、`Baidu QR request timed out`/`failed`；只记 sign 长度不记 sign/cookie。前端超时看 QAM toast 与 `withTimeout` 文案。

**扫码错误诊断（v0.18.0）**：

- `request_qr()` 直接请求 `getqrcode`；v0.19.1 起 aiohttp 会依次尝试系统证书、跳过证书校验，仍失败则回退 urllib（部分 Decky/SteamOS 环境 aiohttp TLS 不可用）；v0.19.2 起 `fetch_qr_image/poll_qr/complete_login` 也做同样的 TLS 回退；错误消息带具体异常类型/HTTP 状态/响应片段；
- HTTP 非 200 时错误消息带状态码/响应片段（如 `获取百度二维码 HTTP 403: ...`）；轮询遇到 HTTP ≥400 或连接重置/DNS/SSL 等**非超时**错误返回 `status=error`，服务层转 `stage=failed` 并在 QAM 显示具体原因，不再一直 waiting；超时仍视为 waiting；
- `start_baidu_qr_login` 的异常会写日志 `Baidu QR request failed: ...` 并返回"获取百度二维码失败：<原因>"；`poll_baidu_qr_login` 的 `stage` 可能是 waiting/scanned/success/expired/failed；
- 调试：看 QAM 二维码区/提示、`/tmp/freedeckcy.log` 里的 `Baidu QR` 关键字、以及 `/api/tianyi/baidu/qr/poll` 返回的 `stage/message`。

HTTP/手动调试（不依赖 QAM）：

```bash
curl -s -X POST http://127.0.0.1:59271/api/tianyi/baidu/qr/start | python3 -m json.tool
# 返回 qr_data_url / qrcode_url / expires_at
curl -s http://127.0.0.1:59271/api/tianyi/baidu/qr/poll | python3 -m json.tool
# stage: waiting / scanned / success / expired / failed
curl -s -X POST http://127.0.0.1:59271/api/tianyi/baidu/qr/cancel
curl -s -X POST http://127.0.0.1:59271/api/tianyi/baidu/clear
```

底层接口（调试用；`sign`/`v` 来自上一步返回）：

```bash
# 1) 取二维码
curl -s 'https://passport.baidu.com/v2/api/getqrcode?lp=pc&qrloginfrom=pc' | python3 -m json.tool
# 2) 轮询（channel_id 即 sign；长轮询，空响应/errno=1 表示 waiting）
curl -s 'https://passport.baidu.com/channel/unicast?channel_id=<sign>&tpl=pp&tt=<ms>' 
# 3) 手机确认后，用返回的 v 换 Cookie
curl -s 'https://passport.baidu.com/v3/login/main/qrbdusslogin?bduss=<v>&qrcode=1&tpl=pp&apiver=v3&tt=<ms>&time=<ms>&alg=v3&elapsed=1'
```

**确认 Cookie 生效**：

```bash
curl -s http://127.0.0.1:59271/api/tianyi/settings | python3 -m json.tool | grep -A3 baidu_login
# state.json 里应有 baidu_login.cookie（注意不要外传；文件 0600）
# 准备百度分享 → 安装计划应返回 provider="baidu"，不再要求开放平台 App Key
```

任务会带百度 Cookie + `Referer=https://pan.baidu.com/disk/home` + `UA=pan.baidu.com`；重试/补下会重新取直链。

**OpenAPI 回退（可选，需开发者资质）**：QAM「百度网盘 OpenAPI（可选）」里填 App Key/Secret → 获取授权链接 → 粘贴授权码；或 env `FREEDECKCY_BAIDU_OPENAPI_APP_KEY` / `SECRET_KEY` / `REFRESH_TOKEN`。只有**没有 Cookie 时**才走这条链路，且分享文件需要转存 `/FreedeckTmp`（安装后清理）。

**测试/mock**：`python -m pytest tests/test_baidu_integration.py tests/test_baidu_openapi_client.py tests/test_baidu_client.py -q`；扫码测试 mock `request_qr`/`fetch_qr_image`/`poll_qr`/`complete_login`，不访问真实百度。

**排障**：

| 现象 | 处理 |
|---|---|
| 二维码不显示/获取失败 | 看 `/baidu/qr/start` 返回；网络需能访问 `passport.baidu.com`；图片下载失败时用返回的 `qrcode_url` 手工打开 |
| 一直 waiting | 手机未扫码/未登录百度 App；刷新二维码重试；长轮询超时是正常行为 |
| scanned 后失败/过期 | 二维码 180s 过期或手机未确认；重新扫码；失败信息看 poll 返回 |
| 扫码成功但安装仍提示未登录 | 确认 `state.json` 的 `baidu_login.cookie` 含 `BDUSS=`；`/api/tianyi/settings` 的 `baidu_login.logged_in` 应为 true；必要时清空后重扫 |
| Cookie 失效 / 直链 403 | Cookie 过期/风控，重新扫码；aria2 已带百度 Cookie/Referer/UA，403 多为直链过期/风控 |
| 想用 OpenAPI 而不是扫码 | QAM 清空百度登录（或不要扫码），配置 OpenAPI 应用并授权；安装计划会在无 Cookie 时回退 OpenAPI |
| 为什么不做 CDP | 不逆向网页接口；Cookie 只通过百度 Passport 官方扫码（`getqrcode/unicast/qrbdusslogin`）获取 |

### 6.12 扫描已安装游戏（v0.18.0；v0.21.0 入口迁移 + 自动补 Steam）

**用途**：插件重装/state 丢失/游戏是旧版本或手动安装时，把 `settings.install_dir` 里已有的游戏补回「已安装」列表，并自动补齐 Steam 快捷方式。**v0.21.0 起入口在 QAM 设置 → 安装 → 「扫描已安装游戏」**（原生库已安装页不再有扫描按钮；网页库按钮保留为备用）。

**命令/API**：

```bash
curl -s -X POST http://127.0.0.1:59271/api/tianyi/installed/scan | python3 -m json.tool
# 返回：scanned / added_count / added_games / skipped_count / unresolved_count / unresolved_dirs / installed_total / message
```

QAM 设置页点「扫描已安装游戏」（`onScanInstalledSettings`），toast 显示"已补回 N 个…（自动加入 Steam：M）"；网页库「已安装」工具栏「扫描已安装」（`app.js` 的 `scanInstalled()`）作为备用。

**匹配规则**：

- 只扫 `settings.install_dir` **一层子目录**（最多 500 项），跳过隐藏目录和 `compatdata/steamapps/downloads/lost+found/.freedeckcy/.cache`；
- 目录名经 `_normalize_scan_title()`（小写、去分隔符）与目录条目标题（`[/|｜]` 拆段）做等值/前缀匹配，取最长；已记录 path → `already_recorded`，已记录 game_id → `game_id_recorded`；
- 匹配到 Steam 快捷方式（`list_all_shortcuts_sync()` 的 app_name 归一化/同 exe realpath）回填 `steam_app_id`，不重复添加；模拟器平台用 `find_rom_file()` 找 ROM（找不到也建记录，`rom_path` 空）；
- **没有快捷方式时自动补建**（v0.21.0）：
  - PC：`_find_scanned_executable()` 优先 `entry.openpath` 的 .exe，否则递归找 .exe（排除 `unins/setup/redist/vcredist/crashreport/dxsetup`，按标题/目录名/大小排序），再 `add_or_update_tianyi_shortcut()`；
  - 模拟器：`ensure_emulator(platform, allow_download=False)`（**不自动下载**）+ `create_launch_wrapper()` 生成 `launch-freedeckcy.sh`，注册原生快捷方式（Proton=none）；模拟器未安装记 `shortcut_error=emulator_not_ready: ...`，ROM 找不到记 `rom_not_found`；
  - **第二遍**：已有记录但 `steam_app_id=0` 的 PC 也补建，结果在 `steam_recovered`；
- 返回字段：`added_count/added_games`（每条含 `steam_added`/`shortcut_error`）、`steam_recovered_count/steam_recovered`、`skipped_count/unresolved_dirs/installed_total/message`；
- 未匹配进 `unresolved_dirs`，原因 `catalog_no_match`/`catalog_missing_game_id`。

**手工检查 Steam 快捷方式**：`shortcuts.vdf` 在 `<Steam>/userdata/<id>/config/shortcuts.vdf`（二进制 VDF，插件写前备份、写后回读）；日志搜 `扫描补 Steam 快捷方式失败`。**新快捷方式需要重启 Steam/切换用户/重开库页才可见**——插件只写文件，不重启 Steam。

**排障/日志**：

- 扫描后没新增：确认安装目录设置正确、游戏目录名与目录标题能对上（改名/英文名差异会 no_match）、不是嵌套目录、不是 0 字节目录；
- 想确认运行细节：看 `/tmp/freedeckcy.log` 的 `scan`/`已安装` 关键字与接口返回的 counts；
- 扫描**只补记录**，不会创建 Steam 快捷方式；快捷方式缺失需重新安装/重新注册。

### 6.13 存储位置选择（SD 卡，v0.19.0）

**用途**：把下载/安装目录一键切到 SD 卡/外置存储。

**命令/API**：

```bash
curl -s http://127.0.0.1:59271/api/tianyi/storage/options | python3 -m json.tool
# data.internal / data.external[] / data.options[] / data.download_dir / data.install_dir
# external 项：kind/label/mount/download_dir/install_dir/free_text/total_text/...
python -m pytest tests/test_storage_options.py -q
```

QAM「设置 → 路径」：下载目录/安装目录下会按外置挂载渲染「下载到 SD 卡 / 外置：<label>（剩余 X）」「安装到 …（剩余 X）」，点击即 `savePatch` 切换并刷新；没有外置时显示"未检测到可写 SD 卡/外置存储（请先在 SteamOS/系统中挂载）"；原「选择下载目录/安装目录」保留。

**检测规则**（`storage_options.detect_storage_options`）：

- 解析 `/proc/mounts`（`\040` 等转义会还原）；候选前缀 `/run/media/`、`/media/`、`/mnt/`、`/storage/`、`/sdcard`；
- 跳过 `proc/sysfs/tmpfs/overlay/squashfs` 等系统 fstype 与 `/`、`/run`、`/mnt`、`/media`、`/storage`、`/sdcard` 挂载根；
- 必须存在、可写、`disk_usage` 有 total 才收录；realpath 去重；容量用 `shutil.disk_usage`；
- 外置建议目录 `<mount>/freedeckCY/downloads`、`<mount>/freedeckCY/installed`；内置 `~/Downloads/freedeckCY`、`~/Games/freedeckCY`。

**常见问题**：

| 现象 | 处理 |
|---|---|
| SD 卡不显示 | 确认已在 SteamOS/系统里挂载（`/run/media/...`）且可写；`/proc/mounts` 里能看到；只读/未挂载不会出现 |
| `/mnt` 被过滤 | 挂载根本身（`/mnt`）会跳过，但子挂载如 `/mnt/sdcard` 会显示；可手动查看 `mount | grep /mnt` |
| 切过去后路径不存在/不可写 | 插件不会自动 mkdir/挂载/格式化；先确认挂载点可写，必要时手动 `mkdir -p <mount>/freedeckCY/{downloads,installed}` |
| 容量不对 | 容量是检测时快照；重新打开路径页/重载插件刷新 |

### 6.14 Decky 原生游戏库与 Steam Deck 输入（v0.20.0；v0.27.20）

**入口**：QAM 主页「游戏库」→ `Router.CloseSideMenus()` → `showModal(<LibraryPage />)`；modal 失败才 `Navigation.Navigate("/freedeckcy/library")`。`routerHook.addRoute` 仍注册全屏入口，卸载移除。旧版 Vue 网页库只作桌面调试/回退。

**页面结构（v0.27.20）**：

- 顶部栏：返回 / Steam 库 / 标题 / 游戏库 / 已安装 / 刷新（普通流式，非 sticky）。
- 搜索：placeholder「搜索游戏」+ 搜索 / 筛选按钮；筛选面板含平台/分类/排序 chip。
- 默认 Hero + 最近更新 + 分类横向货架；搜索/筛选后显示封面网格；卡片含来源/已安装角标。
- 详情：`GameDetailModal` + `showModal`；下载源选择、固定「安装/退出」操作栏。
- 每页 30 条 + 「加载更多」；已安装页签卡片支持启动/目录/卸载。
- QAM 不再显示 `QAM 原生 UI v...` 标识；版本以 Decky 插件列表和 `package.json` 为准。

**手柄/触控板（v0.27）**：

| 输入 | 行为 |
|---|---|
| 方向键 / 左摇杆 | 在 `flow-children` 分组内左右/上下移动；焦点卡片自动滚动到可视区 |
| A | 激活当前按钮/卡片/筛选 chip |
| B | 关闭详情；游戏库内退出（`onCancel`） |
| L1/R1 | 切换「游戏库 / 已安装」 |
| L2/R2 | 游戏库/详情内容约 0.8 屏滚动 |
| 触控板 / 触摸 | 纵向列表、横向货架滚动；按钮/卡片可点击 |
| 搜索框 | A 聚焦后输入，Enter 提交 |

**布局调试要点**：

- 顶部固定 60px 遮罩 → 卡片 `scroll-margin-top:84px`，避免焦点卡顶部/蓝框被裁。
- 货架 `overflow-x:auto` + 焦点 `outline:2px` → 顶部/左右 padding 10/16px，取消 scroll-snap/overflow-anchor，避免最左卡焦点环被裁。
- 详情弹窗 `margin-top:40px` 避开状态栏，`max-height:calc(100vh - 150px)`，操作栏独立固定在底部。
- 搜索框必须用 placeholder（不要 label），搜索/筛选按钮才会和输入框同高。
- 更新按钮用 DialogButton + Focusable row，不要用两个独立 ButtonItem。

**真机 CEF 验证**（Steam Deck，CEF 8081）：

```bash
# 列出 targets；选择「Steam 大屏幕模式」
curl -s http://<deck-ip>:8081/json/list
# 在目标页 Runtime.evaluate：
# document.querySelector('.gpfocus') / '.fdc-root' / '.fdc-shelf'
# 方向键用 Input.dispatchKeyEvent 发送 ArrowUp/Down/Left/Right 验证焦点环
```

检查项：

1. 最左卡焦点环左右完整；
2. 焦点卡顶部蓝框/封面不被状态栏裁；
3. A/B/左右/上下可用；
4. 详情「安装/退出」完整可见；
5. 搜索/筛选/更新按钮同排。

**callable**：`list_tianyi_catalog`、`prepare_tianyi_install`、`start_tianyi_install`、`list_tianyi_installed_games`、`launch_tianyi_installed_game`、`open_tianyi_installed_folder`、`scan_tianyi_installed_games`。

**常见问题**：

| 现象 | 处理 |
|---|---|
| 点「游戏库」仍打开网页/无页面 | 确认插件版本 ≥0.27.20、前端 dist 已更新、Decky 已重载；fallback 会走全屏 route |
| 左右键不能移动 | 检查横向区域是否有 `DFL.Focusable flow-children="row"`；普通 div 不够 |
| 最左卡焦点环被裁 | 货架需 `padding-left:16px`、`scroll-snap-type:none`、`overflow-anchor:none`；卡片聚焦用自定义最近可见滚动，不要 `inline:"center"` |
| 顶部蓝框/封面被裁 | 货架顶部 padding 10px，卡片 `scroll-margin-top:84px` |
| 详情按钮被裁/溢出 | 详情 `margin-top:40px`、`max-height:calc(100vh - 150px)`、内容滚动区与操作栏分离 |
| B 无反应 | 详情根节点必须 `DFL.Focusable onCancel=...`；库根节点也有 onCancel |
| 更新按钮错位/不能左右 | 两个按钮必须同一个 `Focusable flow-children="row"` + DialogButton，不能用两个 ButtonItem |
| 搜索/筛选低一截 | 搜索框用 placeholder，不要 label；按钮 `align-items:center` |

### 6.14.1 双语界面调试（v0.28.14）

- 语言 key：`localStorage["freedeckcy.language"]`，值为 `zh` 或 `en`；首次打开无值会先显示语言选择。
- 清空语言重新测试：在 CEF 中执行 `localStorage.removeItem("freedeckcy.language")`，重载插件。
- 翻译范围：带 `data-fdc-i18n` 的根节点（QAM 内容、设置、原生库、详情）；新增根节点时记得加属性，否则不会被翻译。
- 修改文案后更新 `src/i18n.en.ts` 对应 key；运行 `pnpm build` 重载插件。
- 调试：CEF 中 `localStorage.setItem("freedeckcy.language","en")` + 重载，检查 QAM/设置/游戏库/详情四处。语言切换入口在 QAM 主页和设置页各一处，切换后立即翻译/恢复。
- 诊断属性：`document.documentElement[data-fdc-i18n-observer]` 应为 `ready`；没有时检查 `useI18nRoot` 是否挂到真实根节点、root 的 `ownerDocument` 是否是 QAM/BigPicture 文档。
- Toast：`toaster.toast` 已包装翻译 title/body；检查更新/下载更新/自检弹窗应英文。
- 词表 434 条（`src/i18n.en.ts` + `src/i18n.missing.ts`）；新增中文 UI 后要同时补词表，否则只走短语兜底。

### 6.15 诊断自检（v0.22.0）

**QAM 设置 → 诊断**：「运行自检」调 callable `run_tianyi_diagnostics`；「导出诊断包」调 `export_tianyi_diagnostics_file`（写到下载目录并 toast 路径）。

**命令/API**：

```bash
curl -s -X POST http://127.0.0.1:59271/api/tianyi/diagnostics/run | python3 -m json.tool
# 返回 version/arch/summary{ok,warn,fail,skip}/checks[{id,label,status,detail,fix}]
```

**检查项**：plugin（版本/目录）、state_dir（可写/权限）、download_dir/install_dir（存在/可写/剩余空间，<2GB warn）、runtime_aria2/7z/node（存在+可执行+`--version`/`i`，5s）、catalog（条数/平台/封面）、steam（root + `list_all_shortcuts_sync` 数量）、storage（SD/外置挂载）、network_tianyi（GET cloud.189.cn）、baidu_qr（`request_qr()` 12s，只输出 sign 长度）、tasks（失败/已安装）、log（末尾 300 行 ERROR/Exception/失败 数）。

**导出包**（`export_diagnostics_to_downloads`）：`diagnostics.json` + `self-check.json` + `log-tail.txt` + `README.txt`，写到 `settings.download_dir`（空则插件 downloads 目录，再退 `~/Downloads`），文件名 `freedeckcy-diagnostics-YYYYmmdd-HHMMSS.zip`，权限 0600。

**常见失败项**：

| 检查 | 处理 |
|---|---|
| runtime_* fail | 包内 `defaults/runtime/<component>/<arch>/` 缺失/不可执行；重装插件包或 `make runtime` 后重打包 |
| steam warn/fail | Steam 未登录/`userdata` 不可读；确认 `FREEDECKCY_STEAM_ROOT` 指向正在运行的客户端 |
| state_dir fail | `~/.local/share/freedeckCY` 权限/磁盘；修复后重跑 |
| download/install warn | 剩余 <2GB 或不可写；清理空间/换 SD 卡/重新选目录 |
| baidu_qr fail | 网络/DNS/证书；v0.19.2+ 有 TLS 回退；看 detail 里的异常类型 |
| network_tianyi warn | 网络/代理/DNS；不影响本地功能，但安装需联网 |

**测试**：`python -m pytest tests/test_diagnostics.py -q`（`include_network=False` 的结构用例）；自检不自动修复。

### 6.16 库页时长块隔离（v0.25.0）

**目标**：Steam 原有游戏详情页不再出现 freedeckCY 的「已玩时长 / 主线 / 总时长」块；只有插件安装/补录的游戏才显示。

**验证方法**：

1. **Steam 原有游戏**：打开一个非 freedeckCY 安装的 Steam 游戏详情页 → 不应出现时长块（也不应短暂出现"加载中"）；
2. **插件安装游戏**：打开通过安装/扫描补录的游戏详情页 → 应出现「我的游玩 / 主线 / 总时长」块；
3. **接口层**：`get_library_game_time_stats(app_id=<原版游戏>, title=...)` 应返回 `managed=false`、`reason="not_managed"`、全 0，且日志里没有 HLTB 查询；`app_id=<插件游戏>` 返回 `managed=true`。

**匹配顺序**：先 `_resolve_installed_record_by_app_id()` 按 AppID 精确匹配 → 未命中才按标题归一化（`_normalize_cover_text`，双向包含）；AppID 优先用于避免同名 Steam 游戏误判。

**测试**：`python -m pytest tests/test_diagnostics.py -q`（`test_library_time_stats_unmanaged_games_get_no_hltb`：未托管 → `managed=false` 且不查 HLTB）。

**排障**：原版游戏仍出现块 → 确认前端 `dist` 是 v0.25.0+、Steam 库页是否缓存旧 patch（重启 Steam/重载插件）；插件游戏不出现块 → 检查该游戏是否在 `installed_games`、AppID/标题是否匹配；HLTB 查询失败只影响块内数值。

---

## 7. 常见故障排查---

## 7. 常见故障排查

| 现象 | 原因 / 处理 |
|---|---|
| 下载报 **"下载组件不可用：未找到内置 aria2c 或系统 aria2c"** | 缺 aria2c。执行 `make runtime`（或 `bash scripts/fetch_runtime.sh --only aria2`），或安装系统 aria2；也可用 `FREEDECKCY_ARIA2_BIN` 指定路径。检查 `defaults/runtime/aria2/<arch>/aria2c` 是否可执行 |
| 解压报 **"解压组件不可用"** | 缺 7zz。执行 `make runtime`（或 `--only 7z`），或安装系统 7z；也可用 `FREEDECKCY_7Z_BIN` 指定路径 |
| 云存档提示 **缺少 node / 未找到 node 运行时** | 执行 `bash scripts/fetch_runtime.sh --only node`（等价于只补 node；`make runtime` 会全下）；或安装 node ≥ 18，或用 `FREEDECKCY_NODE_BIN` 指定。注意云存档上传**一定走 node**，SteamOS 默认不带 node |
| 装完 **Steam 库里没有游戏** | ① 写 `shortcuts.vdf` 后必须**重启 Steam**；② 如果安装时 Steam 正在运行，Steam 退出时可能回写覆盖 `shortcuts.vdf` —— 重新安装该游戏一次即可（写前备份在 `shortcuts.vdf.freedeckcy-bak-<时间戳>`，可手工回滚）；③ 打开 `/tmp/freedeckcy.log` 搜"Steam 导入失败"或"回读校验失败"看具体原因；④ 多盘位 / Flatpak 环境可用 `FREEDECKCY_STEAM_ROOT` 指定根目录 |
| 装完点启动 **没反应** | exe 定位是启发式的（openpath → 叶子名搜索 → 目录里第一个可执行文件）。检查安装目录里的 exe 是否正确，必要时改 CSV 的 `openpath` 或手工在 Steam 里改目标 |
| **端口 59271 被占用** | 本地服务启动失败并提示"端口已被占用"。先找占用进程：`ss -ltnp \| grep 59271`；常见是上一个插件实例没退干净——重载/重启插件；或换掉其他占用进程 |
| **SD 卡 / 第二块盘上的游戏识别不到** | 当前版本会扫描 `libraryfolders.vdf` 与 Flatpak 路径；仍失败时：① 确认目标盘存在 `steamapps/compatdata/<appid>/pfx`；② 用 `FREEDECKCY_STEAM_ROOT` 指定 Steam 根；③ 看日志里的"读取 libraryfolders.vdf 失败" |
| 云存档恢复覆盖错了 / 想回滚 | 恢复时会先把同名文件/目录改名为 `*.freedeckcy-bak-<YYmmdd_HHMMSS>`，到对应目录手工改回即可 |
| 卸载后 **Proton 前缀还在占盘** | 卸载默认只删游戏文件。重新卸载时在确认框选「连 Proton 前缀一起删」；若按钮没出现，说明没解析到 AppID/前缀（先用 `make doctor` 看 Steam 段与 `state.json` 的 `steam_app_id`） |
| 卸载报了 **Proton 前缀路径校验失败 / 只清了一部分** | 只自动删除 `<library>/steamapps/compatdata/<appid>` 结构；符号链接、跨库残留或 AppID 对不上会跳过并在 `warning` 里说明，可手工核对后删除 |
| 解压报 **归档校验失败** | `7z t` 失败会先隔离坏包并自动重下一次（每任务一次），完成后继续安装；第二次仍失败则任务标 failed，用任务行「重试」按钮。日志关键字 `Archive validation failed, re-download scheduled` |
| **7z 不可执行 / 校验被跳过** | `7z t` 是 best-effort：找不到 7z（或 macOS 上跑 Linux 版 7zz 报 `Exec format error`）会返回"跳过校验"，**不阻断安装**；但真正解压仍需可用 7z，否则会在解压阶段报"解压组件不可用" |
| 失败任务 **想再试一次** | `status=error` 或 `install_status=failed` 的任务行有「重试」按钮：文件已完整则直接重装（不重下），否则重新取直链下载；直链取不到通常是登录失效，先重新扫码登录 |
| 插件重启后 **下载任务卡住/被判失败** | 插件重载通常会附着到仍存活的 aria2（gid 不变，见 6.4 进程与端口）；**设备重启**后 aria2 会话重建、gid 会变。恢复链：按文件路径重新认领 gid → 文件已完整则直接判完成 → 会话丢失则用原直链 `changeUri` 原地换链 / 重新 addUri（每任务每进程一次）→ 连续 5 次才标 error。若仍失败：移除该任务后从库页重新下载（支持续传） |
| 下载完成但 **一直不安装** | 当前版本有后台维护（启动先跑一次，之后每 8 s），即使 QAM 面板没打开也会推进。若卡住：① 分卷/多包场景需要**整组都 complete** 才安装，检查同 `group_id` 的其它任务；② 看日志里的 `Maintenance` / 解压报错；③ `post_processed=false` 且 `status=complete` 的任务会在下次维护时重试；必要时停插件后把该字段改回 `false` 再重载触发 |
| 下载完成但报 **"文件大小校验失败"** | 清单里的 `file_size` 与实际落盘大小不一致（下载不完整/文件被替换）。当前版本会先自愈一次：把坏文件隔离为 `*.freedeckcy-size-mismatch-<时间戳>` 并用原直链重下，仍失败才标 error；此时移除任务重下。反复出现说明分享里的文件已变化，需要更新资源清单 |
| 解压报 **"下载内容疑似网页错误页"** | 天翼登录态失效时直链可能返回 HTML 登录页。预检会拒绝解压并提示；重新扫码登录，移除任务后重下 |
| 解压报 **"分卷不完整，缺少: …"** | 多分卷归档缺件（如只有 `.7z.001` 没有 `.002`）。整组不会安装；按提示补齐/重新下载缺失分卷（资源本身缺件则需更新清单） |
| 报 **aria2 控制文件错误 / 文件被截断** | 半成品或旧会话损坏。代码会先隔离坏文件（`*.freedeckcy-stale-<时间戳>`）再 auto 重试一次；仍失败就移除任务重下 |
| 多分卷游戏 **识别不出分卷** | 仅支持常见 6 类命名；非标准命名会被当普通文件。可手工把分卷改名成标准形式，或提 issue（见 ROADMAP "7z t 校验/归档识别增强"） |
| **分卷/多包只下了一部分就报错** | 组内某包 `error` 时整组不会安装，已完成的分卷提示"同一安装计划中有分卷下载失败，移除失败任务后可继续安装"。移除失败的那条任务后，剩余分卷会自动继续安装；若是解压阶段失败，已解压文件会保留，移除任务后重新发起 |
| 库页 **看不到平台筛选条** | 平台条只在 `platforms` 数量 > 1 时显示；确认加载的是 `freedeckcy_catalog.csv`（7084 条 / 11 平台）而不是回退的旧目录（全 PC）。可在日志看"已加载游戏目录 total=… platforms=…"或用 `curl '127.0.0.1:59271/api/tianyi/catalog?q=&page=1'` 看 `platforms` 字段 |
| **QAM 游戏库打不开/列表不显示** | v0.20.0 起游戏库是原生路由 `/freedeckcy/library`；确认插件已重载、Decky 日志无路由报错；列表空看目录加载与筛选参数；安装进度在主页任务区 |
| **SD 卡/外置存储没出现** | 只显示已挂载且可写的 `/run/media`、`/media`、`/mnt`、`/storage`、`/sdcard` 子挂载；挂载根会被跳过；只读/未挂载不显示；看 `curl /api/tianyi/storage/options` 的 `external` 与 `/proc/mounts` |
| **扫描已安装没有补回游戏/没补 Steam 快捷方式** | v0.21.0 起入口在设置 → 安装；只扫 `settings.install_dir` 一层，目录名要匹配标题（改名可能 `catalog_no_match`）；PC 找 exe 失败 `exe_not_found`，模拟器未安装 `emulator_not_ready`（不自动下载），ROM 找不到 `rom_not_found`；看返回 `unresolved_dirs`/`steam_added`/`steam_recovered_count`；Steam 需重启/切用户/重开库页才显示新快捷方式 |
| **百度扫码报错/一直 waiting** | v0.18.0 起错误会带 HTTP 状态/原因（`stage=failed`），看 QAM 提示与 `/tmp/freedeckcy.log` 的 `Baidu QR`；网络需能访问 `passport.baidu.com`；二维码 180s 过期；可重试或改用 OpenAPI 回退 |
| **点了非 PC 卡片只弹提示、装不了** | 当前架构有官方包的平台（x86_64：10 个；aarch64：GBA/PSP/NDS/PS1/FC/MD/Switch）应可正常安装（见 §6.8）；其它情况是预期：3DS/PS2/PS3 在 aarch64 上无官方包会被目录白名单隐藏/后端拒绝。报错多为模拟器缺失、ROM 名不匹配或 BIOS/setup 文件未配 |
| 目录里 **`/web/share?code=` 链接没被加载** | v0.3.0 起 `_is_valid_tianyi_url()` 与 `tianyi_client.parse_share_url()` 都支持该形式；检查链接是否带 `code=`、域名是否 `cloud.189.cn`。旧版本目录需重载插件生效 |
| **已安装页签点卡片启动失败** | ① 看 flash 提示：`该游戏缺少 Steam AppID` 说明记录里没有 appid，去 Steam 库手动启动；② `当前环境没有 xdg-open/gio` 说明后端无法拉起外部程序（DroidDeck 桌面需有 xdg-open）；③ 用 `curl /api/tianyi/installed` 确认 `steam_appid` 与 `exists` |
| **自动云存档没触发** | ① 确认设置 `cloud_save_auto_upload` 为 true（QAM 开关/设置接口）；② 需要已登录天翼账号且当前无进行中的上传任务；③ gamewatch 需要进程命令行包含 install_path（自定义 wrapper 可能不满足；容器无 `/proc` 时回退 `pgrep -f`，需系统有 pgrep）；④ 自动上传有 30 s 防抖，连续退出多个游戏只有第一个会立即上传；⑤ 看日志 `auto cloud save upload after exit` / `gamewatch poll failed` |
| **模拟器存档没上传 / 找不到** | 看上传状态 `diagnostics.collect[*].diagnostics.emulator_saves.reason`：`save_dir_missing`（没装到标准目录/portable 目录）、`game_save_not_found`（GBA/FC/MD/NDS 必须与 ROM 同名；改名/自定义存档名会匹配不到）、`emulator_saves_shared`（共享记忆卡已被前一个游戏上传）、`emulator_saves_disabled`（开关关闭）；确认 QAM「包含模拟器存档」开启 |
| **模拟器存档恢复目标不在白名单** | 只能恢复到平台标准/portable 根（`restore_roots`）；跨设备 3DS 可能退化到根目录；不要手工把 manifest 的 `source_path` 指到 HOME 其它位置，插件会拒绝/改落到第一个根 |
| **共享记忆卡恢复覆盖了别的游戏** | PS1/PS2 单片记忆卡、Switch 目录不能按游戏拆；恢复是整卡/整目录覆盖，覆盖前会生成 `*.freedeckcy-bak-<时间戳>`，冲突会要求确认；恢复前建议先备份/确认 |
| **PS1 m3u 顺序不对 / 没生成** | 已有 `.m3u` 优先且不会被覆盖；没有时多张 `.cue/.chd` 才生成 `freedeckcy-multidisc.m3u`（按文件名自然排序）；单碟不生成。顺序不对可手工编辑，或删掉让插件重生成 |
| **3DS title id 读不到 / 没拆分** | 只支持 `.3ds/.cci/.cxi` 且 NCSD 头在 `0x100`；读不到会回退共享 `title` 目录（不是错误）。检查 `xxd -s 0x100 -l 16` 与 `.../title/00040000/<low8>/` 是否存在 |
| **3DS/Switch 上传很大 / 太慢** | 这两个平台是共享标题目录（`sdmc`/`nand/user/save`），目录可能很大；关闭「包含模拟器存档」或手动清理目录后再试；指纹最多 5000 文件 |
| **上传被跳过（reason=unchanged）** | 存档指纹和上次上传相同（相对路径+大小+mtime 未变）。确属未变化是预期；想强制上传：退出插件后删除 `state.json` 里对应游戏的 `cloud_save_fingerprints` 条目，或删除整个字段后重载插件 |
| **Ludusavi 清单未命中（退回 proton_prefix/install_fallback）** | ① 确认 `defaults/ludusavi/manifest.json.gz` 存在（`make ludusavi-manifest`，发布包自带）；② 上传状态 `diagnostics.collect` 里看 `ludusavi.matched/path_count` 与 `source_strategy`；③ 标题差异大时只能靠 Steam AppID 匹配（先看快捷方式是否解析出 appid）；④ 封面/标题含特殊字符时 `normalize_title()` 会去掉非字母数字/CJK 字符 |
| **提交校验报 platform 不支持** | 平台只支持 `pc/gba/psp/nds/ps1/fc/md/3ds/ps2/ps3/switch`；别名只认常见写法（windows→pc、ns→switch、3d→3ds、psx→ps1 等），其它拼写会直接报错。改 JSON 里的 `platform` 后重跑 `make validate-submissions` |
| **提交校验报链接不是 cloud.189.cn** | `share_url` 支持天翼 `https://cloud.189.cn/...`（`/t/<shareCode>`、`/web/share?code=`）或百度分享链接（`pan.baidu.com`），其它域名/短链先展开成对应网盘原始分享链接 |
| **openpath 缺失/包含 ..** | `openpath` 是分享根目录下游戏文件或压缩包的相对路径（如 `Stardew Valley/Stardew Valley.7z`），不能以 `/` 开头、不能含 `..`；安装器靠它分页定位文件 |
| **提交报重复 shareCode** | 同一分享链接已在目录 CSV 或本批其它 JSON 里；用 `python scripts/validate_submissions.py --json` 看具体 shareCode，换链接或删除重复文件 |
| **诊断自检某几项失败** | 设置 → 诊断「运行自检」看 status/detail/fix；runtime_* 检查包内 `defaults/runtime/<component>/<arch>/`，steam 检查登录/`FREEDECKCY_STEAM_ROOT`，network/baidu_qr 检查连通性；自检不自动修复 |
| **导出诊断没反应/下载失败** | 诊断 zip 由浏览器直接 `GET /api/tianyi/diagnostics/export` 下载；若浏览器拦截下载，用 `curl -s -OJ http://127.0.0.1:59271/api/tianyi/diagnostics/export` 手工保存；接口本身失败时看 `/tmp/freedeckcy.log` 的 traceback |
| **检查更新失败** | `update-check` 依赖 `api.github.com`：无网络、代理不通或 GitHub API 未认证限流（60 次/小时/IP）都会返回 `ok:false` + message；等一会儿或手工打开 Release 页；成功结果会缓存 1 小时，不必连续点 |
| **GBA 计划报「未找到 mGBA」** | v0.10.0 起 GBA 也首次安装**自动下载**；失败先看网络/代理，或 `FREEDECKCY_MGBA_BIN=/path/to/mgba` 指向系统/手工预置的 mGBA，或安装 Flatpak `io.mgba.mGBA`；诊断接口 `emulators.gba` 会显示 available/source/message |
| **模拟器安装时下载官方包失败/很慢** | 10 个平台（含 GBA）首次安装都要访问 GitHub release（`api.github.com`/`objects.githubusercontent.com`）；检查网络/系统代理，失败后重装可再次触发下载。可提前用 `FREEDECKCY_PPSSPP_BIN` / `FREEDECKCY_MELONDS_BIN` / `FREEDECKCY_DUCKSTATION_BIN` / `FREEDECKCY_MESEN_BIN` / `FREEDECKCY_MGBA_BIN` 指向系统或手工下载的包；诊断接口会显示对应平台的 source/url/message |
| **想完全离线安装模拟器** | 插件包不含模拟器。离线时手动把官方包放到 `~/.local/share/freedeckCY/emulators/<platform>/<arch>/`（AppImage `chmod +x`；zip 可留原样），或用 `FREEDECKCY_*_BIN` 指向本地可执行文件/AppImage；PS1 另需自备 BIOS。缓存已存在时不会再联网下载 |
| **模拟器计划报「分享中没有找到 ROM」** | 目录 CSV 的 `openpath` 文件名与分享内文件名不一致（或资源包已更新）：核对 CSV/分享文件名，大小写与扩展名要一致（gba `.gba`；psp `.iso/.cso/.pbp/.elf`；nds `.nds/.dsi/.srl`；ps1 `.cue/.m3u/.chd/.iso/.pbp/.bin`；fc `.nes/.fds/.unf/.unif`；md `.md/.gen/.smd/.bin/.32x`）；接口报错会附已扫描文件示例 |
| **模拟器解包失败（AppImage / Mesen2 zip）** | AppImage 首次使用会执行 `--appimage-extract`；Mesen2 是 zip 内单文件 `Mesen`（解压后直接可执行，不走 AppImage）。失败时看日志与 `~/.local/share/freedeckCY/emulators/<state_key>/<arch>/` 权限/空间；可删掉该目录重试，或用对应 `FREEDECKCY_*_BIN` 指向已解包的 `squashfs-root/AppRun` / `Mesen`。下载不完整（小于各平台 `min_bytes`）会删文件并报「<模拟器> 下载不完整」 |
| **模拟器快捷方式点了不启动** | 检查 `launch-freedeckcy.sh` 与 ROM 是否都在安装目录（`find_rom_file` 只认注册表扩展名）；`bash launch-freedeckcy.sh` 手工试跑；Steam 条目 Exe 必须是脚本路径、LaunchOptions 带 token（用于卸载定位），Proton 不应有映射。除 GBA 外还要确认首次下载/解包已完成；PS1 检查 BIOS（见下） |
| **3DS 启动报找不到 Flatpak / 安装失败** | 先确认系统有 `flatpak`（SteamOS 自带）；手动跑 `flatpak remote-add --user --if-not-exists flathub ...` + `flatpak install -y --user flathub org.azahar_emu.Azahar`；还失败可重试/看安装消息，插件会回退 AppImage（或设 `FREEDECKCY_AZAHAR_BIN` 指向本地 AppImage） |
| **3DS 在 Game Mode 崩溃 / 黑屏** | 确认用的是 Flatpak（诊断 `emulators.3ds.source=flatpak`）；wrapper 应包含 `QT_QPA_PLATFORM=xcb`/`SDL_VIDEODRIVER=x11`；旧快捷方式由后台自动重写，也可重装/重新注册触发 |
| **3DS system files 不被识别** | 放 `~/.local/share/freedeckCY/bios/3ds/sysdata/`（整目录）；安装后会复制到 azahar/citra 与 Flatpak 的 `~/.var/app/org.azahar_emu.Azahar/data/{azahar,azahar-emu}/sysdata`；确认目标目录非空 |
| **PS1 黑屏 / 提示没有 BIOS** | DuckStation 必须自备 BIOS：把 `scph*.bin` 放到 `~/.local/share/freedeckCY/bios/ps1/`，安装时会复制到 `~/.local/share/duckstation/bios/`；缺失**不阻断安装**但会警告、运行时可能黑屏。可用 `curl /api/tianyi/diagnostics` 看 `emulators.ps1.bios_present/bios_dir`，或手工 `cp -n ~/.local/share/freedeckCY/bios/ps1/*.bin ~/.local/share/duckstation/bios/` |
| **DroidDeck / aarch64 看不到 3DS/PS2/PS3** | 预期行为：这三个平台官方包仅 x86_64，`available_platforms("aarch64")` 只返回 7 个平台，目录查询按白名单过滤，所以条目与平台筛选条都不显示；`emulator_status` 会返回"已隐藏该平台"。想在 ARM 上用只能等官方 arm64 包，不能靠环境变量绕过 |
| **PS2 BIOS 放哪 / PCSX2 提示没有 BIOS** | 把 `*.bin`（如 `scph39001.bin`）放到 `~/.local/share/freedeckCY/bios/ps2/`；v0.12.0 安装时会部署到 `<AppDir>/bios`、`~/.local/share/PCSX2/bios`、`~/.config/PCSX2/bios` 三处，并写 `portable.ini`+`inis/PCSX2.ini`（`[Folders] Bios`/`[UI] Fullscreen`）。也可手工复制；诊断接口看 `emulators.ps2.bios_present/bios_dir` |
| **BIOS/固件压缩包没生效** | 压缩包放 `~/.local/share/freedeckCY/bios/<platform>/`，安装时由 7zz 解压到同目录 `_extracted/` 再部署；确认系统/插件有 7zz（`FREEDECKCY_7Z_BIN`），解压失败会在安装消息里提示。只想手工放时把已解压文件直接放 `bios/<platform>/`（会跳过解压） |
| **BIOS 路径不对 / 模拟器仍找不到 BIOS** | 部署目标是 `<AppDir>/bios`（AppImage 解包后的 `squashfs-root/`）与各模拟器用户目录；检查 `~/.local/share/freedeckCY/emulators/<state_key>/<arch>/squashfs-root/bios/`、`~/.local/share/duckstation/bios/`、`~/.local/share/PCSX2/bios/`、`~/.config/PCSX2/bios/`。portable 配置存在时模拟器读 `<AppDir>/bios`，否则读用户目录 |
| **PS3 固件安装失败** | 固件必须是 `bios/ps3/PS3UPDAT.PUP`；`~/.config/rpcs3/dev_flash` 已非空时插件会跳过；失败看安装消息里的 `--installfw` 错误，可手工 `rpcs3 --installfw <pup>`。RPCS3 不可执行时插件只提示不安装 |
| **Switch keys/固件没识别** | `prod.keys`/`title.keys` 放 `bios/switch/`，安装时复制到 `~/.local/share/eden/keys/`；固件放压缩包，解出的 `.nca` 目录会部署到 `~/.local/share/eden/nand/system/Contents/registered/`；确认目录非空，必要时重启 Eden |
| **3DS / PS3 / Switch 装完不能直接玩** | 这些平台需要用户自备系统文件：3DS 需要 Azahar 的 system files、PS3 需要固件（`PS3UPDAT.PUP`）、Switch 需要 `prod.keys`+固件。安装消息/库页弹窗会带 `setup_hint`；按提示在模拟器首次启动时配置，插件不内置也不下载这些文件 |
| **Mesen2（FC/MD）不启动 / 参数不对** | Mesen2 是 zip 内单文件 `Mesen`，启动参数是 `/fullscreen <rom>`（不是 `-f`）；FC 与 MD 共用 `emulators/mesen/<arch>/` 缓存，删缓存会同时影响两者。检查 `cat launch-freedeckcy.sh` 是否 `exec <Mesen> /fullscreen <rom>`，并可手工试跑 |
| **PS2/PS3/3DS/Switch 为什么不能装** | 这些平台已接入。x86_64 可安装（PS2 需 BIOS、3DS 需 system files、PS3 需固件、Switch 需 keys）；aarch64 上 3DS/PS2/PS3 无官方 arm64 包，被目录白名单隐藏；Switch 有 arm64 包可用 |
| **PSP/NDS/PS1/FC/MD 找不到存档 / 没法管理存档** | v0.12.0 起自动部署 `bios/<platform>/`；v0.15.0 起模拟器存档纳入云存档上传，v0.16.0 起支持恢复；没有独立存档管理 UI |
| **DroidDeck 里装完游戏，Steam 里看不到快捷方式** | DroidDeck 可能同时运行两个 Steam 客户端：`~/.droiddeck-x64/.local/share/Steam`（x64）与 `~/.local/share/Steam`（标准/ARM）。插件会优先写正在运行的那个（其 `steam.pid` 存在），但若判断错，可用 `FREEDECKCY_STEAM_ROOT` 锁定目标根，重装一次游戏并重启 Steam；`GET /api/tianyi/settings` 可确认 `droiddeck_detected` |
| **游戏启动不了 / 提示兼容工具缺失（DroidDeck）** | 需要 ARM Proton：确认 Steam 里已装 `droiddeck-proton-arm64`（或 11 版）。插件默认写 `droiddeck-proton-arm64`；版本不匹配时用 `FREEDECKCY_PROTON_TOOL=droiddeck-proton-11-arm64`，或设成 `none` 后在 Steam 里手动选兼容工具；`settings` 接口的 `proton_tool_resolved` 是实际写入值 |
| **下载/解压报“找不到二进制”（ARM 设备）** | `ls -l defaults/runtime/{aria2,7z,node}/aarch64/…` 检查 arm64 运行时是否打进包；缺则 `make runtime ARCH=aarch64` 后重新 `make package-droiddeck`；也可用 `FREEDECKCY_ARIA2_BIN` / `FREEDECKCY_7Z_BIN` / `FREEDECKCY_NODE_BIN` 指向系统 arm64 版本 |
| 分类筛选条里 **出现 GBA / Switch 等平台名** | v0.3.1 起加载时会自动清洗（`normalize_categories`），但仍建议把数据落盘清洗：`make normalize-catalog`（`--check` 可先看差异）；CI 的 `validate_catalog --strict` 会把"分类混平台名"判失败 |
| `make validate-catalog` 报 **重复 game_id / 非法链接 / 空标题** | 按报错行修 `freedeckcy_catalog.csv`：重复 id 合并或改 id；链接只允许 `cloud.189.cn/t/…` 或 `cloud.189.cn/web/share?code=…`；空标题补标题。改完重跑 `make validate-catalog` |
| 封面索引 **未命中（封面仍靠在线解析）** | ① 确认 `cover_index.csv` 已随仓库存在/路径正确；② 索引按 `game_id` 或标题匹配，标题需与目录一致（空白归一化后比较）；③ 删除 `cover_cache.json` 后重载插件让新索引生效 |
| 封面 **不显示 / 显示的是错图** | ① 检查 `cover_index.csv` 是否存在/表头是否含 `game_id` 或 `title`（文件可选，缺失就走在线解析）；② `steam_appid` 不对会合成错误的 CDN 图，删掉该行或修正 appid；③ 在线解析失败会写负缓存 30 分钟，删 `~/.local/share/freedeckCY/tianyi/cover_cache.json` 后重载插件立即重试 |
| 改了封面索引 **不生效** | 索引只在 `initialize()` 加载目录时合并；重载插件（或重新进入插件）后生效。确认文件路径（`FREEDECKCY_COVER_INDEX_CSV` 或 `defaults/tianyi_catalog/cover_index.csv`）与列名兼容 |
| 封面缓存 **太大 / 想清空** | 缓存是普通 JSON，直接删 `~/.local/share/freedeckCY/tianyi/cover_cache.json` 并重载插件；正缓存 7 天、负缓存 30 分钟，过期项启动时自动丢弃 |
| 装完启动 **Steam 里目标 exe 不对** | 资源清单 `openpath` 不准时靠启发式定位（相对路径 → 叶子名 → 目录内第一个可执行文件）。改 CSV 的 `openpath` 后重新安装，或手工改 Steam 快捷方式的目标 |

---

## 8. 已知限制

- **库页时长块（v0.25.0）**：只有 `managed=true`（AppID 或标题匹配到 `installed_games`）才插入块；未匹配的 Steam 原有游戏直接 `return null` 且不查 HLTB；AppID 优先降低同名误判但非绝对；HLTB 失败只影响块内数据；仍依赖 Steam 库页内部结构，Steam 更新可能使 patch 失效。

- **诊断自检（v0.22.0）**：一次性快照，网络项受连通性影响；不自动修复，只给 detail/fix；`baidu_qr` 只输出 sign 长度（不含 sign/cookie）；导出包写 0600 zip 到下载目录并含 300 行日志（已脱敏），提交前建议自行过目；不支持在线查看日志/上传诊断包。

- **Decky 原生游戏库（v0.20.0 起；v0.27.20）**：封面网格/Hero/分类货架/详情页、30 条/页+加载更多、双网盘源选择；任务进度仍在 QAM 主页任务区；扫描入口在设置，仍只认 `settings.install_dir` 一层；卸载固定 `delete_files=true`（不弹 compatdata 回收）；旧网页库仅调试/回退。
- **扫描补 Steam 快捷方式（v0.21.0）**：PC 需能找到 .exe（排除常见安装器/运行库），模拟器需已安装（不自动下载），否则记 `shortcut_error`；只写 `shortcuts.vdf`，Steam 需重启/切用户/重开库页才可见；不覆盖已有同名同 exe 快捷方式。

- **存储位置选择（v0.19.0）**：只显示已挂载且可写的外置子挂载（挂载根跳过）；容量为快照；不会自动创建/挂载/格式化，也不检测 Steam 库是否同盘；建议子目录固定 `freedeckCY/{downloads,installed}`。

- **资源源**：天翼云盘 + 百度网盘扫码/Cookie（OpenAPI 可选回退）均已实现；模拟器资源在首次安装时按需下载；独立 Web 提交/管理系统不在本仓库、不进插件包。
- **仅支持 SteamOS / Linux（含 DroidDeck 的 proot 环境）**：依赖 `7zz`、Proton、Steam 的 Linux 目录结构；Windows / macOS 无法运行。Steam 根目录支持原生 / Flatpak / **DroidDeck 双客户端**，SD 卡/第二块盘通过 `libraryfolders.vdf` 扫描。
- **作者已停止维护**：上游不再更新，接口失效只能自行修；上游 release 与本仓库版本存在代差；本仓库当前 0.27.20 已领先上游。
- **本仓库已是完整维护版**：`package.json` 版本 0.27.20，功能以本仓库文档为准；上游 v0.6 仅作历史对照。
- **DroidDeck 适配未真机验证**：ARM64 运行环境、FEX/ARM Proton、Android 存储映射都可能有差异；实测失败时优先参考 [DROIDDECK.md](DROIDDECK.md) 的排障与日志收集。
- **目录数据需保持干净**：新增/合并目录后必须跑 `make normalize-catalog` 与 `make validate-catalog`（CI 对内置目录执行 `--strict`）；「模拟器」是清洗后的兜底分类，不是真实游戏分类。
- **模拟器存档恢复/拆分（v0.16.0）**：PSP/PS3 用 PARAM.SFO、3DS 用 NCSD title id 拆分，PS1/PS2/Switch 仍整卡/整目录；恢复目标受 `restore_roots` 白名单限制，跨设备 3DS 可能退化到根目录；覆盖前有 `*.freedeckcy-bak-<时间戳>` 备份，共享卡冲突需确认；PS1 多碟自动 m3u 需要多张 `.cue/.chd`，已有 m3u 优先。
- **模拟器存档上传（v0.15.0）**：PSP/PS1/PS2/3DS/PS3/Switch 共享记忆卡整目录上传、不按游戏拆分（同卡其它游戏也会包含）；GBA/FC/MD/NDS 按 ROM 文件名匹配，改名会 `game_save_not_found`；3DS/Switch 目录可能很大；`cloud_save_include_emulators` 默认开，可关。
- **3DS（Azahar）SteamOS 兼容**（v0.14.1）：SteamOS 3.9.5 优先 Flathub Flatpak（AppImage 有上游 #127/#953 问题），需要系统有 flatpak 且能访问 Flathub；Flatpak 安装失败会回退 AppImage（可能仍打不开）；3DS 仅 x86_64（aarch64 目录隐藏）；system files 需用户自备并部署到 `~/.var/app/org.azahar_emu.Azahar/data/...`；已有快捷方式会自动重写，但真机验证仍待补。
- **百度网盘（v0.17.0）**：主链路是扫码登录（BDUSS/Cookie），Cookie 等价账号凭据、会过期/被风控，失效需重新扫码；扫码 session 仅内存 180s，**扫码确认/换 Cookie 尚未真机验证**；OpenAPI 是可选回退（需自建应用，转存 `/FreedeckTmp`）；不接 CDP/网页逆向；百度接口变更可能影响扫码/直链。
- **百度网盘 OpenAPI（v0.14.0，可选回退）**：必须自建应用 + OAuth 授权（无公共应用）；分享文件需转存 `/FreedeckTmp` 才能取 dlink，会占用户网盘（安装后清理，失败则保留）；`errno=-6`/dlink 403 等官方错误进安装消息；v0.17.0 主链路是扫码/Cookie，OpenAPI 仅在无 Cookie 时回退；**仍不接 CDP/网页逆向**；公开分享元数据/扫码接口变更可能影响解析。
- **10 平台可安装，按架构裁剪，BIOS/固件自动部署**（v0.12.0）：x86_64 上 10 个平台（含 3DS/PS2/PS3/Switch）都可安装/启动；aarch64 上 3DS/PS2/PS3 无官方 arm64 包，目录按 `available_platforms()` 白名单隐藏（条目与筛选条都不出现），Switch 有 arm64 包可用。**插件包不集成任何模拟器，首次安装都需要联网下载**（包体积约 45MB）；PS1/PS2 需要 BIOS、3DS/PS3/Switch 需要 system files/固件/keys（v0.12.0 安装后自动从 `bios/<platform>/` 部署到模拟器目录并写 portable 配置，含压缩包；缺失不阻断安装但装完不能直接玩）；模拟器只识别注册表内扩展名，不含存档管理；下载/解包会额外占一份空间；ARM64/DroidDeck 上这些平台尚未真机验证。
- **完整性校验是"大小 + 头部预检 + `7z t`（best-effort）"**：7z 不可用时自动跳过校验；没有哈希/签名校验；分卷识别只覆盖常见命名；云存档仍依赖 `node`。
- **Steam 运行中写入仍可能被覆盖**：写前有备份且写后回读，但无法阻止运行中的 Steam 覆盖 `shortcuts.vdf`/`config.vdf`；装完建议重启 Steam（自动重启 Steam 在 ROADMAP §9）。
- **compatdata 清理默认关闭**：卸载默认只删游戏文件；"连 Proton 前缀一起删"需要显式选择，避免误删存档。
- **隔离文件与备份不会自动清理**：`*.freedeckcy-archive-invalid-*`、`*.freedeckcy-size-mismatch-*`、`*.freedeckcy-bak-*` 会留在原目录，需要手工清理（或后续 ROADMAP 项）。
- **更新检查/诊断的能力边界**：`update-check` 未走 GitHub 认证（限流 60 次/小时/IP），失败只返回 message 不缓存失败；诊断包只脱敏常见键值（cookie/token/HOME），提交 issue 前仍建议自己过目一遍。
- **自动云存档的边界**：v0.8.0 只做 PC；v0.15.0 起纳入模拟器存档（GBA/PSP/NDS/PS1/FC/MD/Switch），v0.16.0 起支持恢复（冲突确认、覆盖前备份）；PS1/PS2/Switch 仍整卡/整目录覆盖；指纹只看相对路径+大小+mtime（最多 5000 文件）；`cloud_save_auto_upload` 默认开启；gamewatch 依赖进程命令行含 install_path，无 `/proc` 时用 `pgrep -f`。
- **无 i18n**：界面全硬编码中文，文案散落在 `src/index.tsx`、`defaults/tianyi_library_ui/` 与 Python 返回值里。
- **无 Python 类型检查**：只有 pytest 单测 + CI，没有 mypy/ruff 之类的门禁。
- **天翼接口未公开**：签名、接口、风控随时可能变，失败时优先看 `/tmp/freedeckcy.log` 里的协议诊断。
- **合规风险**：项目分发的资源链接来自互联网，README 自述仅限研发测试，请自行评估版权与云盘服务条款。

---

## 9. 二次开发切入点

| 想改什么 | 去哪 |
|---|---|
| 改资源清单 / 加游戏 | `defaults/tianyi_catalog/*.csv`（字段见 `game_catalog.py` 的 `GameCatalog.load`；新增可选列 `platform`/`cover_url`/`cover_portrait_url`/`steam_appid`） |
| 改平台/分类筛选 | `py_modules/game_catalog.py` 的 `list()`（platform/category）、`platform_counts()`、`category_counts()`；HTTP 入口 `tianyi_http.handle_catalog`；前端 `defaults/tianyi_library_ui/app.js` 的 `platformChips` / `filterChips` / `selectPlatform` / `selectCategory` |
| 更新/扩充目录数据 | `scripts/merge_v06_catalog.py`（从 v0.6 目录生成）或直接改 `defaults/tianyi_catalog/freedeckcy_catalog.csv`（16 列）；封面补在 `cover_index.csv`；改完跑 `make normalize-catalog && make validate-catalog` |
| 改分类清洗 / 数据体检规则 | `py_modules/game_catalog.py` 的 `normalize_categories` / `PLATFORM_TOKENS`；`scripts/normalize_catalog_categories.py`；`scripts/validate_catalog.py`（CI 门禁） |
| 改封面解析/缓存 | `py_modules/tianyi_service.py` 的 `resolve_catalog_cover` / `_catalog_entry_cover` / `_load_cover_cache` / `_save_cover_cache`；索引合并见 `game_catalog._merge_cover_index` |
| 换资源源 / 接其他网盘 | `py_modules/tianyi_client.py`（协议层）+ `backend/`（Node 兜底）；需要同时改 `game_catalog.py` 的链接校验 |
| 改解压 / 安装目录规则 | `py_modules/tianyi_service.py` 的 `_resolve_install_target_dir` / `_extract_archive_to_dir` / `_merge_extracted_content` |
| 改多分卷识别规则 | `py_modules/archive_bundle.py` 的 `detect_archive_sets`（新增命名格式/主卷规则）/ `build_bundle_index` |
| 改 aria2 运行时复用 | `py_modules/aria2_manager.py` 的 `_read_runtime_meta` / `_attach_existing` / `_try_acquire_owner_lock` / `replace_uri` |
| 改下载行为（分片、并发、续传） | `py_modules/aria2_manager.py`（`add_uri` 的 options 与启动参数） |
| 改 Steam 快捷方式 / 封面 / Proton | `py_modules/steam_shortcuts.py`（appid、`shortcuts.vdf`、`config.vdf`、`grid`） |
| 改重启恢复 / 分组语义 / 完整性校验 | `py_modules/tianyi_service.py` 的 `_try_recover_task` / `_readd_task_download` / `_maybe_schedule_group_post_process` / `_finalize_group_install` / `_verify_downloaded_file` |
| 改归档校验 / 自动重下 | `py_modules/seven_zip_manager.py` 的 `test_archive` + `py_modules/tianyi_service.py` 的 `_schedule_archive_repair` / `ArchiveRepairScheduled` |
| 改 Ludusavi 清单/匹配 | `scripts/fetch_ludusavi_manifest.py`（重新生成）、`py_modules/save_manifest.py`（`match_manifest` / `resolve_manifest_paths` / `_placeholder_bases`） |
| 改 gamewatch / 自动上传 | `py_modules/gamewatch.py`（`GameWatcher.poll` / `is_game_running`）、`tianyi_service._poll_game_watch` / `_maybe_auto_cloud_upload` / `_cloud_save_fingerprint`、设置项 `cloud_save_auto_upload` |
| 改原生游戏库 | `src/index.tsx` 的 `LIBRARY_ROUTE`/`LibraryPage`/`routerHook.addRoute`；callable 见 `main.py` 的 `list/prepare/start_tianyi_*` 与 `tianyi_service` 对应方法；网页库备用 |
| 改库页时长块 | `src/index.tsx` 的 `LibraryTimeBlock`（`managed` 门禁）/`installLibraryPlaytimePatch`；`tianyi_service.get_library_game_time_stats()`（AppID→标题匹配、未匹配不查 HLTB） |
| 改诊断自检 | `tianyi_service.run_diagnostics()` / `export_diagnostics_to_downloads()`；`main.py` 的 `run_tianyi_diagnostics`/`export_tianyi_diagnostics_file`；QAM 设置「诊断」页 |
| 改存储位置选择 | `py_modules/storage_options.py`（`detect_storage_options`/挂载前缀/过滤）、`tianyi_service.get_storage_options`、`GET /api/tianyi/storage/options`、QAM 路径页按钮 |
| 改卸载 / Proton 前缀回收 | `py_modules/tianyi_service.py` 的 `preview_uninstall` / `uninstall_installed_game` / `_can_remove_compatdata_dir` + `py_modules/steam_shortcuts.py` 的 `find_compatdata_dirs` |
| 改任务重试语义 | `py_modules/tianyi_service.py` 的 `retry_task` + `src/index.tsx`（任务行「重试」按钮） |
| 扩展环境诊断 | `scripts/doctor.sh`（只读；新增检查项直接加 `section`/`ok`/`warn`） |
| 改 Steam 多库 / Flatpak / DroidDeck 识别 | `py_modules/steam_shortcuts.py` 的 `_steam_root_candidates` / `is_droiddeck` / `_steam_library_paths` / `find_compat_user_dir` |
| 改 Proton 工具解析 / 设置 | `py_modules/steam_shortcuts.py` 的 `detect_proton_tool` / `add_or_update_tianyi_shortcut(proton_tool=)`；设置项 `proton_tool` 贯穿 `tianyi_store` / `tianyi_service.update_settings` / `main.set_tianyi_settings` / `tianyi_http.handle_settings_*` |
| 改打包架构 / ARM64 产物 | `scripts/package.sh` 的 `PACKAGE_ARCH`；`Makefile` 的 `package-droiddeck` / `runtime ARCH=`（模拟器不在包内，与打包无关） |
| 改模拟器支持 / 新增平台 | `py_modules/emulator_manager.py` 的 `EmulatorSpec` / `EMULATORS`（官方资产、launch_args、rom_extensions、env_var、state_key、executables、bios_required、setup_required/setup_hint）；`available_platforms(arch)` 决定架构白名单；`tianyi_service.list_catalog` 传 `allowed_platforms`；`_build_install_plan`/`_auto_register_emulator_to_steam` 的模拟器字段；BIOS 见 `bios_dir`/`bios_present`/`prepare_bios` |
| 改模拟器存档恢复/拆分 | `emulator_saves.py`（`restore_roots`/`build_restore_targets`/`_split_param_sfo`/`_split_3ds`/`_read_3ds_title_id`）、`param_sfo.py`、`tianyi_service._plan_emulator_save_restore`；PS1 多碟见 `emulator_manager.find_rom_file` |
| 改模拟器存档发现 | `py_modules/emulator_saves.py`（`STANDARD_SAVE_DIRS`/`PORTABLE_SUBDIRS`/`PER_GAME_PLATFORMS`/`collect_emulator_save_paths`）；`tianyi_service._collect_cloud_save_candidates` 的 `emulator_saves` 分支与去重；设置 `cloud_save_include_emulators` |
| 改 3DS Flatpak/修复 | `emulator_manager.py` 的 `_is_steamos`/`flatpak_installed`/`_ensure_flatpak`/`ensure_emulator`/`create_launch_wrapper`；`emulator_setup._deploy_3ds`；`tianyi_service._maybe_schedule_launcher_repair`/`_repair_emulator_launchers` |
| 改百度扫码/Cookie | `py_modules/baidu_qr.py`（request_qr/fetch_qr_image/poll_qr/complete_login）、`baidu_client.py`（Cookie 解析/直链）、`tianyi_service` 的 `start/poll/cancel/clear_baidu_*`、`_share_provider` 与任务 header；OpenAPI 见 `baidu_openapi_client.py` |
| 改百度 OpenAPI | `py_modules/baidu_openapi_client.py`（OAuth/refresh/转存/dlink/清理）、`py_modules/baidu_client.py`（公开分享元数据）、`tianyi_service` 的 `_share_provider`/`_build_install_plan`/`_fetch_baidu_direct_url`/`_cleanup_baidu_transfer_files`、QAM 百度区；不引入 BDUSS/Cookie |
| 改仓库提交校验/合并 | `py_modules/submission.py`（`normalize_platform`/`validate_submission`/`build_catalog_row`/`merge_submissions`）、`submissions/schema.json`、`scripts/validate_submissions.py` / `merge_submissions.py`、`.github/workflows/ci.yml` 的提交校验步骤 |
| 改 BIOS/固件部署 | `py_modules/emulator_setup.py`：`setup_emulator`、`_source_files`/`_extract_archives`（压缩包）、`_set_ini_value`（只修单键）、各平台 `_write_*`/`_deploy_*`；`tianyi_service._auto_register_emulator_to_steam` 调用并消费 `setup_messages` |
| 改模拟器下载/缓存 | `py_modules/emulator_manager.py` 的 `_download_asset` / `_extract_zip_emulator` / `_ensure_extracted`（缓存目录 `~/.local/share/freedeckCY/emulators/<state_key>/<arch>/`）；插件包已不集成模拟器 |
| 改 QAM 面板 UI | `src/index.tsx`（`Content` / `SettingsPage`） |
| 改游戏库橱窗 / 登录桥 | `defaults/tianyi_library_ui/{index.html,app.js,app.css,login_bridge.*}` |
| 改本地 HTTP 接口 | `py_modules/tianyi_http.py`（`setup_routes` 与各 `handle_*`；新接口：installed / diagnostics / update-check） |
| 改库页浏览/分页/排序/已安装页签 | `defaults/tianyi_library_ui/{app.js,index.html,app.css}` 的 `reloadList` / `gotoPage` / `cycleSort` / `switchMode` / `reloadInstalled` / `showConfirm`；后端 `game_catalog.list(sort=...)`、`tianyi_service.list_installed_games/launch_installed_game/open_installed_folder` |
| 改诊断导出 / 更新检查 | `py_modules/tianyi_service.py` 的 `get_diagnostics` / `export_diagnostics` / `check_update` / `_redact_text` / `_parse_version` / `_tail_text` / `_launch_external`；路由在 `tianyi_http.py` |
| 加后台任务 / 定时逻辑 | `py_modules/tianyi_service.py` 的 `maintenance_tick` + `main.py` 主循环 |
| 新增单测 | `tests/`（用 `tests/conftest.py` 注入的假 `decky` 模块） |

---

## 10. 提交前检查清单

- [ ] `make test`（或 `.venv/bin/pytest -q`）全绿（当前 585 用例）；
- [ ] 改动运行期/Steam/卸载相关代码后，跑一次 `make doctor` 确认环境自检正常；
- [ ] 改了目录数据后跑 `make normalize-catalog` 与 `make validate-catalog`（CI 会跑 `--strict`）；
- [ ] 改 Ludusavi 清单相关代码后确认 `defaults/ludusavi/manifest.json.gz` 存在且随包（发布包应内置），本地跑 `tests/test_cloud_auto.py`；
- [ ] 改动打包/运行时时验证两种架构：`make package`（x86_64）与 `make package-droiddeck`（aarch64），确认产物后缀与包内 `defaults/runtime/<arch>/` 只有 aria2c/7zz/node（**不含任何模拟器**）；模拟器首次安装联网下载，PS1/PS2 BIOS、3DS/PS3/Switch 系统文件由用户自备；
- [ ] 改 BIOS/固件部署后验证 `bios/<platform>/`（含压缩包）→ `<AppDir>`/用户目录的复制与 portable INI 只改目标键；用 `tests/test_emulator.py` 的 setup 用例回归；
- [ ] 改模拟器存档发现/恢复后跑 `pytest tests/test_emulator_saves.py -q`：单游戏不退化成整目录、共享目录去重、PARAM.SFO/3DS 拆分、恢复目标白名单、开关关闭；PS1 多碟跑 `tests/test_emulator.py` 的 m3u 用例；
- [ ] 改 3DS Flatpak/启动脚本后跑 `tests/test_emulator.py -q` 的 flatpak/wrapper 用例；确认 `emulators.3ds.source` 与 wrapper 的 XWayland env；已有 3DS 记录会由后台 repair 重写；
- [ ] 改库页时长逻辑后验证：原版 Steam 游戏详情页无块、插件游戏有块；`get_library_game_time_stats` 对未托管返回 `managed=false` 且不查 HLTB；`pytest tests/test_diagnostics.py -q`；
- [ ] 改原生库返回逻辑后验证三种路径：modal「返回」、modal「Steam 库」、route「返回」；v0.27.3 起顶部工具栏非 sticky，验证返回按钮/滚动后按钮行为即可；必要时用 `Navigation.NavigateBack` 回退验证；
- [ ] 改原生库入口/百度 QR 后跑 `pnpm build`、重载插件：确认插件版本 0.27.20、点游戏库走 modal；QR 超时日志包含 `Baidu QR ...`；
- [ ] 改原生库布局/输入后，用真机 CEF 验最左卡左右焦点环、顶部蓝框、A/B/方向键、触控板滚动、详情操作栏完整可见；
- [ ] 改诊断后跑 `pytest tests/test_diagnostics.py -q`，确认 checks 结构/summary；导出包含 `self-check.json` 且权限 0600；
- [ ] 改原生库后跑 `pnpm build`、重载插件；确认 `/freedeckcy/library` 路由、搜索/筛选/分页、安装确认与已安装动作；`make test` 仍 585；
- [ ] 改存储检测后跑 `pytest tests/test_storage_options.py -q`，确认系统挂载过滤、外置目录/容量字段；QAM 路径页按钮能切换且刷新；
- [ ] 改扫描已安装后跑 `pytest tests/test_install_pipeline.py -q`（扫描回填/自动补快捷方式用例），确认只扫一层、path/game_id 去重、同名同 exe 不重复、PC exe 查找与模拟器 wrapper；Steam 重启后再核对 `shortcuts.vdf`；
- [ ] 改百度相关代码后跑 `python -m pytest tests/test_baidu_integration.py tests/test_baidu_openapi_client.py tests/test_baidu_client.py -q`（mock HTTP/扫码，不联网）；确认扫码 Cookie 只存 state、不写日志/诊断；
- [ ] 改提交校验/合并后跑 `make validate-submissions`、`python scripts/merge_submissions.py --dry-run`，确认无 JSON 时 CI 也通过；`make validate-catalog` 确认合并后的 CSV 合法；
- [ ] 改动模拟器注册表后验证 `available_platforms()`：x86_64 应有 10 个平台、aarch64 只有 7 个（3DS/PS2/PS3 无包），并确认 `/api/tianyi/catalog` 的 `platforms` 计数同步裁剪；
- [ ] 改了 `src/` → `pnpm build` 并提交 `dist/index.js(.map)`；
- [ ] 没有新增 `__pycache__` / `*.pyc` / `.DS_Store` / `node_modules` 等产物；
- [ ] 没有把 `defaults/runtime/` 下的大二进制提交进去（在 `.gitignore` 里）；
- [ ] 改 `py_modules/*.py` 后至少重载插件跑通一次"打开面板 + 打开游戏库"两条路径；
- [ ] 文档中的命令 / 路径与实际一致（改了 `Makefile`、`scripts/`、`maintenance_tick` 时同步更新本文件）。
