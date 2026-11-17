#!/usr/bin/env bash
# verify_runtime.sh - 在 Linux 上实际执行 aria2c/7zz/node 冒烟测试
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
RUNTIME_DIR="${REPO_ROOT}/defaults/runtime"
ARCH=""

usage() {
    cat <<'EOF'
用法: bash scripts/verify_runtime.sh [--dir <runtime目录>] [--arch <x86_64|aarch64>]
默认目录 <repo>/defaults/runtime，架构按 uname -m。
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir) RUNTIME_DIR="${2:?}"; shift 2 ;;
        --arch) ARCH="${2:?}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "未知参数: $1" >&2; usage; exit 2 ;;
    esac
done

if [[ -z "${ARCH}" ]]; then
    case "$(uname -m)" in
        x86_64|amd64) ARCH=x86_64 ;;
        aarch64|arm64) ARCH=aarch64 ;;
        *) echo "不支持的架构: $(uname -m)" >&2; exit 2 ;;
    esac
fi

fail=0
check_bin() { # path label args...
    local path="$1" label="$2"; shift 2
    if [[ ! -x "${path}" ]]; then
        echo "[runtime-fail] ${label} 不存在或不可执行: ${path}" >&2
        fail=1
        return
    fi
    if ! "$path" "$@" >/tmp/freedeckcy-runtime-verify.out 2>&1; then
        echo "[runtime-fail] ${label} 执行失败: $(head -c 300 /tmp/freedeckcy-runtime-verify.out)" >&2
        fail=1
        return
    fi
    echo "[runtime-ok] ${label}: $(head -n 1 /tmp/freedeckcy-runtime-verify.out)"
}

check_bin "${RUNTIME_DIR}/7z/${ARCH}/7zz" "7-Zip (${ARCH})" i
check_bin "${RUNTIME_DIR}/aria2/${ARCH}/aria2c" "aria2c (${ARCH})" --version
check_bin "${RUNTIME_DIR}/node/${ARCH}/bin/node" "Node.js (${ARCH})" --version

rm -f /tmp/freedeckcy-runtime-verify.out
if [[ "${fail}" -ne 0 ]]; then
    echo "[runtime] 冒烟测试失败" >&2
    exit 1
fi
echo "[runtime] 全部运行时冒烟测试通过 (${ARCH})"
