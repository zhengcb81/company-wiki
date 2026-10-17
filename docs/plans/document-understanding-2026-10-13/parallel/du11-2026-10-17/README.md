## 已派发 — 用户2026-10-17确认

两卡均已发出，RF/FF作者各自独立施工；ROOT继续CWP，不进入作者工区写文件。下方READY描述为派发前记录。

# DU11 — 两条独立消费者改造线

状态：**READY_FOR_DISPATCH**，用户尚未派发。两卡已准备，可以立刻并行；工作目录尚未创建。本轮不重开已完成DU10，也不为凑第三包给ET增加第二缓存。

| 卡片 | 实际施工仓/专用新工作目录 | 目标 |
|---|---|---|
| [DU11-RF-CITATION-CLOSURE](du11_rf_citation_closure.md) | RF；`C:/Users/郑曾波/Projects/revenue-forecast-du11-citation-closure` | 已读支持/上下文与覆盖诊断接到实际claim/参数消费，双入口共因修复 |
| [DU11-FF-TRANSCRIPT-REUSE](du11_ff_transcript_reuse.md) | FF；`C:/Users/郑曾波/Projects/filing-fetch-du11-local-transcript-reuse` | 默认经普通query_local复用跨来源已知公开日合格电话会；unknown/excluded留诊断不重下，真缺失再用原FMP |

卡片存于母company-wiki，但RF作者只改RF专属文件，FF作者只改FF专属文件；两者不写母CWP。ROOT独占CWP automation/source_catalog/document_understanding生产装配与其tests，并承担最终并线/远端发布/必要技能定点同步。作者提交本分支后STOP，不自动合main。

固定基线：RF main/origin/main `568fb9256885eb31a0f76d9ead59fd0f98575073`；FF main/origin/main `f1a939e522c22b23659712a8bd2b344f5eb0a364`。只创建指定新worktree，不复制主仓WIP；RF既有3个assurance/runs修改与output/、FF未跟踪凭证都保持。读依赖CWP固定 `34a7dd71aaa49d18c13fcdd300ce79581114ca5b`、ET参考 `2584b7eed062a9a30254bc06b4f19ab5471b414e`；ROOT主仓会继续变化，作者用固定源快照和公开wire测试，不跟漂移HEAD。

共同边界：不写Dayu/IQS/StockWiki，不读密钥；0外部网络/付费/模型/翻译；真实原文不复制。合成资料仅在owned tmp内，先记初始目录/sentinel/SHA/mtime，最后精确恢复。保持现有预算/拒绝异常/unknown语义，无新人工许可链。A调查RED、B根因修复、C隔离离线E2E三个集中节点，不设逐节点人工签收。

**每卡交接前必须另调用独立agent，全面审查完整度和质量，所有问题修复并测试通过，由审查员复核最终受审源码SHA，零未解决才handoff.md/json。** 已有契约审查可重用，新增实际消费行为仍须检验。最终交接包含基线/实现提交/源SHA/精简命令收据/独审与恢复记录，不保留庞大原始运行树。具体白名单/契约/反控/命令均在各卡，`launch.json`为机器索引。

FF公开接口注意：中性本地复用用普通SourceRequest(provider=null)，不包要求provider非空的transcript-import lookup envelope；显式fmp保留原专用lookup。普通query的unknown日期在excluded_candidates，不是可用历史来源；原provider从成功reader receipt.manifest读取。各分支反控与合格match优先规则已写卡。
