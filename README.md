# freedeckCY

[![CI](https://github.com/hulong1989/freedeckCY/actions/workflows/ci.yml/badge.svg)](https://github.com/hulong1989/freedeckCY/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hulong1989/freedeckCY)](https://github.com/hulong1989/freedeckCY/releases)
[![License](https://img.shields.io/github/license/hulong1989/freedeckCY)](LICENSE)

> **关于本项目**：freedeckCY 是 [Freedeck](https://github.com/panyiwei-home/Freedeck) 的衍生分支（fork），
> 版本号从 **0.1.0** 起步、当前 **0.6.0**，与原仓库的 0.2–0.3 版本号不连续；上游作者已停止维护。
> 与上游的差异（已对齐 / 我们更强 / 不采纳）见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §13。

Steam Deck 的 **Decky Loader 插件**：用一份天翼云盘资源清单，把"下载 → 解压 → 装进 Steam 库"整条链路做成几个按钮，另带云存档上传/恢复和游玩时长统计。

> ⚠️ **免责声明**
> 本项目从互联网收集游戏资源分享链接，属于**盗版资源分发**，违反天翼云盘服务条款，也涉及版权风险。仓库原作者在 README 中自述"仅限研发测试、24 小时内删除"，但这不改变其法律风险。本仓库的"补全"工作只做**工程完整性**（依赖、打包、缺陷修复、文档、测试），**不建议也不认可**在实际设备上部署使用。请支持正版。

---

## 这个仓库现在是什么状态

| | 说明 |
|---|---|
| 代码基线 | 从上游 Freedeck 2026-02 的早期版本（0.2）fork 而来，版本号从 0.1.0 起步、当前 **0.6.0**（见 [CHANGELOG.md](CHANGELOG.md)） |
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
- **平台与分类筛选**：库页可切换平台（PC / FC / NDS / PSP / GBA / 3DS / PS2 / PS1 / PS3 / MD / Switch）与分类，支持手柄导航
- **浏览 / 分页 / 排序**：打开库页即浏览全部资源，按平台/分类筛选，支持排序与 L1/R1 翻页
- **已安装管理**：已安装页签可启动游戏、打开目录、卸载（`steam://rungameid`）
- **GBA 模拟器闭环**：内置 mGBA（x64/arm64 AppImage），GBA 资源可安装/启动；不写 Proton 映射
- **诊断与更新**：一键导出脱敏诊断 zip；检查 GitHub 最新 Release
- **全量资源目录**：内置 7084 条资源（来自 v0.6），合并封面索引后 6823 条有封面（96.3%；原始自带 3473 条，索引命中 3311）；分类已清洗（不含平台名），可用 `scripts/merge_v06_catalog.py` 复现/更新
- **数据体检**：`make validate-catalog` 检查重复 ID / 非法链接 / 空标题 / 分类混平台名，并统计封面覆盖率、平台分布与资源总大小（约 39 TB）；CI 每次都会跑
- **封面索引与缓存**：内置 `cover_index.csv` 3470 行（可用 `FREEDECKCY_COVER_INDEX_CSV` 覆盖）；解析过的封面落盘缓存（正缓存 7 天 / 负缓存 30 分钟），重启后不再重复请求
- **DroidDeck（Android/ARM64）适配**：ARM64 运行时、ARM Proton 工具自动解析、双 Steam 根、`make package-droiddeck` 出 arm64 包，详见 [docs/DROIDDECK.md](docs/DROIDDECK.md)
- **多库 / SD 卡 / Flatpak**：扫描 `libraryfolders.vdf`，Proton 前缀不只在主库找（DroidDeck 双 Steam 根也覆盖）
- **云存档**：扫描 Proton 前缀里的存档目录，打包 `7z + manifest.json` 上传到自己的网盘；恢复时做冲突探测，覆盖前就地备份
- **游玩时长**：监听 Steam 启动/退出事件累计时长，并在游戏库详情页展示（含 HowLongToBeat 的主线/总时长）

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
make emulator-runtime   # 下载 mGBA AppImage（GBA 安装后启动用）
make package     # 产出 dist-artifacts/freedeckCY-v0.6.0.zip
```

把 zip 传到 Steam Deck，用 **Decky → 开发者 → 从文件安装插件** 选择它，然后重启插件加载器。

### 方式 C：DroidDeck（Android / ARM64）

DroidDeck 支持导入 Decky 插件，但手机是 ARM64，需要 arm64 包：

```bash
make runtime ARCH=aarch64
make emulator-runtime ARCH=aarch64
make package-droiddeck    # 产出 dist-artifacts/freedeckCY-v<version>-arm64.zip
```

在 DroidDeck 的 Decky 菜单里 **Import plugin zip** 选择它。路径、Proton 工具、双 Steam 客户端等细节见 [docs/DROIDDECK.md](docs/DROIDDECK.md)。

### 方式 B：直接拿 Release 包

本仓库 [Releases](https://github.com/hulong1989/freedeckCY/releases) 提供已带运行时二进制的安装包：

| 包 | 适用设备 |
|---|---|
| `freedeckCY-v0.6.0.zip` | Steam Deck / x86_64 Linux |
| `freedeckCY-v0.6.0-arm64.zip` | DroidDeck / Android ARM64 |

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
.venv/bin/pytest -q          # 或 make test（用例数以输出为准，当前 260）
make doctor                  # 环境诊断：运行时/Steam/state/日志/端口/网络（只读）
make package-droiddeck       # ARM64 包（DroidDeck/Android 用）
```

更多细节（模块职责、调试、故障排查）见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)；
后续可做项见 [docs/ROADMAP.md](docs/ROADMAP.md)。

常用环境变量：

| 变量 | 作用 |
|---|---|
| `FREEDECKCY_ARIA2_BIN` | 指定 aria2c 路径（默认用 `defaults/runtime/aria2/<arch>/aria2c`） |
| `FREEDECKCY_7Z_BIN` | 指定 7zz 路径 |
| `FREEDECKCY_NODE_BIN` | 指定 node 路径 |
| `FREEDECKCY_PROTON_TOOL` | 覆盖 Proton 兼容工具名；`none` 表示不写映射（DroidDeck 默认 `droiddeck-proton-arm64`） |
| `FREEDECKCY_MGBA_BIN` | 覆盖 mGBA 可执行文件/AppImage 路径（默认用内置 AppImage） |
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
               Steam 库里出现游戏（需重启 Steam）
```

云存档走另一条：`Proton 前缀存档目录 → 7z + manifest.json → 天翼云盘 freedeckCYCloudSaves/`，恢复时反向操作并做冲突确认。

完整架构、两条链路的时序图、天翼接口逆向要点、`state.json` 数据结构都在 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 目录速览

```
main.py                     Decky 插件入口（RPC 薄转发 + 后台维护循环）
py_modules/
  tianyi_service.py         业务内核：下载/安装（分卷/自愈/重试）/卸载/云存档/登录/时长
  tianyi_client.py          天翼云盘协议：分享解析、直链、token、上传
  tianyi_http.py            本地 HTTP 路由（41 条：3 页面/静态 + 38 REST）
  tianyi_store.py           state.json 数据模型与读写
  server_manager.py         aiohttp 生命周期、Host/Origin 校验、设置持久化
  aria2_manager.py          aria2 运行时复用（meta+flock）+ JSON-RPC + changeUri
  seven_zip_manager.py      7zz 解压/压缩 + `7z t` 校验
  emulator_manager.py       mGBA 运行时管理（AppImage 解包/ROM 查找/启动脚本）
  steam_shortcuts.py        快捷方式/Proton/封面/写前备份/compatdata 定位
  game_catalog.py           CSV 资源目录/平台字段/分类清洗/封面索引
  archive_bundle.py         多分卷归档识别（.7z.001 / .part1.rar / .z01+zip ...）
src/index.tsx               QAM 面板（React，构建产物在 dist/）
defaults/tianyi_library_ui  本地游戏库页面（Vue 3，免构建：浏览/分页/排序/已安装/诊断）
defaults/tianyi_catalog     资源清单（freedeckcy_catalog.csv 7084 条 + 旧目录回退）与封面索引
backend/*.js                Node 辅助脚本（分享解析兜底、云盘上传）
scripts/                    运行时获取（含 mGBA）/ 打包（含 ARM64）/ 诊断 / 目录合并 / 目录体检 / 分类清洗
docs/                       架构 / 开发 / 路线图（ARCHITECTURE / DEVELOPMENT / ROADMAP）
tests/                      pytest 用例（260 个）
CHANGELOG.md                版本变更记录
Makefile                    构建入口：runtime / emulator-runtime / package / package-droiddeck / test / doctor / validate-catalog / normalize-catalog / clean
```

## 安全说明

本次补全对本地服务做了加固：

- 仅监听 `127.0.0.1`，并校验 `Host` 必须是回环地址（防 DNS rebinding）
- 写请求若带 `Origin`，必须是本机页面；`Sec-Fetch-Site: cross-site` 直接拒绝
- 不再返回 `Access-Control-Allow-Origin: *`；本地 API 请求体上限从 1GB 收到 16MB
- `share_url` 只接受 `cloud.189.cn` / `*.189.cn`，避免被本地页面塞入任意地址
- `state.json` 含登录 cookie，落盘后目录 0700、文件 0600

云存档恢复覆盖同名文件前，会把原文件/目录就地改名为 `*.freedeckcy-bak-<YYYYmmdd_HHMMSS>`，失败可手工找回。

## 已知问题

完整清单（含已修复/未修复与 P0/P1/P2 分级）见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 的「问题清单」，后续计划见 [docs/ROADMAP.md](docs/ROADMAP.md)。简要版：

- 天翼云盘用的是未公开接口与私有签名，官方一改就可能整体失效
- `config.vdf` 采用文本改写，运行中的 Steam 可能回写覆盖
- 全中文硬编码，无 i18n
- 云存档的上传/恢复仍依赖 `node`（`make runtime` 会准备；未执行则该功能不可用）
- 下载完整性做「大小 + 文件头 + `7z t`」，但没有哈希校验；7z 不可用时自动跳过校验（best-effort）
- **GBA 已可安装/启动**（mGBA）；其余模拟器平台（FC/NDS/PSP/3DS/PS2/PS1/PS3/MD/Switch）仍只可浏览、不可安装
- **GBA 闭环的边界**：只识别 `.gba`（不含 BIOS/存档管理）；首次使用内置 AppImage 会解包到 `~/.local/share/freedeckCY/emulators/`，多占一份空间；ARM64 未真机验证
- **DroidDeck 适配未真机验证**：FEX / ARM Proton / Android 存储映射可能有差异，排障见 [docs/DROIDDECK.md](docs/DROIDDECK.md)
- **更新检查依赖 GitHub API**：未认证限流 60 次/小时/IP，失败只提示、不缓存失败结果；成功结果缓存 1 小时
- 分卷识别只覆盖常见 6 类命名，冷门命名会被当成普通文件
- `tianyi_service.py` 仍是单文件巨型类，长期维护成本高

## 许可

[BSD 3-Clause](LICENSE)（来自 Decky 插件模板，保留原始版权声明）。
