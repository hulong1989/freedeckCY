#!/usr/bin/env bash
# doctor.sh - freedeckCY 环境诊断（只读，不改任何文件）
#
# 用法：
#   bash scripts/doctor.sh                 # 诊断当前仓库/插件目录
#   bash scripts/doctor.sh --plugin-dir /path/to/Freedeck
#   make doctor
#
# 输出：系统/架构、Python、运行时二进制、Steam 根与库、state.json、
#       日志尾部、端口占用、天翼云盘连通性。适合在 Steam Deck 上直接跑。

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
DEFAULT_PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd -P)"
PLUGIN_DIR="${DECKY_PLUGIN_DIR:-$DEFAULT_PLUGIN_DIR}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --plugin-dir)
            [[ $# -ge 2 ]] || { echo "--plugin-dir 需要一个目录" >&2; exit 2; }
            PLUGIN_DIR="$2"; shift 2 ;;
        --plugin-dir=*)
            PLUGIN_DIR="${1#*=}"; shift ;;
        -h|--help)
            sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *)
            echo "未知参数: $1" >&2; exit 2 ;;
    esac
done

STATE_FILE="${FREEDECKCY_STATE_FILE:-$HOME/.local/share/freedeckCY/tianyi/state.json}"
LOG_FILE="/tmp/freedeckcy.log"
PORT="${FREEDECKCY_PORT:-59271}"
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|amd64) ARCH_DIR="x86_64" ;;
    aarch64|arm64) ARCH_DIR="aarch64" ;;
    *) ARCH_DIR="$ARCH" ;;
esac

section() { printf '\n== %s ==\n' "$1"; }
ok() { printf '  [ok]   %s\n' "$1"; }
warn() { printf '  [warn] %s\n' "$1"; }
bad() { printf '  [fail] %s\n' "$1"; }
info() { printf '         %s\n' "$1"; }

section "系统"
info "plugin_dir: $PLUGIN_DIR"
info "kernel:     $(uname -sr)"
info "arch:       $ARCH (运行时目录使用 $ARCH_DIR)"

section "Python"
if command -v python3 >/dev/null 2>&1; then
    PYVER="$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))' 2>/dev/null || echo unknown)"
    info "python3:    $PYVER"
    python3 - <<'PY' 2>/dev/null && ok "Python 版本 >= 3.10" || bad "Python 版本过低（Decky 需要 >= 3.10）"
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
else
    bad "未找到 python3（Decky 运行时自带，通常不应缺失）"
fi

section "运行时二进制"
check_binary() {
    local label="$1"; shift
    local candidate=""
    for path in "$@"; do
        if [[ -f "$path" ]]; then candidate="$path"; break; fi
    done
    if [[ -n "$candidate" ]]; then
        local size
        size="$(du -h "$candidate" 2>/dev/null | awk '{print $1}')"
        local kind
        kind="$(file -b "$candidate" 2>/dev/null | cut -c1-70)"
        ok "$label: $candidate ($size)"
        info "$kind"
    else
        local system_bin=""
        case "$label" in
            aria2c) system_bin="$(command -v aria2c || true)" ;;
            7zz) system_bin="$(command -v 7zz || command -v 7z || true)" ;;
            node) system_bin="$(command -v node || true)" ;;
        esac
        if [[ -n "$system_bin" ]]; then
            warn "$label: 未找到内置版本，回退系统命令 $system_bin"
        else
            bad "$label: 未找到（执行 make runtime 补齐）"
        fi
    fi
}
check_binary "aria2c" \
    "$PLUGIN_DIR/defaults/runtime/aria2/$ARCH_DIR/aria2c" \
    "$PLUGIN_DIR/defaults/runtime/aria2/aria2c" \
    "$PLUGIN_DIR/defaults/aria2/linux-x64/aria2c" \
    "$PLUGIN_DIR/defaults/aria2/aria2c"
check_binary "7zz" \
    "$PLUGIN_DIR/defaults/runtime/7z/$ARCH_DIR/7zz" \
    "$PLUGIN_DIR/defaults/runtime/7z/7zz" \
    "$PLUGIN_DIR/defaults/7z/linux-x86_64/7zz" \
    "$PLUGIN_DIR/defaults/7z/7zz"
check_binary "node" \
    "$PLUGIN_DIR/defaults/runtime/node/$ARCH_DIR/bin/node" \
    "$PLUGIN_DIR/defaults/node/bin/node"

section "Steam"
STEAM_ROOT=""
for candidate in \
    "${FREEDECKCY_STEAM_ROOT:-}" \
    "$HOME/.steam/steam" \
    "$HOME/.local/share/Steam" \
    "$HOME/.steam/root" \
    "$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam" \
    "$HOME/.var/app/com.valvesoftware.Steam/.steam/steam"; do
    if [[ -n "$candidate" && -d "$candidate/steamapps" ]]; then
        STEAM_ROOT="$(cd "$candidate" && pwd -P)"; break
    fi
done
if [[ -n "$STEAM_ROOT" ]]; then
    ok "Steam 根目录: $STEAM_ROOT"
    if [[ -f "$STEAM_ROOT/steamapps/libraryfolders.vdf" ]]; then
        info "库列表:"
        grep -oE '"path"[[:space:]]+"[^"]+"' "$STEAM_ROOT/steamapps/libraryfolders.vdf" 2>/dev/null \
            | sed -E 's/.*"([^"]+)"$/  - \1/' || true
    else
        warn "未找到 steamapps/libraryfolders.vdf（只有一个库或路径非常规）"
    fi
    if [[ -d "$STEAM_ROOT/userdata" ]]; then
        USERS="$(ls -1 "$STEAM_ROOT/userdata" 2>/dev/null | grep -E '^[0-9]+$' | tr '\n' ' ' || true)"
        info "userdata 用户: ${USERS:-<none>}"
    fi
else
    bad "未找到 Steam 安装目录（可设置 FREEDECKCY_STEAM_ROOT）"
fi

section "状态文件"
if [[ -f "$STATE_FILE" ]]; then
    ok "state.json: $STATE_FILE"
    info "大小/权限: $(du -h "$STATE_FILE" | awk '{print $1}') / $(ls -l "$STATE_FILE" | awk '{print $1}')"
    python3 - "$STATE_FILE" <<'PY' 2>/dev/null || warn "state.json 解析失败"
import json, sys
with open(sys.argv[1], encoding="utf-8") as fh:
    data = json.load(fh)
tasks = data.get("tasks") or []
installed = data.get("installed_games") or []
print(f"         登录态: {'已登录' if (data.get('login') or {}).get('cookie') else '未登录'}")
print(f"         任务: {len(tasks)}（error={sum(1 for t in tasks if str(t.get('status'))=='error')}, waiting={sum(1 for t in tasks if str(t.get('status')) in {'waiting','active'})}）")
print(f"         已安装记录: {len(installed)}")
settings = data.get("settings") or {}
print(f"         下载目录: {settings.get('download_dir','') or '-'}")
print(f"         安装目录: {settings.get('install_dir','') or '-'}")
PY
else
    warn "state.json 不存在（尚未初始化或路径不同）: $STATE_FILE"
fi

section "日志"
if [[ -f "$LOG_FILE" ]]; then
    info "$LOG_FILE ($(du -h "$LOG_FILE" | awk '{print $1}'))"
    info "最近错误:"
    grep -E "ERROR|Exception|失败" "$LOG_FILE" 2>/dev/null | tail -5 | sed 's/^/         /' || info "无"
else
    warn "日志不存在: $LOG_FILE（插件可能还没启动过）"
fi

section "本地服务"
if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    ok "端口 $PORT 正在监听"
else
    warn "端口 $PORT 未被监听（插件未启动或服务未开启）"
fi
if command -v curl >/dev/null 2>&1; then
    code="$(curl -s -o /dev/null -m 3 -w '%{http_code}' "http://127.0.0.1:${PORT}/_healthz" 2>/dev/null)" || code="000"
    code="${code:-000}"
    [[ "${code}" == "200" ]] && ok "/_healthz 返回 200" || warn "/_healthz 返回 ${code}"
fi

section "网络"
if command -v curl >/dev/null 2>&1; then
    code="$(curl -s -o /dev/null -m 6 -w '%{http_code}' https://cloud.189.cn/ 2>/dev/null)" || code="000"
    code="${code:-000}"
    if [[ "${code}" =~ ^(200|301|302|403)$ ]]; then
        ok "cloud.189.cn 可达（HTTP ${code}）"
    else
        bad "cloud.189.cn 不可达（${code}），登录/下载会失败"
    fi
else
    warn "缺少 curl，跳过网络检查"
fi

printf '\n诊断完成。把上面输出（或 /tmp/freedeckcy.log）发出来即可定位大部分问题。\n'
