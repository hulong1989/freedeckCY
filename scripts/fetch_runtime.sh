#!/usr/bin/env bash
# fetch_runtime.sh - 一键补齐 freedeckCY 运行所需的 Linux 二进制
#
# 默认下载到 <repo>/defaults/runtime/：
#   aria2/<arch>/aria2c        abcfy2/aria2-static-build 1.37.0（musl 静态构建）
#   7z/<arch>/7zz              https://www.7-zip.org/a/7z2301-linux-*.tar.xz
#   node/<arch>/bin/node       https://nodejs.org/dist/v20.18.1/node-v20.18.1-linux-*.tar.xz
#
# arch 统一使用 x86_64 / aarch64，与 Python 侧 platform.machine() 对齐。
# 依赖：curl；aria2 需要 unzip；7z / node 需要 python3（本机无 xz 命令，用 tarfile 解压）。
# 特性：幂等（已存在且校验通过则跳过）、--force 强制重下、失败时打印源地址与建议。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
DEFAULT_DEST="${REPO_ROOT}/defaults/runtime"

# ---- 下载源（已核实） -------------------------------------------------------
ARIA2_VERSION="1.37.0"
ARIA2_REPO="abcfy2/aria2-static-build"
ARIA2_API_TAGS_URL="https://api.github.com/repos/${ARIA2_REPO}/releases/tags/${ARIA2_VERSION}"
ARIA2_X86_64_ASSET="aria2-x86_64-linux-musl_static.zip"
ARIA2_AARCH64_ASSET="aria2-aarch64-linux-musl_static.zip"
# GitHub API 解析失败时回退使用的已知 asset id（1.37.0 release）。
ARIA2_X86_64_FALLBACK_ID="416692128"
ARIA2_AARCH64_FALLBACK_ID="416692696"

SEVEN_ZIP_X86_64_URL="https://www.7-zip.org/a/7z2301-linux-x64.tar.xz"
SEVEN_ZIP_AARCH64_URL="https://www.7-zip.org/a/7z2301-linux-arm64.tar.xz"

NODE_VERSION="20.18.1"
NODE_X86_64_URL="https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz"
NODE_AARCH64_URL="https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-arm64.tar.xz"

MIN_BINARY_SIZE=1048576 # 1 MiB，防止把 LFS 占位符 / 错误页面当成二进制

# ---- 运行参数 ---------------------------------------------------------------
DEST="${DEFAULT_DEST}"
DEST_INPUT=""
ARCH_INPUT=""
FORCE=0
SELECTED=()
ARCH_LIST=()
FAILURES=0
TMP_DIR=""
TMP_BASE="${TMPDIR:-/tmp}"
TMP_BASE="${TMP_BASE%/}"

# ---- 输出辅助 ---------------------------------------------------------------
log() { printf '[runtime] %s\n' "$*"; }
warn() { printf '[runtime][warn] %s\n' "$*" >&2; }
die() {
    printf '[runtime][error] %s\n' "$*" >&2
    exit 2
}

usage() {
    cat <<'EOF'
用法: bash scripts/fetch_runtime.sh [选项]

下载 freedeckCY 运行所需的 Linux 二进制到 defaults/runtime/：
  aria2/<arch>/aria2c       aria2 1.37.0 静态构建（来自 abcfy2/aria2-static-build）
  7z/<arch>/7zz             7-Zip 23.01 官方 Linux 版
  node/<arch>/bin/node      Node.js v20.18.1（天翼 JS 解析器使用）

选项:
  --arch <x86_64|aarch64|all>  目标架构，默认按本机 uname -m 自动识别
  --only <aria2|7z|node>       只下载指定组件；可重复，也可逗号分隔
  --dest <目录>                输出目录，默认 <repo>/defaults/runtime
  -f, --force                  已存在也强制重新下载
  -h, --help                   显示本帮助并退出

示例:
  bash scripts/fetch_runtime.sh                        # 本机架构，下载全部组件
  bash scripts/fetch_runtime.sh --arch all             # Steam Deck(x86_64) + ARM 设备
  bash scripts/fetch_runtime.sh --only aria2,7z        # 只补 aria2 与 7z
  bash scripts/fetch_runtime.sh --only 7z --arch x86_64 --force

说明:
  - github.com 网页不可直连，aria2 通过 api.github.com 取 release asset 字节流。
  - 本机无 xz 命令，.tar.xz 使用 python3 -m tarfile 解压。
  - 已存在且校验（大小 > 1MiB、file 显示 ELF）通过的二进制默认跳过，可安全重复执行。
  - 会把第三方许可证一并放入运行时目录：node/<arch>/LICENSE、7z/<arch>/License.txt；
    aria2 上游 zip 仅含 aria2c，没有可拷贝的许可证/说明文件时会明确跳过（不编造）。
  - 下载失败时会打印源地址与网络/代理建议。
EOF
}

# ---- 通用工具 ---------------------------------------------------------------
have_cmd() { command -v "$1" >/dev/null 2>&1; }

normalize_arch() {
    printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

detect_host_arch() {
    case "$(normalize_arch "$(uname -m)")" in
        x86_64 | amd64 | x64) printf 'x86_64' ;;
        aarch64 | arm64) printf 'aarch64' ;;
        *) return 1 ;;
    esac
}

valid_arch() {
    case "$1" in
        x86_64 | aarch64) return 0 ;;
        *) return 1 ;;
    esac
}

cleanup() {
    if [[ -n "${TMP_DIR:-}" && -d "${TMP_DIR}" ]]; then
        # 只删除本脚本用 mktemp 创建的临时目录
        case "${TMP_DIR}" in
            "${TMP_BASE}"/freedeckcy-runtime.*) rm -rf -- "${TMP_DIR}" ;;
            *) warn "跳过清理非预期临时目录: ${TMP_DIR}" ;;
        esac
    fi
}

# ---- 参数解析 ---------------------------------------------------------------
add_only() {
    local raw="${1:-}" item
    local normalized
    normalized="$(printf '%s' "${raw}" | tr ',' '\n')"
    while IFS= read -r item; do
        item="$(printf '%s' "${item}" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')"
        [[ -n "${item}" ]] || continue
        case "${item}" in
            aria2 | 7z | node) SELECTED+=("${item}") ;;
            *) die "--only 只接受 aria2|7z|node（可重复或逗号分隔），收到: ${item}" ;;
        esac
    done <<<"${normalized}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h | --help)
            usage
            exit 0
            ;;
        --arch)
            [[ $# -ge 2 ]] || die "--arch 需要一个值（x86_64|aarch64|all）"
            ARCH_INPUT="$2"
            shift 2
            ;;
        --arch=*)
            ARCH_INPUT="${1#*=}"
            shift
            ;;
        --only)
            [[ $# -ge 2 ]] || die "--only 需要一个值（aria2|7z|node）"
            add_only "$2"
            shift 2
            ;;
        --only=*)
            add_only "${1#*=}"
            shift
            ;;
        -f | --force)
            FORCE=1
            shift
            ;;
        --dest)
            [[ $# -ge 2 ]] || die "--dest 需要一个目录路径"
            DEST_INPUT="$2"
            shift 2
            ;;
        --dest=*)
            DEST_INPUT="${1#*=}"
            shift
            ;;
        --)
            shift
            break
            ;;
        *)
            die "未知参数: $1（用 --help 查看用法）"
            ;;
    esac
done
[[ $# -eq 0 ]] || die "无法识别的多余参数: $*"

# ---- 参数校验 ---------------------------------------------------------------
if [[ -n "${DEST_INPUT}" ]]; then
    case "${DEST_INPUT}" in
        /*) DEST="${DEST_INPUT}" ;;
        *) DEST="$(pwd -P)/${DEST_INPUT}" ;;
    esac
fi
[[ -n "${DEST}" ]] || die "--dest 不能为空"

if [[ -z "${ARCH_INPUT}" ]]; then
    HOST_ARCH="$(detect_host_arch || true)"
    if [[ -z "${HOST_ARCH}" ]]; then
        die "无法自动识别本机架构（uname -m=$(uname -m)），请显式指定 --arch x86_64|aarch64|all"
    fi
    ARCH_LIST=("${HOST_ARCH}")
else
    ARCH_NORMALIZED="$(normalize_arch "${ARCH_INPUT}")"
    case "${ARCH_NORMALIZED}" in
        all) ARCH_LIST=(x86_64 aarch64) ;;
        *)
            valid_arch "${ARCH_NORMALIZED}" ||
                die "不支持的 --arch: ${ARCH_INPUT}（可用: x86_64|aarch64|all）"
            ARCH_LIST=("${ARCH_NORMALIZED}")
            ;;
    esac
fi

if [[ ${#SELECTED[@]} -eq 0 ]]; then
    SELECTED=(aria2 7z node)
fi

# ---- 依赖预检 ---------------------------------------------------------------
have_cmd curl || die "缺少 curl 命令，无法下载运行时"
NEED_PYTHON=0
NEED_UNZIP=0
for _comp in "${SELECTED[@]}"; do
    case "${_comp}" in
        7z | node) NEED_PYTHON=1 ;;
        aria2) NEED_UNZIP=1 ;;
    esac
done
if [[ "${NEED_PYTHON}" -eq 1 ]]; then
    have_cmd python3 ||
        die "缺少 python3：解压 .tar.xz 需要 python3 的 tarfile 模块（本机没有 xz 命令）。请安装 python3 后重试"
fi
if [[ "${NEED_UNZIP}" -eq 1 ]]; then
    have_cmd unzip || die "缺少 unzip：解压 aria2 的 .zip 资产需要 unzip。请安装 unzip 后重试"
fi

mkdir -p "${DEST}"
[[ -d "${DEST}" ]] || die "无法创建输出目录: ${DEST}"

TMP_DIR="$(mktemp -d "${TMP_BASE}/freedeckcy-runtime.XXXXXX")"
trap cleanup EXIT INT TERM

log "输出目录: ${DEST}"
log "目标架构: ${ARCH_LIST[*]}"
log "下载组件: ${SELECTED[*]}"
log "模式: $([[ "${FORCE}" -eq 1 ]] && echo '强制重新下载 (--force)' || echo '幂等（已存在且有效则跳过）')"

# ---- 校验 / 下载 / 解压 / 安装 ----------------------------------------------
validate_binary() { # path label [expected_arch]
    local path="$1" label="$2" expected_arch="${3:-}" size desc
    if [[ ! -f "${path}" ]]; then
        warn "${label} 不存在: ${path}"
        return 1
    fi
    size="$(wc -c <"${path}" | tr -d '[:space:]')"
    if [[ -z "${size}" || "${size}" -lt "${MIN_BINARY_SIZE}" ]]; then
        warn "${label} 文件过小（${size:-0} bytes < ${MIN_BINARY_SIZE}），疑似下载不完整: ${path}"
        return 1
    fi
    if have_cmd file; then
        desc="$(file -b "${path}" 2>/dev/null || true)"
        if [[ "${desc}" != *ELF* ]]; then
            warn "${label} 不是 ELF 可执行文件（file: ${desc:-未知}）: ${path}"
            return 1
        fi
        if [[ -n "${expected_arch}" ]]; then
            case "${expected_arch}" in
                x86_64)
                    if [[ "${desc}" != *x86-64* && "${desc}" != *x86_64* ]]; then
                        warn "${label} 架构可能不匹配（期望 x86_64，file: ${desc}）"
                    fi
                    ;;
                aarch64)
                    if [[ "${desc}" != *aarch64* && "${desc}" != *ARM* ]]; then
                        warn "${label} 架构可能不匹配（期望 aarch64，file: ${desc}）"
                    fi
                    ;;
            esac
        fi
    else
        log "未找到 file 命令，跳过 ELF 校验: ${label}"
    fi
    return 0
}

license_present() { # dest_dir file_name
    local dir="$1" name="$2"
    [[ -f "${dir}/${name}" ]]
}

should_skip() { # dest label arch [required_license_name] [license_dir]
    local dest="$1" label="$2" arch="$3" license_name="${4:-}" license_dir="${5:-}" dir
    [[ -f "${dest}" ]] || return 1
    if [[ "${FORCE}" -eq 1 ]]; then
        log "--force：重新获取 ${label}"
        return 1
    fi
    if ! validate_binary "${dest}" "${label}" "${arch}" 2>/dev/null; then
        warn "已存在但校验未通过，重新下载: ${dest}"
        return 1
    fi
    if [[ -n "${license_name}" ]]; then
        if [[ -n "${license_dir}" ]]; then
            dir="${license_dir}"
        else
            dir="$(dirname "${dest}")"
        fi
        if ! license_present "${dir}" "${license_name}"; then
            log "许可证文件缺失（${dir}/${license_name}），重新下载并补齐"
            return 1
        fi
    fi
    log "跳过 ${label}（已存在且校验通过）: ${dest}"
    return 0
}

download() { # url out label [accept]
    local url="$1" out="$2" label="$3" accept="${4:-}"
    local -a curl_args
    if [[ -t 1 ]]; then
        curl_args=(--progress-bar)
    else
        curl_args=(-sS)
    fi
    log "下载 ${label}"
    log "  源地址: ${url}"
    if [[ -n "${accept}" ]]; then
        curl_args+=(-H "Accept: ${accept}")
    fi
    curl_args+=(-fL --retry 3 --retry-delay 2 --connect-timeout 20 --max-time 1800 -o "${out}" "${url}")
    if ! curl "${curl_args[@]}"; then
        warn "下载失败: ${label}"
        warn "  源地址: ${url}"
        warn "  建议: 检查网络/代理设置后重试；确认 curl 可访问该域名（aria2 走 api.github.com，7z/node 走官方直链）"
        return 1
    fi
    if [[ ! -s "${out}" ]]; then
        warn "下载结果为空文件: ${label} (${out})"
        warn "  源地址: ${url}"
        warn "  建议: 检查网络/代理或更换网络后重试"
        return 1
    fi
    return 0
}

extract_zip() { # archive outdir
    local archive="$1" outdir="$2"
    mkdir -p "${outdir}"
    if ! unzip -q -o "${archive}" -d "${outdir}"; then
        warn "解压 zip 失败: ${archive}"
        warn "  建议: 确认 unzip 正常，或删除临时目录后重试（可用 --force）"
        return 1
    fi
    return 0
}

extract_tar_xz() { # archive outdir
    local archive="$1" outdir="$2"
    mkdir -p "${outdir}"
    if ! python3 -m tarfile -e "${archive}" "${outdir}"; then
        warn "解压 .tar.xz 失败: ${archive}"
        warn "  建议: 确认 python3 可用（$(python3 --version 2>&1 || echo 'python3 不可用')），或检查下载文件是否完整"
        return 1
    fi
    return 0
}

find_first_file() { # dir find-args...
    local dir="$1" found
    shift
    # 用 sed 而非 head，避免 pipefail 下 find 因 SIGPIPE 返回非零导致 set -e 退出。
    found="$(find "${dir}" -type f "$@" -print 2>/dev/null | sed -n '1p')"
    printf '%s' "${found}"
}

install_binary() { # src dest label arch
    local src="$1" dest="$2" label="$3" arch="$4"
    if [[ -z "${src}" || ! -f "${src}" ]]; then
        warn "${label} 解压产物中未找到可执行文件"
        return 1
    fi
    mkdir -p "$(dirname "${dest}")"
    if ! mv -f "${src}" "${dest}"; then
        warn "安装 ${label} 失败: ${dest}"
        return 1
    fi
    chmod 755 "${dest}"
    if ! validate_binary "${dest}" "${label}" "${arch}"; then
        warn "安装后校验失败: ${dest}"
        return 1
    fi
    log "完成 ${label} -> ${dest}"
    return 0
}

# ---- 第三方许可证 -----------------------------------------------------------
find_named_file() { # dir file_name [maxdepth]
    local dir="$1" name="$2" depth="${3:-2}" found
    # 用 sed 而非 head，避免 pipefail 下 find 因 SIGPIPE 报错。
    found="$(find "${dir}" -maxdepth "${depth}" -type f -name "${name}" -print 2>/dev/null | sed -n '1p')"
    printf '%s' "${found}"
}

install_required_license() { # extract_dir dest_dir file_name label
    local extract="$1" dest_dir="$2" name="$3" label="$4" src
    src="$(find_named_file "${extract}" "${name}" 2)"
    if [[ -z "${src}" ]]; then
        warn "未能在 ${label} 解压产物中找到许可证文件 ${name}，组件安装不完整"
        return 1
    fi
    mkdir -p "${dest_dir}"
    cp -f "${src}" "${dest_dir}/${name}"
    log "许可证 ${label}: ${dest_dir}/${name}"
    return 0
}

install_optional_licenses() { # extract_dir dest_dir label
    local extract="$1" dest_dir="$2" label="$3" name src count=0
    for name in LICENSE LICENSE.txt COPYING COPYING.txt README README.md README.txt; do
        src="$(find_named_file "${extract}" "${name}" 2)"
        [[ -n "${src}" ]] || continue
        mkdir -p "${dest_dir}"
        cp -f "${src}" "${dest_dir}/${name}"
        log "许可证/说明 ${label}: ${dest_dir}/${name}"
        count=$((count + 1))
    done
    if [[ "${count}" -eq 0 ]]; then
        log "${label} 上游压缩包未附带 LICENSE/README 文件，跳过（不编造许可证）"
    fi
    return 0
}

# ---- aria2 ------------------------------------------------------------------
# 解析结果写入全局 ARIA2_ASSET_ID（避免命令替换把日志一起捕获）。
ARIA2_ASSET_ID=""
resolve_aria2_asset_id() { # asset_name fallback_id
    local asset="$1" fallback="$2" json id
    ARIA2_ASSET_ID=""
    if ! have_cmd python3; then
        ARIA2_ASSET_ID="${fallback}"
        return 0
    fi
    json="${TMP_DIR}/aria2-release-${ARIA2_VERSION}.json"
    log "查询 aria2 release 资产列表 (api.github.com)"
    if curl -fsSL --retry 3 --retry-delay 2 --connect-timeout 20 --max-time 120 \
        -o "${json}" "${ARIA2_API_TAGS_URL}"; then
        id="$(python3 - "${json}" "${asset}" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    sys.exit(1)

for item in data.get("assets") or []:
    if item.get("name") == sys.argv[2]:
        asset_id = item.get("id")
        if asset_id:
            print(asset_id)
            sys.exit(0)
sys.exit(1)
PY
)" || id=""
        if [[ -n "${id}" ]]; then
            log "  资产 ${asset} -> id ${id}"
            ARIA2_ASSET_ID="${id}"
            return 0
        fi
        warn "未能从 GitHub API 响应解析资产 ${asset}，回退已知 id ${fallback}"
    else
        warn "GitHub API 查询失败，回退已知资产 id ${fallback}"
        warn "  源地址: ${ARIA2_API_TAGS_URL}"
        warn "  建议: 检查网络/代理；也可稍后重试（未认证 API 有频率限制）"
    fi
    ARIA2_ASSET_ID="${fallback}"
    return 0
}

fetch_aria2() { # arch
    local arch="$1" asset fallback_id asset_id url dest zip extract dir binary
    case "${arch}" in
        x86_64)
            asset="${ARIA2_X86_64_ASSET}"
            fallback_id="${ARIA2_X86_64_FALLBACK_ID}"
            ;;
        aarch64)
            asset="${ARIA2_AARCH64_ASSET}"
            fallback_id="${ARIA2_AARCH64_FALLBACK_ID}"
            ;;
        *)
            warn "aria2 不支持的架构: ${arch}"
            return 1
            ;;
    esac

    dest="${DEST}/aria2/${arch}/aria2c"
    if should_skip "${dest}" "aria2c (${arch})" "${arch}"; then
        return 0
    fi

    resolve_aria2_asset_id "${asset}" "${fallback_id}"
    asset_id="${ARIA2_ASSET_ID}"
    if [[ -z "${asset_id}" ]]; then
        warn "无法确定 aria2 ${arch} 的 release asset id"
        return 1
    fi
    url="https://api.github.com/repos/${ARIA2_REPO}/releases/assets/${asset_id}"

    zip="${TMP_DIR}/aria2-${arch}.zip"
    download "${url}" "${zip}" "aria2 ${arch} (${asset})" "application/octet-stream" || return 1

    extract="${TMP_DIR}/aria2-${arch}"
    rm -rf -- "${extract}"
    extract_zip "${zip}" "${extract}" || return 1

    dir="$(find_first_file "${extract}" -name aria2c)"
    install_binary "${dir}" "${dest}" "aria2c (${arch})" "${arch}" || return 1
    install_optional_licenses "${extract}" "$(dirname "${dest}")" "aria2c (${arch})"
}

# ---- 7z ---------------------------------------------------------------------
fetch_7z() { # arch
    local arch="$1" url dest tar extract dir
    case "${arch}" in
        x86_64) url="${SEVEN_ZIP_X86_64_URL}" ;;
        aarch64) url="${SEVEN_ZIP_AARCH64_URL}" ;;
        *)
            warn "7z 不支持的架构: ${arch}"
            return 1
            ;;
    esac

    dest="${DEST}/7z/${arch}/7zz"
    if should_skip "${dest}" "7zz (${arch})" "${arch}" "License.txt"; then
        return 0
    fi

    tar="${TMP_DIR}/7z-${arch}.tar.xz"
    download "${url}" "${tar}" "7-Zip 7zz (${arch})" || return 1

    extract="${TMP_DIR}/7z-${arch}"
    rm -rf -- "${extract}"
    extract_tar_xz "${tar}" "${extract}" || return 1

    dir="$(find_first_file "${extract}" -name 7zz)"
    install_binary "${dir}" "${dest}" "7zz (${arch})" "${arch}" || return 1
    install_required_license "${extract}" "$(dirname "${dest}")" "License.txt" "7zz (${arch})"
}

# ---- node -------------------------------------------------------------------
fetch_node() { # arch
    local arch="$1" url dest tar extract dir license_dir
    case "${arch}" in
        x86_64) url="${NODE_X86_64_URL}" ;;
        aarch64) url="${NODE_AARCH64_URL}" ;;
        *)
            warn "node 不支持的架构: ${arch}"
            return 1
            ;;
    esac

    dest="${DEST}/node/${arch}/bin/node"
    license_dir="${DEST}/node/${arch}"
    if should_skip "${dest}" "node (${arch})" "${arch}" "LICENSE" "${license_dir}"; then
        return 0
    fi

    tar="${TMP_DIR}/node-${arch}.tar.xz"
    download "${url}" "${tar}" "Node.js v${NODE_VERSION} (${arch})" || return 1

    extract="${TMP_DIR}/node-${arch}"
    rm -rf -- "${extract}"
    extract_tar_xz "${tar}" "${extract}" || return 1

    dir="$(find_first_file "${extract}" -path '*/bin/node')"
    if [[ -z "${dir}" ]]; then
        dir="$(find_first_file "${extract}" -name node)"
    fi
    install_binary "${dir}" "${dest}" "node (${arch})" "${arch}" || return 1
    install_required_license "${extract}" "${license_dir}" "LICENSE" "node (${arch})"
}

# ---- 主流程 -----------------------------------------------------------------
print_manifest() {
    local file size mb count=0
    log "运行时清单（二进制 + 第三方许可证）(${DEST}):"
    if [[ ! -d "${DEST}" ]]; then
        log "  (目录不存在)"
        return 0
    fi
    while IFS= read -r file; do
        [[ -n "${file}" ]] || continue
        size="$(wc -c <"${file}" | tr -d '[:space:]')"
        mb="$(awk -v s="${size}" 'BEGIN { printf "%.1f", s / 1048576 }')"
        printf '  %-58s %8s MB\n' "${file#"${DEST}"/}" "${mb}"
        count=$((count + 1))
    done < <(find "${DEST}" -type f | sort)
    if [[ "${count}" -eq 0 ]]; then
        log "  (空)"
    else
        log "共 ${count} 个文件"
    fi
}

for _arch in "${ARCH_LIST[@]}"; do
    for _comp in "${SELECTED[@]}"; do
        case "${_comp}" in
            aria2) FETCH_FN=fetch_aria2 ;;
            7z) FETCH_FN=fetch_7z ;;
            node) FETCH_FN=fetch_node ;;
            *) die "内部错误: 未知组件 ${_comp}" ;;
        esac
        log "==== 组件 ${_comp} / 架构 ${_arch} ===="
        if ! "${FETCH_FN}" "${_arch}"; then
            warn "组件 ${_comp} (${_arch}) 获取失败，继续处理其余组件"
            FAILURES=$((FAILURES + 1))
        fi
    done
done

if [[ "${FAILURES}" -gt 0 ]]; then
    warn "有 ${FAILURES} 项运行时获取失败，详见上方日志"
    warn "建议: 检查网络/代理后重试；或单独执行 --only <组件> 定位问题"
    print_manifest
    exit 1
fi

log "全部运行时获取完成"
print_manifest
exit 0
