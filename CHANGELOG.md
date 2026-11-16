# Changelog

本项目从 v0.1.0 起使用独立版本号（fork 自 Freedeck，与上游 0.2–0.3 不连续）。

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
