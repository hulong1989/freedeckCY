# tests/sim — 全模拟测试

不联网、不执行 Linux 二进制、不碰真实 Steam/Decky 目录，用假组件把
**下载 → 安装 → 重启恢复 → 云存档上传/恢复 → 本地 HTTP** 整条链路跑起来。
macOS 可直接运行，只依赖 `requirements-dev.txt`（pytest / aiohttp）。

## 替身（`fakes.py` / `support.py`）

- `FakeAria2`：内存下载；可注入 add 失败、status error、gid 丢失/永久丢失、
  “永远 active”、pause/resume、重启后新 gid、`changeUri` 原地换链失败回退。
- `FakeSevenZip`：用 `zipfile` 模拟 7z；可制造损坏包、创建/解压/校验失败、
  多分卷（`.7z.001`、`.z01+.zip`）、排除规则（`*.freedeckcy-bak-*`）。
- `FakeCloud`：内存天翼云盘，实现 `upload_archive_to_cloud` /
  `list_cloud_archives` / `download_cloud_archive` 三个接口，可注入上传/列表/下载失败。
- `support.py`：装配真实 `TianyiService`（state/catalog 都落 tmp_path）、
  打桩网络/Steam/封面/收尾等待，提供建计划、造任务、等后台安装、云盘打桩等工具。
- 辅助构造器：`build_param_sfo`（PSP/PS3 存档标题）、`write_3ds_rom`（NCSD 头）、
  `write_zip_archive` / `corrupt_archive`。

## 覆盖

- `test_install_sim.py`（原有）
  - plan → 任务 → 假下载 → 假解压 → 已安装记录 + Steam 参数
  - 部分文件 add 失败 → 回滚已加 aria2 任务；解压失败 → failed + 手动重试
  - 安装根消失 → 组级退避；重启后已完成任务补装
- `test_restore_sim.py`（原有）
  - PSP `SAVEDATA/<TITLEID>` 上传 → 归档 → manifest → 恢复计划保留目录层
  - 完全无目录结构旧 manifest → 恢复进 `<TITLEID>/`
- `test_aria2_fault_sim.py`
  - gid 丢失：按落盘路径认领新 gid、进度保留、不重复 addUri
  - gid 丢失但文件已完整：直接判完成并安装
  - gid 丢失且无半成品：自动重下（每任务一次）；无法取链时连续 5 次后 error
  - aria2 status error：同组 complete 分卷提示“分卷下载失败”，移除失败任务后自动补装
  - 永远 active：不误装、不超时；pause/resume 状态可见；完成后正常安装
  - error 任务但文件完整：retry 跳过重下直接重装
  - gid 仍在时优先 `changeUri` 原地换链
- `test_restart_sim.py`
  - 重启后 gid 变化 → 认领 → 下载完成 → 自动安装
  - 分卷组重启恢复：一半完成一半在跑，全部完成后只安装/注册一次
  - 重启后后台维护迁移旧 `.freedeckcy-bak-*` 到中央备份目录
  - 并发双入口 `start_install`：第二次复用正在下载的任务，只 addUri 一次
  - 并发触发同一任务安装：只解压一次、一条记录、一次 Steam 注册
  - 安装收尾持锁期间卸载：卸载等待锁，不会删到一半又开始解压
  - 两个 `maintenance_tick` 重叠：第二个返回 `{"skipped": "busy"}`
- `test_sevenzip_sim.py`
  - 坏包 → `7z t` 失败 → 隔离 `.freedeckcy-archive-invalid-*` → 自动重下 → 重装成功
  - 坏包且无法重新取链 → failed + 具体原因；解压抛 `SevenZipError` → failed
  - `.7z.001/.002`：只解主卷、非主卷 `bundled`、只注册一次
  - 缺 `.002` / zip 分卷缺 `.zip` 入口卷：整组失败并列出缺失分卷
  - 排除规则：备份文件/备份目录不进包，正常文件保留
- `test_cloud_save_sim.py`
  - PSP / PS3 / 3DS 上传 → 覆盖前取消 → 确认恢复；目录层（`SAVEDATA/<TITLEID>`、
    `dev_hdd0/home/.../savedata/<TITLEID>`、3DS `title/<hi>/<lo>/data`）完整保留
  - 恢复覆盖前备份到 `backups/cloud-save-*`；同目录其它游戏存档不受影响
  - manifest v2 内容（entries / 游玩时长）与恢复后的游玩时长合并
  - 旧 manifest：只有 `source_paths`（无 entries）、entries 只有 name（无 archive_rel_path）
  - 旧 `.freedeckcy-bak-*` 迁移 + 备份保留策略（≤10 份且不删 `legacy/`）
  - 上传失败（upload_failed / package_failed）、未变化指纹跳过、变化后重传
  - 无候选游戏、下载云版本失败 → 状态复位且不落盘
  - `/restore/list` 版本分组；安装记录已删时恢复计划失败
- `test_http_sim.py`
  - `/api/tianyi/state` 正常响应；非本服务端口的 localhost Origin POST → 403
  - 允许来源的 GET 返回 CORS 头（`Access-Control-Allow-Origin`/`Vary`）
  - 写请求：允许 Origin 正常执行；远程 Origin / `Sec-Fetch-Site: cross-site` → 403
  - `OPTIONS` 预检只对允许来源返回 204；Host 非回环 → 403
  - `/`、`/_healthz`；诊断 JSON / 自检 / 导出 zip；错误诊断 token/cookie 脱敏

## 不覆盖 / 已知边界

- 真实 Steam QAM/Decky Loader、真实 Proton/Flatpak、SD 热插拔、模拟器画面、
  百度真实账号仍需真机 + 诊断包。
- `FakeSevenZip` 用 zipfile 模拟：不验证真实 7z 分卷格式、加密包、RAR/zip 分卷
  的解压本身（生产只识别并把主卷交给 7zz）。
- `FakeAria2` 即时完成/即时返回状态：未覆盖真实 aria2 RPC 超时、断线重连、
  限速长下载、磁盘写满等。
- 多分卷“组内 lead”按 `created_at` + `task_id` 排序。同一秒创建且**非主卷**
  task_id 更小时，最终 `_finalize_group_install` 会把该 lead 的 `bundled` 标签
  覆盖成 `installed`（解压/注册仍只一次，仅展示层语义差异）；当前测试固定
  `created_at` 保证主卷为 lead 来断言 `bundled`。
- 云存档 PC/Proton 路径的候选扫描在 `tests/test_cloud_auto.py`、
  `tests/test_emulator_saves.py` 里有单元覆盖，本目录 e2e 只覆盖模拟器三平台。
- HTTP 测试用真实 `cors_middleware`/路由，但通过临时往
  `server_manager._ALLOWED_ORIGIN_PORTS` 注入 TestServer 随机端口来模拟
  “本服务端口”；未覆盖真实 59271 端口绑定/端口占用。
- 诊断导出 zip 的真实内容由 `tests/test_install_pipeline.py` 覆盖；本目录只验证
  HTTP 层响应头/字节透传与错误脱敏。
