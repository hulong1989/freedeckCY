# freedeckCY 后续路线图（ROADMAP）

> 本文件列出本仓库在 **2026-11 三轮工程补全之后**（第三轮参考作者 v0.6 发行版对齐了部分下载/Steam 集成能力）值得继续做、以及明确不建议做的方向。它不是承诺，也不绑定版本；各项给出现状、动机、代价与验收标准，方便二次开发者按需领取。
>
> 背景：上游作者已停止维护，`main` 只是早期版本，Releases 里的百度网盘 / 模拟器 / 资源池代码**不在本仓库**（见 [ARCHITECTURE.md](ARCHITECTURE.md) §2）。
>
> ⚠️ 合规提示：本项目分发的资源链接来自互联网，属于盗版资源分发，违反云盘服务条款并涉及版权风险。本路线图只讨论**工程改进**，不建议部署使用，更不建议扩大资源分发能力。

---

## 优先级总览

| # | 事项 | 优先级 | 预估 | 一句话收益 |
|---|---|---|---|---|
| 1 | 拆分 `tianyi_service.py` | P0（工程健康） | 大 | 让 7200 行巨型类可维护、可测试 |
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

## 1. 拆分 `tianyi_service.py`（P0，当前约 7200 行）

**现状**：`py_modules/tianyi_service.py` 约 7200 行、单个 `TianyiService` 类 100+ 方法，覆盖安装、云存档、登录采集、时长、面板缓存等互相独立的职责；此外 `_post_process_completed_task` / `_collect_cloud_save_candidates` 等长函数仍在膨胀。

**为什么**：巨型类导致改动风险高、review 困难、测试只能整体起实例；第二轮的"分组安装 / 重启恢复"是在这个文件里继续叠加的，再拖延拆分成本只会更高。

**代价**：大规模搬迁有回归风险，需要分阶段、保持对外接口不变；短期内 diff 很大；需要同步更新文档里全部 `tianyi_service.py:行号` 引用。

**验收标准**：

- 拆出至少 4 个模块（建议：`install_flow.py`、`cloud_save_flow.py`、`login_flow.py`、`playtime.py`），`TianyiService` 只做编排与状态持有；
- `main.py` / `tianyi_http.py` 的调用面不变（RPC 与 HTTP 契约不动）；
- `make test`（当前 215 个用例）保持全绿，新增用例覆盖搬迁后的模块；
- 单个 Python 文件 < 1500 行；`docs/ARCHITECTURE.md` 的引用与模块图同步更新。

**涉及文件**：`py_modules/tianyi_service.py`、`py_modules/tianyi_http.py`、`docs/ARCHITECTURE.md`。

---

## 2. CI 增加 `ruff` / `mypy`（P0）

**现状**：CI 只有 pytest + 前端构建；Python 侧无静态检查、无类型检查（`ARCHITECTURE.md` P2-19 已记录）。

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

**现状**：只有 `/_healthz` 与 `/tmp/freedeckcy.log`；排障需要用户会 `curl`、会看日志，常见问题（缺运行时、Steam 路径不对、state 权限异常）都要来回问答。

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

**现状**：界面与错误消息全中文硬编码在 `src/index.tsx`、`defaults/tianyi_library_ui/`、Python 返回值与日志里（`ARCHITECTURE.md` P2-20）。

**为什么**：英文用户无法使用；文案集中后也更容易维护与统一术语。

**代价**：前端 React 侧可接 `i18next` 之类方案，Vue 无构建页面需要轻量字典；Python 侧返回给前端的中文消息应改为"错误码 + 参数"，由前端翻译，否则两端各维护一套文案；工作量大且要持续同步。

**验收标准**：

- 至少 `zh-CN` / `en-US` 两套文案；语言可配置/自动跟随系统，持久化到设置；
- 前端所有用户可见文案来自字典（`src/index.tsx` 与 `defaults/tianyi_library_ui/` 无硬编码中文）；
- Python 关键错误提供稳定 `reason` 错误码，前端能翻译；未知错误回退原文；
- 文档与测试同步（至少覆盖语言切换与缺 key 回退）。

**涉及文件**：`src/index.tsx`、`defaults/tianyi_library_ui/`、`py_modules/tianyi_http.py`、`py_modules/tianyi_service.py`、`docs/`。

---

## 9. v0.6 对齐候选（本轮未做）

作者 v0.6 发行版（本地只读参考 `0.6/freedeck-plugin`，不随本仓库分发）在下载管线、模拟器与资源池上完整得多。本轮只采纳了下载/Steam 写入相关的少数能力（见 [ARCHITECTURE.md](ARCHITECTURE.md) §13），以下按 **性价比 + 工作量** 从高到低排列，供后续认领。

| # | 候选 | 优先级 | 工作量 | v0.6 出处 | 一句话收益 |
|---|---|---|---|---|---|
| 9.1 | Range 续传探测 | P1 | 小 | `_remote_supports_resume()` | 避免对不支持续传的直链做无效重试 |
| 9.2 | compatdata 卸载清理 | P1 | 小 | `uninstall_installed_game(delete_compatdata=)` | 卸载后回收 Proton 前缀空间 |
| 9.3 | 自动重启 Steam | P1 | 小 | `main.py::restart_steam` | 写完快捷方式即可生效，不用手动重启 |
| 9.4 | `7z t` 全量归档校验 | P1 | 中 | `archive_validator.test_archive` | 解压前发现坏包，避免"解到一半失败" |
| 9.5 | SQLite 任务库 | P2 | 大 | `archive_task_db.py` | 任务持久化/查询与崩溃恢复更可靠 |
| 9.6 | 平台目录 + 封面索引 | P2 | 大 | `gba_catalog.py` 等 + `generate_*_cover_urls.py` | 多平台资源目录与封面本地化 |
| 9.7 | 资源池只读 | P2 | 中 | 腾讯文档 smartsheet 读取 | 扩充资源，但不引入投稿/点赞 |
| 9.8 | 单平台模拟器闭环 | P2 | 大 | `emulator_adapters.py` | 打通一个模拟器平台的下载→安装→启动 |
| 9.9 | 百度 OpenAPI | P3 | 大 | `baidu_openapi_client.py` | 新增一个"干净"的网盘来源 |

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

### 9.2 compatdata 卸载清理（P1，工作量：小）

**v0.6 参考**：`uninstall_installed_game(..., delete_compatdata=delete_proton_files)`，返回 `proton_files_deleted`。

**为什么**：一个 Proton 前缀动辄几百 MB～数 GB；只删游戏目录会让 `steamapps/compatdata/<appid>` 长期占盘。

**代价**：误删会丢存档/配置，必须做成显式选项（默认关）、严格校验 appid 与路径归属。

**验收标准**：

- 卸载 RPC/HTTP 增加 `delete_compatdata` 选项（默认 false），UI 二次确认；
- 只允许删 `steamapps/compatdata/<appid>` 且 appid 来自本插件安装记录 / 快捷方式解析；删除前校验路径在任一 Steam 库内；
- 返回 `compatdata_deleted` 字段；失败不影响游戏目录卸载；
- 单测覆盖"正常删除 / 非本插件 appid 拒绝 / 路径越界拒绝"。

**涉及文件**：`py_modules/tianyi_service.py`、`py_modules/steam_shortcuts.py`、`py_modules/tianyi_http.py`、`src/index.tsx`、`tests/`。

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

### 9.4 `7z t` 全量归档校验（P1，工作量：中）

**v0.6 参考**：`archive_validator.test_archive()` 在解压前执行 `7zz t <entry>`，配合签名/HTML 预检与超时。

**为什么**：当前只做"文件大小 + 头部预检"；坏包（截断、串包、加密）仍可能解到一半失败，浪费已下载流量与解压时间。

**代价**：大包 `7z t` 要额外读一遍（分钟级），需要超时与"跳过校验"开关；解压链路要多一次子进程调用与错误码映射。

**验收标准**：

- 解压前对主卷执行 `7zz t`（带超时、可配置跳过；>N GB 时提示耗时）；
- 校验失败映射为可读原因（签名错误/截断/密码/工具缺失），不再进入解压；
- 单测用假 7z 脚本覆盖成功/失败/超时；DEVELOPMENT 故障排查补"归档校验失败"处置；
- 多分卷场景只测主卷（与 7z 行为一致）。

**涉及文件**：`py_modules/tianyi_service.py`、`py_modules/seven_zip_manager.py`、`tests/`、`docs/DEVELOPMENT.md`。

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

### 9.6 平台目录 + 封面索引（P2，工作量：大）

**v0.6 参考**：`gba_catalog.py` / `ps1_catalog.py` / `ps3_catalog.py` 等平台目录 + `generate_*_catalog_cover_urls.py` / `emulator_cover_pipeline.py` 封面生成。

**为什么**：当前只有一份 PC 资源 CSV + 在线封面解析；多平台目录与离线封面索引能减少网络依赖、提升库页加载。

**代价**：要定义多平台 CSV schema、生成流程（脚本/CI）与数据体积控制；封面版权与 CDN 失效问题需要处理。

**验收标准**：

- 先落地**一个平台**（建议 PS1/GBA 之一）的目录格式 + 封面索引生成脚本，生成物可复现（固定输入 → 固定输出）；
- 加载端按 `platform` 字段分流，不影响现有 PC 目录；
- 无网络时库页仍能显示本地封面索引；单测覆盖索引读取与回退；
- 数据来源/版权说明写入文档，不内置 ROM/镜像。

**涉及文件**：`defaults/tianyi_catalog/`、`py_modules/game_catalog.py`、新增脚本（`scripts/`）、`tests/`。

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

### 9.8 单平台模拟器闭环（P2，工作量：大，**合规风险高**）

**v0.6 参考**：`emulator_adapters.py`（Eden/DuckStation/PCSX2/PPSSPP/RPCS3/mGBA/Lime3DS/melonDS/Nestopia/BlastEm/MAME）+ 平台目录 + 封面流水线。

**为什么**：模拟器是 v0.6 的主要差异化能力；先打通一个平台可验证"目录→下载→解压→配置→快捷方式"闭环。

**代价**：每个模拟器配置差异大；ROM/BIOS 的版权风险极高；需要模拟器安装检测、配置写入与 Proton/原生启动适配。

**验收标准**：

- 只选**一个**平台（建议 PS1 + DuckStation 或 GBA + mGBA）做闭环：识别模拟器可执行文件 → 定位 ROM 目录 → 生成 Steam 快捷方式 → 可启动；
- 不内置模拟器/BIOS/ROM，只做"用户自备文件"的配置与启动；
- 端到端人工验收一次 + 配置生成单测；
- **先完成合规评审**再决定是否扩大平台数量（当前建议不扩大）。

**涉及文件**：`py_modules/`（新增 emulator 模块）、`defaults/`、`src/index.tsx`、`scripts/`、`tests/`、`docs/`。

### 9.9 百度 OpenAPI（P3，工作量：大，**合规风险高**）

**v0.6 参考**：`baidu_openapi_client.py`（OAuth2 + xpan/file / multimedia / nas 接口）。

**为什么**：比网页版 CDP 采集干净、稳定；可作为天翼之外的第二来源。

**代价**：需要注册开发者应用、处理 OAuth 回调与 token 刷新；用户需授权；接口有配额/审核；仍属资源分发面扩张，合规风险高。

**验收标准**：

- 只做 provider 抽象与"分享解析 + 直链"最小闭环，不做转存/上传；
- token 存 `state.json` 时加密或至少 0600，支持刷新与撤销；
- 用户显式授权、默认关闭；失败回退天翼/清晰报错；
- 单测 mock OAuth/接口；文档写明申请流程与风险。

**涉及文件**：`py_modules/tianyi_client.py`（provider 抽象）、新增 `baidu` 模块、`backend/`、`tests/`、`docs/`。

> CTFile / Quark 等其它来源同理：先评估公开 API 与合规成本，再决定是否走同一 provider 抽象；本轮不排期。

---

## 10. 明确不建议做

### 10.1 移植 release 的百度网盘 / 模拟器整合 / 资源池

- **理由 1（合规）**：这些功能会进一步扩大盗版资源的分发面（新增网盘源、模拟器 ROM 分区、用户上传资源池），版权与云盘服务条款风险显著高于现状。
- **理由 2（来源）**：这些功能的代码只存在于上游 Releases 的二进制包里，**不在本仓库**，没有可维护的源码基线；逆向/重写成本高且无法跟随上游修复。
- **理由 3（工程）**：本仓库的补全目标是"让现有能力可维护、可构建、可测试"，新增资源分发渠道与该目标冲突，会稀释有限维护精力。
- **结论**：不移植、不内置、不提供接入指引；如确需扩展，应先解决版权合规问题，并作为独立项目维护。

### 10.2 不采纳 v0.6 的具体方案

- **`plugin.json` 的 `flags: ["root"]` + `steam_host_writer` + `sudo -u deck` 写 Steam 文件**：v0.6 让插件以 root 运行，再用 helper 降权写文件。本插件始终以 deck 用户运行，引入 root 会扩大权限面、增加 Decky 审核/误用风险；当前"同用户原子写 + 写前备份 + 写后回读"已够用（见 ARCHITECTURE §13.3）。
- **腾讯文档资源池的点赞 / 投稿**：需要腾讯文档登录态 + CDP 投稿（`_submit_resource_pool_entry_via_cdp` 等），属于用户生成内容/运营功能，显著扩大合规面；只读版本作为 §9.7 候选保留。
- **百度网页版 CDP 采集 / 未公开接口**：需采集网页登录态并逆向网页接口，维护成本与封号风险高；如要做百度，只考虑 §9.9 的 OpenAPI 路线。
- **为了"对齐 v0.6"而退回"仅主库"**：v0.6 不解析 `libraryfolders.vdf`、`compatdata` 只在主库找；本仓库已支持多库/SD 卡/Flatpak，**明确不回退**。

### 10.3 其他不做项

- 不做任何绕过云盘限速/风控的"加速"能力（现状已是"不设上限"，不额外优化）；
- 不收集用户数据、不上报使用统计；
- 不内置资源搜索/推荐等运营功能（只读随包 CSV 或 §9.7 的只读资源池缓存）。

---

## 其他小项（P3 候选）

| 事项 | 说明 | 验收要点 |
|---|---|---|
| 日志路径可配置 | 目前写死 `/tmp/freedeckcy.log`（已轮转） | 支持 `FREEDECKCY_LOG_FILE`，非法路径回退默认；文档同步 |
| 下载完整性升级为 hash | 目前只比对 `file_size` | 清单提供 sha256 时校验；不提供时保持现状 |
| `7z t` 之外的归档增强 | §9.4 落地后，再评估非标准分卷命名识别 | 归档预检错误码统一、可读 |
| `make doctor` 自检 | 用一条命令检查运行时/Steam 路径/state 权限 | 与诊断页共享同一套检测函数，CI 不跑（依赖真实环境） |

---

## 参考

- 架构与问题清单：[ARCHITECTURE.md](ARCHITECTURE.md)
- 与作者 v0.6 的能力对照：[ARCHITECTURE.md](ARCHITECTURE.md) §13
- 本地开发、调试、故障排查：[DEVELOPMENT.md](DEVELOPMENT.md)
- 当前测试基线：`make test` → 215 passed（2026-11 第三轮补全后）
