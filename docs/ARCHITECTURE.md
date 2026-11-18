# freedeckCY 架构说明

本文面向二次开发者与维护者，说明 freedeckCY **本仓库（`main` 分支）**的实现结构，内容已同步到 freedeckCY **v0.26.29**（2026-11）的代码。文中代码引用均使用仓库内相对路径；`文件:行号` 指向当前工作区，重构后可能偏移，函数名可作稳定锚点。

---

## 1. 一句话定位

freedeckCY 是一个运行在 **Steam Deck / SteamOS** 上的 **Decky Loader 插件**：它把随插件分发的天翼云盘分享清单变成"可安装游戏库"，用 aria2 多线程下载、7zz 解压，再写入 Steam 的快捷方式与 Proton 兼容层配置，让非 Steam 游戏像正版一样出现在 Steam 游戏模式库中；此外还提供一条基于天翼云盘的**云存档备份 / 恢复**链路。

> 合规提示：项目 README 自述"仅限研发测试、资源源自互联网、24 小时内删除"，代码会解析第三方云盘分享链接并绕过官方客户端下载。这属于版权与云盘服务条款的高风险区，请自行评估后使用。

**关键事实**：它没有自建服务器。资源清单是仓库内的 CSV 文件（`defaults/tianyi_catalog/`，一条记录 = 游戏名 + 天翼云盘分享链接 + 解压后 exe 相对路径），下载直链在运行时由天翼云盘接口现取。

---

## 2. 仓库 ≠ 产品：`main` 只是早期版本

这是阅读本仓库最容易踩的坑：**GitHub Releases 里的成品功能远多于仓库代码**。

> 本仓库 **freedeckCY** 是上游 [Freedeck](https://github.com/panyiwei-home/Freedeck) 的衍生分支，版本号从 **0.1.0** 起步（与上游 0.2–0.3 不连续），当前 **0.26.29**。下面的"上游现状"描述的是上游仓库，不是本仓库已实现的功能。

| 位置 | 内容 | 说明 |
|---|---|---|
| 本仓库 `main` | `package.json` 版本 `0.26.29`，纯天翼云盘 + 多平台目录，适配 Steam Deck / DroidDeck | 从上游 Freedeck 2026-02 的早期版本（0.2）fork 而来，版本号重新从 0.1.0 起步；v0.1.1 完成"四件套"，v0.2.0 完成目录平台化/封面索引/分类筛选，v0.3.0 补齐全量目录与平台筛选 UI，v0.3.1 做分类清洗与目录数据体检，v0.4.0 做 DroidDeck（Android/ARM64）适配，v0.5.0 完成第一梯队浏览/分页/排序/已安装页签与诊断导出/更新检查，v0.6.0~v0.6.2 做 GBA 模拟器闭环与远程 JSON 目录，v0.7.0 做通用模拟器注册表并接入 PSP/NDS，v0.8.0 做 Ludusavi + gamewatch 自动云存档，v0.9.0 把模拟器注册表扩到 PS1/FC/MD（6 平台），v0.10.0 改为全部模拟器在线下载（插件包不集成），v0.11.0 补齐 10 平台 + 架构能力矩阵，v0.12.0 做模拟器 BIOS/固件部署 + portable 配置，v0.13.0 做仓库游戏提交（Issue/PR → 目录），v0.14.0 接入百度网盘官方 OpenAPI，v0.14.1 修复 3DS（Azahar）在 SteamOS 3.9.5 的兼容问题（优先官方 Flatpak），v0.15.0 把模拟器存档纳入云存档上传，v0.16.0 做模拟器存档恢复 + 按游戏拆分 + PS1 多碟 m3u，v0.17.0 百度网盘改为扫码登录（BDUSS/Cookie 主链路，OpenAPI 可选回退），v0.18.0 做扫描已安装游戏 + 百度扫码错误诊断，v0.19.0 下载/安装目录支持 SD 卡选择，v0.20.0 做 Decky 原生游戏库（不再依赖网页），v0.21.0 扫描已安装移到设置并自动补 Steam 快捷方式，v0.22.0 做诊断自检 + 一键诊断包，v0.23.0 原生库兜底 + 百度扫码超时/点击反馈，v0.24.0 修复原生库返回/关闭，v0.25.0 让 Steam 原有游戏不再显示插件时长块 |
| Releases v0.2.3 → v0.6 | 发布包约 50 MB | 增加**百度网盘**支持、**模拟器整合**、**资源池（用户上传）**、CRT 滤镜、点赞等 |
| Releases NewFreedeck v0.1 → v0.3 | 2026-08 ~ 09 重构版 | 模拟器可玩、稍后再玩 tab、分卷下载修复 |

由此得到几条直接结论：

- **仓库代码只是早期版本**：releases 里的百度网盘、模拟器、资源池等模块在 `main` 上完全不存在。不要在本仓库里寻找它们。
- **仓库缺运行时二进制**：`aria2_manager.py` / `seven_zip_manager.py` / `tianyi_client.py` 会优先查找 `defaults/runtime/` 下的 `aria2c`、`7zz`、`node`，但仓库本身不提交这些文件（已在 `.gitignore` 中）。插件可以不带它们启动，但要完整跑通下载/安装/云存档，克隆后必须先执行 `make runtime` 补齐，否则会分别报"下载组件不可用 / 解压组件不可用 / 未找到 node 运行时"。release zip 约 50 MB 与源码约 1 MB 的差值，主要就是这些二进制。
- **作者已停止维护**：NewFreedeck v0.1 的发布说明原文是"目前我没有精力与时间继续维护，抱歉，所以可以根据我整理的 skill 自行修改，最后可以给我推 pr"。
- **v0.25.0 库详情时长块按 managed 隔离**：`LibraryTimeBlock` 只在 `data.managed === true` 时渲染，未匹配/未加载直接 `return null`（不再对 Steam 原有游戏插入"已玩/主线/总时长"，也不先显示"加载中"）；后端 `get_library_game_time_stats()` **先按 AppID** `_resolve_installed_record_by_app_id`、再按标题匹配，未匹配返回 `managed=false` + 全 0 且**不调用 `resolve_hltb_stats`**；只影响插件安装的游戏（见 7.3）。
- **v0.24.0 原生库返回/关闭修复**：`LibraryPage` 新增 `onClose?`——modal 模式 `showModal(<LibraryPage onClose={() => modal.Close()} />)`，route 模式无 `onClose` 时 `handleClose` 用 `Navigation.NavigateBack()`；顶部新增 **sticky 固定栏**（返回/Steam 库/刷新，滚动仍可见），标题栏也保留「返回」；「Steam 库」关闭 modal/返回后 `Router.NavigateToLibraryTab()` 回 Steam 库（失败再 `NavigateBack`）（见 5.16）。
- **v0.23.0 原生库兜底 + 百度扫码超时/反馈**：QAM「游戏库」改为 **`showModal(<LibraryPage />)` 优先**、失败才 `Navigation.Navigate(LIBRARY_ROUTE)`（全屏路由保留）；主页显示 `QAM 原生 UI v0.23.0`、库页标题下显示 `原生 UI · v0.23.0` 便于确认前端是否更新；百度扫码点击立即 toast，前端 `withTimeout`（start 20s/poll 15s）、后端 `wait_for(request_qr, 12)`/图片 10s，超时给出明确文案并记 `Baidu QR ...` 日志（见 5.13 / 5.16）。
- **v0.22.0 诊断自检 + 一键诊断包**：QAM 设置新增「诊断」页（运行自检/导出诊断包）；`run_diagnostics()` 检查插件/目录/runtime/目录数据/Steam/存储/天翼网络/百度扫码/任务/日志，每项 `ok|warn|fail|skip` + detail/fix；`export_diagnostics()` 的 zip 新增 `self-check.json`，`export_diagnostics_to_downloads()` 写到下载目录（0600，`freedeckcy-diagnostics-<时间>.zip`）；百度 QR 自检只返回 sign 长度，不输出 sign/cookie（见 5.17）。
- **v0.21.0 扫描已安装迁移 + 自动补 Steam 快捷方式**：「扫描已安装游戏」从原生库「已安装」页移到 **QAM 设置 → 安装**；`scan_installed_games()` 新增 `list_all_shortcuts_sync()` 同名/同 exe 查重，PC 用 `_find_scanned_executable()` 找 exe、模拟器用 `ensure_emulator(allow_download=False)` + wrapper **自动补建 Steam 快捷方式**（模拟器未安装只记 `shortcut_error`、不自动下载）；第二遍为已有记录 `steam_app_id=0` 的 PC 补建；返回 `steam_added`/`steam_recovered_count`/`shortcut_error`（见 5.14 / 5.16）。
- **v0.20.0 Decky 原生游戏库**：QAM 新增 `LibraryPage`（路由 `/freedeckcy/library`，`routerHook.addRoute` 注册/卸载移除），主页「游戏库」按钮改为 `Navigation.Navigate(LIBRARY_ROUTE)`；原生库含「游戏库/已安装/刷新」Tab、搜索 + 平台/分类/排序下拉、20 条/页分页、安装 `ConfirmModal`（下载/安装大小、目录、模拟器/BIOS/setup 提示）与已安装启动/打开目录/卸载/扫描；全部走 Decky callable，不依赖本地 HTTP/CORS；网页库保留为备用（见 5.16）。
- **v0.19.0 下载/安装目录支持 SD 卡**：新增 `py_modules/storage_options.py`——解析 `/proc/mounts` 识别 `/run/media`（SteamOS SD）、`/media`、`/mnt`、`/storage`（DroidDeck）等可写挂载，过滤 proc/sysfs/tmpfs/overlay 等系统 fstype 与根挂载，`shutil.disk_usage` 返回 free/total；每个外置挂载给出 `freedeckCY/downloads`、`freedeckCY/installed` 建议目录；`GET /api/tianyi/storage/options` + QAM「路径」页一键切换（无外置时提示）（见 5.15）。
- **v0.18.0 扫描已安装 + 百度扫码错误诊断**：`scan_installed_games()` 扫 `settings.install_dir` **一层子目录**，按目录名/标题与目录条目匹配，跳过已记录 path/game_id，回填 Steam appid，模拟器平台用 `find_rom_file()` 找 ROM；HTTP `POST /api/tianyi/installed/scan` + 网页库「扫描已安装」按钮；百度扫码补 **BAIDUID CookieJar**、HTTP 状态/响应片段错误、轮询网络错误 `stage=failed`（不再一直 waiting）（见 5.13 / 5.14）。
- **v0.17.0 百度扫码登录（主链路）**：新增 `py_modules/baidu_qr.py`（Passport `getqrcode` → `unicast` 长轮询 → `qrbdusslogin` 换 `BDUSS/STOKEN/PTOKEN`）；QAM「百度网盘（扫码登录）」显示二维码，Cookie 持久化到 `state.json` 的 `baidu_login`；百度安装计划**优先 Cookie**，没有才用 OpenAPI（可选回退），都没有则提示扫码；任务 aria2 带百度 Cookie/Referer/UA；**仍不接 CDP/网页逆向**（见 5.13）。
- **v0.16.0 模拟器存档恢复 + 按游戏拆分 + PS1 多碟**：`restore_roots()`/`build_restore_targets()` 用**已知存档根白名单**限制恢复目标（同机恢复到原父目录、跨机落到第一个根），计划阶段统计冲突并要求确认，apply 沿用 `*.freedeckcy-bak-<时间戳>` 备份；PSP/PS3 用 `PARAM.SFO` 的 `TITLE`、3DS 用 NCSD 头 `0x108` 的 Program ID 做**单游戏拆分**（匹配不到回退共享目录）；PS1 `find_rom_file()` **`.m3u` 优先**，多 `.cue/.chd` 自动生成 `freedeckcy-multidisc.m3u`（自然排序、相对路径），单碟仍返回 `.cue`（见 5.10 / 5.11）。
- **v0.15.0 模拟器存档纳入云存档**：新增 `py_modules/emulator_saves.py`——按 10 平台标准目录 + portable/Flatpak 目录发现存档；GBA/FC/MD/NDS 按 ROM 文件名做**单游戏**匹配（找不到返回 `game_save_not_found`，绝不退化成整目录），PSP/PS1/PS2/3DS/PS3/Switch 返回**共享**记忆卡/标题目录并按路径签名去重（`emulator_saves_shared`）；设置 `cloud_save_include_emulators`（默认 true）控制是否参与上传；上传接入 `source_strategy="emulator_saves"`；恢复当时（v0.15.0）只支持 PC/Proton；**v0.16.0 起已支持模拟器存档恢复**（见 5.11）。
- **v0.14.1 修复 3DS（Azahar）SteamOS 兼容**：Azahar 官方 AppImage 在 SteamOS 有已知问题（上游 #127 打不开、#953 Game Mode 崩溃）；SteamOS 3.9.5 上优先用 **Flathub 官方 Flatpak `org.azahar_emu.Azahar`**，`ensure_emulator()` 按"env → 已装 Flatpak → SteamOS 自动装 Flatpak → AppImage 回退"选路；3DS 启动脚本强制 XWayland（`QT_QPA_PLATFORM=xcb`、`SDL_VIDEODRIVER=x11`）；已安装的 3DS 游戏由后台维护**自动重写启动脚本**，无需重装；system files 额外部署到 Flatpak 数据目录（见 5.10）。
- **v0.14.0 百度网盘（官方 OpenAPI）**：新增 `py_modules/baidu_openapi_client.py`（OAuth oob 授权/refresh、分享转存、dlink、清理）与 `py_modules/baidu_client.py`（**仅**用于公开分享 URL 的元数据解析，不带 Cookie）；百度链接走独立 provider（`baidu_openapi`），不要求天翼登录；安装计划/任务/重试按 provider 分流，下载 header 用 `Referer=https://pan.baidu.com/disk/home`、`UA=pan.baidu.com`；安装后清理 `/FreedeckTmp` 转存；v0.17.0 起改为扫码/Cookie 主链路、OpenAPI 作为可选回退（见 5.13；仍不接 CDP/网页逆向）。
- **v0.13.0 仓库游戏提交**：新增 `.github/ISSUE_TEMPLATE/submit-game.yml`（Issue 表单）与 `submissions/`（JSON + schema + 示例），`py_modules/submission.py` 做字段/平台别名/分享链接/openpath/重复 shareCode 校验，`merge_submissions()` 合并进目录 CSV 并归档到 `submissions/merged/`；网页库新增「提交游戏」按钮；CI 校验、`make validate-submissions`（见 5.12 / [submissions/README.md](../submissions/README.md)）。
- **v0.12.0 模拟器 BIOS/固件部署 + portable 配置**：新增 `py_modules/emulator_setup.py`——安装后把 `~/.local/share/freedeckCY/bios/<platform>/` 里的 BIOS/固件/keys 部署到模拟器实际读取的位置（压缩包用 7zz 解压并持久缓存），并写最小 portable 配置（DuckStation/PCSX2 的 INI、mGBA/PPSSPP 全屏）；PS3 固件在 `dev_flash` 为空时自动 `rpcs3 --installfw`；部署消息并入安装完成消息（见 5.10 - 模拟器 BIOS/固件部署）。
- **v0.11.0 补齐 10 平台 + 架构能力矩阵**：模拟器注册表新增 **3DS（Azahar）/ PS2（PCSX2）/ PS3（RPCS3）/ Switch（Eden）**，合计 **10 个平台**；3DS/PS2/PS3 官方包**仅 x86_64**，在 aarch64（含 DroidDeck）上目录查询按 `available_platforms()` 白名单**自动隐藏平台条目与筛选条**，Switch 有 x64/arm64 双包；3DS/PS3/Switch 需要 system files/固件/keys（`setup_hint` 提示），PS2 需要 BIOS（`bios/ps2/*.bin` 复制到 PCSX2 目录）（见 5.10）。
- **v0.10.0 模拟器全部在线下载**：插件包**不再集成任何模拟器**（删除 `scripts/fetch_emulator.sh` 与 `make emulator-runtime`，包体积从约 68 MB 降到约 45 MB）；6 个平台（含 GBA）的官方包都在首次安装时从 GitHub release 下载到 `~/.local/share/freedeckCY/emulators/<platform>/<arch>/`，离线环境可手动预置缓存或设 `FREEDECKCY_*_BIN`（见 5.10 / 5.7）。
- **v0.9.0 模拟器扩到 6 平台**：注册表新增 **PS1（DuckStation，需自备 BIOS）/ FC（Mesen2）/ MD（Mesen2，与 FC 共享缓存）**；PS1 BIOS 放 `~/.local/share/freedeckCY/bios/ps1/`，安装时复制到 `~/.local/share/duckstation/bios/`，缺失只提示不阻断；FC/MD 的 Mesen2 是 zip 内单个可执行文件；PS2/PS3/3DS/Switch 因 x64-only 官方包或需固件/keys 暂未接入（见 5.10）。
- **v0.8.0 自动云存档**：内置 **Ludusavi 存档清单**（53,549 款游戏，MIT）做标题/SteamID 匹配并把 `<winAppData>` 等模板解析到 Proton 前缀，与原有 Proton 扫描合并；`gamewatch` 每 8 秒用 `/proc/*/cmdline`（无 `/proc` 时 `pgrep -f`）检测游戏退出，**只对刚退出的游戏**自动触发云存档上传（设置 `cloud_save_auto_upload` 默认开启、30 秒防抖）；上传前用"相对路径+大小+mtime"指纹去重，未变化则 `reason=unchanged` 跳过（见 5.11）。
- **v0.7.0 通用模拟器注册表**：`EmulatorSpec` 注册表接入 **GBA（mGBA 0.10.5）/ PSP（PPSSPP 1.20.4）/ NDS（melonDS 1.1）** 三个平台——（当时 GBA 随包内置，**v0.10.0 起改为全部在线下载**）PSP/NDS 首次安装按需下载官方 AppImage（NDS 为 zip 内 AppImage），统一 `--appimage-extract` 解包（不依赖 FUSE），生成启动脚本后以原生 Linux 快捷方式注册（不写 Proton）；PS1 因 BIOS 依赖暂缓，其它平台仍只可浏览（见 5.10 / ROADMAP 9.8）。
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
| 自动云存档（v0.8.0；v0.15.0 模拟器存档；v0.16.0 恢复/拆分） | **Ludusavi 清单** + **gamewatch** 进程检测；退出后只上传该游戏，指纹去重；v0.15.0 起非 PC 平台走 `emulator_saves.py` 发现模拟器存档（单游戏/共享目录），设置 `cloud_save_include_emulators` 可关；v0.16.0 支持恢复（白名单目标/备份/冲突确认）与 PSP/PS3/3DS 按游戏拆分 | `py_modules/save_manifest.py`、`py_modules/gamewatch.py`、`py_modules/emulator_saves.py`、`defaults/ludusavi/` |
| 百度网盘（v0.17.0，扫码/Cookie 主链路） | Passport 二维码登录（`getqrcode` → `unicast` → `qrbdusslogin`）换 `BDUSS/STOKEN/PTOKEN`，Cookie 存 `state.json` 的 `baidu_login`；分享解析/下载走 Cookie，aria2 带百度 Cookie/Referer/UA；**OpenAPI 仅可选回退**（自建应用 OAuth，v0.14.0）；不接 CDP/网页逆向 | `py_modules/baidu_qr.py`、`py_modules/baidu_client.py`、`py_modules/baidu_openapi_client.py`、`tianyi_store.BaiduLoginState` |
| 仓库游戏提交（v0.13.0） | GitHub Issue 表单 / `submissions/*.json` PR → `submission.py` 校验 → `merge_submissions.py` 写入目录 CSV → `submissions/merged/` 归档；纯标准库 CLI，无运行时依赖 | `py_modules/submission.py`、`submissions/`、`.github/ISSUE_TEMPLATE/submit-game.yml`、`scripts/{validate,merge}_submissions.py` |
| 模拟器运行时（v0.6.0 起，v0.7.0 注册表，v0.9.0 六平台，v0.10.0 全部在线下载，v0.11.0 十平台，v0.12.0 部署 BIOS/固件） | **GBA=mGBA / PSP=PPSSPP / NDS=melonDS / PS1=DuckStation / FC、MD=Mesen2 / 3DS=Azahar / PS2=PCSX2 / PS3=RPCS3 / Switch=Eden**；**插件包不集成模拟器**，首次安装按需从官方 release 下载并解包；安装后 `emulator_setup.setup_emulator()` 部署 BIOS/固件/keys 并写 portable 配置；3DS/PS2/PS3 官方包仅 x86_64，aarch64 上自动隐藏 | `py_modules/emulator_manager.py`（注册表/下载）、`py_modules/emulator_setup.py`（部署/portable 配置）、`~/.local/share/freedeckCY/{emulators,bios}/<...>/` |

运行时一共会拉起 **4 类进程**：Decky 的 Python 进程、`aria2c`、`7zz`、偶尔的 `node`。

### 3.1 运行环境与平台（Steam Deck / DroidDeck，v0.4.0）

| 项 | Steam Deck | DroidDeck |
|---|---|---|
| CPU 架构 | x86_64 | **aarch64（ARM64）** |
| 运行环境 | SteamOS | Android 上的 proot SteamOS 运行时，HOME 通常 `/root` |
| Steam 根 | `~/.steam/steam` / `~/.local/share/Steam` / Flatpak | 同上；x64 客户端另有 `~/.droiddeck-x64/.local/share/Steam` |
| Proton 工具 | `proton_experimental` 等 Valve 工具 | **ARM 工具名** `droiddeck-proton-arm64` / `droiddeck-proton-11-arm64` |
| 运行时二进制 | `defaults/runtime/x86_64/` | `defaults/runtime/aarch64/` |

- **运行时架构**：aria2c / 7zz / node 都按 `platform.machine()` 归一（`x86_64`；`aarch64`/`arm64`→`aarch64`）后找 `defaults/runtime/<arch>/`，见 [aria2_manager.py:107](../py_modules/aria2_manager.py) `_resolve_binary_path()`、[seven_zip_manager.py:26](../py_modules/seven_zip_manager.py) `_resolve_binary_path()`、[tianyi_client.py:631](../py_modules/tianyi_client.py) `_runtime_arch()`。
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
├── package.json                # 版本 0.26.29；build=rollup；前端依赖
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
├── tests/                      # pytest 单测（552 个用例，不联网、不碰 Steam 目录；模拟器下载/部署/存档发现/恢复计划/已安装扫描/挂载检测/自检走 mock；提交校验用临时 CSV；百度 HTTP/扫码走 mock；原生库/超时为前端构建验证）
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
- **控制面 2**：Vue 页面 ↔ 本地 HTTP API（`py_modules/tianyi_http.py` 的 38 条 `/api/tianyi/*` 路由，路由表在 [tianyi_http.py:704](../py_modules/tianyi_http.py) `setup_routes()`）。
- **控制面 3**：Python ↔ Node 子进程（stdin 一行 JSON，stdout 一行 JSON；node 解析见 [tianyi_client.py:641](../py_modules/tianyi_client.py) `_resolve_node_binary()`）。
- **数据面**：`aria2c` 从 `api.cloud.189.cn` 拿到的直链下载到本地磁盘。

### 5.3 两个前端的分工

| | QAM 面板（React） | 本地网页（Vue） |
|---|---|---|
| 路由 | 插件内容区 + `/freedeckcy/settings` | `/tianyi/library`、`/tianyi/library/login-bridge` |
| 页面 | 登录状态/入口、下载队列（最多 20 条，自绘进度条）、已安装游戏预览+卸载；设置页 4 个 tab（路径/安装/下载/账号，账号页含云存档上传与恢复） | **两个**：游戏库橱窗（打开即浏览全部资源 + 搜索/平台/分类筛选 + 分页 + 排序 + 「已安装」页签 + 诊断/更新工具条 + 安装确认弹窗）、二维码登录桥 |
| 能干什么 | 看任务、暂停/继续/移除任务、改设置、管云存档、卸载（除了卸载，**不能**自己发起下载） | **唯一能"下单"的地方**：浏览→确认→创建下载任务 |
| 交互特点 | 900 ms / 6 s / 30 s 三档轮询 | 手柄/键盘双焦点模型（160 ms 轮询、方向键导航、A/B/X/Y/L1/R1 快捷键，为掌机设计；详见 5.8） |
| 怎么打开 | 插件自带 | 调 RPC 拿 URL → `SteamClient.Browser.OpenUrl`（Steam 内置浏览器），不是 iframe/webview |

QAM 主面板由登录/操作入口、下载列表、已安装游戏预览等 `PanelSection` 组成，代码在 [src/index.tsx:3137](../src/index.tsx) `Content()` 到文件末尾；设置页是 `Tabs` 四页（路径 / 安装 / 下载 / 账号），在 [src/index.tsx:1730](../src/index.tsx) `SettingsPage()`。

### 5.4 前端调用面

**RPC（[src/index.tsx:425](../src/index.tsx) 起，全部 `callable("...")`，共 20 个天翼 RPC）**

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
- `down_url` 支持两种天翼分享链接：`https://cloud.189.cn/t/<code>?pwd=...` 与 `https://cloud.189.cn/web/share?code=...`（后者必须带 `code=`）；目录校验 [game_catalog.py:138](../py_modules/game_catalog.py) `_is_valid_tianyi_url()` 与协议层 [tianyi_client.py:188](../py_modules/tianyi_client.py) `parse_share_url()` 都兼容两种形式；
- v0.2.0 新增 4 个可选列：`platform`（默认 `pc`；别名 `steam/windows/win`→`pc`、`ns/nsx`→`switch`）、`cover_url`（横版）、`cover_portrait_url`（竖版）、`steam_appid`；
- 目录文件优先级（[game_catalog.py:159](../py_modules/game_catalog.py) `resolve_default_catalog_path()`）：`FREEDECKCY_GAME_CATALOG_CSV` → 插件目录 `freedeckcy_catalog.csv` → 旧版 `gamebox_all_links_20260221_234730.csv`（回退）→ `defaults/tianyi_catalog.csv` → 当前目录下的 export 副本；
- 当前内置 `freedeckcy_catalog.csv`：**7084 条有效、11 个平台** —— PC 2540 / FC 1475 / NDS 722 / PSP 575 / GBA 553 / 3DS 305 / PS2 250 / PS1 194 / PS3 194 / MD 191 / Switch 85；
- 分类已清洗（v0.3.1，见 5.6）：Top12（计数，一条可属多分类）——动作冒险 3483、角色扮演 970、**模拟器 606**、策略战棋 535、模拟经营 371、休闲益智 352、枪战射击 272、体育竞速 258、恐怖惊悚 119、卡牌桌游 59、格斗清版 29、即时战略 14；**分类中不再出现平台名**（GBA/Switch 等已并入「模拟器」）；
- 旧 `gamebox_all_links_20260221_234730.csv` 保留为回退（2845 行 / 2685 条有效，全 PC），新目录缺失时仍能启动；
- **远程 JSON 目录（v0.6.1/v0.6.2）**：`FREEDECKCY_CATALOG_JSON` 可指向本地 JSON 或 `https://…` URL（NewFreedeck 兼容格式，[game_catalog.py:183](../py_modules/game_catalog.py) `resolve_default_catalog_json_path()`）；远程内容缓存 6 小时（[game_catalog.py:23](../py_modules/game_catalog.py) `REMOTE_CATALOG_TTL_SECONDS`），拉取失败回退本地 CSV/缓存。默认关闭，只在显式设置 `FREEDECKCY_CATALOG_JSON` 时启用；游戏目录默认由设置页下载服务器 CSV 到本地。

**封面索引（`defaults/tianyi_catalog/cover_index.csv`，仓库已内置）**：

- 路径（[game_catalog.py:204](../py_modules/game_catalog.py) `resolve_default_cover_index_path()`）：环境变量 `FREEDECKCY_COVER_INDEX_CSV` 优先（兼容旧 `FRIENDECK_COVER_INDEX_CSV`），其次插件目录 `defaults/tianyi_catalog/cover_index.csv`；当前仓库内置 **3470 行**，缺失时自动跳过（封面走在线解析）；
- 表头：`game_id,title,steam_appid,cover_url,cover_portrait_url,platform`；
- 列名兼容：横版 `cover_url` / `landscape_cover_url` / `cover`；竖版 `cover_portrait_url` / `square_cover_url` / `portrait_url` / `portrait`；appid `steam_appid` / `app_id` / `appid`；
- 合并规则（[game_catalog.py:491](../py_modules/game_catalog.py) `_merge_cover_index()`）：先按 `game_id` 精确匹配，其次按标题（去空白、小写）匹配；**只补空值，不覆盖目录 CSV 已有值**；`platform` 也可被索引补齐；合并后 **6823 / 7084 条资源自带封面（96.3%）**；`summary()` 汇总 `cover_index_total` / `with_cover` / `platforms`。

**封面解析优先级**（[tianyi_service.py:2279](../py_modules/tianyi_service.py) `resolve_catalog_cover()`）：

1. **目录/封面索引静态封面**（[tianyi_service.py:2251](../py_modules/tianyi_service.py) `_catalog_entry_cover()`）：CSV/索引自带 `cover_url`/`cover_portrait_url` 直接用；只有 `steam_appid` 时合成 Steam CDN 图（横版 `.../apps/<appid>/header.jpg`、竖版 `.../apps/<appid>/library_600x900.jpg`），`source="catalog"`；
2. **内存 + 磁盘缓存**（[tianyi_service.py:2199](../py_modules/tianyi_service.py) `_load_cover_cache()` / [tianyi_service.py:2228](../py_modules/tianyi_service.py) `_save_cover_cache()`）：`~/.local/share/freedeckCY/tianyi/cover_cache.json`（目录 0700、文件 0600、临时文件 + `os.replace` 原子写；启动时只加载未过期项）；正结果 TTL **7 天**（`CATALOG_COVER_CACHE_TTL_SECONDS`），负结果 TTL **30 分钟**（`CATALOG_COVER_NEGATIVE_TTL_SECONDS`）；
3. **Steam 商店搜索**（`store.steampowered.com/api/storesearch`，中文/中国区，最多 8 个候选）；
4. **ProtonDB 兼容性等级**（拿到 appid 后附加查询，仅作 `protondb_tier` 展示字段）。

解析结果写回内存并落盘；`/api/tianyi/catalog/cover` 返回 `cover_url/square_cover_url/source/matched_title/app_id/protondb_tier/cached`。`cached=true` 表示来自静态封面或缓存。

**平台 / 分类筛选**：

- `GET /api/tianyi/catalog?q=&page=&page_size=&platform=&category=`（[tianyi_http.py:270](../py_modules/tianyi_http.py) `handle_catalog()`；过滤实现在 [game_catalog.py:578](../py_modules/game_catalog.py) `list()`），返回 `items/total/page/page_size/platforms/categories/platform/category`；`platforms` 为各平台计数（降序，[game_catalog.py:550](../py_modules/game_catalog.py) `platform_counts()`），`categories` 为分类 Top12（`CATEGORY_FILTER_LIMIT`，[game_catalog.py:562](../py_modules/game_catalog.py) `category_counts()`）；
- `platform` 传 `all`/`*` 视为不筛选；`category` 对 `categories` 字段做大小写不敏感子串匹配；平台与分类可组合（如 `platform=gba&category=动作冒险`）；
- 库页现状（v0.3.0）：搜索后显示**两行筛选条**——第一行「全部平台」+ 各平台（带计数），第二行「全部分类」+ Top12 分类（带计数）；手柄焦点顺序：搜索框 → 搜索按钮 → **平台条** → **分类条** → 卡片；卡片对非 `pc` 平台显示平台标签；
- **平台筛选已实现**（v0.3.0）：`platforms` 数量 > 1 时前端才显示平台条，当前 11 个平台所以可见；选择平台后请求带 `platform` 参数并刷新列表。
- **GBA 可安装、其它模拟器平台只可浏览**（v0.6.0）：前端对 GBA 卡片正常打开安装确认（弹窗显示"模拟器：mGBA"），其它非 PC 平台仍 flash 提示；后端 `_build_install_plan()` 只放行 `pc`/`gba`，其余抛"只支持 PC 与 GBA（mGBA）资源"。GBA 闭环见 5.10，其它平台见 ROADMAP 9.8。

### 5.6 分类清洗与目录数据体检（v0.3.1）

**分类清洗规则**（[game_catalog.py:89](../py_modules/game_catalog.py) `normalize_categories()`）：

- 分隔符：`,`、`，`、`/`、`、`、`;`、`；`、`|` 全部视为分类分隔符；
- 逐段去空白，**不区分大小写去重**，输出统一用英文逗号连接；
- 剔除平台名 token（[game_catalog.py:25](../py_modules/game_catalog.py) `PLATFORM_TOKENS`：`pc/fc/nds/psp/gba/3ds/ps1/ps2/ps3/md/switch/ns/arcade/psx`）以及该行自身的 `platform`；
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

- 单架构打包会删掉 `defaults/runtime/{aria2,7z,node}/*/<arch>` 下其它架构目录，避免包体积翻倍；打包前先 `make runtime ARCH=aarch64`（或 `ARCH=all`）准备 arm64 的 aria2c / 7zz / node（**模拟器不参与打包**，`make emulator-runtime` 与 `scripts/fetch_emulator.sh` 已在 v0.10.0 删除）；
- **插件包不包含任何模拟器**：10 个平台的官方包全部在首次安装时按需下载（需要网络，失败会报错可重试），因此包体积从约 68 MB 降到约 45 MB；离线环境可提前把官方包放到 `~/.local/share/freedeckCY/emulators/<platform>/<arch>/`（AppImage 需可执行）或用 `FREEDECKCY_*_BIN` 指向本地版本；PS1 BIOS 仍由用户自备；
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

- 列表 `GET /api/tianyi/installed`：handler [tianyi_http.py:304](../py_modules/tianyi_http.py) `handle_installed_games()` → 服务 [tianyi_service.py:6710](../py_modules/tianyi_service.py) `list_installed_games()`；返回 `{total, items[]}`，按 `updated_at` 倒序，补 `exists`（目录还在不在）、`platform`/`cover_url`/`cover_portrait_url`/`steam_appid`。
- 启动 `POST /api/tianyi/installed/launch`：handler [tianyi_http.py:313](../py_modules/tianyi_http.py) `handle_installed_launch()` → [tianyi_service.py:6735](../py_modules/tianyi_service.py) `launch_installed_game()`；用 `_launch_external("steam://rungameid/<appid>")` 拉起 Steam，AppID 缺失时报"请从 Steam 库手动启动"。
- 打开目录 `POST /api/tianyi/installed/open-folder`：handler [tianyi_http.py:323](../py_modules/tianyi_http.py) `handle_installed_open_folder()` → [tianyi_service.py:7091](../py_modules/tianyi_service.py) `open_installed_folder()`；先校验目录存在再 `_launch_external(install_path)`。
- 卸载 `POST /api/tianyi/installed/uninstall`：handler [tianyi_http.py:350](../py_modules/tianyi_http.py) `handle_installed_uninstall()`（`delete_files` 默认 true、`delete_compatdata` 默认 false）→ 复用 `uninstall_installed_game()`。

卡片显示封面、安装大小、游玩时长（缺失显示 `-`）；点击卡片启动，卡片内按钮分别打开目录/卸载；卸载走自定义 confirm，完成后刷新已安装列表 + 游戏库列表。

**自定义 confirm 弹窗**：`showConfirm()` 记录返回焦点、初始焦点在"确认"(index 1)，`confirmAction()` 关弹窗后执行回调并恢复焦点；Esc/B 等价"取消"。已安装页签的启动入口已按 `mode` 分支：鼠标点击卡片、键盘 Enter、手柄 A 都调用 `launchInstalled()`。

### 5.9 诊断与更新（v0.5.0）

**`GET /api/tianyi/diagnostics`**（JSON，本地只读；handler [tianyi_http.py:365](../py_modules/tianyi_http.py) `handle_diagnostics()` → [tianyi_service.py:7119](../py_modules/tianyi_service.py) `get_diagnostics()`）：`version / python / system / arch / paths(plugin_dir, state_file, log_file, steam_root) / runtime(aria2c,7zz,node 的存在性+大小) / steam(root_exists, proton_tool, droiddeck) / catalog(total, platforms, cover_index_total, with_cover) / tasks(counts,total) / installed(total,bytes,missing_paths) / settings / recent_errors / log_tail`。

- 脱敏：`_redact_text()` 把 HOME 替换成 `~`，并对 `cookie / authorization / token / sessionkey / accesstoken / uid / pwd` 的键值统一替换为 `<redacted>`；
- 日志：`_tail_text(/tmp/freedeckcy.log, 300)` 取末尾 300 行，再筛出含 `ERROR/Exception/失败` 的最近 20 行到 `recent_errors`。

**`GET /api/tianyi/diagnostics/export`**（handler [tianyi_http.py:382](../py_modules/tianyi_http.py) `handle_diagnostics_export()` → [tianyi_service.py:7423](../py_modules/tianyi_service.py) `export_diagnostics()`）：内存生成 zip（`Content-Disposition: attachment; filename="freedeckcy-diagnostics.zip"`），内含：

| 文件 | 内容 |
|---|---|
| `diagnostics.json` | 上面的 JSON（`log_tail` 已移出，避免与 log-tail.txt 重复） |
| `log-tail.txt` | 日志末尾 300 行（同样脱敏） |
| `README.txt` | 诊断包说明 + 提交 issue 指引 |

**`GET /api/tianyi/update-check`**（handler [tianyi_http.py:395](../py_modules/tianyi_http.py) `handle_update_check()` → [tianyi_service.py:7466](../py_modules/tianyi_service.py) `check_update()`）：请求 `https://api.github.com/repos/hulong1989/freedeckCY/releases/latest`（10 s 超时，未认证 GitHub API 有速率限制）；结果 `{ok, current, latest, has_update, url, name, published_at}`，`has_update = _parse_version(latest) > _parse_version(current)`；成功结果在内存缓存 **1 小时**（`_update_cache`），失败返回 `ok: false` + `message`（网络错误/HTTP 状态）。

**公共 helper**：[tianyi_service.py:394](../py_modules/tianyi_service.py) `_tail_text()`（读文件末尾 N 行）、[tianyi_service.py:419](../py_modules/tianyi_service.py) `_redact_text()`（脱敏）、[tianyi_service.py:428](../py_modules/tianyi_service.py) `_parse_version()`（从 `v0.5.0`/`0.5.0-pre` 提取数字元组比较）、[tianyi_service.py:434](../py_modules/tianyi_service.py) `_launch_external()`（优先 `xdg-open`，否则 `gio open`；拉起 `steam://rungameid/...` 或安装目录）。

### 5.10 模拟器注册表与接入平台（v0.6.0 起 / v0.7.0 注册表 / v0.9.0 六平台 / v0.10.0 全部在线下载 / v0.11.0 十平台 + 架构矩阵）

**注册表**：[emulator_manager.py:30](../py_modules/emulator_manager.py) `EmulatorSpec` 描述一个平台（`platform / name / adapter / repo / download_base / assets{arch: 文件名} / archive(appimage|zip) / launch_args / rom_extensions / env_var / min_bytes / state_key / executables / bios_required / setup_required / setup_hint`），[emulator_manager.py:55](../py_modules/emulator_manager.py) `EMULATORS` 是注册表本体；[emulator_manager.py:238](../py_modules/emulator_manager.py) `available_platforms(arch)` 返回"当前架构有官方包"的平台，[emulator_manager.py:256](../py_modules/emulator_manager.py) `get_spec()` / [emulator_manager.py:265](../py_modules/emulator_manager.py) `supported_platforms()` 供服务层与诊断使用。当前接入 **10 个平台，全部首次安装在线下载**：

| 平台 | 模拟器 | 版本 / 仓库 | 官方资产（架构） | 启动参数 | ROM 扩展名 | 依赖 / 环境变量 |
|---|---|---|---|---|---|---|
| gba | mGBA | 0.10.5 / mgba-emu/mgba | appimage：x64（约 25MB）/ arm64（约 24.6MB） | `-f {rom}` | `.gba` | `FREEDECKCY_MGBA_BIN` |
| psp | PPSSPP | 1.20.4 / hrydgard/ppsspp | appimage：x86_64 / aarch64 | `--fullscreen {rom}` | `.iso` `.cso` `.pbp` `.elf` | `FREEDECKCY_PPSSPP_BIN` |
| nds | melonDS | 1.1 / melonDS-emu/melonDS | zip 内 AppImage：x86_64 / aarch64 | `{rom}` | `.nds` `.dsi` `.srl` | `FREEDECKCY_MELONDS_BIN` |
| ps1 | DuckStation | `latest` / stenzek/duckstation | appimage：x64 / arm64 | `-batch -fullscreen {rom}` | `.cue` `.m3u` `.chd` `.iso` `.pbp` `.bin` | PS1 BIOS；`FREEDECKCY_DUCKSTATION_BIN` |
| fc | Mesen2 | 2.1.1 / SourMesen/Mesen2 | zip 内单文件 `Mesen`：x86_64 / ARM64 | `/fullscreen {rom}` | `.nes` `.fds` `.unf` `.unif` | `FREEDECKCY_MESEN_BIN` |
| md | Mesen2 | 2.1.1 / SourMesen/Mesen2 | 同上，与 FC 共享缓存 | `/fullscreen {rom}` | `.md` `.gen` `.smd` `.bin` `.32x` | 同 FC |
| 3ds | Azahar | 2126.2 / azahar-emu/azahar | **SteamOS 优先 Flathub Flatpak `org.azahar_emu.Azahar`**；否则 appimage（**仅 x86_64**，`azahar.AppImage`） | `{rom}` | `.3ds` `.cci` `.cxi` `.app`（`.cia` 走 `--install`） | 3DS system files（setup）；`FREEDECKCY_AZAHAR_BIN`；Flatpak `flatpak_id` |
| ps2 | PCSX2 | v2.8.2 / PCSX2/pcsx2 | appimage：**仅 x86_64** | `-batch -fullscreen {rom}` | `.iso` `.chd` `.cue` `.bin` `.gz` | PS2 BIOS；`FREEDECKCY_PCSX2_BIN` |
| ps3 | RPCS3 | build-8d6b42e / RPCS3/rpcs3-binaries-linux | appimage：**仅 x86_64** | `--no-gui {rom}` | `.iso` `.pkg` `.elf` `.self` | PS3 固件（setup）；`FREEDECKCY_RPCS3_BIN` |
| switch | Eden | v0.2.1 / stable.eden-emu.dev | appimage：**x86_64 + aarch64** | `{rom}` | `.nsp` `.xci` | prod.keys + 固件（setup）；`FREEDECKCY_EDEN_BIN` |

**架构能力矩阵**（[emulator_manager.py:238](../py_modules/emulator_manager.py) `available_platforms()` 按 `spec.assets` 是否含当前 arch 判定）：

| 架构 | 可用平台 | 说明 |
|---|---|---|
| x86_64 | 全部 10 个 | GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch |
| aarch64（DroidDeck/ARM） | **GBA/PSP/NDS/PS1/FC/MD/Switch**（7 个） | 3DS/PS2/PS3 官方无 arm64 包 → **目录查询用白名单过滤，条目与平台筛选条都不出现**；`emulator_status()` 对它们返回 `available=false`（message 含"已隐藏该平台"） |

**目录白名单**：`TianyiService.list_catalog()` 传入 `["pc", *available_platforms()]`，`GameCatalog.list(..., allowed_platforms=...)` 先按白名单过滤条目，再算 `platforms`/`categories` 计数与分页——所以 aarch64 上不会出现"点进去装不了"的隐藏平台条目。

**解析顺序**（[emulator_manager.py:456](../py_modules/emulator_manager.py) `resolve_command()`，无内置包分支）：

1. `FREEDECKCY_<PLATFORM>_BIN` 环境变量（spec.env_var，指向可执行文件/AppImage）；
2. 已下载并解包的模拟器（[emulator_manager.py:320](../py_modules/emulator_manager.py) `installed_command()`）：`~/.local/share/freedeckCY/emulators/<state_key>/<arch>/`（[emulator_manager.py:306](../py_modules/emulator_manager.py) `_find_spec_executable()` 按 `executables` 找 Mesen2 等非 AppImage 可执行文件；AppImage 解包目录里再找 `squashfs-root/`）；GBA 兼容旧路径 `emulators/<arch>/squashfs-root/`；
3. 系统命令（[emulator_manager.py:334](../py_modules/emulator_manager.py) `system_command()`：`mgba/ppsspp/melonds/duckstation/Mesen` 等，见实现）；
4. Flatpak（[emulator_manager.py:349](../py_modules/emulator_manager.py) `flatpak_command()`；mGBA 的 `io.mgba.mGBA`）；**3DS 例外**：注册表 `flatpak_id=org.azahar_emu.Azahar`，已安装时直接返回 `flatpak run org.azahar_emu.Azahar`（SteamOS 上由 `_ensure_flatpak()` 自动安装，见本节末尾）；
5. 都没有时：[emulator_manager.py:540](../py_modules/emulator_manager.py) `emulator_status()` 返回 `available=True, source="download", requires_setup=True`（附 `asset/url/bios_*/setup_*`；无 `source=bundled`）；安装时由 [emulator_manager.py:689](../py_modules/emulator_manager.py) `ensure_emulator()` 选择来源：3DS 在 **env `FREEDECKCY_AZAHAR_BIN` 优先**，否则 **已装 Flatpak 或 SteamOS（且允许下载）优先 Flatpak**，Flatpak 不可用/安装失败才回退 AppImage 下载/解包。**若当前 arch 没有官方资产**则返回 `available=false`（message 含"已隐藏该平台"），前端/目录白名单会隐藏。兼容旧接口：[emulator_manager.py:729](../py_modules/emulator_manager.py) `ensure_mgba()`。

**按需下载与解包**（不依赖 FUSE）：

- [emulator_manager.py:639](../py_modules/emulator_manager.py) `_download_asset()`：下载到 `~/.local/share/freedeckCY/emulators/<state_key>/<arch>/<资产名>`（HTTP 非 200 / 文件小于 `min_bytes` 会删文件并报错，可重试）；**FC/MD 共用 `state_key="mesen"`**；
- zip 资产：NDS 是 zip 内 AppImage，[emulator_manager.py:623](../py_modules/emulator_manager.py) `_extract_zip_emulator()` 解压后先找 `executables` 指定的可执行文件（Mesen2 的 `Mesen`），否则找 `.appimage`；AppImage 再走 [emulator_manager.py:609](../py_modules/emulator_manager.py) `_run_appimage_extract()` 解包到平台目录，[emulator_manager.py:669](../py_modules/emulator_manager.py) `_ensure_extracted()` 在解包失败时退回直接运行 AppImage。下载/解包失败会写进安装消息。

**ROM 选择与启动参数**：[emulator_manager.py:750](../py_modules/emulator_manager.py) `find_rom_file()` 按平台扩展名过滤（上表；PS1 优先 `.m3u`，PS2 优先 `.iso` 等），优先 `openpath` 同名，其次按扩展名优先级+路径长度选；**PS1 多碟**：已有 `.m3u` 直接返回；否则多张 `.cue/.chd` 时按自然顺序生成 `freedeckcy-multidisc.m3u`（相对路径、`#EXTM3U`），单碟仍返回 `.cue`；[emulator_manager.py:800](../py_modules/emulator_manager.py) `create_launch_wrapper()` 按 spec.launch_args 生成 `<install_dir>/launch-freedeckcy.sh`（GBA `-f`、PSP `--fullscreen`、PS1/PS2 `-batch -fullscreen`、PS3 `--no-gui`、FC/MD `/fullscreen`、NDS/3DS/Switch 直接接 ROM）。**3DS 的 wrapper 额外注入 `QT_QPA_PLATFORM=xcb`、`SDL_VIDEODRIVER=x11`**，强制走 XWayland，规避 Azahar 在 Game Mode/Wayland 下的崩溃。

**模拟器 BIOS / 固件部署（v0.12.0，`py_modules/emulator_setup.py`）**：

- 安装完成后由 [emulator_setup.py:383](../py_modules/emulator_setup.py) `setup_emulator(platform, command, seven_zip=...)` 统一部署：先调 [emulator_setup.py:177](../py_modules/emulator_setup.py) `_source_files()` 递归扫描 `~/.local/share/freedeckCY/bios/<platform>/`，收集 `.bin/.rom/.bios/.keys/.pup/.nca`；zip/7z/rar/tar/gz/tgz/xz/bz2 等压缩包用 [emulator_setup.py:152](../py_modules/emulator_setup.py) `_extract_archives()` 调 7zz 解压，产物复制到 `bios/<platform>/_extracted/` 作**持久缓存**（下次不再解压）；
- **只创建缺失项/只改单个键**：[emulator_setup.py:61](../py_modules/emulator_setup.py) `_set_ini_value()` 在已有 INI 里只修复目标键并保留其它配置；配置文件已存在时不覆盖；
- **不自动下载** BIOS/固件/keys（版权原因），缺失时返回面向用户的提示；`bios_required` 平台还会追加"未检测到 BIOS"消息；
- 各平台目标路径与 portable 配置：

| 平台 | 部署内容 | 目标路径 / portable 配置 |
|---|---|---|
| PS1 | BIOS（`scph*.bin`） | [emulator_setup.py:216](../py_modules/emulator_setup.py) `_write_duckstation()`：`<AppDir>/portable.txt` + `portable_data/settings/settings.ini`（`[BIOS] SearchDirectory=./bios`、`[Display] Fullscreen=true`，已存在则用 `_set_ini_value` 修复这两个键）；BIOS 复制到 `<AppDir>/bios`，同时旧 `prepare_bios()` 仍复制到 `~/.local/share/duckstation/bios` |
| PS2 | BIOS（`*.bin`） | [emulator_setup.py:245](../py_modules/emulator_setup.py) `_write_pcsx2()`：`<AppDir>/portable.ini` + `inis/PCSX2.ini`（`[Folders] Bios=<AppDir>/bios`、`[UI] Fullscreen=true`）；BIOS 复制到 `<AppDir>/bios`、`~/.local/share/PCSX2/bios`、`~/.config/PCSX2/bios` 三处 |
| NDS | `bios7.bin/bios9.bin/firmware.bin/dsi_firmware.bin` 等 | [emulator_setup.py:295](../py_modules/emulator_setup.py) `_deploy_nds()`：复制到 `<AppDir>` 与 `~/.local/share/melonDS` |
| Switch | `prod.keys`/`title.keys` + 固件 `.nca` | [emulator_setup.py:304](../py_modules/emulator_setup.py) `_deploy_switch()`：keys → `~/.local/share/eden/keys/`；固件压缩包解出的 `.nca` 目录 → `~/.local/share/eden/nand/system/Contents/registered/` |
| PS3 | `PS3UPDAT.PUP` | [emulator_setup.py:337](../py_modules/emulator_setup.py) `_install_rpcs3_firmware()`：若 `~/.config/rpcs3/dev_flash` 为空且 RPCS3 可执行，执行 `rpcs3 --installfw <pup>`（600s 超时，失败原因写进消息） |
| 3DS | system files（`sysdata`） | [emulator_setup.py:362](../py_modules/emulator_setup.py) `_deploy_3ds()`：复制到 `~/.local/share/azahar-emu/sysdata`（兼容旧 `azahar`/`citra`），以及 Flatpak 数据目录 `~/.var/app/org.azahar_emu.Azahar/data/azahar-emu/sysdata`；`bios/3ds/` 的 `nand/`、`sdmc/`、`sysdata/` 或压缩包按布局部署，保留目录树且不覆盖已有文件 |
| GBA | portable 配置 | [emulator_setup.py:272](../py_modules/emulator_setup.py) `_write_mgba_config()`：`portable.ini` + `qt.ini`（`[General] fullScreen=true`） |
| PSP | portable 配置 | [emulator_setup.py:285](../py_modules/emulator_setup.py) `_write_ppsspp_config()`：`portable.txt` + `memstick/PSP/SYSTEM/ppsspp.ini`（`[General] FullScreen=True`） |

- `<AppDir>` 是 `ensure_emulator()` 返回的可执行文件所在目录（AppImage 解包后是 `squashfs-root/`）；目录不可写时只写用户数据目录并提示；
- 部署消息由 `setup_emulator()` 返回，服务层把它并入**安装完成消息**（不再单独发 `warning` 字段）；`emulator_status()`/plan 仍返回 `bios_required/bios_present/bios_dir` 与 `setup_required/setup_hint`；（BIOS 缺失不阻断安装，装完不能直接玩通常是没有放对文件/没走到部署）
- 旧 [emulator_manager.py:485](../py_modules/emulator_manager.py) `prepare_bios()` 保留（PS1/PS2 直接复制），`emulator_setup.setup_emulator()` 内部也会调用它，兼容旧测试/调用。

**安装链路 / 平台准入 / UI / 诊断**：计划阶段不要求模拟器已存在（`source=download` 放行；无当前架构资产的平台被隐藏）；安装完成后 `find_rom_file()` → `ensure_emulator(platform)`（首次下载/解包）→ `setup_emulator(platform, command, seven_zip)`（部署 BIOS/固件/keys、写 portable 配置）→ wrapper → Steam 快捷方式 **Exe=启动脚本、LaunchOptions 带 token、Proton=none**；已安装记录写 `platform/emulator/rom_path/launcher_path`。库页 `emulatorPlatforms` 覆盖 10 平台 + pc，弹窗显示模拟器名、BIOS 警告与 setup 提示；诊断包 `emulators` 遍历 [emulator_manager.py:265](../py_modules/emulator_manager.py) `supported_platforms()`，无当前架构资产的平台给出可用性/提示。

**3DS（Azahar）SteamOS 专用链路（v0.14.1）**：

- **根因**：Azahar 官方 AppImage 在 SteamOS 有已知兼容问题（上游 issue #127：AppImage 打不开；#953：Game Mode 偶发崩溃），SteamOS 3.9.5 上优先用 **Flathub 官方 Flatpak `org.azahar_emu.Azahar`**，绕开 AppImage/glibc/依赖问题；
- **Flatpak 安装/解析链**：
  1. [emulator_manager.py:369](../py_modules/emulator_manager.py) `_is_steamos()` 读 `/etc/os-release` 判断 SteamOS；
  2. [emulator_manager.py:381](../py_modules/emulator_manager.py) `flatpak_installed()` 用 `flatpak info <app_id>` 检测（结果缓存 30 s）；
  3. [emulator_manager.py:422](../py_modules/emulator_manager.py) `_ensure_flatpak()`：已安装 → `flatpak run org.azahar_emu.Azahar`；未安装且允许下载 → `flatpak remote-add --user --if-not-exists flathub …` + `flatpak install -y --user flathub org.azahar_emu.Azahar`（失败再试 system 安装，[emulator_manager.py:404](../py_modules/emulator_manager.py) `_run_flatpak()` 带超时/输出）；
  4. 选路优先级：**`FREEDECKCY_AZAHAR_BIN` env > 已装 Flatpak > SteamOS 自动装 Flatpak > AppImage 下载/解包**；非 SteamOS 且未装 Flatpak 时仍走 AppImage；
- **状态/提示**：`emulator_status()` 返回 `flatpak_id/flatpak_available/flatpak_installed`；有 flatpak 时下载提示改为"通过官方 Flatpak 安装 Azahar"；
- **XWayland**：3DS wrapper 固定 `QT_QPA_PLATFORM=xcb`、`SDL_VIDEODRIVER=x11`（Game Mode/Wayland 崩溃规避）；
- **system files**：`~/.local/share/azahar-emu/sysdata`（兼容旧 `azahar`/`citra`）及 Flatpak `~/.var/app/org.azahar_emu.Azahar/data/azahar-emu/sysdata`；
- **已有游戏自动修复**：后台维护在首次 tick 调 [tianyi_service.py:4916](../py_modules/tianyi_service.py) `_maybe_schedule_launcher_repair()`，对已安装的 3DS 记录创建 repair task，[tianyi_service.py:4935](../py_modules/tianyi_service.py) `_repair_emulator_launchers()` 重新 `ensure_emulator("3ds")` 并重写 `launch-freedeckcy.sh`（AppImage 命令 → Flatpak 命令），保存 state/刷新已安装缓存；插件 shutdown 会取消该任务；用户无需重装游戏。

### 5.11 自动云存档（Ludusavi + gamewatch，v0.8.0；v0.15.0 模拟器存档）

**Ludusavi 存档清单**：`defaults/ludusavi/manifest.json.gz`（**53,549 款游戏**，gzip 约 2 MB / 未压缩 14 MB，**MIT**），来自 [mtkennerly/ludusavi-manifest](https://github.com/mtkennerly/ludusavi-manifest) 的 YAML，经 [scripts/fetch_ludusavi_manifest.py](../scripts/fetch_ludusavi_manifest.py) 转成精简 JSON 后随包分发（PyYAML 仅构建时需要）；运行时只读本地文件、不联网。可用 `FREEDECKCY_LUDUSAVI_MANIFEST` 覆盖路径（[save_manifest.py:35](../py_modules/save_manifest.py) `manifest_path()`），进程内缓存见 [save_manifest.py:50](../py_modules/save_manifest.py) `load_manifest()`。

**匹配规则**（[save_manifest.py:98](../py_modules/save_manifest.py) `match_manifest()`）：先按 Steam AppID（清单条目的 `steam.id`），再按标题——标题做 [save_manifest.py:31](../py_modules/save_manifest.py) `normalize_title()`（小写、去掉非字母数字/CJK 的字符）并支持用 `[/|｜丨]` 拆段后逐个匹配。

**占位符 → Proton 前缀**（[save_manifest.py:165](../py_modules/save_manifest.py) `resolve_manifest_paths()`）：

| 占位符 | 解析到（Proton 前缀内） |
|---|---|
| `<base>` | 游戏安装目录 |
| `<home>` / `<root>` | `drive_c/users/steamuser` / `drive_c` |
| `<winAppData>` / `<winLocalAppData>` | `AppData/Roaming` / `AppData/Local` |
| `<winDocuments>` / `<winSavedGames>` | `Documents` / `Saved Games` |
| `<winProgramData>` / `<winPublic>` / `<winDir>` | `drive_c/ProgramData` / `drive_c/Users/Public` / `drive_c/Windows` |

- [save_manifest.py:132](../py_modules/save_manifest.py) `_placeholder_bases()` 生成上表前缀；含 `*`/`?`/`[` 的模板用 glob 展开；结果必须存在（目录还需非空），`realpath` 去重，单游戏最多 200 条路径；
- `when` 条件：[save_manifest.py:149](../py_modules/save_manifest.py) `_when_allows_proton()` 认为"无 when 或含 `os: windows`"才处理；**只写 `os: linux`/mac 的条目跳过**（Proton 下按 Windows 路径找）。

**与原有 Proton 扫描合并**：`_collect_cloud_save_candidates()` 先按快捷方式解析出 `compat_user_dir` 与 appid，再用清单匹配/解析；命中时 `source_paths = manifest 路径 + Proton 扫描路径`（去重），`source_strategy` 取 `ludusavi`（清单命中且 Proton 未命中）/`ludusavi+proton`（两者都有）/`proton_prefix`（仅 Proton 扫描）/`install_fallback`（无前缀时按安装目录白名单兜底）；诊断里 `ludusavi = {matched, path_count}`。

**gamewatch 进程检测**（`py_modules/gamewatch.py`）：后台维护每 8 s 调用 `_poll_game_watch()`（`maintenance_tick` 内，[tianyi_service.py:4968](../py_modules/tianyi_service.py) `_poll_game_watch()`）。[gamewatch.py:74](../py_modules/gamewatch.py) `is_game_running()` 优先扫描 `/proc/*/cmdline`（[gamewatch.py:51](../py_modules/gamewatch.py) `_is_running_proc()`，判断 install_path 是否出现在命令行），没有 `/proc` 时回退 [gamewatch.py:58](../py_modules/gamewatch.py) `_is_running_pgrep()`（`pgrep -f`）；[gamewatch.py:81](../py_modules/gamewatch.py) `GameWatcher.poll()` 维护每个 game_id 的运行状态：首次 poll 只建立基线，之后只在状态切换时产出 `start`/`end` 事件，已移除的游戏清空状态（[gamewatch.py:88](../py_modules/gamewatch.py) `poll()`）。服务层**只消费 `end` 事件**（start 事件不触发上传）。

**只上传刚退出的游戏**（[tianyi_service.py:4982](../py_modules/tianyi_service.py) `_maybe_auto_cloud_upload()`）：`end` 事件 → 检查设置 `cloud_save_auto_upload`（默认 **true**）、登录态、当前无云存档上传/自动上传任务、距上次自动上传 ≥ **30 s** 防抖 → 调 [tianyi_service.py:3071](../py_modules/tianyi_service.py) `start_cloud_save_upload(game_ids=[该 game_id])`；上传任务构建候选后按 `game_ids` 过滤（诊断 `filtered_game_ids`），因此不会顺带打包其它游戏。

**指纹去重**：[tianyi_service.py:5017](../py_modules/tianyi_service.py) `_cloud_save_fingerprint()` 对每个游戏的 `source_paths` 递归取文件（最多 **5000** 个），指纹 = `sha256(相对路径|size|mtime_ns …)`；指纹按 `game_key` 持久化到 `state.json` 的 `cloud_save_fingerprints`。上传前计算并与上次比较，相同则**跳过打包/上传**（结果 `status=skipped`、`reason=unchanged`）；上传成功后写回新指纹。

**设置与 UI**：设置项 `cloud_save_auto_upload`（默认 true）与 `cloud_save_include_emulators`（默认 true）贯穿 `tianyi_store`（默认/加载/set_settings）、`main.set_tianyi_settings`、`tianyi_http.handle_settings_set` 与 QAM 设置页「云存档上传」的两个开关（`src/index.tsx` 的 `ToggleField`）。

**模拟器存档（v0.15.0，`py_modules/emulator_saves.py`）**：

- [emulator_saves.py:23](../py_modules/emulator_saves.py) `STANDARD_SAVE_DIRS`：10 平台标准目录（mGBA `~/.local/share/mgba/saves` 与 Flatpak `~/.var/app/io.mgba.mGBA/...`、PPSSPP `PSP/SAVEDATA`、melonDS `saves`、DuckStation `memcards`、Mesen2 `Saves`、PCSX2 `memcards`、RPCS3 `dev_hdd0/home`、Eden `nand/user/save`、3DS 的 `sdmc`/`nand/user/save` 与 Azahar Flatpak 目录）；
- [emulator_saves.py:76](../py_modules/emulator_saves.py) `PORTABLE_SUBDIRS`：相对安装根/ROM 目录/启动脚本目录/已解包模拟器目录的 portable 路径（如 `saves`、`memcards`、`memstick/PSP/SAVEDATA`、`sdmc`、`nand/user/save`）；
- **单游戏平台**：[emulator_saves.py:90](../py_modules/emulator_saves.py) `PER_GAME_PLATFORMS = {gba, fc, md, nds}`——[emulator_saves.py:274](../py_modules/emulator_saves.py) `collect_emulator_save_paths()` 在候选目录里用 ROM 文件名 stem 匹配（[emulator_saves.py:174](../py_modules/emulator_saves.py) `_per_game_entries()`，`.sav/.srm/.dsv/...` 或同名目录）；**找不到就返回 `game_save_not_found`，不会退化成整目录**，避免把同平台其它游戏一起上传；
- **共享/可拆平台**：PSP/PS1/PS2/3DS/PS3/Switch 默认返回整个记忆卡/标题目录（空目录跳过），结果 [emulator_saves.py:99](../py_modules/emulator_saves.py) `EmulatorSaveResult(per_game=False)`；**v0.16.0 起 PSP/PS3/3DS 先尝试按游戏拆分**（见下），匹配不到才回退共享目录；服务层 `_collect_cloud_save_candidates()` 按 `tuple(source_paths)` 签名去重，重复记录标记 `emulator_saves_shared` 并跳过；
- **接入**：非 PC 平台的候选直接来自 `collect_emulator_save_paths()`，`source_strategy="emulator_saves"`、`diagnostics.emulator_saves` 带 platform/emulator/per_game/searched/reason；找不到路径时 skip_reason 为 `save_dir_missing` / `game_save_not_found`；
- **开关**：设置 `cloud_save_include_emulators` 默认 **true**（store/service/main/HTTP/QAM「包含模拟器存档」），关闭时非 PC 记录记 `emulator_saves_disabled`，不参与上传；
- 平台列表与路径覆盖见 [emulator_saves.py:23](../py_modules/emulator_saves.py)；3DS/Switch 目录可能很大，上传前会按 `_MAX_PATHS`/指纹（最多 5000 文件）截断/去重。

**按游戏拆分（v0.16.0）**：

- **PSP/PS3**：[emulator_saves.py:91](../py_modules/emulator_saves.py) `PARAM_SFO_PLATFORMS`；用 [param_sfo.py:12](../py_modules/param_sfo.py) `read_param_sfo()`（[param_sfo.py:46](../py_modules/param_sfo.py) `find_param_sfo()` 在存档目录找 `PARAM.SFO`）读取 `TITLE`，[emulator_saves.py:92](../py_modules/emulator_saves.py) `_split_param_sfo()` 与游戏标题归一化匹配：PSP 匹配 `SAVEDATA/<id>/PARAM.SFO`，PS3 匹配 `dev_hdd0/home/<user>/savedata/<id>/PARAM.SFO`；匹配则 `per_game=True`，只上传该存档目录；
- **3DS**：[emulator_saves.py:256](../py_modules/emulator_saves.py) `TITLE_ID_PLATFORMS`；[emulator_saves.py:218](../py_modules/emulator_saves.py) `_read_3ds_title_id()` 读 `.3ds/.cci/.cxi` 的 NCSD 头 `0x100` 后 16 字节（Program ID 在 `0x108`），[emulator_saves.py:239](../py_modules/emulator_saves.py) `_split_3ds()` 在 `title/00040000/<low8>` 下找标题目录；匹配则只上传该目录；
- **仍共享**：PS1/PS2 单片记忆卡、Switch 的 `nand/user/save` 目录无法按游戏拆分，保持整目录上传（按签名去重）；
- 拆分失败（无 PARAM.SFO / TITLE 不匹配 / NCSD 读不到）自动回退共享目录，不阻断上传。

**模拟器存档恢复（v0.16.0）**：

- `plan_cloud_save_restore()` 遇到 manifest `source_strategy="emulator_saves"` 不再拒绝，转 [tianyi_service.py:3328](../py_modules/tianyi_service.py) `_plan_emulator_save_restore()`：按已安装记录找平台根、构建 `copy_pairs`/`plan_items`，统计冲突（`conflict_count`/`conflict_samples`）并设置 `requires_confirmation`；
- **恢复根白名单**：[emulator_saves.py:326](../py_modules/emulator_saves.py) `restore_roots(record)` 返回平台标准目录 + portable 根；[emulator_saves.py:344](../py_modules/emulator_saves.py) `build_restore_targets(record, entries)` 只允许把文件写到这些根内——同机时若 `source_path` 的父目录仍在某个根内，恢复到**原父目录**；跨设备/路径不存在时落到**第一个根**；**不会把 manifest 里的任意 HOME 路径当目标**；
- **冲突与备份**：目标已存在时计入冲突并要求确认（QAM confirm）；apply 复用现有恢复流程，覆盖前自动生成 `*.freedeckcy-bak-<时间戳>` 备份；
- 边界：3DS 跨设备恢复可能退化到根目录（title 目录结构不一致时）；PS1/PS2/Switch 仍是整卡/整目录覆盖，不能只挑单个游戏。

**边界**：只对 gamewatch 检测到"退出"的游戏自动上传，gamewatch 依赖进程命令行包含 install_path（自定义 wrapper 可能漏检）；指纹只覆盖大小/mtime，不读文件内容；PS1/PS2 单片记忆卡与 Switch 目录仍共享（不能按游戏拆分）。

**边界**：只对 gamewatch 检测到"退出"的游戏自动上传，gamewatch 依赖进程命令行包含 install_path（自定义 wrapper 可能漏检）；没有自动恢复/冲突策略（恢复仍需手动在 QAM 操作、覆盖前备份）；指纹只覆盖大小/mtime，不读文件内容；模拟器共享记忆卡暂不按游戏拆分。

### 5.12 游戏提交（仓库，v0.13.0）

**定位**：给仓库补目录条目（对应原版资源池投稿字段），**不要求云账号登录**，也不上传游戏文件；只收集分享链接与网盘内路径，合并进 `defaults/tianyi_catalog/freedeckcy_catalog.csv` 后走现有"目录 → 安装"链路。**v0.14.0 起支持天翼云盘与百度网盘两种分享链接**（合并时 `server=t` / `server=b`）。主文档见 [submissions/README.md](../submissions/README.md)（字段表/规则/命令），本节只讲实现与数据流。

**两种入口**：

| 入口 | 文件 / 位置 | 适用 |
|---|---|---|
| GitHub Issue 表单 | [.github/ISSUE_TEMPLATE/submit-game.yml](../.github/ISSUE_TEMPLATE/submit-game.yml)（字段 name/english_name/platform/share_url/access_code/share_user_version/executable_name/openpath/categories/filesize_z/notes；平台下拉 11 个） | 单条、不想开 PR |
| JSON PR | `submissions/*.json`（复制 `submissions/examples/example-pc.json` / `example-switch.json` / `example-baidu.json`，按 [schema.json](../submissions/schema.json) 填） | 批量/长期/可校验 |

- 网页库工具栏「提交游戏」按钮（`defaults/tianyi_library_ui/app.js` 的 `submitGame()`）直接打开上述 Issue 模板（`https://github.com/hulong1989/freedeckCY/issues/new?template=submit-game.yml`）；
- 字段与原版资源池投稿的对应：`name/english_name/platform/share_url/access_code/share_user_version/executable_name` 原样保留，额外要求 `openpath`（安装器定位文件必需），`categories/filesize_z/category_parent/list_filesize/notes` 为目录补充。

**校验链路**（[submission.py:173](../py_modules/submission.py) `validate_submission()`；批量为 [submission.py:276](../py_modules/submission.py) `validate_submission_files()`）：

1. [submission.py:66](../py_modules/submission.py) `normalize_platform()`：平台别名归一（windows/win→pc、ns→switch、3d→3ds、psx/playstation→ps1、genesis→md 等），只接受 11 个平台；
2. 必填 `name/platform/share_url/openpath`；[submission.py:72](../py_modules/submission.py) `normalize_categories()` 清洗分类（去平台名、去重、模拟器补「模拟器」）；
3. 分享链接必须是 `https://cloud.189.cn/...` 或 `https://pan.baidu.com/...` / `yun.baidu.com` / `eyun.baidu.com`（[submission.py:120](../py_modules/submission.py) `_parse_share_url()` 解析天翼 `/t/<shareCode>`、`/web/share?code=` 与百度 `/s/<surl>`、`/share/init?surl=`，提取 `pwd` / `access_code`）；[submission.py:156](../py_modules/submission.py) `_with_access_code()` 在合并时补 `pwd=`；百度行 `server=b`；
4. `openpath` 不能含 `..`、不能是绝对路径；`filesize_z` 必须是非负整数；`access_code` 4–8 位字母/数字（缺失且链接无 `pwd` 只是警告）；`executable_name` 仅 PC 需要（模拟器留空时警告）；
5. 重复 shareCode：同时对比**目录已有行**与**本批其它提交**，重复即 ERROR；
6. 无提交文件时 `ok=True`（CI 不红）。

**合并链路**（[submission.py:326](../py_modules/submission.py) `build_catalog_row()` / [submission.py:363](../py_modules/submission.py) `merge_submissions()`）：

- dry-run（默认）只返回待写入行；`--apply` 先确认全部提交无 ERROR，否则整批拒绝；
- 生成行：`title = 中文/英文`（英文已在中文名里则只留中文）、`server="t"`（天翼）或 `"b"`（百度）、`down_url` 补 `pwd`、`shorturl=shareCode`、`pwd`、`platform`、`category_parent` 默认 `5`、`categories` 清洗后为空则 `未分类`、`openpath/filesize_z/list_filesize` 原样；
- game_id：[submission.py:316](../py_modules/submission.py) `_next_game_id()` 取目录现有最大数字 +1，逐条递增；
- 写入：先写临时 CSV 再 `os.replace` 原子替换，成功后把 JSON 移到 `submissions/merged/`，并追加 `submissions/merged/index.json`（file/game_id/title/merged_at）；`submissions/merged/` 运行时创建，不提交合并产物也行。

**CI / 命令 / 与安装的关系**：

- CI `.github/workflows/ci.yml` 的 `Validate game submissions` 步骤执行 `python scripts/validate_submissions.py`（无提交也通过）；
- 本地：`make validate-submissions`、`python scripts/merge_submissions.py --dry-run` / `--apply`（支持 `--json`）；
- 合并后的行与手工目录条目完全同构，库页/安装器按 `platform/openpath/share_url` 解析——即"提交 → 审核 → 合并 CSV → 库页出现 → 安装"。

### 5.13 百度网盘（扫码/Cookie 主链路，v0.17.0；OpenAPI 可选回退）

**定位与优先级**：v0.17.0 起百度网盘以**网页扫码登录（BDUSS/Cookie）**为主链路——用户不需要开发者资质/App Key，QAM 里扫码即可安装百度分享；v0.14.0 的**官方 OpenAPI 保留为可选回退**（自建应用 + OAuth，见本节末尾）。仍然**不接 CDP、不做网页接口逆向**；Cookie 只通过百度 Passport 官方扫码接口获取。

**扫码链路（`py_modules/baidu_qr.py`）**：

1. [baidu_qr.py:80](../py_modules/baidu_qr.py) `request_qr()`：GET `https://passport.baidu.com/v2/api/getqrcode?lp=pc&qrloginfrom=pc`，返回 `sign` + `imgurl`；
2. [baidu_qr.py:123](../py_modules/baidu_qr.py) `fetch_qr_image()` 下载二维码 PNG；服务层 `start_baidu_qr_login()` 转 `data:image/png;base64,...` 给 QAM，**session 只存内存、180 秒过期**（`expires_at`）；
3. [baidu_qr.py:143](../py_modules/baidu_qr.py) `poll_qr(sign)` 对 `https://passport.baidu.com/channel/unicast` 做长轮询：空响应/`errno=1` 视为 waiting，`channel_v` 里 `status=1` 是 scanned，带 `v` 是 confirmed；
4. [baidu_qr.py:222](../py_modules/baidu_qr.py) `complete_login(v)`：GET `https://passport.baidu.com/v3/login/main/qrbdusslogin?bduss=<v>...`，解析 `data.session.bduss/stoken/ptoken`，拼成 `BDUSS=...; STOKEN=...; PTOKEN=...` Cookie 并尽量取用户名；
5. 服务层 [tianyi_service.py:922](../py_modules/tianyi_service.py) `start_baidu_qr_login()` / [tianyi_service.py:957](../py_modules/tianyi_service.py) `poll_baidu_qr_login()`：waiting→scanned→confirmed→success，成功后写入 `state.json` 的 `baidu_login` 并清空内存 session；[tianyi_service.py:994](../py_modules/tianyi_service.py) `cancel_baidu_qr_login()` 取消；[tianyi_service.py:999](../py_modules/tianyi_service.py) `clear_baidu_login()` 退出登录（清 cookie/账号）；
6. 状态持久化：[tianyi_store.py:60](../py_modules/tianyi_store.py) `BaiduLoginState(cookie, user_account, updated_at)`，`logged_in` 检查 Cookie 里是否有 `BDUSS=`；`state.json` 权限 0600，诊断/日志沿用 cookie/token 脱敏，不把 Cookie 打进诊断包。

**provider 优先级与安装链路**：

- [tianyi_service.py:245](../py_modules/tianyi_service.py) `_share_provider()` 识别 `pan.baidu.com`/`yun.baidu.com`/`eyun.baidu.com` → `"baidu"`；安装计划里：
  1. 若 `store.baidu_login.cookie` 含 `BDUSS=` → `provider="baidu"`（Cookie 链路）；
  2. 否则若 `store.baidu_openapi.configured` → `provider="baidu_openapi"`（可选回退）；
  3. 都没有 → 报"请先扫码登录百度网盘（设置 → 百度网盘扫码登录）"；
- Cookie 链路：[baidu_client.py:477](../py_modules/baidu_client.py) `resolve_baidu_share(share_url, cookie)` 解析分享/文件列表，`fetch_baidu_download_url(cookie, ctx, file_id)` 取直链；任务 aria2 `cookie=<百度 Cookie>`、`referer=https://pan.baidu.com/disk/home`、`user_agent=pan.baidu.com`；任务 `provider="baidu"`，重试/补下 `_readd_task_download()` 按 provider 重新取直链（Cookie 过期会失败，需重新扫码）；
- **OpenAPI 回退**（自建应用）：[baidu_openapi_client.py:1540](../py_modules/baidu_openapi_client.py) `resolve_baidu_openapi_share_url()` + [baidu_openapi_client.py:1987](../py_modules/baidu_openapi_client.py) `fetch_baidu_openapi_download_url()`，OAuth 流程 [baidu_openapi_client.py:359](../py_modules/baidu_openapi_client.py) `build_baidu_oauth_authorize_url()` / [baidu_openapi_client.py:387](../py_modules/baidu_openapi_client.py) `exchange_baidu_oauth_code()` / [baidu_openapi_client.py:418](../py_modules/baidu_openapi_client.py) `refresh_baidu_oauth_token()`；任务 `provider="baidu_openapi"`，aria2 空 cookie + 同 Referer/UA；安装后 [tianyi_service.py:7635](../py_modules/tianyi_service.py) `_cleanup_baidu_transfer_files()` 调 [baidu_openapi_client.py:1285](../py_modules/baidu_openapi_client.py) `delete_baidu_openapi_transfer_file()` 清理 `/FreedeckTmp` 转存（Cookie 链路无转存）；
- QAM：新增「百度网盘（扫码登录）」区（二维码/等待/已扫码/取消/退出）；原「百度网盘 OpenAPI」改为「（可选，需开发者资质）」保留；面板状态 `baidu_login`；HTTP `/api/tianyi/baidu/qr/{start,poll,cancel}` 与 `/api/tianyi/baidu/clear`，`main.py` 4 个同名 callable。

**错误诊断（v0.18.0 起，v0.19.1 增强 TLS/urllib 回退）**：

- `request_qr()` 直接请求 `getqrcode`；v0.19.1/v0.19.2 起二维码、图片、轮询、换 Cookie 均依次尝试系统证书、跳过证书校验/urllib 回退（兼容 SteamOS 证书链问题），错误消息带具体异常/HTTP 状态/响应片段；
- HTTP 非 200 会抛带状态码/响应片段的 `BaiduQrError`（如 `获取百度二维码 HTTP 403: ...`）；轮询时 HTTP ≥400 或连接重置/DNS/SSL 等非超时错误返回 `{"status":"error"}`，服务层转 `stage=failed` 并把真实异常写进 QAM 消息，不再一直显示 waiting；超时仍视为 waiting；
- `start_baidu_qr_login()` 会对任何取码异常记日志并返回"获取百度二维码失败：<原因>"；`poll_baidu_qr_login()` 的 `stage` 为 waiting/scanned/success/expired/failed，`failed` 带具体原因；`complete_login()` 非 200/无 BDUSS 时抛 `BaiduQrError`。

**点击反馈与超时（v0.23.0）**：

- QAM 点击「扫码登录百度网盘」立即 toast「正在获取百度二维码...」；
- 前端 `withTimeout(startBaiduQrLogin(), 20000)`、轮询 `withTimeout(pollBaiduQrLogin(), 15000)`；超时提示"获取百度二维码超时（网络/TLS 可能受阻，请稍后重试或运行诊断）"；
- 后端 `start_baidu_qr_login()` 用 `asyncio.wait_for(request_qr(), 12)` 取码、`wait_for(fetch_qr_image(...), 10)` 下载图片；超时/异常分别记 `Baidu QR request timed out`/`Baidu QR request failed`，成功记 `Baidu QR start requested`/`Baidu QR ready sign_len=...`（只记长度，不记 sign/cookie）；
- 超时/失败会以 toast 显示真实原因，不再"点了没反应"。

**安全与边界**：

- Cookie 等价账号凭据：只存 `state.json`（0600），不写日志/诊断、不传给第三方；退出登录清空；
- 扫码 session 仅内存 180 秒，插件重启即失效；二维码过期需重新获取；**扫码确认/换 Cookie 目前未真机验证**（已实测 `getqrcode` 返回 PNG、`unicast` 未扫码返回 waiting）；
- Cookie 会过期/被风控，失效后需重新扫码；部分分享需要账号权限（提取码/转存），Cookie 链路直接按用户账号权限解析；
- OpenAPI 回退需要自建应用/授权，没有公共 App Key；两条链路都**不接 CDP/网页逆向**；百度接口变更可能影响扫码/直链。

### 5.14 扫描已安装游戏（v0.18.0；v0.21.0 入口迁移 + 自动补 Steam 快捷方式）

**问题**：旧版本/手动安装/重装插件后 `state.json` 丢失时，目录里已有游戏但「已安装」页签为空。**v0.21.0 起入口在 QAM 设置 → 安装 → 「扫描已安装游戏」**（原生库已安装页不再有扫描按钮）；[tianyi_service.py:6838](../py_modules/tianyi_service.py) `scan_installed_games()` 把安装目录里的游戏补回已安装列表，并自动补齐 Steam 快捷方式。

**扫描逻辑**：

- 范围：`settings.install_dir` 下**一层子目录**（`os.listdir`，最多 500 项）；跳过隐藏目录与 `compatdata/steamapps/downloads/lost+found/.freedeckcy/.cache` 等；
- 匹配：把子目录名归一化（[tianyi_service.py:6780](../py_modules/tianyi_service.py) `_normalize_scan_title()`：小写、去分隔符/特殊字符）后与目录条目标题（按 `[/|｜]` 拆段）做**前缀/等值**匹配，取最长匹配；目录条目按 `game_id` 去重；
- 已存在：安装 path 已记录 → `already_recorded`；game_id 已记录 → `game_id_recorded`（计入 skipped，不重复添加）；
- 回填：匹配到 Steam 快捷方式（按 app_name 归一化/同 exe realpath）则写 `steam_app_id`；模拟器平台用 `find_rom_file(install_path, entry.openpath, platform)` 找 ROM；新记录写 `TianyiInstalledGame` 并保存；
- **自动补 Steam 快捷方式（v0.21.0）**：
  - `steam_shortcuts.list_all_shortcuts_sync()` 读 `shortcuts.vdf` 全部条目，按 AppName 归一化 + `Exe` realpath 建索引；同名或同 exe 已有 appid 时只回填、不重复添加；
  - 没有快捷方式时：PC 先 [tianyi_service.py:6790](../py_modules/tianyi_service.py) `_find_scanned_executable()` 找 exe（优先 `entry.openpath` 指向的 .exe，否则递归找 .exe，排除 `unins/setup/redist/vcredist/crashreport/dxsetup`，按标题/目录名/大小排序），找到后 `add_or_update_tianyi_shortcut()`（带 `freedeckcy:tianyi:<token>`、Proton 设置、封面）；找不到记 `shortcut_error="exe_not_found"`；
  - 模拟器：`ensure_emulator(platform, allow_download=False)`（**不自动下载**）+ `create_launch_wrapper()` 生成 `launch-freedeckcy.sh`，再注册原生快捷方式（Proton=none）；ROM 找不到 → `rom_not_found`；模拟器未就绪 → `emulator_not_ready: ...`；
  - **第二遍**：对已存在但 `steam_app_id=0` 的 PC 记录，按同样规则补建快捷方式，结果写入 `steam_recovered`；返回汇总 `steam_added`（新记录里补建成功数）、`steam_recovered_count`、`shortcut_error`；
  - **Steam 需要重启/切换用户/重新打开库页**才能看到新快捷方式（插件只写 `shortcuts.vdf`，不重启 Steam）。
- 返回：`scanned/added_count/added_games/skipped_count/skipped/unresolved_count/unresolved_dirs/installed_total/message`；未匹配目录进 `catalog_no_match`（或 `catalog_missing_game_id`）。

**API / UI**：主入口是 **QAM 设置 → 安装 → 「扫描已安装游戏」**（`src/index.tsx` 的 `onScanInstalledSettings`，toast 带"自动加入 Steam：N"）；HTTP `POST /api/tianyi/installed/scan`（`tianyi_http.handle_installed_scan`）→ `main.scan_tianyi_installed_games` 仍保留；网页库「已安装」工具栏「扫描已安装」（`app.js` 的 `scanInstalled()`）作为备用入口；原生库已安装页 v0.21.0 起不再有扫描按钮。

**边界**：只扫**一层**（嵌套目录/多级子目录不识别）；目录名必须能与目录标题匹配（改名/英文名差异可能 `catalog_no_match`）；只补记录，**不会创建 Steam 快捷方式**（也不改 `shortcuts.vdf`）；模拟器 ROM 找不到时 `rom_path` 为空但记录仍会建立；空目录/0 字节目录跳过。

### 5.15 存储位置选择（v0.19.0）

**目的**：Steam Deck 的 SD 卡 / DroidDeck 的外置存储挂载后，让用户在 QAM「路径」页一键把下载/安装目录切过去，不用手动输入路径。

**检测（`py_modules/storage_options.py`）**：

- [storage_options.py:66](../py_modules/storage_options.py) `detect_storage_options(mounts_text, home, disk_usage)` 解析 `/proc/mounts`（[storage_options.py:39](../py_modules/storage_options.py) `_unescape_mount()` 处理 `\040` 等转义）；
- 候选挂载前缀：[storage_options.py:9](../py_modules/storage_options.py) `_MOUNT_PREFIXES = /run/media/（SteamOS SD）/ /media/ /mnt/ /storage/（DroidDeck）/ /sdcard`；跳过 [storage_options.py:16](../py_modules/storage_options.py) `_SKIP_FSTYPES`（proc/sysfs/tmpfs/overlay/squashfs 等系统 fstype）与 [storage_options.py:36](../py_modules/storage_options.py) `_SKIP_MOUNTS`（`/`、`/run`、`/mnt`、`/media`、`/storage`、`/sdcard` 挂载根本身）；
- 必须存在、**可写**、`disk_usage` 有总容量才收录；同一 realpath 去重；每个外置选项给出：
  - `label`（`SD 卡 / 外置：<目录名>`）、`mount`、`free_bytes/total_bytes`、`free_text/total_text`；
  - `download_dir=<mount>/freedeckCY/downloads`、`install_dir=<mount>/freedeckCY/installed`；
- 内置选项：`~/Downloads/freedeckCY` / `~/Games/freedeckCY`（home 容量）；返回 `{internal, external, options}`；
- 服务层 [tianyi_service.py:6783](../py_modules/tianyi_service.py) `get_storage_options()` 追加当前 `settings.download_dir/install_dir`。

**API / UI**：`GET /api/tianyi/storage/options`（`tianyi_http.handle_storage_options`、`main.get_tianyi_storage_options`）；QAM「路径」页在下载/安装目录下按外置挂载渲染「下载到 <label>（剩余 X）」「安装到 <label>（剩余 X）」按钮，点击 `savePatch` 切换目录并刷新；没有外置挂载时显示"未检测到可写 SD 卡/外置存储"；原「选择下载目录/安装目录」保留。

**边界**：只看已挂载且**可写**的挂载（未挂载/只读/权限不足不会出现）；`/mnt`、`/media`、`/storage` 的**挂载根本身**会被跳过（子挂载如 `/mnt/sdcard` 可显示）；容量是检测时的快照；不会自动 `mkdir`/格式化/挂载；**不做 Steam 库同盘检测**（切目录后 Steam 库是否同盘需用户自行判断）；建议子目录固定为 `freedeckCY/{downloads,installed}`（暂不支持自定义名字）。

### 5.16 Decky 原生游戏库（v0.20.0）

**背景**：之前 QAM「游戏库」按钮打开的是本地网页库（`defaults/tianyi_library_ui/`，依赖本地 HTTP 服务/浏览器）。v0.20.0 起改为 Decky 原生 React 页面，网页库保留为备用（桌面浏览器/调试/回退）。

**路由与入口（v0.23.0：modal 优先、route 兜底）**：

- [src/index.tsx:32](../src/index.tsx) `LIBRARY_ROUTE = "/freedeckcy/library"`；[src/index.tsx:3703](../src/index.tsx) `LibraryPage()` 是页面组件；[src/index.tsx:4132](../src/index.tsx) `routerHook.addRoute(LIBRARY_ROUTE, LibraryPage)` 在插件挂载时注册，`onDismount()` 里 `removeRoute`；
- QAM 主页「游戏库」`onOpenLibrary()` **优先 `showModal(<LibraryPage />)` 原生弹层**，失败才 `Navigation.Navigate(LIBRARY_ROUTE)`（全屏路由保留）；不再调用后端打开网页；网页库入口仍保留作备用；
- **版本标识**：主页显示 `QAM 原生 UI v${PLUGIN_UI_BUILD}`，库页标题下显示 `原生 UI · v${PLUGIN_UI_BUILD}`，用于确认前端是否已更新；**前端未重载/旧 dist 仍会打开网页或看不到该标识**。

**返回 / 关闭链路（v0.24.0）**：

- `LibraryPage({ onClose? })`：**modal 模式**由 `onOpenLibrary` 传 `onClose={() => modal.Close()}`；**route 模式**不传 `onClose`，`handleClose()` 走 `Navigation.NavigateBack()`（失败回退 `Router.CloseSideMenus`）；
- 顶部 **sticky 固定栏**（`position: sticky; top: 0`）：「返回」「Steam 库」「刷新」，页面滚动时仍可点；页面标题栏也保留「返回」按钮；
- `handleSteamLibrary()`：先关闭 modal（`onClose?.()`），再 `Router.NavigateToLibraryTab()` 直接回 Steam 库页；该 API 不可用时回退 `Navigation.NavigateBack()`；
- **边界**：Steam 覆盖层里手柄 B/键盘 Esc 不一定能关掉 QAM modal（不同 Steam UI 版本行为不同），所以提供**显式返回/Steam 库按钮**兜底；如果 modal 打开失败会走全屏 route（无 `onClose`，返回用 `NavigateBack`）；若当前不在路由页/导航栈为空，返回按钮可能只关侧栏或无效。

**页面能力**：

- Tab：「游戏库 / 已安装 / 刷新」；游戏库页：搜索 `TextField`（Enter 触发）+「搜索/重置」、「平台/分类/排序」三个 `DropdownItem`、**20 条/页**分页（上一页/下一页）；
- 游戏行：标题、平台（大写）、大小、分类 + 「安装」按钮；点击走 `prepare_tianyi_install` 生成计划，`ConfirmModal` 显示下载/安装大小、目标目录、模拟器名与 `emulator_info.setup_hint`（BIOS/setup 提示），确认后 `start_tianyi_install` 入队；
- 已安装页：`list_tianyi_installed_games` 列表，显示安装路径/大小/时长；「启动」`launch_tianyi_installed_game`、「目录」`open_tianyi_installed_folder`、「卸载」`ConfirmModal`（`delete_files=true`）→ `uninstall_tianyi_installed_game`。**v0.21.0 起「扫描已安装」不在库页**，统一到 QAM 设置 → 安装（见 5.14）。

**callable 链路**：`main.py` 暴露 `list_tianyi_catalog`（query/page/page_size/platform/category/sort）、`prepare_tianyi_install`、`start_tianyi_install`、`list_tianyi_installed_games`、`launch_tianyi_installed_game`、`open_tianyi_installed_folder`、`scan_tianyi_installed_games`（扫描实现仍是 `settings.install_dir` 一层 + 目录名/标题匹配，见 5.14）；前端通过 `callable("...")` 直连 Python，**不经过本地 HTTP，也没有 CORS/浏览器依赖**。

**边界**：原生库只做浏览/安装/已安装动作，**任务进度仍在 QAM 主页任务区**（不在库页）；列表是行式（无封面卡片视图）；分页固定 20 条；扫描仍只认 `settings.install_dir` 一层；卸载固定 `delete_files=true`（不弹 compatdata 回收选项）；网页库作为备用保留，功能以原生库为准。

### 5.17 诊断自检（v0.22.0）

**QAM 入口**：设置页新增「诊断」Tab（`src/index.tsx`，`onRunDiagnostics`/`onExportDiagnostics`）：

- 「运行自检」调 callable `run_tianyi_diagnostics`（`main.py`）→ [tianyi_service.py:7234](../py_modules/tianyi_service.py) `run_diagnostics(include_network=True)`；返回 `{generated_at, version, arch, summary{ok,warn,fail,skip}, checks[{id,label,status,detail,fix}]}`；QAM 按状态着色（ok/warn/fail/skip）并展示 `建议：fix`；
- 「导出诊断包」调 `export_tianyi_diagnostics_file` → [tianyi_service.py:7446](../py_modules/tianyi_service.py) `export_diagnostics_to_downloads()`：写 `settings.download_dir`（空则 `plugin.downloads_dir`、再退 `~/Downloads`）的 `freedeckcy-diagnostics-YYYYmmdd-HHMMSS.zip`（**0600**），返回 `path/filename/size/message`，QAM toast 显示路径；
- HTTP 仍保留 `POST /api/tianyi/diagnostics/run`（`tianyi_http.handle_diagnostics_run`），供网页/脚本使用。

**检查项**（每项都带 `status`/`detail`/`fix`）：

| 检查 | 内容 |
|---|---|
| `plugin` | 插件版本/目录（缺失 warn） |
| `state_dir` | `state.json` 目录可写、state 权限 |
| `download_dir` / `install_dir` | 存在/可写/剩余空间；**< 2 GB warn** |
| `runtime_aria2` / `runtime_7z` / `runtime_node` | 包内 `defaults/runtime/<component>/<arch>/` 存在可执行并跑 `--version`（7zz 用 `i`，5s 超时） |
| `catalog` | 目录条数/平台数/封面索引数 |
| `steam` | Steam root + `list_all_shortcuts_sync()` 快捷方式数量（未登录/读不到 warn） |
| `storage` | `detect_storage_options()` 的 SD/外置挂载数量与标签 |
| `network_tianyi` | GET `https://cloud.189.cn/`（HTTP <500 ok，否则 warn） |
| `baidu_qr` | `request_qr()`（12s 超时）**只输出 sign 长度**，不输出 sign/cookie；失败 fix 提示 TLS/证书/连通性 |
| `tasks` | 任务数/失败数/已安装数（有失败任务 warn） |
| `log` | `/tmp/freedeckcy.log` 末尾 300 行里 ERROR/Exception/失败 行数（有则 warn） |

**诊断包内容**：`diagnostics.json`（版本/路径/运行时/任务/已安装统计，cookie/token 脱敏、HOME→~）、`self-check.json`（上述自检结果）、`log-tail.txt`（300 行，同样脱敏）、`README.txt`（说明）；打包时再跑一次自检（`export_diagnostics()`）。**网络项可跳过**：`run_diagnostics(include_network=False)` 时不发网络请求，百度 QR 记 `skip`；自检**不会自动修复**，只给建议；导出包只写本地下载目录，不上传。

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
| 运行时二进制 | `defaults/runtime/{aria2,7z}/<arch>/`、`defaults/runtime/node/<arch>/bin/node`（模拟器不在包内） |
| 模拟器解包产物 | `~/.local/share/freedeckCY/emulators/<platform>/<arch>/squashfs-root/`（AppRun，不依赖 FUSE；FC/MD 共用 `mesen/`；GBA 兼容旧 `emulators/<arch>/`） |
| 按需下载的模拟器资产 | `~/.local/share/freedeckCY/emulators/<platform>/<arch>/<官方资产名>`（PSP/NDS 首次安装时下载） |
| GBA 启动脚本 | `<install_dir>/launch-freedeckcy.sh`（`exec <mGBA> -f <rom>`） |
| 日志 | `/tmp/freedeckcy.log` |

**关键函数索引（安装链路）**

| 环节 | 代码位置 |
|---|---|
| HTTP 入口 prepare / start | [tianyi_http.py:608](../py_modules/tianyi_http.py) `handle_prepare_install` / [tianyi_http.py:629](../py_modules/tianyi_http.py) `handle_start_install` |
| 安装计划 + 空间探针 | [tianyi_service.py:1612](../py_modules/tianyi_service.py) `_build_install_plan()` |
| 创建下载任务 | [tianyi_service.py:1344](../py_modules/tianyi_service.py) `_create_tasks_from_plan()` |
| 任务状态同步 | [tianyi_service.py:5727](../py_modules/tianyi_service.py) `refresh_tasks()` |
| 安装调度 / 目录级互斥 | [tianyi_service.py:5990](../py_modules/tianyi_service.py) `_schedule_post_process_task()` / [tianyi_service.py:6340](../py_modules/tianyi_service.py) `_post_process_completed_task()` / [tianyi_service.py:6451](../py_modules/tianyi_service.py) `_install_lock_for()` |
| 解压 / 合并 staging | [tianyi_service.py:7527](../py_modules/tianyi_service.py) `_extract_archive_to_dir()` / [tianyi_service.py:7506](../py_modules/tianyi_service.py) `_merge_extracted_content()` |
| 写 Steam 快捷方式 / Proton / 封面 | [steam_shortcuts.py:432](../py_modules/steam_shortcuts.py) `_upsert_shortcut_sync()`、[steam_shortcuts.py:563](../py_modules/steam_shortcuts.py) `_set_proton_mapping_sync()`、[steam_shortcuts.py:813](../py_modules/steam_shortcuts.py) `_apply_grid_assets()` |
| 非 Steam appid | [steam_shortcuts.py:425](../py_modules/steam_shortcuts.py) `_generate_non_steam_app_id()` |
| aria2 下单 | [aria2_manager.py:452](../py_modules/aria2_manager.py) `add_uri()` |
| 分享解析 / 直链 | [tianyi_client.py:1081](../py_modules/tianyi_client.py) `resolve_share()`、[tianyi_client.py:1640](../py_modules/tianyi_client.py) `fetch_access_token()`、[tianyi_client.py:1683](../py_modules/tianyi_client.py) `fetch_download_url()` |
| 后台维护 | [tianyi_service.py:8270](../py_modules/tianyi_service.py) `maintenance_tick()` |
| 多分卷归档识别 | [archive_bundle.py:88](../py_modules/archive_bundle.py) `detect_archive_sets()` / [archive_bundle.py:228](../py_modules/archive_bundle.py) `build_bundle_index()` |
| 解压前 settle / 预检 | [tianyi_service.py:8316](../py_modules/tianyi_service.py) `_wait_payload_settled()` / [tianyi_service.py:650](../py_modules/tianyi_service.py) `_precheck_archive_payload()` |
| 分卷只解主卷 / bundled | [tianyi_service.py:7653](../py_modules/tianyi_service.py) `_post_process_completed_task()` / [tianyi_service.py:7697](../py_modules/tianyi_service.py) `_install_payload()` |
| 坏文件隔离 / 自愈 | [tianyi_service.py:7527](../py_modules/tianyi_service.py) `_quarantine_download_file()` |
| aria2 运行时复用（meta+flock） | [aria2_manager.py:158](../py_modules/aria2_manager.py) `_read_runtime_meta()` / [aria2_manager.py:248](../py_modules/aria2_manager.py) `_attach_existing()` / [aria2_manager.py:205](../py_modules/aria2_manager.py) `_try_acquire_owner_lock()` |
| 直链原地换链 | [aria2_manager.py:510](../py_modules/aria2_manager.py) `replace_uri()` |
| 重启恢复（gid 丢失） | [tianyi_service.py:7740](../py_modules/tianyi_service.py) `_try_recover_task()` / [tianyi_service.py:6226](../py_modules/tianyi_service.py) `_file_matches_expected_size()` / [tianyi_service.py:6190](../py_modules/tianyi_service.py) `_readd_task_download()` |
| 分卷分组安装 | [tianyi_service.py:6115](../py_modules/tianyi_service.py) `_install_group_members()` / [tianyi_service.py:6246](../py_modules/tianyi_service.py) `_maybe_schedule_group_post_process()` / [tianyi_service.py:6145](../py_modules/tianyi_service.py) `_install_payload()` / [tianyi_service.py:6161](../py_modules/tianyi_service.py) `_finalize_group_install()` |
| 下载完整性校验 | [tianyi_service.py:7740](../py_modules/tianyi_service.py) `_verify_downloaded_file()` |
| 归档 `7z t` 校验 | [seven_zip_manager.py:66](../py_modules/seven_zip_manager.py) `test_archive()` |
| 校验失败自动重下 | [tianyi_service.py:7835](../py_modules/tianyi_service.py) `_schedule_archive_repair()` / [tianyi_service.py:6126](../py_modules/tianyi_service.py) `ArchiveRepairScheduled` |
| 失败任务重试 | [tianyi_service.py:7718](../py_modules/tianyi_service.py) `retry_task()` |
| 卸载预览 / compatdata 回收 | [tianyi_service.py:253](../py_modules/tianyi_service.py) `preview_uninstall()` / [tianyi_service.py:6534](../py_modules/tianyi_service.py) `_can_remove_compatdata_dir()` / [steam_shortcuts.py:165](../py_modules/steam_shortcuts.py) `find_compatdata_dirs()` |
| aria2 全量列表（恢复用） | [aria2_manager.py:534](../py_modules/aria2_manager.py) `list_downloads()` |

**几个容易误解的点**

- **"不限速"的真相**：全仓库没有任何 `--max-*-limit`，所以是"不设上限"而不是加速。实际速度取决于天翼直链和单文件分片数（默认 `split=16`，aria2 全局并发 3）。
- **不转存**：分享资源不会保存到用户网盘，直接拿直链给 aria2 下载（这点和很多"转存类"工具不同）。
- **`freedeckcy:tianyi:<game_id>`** 只是写在 LaunchOptions 里的标记，本插件没有读取它的运行时代码（时长统计走 Steam 全局事件，见 7.3）。
- **exe 定位是启发式**：CSV 的 `openpath` 精确时靠它；不精确时靠"叶子文件名搜索"和"目录里第一个可执行文件"，这是很多"装完点了没反应"的根源。
- **写 `shortcuts.vdf` 必须重启 Steam** 才能看到。
- **error 任务不会自动重试安装**：先移除出错的任务；分卷场景下移除失败的那一包后，剩余已完成的分卷会继续安装（见 6.2）。

### 6.1 重启恢复：gid 变化与直链过期

插件重载现在会附着到仍存活的 aria2（见 6.4），**gid 通常不变**；但**设备重启**后 aria2 会话重建、gid 会变，直链也可能过期。`state.json` 里存的旧 gid 查不到时，`refresh_tasks()` 对查询失败的任务按以下顺序恢复（[tianyi_service.py:5444](../py_modules/tianyi_service.py) `_try_recover_task()` / [tianyi_service.py:5434](../py_modules/tianyi_service.py) `_file_matches_expected_size()` / [tianyi_service.py:6190](../py_modules/tianyi_service.py) `_readd_task_download()`）：

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

同一安装计划（`install/prepare` 返回的多个文件）在创建任务时共享一个 `group_id`，`group_total` 记录包数。**"代表任务" = 组内 `created_at` 最早的那个**（[tianyi_service.py:6115](../py_modules/tianyi_service.py) `_install_group_members()` 按 `(created_at, task_id)` 排序），Steam 注册与已安装记录都以它为准。

- **下载阶段**：`_maybe_schedule_group_post_process()` 只在整组任务全部 `complete` 后才调度安装。
  - 组内某包 `error`：不安装；已完成的包显示"同一安装计划中有分卷下载失败，移除失败任务后可继续安装"；
  - 用户移除失败任务后（`removed` 状态不参与分组），剩余的 complete 分卷会被重新调度安装。
- **安装阶段**：逐包解压到同一目标目录（目录级互斥串行），全部成功才 [tianyi_service.py:6246](../py_modules/tianyi_service.py) `_finalize_group_install()`：
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
- **Proton 工具解析与设置（v0.4.0）**：设置项 `proton_tool`（默认 `auto`）落在 [tianyi_store.py:94](../py_modules/tianyi_store.py) `TianyiSettings`；RPC/HTTP 透传为 [main.py:282](../main.py) `set_tianyi_settings()`、[tianyi_http.py:473](../py_modules/tianyi_http.py) `handle_settings_get()` / [tianyi_http.py:482](../py_modules/tianyi_http.py) `handle_settings_set()`，服务层 [tianyi_service.py:6145](../py_modules/tianyi_service.py) `update_settings()`；`GET /api/tianyi/settings` 额外返回 `proton_tool_resolved` / `droiddeck_detected`（[tianyi_service.py:7835](../py_modules/tianyi_service.py) `get_settings()`）。写快捷方式时 [steam_shortcuts.py:1068](../py_modules/steam_shortcuts.py) `add_or_update_tianyi_shortcut(proton_tool=...)`：`auto` → `detect_proton_tool()`，`none`/`skip`/`disabled` → 跳过映射，其它值直接当工具名；最终由 `_set_proton_mapping_sync()` 写入 `config.vdf` 的 `CompatToolMapping`。
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
| 上传入口 | [tianyi_service.py:5607](../py_modules/tianyi_service.py) `start_cloud_save_upload()` |
| 上传后台任务 | [tianyi_service.py:2804](../py_modules/tianyi_service.py) `_run_cloud_save_upload_task()` |
| 候选目录扫描 | [tianyi_service.py:3071](../py_modules/tianyi_service.py) `_collect_cloud_save_candidates()` |
| 打包 + manifest | [tianyi_service.py:5157](../py_modules/tianyi_service.py) `_archive_single_game_saves()` |
| 云端上传 / 列版本 / 下载 | [tianyi_client.py:2079](../py_modules/tianyi_client.py) `upload_archive_to_cloud()`、[tianyi_client.py:2116](../py_modules/tianyi_client.py) `list_cloud_archives()`、[tianyi_client.py:2167](../py_modules/tianyi_client.py) `download_cloud_archive()` |
| 恢复四步 | [tianyi_service.py:4426](../py_modules/tianyi_service.py) `list_cloud_save_restore_options()`、[tianyi_service.py:5048](../py_modules/tianyi_service.py) `list_cloud_save_restore_entries()`、[tianyi_service.py:3127](../py_modules/tianyi_service.py) `plan_cloud_save_restore()`、[tianyi_service.py:3241](../py_modules/tianyi_service.py) `apply_cloud_save_restore()` |

### 7.3 游玩时长（独立小链路，v0.25.0 加 managed 门禁）

- `SteamClient.Apps.RegisterForGameActionStart/End` 全局监听 → `record_tianyi_game_action`（[src/index.tsx:1000](../src/index.tsx) `installGlobalGameActionReporter()`）→ `TianyiService.record_game_action()`：重复 start 且间隔超过 5 秒视为上一局结束，单局封顶 12 小时，重启后能恢复会话。
- **库页插入**：`routerHook.addPatch("/library/app/:appid")` patch Steam 库详情页的 `renderFunc` 和组件 `type`，把「我的游玩 / 主线 / 总时长（HowLongToBeat）」插进去（[src/index.tsx:1555](../src/index.tsx) `installLibraryPlaytimePatch()`、`LibraryTimeBlock`）。这是全项目最"黑魔法"的一段，依赖 Steam UI 内部结构。

**managed 门禁（v0.25.0）**：

- 前端 `LibraryTimeBlock` 只在 `data.managed === true` 时渲染；未匹配/未加载/请求失败直接 `return null`，**不再对 Steam 原有游戏插入任何时长块，也不先显示"加载中"**；
- 后端 [tianyi_service.py:3434](../py_modules/tianyi_service.py) `get_library_game_time_stats()`：**先按 AppID** [tianyi_service.py:3677](../py_modules/tianyi_service.py) `_resolve_installed_record_by_app_id()` 精确匹配已安装记录，未命中再按标题归一化匹配（`_normalize_cover_text`，双向包含）；**避免 Steam 原有游戏与插件游戏同名时误判**；
- 未匹配 → 直接返回 `{managed:false, reason:"not_managed", ...全 0}`，**不调用 `resolve_hltb_stats`、不返回 HLTB 数据**；
- 只有匹配到 `store.installed_games` 的记录才返回 `managed:true` + 时长/HLTB，前端才插入块。

**边界**：只影响「插件安装/补录的游戏」；Steam 自己买/装的原版游戏详情页**不会出现**插件的时长块（除非被扫描补录为插件记录）；标题匹配可能把同名 Steam 游戏误判为插件游戏（AppID 优先已降低概率，仍非绝对）；HLTB 查询失败只影响块内数据，不影响库页本身。

## 8. 登录：四种方式，UI 只走二维码

| 方式 | 实现 | 现状 |
|---|---|---|
| **二维码**（UI 唯一入口） | Python 侧 aiohttp 直接调 `open.e.189.cn` 的二维码接口，抓取二维码 PNG 代理给页面；1.6 s 轮询状态；成功后从 cookie jar 拼 cookie 串存 `state.json` | 在用，最稳 |
| **CDP 抓取** | 连 Steam 内置浏览器 / Chromium 的调试端口（8080、9222），用 DevTools 协议读 cookie | 旧方案，API 还在（`/api/tianyi/login/capture/*`），前端已不调用 |
| **Cookie DB 直读** | 读 `~/.local/share/Steam/config/htmlcache/Cookies` 等 SQLite，过滤 `189.cn` 域 | 旧方案；`v10/v11` 加密的 cookie 直接跳过 |
| 手动粘贴 cookie | `POST /api/tianyi/login/manual` | 兜底 API 保留 |

代码位置：二维码 [tianyi_service.py:1699](../py_modules/tianyi_service.py) `start_qr_login()` / [tianyi_service.py:1785](../py_modules/tianyi_service.py) `poll_qr_login()`；CDP [tianyi_service.py:9083](../py_modules/tianyi_service.py) `_collect_tianyi_cookie_from_cdp()`；Cookie DB [tianyi_service.py:9282](../py_modules/tianyi_service.py) `_collect_tianyi_cookie_from_cookie_db()`；手动 cookie [tianyi_http.py:151](../py_modules/tianyi_http.py) `handle_login_manual()`。

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

`~/.local/share/freedeckCY/tianyi/state.json`（**每次全量重写**，原子替换临时文件；数据类与读写见 [tianyi_store.py:51](../py_modules/tianyi_store.py) 起、[tianyi_store.py:250](../py_modules/tianyi_store.py) `load()`、[tianyi_store.py:351](../py_modules/tianyi_store.py) `save()`）：

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

21. `tianyi_service.py` 约 9500 行、单类 100+ 方法；`src/index.tsx` 约 4200 行单文件。已补 `tests/`（552 个用例）与 GitHub Actions CI，但**仍无 Python 类型检查**（mypy/ruff 未接入，见 ROADMAP）。
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
33. ~~非 PC 资源只可浏览、无法安装~~（模拟器未集成）：**已修复（v0.6.0~v0.11.0）**——**10 个平台已接入**（GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch）；3DS/PS2/PS3 官方包仅 x86_64，在 aarch64 上由目录白名单自动隐藏（见 5.10 架构矩阵），不属于"装不了"。（已知限制）
34. ~~目录分类混入平台名（GBA/Switch…）、分类筛选里出现平台名、数据无自动体检~~：**v0.3.1 已修复**——`normalize_categories()` 加载时清洗 + 606 行数据已改写（「模拟器」606 条），`validate_catalog.py --strict` 进 CI（见 5.6）。
35. **DroidDeck 适配未真机验证**：v0.4.0 按 DroidDeck 源码/ARM64 运行时结构适配（未在真机完整验证）；FEX/ARM Proton、Android 存储映射可能影响结果；**GBA/PSP/NDS 已可安装/启动**，其它模拟器平台仍只可浏览（见 [DROIDDECK.md](DROIDDECK.md) / ROADMAP 9.8）。（已知限制）
36. **模拟器闭环的边界（v0.12.0）**：插件包**不集成任何模拟器**，**所有平台（含 GBA）首次安装都需要联网**从 GitHub release 下载（失败写进安装消息，可重试；离线可手动预置 `~/.local/share/freedeckCY/emulators/<platform>/<arch>/` 或用 `FREEDECKCY_*_BIN`）；3DS（Azahar）在 SteamOS 3.9.5 上优先官方 Flatpak（AppImage 有已知兼容问题，见 5.10）；PS1/PS2 **必须用户自备 BIOS**（分别放 `bios/ps1`、`bios/ps2`，缺失不阻断安装但会警告/可能导致黑屏；PS2 会复制到 PCSX2 的两个默认目录）；3DS 需要 system files、PS3 需要固件、Switch 需要 prod.keys+固件（v0.12.0 起安装后会自动部署到模拟器目录并写 portable 配置；缺失仍不阻断安装，但装完不能直接玩）；FC/MD 共用 Mesen2 缓存（`emulators/mesen/<arch>/`），zip 内是可执行文件而非 AppImage；只识别注册表内 ROM 扩展名，**不含 BIOS/存档管理**（BIOS/固件只做"从 bios/<platform>/ 部署到模拟器目录"，不下载、不校验版本）；下载/解包会多占一份磁盘空间；ARM64/DroidDeck 上这些平台尚未真机验证。（已知限制）
37. **自动云存档的边界（v0.15.0）**：只对 gamewatch 检测到"退出"的游戏自动上传，且 gamewatch 依赖进程命令行包含 install_path（自定义 wrapper 可能漏检）；**没有自动恢复/冲突策略**；上传前指纹只看相对路径+size+mtime（最多 5000 文件），不读内容；`cloud_save_auto_upload` 默认开启（可在 QAM 关闭）。（已知限制）
38. **模拟器架构矩阵差异（v0.11.0）**：3DS/PS2/PS3 官方包仅 x86_64，aarch64（含 DroidDeck）上目录查询按 `available_platforms()` 白名单隐藏这些平台的条目/筛选条，`emulator_status` 也会提示"已隐藏该平台"——这是**预期行为**，不是 bug；Switch 有 x86_64 + aarch64 双包但需要 keys/固件，首次安装仍需联网下载。（已知限制）
39. **仓库提交的边界（v0.13.0）**：Issue 表单只是人工审核入口，暂不自动转 JSON（维护者手工/脚本处理）；没有审核标签、自动评论、自动 PR、自动 git commit；校验只做静态字段/重复 shareCode，**不联网验证分享链接是否可访问、提取码是否有效**；提交不包含封面/Steam AppID（合并行留空，后续由封面解析/目录维护补）；`submissions/merged/` 的归档文件不自动提交回仓库。（已知限制）
40. **百度网盘的边界（v0.17.0）**：主链路是**扫码登录（BDUSS/Cookie）**，Cookie 等价账号凭据、会过期/被风控，失效需重新扫码；扫码 session 仅内存 180s，**扫码确认/换 Cookie 尚未真机验证**（`getqrcode`/`unicast` waiting 已实测）；OpenAPI 是可选回退，需要自建应用/授权，并会把分享文件转存 `/FreedeckTmp`（占网盘空间，安装后清理）；两条链路都**不接 CDP/网页逆向**，百度接口变更可能影响扫码/直链；下载速度受百度账号与官方限速影响。（已知限制）
41. **模拟器存档上传的边界（v0.16.0）**：PSP/PS3/3DS 已支持按游戏拆分（PARAM.SFO/NCSD），但 PS1/PS2 单片记忆卡与 Switch 目录仍整目录上传（同卡其它游戏也会被包含）；GBA/FC/MD/NDS 按 ROM 文件名匹配，改名/自定义存档名会 `game_save_not_found`（不会退化成整目录）；3DS/Switch 目录可能很大（受指纹 5000 文件与上传体积限制）；设置 `cloud_save_include_emulators` 默认开，可关。（已知限制）
42. **模拟器存档恢复/多碟的边界（v0.16.0）**：恢复目标受已知存档根白名单限制（`restore_roots`），跨设备 3DS 可能退化到根目录；PS1/PS2/Switch 共享卡/目录覆盖不能只挑单个游戏，冲突需确认后整文件覆盖（有 `*.freedeckcy-bak-<时间戳>` 备份）；PS1 多碟只在多张 `.cue/.chd` 时自动生成 `freedeckcy-multidisc.m3u`，单碟/已有 m3u 不生成；m3u 按文件名自然排序，碟号命名不规范时顺序可能不符合预期。（已知限制）
43. **扫描已安装的边界（v0.18.0；v0.21.0 补快捷方式）**：只扫安装目录一层、最多 500 项；目录名需与目录标题归一化匹配（改名可能 `catalog_no_match`）；补已安装记录/回填 appid/找 ROM；v0.18 不创建 Steam 快捷方式，**v0.21.0 起自动补建**（见 46，模拟器未装不下载）；模拟器 ROM 找不到时记录仍建但 `rom_path` 为空；扫描不会删除/修正已有记录。（已知限制）
44. **存储位置选择的边界（v0.19.0）**：只显示已挂载且可写的 `/run/media`、`/media`、`/mnt`、`/storage`、`/sdcard` 子挂载；挂载根（如 `/mnt` 本身）跳过；只读/权限不足/未挂载不会出现；容量为快照；不会自动创建/挂载/格式化，也不检测 Steam 库是否同盘；建议子目录固定 `freedeckCY/{downloads,installed}`。（已知限制）
45. **Decky 原生游戏库的边界（v0.20.0）**：任务进度仍在 QAM 主页任务区，库页只有列表/分页/安装/已安装动作；没有封面卡片视图，固定 20 条/页；扫描仍只认 `settings.install_dir` 一层；卸载固定删文件（不含 compatdata 回收选项）；网页库仅作备用，两套 UI 可能短暂不同步（以原生库/接口为准）。（已知限制）
46. **扫描补 Steam 快捷方式的边界（v0.21.0）**：只对扫描到/已存在但 `steam_app_id=0` 的 PC 记录补建；模拟器快捷方式要求模拟器已安装（`allow_download=False`，不会自动下载），否则记 `shortcut_error=emulator_not_ready`；PC 找不到 exe/ROM 时跳过并记 `exe_not_found`/`rom_not_found`；只写 `shortcuts.vdf`，**Steam 需重启/切用户/重开库页才可见**；不覆盖已有同名同 exe 快捷方式。（已知限制）
47. **诊断自检的边界（v0.22.0）**：自检是一次性快照（版本/目录/运行时/Steam/存储/网络/百度 QR/任务/日志），网络项受连通性影响；「运行自检」不自动修复，只给 detail/fix；`baidu_qr` 只输出 sign 长度（不输出 sign/cookie）；导出诊断包会写 0600 zip 到下载目录并包含 300 行日志（已脱敏），仍建议提交前自行过目；不支持在线查看日志或上传诊断包。（已知限制）
48. **原生库兜底/扫码超时的边界（v0.23.0）**：`showModal(<LibraryPage />)` 失败才走全屏路由，两者都失败才 toast；**前端未重载/旧 `dist` 仍可能打开旧网页或没有版本标识**（以 `QAM 原生 UI v0.23.0`/`原生 UI · v0.23.0` 为准）；百度扫码前后端超时（start 20s/12s、poll 15s）依赖网络/TLS，超时只提示不自动重试；`Baidu QR` 日志只记 sign 长度，不记 sign/cookie。（已知限制）
49. **原生库返回/关闭的边界（v0.24.0）**：modal 模式依赖 `onClose` 回调关闭，route 模式用 `Navigation.NavigateBack()`；Steam 覆盖层的 B/Esc 不一定能关闭 modal，需用显式「返回」/「Steam 库」按钮；`Router.NavigateToLibraryTab()` 不可用时只回退 `NavigateBack`；sticky 栏只覆盖库页内部滚动，不改变 Steam 全局导航行为。（已知限制）
50. **库详情时长块的边界（v0.25.0）**：只有 `managed=true`（AppID 或标题匹配到 `installed_games`）才插入时长块；未匹配的 Steam 原有游戏直接 `return null` 且不查 HLTB；AppID 优先已降低同名误判，但标题匹配仍可能把同名 Steam 游戏认成插件游戏；HLTB 失败只影响块内数据；仍依赖 Steam 库页内部结构（patch 可能随 Steam 更新失效）。（已知限制）

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
| 模拟器注册表 / 10 平台（v0.6.0 起，v0.7.0/v0.9.0/v0.11.0 扩展，v0.10.0 全部在线下载） | `emulator_adapters.py`（Eden/DuckStation/PCSX2/PPSSPP/RPCS3/mGBA/Lime3DS/melonDS/Nestopia/BlastEm/MAME） | `emulator_manager.py` 的 `EmulatorSpec` 注册表：GBA=mGBA、PSP=PPSSPP、NDS=melonDS、PS1=DuckStation（需 BIOS）、FC/MD=Mesen2、3DS=Azahar（SteamOS 优先官方 Flatpak，AppImage 回退）/PS2=PCSX2/PS3=RPCS3（仅 x86_64，需 system files/BIOS/固件）、Switch=Eden（x64/arm64，需 keys/固件）；**插件包不集成模拟器、首次安装在线下载**；架构白名单/BIOS 复制/ROM 查找/启动脚本见 5.10 |
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
- **百度网页版 CDP 采集 / 未公开接口**：需逆向网页接口/采集登录态，维护成本与封号风险高；v0.17.0 改为**百度 Passport 官方扫码**拿 BDUSS/Cookie（主链路），OpenAPI 仅可选回退，**仍不做 CDP/网页接口逆向**。

### 13.4 待做（详见 ROADMAP §9）

`7z t` 校验与 compatdata 卸载清理已在 v0.1.1 落地（见 13.1）。其余待做：Range 续传探测、SQLite 任务库、资源池只读、自动重启 Steam；百度网盘已在 v0.14.0 落地 OpenAPI、v0.17.0 改为扫码/Cookie 主链路（OpenAPI 可选回退，见 5.13；CDP/网页逆向不做）；模拟器 10 平台已全部接入（3DS/PS2/PS3 仅 x86_64，aarch64 自动隐藏；各平台 BIOS/固件/keys 由用户自备）；CTFile 等其它网盘来源仅作评估（接口/合规先决条件多，未列入当前优先级）。

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
| HLTB | How Long To Beat，游戏时长数据库，本项目用它显示"主线 / 总时长"；v0.25.0 起只对 `managed=true`（插件安装记录）查询 |
| managed 门禁 | v0.25.0 的库页时长隔离：前端只在 `data.managed===true` 渲染 `LibraryTimeBlock`，后端未匹配已安装记录直接返回 `managed=false` 且不查 HLTB |
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
| 模拟器注册表 / 闭环 | v0.11.0：`EmulatorSpec` 注册表接入 10 平台（GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch）；**全部首次安装在线下载、插件包不集成**；下载 ROM → 生成启动脚本 → Steam 原生快捷方式（不经 Proton） |
| 架构能力矩阵 / available_platforms | 按当前架构是否有官方资产决定可用平台：x86_64 全部 10 个；aarch64 仅 GBA/PSP/NDS/PS1/FC/MD/Switch（3DS/PS2/PS3 无 arm64 包 → 目录白名单隐藏条目与筛选条） |
| EmulatorSpec | 平台注册表条目：官方资产（repo/版本/各 arch 文件名）、archive（appimage/zip）、launch_args、rom_extensions、env_var、min_bytes、state_key（缓存目录名，FC/MD 共用 mesen）、executables（zip 内可执行文件名）、bios_required |
| 诊断自检 / run_diagnostics | v0.22.0 的自检：插件/目录/runtime/目录数据/Steam/存储/网络/百度 QR/任务/日志逐项 `ok|warn|fail|skip` + detail/fix；导出包含 `self-check.json` |
| 原生游戏库 / LibraryPage | v0.20.0 的 Decky 原生库：路由 `/freedeckcy/library`，Tab（游戏库/已安装/刷新）、搜索/筛选/排序/20 条分页、安装确认与已安装启动/目录/卸载/扫描；全部走 callable，不依赖本地网页 |
| 存储位置 / storage_options | v0.19.0 的 SD 卡选择：解析 `/proc/mounts` 找可写外置挂载（SteamOS `/run/media`、DroidDeck `/storage` 等），给 `freedeckCY/{downloads,installed}` 建议目录与容量，QAM「路径」页一键切换 |
| 扫描已安装 / scan_installed_games | v0.18.0 的补录入口（v0.21.0 移到设置并自动补 Steam）：扫安装目录一层，按目录名/标题匹配目录条目，回填 appid、模拟器找 ROM，补 `TianyiInstalledGame`；v0.21.0 起查重后自动补建快捷方式 |
| 百度扫码 / BaiduLoginState | v0.17.0 的百度主链路：Passport 二维码（`getqrcode` → `unicast` → `qrbdusslogin`）换 BDUSS/STOKEN/PTOKEN，Cookie 存 `state.json` 的 `baidu_login`；安装计划优先 Cookie |
| 百度 OpenAPI / BaiduOpenApiLoginState | v0.14.0 的可选回退：OAuth oob 授权（App Key/Secret → 授权码 → access/refresh token），state 顶层 `baidu_openapi`；分享文件转存 `/FreedeckTmp` 后取 dlink，安装后清理 |
| 仓库提交 / submission | v0.13.0 的投稿通道：Issue 表单或 `submissions/*.json` PR，字段对应原版资源池投稿；`submission.py` 校验后由维护者合并进目录 CSV，文件归档到 `submissions/merged/` |
| Azahar Flatpak / flatpak_id | v0.14.1 的 3DS SteamOS 方案：`EmulatorSpec.flatpak_id=org.azahar_emu.Azahar`；SteamOS 或已装 Flatpak 时优先 `flatpak run`，未装则自动 `flatpak remote-add` + `flatpak install`，失败回退 AppImage；3DS wrapper 走 XWayland |
| 模拟器存档恢复白名单 / restore_roots | v0.16.0 的安全边界：只允许恢复到平台标准/portable 存档根；同机优先原父目录，跨机落到第一个根，拒绝 manifest 任意路径 |
| PARAM.SFO / NCSD title id | PSP/PS3 存档目录里的 `PARAM.SFO`（`TITLE` 用于匹配游戏）；3DS NCSD 头 `0x108` 的 Program ID（十六进制）用于匹配 `title/00040000/<low8>`；两者用于把共享存档拆成单游戏 |
| 模拟器存档 / emulator_saves | v0.15.0 的存档发现模块：`STANDARD_SAVE_DIRS`/`PORTABLE_SUBDIRS` 覆盖 10 平台；GBA/FC/MD/NDS 按 ROM 文件名单游戏匹配，PSP/PS1/PS2/3DS/PS3/Switch 返回共享记忆卡/标题目录（按路径签名去重）；v0.16.0 起 PSP/PS3/3DS 可按游戏拆分，并支持恢复（白名单目标 + 备份 + 冲突确认） |
| emulator_setup / portable 配置 | v0.12.0 新增的部署模块：把 `bios/<platform>/` 下的 BIOS/固件/keys（含压缩包）复制到模拟器实际读取目录，并写最小 portable 配置（DuckStation/PCSX2 INI、mGBA/PPSSPP 全屏）；只补缺失/只改单个键，不下载、不覆盖用户配置 |
| BIOS / setup 文件 | PS1 需要 DuckStation BIOS（`bios/ps1/`）、PS2 需要 PCSX2 BIOS（`bios/ps2/`，复制到 `~/.local/share/PCSX2/bios` 与 `~/.config/PCSX2/bios`）；3DS 需要 system files、PS3 需要固件、Switch 需要 prod.keys+固件（`setup_hint` 提示）；插件不内置这些文件，缺失只提示不阻断安装 |
| 按需下载 | **10 个平台（含 GBA）首次安装时**都从 GitHub release 下载官方包到 `~/.local/share/freedeckCY/emulators/<platform>/<arch>/`（FC/MD 共用 `mesen/`）；插件包不集成模拟器，离线可手动预置缓存或用 `FREEDECKCY_*_BIN` |
| ROM / wrapper | ROM = 安装目录里符合平台扩展名的文件（GBA `.gba`；PSP `.iso/.cso/.pbp/.elf`；NDS `.nds/.dsi/.srl`，优先 openpath 同名）；wrapper = `<install_dir>/launch-freedeckcy.sh`（按平台拼启动参数，Steam 快捷方式的 Exe） |
| `proton_tool` / `PACKAGE_ARCH` | 设置项 `proton_tool`：`auto`/`none`/具体兼容工具名；打包变量 `PACKAGE_ARCH`：`x86_64`/`aarch64`/`all`，决定产物架构与后缀 |
| cover_index.csv | 封面索引文件（仓库已内置 3470 行）：按 `game_id` 或标题补齐封面/appid/platform，不覆盖目录 CSV 已有值 |
| 平台 / 分类筛选条 | 库页搜索后的两行 chip：平台条（「全部平台」+ 各平台计数，v0.3.0 起可见）与分类条（「全部分类」+ Top12 分类计数，含「模拟器」）；都可与搜索词组合 |
| 分类清洗 / 数据体检 | v0.3.1 引入：`normalize_categories()` 在加载时剔除分类中的平台名并去重；`validate_catalog.py` 对目录做重复/非法链接/封面覆盖率等体检，`--strict` 进 CI 门禁 |
| 天翼云盘 | 中国电信 189 云盘，`cloud.189.cn`，本项目唯一的资源存储后端 |
