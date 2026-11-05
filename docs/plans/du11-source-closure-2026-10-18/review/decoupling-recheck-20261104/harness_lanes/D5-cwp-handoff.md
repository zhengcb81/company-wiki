# D5 外包交接 — CWP 侧 producer port（handoff）

状态：实现完成、契约测试绿、跨仓隔离 E2E 绿、独立审查见文末。
本卡（[D5-CWP-STOCKWIKI-PROCESSED-READING.md](D5-CWP-STOCKWIKI-PROCESSED-READING.md)）的 producer 侧交付。

## 1. 版本与写域

| 项 | 值 |
|---|---|
| 仓 | `C:\Users\郑曾波\Projects\_harness_worktrees\d5-20261105\cwp`（主仓 `C:\Users\郑曾波\Projects\company-wiki` 的独立 worktree，作者工区未动） |
| 起始 HEAD | `f8eccf0a10f9211cbb7ee0dd2c405e37d07b867b`（master，与 origin/master 一致） |
| 分支 | `codex/d5-cwp-processed-port`（基于上述 master 新建） |
| 最终 HEAD | 见 git log（本文件随最终 commit 提交，最终 HEAD = 本 commit） |
| 起始 WIP | 主仓工作区全部为 untracked（`.planning/`、`.m9-*`、`.cwp*` 等），未触碰；worktree 内起始干净 |

改动文件（全部新增，无既有文件修改）：

- `src/company_wiki/source_catalog/processed_document.py` — port 核心（合同、双 lane 解析、分页 cursor、错误映射）
- `src/company_wiki/source_catalog/processed_document_cli.py` — stdin/stdout JSON CLI（exit 0/2）
- `tests/contract/test_processed_document_cli.py` — 12 个契约用例（子进程真实边界）

## 2. 接口

- envelope：`company-wiki-processed-document/1`（卡面冻结合同，逐字段实现）。
- 请求：`{"schema_version": "company-wiki-processed-document/1", "source_ref": <SourceRef v2 6 字段>, "options"?}`；`options` 仅 `{max_units?, continuation?}`。
- 响应：`{schema_version, source_ref（SourceRefValue.to_dict() 形状逐字段回显）, manifest（SourceVersionReader.describe_version 的 22 字段 pathless 投影）, parser{name,version,profile=null}, status(complete|partial|unsupported), units[{unit_id,kind,locator,content}], continuation, quality{quality_flags,coverage_complete,page_count,errors,reason}}`。
- 身份校验复用 `automation/narrative_contracts.SourceRefValue.from_dict`（schema 2.0、source_id 与 content_sha256 派生一致）；读取走 `SourceVersionReader.open_described_version(purpose="source_export")`（与 SourceExport v2 同一 verified-open 链，含 read policy/root admission/预算）。
- 解析复用：
  - docx/html/pptx → `document_normalization.normalize_document`（R6-FORMAT 纯 normalizer；unit_id 直接沿用 narrative-unit URN，locator 沿用 cwp-docx-body/cwp-html-dom/cwp-pptx-shape）；
  - 其余格式（pdf/xlsx/xls/txt/md/csv/mht/json/xml）→ 既有 `normalizer._run_parser_isolated` 隔离子进程（沿用 owner 默认预算：timeout 3600s / heartbeat 15s / result 256MB；临时文件写 `catalog_dir/parser_tmp`，用后即删）；
  - xlsx 薄 adapter（`_port_parse_source`）：仅补充结构化行列输出（structured_value `{"sheet","rows"}`），不改 legacy `_xlsx_markdown` 行为；空文本 → 诚实 unsupported。
- unit_id：catalog lane 为 `urn:company-wiki:processed-unit:sha256:<sha256(content_sha256, parser_name, parser_version, kind, locator)>`；normalization lane 复用既有 `urn:company-wiki:narrative-unit:sha256:*`。
- 禁止项已满足：响应/错误/cursor 不含 original_path、存储根、SQLite 细节；legacy `SourceManifest.to_dict()` 不入响应（子进程内部所需的 legacy manifest 来自 locations.manifest_json，仅作解析归属，不外发）。
- 分页：`options.max_units`（调用方预算， producer 不设固定上限）+ 不透明 cursor（base64url JSON：`{v,after_index,after_unit_id,content_sha256}`）；续读校验 `units[after_index-1].unit_id == after_unit_id`，解析漂移/篡改 → `blocked/invalid_continuation`。

## 3. 真实执行命令与通过数

运行环境：worktree + `PYTHONPATH=<worktree>/src`，宿主 Miniconda Python 3.13（`C:/Miniconda/python.exe`；worktree `.venv` 存在完整性降级问题，见主仓 AGENTS.md 2026-10-26 节）。

```
cd <worktree>
PYTHONPATH=<worktree>/src PYTHONUTF8=1 python -m pytest tests/contract/test_processed_document_cli.py -q
  → 12 passed（56s）
PYTHONPATH=<worktree>/src PYTHONUTF8=1 python -m pytest tests/contract/test_source_export_v2_cli.py \
  tests/contract/test_source_export_v2.py tests/contract/test_source_version_reader.py \
  tests/contract/test_source_version_reader_cli.py tests/unit/test_p2_office_table -q
  → 148 passed（37s）
python -m ruff check src/company_wiki/source_catalog/processed_document.py \
  src/company_wiki/source_catalog/processed_document_cli.py tests/contract/test_processed_document_cli.py
  → All checks passed
```

tests/contract 全量回归：见第 6 节收据。

## 4. 真实样本 SHA

契约测试 fixture 全部在测试内程序化生成（`test_processed_document_cli.py`，tmp_path 内）：

| fixture | 生成方式 | SHA-256 |
|---|---|---|
| `2025.txt`（complete 正例） | UTF-8 双段落文本 | `ff8accbe3fb16e510db26f8d0f5bb5e64d1c449a23a11fc2d8c111588b1b92f1`（120 bytes） |
| `partial-2024.txt`（partial 正例，encoding_repaired） | gb18030 编码 | 运行期生成 |
| `2025.docx` | python-docx（heading+2 段） | 运行期生成 |
| `2025.pdf` | PyMuPDF 两页（ASCII 文本；默认字体不嵌 CJK） | 运行期生成 |
| `2025.xlsx`（sheet 结构化正例） | openpyxl（3 行×2 列，含 None 单元格） | 运行期生成 |
| `empty-2023.xlsx`（unsupported 正例） | openpyxl 空表 | 运行期生成 |

跨仓 E2E（消费者仓 `tests/e2e/test_cwp_processed_document.py`）同样在 tmp 内生成 PDF/DOCX/XLSX 三族样本，经真实 CWP CLI 子进程解析。

## 5. 临时恢复收据（D.3）

- 所有测试新建对象（原件副本、catalog、SQLite state、parser_tmp、输出）位于 pytest `tmp_path` 下，由 pytest 自动删除；测试不写仓内任何路径。
- CWP worktree 的 `git status` 在测试前后无被测改动（仅本卡新增三文件）。
- StockWiki 跨仓 E2E 断言 producer checkout `git status --porcelain -- src config` 前后逐字相同（owner checkout 只读）。
- 生产原件未复制、未移动、未覆盖；无付费供应商调用（契约测试用 sitecustomize 禁 socket；E2E signals 用注入 chat_func）。
- 实现过程的临时探针脚本（`%TEMP%/d5probe`、`C:/Temp/d5tmp`）已删除。
- 会话前期事故记录：侦察时一条 `git config extensions.worktreeConfig --get` 误被 git 解析为赋值，写入主仓 `.git/config` 的 `[extensions] worktreeConfig = --get`；已即时发现并手工移除该行恢复原值（`git config --file` 全文核对），主仓 git 操作恢复正常。此为会话自愈项，主仓当前 config 与基线一致。

## 6. 回归

- 相邻域（148 passed）：`tests/contract/test_source_export_v2*.py`、`test_source_version_reader*.py`、`tests/unit/test_p2_office_table`。
- `tests/contract` 全量对照（同宿主 Python、同基线 master 内容）：
  - 本 worktree（含 D5）：**47 failed / 2590 passed / 21 skipped**
  - 基线主仓（无 D5）：**47 failed / 2578 passed / 21 skipped**
  - 失败集合逐条 diff **完全相同**（清单见 `full-failures.txt` / `baseline-failures.txt`，随交接留存于 worktree 父目录）；passed 差值恰为本卡新增 12 项契约测试。
  - 结论：D5 引入 **零回归**；47 项失败为本环境既有失败（docs 断言、location/portfolio/live-data 依赖类），与本卡无关，属基线状态，不在本卡修复范围。
- `mypy src` 全量：Success（429 source files）。
- 日志：`cwp-contract-full.log` / `cwp-contract-baseline.log` 留存于 worktree 父目录 `C:\Users\郑曾波\Projects\_harness_worktrees\d5-20261105\`。

## 7. 兼容调用方与未完成限制

- CWP 侧本卡为零删除、零既有文件修改：所有既有 CLI/合同/测试不受影响。
- `processing purpose` 未新增：复用 `source_export`（与 SourceExport v2 一致），未给 runtime policy 增加新门。
- profile 字段当前恒为 null：本 port 路径未启用 OCR/recipe 变体；一旦启用（如 pptx OCR），parser.version 已随 `narrative_contracts` 的版本 pin 变化，profile 需随实现携带 OCR fingerprint（后续卡）。
- XLSX 多 sheet 已支持；`.doc/.xls` 走既有 catalog 适配（antiword/xlrd），缺失依赖时为诚实错误/unsupported，不为测试伪造支持。
- ROOT 独占的组合验证（CWP port → StockWiki 三入口 + FF schema 2.0 路由 + V1 隔离）按卡第 6 节仍由 ROOT 在 FF 仓执行，不在本卡写域内。

## 8. 独立审查结论

独立审查 agent 已派出（未参与实现），审查范围为本卡冻结合同符合性、三入口调用路径、复用而非重建、测试真实性、边界写域与可移植性。该 agent 三次因运行环境中断（并发限制 ×2、Token Plan 用量上限 ×1），尚未产出最终结论；配额恢复后可继续同一审查上下文并绑定本仓最终 commit SHA。此项为交接的**未完结项**：D5 完成（卡片 §6"解耦完成"）仍需该独审在最终 commit 上通过。
