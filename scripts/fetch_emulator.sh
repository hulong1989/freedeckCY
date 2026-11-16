#!/usr/bin/env bash
# fetch_emulator.sh - 下载 GBA 闭环所需的 mGBA AppImage（x86_64 / aarch64）
#
# 产物：
#   defaults/runtime/mgba/<arch>/mGBA.AppImage
#   defaults/runtime/mgba/<arch>/LICENSE
#
# 打包时 `make package` / `make package-droiddeck` 会自动带上对应架构。
# 运行时会用 `--appimage-extract` 解包到用户目录，不依赖 FUSE。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"

MGBA_VERSION="${MGBA_VERSION:-0.10.5}"
# 默认走 GitHub 官方 release；若网络不通，可显式指定可信镜像（注意供应链风险）：
#   MGBA_BASE=https://ghproxy.net/https://github.com/mgba-emu/mgba/releases/download/0.10.5 #       bash scripts/fetch_emulator.sh --arch all
MGBA_BASE="${MGBA_BASE:-https://github.com/mgba-emu/mgba/releases/download/${MGBA_VERSION}}"
LICENSE_URL="https://raw.githubusercontent.com/mgba-emu/mgba/${MGBA_VERSION}/LICENSE"
MIN_BYTES=$((8 * 1024 * 1024))

asset_size() {
    case "$1" in
        x86_64) printf '25208000' ;;
        aarch64) printf '24576384' ;;
        *) printf '0' ;;
    esac
}

DEST="${REPO_ROOT}/defaults/runtime"
ARCH_INPUT=""
FORCE=0
TMP_DIR=""

log() { printf '[emulator] %s\n' "$*"; }
warn() { printf '[emulator][warn] %s\n' "$*" >&2; }
die() { printf '[emulator][error] %s\n' "$*" >&2; exit 2; }

usage() {
    cat <<'EOF'
用法: bash scripts/fetch_emulator.sh [选项]

选项:
  --arch <x86_64|aarch64|all>  目标架构，默认按本机 uname -m
  --dest <目录>                输出根目录（默认 defaults/runtime）
  -f, --force                  已存在也重新下载
  -h, --help                   显示帮助

示例:
  bash scripts/fetch_emulator.sh --arch all
  bash scripts/fetch_emulator.sh --arch aarch64 --force
EOF
}

normalize_arch() {
    case "$1" in
        x86_64 | amd64) printf 'x86_64' ;;
        aarch64 | arm64) printf 'aarch64' ;;
        *) printf '%s' "$1" ;;
    esac
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h | --help) usage; exit 0 ;;
        --arch)
            [[ $# -ge 2 ]] || die "--arch 需要一个值"
            ARCH_INPUT="$2"; shift 2 ;;
        --arch=*) ARCH_INPUT="${1#*=}"; shift ;;
        --dest)
            [[ $# -ge 2 ]] || die "--dest 需要一个目录"
            DEST="$2"; shift 2 ;;
        --dest=*) DEST="${1#*=}"; shift ;;
        -f | --force) FORCE=1; shift ;;
        *) die "未知参数: $1（--help 查看用法）" ;;
    esac
done

command -v curl >/dev/null 2>&1 || die "缺少 curl"

if [[ -z "${ARCH_INPUT}" ]]; then
    ARCH_INPUT="$(normalize_arch "$(uname -m)")"
fi
ARCH_LIST=()
case "${ARCH_INPUT}" in
    x86_64 | aarch64) ARCH_LIST=("${ARCH_INPUT}") ;;
    all) ARCH_LIST=(x86_64 aarch64) ;;
    *) die "不支持的 --arch: ${ARCH_INPUT}（x86_64|aarch64|all）" ;;
esac

asset_for() {
    case "$1" in
        x86_64) printf 'mGBA-%s-appimage-x64.appimage' "${MGBA_VERSION}" ;;
        aarch64) printf 'mGBA-%s-appimage-arm64.appimage' "${MGBA_VERSION}" ;;
        *) return 1 ;;
    esac
}

download() {
    local url="$1" out="$2" label="$3"
    log "下载 ${label}"
    log "  源地址: ${url}"
    if [[ -t 1 ]]; then
        curl -fL --retry 5 --retry-delay 3 --connect-timeout 20 --max-time 1800 --progress-bar -o "${out}" "${url}" || {
            warn "下载失败: ${label}"; return 1; }
    else
        curl -fsSL --retry 5 --retry-delay 3 --connect-timeout 20 --max-time 1800 -o "${out}" "${url}" || {
            warn "下载失败: ${label}"; return 1; }
    fi
    [[ -s "${out}" ]] || { warn "下载结果为空: ${out}"; return 1; }
}

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/freedeckcy-emulator.XXXXXX")"
cleanup() { [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]] && rm -rf -- "${TMP_DIR}"; }
trap cleanup EXIT INT TERM

FAILURES=0
for arch in "${ARCH_LIST[@]}"; do
    target_dir="${DEST}/mgba/${arch}"
    target="${target_dir}/mGBA.AppImage"
    mkdir -p "${target_dir}"

    asset="$(asset_for "${arch}")"
    if [[ "${FORCE}" -eq 0 && -f "${target}" ]]; then
        size="$(wc -c <"${target}" | tr -d '[:space:]')"
        if [[ "${size}" -ge "${MIN_BYTES}" ]]; then
            log "跳过 mGBA (${arch})（已存在: ${target}）"
            continue
        fi
        warn "已存在文件过小，重新下载: ${target}"
    fi

    tmp_file="${TMP_DIR}/mgba-${arch}.appimage"
    if ! download "${MGBA_BASE}/${asset}" "${tmp_file}" "mGBA ${MGBA_VERSION} (${arch})"; then
        FAILURES=$((FAILURES + 1))
        continue
    fi
    size="$(wc -c <"${tmp_file}" | tr -d '[:space:]')"
    expected="$(asset_size "${arch}")"
    if [[ "${size}" -lt "${MIN_BYTES}" ]]; then
        warn "mGBA (${arch}) 下载不完整（${size} bytes）"
        FAILURES=$((FAILURES + 1))
        continue
    fi
    if [[ "${expected}" -gt 0 && "${size}" -ne "${expected}" ]]; then
        warn "mGBA (${arch}) 大小与官方 release 不一致（${size} != ${expected}），请确认镜像可信"
    fi
    mv -f "${tmp_file}" "${target}"
    chmod 755 "${target}"
    log "完成 mGBA (${arch}) -> ${target} ($(awk -v s="${size}" 'BEGIN {printf "%.1f", s/1048576}') MB)"

    license="${target_dir}/LICENSE"
    if [[ ! -f "${license}" ]]; then
        if curl -fsSL --retry 3 --max-time 60 -o "${license}" "${LICENSE_URL}"; then
            log "许可证 -> ${license}"
        else
            warn "mGBA LICENSE 下载失败（不影响运行，但发布前应补齐）"
            rm -f "${license}"
        fi
    fi
done

if [[ "${FAILURES}" -gt 0 ]]; then
    warn "有 ${FAILURES} 个架构下载失败"
    exit 1
fi

log "完成。运行 make package / make package-droiddeck 会按架构打包。"
