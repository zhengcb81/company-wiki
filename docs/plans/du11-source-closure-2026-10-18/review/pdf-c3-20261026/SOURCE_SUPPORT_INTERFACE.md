# 来源支持能力接线（2026-10-28 实施中）

本细则承接 ADMISSION_ROOT_PLAN，不是新审批或许可。源码尚在施工，未签收或发布。

- 唯一源 wire：`du-production-reading/4`；每个 `citation_views[]` 保留原 support/context 完整分区，新增必需字段 `reading_support_use`（support/context_only/unresolved）和 `reading_support_reason`（小写下划线诊断码，最长80字符）。判定属于此完整 support view，不能借 context 或按 span 多数投票。
- ROOT 唯一数据能力注册：`document_understanding/reading_context_contract.py`。仅定义版本/字段验证，没有正文分类。源 producer、canonical contract、任务投影、引用适配与 benchmark 观察器引用同一能力定义，避免分散版本判断。
- 来源线负责 `narrative_reading`、`narrative_support_use`、`narrative_business_policy`、`narrative_source_purpose` 及其新中性测试；早期选材避免明显caption/footer抢占112位置，完整 scope 用途由来源 owner 判断，未知完整业务描述、资源、原因、风险、未来、否定不一刀切。原件和检索可见不删除。
- ROOT消费线负责 canonical contract、summary_tasks/source_cards、scoped/model引用消费、decision identity及benchmark兼容。SourceCard.available继续表示可读性；只有source use为support的当前任务进入生成；context_only/unresolved保留原plan和原因。compiler不解析正文，不跨task拼接。/4未分组孤立资料为unresolved/source_use_unassessed，不凭缺省宣称完整。
- 历史/1–3只读/显式兼容保留，旧source task binding维持/1；携带新use的plan为/2。新付费执行按当前source recipe重新准备，不能用旧历史缺字段产物冒充/4已评估来源。
- 现有scoped identity与decision business算法闭包包含新的数据能力注册及来源语义helper；不创建第二缓存、任务库或许可链。

ROOT消费TDD：旧代码5F/2控制通过；新7测试及原任务/admission包34P/4.71秒。这只证明消费合同，不证明来源识别。来源线独立RED18F/11P，包含真实 `_candidates` 接线与unknown定性/原因/风险/资源/未来正例；尚待工程完成、整体实源复验及独审。

发布前跨仓兼容：RF有/3版本和view exactfields重复解析，需要窄幅兼容并保留use，不能丢标记或当context_only为独立事实；FF仍走SourceExport采集，不增加正文判断。StockWiki既有bundle reader还存在/2–3兼容债，先界定当前实际消费路径，不能顺手改其他owner运行资料。先只读盘点Git/PWF，隔离源码施工，完成离线联调再发布/4。未清理或覆盖他人assurance/output/runs。

后续验收次序：来源与消费集中中性正反例→已保存真实112材料的源owner离线重放（不是手填能力标记）→原生实际来源选材与跨仓接缝→关键节点独审→正式原语言摘要/恢复/缓存/FF-RF实际采用→新holdout与公司循环。修oracle后不能再为同一检查器误报重跑未改变的120秒SDK。SDK依赖隔离设计保持独立，不抬额度。
