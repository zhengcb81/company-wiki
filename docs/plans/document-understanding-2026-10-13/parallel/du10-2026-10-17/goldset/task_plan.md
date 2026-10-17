# DU10-CWP-SUMMARY-GOLDSET — 任务计划（PWF）

- 卡：`du10_cwp_summary_goldset.md`（同目录）
- worktree：`C:/Users/郑曾波/Projects/company-wiki-du10-summary-goldset`
- 分支：`codex/du10-cwp-summary-goldset`
- 基线：`900dbf6489f3b995a0bfb7fcbb8a001a68df241d`（master）
- 交付目录：本 `goldset/`；其余仓库内容只读
- 状态：A 完成 → B 完成 → C 完成后标记最终状态（见 handoff.json）

## A — 缺口盘点与样本冻结

- 对照既有 29 个 DU-Gold case（`tools/document_understanding_benchmark/gold/`）、
  DU2 families/facets 交付、摘要合同（`review/summary_grounding_implementation.md`、
  `review/source_scoped_summary_implementation.md`）与已知六类错引失败，列出只补缺清单。
- 逐例记录：原件绝对路径（机内 bindings，不提交）、SHA-256、页数、选用锚点页。
- 先用（prior-use）逐公司核查 `.planning/`、`docs/plans/`、benchmark gold。
- 冻结收据：`receipts/node_a_freeze.json`；详细缺口矩阵见 `findings.md`。

## B — 标注与离线校验器

- `cases/du10gs-*.json`：schema `du10-summary-goldset-case/1`，复用 du-gold/1 的
  fact/any_support_sets/quote-anchor/must_preserve/must_not_assert 约定，
  另加摘要专用字段（allowed_summary、misread_traps、summary_guidance）。
- `cases/index.json`：case 清单 + 覆盖矩阵 + SHA。
- `tests/test_goldset_structure.py`：必需字段、ID 唯一、市场/文档类型覆盖、
  支持与反例不冲突、引文预算、无绝对路径泄漏。离线、无原件依赖。
- `tests/verify_anchors.py`：只读原件核对（SHA 复算 + 页文本空白归一化逐字比对 +
  mtime 前后不变）。需本机 bindings，不进 pytest 收集。
- 校验器只报告数据完整性，不自动判定经济事实或摘要质量。

## C — 独立实读与交付

- 由非作者独立 agent 通过只读方式逐例重开原件：核对 SHA、锚点引文在所指页/行存在、
  支持关系成立、标注未把管理层展望/计划写成已实现事实。
- 问题修复后由同一 reviewer 对最终 HEAD 与每例 hash 复核。
- 交接：`handoff.md`、`handoff.json`、`receipts/`（测试命令/退出码、清理验证、独审报告）。

## 边界

- 不修改 `scripts/`、`automation/`、`document_understanding/`、`profiles/`、现有 tests/、
  任何原件与配置；不写公司资料目录；不复制/改写/翻译/下载原件。
- 不调用 LLM/付费 API；0 网络调用；测试只用本卡轻量 JSON 夹具。
- 不新建第二套摘要产品或新 PASS 门；重复既有 case 必须说明新增证据。
