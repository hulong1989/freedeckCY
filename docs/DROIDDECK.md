# 在 DroidDeck 上使用 freedeckCY

[DroidDeck](https://github.com/Droid-Deck/DroidDeck) 是在 Android 手机上运行 SteamOS 运行时的开源项目：它自带 Linux 桌面、Steam 游戏模式，并支持 **[Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) 插件**。freedeckCY 从 v0.4.0 起适配 DroidDeck，v0.6.0 起 GBA 模拟器闭环、v0.7.0 起通用模拟器注册表（GBA/PSP/NDS）、v0.8.0 起 Ludusavi + gamewatch 自动云存档、v0.9.0 起 PS1/FC/MD、v0.10.0 起全部模拟器改为在线下载、v0.11.0 起 10 平台 + 架构能力矩阵（DroidDeck 自动隐藏 3DS/PS2/PS3）、v0.12.0 起安装后自动部署 BIOS/固件并写 portable 配置、v0.13.0 起网页库支持仓库游戏提交（Issue/PR）也可在 DroidDeck 上使用；本文是安装与排障说明。

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
- 打开游戏库页面（QAM 里“游戏列表”或本地 Web UI），搜索/筛选后安装；
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
| 3DS / PS2 / PS3（v0.11.0） | ⚠️ **仅 x86_64，DroidDeck 自动隐藏**：Azahar/PCSX2/RPCS3 官方包没有 arm64，目录白名单过滤后条目与平台筛选条都不出现（不是 bug） |
| 模拟器 BIOS/固件部署（v0.12.0） | ✅ 安装后自动部署 `bios/<platform>/`（支持压缩包，7zz 解压缓存）；aarch64 可用 PS1/NDS/Switch 的部署与 GBA/PSP 全屏配置；PS2/PS3/3DS 仅 x86_64 |
| 仓库游戏提交（v0.13.0） | ✅ 网页库「提交游戏」按钮打开 GitHub Issue 表单；或直接 PR `submissions/*.json`。无设备特定逻辑，DroidDeck 与 Steam Deck 行为一致 |
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
      defaults/runtime/mgba/aarch64/mGBA.AppImage
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

**日志**

- 插件日志：`/tmp/freedeckcy.log`
- 状态：`~/.local/share/freedeckCY/tianyi/state.json`
- 健康检查：`curl 127.0.0.1:59271/_healthz`

## 7. 已知限制

- 未在真机验证：DroidDeck 的 FEX/ARM Proton、不同 Android 机型的存储映射都可能影响结果。
- aarch64 上可安装 **GBA/PSP/NDS/PS1/FC/MD/Switch** 共 7 个平台（mGBA/PPSSPP/melonDS/DuckStation/Mesen2/Eden；v0.6.0~v0.12.0，全部在线下载）；v0.12.0 安装后自动部署 `bios/<platform>/`（含压缩包）并写 portable 配置（PS1/NDS/Switch/GBA/PSP；PS2/PS3/3DS 仅 x86_64）；**3DS/PS2/PS3 官方包仅 x86_64，DroidDeck 上被目录白名单自动隐藏**（条目/筛选条都不出现，见 [ROADMAP.md](ROADMAP.md) 9.8）。**插件包不集成任何模拟器，7 个平台（含 GBA）首次安装都需要联网**从官方 release 下载 arm64 包（包体积约 45MB），离线可手动预置缓存或用 `FREEDECKCY_*_BIN`；**PS1 需自备 BIOS、Switch 需 keys+固件**（setup_hint 提示，缺失不阻断但装完不能直接玩）；各平台只识别各自 ROM 扩展名，不含存档管理；ARM64 上这些平台尚未真机验证。
- **自动云存档边界（v0.8.0）**：只对 gamewatch 检测到"退出"的游戏自动上传，没有自动恢复/冲突策略；模拟器（GBA/PSP/NDS/PS1/FC/MD）存档在模拟器配置目录，暂未纳入清单/Proton 扫描；指纹只看相对路径+大小+mtime（≤5000 文件）；`/proc` 不可用时依赖 `pgrep`；ARM64 上该链路尚未真机验证。
- 仓库游戏提交（v0.13.0）只依赖网页/GitHub，无设备特定逻辑；DroidDeck 上没有额外限制（除了需要能打开 GitHub 的浏览器）。
- DroidDeck 升级/重装 Decky 可能清空插件，需重新导入 zip。
- 本插件不修改 DroidDeck 自身的启动参数或系统设置，只读写 Steam 用户配置与游戏目录。
