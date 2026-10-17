## ROOT 最终接收 — 2026-10-17

状态：PASS，作者完整历史 faf5e580 已 merge；ROOT 修正与独立复审以 receipts/root-gold-final-review.json 的 17 项实际文件 SHA 为准。下方旧 schema1、raw bindings 命令、旧 PASS 和原始 handoff SHA 均为历史，不能用于当前 schema2。

### 实际修正

- 语义：Verisk 单一 Insurance segment 的分母（552.1+230.5=782.6 million）不再误罚为非总收入；阿里8.60亿与含蚂蚁9.60亿去重口径分开；东方电缆原文 Q3 总额约30.66亿与类别35.49亿的冲突保持未知，不自创包含其他收入/YTD解释；名创电话会按开场创始人/CEO归因；中微21.81%属于等离子体刻蚀设备，XD RIE与YDRIE时间点分开；宁德772保留报告期内，仅321在建为期末。
- 抽象：source_ref 使用真实公开v2身份，source_binding仅用于测试初次登记；临时 SourceCatalog.register_sources → query_ref → open_version 实读验证SHA。HTML严格绑定 canonical unit_id+source_locator 并批量 replay；PDF只查指定物理页，无全篇回退。生产根/配置不改，不复制原文。
- TDD语义先8FAIL；当前71PASS/2.83秒，含5个真实临时Catalog正反控（错误SHA、大小、页码、quote拒绝）。11/11真实来源回放PASS；独立复算10原件SHA/size/mtime保持，生产config SHA保持，隔离目录和sentinel恢复。
- 最终独立复审8项全部闭环、0未解决。旧独审Verisk数字误读保留为历史，由本ROOT结论覆盖。

### 当前复现命令（从 company-wiki 根运行）

```powershell
python -B -X utf8 -m pytest docs/plans/document-understanding-2026-10-13/parallel/du10-2026-10-17/goldset/tests -q -p no:cacheprovider
python -B -X utf8 docs/plans/document-understanding-2026-10-13/parallel/du10-2026-10-17/goldset/tests/verify_anchors.py --project-root . --output <独立测试收据路径>
```

环境需已安装本项目和catalog/PDF依赖；第二条需要当前source_catalog配置中的原件。只在隔离临时catalog登记少量选定路径，不扫描全湖、不写生产库。回放PASS只证明来源/locator，不证明经济语义或摘要质量；语义另由独立实读审查负责。

**这是已被读取和修正的回归标注集，不是盲holdout，不是正式模型摘要质量验收。** case.prior_use仅描述最初选样时的历史；新holdout必须另选未参与调整的来源。新增股发行等完整文档阅读覆盖仍遵循母计划，不以本11例冒称全覆盖。0收费/下载/翻译，原件无变更。

Next Step：ROOT继续共享引擎PDF生产接线，随后配置供应商真实摘要、缓存恢复与新盲样本验收；此数据包不新增生产门禁。


---

以下为历史记录（状态以顶部 ROOT 更新为准）。

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
