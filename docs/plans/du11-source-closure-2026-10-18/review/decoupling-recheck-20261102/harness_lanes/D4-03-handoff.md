# D4-03 交付 — CWP 文档解析层与存储层解耦

状态：**已实现、测试通过、独立审查通过、独立审计补齐后交付。**
基线 HEAD `503f6510c6aa8c18bbbc6ad53b44f14fce6882ce`。
施工位置：独立 worktree `C:/Users/郑曾波/Projects/_harness_worktrees/d4-03-20261102/cwp`，分支 `codex/d4-03-document-model`（基于上述 HEAD）。主工作树中不再保留本卡改动。
交付 commit：实现 `113490729`（`refactor: own the document model outside the source catalog`，pre-commit 的 ruff/mypy 均 Passed）；本说明与 `D4-03-independent-review.md` 在同一分支的后续文档提交（`git log --oneline -2 codex/d4-03-document-model` 可查）。未推送、未部署。

## 1. 新模型 owner 与旧别名映射

新增中性包 `src/company_wiki/document_model/`（纯 DTO + 通用 turn 语法，不加载任何 catalog/store/acquisition/automation 运行时）：

| 新 owner | 内容 |
|---|---|
| `company_wiki.document_model.narrative` | `NarrativeUnit`、`DocumentStructure`、`NarrativeParseResult`、`NarrativeEvidencePackage`、`selected_summary_input`（含 `_group_spans/_span_order/_summary_group` 等私有 helper，逐字迁移） |
| `company_wiki.document_model.turns` | `NATURAL_START`/`QA_HEADING`/`END` 正则、`AnonymousTurnObserver`、`legacy_speaker_fields`、`valid_speaker`、`speaker_fields`、`body_start` |
| `company_wiki.document_model`（`__init__`） | 上述公开名的聚合导出 |

旧路径保留为**同一对象**的兼容再导出，不是第二份定义：

| 旧路径 | 新 owner | 语义 |
|---|---|---|
| `source_catalog.narrative_document.{NarrativeUnit, DocumentStructure, NarrativeParseResult, NarrativeEvidencePackage, selected_summary_input}` | `document_model.narrative.*` | `is` 同一对象；`__module__ == "company_wiki.document_model.narrative"` |
| `source_catalog.transcript_layout.{END, NATURAL_START, QA_HEADING, AnonymousTurnObserver, body_start, legacy_speaker_fields, speaker_fields, valid_speaker}` | `document_model.turns.*` | `is` 同一对象。函数/类（含 `AnonymousTurnObserver`）的 `__module__ == "company_wiki.document_model.turns"`；`END`/`NATURAL_START`/`QA_HEADING` 是同一 `re.Pattern` 对象，其 `__module__` 为 `re` |

`source_catalog/__init__.py` **未改**：该门面此前从未导出这些 DTO，不存在需要保持的兼容导出；本轮不新增门面导出，也不用 lazy import 掩盖归属。

## 2. 修改路径（写域内，逐项）

新增：

- `src/company_wiki/document_model/__init__.py`
- `src/company_wiki/document_model/narrative.py`
- `src/company_wiki/document_model/turns.py`
- `tests/unit/test_document_layer_isolation.py`
- `tests/unit/test_document_model_identity.py`

修改（仅 import 目标 / 兼容导出，共 +52/−477 行）：

- `src/company_wiki/source_catalog/narrative_document.py` → 兼容再导出 shim
- `src/company_wiki/source_catalog/transcript_layout.py` → 兼容再导出 shim（新增 `__all__`）
- `src/company_wiki/document_normalization/document.py`（模块级 import）
- `src/company_wiki/document_normalization/units.py`（模块级 import）
- `src/company_wiki/document_normalization/docx_parser.py`（`DocumentStructure` + `AnonymousTurnObserver`）
- `src/company_wiki/document_normalization/html_parser.py`（函数内 import，仅换目标）
- `src/company_wiki/document_normalization/pptx_parser.py`（函数内 import，仅换目标）

未改：`document_understanding/`（隔离后已无需改动）、`integration/`、ROOT runner、SourceCatalog 业务/schema、StockWiki/RF/FF/ET、生产配置与原件。`document_normalization` 中已无任何 `source_catalog` 文本引用。

## 3. 行为测试与导入探针（先 RED 后 GREEN）

**RED 证据**：改动前用同一探针（新进程 + `sys.meta_path` 拒绝 catalog 前缀）实际导入 `company_wiki.document_normalization` 即失败：

```
AssertionError: document layer imported runtime owner: company_wiki.source_catalog
```

**新增 `tests/unit/test_document_layer_isolation.py`**（3 例，全部为真实行为，不是 import 文本扫描）：

1. 独立新进程（`-I -B`，`sys.path` 绑定本仓 `src`）安装 finder 拒绝 `company_wiki.source_catalog*`、`company_wiki.automation*`、`company_wiki.ingest*`、`company_wiki.canonical_ingest`、`company_wiki.run_store`、`company_wiki.scheduler`、`company_wiki.wiki_repository`、`company_wiki.source_registry`、`sqlite3`，然后实际执行：
   - 小 HTML：`normalize_document` + 逐 unit `replay_unit`（回放文本 == 原文 unit 文本）；
   - 合成小 DOCX（含 `Speaker 1 00:00:05` / `Speaker 2 00:03:11`）：normalize + replay，并断言 `native_speaker_turn` 的 speaker/timestamp/turn_id 与 `source_role == "unknown"`（覆盖 `AnonymousTurnObserver` 的原 DOCX 行为）；
   - 合成单页 PPTX：normalize + replay（`pptx_parser.py` 的结构 import 在函数内，模块级扫描看不到，必须真解析）；
   - `understand_units(html_doc.units, ...)` 产出 `du-pipeline/1`、route profile、section/package 计数；
   - 断言 `sys.modules` 中上述运行时模块为 0。
2. 同一探针在不屏蔽模式下再跑一次：`observation` 必须与隔离运行**完全相等**（同字节 → 同 unit/locator/回放/理解摘要），且不屏蔽时 `leaked == []`（证明文档层不会顺手拉起 catalog）。
3. 自检：屏蔽 finder 确实能让 `import company_wiki.source_catalog` 失败（防止探针假绿）。

**新增 `tests/unit/test_document_model_identity.py`**（18 例）：13 个符号 `is` 同一对象；`__module__` 指向新 owner；双向 `isinstance`；构造相等；frozen（`FrozenInstanceError`）与 `metadata` 只读；`to_evidence_span` 的 `span_id`/structured 字段两路径一致；`NarrativeEvidencePackage.summary_input()` 与 `selected_summary_input()` 一致；`AnonymousTurnObserver` 的 TXT/native turn 语义（turn_id = `native-speaker:` + sha256(`source_id\0locator\0speaker\0timestamp`)）、label 边界、END 关闭语义；旧 label 语法（`Name: body`、`Name -- Title`、`Q&A Session`、`End of transcript`）。

**变异验证（护栏有效，已恢复）**：把 `pptx_parser.py` 的函数内 import 改回 catalog 路径 → 隔离测试立即失败；恢复后通过。独立审查者对 `document.py`/`units.py` 与旧路径本地定义两处变异亦确认必红。

## 3.1 逐项 D4 闭合点

| 卡上要求 | 实现/证据 | 状态 |
|---|---|---|
| D1 独立新进程屏蔽 catalog service/数据库模块；实际 HTML 与小 DOCX normalize、locator replay；实际 `understand_units` 产出**版本化结构** | `tests/unit/test_document_layer_isolation.py::test_document_layer_normalizes_and_understands_without_catalog_runtime`：`-I -B` + `meta_path` 拒绝 8 个前缀与 `sqlite3`，HTML/DOCX/PPTX 各跑 `normalize_document` + 逐 unit `replay_unit`，`understand_units` 断言 `du-pipeline/1`、route profile、section/package 计数 | 满足 |
| D2 `sys.modules` 无 SourceCatalog/store/acquisition/automation；正常 runtime 复测同一输入结果一致 | 同一文件：隔离运行 `leaked == []`；`test_isolated_observation_matches_unblocked_runtime` 要求不屏蔽运行 `leaked == []` 且 `observation` 逐字段相等（unit 文本/kind/role/locator/unit_id/replay/native_turns/理解 sha256） | 满足 |
| D3 旧 `source_catalog.narrative_document` 路径 import 的是新中性类本身；isinstance/构造/immutability/to-dict/序列化不分裂 | `tests/unit/test_document_model_identity.py`：13 符号 `is`、`__module__`、双向 `isinstance`、frozen、`metadata` 只读、`to_evidence_span` span id、`summary_input()` 等价、`DocumentStructure` 别名关系 | 满足 |
| D4 完整跑现有 DOCX transcript/HTML/PPTX normalization 与 D3 document-understanding 受影响小组；特别覆盖 `AnonymousTurnObserver` 原 TXT/DOCX 行为；写域只纳入测试证明确有调用的文件并在此列明 | 回归见 §4；TXT 原行为由 `tests/contract/test_official_transcript_layouts.py`（`parse_transcript_text`）覆盖，DOCX native turn 由 `tests/document_normalization/test_docx.py` + 隔离探针 `native_turns` 断言覆盖；写域 5 个 normalization 文件的真实调用见 §2 说明 | 满足 |

写域内每个 `document_normalization` 文件的真实调用：`document.py`（`NormalizedDocument.structure`/`units` 类型）、`units.py`（`build_unit` 构造 `NarrativeUnit`）、`docx_parser.py`（构造 `DocumentStructure` + `AnonymousTurnObserver`）、`html_parser.py`/`pptx_parser.py`（`_result()` 构造 `DocumentStructure`，函数内 import，需真解析才可见）。

## 4. 测试结果（确切命令）

| 命令 | 结果 |
|---|---|
| `python -m pytest tests/unit/test_document_layer_isolation.py tests/unit/test_document_model_identity.py -q --basetemp=.tmp403/bt-new` | **21 passed**（交付 worktree 内复跑同为 21 passed） |
| `python -m pytest tests/document_normalization -q --ignore=test_isolated_ocr.py --ignore=test_local_ocr_adapter.py --ignore=test_local_pptx_ocr.py` | **138 passed** |
| `python -m pytest tests/document_normalization/test_isolated_ocr.py tests/document_normalization/test_local_ocr_adapter.py -q` | **34 passed** |
| `python -m pytest tests/unit/test_document_layer_isolation.py tests/unit/test_document_model_identity.py tests/contract/test_official_transcript_layouts.py tests/unit/document_understanding_root -q --basetemp=.tmp403/bt-final2` | **554 passed, 11 skipped** |
| `python -m pytest tests/contract/test_official_transcript_layouts.py tests/unit/test_narrative_selection_architecture.py -q` | **57 passed** |
| `python -m pytest tests/unit/document_understanding_{root,profiles,structure,layout_hints,decision_dependencies,note_scope,selection} -q` | **3311 passed, 17 skipped, 18 failed（全部为 HEAD 既有失败，见下）** |
| `ruff check <改动文件>` | All checks passed |

上表在内容与交付 commit 一致的主工作树测得（交付前已逐文件 `cmp` 确认与分支内容相同）。交付 worktree 内复跑新测试 21 passed；同批 3 个 DU root 用例在 worktree 内因本机 sandbox safe-delete 钩子报 `SAFE_DELETE_BULK_GUARD_ERROR`（`SystemExit: 1`，setup 阶段），属环境噪声，同一内容在主工作树为 passed。

**既有失败证明**：`document_understanding_selection` 的 18 个失败（`source_grammar_unavailable` 等）在 HEAD 基线 worktree（`git worktree` @ `503f6510`，`PYTHONPATH` 指向基线 src）中逐条重现，失败 node id 集合与本轮工作树**完全相同**（15 例逐条 diff 一致 + 另 3 例 `test_reading_named_segment_scope.py` 基线同样失败）。不是本次回归。

**环境说明**：本机沙箱的 safe-delete 钩子会在 pytest 会话收尾/部分 OCR 夹具 rmtree 时抛 `SAFE_DELETE_BULK_GUARD_ERROR`；用默认 basetemp 或把 basetemp 放在仓内即可正常收尾，与本次改动无关。

## 5. 公开合同与兼容性

- 类 identity：旧路径与新 owner 是同一 class 对象；`isinstance`、构造、frozen、`to_evidence_span`、`summary_input` 不分裂。
- schema/版本未变：`cwp-document-normalization/1`、`PARSER 1.0.0`、`DOCX 1.2.0`（legacy 1.0.0）、`PPTX 1.1.0`（OCR 2.0.0）、`narrative-summary-input/0.2.0`、`du-pipeline/1`；`DocumentStructure` 字段集合与顺序未变。
- 重放/序列化：HTML/DOCX/PPTX 的 unit 文本、locator、`unit_id`、`source_sha256`、`to_evidence_span` structured 字段与改动前逐字一致（隔离/不隔离两种运行 observation 完全相等；理解链摘要 sha256 与改动前相同 `c72aaeb8…`）。
- 真实消费者：`automation/*` 5 处模块级 import、`source_catalog/narrative_evidence.py` 4 处函数内 `from .transcript_layout import …`、`narrative_evidence` 再导出的 `NarrativeParseResult` 均照常工作。
- 兼容层收窄：`transcript_layout` 原先无 `__all__`，star-import 会附带 `re/sha256/dataclass`；现按 `__all__` 收窄为 8 个语法名。仓内无 star-import 消费者；已在 shim docstring 注明不再转发附带名。

## 6. 独立审查

审查者：未参与实现的独立 agent（`agent-e6c6dcbd-6a67-4920-b1fe-c81fe888f613`），只读审查，结论 **通过**。核查覆盖：隔离进程真实 normalize/replay/understand、13 符号 identity、AST 逐字等价（剥离 docstring/import 后两份迁移文件 AST 完全一致）、schema/字段顺序、动态 import/star-import/`dataclasses.fields`/pickle、写域合规、残余入口、测试有效性（变异必红）。

审查提出 3 项次要问题及处理：

1. **PPTX 未纳入隔离探针**（函数内 import 无护栏）→ 已在探针中加入确定性合成的单页 PPTX（固定 core properties + 固定 ZIP 时间戳），并做变异验证；已修。
2. **`.githooks/pre-push` 模式位悬空**（`100755→100644`，本轮之前既有，mtime 22:39 早于首个源码改动 22:55）→ 非本轮改动，未触碰；提醒：若日后 `git add -A` 提交会连带丢可执行位，应显式按路径 add 或先 `git checkout -- .githooks/pre-push`。
3. **shim 收窄旧模块附带可导入名** → 已在两个 shim docstring 明确「只再导出文档化名称，`EvidenceSpan` 等请从 `source_contract` 导入」；仓内零消费者，未额外转发无关名。

## 7. 残余 storage-boundary 入口（如实列出）

- `document_understanding/decision_inventory.py:1-13`：仍是 catalog 组合 owner（`source_catalog.narrative_decision_inventory`）的历史兼容适配器，真实调用需要 catalog。它**不在** `understand_units` 调用链上（隔离探针已证明），docstring 已明示 "Historical import compatibility"，本轮未改、也未把它算作已解耦。
- `source_catalog/narrative_evidence.py` 等 catalog 业务模块继续从 `.narrative_document` / `.transcript_layout` 旧路径导入：它们本身就是 catalog 消费者，属预期。
- `document_understanding/__init__` → `observation_adapter` → `document_normalization` 的包 `__init__` 会加载 `local_ocr`（PIL/numpy 等解析期依赖）。这是解析层自身的依赖，不含存储/采集运行时。

## 8. 未完成/外限

- 未提交、未推送、未部署（按本卡与既有 lane 约定）。
- 未跑 CWP 全仓；未跑跨仓（StockWiki/RF/FF/ET）消费；未构建 sdist/wheel 实物验证打包（`pyproject.toml:79-81` 的 `packages.find include=["company_wiki*"]` 会自动包含新包）。
- 未跑真实原件/生产库/生产配置；所有样例均为内存合成字节。
- 临时资料：主工作树 `.tmp403/`（探针、失败清单、basetemp 残留）、基线 worktree `%TEMP%/cw-baseline-wt`、审查者 `.tmp403/reviewer/`、审计者 `.audit403/` 均已清理；本 worktree 内 `.tmp403/`（basetemp）在提交前清理。仓库只保留 §2 与两份说明文档。

## 9. 独立完成度审计（2026-11-02）

由第三个独立 agent（`agent-b2b6f059-8440-4f98-9763-0d5f6c590152`，未参与实现与上一轮审查）按施工卡逐条判定。其结论为 **部分完成**：产品行为（唯一目标、禁止项、D1–D4、通过标准）全部满足，缺口集中在交付形态与文档字段。已按审计意见整改：

1. **独立 worktree/分支**（重要）：原在主工作树施工，不符合 `D4_PACKAGES.md:25`。已改为独立 worktree `_harness_worktrees/d4-03-20261102/cwp` + 分支 `codex/d4-03-document-model`，主工作树恢复干净；本文件所在 commit 即交付记录。
2. **实际交付 commit**（次要）：由上述分支提供，见文件头。
3. **缺逐项闭合点表**（次要）：新增 §3.1。
4. **handoff 对正则 `__module__` 表述不准**（次要）：已在 §1 修正为「同一 `re.Pattern` 对象，`__module__` 为 `re`」。
5. **隔离测试子进程解码健壮性**（次要）：`subprocess.run` 增加 `errors="replace"`，避免非 UTF-8 子进程 stderr 遮蔽真实断言。
6. **独审无可核工件**（次要）：新增同目录 `D4-03-independent-review.md`。

审计同时复核并确认：六组测试数字与 handoff 逐字吻合；`.tmp403/` 与基线 worktree 确已清理；`document_normalization` 无 `source_catalog` 文本引用；`source_catalog/__init__.py` 确未导出 DTO 且未改；ruff 全绿；18 个 `document_understanding_selection` 失败在 `git archive HEAD` 只读副本上同样失败（抽查 8 节点）。
