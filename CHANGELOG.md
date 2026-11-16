# Changelog

本项目从 v0.1.0 起使用独立版本号（fork 自 Freedeck，与上游 0.2–0.3 不连续）。

## v0.14.0

### 新增

- **百度网盘（官方 OpenAPI）**：
  - 移植 v0.6 的 `baidu_client.py` / `baidu_openapi_client.py`，安装计划与下载任务支持 `baidu_openapi` 来源。
  - QAM「设置 → 百度网盘（官方 OpenAPI）」：填写 App Key/Secret Key、获取授权链接、粘贴授权码、清除授权；token 过期自动 refresh。
  - 安装时自动解析公开分享、转存到 `/FreedeckTmp`、获取 dlink，aria2 使用 `Referer: https://pan.baidu.com/disk/home` + `UA: pan.baidu.com` 下载；安装完成后清理转存文件。
  - 支持 `FREEDECKCY_BAIDU_OPENAPI_APP_KEY` / `SECRET_KEY` / `REFRESH_TOKEN` 环境变量。
- **仓库提交/目录支持百度链接**：`submissions` 接受 `pan.baidu.com` / `yun.baidu.com`，合并时 `server=b`；目录校验与加载同时支持天翼/百度。
- 新增 HTTP API：`/api/tianyi/baidu/openapi/{app,authorize-url,exchange,clear}`。

### 变更

- 任务记录新增 `provider` / `share_url` / `share_ctx`；重新获取直链按来源分支。
- 测试 314 → 326（新增百度来源识别、token 刷新、安装计划、任务头、授权码交换、百度提交等用例）。

### 说明

- 只接官方 OpenAPI，不实现 BDUSS/Cookie 网页抓取或 CDP；用户需自行在百度网盘开放平台创建应用并授权。

## v0.13.0

### 新增

- **仓库游戏提交**（对应原版资源池投稿字段）：
  - GitHub Issue 表单 `.github/ISSUE_TEMPLATE/submit-game.yml`：名称/英文名/平台/分享链接/提取码/分享用户版本/可执行文件名/网盘路径。
  - PR 流程 `submissions/*.json`（schema + 示例），支持批量提交。
  - `scripts/validate_submissions.py`：平台、分享链接、`openpath`、重复 shareCode 校验；已接入 CI。
  - `scripts/merge_submissions.py`：dry-run / `--apply` 合并进目录 CSV，自动分配 `game_id`，已合并文件移到 `submissions/merged/`。
  - 网页库工具栏新增「提交游戏」按钮，直接打开 GitHub Issue 表单。
- 新文档 `submissions/README.md`，字段表、规则、维护者命令。

### 变更

- 测试 308 → 314。

## v0.12.0

### 新增

- **模拟器 BIOS/固件部署（参考 v0.6 / NewFreedeck）**：`bios/<platform>/` 里可以直接放原始文件或 zip/7z/rar 压缩包，安装时用 7zz 解压并部署到模拟器实际读取的位置。
  - PS1/PS2：BIOS 复制到 portable 目录 + DuckStation/PCSX2 用户目录；自动写/修复 `portable.txt`、`settings.ini`、`PCSX2.ini` 的 BIOS 搜索路径。
  - NDS：`bios7.bin`/`bios9.bin`/`firmware.bin`/DSi 固件复制到 melonDS 目录。
  - Switch：`prod.keys`/`title.keys` 复制到 Eden keys；固件压缩包解压出 `.nca` 后部署到 `nand/system/Contents/registered`。
  - PS3：检测到 `PS3UPDAT.PUP` 且 `dev_flash` 为空时，自动执行 `rpcs3 --installfw`。
  - 3DS：system files 复制到 Azahar/Citra 的 sysdata 目录。
- **Portable 配置**：mGBA（`portable.ini` + `qt.ini` 全屏）、PPSSPP（`portable.txt` + `ppsspp.ini` 全屏）、DuckStation/PCSX2（BIOS 搜索目录/全屏）。
- 安装消息会列出 BIOS/固件部署结果与缺失提示。

### 变更

- 服务层安装流程改为统一调用 `emulator_setup.setup_emulator()`；旧 `prepare_bios()` 保留兼容。
- 测试 302 → 308。

## v0.11.0

### 新增

- **补齐模拟器平台**：
  - 3DS：Azahar（官方 AppImage，**仅 x86_64**；需要 system files）
  - PS2：PCSX2 2.8.2（**仅 x86_64**；需要 PS2 BIOS，安装时复制到 PCSX2 bios 目录）
  - PS3：RPCS3（**仅 x86_64**；需要 PS3 固件）
  - Switch：Eden 0.2.1（**x86_64 + aarch64**；需要 prod.keys 与固件）
- **架构能力矩阵**：x86_64 显示全部 10 个平台；aarch64 只显示有官方 arm64 包的平台（GBA/PSP/NDS/PS1/FC/MD/Switch），3DS/PS2/PS3 自动隐藏（目录条目与平台筛选条都不显示）。
- 模拟器 setup 提示：BIOS（PS1/PS2）、固件/keys/system files（PS3/Switch/3DS）会在安装弹窗和安装消息里提示；不阻断安装。
- 新环境变量：`FREEDECKCY_AZAHAR_BIN`、`FREEDECKCY_PCSX2_BIN`、`FREEDECKCY_RPCS3_BIN`、`FREEDECKCY_EDEN_BIN`。

### 变更

- 目录列表支持平台白名单：按当前架构过滤条目、平台/分类计数。
- 测试 295 → 302。

## v0.10.0

### 变更

- **模拟器全部改为在线下载**：移除内置 mGBA AppImage、`make emulator-runtime` 与 `defaults/runtime/mgba/` 的打包集成；GBA/PSP/NDS/PS1/FC/MD 六个平台都在首次安装时从官方 release 下载，缓存到 `~/.local/share/freedeckCY/emulators/<platform>/<arch>/`。
- 插件包不再包含任何模拟器二进制，体积由约 68MB 降到约 45MB；模拟器下载一次后离线可用。
- `emulator_status` 不再返回 `source=bundled`；无本地版本时显示 `source=download`。
- 保留 `FREEDECKCY_*_BIN` 覆盖与手动预置缓存（离线环境可自行放入对应目录）。

## v0.9.0

### 新增

- **PS1（DuckStation）**：官方 AppImage（x86_64 / arm64），支持 `.cue/.m3u/.chd/.iso/.pbp/.bin`；启动 `-batch -fullscreen`。
  - **BIOS**：把 `scph*.bin` 放到 `~/.local/share/freedeckCY/bios/ps1/`，安装时自动复制到 DuckStation 的 bios 目录；缺 BIOS 时安装消息/库页弹窗会提示。
- **FC（Mesen2）**：支持 `.nes/.fds/.unf/.unif`，官方 Linux x64/arm64 zip，启动 `/fullscreen`。
- **MD（Mesen2）**：支持 `.md/.gen/.smd/.bin/.32x`，与 FC 共用同一份 Mesen2 缓存。
- 模拟器支持范围扩展到 PC + GBA/PSP/NDS/PS1/FC/MD；PS2/PS3/3DS/Switch 因仅 x86 或依赖 BIOS/固件暂未接入。

### 变更

- 新环境变量：`FREEDECKCY_DUCKSTATION_BIN`、`FREEDECKCY_MESEN_BIN`。
- 模拟器状态新增 `bios_required` / `bios_present` / `bios_dir`；库页弹窗显示 BIOS 提示。
- 测试 289 → 295。

## v0.8.0

### 新增

- **Ludusavi 存档清单**：内置 53,549 款 PC 游戏的存档路径（MIT，`defaults/ludusavi/`），按标题/Steam ID 匹配，解析 `<base>` / `<winAppData>` / `<winLocalAppData>` / `<winDocuments>` 等占位符到 Proton 前缀，与原有目录扫描合并。
- **gamewatch 自动同步**：后台每 8 秒扫描 `/proc/*/cmdline`（无 `/proc` 时回退 `pgrep -f`），游戏退出后**只上传该游戏**的存档；`cloud_save_auto_upload` 默认开启，QAM「云存档上传」里可关闭。
- **存档指纹去重**：按文件相对路径/大小/mtime 计算指纹并持久化；未变化的游戏自动跳过，避免每次退出都产生新版本。
- `make ludusavi-manifest`：从上游 YAML 重新生成清单（PyYAML 仅构建时需要）；`FREEDECKCY_LUDUSAVI_MANIFEST` 可覆盖路径。

### 变更

- 云存档上传任务支持 `game_ids` 过滤（手动上传仍处理全部）。
- 测试 280 → 289。

## v0.7.0

### 新增

- **通用模拟器注册表**：`py_modules/emulator_manager.py` 改为按平台描述（官方资产、启动参数、ROM 扩展名、环境变量），后续平台只需加一条配置。
- **PSP（PPSSPP）**：支持 `.iso/.cso/.pbp/.elf`；首次安装按需下载官方 AppImage（x86_64 / aarch64，约 46–48MB），启动加 `--fullscreen`。
- **NDS（melonDS）**：支持 `.nds/.dsi/.srl`；首次安装按需下载官方 AppImage zip（x86_64 / aarch64，约 32MB），自动解包。
- 已安装的模拟器缓存到 `~/.local/share/freedeckCY/emulators/<platform>/<arch>/`；`FREEDECKCY_PPSSPP_BIN` / `FREEDECKCY_MELONDS_BIN` 可覆盖。
- 诊断包 `emulators` 改为输出所有已接入平台的状态（本地/需下载/不可用）。

### 变更

- 库页允许安装 GBA / PSP / NDS；弹窗显示对应模拟器名称。
- 安装计划不再要求模拟器已存在：可下载的平台会标记 `source=download`，安装完成时再拉取；失败会写入安装消息。
- 测试 271 → 280。

## v0.6.2

### 新增

- **远程 JSON 目录**：`FREEDECKCY_CATALOG_JSON` 现在支持 `https://` URL（例如 `raw.githubusercontent.com/.../catalog-json/all.json`），下载后缓存到 `~/.local/share/freedeckCY/catalog-remote-cache.json`，6 小时内直接读缓存；网络失败时用旧缓存，缓存也没有则回退 CSV。
- 目录来源 `source` 新增 `json-url` / `json-url-cache`，诊断包可见。

### 变更

- 远程目录下载上限 64MB、超时 10s；实测 7084 条 4.9MB。
- 测试 271 → 275。

## v0.6.1

### 新增

- **运行时 JSON 目录**：新增 `FREEDECKCY_CATALOG_JSON` 环境变量，可直接加载 NewFreedeck 兼容 JSON（如 `catalog-json/all.json`）；支持 `variants` 去重、保留 `openpath`，文件缺失/为空时自动回退 CSV。
- 仓库内提交 `catalog-json/` 快照（`all.json` / 平台 / 精选 / `manifest.json` / schema / `emu.example.json`），clone 后可直接读取或自托管；新增一致性测试。
- 新增 `scripts/export_remote_catalog.py` + `make catalog-json`，以及 [docs/UPSTREAM_SERVER.md](docs/UPSTREAM_SERVER.md)（`panyiwei.xyz` 依赖逆向与替代方案）。

### 变更

- 诊断包 `catalog` 字段新增 `source` / `json_path`。
- 测试 260 → 271。

## v0.6.0

### 新增

- **GBA 模拟器闭环（x86_64 + ARM64）**：GBA 资源从“只可浏览”变为可安装、可启动。
  - 内置 mGBA 0.10.5 官方 AppImage（x64 / arm64，各约 24MB）；首次使用 `--appimage-extract` 解包到用户目录，不依赖 FUSE（DroidDeck/proot 可用）。
  - 天翼分享分页查找目标 ROM（一个分享含数百个 ROM），按目录 `openpath` 精确选择文件。
  - 安装完成自动生成 `<install_dir>/launch-freedeckcy.sh`，写入 Steam 快捷方式；**不写 Proton 映射**（原生 Linux）。
  - 已安装记录新增 `platform` / `emulator` / `rom_path` / `launcher_path`，列表与诊断可见。
- `make emulator-runtime`（`scripts/fetch_emulator.sh`）：按架构下载 mGBA AppImage，打包时自动带上对应架构。
- 库页允许 GBA 安装，弹窗显示“模拟器：mGBA”。

### 变更

- 非 PC 平台：GBA 放行，其余平台仍拒绝并提示“暂未接入模拟器”。
- `resolve_share()` 新增 `target_name` / `max_pages` 参数，支持分页定位文件。
- 打包按架构裁剪 `defaults/runtime/mgba/`，并检查 `mGBA.AppImage` 是否存在。
- 测试 251 → 260。

## v0.5.0

### 新增

- **目录浏览**：库页打开即浏览全部 7084 条资源（不再必须先搜索），支持平台/分类筛选、分页（L1/R1、PageUp/PageDown 或按钮）与排序（默认/名称/大小）。
- **已安装页签**：库页可切换「游戏库 / 已安装」；已安装卡片支持启动（`steam://rungameid/<appid>`）、打开目录、卸载；手柄 A 启动、Y 打开目录、Delete 卸载、X 切换页签。
- **诊断导出**：`GET /api/tianyi/diagnostics/export` 生成 zip（diagnostics.json + 日志末尾 300 行 + README），cookie/token 与 HOME 路径自动脱敏；库页「导出诊断」一键下载。
- **更新检查**：`GET /api/tianyi/update-check` 对比 GitHub 最新 Release（1 小时缓存），库页「检查更新」提示并可打开 Release 页。

### 变更

- `GET /api/tianyi/catalog` 新增 `sort` 参数（`title` / `size_desc` / `size_asc` / `platform`）。
- 新增接口：`GET /api/tianyi/installed`、`POST /api/tianyi/installed/launch|open-folder|uninstall`、`GET /api/tianyi/diagnostics[/export]`、`GET /api/tianyi/update-check`。
- 修复库页卡片焦点环在平台/分类筛选条存在时偏移的问题。
- 测试 242 → 251。

## v0.4.0

### 新增

- **DroidDeck 适配（Android/ARM64）**：新增 `make package-droiddeck` 产出 `-arm64` 插件包；运行时按 `platform.machine()` 选择 `aarch64` 版 aria2c / 7zz / node。
- **Proton 工具自动判断**：检测到 DroidDeck 时自动改用 `droiddeck-proton-arm64`（若 `config.vdf` 出现 11 版则用 `droiddeck-proton-11-arm64`）；新增设置项 `proton_tool`（`auto` / `none` / 指定工具名）与环境变量 `FREEDECKCY_PROTON_TOOL`。
- **双 Steam 客户端处理**：DroidDeck 的 x64 Steam 客户端有独立 HOME（`~/.droiddeck-x64/.local/share/Steam`）；若其正在运行（`steam.pid`）则优先写入该客户端。
- 新增 [docs/DROIDDECK.md](docs/DROIDDECK.md)：安装、构建、路径、Proton、排障与已知限制。

### 变更

- 打包脚本支持 `PACKAGE_ARCH=x86_64|aarch64|all`，单架构打包会裁剪其它架构运行时。
- `GET /api/tianyi/settings` 返回 `proton_tool_resolved` 与 `droiddeck_detected`。
- 测试 233 → 242（新增 DroidDeck 检测、ARM 工具选择、双客户端路径、设置往返等用例）。

## v0.3.1

### 新增

- **目录数据体检**：`scripts/validate_catalog.py` + `make validate-catalog`，检查重复 game_id / 非法链接 / 空标题 / 分类混入平台名 / 封面覆盖率；CI 增加 strict 校验步骤。
- **分类清洗**：`scripts/normalize_catalog_categories.py` + `make normalize-catalog`，剔除分类里的平台名（GBA、Switch 等）、统一分隔符与去重；模拟器行清洗后为空时补“模拟器”。

### 变更

- 目录数据已清洗：606 行 categories 变更，分类里不再出现平台名（`GBA` 553 条、`Switch` 42 条已并入“模拟器”分类）。
- 测试 231 → 233（新增分类清洗与数据洁净度用例）。

## v0.3.0

### 新增

- **内置目录扩充到 v0.6 全量数据**：`defaults/tianyi_catalog/freedeckcy_catalog.csv`，7084 条有效资源、11 个平台（PC 2540 / FC 1475 / NDS 722 / PSP 575 / GBA 553 / 3DS 305 / PS2 250 / PS1 194 / PS3 194 / MD 191 / Switch 85），并随包附带 3470 行封面索引。
- **平台筛选**：库页新增平台筛选条（全部平台 / PC / FC / NDS …），与分类筛选条并存；手柄焦点序列更新为 搜索框 → 搜索按钮 → 平台条 → 分类条 → 卡片。
- **网页版分享链接**：支持 `https://cloud.189.cn/web/share?code=…`（FC/GBA/MD 等模拟器资源使用该形式）。
- **封面覆盖**：合并后的目录有 6823 条自带封面，店铺页不再依赖实时搜索。

### 变更

- 目录文件切换为 `freedeckcy_catalog.csv`（旧 `gamebox_all_links_*.csv` 保留为回退）。
- 非 PC 平台资源当前**只可浏览、不可安装**：库页点击会提示“未集成模拟器”，后端安装计划也会拒绝，避免误下整包。
- 测试 227 → 231。

## v0.2.0

### 新增

- **目录平台化**：目录条目新增 `platform` / `cover_url` / `cover_portrait_url` / `steam_appid` 字段，缺失平台默认 `pc`；搜索接口支持 `platform` 与 `category` 筛选，返回平台与分类计数。
- **封面索引**：支持可选的 `defaults/tianyi_catalog/cover_index.csv`（按 `game_id`、标题匹配），命中后直接用本地封面，不再请求 Steam 商店；有 `steam_appid` 时可直接合成 Steam CDN 封面。
- **封面磁盘缓存**：运行时解析到的封面写入 `~/.local/share/freedeckCY/tianyi/cover_cache.json`（0600、TTL 7 天），重启插件后仍生效。
- **库页分类筛选**：搜索结果上方新增分类筛选条（全部 / 动作冒险 / 角色扮演 …），支持手柄方向键在筛选条与卡片间导航；卡片显示平台标签。

### 变更

- 目录接口 `/api/tianyi/catalog` 新增 `platform`、`category` 参数，响应新增 `platforms`、`categories` 字段。
- 修正目录环境变量名为 `FREEDECKCY_GAME_CATALOG_CSV`（兼容旧名）。
- 测试 220 → 227。

## v0.1.1

### 新增

- **卸载回收 Proton 前缀**：卸载时可选择同时删除 `steamapps/compatdata/<appid>`；确认框会先显示安装目录与 Proton 前缀各自占用，默认只删游戏文件。跨 Steam 库定位，路径结构校验后才删除。
- **解压前 `7z t` 校验**：解压前先测试归档完整性；校验失败会隔离坏文件并用原直链自动重新下载一次，重下完成后自动继续安装。7z 不可用时自动跳过校验，不影响安装。
- **失败任务重试**：QAM 任务行新增「重试」按钮。文件已完整时直接重新安装；不完整则重新获取直链续传。
- **`make doctor` 环境诊断**：一条命令输出系统/架构、Python 版本、运行时二进制、Steam 根与库、state.json、日志最近错误、端口与 `/_healthz`、天翼云盘连通性，只读。

### 变更

- 版本号 0.1.0 → 0.1.1。
- 测试从 215 增加到 220（新增卸载清理、7z 校验失败自愈、任务重试等用例）。

## v0.1.0

首个独立版本：

- 从上游 Freedeck 早期版本 fork，更名 freedeckCY，状态目录 `~/.local/share/freedeckCY`、日志 `/tmp/freedeckcy.log`、Launch token `freedeckcy:tianyi:`。
- 继承并整合三轮工程补全：运行时获取与打包、P0 缺陷修复、分卷分组安装、aria2 运行时复用与直链原地换链、Steam 多库/SD 卡/Flatpak、Steam 配置写前备份与 `DevkitGameID` 去重。
- 215 个 pytest 用例；GitHub Actions（pytest + pnpm build）。
