# R3A：普通资料阅读与历史时点读取分开

**Status: in_progress。** 2026-10-08准备正式R3验收时发现，现有`NarrativeReadRequest`强制ISO `as_of_date`，producer及RF/SW消费者无条件校验公开日期。S09的真实公开日未知，按现状只能得到metadata reference，无法通过公共接口阅读生产摘要或检索业务片段；不能用fixture公开日或直接读object路径完成R3。

## 接口与职责

- 保留`narrative-read-request/1`的四个字段；`as_of_date`明确为ISO日期或JSON `null`。`null`表示当前资料阅读，不声称资料在任何历史日期已公开；缺字段、空字符串、非法日期仍拒绝。已有ISO请求行为不变。
- producer继续验当前SourceRef、原件/工件SHA、身份/期间、版本、locator和当前来源状态。仅`as_of_date=null`时不执行历史公开时点判定；manifest公开日保持真实值或未知。
- RF与SW薄consumer接受并回显此明确模式，receipt必须与请求的`as_of_date`精确一致。当前模式不产生历史可用性或预测资格；指定日期时公开日未知/晚于cutoff仍拒绝。研究/预测入口的历史证据责任不取消。
- read/evidence-list/evidence-search/evidence-lookup复用同一个transport判断，不另造reader、队列、权限开关或fallback。无下载、模型、翻译或生产写入。

## 一次接口节点（TDD）

1. 先写producer RED：未知公开日当前read与三检索成功，历史read拒绝；坏SHA/错身份仍拒绝，非法cutoff拒绝、receipt模式不变。复用实际DAG/持久化/CLI夹具，生成资料全部在短测试根并finally恢复。
2. CWP实现nullable cutoff。为RF/SW各自独立clean工作树补请求/receipt/DTO责任测试与实现；不触碰RF owner日志、SW quick-scan或IQS/Dayu。检查既有工作树后使用新的明确归属目录，不复用其他harness未交接工作。
3. 当前三仓真实producer→正式消费者CLI联调：明确fixture身份/日期及loopback摘要仅证明接口，不冒充真实模型质量。当前模式正向和历史拒绝同时通过，ref/hash/evidence一致，未选资料与独立根保持。受影响旧历史反例通过，不每helper或每commit跑全仓。
4. 正常合入/提交/push与对应源码CI；更新当前R3调用卡。正式live R3仍须token增额答复，使用生产真实metadata/null模式；不改模型请求、历史费用、token/费用上限。

## 输出与停止条件

持久化RED/责任绿/当前三仓CLI节点、源码SHA/CI及清根证据。只有三个当前消费者都具备明确模式且历史规则不退化，R3A才complete。它不能代替R3的真实生产final、语义复核、同run零POST恢复和实际空间测量。

## 本轮实际结果：producer本地通过，consumer仍pending

正常OS首次产品RED为2失败/7通过；此前9个沙箱夹具错误发生在原子rename阶段，不算产品RED。现10个新纯DTO单测与既有28单测共38通过/0.70秒；正式CLI责任包连同新DTO26通过/27.08秒，两包的10项重复不累加。Ruff、两transport源文件mypy通过。当前read/list/search/lookup均成功并回显null，未知公开日历史请求及错证券/原件篡改仍拒绝；旧dated golden未重生成。

七个实际存在的owned测试目标已恢复absent（4文件21916B）；26保护文件SHA/大小与生产DB stat保持，生产AUTO仍absent、模型POST0。证据：[producer](harness_lanes/results/r3a_producer_acceptance_2026-10-08.json)、[清根](harness_lanes/results/r3a_test_cleanup_2026-10-08.json)。

**Next Step:** 正常发布producer并核精确源码CI；然后RF/SW独立clean工作树的request/receipt/DTO同步与三仓节点。已检查现有工作树，它们是其他施工历史/owner，不能随意复用或重置。live token增额仍未获答复，真实生产final仍0。
