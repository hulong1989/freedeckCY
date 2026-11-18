# Changelog

本项目从 v0.1.0 起使用独立版本号（fork 自 Freedeck，与上游 0.2–0.3 不连续）。

## v0.27.0

### 游戏库全面改版（三阶段）

- 第一阶段：
  - 响应式封面网格（auto-fill，适配全屏/QAM 宽度）
  - 重做游戏卡片：2:3 封面、独立标题区、来源角标、已安装角标
  - 骨架屏、封面渐变占位、懒加载
- 第二阶段：
  - Hero 推荐区（最近更新/封面背景）
  - 顶部工具栏合并：返回/Steam 库、标题、页签、搜索、筛选、刷新
  - 平台/分类/排序收进可折叠筛选面板
  - 分类货架加大卡片、横向滚动
  - 详情页改为大幅海报 + 背景 + 下载源卡片
- 第三阶段：
  - 已安装游戏改卡片网格（封面/时长/目录/卸载）
  - 焦点外发光/缩放动效
  - `content-visibility`、分页加载、图片懒加载
- 保留单/双网盘选择、安装、已安装管理全部逻辑。
- 测试 554 passed。

## v0.26.51

### 取消 QAM 标识

- 移除主面板「QAM 原生 UI v...」标识。
- 移除游戏库标题下「原生 UI · v...」标识。
- 界面不再显示构建版本/QAM 字样，版本仍可在诊断和包信息中查看。
- 测试 554 passed。

## v0.26.50

### 安装目录增加内置硬盘

- 设置 → 路径 → 安装目录新增「安装到 内置硬盘」按钮。
- 内置安装目录固定为 `~/Games/freedeckCY`。
- 安装目录与下载目录都可以在内置硬盘、SD 卡、外置存储之间切换。
- 测试 554 passed。

## v0.26.49

### 下载目录增加内置硬盘

- 设置 → 路径 → 下载目录新增「下载到 内置硬盘」按钮。
- 内置硬盘下载目录固定为 `~/Downloads`。
- 内置硬盘选项始终显示，不再只显示 SD/外置存储。
- 测试 553 passed。

## v0.26.48

### 百度登录链路检查与增强

- 扫码登录成功后保留 `BAIDUID/BAIDUID_BFESS` 等会话 Cookie，降低后续分享风控概率。
- `qrbdusslogin` 未返回 BDUSS 时，错误信息附带 errno。
- 扫码获取/轮询实时接口验证通过。
- 百度分享转存/下载链路与 freedeck-go 对照检查。
- 测试 552 passed。

## v0.26.47

### 单网盘条目与卡片来源提示

- 明确支持只有天翼或只有百度的单网盘目录条目，不要求双网盘。
- 双网盘才合并显示下载源选择；单网盘直接使用对应来源。
- 游戏卡片副标题显示来源：`大小 · 天翼云盘 / 百度网盘`。
- 新增单百度条目测试；552 passed。

## v0.26.46

### 双网盘游戏选择下载源

- 目录记录新增 `server` / `provider` 字段。
- 同一标题、同一平台、不同网盘的条目合并为一个游戏。
- 游戏详情页显示「下载源」：
  - 天翼云盘
  - 百度网盘
  - 用户选择后按对应 game_id 生成安装计划。
- 修复 `game_catalog.py` 百度链接校验缺少 `urlparse`，导致百度目录条目被误判无效。
- 新增双网盘/同网盘重复条目测试；551 passed。

## v0.26.45

### 更新包固定下载到内置硬盘

- 插件更新包固定保存到本机 `~/Downloads`。
- 不再跟随 SD 卡/外置存储的下载目录设置。
- 游戏本体的下载目录不变。
- 新增下载目录测试；测试 549 passed。

## v0.26.44

### 修复手动检查更新被缓存

- 手动点「检查更新」强制绕过缓存。
- 自动检查缓存从 1 小时缩短到 2 分钟。
- 更新检查优先自有服务器，服务器不可用才回退 GitHub。
- 测试 548 passed。

## v0.26.43

### P0 工程健康

- 新增前端 hooks 依赖作用域检查 `scripts/check-ui-scope.mjs`：
  - 检查 useMemo/useCallback/useEffect 依赖数组中的未定义标识符
  - CI UI job 与 `make check-ui` 执行
  - 防止再次出现 `batchBusy is not defined`
- 拆分 `tianyi_service.py` 第一块：更新检查/下载流程迁移到 `py_modules/update_flow.py` 的 `UpdateFlowMixin`。
- 新增更新流程契约测试；测试 548 passed。

## v0.26.42

### 从自有服务器检查插件更新

- 更新检查优先请求目录服务器：
  - `GET /api/update/latest`
  - `GET /api/update/latest.json.sig`
- 使用现有 Ed25519 公钥验签更新清单。
- 更新包从服务器 `/api/update/asset/...` 下载并校验 SHA256。
- 自有服务器不可用时回退 GitHub Release。
- 需要 Web 系统 1.3.0+ 并在后台发布更新清单。
- 测试 546 passed。

## v0.26.41

### GitHub 更新证书降级

- 更新检查先用内置 CA 校验证书。
- 仅当证书链失败时，对 GitHub API/Release 下载降级一次。
- 降级会写入 `tls_insecure`，设置页显示“TLS 证书校验失败，已降级”。
- 连接超时/HTTP 错误不降级。
- 其他请求继续强制证书校验。
- 测试 546 passed。

## v0.26.40

### 修复内置 CA 未生效

- 内置 `cacert.pem` 改为最高优先级，避免 Decky 的 `SSL_CERT_FILE` 指向不完整 CA。
- 百度/二维码/更新检查共用同一优先级。
- 新增“环境变量指向坏 CA 时仍使用内置 CA”测试；测试 546 passed。

## v0.26.39

### 内置服务器地址但不显示

- 内置目录服务器地址改为编码存放，设置页不回显。
- 用户留空时后台自动使用内置地址。
- 用户手动填写 `catalog_url` 后覆盖内置地址。
- 清空后恢复内置地址。
- 测试 545 passed。

## v0.26.38

### 修复插件更新证书错误

- 内置 `cacert.pem` CA bundle，兼容 Decky Python 缺少系统 CA 的环境。
- 更新检查、Release SHA256 下载统一使用 `build_tls_context()`。
- 修复：
  `CERTIFICATE_VERIFY_FAILED unable to get local issuer certificate`
- 新增 CA bundle 测试；测试 544 passed。

## v0.26.37

### CI 修复

- `@decky/ui` 恢复 4.11.0，与 pnpm-lock.yaml 保持一致。
- 修复 v0.26.36 CI `ERR_PNPM_OUTDATED_LOCKFILE`。
- 其余功能与 v0.26.36 相同。

## v0.26.36

### 修复百度扫码后无法登录

- 轮询先判断 `channel_v.status`：
  - `status=1` 只表示已扫码，不再提前换 BDUSS；
  - `status=0` 才算手机确认。
- `qrbdusslogin` 响应同时从 JSON `data.session` 和 `Set-Cookie` 读取 `BDUSS/STOKEN/PTOKEN`。
- auth hop 补充 `BDUSS` Cookie，确保拿到 pan.baidu.com 的 `STOKEN`。
- 新增扫码状态回归测试；测试 543 passed。

## v0.26.35

### 移除内置服务器地址

- 插件不再内置真实服务器地址。
- 目录地址改为在 设置 → 路径 → 游戏目录 中填写。
- `FREEDECKCY_CATALOG_CSV_URL` 仍可作为无头环境覆盖。
- 客户端会保留已保存的 `catalog_url`；没有配置时跳过自动检查。

### 恢复设置面板

- 重新加回百度登录健康检查、插件内更新入口。
- 修复设置页 `batchBusy is not defined` 后，面板依赖仅引用 SettingsPage 变量。
- 测试 541 passed。

## v0.26.34

### 恢复百度健康检查与插件更新面板

- 设置页 ReferenceError 修复后，重新加回：
  - 百度登录健康检查
  - 插件内更新
- 新增 state/useCallback 只加入 SettingsPage 自己的依赖数组，避免再次混入 Content 变量。
- 测试 541 passed。

## v0.26.33

### 修复设置页 ReferenceError

- 修复 `SettingsPage` 的 tabs useMemo 依赖数组误混入 Content 变量：
  `batchBusy` / `speedDraft` / `onPauseAllTasks` / `onResumeAllTasks` / `onApplySpeedLimit`
- 该问题导致打开设置页报：
  `ReferenceError: batchBusy is not defined`
- 恢复正常 SettingsPage 路由，移除诊断 ErrorBoundary。
- 测试 541 passed。

## v0.26.32

### 设置页错误边界

- 恢复真实 SettingsPage 路由。
- 外层增加 React ErrorBoundary：
  - 捕获渲染错误
  - 在设置页直接显示 error.message / stack
  - 不再只显示 Decky Shared SteamUI 通用错误
- 用于精确定位设置页崩溃组件。

## v0.26.31

### 设置页最小诊断

- 设置路由临时替换为一行纯文本 `freedeckCY settings diagnostic`。
- 用于判断崩溃来自 SettingsPage 内部，还是插件路由/注入。
- 其他路由与功能保留。

## v0.26.30

### Decky 3.3.1 兼容性测试

- 设置页保持 v0.26.29 的 v0.26.25 结构。
- `@decky/ui` 从 4.11.0 升级到 4.16.5 重建。
- 用于验证 Decky/SteamUI 新版本兼容性。

## v0.26.29

### 设置页完全回退验证

- 完整删除 v0.26.26/27 新增的设置页 state/useCallback，而不只是隐藏 UI。
- 设置页 Hook 结构恢复为 v0.26.25。
- 百度健康检查、插件更新后端逻辑保留。
- 用于确认设置页 React 异常是否由新增 Hook 引起。

## v0.26.28

### 设置页稳定模式

- 临时隐藏 v0.26.26/27 新增的「百度登录检查」和「插件更新」设置面板。
- 后端健康检查/更新下载仍保留，待定位设置页 React 渲染异常后重新接入 UI。
- 用于验证设置页崩溃是否由新增面板引起。

## v0.26.27

### 插件内更新

- 设置 → 诊断新增「插件更新」：
  - 检查 GitHub 最新 Release
  - 显示当前/最新版本
  - 下载并校验当前架构的更新包
- 更新包支持 GitHub API digest 或 Release `.sha256` 校验；缺少校验值拒绝下载。
- 下载到下载目录，不自动覆盖运行中的插件；按提示用 Decky「从文件安装插件」升级。
- 测试 541 passed。

## v0.26.26

### 百度登录健康检查

- 设置 → 百度网盘新增「检查登录状态」。
- 检查 BDUSS、STOKEN、账号信息、bdstoken、`/FreedeckTmp` 访问。
- 明确提示：
  - 登录已失效 → 重新扫码
  - 缺少 STOKEN → 重新扫码补齐
  - 转存目录未创建 → 首次下载会自动创建
- 检查结果逐项显示状态，不泄露 Cookie。
- 测试 541 passed。

## v0.26.25

### 百度网盘对齐 freedeck-go

- 打开分享前先 `share/verify`，用 `BDCLND` cookie 打开分享页；提取码分享更稳定。
- 根目录与子目录都分页（100/页），修复模拟器合集只取第一页导致文件缺失。
- 转存前创建 `/FreedeckTmp`，使用 `ondup=overwrite`，并补充 `channel/web/clienttype` 参数。
- 转存目标路径优先由文件名推导，异步 task 不返回 `to` 时不再失败。
- 安装成功后删除 `/FreedeckTmp` 临时文件（网页百度和 OpenAPI 都清理）。
- 扫码登录参数对齐 netdisk；登录后补调 passport auth 获取 pan 侧 STOKEN。
- 测试 540 passed。

## v0.26.24

### 目录签名 / 更新提醒 / 免重启尝试

- 目录 CSV 增加 Ed25519 验签：
  - 下载 `catalog.csv.sig` 并用内置公钥校验
  - 签名缺失或校验失败 → 保留本地目录
- Web 1.2.0 起自动生成签名；审核通过/上传目录后重新签名。
- 目录自动更新后，QAM 弹窗提示新增游戏，并清除提示状态。
- Steam 快捷方式安装后新增「免重启刷新」按钮：
  - 尝试调用 `SteamClient.Apps.Refresh/RefreshApps/RefreshLibrary`
  - 不支持时提示手动重启，保留原重启按钮
- 测试 540 passed。

## v0.26.23

### 内置目录服务器

- 插件内置默认目录地址：
  `https://你的目录服务器/catalog.csv`
- 启动时自动检查该地址，有更新才下载，失败回退本地 CSV。
- 设置页 `catalog_url` 为空时显示内置地址；仍可手动覆盖。
- 最近更新 shelf、新增提示继续生效。

### 验证

- 539 passed；QAM 构建通过。

## v0.26.22

### Web 服务器目录自动读取

- `catalog_url` 配置后，插件启动时后台自动请求服务器 CSV：
  - 304 或 SHA256 相同 → 不写入
  - 有更新 → 校验、原子替换、重新加载目录
  - 失败只记日志，不阻塞插件启动
- 保留设置页「检查并更新游戏列表」和启动时自动检查两种方式。
- 自动更新仍写入 `catalog.csv.meta.json`，最近更新 shelf 可显示新增游戏。

### 验证

- 539 passed；QAM 构建通过。

## v0.26.21

### 可选启动文件

- 目录 CSV 新增可选列 `executable_name`（相对安装根目录）。
- `GameCatalogEntry` / 任务记录保存启动文件；兼容旧 CSV 和旧 state.json。
- 安装/扫描已安装时优先使用声明的启动文件，找不到再按 `openpath` 和自动扫描。
- Web 提交系统 1.1.0 表单新增「启动文件（可选）」；审核通过后写入 CSV。
- 旧 Web 目录 CSV 在合并时自动补 `executable_name` 列。

### 验证

- 539 passed；QAM 构建通过。

## v0.26.20

### 目录新增提醒 / 最近更新

- 检查目录更新时对比本地 CSV 与服务器 CSV 的 `game_id`，记录新增游戏。
- 更新成功提示新增数量。
- 游戏库顶部增加「最近更新」shelf，显示新增游戏封面。
- 更新元数据写入 `catalog.csv.meta.json`，重复检查不会清空最近新增。

### 封面本地代理缓存

- 新增 `/api/tianyi/cover-image`：
  - 仅允许 Steam/封面 CDN 域名
  - 磁盘缓存 30 天
  - 8MB 大小限制、禁止重定向
- QAM 封面优先走本地缓存，失败自动回退直连 CDN。

### 下载批量管理

- 下载列表顶部新增「全部暂停 / 全部继续」。
- 新增全局下载限速（KB/s，0 不限），写入设置并持久化。
- 批量操作走 aria2 `pauseAll` / `unpauseAll` / `changeGlobalOption`。

### 验证

- 537 passed；QAM 构建通过。

## v0.26.19

### 游戏库性能与手柄反馈

- 首页从 60 条降到 30 条，减少首屏封面并发加载。
- 封面缩略图改用 1x `library_600x900.jpg`，前端去掉 `_2x`，图片加 `loading="lazy"`。
- 卡片增加聚焦高亮（蓝色描边 + 亮度）。
- 焦点移动到卡片时，底部显示当前选中游戏信息条：
  标题、平台、大小、`A 选择 / B 返回`。
- 修复 v0.26.18 工作区源码异常，功能已从安装包构建产物恢复并重新构建。

### 验证

- 533 passed；QAM 构建通过。

## v0.26.18

### 目录增量检查

- 设置页从「更新游戏列表」改为「检查并更新游戏列表」。
- 下载前带 `If-None-Match` / `If-Modified-Since`：
  - 服务器 304 → 已是最新，不写入
  - 服务器 200 但 SHA256 与本地相同 → 已是最新，不写入
  - 内容变化 → 校验后原子替换本地 CSV 并重载
- 本地保存 `catalog.csv.meta.json`（ETag/Last-Modified/SHA256/更新时间）。
- Web 系统新增 `/api/catalog/meta`，返回行数/SHA256/最后更新时间。
- UI 区分「已更新」和「已是最新」。

### 验证

- 533 passed；QAM 构建通过。

## v0.26.17

### 变更

- Web 提交系统移出插件仓库，改为独立项目 `freedeck-submit-web`；
  插件包/插件仓库不再包含 Web 代码，只保留 `catalog_url` 设置和 CSV 下载。
- 插件测试回落到 531 passed（Web 核心测试随独立项目迁移）。

## v0.26.16

### 独立 Web 提交系统 + 自定义目录服务器

- 新增 `web-submit/`：FastAPI + SQLite 的独立提交/审核系统。
  - 玩家网页填表提交，后台待审核
  - 管理员 `/admin` token 登录，通过后原子追加服务器 `catalog.csv`
  - 公开 `/catalog.csv` 供插件下载
  - Dockerfile / docker-compose / Nginx 示例 / 限流 / 同源检查 / 审计数据
- 插件设置新增 `catalog_url`：填写自己服务器的 `/catalog.csv` 地址；
  「更新游戏列表」从该地址下载、校验、原子替换本地 CSV 并立即重载。
- 服务器 CSV 成为唯一源；不再默认读取远程 JSON。
- 保留 GitHub Issue `auto-merge` 即时/每 6 小时定时合并，作为另一种维护方式。

### 验证

- 534 passed；QAM 构建通过；Web 端提交流程测试通过。

## v0.26.15

### 服务器 CSV 游戏目录 + 定时自动合并

- **服务器 CSV 为唯一源**：`defaults/tianyi_catalog/freedeckcy_catalog.csv` 由仓库维护；
  玩家不再启动时自动联网，也不会读取远程 JSON。
- **设置页「更新游戏列表」**：下载服务器最新 CSV → 校验字段/行数 → 原子写入
  `~/.local/share/freedeckCY/tianyi/catalog.csv` → 立即重新加载；失败保留旧文件。
  本地下载的 CSV 优先于包内 CSV。
- **Issue 自动合并**：维护者添加 `auto-merge` 标签后 Action 立即合并；新增每 6 小时
  定时任务扫描带该标签的开放 Issue，自动解析/校验/合并 CSV、评论并关闭。
- 新增 `scripts/issue_to_submission.py`、`merge_approved_issues.py`；
  CI 继续校验 submissions 与目录 CSV。
- 远程 JSON 仍作为可选 `FREEDECKCY_CATALOG_JSON` 兼容能力保留，但默认关闭。

### 验证

- 531 passed；QAM 构建通过。

## v0.26.13

### 游戏库改版（参考 0.6）

- 顶部改为紧凑搜索 + 平台 chips + 分类 chips + 排序 chips，去掉占半屏的三个下拉框。
- 默认首页按分类生成横向 shelf（最多 8 个分类 + 其他），每行左右滚动。
- 搜索/平台/分类/排序激活时切换为 5 列网格。
- 分页改为「加载更多」，显示已加载/总数。
- 卡片补已安装角标；刷新回到第 1 页。
- 点击卡片仍先进入详情页，再安装/退出。

## v0.26.12

### 变更

- **游戏详情页**：参考 0.6，点击游戏卡片不再直接生成安装计划，而是先打开详情
  Modal（封面、中英文标题、平台、大小、分类），底部「安装 / 退出」。
  点「安装」后才进入原有确认与下载流程。
- 已安装游戏在详情页显示角标，安装按钮禁用。

## v0.26.11

### 修复

- **下载列表无法移除**：`remove_task` 把任务标 `removed` 后，`_cleanup_tasks`
  仍按 7 天保留，导致列表永远不消失；现在立即从本地任务列表删除。
- `aria2.remove` 加 3 秒超时，RPC/DNS 异常也不会阻塞移除。
- 前端额外过滤 `removed` 任务，避免旧缓存残留。

## v0.26.10

### 审计修复

- **重启 Steam**：runuser 成功后立即返回，不再继续执行 sudo 造成双重启；
  root/非 root 路径统一总超时；前端超时 70s，避免后端 15s×2 被误判失败。
- **重复安装**：`complete` 但尚未安装完成的任务也视为活动安装，防止安装窗口内
  再建一份相同下载、误隔离 `.aria2`。
- **放弃重试**：`_give_up_post_process` 使用 `install_status=gave_up`，启动恢复
  只迁移旧版 `failed/pending`，不会每次重启重新解压。
- **换机恢复根**：`restore_roots` 不再把游戏安装/ROM/launcher 目录拼成存档根，
  标准模拟器目录优先；portable 子目录只用于模拟器 AppDir。
- **3DS CIA**：按 3dbrew 规范逐段 64 字节对齐，meta 在 content 之后，
  NCCH magic 在 +0x100；修正测试 fixture。
- **CIA 安装**：改用 `QT_QPA_PLATFORM=offscreen`，避免 Decky 后端无 DISPLAY 时 Qt 退出。
- **重启提示**：「稍后」等待后端清除成功再隐藏；过滤旧轮询响应回弹；请求失败保留横幅。
- **入口冒烟**：新增 `tests/test_plugin_import.py`，防止 runtime_user 等模块漏提交/漏打包。

### 验证

- 526 passed；QAM 构建通过。

## v0.26.9

### 修复

- **自动重启 Steam**：Decky 后端常以 root 运行，原 `systemctl --user` 连到 root bus
  必然失败。新增 `runtime_user` 解析真实桌面用户；root 时通过 `runuser -u deck`
  （或 `sudo -u deck`）带 `XDG_RUNTIME_DIR`/`DBUS_SESSION_BUS_ADDRESS` 重启
  `steam-launcher.service`，失败再回退 `SteamClient.User.StartRestart`。
- **QAM 渲染崩溃**：v0.26.8 已修复 hooks 顺序；本版继续保留。
- 返回栏固定为普通内容行，重启提示为内联横幅。

## v0.26.8

### 修复

- **QAM 打开报错 “An error occurred while rendering”**：`dismissSteamRestart` /
  `restartSteamNow` 两个 useCallback 原本放在 `if (loading) return` 之后，
  加载完成后 hooks 数量变化导致 React 崩溃；已移到 early return 之前。
- 返回栏改为普通内容行（v0.26.7）；重启提示为内联横幅（v0.26.6）。

## v0.26.7

### 修复

- **返回栏位置**：彻底取消 sticky/fixed 浮动，返回 / Steam 库 / 刷新改为页面内容顶部
  的普通行，随内容滚动；不会再停在卡片中间。
- 去掉下方重复的返回/刷新按钮，只保留「游戏库 / 已安装」页签。
- 顶部/底部遮罩与 72px 安全区保留。

## v0.26.6

### 修复

- **重启提示改为 QAM 内联横幅**：不再用阻塞式 ConfirmModal，避免弹窗关不掉时
  无法进入设置；横幅提供「现在重启 / 稍后」，稍后立即清除后端 pending。
- **自动重启**：后端优先 `systemctl --user restart steam-launcher.service`，
  失败再回退 `SteamClient.User.StartRestart`，都失败才提示手动重启。
- 返回栏固定 `top: 64px`。

## v0.26.5

### 修复

- **安装完成重启 Steam**：优先调用后端 `systemctl --user restart steam-launcher.service`
  （SteamOS 用户会话），失败再回退 `SteamClient.User.StartRestart`；不再出现“点了没反应”。
- **「稍后」一直弹窗**：「现在重启 / 稍后 / 关闭」都会调用 `clear_steam_restart_pending`
  清除后端 pending，弹窗只出现一次；关闭按钮也生效。
- 返回栏固定 `top: 64px`，不随滚动跑到卡片中间。

## v0.26.4

### 修复

- **返回栏位置**：全屏库页工具栏从 `sticky` 改为 `position: fixed; top: 64px`，
  不再随滚动停在卡片中间；顶部 60px/底部 72px 遮罩继续挡住 Steam 状态栏/菜单栏。

- 其余同 v0.26.3：自动解压入库、.aria2 残留隔离/自动重试、安装完成重启提示、
  0.6 风格卡片、B 键 onCancel、诊断任务详情、aarch64 QEMU CI。

## v0.26.3（2026-11-17）

### 修复

- **下载完成不自动解压入库**：后台维护在 aria2 同步超时/失败时不再提前 return；
  继续扫描 complete 任务并调度后处理，文件大小已匹配时直接判定完成；
  启动时恢复旧版本“post_processed=True 但安装失败”的卡死任务。
- **返回/Steam 库/刷新按钮不灵敏**：全屏库页顶部固定 72px、底部 160px；
  sticky 顶栏停在 64px，避开 Steam 顶栏/底栏；加大按钮点击区、包 Focusable、
  onClose 失败时回退 Navigation.NavigateBack。
- **诊断 TLS**：自检复用 tianyi_client 的 build_tls_context，支持
  FREEDECKCY_TLS_CA_FILE/SSL_CERT_FILE；日志空异常至少记录类型。
- **安装诊断**：诊断包增加最近任务详情；自检把“安装失败/待安装”单独标 warn；
  安装失败写入日志，便于定位 SD 路径/解压/空间问题。
- **B 键返回**：库页根 Focusable 绑定 onCancel，B 键可关闭全屏库弹层。
- **安装完成重启提示**：Steam 快捷方式写入后，QAM 弹出「重启 Steam / 稍后」；
  现在重启调用 `SteamClient.User.StartRestart(false)`，不可用时提示手动重启。
- **下载完成调度**：维护 tick 在 aria2 同步前就先调度已完成的安装。
- **残留 .aria2 控制文件**：等待释放从 8s 提高到 30s；文件大小已完整时隔离残留
  `.aria2` 后继续安装；仍不完整则自动退避重试，不再直接判失败。
- **面板刷新锁**：刷新锁被安装准备占用时直接使用缓存，不再每 3 秒 TimeoutError。
- **游戏库展示**：原生库改为 0.6 风格 133×200 封面卡片、5 列、每页 30。
- **arm64 CI**：新增 QEMU aarch64 runtime smoke。

### 验证

- 522 passed；QAM 构建通过。

## v0.26.2

### 多智能体集中修复

- **后端**：分卷组 lead 优先主卷并保留 `bundled` 语义；安装收尾异常不再错误标记 `post_processed`；
  自动重试最多 5 次后转终态；7 天清理不再删除“已下完未安装”的任务；
  面板只读刷新不再裁掉 installed 记录；卸载与安装收尾竞态；HTTP 错误 message 脱敏；
  跨站 GET 副作用拒绝；Origin 端口随服务端口重置；并发 start_server 单实例；
  日志 `O_NOFOLLOW`、aria2 runtime meta 0600 原子写。
- **模拟器/存档**：3DS sysdata 临时目录/`azahar-emu` 路径/`nand+sdmc` 布局修复；
  `.cia` title-id 与按 title 存档；PS1 `.iso/.pbp`、单组回退、已有 m3u 优先；
  GBA 嵌套 ROM 目录不再当存档；PSP/PS3/3DS 跨设备恢复目录层；
  模拟器缓存完整性、Content-Length、原子解包、Flatpak 非交互。
- **前端**：设置页漏依赖、百度扫码状态、全局 busy 超时；原生库请求序号/搜索回车/卸载锁；
  “Steam 库”兜底；网页库 API 错误、安装卡死、焦点/回车、登录态与备份入口。
- **网盘/提交/打包**：百度 QR 错误脱敏/Cookie 回退/超时状态；OpenAPI 双层脱敏；
  分享码归一、pwd 覆盖、openpath/公式校验；Android 存储别名；
  runtime 损坏自愈、`--verify-only`/`--self-test`/manifest；package 全架构检查与自动 sha256。
- **测试**：新增 `tests/sim/` 全模拟与 `tests/test_backend_fixes.py`；385 → 518。

### 已知限制

- 3DS CIA 自动安装后仍无直接 Steam 快捷方式，从 Azahar 列表启动。
- SteamOS/DroidDeck 真机、CIA 启动、百度真实扫码仍需验收。
- docs 部分历史行号/旧路径可能滞后，后续统一校准。

## v0.26.1

### 新增

- **3DS `.cia` 自动安装**：没有可启动 ROM 时，先部署 system files，再调用 Azahar
  `--install <cia>`；成功提示从 Azahar 列表启动，失败返回具体输出。不再只提示用户手动安装。
- **旧云存档备份迁移**：后台维护把存档树里的旧 `.freedeckcy-bak-*` 移到
  `~/.local/share/freedeckCY/backups/legacy/`，中央备份保留最近 10 份；
  `cloud-save-*` 清理不会误删 `legacy/`。
- **旧 manifest 完全无目录结构兼容**：`archive_rel_path` 缺失时按 `entry_name`
  或在归档根内容上重建条目目录层，避免旧包恢复丢条目。
- **运行时 Linux 冒烟**：新增 `scripts/verify_runtime.sh` 与 CI job，实际执行
  `7zz i` / `aria2c --version` / `node --version`。

### 修复

- **PS1 同名歧义**：标题支持 `中文/English` 多段匹配；完整 openpath、目录、标题三级判定；
  多个 m3u/分组仍不唯一时明确失败，不再注册错游戏。
- **后处理退避**：安装收尾失败按组退避（最长 5 分钟），不再每 8 秒重试刷日志。
- **安全**：日志轮转后仍 0600；Origin 只允许本插件监听端口；aria2 RPC 关闭
  `--rpc-allow-origin-all`；空目录不再 realpath 成 CWD。
- **提交校验**：百度 `/s/1...` 与 `?surl=...` 分享码归一，修复重复提交绕过。

### 变更

- CI UI 构建升级 Node 24；新增 Python 编译/shell 语法检查与运行时冒烟 job。
- 测试 377 → 385。

## v0.26.0

### 安全与稳定性

- **tar 解压安全**：拒绝绝对路径、`..`、符号链接/硬链接/设备文件；staging 全树复查，合并阶段拒绝 symlink，修复归档路径穿越与用户文件被移动。
- **运行时升级**：7-Zip 23.01 → 26.06（CVE-2024-11477 影响面）、Node 20.18.1 → 24.22.3 LTS；aria2/7z/node 全部二进制固定 SHA256，下载/已存在跳过时都校验；GitHub 下载 HTTP/2 失败回退 HTTP/1.1。
- **凭据与日志**：`/tmp/freedeckcy.log` 固定 0600；HTTP/OpenAPI 诊断递归脱敏；state.json 改为 0600 临时文件 + fsync + 原子替换，损坏文件备份后重建。
- **本地 API/校验**：目录 `openpath` 校验、CSV 公式注入校验；submission 同步；扫描 ROM 路径禁止越界。
- **诊断**：新增 QAM 设置「诊断」页（自检 + 导出诊断包），含目录/运行时/Steam/SD/网络/百度扫码/任务/日志；诊断包含 `self-check.json`。

### 安装 / 任务 / 云存档

- 修复设置页 `tabs` 漏依赖导致百度扫码/AppKey 输入冻结；扫码超时、TLS 证书回退、BAIDUID Cookie、轮询状态解析和过期提示。
- 修复模拟器记录持久化丢失 `platform/emulator/rom_path/launcher_path`。
- 修复 `proton_tool/cloud_save_*` 设置不生效、空目录被 realpath 成 CWD。
- 任务刷新/创建串行化，重复安装复用活动任务，多文件失败回滚 aria2，aria2 重建前终止旧进程。
- 恢复保留 PSP/PS3/3DS 目录层；备份移出存档树、排除旧备份、保留最近 10 份；源缺失/计划失败不再假成功或卡 running。
- 卸载与安装收尾共用安装锁。

### 模拟器 / PS1 / 3DS

- `find_rom_file` 支持 `strict` 与标题；PS1 按目录/游戏名分组，openpath 完整路径与标题唯一匹配，仍歧义则明确失败，不再注册错游戏。
- PS1 平铺多游戏独立 m3u、cue/chd 去重、嵌套碟目录自然排序。
- GBA 支持 ROM 同目录 `.sav`；3DS sysdata 保留目录树且不覆盖；`.cia` 不再当直接 ROM；NCCH title id；只上传 3DS `data/`。
- 模拟器下载 `.part` 原子落盘。

### 工程化

- 打包校验运行时 ELF 架构、排除 `dist/*.map`；CI 增加 Python 编译与 shell 语法检查。
- 测试 354 → 377。

## v0.25.0

### 修复

- **不再给 Steam 原有游戏加“日期/游戏时长/总时长”**：
  - Steam 库详情页的时长块只对 `freedeckCY` 安装记录（`managed=true`）渲染；
  - 未匹配到插件记录时直接返回 `null`，不再显示“加载中/已玩时长/主线时长/总时长”；
  - 后端未匹配记录时不再查询 HowLongToBeat，也不返回时长字段；
  - 匹配顺序改为 **AppID 优先**，避免 Steam 原有游戏与插件游戏同名时误显示。

### 变更

- 测试 353 → 354（未托管游戏不查询 HLTB）。

## v0.24.0

### 修复

- **原生游戏库无法返回首页/桌面**：
  - 游戏库顶部新增固定「返回」「Steam 库」「刷新」按钮（sticky，滚动时仍可见）；
  - Modal 模式通过 `showModal(...).Close()` 关闭，路由模式通过 `Navigation.NavigateBack()`；
  - 「Steam 库」直接切回 Steam 库页，避免困在插件页面；
  - 页面内标题栏也保留「返回」。

### 变更

- 测试仍 353。

## v0.23.0

### 修复

- **游戏库仍打开网页**：QAM「游戏库」改为优先 `showModal(<LibraryPage />)` 原生弹层，
  不再先走 `Navigation.Navigate`；路由注册仍保留作全屏入口。页面顶部显示
  `原生 UI · v0.23.0`，主页显示 `QAM 原生 UI v0.23.0`，便于确认前端是否真的更新。
- **百度扫码点击没反应**：
  - 点击后立即 toast「正在获取百度二维码...」；
  - 前端 `withTimeout` 20s（轮询 15s），后端 `asyncio.wait_for(request_qr, 12s)`；
  - 超时返回明确错误，不再一直 busy/无反馈；
  - 后端记录 `Baidu QR start requested` / `Baidu QR ready sign_len=...` / 超时日志。

### 变更

- 测试仍 353。

## v0.22.0

### 新增

- **诊断自检**：QAM 设置新增「诊断」页。
  - 「运行自检」检查：插件版本、状态目录权限、下载/安装目录与剩余空间、
    aria2/7zz/node 可执行、Steam 快捷方式读取、SD/外置挂载、天翼云网络、
    百度扫码 `getqrcode`、任务/已安装、最近日志错误；
  - 每条返回 `ok/warn/fail/skip` + 具体原因 + 修复建议；
  - 「导出诊断包」写到下载目录，包含 `diagnostics.json`、`self-check.json`、
    `log-tail.txt`（最多 300 行），cookie/token 脱敏。
- HTTP `POST /api/tianyi/diagnostics/run`；main callable
  `run_tianyi_diagnostics` / `export_tianyi_diagnostics_file`。

### 变更

- 测试 352 → 353（诊断自检结构）。

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
