#!/usr/bin/env bash
# package.sh - 组装可安装的 Decky 插件 zip
#
# 产物：dist-artifacts/freedeckCY-v<package.json version>.zip
# zip 根目录直接是插件根（不额外套一层目录），包含：
#   main.py plugin.json package.json LICENSE README.md
#   dist/ py_modules/ backend/ defaults/
# 排除：__pycache__、*.pyc、.DS_Store、node_modules、.git、tests、scripts、
#       .github、docs、gl、dist-artifacts（以及打包白名单之外的一切）。
# 默认复用已提交的 dist/index.js；只有传入 --build-ui 才执行 pnpm build。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
DEFAULT_OUT_DIR="$REPO_ROOT/dist-artifacts"

OUT_DIR="$DEFAULT_OUT_DIR"
OUT_DIR_INPUT=""
BUILD_UI=0
STAGE=""
TMP_BASE="${TMPDIR:-/tmp}"
TMP_BASE="${TMP_BASE%/}"

# 打包进入 zip 根的顶层目录（按顺序复制）。
PACKAGE_DIRS=(dist py_modules backend defaults)
# 打包进入 zip 根的文件（前三个必需，其余存在才复制）。
PACKAGE_FILES_REQUIRED=(main.py plugin.json package.json)
PACKAGE_FILES_OPTIONAL=(LICENSE README.md)

log() { printf '[package] %s\n' "$*"; }
warn() { printf '[package][warn] %s\n' "$*" >&2; }
die() {
    printf '[package][error] %s\n' "$*" >&2
    exit 2
}

usage() {
    cat <<'EOF'
用法: bash scripts/package.sh [选项]

组装 Decky 插件 zip 到 dist-artifacts/freedeckCY-v<version>.zip：
  - zip 根目录直接是 main.py / plugin.json / package.json / LICENSE / README.md
    以及 dist/、py_modules/、backend/、defaults/
  - 版本号取自 package.json
  - 默认复用已提交的 dist/index.js，不强制构建前端
  - 若 defaults/runtime 缺失只警告（提示先跑 fetch_runtime.sh），不中断

环境变量:
  PACKAGE_ARCH       目标架构：x86_64（默认）| aarch64 | all
                     aarch64 产物名带 -arm64 后缀；all 产物名带 -universal 后缀

选项:
  --build-ui         打包前执行 `pnpm build` 重新构建前端（需要 pnpm；默认不构建）
  --out-dir <目录>   输出目录，默认 <repo>/dist-artifacts
  -h, --help         显示本帮助并退出

示例:
  bash scripts/package.sh
  bash scripts/package.sh --build-ui
  bash scripts/package.sh --out-dir /tmp/freedeckcy-build

说明:
  打包过程在 mktemp 临时目录组装，zip 使用 `cd 临时目录 && zip -qr` 保证根结构；
  退出时自动清理临时目录。
EOF
}

have_cmd() { command -v "$1" >/dev/null 2>&1; }

cleanup() {
    if [[ -n "${STAGE:-}" && -d "$STAGE" ]]; then
        # 只删除本脚本用 mktemp 创建的临时目录
        case "$STAGE" in
            "${TMP_BASE}"/freedeckcy-package.*) rm -rf -- "$STAGE" ;;
            *) warn "跳过清理非预期临时目录: ${STAGE}" ;;
        esac
    fi
}

# ---- 参数解析 ---------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h | --help)
            usage
            exit 0
            ;;
        --build-ui)
            BUILD_UI=1
            shift
            ;;
        --out-dir)
            [[ $# -ge 2 ]] || die "--out-dir 需要一个目录路径"
            OUT_DIR_INPUT="$2"
            shift 2
            ;;
        --out-dir=*)
            OUT_DIR_INPUT="${1#*=}"
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

if [[ -n "$OUT_DIR_INPUT" ]]; then
    case "$OUT_DIR_INPUT" in
        /*) OUT_DIR="$OUT_DIR_INPUT" ;;
        *) OUT_DIR="$(pwd -P)/$OUT_DIR_INPUT" ;;
    esac
fi
[[ -n "$OUT_DIR" ]] || die "--out-dir 不能为空"

command -v zip >/dev/null 2>&1 || die "缺少 zip 命令，无法生成插件包（Debian/Ubuntu: apt install zip；Arch: pacman -S zip）"
command -v tar >/dev/null 2>&1 || die "缺少 tar 命令，无法组装插件包"

# ---- 前置检查 ---------------------------------------------------------------
cd "$REPO_ROOT"

for _f in "${PACKAGE_FILES_REQUIRED[@]}"; do
    [[ -f "$REPO_ROOT/$_f" ]] || die "缺少必需文件: ${_f}（请在仓库根目录执行：${REPO_ROOT}）"
done
for _d in "${PACKAGE_DIRS[@]}"; do
    [[ -d "$REPO_ROOT/$_d" ]] || die "缺少必需目录: ${_d}/（请在仓库根目录执行：${REPO_ROOT}）"
done

if [[ "$BUILD_UI" -eq 1 ]]; then
    if ! have_cmd pnpm; then
        die "--build-ui 需要 pnpm，但当前 PATH 中没有 pnpm。
  建议：去掉 --build-ui 直接复用已提交的 dist/index.js；
  或先安装 pnpm（corepack enable pnpm / npm i -g pnpm）并执行 pnpm install。"
    fi
    log "构建前端: pnpm build"
    if ! pnpm build; then
        die "pnpm build 失败：请检查 node/pnpm 版本及依赖安装（pnpm install）后重试"
    fi
fi
[[ -f "$REPO_ROOT/dist/index.js" ]] ||
    die "dist/index.js 不存在：请先构建前端（pnpm build 或 bash scripts/package.sh --build-ui），或恢复已提交的 dist/"

# 版本号：优先 python3 解析 JSON，回退 sed；只允许安全字符。
read_version() {
    local pkg="$1" version=""
    if have_cmd python3; then
        version="$(python3 - "$pkg" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
except Exception as exc:
    print("PARSE_ERROR:%s" % exc, file=sys.stderr)
    sys.exit(1)
version = str(data.get("version") or "").strip()
if not version:
    print("PARSE_ERROR:package.json 缺少 version 字段", file=sys.stderr)
    sys.exit(1)
print(version)
PY
)" || version=""
    fi
    if [[ -z "$version" ]]; then
        version="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$pkg" | head -n 1)"
    fi
    printf '%s' "$version"
}

VERSION_RAW="$(read_version "$REPO_ROOT/package.json")"
[[ -n "$VERSION_RAW" ]] || die "无法从 package.json 读取 version 字段"
VERSION="$(printf '%s' "$VERSION_RAW" | tr -cd 'A-Za-z0-9._+~-')"
[[ -n "$VERSION" ]] || die "package.json version 含非法字符，处理后为空: ${VERSION_RAW}"

PACKAGE_ARCH="${PACKAGE_ARCH:-x86_64}"
case "$PACKAGE_ARCH" in
    x86_64 | aarch64 | all) ;;
    *) die "PACKAGE_ARCH 仅支持 x86_64|aarch64|all（当前: ${PACKAGE_ARCH}）" ;;
esac
ARCH_SUFFIX=""
if [[ "$PACKAGE_ARCH" == "aarch64" ]]; then
    ARCH_SUFFIX="-arm64"
elif [[ "$PACKAGE_ARCH" == "all" ]]; then
    ARCH_SUFFIX="-universal"
fi

log "插件版本: ${VERSION_RAW}"
log "目标架构: ${PACKAGE_ARCH}"

# ---- 运行时提示（缺失只警告） ----------------------------------------------
if [[ ! -d "$REPO_ROOT/defaults/runtime" ]]; then
    warn "defaults/runtime/ 不存在：插件将回退系统 aria2c/7zz/node，Steam Deck 上通常没有。"
    warn "建议先执行: bash scripts/fetch_runtime.sh（或 make runtime）"
else
    runtime_has_binary() { # comp_file_name
        local name="$1"
        local found
        if [[ "$PACKAGE_ARCH" == "all" ]]; then
            found="$(find "$REPO_ROOT/defaults/runtime" -type f -name "$name" | sed -n '1p')"
        else
            found="$(find "$REPO_ROOT/defaults/runtime" -type f -path "*/${PACKAGE_ARCH}/*" -name "$name" | sed -n '1p')"
        fi
        [[ -n "$found" ]]
    }
    runtime_has_binary aria2c || warn "defaults/runtime/${PACKAGE_ARCH}/ 中没有 aria2c：建议先 bash scripts/fetch_runtime.sh --arch ${PACKAGE_ARCH}"
    runtime_has_binary 7zz || warn "defaults/runtime/${PACKAGE_ARCH}/ 中没有 7zz：建议先 bash scripts/fetch_runtime.sh --arch ${PACKAGE_ARCH}"
    runtime_has_binary node || warn "defaults/runtime/${PACKAGE_ARCH}/ 中没有 node：建议先 bash scripts/fetch_runtime.sh --arch ${PACKAGE_ARCH}"
    [[ -f "$REPO_ROOT/defaults/ludusavi/manifest.json.gz" ]] || warn "缺少 defaults/ludusavi/manifest.json.gz：自动云存档只会退回 Proton 目录扫描（make ludusavi-manifest）"
fi

# ---- 组装暂存目录 -----------------------------------------------------------
STAGE="$(mktemp -d "${TMP_BASE}/freedeckcy-package.XXXXXX")"
trap cleanup EXIT INT TERM

# macOS 下避免 tar 把扩展属性写成 ._* 文件
export COPYFILE_DISABLE=1

copy_file() { # rel_path
    local rel="$1" src="$REPO_ROOT/$1"
    if [[ ! -f "$src" ]]; then
        warn "跳过不存在的文件: ${rel}"
        return 0
    fi
    mkdir -p "$STAGE/$(dirname "$rel")"
    cp -p "$src" "$STAGE/$rel"
    log "复制 ${rel}"
    return 0
}

copy_tree() { # rel_dir
    local rel="$1" src="$REPO_ROOT/$1"
    if [[ ! -d "$src" ]]; then
        warn "跳过不存在的目录: ${rel}/"
        return 0
    fi
    mkdir -p "$STAGE/$rel"
    # 白名单复制 + 统一排除缓存/版本库/依赖目录
    tar -C "$src" -cf - \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='*.pyo' \
        --exclude='.DS_Store' \
        --exclude='node_modules' \
        --exclude='.git' \
        . | tar -C "$STAGE/$rel" -xf -
    log "复制 ${rel}/"
    return 0
}

for _f in "${PACKAGE_FILES_REQUIRED[@]}"; do
    copy_file "$_f"
done
for _f in "${PACKAGE_FILES_OPTIONAL[@]}"; do
    copy_file "$_f"
done
for _d in "${PACKAGE_DIRS[@]}"; do
    copy_tree "$_d"
done

# 单架构打包：删掉 defaults/runtime 下其它架构，避免包体积翻倍
if [[ "$PACKAGE_ARCH" != "all" && -d "$STAGE/defaults/runtime" ]]; then
    for _component in aria2 7z node; do
        _dir="$STAGE/defaults/runtime/$_component"
        [[ -d "$_dir" ]] || continue
        find "$_dir" -mindepth 1 -maxdepth 1 -type d ! -name "$PACKAGE_ARCH" -exec rm -rf {} + 2>/dev/null || true
    done
    log "已裁剪运行时到 ${PACKAGE_ARCH}"
fi

# ---- 校验暂存内容 -----------------------------------------------------------
for _f in main.py plugin.json package.json dist/index.js; do
    [[ -f "$STAGE/$_f" ]] || die "打包暂存目录缺少 ${_f}"
done
[[ -d "$STAGE/py_modules" ]] || die "打包暂存目录缺少 py_modules/"
[[ -d "$STAGE/defaults" ]] || die "打包暂存目录缺少 defaults/"
[[ -f "$STAGE/backend/tianyi_share_resolver.js" ]] || warn "backend/tianyi_share_resolver.js 缺失：天翼 JS 分享解析可能不可用"

# ---- 生成 zip ---------------------------------------------------------------
mkdir -p "$OUT_DIR"
[[ -d "$OUT_DIR" ]] || die "无法创建输出目录: ${OUT_DIR}"
OUT_ZIP="$OUT_DIR/freedeckCY-v${VERSION}${ARCH_SUFFIX}.zip"
if [[ -f "$OUT_ZIP" ]]; then
    rm -f -- "$OUT_ZIP"
fi

log "生成 ${OUT_ZIP}"
(
    cd "$STAGE"
    # zip 根目录即插件根，不额外套目录；-x 为防御性排除（正常在复制阶段已排除）。
    zip -qr "$OUT_ZIP" . \
        -x '*/__pycache__/*' '__pycache__/*' '*__pycache__*' \
        '*.pyc' '*.pyo' \
        '*/.DS_Store' '.DS_Store' \
        '*/node_modules/*' 'node_modules/*' '*node_modules*' \
        '*/.git/*' '.git/*' \
        '*/tests/*' 'tests/*' \
        '*/scripts/*' 'scripts/*' \
        '*/.github/*' '.github/*' \
        '*/docs/*' 'docs/*' \
        '*/gl/*' 'gl/*' \
        '*/dist-artifacts/*' 'dist-artifacts/*'
)
[[ -f "$OUT_ZIP" ]] || die "zip 生成失败: ${OUT_ZIP}"

# ---- 产物校验与清单 ---------------------------------------------------------
ZIP_BYTES="$(wc -c <"$OUT_ZIP" | tr -d '[:space:]')"
ZIP_MB="$(awk -v s="$ZIP_BYTES" 'BEGIN { printf "%.1f", s / 1048576 }')"

if have_cmd unzip; then
    # 一次性取出条目列表：避免 `unzip | grep -q` 在 pipefail 下因 SIGPIPE 误报失败。
    ZIP_LIST="$(unzip -Z1 "$OUT_ZIP")"
    ENTRIES="$(printf '%s\n' "$ZIP_LIST" | wc -l | tr -d '[:space:]')"
    log "条目数: ${ENTRIES}"
    log "zip 顶层结构:"
    printf '%s\n' "$ZIP_LIST" | awk -F/ 'NF > 0 && $1 != "" { print $1 }' | sort -u | sed 's/^/  /'

    # 根目录必需条目检查
    ROOT_ENTRIES_OK=1
    for _entry in main.py plugin.json package.json dist/index.js py_modules/aria2_manager.py; do
        if grep -qx "$_entry" <<<"$ZIP_LIST"; then
            log "根条目存在: ${_entry}"
        else
            warn "zip 根目录缺少必需条目: ${_entry}"
            ROOT_ENTRIES_OK=0
        fi
    done
    if [[ "$ROOT_ENTRIES_OK" -ne 1 ]]; then
        die "zip 根结构校验失败: ${OUT_ZIP}"
    fi

    # 排除规则检查
    LEAKED="$(printf '%s\n' "$ZIP_LIST" |
        grep -E '(__pycache__|\.pyc$|\.pyo$|\.DS_Store$|(^|/)node_modules/|(^|/)\.git/|^tests/|^scripts/|^\.github/|^docs/|^gl/|^dist-artifacts/)' || true)"
    if [[ -n "$LEAKED" ]]; then
        warn "zip 中发现应排除的条目（请检查打包规则）:"
        printf '%s\n' "$LEAKED" | sed 's/^/  /'
    else
        log "排除规则检查通过（无 __pycache__/*.pyc/.DS_Store/node_modules/.git/tests/scripts/docs/gl）"
    fi
else
    warn "未找到 unzip 命令，跳过 zip 结构检查（产物仍已生成）"
fi

log "打包完成: ${OUT_ZIP} (${ZIP_MB} MB)"
if [[ ! -d "$REPO_ROOT/defaults/runtime" ]]; then
    warn "提醒：本次包内不含 defaults/runtime/，安装后需系统具备 aria2c/7zz/node，或先执行 make runtime 再重新打包"
fi
exit 0
