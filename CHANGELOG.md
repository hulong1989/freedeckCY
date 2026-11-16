# Changelog

本项目从 v0.1.0 起使用独立版本号（fork 自 Freedeck，与上游 0.2–0.3 不连续）。

## v0.21.0

### 变更

- **「扫描已安装」移到设置**：QAM 设置 → 安装 → 扫描已安装游戏；原生游戏库「已安装」页不再放扫描按钮。
- **扫描后自动补 Steam 库**：
  - 扫描目录匹配到游戏后，`list_all_shortcuts_sync()` 检查 Steam 里是否已有同名/同 exe 快捷方式；
  - 没有则自动创建 freedeckCY 快捷方式（PC 自动找 `.exe`，优先 openpath；模拟器用已安装模拟器生成 wrapper，不自动下载）；
  - 对状态库已存在、但 `steam_app_id=0` 的旧记录也会补建；
  - 结果返回 `steam_added/steam_recovered_count`，设置页提示补建数量。
- 扫描仍以设置里的 `install_dir` 为根，一层子目录、目录名匹配标题。

### 变更

- 测试 351 → 352（扫描自动补 Steam 快捷方式）。

## v0.20.0

### 新增

- **Decky 原生游戏库（不再依赖网页）**：新增 `/freedeckcy/library` 路由，
  QAM 主页「游戏库」直接打开原生页面：
  - 游戏库：搜索、平台/分类/排序、分页、封面/标题/大小/分类展示，逐条安装；
  - 安装确认弹窗：下载/安装大小、目标目录、模拟器/BIOS 提示；
  - 已安装：启动、打开目录、卸载、扫描已安装；
  - 全部通过 Decky callable（`list_tianyi_catalog` / `prepare_tianyi_install` /
    `start_tianyi_install` / `list_tianyi_installed_games` / `launch/open/uninstall`）
    调用，不经过本地 HTTP 网页，也不受网页 CORS/浏览器限制。
- 扫描仍以设置里的「安装目录」为根目录；只扫一层、目录名需匹配标题。

### 变更

- QAM 主页「游戏库」按钮改为 `Navigation.Navigate("/freedeckcy/library")`；
  原本地网页库保留为备用，但不再是默认入口。
- 测试仍 351（新增为前端构建验证）。

## v0.19.2

### 修复

- **Deck 上百度扫码 TLS 证书失败**：诊断包确认 `SSLCertVerificationError: unable to get local issuer certificate`
  （SteamOS/Python 证书链问题）。v0.19.1 只给 `getqrcode` 加了 TLS/urllib 回退，本版补齐：
  - `fetch_qr_image()`：aiohttp 失败后用未校验 SSL 的 urllib 重试；
  - `poll_qr()`：先系统证书，失败后 `ssl=False` 重试；
  - `complete_login()`：同样两层 TLS 回退；
  - 全部失败时返回具体异常/HTTP 状态。
- 诊断包中版本仍为 0.18.0；更新到 0.19.2 后重新扫码即可。

### 变更

- 版本 0.19.1 → 0.19.2；测试仍 351。

## v0.19.1

### 修复

- **获取百度二维码失败**：`baidu_qr.request_qr()` 现在：
  - aiohttp 先使用系统证书；失败后重试跳过证书校验；
  - 仍失败则回退标准库 `urllib`（解决部分 Decky/SteamOS 环境 aiohttp TLS/CA 不可用）；
  - 错误消息带具体异常类型/HTTP 状态/响应片段，QAM 不再只显示笼统失败。
- 移除二维码前的 passport 首页预请求，避免多一次超时/风控；轮询与换 Cookie 仍按原流程。

### 变更

- 版本 0.19.0 → 0.19.1；测试仍 351。

## v0.19.0

### 新增

- **下载/安装目录支持 SD 卡选择**：
  - 新增 `storage_options.py`：解析 `/proc/mounts`，识别 `/run/media/*`（SteamOS SD）、`/media/*`、`/mnt/*`、`/storage/*`（DroidDeck）等可写挂载点，带剩余/总容量。
  - QAM 的「下载目录」「安装目录」下直接显示 SD 卡按钮：一键切到
    `<挂载点>/freedeckCY/downloads` / `<挂载点>/freedeckCY/installed`。
  - 没有检测到可写外置存储时显示提示；仍保留原来的目录选择器。
  - API：`GET /api/tianyi/storage/options`；main callable `get_tianyi_storage_options`。

### 变更

- 测试 349 → 351（SD/外置挂载识别、系统挂载过滤）。

## v0.18.0

### 新增

- **扫描已安装游戏**：网页库「已安装」页签新增「扫描已安装」按钮；后端扫描安装目录，
  按目录名匹配目录标题，把旧版本/手动安装、但状态库缺失的游戏补回已安装列表；
  能匹配 Steam 快捷方式时回填 AppID，支持启动/打开目录/卸载。
  - API：`POST /api/tianyi/installed/scan`
  - CLI/Decky callable：`scan_tianyi_installed_games`
  - 返回新增/跳过/未匹配数量，截断展示前 24 个，避免大目录卡 UI。

### 修复

- **百度扫码登录失败更可诊断**：二维码请求/轮询/换 Cookie 会保留 HTTP 状态与响应片段，
  QAM 失败状态直接显示具体错误；二维码会话增加 BAIDUID Cookie 并在轮询/换 Cookie 时复用，
  降低风控环境下的失败率。

### 变更

- 测试 348 → 349（扫描已安装回填）。

## v0.17.1

### 修复

- **Decky「从文件安装 ZIP」无反应**：Decky 对 `version=dev` 的本地 ZIP 会查找
  `顶层目录/plugin.json`（路径中恰好一个 `/`）；旧包把 `plugin.json` 放在 zip 根目录，
  Decky 静默 `return`，表现为点安装没反应。现在打包统一为：
  ```
  freedeckCY/
    main.py plugin.json package.json ...
  ```
  已用 ZipFile 校验 `freedeckCY/plugin.json` 命中 Decky 规则。
- 同步 `scripts/package.sh` 的结构校验（顶层只能有一个 `freedeckCY/`）与文档。

## v0.17.0

### 新增

- **百度网盘扫码登录（BDUSS/Cookie）**：
  - `passport.baidu.com` 二维码 + 长轮询 + `qrbdusslogin`，扫码确认后保存 `BDUSS/STOKEN/PTOKEN`，不依赖开放平台 App Key。
  - QAM「百度网盘（扫码登录）」：二维码直接显示、已扫码/已确认状态、取消/退出登录。
  - 百度链接优先走 Cookie 链路（`provider=baidu`）：`resolve_baidu_share` + `fetch_baidu_download_url`，aria2 带百度 Cookie/Referer/UA。
  - 没有 Cookie 时仍可回退到 OpenAPI（`provider=baidu_openapi`，需要 App Key）；OpenAPI 继续保留在设置里作为可选。
- 新增 HTTP API：`/api/tianyi/baidu/qr/{start,poll,cancel}`、`/api/tianyi/baidu/clear`。

### 变更

- `BaiduLoginState`（cookie/user_account/updated_at）持久化；面板增加 `baidu_login`。
- 测试 345 → 348（Cookie provider 计划/任务、扫码登录流程）。
- 实测 `getqrcode` 能返回二维码图片、`unicast` 未扫码时返回等待；扫码确认需要真机手机验证。

### 说明

- 二维码/轮询来自百度网页版接口，不是官方 OpenAPI；Cookie 失效需重新扫码。
- Cookie 仅存本地 state（0600），不写入日志/诊断。

## v0.16.0

### 新增

- **模拟器存档恢复**：
  - 同机恢复优先回到原路径；跨设备/路径不存在时回到平台默认存档根目录；只允许写入已知模拟器存档目录，防止恶意 manifest 写入 HOME 任意位置。
  - 覆盖已有文件前自动备份（`*.freedeckcy-bak-<时间戳>`），冲突需要确认。
  - 共享记忆卡逐个文件恢复，不再直接拒绝整个 `emulator_saves`。
- **共享存档按游戏拆分**：
  - PSP/PS3：读存档内 `PARAM.SFO` 的 `TITLE`，只把匹配当前游戏的 `SAVEDATA/<id>` / `savedata/<id>` 纳入该游戏。
  - 3DS：从 NCSD 头 `0x108` 读 Program ID，只匹配 `title/00040000/<titleid>` 目录。
  - PS1/PS2 单片记忆卡、Switch 存档目录暂无法按游戏拆分，仍按共享目录处理（恢复会整卡覆盖，需确认）。
- **PS1 多碟 `.m3u`**：
  - 安装目录内有多张 `.cue`/`.chd` 时自动生成 `freedeckcy-multidisc.m3u`（自然排序），DuckStation 直接启动合集。
  - 已有 `.m3u` 优先；单碟仍直接返回 `.cue`。

### 变更

- 测试 337 → 345。

## v0.15.0

### 新增

- **模拟器存档纳入云存档**：自动发现 GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch 的存档/记忆卡，随游戏退出自动上传；`source_strategy=emulator_saves`。
  - 单游戏存档（GBA/FC/MD/NDS）按 ROM 文件名匹配，避免把同目录其它游戏一起打包。
  - PSP/PS1/PS2/3DS/PS3/Switch 为共享记忆卡/标题目录，按路径签名去重，避免每个游戏重复上传。
  - 覆盖标准目录、portable 目录、Flatpak 数据目录（mGBA/PPSSPP/DuckStation/PCSX2/Azahar）。
  - QAM 新增「包含模拟器存档」开关（默认开）；关闭后只上传 PC/Proton 存档。

### 变更

- 测试 330 → 337（新增模拟器存档发现与开关用例）。

### 说明

- 目前只做**上传**；云端模拟器存档的恢复路径映射尚未做（PC 存档恢复不变）。

## v0.14.1

### 修复

- **3DS（Azahar）在 SteamOS 3.9.5 无法启动**：
  - SteamOS 上优先使用官方 **Flatpak（Flathub `org.azahar_emu.Azahar`）**，首次安装时自动 `flatpak remote-add` + `flatpak install`；Flatpak 自带运行时，避开官方 AppImage 在 Steam Deck 上的 glibc/AppImage 兼容问题。
  - 非 SteamOS / 无 Flatpak 环境回退官方 AppImage；`FREEDECKCY_AZAHAR_BIN` 优先于 Flatpak。
  - 3DS 启动脚本强制 `QT_QPA_PLATFORM=xcb`、`SDL_VIDEODRIVER=x11`，规避 Game Mode/Wayland 崩溃。
  - 3DS system files 增加 Flatpak 数据目录：`~/.var/app/org.azahar_emu.Azahar/data/{azahar,azahar-emu}/sysdata`。
  - 已安装的 3DS 游戏在插件启动后自动修复启动脚本（AppImage → Flatpak），无需重装游戏。
- 测试 326 → 330。

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
