# freedeckCY 架构说明

本文面向二次开发者与维护者，说明 freedeckCY **本仓库（`main` 分支）**的实现结构，内容已同步到 2026-11 第二轮补全后的代码。文中代码引用均使用仓库内相对路径；`文件:行号` 指向当前工作区，重构后可能偏移，函数名可作稳定锚点。

---

## 1. 一句话定位

freedeckCY 是一个运行在 **Steam Deck / SteamOS** 上的 **Decky Loader 插件**：它把随插件分发的天翼云盘分享清单变成"可安装游戏库"，用 aria2 多线程下载、7zz 解压，再写入 Steam 的快捷方式与 Proton 兼容层配置，让非 Steam 游戏像正版一样出现在 Steam 游戏模式库中；此外还提供一条基于天翼云盘的**云存档备份 / 恢复**链路。

> 合规提示：项目 README 自述"仅限研发测试、资源源自互联网、24 小时内删除"，代码会解析第三方云盘分享链接并绕过官方客户端下载。这属于版权与云盘服务条款的高风险区，请自行评估后使用。

**关键事实**：它没有自建服务器。资源清单是仓库内的 CSV 文件（`defaults/tianyi_catalog/`，一条记录 = 游戏名 + 天翼云盘分享链接 + 解压后 exe 相对路径），下载直链在运行时由天翼云盘接口现取。

---

## 2. 仓库 ≠ 产品：`main` 只是早期版本

这是阅读本仓库最容易踩的坑：**GitHub Releases 里的成品功能远多于仓库代码**。

> 本仓库 **freedeckCY** 是上游 [Freedeck](https://github.com/panyiwei-home/Freedeck) 的衍生分支，版本号从 **0.1.0** 重新起步（与上游 0.2–0.3 不连续）。下面的"上游现状"描述的是上游仓库，不是本仓库已实现的功能。

| 位置 | 内容 | 说明 |
|---|---|---|
| 本仓库 `main` | `package.json` 版本 `0.1.0`，纯天翼云盘 + CSV 目录 | 从上游 Freedeck 2026-02 的早期版本（0.2）fork 而来，版本号重新从 0.1.0 起步 |
| Releases v0.2.3 → v0.6 | 发布包约 50 MB | 增加**百度网盘**支持、**模拟器整合**、**资源池（用户上传）**、CRT 滤镜、点赞等 |
| Releases NewFreedeck v0.1 → v0.3 | 2026-08 ~ 09 重构版 | 模拟器可玩、稍后再玩 tab、分卷下载修复 |

由此得到几条直接结论：

- **仓库代码只是早期版本**：releases 里的百度网盘、模拟器、资源池等模块在 `main` 上完全不存在。不要在本仓库里寻找它们。
- **仓库缺运行时二进制**：`aria2_manager.py` / `seven_zip_manager.py` / `tianyi_client.py` 会优先查找 `defaults/runtime/` 下的 `aria2c`、`7zz`、`node`，但仓库本身不提交这些文件（已在 `.gitignore` 中）。插件可以不带它们启动，但要完整跑通下载/安装/云存档，克隆后必须先执行 `make runtime` 补齐，否则会分别报"下载组件不可用 / 解压组件不可用 / 未找到 node 运行时"。release zip 约 50 MB 与源码约 1 MB 的差值，主要就是这些二进制。
- **作者已停止维护**：NewFreedeck v0.1 的发布说明原文是"目前我没有精力与时间继续维护，抱歉，所以可以根据我整理的 skill 自行修改，最后可以给我推 pr"。
- **本仓库由模板 / 旧项目改造而来**：`defaults/defaults.txt` 仍是 Decky 模板说明文件，`config.py` 里保留了 `Decky-send` 命名的回退路径。`package.json` 里指向上游模板的 `repository` / `bugs` / `homepage` 已移除，`license` 改为 BSD-3-Clause（与 `LICENSE` 一致）。

> 本次补全统一了源码行尾为 LF（`.gitattributes` 约束），所以用 `git diff` 看提交时可能出现“整文件重写”的假象，实际逻辑改动见各文件 diff 的 `-w` 视图。

---

## 3. 技术栈

| 层 | 选型 | 位置 |
|---|---|---|
| 插件运行时 | Decky Loader（Python 3 + asyncio） | `main.py`、`decky.pyi` |
| 本地 Web 服务 | **aiohttp**，仅监听 `127.0.0.1:59271` | `py_modules/server_manager.py` |
| 业务内核 | 单个巨型类 `TianyiService`（约 7200 行） | `py_modules/tianyi_service.py` |
| 天翼 API 客户端 | aiohttp + 自写 MD5 签名 / XML/JSONP 兼容解析 | `py_modules/tianyi_client.py` |
| 状态持久化 | 单个 JSON 全量重写；状态目录 0700 / 文件 0600 | `py_modules/tianyi_store.py` → `~/.local/share/freedeckCY/tianyi/state.json` |
| 日志 | `RotatingFileHandler`（5 MB × 3，`propagate=False`） | `py_modules/config.py` → `/tmp/freedeckcy.log` |
| 下载器 | 内置 / 系统 **aria2c**，JSON-RPC 控制 | `py_modules/aria2_manager.py` |
| 解压 | 内置 / 系统 **7zz**（`.7z/.rar` 等），其余走 `shutil` | `py_modules/seven_zip_manager.py` |
| Steam 集成 | 自实现 VDF 读写 + 二进制 `shortcuts.vdf` | `py_modules/steam_shortcuts.py`、`py_modules/vdf/` |
| QAM 前端 | **React 19 + TypeScript**，`@decky/api` + `@decky/ui`，Rollup 打包 | `src/index.tsx` → `dist/index.js` |
| 本地网页前端 | **Vue 3 全局构建**（无构建步骤，直接引入 `vue.global.prod.js`） | `defaults/tianyi_library_ui/` |
| 云盘上传 / 分享兜底 | **Node ≥ 18**，子进程 stdin/stdout JSON 协议 | `backend/*.js`、`backend/*.cjs` |

运行时一共会拉起 **4 类进程**：Decky 的 Python 进程、`aria2c`、`7zz`、偶尔的 `node`。

---

## 4. 目录地图

```text
repo/
├── main.py                     # 插件入口：Plugin 类，22 个可调用 RPC，大部分薄转发给 TianyiService / server_manager
├── plugin.json                 # Decky 元信息（api_version=1, flags=[]，publish 描述已更新）
├── package.json                # 版本 0.1.0；build=rollup；前端依赖
├── decky.pyi                   # Decky Python API 类型存根
├── Makefile                    # runtime / package / test / clean / help 目标（见 DEVELOPMENT.md）
├── requirements-dev.txt        # 开发与 CI 依赖（pytest 等，运行期依赖由 Decky 自带）
├── .gitignore                  # 忽略 __pycache__、defaults/runtime/、node_modules、dist-artifacts 等
├── .gitattributes              # 行尾统一为 LF，二进制资源按原样处理
├── clear_freedeckcy_tasks.sh     # 运维脚本：清空 state.json 里的 tasks（支持 $HOME / FREEDECKCY_STATE_FILE）
├── dist/index.js(.map)         # 已提交的构建产物（约 100 KB / 1.6 MB sourcemap）
├── src/
│   ├── index.tsx               # 全部 React 代码：Content(QAM) / SettingsPage / 库页面注入补丁
│   └── types.d.ts
├── defaults/                   # 随插件分发的静态资源（打包时复制到插件根目录）
│   ├── tianyi_catalog/gamebox_all_links_*.csv   # 资源清单（2844 条记录，核心数据）
│   ├── tianyi_library_ui/      # Vue 游戏库 + 二维码登录桥（6 个文件，含 vue.global.prod.js）
│   ├── runtime/                # 运行期二进制（不提交，由 make runtime 下载到 .gitignore 的目录）
│   └── defaults.txt            # Decky 模板说明文件（原样保留）
├── py_modules/
│   ├── tianyi_service.py       # ★ 业务内核：下载/安装（分卷、自愈）/云存档/登录/时长
│   ├── tianyi_client.py        # ★ 天翼云盘协议：分享解析、直链、token、上传（调 Node）
│   ├── tianyi_http.py          # 本地 HTTP 路由与 handler（34 条路由）
│   ├── tianyi_store.py         # 数据类 + state.json 读写（目录 0700 / 文件 0600）
│   ├── server_manager.py       # aiohttp 生命周期 + 本地 API 安全边界（Host/Origin）+ 设置备份 + /_healthz
│   ├── aria2_manager.py        # aria2 子进程 + 运行时元数据/flock 复用 + JSON-RPC（addUri/changeUri/listDownloads…）
│   ├── seven_zip_manager.py    # 7z 解压 / 压缩
│   ├── steam_shortcuts.py      # shortcuts.vdf / config.vdf / grid 封面；多库/Flatpak、写前备份、DevkitGameID 去重
│   ├── game_catalog.py         # CSV → 内存目录（校验、搜索、分页）
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
│   └── package.sh              # 组装 Decky 插件 zip 到 dist-artifacts/
├── tests/                      # pytest 单测（215 个用例，不联网、不碰 Steam 目录）
├── docs/                       # 项目文档（ARCHITECTURE / DEVELOPMENT / ROADMAP）
├── .github/workflows/ci.yml    # CI：pytest + pnpm build
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
│        ├── GameCatalog         ──▶ defaults/tianyi_catalog/*.csv
│        ├── ArchiveBundle       ──▶ 多分卷归档识别（主卷 / 缺失分卷 / bundled）
│        ├── Aria2Manager        ──▶ aria2c 子进程（运行时元数据 + flock 复用，JSON-RPC 控制）
│        ├── SevenZipManager     ──▶ 7zz 子进程（解压/打包）
│        ├── SteamShortcuts      ──▶ ~/.steam/.../shortcuts.vdf、config.vdf、userdata/*/grid/
│        └── TianyiClient        ──▶ cloud.189.cn / api.cloud.189.cn（Cookie + MD5/AES/RSA 签名）
│
├── aiohttp 本地服务（127.0.0.1:59271，只绑回环）
│   ├── /                            服务首页
│   ├── /_healthz                    健康检查
│   ├── /tianyi/library              Vue 游戏库橱窗  ── 由 Steam 内置浏览器打开
│   ├── /tianyi/library/login-bridge 二维码登录桥
│   └── /api/tianyi/*                31 条 REST 路由（给 Vue 页用）
│
└── 外部依赖
    ├── open.e.189.cn        二维码登录
    ├── api.cloud.189.cn     accessToken / 直链 / 分片上传
    └── node (>=18)          分享解析兜底、云存档上传（stdin/stdout JSON 子进程）
```

### 5.2 三条"控制面"、一条"数据面"

- **控制面 1**：QAM 面板 ↔ `@decky/api` RPC（`main.py` 的 22 个可调用方法，前端实际用到其中 18 个天翼 RPC；入口 [main.py:39](../main.py) `_main`，天翼 RPC 定义从 [main.py:147](../main.py) 起）。
- **控制面 2**：Vue 页面 ↔ 本地 HTTP API（`py_modules/tianyi_http.py` 的 31 条 `/api/tianyi/*` 路由，路由表在 [tianyi_http.py:522](../py_modules/tianyi_http.py) `setup_routes()`）。
- **控制面 3**：Python ↔ Node 子进程（stdin 一行 JSON，stdout 一行 JSON；node 解析见 [tianyi_client.py:630](../py_modules/tianyi_client.py) `_resolve_node_binary()`）。
- **数据面**：`aria2c` 从 `api.cloud.189.cn` 拿到的直链下载到本地磁盘。

### 5.3 两个前端的分工

| | QAM 面板（React） | 本地网页（Vue） |
|---|---|---|
| 路由 | 插件内容区 + `/freedeckcy/settings` | `/tianyi/library`、`/tianyi/library/login-bridge` |
| 页面 | 登录状态/入口、下载队列（最多 20 条，自绘进度条）、已安装游戏预览+卸载；设置页 4 个 tab（路径/安装/下载/账号，账号页含云存档上传与恢复） | **只有两个**：游戏库橱窗（搜索 + 封面卡片网格 + 安装确认弹窗）、二维码登录桥 |
| 能干什么 | 看任务、暂停/继续/移除任务、改设置、管云存档、卸载（除了卸载，**不能**自己发起下载） | **唯一能"下单"的地方**：浏览→确认→创建下载任务 |
| 交互特点 | 900 ms / 6 s / 30 s 三档轮询 | 手柄支持（160 ms 轮询、方向键导航，为掌机设计） |
| 怎么打开 | 插件自带 | 调 RPC 拿 URL → `SteamClient.Browser.OpenUrl`（Steam 内置浏览器），不是 iframe/webview |

QAM 主面板由登录/操作入口、下载列表、已安装游戏预览等 `PanelSection` 组成，代码在 [src/index.tsx:2447](../src/index.tsx) `Content()` 到文件末尾；设置页是 `Tabs` 四页（路径 / 安装 / 下载 / 账号），在 [src/index.tsx:1533](../src/index.tsx) `SettingsPage()`。

### 5.4 前端调用面

**RPC（[src/index.tsx:297](../src/index.tsx) 起，全部 `callable("...")`，共 18 个天翼 RPC）**

| RPC | 用途 |
|---|---|
| `get_tianyi_panel_state` | 面板总状态（登录/任务/已装/设置），高频轮询 |
| `get_tianyi_cloud_save_upload_status` / `..._restore_status` | 云存档进度，运行中 1.2 s |
| `get_tianyi_library_game_time_stats` | 库页时长（本人/主线/总时长），2 min 或 3 s 重试 |
| `get_tianyi_library_url` / `get_tianyi_login_url` | 拿本地页面 URL |
| `set_tianyi_settings` / `clear_tianyi_login` | 设置 / 注销 |
| `start_tianyi_cloud_save_upload` / `list_..._options` / `list_..._entries` / `plan_..._restore` / `apply_..._restore` | 云存档五连 |
| `pause_tianyi_task` / `resume_tianyi_task` / `remove_tianyi_task` | 暂停 / 继续 / 移除下载任务 |
| `uninstall_tianyi_installed_game` | 卸载（删目录 + 记录） |
| `record_tianyi_game_action` | 启动/退出事件上报（计时用） |

**HTTP API 分组（`py_modules/tianyi_http.py` 的 `setup_routes()`，34 条路由）**：3 条页面/静态资源（`/tianyi/library`、`/tianyi/library/login-bridge`、静态文件兜底），以及 `login/*`（qr、capture、manual、clear）、`catalog`、`catalog/cover`、`settings`、`install/prepare|start`、`download/create|tasks|pause|resume|remove`、`cloud-save/*`、`state`。

---

## 6. 链路 A：从点"安装"到 Steam 库里出现游戏

```text
[Vue 库页]点击卡片
   │ POST /api/tianyi/install/prepare  {game_id 或 share_url}
   ▼
_build_install_plan()
   ├─ share_url 只接受天翼域名（cloud.189.cn / *.189.cn，_is_tianyi_share_url）
   ├─ 查 CSV → share_url / openpath / title
   ├─ resolve_share(cookie)                ← 拿文件清单 fileId + size
   └─ 空间探针：下载/安装目录可用空间判定 + 解压后体积估算
   │ 返回 plan（含 can_install / files[] / 空间与估算字段）
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
   │    → 空间检查 → 7zz 强制解压（分卷必须走 7z）→ staging 合并
   ├─ 全部成功 → _finalize_group_install()
   │    ├─ 写 TianyiInstalledGame 记录（体积 = 组内各包之和）
   │    ├─ 只以"代表任务"（created_at 最早）注册一次 Steam（见 6.5）
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
| 运行时二进制 | `defaults/runtime/{aria2,7z}/<arch>/`、`defaults/runtime/node/<arch>/bin/node` |
| 日志 | `/tmp/freedeckcy.log` |

**关键函数索引（安装链路）**

| 环节 | 代码位置 |
|---|---|
| HTTP 入口 prepare / start | [tianyi_http.py:426](../py_modules/tianyi_http.py) `handle_prepare_install` / [tianyi_http.py:447](../py_modules/tianyi_http.py) `handle_start_install` |
| 安装计划 + 空间探针 | [tianyi_service.py:4669](../py_modules/tianyi_service.py) `_build_install_plan()` |
| 创建下载任务 | [tianyi_service.py:4807](../py_modules/tianyi_service.py) `_create_tasks_from_plan()` |
| 任务状态同步 | [tianyi_service.py:5109](../py_modules/tianyi_service.py) `refresh_tasks()` |
| 安装调度 / 目录级互斥 | [tianyi_service.py:5220](../py_modules/tianyi_service.py) `_schedule_post_process_task()` / [tianyi_service.py:5454](../py_modules/tianyi_service.py) `_post_process_completed_task()` / [tianyi_service.py:5433](../py_modules/tianyi_service.py) `_install_lock_for()` |
| 解压 / 合并 staging | [tianyi_service.py:6003](../py_modules/tianyi_service.py) `_extract_archive_to_dir()` / [tianyi_service.py:6049](../py_modules/tianyi_service.py) `_merge_extracted_content()` |
| 写 Steam 快捷方式 / Proton / 封面 | [steam_shortcuts.py:363](../py_modules/steam_shortcuts.py) `_upsert_shortcut_sync()`、[steam_shortcuts.py:494](../py_modules/steam_shortcuts.py) `_set_proton_mapping_sync()`、[steam_shortcuts.py:744](../py_modules/steam_shortcuts.py) `_apply_grid_assets()` |
| 非 Steam appid | [steam_shortcuts.py:356](../py_modules/steam_shortcuts.py) `_generate_non_steam_app_id()` |
| aria2 下单 | [aria2_manager.py:452](../py_modules/aria2_manager.py) `add_uri()` |
| 分享解析 / 直链 | [tianyi_client.py:1070](../py_modules/tianyi_client.py) `resolve_share()`、[tianyi_client.py:1585](../py_modules/tianyi_client.py) `fetch_access_token()`、[tianyi_client.py:1628](../py_modules/tianyi_client.py) `fetch_download_url()` |
| 后台维护 | [tianyi_service.py:455](../py_modules/tianyi_service.py) `maintenance_tick()` |
| 多分卷归档识别 | [archive_bundle.py:88](../py_modules/archive_bundle.py) `detect_archive_sets()` / [archive_bundle.py:228](../py_modules/archive_bundle.py) `build_bundle_index()` |
| 解压前 settle / 预检 | [tianyi_service.py:5539](../py_modules/tianyi_service.py) `_wait_payload_settled()` / [tianyi_service.py:5583](../py_modules/tianyi_service.py) `_precheck_archive_payload()` |
| 分卷只解主卷 / bundled | [tianyi_service.py:5454](../py_modules/tianyi_service.py) `_post_process_completed_task()` / [tianyi_service.py:5604](../py_modules/tianyi_service.py) `_install_payload()` |
| 坏文件隔离 / 自愈 | [tianyi_service.py:5011](../py_modules/tianyi_service.py) `_quarantine_download_file()` |
| aria2 运行时复用（meta+flock） | [aria2_manager.py:158](../py_modules/aria2_manager.py) `_read_runtime_meta()` / [aria2_manager.py:248](../py_modules/aria2_manager.py) `_attach_existing()` / [aria2_manager.py:205](../py_modules/aria2_manager.py) `_try_acquire_owner_lock()` |
| 直链原地换链 | [aria2_manager.py:510](../py_modules/aria2_manager.py) `replace_uri()` |
| 重启恢复（gid 丢失） | [tianyi_service.py:4975](../py_modules/tianyi_service.py) `_try_recover_task()` / [tianyi_service.py:4900](../py_modules/tianyi_service.py) `_file_matches_expected_size()` / [tianyi_service.py:5031](../py_modules/tianyi_service.py) `_readd_task_download()` |
| 分卷分组安装 | [tianyi_service.py:4930](../py_modules/tianyi_service.py) `_install_group_members()` / [tianyi_service.py:4946](../py_modules/tianyi_service.py) `_maybe_schedule_group_post_process()` / [tianyi_service.py:5604](../py_modules/tianyi_service.py) `_install_payload()` / [tianyi_service.py:5692](../py_modules/tianyi_service.py) `_finalize_group_install()` |
| 下载完整性校验 | [tianyi_service.py:4911](../py_modules/tianyi_service.py) `_verify_downloaded_file()` |
| aria2 全量列表（恢复用） | [aria2_manager.py:534](../py_modules/aria2_manager.py) `list_downloads()` |

**几个容易误解的点**

- **"不限速"的真相**：全仓库没有任何 `--max-*-limit`，所以是"不设上限"而不是加速。实际速度取决于天翼直链和单文件分片数（默认 `split=16`，aria2 全局并发 3）。
- **不转存**：分享资源不会保存到用户网盘，直接拿直链给 aria2 下载（这点和很多"转存类"工具不同）。
- **`freedeckcy:tianyi:<game_id>`** 只是写在 LaunchOptions 里的标记，本插件没有读取它的运行时代码（时长统计走 Steam 全局事件，见 7.3）。
- **exe 定位是启发式**：CSV 的 `openpath` 精确时靠它；不精确时靠"叶子文件名搜索"和"目录里第一个可执行文件"，这是很多"装完点了没反应"的根源。
- **写 `shortcuts.vdf` 必须重启 Steam** 才能看到。
- **error 任务不会自动重试安装**：先移除出错的任务；分卷场景下移除失败的那一包后，剩余已完成的分卷会继续安装（见 6.2）。

### 6.1 重启恢复：gid 变化与直链过期

插件重载现在会附着到仍存活的 aria2（见 6.4），**gid 通常不变**；但**设备重启**后 aria2 会话重建、gid 会变，直链也可能过期。`state.json` 里存的旧 gid 查不到时，`refresh_tasks()` 对查询失败的任务按以下顺序恢复（[tianyi_service.py:4975](../py_modules/tianyi_service.py) `_try_recover_task()` / [tianyi_service.py:4900](../py_modules/tianyi_service.py) `_file_matches_expected_size()` / [tianyi_service.py:5031](../py_modules/tianyi_service.py) `_readd_task_download()`）：

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

同一安装计划（`install/prepare` 返回的多个文件）在创建任务时共享一个 `group_id`，`group_total` 记录包数。**"代表任务" = 组内 `created_at` 最早的那个**（[tianyi_service.py:4930](../py_modules/tianyi_service.py) `_install_group_members()` 按 `(created_at, task_id)` 排序），Steam 注册与已安装记录都以它为准。

- **下载阶段**：`_maybe_schedule_group_post_process()` 只在整组任务全部 `complete` 后才调度安装。
  - 组内某包 `error`：不安装；已完成的包显示"同一安装计划中有分卷下载失败，移除失败任务后可继续安装"；
  - 用户移除失败任务后（`removed` 状态不参与分组），剩余的 complete 分卷会被重新调度安装。
- **安装阶段**：逐包解压到同一目标目录（目录级互斥串行），全部成功才 [tianyi_service.py:5692](../py_modules/tianyi_service.py) `_finalize_group_install()`：
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

- **token 去重**：新条目同时写 `LaunchOptions="freedeckcy:tianyi:<token>"` 与 `DevkitGameID=<token>`；匹配时读 `DevkitGameID` 或旧 `LaunchOptions` 任一（[steam_shortcuts.py:344](../py_modules/steam_shortcuts.py) `_shortcut_tokens()`），避免用户手动改启动项后重复建条目；启动前缀常量 `FREEDECKCY_LAUNCH_PREFIX`。
- **差异写入**：目标条目字段全部一致且文件存在时返回 `action="unchanged"`，不重写文件。
- **写前备份**：`shortcuts.vdf` / `config.vdf` 写入前复制为 `*.freedeckcy-bak-<YYYYmmdd_HHMMSS>`（[steam_shortcuts.py:311](../py_modules/steam_shortcuts.py) `_backup_file()`），同类备份只保留最近 **12** 份；`config.vdf` 的 Proton 映射改写同样先备份。
- **写后校验**：`shortcuts.vdf` 写完重新读回，确认 token 真的落盘，否则返回失败（防"以为写成功"）。
- **compatdata 用户名打分**：`find_compat_user_dir()` 先试 `steamuser` / `deck` / `root`，再对自定义 Wine 用户名按 `AppData`(+3)/`Documents`(+2)/`Saved Games`(+2) 打分挑选（参考 v0.6 同类实现）。

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
| 多库 compatdata 定位 | [steam_shortcuts.py:115](../py_modules/steam_shortcuts.py) `find_compat_user_dir()` / [steam_shortcuts.py:80](../py_modules/steam_shortcuts.py) `_steam_library_paths()` |
| 上传入口 | [tianyi_service.py:2457](../py_modules/tianyi_service.py) `start_cloud_save_upload()` |
| 上传后台任务 | [tianyi_service.py:4211](../py_modules/tianyi_service.py) `_run_cloud_save_upload_task()` |
| 候选目录扫描 | [tianyi_service.py:3689](../py_modules/tianyi_service.py) `_collect_cloud_save_candidates()` |
| 打包 + manifest | [tianyi_service.py:4102](../py_modules/tianyi_service.py) `_archive_single_game_saves()` |
| 云端上传 / 列版本 / 下载 | [tianyi_client.py:2024](../py_modules/tianyi_client.py) `upload_archive_to_cloud()`、[tianyi_client.py:2061](../py_modules/tianyi_client.py) `list_cloud_archives()`、[tianyi_client.py:2112](../py_modules/tianyi_client.py) `download_cloud_archive()` |
| 恢复四步 | [tianyi_service.py:2509](../py_modules/tianyi_service.py) `list_cloud_save_restore_options()`、[tianyi_service.py:2623](../py_modules/tianyi_service.py) `list_cloud_save_restore_entries()`、[tianyi_service.py:2710](../py_modules/tianyi_service.py) `plan_cloud_save_restore()`、[tianyi_service.py:2940](../py_modules/tianyi_service.py) `apply_cloud_save_restore()` |

### 7.3 游玩时长（独立小链路）

- `SteamClient.Apps.RegisterForGameActionStart/End` 全局监听 → `record_tianyi_game_action`（[src/index.tsx:804](../src/index.tsx) `installGlobalGameActionReporter()`）→ `TianyiService.record_game_action()`：重复 start 且间隔超过 5 秒视为上一局结束，单局封顶 12 小时，重启后能恢复会话。
- 库游戏详情页：用 `routerHook.addPatch("/library/app/:appid")` **patch Steam 库页面的 `renderFunc` 和组件 `type`**，把"我的游玩 / 主线 / 总时长（HowLongToBeat）"插进去（[src/index.tsx:1358](../src/index.tsx) `installLibraryPlaytimePatch()`）。这是全项目最"黑魔法"的一段，依赖 Steam UI 内部结构。

---

## 8. 登录：四种方式，UI 只走二维码

| 方式 | 实现 | 现状 |
|---|---|---|
| **二维码**（UI 唯一入口） | Python 侧 aiohttp 直接调 `open.e.189.cn` 的二维码接口，抓取二维码 PNG 代理给页面；1.6 s 轮询状态；成功后从 cookie jar 拼 cookie 串存 `state.json` | 在用，最稳 |
| **CDP 抓取** | 连 Steam 内置浏览器 / Chromium 的调试端口（8080、9222），用 DevTools 协议读 cookie | 旧方案，API 还在（`/api/tianyi/login/capture/*`），前端已不调用 |
| **Cookie DB 直读** | 读 `~/.local/share/Steam/config/htmlcache/Cookies` 等 SQLite，过滤 `189.cn` 域 | 旧方案；`v10/v11` 加密的 cookie 直接跳过 |
| 手动粘贴 cookie | `POST /api/tianyi/login/manual` | 兜底 API 保留 |

代码位置：二维码 [tianyi_service.py:1197](../py_modules/tianyi_service.py) `start_qr_login()` / [tianyi_service.py:1283](../py_modules/tianyi_service.py) `poll_qr_login()`；CDP [tianyi_service.py:6816](../py_modules/tianyi_service.py) `_collect_tianyi_cookie_from_cdp()`；Cookie DB [tianyi_service.py:7015](../py_modules/tianyi_service.py) `_collect_tianyi_cookie_from_cookie_db()`；手动 cookie [tianyi_http.py:151](../py_modules/tianyi_http.py) `handle_login_manual()`。

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

`~/.local/share/freedeckCY/tianyi/state.json`（**每次全量重写**，原子替换临时文件；数据类与读写见 [tianyi_store.py:51](../py_modules/tianyi_store.py) 起、[tianyi_store.py:191](../py_modules/tianyi_store.py) `load()`、[tianyi_store.py:261](../py_modules/tianyi_store.py) `save()`）：

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
- `install_status` 取值：`pending` / `installing` / `installed` / `failed` / **`bundled`**（多分卷归档的非主卷，由主卷统一解压，安装完成后保持该值）。
- 状态文件含登录 Cookie：保存时状态目录 chmod **0700**、`state.json` 及临时文件 chmod **0600**（`_chmod_private()`，失败不阻断）。

---

## 11. 值得学的 6 个设计

1. **面板三档轮询 + 后端二次节流**：前端 active 900 ms / idle 6 s / background 30 s；后端再按"有无活跃任务"把任务刷新窗口分成 1 s/10 s/30 s，安装列表 20 s/60 s/120 s，并且有缓存和超时降级。轮询路径上**不做端口探测和网络校验**，耗时的刷新有窗口节流。
2. **重活全部异步化 + 后台维护 + 分组收口**：解压、aria2 控制、store 写盘都走 `asyncio.to_thread`；下载完成后的安装调度成后台任务并按 task_id 去重；`main.py` 启动时先跑一次、之后按 `config.MAINTENANCE_INTERVAL_SECONDS` 周期调用 `maintenance_tick()`，保证**面板没打开时也能自动安装**；同组任务以 `group_id` 收口（整组下完才装、只注册一次 Steam），并用任务列表指纹避免每轮维护都重写 `state.json`。
3. **两段式安装**：`prepare`（只探测：文件清单、剩余空间、Proton 评级）→ `start`（真正下单）。用户能在确认前看到"要下多大、装完多大、盘够不够"。
4. **解压到 staging 再合并**：先解到临时目录，再合并进目标目录，并自动去掉压缩包里"套一层同名文件夹"的情况。这是处理第三方打包资源非常实用的技巧。
5. **云存档带 manifest**：不裸传文件，而是打包 + `manifest.json` 记录源路径、条目、游玩时长。恢复时才能做**路径推断**、**冲突探测**、**时长合并**（取较大值，不降级覆盖）和**覆盖前自动备份**。
6. **降级链与自愈**：Python 解析失败 → Node 解析；内置运行时优先 → 系统命令兜底；7z 失败 → `shutil.unpack_archive`；缓存刷新失败 → 用旧缓存；aria2 会话丢失 → 按路径认领 / 原直链重新加入，直链过期 → `changeUri` 原地换链；文件大小不符 → 隔离坏文件后自动重下一次。

---

## 12. 问题清单

> 本清单覆盖 2026-11 三轮工程补全后的状态；标注"（本次补全已修复）"的条目已落地，其余为当前仍存在的**已知问题**。维护建议见 [ROADMAP.md](ROADMAP.md)。

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

### P2：工程性

19. `tianyi_service.py` 约 7200 行、单类 100+ 方法；`src/index.tsx` 约 100 KB / 2900 行单文件。已补 `tests/`（215 个用例）与 GitHub Actions CI，但**仍无 Python 类型检查**（mypy/ruff 未接入，见 ROADMAP）。
20. 全硬编码中文，**无 i18n**；大量 `unknown` / `as` 断言绕过 TS 类型。（已知问题）
21. ~~`clear_freedeckcy_tasks.sh` 写死 `/home/deck`~~：**本次补全已修复**——改用 `$HOME` 并支持 `FREEDECKCY_STATE_FILE` 覆盖。
22. 日志路径仍写死 `/tmp/freedeckcy.log`，不可配置（已轮转，不再是无限增长）。（已知问题）
23. ~~日志无限增长 / `basicConfig(force=True)` 覆盖 Decky 日志配置~~：**本次补全已修复**——改为 `RotatingFileHandler`（5 MB × 3），`propagate=False`。
24. ~~`state.json` 以默认文件权限落盘（内容含登录 Cookie）~~：**本次补全已修复**——状态目录 0700、文件 0600。
25. ~~aria2 启动参数偏弱（预分配慢、无超时/重试/日志/证书）~~：**本次补全已修复**——`--file-allocation=none`、connect 10 s / read 60 s、retry-wait 5 / max-tries 10、`--log aria2.log`、自动选 `--ca-certificate`，下载请求带 UA/Referer。
26. ~~Steam 快捷方式/Proton 写入无法回滚~~：**本次补全已修复**（同第 10 条，写前备份 + 回读；但运行中的 Steam 仍可能覆盖，见第 13 条）。
27. Proton 用户目录已支持自定义用户名打分兜底，但极端布局（多前缀、非常规用户名）仍可能漏扫。（已知问题）

---

## 13. 与 v0.6 的对齐

作者 v0.6 发行版（解包于本地 `0.6/freedeck-plugin`，**只读参考、不随本仓库分发**）在下载管线、Steam 写入、模拟器与资源池上比本仓库完整得多。本轮只借鉴与"稳定下载 / 安全写 Steam"直接相关的少数能力；其余能力要么不采纳、要么列入 [ROADMAP.md](ROADMAP.md)。

### 13.1 已采纳（本轮）

| 能力 | v0.6 出处 | 本仓库实现 |
|---|---|---|
| 多分卷归档识别（6 类命名、主卷、缺失分卷） | `archive_detector.py` | `py_modules/archive_bundle.py`；只解主卷、其余 `bundled`（见 6.3） |
| 解压前收紧 | `archive_validator.py` 预检思路 | `_wait_payload_settled()`（等 `.aria2` 释放、大小稳定两次）+ `_precheck_archive_payload()`（空文件/HTML）；**未照搬 `7z t`**（见 13.4 / ROADMAP §9.4） |
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

`7z t` 全量校验、Range 续传探测、SQLite 任务库、平台目录 + 封面索引、单平台模拟器闭环、资源池只读、百度 OpenAPI、自动重启 Steam、compatdata 卸载清理；CTFile 等其它网盘来源仅作评估（接口/合规先决条件多，未列入当前优先级）。

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
| libraryfolders.vdf | Steam 记录多游戏库（SD 卡、第二块盘）的 VDF 配置；本项目据此在所有库中扫描 `compatdata` |
| 天翼云盘 | 中国电信 189 云盘，`cloud.189.cn`，本项目唯一的资源存储后端 |
