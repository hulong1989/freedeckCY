#!/usr/bin/env bash
# 清空 freedeckCY 的下载任务列表（保留登录态、设置与已安装记录）。
#
# 用法：bash clear_freedeckcy_tasks.sh
# 注意：执行前先退出插件（Decky 里停用/重载），否则内存状态可能把任务写回。

set -euo pipefail

# 插件状态目录默认在 $HOME/.local/share/freedeckCY；可用 FREEDECKCY_STATE_FILE 覆盖。
STATE_FILE="${FREEDECKCY_STATE_FILE:-${HOME}/.local/share/freedeckCY/tianyi/state.json}"

if [[ ! -f "$STATE_FILE" ]]; then
  echo "未找到状态文件: $STATE_FILE" >&2
  exit 1
fi

BACKUP_FILE="${STATE_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
cp -f "$STATE_FILE" "$BACKUP_FILE"

python3 - "$STATE_FILE" <<'PY'
import json
import sys

state_file = sys.argv[1]

with open(state_file, "r", encoding="utf-8") as f:
    data = json.load(f)

if not isinstance(data, dict):
    raise SystemExit("state.json 格式异常，不是 JSON 对象")

data["tasks"] = []

with open(state_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY

# 状态文件含登录 cookie，保持仅属主可读写。
chmod 600 "$STATE_FILE" 2>/dev/null || true

echo "已清空下载任务列表。"
echo "备份文件: $BACKUP_FILE"
echo "如果 freedeckCY 当前正在打开，先退出再重新进入插件。"
