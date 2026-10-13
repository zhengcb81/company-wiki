## 当前执行归总 — 2026-10-13

已交付DU/DU2接收与发布保持完成；剩余共享阅读升级统一按[ROOT状态表](../task_plan.md)及[完整施工细则](../completion_implementation.md)执行。此文保留设计/历史，不依据下方旧“施工中/待接收”指令重开卡；仅A/B/C三个集中验收节点。

# 共享引擎与阅读策略：深化复审及下一轮施工

2026-10-13；Owner ROOT。先读[复审结论](report.md)、[文档覆盖与阅读矩阵](strategy_matrix.md)、[ROOT 实施顺序](root_implementation.md)。本次是有代码和小样本证据的复审，未修改生产代码，未接收或覆盖既有四个 DU 工作树。

**结论：保留共享引擎；先修策略未生效、依赖闭包和评价基准的共用问题，再扩充类型与业务深度。** 15 个 profile 不等于 15 类文档已经通过真实质量验收。现有部分基准分数不能继续作为改进幅度的可靠依据，原因见报告；旧失败和旧报告保留。

当前实况：原 PROFILES/STRUCTURE/BENCH 已有交付，另有 ROOT 整合分支；它们均未在主线启用。本轮只在 review/ 保存新增设计，原 DU/1 不变。新卡不是重新分发旧三卡。

## 可以现在分发的三包

| 新卡 | 工作目录（company-wiki 的独立 worktree） | 做什么 | 独占目录 |
|---|---|---|---|
| [DU2-FAMILIES](cards/DU2-FAMILIES.md) | C:/Users/郑曾波/Projects/_harness_worktrees/document-reading-review-20261013/families | 各市场文档形态、招股/融资、附件/修订等阅读策略与真实证据 | review/deliverables/families/ 与自身 PWF |
| [DU2-FACETS](cards/DU2-FACETS.md) | C:/Users/郑曾波/Projects/_harness_worktrees/document-reading-review-20261013/facets | 主业/新业务/出海/产能/订单等业务关注点、必要上下文与反例 | review/deliverables/facets/ 与自身 PWF |
| [DU2-LAYOUT](cards/DU2-LAYOUT.md) | C:/Users/郑曾波/Projects/_harness_worktrees/document-reading-review-20261013/layout | 字体/几何结构提示、双栏和经营表格依赖，纯函数及真实样本测试 | 新 layout_hints 子包、专属测试与自身 PWF |

前两包交付可执行验证的数据和策略规格，由 ROOT 接入唯一 profiles registry；不另建路由器或第二套金标判定器。第三包只实现新辅助目录，原 parser/adapter 接线仍归 ROOT。三包不需要互相等待，不写原 profiles/structure/benchmark/root 模块，不写共享计划、配置、CI 或安装副本。

公共[增量数据接口与交接格式](INTERFACES.md)已定义。只做 A/B/C 集中检查。分发时给卡片和对应工作目录即可；卡片引用的上下文和现有原件定位清单均在 checkout 中。目录准备结果见[发布记录](dispatch.json)。

## ROOT 保留的工作

统一接收旧 DU 四个分支；修原 benchmark 的目标及证据绑定；统一依赖闭包/原子预算；使章节别名和子路由真正生效；已有元信息透传；调用既有格式前端；生产与 AUTO/generation 接线。随后一次跨层 B 和真实 C 节点，复用母计划 G2/G4/G5，避免重复付费验收。新卡未完成不阻碍 ROOT 先修这些已证实问题。

本轮记录在[task_plan](task_plan.md)、[findings](findings.md)、[progress](progress.md)；根因最小复现及证据见[receipt](evidence.json)和 probes/。调查用小脚本不进入日常 CI。
