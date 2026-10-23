# 两条可立即启动的独立施工包（2026-10-23）

这次只有下面两张卡；两条可以同时开始，不等ROOT完成W08或额外签A。每个harness只领一张卡，必须在指定工区施工。ROOT保留W08选材/结构/缓存、实际联网与摘要、统一费用账、中央审查循环及最终并线；两线不写中央run和母PWF。

| 施工卡唯一入口 | 已准备的独立工作目录 | 任务 |
| --- | --- | --- |
| [W09-RF-RESEARCH](W09-RF-RESEARCH.md) | `C:/Users/郑曾波/Projects/revenue-forecast-r1-research` | 修正式引用和角色、做最大收入驱动的经营桥、运行离线主/压力预测、提升通用买方研究方法 |
| [W11-CWP-SOURCES](W11-CWP-SOURCES.md) | `C:/Users/郑曾波/Projects/company-wiki-r1-source-recovery` | 官方来源发现的离线分类/覆盖诊断，只有真实内部缺陷才修产品 |

## 给外部harness的启动指令

进入上表指定工作目录，读取其`START_HERE.md`，再完整读本目录对应施工卡、[INTERFACES](INTERFACES.md)、[INPUTS](INPUTS.json)和[交接模板](handoff.template.json)。按指定独立PLAN_ID/PWF_PLAN_ROOT继续，完成A/B/C；**交接前调用未参与实现的独立agent全面审查，全部修复内部问题并复审最终版本后交接**。不需逐小步人工签收，不向ROOT重复索要已授权范围内的权限。

施工卡只在这里维护，不复制多份。工区的START_HERE只是指针，继承来的根目录旧计划不是本包队列。实际代码base与开工文档start HEAD在[dispatch.json](dispatch.json)，二者不同是正常文档提交，不代表代码变了。

## 关键边界

- 两包不下载、不调用外部模型、不改生产原件/配置/数据库，不占用统一剩余费用。W09复用旧已付摘要并标历史生产版本；ROOT后续采用新的W08正式摘要。
- W11旧IR只找到了结果与486789B响应的hash，尚未找到完整HTML正文。不得把hash当作可重放正文；如仍不可得，可以交付完整、有证据的不改结论与外部资料缺口，不能伪造修复或开新provider。
- 两个工区实际检出且不复制原件、旧`.planning`树；共用原Git对象库。RF初始检出约9.15MB，CWP约111.77MB，含现有代码和已跟踪文档，不是新的解析缓存。
- 可正常提交并推送各自codex支线；不merge主线、不force-push、不安装技能。ROOT负责验收、组合测试和主线发布。

## 固定交接入口

- RF：工区`delivery/w09/handoff.md`及`handoff.json`。
- 来源：工区`delivery/w11/handoff.md`及`handoff.json`。
- JSON统一`r1-harness-handoff/1`，包含需求逐项结果、实际命令和日志、最终源码/产物SHA、独审原报告与问题关闭、测试目录恢复、空间占用、外限和ROOT下一步。不将包完成写成整个公司或PWF已通过。
