# Changelog

本项目从 v0.1.0 起使用独立版本号（fork 自 Freedeck，与上游 0.2–0.3 不连续）。

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
