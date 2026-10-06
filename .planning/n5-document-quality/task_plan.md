# Task Plan: N5-DOCSET 多文档类型真实质量基准

## Goal

在独占 worktree（分支 `codex/n5-document-quality`，基线 `e46108b4f30d5b7e47bfc712e360f173c00b702c`）内，
用 ≥8 份真实原件 + 实读人工 Golden，离线评测现有 parser/selector/locator 的“挑出来的是否真有价值、漏了多少、夹杂多少”，
产出 `benchmarks/narrative_document_types/`（manifest/golden/评估器/CLI/测试/报告）与
`docs/implementation/handoffs/N5-DOCSET/`（HANDOFF.md + handoff.json），零网络/LLM/下载。

## Next Step

Phase 2 进行中：完成 9 份样本 SHA/size/fingerprint 实测并写 `samples.json` + `local.json`，随后逐份实读原文产出 `golden.json`。

## Current Phase

Phase 2

## Phases

### Phase 1: 环境与只读盘点

- [x] 建 worktree/分支，确认基线 SHA
- [x] 读卡（n5_document_quality_benchmark.md）、总包（n5_parallel_packages_2026-10-06.md）、N4 实施细则
- [x] 摸清现有 parser/selector/locator/路由/现有 pilot runner 与 E6 样本
- [x] 盘点本地真实原件库存（年报/半年/季/招股书/增发/可转债/IR/英文电话会）
- **Status:** complete

### Phase 2: 样本冻结与人工 Golden

- [ ] 选定 9 份样本，实测 SHA256/byte_size/mtime，写 `samples.json`（无绝对路径）与 `local.json`（本机只读根，非 Git）
- [ ] 逐份实读原文（页/TXT 段），每份写 6–15 个 golden 标注点（正/负例、required/optional、角色、情态、locator、短引文+hash、选择理由）
- [ ] 每份注明已读页段、未覆盖范围与歧义
- **Status:** in_progress

### Phase 3: 评估器与 TDD 反例

- [ ] 定义 `narrative-document-quality/1` report schema 与评估器语义（required 覆盖率、噪声率、角色/情态混淆、duplicate ratio、scope 分母）
- [ ] TDD 反例：页码偏一、相似段落误命中、未知 golden 引用、错误 SHA、无标注范围、角色错配 —— 先红后绿
- [ ] 评估器标准不因实现改成“全过”
- **Status:** pending

### Phase 4: 跑批 CLI 与真实报告

- [ ] 复用现有 parse/select/verify 产出选择结果（无 LLM），写 `run_benchmark.py`
- [ ] 一次汇总全部类型，产出真实 `report.json`（含耗时、临时峰值、UTF8/raw bytes、real/fixture 说明）
- [ ] 不为有噪声的基准调阈值“修到全绿”
- **Status:** pending

### Phase 5: 测试（Unit / Integration / E2E）

- [ ] Unit：评估器集中验证
- [ ] Integration：实际现有 parser/selector 产出对比
- [ ] E2E：独立 catalog + 半年报/季报/再融资 ≥3 份原件走正式只读接口，locator 回放、SHA 不变、tmp 根恢复
- [ ] 本包 lint + ruff + git diff --check
- **Status:** pending

### Phase 6: 交付

- [ ] 提交代码/goldens/小报告（总提交 ≤2MiB，不入库原文/绝对路径）
- [ ] `docs/implementation/handoffs/N5-DOCSET/HANDOFF.md` + `handoff.json`
- [ ] 产品缺陷列 MAIN open_items
- **Status:** pending

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
