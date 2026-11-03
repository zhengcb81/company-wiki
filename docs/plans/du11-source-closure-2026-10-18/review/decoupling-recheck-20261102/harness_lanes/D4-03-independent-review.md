# D4-03 独立审查记录

审查者：未参与实现的独立 agent（`agent-e6c6dcbd-6a67-4920-b1fe-c81fe888f613`），只读审查，2026-11-02。
审查对象：D4-03 的解析层解耦改动（审查时点在主工作树，内容与分支 `codex/d4-03-document-model` 的交付一致）。
结论：**通过**，提出 3 项次要问题，均已修复（见文末）。

## 审查方法

- 独立新进程探针（`-I -B`，`sys.path` 绑定本仓 `src`，`sys.meta_path` 拒绝 `company_wiki.source_catalog*`/`automation*`/`ingest*`/`canonical_ingest`/`run_store`/`scheduler`/`wiki_repository`/`source_registry`/`sqlite3`）：实际跑 HTML、合成 DOCX、合成 PPTX 的 `normalize_document` + `replay_unit`，再跑 `understand_units`，并核对 `sys.modules`。
- 身份探针：13 个符号 `is` 比较、`__module__`、双向 `isinstance`、frozen、`metadata` 只读、`to_evidence_span` 的 span id、`summary_input` 等价、turn_id 公式。
- AST 对比：剥离 docstring 与 import 节点后，`HEAD:source_catalog/narrative_document.py` 与 `document_model/narrative.py`、`HEAD:source_catalog/transcript_layout.py` 与 `document_model/turns.py` 逐节点比较。
- 动态 import：字符串 `import_module`、star-import、`dataclasses.fields`、pickle、`__all__` 语义。
- 写域：`git status --short`、`git diff --stat/--raw`、mtime 与 `git log` 交叉核对既有脏状态。
- 变异验证：把 `document.py`/`units.py` 与旧路径本地定义两处改回原状，确认隔离/身份测试必红。
- 只跑相关测试（新测试、`tests/document_normalization/`、电话会契约、DU root），未跑 CWP 全仓。

## 结果

| 检查 | 结果 |
|---|---|
| 隔离进程真实 normalize/replay/understand | 通过（HTML 5 units / DOCX 5 units / PPTX 2 units，replay 逐字相等，`du-pipeline/1`，违规模块 0） |
| 类 identity | 通过（13 符号 `is` 全 True，`__module__` 指向 `company_wiki.document_model.*`，无第二份定义） |
| AST 等价 | 通过（两份迁移文件 AST 完全一致） |
| schema/字段顺序 | 通过（`cwp-document-normalization/1`、parser 版本、`du-pipeline/1`、`narrative-summary-input/0.2.0`、`DocumentStructure` 15 字段顺序不变） |
| 动态 import / star-import / pickle | 通过（仓内无 star-import；旧路径实体文件仍在，字符串 import 可用；pickle 在 HEAD 同样不可用，非回归） |
| 写域合规 | 通过（仅 8 个跟踪文件，其中 `.githooks/pre-push` 为既有模式位差异） |
| 测试有效性 | 通过（变异必红） |
| 测试实跑 | 21 passed（新测试）；105 passed（normalization，排除 3 个 OCR 文件）；533 passed/11 skipped（电话会契约 + DU root）；ruff 全绿 |

## 审查发现与处理

1. **PPTX 未纳入隔离探针**（`pptx_parser.py` 的结构 import 在函数内，模块级扫描看不到）→ 已在 `tests/unit/test_document_layer_isolation.py` 中加入确定性合成 PPTX（固定 core properties + 固定 ZIP 时间戳）与 units/replay 断言，并做变异验证（改回 catalog 路径时探针必红）。
2. **`.githooks/pre-push` 模式位悬空**（`100755→100644`，本轮之前既有）→ 未触碰；提交时按路径 add，禁止 `git add -A`。
3. **兼容层收窄旧模块附带可导入名** → 两个 shim docstring 已注明「只再导出文档化名称，`EvidenceSpan` 等请从 `source_contract` 导入」；仓内零 star-import 消费者。

## 未覆盖

- 未跑 CWP 全仓与跨仓（StockWiki/RF/FF/ET）消费者。
- 未构建 sdist/wheel 实物验证打包（`pyproject.toml:79-81` 的 `packages.find include=["company_wiki*"]` 会自动包含新包）。
- 未跑真实原件/生产库/生产配置。
