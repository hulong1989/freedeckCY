# catalog-json

从 `defaults/tianyi_catalog/freedeckcy_catalog.csv` 导出的 **NewFreedeck 兼容目录 JSON**，已提交入库，clone 后可直接读取，也用于自托管（不依赖作者服务器 `panyiwei.xyz`）。

## 文件

| 文件 | 说明 |
|---|---|
| `all.json` | 全部 7084 条资源（数组） |
| `platform/<platform>.json` | 按平台拆分（pc/gba/fc/nds/psp/3ds/ps2/ps1/ps3/md/switch） |
| `curated/<platform>.json` | 每平台精选（有封面优先、体积降序，默认 60 条） |
| `manifest.json` | 总数、平台分布、每个文件的 sha256 |
| `schema.json` | 单条目录 item 的 JSON Schema |
| `emu.example.json` / `emu.schema.json` | `emu.json` 模板与 schema（**不含真实分享链接**） |

## 重新生成

目录 CSV 更新后执行：

```bash
make catalog-json
# 或
python3 scripts/export_remote_catalog.py \
  --catalog defaults/tianyi_catalog/freedeckcy_catalog.csv \
  --out catalog-json
```

CI 中的 `tests/test_committed_catalog_json.py` 会校验 `manifest.json` 的哈希与条数；改 CSV 后忘记重新生成会红。

## 插件运行时读取

默认插件读 CSV；如需直接读这份 JSON（例如想验证导出一致性），设置环境变量后重启插件：

```bash
# 本地路径
export FREEDECKCY_CATALOG_JSON="$PWD/catalog-json/all.json"

# 或者直接用 GitHub raw URL（会缓存到 ~/.local/share/freedeckCY/catalog-remote-cache.json，6 小时）
export FREEDECKCY_CATALOG_JSON="https://raw.githubusercontent.com/hulong1989/freedeckCY/main/catalog-json/all.json"
```

JSON 加载失败/为空时会自动回退 CSV（`FREEDECKCY_CATALOG_JSON` 指向的文件不存在时也会回退）。

## 自托管

```bash
cd catalog-json
python3 -m http.server 8000
# GET http://127.0.0.1:8000/all.json
# GET http://127.0.0.1:8000/platform/gba.json
# GET http://127.0.0.1:8000/curated/gba.json
```

协议、字段含义、`emu.json` 格式与替代方案见 [../docs/UPSTREAM_SERVER.md](../docs/UPSTREAM_SERVER.md)。

## 注意

- 这些 JSON 里包含天翼云盘分享链接（与仓库里的 CSV 同源），仅用于互操作/自托管，版权与合规风险同主仓库免责声明。
- `emu.example.json` 故意留空：模拟器安装包请使用官方发行版（mGBA/DuckStation/PCSX2 等），不要镜像作者的网盘转存包。
