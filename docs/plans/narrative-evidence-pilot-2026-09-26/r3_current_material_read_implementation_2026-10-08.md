# R3A：普通资料阅读与历史时点读取分开

**Status: implemented_merged，CWP联调测试提交的精确CI待发布。** 2026-10-08准备正式R3验收时发现，原`NarrativeReadRequest`强制ISO `as_of_date`，producer及RF/SW消费者无条件校验公开日期。S09的真实公开日未知，原机制只能得到metadata reference，无法通过公共接口阅读摘要或检索业务片段；不能用fixture公开日或直接读object路径完成R3。下述三仓实现已完成，live R3仍独立待做。

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

## Producer已发布（不重跑）

正常OS首次产品RED为2失败/7通过；此前9个沙箱夹具错误发生在原子rename阶段，不算产品RED。现10个新纯DTO单测与既有28单测共38通过/0.70秒；正式CLI责任包连同新DTO26通过/27.08秒，两包的10项重复不累加。Ruff、两transport源文件mypy通过。当前read/list/search/lookup均成功并回显null，未知公开日历史请求及错证券/原件篡改仍拒绝；旧dated golden未重生成。

七个实际存在的owned测试目标已恢复absent（4文件21916B）；26保护文件SHA/大小与生产DB stat保持，生产AUTO仍absent、模型POST0。证据：[producer](harness_lanes/results/r3a_producer_acceptance_2026-10-08.json)、[清根](harness_lanes/results/r3a_test_cleanup_2026-10-08.json)。

Producer已正常提交/push为4c5590a，精确[CI37710026917](https://github.com/zhengcb81/company-wiki/actions/runs/37710026917)全部成功、80秒，[CI收据](harness_lanes/results/r3a_exact_source_ci_2026-10-08.json)。提交静态钩子和短pre-push通过，没有增加每commit完整pytest。

## Consumer、三仓节点与并线

RF先4失败/55通过，SW先4失败/48通过，再分别修正null请求和manifest时点责任。现RF67通过/1个Windows跳过，SW68通过/0跳过；跳过项是POSIX executable-provider CLI smoke，不计作通过。旧日期/hash/身份/receipt反例保持。RF代码e585f6d，SW代码42fba06；Ruff绿，SW既有static-only绿。隔离RF兼容测试的9次WinError267是兄弟仓目录不存在，不算产品RED；未改oracle，实际仓布局19/19通过。

一次[三仓真实原件CLI节点](harness_lanes/results/r3a_three_repository_chain_2026-10-08.json)1通过/0跳过/49.98秒：S07 IR、S09 TXT、真制度、误导标题业务PDF。metadata明确为isolated fixture、公开日null；CWP/RF/SW当前read及证据一致，各源三个历史请求均拒绝。业务证据9/49/0/12条，制度零模型；本地loopback共3 POST，重复新增0、真实provider/付费/生产写入0。fixture根恢复absent。这证明接口与恢复，不能冒充真实摘要质量或生产final。

RF依赖pin同步到已发布CWP4c5590a，未改冻结基线/registry；main快进c672a5e并推送，短pre-push Ruff/mypy/107 smoke通过，[精确CI37712024241](https://github.com/zhengcb81/revenue-forecast/actions/runs/37712024241)全部success。SW master快进42fba06，无remote，不伪称远端已推。342 owner文件、26原件/config/sidecar/pilot SHA及生产DB stat保持，Dayu/IQS零修改。

[RF定点安装](harness_lanes/results/r3a_rf_selective_install_2026-10-08.json)只更新一个接口文件、两个物理副本（.claude指向.agents），480未选文件保持；重复零写。自己创建的两个工作树已清理91161217B副本，RF用稀疏检出避免复制约4.7万tracked历史planning文件；原仓历史不删。[测试清理](harness_lanes/results/r3a_owned_cleanup_2026-10-08.json)解释精确临时目标及PowerShell参数错误复核，不声称清空全部系统TEMP。

权威[consumer收据](harness_lanes/results/r3a_consumer_acceptance_2026-10-08.json)、[RF CI](harness_lanes/results/r3a_rf_exact_ci_2026-10-08.json)、[owner保护](harness_lanes/results/r3a_consumer_isolation_2026-10-08.json)。

**Next Step:** 正常提交/push当前CWP联调测试与PWF，观察其精确CI后R3A complete。live token增额尚无答复，真实生产final仍0；不重跑已绿三仓节点。R3预算答复齐备后，生产阅读request使用`as_of_date: null`，历史ISO请求仍诚实拒绝unknown，不用object路径绕过公共接口。
