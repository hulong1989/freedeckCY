# 在 DroidDeck 上使用 freedeckCY

[DroidDeck](https://github.com/Droid-Deck/DroidDeck) 是在 Android 手机上运行 SteamOS 运行时的开源项目：它自带 Linux 桌面、Steam 游戏模式，并支持 **[Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) 插件**。freedeckCY 从 v0.4.0 起适配 DroidDeck，本文是安装与排障说明。

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

## 2. 构建 ARM64 插件包

在开发机（Linux/macOS 均可）执行：

```bash
cd freedeckCY
make runtime ARCH=aarch64      # 下载 ARM64 版 aria2c / 7zz / node
make package-droiddeck         # 产出 dist-artifacts/freedeckCY-v<version>-arm64.zip
```

说明：

- `make runtime ARCH=all` 可以同时准备 x86_64 与 aarch64 两份运行时。
- `PACKAGE_ARCH=aarch64` 打包时会自动裁剪掉其它架构的运行时，避免包体积翻倍。
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
- 打开游戏库页面（QAM 里“游戏列表”或本地 Web UI），搜索/筛选后安装。

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
| 模拟器平台（FC/NDS/PSP/GBA/…） | ⚠️ 只可浏览，暂不可安装（与 Steam Deck 相同） |
| `make doctor` | ⚠️ 需要 DroidDeck 桌面终端；Android 上 `lsof` 可能不存在 |

## 5. 环境变量与设置

| 变量/设置 | 作用 |
|---|---|
| `FREEDECKCY_STEAM_ROOT` | 指定 Steam 根目录（DroidDeck 双客户端时手动锁定） |
| `FREEDECKCY_PROTON_TOOL` | 覆盖 Proton 工具名；`none` 表示不写映射 |
| `FREEDECKCY_ARIA2_BIN` / `FREEDECKCY_7Z_BIN` / `FREEDECKCY_NODE_BIN` | 覆盖运行时二进制路径 |
| 设置项 `proton_tool` | `auto`（默认，自动判断）/ `none` / 具体工具名 |

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
      defaults/runtime/node/aarch64/bin/node
```

缺哪个就重新 `make runtime ARCH=aarch64` 并重新打包；也可用环境变量指向系统里的 arm64 版本。

**日志**

- 插件日志：`/tmp/freedeckcy.log`
- 状态：`~/.local/share/freedeckCY/tianyi/state.json`
- 健康检查：`curl 127.0.0.1:59271/_healthz`

## 7. 已知限制

- 未在真机验证：DroidDeck 的 FEX/ARM Proton、不同 Android 机型的存储映射都可能影响结果。
- 模拟器平台暂不可安装（见 ROADMAP 9.8）。
- DroidDeck 升级/重装 Decky 可能清空插件，需重新导入 zip。
- 本插件不修改 DroidDeck 自身的启动参数或系统设置，只读写 Steam 用户配置与游戏目录。
