# DU9 POLICY / PLANNER 接收核对

状态：DELIVERY_LOCATION_PENDING，2026-10-17。用户已通知两卡完成；下列是ROOT实际可见事实，尚未宣称这两包验收或并线。

| 施工包 | 指定作者目录 | 实际 HEAD / Git 状态 | 已见 / 未见 |
|---|---|---|---|
| POLICY | `C:/Users/郑曾波/Projects/company-wiki-du9-geometry-policy` | `f70318f1edd3e5bfec86ae1ee0922a1ac72b59a2`，干净 | 只有种子及A调查提交；无geometry_policy.py、专用测试、handoff或独审 |
| PLANNER | `C:/Users/郑曾波/Projects/company-wiki-du9-geometry-planner` | `8ff47e28031270c7bf7f6fca01b582fdb680fd64`；未跟踪geometry_intent/ | 已提交A测试/手算96页fixture；未跟踪contracts.py及__init__.py，但无planner实现、handoff或独审；PWF B/C仍pending |

已只读核对：作者PWF三个文件与源/测试实际目录、基线至HEAD的全部commit与diff、本地全部DU9 refs和注册worktree、Projects顶层同名目录、origin的DU9 refs。远端查询未返回DU9分支。未扫描真实公司资料/凭证/会话记录；未改作者树。

两张施工卡要求执行A→B→C再独立agent全面审查、修完后交接，不要求A阶段后停工。POLICY progress自行写的“等待ROOT B阶段/停止”与原卡不符。先向用户核对是否在另一目录/分支交付，不把这段自述当ROOT的待批准门。

ROOT实际 `python -B` import 两次均失败：POLICY缺 `profiles.geometry_policy`，PLANNER入口引用不存在的 `geometry_intent.planner`。收尾再次只读核对HEAD/文件仍一致，无handoff。未在缺实现时虚构独立代码审查PASS。

若预设目录即实际交付，请原harness沿用[继续B/C说明](../parallel/du9-2026-10-16/CONTINUE_BC.md)，不需要ROOT签A、不另开任务包。若成果在其他位置，只需给最终路径/commit，不重写已完成成果。

独立主线工程已正常发布master/origin `ce6e4646`、6213PASS/24SKIP与[精确CI SUCCESS](https://github.com/zhengcb81/company-wiki/actions/runs/38979991954)，本地工程WIP已清理；这不等于DU9组件或默认深页完成。收据见[工程发布](../common-root-quality-evidence/production-ports-publication.json)。

## 下一步

1. 确认最终交接路径/commit；若用户明确由ROOT接手半成品，在新的ROOT接收树中继续，保护作者原内容。
2. 有真实交付后分别检查唯一catalog/registry/薄编译与纯planner的职责、固定DTO、原WorkBudget、缓存因果、零/小额度、窗口公平/重叠、恢复与独审证据。
3. 根因反例与相关集中套件通过后并线；ROOT再接原生导航/章节匹配、默认深页collector与单次parse预算，做真实PDF和正式摘要。组件PASS不冒充生产深页/摘要质量。
4. 核对期间可独立发布现有已冻结的CWP工程节点；不修改POLICY/PLANNER/ET外包范围，不抬原15秒/64页/2M预算，不添人签或许可文件。
