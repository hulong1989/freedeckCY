# freedeckCY

[![CI](https://github.com/hulong1989/freedeckCY/actions/workflows/ci.yml/badge.svg)](https://github.com/hulong1989/freedeckCY/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hulong1989/freedeckCY)](https://github.com/hulong1989/freedeckCY/releases)
[![License](https://img.shields.io/github/license/hulong1989/freedeckCY)](LICENSE)

> **关于本项目**：freedeckCY 是 [Freedeck](https://github.com/panyiwei-home/Freedeck) 的衍生分支（fork），
> 版本号从 **0.1.0** 起步、当前 **0.27.9**，与原仓库的 0.2–0.3 版本号不连续；上游作者已停止维护。
> 与上游的差异（已对齐 / 我们更强 / 不采纳）见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §13。
>
> 交流 QQ 群：**1136434612**（使用交流 / 问题反馈，加群请备注 freedeckCY）

Steam Deck 的 **Decky Loader 插件**：用天翼云盘 / 百度网盘资源清单，把「下载 → 解压 → 装进 Steam 库」做成 Decky 插件面板里的几个按钮，另带云存档、游玩时长、模拟器与诊断。

> ⚠️ **免责声明**
> 本项目从互联网收集游戏资源分享链接，属于**盗版资源分发**，违反云盘服务条款，也涉及版权风险。仓库中的工程补全只做依赖、打包、缺陷修复、文档与测试，**不建议也不认可**在实际设备上部署使用。请支持正版。

---

## 当前状态

| | 说明 |
|---|---|
| 当前版本 | **0.27.9**（见 [CHANGELOG.md](CHANGELOG.md)） |
| 代码基线 | 从上游 Freedeck 2026-02 的早期版本（0.2）fork；上游已停止维护 |
| 测试 | **555 passed**，覆盖目录、安装、云存档、百度、模拟器、存储、更新等离线逻辑 |
| CI | Python 测试 / UI 构建 / 前端 hooks 作用域检查 / x86_64 与 aarch64 运行时冒烟 |
| 数据目录 | `~/.local/share/freedeckCY/`（`state.json` 权限 0600，目录 0700） |
| 资源目录 | `defaults/tianyi_catalog/freedeckcy_catalog.csv`（7084 条） |
| Web 系统 | 独立项目，不在本仓库、不进入插件包；插件只通过 `catalog_url` 拉取并验签服务器 CSV |

## 核心功能

### 游戏库与下载

- **Decky 原生游戏库**：插件内浏览、搜索、平台/分类筛选、排序、分页、加载更多、已安装页，不依赖网页。
- **游戏库三阶段视觉改版**：响应式封面网格、Hero 推荐区、卡片来源/已安装角标、折叠筛选工具栏、分类货架、海报式详情页、已安装卡片、骨架屏与焦点动效。
- **单/双网盘资源**：
  - 单天翼条目、单百度条目都可直接入目录。
  - 同一游戏同时有天翼和百度时自动合并，详情页让用户选择「天翼云盘 / 百度网盘」。
  - 卡片显示来源：`大小 · 天翼云盘 / 百度网盘`。
- **下载安装链路**：aria2 多连接下载（默认 16 分片）→ 7zz 解压 → 自动写 Steam 快捷方式、Proton 兼容映射与封面。
- **分卷/多包**：识别 `.7z.001` / `.part1.rar` / `.z01+zip` 等常见分卷，全部下完才安装，只解主卷、只注册一次 Steam。
- **断点与恢复**：aria2 运行时元数据落盘；插件重载附着老进程，会话丢失时按文件路径认领 + 原直链换链续传。
- **完整性保护**：按资源清单大小比对落盘结果；异常先隔离并自愈重下。解压前 `7z t` 校验（best-effort），损坏包自动重下一次。
- **解压保护**：等待 `.aria2` 释放、大小稳定后再解压；空文件/HTML 错误页提前拦截。
- **Steam 配置安全**：`shortcuts.vdf` / `config.vdf` 写前留时间戳备份（保留 12 份），无变化不重写。
- **下载管理**：全部暂停/继续、全局限速、失败任务重试；任务进度在插件主页展示。
- **存储位置**：
  - 下载目录支持「内置硬盘 / SD 卡 / 外置存储」一键切换。
  - 内置硬盘固定 `~/Downloads`；外置使用 `<SD>/freedeckCY/downloads`，并显示剩余空间。
  - 安装目录同样支持「内置硬盘 / SD 卡 / 外置存储」切换；内置安装目录固定 `~/Games/freedeckCY`。
- **可选启动文件**：目录 `executable_name` 指定 PC 主 exe / ROM；留空自动识别。
- **免重启刷新**：安装后尝试 SteamClient Refresh，失败则提示重启 Steam。

### 百度网盘

- **扫码登录百度网盘**：Passport `getqrcode → unicast → qrbdusslogin`，保存 `BDUSS/STOKEN/PTOKEN` 及扫码会话 Cookie。
- **登录健康检查**：设置页检查 BDUSS、STOKEN、账号信息、bdstoken、`/FreedeckTmp` 转存目录。
- **分享解析**：`share/verify` 取 `BDCLND` → 打开 `/s/1...` 页面 → `share/list` 100 条/页分页。
- **转存下载**：创建 `/FreedeckTmp` → `share/transfer`（`ondup=overwrite`）→ `filemetas` → dlink 302，安装后清理临时文件。
- **OpenAPI 可选回退**：没有扫码 Cookie 时可配置百度开放平台应用；主链路仍是网页 Cookie。
- **Cookie 存储**：`state.json` 的 `baidu_login`，文件权限 0600；退出登录会清除。

### 目录与更新

- **服务器 CSV 目录**：设置页「检查并更新游戏列表」用 ETag / Last-Modified + SHA256 判断，有变化才下载，提示新增数量。
- **Ed25519 签名**：目录 CSV 与更新清单都验签；验签失败保留旧目录。
- **内置目录服务器**：
  - 默认地址编码内置，设置页不显示真实地址。
  - 设置页留空 → 使用内置服务器。
  - 手动填写 URL → 覆盖内置地址；清空并保存 → 恢复内置。
  - 启动时自动检查目录更新。
- **自有服务器插件更新**：
  - 优先请求目录服务器（Web 1.3.0+）：
    ```text
    GET /api/update/latest
    GET /api/update/latest.json.sig
    GET /api/update/asset/<file>.zip
    ```
  - 版本清单 Ed25519 验签，更新包 SHA256 校验。
  - 服务器不可用时回退 GitHub Release。
  - 手动点「检查更新」强制绕过缓存；自动缓存 2 分钟。
  - 更新包固定保存到内置硬盘 `~/Downloads`，不再跟随 SD 卡下载目录。
- **插件内更新**：插件设置「诊断 → 插件更新」检查、下载、校验；使用 Decky「从文件安装插件」升级。
- **诊断与自检**：检查插件版本、目录、运行时、Steam、SD 卡、网络、百度扫码、任务与日志；一键导出脱敏 zip。

### 云存档、模拟器与时长

- **自动云存档**：Ludusavi 清单（53k+ 游戏）+ gamewatch 进程检测；游戏退出后只上传该游戏，未变化自动跳过。
- **云存档恢复**：冲突探测、覆盖前就地备份；支持 PC Proton 与模拟器存档恢复。
- **模拟器 10 平台**：GBA（mGBA）/ PSP（PPSSPP）/ NDS（melonDS）/ PS1（DuckStation）/ FC、MD（Mesen2）/ 3DS（Azahar）/ PS2（PCSX2）/ PS3（RPCS3）/ Switch（Eden）。
  - 首次安装在线下载官方包，插件包不集成模拟器。
  - 3DS/PS2/PS3 仅 x86_64；aarch64 自动隐藏。
  - BIOS/固件部署：PS1/PS2 BIOS、PS3 固件、3DS system files、Switch keys 由用户自备。
- **PS1 多碟**：多 `.cue/.chd` 自动生成 `freedeckcy-multidisc.m3u`。
- **游玩时长**：监听 Steam 启动/退出事件累计；只在 freedeckCY 管理的游戏详情页展示。

### 工程与安全

- **前端 hooks 作用域检查**：`scripts/check-ui-scope.mjs` 检查 `useMemo/useCallback/useEffect` 依赖数组中的未定义标识符，CI 与 `make check-ui` 执行，防止设置页 `ReferenceError` 再次进包。
- **更新流程拆分**：`py_modules/update_flow.py` 的 `UpdateFlowMixin` 负责服务器/GitHub 更新检查与下载，`TianyiService` 只做编排；后续继续拆分安装/云存档/登录流程。
- **本地 HTTP 服务**：仅监听 `127.0.0.1:59271`，校验 Host/Origin，请求体有上限。
- **Cookie/Token 脱敏**：日志、诊断包、错误信息对 BDUSS/STOKEN/cookie 做脱敏。
- **依赖内置 CA**：`py_modules/cacert.pem` 优先于系统 CA，规避 Decky Python CA 不完整导致的证书错误。
- **CI**：pytest、UI 构建、hooks 作用域检查、x86_64/aarch64 运行时冒烟、目录数据校验、打包冒烟。

## 环境要求

- SteamOS 或其他 Linux（x86_64 / aarch64）
- [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader)
- 天翼云盘账号；百度网盘功能需要百度账号扫码
- 插件自行拉起的外部依赖：`aria2c`、`7zz`、`node`（`make runtime` 准备，打包版已包含）

## 安装

### 方式 A：Release 包（推荐）

Releases 提供带运行时二进制的安装包：

| 包 | 适用设备 |
|---|---|
| `freedeckCY-v0.27.9.zip` | Steam Deck / x86_64 Linux |
| `freedeckCY-v0.27.9-arm64.zip` | DroidDeck / Android ARM64 |

下载后使用 **Decky → 开发者 → 从文件安装插件**，选择对应 zip，重启 Decky Loader。
校验值见 Release 中的 `.sha256` 文件。

### 方式 B：源码打包

```bash
git clone <this-repo> freedeckCY && cd freedeckCY
make runtime              # 下载 aria2c / 7zz / node 到 defaults/runtime/
make package              # 产出 dist-artifacts/freedeckCY-v0.27.9.zip
```

### 方式 C：DroidDeck / ARM64

```bash
make runtime ARCH=aarch64
make package-droiddeck    # 产出 dist-artifacts/freedeckCY-v<version>-arm64.zip
```

在 DroidDeck 的 Decky 菜单里 **Import plugin zip**。路径、Proton、Android 存储细节见 [docs/DROIDDECK.md](docs/DROIDDECK.md)。

## 首次使用

1. 安装插件并重启 Decky Loader。
2. Decky 快捷菜单 → freedeckCY → 设置：
   - 路径 → 下载目录：选择「内置硬盘」或 SD 卡。
   - 路径 → 安装目录：选择内置或外置。
   - 游戏目录：默认使用内置服务器，无需填写。
3. 账号 → 扫码登录天翼云盘 / 百度网盘（按需）。
4. 游戏库 → 选择游戏 → 选择下载源（双网盘时）→ 安装。
5. 设置 → 诊断 → 运行自检 / 导出诊断包。

## 从源码开发

### Python 侧

改 `py_modules/` 后重载 Decky 插件即可，无需构建。

### React 插件面板

```bash
pnpm install
pnpm build          # 产出 dist/index.js
pnpm check:ui       # hooks 依赖作用域检查
```

### 测试与检查

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q          # 或 make test，当前 555 个用例
make check-ui                # 前端 hooks 作用域检查
make doctor                  # 环境诊断（只读）
make package-droiddeck       # ARM64 包
```

CI 同时执行目录数据校验、提交校验、打包冒烟与 x86_64/aarch64 运行时冒烟。

更多细节：

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 架构、时序、接口、问题清单
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — 开发、调试、排障
- [docs/DROIDDECK.md](docs/DROIDDECK.md) — Android / ARM64
- [docs/ROADMAP.md](docs/ROADMAP.md) — 后续计划
- [docs/UPSTREAM_SERVER.md](docs/UPSTREAM_SERVER.md) — 上游服务器依赖的逆向记录

## 常用环境变量

| 变量 | 作用 |
|---|---|
| `FREEDECKCY_CATALOG_CSV_URL` | 覆盖内置目录服务器地址（无头/自动化部署用） |
| `FREEDECKCY_GAME_CATALOG_CSV` | 覆盖资源清单 CSV 路径 |
| `FREEDECKCY_COVER_INDEX_CSV` | 覆盖封面索引 CSV 路径 |
| `FREEDECKCY_CATALOG_JSON` | 改读 NewFreedeck 兼容 JSON（本地路径或 `https://`，默认关闭） |
| `FREEDECKCY_ARIA2_BIN` | 指定 aria2c 路径 |
| `FREEDECKCY_7Z_BIN` | 指定 7zz 路径 |
| `FREEDECKCY_NODE_BIN` | 指定 node 路径 |
| `FREEDECKCY_PROTON_TOOL` | 覆盖 Proton 兼容工具名；`none` 表示不写映射 |
| `FREEDECKCY_STEAM_ROOT` | 覆盖 Steam 根目录（Flatpak / 自定义安装） |
| `FREEDECKCY_STATE_FILE` | `clear_freedeckcy_tasks.sh` 使用的 state.json 路径 |
| `FREEDECKCY_PORT` | `make doctor` 检测的本地服务端口（默认 59271） |
| `FREEDECKCY_TLS_CA_FILE` | 覆盖 TLS CA 文件（默认优先内置 `cacert.pem`） |
| `FREEDECKCY_LUDUSAVI_MANIFEST` | 覆盖 Ludusavi 存档清单路径 |
| `FREEDECKCY_BAIDU_OPENAPI_APP_KEY` | 百度开放平台 App Key（可选回退） |
| `FREEDECKCY_BAIDU_OPENAPI_SECRET_KEY` | 百度开放平台 Secret Key（可选回退） |
| `FREEDECKCY_BAIDU_OPENAPI_REFRESH_TOKEN` | 百度 refresh_token（无头环境） |

模拟器路径变量（`FREEDECKCY_MGBA_BIN`、`FREEDECKCY_PPSSPP_BIN` 等）见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。

## 工作原理（一屏版）

```text
目录：内置/自定义 CSV（Ed25519 验签）
        │
        ▼
解析分享（天翼 / 百度 Cookie）→ 直链 + Cookie
        │
        ▼
aria2c 多连接下载 ──▶ 7zz 解压 ──▶ Steam 快捷方式/Proton/封面
        │
        ▼
Steam 库出现游戏（尝试免重启刷新，失败再重启 Steam）

插件更新：自有服务器 /api/update/latest（签名清单）
        │
        ▼
下载包到 ~/Downloads → SHA256 → Decky 从文件安装
```

云存档走另一条：`Proton 前缀存档目录 → 7z + manifest.json → 云盘 freedeckCYCloudSaves/`，恢复时反向操作并做冲突确认。

## 目录速览

```text
main.py                     Decky 插件入口（RPC 薄转发 + 后台维护循环）
py_modules/
  tianyi_service.py         业务编排：安装/云存档/登录/时长/诊断
  update_flow.py            插件更新检查与下载（UpdateFlowMixin）
  tianyi_client.py          天翼云盘协议、TLS、直链、上传
  baidu_client.py           百度网页协议：verify/列表/转存/直链/清理/健康检查
  baidu_qr.py               百度 Passport 扫码登录（BDUSS/STOKEN/PTOKEN）
  catalog_signature.py      目录/更新清单的 Ed25519 验签
  game_catalog.py           目录解析、平台/分类、provider 合并、封面索引
  storage_options.py        内置硬盘 / SD / 外置存储检测
  tianyi_http.py            本地 HTTP 路由
  tianyi_store.py           state.json 数据模型与读写
  server_manager.py         aiohttp 生命周期、Host/Origin 校验
  aria2_manager.py          aria2 运行时复用、JSON-RPC、续传
  seven_zip_manager.py      7zz 解压/压缩、`7z t` 校验
  emulator_manager.py       模拟器注册表与在线下载（10 平台）
  emulator_setup.py         BIOS/固件部署、portable 配置
  save_manifest.py          Ludusavi 存档匹配
  gamewatch.py              游戏进程检测（自动云存档）
  steam_shortcuts.py        Steam 快捷方式/Proton/封面/备份
  archive_bundle.py         多分卷识别
  cacert.pem                内置 CA bundle
src/index.tsx               Decky 面板（构建产物 dist/）
scripts/check-ui-scope.mjs  前端 hooks 作用域检查
defaults/tianyi_catalog     资源清单（7084 条）与封面索引
defaults/ludusavi           存档清单（53,549 游戏）
submissions/                仓库游戏提交 JSON / schema
backend/*.js                Node 辅助脚本（分享解析兜底、云存档上传）
scripts/                    运行时获取/打包/诊断/目录校验/提交合并
docs/                       架构/开发/路线图/DroidDeck
tests/                      pytest 用例（554 个）
CHANGELOG.md                版本变更
Makefile                    runtime / package / package-droiddeck / test / check-ui / doctor / ...
```

## 安全说明

- 本地服务仅监听 `127.0.0.1`，Host 必须是回环地址；写请求校验 Origin，拒绝跨站。
- 不返回 `Access-Control-Allow-Origin: *`。
- `share_url` 仅接受 `cloud.189.cn` / `*.189.cn` / `pan.baidu.com`。
- `state.json` 含登录 Cookie，目录 0700、文件 0600。
- 更新清单 Ed25519 验签，更新包 SHA256 校验。
- 云存档覆盖前就地备份为 `*.freedeckcy-bak-<时间戳>`。

## 独立 Web 提交系统

玩家投稿网页 + 管理员/审核员后台 + SQLite + 服务器 CSV 是**独立项目**，不在本仓库、也不在插件包内。

插件只负责：

- 通过 `catalog_url` 下载目录 CSV；
- 通过自有服务器更新接口检查插件更新；
- 验签与 SHA256 校验。

Web 1.4.0 起，提交表单支持分别填写天翼云盘链接和百度网盘链接；审核通过生成一条或两条目录记录（`server=t` / `server=b`）。

## 游戏提交（仓库）

两种方式：

1. **Issue 表单**：网页库「提交游戏」，或直接打开 [Issue 表单](https://github.com/hulong1989/freedeckCY/issues/new?template=submit-game.yml)。维护者加 `auto-merge` 标签后立即合并，另有每 6 小时定时任务。
2. **PR**：复制 `submissions/examples/example-pc.json` 到 `submissions/<平台>-<游戏名>.json`，运行 `python scripts/validate_submissions.py` 后提 PR。

只提交分享链接，不要上传游戏文件；字段与规则见 [submissions/README.md](https://github.com/hulong1989/freedeckCY/blob/main/submissions/README.md)。

## 已知问题

- **下载目录不可写**：设置页保存的目录无写权限时，插件会自动回退到 `~/Downloads`，避免“天翼服务未初始化”。

- **云盘接口不稳定**：天翼私有签名、百度网页接口都可能随官方调整失效。
- **百度登录**：Cookie 失效后需要重新扫码；转存受账号空间/接口配额/安全验证影响；临时文件删除失败不影响已下载文件。
- **云存档**：上传/恢复依赖 `node`（打包版已包含）；PS1/PS2 记忆卡、Switch 存档目录仍可能无法按游戏拆分。
- **模拟器**：首次安装需联网下载官方包；PS1/PS2 BIOS、PS3 固件、3DS system files、Switch keys 需自备；3DS/PS2/PS3 仅 x86_64。
- **DroidDeck**：ARM64 适配尚未完整真机验证。
- **更新**：需要 Web 1.3.0+ 发布签名清单；服务器不可用时才回退 GitHub。更新包固定写入 `~/Downloads`。
- **目录合并**：仅「同标题 + 同平台 + 不同网盘」才会合并；同网盘重复条目保持独立。
- **工程债务**：`tianyi_service.py` 仍较大，已完成更新流程拆分，安装/云存档/登录流程继续拆分中。
- **无 i18n**：界面与错误消息全中文硬编码。

完整问题清单与优先级见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 的「问题清单」。

## 许可

[BSD 3-Clause](LICENSE)（来自 Decky 插件模板，保留原始版权声明）。
