# PDF-C3 运行环境、历史恢复与推送反馈根修

最新：旧精确CI40402565591失败4项旧cache夹具，修复ROOT48P；语义候选独审3项OPEN。见[CI与语义当前收据](ci-followup.json)。以下原运行中状态为发布当时快照；不代签新CI或内容。

状态：工程与历史物理部署测试独审 PASS/0 OPEN，已正常推送 master `ad9a9a96`；pre-push154P/30.11秒，精确CI运行中。[发布收据](runtime-publication.json)。正式摘要、RF采用与holdout内容仍 OPEN。

## 已完成的共因修复

|责任层|问题与结果|验收|
|---|---|---|
|PDF阅读实现|整个环境枚举将重复发行元数据算进hash；v2改为实际声明依赖闭包，v1不改|独审25P；真实worker两启动路径104依赖一致；真实HK3页增强117.40秒成功|
|叙述generation/cache|历史完成结果被当前recipe误拒；冻结身份不应变成重新执行条件|独审32P；原parser升级、PDF跨run、paid恢复各精确节点通过；实际执行仍严格recipe绑定|
|发布metadata owner|JSON数组/null/标量泄漏AttributeError|5类中性RED；统一ValueError并被batch标准化；原独审复验关闭|
|本地推送执行器|affected扫描拉入重集成、600秒超时且孙进程持锁|FAST不减；仅小范围unit追加，180秒总界限，受界子进程树清理；真launcher/持锁文件独审通过|
|历史部署测试|旧代码exec到当前module，却仍hash当前物理package|修真实隔离物理部署，保留全部缓存/材料/费用断言；1P/31.69秒，25原assert不变，独审PASS/0 OPEN|

各作者handoff为历史记录，其pending及旧SHA以同目录independent/final-review为最终结论；不覆盖旧报告。来源见 [evidence-map](evidence/runtime-recovery/evidence-map.json)，约454KB，原件/整库/本机配置未复制。

## 实际内容情况与下一步

首个正式attempt在预留前发现3项gold未覆盖，0POST/费用。环境v2真实读成功后，行业云的收入变化及原因已在原文选材中出现，但还需同一封闭引用组检验；研发420.5百万元/1,094人、下半年AI计划仍未入选，不标成内容PASS。

随后native-only的4.31秒观察确认这两段原文完整且admitted=True，shared fact判定却eligible=False，落入description。reading_plan/3防套话优先级本身是既有不变量，不能为了金标硬把所有展望标题提权。先补共有经营资源/计划关系和独立来源主题的正反例，再修语义owner；保留112span、16M work与业务财务边界，不从PDF重建三表。

本轮无新模型/下载，母账1,783,378tokens/$0.724836不变；新US股东信和CN IR holdout尚未产出candidate/summary。真实摘要语义、activation/跨run恢复、FF→RF实际采用和完整公司循环都是后续责任。

## 复现边界

只用原有PdfReading/selector与SourceVersionReader端口；diagnose_material.py是已登记SourceRef的只读观测器，不是第二解析入口。增强配置保留本机，v1/v2 SHA在独审JSON里；真实源观察压缩存档90KB级。归档脚本是当时原位置字节快照，复跑应从evidence-map原路径或节点正式入口，不直接在归档目录运行。

聚焦ruff通过；Linux全src mypy389文件通过。元数据单测已原样迁到tests/unit以纳入CI；正常宿主14P/1.57秒。第一次默认沙箱在tmp_path setup因临时目录拒写产生6errors/8P，未改测试；按既有正常宿主+仓内独有短TEMP复跑通过并清理。没有放宽原文、recipe或断言。

下一施工细则：[共同语义owner与中性正反例](SELECTION_ROOT_DESIGN.md)。这份设计不修改生产代码，不扩大本轮工程验收范围。
