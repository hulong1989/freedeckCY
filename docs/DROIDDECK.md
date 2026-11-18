# 在 DroidDeck 上使用 freedeckCY

> [English](DROIDDECK.en.md) | 中文

[DroidDeck](https://github.com/Droid-Deck/DroidDeck) 是在 Android 手机上运行 SteamOS 运行时的开源项目：它自带 Linux 桌面、Steam 游戏模式，并支持 **[Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) 插件**。freedeckCY 从 v0.4.0 起适配 DroidDeck，v0.6.0 起 GBA 模拟器闭环、v0.7.0 起通用模拟器注册表（GBA/PSP/NDS）、v0.8.0 起 Ludusavi + gamewatch 自动云存档、v0.9.0 起 PS1/FC/MD、v0.10.0 起全部模拟器改为在线下载、v0.11.0 起 10 平台 + 架构能力矩阵（DroidDeck 自动隐藏 3DS/PS2/PS3）、v0.12.0 起安装后自动部署 BIOS/固件并写 portable 配置、v0.13.0 起网页库支持仓库游戏提交（Issue/PR）、v0.14.0 起百度网盘（官方 OpenAPI）、v0.14.1 起 3DS（Azahar）SteamOS 兼容修复（优先官方 Flatpak，无 Flatpak 回退 AppImage）、v0.15.0 起模拟器存档纳入云存档上传、v0.16.0 起模拟器存档恢复 + PSP/PS3/3DS 按游戏拆分 + PS1 多碟 m3u、v0.17.0 起百度网盘扫码登录（BDUSS/Cookie 主链路，OpenAPI 可选回退）、v0.18.0 起扫描已安装游戏 + 百度扫码错误诊断、v0.19.0 起下载/安装目录支持 SD 卡/外置存储选择、v0.20.0 起 Decky 原生游戏库（不再依赖网页）、v0.21.0 起扫描已安装移到设置并自动补 Steam 快捷方式、v0.22.0 起诊断自检 + 一键诊断包、v0.23.0 起原生库 modal 兜底/版本标识 + 百度扫码超时、v0.24.0 起原生库返回/关闭修复、v0.25.0 起 Steam 原有游戏不再显示插件时长块、v0.26.x 做架构/稳定性修复、v0.27.0–v0.27.20 做原生游戏库视觉重构与 Steam Deck 手柄/触控板适配（DroidDeck 同样使用 Decky 焦点系统，触控/手柄逻辑可复用）。本文对应 **v0.28.7**，是安装与排障说明。

> 适配基于 DroidDeck 的源码与 ARM64 运行时结构，**尚未在真机上完整验证**。遇到问题请按文末“排障”收集日志。

## 1. 与 Steam Deck 的差异

| 项 | Steam Deck | DroidDeck |
|---|---|---|
| CPU 架构 | x86_64 | **aarch64（ARM64）** |
| 运行时 | SteamOS | proot Linux，HOME 通常是 `/root` |
| Steam 根 | `~/.steam/steam` / `~/.local/share/Steam` | 同上；x64 Steam 客户端另有 `~/.droiddeck-x64/.local/share/Steam` |
| Proton | `proton_experimental` 等 Valve 工具 | **ARM 工具名** `droiddeck-proton-arm64` / `droiddeck-proton-11-arm64` |
| 存储 | SSD/SD 卡 | Android 内部存储，路径在 proot 内映射 |

freedeckCY 的处理方式：

- 运行时（aria2c、7zz、node）按 `platform.machine()` 选择 `defaults/runtime/<arch>/`，ARM 设备用 `aarch64`。
- 检测到 DroidDeck 标记（`~/.droiddeck-x64`、`~/.droiddeck-decky-enabled`、`<Steam>/package/droiddeck-installed`）时，Proton 映射自动改用 `droiddeck-proton-arm64`；若 `config.vdf` 里已出现 `droiddeck-proton-11-arm64` 则优先用它。
- 若 DroidDeck 的 x64 Steam 客户端正在运行（`steam.pid` 存在），优先把快捷方式写到它的 `~/.droiddeck-x64/.local/share/Steam`，否则回退标准路径。
- GBA 闭环（v0.6.0 起）使用 **mGBA arm64 AppImage**：v0.10.0 起**不再随包内置**，首次安装 GBA 时自动从官方 release 下载，再用 `--appimage-extract` 解包到 `~/.local/share/freedeckCY/emulators/gba/aarch64/squashfs-root`（GBA 兼容旧 `emulators/aarch64/`；**不依赖 FUSE**，proot 环境可用）；Steam 快捷方式的 Exe 是生成的 `launch-freedeckcy.sh`，**不写 Proton 映射**（原生 Linux 启动）。
- 模拟器存档恢复（v0.16.0）：云存档恢复不再只支持 PC——模拟器存档按 `restore_roots` 白名单恢复（同机优先原父目录、跨设备落到平台第一个根），覆盖前自动生成 `*.freedeckcy-bak-<时间戳>` 备份；冲突需要确认。**aarch64 上可用 GBA/PSP/NDS/PS1/FC/MD 的恢复/拆分（3DS/PS2/PS3 平台本身隐藏）**；PSP（PARAM.SFO）、3DS（NCSD title id）拆分在 ARM 上同样适用（3DS 平台不可见）；PS1 多碟在 aarch64 上也会生成/优先 `.m3u`。
- 模拟器存档上传（v0.15.0）：QAM「云存档上传 → 包含模拟器存档」（`cloud_save_include_emulators`，默认开）控制是否上传模拟器存档；发现路径基于 **proot 内 HOME**（`~/.local/share/...`、`~/.config/...`，如 `~/.local/share/ppsspp/PSP/SAVEDATA`、`~/.local/share/azahar-emu/sdmc`、`~/.local/share/eden/nand/user/save`）。**Flatpak 的 `~/.var/app/...` 路径在 Android/proot 下不适用**（DroidDeck 没有 SteamOS Flatpak 环境），不会被误用；GBA/FC/MD/NDS 按 ROM 同名找单游戏存档，PSP/PS1/PS2/3DS/PS3/Switch 上传共享记忆卡/标题目录；**v0.16.0 起支持恢复**（见上一条，白名单目标 + 备份 + 冲突确认）。
- 3DS（Azahar，v0.14.1）：SteamOS 3.9.5 上优先官方 Flathub Flatpak `org.azahar_emu.Azahar`（AppImage 有上游 #127/#953 兼容问题）；**DroidDeck/aarch64 没有 3DS 官方 arm64 包，目录里仍不显示 3DS**（架构白名单，见 §9.8）。如果设备能跑 x86_64 且装有 flatpak，则自动用 Flatpak、失败回退 AppImage；3DS 启动脚本会强制 XWayland（`QT_QPA_PLATFORM=xcb`/`SDL_VIDEODRIVER=x11`）；system files 放 `~/.local/share/freedeckCY/bios/3ds/sysdata/`，会部署到 azahar/citra 与 `~/.var/app/org.azahar_emu.Azahar/data/{azahar,azahar-emu}/sysdata`。已有 3DS 快捷方式由后台自动重写，无需重装。
- 库页时长隔离（v0.25.0）：Steam 原有游戏详情页不再出现 freedeckCY 的「已玩/主线/总时长」块——前端只在 `managed===true` 时渲染，未匹配直接 `return null`；后端先按 AppID、再按标题匹配插件安装记录，未匹配返回 `managed=false` 且不查 HLTB。只影响插件安装/补录的游戏，DroidDeck 上同样生效。
- 库页时长（v0.25.0）：仅 `managed=true` 显示；AppID 优先降低同名误判但非绝对；HLTB 失败只影响块内数值；依赖 Steam 库页结构。
- 原生库返回（v0.24.0；v0.27.20）：库页顶部有「返回 / Steam 库 / 刷新」工具栏（v0.27.3 起因 QAM sticky 偏移改为普通流式）；modal 模式「返回」调 `onClose` 关闭弹层，全屏 route 模式用 `Navigation.NavigateBack()`；「Steam 库」关闭弹层后 `Router.NavigateToLibraryTab()` 回 Steam 库页（DroidDeck 上该 API 不可用时回退 `NavigateBack`）。B 键在详情/库根节点绑定 `onCancel`；仍可用显式按钮兜底。
- 原生库入口（v0.20.0 起；v0.27.20 当前）：QAM 主页「游戏库」优先 `showModal(<LibraryPage />)` 原生弹层，失败才 `Navigation.Navigate("/freedeckcy/library")`；v0.27.20 起不再显示 UI 版本标识，版本以 Decky 插件列表/`package.json` 为准。
- 双语界面（v0.28.7）：首次打开 QAM 插件选择中文 / English；选择存 localStorage，可在 QAM 主页切换；原生库/设置/详情同样生效。
- 手柄/触控板（v0.27）：D-pad/左摇杆在 `flow-children` 分组内移动；A 选择，B 关闭详情/游戏库，L1/R1 切换游戏库/已安装，L2/R2 约 0.8 屏滚动；触控板/触摸纵向列表与横向货架滚动。焦点卡自动滚入可视区，最左卡焦点环/顶部蓝框不被裁。
- 百度扫码超时（v0.23.0）：点击立即 toast「正在获取百度二维码...」；前端 20s/15s、后端 12s/10s 超时，提示"获取百度二维码超时（网络/TLS 可能受阻...）"；DroidDeck/proot 网络/TLS 受限时按提示重试或运行诊断。
- 诊断自检（v0.22.0）：QAM 设置 → 「诊断」→「运行自检」显示 summary（OK/警告/失败/跳过）和每项检查（插件/state/下载安装目录/runtime/目录数据/Steam/存储/天翼网络/百度 QR/任务/日志）与建议；「导出诊断包」把 `freedeckcy-diagnostics-<时间>.zip` 写到 proot 内下载目录（`settings.download_dir`，未设置则插件下载目录/`~/Downloads`），权限 0600，toast 显示路径。DroidDeck 上 runtime 检查会看 `defaults/runtime/aarch64/` 的 aria2c/7zz/node；Steam 检查看当前正在运行的客户端；网络/百度 QR 受 proot 网络限制。
- 扫描已安装（v0.21.0 位置变更）：入口在 **QAM 设置 → 安装 → 「扫描已安装游戏」**（原生库已安装页不再有扫描按钮；网页库按钮保留备用）。扫描仍以 proot 内 `settings.install_dir` 为根、只扫一层、目录名匹配标题；对没有快捷方式的游戏会自动补建：PC 找 `.exe`，模拟器需已安装（不自动下载）并生成 wrapper；成功后 toast 显示"自动加入 Steam：N"。**Steam 需要重启/切用户/重开库页**才能在 DroidDeck 里看到新快捷方式。
- Decky 原生游戏库（v0.20.0；v0.27.20 视觉/输入重构）：QAM 主页「游戏库」进入原生库（默认 Hero+分类货架，搜索/筛选后网格）；不再打开本地网页；搜索 + 平台/分类/排序筛选、30 条/页 + 加载更多、双网盘下载源选择；已安装页签支持启动/目录/卸载。扫描入口在设置；安装进度在 QAM 主页任务区。旧本地网页库仅桌面调试/回退。
- 存储位置选择（v0.19.0）：QAM「设置 → 路径」会在下载/安装目录下显示检测到的外置挂载按钮（如 `/storage/emulated/0`、`/sdcard`、`/mnt/...`；标签「SD 卡 / 外置：<目录名>（剩余 X）」），点一下就把目录切到 `<mount>/freedeckCY/downloads|installed`。**只显示已挂载且 proot/Android 下可写的子挂载**；/storage、/sdcard、/mnt 挂载根本身会被跳过；权限不足/只读/未挂载不显示；插件不会自动创建/挂载/格式化，也不检测 Steam 库是否同盘。原「选择下载目录/安装目录」仍保留。
- 扫描已安装（v0.18.0 起，v0.21.0 迁移）：网页库「已安装」工具栏按钮仍作为备用（`POST /api/tianyi/installed/scan`）；主入口在 QAM 设置 → 安装。DroidDeck 上安装目录通常是 proot 内路径（如 `/root/Games`），插件只扫 `settings.install_dir` **一层子目录**；目录名需与目录标题匹配，v0.21.0 起会自动补建 Steam 快捷方式（见上一条）。
- 百度网盘（v0.17.0，扫码/Cookie 主链路）：aarch64 与 x86_64 行为一致（纯 HTTPS API，无本地二进制）。QAM「百度网盘（扫码登录）」→「扫码登录百度网盘」→ 用手机百度 App/百度网盘 App 扫码确认；Cookie 写入 proot 内 `~/.local/share/freedeckCY/tianyi/state.json` 的 `baidu_login`，之后百度分享可直接安装，不需要开放平台 App Key。Cookie 会过期/被风控，失效后重新扫码；扫码 session 仅内存 180s。**OpenAPI（v0.14.0）保留为可选回退**（自建应用 + OAuth，无 Cookie 时才用）。**不接 CDP/网页逆向**。详见 [ARCHITECTURE.md](ARCHITECTURE.md) §5.13 / [DEVELOPMENT.md](DEVELOPMENT.md) §6.11。
- 仓库游戏提交（v0.13.0）：网页库工具栏有「提交游戏」按钮，点击后用系统浏览器/Steam 内置浏览器打开 GitHub Issue 表单（`https://github.com/hulong1989/freedeckCY/issues/new?template=submit-game.yml`）；也可以直接提 PR 改 `submissions/*.json`。字段与原版资源池投稿一致（名称/英文名/平台/分享链接/提取码/版本/可执行文件名 + `openpath`），**只提交分享链接，不上传游戏文件**；这条链路与设备无关，DroidDeck 上不需要任何额外配置。详见 [submissions/README.md](../submissions/README.md)。
- 自动云存档（v0.8.0）：内置 Ludusavi 清单（53,549 游戏）按标题/SteamID 匹配，并把 Windows 存档路径解析到 **ARM Proton 前缀**（`compatdata/.../pfx` 内布局与 x86_64 一致）；`gamewatch` 每 8 秒扫 `/proc/*/cmdline`（proot 下通常可用；没有 `/proc` 时回退 `pgrep -f`，需要系统有 pgrep），检测到游戏退出后只上传该游戏。自动上传**默认开启**，可在 QAM「云存档上传」里关闭。
- 模拟器注册表（v0.11.0）共 **10 个平台**，但 DroidDeck/aarch64 上**只有 7 个可用**：GBA（mGBA）/ PSP（PPSSPP）/ NDS（melonDS）/ PS1（DuckStation）/ FC、MD（Mesen2）/ **Switch（Eden，有 arm64 官方包）**；**3DS（Azahar）/ PS2（PCSX2）/ PS3（RPCS3）官方包仅 x86_64**，`available_platforms("aarch64")` 不返回它们，目录查询按白名单过滤，**条目和平台筛选条都不会出现**（预期行为，不是缺数据）。
- **插件包不集成任何模拟器**：上述 7 个平台首次安装都会从官方 release 下载 arm64 包（NDS 是 zip 内 AppImage；Mesen2 是 zip 内单文件 `Mesen`），AppImage 解包到 `~/.local/share/freedeckCY/emulators/<state_key>/aarch64/squashfs-root`，不依赖 FUSE；离线可手动预置缓存或用 `FREEDECKCY_*_BIN`。
- **BIOS / 固件部署（v0.12.0）**：用户文件统一放 `~/.local/share/freedeckCY/bios/<platform>/`（proot 内 HOME 路径），**支持压缩包**（`.zip/.7z/.rar` 等，安装时用 7zz 解压到同目录 `_extracted/` 缓存）；安装后自动部署：
  - PS1：BIOS → `<AppDir>/bios` + `~/.local/share/duckstation/bios`，并写 `portable.txt`/`portable_data/settings/settings.ini`（`SearchDirectory=./bios`、全屏）；
  - PS2：仅 x86_64（DroidDeck 隐藏），BIOS → `<AppDir>/bios` + `~/.local/share/PCSX2/bios` + `~/.config/PCSX2/bios`；
  - NDS：`bios7/bios9/firmware` → `<AppDir>` + `~/.local/share/melonDS`；
  - Switch（Eden）：`prod.keys/title.keys` → `~/.local/share/eden/keys/`，固件 `.nca` → `~/.local/share/eden/nand/system/Contents/registered/`；
  - PS3（RPCS3）：仅 x86_64（DroidDeck 隐藏），`PS3UPDAT.PUP` 在 `dev_flash` 为空时自动 `--installfw`；
  - GBA/PSP：写 portable 全屏配置；3DS 仅 x86_64（隐藏）。
  部署消息会并入安装完成消息；缺失文件不阻断安装，但装完不能直接玩。

## 2. 构建 ARM64 插件包

在开发机（Linux/macOS 均可）执行：

```bash
cd freedeckCY
make runtime ARCH=aarch64        # 下载 ARM64 版 aria2c / 7zz / node
make package-droiddeck           # 产出 dist-artifacts/freedeckCY-v<version>-arm64.zip
```

说明：

- `make runtime ARCH=all` 可以同时准备 x86_64 与 aarch64 两份运行时。**v0.10.0 起不再有 `make emulator-runtime`**：插件包不包含任何模拟器（GBA 也改为首次安装在线下载），包体积约 45MB（此前含 mGBA 时约 68MB）。
- `PACKAGE_ARCH=aarch64` 打包时会自动裁剪 `defaults/runtime/{aria2,7z,node}` 里其它架构，避免包体积翻倍；**模拟器不参与打包**，DroidDeck 上 7 个平台（含 Switch）首次安装都需要联网下载 arm64 官方包；PS1 BIOS 需自己放到 `~/.local/share/freedeckCY/bios/ps1/`。
- 产物名带 `-arm64` 后缀；x86_64 的普通包仍用 `make package`。

## 3. 安装

1. 在 DroidDeck 里装好并启用 **Decky Loader**（DroidDeck 设置 → Decky → 安装/启用）。
2. 把 `freedeckCY-v<version>-arm64.zip` 放进手机存储。
3. 打开 DroidDeck 的 Decky 菜单 → **Import plugin zip** → 选择该 zip。
   - DroidDeck 会按 `plugin.json` 的 `name` 做覆盖安装，升级时无需先卸载。
4. 启动/重启 Steam 游戏模式，在 Decky 侧栏打开 freedeckCY。

首次使用：

- 登录天翼云盘（QAM 面板）；
- 在下载设置里把下载目录/安装目录改到空间充足的路径（例如 `/root/Games`）；
- 打开 QAM 主页「游戏库」（原生弹层），搜索/筛选后安装；本地 Web UI 仅桌面调试/回退；
- 模拟器：aarch64 上可看到 GBA/PSP/NDS/PS1/FC/MD/Switch（3DS/PS2/PS3 被隐藏），筛选后直接安装，插件会自动生成启动脚本并注册 Steam 快捷方式。**所有平台（含 GBA）首次安装都要联网下载 arm64 官方包**，耗时取决于网络。**装前/装后都可把 BIOS/固件/keys（或压缩包）放到 `~/.local/share/freedeckCY/bios/<platform>/`**，重装/重新注册时会自动部署；PS1 需要 BIOS，Switch 需要 `prod.keys`+固件。

## 4. 功能支持情况

| 功能 | DroidDeck 状态 |
|---|---|
| 天翼登录、分享解析、直链下载 | ✅ 使用 ARM64 aria2c |
| 7z 解压 / `7z t` 校验 | ✅ 使用 ARM64 7zz |
| PC 游戏安装 + Steam 快捷方式 + 封面 | ✅（依赖 Steam 根与 Proton 映射正确） |
| 全量目录 / 平台与分类筛选 / 封面缓存 | ✅ |
| 卸载回收 Proton 前缀 | ✅（compatdata 在 ARM Proton 下同样适用） |
| 任务重试、下载完整性校验、自动重下 | ✅ |
| 云存档上传/恢复 | ✅ 需要 ARM64 node（`make runtime ARCH=aarch64` 自带） |
| 自动云存档（Ludusavi + gamewatch，v0.8.0） | ✅ 内置清单随包；游戏退出后自动上传该游戏（30 s 防抖、指纹去重）。`/proc` 在 proot 下通常可用，无则回退 `pgrep -f`；默认开启可在 QAM 关闭；ARM64 未真机验证 |
| GBA 模拟器（mGBA，v0.6.0 起，v0.10.0 在线下载） | ✅ 可安装/启动：首次安装从官方 release 下载 arm64 AppImage（约 24.6MB）→ `--appimage-extract` 解包（不依赖 FUSE），Steam 快捷方式走原生（无 Proton 映射） |
| PSP 模拟器（PPSSPP，v0.7.0） | ✅ 可安装/启动：首次安装从 GitHub 下载 arm64 官方 AppImage（已按 aarch64 选资产），解包不依赖 FUSE |
| NDS 模拟器（melonDS，v0.7.0） | ✅ 可安装/启动：首次安装下载官方 zip（内含 aarch64 AppImage）→ 解 zip → `--appimage-extract`，不依赖 FUSE |
| PS1 模拟器（DuckStation，v0.9.0） | ✅ 可安装/启动：官方 arm64 AppImage 按需下载；**需自备 BIOS**（`~/.local/share/freedeckCY/bios/ps1/`，安装时复制到 `~/.local/share/duckstation/bios/`）；缺失不阻断但会警告/可能黑屏 |
| FC 模拟器（Mesen2，v0.9.0） | ✅ 可安装/启动：官方 ARM64 zip 内单文件 `Mesen`（按需下载） |
| MD 模拟器（Mesen2，v0.9.0） | ✅ 可安装/启动：与 FC 共用 Mesen2（`emulators/mesen/aarch64/`），ROM 扩展名不同 |
| Switch 模拟器（Eden，v0.11.0） | ✅ 可安装/启动：有 **arm64 官方 AppImage**；需要 `prod.keys` + 固件（`setup_hint` 提示，缺失不阻断但装完不能直接玩） |
| 3DS / PS2 / PS3（v0.11.0） | ⚠️ **仅 x86_64，DroidDeck 自动隐藏**：Azahar/PCSX2/RPCS3 官方包没有 arm64，目录白名单过滤后条目与平台筛选条都不出现（不是 bug）；3DS 在 x86_64 上 v0.14.1 起优先 Flatpak、回退 AppImage |
| 模拟器 BIOS/固件部署（v0.12.0） | ✅ 安装后自动部署 `bios/<platform>/`（支持压缩包，7zz 解压缓存）；aarch64 可用 PS1/NDS/Switch 的部署与 GBA/PSP 全屏配置；PS2/PS3/3DS 仅 x86_64 |
| 仓库游戏提交（v0.13.0） | ✅ 网页库「提交游戏」按钮打开 GitHub Issue 表单；或直接 PR `submissions/*.json`。无设备特定逻辑，DroidDeck 与 Steam Deck 行为一致 |
| 模拟器存档上传/恢复（v0.15.0 / v0.16.0） | ✅ aarch64 可用：按 proot 内 HOME 发现/恢复 GBA/PSP/NDS/PS1/FC/MD/Switch 存档；恢复走白名单目标 + `*.freedeckcy-bak-*` 备份，冲突需确认；PSP 按 PARAM.SFO 拆分；PS1 多碟 m3u 可用；3DS 拆分随平台隐藏（仅 x86_64） |
| Decky 原生游戏库（v0.20.0；v0.27.20） | ✅ aarch64 可用：QAM 原生库（Hero+分类货架，搜索/筛选后网格）/详情页/已安装动作；不依赖网页与本地 HTTP |
| 手柄/触控板（v0.27） | ✅ DroidDeck 触控/手柄走 Decky 焦点系统：A/B、方向键、L1/R1、L2/R2、触控滚动；与 Steam Deck 共用同一实现 |
| 库页时长隔离（v0.25.0） | ✅ aarch64 可用：仅插件安装/补录游戏显示时长块；Steam 原有游戏 `managed=false` 不插入、不查 HLTB |
| 原生库返回/关闭（v0.24.0） | ✅ aarch64 可用：「返回 / Steam 库 / 刷新」工具栏（v0.27.3 起普通流式）+ 标题栏；modal 用 `onClose`，route 用 `NavigateBack`；「Steam 库」走 `NavigateToLibraryTab`（不可用则回退） |
| 原生库 modal 兜底/QR 超时（v0.23.0） | ✅ aarch64 可用：游戏库优先 modal、全屏路由兜底；v0.27.20 起不再显示 UI 版本标识；百度扫码前后端超时与明确提示 |
| 诊断自检/诊断包（v0.22.0） | ✅ aarch64 可用：QAM 设置「诊断」运行自检、导出 0600 zip 到 proot 下载目录；runtime 检查 aarch64 组件，网络/百度 QR 受 proot 限制 |
| 扫描已安装 + 自动补 Steam（v0.21.0） | ✅ 入口在设置 → 安装；扫描 proot 内 `install_dir` 一层，自动补建 PC/模拟器快捷方式（模拟器未安装不下载，记 `shortcut_error`）；Steam 需重启/切用户/重开库页才显示 |
| 存储位置选择（v0.19.0） | ✅ aarch64 可用：QAM 路径页按 `/storage`、`/sdcard`、`/mnt` 等可写挂载渲染「下载/安装到 …（剩余 X）」按钮，一键切换；只读/未挂载不显示 |
| 百度网盘（扫码/Cookie，v0.17.0） | ✅ aarch64 可用：QAM 显示二维码，手机扫码后 Cookie 存 state（0600）；安装优先 Cookie，任务带百度 Cookie/Referer/UA；Cookie 过期需重扫；OpenAPI 为可选回退（自建应用/授权）；不接 CDP/网页逆向 |
| `make doctor` | ⚠️ 需要 DroidDeck 桌面终端；Android 上 `lsof` 可能不存在 |

## 5. 环境变量与设置

| 变量/设置 | 作用 |
|---|---|
| `FREEDECKCY_STEAM_ROOT` | 指定 Steam 根目录（DroidDeck 双客户端时手动锁定） |
| `FREEDECKCY_PROTON_TOOL` | 覆盖 Proton 工具名；`none` 表示不写映射 |
| `FREEDECKCY_ARIA2_BIN` / `FREEDECKCY_7Z_BIN` / `FREEDECKCY_NODE_BIN` | 覆盖运行时二进制路径 |
| `FREEDECKCY_MGBA_BIN` | 覆盖 mGBA 可执行文件/AppImage 路径（默认用已下载的缓存；也可指向系统 mGBA 或手工预置的 AppImage） |
| `FREEDECKCY_PPSSPP_BIN` | 覆盖 PPSSPP 路径（默认用已下载的 arm64 AppImage / 系统 PPSSPP） |
| `FREEDECKCY_MELONDS_BIN` | 覆盖 melonDS 路径（默认用已下载的 arm64 AppImage / 系统 melonDS） |
| `FREEDECKCY_DUCKSTATION_BIN` | 覆盖 DuckStation 路径（PS1；默认用已下载的 arm64 AppImage / 系统 DuckStation） |
| `FREEDECKCY_MESEN_BIN` | 覆盖 Mesen2 路径（FC/MD 共用；默认用已下载的 ARM64 `Mesen` / 系统 Mesen） |
| `FREEDECKCY_EDEN_BIN` | 覆盖 Eden 路径（Switch；默认用已下载的 arm64 AppImage / 系统 Eden） |
| `FREEDECKCY_BAIDU_OPENAPI_APP_KEY` / `SECRET_KEY` | 百度开放平台应用（无头/纯 API 环境；state 优先） |
| `FREEDECKCY_BAIDU_OPENAPI_REFRESH_TOKEN` | 百度 refresh_token 兜底（state 为空时） |
| `FREEDECKCY_AZAHAR_BIN` / `FREEDECKCY_PCSX2_BIN` / `FREEDECKCY_RPCS3_BIN` | 仅 x86_64 平台，aarch64 上不会出现；保留给跨架构调试/未来 arm64 包 |
| 设置项 `proton_tool` | `auto`（默认，自动判断）/ `none` / 具体工具名 |
| 设置项 `cloud_save_auto_upload` | 游戏退出后自动上传云存档（默认 `true`，QAM「云存档上传」可关） |

查看当前解析结果：`GET /api/tianyi/settings`（本地服务返回 `proton_tool_resolved` 与 `droiddeck_detected`）。

## 6. 排障

**安装后游戏没出现在 Steam 里**

- DroidDeck 可能同时存在两个 Steam 客户端。确认当前运行的是哪一个：
  - `~/.droiddeck-x64/.local/share/Steam`（x64 客户端）
  - `~/.local/share/Steam`（标准/ARM 客户端）
- 用 `FREEDECKCY_STEAM_ROOT` 指向正在运行的那个，重装一次游戏（或等插件下次写快捷方式）。
- 重启 Steam 让 `shortcuts.vdf` 重新加载。

**游戏启动不了 / 提示兼容工具缺失**

- DroidDeck 需要 ARM Proton。确认 Steam 里已安装 `droiddeck-proton-arm64`（或 11 版）。
- 插件默认会写 `droiddeck-proton-arm64`；如果版本不匹配，可用 `FREEDECKCY_PROTON_TOOL=droiddeck-proton-11-arm64` 或设为 `none` 后在 Steam 里手动选兼容工具。

**下载/解压报 “找不到二进制”**

```bash
ls -l defaults/runtime/aria2/aarch64/aria2c \
      defaults/runtime/7z/aarch64/7zz \
      defaults/runtime/node/aarch64/bin/node \
      ~/.local/share/freedeckCY/emulators/gba/aarch64/  # 模拟器不在插件包内
```

缺哪个就重新 `make runtime ARCH=aarch64` 并重新打包；也可用环境变量指向系统里的 arm64 版本。（模拟器已不在包内，无需准备。）

**GBA 装完启动不了 / 提示未找到 mGBA / 下载失败**

- v0.10.0 起 GBA 也**首次安装自动下载**（包内不再含 mGBA）：检查网络/系统代理；失败后重装可再次触发下载。
- 下载/解包位置 `~/.local/share/freedeckCY/emulators/gba/aarch64/`（GBA 兼容旧 `emulators/aarch64/`；不依赖 FUSE）；解包失败通常是存储空间/权限问题，可删掉该目录重试，或用 `FREEDECKCY_MGBA_BIN` 指向系统 mGBA / 手工预置的 AppImage。
- 离线时可把 mGBA arm64 AppImage 放到 `~/.local/share/freedeckCY/emulators/gba/aarch64/` 并 `chmod +x`，或用 `FREEDECKCY_MGBA_BIN` 指向本地版本；PSP/NDS/PS1/FC/MD 同理（各自 `<state_key>/aarch64/`，FC/MD 共用 `mesen/`）。
- 用 `GET /api/tianyi/diagnostics` 看 `emulators.gba` 的 available/source/command 快速定位。
- GBA 快捷方式在 Steam 里的 Exe 是 `<安装目录>/launch-freedeckcy.sh`（`exec <mGBA> -f <rom>`）；可进安装目录手工 `bash launch-freedeckcy.sh` 验证。

**PSP/NDS/PS1/FC/MD 装完启动不了 / 首次安装下载失败**

- 这些平台的官方包 **不随包内置**（v0.10.0 起 GBA 也一样）：首次安装需要访问 GitHub release 下载 arm64 资产；无网络、代理不通或 GitHub 限流都会失败，失败后重装可再次触发下载。
- 下载/解包位置：`~/.local/share/freedeckCY/emulators/{psp,nds,duckstation,mesen}/aarch64/`；NDS/Mesen2 先解 zip（Mesen2 直接是可执行文件 `Mesen`），PSP/PS1 是 AppImage（`--appimage-extract`），均不依赖 FUSE。
- 检查诊断接口 `emulators.{psp,nds,ps1,fc,md}` 的 `source`（`download` 表示尚未下载）与 `message`；也可用 `FREEDECKCY_PPSSPP_BIN` / `FREEDECKCY_MELONDS_BIN` / `FREEDECKCY_DUCKSTATION_BIN` / `FREEDECKCY_MESEN_BIN` 指向手工下载的 arm64 包。
- 手工验证 wrapper：`bash "<安装目录>/launch-freedeckcy.sh"`（PSP `--fullscreen`、PS1 `-batch -fullscreen`、FC/MD `/fullscreen`、NDS 直接接 ROM）。

**看不到 3DS / PS2 / PS3（预期）**

- 这三个平台官方包**只有 x86_64**，DroidDeck 是 aarch64：`available_platforms("aarch64")` 只返回 7 个平台，目录查询按白名单过滤，所以游戏条目与平台筛选条都不会出现；`emulator_status` 对它们返回 `available=false`（"已隐藏该平台"）。
- 不是缺数据、也不是没装依赖；只能等官方 arm64 包，不能用 `FREEDECKCY_*_BIN` 绕过（目录层就不展示）。

**PS2 BIOS 放哪 / PCSX2 提示没有 BIOS**

- 放 `~/.local/share/freedeckCY/bios/ps2/*.bin`（或压缩包）；v0.12.0 安装时会部署到 `<AppDir>/bios`、`~/.local/share/PCSX2/bios`、`~/.config/PCSX2/bios` 三处，并写 `portable.ini`/`inis/PCSX2.ini`。注意 **PS2 平台在 DroidDeck 上被隐藏**，只有 x86_64 设备会用到这条路径。

**BIOS/固件压缩包没生效 / 路径不对**

- 压缩包放 `~/.local/share/freedeckCY/bios/<platform>/`，安装时由 7zz 解压到 `_extracted/` 再部署；确认插件有 ARM64 7zz（`make runtime ARCH=aarch64` 或 `FREEDECKCY_7Z_BIN`），失败会在安装消息里显示。
- 部署目标：`<AppDir>/bios`（AppImage 解包后的 `squashfs-root/bios`）、DuckStation/melonDS/Eden 的用户目录；portable 配置存在时模拟器优先读 `<AppDir>/bios`。
- 只想手工放时，把已解压文件直接放 `bios/<platform>/`（会跳过解压步骤）；重装或重新注册 Steam 快捷方式会再次触发部署。

**PS3 固件 / Switch keys 没识别**

- PS3（仅 x86_64）：固件必须是 `bios/ps3/PS3UPDAT.PUP`；`~/.config/rpcs3/dev_flash` 非空时跳过；失败看安装消息里的 `--installfw` 错误。
- Switch（aarch64 可用）：`prod.keys/title.keys` 放 `bios/switch/` → 复制到 `~/.local/share/eden/keys/`；固件压缩包解出的 `.nca` → `~/.local/share/eden/nand/system/Contents/registered/`；目录为空时重启 Eden 再试。

**Switch / 3DS / PS3 装完不能直接玩**

- Switch（Eden，aarch64 可用）需要 `prod.keys` 与固件；3DS/PS3 在 ARM 上不可用。安装消息/库页弹窗会带 `setup_hint`，按提示在模拟器首次启动时配置；插件不内置也不下载这些文件。

**PS1 黑屏 / 提示没有 BIOS / Mesen2（FC/MD）不启动**

- PS1：DuckStation 必须自备 BIOS。把 `scph*.bin` 放到 `~/.local/share/freedeckCY/bios/ps1/` 后重装（或手工 `cp -n .../bios/ps1/*.bin ~/.local/share/duckstation/bios/`）；诊断接口看 `emulators.ps1.bios_present/bios_dir`。
- Mesen2：官方 ARM64 zip 内是单文件 `Mesen`，启动参数是 `/fullscreen <rom>`（不是 `-f`）；FC 与 MD 共用同一份 `emulators/mesen/aarch64/`，删缓存会影响两者。

**游戏退出后没有自动上传云存档**

- 确认设置 `cloud_save_auto_upload` 为 true（QAM「云存档上传 → 游戏退出后自动上传」）。
- gamewatch 靠 `/proc/*/cmdline` 判断 install_path 是否在运行；DroidDeck 的 proot 通常提供 `/proc`，若没有会回退 `pgrep -f`（需要系统有 pgrep），两种方式都要求**进程命令行里出现安装目录**（自定义 wrapper 可能不满足）。
- 自动上传需要已登录天翼账号、当前没有进行中的上传任务，且两次自动上传间至少间隔 30 秒；连续退出多个游戏时只有第一个会立即上传。
- 日志搜 `auto cloud save upload after exit`（触发）与 `gamewatch poll failed`（检测异常）；上传状态里 `reason=unchanged` 表示存档指纹未变化、已按设计跳过。

**点「提交游戏」没反应 / 没有浏览器**

- 按钮只是打开 GitHub Issue 表单（不是插件内表单）：DroidDeck 的 Steam 内置浏览器或系统默认浏览器能打开 GitHub 即可；完全无浏览器时，手工在电脑/手机浏览器打开 `https://github.com/hulong1989/freedeckCY/issues/new?template=submit-game.yml`，或直接在 `submissions/` 下提 PR。
- 提交只需要分享链接与字段，**不需要天翼云账号登录**；字段说明见 [submissions/README.md](../submissions/README.md)。

**百度网盘未配置 / 授权失效 / 下载失败**

- 「未配置百度开放平台应用」：QAM 保存 App Key/Secret（或设 env `FREEDECKCY_BAIDU_OPENAPI_APP_KEY`/`SECRET_KEY`）。
- 授权失效：清除授权后重新「获取授权链接」→ 浏览器登录百度 → 把授权码粘回「完成授权」；refresh 失败时也可用 `FREEDECKCY_BAIDU_OPENAPI_REFRESH_TOKEN` 兜底。
- 安装报 `errno=-6` / transfer disabled：百度账号转存被限制或分享文件禁止转存；换账号/稍后重试，按安装消息里的官方 errno 处理。
- dlink 403/下载失败：插件已带 `Referer=https://pan.baidu.com/disk/home`、`UA=pan.baidu.com`、空 cookie；重试会重新取 dlink，仍失败看安装消息（dlink 过期/风控）。
- 转存空间：分享文件会转存到百度网盘 `/FreedeckTmp`，安装结束自动清理；失败会保留，可手动删除该目录。
- 链接格式：支持 `pan.baidu.com/s/<surl>`、`/share/init?surl=...`、`yun.baidu.com`/`eyun.baidu.com`；短链先展开。

**3DS 相关（DroidDeck/aarch64）**

- DroidDeck 上目录不显示 3DS 是预期：3DS 只有 x86_64 官方包，`available_platforms("aarch64")` 不含它；不要尝试用 `FREEDECKCY_AZAHAR_BIN` 绕过目录白名单。
- 在 x86_64 + flatpak 环境（如 SteamOS 主机）上：先 `flatpak remote-add --user --if-not-exists flathub ...`、`flatpak install -y --user flathub org.azahar_emu.Azahar`；诊断 `emulators.3ds.source` 应为 `flatpak`，否则回退 AppImage。
- 3DS system files 放 `~/.local/share/freedeckCY/bios/3ds/sysdata/`；Flatpak 环境还会复制到 `~/.var/app/org.azahar_emu.Azahar/data/{azahar,azahar-emu}/sysdata`。

**模拟器存档恢复失败 / 恢复到错误位置**

- 恢复目标只能在平台标准/portable 根内（`restore_roots`）；同机优先原父目录，跨设备落到第一个根；manifest 里的任意 HOME 路径会被拒绝/回退。
- 覆盖前会生成 `*.freedeckcy-bak-<时间戳>`；PS1/PS2 单片记忆卡、Switch 目录是整卡/整目录覆盖（不能只挑一个游戏），冲突需确认。
- PSP/PS3 拆分依赖存档目录里的 `PARAM.SFO`；3DS 拆分依赖 NCSD `0x108` title id 且平台在 aarch64 不可见；拆分失败会回退共享目录（不是错误）。
- PS1 多碟：已有 `.m3u` 优先；多张 `.cue/.chd` 会生成 `freedeckcy-multidisc.m3u`（自然排序），单碟仍 `.cue`。

**模拟器存档没有上传 / 上传很大**

- 先确认 QAM「云存档上传 → 包含模拟器存档」开启；关闭后非 PC 记录会计入 `emulator_saves_disabled`。
- 找不到存档：看上传状态 `diagnostics.collect[*].diagnostics.emulator_saves.reason`（`save_dir_missing`/`game_save_not_found`/`emulator_saves_shared`）；GBA/FC/MD/NDS 必须与 ROM 同名（`.sav/.srm/...`）。
- DroidDeck 的路径是 proot 内 HOME（如 `~/.local/share/ppsspp/PSP/SAVEDATA`、`~/.local/share/eden/nand/user/save`）；**`~/.var/app/...` Flatpak 路径不适用**。
- 共享记忆卡/标题目录可能很大（3DS/Switch），受指纹 5000 文件与上传体积限制；必要时关闭开关或手动清理。
- 恢复支持模拟器存档（v0.16.0，白名单目标 + 备份 + 冲突确认）；PS1/PS2 单片记忆卡、Switch 目录仍整卡覆盖。

**百度网盘扫码登录失败 / 安装提示未登录**（v0.18.0 起错误会带具体原因）：

- 二维码/轮询会用同一组 Cookie（先访问 passport 首页拿 BAIDUID）；HTTP 非 200 会显示状态码与响应片段，轮询网络错误会显示 `stage=failed`（不再一直 waiting）。
- 检查 DroidDeck 内网络能否访问 `passport.baidu.com`；二维码 180s 过期需重新获取；扫码后需在手机上确认。

- QAM「百度网盘（扫码登录）」点「扫码登录百度网盘」；二维码不显示时看返回的 `qrcode_url`，或检查 DroidDeck 内网络能否访问 `passport.baidu.com`。
- 一直 waiting：手机未扫码/未确认；二维码 180s 过期，重新获取即可。scanned 表示已扫码待手机确认。
- 扫码成功但安装仍提示未登录：确认 `state.json` 的 `baidu_login.cookie` 含 `BDUSS=`，`/api/tianyi/settings` 的 `baidu_login.logged_in` 为 true；必要时「退出百度网盘」后重扫。
- Cookie 失效/直链 403：重新扫码；任务已带百度 Cookie/Referer/UA，403 多为直链过期/风控。
- 想用 OpenAPI 回退：不扫码（或清空百度登录），在「百度网盘 OpenAPI（可选）」配置 App Key/Secret 并授权；分享文件会转存 `/FreedeckTmp`（安装后清理）。
- 扫码确认/换 Cookie 尚未真机验证，遇到问题请附 QAM 状态与安装消息。

**Steam 原有游戏详情页出现插件时长块**

- v0.25.0 起只对 `managed=true` 的插件安装/补录游戏显示；原版游戏未匹配时前端直接 `return null`、后端 `managed=false` 且不查 HLTB。
- 仍出现时确认前端 dist/插件已重载、Steam 库页重开；同名游戏可能被标题匹配误认，先看 `installed_games` 是否有同名记录。

**游戏库无法返回 / 困在库页**

- 库页顶部有「返回 / Steam 库 / 刷新」工具栏（v0.27.3 起普通流式）和标题栏返回；modal 用 `onClose` 关闭、全屏 route 用 `Navigation.NavigateBack()`。
- 「Steam 库」按钮会先关库页再 `Router.NavigateToLibraryTab()`；DroidDeck 上该 API 不可用时会回退 `NavigateBack`。
- Steam 覆盖层 B/Esc 不一定能关 modal，优先点显式按钮；route 返回依赖导航栈，栈空时只能关侧栏或重载插件。

**点游戏库仍打开旧网页 / QR 点了没反应**

- v0.20.0 起游戏库优先 `showModal(<LibraryPage />)`；v0.27.20 起不再显示 UI 版本标识，先确认插件版本为 0.27.20、dist 已更新、Decky 已重载。
- 百度扫码点击后应立刻出现 toast；若超时，提示会带"网络/TLS 可能受阻"，看 `/tmp/freedeckcy.log` 的 `Baidu QR` 关键字，或运行诊断。

**诊断自检失败 / 诊断包导出失败**

- 设置 → 诊断「运行自检」看每项 status/detail/fix；runtime_* 失败检查 `defaults/runtime/aarch64/{aria2,7z,node}`（重装/重打包），state/下载/安装目录失败检查 proot 权限与剩余空间。
- Steam 项 warn/fail：确认 DroidDeck 双 Steam 根下正在运行的客户端，或用 `FREEDECKCY_STEAM_ROOT` 锁定；网络/百度 QR 失败先确认 proot 能访问对应域名。
- 导出失败看下载目录是否可写；诊断包权限 0600，路径见 toast。自检只给建议，不会自动修复。

**扫描已安装没补回游戏 / 没补 Steam 快捷方式**

- v0.21.0 起入口在 **QAM 设置 → 安装 → 扫描已安装游戏**（不在原生库已安装页）。
- 只扫 proot 内 `settings.install_dir` 一层，目录名要匹配标题；嵌套目录/0 字节目录跳过。
- PC 找 exe 失败会记 `exe_not_found`；模拟器未安装记 `emulator_not_ready`（不会自动下载）；ROM 找不到 `rom_not_found`；看 toast/接口返回的 `shortcut_error` 与 `steam_added`/`steam_recovered_count`。
- 只写 `shortcuts.vdf`，**Steam 需重启/切用户/重开库页**才显示新快捷方式；DroidDeck 双 Steam 根时确认写到了正在运行的那个（`FREEDECKCY_STEAM_ROOT`）。

**原生游戏库打不开 / 列表空 / 安装失败**

- v0.20.0 起「游戏库」是 QAM 原生路由 `/freedeckcy/library`（不是网页）；打不开时确认插件已重载、Decky 日志无路由报错。
- 列表空：看目录是否加载、搜索/平台/分类/排序筛选；安装失败看 `ConfirmModal`/toast 里的计划错误（空间不足、目录不可写、模拟器不可用）。
- 安装进度在 QAM 主页任务区，不在库页；已安装页扫描仍只认 proot 内 `settings.install_dir` 一层、目录名需匹配。
- 需要 compatdata 回收等高级卸载选项时用主页/网页库；原生库卸载固定删游戏文件。

**SD 卡/外置存储按钮没出现 / 切换后不可写**

- 只显示已挂载且可写的 `/run/media`、`/media`、`/mnt`、`/storage`、`/sdcard` 子挂载；挂载根本身会跳过（如 `/storage`、`/sdcard` 本身），`/storage/emulated/0` 这类子挂载才会显示。
- 确认 DroidDeck/proot 内该路径可写（Android 存储映射/权限可能让某些路径只读）；可用 `curl /api/tianyi/storage/options` 看 `external` 与 `free_text`，或到终端 `touch` 测试。
- 插件不创建目录/挂载；必要时手动 `mkdir -p <mount>/freedeckCY/{downloads,installed}`。
- 切目录后安装仍失败：检查目标盘空间与权限（`df -h`），以及 Steam 库是否在同一盘。

**日志**

- 插件日志：`/tmp/freedeckcy.log`
- 状态：`~/.local/share/freedeckCY/tianyi/state.json`
- 健康检查：`curl 127.0.0.1:59271/_healthz`

## 7. 已知限制

- 未在真机验证：DroidDeck 的 FEX/ARM Proton、不同 Android 机型的存储映射都可能影响结果。
- aarch64 上可安装 **GBA/PSP/NDS/PS1/FC/MD/Switch** 共 7 个平台（mGBA/PPSSPP/melonDS/DuckStation/Mesen2/Eden；v0.6.0~v0.12.0，全部在线下载）；v0.12.0 安装后自动部署 `bios/<platform>/`（含压缩包）并写 portable 配置（PS1/NDS/Switch/GBA/PSP；PS2/PS3/3DS 仅 x86_64）；**3DS/PS2/PS3 官方包仅 x86_64，DroidDeck 上被目录白名单自动隐藏**（条目/筛选条都不出现，见 [ROADMAP.md](ROADMAP.md) 9.8）。**插件包不集成任何模拟器，7 个平台（含 GBA）首次安装都需要联网**从官方 release 下载 arm64 包（包体积约 45MB），离线可手动预置缓存或用 `FREEDECKCY_*_BIN`；**PS1 需自备 BIOS、Switch 需 keys+固件**（setup_hint 提示，缺失不阻断但装完不能直接玩）；各平台只识别各自 ROM 扩展名，不含存档管理；ARM64 上这些平台尚未真机验证。
- **自动云存档边界**：v0.8.0 只做 PC；v0.15.0 起纳入模拟器存档（GBA/PSP/NDS/PS1/FC/MD/Switch），v0.16.0 起支持恢复；PS1/PS2/Switch 仍整卡/整目录覆盖；指纹只看相对路径+大小+mtime（≤5000 文件）；`/proc` 不可用时依赖 `pgrep`；ARM64 上该链路真机验证有限。
- 模拟器存档恢复（v0.16.0）在 Android/proot 下按 HOME 白名单恢复，Flatpak 路径不适用；PS1/PS2 单片记忆卡、Switch 目录不能按游戏拆；3DS 恢复随平台不可见；共享卡覆盖需确认且有备份。
- 模拟器存档（v0.15.0）在 Android/proot 下只认 HOME 内标准/portable 路径，Flatpak 的 `~/.var/app/...` 不适用；GBA/FC/MD/NDS 需 ROM 同名，PSP/PS1/PS2/3DS/PS3/Switch 上传共享记忆卡/标题目录（同卡其它游戏也会包含）；v0.16.0 起支持恢复（白名单目标/备份/冲突确认）；PS1/PS2/Switch 仍整卡覆盖，3DS/Switch 大目录受 5000 文件限制。
- 3DS（v0.14.1）在 DroidDeck/aarch64 上仍不可用（无 arm64 官方包，目录隐藏）；SteamOS/x86_64 优先 Flatpak（需系统有 flatpak 且能访问 Flathub），无 Flatpak 时回退 AppImage（可能仍有上游 #127/#953 问题）；3DS wrapper 走 XWayland；已有快捷方式自动重写但未在 DroidDeck 真机验证。
- 百度网盘（v0.17.0）主链路是扫码登录（BDUSS/Cookie）：需要手机百度 App 扫码，Cookie 会过期/被风控、失效需重扫；扫码 session 仅内存 180s；OpenAPI 是可选回退（自建应用/授权，转存 `/FreedeckTmp` 占网盘空间）；不接 CDP/网页逆向；扫码确认/换 Cookie 尚未真机验证；aarch64 与 x86_64 行为一致。
- 仓库游戏提交（v0.13.0）只依赖网页/GitHub，无设备特定逻辑；DroidDeck 上没有额外限制（除了需要能打开 GitHub 的浏览器）。
- DroidDeck 升级/重装 Decky 可能清空插件，需重新导入 zip。
- 原生库返回（v0.24.0；v0.27.20 起 B 键绑定 onCancel）：modal/route 返回逻辑不同；B 键在详情/游戏库根节点已绑定，仍建议用显式按钮兜底；route 返回依赖导航栈。
- 原生库/扫码超时：modal 失败才走路由；版本以 Decky 插件列表/`package.json` 为准；扫码超时依赖 proot 网络/TLS，只提示不自动重试。
- 诊断自检（v0.22.0）是一次性快照，网络项受 proot 连通性影响；`baidu_qr` 只输出 sign 长度（不含 sign/cookie）；导出包含 300 行日志（已脱敏），提交前自行过目；不支持在线查看日志/上传诊断包。
- 原生游戏库（v0.20.0；v0.27.20）：封面网格/Hero/筛选/详情/已安装动作齐全；任务进度在主页任务区；扫描入口在设置，仍只认 `settings.install_dir` 一层；卸载固定删文件（不弹 compatdata 回收）；旧网页库仅调试/回退。
- 扫描补 Steam（v0.21.0）只写 `shortcuts.vdf`，需重启 Steam/切用户/重开库页才可见；模拟器未安装不自动下载；PC 找不到 exe/ROM 会跳过并记 `shortcut_error`。
- 存储位置选择依赖 `/proc/mounts` 与 proot 内可写权限；Android 的 `/storage/emulated/0` 等路径可见性/可写性因设备而异，插件不自动挂载/格式化；不会检测 Steam 库同盘。
- 扫描已安装依赖 proot 内 `settings.install_dir` 可见、目录名与目录标题匹配；只扫一层；v0.21.0 起会自动补建 Steam 快捷方式（模拟器未安装不下载，记 `shortcut_error`；Steam 需重启/切用户/重开库页才显示）；百度扫码要求手机 App 与网络可达 `passport.baidu.com`。
- 本版测试基线：`make test` → 555 passed（2026-11 v0.28.7）。
- 本插件不修改 DroidDeck 自身的启动参数或系统设置，只读写 Steam 用户配置与游戏目录。
