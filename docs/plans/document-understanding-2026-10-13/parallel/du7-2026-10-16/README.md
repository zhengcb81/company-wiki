## ROOT调度更新 — 2026-10-16

PDF已验收并线；ET仍施工，保持其目录排他。

---

# DU7：两张可同时施工的独立大包

2026-10-16。本次只有**两张**新卡；不重复已分发的DU6三卡。不强凑第三项或重开已经完成的RF/AUDIT工作。源码基线、真实工区和种子提交见ROOT生成的 `launch.json`，状态READY后均可立即独立开工。

| 卡 | 项目/工作目录 | 独立计划入口 | 负责的结果 |
|---|---|---|---|
| [DU7-PDF-TABLE](du7_pdf_table_observations.md) | `C:/Users/郑曾波/Projects/company-wiki-du7-pdf-tables` | `docs/plans/du7-pdf-tables-2026-10-16/task_plan.md` | 现有PDF细格/逐值定位→现有TABLE观察，不重新解析PDF |
| [DU7-ET-EXTRACTION](du7_et_extraction_fidelity.md) | `C:/Users/郑曾波/Projects/earnings-transcripts-du7-extraction` | `docs/plans/du7-extraction-2026-10-16/task_plan.md` | 修已有网页抽取的漏句、重复和短标题丢失 |

PDF包优先级更高，直接服务共享阅读引擎TABLE生产接线。ET包修复的是目前默认关闭的既有Motley网页能力，不代表FMP生产抓取故障，也不允许为本卡开启provider或增加付费订阅。

两包目录不重叠；都不写ROOT生产组合层、DU6作者树、其他仓、技能安装目录或生产数据。ROOT继续统一预算/来源准备、TABLE依赖闭包、显式v4摘要/恢复和真实质量。合流时ROOT接入和最终跨仓验收，作者交付后STOP，不自行并主线。

先读各自工区内的 `construction_card.md`、`INTERFACES.md`、task_plan/progress/findings；它们足以提供独立上下文。[共同接口与交付规范](INTERFACES.md)是文件所有权和验收说明，不是人工许可链。只保留A/B/C三个大节点，不逐小步骤审批或全仓复核。
