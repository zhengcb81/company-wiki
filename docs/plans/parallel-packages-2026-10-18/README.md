# 并行施工包 2026-10-18（P1–P4）

状态：**P1/P4 RECEIVED；P2/P3 IMPLEMENTED_PENDING_ROOT_RECEPTION**（2026-10-18 更新；起草时为 READY_TO_DISPATCH）。本目录只放施工卡与交接约定，不含实现。四张卡已在本地分支 `codex/p1-ocr-text-20261018`、`codex/p2-office-table-20261018`、`codex/p3-identity-audit-20261018`、`codex/p4-consumer-contract-20261018` 实现完毕，写集互斥已核实（见下方写集表），均**未推送**。

**ROOT 接收（2026-10-18）**：P1 与 P4 已合入本地 `master`（合并提交 `09a8dded`、`626eb32f`）。
- P1：`tests/unit/test_p1_ocr_text` **40 passed**；`ruff`/`mypy` 干净；独立复审 round 2 PASS。已知限制：未接生产、未跑真实扫描件。**接收时偏差**：助手模块 `synth.py` 与 `tests/fixtures/document_normalization_layout_snapshots/synth.py` 在全量单测收集时重名，已重命名为 `p1_synth.py`（否则全量套件报 `AttributeError: module 'synth' has no attribute 'load_fixture'`）。
- P4：`tests/integration/test_p4_contract` 在 `CWP_P4_CATALOG_CONFIG=<本卡 fixtures>/catalog/catalog.yaml` 下 **34 passed**；无 env 时 34 skipped（按卡设计，非静默通过）；独立复审 PASS。P4 为 opt-in，不进 pre-push。
- P2/P3 仍为 IMPLEMENTED_PENDING_ROOT_RECEPTION。
起草人：外部 agent；接收与验收：ROOT。主线 PWF 为 `docs/plans/document-understanding-2026-10-13`（母）与 `docs/plans/du11-source-closure-2026-10-18`（当前 B2 来源闭合），本目录的四张卡**不是**主线的一部分，也不改变主线状态。

## 1. 四张卡一览

| 卡 | 一句话范围 | 产出物 | 生产线依赖 |
|---|---|---|---|
| P1-OCR-TEXT | 扫描件/图片页的 OCR 行 → 有界、可定位正文，低置信与顺序歧义显式 defer | `cwp-ocr-page-text/1` 结果 + 纯 PDF 页适配器 | 仅标准库 + 现有 `ImageOCRResult` |
| P2-OFFICE-TABLE | DOCX/PPTX 表格结构（合并单元格/续表/表头/脚注）与结构回放 | `cwp-office-table/1` 结构 + replay 函数 | 标准库 + lxml/python-pptx（现有可选依赖） |
| P3-IDENTITY-AUDIT | 只读 CLI，核对导出与读取两侧的 identity/period/unit/SHA | `identity-audit-receipt/1` JSON | 已发布 CWP 读/导出接口 |
| P4-CONSUMER-CONTRACT | FF/RF 只读契约验证，核对 SourceRef/期间/单位/未知可用性 | `p4-contract-receipt/1` 收据 + 集成测试 | 已发布 CWP CLI + 冻结消费端观测 |

四张卡都**不接线生产**、不启用默认、不发布，也不要求 ROOT 立即合并。ROOT 按各卡交接独立决定接线顺序。

## 2. 为什么互不冲突

### 2.1 文件级写集（精确）

| 路径 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| `src/company_wiki/document_normalization/ocr_page_text.py`（新） | 写 | — | — | — |
| `src/company_wiki/document_normalization/ocr_composition.py`（仅可选、窄改） | 写 | — | — | — |
| `src/company_wiki/parser_adapters/pdf_ocr_page_adapter.py`（新） | 写 | — | — | — |
| `src/company_wiki/document_normalization/office_table_structure.py`（新） | — | 写 | — | — |
| `src/company_wiki/document_normalization/docx_parser.py` | — | 不写 | — | — |
| `src/company_wiki/document_normalization/pptx_parser.py` | — | 不写 | — | — |
| `src/company_wiki/automation/narrative_formats.py`（可选、窄改） | — | 写 | — | — |
| `tools/identity_audit/**`（新） | — | — | 写 | — |
| `tests/unit/test_p1_ocr_text/**`（新） | 写 | — | — | — |
| `tests/unit/test_p2_office_table/**`（新） | — | 写 | — | — |
| `tests/unit/test_identity_audit/**`（新） | — | — | 写 | — |
| `tests/integration/test_p4_contract/**`（新） | — | — | — | 写 |
| `docs/plans/parallel-packages-2026-10-18/P1-OCR-TEXT/**` | 写 | — | — | — |
| `docs/plans/parallel-packages-2026-10-18/P2-OFFICE-TABLE/**` | — | 写 | — | — |
| `docs/plans/parallel-packages-2026-10-18/P3-IDENTITY-AUDIT/**` | — | — | 写 | — |
| `docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/**` | — | — | — | 写 |
| `docs/plans/parallel-packages-2026-10-18/README.md`、`INTERFACES.md` | 只读 | 只读 | 只读 | 只读 |

四行四列中没有一格被两卡同时勾选；唯一的相邻点是 P1 与 P2 同在 `document_normalization/` 目录下，但落在不同文件，且两卡都不许改 `__init__.py`、`units.py`、`errors.py`、`limits.py`、`document.py`、`replay.py`。

### 2.2 运行环境隔离

- P1/P2 是纯单元层：不读真实原件、不建 catalog、不联网、不调模型。
- P3 只读打开既有 catalog（`mode=ro`），唯一写操作是 `--out` 指定的一个 JSON 文件。
- P4 是集成层，默认 `skip`，只有显式设置 env 才运行；不写 catalog、不下载、不调模型。

### 2.3 依赖方向

- P1、P2 互不依赖，也不依赖 P3/P4。
- P3 只依赖已发布的 CWP 读/导出接口与 `SourceRef`/`EvidenceSpan` 契约，不依赖 P1/P2 的新结构。
- P4 只依赖已发布 CLI 与冻结的消费端观测文件，不依赖 P1/P2/P3 的产物。

因此四卡可同时开工；即使其中一张失败或延期，另外三张的验收不受影响。

## 3. 共同边界（四卡都适用）

1. **原件只读**：不修改、不移动、不重命名任何已下载原件、原文 TXT、gold；不新建原件副本。只读回放时必须前后核对 SHA。
2. **不读密钥**：不读取 `.env`、`config` 中的 API key，不打印、不写入收据；不在进程环境里探测供应商凭据。
3. **不新增人工许可**：不创建审批 JSON、签收文件、canary 放行链或逐材料许可。仓库已有授权按 AGENTS.md 执行。
4. **不写生产 config/DB**：`config/source_catalog.yaml`、生产 `catalog.sqlite3`、`automation` 库、gold、`output/` 一律不写。测试用 tmp 夹具，结束后恢复。
5. **不联网、不调模型、不产生费用**：0 下载、0 LLM 请求、0 供应商调用；断言方式见各卡。
6. **不改 CI/hooks**：不修改 `.githooks/`、`.github/`、`.pre-commit-config.yaml`、`tools/pre_push_gate.py`。
7. **不删测试、不放宽断言、不跳 hook、不提高限额**；失败收据必须保留。
8. **不碰 ROOT 独占文件**（见第 4 节）。
9. **不改主线计划**：`docs/plans/du11-*/**` 与 `docs/plans/document-understanding-2026-10-13/**` 只读。
10. **一处只碰一次**：每张卡只在自己的 PWF 写 `task_plan.md`/`progress.md`/`findings.md`/`handoff.md`/`handoff.json`，不建第二个计划目录。

## 4. ROOT 独占（四卡一律禁写）

- `src/company_wiki/source_catalog/narrative_reading.py`
- `src/company_wiki/source_catalog/narrative_operating_relations.py`
- `src/company_wiki/source_catalog/narrative_antecedent.py`
- `src/company_wiki/document_understanding/operating_states/relations.py`
- `src/company_wiki/document_understanding/operating_states/product_reference.py`
- `tests/unit/du11_source_closure/**`（整目录）
- `docs/plans/du11-*/**`、`docs/plans/document-understanding-2026-10-13/**`

任何卡若因实现需要触碰上述路径或第 3 节第 6–8 条：**停止该处实现**，在 `handoff.md` 写 `BLOCKED_BY_SCOPE` 与所需最小改动，交 ROOT 决定；不得先改后报。

## 5. 派发建议

- 工作目录：每卡一个独立 worktree（沿用仓库既有习惯），不要四卡共用一棵树：
  `C:/Users/郑曾波/Projects/company-wiki-p1-ocr-text`、`-p2-office-table`、`-p3-identity-audit`、`-p4-consumer-contract`。
- 分支：`codex/p1-ocr-text-20261018`、`codex/p2-office-table-20261018`、`codex/p3-identity-audit-20261018`、`codex/p4-consumer-contract-20261018`。
- 基线：以派发当日远端 `master` 为准，由 ROOT 在派发时写入各卡 `baseline.json`；作者不得自行改基线。
- 并行度：四卡可全并行。若只能开两张，先 P1、P2（纯单元、反馈快），P3 次之，P4 最后（依赖冻结观测）。
- 每卡只与 ROOT 通信一次交付（`handoff.md`/`handoff.json`），中间不设人工签收。

## 6. ROOT 接收检查清单

对每张卡逐项核对，任一项不满足即 `REJECTED`：

1. `git diff --stat` 的路径集合 ⊆ 该卡写集，且不包含第 4 节任何路径。
2. 新建文件与`handoff.json` 中 `file_bindings` 的 SHA-256 逐一相等（重新计算，不信自报）。
3. `red_receipt` 指向真实失败日志，且失败发生在实现之前；日志里能看到断言消息而不是仅有 ImportError。
4. 测试数量、跳过数与交接一致；无 `-k` 缩范围、无删除用例、无 `pytest.mark.skip` 新增。
5. 验收命令在干净树可复现（ROOT 亲自跑一次，含 ruff/mypy）。
6. 未写 `config/source_catalog.yaml`、生产 DB、`output/`、原件；未读密钥。
7. 独立审查者 ≠ 作者，审查报告绑定最终文件 SHA，且发现项已修完并复跑。
8. `not_run`/`known_limits` 诚实列出，未把未做当通过（尤其 P1 真实扫描件、P2 真实 DOCX 续表、P3 真实生产 catalog、P4 真实消费端）。
9. 关掉本卡后主线仍绿：ROOT 合并前跑一次受影响单测 + 合同冒烟。

## 7. 文件

- [INTERFACES.md](INTERFACES.md)：跨卡共用约定（状态词表、错误码、JSON 收据、版本号、偏移语义）。
- [P1-OCR-TEXT/card.md](P1-OCR-TEXT/card.md)
- [P2-OFFICE-TABLE/card.md](P2-OFFICE-TABLE/card.md)
- [P3-IDENTITY-AUDIT/card.md](P3-IDENTITY-AUDIT/card.md)
- [P4-CONSUMER-CONTRACT/card.md](P4-CONSUMER-CONTRACT/card.md)
