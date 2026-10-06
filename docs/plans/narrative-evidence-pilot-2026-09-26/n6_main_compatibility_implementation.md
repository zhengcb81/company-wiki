# N6 MAIN：选择器升级后的历史 final 兼容

## 范围与现状

2026-10-06复核：RF main仍为6e6b817a，两份weekly owner日志不动；CWP master ca6d9ce只含新卡文档，用户source_acquisition改动不动。上一目标回合为progress（DOCSET发布与N6独立卡/分支准备），不重复已绿节点。

正式NarrativeTransportReader保存完整EvidenceSpan，按原件字节/parser定位回放，未重新运行选择器。旧NarrativeEvidenceResolver只是isolated pilot，summary-only合同会重选且限制当前selector版本；不能据此宣称正式final已经坏掉，也不能放宽ID/hash校验来修这个旧工具。S7最终端到端必须走正式transport/search/exact/RF消费，旧试点不升级为第二canonical reader。

## 本轮先完成的兼容测试

1. 在0.3.2代码下，复用正式三个job与outbox发布夹具，一次生成小型TXT、JSON电话会及PDF产物；全部合成原件、确定性本地模型、无网络/费用。把原件bytes、完整bundle和实际生成版本冻结在tests/fixtures/n6_main_compatibility/，总量不超过128KiB。冻结测试数据不含真实身份/密钥/物理路径，不能在未来测试时用新选择器重新生成旧标准答案。
2. 新独立Integration只用冻结原件建立tmp catalog，通过既有artifact store登记冻结final。模拟当前selector升级/不可调用，正式transport.reference/read仍返回精确旧bytes与evidence IDs/locator；语种和角色不变。
3. 对相同升级状态加入真实字节等长篡改反例，仍被当前来源SHA拒绝。测试的源码version与历史bundle版本分开记录；没有产品缺陷不制造RED、不改已正确读取架构。
4. fixture根起初不存在，finally关闭catalog并清理；外层短pytest根由MAIN核归属后清理至absent。一次责任包，不进入普通CI新增长矩阵；本轮不重跑9文档基准或并发kill/ACK包。

MAIN独占新tests/integration/test_n6_persisted_selection_compatibility.py和新fixture目录，不写N6-CANDIDATE的4模块、N6-BUDGET的2模块、FOOTPRINT目录，不编辑三树PWF。这里的版本模拟只验证兼容边界，最终两线真实代码并入后的正式E2E仍需执行。

## 接线/后续集中节点

收到质量线完整handoff后，MAIN读取main_wiring可选Rules字段和原因，不预先猜新增字段。实际合入候选/预算后再注入narrative_evidence.py、更新selector版本及生成identity测试；parser/locator/public wire保持。重跑本卡冻结兼容测试，再一次真实9样本与正式Worker→search/exact→RF。已提交卡内互斥文件责任继续有效。

## 状态

兼容责任包已完成（最终发布收据随本轮补齐）：实际冻结3份0.3.2产物，共17056 B（含README共18247 B）；强化后的Integration 9项通过/4.85秒，Ruff绿，legacy spans表为零、篡改前后成功读取证明通过。初轮9红是本线夹具误拿catalog内部ID与public URN比较，改成对比完整SourceRef后通过；没有产品RED、不改正式reader。旧试点version耦合不改成canonical。

共享入口也已只读复核：route_document只提供默认96/160与empty_result_may_skip，未在候选前hard skip行政标题，混合文档由候选与finalize按内容处理；不需要抢外线文件或先改路由。用户已通知三线分派，尚未收到新交付；不据此宣称进程live或已经完成。
