# DU10-CWP-SUMMARY-GOLDSET — 建立可复用的叙述摘要质量基准

## 工作区与目标

- 仓库：`C:/Users/郑曾波/Projects/company-wiki`
- 独立 worktree：`C:/Users/郑曾波/Projects/company-wiki-du10-summary-goldset`
- 起点：`master` / `900dbf6489f3b995a0bfb7fcbb8a001a68df241d`
- 建议分支：`codex/du10-cwp-summary-goldset`
- 唯一交付目录：`docs/plans/document-understanding-2026-10-13/parallel/du10-2026-10-17/goldset/`
- 目标：为 ROOT 即将完成的正式摘要与真实 holdout 验收准备小而可复查的来源定位基准；不重建现有 DU-Gold 体系，不修改生产 reader/selector/parser。

## 唯一文件所有权

只可新增/修改本卡 `goldset/` 目录下的 JSON case、标注说明、校验器、专属测试和 receipts。CWP 的 `scripts/`、`automation/`、`document_understanding/`、`profiles/`、现有 tests/、其它 PWF、配置/数据库及任何公司目录都只读。原件不复制、不改写、不翻译、不下载；用既有 SourceRef/SourceExport、SHA 与 locator 引用原件。

先读现有 `review/deliverables/` 和已有 source/summary review contracts，复用其 case/key/locator 约定。不能另造第二套摘要产品或新的 PASS 门。只收录尚未覆盖的缺口；重复既有 case 需说明它增加哪项证据。

## 基准内容

准备至少 10 个互不重复的来源定位 case，来自当前本地可用原件，尽量覆盖 A/H/US 和：年报/半年报/季报、招股/增发/可转债、投资者关系、电话会 TXT。缺少某类真实样本就写清 `NOT_AVAILABLE`，不得下载、以合成冒充真实覆盖或声称全覆盖。

每例聚焦叙述性业务信息：行业变化、主营业务进展、新业务/第二曲线、出海、项目实际进度与管理层计划。至少有：

- 支持摘要命题的 SourceRef、原件 SHA、精确 locator（页/段/表/话轮）；
- 允许的摘要表达和不能越过的结论边界；
- 必须保留的时间/期间、actual vs planned、说话人/主体、币种/单位（若相关）；
- 易误读反例，如套话、风险提示、项目计划与投产、财务表与业务叙述混在同页。

排除纯财务报表数值复算；这些数字由金融 API/下游模型处理。标注要短，存 locator 与必要的最小证据片段，不存整页/整份 MD/PDF/TXT。

## A/B/C 节点

### A — 缺口盘点与样本冻结

对照已有 DU-Gold case ID、当前摘要合同及已知失败（关键事实遗漏、引用范围过宽、actual/planned 混淆），列出只补缺的 case 清单。记录每个源文件 SHA 与可读 locator；确认原件/配置未变。

### B — 标注与离线校验器

形成版本化、机器可读 case 文件；校验必需字段、ID 唯一、市场/文档类型覆盖、SourceRef 可由只读接口解析、locator 有效、支持与反例不冲突。校验器仅报告数据完整性，不自动判定经济事实或摘要质量。

### C — 独立实读与交付

由非作者独立 agent 逐例通过 CWP 只读接口重新打开原文，确认 SHA/定位/支持关系，并复核标注没有把管理层展望写成已实现事实。修复全部问题后，再由同一 reviewer 对最终提交和每例 hash 复核。完整度/质量审查通过才交接。

不调用 LLM、不创建生产摘要、不写公司资料目录。测试只用本卡新建的轻量 JSON/少量文本夹具；结束后验证 owned temp 与 sentinel 已恢复。

## 交接

在 `goldset/` 下交 `task_plan.md`、`findings.md`、`progress.md`、`handoff.md/json`、`cases/`、`tests/`、`receipts/`。记录每例来源 SHA/locator 验证、真实文档类型分布、缺失样本、测试命令/退出码、临时文件清理、独审最终 SHA/报告。所有纳入 case 经独立实读且无未修问题时标记 `COMPLETE`；否则如实保持 `PARTIAL`，不以数量凑齐覆盖。
