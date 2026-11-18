# freedeckCY

[![CI](https://github.com/hulong1989/freedeckCY/actions/workflows/ci.yml/badge.svg)](https://github.com/hulong1989/freedeckCY/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hulong1989/freedeckCY)](https://github.com/hulong1989/freedeckCY/releases)
[![License](https://img.shields.io/github/license/hulong1989/freedeckCY)](LICENSE)

> **关于本项目**：freedeckCY 是 [Freedeck](https://github.com/panyiwei-home/Freedeck) 的衍生分支（fork），
> 版本号从 **0.1.0** 起步、当前 **0.26.29**，与原仓库的 0.2–0.3 版本号不连续；上游作者已停止维护。
> 与上游的差异（已对齐 / 我们更强 / 不采纳）见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §13。
>
> 交流 QQ 群：**1136434612**（使用交流 / 问题反馈，加群请备注 freedeckCY）

Steam Deck 的 **Decky Loader 插件**：用一份天翼云盘资源清单，把"下载 → 解压 → 装进 Steam 库"整条链路做成几个按钮，另带云存档上传/恢复和游玩时长统计。

> ⚠️ **免责声明**
> 本项目从互联网收集游戏资源分享链接，属于**盗版资源分发**，违反天翼云盘服务条款，也涉及版权风险。仓库原作者在 README 中自述"仅限研发测试、24 小时内删除"，但这不改变其法律风险。本仓库的"补全"工作只做**工程完整性**（依赖、打包、缺陷修复、文档、测试），**不建议也不认可**在实际设备上部署使用。请支持正版。

---

## 这个仓库现在是什么状态

| | 说明 |
|---|---|
| 代码基线 | 从上游 Freedeck 2026-02 的早期版本（0.2）fork 而来，版本号从 0.1.0 起步、当前 **0.26.29**（见 [CHANGELOG.md](CHANGELOG.md)） |
| 上游现状 | 作者已停止维护；Releases 里的 v0.5/v0.6 与 NewFreedeck v0.1–0.3 才是功能更全的产品（百度网盘、模拟器、资源池），**这些代码不在本仓库**。第三轮已对照 v0.6 对齐了部分底层能力，差异见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| 本次补全 | 三轮工程补全 + v0.1.1 四件套：① 运行时/打包、P0 修复、接口加固、文档/测试/CI；② 分卷分组、aria2 重启恢复、完整性校验、多库/SD 卡、权限收紧；③ 对照 v0.6：多分卷只解主卷、aria2 运行时复用、直链原地换链、解压前 settle/预检、隔离自愈、Steam 写前备份与去重；④ 卸载回收 Proton 前缀、`7z t` 校验+自动重下、失败任务重试、`make doctor` |
| 数据目录 | `gl/` 是作者手工囤的 CSV 数据，代码**不读取**；实际资源清单是 `defaults/tianyi_catalog/*.csv` |

## 功能

- **扫码登录天翼云盘**（二维码由 Python 侧轮询，Cookie 不经过浏览器）
- **本地游戏库网页**：搜索、封面网格、空间/ProtonDB 提示、安装确认；支持手柄方向键导航
- **下载与安装**：aria2 多连接下载（默认 16 分片）→ 7zz 解压 → 自动写 Steam 快捷方式、Proton 兼容映射与封面
- **分卷/多包资源**：识别 `.7z.001` / `.part1.rar` / `.z01+zip` 等六类分卷，全部下完才安装、只解主卷、只注册一次 Steam
- **重启可恢复**：aria2 运行时元数据落盘，插件重载直接附着老进程不断点；会话丢失时按文件路径认领 + 原直链原地换链续传
- **下载完整性校验**：按资源清单里的文件大小比对落盘结果；不一致先隔离坏文件自愈重下一次，仍失败才标错
- **解压保护**：等 aria2 释放 `.aria2` 控制文件、大小稳定后才解压；空文件/HTML 错误页会被提前拦截
- **Steam 配置安全**：shortcuts.vdf / config.vdf 写前留时间戳备份（保留 12 份），无变化不重写
- **归档校验与自愈**：解压前 `7z t` 测试完整性；失败自动隔离坏包并重下一次，完成后继续安装
- **卸载回收 Proton 前缀**：可选删除 `compatdata/<appid>`，确认前显示占用，默认只删游戏文件
- **失败任务重试**：QAM 任务行一键重试（文件完整则直接重装，不完整则重新取直链）
- **环境诊断**：`make doctor` 一条命令输出运行时/Steam/state/日志/端口/网络（只读）
- **Decky 原生游戏库**：QAM 内直接浏览/搜索/筛选/安装，已安装页可启动/打开目录/卸载；扫描已移至设置 → 安装（自动补 Steam 快捷方式），不再依赖浏览器网页
- **平台与分类筛选**：库页可切换平台（PC / FC / NDS / PSP / GBA / 3DS / PS2 / PS1 / PS3 / MD / Switch）与分类，支持手柄导航
- **浏览 / 分页 / 排序**：封面网格 + 分类 shelf，支持平台/分类/排序 chips、加载更多；封面懒加载 1x，聚焦时底部显示游戏信息条
- **已安装管理**：已安装页签可启动游戏、打开目录、卸载；「扫描已安装」在**设置 → 安装**里，按目录名匹配标题补回列表，Steam 里没有的会自动创建快捷方式（只扫安装目录一层）
- **存储位置**：QAM 自动识别 SD 卡/外置挂载，下载目录、安装目录可一键切到 `<SD>/freedeckCY/{downloads,installed}`，并显示剩余空间；只显示已挂载且可写的外置子挂载，不自动挂载/格式化、不检测 Steam 库同盘
- **模拟器闭环（10 平台）**：GBA（mGBA）/ PSP（PPSSPP）/ NDS（melonDS）/ PS1（DuckStation）/ FC/MD（Mesen2）/ 3DS（Azahar，支持 .cia 自动安装）/ PS2（PCSX2）/ PS3（RPCS3）/ Switch（Eden）；全部首次安装在线下载官方包（不集成进插件包），启动脚本走原生 Linux、不写 Proton
- **自动云存档**：Ludusavi 清单（53k+ 游戏）+ gamewatch 进程检测；游戏退出后只上传该游戏，存档未变化自动跳过；PC + **10 个模拟器平台**的存档都能纳入；支持模拟器存档恢复（自动备份、同机原路径优先）；PSP/PS3/3DS 共享存档会按游戏拆分；QAM 可关闭/关闭模拟器部分
- **PS1 多碟**：安装目录多张 `.cue`/`.chd` 时自动生成 `freedeckcy-multidisc.m3u`，DuckStation 直接启动；同目录多游戏按标题/目录消歧，仍歧义会明确失败
- **百度网盘（对齐 freedeck-go）**：QAM 扫码登录（BDUSS/Cookie，无需 App Key）；分享先 `share/verify` 并带 `BDCLND` 打开；目录 100 条分页；转存前创建 `/FreedeckTmp`、`ondup=overwrite`；异步任务路径按文件名兜底；安装后清理临时文件；登录后补 passport auth 获取 pan STOKEN；OpenAPI 作为可选回退；后端可检查 BDUSS/STOKEN/bdstoken/转存目录健康状态（设置页入口在 v0.26.29 暂隐藏，待修复渲染问题）
- **服务器 CSV 目录**：设置页「检查并更新游戏列表」用 ETag/Last-Modified + SHA256 判断；有变化才下载，提示新增数量，库页显示「最近更新」shelf
- **可选启动文件**：目录 `executable_name` 指定 PC 主 exe / ROM；留空自动识别
- **目录服务器**：不内置真实地址；在设置页填写自己的 `catalog.csv` 地址，启动时自动检查并验证 Ed25519 签名
- **目录更新提示**：自动更新后 QAM 弹窗显示新增游戏
- **插件内更新**：后端支持检查 Release、下载并校验当前架构更新包；设置页入口在 v0.26.29 暂隐藏
- **免重启刷新**：安装后尝试 SteamClient Refresh，失败保留重启 Steam
- **封面本地缓存**：`/api/tianyi/cover-image` 磁盘缓存封面，失败回退直连 CDN
- **下载批量管理**：全部暂停/继续、全局下载限速
- **游戏提交/自动合并**：网页库「提交游戏」打开 GitHub Issue 表单；维护者加 `auto-merge` 标签后 Action 立即合并，另有每 6 小时定时合并任务；也支持 `submissions/*.json` PR
- **原生游戏库兜底**：QAM「游戏库」优先打开原生弹层并显示 UI 版本；如仍看到网页，说明前端未重载
- **诊断与更新**：QAM 设置「诊断」页可运行自检（目录/运行时/Steam/SD/网络/百度扫码/日志）并一键导出脱敏诊断 zip；检查 GitHub 最新 Release
- **全量资源目录**：内置 7084 条资源（来自 v0.6），合并封面索引后 6823 条有封面（96.3%；原始自带 3473 条，索引命中 3311）；分类已清洗（不含平台名），可用 `scripts/merge_v06_catalog.py` 复现/更新
- **无作者服务器依赖**：目录/封面/模拟器运行时均为本地或官方源；NewFreedeck 的 `panyiwei.xyz` 硬依赖已逆向并记录替代方案（[docs/UPSTREAM_SERVER.md](docs/UPSTREAM_SERVER.md)），兼容 JSON 快照在 [catalog-json/](catalog-json/)
- **可选 JSON 目录**：`FREEDECKCY_CATALOG_JSON` 支持本地路径或 `https://` URL（默认关闭，失败回退 CSV）
- **数据体检**：`make validate-catalog` 检查重复 ID / 非法链接 / 空标题 / 分类混平台名，并统计封面覆盖率、平台分布与资源总大小（约 39 TB）；CI 每次都会跑
- **封面索引与缓存**：内置 `cover_index.csv` 3470 行（可用 `FREEDECKCY_COVER_INDEX_CSV` 覆盖）；解析过的封面落盘缓存（正缓存 7 天 / 负缓存 30 分钟），重启后不再重复请求
- **DroidDeck（Android/ARM64）适配**：ARM64 运行时、ARM Proton 工具自动解析、双 Steam 根、`make package-droiddeck` 出 arm64 包，详见 [docs/DROIDDECK.md](docs/DROIDDECK.md)
- **多库 / SD 卡 / Flatpak**：扫描 `libraryfolders.vdf`，Proton 前缀不只在主库找（DroidDeck 双 Steam 根也覆盖）
- **云存档**：扫描 Proton 前缀里的存档目录，打包 `7z + manifest.json` 上传到自己的网盘；恢复时做冲突探测，覆盖前就地备份
- **游玩时长**：监听 Steam 启动/退出事件累计时长；只在 freedeckCY 安装的游戏详情页展示（含 HowLongToBeat 主线/总时长），不改 Steam 原有游戏

## 环境要求

- SteamOS 或其他 Linux（x86_64 / aarch64）
- [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader)
- 一个可正常登录的天翼云盘账号（部分分享需要转存/提取码权限）
- 由插件自行拉起的外部依赖：`aria2c`、`7zz`、`node`（见下文，`make runtime` 会准备）

## 安装

### 方式 A：用打包好的 zip

```bash
git clone <this-repo> freedeckCY && cd freedeckCY
make runtime     # 下载 aria2c / 7zz / node 到 defaults/runtime/（按组件与架构分目录）
make package     # 产出 dist-artifacts/freedeckCY-v0.26.29.zip
```

把 zip 传到 Steam Deck，用 **Decky → 开发者 → 从文件安装插件** 选择它，然后重启插件加载器。

### 方式 C：DroidDeck（Android / ARM64）

DroidDeck 支持导入 Decky 插件，但手机是 ARM64，需要 arm64 包：

```bash
make runtime ARCH=aarch64
make package-droiddeck    # 产出 dist-artifacts/freedeckCY-v<version>-arm64.zip
```

在 DroidDeck 的 Decky 菜单里 **Import plugin zip** 选择它。路径、Proton 工具、双 Steam 客户端等细节见 [docs/DROIDDECK.md](docs/DROIDDECK.md)。

### 方式 B：直接拿 Release 包

本仓库 [Releases](https://github.com/hulong1989/freedeckCY/releases) 提供已带运行时二进制的安装包：

| 包 | 适用设备 |
|---|---|
| `freedeckCY-v0.26.29.zip` | Steam Deck / x86_64 Linux |
| `freedeckCY-v0.26.29-arm64.zip` | DroidDeck / Android ARM64 |

下载后用 **Decky → 开发者 → 从文件安装插件** 选择对应 zip 即可；校验值见 Release 里的 `.sha256` 文件。

## 从源码开发

```bash
# Python 侧：改 py_modules/ 后重载 Decky 插件即可，无需构建
# React 侧（QAM 面板）：改动 src/ 后需要打包
pnpm install
pnpm build          # 产出 dist/index.js

# Vue 游戏库页面：免构建，直接改 defaults/tianyi_library_ui/
```

测试与检查：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q          # 或 make test（用例数以输出为准，当前 541）
make doctor                  # 环境诊断：运行时/Steam/state/日志/端口/网络（只读）
make package-droiddeck       # ARM64 包（DroidDeck/Android 用）
```

更多细节（模块职责、调试、故障排查）见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)；
上游 `panyiwei.xyz` 依赖的逆向记录与自托管替代方案见 [docs/UPSTREAM_SERVER.md](docs/UPSTREAM_SERVER.md)；
后续可做项见 [docs/ROADMAP.md](docs/ROADMAP.md)。

常用环境变量：

| 变量 | 作用 |
|---|---|
| `FREEDECKCY_ARIA2_BIN` | 指定 aria2c 路径（默认用 `defaults/runtime/aria2/<arch>/aria2c`） |
| `FREEDECKCY_7Z_BIN` | 指定 7zz 路径 |
| `FREEDECKCY_NODE_BIN` | 指定 node 路径 |
| `FREEDECKCY_PROTON_TOOL` | 覆盖 Proton 兼容工具名；`none` 表示不写映射（DroidDeck 默认 `droiddeck-proton-arm64`） |
| `FREEDECKCY_MGBA_BIN` | 覆盖 mGBA 可执行文件/AppImage 路径（默认用已下载/系统版本） |
| `FREEDECKCY_PPSSPP_BIN` | 覆盖 PPSSPP 路径（默认用已下载/系统版本） |
| `FREEDECKCY_MELONDS_BIN` | 覆盖 melonDS 路径（默认用已下载/系统版本） |
| `FREEDECKCY_LUDUSAVI_MANIFEST` | 覆盖 Ludusavi 清单 JSON 路径（默认 `defaults/ludusavi/manifest.json.gz`） |
| `FREEDECKCY_DUCKSTATION_BIN` | 覆盖 DuckStation 路径（默认用已下载/系统版本） |
| `FREEDECKCY_MESEN_BIN` | 覆盖 Mesen2 路径（默认用已下载/系统版本） |
| `FREEDECKCY_AZAHAR_BIN` | 覆盖 Azahar 路径（3DS，仅 x86_64） |
| `FREEDECKCY_PCSX2_BIN` | 覆盖 PCSX2 路径（PS2，仅 x86_64） |
| `FREEDECKCY_RPCS3_BIN` | 覆盖 RPCS3 路径（PS3，仅 x86_64） |
| `FREEDECKCY_EDEN_BIN` | 覆盖 Eden 路径（Switch） |
| `FREEDECKCY_BAIDU_OPENAPI_APP_KEY` | 百度开放平台 App Key（也可在 QAM 填） |
| `FREEDECKCY_BAIDU_OPENAPI_SECRET_KEY` | 百度开放平台 Secret Key |
| `FREEDECKCY_BAIDU_OPENAPI_REFRESH_TOKEN` | 百度 refresh_token（无头/容器环境） |
| `FREEDECKCY_CATALOG_JSON` | 运行时改读 NewFreedeck 兼容 JSON：本地路径或 `https://` URL；远程缓存 6 小时，失败回退旧缓存/CSV |
| `FREEDECKCY_STEAM_ROOT` | 覆盖 Steam 根目录（Flatpak/自定义安装时用） |
| `FREEDECKCY_STATE_FILE` | `clear_freedeckcy_tasks.sh` 使用的 state.json 路径 |
| `FREEDECKCY_GAME_CATALOG_CSV` | 覆盖资源清单 CSV 路径 |
| `FREEDECKCY_COVER_INDEX_CSV` | 覆盖封面索引 CSV 路径（仓库已内置 3470 行） |
| `FREEDECKCY_PORT` | `make doctor` 检测本地服务端口（默认 59271） |

## 工作原理（一屏版）

```
CSV 资源清单 ──▶ 分享解析（天翼云盘开放接口 + Node 兜底）
                     │
                     ▼
             直链（MD5 签名）+ Cookie ──▶ aria2c 多连接下载
                     │
                     ▼
            7zz 解压到安装目录 ──▶ 写 shortcuts.vdf / config.vdf / grid 封面
                     │
                     ▼
               Steam 库里出现游戏（尝试免重启刷新，失败再重启 Steam）
```

云存档走另一条：`Proton 前缀存档目录 → 7z + manifest.json → 天翼云盘 freedeckCYCloudSaves/`，恢复时反向操作并做冲突确认。

完整架构、两条链路的时序图、天翼接口逆向要点、`state.json` 数据结构都在 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 目录速览

```
main.py                     Decky 插件入口（RPC 薄转发 + 后台维护循环）
py_modules/
  tianyi_service.py         业务内核：下载/安装（分卷/自愈/重试）/卸载/云存档/登录/时长
  tianyi_client.py          天翼云盘协议：分享解析、直链、token、上传
  baidu_client.py           百度网盘网页协议：分享 verify/列表/转存/直链/临时文件清理
  baidu_qr.py               百度 Passport 扫码登录（BDUSS/STOKEN）
  catalog_signature.py      目录 CSV 的 Ed25519 公钥验签
  tianyi_http.py            本地 HTTP 路由（41 条：3 页面/静态 + 38 REST）
  tianyi_store.py           state.json 数据模型与读写
  server_manager.py         aiohttp 生命周期、Host/Origin 校验、设置持久化
  aria2_manager.py          aria2 运行时复用（meta+flock）+ JSON-RPC + changeUri
  seven_zip_manager.py      7zz 解压/压缩 + `7z t` 校验
  emulator_manager.py       通用模拟器注册表（10 平台：GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch；架构白名单/按需下载/解包/ROM/启动脚本）
  emulator_setup.py         BIOS/固件/keys 部署与 portable 配置（压缩包解压、DuckStation/PCSX2/Eden/RPCS3 等）
  save_manifest.py          Ludusavi 存档清单匹配与 Proton 路径解析
  gamewatch.py              游戏进程检测（自动云存档触发）
  steam_shortcuts.py        快捷方式/Proton/封面/写前备份/compatdata 定位
  game_catalog.py           CSV 资源目录/平台字段/分类清洗/封面索引
  archive_bundle.py         多分卷归档识别（.7z.001 / .part1.rar / .z01+zip ...）
src/index.tsx               QAM 面板（React，构建产物在 dist/）
defaults/tianyi_library_ui  本地游戏库页面（Vue 3，免构建：浏览/分页/排序/已安装/诊断）
defaults/tianyi_catalog     资源清单（freedeckcy_catalog.csv 7084 条 + 旧目录回退）与封面索引
defaults/ludusavi           存档清单（53,549 游戏，MIT，gzip）
submissions/                仓库游戏提交（JSON 示例/schema/合并说明）
backend/*.js                Node 辅助脚本（分享解析兜底、云盘上传）
scripts/                    运行时获取（aria2/7zz/node）/ 打包（含 ARM64）/ 诊断 / 目录合并 / 目录体检 / 分类清洗 / 远程目录 / 清单转换
docs/                       架构 / 开发 / 路线图（ARCHITECTURE / DEVELOPMENT / ROADMAP）
catalog-json/               NewFreedeck 兼容目录 JSON + schema（可直接读/自托管）
tests/                      pytest 用例（541 个）
CHANGELOG.md                版本变更记录
Makefile                    构建入口：runtime / catalog-json / ludusavi-manifest / package / package-droiddeck / test / doctor / validate-catalog / validate-submissions / normalize-catalog / clean
```

## 安全说明

本次补全对本地服务做了加固：

- 仅监听 `127.0.0.1`，并校验 `Host` 必须是回环地址（防 DNS rebinding）
- 写请求若带 `Origin`，必须是本机页面；`Sec-Fetch-Site: cross-site` 直接拒绝
- 不再返回 `Access-Control-Allow-Origin: *`；本地 API 请求体上限从 1GB 收到 16MB
- `share_url` 只接受 `cloud.189.cn` / `*.189.cn` / `pan.baidu.com`，避免被本地页面塞入任意地址
- `state.json` 含登录 cookie，落盘后目录 0700、文件 0600

云存档恢复覆盖同名文件前，会把原文件/目录就地改名为 `*.freedeckcy-bak-<YYYYmmdd_HHMMSS>`，失败可手工找回。

## 独立 Web 提交系统

玩家网页投稿 + 管理员/审核员后台 + SQLite + 服务器 CSV 的独立项目不在本仓库、也不在插件包内；插件只负责通过 `catalog_url` 下载并验签服务器 CSV。

## 游戏提交（仓库）

两种方式，字段与原版资源池投稿一致：

1. **Issue 表单**：网页库右上角「提交游戏」，或直接打开 [Issue 表单](https://github.com/hulong1989/freedeckCY/issues/new?template=submit-game.yml)。维护者添加 `auto-merge` 标签后立即合并，另有每 6 小时定时合并。
2. **PR**：复制 `submissions/examples/example-pc.json` 到 `submissions/<平台>-<游戏名>.json`，本地跑 `python scripts/validate_submissions.py`，然后提 PR。CI 通过后维护者执行 `python scripts/merge_submissions.py --apply` 合并。

只提交分享链接，不要上传游戏文件；规则/字段/命令见 [submissions/README.md](https://github.com/hulong1989/freedeckCY/blob/main/submissions/README.md)。

## 已知问题

- **Decky 更新后仍看到网页游戏库**：v0.23.0 起游戏库优先打开原生 modal，v0.24.0 增加返回/Steam 库按钮；页面顶部显示 `原生 UI · v0.26.29`，QAM 主页显示 `QAM 原生 UI v0.26.29`。如果看不到版本标识或仍打开网页，说明前端 `dist` 未更新，重装/重载插件（必要时重启 Decky Loader）后再试。

完整清单（含已修复/未修复与 P0/P1/P2 分级）见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 的「问题清单」，后续计划见 [docs/ROADMAP.md](docs/ROADMAP.md)。简要版：

- 天翼云盘用的是未公开接口与私有签名，官方一改就可能整体失效
- `config.vdf` 采用文本改写，运行中的 Steam 可能回写覆盖
- 全中文硬编码，无 i18n
- 云存档的上传/恢复仍依赖 `node`（`make runtime` 会准备；未执行则该功能不可用）
- 下载完整性做「大小 + 文件头 + `7z t`」，但没有哈希校验；7z 不可用时自动跳过校验（best-effort）
- **模拟器已接入 10 个平台（PC / FC / NDS / PSP / GBA / 3DS / PS2 / PS1 / PS3 / MD / Switch）**：全部首次安装在线下载官方包，**插件包不集成模拟器**；3DS/PS2/PS3 只有 x86_64 官方包，DroidDeck（aarch64）会自动隐藏这三个平台
- **3DS / SteamOS**：SteamOS 上 3DS 优先走官方 Flatpak（首次安装自动装，约数百 MB 运行时），避免官方 AppImage 在 Steam Deck 上的兼容问题；无 Flatpak 环境回退 AppImage
- **模拟器边界**：所有平台首次安装都需联网下载官方包（约 15–99MB）；PS1/PS2 BIOS、PS3 固件、3DS system files、Switch keys/固件都要自备，放到 `~/.local/share/freedeckCY/bios/<platform>/`（支持 zip/7z 压缩包，安装时自动解压部署）；3DS/PS2/PS3 仅 x86_64；解包目录会多占空间；ARM64 未真机验证
- **百度网盘边界**：默认扫码登录（BDUSS/Cookie，网页版接口，非官方 OpenAPI）；Cookie 失效需重新扫码；OpenAPI 仅作为需要开发者资质时的可选回退；转存受百度账号空间/接口配额限制；删除临时文件可能触发百度安全验证，失败不影响已下载文件
- **模拟器云存档边界**：PS1/PS2 单片记忆卡、Switch 存档目录仍无法按游戏拆分，恢复会整卡覆盖（需确认）；3DS/Switch 整目录可能较大，可在 QAM 关闭「包含模拟器存档」
- **自动云存档边界**：PC 存档覆盖 Ludusavi 清单/Proton 前缀；模拟器存档 v0.15.0 起支持上传、v0.16.0 起支持恢复（见上一条）；首次自动上传依赖清单匹配/登录态
- **DroidDeck 适配未真机验证**：FEX / ARM Proton / Android 存储映射可能有差异，排障见 [docs/DROIDDECK.md](docs/DROIDDECK.md)
- **更新检查依赖 GitHub API**：未认证限流 60 次/小时/IP，失败只提示、不缓存失败结果；成功结果缓存 1 小时
- 分卷识别只覆盖常见 6 类命名，冷门命名会被当成普通文件
- `tianyi_service.py` 仍是单文件巨型类，长期维护成本高

## 许可

[BSD 3-Clause](LICENSE)（来自 Decky 插件模板，保留原始版权声明）。
