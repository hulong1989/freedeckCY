# freedeckCY 开发/打包快捷入口
#
# 常用：
#   make runtime                 # 下载本机架构运行所需的 aria2/7z/node 到 defaults/runtime
#   make runtime ARCH=all        # 同时下载 x86_64 与 aarch64
#   make package                 # 生成 dist-artifacts/freedeckCY-v<version>.zip
#   make package PACKAGE_ARGS=--build-ui
#   make test                    # 使用 .venv/bin/pytest 运行测试
#   make doctor                  # 环境诊断（只读）
#   make clean                   # 清理 dist-artifacts 与 Python 缓存
#
# 所有目标都从仓库根目录执行。

ROOT := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
SHELL := /bin/bash

# runtime 目标参数：ARCH 为空时由脚本按 uname -m 自动识别。
ARCH ?=
RUNTIME_ARGS ?= $(if $(ARCH),--arch $(ARCH),)
# package 目标参数：例如 PACKAGE_ARGS=--build-ui 或 PACKAGE_ARGS="--out-dir /tmp/out"。
PACKAGE_ARGS ?=

PYTEST := $(ROOT)/.venv/bin/pytest
REQUIREMENTS_DEV := requirements-dev.txt

.DEFAULT_GOAL := help
.PHONY: runtime emulator-runtime catalog-json package package-droiddeck test doctor validate-catalog normalize-catalog clean help

help:
	@echo "freedeckCY 构建入口"
	@echo ""
	@echo "用法: make <target> [变量=值]"
	@echo ""
	@echo "目标:"
	@echo "  runtime    下载 aria2c / 7zz / node 到 defaults/runtime/（幂等，可重复执行）"
	@echo "  emulator-runtime  下载 mGBA AppImage（x86_64/aarch64）到 defaults/runtime/mgba/"
	@echo "  catalog-json  导出 NewFreedeck 兼容目录 JSON 到 catalog-json/（仓库内，可直接读）"
	@echo "  package    组装 Decky 插件 zip 到 dist-artifacts/freedeckCY-v<version>.zip"
	@echo "  package-droiddeck  组装 aarch64 包（DroidDeck/ARM 设备）到 ...-arm64.zip"
	@echo "  test       使用 .venv/bin/pytest 运行测试（未安装则提示安装 dev 依赖）"
	@echo "  doctor     环境诊断：运行时/Steam/state/日志/端口/网络（只读）"
	@echo "  validate-catalog  目录 CSV 体检（重复/非法链接/分类混平台名等）"
	@echo "  normalize-catalog 清洗目录 categories 字段"
	@echo "  clean      删除 dist-artifacts/ 与 __pycache__/*.pyc（默认保留 defaults/runtime）"
	@echo "  help       显示本帮助"
	@echo ""
	@echo "变量:"
	@echo "  ARCH=x86_64|aarch64|all   runtime 目标的目标架构（默认按本机自动识别）"
	@echo "  RUNTIME_ARGS=\"...\"       透传给 scripts/fetch_runtime.sh 的额外参数"
	@echo "  PACKAGE_ARGS=\"...\"       透传给 scripts/package.sh 的额外参数，如 --build-ui"
	@echo "  CLEAN_RUNTIME=1          clean 时一并删除 defaults/runtime/"
	@echo ""
	@echo "示例:"
	@echo "  make runtime"
	@echo "  make runtime ARCH=all"
	@echo "  make package"
	@echo "  make package PACKAGE_ARGS=--build-ui"
	@echo "  make test"
	@echo "  make clean CLEAN_RUNTIME=1"

runtime:
	@cd "$(ROOT)" && bash scripts/fetch_runtime.sh $(RUNTIME_ARGS)

emulator-runtime:
	@cd "$(ROOT)" && bash scripts/fetch_emulator.sh $(RUNTIME_ARGS)

catalog-json:
	@cd "$(ROOT)" && python3 scripts/export_remote_catalog.py

package:
	@cd "$(ROOT)" && bash scripts/package.sh

package-droiddeck:
	@cd "$(ROOT)" && PACKAGE_ARCH=aarch64 bash scripts/package.sh $(PACKAGE_ARGS)

doctor:
	@cd "$(ROOT)" && bash scripts/doctor.sh

validate-catalog:
	@cd "$(ROOT)" && python3 scripts/validate_catalog.py defaults/tianyi_catalog/freedeckcy_catalog.csv --cover-index defaults/tianyi_catalog/cover_index.csv --strict

normalize-catalog:
	@cd "$(ROOT)" && python3 scripts/normalize_catalog_categories.py defaults/tianyi_catalog/freedeckcy_catalog.csv

test:
	@cd "$(ROOT)" || exit 1; \
	if [ -x "$(PYTEST)" ]; then \
		echo ">>> .venv/bin/pytest -q"; \
		"$(PYTEST)" -q; \
	else \
		echo "未找到 $(PYTEST)"; \
		echo "请先安装开发依赖："; \
		echo "  python3 -m venv .venv"; \
		echo "  .venv/bin/python -m pip install -r $(REQUIREMENTS_DEV)"; \
		exit 1; \
	fi

clean:
	@echo ">>> 清理 dist-artifacts/ 与 Python 缓存"
	@rm -rf "$(ROOT)/dist-artifacts"
	@find "$(ROOT)" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
	@find "$(ROOT)" -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>/dev/null || true
	@find "$(ROOT)" -type f -name '*.pyc' -not -path '*/.git/*' -delete 2>/dev/null || true
	@if [ "$(CLEAN_RUNTIME)" = "1" ]; then \
		echo ">>> 删除 defaults/runtime/"; \
		rm -rf "$(ROOT)/defaults/runtime"; \
	else \
		echo ">>> 保留 defaults/runtime/（如需一并清理：make clean CLEAN_RUNTIME=1）"; \
	fi
	@echo ">>> 清理完成"
