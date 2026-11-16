# 游戏提交（仓库）

这是 freedeckCY 的**仓库提交**方式：不需要天翼云账号登录，也不需要腾讯文档。
字段与原版资源池投稿一致，额外补了目录安装需要的 `openpath`。

## 方式一：Issue 表单（最简单）

打开：

**https://github.com/hulong1989/freedeckCY/issues/new?template=submit-game.yml**

填写游戏名称、平台、天翼云盘分享链接、提取码、网盘内路径即可。
维护者会审核，必要时转成 `submissions/*.json` 或要求补充信息。

## 方式二：PR 提交 JSON（推荐批量/长期）

1. 复制 `submissions/examples/example-pc.json` 到 `submissions/<平台>-<游戏名>.json`；
2. 按 [schema.json](schema.json) 填写：

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | ✅ | 中文名 |
| `english_name` |  | 英文名/原名，合并时生成 `中文/英文` 标题 |
| `platform` | ✅ | `pc/gba/psp/nds/ps1/fc/md/3ds/ps2/ps3/switch` |
| `share_url` | ✅ | `https://cloud.189.cn/...` 分享链接 |
| `access_code` |  | 提取码；链接里已有 `pwd=` 可留空 |
| `share_user_version` |  | 原版资源池字段，整合包/分享版本 |
| `executable_name` |  | PC 可执行文件名，模拟器可留空 |
| `openpath` | ✅ | 分享根目录下游戏文件/压缩包的相对路径 |
| `categories` |  | 逗号分隔，例如 `动作冒险,角色扮演` |
| `filesize_z` |  | 压缩包字节数，可留空 |
| `notes` |  | 多分卷/语言/版本说明（不会写入目录 CSV） |

3. 本地校验：

```bash
python scripts/validate_submissions.py
```

4. 提 PR。CI 会自动跑校验；通过后维护者执行：

```bash
python scripts/merge_submissions.py --dry-run   # 预览
python scripts/merge_submissions.py --apply     # 写入目录并移动文件
make validate-catalog                          # 再跑目录体检
```

合并后 JSON 会移动到 `submissions/merged/`，并记录在 `submissions/merged/index.json`。

## 规则

- **只提交分享链接**，不要上传游戏文件、破解补丁、账号 Cookie。
- 链接必须可访问、提取码正确；失效链接会被关闭。
- `openpath` 必须能在分享里唯一定位文件/目录，否则安装器无法匹配。
- 同一 `shareCode` 不能重复提交；目录已有的会被拒绝。
- 提交即表示你确认有权分享该资源；维护者可拒绝/删除任何侵权或违规内容。
- 平台仅支持：PC / GBA / PSP / NDS / PS1 / FC / MD / 3DS / PS2 / PS3 / Switch。

## 维护者命令

```bash
python scripts/validate_submissions.py --json
python scripts/merge_submissions.py --dry-run --json
python scripts/merge_submissions.py --apply
python -m pytest tests/test_submissions.py -q
```

## 相关

- 目录格式与校验：`defaults/tianyi_catalog/freedeckcy_catalog.csv`、`scripts/validate_catalog.py`
- 安装流程：`docs/ARCHITECTURE.md`、`docs/DEVELOPMENT.md`
