#!/usr/bin/env bash
# fetch_runtime.sh - 一键补齐 freedeckCY 运行所需的 Linux 二进制
#
# 默认下载到 <repo>/defaults/runtime/：
#   aria2/<arch>/aria2c        abcfy2/aria2-static-build 1.37.0（musl 静态构建）
#   7z/<arch>/7zz              ip7z/7zip 26.06 官方 Linux 版
#   node/<arch>/bin/node       nodejs.org v24.22.3 LTS
#
# arch 统一使用 x86_64 / aarch64，与 Python 侧 platform.machine() 对齐。
# 依赖：curl；aria2 需要 unzip；7z / node 需要 python3（本机无 xz 命令，用 tarfile 解压）。
# 特性：幂等（已存在且 SHA256 校验通过则跳过，损坏文件自动删除重下）、--force 强制重下、
#       --verify-only 只校验已安装运行时、--self-test 离线自检脚本逻辑、失败时打印源地址与建议。
# 安装成功后在 <dest>/runtime-manifest.txt 记录各组件版本，供 verify_runtime.sh 做版本一致性校验。
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

# 7-Zip 版本只在这里定义一次，URL/帮助文本/自检都由它派生，避免多处漂移。
SEVEN_ZIP_VERSION="26.06"
SEVEN_ZIP_FILE_VERSION="${SEVEN_ZIP_VERSION//./}" # 26.06 -> 2606（文件名用去点版本）
SEVEN_ZIP_X86_64_URL="https://github.com/ip7z/7zip/releases/download/${SEVEN_ZIP_VERSION}/7z${SEVEN_ZIP_FILE_VERSION}-linux-x64.tar.xz"
SEVEN_ZIP_AARCH64_URL="https://github.com/ip7z/7zip/releases/download/${SEVEN_ZIP_VERSION}/7z${SEVEN_ZIP_FILE_VERSION}-linux-arm64.tar.xz"

NODE_VERSION="24.22.3"
NODE_X86_64_URL="https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz"
NODE_AARCH64_URL="https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-arm64.tar.xz"

# 当前固定版本的二进制 SHA256（下载/安装后强校验，防止镜像/代理替换）。
RUNTIME_SHA256_ARIA2_X86_64="80e577dc58348b96da46dd12d326bc99794b5021be395a3e890f2d67c8790c22"
RUNTIME_SHA256_ARIA2_AARCH64="99a057bd383a28f1d5fab6e8cc5f6f3ed4172f5e65c59548242e965454d654c1"
RUNTIME_SHA256_7Z_X86_64="f94066e93f9a807547a3bff1021b3ec79d5ea4f57dfead018e9698182ad283b5"
RUNTIME_SHA256_7Z_AARCH64="798bf71d3e2c33ae098c32965b9868e1b4ae8bfaeeba9bed06d9eabceffcd1a4"
RUNTIME_SHA256_NODE_X86_64="a7ec1b37e6ff9d187e4198c5b6df9a4eb1c74dd31804fb3bac55cc4ceca1ac01"
RUNTIME_SHA256_NODE_AARCH64="8f9c2a55879e9705cb285b6cdd649d95df642c6720f052cb30f300d2677da99f"

MIN_BINARY_SIZE=1048576 # 1 MiB，防止把 LFS 占位符 / 错误页面当成二进制

# ---- 运行参数 ---------------------------------------------------------------
DEST="${DEFAULT_DEST}"
DEST_INPUT=""
ARCH_INPUT=""
FORCE=0
VERIFY_ONLY=0
SELF_TEST=0
SELECTED=()
ARCH_LIST=()
FAILURES=0
TMP_DIR=""
TMP_BASE="${TMPDIR:-/tmp}"
TMP_BASE="${TMP_BASE%/}"
if [[ -n "${TMP_BASE}" && "${TMP_BASE}" != /* ]]; then
    # TMPDIR 可能是相对路径；清理逻辑按绝对路径匹配，这里统一成绝对路径。
    TMP_BASE="$(pwd -P)/${TMP_BASE}"
fi

# GitHub API 未认证时有 60 次/小时限流，CI 传入 GITHUB_TOKEN 可避免随机 403。
GITHUB_TOKEN_VALUE="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
GITHUB_AUTH_ARGS=()
if [[ -n "${GITHUB_TOKEN_VALUE}" ]]; then
    GITHUB_AUTH_ARGS=(-H "Authorization: Bearer ${GITHUB_TOKEN_VALUE}")
fi

# ---- 输出辅助 ---------------------------------------------------------------
log() { printf '[runtime] %s\n' "$*"; }
warn() { printf '[runtime][warn] %s\n' "$*" >&2; }
die() {
    printf '[runtime][error] %s\n' "$*" >&2
    exit 2
}

usage() {
    cat <<EOF
用法: bash scripts/fetch_runtime.sh [选项]

下载 freedeckCY 运行所需的 Linux 二进制到 defaults/runtime/：
  aria2/<arch>/aria2c       aria2 ${ARIA2_VERSION} 静态构建（来自 ${ARIA2_REPO}）
  7z/<arch>/7zz             7-Zip ${SEVEN_ZIP_VERSION} 官方 Linux 版
  node/<arch>/bin/node      Node.js v${NODE_VERSION}（天翼 JS 解析器使用）

选项:
  --arch <x86_64|aarch64|all>  目标架构，默认按本机 uname -m 自动识别
  --only <aria2|7z|node>       只下载指定组件；可重复，也可逗号分隔
  --dest <目录>                输出目录，默认 <repo>/defaults/runtime
  -f, --force                  已存在也强制重新下载
  --verify-only                只校验 --dest 里已安装的运行时（不联网、不下载）
  --self-test                  离线自检脚本逻辑（版本一致性/SHA/跳过与损坏重下判断）
  -h, --help                   显示本帮助并退出

示例:
  bash scripts/fetch_runtime.sh                        # 本机架构，下载全部组件
  bash scripts/fetch_runtime.sh --arch all             # Steam Deck(x86_64) + ARM 设备
  bash scripts/fetch_runtime.sh --only aria2,7z        # 只补 aria2 与 7z
  bash scripts/fetch_runtime.sh --only 7z --arch x86_64 --force
  bash scripts/fetch_runtime.sh --verify-only          # 校验 defaults/runtime 是否完整
  bash scripts/fetch_runtime.sh --self-test            # CI/本地离线自检

说明:
  - github.com 网页不可直连，aria2 通过 api.github.com 取 release asset 字节流；
    设置环境变量 GITHUB_TOKEN（CI 默认注入）可避免未认证 API 限流。
  - 本机无 xz 命令，.tar.xz 使用 python3 -m tarfile 解压。
  - 已存在且校验（大小 > 1MiB、file 显示 ELF、SHA256 匹配固定版本）通过的二进制默认跳过；
    已存在但 SHA256 不匹配（损坏/被替换）会自动删除并重新下载，不需要手加 --force。
  - 会把第三方许可证一并放入运行时目录：node/<arch>/LICENSE、7z/<arch>/License.txt；
    aria2 上游 zip 仅含 aria2c，没有可拷贝的许可证/说明文件时会明确跳过（不编造）。
  - 安装完成后写 <dest>/runtime-manifest.txt（组件版本），verify_runtime.sh 据此校验
    Node/7-Zip/aria2 实际版本，避免"二进制能跑但版本不对"。
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
        --verify-only)
            VERIFY_ONLY=1
            shift
            ;;
        --self-test)
            SELF_TEST=1
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

should_skip() { # dest label arch [expected_sha256] [required_license_name] [license_dir]
    local dest="$1" label="$2" arch="$3" expected="${4:-}" license_name="${5:-}" license_dir="${6:-}" dir
    [[ -f "${dest}" ]] || return 1
    if [[ "${FORCE}" -eq 1 ]]; then
        log "--force：重新获取 ${label}"
        return 1
    fi
    if ! validate_binary "${dest}" "${label}" "${arch}" 2>/dev/null; then
        warn "已存在但校验未通过，重新下载: ${dest}"
        return 1
    fi
    if ! verify_binary_sha256 "${dest}" "${expected}" "${label}"; then
        # 大小/ELF 正常但 SHA 不符，说明是损坏/被替换/错版本：删除后走正常下载流程，
        # 否则每次重跑都会"跳过 -> SHA 失败 -> 整体失败"，只能靠 --force 人工解围。
        warn "已存在但 SHA256 与固定版本不一致，删除并重新下载: ${dest}"
        rm -f -- "${dest}"
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

download() { # url out label [accept] [github_api]
    local url="$1" out="$2" label="$3" accept="${4:-}" github_api="${5:-}"
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
    if [[ -n "${github_api}" && ${#GITHUB_AUTH_ARGS[@]} -gt 0 ]]; then
        curl_args+=("${GITHUB_AUTH_ARGS[@]}")
    fi
    curl_args+=(-fL --retry 3 --retry-delay 2 --connect-timeout 20 --max-time 1800 -o "${out}" "${url}")
    if ! curl "${curl_args[@]}"; then
        # GitHub 直链在部分网络下 HTTP/2 framing 会失败，回退 HTTP/1.1 再试一次。
        warn "下载失败，尝试 HTTP/1.1 重试: ${label}"
        rm -f -- "${out}"
        if ! curl --http1.1 "${curl_args[@]}"; then
            warn "下载失败: ${label}"
            warn "  源地址: ${url}"
            warn "  建议: 检查网络/代理设置后重试；确认 curl 可访问该域名（aria2 走 api.github.com，7z/node 走官方直链）"
            return 1
        fi
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

file_sha256() { # path
    local path="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "${path}" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "${path}" | awk '{print $1}'
    else
        return 1
    fi
}

verify_binary_sha256() { # path expected label
    local path="$1" expected="$2" label="$3" actual=""
    [[ -n "${expected}" ]] || return 0
    if ! actual="$(file_sha256 "${path}")"; then
        warn "缺少 sha256sum/shasum，无法校验 ${label}"
        return 1
    fi
    if [[ "${actual}" != "${expected}" ]]; then
        warn "${label} SHA256 不匹配（期望 ${expected}，实际 ${actual}）"
        return 1
    fi
    log "SHA256 校验通过 ${label}"
    return 0
}

install_binary() { # src dest label arch [expected_sha256]
    local src="$1" dest="$2" label="$3" arch="$4" expected="${5:-}"
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
        warn "安装后校验失败，删除损坏文件: ${dest}"
        rm -f -- "${dest}"
        return 1
    fi
    if ! verify_binary_sha256 "${dest}" "${expected}" "${label}"; then
        warn "安装后 SHA256 校验失败，删除损坏文件: ${dest}"
        rm -f -- "${dest}"
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
    # bash 3.2(macOS) 下空数组展开会触发 set -u，因此先构造非空命令数组。
    local -a curl_cmd=(curl -fsSL --retry 3 --retry-delay 2 --connect-timeout 20 --max-time 120)
    if [[ ${#GITHUB_AUTH_ARGS[@]} -gt 0 ]]; then
        curl_cmd+=("${GITHUB_AUTH_ARGS[@]}")
    fi
    curl_cmd+=(-o "${json}" "${ARIA2_API_TAGS_URL}")
    if "${curl_cmd[@]}"; then
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
    local expected=""
    case "${arch}" in
        x86_64) expected="${RUNTIME_SHA256_ARIA2_X86_64}" ;;
        aarch64) expected="${RUNTIME_SHA256_ARIA2_AARCH64}" ;;
    esac
    if should_skip "${dest}" "aria2c (${arch})" "${arch}" "${expected}"; then
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
    download "${url}" "${zip}" "aria2 ${arch} (${asset})" "application/octet-stream" "github-api" || return 1

    extract="${TMP_DIR}/aria2-${arch}"
    rm -rf -- "${extract}"
    extract_zip "${zip}" "${extract}" || return 1

    dir="$(find_first_file "${extract}" -name aria2c)"
    install_binary "${dir}" "${dest}" "aria2c (${arch})" "${arch}" "${expected}" || return 1
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
    local expected=""
    case "${arch}" in
        x86_64) expected="${RUNTIME_SHA256_7Z_X86_64}" ;;
        aarch64) expected="${RUNTIME_SHA256_7Z_AARCH64}" ;;
    esac
    if should_skip "${dest}" "7zz (${arch})" "${arch}" "${expected}" "License.txt"; then
        return 0
    fi

    tar="${TMP_DIR}/7z-${arch}.tar.xz"
    download "${url}" "${tar}" "7-Zip 7zz (${arch})" || return 1

    extract="${TMP_DIR}/7z-${arch}"
    rm -rf -- "${extract}"
    extract_tar_xz "${tar}" "${extract}" || return 1

    dir="$(find_first_file "${extract}" -name 7zz)"
    install_binary "${dir}" "${dest}" "7zz (${arch})" "${arch}" "${expected}" || return 1
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
    local expected=""
    case "${arch}" in
        x86_64) expected="${RUNTIME_SHA256_NODE_X86_64}" ;;
        aarch64) expected="${RUNTIME_SHA256_NODE_AARCH64}" ;;
    esac
    if should_skip "${dest}" "node (${arch})" "${arch}" "${expected}" "LICENSE" "${license_dir}"; then
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
    install_binary "${dir}" "${dest}" "node (${arch})" "${arch}" "${expected}" || return 1
    install_required_license "${extract}" "${license_dir}" "LICENSE" "node (${arch})"
}

# ---- 版本清单（供 verify_runtime.sh 校验实际版本） --------------------------
MANIFEST_NAME="runtime-manifest.txt"

component_version() { # comp
    case "$1" in
        aria2) printf '%s' "${ARIA2_VERSION}" ;;
        7z) printf '%s' "${SEVEN_ZIP_VERSION}" ;;
        node) printf '%s' "${NODE_VERSION}" ;;
        *) printf '' ;;
    esac
}

manifest_version_of() { # comp -> 旧清单里的版本（没有则空）
    local comp="$1" line
    [[ -f "${DEST}/${MANIFEST_NAME}" ]] || return 0
    while IFS= read -r line; do
        case "${line}" in
            "${comp}="*) printf '%s' "${line#*=}"; return 0 ;;
        esac
    done <"${DEST}/${MANIFEST_NAME}"
    return 0
}

write_runtime_manifest() {
    local comp="" item="" line value
    local -a lines=()
    for comp in aria2 7z node; do
        value=""
        for item in "${SELECTED[@]}"; do
            if [[ "${item}" == "${comp}" ]]; then
                value="$(component_version "${comp}")"
                break
            fi
        done
        # 本次只跑 --only 7z 时，其它组件沿用旧清单里的版本，不要丢。
        if [[ -z "${value}" ]]; then
            value="$(manifest_version_of "${comp}")"
        fi
        if [[ -n "${value}" ]]; then
            lines+=("${comp}=${value}")
        fi
    done
    {
        echo "# freedeckCY runtime manifest（scripts/fetch_runtime.sh 生成，请勿手改）"
        # bash 3.2 下空数组展开会触发 set -u，先判长度。
        if [[ ${#lines[@]} -gt 0 ]]; then
            for line in "${lines[@]}"; do
                echo "${line}"
            done
        fi
    } >"${DEST}/${MANIFEST_NAME}"
    log "已写入版本清单: ${DEST}/${MANIFEST_NAME}"
}

# ---- 只校验模式（不联网） ---------------------------------------------------
runtime_binary_path() { # comp arch
    case "$1" in
        aria2) printf '%s/aria2/%s/aria2c' "${DEST}" "$2" ;;
        7z) printf '%s/7z/%s/7zz' "${DEST}" "$2" ;;
        node) printf '%s/node/%s/bin/node' "${DEST}" "$2" ;;
        *) printf '' ;;
    esac
}

runtime_expected_sha() { # comp arch
    case "$1:$2" in
        aria2:x86_64) printf '%s' "${RUNTIME_SHA256_ARIA2_X86_64}" ;;
        aria2:aarch64) printf '%s' "${RUNTIME_SHA256_ARIA2_AARCH64}" ;;
        7z:x86_64) printf '%s' "${RUNTIME_SHA256_7Z_X86_64}" ;;
        7z:aarch64) printf '%s' "${RUNTIME_SHA256_7Z_AARCH64}" ;;
        node:x86_64) printf '%s' "${RUNTIME_SHA256_NODE_X86_64}" ;;
        node:aarch64) printf '%s' "${RUNTIME_SHA256_NODE_AARCH64}" ;;
        *) printf '' ;;
    esac
}

runtime_license_path() { # comp arch
    case "$1" in
        7z) printf '%s/7z/%s/License.txt' "${DEST}" "$2" ;;
        node) printf '%s/node/%s/LICENSE' "${DEST}" "$2" ;;
        *) printf '' ;;
    esac
}

verify_installed_runtime() {
    local failures=0 arch comp dest expected license
    log "只校验模式: ${DEST}（架构: ${ARCH_LIST[*]}，组件: ${SELECTED[*]}）"
    if [[ ! -d "${DEST}" ]]; then
        warn "运行时目录不存在: ${DEST}"
        warn "建议: 先执行 bash scripts/fetch_runtime.sh"
        return 1
    fi
    for arch in "${ARCH_LIST[@]}"; do
        for comp in "${SELECTED[@]}"; do
            dest="$(runtime_binary_path "${comp}" "${arch}")"
            expected="$(runtime_expected_sha "${comp}" "${arch}")"
            if [[ ! -f "${dest}" ]]; then
                warn "缺少 ${comp} (${arch}): ${dest}"
                failures=$((failures + 1))
                continue
            fi
            if ! validate_binary "${dest}" "${comp} (${arch})" "${arch}"; then
                failures=$((failures + 1))
                continue
            fi
            if ! verify_binary_sha256 "${dest}" "${expected}" "${comp} (${arch})"; then
                failures=$((failures + 1))
                continue
            fi
            license="$(runtime_license_path "${comp}" "${arch}")"
            if [[ -n "${license}" && ! -f "${license}" ]]; then
                warn "${comp} (${arch}) 缺少第三方许可证: ${license}"
                failures=$((failures + 1))
                continue
            fi
            log "校验通过 ${comp} (${arch}): ${dest}"
        done
    done
    if [[ -f "${DEST}/${MANIFEST_NAME}" ]]; then
        for comp in "${SELECTED[@]}"; do
            expected="$(component_version "${comp}")"
            if ! grep -qx "${comp}=${expected}" "${DEST}/${MANIFEST_NAME}" 2>/dev/null; then
                warn "${MANIFEST_NAME} 中缺少 ${comp}=${expected}（旧清单，可重跑 fetch_runtime.sh 更新）"
            fi
        done
    else
        warn "未找到 ${DEST}/${MANIFEST_NAME}（旧版运行时目录），跳过版本清单校验"
    fi
    if [[ "${failures}" -gt 0 ]]; then
        warn "只校验模式失败: ${failures} 项"
        return 1
    fi
    log "只校验模式通过"
    return 0
}

# ---- 离线自检 ---------------------------------------------------------------
SELF_TEST_CHECKS=0
self_test_ok() { # message
    SELF_TEST_CHECKS=$((SELF_TEST_CHECKS + 1))
    printf '[runtime][self-test] ok %s\n' "$*"
}

self_test_fail() { # message
    printf '[runtime][self-test][fail] %s\n' "$*" >&2
    return 1
}

evaluate_skip_decision() { # dest label arch expected
    # 自检复用 should_skip 的真实逻辑（成功=0 表示"跳过"，非 0 表示需要重新下载）。
    should_skip "$1" "$2" "$3" "$4" >/dev/null 2>&1
}

run_self_test() {
    local tmp help_text good_sha
    log "离线自检（不联网、不下载）"

    # 1) 版本单一来源：帮助文本与 URL 必须和常量一致（防止升级时漏改一处）。
    help_text="$(usage)"
    local version
    for version in "${ARIA2_VERSION}" "${SEVEN_ZIP_VERSION}" "${NODE_VERSION}"; do
        if ! grep -Fq "${version}" <<<"${help_text}"; then
            self_test_fail "帮助文本缺少版本 ${version}"
            return 1
        fi
    done
    self_test_ok "帮助文本版本与常量一致（aria2 ${ARIA2_VERSION} / 7z ${SEVEN_ZIP_VERSION} / node ${NODE_VERSION}）"

    if [[ "${SEVEN_ZIP_X86_64_URL}" != *"/${SEVEN_ZIP_VERSION}/7z${SEVEN_ZIP_FILE_VERSION}-linux-x64.tar.xz" ]]; then
        self_test_fail "7-Zip x86_64 URL 未使用版本常量: ${SEVEN_ZIP_X86_64_URL}"
        return 1
    fi
    if [[ "${SEVEN_ZIP_AARCH64_URL}" != *"/${SEVEN_ZIP_VERSION}/7z${SEVEN_ZIP_FILE_VERSION}-linux-arm64.tar.xz" ]]; then
        self_test_fail "7-Zip aarch64 URL 未使用版本常量: ${SEVEN_ZIP_AARCH64_URL}"
        return 1
    fi
    if [[ "${NODE_X86_64_URL}" != *"v${NODE_VERSION}"* ]]; then
        self_test_fail "Node x86_64 URL 未使用版本常量: ${NODE_X86_64_URL}"
        return 1
    fi
    self_test_ok "7-Zip/Node 下载 URL 由版本常量派生"

    # 2) 架构归一化。
    if [[ "$(normalize_arch 'AMD64')" != "amd64" ]]; then
        self_test_fail "normalize_arch(AMD64) 结果异常"
        return 1
    fi
    valid_arch x86_64 || { self_test_fail "valid_arch(x86_64) 失败"; return 1; }
    valid_arch aarch64 || { self_test_fail "valid_arch(aarch64) 失败"; return 1; }
    if valid_arch armv7; then
        self_test_fail "valid_arch(armv7) 不应通过"
        return 1
    fi
    self_test_ok "架构归一化/白名单正确"

    # 3) SHA256 校验本身。
    tmp="$(mktemp -d "${TMP_BASE}/freedeckcy-runtime-selftest.XXXXXX")"
    printf 'selftest-%s' "$(date +%s)" >"${tmp}/payload"
    if ! good_sha="$(file_sha256 "${tmp}/payload")"; then
        self_test_fail "无法计算 SHA256（缺少 sha256sum/shasum）"
        rm -rf -- "${tmp}"
        return 1
    fi
    if ! verify_binary_sha256 "${tmp}/payload" "${good_sha}" "self-test payload" >/dev/null 2>&1; then
        self_test_fail "verify_binary_sha256 对正确哈希失败"
        rm -rf -- "${tmp}"
        return 1
    fi
    if verify_binary_sha256 "${tmp}/payload" "deadbeef" "self-test payload" >/dev/null 2>&1; then
        self_test_fail "verify_binary_sha256 对错误哈希不应通过"
        rm -rf -- "${tmp}"
        return 1
    fi
    self_test_ok "SHA256 校验对正确/错误哈希判断正确"

    # 4) 损坏二进制会被"跳过判定"拒绝并删除，随后走重下流程（不再卡死在 SHA 失败）。
    python3 - "${tmp}/fake-elf" <<'PY' 2>/dev/null || true
import sys

with open(sys.argv[1], "wb") as fh:
    fh.write(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * (1048576 + 8))
PY
    if [[ ! -f "${tmp}/fake-elf" ]]; then
        self_test_fail "无法生成自检用 ELF 占位文件（需要 python3）"
        rm -rf -- "${tmp}"
        return 1
    fi
    good_sha="$(file_sha256 "${tmp}/fake-elf")"
    if ! evaluate_skip_decision "${tmp}/fake-elf" "self-test" "" "${good_sha}"; then
        self_test_fail "正确 SHA 的二进制未被跳过"
        rm -rf -- "${tmp}"
        return 1
    fi
    cp -f "${tmp}/fake-elf" "${tmp}/corrupt-elf"
    printf 'X' >>"${tmp}/corrupt-elf"
    if evaluate_skip_decision "${tmp}/corrupt-elf" "self-test" "" "${good_sha}"; then
        self_test_fail "SHA 不符的二进制不应被跳过"
        rm -rf -- "${tmp}"
        return 1
    fi
    if [[ -f "${tmp}/corrupt-elf" ]]; then
        self_test_fail "SHA 不符的二进制应被删除以便重新下载"
        rm -rf -- "${tmp}"
        return 1
    fi
    self_test_ok "损坏/错版本二进制会删除并重新下载（幂等可自愈）"

    # 5) 组件版本映射与固定 SHA 映射。
    if [[ "$(component_version aria2)" != "${ARIA2_VERSION}" ]]; then
        self_test_fail "component_version aria2 错误"
        rm -rf -- "${tmp}"
        return 1
    fi
    if [[ "$(component_version 7z)" != "${SEVEN_ZIP_VERSION}" ]]; then
        self_test_fail "component_version 7z 错误"
        rm -rf -- "${tmp}"
        return 1
    fi
    if [[ "$(component_version node)" != "${NODE_VERSION}" ]]; then
        self_test_fail "component_version node 错误"
        rm -rf -- "${tmp}"
        return 1
    fi
    if [[ "$(runtime_expected_sha 7z x86_64)" != "${RUNTIME_SHA256_7Z_X86_64}" ]]; then
        self_test_fail "runtime_expected_sha 映射错误"
        rm -rf -- "${tmp}"
        return 1
    fi
    self_test_ok "组件版本/固定 SHA 映射正确"

    rm -rf -- "${tmp}"
    printf '[runtime][self-test] 全部通过（%s 项）\n' "${SELF_TEST_CHECKS}"
    return 0
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

main_runtime() {
    # ---- 依赖预检 ----
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
    if [[ -n "${GITHUB_TOKEN_VALUE}" ]]; then
        log "GitHub API: 已配置 GITHUB_TOKEN（避免未认证限流）"
    fi

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

    write_runtime_manifest
    log "全部运行时获取完成"
    print_manifest
    exit 0
}

# ---- 入口分派 ---------------------------------------------------------------
if [[ "${SELF_TEST}" -eq 1 ]]; then
    run_self_test
    exit $?
fi
if [[ "${VERIFY_ONLY}" -eq 1 ]]; then
    verify_installed_runtime
    exit $?
fi
main_runtime
