# freedeckCY 开发指南

本文面向二次开发者，对应 freedeckCY **v0.1.1**：如何在本地跑起来、改代码、打补丁、排查故障。架构与协议细节见 [ARCHITECTURE.md](ARCHITECTURE.md)，与作者 v0.6 的能力对照见 [ARCHITECTURE.md](ARCHITECTURE.md) §13，后续可做项见 [ROADMAP.md](ROADMAP.md)。

> 前提：本项目只支持 **SteamOS / Linux**。开发机可以是 Steam Deck，也可以是装了 Decky Loader 的 Linux 桌面环境；Windows / macOS 只能改代码，不能完整运行。

---

## 1. 模块职责速查

| 路径 | 职责（一句话） |
|---|---|
| `main.py` | Decky 插件入口：`Plugin` 类持有 Python 侧状态，把 24 个可调用 RPC 薄转发给 `TianyiService` / `server_manager`；主循环周期调用后台维护 |
| `py_modules/config.py` | 路径常量（下载目录、`~/.local/share/freedeckCY`）、后台维护间隔与日志器（`/tmp/freedeckcy.log`，`RotatingFileHandler` 5 MB × 3） |
| `py_modules/tianyi_service.py` | **业务内核**：安装计划、下载任务、后台安装、云存档、登录、游玩时长、面板状态缓存；关键函数 `maintenance_tick`（后台维护）、`refresh_tasks`（状态同步）、`_try_recover_task` / `_readd_task_download`（重启恢复 + `changeUri` 原地换链）、`_maybe_schedule_group_post_process` / `_finalize_group_install`（分卷分组）、`_verify_downloaded_file` / `_quarantine_download_file`（完整性校验与自愈）、`_wait_payload_settled` / `_precheck_archive_payload` / `_schedule_archive_repair`（解压前收紧与 `7z t` 失败自动重下）、`retry_task`（失败任务重试）、`preview_uninstall` / `uninstall_installed_game`（卸载预览与 Proton 前缀回收） |
| `py_modules/tianyi_client.py` | **天翼云盘协议客户端**：分享解析、accessToken、下载直链、上传（调 Node）、sessionKey |
| `py_modules/tianyi_http.py` | 本地 HTTP 路由与 handler：Vue 页面、REST API、统一 JSON 响应 |
| `py_modules/server_manager.py` | aiohttp 生命周期、本地 API 安全边界（Host/Origin 校验）、设置备份、`/_healthz` |
| `py_modules/tianyi_store.py` | 数据类（登录/设置/任务/已装游戏，含 `file_size` / `group_id` / `group_total`）+ `state.json` 原子读写；写入时目录 0700 / 文件 0600 |
| `py_modules/aria2_manager.py` | aria2 子进程管理（运行时元数据 `aria2-runtime.json` + `flock` 让插件重载可附着存活实例）+ JSON-RPC（`addUri` / `changeUri` / `tellStatus` / `listDownloads` …） |
| `py_modules/seven_zip_manager.py` | 7z 解压 / 压缩（带进度回调）；`test_archive()` 跑 `7z t` 做解压前校验（7z 不可用时 best-effort 跳过） |
| `py_modules/steam_shortcuts.py` | 写 `shortcuts.vdf`（`DevkitGameID` token 去重、无变化不重写、写前备份 12 份、写后回读）、改 `config.vdf` 的 Proton 映射、下载 `grid` 封面、解析 appid；Steam 多库 / Flatpak 识别（`_steam_library_paths` / `find_compat_user_dir`，自定义用户名打分）；`find_compatdata_dirs()` 跨库定位待清理的 Proton 前缀 |
| `py_modules/game_catalog.py` | 读 CSV 资源清单：校验、搜索、分页、按 `game_id` 查找 |
| `py_modules/archive_bundle.py` | 多分卷归档识别（`.7z.001`/`.partN.rar`/`.z01+zip`/`.r00+rar` 等 6 类）：`detect_archive_sets` / `build_bundle_index` / `looks_like_multi_volume_name` |
| `py_modules/utils.py` | 端口占用检测、等待端口释放、局域网 IP 探测（历史遗留） |
| `py_modules/vdf/` | 第三方 VDF 库（文本 + 二进制格式），`py_modules/vdf/__init__.py` 提供 `parse/loads/dumps/binary_dumps` 等 |
| `backend/tianyi_share_resolver.js` | 分享链接解析的 Node 兜底实现（stdin 一行 JSON → stdout 一行 JSON） |
| `backend/tianyi_cloud_upload.js` | 云盘上传（`upload`）、列版本（`list_versions`）、下载（`download_file`）的 ESM 实现 |
| `backend/tianyi_cloud_upload.cjs` | 同一逻辑的 CommonJS 版，**只实现 `upload`**；仅在 `.js` 不存在时启用 |
| `src/index.tsx` | 全部 React 代码：QAM 主面板、设置页、Steam 库页时长注入、全局游戏事件监听 |
| `defaults/tianyi_library_ui/` | 本地 Vue 游戏库与二维码登录桥（免构建，直接改） |
| `defaults/tianyi_catalog/gamebox_all_links_*.csv` | 随插件分发的资源清单（`game_id,title,categories,down_url,pwd,openpath,filesize_z` 等） |
| `scripts/fetch_runtime.sh` | 下载 aria2c / 7zz / node 到 `defaults/runtime/`（`make runtime` 调用它） |
| `scripts/package.sh` | 组装 Decky 插件 zip 到 `dist-artifacts/`（`make package` 调用它） |
| `scripts/doctor.sh` | 环境诊断（只读，`make doctor` 调用）：系统/Python/运行时/Steam/state/日志/端口/网络 |
| `tests/` | pytest 单测（220 个用例）：目录解析、VDF、状态存储、云存档版本、安装链路、分组语义、重启恢复、多分卷识别、aria2 运行时、多库识别、卸载/compatdata、安全边界等离线逻辑 |
| `clear_freedeckcy_tasks.sh` | 运维脚本：清空 `state.json` 的 `tasks`（用 `$HOME`，可用 `FREEDECKCY_STATE_FILE` 覆盖路径） |
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

### 2.4 Vue 本地页面：免构建

`defaults/tianyi_library_ui/` 下的 `index.html`、`app.js`、`app.css`、`login_bridge.*`、`vue.global.prod.js` 是**浏览器直出**的静态文件，没有构建步骤：

- 直接编辑这些文件，刷新 Steam 内置浏览器里的页面即可（必要时重载插件让 Python 重新识别资源目录）；
- 本地网页地址：QAM 里"打开游戏库"按钮会调 `get_tianyi_library_url`，形如 `http://127.0.0.1:59271/tianyi/library`；
- 建议在桌面浏览器的无痕窗口里直接访问上述地址调试（只在回环地址监听，必须在本机访问）。

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

代码会优先使用这些内置运行时，只有不存在时才回退系统命令（`aria2c`、`7zz/7zr/7z`、`node`）。也可以用环境变量强制指定：

| 环境变量 | 作用 |
|---|---|
| `FREEDECKCY_ARIA2_BIN` | aria2c 可执行文件路径（另有历史拼写 `FRIENDECK_ARIA2_BIN` 兼容） |
| `FREEDECKCY_7Z_BIN` | 7zz 可执行文件路径 |
| `FREEDECKCY_NODE_BIN` | node 可执行文件路径（需 ≥ 18） |
| `FRIENDECK_GAME_CATALOG_CSV` | 覆盖资源清单 CSV 路径（注意是历史拼写 `FRIENDECK_`） |
| `FREEDECKCY_STEAM_ROOT` | 覆盖 Steam 根目录（Flatpak / 自定义安装 / 多盘位时用） |
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

- 版本号取自 `package.json` 的 `version` 字段（当前为 `0.1.1`）；
- zip 根目录直接是插件结构（不额外套目录）：`main.py`、`plugin.json`、`package.json`、`LICENSE`、`README.md`，以及 `dist/`、`py_modules/`、`backend/`、`defaults/`；
- 打包脚本会排除 `__pycache__`、`*.pyc`、`.DS_Store`、`node_modules`、`.git`、`tests`、`scripts`、`.github`、`docs`、`gl`、`dist-artifacts`（白名单之外的一律不打包）；
- 默认复用已提交的 `dist/index.js`，不会强制跑 `pnpm build`；需要重新构建前端时用 `bash scripts/package.sh --build-ui`（要求 PATH 里有 pnpm）；
- 如果此前跑过 `make runtime`，`defaults/runtime/` 会被一起打进 zip（这是能离线安装的关键）；因此 `make clean` 默认**保留** `defaults/runtime/`，要删需 `make clean CLEAN_RUNTIME=1`；
- 自定义输出目录：`bash scripts/package.sh --out-dir /tmp/freedeckcy-build`；
- 如果 `defaults/runtime/` 还没准备，脚本只警告不失败——但这样打出来的包在目标机上仍会缺运行时，请先 `make runtime`；
- 安装：Decky Loader → 设置 → 开发者 → 从压缩包安装插件（不同 Decky 版本措辞略有差异），或解压到 `~/homebrew/plugins/freedeckCY/` 后重启插件加载器。

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
- 当前共 **220 个用例**（`make test` 实测 `220 passed`）。其中 `tests/test_utils.py` 的端口相关用例依赖真实 socket 与计时，在机器高负载时可能偶发超时失败，重跑即可。
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

---

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
| 装完启动 **Steam 里目标 exe 不对** | 资源清单 `openpath` 不准时靠启发式定位（相对路径 → 叶子名 → 目录内第一个可执行文件）。改 CSV 的 `openpath` 后重新安装，或手工改 Steam 快捷方式的目标 |

---

## 8. 已知限制

- **资源源只有天翼云盘**：百度网盘、模拟器整合、用户资源池只存在于 GitHub Releases（v0.5 之后 / NewFreedeck），**本仓库没有实现**。
- **仅支持 SteamOS / Linux**：依赖 `7zz`、Proton、Steam 的 Linux 目录结构；Windows / macOS 无法运行。Steam 根目录支持原生 / Flatpak，SD 卡/第二块盘通过 `libraryfolders.vdf` 扫描。
- **作者已停止维护**：上游不再更新，接口失效只能自行修；release 与仓库版本存在代差（仓库落后）。
- **仅早期版本**：`package.json` 版本 0.1.1（fork 自上游 0.2 基线），功能和上游 release 里的成品有差距。
- **完整性校验是"大小 + 头部预检 + `7z t`（best-effort）"**：7z 不可用时自动跳过校验；没有哈希/签名校验；分卷识别只覆盖常见命名；云存档仍依赖 `node`。
- **Steam 运行中写入仍可能被覆盖**：写前有备份且写后回读，但无法阻止运行中的 Steam 覆盖 `shortcuts.vdf`/`config.vdf`；装完建议重启 Steam（自动重启 Steam 在 ROADMAP §9）。
- **compatdata 清理默认关闭**：卸载默认只删游戏文件；"连 Proton 前缀一起删"需要显式选择，避免误删存档。
- **隔离文件与备份不会自动清理**：`*.freedeckcy-archive-invalid-*`、`*.freedeckcy-size-mismatch-*`、`*.freedeckcy-bak-*` 会留在原目录，需要手工清理（或后续 ROADMAP 项）。
- **无 i18n**：界面全硬编码中文，文案散落在 `src/index.tsx`、`defaults/tianyi_library_ui/` 与 Python 返回值里。
- **无 Python 类型检查**：只有 pytest 单测 + CI，没有 mypy/ruff 之类的门禁。
- **天翼接口未公开**：签名、接口、风控随时可能变，失败时优先看 `/tmp/freedeckcy.log` 里的协议诊断。
- **合规风险**：项目分发的资源链接来自互联网，README 自述仅限研发测试，请自行评估版权与云盘服务条款。

---

## 9. 二次开发切入点

| 想改什么 | 去哪 |
|---|---|
| 改资源清单 / 加游戏 | `defaults/tianyi_catalog/*.csv`（字段见 `game_catalog.py` 的 `GameCatalog.load`） |
| 换资源源 / 接其他网盘 | `py_modules/tianyi_client.py`（协议层）+ `backend/`（Node 兜底）；需要同时改 `game_catalog.py` 的链接校验 |
| 改解压 / 安装目录规则 | `py_modules/tianyi_service.py` 的 `_resolve_install_target_dir` / `_extract_archive_to_dir` / `_merge_extracted_content` |
| 改多分卷识别规则 | `py_modules/archive_bundle.py` 的 `detect_archive_sets`（新增命名格式/主卷规则）/ `build_bundle_index` |
| 改 aria2 运行时复用 | `py_modules/aria2_manager.py` 的 `_read_runtime_meta` / `_attach_existing` / `_try_acquire_owner_lock` / `replace_uri` |
| 改下载行为（分片、并发、续传） | `py_modules/aria2_manager.py`（`add_uri` 的 options 与启动参数） |
| 改 Steam 快捷方式 / 封面 / Proton | `py_modules/steam_shortcuts.py`（appid、`shortcuts.vdf`、`config.vdf`、`grid`） |
| 改重启恢复 / 分组语义 / 完整性校验 | `py_modules/tianyi_service.py` 的 `_try_recover_task` / `_readd_task_download` / `_maybe_schedule_group_post_process` / `_finalize_group_install` / `_verify_downloaded_file` |
| 改归档校验 / 自动重下 | `py_modules/seven_zip_manager.py` 的 `test_archive` + `py_modules/tianyi_service.py` 的 `_schedule_archive_repair` / `ArchiveRepairScheduled` |
| 改卸载 / Proton 前缀回收 | `py_modules/tianyi_service.py` 的 `preview_uninstall` / `uninstall_installed_game` / `_can_remove_compatdata_dir` + `py_modules/steam_shortcuts.py` 的 `find_compatdata_dirs` |
| 改任务重试语义 | `py_modules/tianyi_service.py` 的 `retry_task` + `src/index.tsx`（任务行「重试」按钮） |
| 扩展环境诊断 | `scripts/doctor.sh`（只读；新增检查项直接加 `section`/`ok`/`warn`） |
| 改 Steam 多库 / Flatpak 识别 | `py_modules/steam_shortcuts.py` 的 `_steam_root_candidates` / `_steam_library_paths` / `find_compat_user_dir` |
| 改 QAM 面板 UI | `src/index.tsx`（`Content` / `SettingsPage`） |
| 改游戏库橱窗 / 登录桥 | `defaults/tianyi_library_ui/{index.html,app.js,app.css,login_bridge.*}` |
| 改本地 HTTP 接口 | `py_modules/tianyi_http.py`（`setup_routes` 与各 `handle_*`） |
| 加后台任务 / 定时逻辑 | `py_modules/tianyi_service.py` 的 `maintenance_tick` + `main.py` 主循环 |
| 新增单测 | `tests/`（用 `tests/conftest.py` 注入的假 `decky` 模块） |

---

## 10. 提交前检查清单

- [ ] `make test`（或 `.venv/bin/pytest -q`）全绿（当前 220 用例）；
- [ ] 改动运行期/Steam/卸载相关代码后，跑一次 `make doctor` 确认环境自检正常；
- [ ] 改了 `src/` → `pnpm build` 并提交 `dist/index.js(.map)`；
- [ ] 没有新增 `__pycache__` / `*.pyc` / `.DS_Store` / `node_modules` 等产物；
- [ ] 没有把 `defaults/runtime/` 下的大二进制提交进去（在 `.gitignore` 里）；
- [ ] 改 `py_modules/*.py` 后至少重载插件跑通一次"打开面板 + 打开游戏库"两条路径；
- [ ] 文档中的命令 / 路径与实际一致（改了 `Makefile`、`scripts/`、`maintenance_tick` 时同步更新本文件）。
