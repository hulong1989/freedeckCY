# freedeckCY 后续路线图（ROADMAP）

> 本文件列出本仓库在 **2026-11 三轮工程补全 + v0.1.1 四件套 + v0.2.0 目录/封面 + v0.3.0 全量数据/平台筛选 + v0.3.1 分类清洗/数据体检 + v0.4.0 DroidDeck 适配 + v0.5.0 第一梯队 + v0.6.0 GBA 闭环 + v0.7.0 模拟器注册表 + v0.8.0 自动云存档 + v0.9.0 模拟器六平台 + v0.10.0 模拟器全部在线下载 + v0.11.0 十平台 + 架构能力矩阵 + v0.12.0 模拟器 BIOS/固件部署 + v0.13.0 仓库游戏提交 + v0.14.0 百度网盘官方 OpenAPI + v0.14.1 3DS SteamOS 兼容修复之后**（v0.1.1 落地 compatdata 清理与 `7z t` 校验；v0.2.0 平台字段/封面缓存/分类筛选；v0.3.0 全量目录与平台筛选 UI；v0.3.1 分类清洗 + 数据体检 CI；v0.4.0 Android/ARM64 的 DroidDeck 适配；v0.5.0 目录浏览/分页/排序/已安装页签/诊断导出/更新检查；v0.6.0 GBA 模拟器闭环；v0.6.1/v0.6.2 远程 JSON 目录；v0.7.0 通用模拟器注册表 + PSP/NDS；v0.8.0 Ludusavi + gamewatch 自动云存档；v0.9.0 模拟器扩到 PS1/FC/MD；v0.10.0 模拟器全部在线下载、插件包不集成；v0.11.0 补齐 3DS/PS2/PS3/Switch、10 平台 + 架构白名单；v0.12.0 模拟器 BIOS/固件部署 + portable 配置；v0.13.0 仓库游戏提交（Issue/PR → 目录）；v0.14.0 百度网盘官方 OpenAPI；v0.14.1 3DS（Azahar）SteamOS 兼容修复（优先官方 Flatpak））值得继续做、以及明确不建议做的方向。当前版本 **v0.14.1**。它不是承诺，也不绑定版本；各项给出现状、动机、代价与验收标准，方便二次开发者按需领取。
>
> 背景：上游作者已停止维护，`main` 只是早期版本，Releases 里的百度网盘 / 模拟器 / 资源池代码**不在本仓库**（见 [ARCHITECTURE.md](ARCHITECTURE.md) §2）。
>
> ⚠️ 合规提示：本项目分发的资源链接来自互联网，属于盗版资源分发，违反云盘服务条款并涉及版权风险。本路线图只讨论**工程改进**，不建议部署使用，更不建议扩大资源分发能力。
>
> **已落地（本文件不再列为候选）**：v0.1.1 —— 卸载可选回收 Proton 前缀（§9.2）、`7z t` best-effort 校验 + 自动重下（§9.4）、失败任务「重试」、`make doctor`；v0.2.0/v0.3.0 —— 目录平台字段 + `cover_index.csv` + 封面磁盘缓存 + **全量目录（7084 条 / 11 平台）+ 平台/分类双筛选 UI**（§9.6）；v0.3.1 —— 分类清洗（606 行，「模拟器」606 条）+ `validate_catalog --strict` 进 CI；v0.4.0 —— **DroidDeck（Android/ARM64）适配**：ARM64 运行时/ARM Proton 解析/双 Steam 根/`PACKAGE_ARCH` 打包（见 [DROIDDECK.md](DROIDDECK.md)，尚未真机验证）；v0.5.0 —— **第一梯队**：目录浏览/分页/排序、已安装页签（启动/打开目录/卸载）、诊断 JSON+zip 导出（脱敏）、GitHub 更新检查（1 h 缓存）；v0.6.0 —— **GBA 模拟器闭环**：内置 mGBA AppImage、分享分页找 ROM、启动脚本 + 原生 Steam 快捷方式（不写 Proton）；v0.6.1/v0.6.2 —— **远程 JSON 目录**：`FREEDECKCY_CATALOG_JSON` 读本地/HTTP JSON（远程缓存 6 h、失败回退 CSV，默认关闭）；v0.7.0 —— **通用模拟器注册表**：`EmulatorSpec` 接入 GBA/PSP/NDS，GBA 内置、PSP/NDS 首次安装按需下载官方 AppImage，启动脚本按平台参数生成；v0.8.0 —— **自动云存档**：内置 Ludusavi 清单（53,549 游戏）+ gamewatch 进程检测，游戏退出后只上传该游戏（30 s 防抖、指纹去重 reason=unchanged、设置 `cloud_save_auto_upload` 默认开）；v0.9.0 —— **模拟器扩到 6 平台**：PS1（DuckStation，需自备 BIOS，安装时复制到 DuckStation 目录）、FC/MD（Mesen2，共享缓存、zip 内可执行文件）；v0.10.0 —— **模拟器全部在线下载**：删除 `fetch_emulator.sh`/`make emulator-runtime` 与包内 mGBA，6 个平台（含 GBA）首次安装都从官方 release 下载，包体积约 68MB→45MB，离线可手动预置缓存；v0.11.0 —— **10 平台 + 架构能力矩阵**：新增 3DS（Azahar）/PS2（PCSX2）/PS3（RPCS3）/Switch（Eden）；3DS/PS2/PS3 仅 x86_64，aarch64 上目录白名单自动隐藏（条目/筛选条不出现）；Switch 有 x64/arm64 双包；PS2 BIOS 复制到 PCSX2 两处目录，3DS/PS3/Switch 给 setup 提示；v0.12.0 —— **BIOS/固件部署 + portable 配置**：新增 `emulator_setup.py`，把 `bios/<platform>/`（含压缩包）部署到模拟器目录，写 DuckStation/PCSX2 INI 与 mGBA/PPSSPP 全屏，RPCS3 自动 `--installfw`；部署消息并入安装完成消息；v0.13.0 —— **仓库游戏提交**：Issue 表单 + `submissions/*.json` PR，`submission.py` 校验/兼容平台别名/拒绝重复 shareCode，`merge_submissions.py` 合并进目录 CSV 并归档 `submissions/merged/`；网页库「提交游戏」按钮、CI 校验、`make validate-submissions`；v0.14.0 —— **百度网盘官方 OpenAPI**：OAuth oob 授权 + token 自动刷新、公开分享转存 `/FreedeckTmp`、dlink 下载（专用 Referer/UA）、安装后清理；`provider/share_ctx` 任务分流；**不接 BDUSS/Cookie/CDP**；仓库提交/目录支持百度（`server=b`）；v0.14.1 —— **3DS SteamOS 兼容修复**：Azahar AppImage 有上游 #127/#953 问题，SteamOS 3.9.5 优先 Flathub `org.azahar_emu.Azahar`（自动 remote-add/install，失败回退 AppImage）；3DS wrapper 强制 XWayland；已有 3DS 快捷方式后台自动重写（无需重装）；system files 增 Flatpak 数据目录。

---

## 优先级总览

| # | 事项 | 优先级 | 预估 | 一句话收益 |
|---|---|---|---|---|
| 1 | 拆分 `tianyi_service.py` | P0（工程健康） | 大 | 让 8200 行巨型类可维护、可测试 |
| 2 | CI 增加 `ruff` / `mypy` | P0（工程健康） | 中 | 拦住低级错误与类型漂移 |
| 3 | 云存档 plan/apply 与 HTTP handler 测试 | P1（数据安全） | 中 | 覆盖最容易丢存档的路径 |
| 4 | 去掉 node 依赖（纯 Python 实现） | P1（可部署性） | 中 | 去掉约 90 MB 的 node 运行时与跨架构问题 |
| 5 | release 自动化工作流 | P1（发布质量） | 小 | 可复现地打出可安装 zip |
| 6 | 资源清单更新机制 | P2（内容运营） | 中 | 链接失效时无需重发版 |
| 7 | 诊断页 | P2（可排障性） | 中 | 用户能自助定位"为什么装不上" |
| 8 | i18n | P2（可维护性） | 中 | 中英文可切换、文案集中管理 |
| — | 移植 release 的百度网盘 / 模拟器 / 资源池 | **明确不做** | — | 合规与维护风险大于收益 |

> 另有 9 项来自作者 v0.6 的候选能力（Range 探测、`7z t`、SQLite 任务库、模拟器等），按"性价比 + 工作量"排序见 **§9**；其中明确不采纳的方案见 **§10.2**。

---

## 1. 拆分 `tianyi_service.py`（P0，当前约 8200 行）

**现状**：`py_modules/tianyi_service.py` 约 8200 行、单个 `TianyiService` 类 100+ 方法，覆盖安装、云存档、登录采集、时长、面板缓存等互相独立的职责；此外 `_post_process_completed_task` / `_collect_cloud_save_candidates` 等长函数仍在膨胀。

**为什么**：巨型类导致改动风险高、review 困难、测试只能整体起实例；第二轮的"分组安装 / 重启恢复"是在这个文件里继续叠加的，再拖延拆分成本只会更高。

**代价**：大规模搬迁有回归风险，需要分阶段、保持对外接口不变；短期内 diff 很大；需要同步更新文档里全部 `tianyi_service.py:行号` 引用。

**验收标准**：

- 拆出至少 4 个模块（建议：`install_flow.py`、`cloud_save_flow.py`、`login_flow.py`、`playtime.py`），`TianyiService` 只做编排与状态持有；
- `main.py` / `tianyi_http.py` 的调用面不变（RPC 与 HTTP 契约不动）；
- `make test`（当前 330 个用例）保持全绿，新增用例覆盖搬迁后的模块；
- 单个 Python 文件 < 1500 行；`docs/ARCHITECTURE.md` 的引用与模块图同步更新。

**涉及文件**：`py_modules/tianyi_service.py`、`py_modules/tianyi_http.py`、`docs/ARCHITECTURE.md`。

---

## 2. CI 增加 `ruff` / `mypy`（P0）

**现状**：CI 只有 pytest + 前端构建；Python 侧无静态检查、无类型检查（`ARCHITECTURE.md` P2-21 已记录）。

**为什么**：代码里大量 `Any` / 动态字典，且 `decky` 是注入模块；引入静态检查能在不改行为的前提下拦住未定义名、拼写错误和类型漂移（例如未定义变量、漏 import、未使用变量这类问题正是 ruff 能直接抓到的）。

**代价**：要先消化存量告警，不能一次全开；`decky` 需要 stub（仓库根已有 `decky.pyi` 可复用）；`aiohttp` / 动态 JSON 需要局部 `Any` 或忽略规则；建议按"先 ruff、后 mypy 渐进"推进。

**验收标准**：

- CI 增加 `ruff check` 步骤：首版可只启用高置信规则集（如 `E9,F63,F7,F82` + 未使用 import），基线 0 error；
- CI 增加 `mypy` 步骤：先只检查 `py_modules/` 中已标注类型的模块，允许 `--ignore-missing-imports`，用渐进白名单，不要求一次全绿；
- 本地 `make lint`（新增目标）与 CI 命令一致；
- 文档（DEVELOPMENT.md 提交前检查清单）同步更新。

**涉及文件**：`.github/workflows/ci.yml`、`Makefile`、`docs/DEVELOPMENT.md`、`pyproject.toml`（新增）。

---

## 3. 云存档 plan / apply 与 HTTP handler 测试（P1）

**现状**：单测已覆盖云存档版本时间解析、部分模型与安装链路，但**云存档恢复的 `plan` / `apply`（会真实覆盖文件）与本地 HTTP handler 基本没有测试**；这是全项目最接近"丢数据"的路径。

**为什么**：`plan` 依赖 manifest 的 `source_path` 推断 Proton 相对路径并统计冲突，`apply` 会先备份再覆盖；路径推断/边界校验/失败回滚任何一处回归都会破坏用户存档，靠手工验证不可靠。

**代价**：需要构造 manifest、临时目录、假 7z/下载器与 aiohttp 测试客户端；可能要把文件 IO 进一步抽象成可注入的依赖，测试代码量较大（预计新增 30–50 个用例）。

**验收标准**：

- `plan_cloud_save_restore` 覆盖：正常路径推断、manifest 路径逃逸（`../`）被拒、冲突计数、`selected_entry_ids` 过滤；
- `apply_cloud_save_restore` 覆盖：覆盖前备份命名 `*.freedeckcy-bak-<时间戳>`、失败时已恢复文件计数、playtime 取较大值合并；
- `tianyi_http.py` 的 `handle_cloud_save_*` / `handle_install_*` 覆盖正常与错误响应（含 4xx/5xx 与脱敏字段）；
- 全部离线可跑（不联网、不写真实 Steam 目录），`make test` 全绿。

**涉及文件**：`tests/`、`py_modules/tianyi_service.py`、`py_modules/tianyi_http.py`。

---

## 4. 去掉 node 依赖（P1）

**现状**：分享解析兜底（`backend/tianyi_share_resolver.js`）与云存档上传（`backend/tianyi_cloud_upload.js`）走 Node 子进程；`make runtime` 会把 Node v20 打进 zip（x86_64 单文件约 94 MB，aarch64 需另下）。

**为什么**：Node 运行时是包体积与跨架构复杂度的最大来源；SteamOS 默认不带 Node，用户若不用 `make runtime` 就会在云存档时失败；Node ESM/ABI 兼容问题也是已知坑。

**代价**：需要在 Python 侧实现 AES-128-ECB 加密、RSA 公钥加密、MD5/HMAC 签名与 10 MB 分片上传；Decky 自带 Python 不保证有 `cryptography` / `pycryptodome`，要么自带纯 Python 实现（性能/复杂度），要么引入 vendored 库；Node 兜底应保留为开关，便于对比与回滚。

**验收标准**：

- 在**没有 node** 的环境下，云存档上传 / 列版本 / 下载、分享解析兜底全部可用（用 Python 实现，Node 实现保留为 `FREEDECKCY_CLOUD_IMPL=node` 之类的回退）；
- 上传结果与现有 Node 实现一致（同一测试账号下文件名、分片、`sliceMd5` 校验通过）；
- `make runtime` 可选择不再下载 node（`--only aria2,7z`），zip 体积显著下降；
- 新增实现有离线单测（签名/crypto 用固定向量）。

**涉及文件**：`py_modules/tianyi_client.py`、`backend/*.js`、`scripts/fetch_runtime.sh`、`docs/DEVELOPMENT.md`。

---

## 5. release 自动化工作流（P1）

**现状**：发布靠手动 `make runtime && make package` 产出 `dist-artifacts/freedeckCY-v<version>.zip`；仓库没有 tag/release CI（本次补全只加了测试与前端构建的 CI）。

**为什么**：运行时二进制较大且来源外网，手工打包容易漏 `defaults/runtime/` 或忘记重建 `dist/index.js`；自动化可以产出可复现、带校验和的安装包。

**代价**：GitHub Actions runner 需要能下载 aria2/7z/node（涉及外网与体积，需缓存策略）；版本号/发布说明需要约定；产物校验（sha256）与签名策略要定。

**验收标准**：

- 推送 `v*` tag（或手动 `workflow_dispatch`）触发：pytest → `pnpm build` → `make runtime` → `make package` → 上传 zip + `sha256sum` 到 GitHub Release；
- 产物结构用 `unzip -l` 校验（`main.py`、`plugin.json`、`dist/`、`py_modules/`、`backend/`、`defaults/` 齐全，`docs/`、`tests/` 不进入包）；
- 打出的包能在 Steam Deck 上通过 Decky Loader 安装并启动（人工验收一次）；
- 版本号与 `package.json` 联动，release notes 模板化。

**涉及文件**：`.github/workflows/`、`Makefile`、`scripts/package.sh`、`docs/DEVELOPMENT.md`。

---

## 6. 资源清单更新机制（P2）

**现状**：资源清单 `defaults/tianyi_catalog/*.csv` 随插件分发，更新链接必须改仓库重新打包发版；失效链接只能用户报错后手工修。

**为什么**：分享链接会失效/换提取码，而清单是插件的核心数据；一个可校验、可回滚的更新机制能显著降低维护成本。

**代价**：需要确定可信分发渠道与完整性校验（签名/hash），否则等于给插件加了"远程下发任意链接"的攻击面；还要处理缓存、并发更新与回滚；若做自动拉取，会进一步放大版权与合规风险。

**验收标准（务实版）**：

- 支持"手动导入本地 CSV"：校验表头/`down_url` 域名/重复 `game_id` → 通过后原子替换当前清单并保留旧版备份；
- 可选"从固定 URL 拉取"：必须带 `sha256` 校验、失败自动回滚到旧清单、默认关闭且需用户显式开启；
- 更新过程有日志与 UI 结果提示；不引入后台常驻网络请求；
- 文档明确合规风险，默认行为不改变"随包分发"。

**涉及文件**：`py_modules/game_catalog.py`、`py_modules/tianyi_service.py`、`py_modules/tianyi_http.py`、`defaults/tianyi_catalog/`。

---

## 7. 诊断页（P2）

**现状**：`/_healthz`、`/tmp/freedeckcy.log`、v0.1.1 的**只读 CLI** `make doctor`（运行时/Steam/state/日志/端口/网络），以及 v0.5.0 的 **`GET /api/tianyi/diagnostics` + `/diagnostics/export`（脱敏 zip）**；但仍没有多页面的图形化诊断面板，排障仍需用户发诊断包/输出。

**为什么**：把"环境自检"可视化能显著降低支持成本，也方便开发者在 Steam Deck 上快速确认部署是否正确。

**代价**：新增页面（Vue 或纯 HTML）+ 聚合接口；必须严格脱敏（Cookie / 直链 / 路径中的用户名），并且只允许回环访问。

**验收标准**：

- 新增 `/tianyi/diagnostics` 页面（仅 `127.0.0.1`）：展示插件版本、Python/前端构建版本、aria2c/7zz/node 的路径与是否可执行、Steam 根目录与识别到的库、`compatdata` 定位结果、`state.json` 路径与权限、最近 N 条错误摘要；
- 不显示 Cookie、分享链接、完整直链等敏感内容（可用长度/域名代替）；
- 有自动化测试覆盖"未登录 / 缺运行时 / 多库"等场景的字段；
- DEVELOPMENT.md 增加"让用户提供诊断页截图"的排障流程。

**涉及文件**：`py_modules/tianyi_http.py`、`py_modules/tianyi_service.py`、`defaults/tianyi_library_ui/`、`docs/DEVELOPMENT.md`。

---

## 8. i18n（P2）

**现状**：界面与错误消息全中文硬编码在 `src/index.tsx`、`defaults/tianyi_library_ui/`、Python 返回值与日志里（`ARCHITECTURE.md` P2-22）。

**为什么**：英文用户无法使用；文案集中后也更容易维护与统一术语。

**代价**：前端 React 侧可接 `i18next` 之类方案，Vue 无构建页面需要轻量字典；Python 侧返回给前端的中文消息应改为"错误码 + 参数"，由前端翻译，否则两端各维护一套文案；工作量大且要持续同步。

**验收标准**：

- 至少 `zh-CN` / `en-US` 两套文案；语言可配置/自动跟随系统，持久化到设置；
- 前端所有用户可见文案来自字典（`src/index.tsx` 与 `defaults/tianyi_library_ui/` 无硬编码中文）；
- Python 关键错误提供稳定 `reason` 错误码，前端能翻译；未知错误回退原文；
- 文档与测试同步（至少覆盖语言切换与缺 key 回退）。

**涉及文件**：`src/index.tsx`、`defaults/tianyi_library_ui/`、`py_modules/tianyi_http.py`、`py_modules/tianyi_service.py`、`docs/`。

---

## 9. v0.6 对齐候选（9.2 / 9.4 已落地；9.6 已在 v0.3.0 完成；9.8 的 10 平台模拟器已在 v0.6.0~v0.11.0 完成；9.9 百度 OpenAPI 已在 v0.14.0 完成；其余未做）

作者 v0.6 发行版（本地只读参考 `0.6/freedeck-plugin`，不随本仓库分发）在下载管线、模拟器与资源池上完整得多。三轮补全只采纳了下载/Steam 写入相关的少数能力（见 [ARCHITECTURE.md](ARCHITECTURE.md) §13）；**v0.1.1 落地 9.2（compatdata 清理）与 9.4（`7z t` best-effort 校验）；v0.2.0 起步 9.6；v0.3.0 完成 9.6（全量目录 7084 条 / 11 平台 + cover_index 3470 行 + 平台/分类双筛选 UI）；v0.3.1 做数据质量（分类清洗 + validate_catalog --strict CI）**，其余按 **性价比 + 工作量** 从高到低排列，供后续认领。

| # | 候选 | 优先级 | 工作量 | v0.6 出处 | 一句话收益 |
|---|---|---|---|---|---|
| 9.1 | Range 续传探测 | P1 | 小 | `_remote_supports_resume()` | 避免对不支持续传的直链做无效重试 |
| 9.2 | ~~compatdata 卸载清理~~ ✅ | ~~P1~~ | ~~小~~ | `uninstall_installed_game(delete_compatdata=)` | **已在 v0.1.1 落地**：卸载可选回收 Proton 前缀 |
| 9.3 | 自动重启 Steam | P1 | 小 | `main.py::restart_steam` | 写完快捷方式即可生效，不用手动重启 |
| 9.4 | ~~`7z t` 全量归档校验~~ ✅ | ~~P1~~ | ~~中~~ | `archive_validator.test_archive` | **已在 v0.1.1 落地（best-effort）**：解压前发现坏包并自动重下 |
| 9.5 | SQLite 任务库 | P2 | 大 | `archive_task_db.py` | 任务持久化/查询与崩溃恢复更可靠 |
| 9.6 | ~~平台目录 + 封面索引~~ ✅ | ~~P2~~ | ~~大~~ | `gba_catalog.py` 等 + `generate_*_cover_urls.py` | **v0.3.0 完成**（7084 条/11 平台 + cover_index + 双筛选），**v0.3.1 数据清洗/体检**；封面生成流水线仍未做 |
| 9.7 | 资源池只读 | P2 | 中 | 腾讯文档 smartsheet 读取 | 扩充资源，但不引入投稿/点赞 |
| 9.8 | ~~单平台模拟器闭环~~ ✅（10 平台，全部在线下载 + BIOS/固件部署） | ~~P2~~ | ~~大~~ | `emulator_adapters.py` | **v0.6.0 GBA、v0.7.0 PSP/NDS、v0.9.0 PS1/FC/MD、v0.10.0 全部在线下载、v0.11.0 3DS（Azahar）/PS2（PCSX2）/PS3（RPCS3）/Switch（Eden）、v0.12.0 BIOS/固件部署 + portable 配置（含压缩包、RPCS3 `--installfw`）**；3DS/PS2/PS3 官方包仅 x86_64（aarch64 自动隐藏）；PS1/PS2 BIOS、3DS/PS3/Switch 系统文件由用户自备 |
| 9.9 | ~~百度 OpenAPI~~ ✅（v0.14.0） | ~~P3~~ | ~~大~~ | `baidu_openapi_client.py` | **v0.14.0 已完成**：OAuth oob + token 自动刷新、公开分享转存 `/FreedeckTmp`、dlink 下载（专用 Referer/UA）、安装后清理；`provider/share_ctx` 任务分流；**不接 BDUSS/Cookie/CDP**；仓库提交/目录支持百度（`server=b`） |

### 9.1 Range 续传探测（P1，工作量：小）

**v0.6 参考**：`_remote_supports_resume()` 对直链发 `Range: bytes=0-0`，只有返回 206 / `Content-Range` / `Accept-Ranges: bytes` 才认为可续传。

**为什么**：当前"直链过期 → 重新 addUri"默认服务端支持断点续传；不支持的线路会一直重试同一段，浪费时间与请求。

**代价**：每个需要恢复的任务多一次探测请求；探测失败要保守按"支持"处理，避免误判导致重下。

**验收标准**：

- 新增 `probe_resume_support(direct_url, headers)`：解析 206 / `Content-Range` / `Accept-Ranges`，异常时返回 True（保守续传）；
- 仅**恢复/换链路径**调用一次，正常下载不额外探测；结果写日志；
- 离线单测覆盖 206 / 200+Accept-Ranges / 200 无头 / 异常四种情况；
- DEVELOPMENT 故障排查补一句"日志里 `resume unsupported` 表示该线路不支持续传"。

**涉及文件**：`py_modules/tianyi_service.py`、`py_modules/tianyi_client.py`、`tests/`、`docs/DEVELOPMENT.md`。

### 9.2 ~~compatdata 卸载清理~~（✅ 已在 v0.1.1 落地）

**落地实现（v0.1.1）**：

- `steam_shortcuts.find_compatdata_dirs(app_id)` 跨所有 Steam 库定位 `<library>/steamapps/compatdata/<appid>`；
- `tianyi_service.preview_uninstall()` + `preview_tianyi_uninstall` RPC 返回安装目录与 Proton 前缀占用；QAM 卸载确认框显示两者大小，三按钮：取消 / 仅删游戏文件 / 连 Proton 前缀一起删（默认不删）；
- `uninstall_installed_game(delete_compatdata=...)` 返回 `compatdata: {requested, app_id, paths, removed_paths, freed_bytes}`；
- 路径安全：`_can_remove_compatdata_dir()` 只允许标准 `steamapps/compatdata/<appid>` 结构、拒绝符号链接，appid 由 `_resolve_record_app_id()` 从记录或快捷方式解析。

**仍未做**：`shadercache` / `compatdata` 以外的 per-appid 残留不做自动清理；默认不删的语义保持不变。

### 9.3 自动重启 Steam（P1，工作量：小）

**v0.6 参考**：`main.py::_restart_steam_best_effort()`，通过用户会话 `systemctl --user restart steam-launcher.service`（必要时 `sudo -u <user>`）。

**为什么**：写 `shortcuts.vdf` 后必须重启 Steam 才可见；手动重启对掌机用户门槛高。

**代价**：重启 Steam 会打断正在运行的游戏/下载；必须用户显式触发、检测 Steam 是否在运行，且**不能引入 root**（仅用 deck 用户会话；`sudo` 分支不采纳）。

**验收标准**：

- QAM 设置页/安装完成提示里提供"重启 Steam"按钮（显式点击，不自动）；
- 通过 `systemctl --user restart steam-launcher.service`（设置 `XDG_RUNTIME_DIR` / `DBUS_SESSION_BUS_ADDRESS`），失败时给出"请手动重启"提示；
- 拒绝在 Steam 有运行中游戏时执行（或二次确认）；
- 单测覆盖命令构造与失败分支（不真正重启）；文档写清副作用。

**涉及文件**：`main.py`、`py_modules/tianyi_service.py`、`src/index.tsx`、`tests/`。

### 9.4 ~~`7z t` 全量归档校验~~（✅ 已在 v0.1.1 落地，best-effort）

**落地实现（v0.1.1）**：

- `SevenZipManager.test_archive()` 在解压前对主卷执行 `7z t`（默认超时 900 s）；**7z 缺失或无法执行时返回"跳过校验"，不阻断安装**（后续解压仍需要可用 7z）；
- 校验失败 → `_schedule_archive_repair()`：隔离坏包（`*.freedeckcy-archive-invalid-*`）+ 原直链自动重下一次（每任务一次，`post_processed` 不置真）；重下完成后自动重新安装；
- 第二次仍失败 → 任务 `failed`，用任务行「重试」按钮人工重试；
- 单测覆盖：校验成功 / 失败 / 7z 不可执行跳过 / 自动重下与二次失败路径。

**仍未做**：没有 hash/签名校验；超时与"按体积跳过校验"暂未做成可配置项（当前固定 900 s 超时、始终尝试）；`7z t` 会多读一遍大包，属已知开销。

### 9.5 SQLite 任务库（P2，工作量：大）

**v0.6 参考**：`archive_task_db.py`（SQLite + WAL + 资源/文件任务表）。

**为什么**：`state.json` 全量重写、并发写要靠内存锁；任务多/崩溃时容易丢最后状态。SQLite 可做原子更新、历史查询与恢复。

**代价**：要设计 schema、迁移现有 `state.json`、保留兼容读取；引入数据库文件权限/备份/清理策略；测试量明显增加。

**验收标准**：

- 新库 `~/.local/share/freedeckCY/tianyi/tasks.db`（0700 目录 / 0600 文件），WAL 模式；
- 首次启动自动从 `state.json` 迁移任务与已安装记录，失败回退 JSON；
- 任务状态更新为行级 UPSERT，不再整文件重写；崩溃后重启能恢复到最近一致状态；
- 单测覆盖迁移、并发更新、损坏库回退；README/DEVELOPMENT 说明两个文件的职责。

**涉及文件**：`py_modules/tianyi_store.py`（或新增 `task_store.py`）、`py_modules/tianyi_service.py`、`tests/`、`docs/`。

### 9.6 ~~平台目录 + 封面索引~~（✅ 已在 v0.3.0 完成，v0.3.1 数据清洗）

**落地实现（v0.3.0 / v0.3.1）**：

- **全量目录**：`defaults/tianyi_catalog/freedeckcy_catalog.csv`（16 列，**7084 条有效 / 11 平台**：PC 2540 / FC 1475 / NDS 722 / PSP 575 / GBA 553 / 3DS 305 / PS2 250 / PS1 194 / PS3 194 / MD 191 / Switch 85）；旧 `gamebox_all_links_*.csv` 保留为回退；
- **可复现**：`scripts/merge_v06_catalog.py` 从上游 v0.6 目录（7041 行 / 28 列）合并生成，补 43 条旧目录独有条目；
- **封面索引**：`defaults/tianyi_catalog/cover_index.csv`（3470 行，来自 v0.6），按 `game_id`/标题补齐、不覆盖已有值；合并后 **6823 / 7084 条资源自带封面**；
- **封面缓存**：`cover_cache.json`（0600，正缓存 7 天 / 负缓存 30 分钟），优先级"目录静态 → 缓存 → Steam 商店 → ProtonDB"；
- **平台/分类双筛选 UI**：库页两行筛选条（全部平台 + 各平台；全部分类 + Top12 分类），手柄焦点顺序 搜索框→搜索按钮→平台条→分类条→卡片；
- **链接格式**：`_is_valid_tianyi_url()` / `parse_share_url()` 支持 `/t/<code>` 与 `/web/share?code=` 两种天翼分享链接；
- **数据质量（v0.3.1）**：`normalize_categories()` 加载时清洗分类（去平台名/去重/模拟器兜底），数据 606 行改写、「模拟器」606 条；`scripts/validate_catalog.py --strict` 进 CI，重复 `game_id`/非法链接/空标题/分类混平台名会让 CI 红；
- 测试：`make test` 330 用例（含 `tests/test_catalog_platform.py` / `tests/test_droiddeck.py` / `tests/test_emulator.py` / `tests/test_cloud_auto.py` / `tests/test_submissions.py` / `tests/test_baidu_integration.py` 与分类清洗/默认目录洁净度用例）。

**仍未做**：封面索引的**生成流水线**（`generate_*_cover_urls.py` 类脚本；当前 index 直接来自 v0.6）、无网络时纯离线封面库；模拟器 10 平台已全部接入（见 9.8）。

### 9.7 资源池只读（P2，工作量：中，**合规风险高**）

**v0.6 参考**：腾讯文档 smartsheet 资源池（`get_qqdocs_login_url` / `_decode_qqdocs_smartsheet_blob` / `list_resource_pool_catalog`）。

**为什么**：资源池能补充失效清单；只读模式比"投稿/点赞"风险低。

**代价**：依赖腾讯文档登录态与私有解析；内容来源不可控、合规风险仍高；需要缓存与筛选（防止恶意链接）。

**验收标准**：

- 只读：仅拉取/解析资源池目录（需要腾讯文档登录态，或支持手工导出表格导入），**不实现投稿、点赞与 CDP 自动操作**（不采纳项见 §10.2）；
- 默认关闭、显式开启；解析结果先落到本地缓存文件，人工可审查；不自动混入主清单；
- 校验 `down_url` 域名/重复项；单测用固定 fixture，不联网；
- 文档显著标注版权/合规风险。

**涉及文件**：`py_modules/tianyi_service.py`、`py_modules/game_catalog.py`、`defaults/`、`tests/`、`docs/`。

### 9.8 ~~单平台模拟器闭环~~（✅ 10 平台已完成，全部在线下载；v0.12.0 BIOS/固件部署完成）

**落地实现（v0.6.0 起 / v0.7.0 注册表 / v0.9.0 六平台 / v0.10.0 全部在线下载 / v0.11.0 十平台）**：

- `py_modules/emulator_manager.py` 的 `EmulatorSpec` 注册表当前接入 **10 个平台**：
  - GBA = mGBA 0.10.5（x64/arm64，首次安装在线下载）；
  - PSP = PPSSPP 1.20.4、NDS = melonDS 1.1、PS1 = DuckStation（需 BIOS）、FC/MD = Mesen2 2.1.1（共享缓存）；
  - **3DS = Azahar 2126.2（仅 x86_64，需 system files）**；
  - **PS2 = PCSX2 v2.8.2（仅 x86_64，需 BIOS）**；
  - **PS3 = RPCS3 build-8d6b42e（仅 x86_64，需固件）**；
  - **Switch = Eden v0.2.1（x86_64 + aarch64，需 prod.keys + 固件）**；
- **架构能力矩阵**：`available_platforms(arch)` 按 `spec.assets` 过滤——x86_64 可用全部 10 个；aarch64（DroidDeck）只有 GBA/PSP/NDS/PS1/FC/MD/Switch，3DS/PS2/PS3 **没有 arm64 官方包**，目录查询用白名单过滤后条目与平台筛选条都不出现（`emulator_status` 返回"已隐藏该平台"）；
- 解析顺序（无内置包分支）：`FREEDECKCY_<PLATFORM>_BIN` → 已下载/已解包（`emulators/<state_key>/<arch>/`）→ 系统命令 → Flatpak（mGBA 的 `io.mgba.mGBA`；3DS 用 `org.azahar_emu.Azahar`，SteamOS 自动安装）；`emulator_status` 可按需返回 `source=download`，安装时 `ensure_emulator` 下载并按 AppImage/zip 分别解包（不依赖 FUSE）；
- BIOS/固件部署（v0.12.0）：`emulator_setup.setup_emulator()` 扫描 `bios/<platform>/`（含 `.zip/.7z/.rar`，7zz 解压到 `_extracted/` 缓存），部署到各模拟器目录并写 portable 配置（PS1 `<AppDir>/bios`+DuckStation INI、PS2 三处 BIOS+PCSX2 INI、NDS bios/firmware、Switch keys/`.nca`、PS3 `--installfw`、3DS sysdata、GBA/PSP 全屏配置）；只补缺失/只改单个键，部署消息并入安装完成消息；
- **v0.10.0 打包变化**：`scripts/fetch_emulator.sh` 与 `make emulator-runtime` 删除、`defaults/runtime/mgba/` 不再打包，插件包不集成模拟器（约 68MB→45MB）；离线可手动预置缓存或用 `FREEDECKCY_*_BIN`；
- **v0.14.1 3DS SteamOS 修复**：Azahar 官方 AppImage 在 SteamOS 有上游 #127/#953 兼容问题，SteamOS 3.9.5 上优先 Flathub Flatpak `org.azahar_emu.Azahar`（`_is_steamos`/`flatpak_installed`/`_ensure_flatpak`，自动 `remote-add` + `install`，失败重试 system 安装后回退 AppImage）；3DS wrapper 强制 XWayland（`QT_QPA_PLATFORM=xcb`/`SDL_VIDEODRIVER=x11`）；已安装 3DS 记录由后台 `_repair_emulator_launchers` 自动重写启动脚本，无需重装；system files 增 Flatpak 数据目录；测试 330；
- 测试 `tests/test_emulator.py` / `tests/test_catalog_platform.py`（架构白名单、目录计数、3DS Flatpak/wrapper）；`make test` 330 用例。

**剩余 / 边界**：3DS Flatpak 真机验证（SteamOS 3.9.5/Deck）、无 Flatpak 环境的 AppImage 兼容增强（如自带 runtime/依赖）、模拟器真机验证（DroidDeck/ARM64）、模拟器存档纳入云存档、多碟游戏（`.m3u`/多 `.cue`）与 BIOS/固件版本校验；BIOS/固件/keys 由用户自备（版权原因，插件只部署不下载）；3DS/PS2/PS3 的 arm64 官方包不存在，ARM 设备无法安装；所有已接平台**不含存档管理**。

**涉及文件**：`py_modules/emulator_manager.py`、`py_modules/game_catalog.py`（`allowed_platforms` 白名单）、`py_modules/tianyi_service.py`、`defaults/tianyi_library_ui/`、`tests/test_emulator.py`、`tests/test_catalog_platform.py`、`docs/`。

### 9.9 ~~百度 OpenAPI~~（✅ v0.14.0 完成；网页 Cookie/CDP 不做）

**已完成（v0.14.0）**：

- 只走**官方 OpenAPI**：百度网盘开放平台自建应用 → App Key/Secret → OAuth `oob` 授权码 → access/refresh token（过期自动 refresh，auth 错误强制刷新重试）；state 顶层 `baidu_openapi`；
- `provider` 分流：`_share_provider()` 识别 `pan.baidu.com`/`yun.baidu.com`/`eyun.baidu.com` → `baidu_openapi`；安装计划不要求天翼登录；任务记录带 `provider/share_url/share_ctx`；
- 分享转存 `/FreedeckTmp` → `fetch_baidu_openapi_download_url()` 取 dlink → aria2（`Referer=https://pan.baidu.com/disk/home`、`UA=pan.baidu.com`、空 cookie）；重试按 provider 重新取 dlink；
- 安装结束 `_cleanup_baidu_transfer_files()` 调 `delete_baidu_openapi_transfer_file()` 清理转存，避免占网盘；
- QAM「百度网盘（官方 OpenAPI）」区 + HTTP `/api/tianyi/baidu/openapi/{authorize-url,app,exchange,clear}` + `main.py` 4 个 callable；env `FREEDECKCY_BAIDU_OPENAPI_{APP_KEY,SECRET_KEY,REFRESH_TOKEN}`；
- 仓库提交/目录支持百度链接（`server=b`，Issue 表单/schema/示例同步）；测试 326 用例。

**明确不做（本次及后续）**：

- 网页 Cookie / BDUSS 抓取、CDP 投稿或下载——v0.6 的失败路径不再维护；
- 公共应用/内置 App Key（每个人自建应用并授权）；
- 绕过百度限速、转存配额/风控的“加速”能力。

**剩余增强（可选）**：转存失败/配额满的分级重试与提示、dlink 过期预刷新、分享失效自动检测、多账号切换；均非必需，按实际反馈再做。

---

## 10. 明确不建议做

### 10.1 移植 release 的百度网盘 / 模拟器整合 / 资源池

- **理由 1（合规）**：这些功能会进一步扩大盗版资源的分发面（新增网盘源、模拟器 ROM 分区、用户上传资源池），版权与云盘服务条款风险显著高于现状。
- **理由 2（来源）**：这些功能的代码只存在于上游 Releases 的二进制包里，**不在本仓库**，没有可维护的源码基线；逆向/重写成本高且无法跟随上游修复。
- **理由 3（工程）**：本仓库的补全目标是"让现有能力可维护、可构建、可测试"，新增资源分发渠道与该目标冲突，会稀释有限维护精力。
- **结论**：不移植、不内置、不提供接入指引；如确需扩展，应先解决版权合规问题，并作为独立项目维护。

### 10.2 不采纳 v0.6 的具体方案

- **`plugin.json` 的 `flags: ["root"]` + `steam_host_writer` + `sudo -u deck` 写 Steam 文件**：v0.6 让插件以 root 运行，再用 helper 降权写文件。本插件始终以 deck 用户运行，引入 root 会扩大权限面、增加 Decky 审核/误用风险；当前"同用户原子写 + 写前备份 + 写后回读"已够用（见 ARCHITECTURE §13.3）。
- **腾讯文档资源池的点赞 / 投稿**：需要腾讯文档登录态 + CDP 投稿（`_submit_resource_pool_entry_via_cdp` 等），属于用户生成内容/运营功能，显著扩大合规面；只读版本作为 §9.7 候选保留。**投稿需求改走 v0.13.0 的仓库 Issue/PR 通道（§9.10）**，不碰腾讯文档登录态。
- **百度网页版 CDP 采集 / 未公开接口**：需采集网页登录态并逆向网页接口，维护成本与封号风险高；本仓库已走 §9.9 的官方 OpenAPI（v0.14.0），**仍不做** BDUSS/Cookie 抓取与 CDP。
- **为了"对齐 v0.6"而退回"仅主库"**：v0.6 不解析 `libraryfolders.vdf`、`compatdata` 只在主库找；本仓库已支持多库/SD 卡/Flatpak，**明确不回退**。

### 10.3 其他不做项

- 不做任何绕过云盘限速/风控的"加速"能力（现状已是"不设上限"，不额外优化）；
- 不收集用户数据、不上报使用统计；
- 不内置资源搜索/推荐等运营功能（只读随包 CSV 或 §9.7 的只读资源池缓存）。

---

## 其他小项（P3 候选）

| 事项 | 说明 | 验收要点 |
|---|---|---|
| 自动云存档（Ludusavi + gamewatch）✅ | **v0.8.0 已落地**：内置 Ludusavi 清单（53,549 游戏，MIT）做标题/SteamID 匹配并解析到 Proton 前缀，与原有 Proton 扫描合并；gamewatch 每 8 s 检测游戏退出，只上传**刚退出的那个 game_id**（30 s 防抖）；指纹（相对路径+size+mtime，≤5000 文件）持久化去重，未变化 `reason=unchanged`；设置 `cloud_save_auto_upload` 默认开、QAM 可关。**仍未做**：自动恢复/冲突策略、模拟器（GBA/PSP/NDS/PS1/FC/MD）存档纳入、跨设备同步/版本保留策略 | 已完成；后续按"仍未做"继续 |
| 第一梯队：目录浏览 / 分页 / 排序 / 已安装管理 / 诊断导出 / 更新检查 ✅ | **v0.5.0 已落地**：库页打开即浏览全部资源（空查询不再隐藏）、平台/分类筛选 + 分页（L1/R1、PageUp/PageDown）+ 排序（默认/名称/大小↓/大小↑）、已安装页签（鼠标点击启动 / 打开目录 / 卸载 confirm）、自定义双按钮 confirm、`GET /catalog?sort=`、`/installed*`、`/diagnostics`+`/diagnostics/export`（zip，cookie/token/HOME 脱敏）、`/update-check`（GitHub release，1 h 缓存） | 已完成；体验小项（已安装页签键盘/手柄启动接线）继续迭代 |
| DroidDeck 适配 ✅ | **v0.4.0 已落地**：ARM64 运行时选择（`make runtime ARCH=aarch64`）、`is_droiddeck()` 检测、ARM Proton 自动解析（`droiddeck-proton-arm64`/`11-arm64`）、双 Steam 根（x64 客户端优先）、`PACKAGE_ARCH` 打包（`-arm64`/`-universal`）。**尚未真机验证**；模拟器在 aarch64 可用 GBA/PSP/NDS/PS1/FC/MD/Switch（v0.11.0），3DS/PS2/PS3 因无 arm64 官方包被目录白名单自动隐藏（§9.8） | 真机验证通过后回归本项；详见 [DROIDDECK.md](DROIDDECK.md) |
| 目录数据体检 / 分类清洗 ✅ | **v0.3.1 已完成**：`normalize_categories` + `normalize_catalog_categories.py` 清洗 606 行，`validate_catalog.py --strict` 进 CI（封面覆盖 96.3%，总大小约 39 TB） | 已完成，后续仅在数据变更时复用 `make normalize-catalog` / `make validate-catalog` |
| 日志路径可配置 | 目前写死 `/tmp/freedeckcy.log`（已轮转） | 支持 `FREEDECKCY_LOG_FILE`，非法路径回退默认；文档同步 |
| 下载完整性升级为 hash | 目前只比对 `file_size` | 清单提供 sha256 时校验；不提供时保持现状 |
| `7z t` 之外的归档增强 | §9.4 落地后，再评估非标准分卷命名识别 | 归档预检错误码统一、可读 |
| `make doctor` 自检 | 用一条命令检查运行时/Steam 路径/state 权限 | 与诊断页共享同一套检测函数，CI 不跑（依赖真实环境） |

---

## 参考

- 架构与问题清单：[ARCHITECTURE.md](ARCHITECTURE.md)
- 与作者 v0.6 的能力对照：[ARCHITECTURE.md](ARCHITECTURE.md) §13
- 本地开发、调试、故障排查：[DEVELOPMENT.md](DEVELOPMENT.md)
- 当前测试基线：`make test` → 330 passed（2026-11 v0.14.1）
