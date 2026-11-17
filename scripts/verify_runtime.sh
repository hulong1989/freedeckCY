#!/usr/bin/env bash
# verify_runtime.sh - 在 Linux 上实际执行 aria2c/7zz/node 冒烟测试
#
# 除"能执行"外，还读取 <dir>/runtime-manifest.txt 校验实际版本与固定版本一致，
# 防止出现"二进制能跑但版本不对/混入旧版本"的包（CI runtime job 会跑本脚本）。
# 支持 --self-test：不依赖任何 Linux 二进制，用假 7zz/aria2c/node 自检本脚本逻辑。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
RUNTIME_DIR="${REPO_ROOT}/defaults/runtime"
MANIFEST_NAME="runtime-manifest.txt"
ARCH=""
RUNNER=""
SYSROOT=""
SELF_TEST=0
TMP_BASE="${TMPDIR:-/tmp}"
TMP_BASE="${TMP_BASE%/}"
VERIFY_OUT="$(mktemp "${TMP_BASE}/freedeckcy-runtime-verify.XXXXXX")"
BIN_OUT=""
fail=0

cleanup() {
    rm -f -- "${VERIFY_OUT}"
}
trap cleanup EXIT INT TERM

usage() {
    cat <<'EOF'
用法: bash scripts/verify_runtime.sh [--dir <runtime目录>] [--arch <x86_64|aarch64>]
       [--runner <qemu-aarch64-static>] [--sysroot <路径>] [--self-test]
默认目录 <repo>/defaults/runtime，架构按 uname -m。
  --runner     用 qemu 等模拟器执行目标架构二进制（默认直接执行）
  --sysroot    传给 qemu 的 -L 根目录（如 /usr/aarch64-linux-gnu）
  --self-test  用假二进制自检本脚本的版本一致性校验逻辑（不需要真实运行时）
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir)
            [[ $# -ge 2 ]] || { echo "--dir 需要一个目录路径" >&2; exit 2; }
            RUNTIME_DIR="$2"
            shift 2
            ;;
        --arch)
            [[ $# -ge 2 ]] || { echo "--arch 需要 x86_64|aarch64" >&2; exit 2; }
            ARCH="$2"
            shift 2
            ;;
        --runner)
            [[ $# -ge 2 ]] || { echo "--runner 需要一个可执行命令" >&2; exit 2; }
            RUNNER="$2"
            shift 2
            ;;
        --sysroot)
            [[ $# -ge 2 ]] || { echo "--sysroot 需要一个目录" >&2; exit 2; }
            SYSROOT="$2"
            shift 2
            ;;
        --self-test)
            SELF_TEST=1
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            echo "未知参数: $1" >&2
            usage
            exit 2
            ;;
    esac
done

normalize_arch() {
    case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
        x86_64 | amd64 | x64) printf 'x86_64' ;;
        aarch64 | arm64) printf 'aarch64' ;;
        *) printf '' ;;
    esac
}

if [[ -z "${ARCH}" ]]; then
    ARCH="$(normalize_arch "$(uname -m)")"
    if [[ -z "${ARCH}" ]]; then
        echo "不支持的架构: $(uname -m)" >&2
        exit 2
    fi
else
    ARCH="$(normalize_arch "${ARCH}")"
    if [[ -z "${ARCH}" ]]; then
        echo "不支持的 --arch（可用: x86_64|aarch64）" >&2
        exit 2
    fi
fi

manifest_version() { # component -> 版本（没有 manifest/键时为空）
    local component="$1" line
    [[ -f "${RUNTIME_DIR}/${MANIFEST_NAME}" ]] || return 0
    while IFS= read -r line; do
        case "${line}" in
            "${component}="*) printf '%s' "${line#*=}"; return 0 ;;
        esac
    done <"${RUNTIME_DIR}/${MANIFEST_NAME}"
    return 0
}

check_bin() { # path label args...
    local path="$1" label="$2"
    shift 2
    if [[ ! -x "${path}" ]]; then
        echo "[runtime-fail] ${label} 不存在或不可执行: ${path}" >&2
        fail=1
        return
    fi
    local -a cmd=("${path}")
    if [[ -n "${RUNNER}" ]]; then
        cmd=("${RUNNER}")
        [[ -n "${SYSROOT}" ]] && cmd+=(-L "${SYSROOT}")
        cmd+=("${path}")
    fi
    if ! "${cmd[@]}" "$@" >"${VERIFY_OUT}" 2>&1; then
        echo "[runtime-fail] ${label} 执行失败: $(head -c 300 "${VERIFY_OUT}")" >&2
        fail=1
        return
    fi
    BIN_OUT="$(cat "${VERIFY_OUT}")"
    echo "[runtime-ok] ${label}: $(printf '%s' "${BIN_OUT}" | sed -n '1p')"
}

check_version() { # label expected output
    local label="$1" expected="$2" output="$3"
    if [[ -z "${expected}" ]]; then
        echo "[runtime-warn] ${label} 缺少固定版本记录（${MANIFEST_NAME}），跳过版本一致性校验" >&2
        return
    fi
    if ! printf '%s' "${output}" | grep -Fq "${expected}"; then
        echo "[runtime-fail] ${label} 版本不一致：期望 ${expected}，实际输出: $(printf '%s' "${output}" | sed -n '1p')" >&2
        fail=1
        return
    fi
    echo "[runtime-ok] ${label} 版本一致: ${expected}"
}

run_checks() {
    local aria2_expected sevenzip_expected node_expected
    fail=0
    BIN_OUT=""

    aria2_expected="$(manifest_version aria2)"
    sevenzip_expected="$(manifest_version 7z)"
    node_expected="$(manifest_version node)"
    if [[ -f "${RUNTIME_DIR}/${MANIFEST_NAME}" ]]; then
        echo "[runtime] 版本清单: ${RUNTIME_DIR}/${MANIFEST_NAME}"
    else
        echo "[runtime-warn] 未找到 ${RUNTIME_DIR}/${MANIFEST_NAME}：只做可执行冒烟，不做版本一致性校验" >&2
    fi

    check_bin "${RUNTIME_DIR}/7z/${ARCH}/7zz" "7-Zip (${ARCH})" i
    if [[ "${fail}" -eq 0 ]]; then
        check_version "7-Zip (${ARCH})" "${sevenzip_expected}" "${BIN_OUT}"
    fi

    check_bin "${RUNTIME_DIR}/aria2/${ARCH}/aria2c" "aria2c (${ARCH})" --version
    if [[ "${fail}" -eq 0 ]]; then
        check_version "aria2c (${ARCH})" "${aria2_expected}" "${BIN_OUT}"
    fi

    check_bin "${RUNTIME_DIR}/node/${ARCH}/bin/node" "Node.js (${ARCH})" --version
    if [[ "${fail}" -eq 0 ]]; then
        check_version "Node.js (${ARCH})" "${node_expected}" "${BIN_OUT}"
    fi

    if [[ "${fail}" -ne 0 ]]; then
        echo "[runtime] 冒烟测试失败 (${ARCH})" >&2
        return 1
    fi
    echo "[runtime] 全部运行时冒烟测试通过 (${ARCH})"
    return 0
}

# ---- 离线自检（假二进制，不需要 Linux 运行时） -------------------------------
run_self_test() {
    local tmp SELF_TEST_CHECKS=0
    tmp="$(mktemp -d "${TMP_BASE}/freedeckcy-runtime-verify-selftest.XXXXXX")"
    make_fake() { # path body
        mkdir -p "$(dirname "$1")"
        printf '#!/usr/bin/env bash\n%s\n' "$2" >"$1"
        chmod 755 "$1"
    }
    make_fake "${tmp}/7z/x86_64/7zz" 'echo "7-Zip (z) 26.06 (x64) : Copyright (c) 1999-2026 Igor Pavlov"'
    make_fake "${tmp}/7z/aarch64/7zz" 'echo "7-Zip (z) 26.06 (ARM64) : Copyright (c) 1999-2026 Igor Pavlov"'
    make_fake "${tmp}/aria2/x86_64/aria2c" 'printf "aria2 version 1.37.0\nCopyright (C) 2006, 2019 Tatsuhiro Tsujikawa\n"'
    make_fake "${tmp}/aria2/aarch64/aria2c" 'printf "aria2 version 1.37.0\n"'
    make_fake "${tmp}/node/x86_64/bin/node" 'echo "v24.22.3"'
    make_fake "${tmp}/node/aarch64/bin/node" 'echo "v24.22.3"'
    {
        echo "# self-test manifest"
        echo "aria2=1.37.0"
        echo "7z=26.06"
        echo "node=24.22.3"
    } >"${tmp}/${MANIFEST_NAME}"

    local saved_runtime_dir="${RUNTIME_DIR}" saved_arch="${ARCH}"
    RUNTIME_DIR="${tmp}"
    ARCH="x86_64"

    if ! run_checks >/dev/null 2>&1; then
        echo "[runtime][self-test][fail] 正确的假运行时未通过冒烟/版本校验" >&2
        RUNTIME_DIR="${saved_runtime_dir}"
        ARCH="${saved_arch}"
        rm -rf -- "${tmp}"
        return 1
    fi
    echo "[runtime][self-test] ok 正确版本（7zz/aria2c/node）通过冒烟+版本校验"
    SELF_TEST_CHECKS=1

    make_fake "${tmp}/node/x86_64/bin/node" 'echo "v99.0.0"'
    if run_checks >/dev/null 2>&1; then
        echo "[runtime][self-test][fail] 版本不一致（node v99.0.0）未被发现" >&2
        RUNTIME_DIR="${saved_runtime_dir}"
        ARCH="${saved_arch}"
        rm -rf -- "${tmp}"
        return 1
    fi
    echo "[runtime][self-test] ok 版本不一致（node v99.0.0）被拒绝"
    SELF_TEST_CHECKS=2

    make_fake "${tmp}/node/x86_64/bin/node" 'echo "v24.22.3"'
    make_fake "${tmp}/aria2/x86_64/aria2c" 'echo "not aria2"'
    if run_checks >/dev/null 2>&1; then
        echo "[runtime][self-test][fail] 缺失版本号的 aria2c 未被发现" >&2
        RUNTIME_DIR="${saved_runtime_dir}"
        ARCH="${saved_arch}"
        rm -rf -- "${tmp}"
        return 1
    fi
    echo "[runtime][self-test] ok aria2c 版本无法确认时被拒绝"
    SELF_TEST_CHECKS=3

    make_fake "${tmp}/aria2/x86_64/aria2c" 'printf "aria2 version 1.37.0\n"'
    rm -f -- "${tmp}/${MANIFEST_NAME}"
    if ! run_checks >/dev/null 2>&1; then
        echo "[runtime][self-test][fail] 缺少 manifest 时不应因版本校验失败" >&2
        RUNTIME_DIR="${saved_runtime_dir}"
        ARCH="${saved_arch}"
        rm -rf -- "${tmp}"
        return 1
    fi
    echo "[runtime][self-test] ok 旧运行时目录（无 manifest）降级为只做可执行冒烟"
    SELF_TEST_CHECKS=4

    RUNTIME_DIR="${saved_runtime_dir}"
    ARCH="${saved_arch}"
    rm -rf -- "${tmp}"
    printf '[runtime][self-test] 全部通过（%s 项）\n' "${SELF_TEST_CHECKS}"
    return 0
}

if [[ "${SELF_TEST}" -eq 1 ]]; then
    run_self_test
    exit $?
fi

run_checks
