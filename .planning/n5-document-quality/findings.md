# Findings — N5-DOCSET

## 1. 只读原件与路径（实测 2026-10-06）

| 样本 | 类型 | 路径（只读根内相对） | SHA-256 | bytes | 页/行 |
|---|---|---|---|---|---|
| S01 | 年报 | `companies/中微公司/raw/financial_reports/中微公司：2025年年度报告.pdf` | d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5 | 9,165,875 | 259 |
| S02 | 半年报 | `companies/中微公司/raw/financial_reports/中微公司：2025年半年度报告.pdf` | 91ae4978b694ef8361195e50a414e00d071c835d1d6e9f60bccc75dc22175cdd | 6,361,468 | 188 |
| S03 | 季报 | `companies/中微公司/raw/financial_reports/中微公司：2026年第一季度报告.pdf` | ab7bb0076b2a3fb42ebca7b54d1b167a790221e394613ce544e275b249eb3268 | 217,264 | 15 |
| S04 | 招股书 | `companies/中微公司/raw/prospectus/中微公司：首次公开发行股票并在科创板上市招股说明书.pdf` | 19cdb41e03b2d86ac15007753784f5859e1450a2bf79b514a7c0d4bd6830be67 | 11,211,796 | 429 |
| S05 | 增发募集说明书 | `companies/三角防务/raw/research/三角防务：西安三角防务股份有限公司向特定对象发行股票并在创业板上市募集说明书（注册稿）.PDF` | cd803fe9528f4646f8f29b518a450ae4bd5b5968c482eb49789f9786b523595b | 5,595,592 | 191 |
| S06 | 可转债募集说明书 | `companies/华锐精密/raw/research/华锐精密：向不特定对象发行可转换公司债券证券募集说明书.PDF` | c6ed566631e123f159abf2697c157f1868f8e994ccf8e3352132046a6c5ca0a1 | 4,756,322 | 227 |
| S07 | 有价值IR | `companies/万润股份/raw/research/万润股份：投资者关系活动记录表20260515.pdf` | 221467c15a24180205a8226f96fea9bda0262c866d5ba8aa31889ec96e6466d7 | 153,851 | 6 |
| S08 | 程序性IR | `companies/中际旭创/raw/research/中际旭创：投资者关系活动记录表20220506.pdf` | 53bb98b65d40318a610242bf4f97f94a24ab66834e573f9248fcd8864706c44a | 10,155 | 1 |
| S09 | 英文电话会 | `MSFT/MSFT_Q4_2026_earnings_call.txt`（earnings-transcripts 根） | 4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a | 66,324 | 340 行 |

- 只读根用 root key 表示：`company_raw`（源仓主工作副本，原件均被 `*.pdf`/`**/raw/` ignore，不入 Git）、`earnings_transcripts`（兄弟仓 transcripts 目录）。**本机绝对路径只写 `benchmarks/narrative_document_types/local.json`，该文件被 `.gitignore` 排除，不入 Git。**
- S01/S02/S03/S04/S05/S07/S09 与既有 G1 manifest P01/P02/P03/P04/P06/P07/T01 的 SHA 前缀一致；S06/S08 为新增。
- 既有四样本（P01 年报、P04 招股书、P07 IR、T01 电话会）作对照，本包新增半年报、季报、增发、可转债、程序性 IR。

## 2. 运行时复用点（不抄实现）

- 解析：`company_wiki.source_catalog.narrative_evidence.parse_pdf / parse_pdf_bytes / parse_transcript_text`
- 选择：`select_narrative_evidence(parsed, title=…, existing_kind=…, max_selected=…)` → `NarrativeEvidencePackage`
- locator 回放：`verify_pdf_evidence_spans / verify_pdf_evidence_spans_bytes / verify_transcript_evidence_spans`
- 路由：`route_document / classify_document_kind`（`narrative_routing.py`）
- 版本：`NARRATIVE_PARSER_NAME/VERSION = selective_narrative_parser 0.1.0`、`NARRATIVE_SELECTOR_NAME/VERSION = select_narrative_evidence 0.3.1`
- 角色：span `structured_value.source_role` ∈ {company_filing, management, analyst, investor_question, operator, editorial, qa_text_shadow}
- 情态不在 selector 输出中 → 由 golden 标注，评估器用“角色类 vs 情态”一致性度量混淆。
- 正式只读接口（E2E）：`SourceCatalog` 独立 catalog → `SourceVersionReader.query_ref` → `open_version(ref, purpose="narrative_derivation", expected_read_policy_sha256=reader.read_policy_sha256())`

## 3. 现有可参考件

- `scripts/narrative_evidence_pilot.py`（G1 runner）：SHA 前缀校验、parse→select→verify、anchor 匹配、summary_input 字节测量。
- `docs/plans/narrative-evidence-pilot-2026-09-26/g1_sample_manifest.json`：manifest 形状与 anchor_checks（本包只作对照，不作标准答案）。
- `tests/integration/test_narrative_runtime_e2e.py::_new_catalog`：独立 catalog + sidecar + `SourceVersionReader` 的最小搭法。
- `tests/conftest.py` hermetic socket 阻断；根 `conftest.py` 短 basetemp 约定（`tests/` 下的 conftest 不会作用到 `benchmarks/` 下的测试，故本包自带 conftest）。

## 4. 关键约束复述

- 允许写：`benchmarks/narrative_document_types/`、`.planning/n5-document-quality/`、`docs/implementation/handoffs/N5-DOCSET/`。
- 0 网络 / 0 LLM / 0 下载；总提交 ≤2MiB；原件 SHA/size/mtime 结束不变；不写生产 catalog/索引。
- 报告 `narrative-document-quality/1` 为 source-only，不做投资评价。
