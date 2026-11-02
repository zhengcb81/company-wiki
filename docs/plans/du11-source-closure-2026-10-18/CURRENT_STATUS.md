# 当前状态 — 整改复核完成，残留门禁与真实主线仍待收口

唯一入口本页/[机器状态](CURRENT_STATUS.json)，交接[HANDOFF](HANDOFF.md)，实施[task_plan](task_plan.md)。

**上一轮具体修复和精确CI有效，但不能说所有问题已解决。** 本轮三独立审查与小型离线反例新确认：本地OCR/CLI JSON仍有表示大小门；ET/FF放行后CWP最终入库仍有16MiB帽；official资源参数仍有二次上帽。新发现尚未修复，详见[效果与架构复核](review/architecture-reassessment-20261102/README.md)。本轮只有调查/计划，没有产品改动或真实模型/下载。

|责任|已完成|仍未完成|
|---|---|---|
|门禁简化|上轮摘要配额、观察日志、mtime、可选review/trace、公式、ET/FF指定路径整改及独审/发布|新确认codec表示帽与采集最终入库预算残留；完整链跨层预算验收|
|抽象层|SourceRef/公开export、存储虚拟化、来源与研究职责已有|wire兼容/部署与部分测试夹具仍耦合，不能称完全解耦|
|来源内容|历史H1有12重点召回；旧有界摘要/恢复/RF采用证据保留|T4三个view父链、SEM-QUAL-01跨段条件→actual、新版真实摘要/恢复/采用|
|跨仓主线|原Q01–Q14/41项定义范围工程有处置；上轮四仓精确CI绿|RF ghost/期间补集、AUDIT新attempt/风险检测、原R4研究与完整公司循环|

## 唯一下一步与并行责任

ROOT先同族修复本地输入表示门与FF→ET→CWP最终入库预算残留，完整离线端点验收；随后T4父链/SEM-QUAL-01及单H1真实来源，再新摘要/恢复/同artifact实际RF采用。RF与AUDIT仓内既有整改可独立并行。

[协调入口](review/architecture-reassessment-20261102/COORDINATION.md)列出各仓唯一PWF。ROOT写CWP及必要FF适配；RF和AUDIT各一条本仓线，计划已备、尚未派发。沿用既有未完scope，不扩新产品包；StockWiki/ET/invest不强开任务。全局部署/真实paid/组合验收归ROOT。

上轮代码/测试五仓已推，StockWiki无remote只本地主线；ET无tracked Actions workflow。当前不重跑已绿全量。原件、生产config/DB、旧R4和外来WIP保持，Dayu/IQS/Dashboard不动。只在仓内交付/来源/真实链大节点独审，不增加许可JSON、每helper签收或人工放行。
