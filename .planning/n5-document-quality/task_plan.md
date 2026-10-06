# Task Plan: N5-DOCSET 多文档类型真实质量基准

## Goal

在独占 worktree（分支 `codex/n5-document-quality`，基线 `e46108b4f30d5b7e47bfc712e360f173c00b702c`）内，
用 ≥8 份真实原件 + 实读人工 Golden，离线评测现有 parser/selector/locator 的“挑出来的是否真有价值、漏了多少、夹杂多少”，
产出 `benchmarks/narrative_document_types/`（manifest/golden/评估器/CLI/测试/报告）与
`docs/implementation/handoffs/N5-DOCSET/`（HANDOFF.md + handoff.json），零网络/LLM/下载。

## Next Step

已完成全部阶段；等待 MAIN 按 `docs/implementation/handoffs/N5-DOCSET/` 验收合入。

## Current Phase

Phase 6

## Phases

### Phase 1: 环境与只读盘点

- [x] 建 worktree/分支，确认基线 SHA
- [x] 读卡（n5_document_quality_benchmark.md）、总包（n5_parallel_packages_2026-10-06.md）、N4 实施细则
- [x] 摸清现有 parser/selector/locator/路由/现有 pilot runner 与 E6 样本
- [x] 盘点本地真实原件库存（年报/半年/季/招股书/增发/可转债/IR/英文电话会）
- **Status:** complete

### Phase 2: 样本冻结与人工 Golden

- [x] 选定 9 份样本，实测 SHA256/byte_size/mtime，写 `samples.json`（无绝对路径）与 `local.json`（本机只读根，非 Git）
- [x] 逐份实读原文（页/TXT 段），共 86 个 golden 标注点（每份 8–12 个）
- [x] 每份注明已读页段、未覆盖范围与歧义；全部引文回原件核验并写入 `quote_sha256`
- **Status:** complete

### Phase 3: 评估器与 TDD 反例

- [x] `evaluator.py`：`evaluate()` + `validate_report()`，schema `narrative-document-quality/1`
- [x] TDD 反例 22 条（页码偏一、相似段落、未知 golden、错误 SHA、无范围、角色/情态错配、篡改引文哈希、抬高分子、删 golden、缺分母），先 RED 后 GREEN
- [x] 评估器标准不随实现改成全过
- **Status:** complete

### Phase 4: 跑批 CLI 与真实报告

- [x] `run_benchmark.py` 复用现有 parse/select/verify，零 LLM/网络
- [x] 真实 `report.json`：9 份 / 86 点 / 712 span，回放 712 通过 0 失败，耗时 260.8s，临时峰值 152,604B
- [x] 未调阈值：required 0.3333、噪声 0.0833、重复 0.0674 如实入库
- **Status:** complete

### Phase 5: 测试（Unit / Integration / E2E）

- [x] Unit 22 / Integration 6 / E2E 1 = 29 passed（37.62s）
- [x] E2E：独立 catalog + S02/S03/S05 走 `open_version(purpose=narrative_derivation)`，271 span 回放全通过，原件指纹与 tmp 根恢复
- [x] `ruff check benchmarks/narrative_document_types` 全绿；`git diff --check` 干净
- **Status:** complete

### Phase 6: 交付

- [x] 代码提交 `9ff251ec9ce5b29b294477d66f84336a464fc29c`（15 文件 7,164 行 ≈350KB，≤2MiB；无原文、无绝对源路径）
- [x] `docs/implementation/handoffs/N5-DOCSET/HANDOFF.md` + `handoff.json`（7 条 open_items）
- [x] 产品缺陷移交 MAIN，外线不自改主线
- **Status:** complete

## Key Questions

1. 哪些文档类型本地有真实原件？→ 年报/半年/季/招股书/增发/可转债/IR/英文电话会均有（见 findings.md 样本表）。
2. 允许写哪些路径？→ 仅 `benchmarks/narrative_document_types/`、`.planning/n5-document-quality/`、`docs/implementation/handoffs/N5-DOCSET/`。
3. 公开入口能否直接给中间选择结果？→ `parse_*` + `select_narrative_evidence` + `verify_*_evidence_spans` 均为公开 API；E2E 用独立 catalog + `SourceVersionReader.open_version` 正式只读接口，层级如实标注。

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 样本 9 份（含增发+可转债各 1） | 卡要求 ≥8 且补半年/季报与再融资；两类再融资本地均有 |
| 原件只读、引用放 `local.json` 且不入 Git | 卡规定 Git 不存原件与机器绝对路径 |
| 评估器与 CLI 全部落在 `benchmarks/narrative_document_types/` | 卡限定允许写集合，不动 tests/src/scripts/CI |
| Golden 由实读原文产出，selector 输出仅作被测对象 | 卡禁止拿当前 selector 输出当标准答案 |
| E2E 用独立 tmp catalog + 样本副本 | 卡要求独立 catalog；原件不动、不硬链接，raw 复制进自己的 tmp 根 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| （待记录） | | |

## Notes

- 零网络/LLM/下载；所有测试 DB/WAL/缓存/raw 副本放本 worktree `tmp/` 短根，结束后恢复。
- 不写生产 catalog/索引/配置；`config/source_acquisition.yaml` 的既有未提交改动属 MAIN，不碰。
