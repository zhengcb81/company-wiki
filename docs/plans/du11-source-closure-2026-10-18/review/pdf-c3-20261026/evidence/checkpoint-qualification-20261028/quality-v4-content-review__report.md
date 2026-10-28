# 真实 HK v4 独立内容审查

FINAL — PARTIAL；来源准入 FAIL，摘要内容尚未通过。实际run `phaseC-090-9f3f43873512` 在预约/POST前被 `PHASE_C_GOLD_SUPPORT_MISSING` 阻断，没有response、bundle、artifact或final；这些SHA在JSON中明确为null。不能把源gold2/3写成摘要2/3。

行业云仍缺共同事实支持：t4/p2=s33（p13/paragraph9，pdf_text_block）保留1340.4百万元及截至1245.4的半句；t35/p2=s34（p13/paragraph10，pdf_native_range）从“百萬元增加7.6%”开始并含IT需求、复制垂直行业方案两原因。两组分别只支持自己的span，context都只是“管理層討論與分析”。模型的task-local规则不能跨task拼事实；t19的1340.4也不能补出完整同比及原因。QCV4-IR-01仍open，owner是native fallback下的原句/来源支持闭合，尚未进入模型。

R&D准备支持t32保留报告期420.5百万元人民币/58.7百万美元，以及2025-06-30的1094名研发人员。t31的2024年底武汉中心620余人（含实习/外包）是另一个范围。H2准备支持t33保留“展望下半年”“將”“旨在”及AI计划。两项仅来源准备PASS；没有生成文字可判定是否改错时期、货币、人数字段或未来模态。

新selection检查点准确记录：paragraph增强请求[12,13,17]，120.0252秒后ChildTimeout；最后stage=IMPORT，completed=[]，pending=[12,13,17]，accepted_groups=0，native_fallback，stream_complete=false，temporary_root_restored_absent=true。没有已完成页可恢复，不是完成页丢失或partial_enhanced。IMPORT后的具体SDK操作未被这份诊断细分，不能据此猜导入模块、文件读写或转换内部原因。native pages_read=75也不代表完整细粒度解析；layout/planning仍partial，page75 deferred。

实际准备57tasks/112spans/5675原文字符；逐57task核对了实际support_parts与selected citation support。输出计划仍8192tokens、40全局、2/task、软目标24。准备输入仍有页脚作为事实任务（t2/3/9/11/12）、非GAAP标签碎成独立tasks（t5–8）、无指标前件的研发原因t10，以及定义/会计政策/套话。它们是选材观察，不是本次final已经输出的错误。没有final可审整篇引用、单位货币或更多增量遗漏，不作虚构通过/失败结论。

本run 0预约、0POST、0usage rows、0tokens、0费用；母账本前后同为1800368tokens/727945microUSD。activation recovery虽被请求但未进入；same-run重启、跨run cache及FF/RF消费者均未执行，不能宣称新生命周期已PASS，也不把公共只读消费者当预测采用。本次确实没有新增收费，恢复去重未被实际演练。

来源SHA、实际input/selected压缩与解压SHA、planned generation pin及收据SHA详见report.json。保护文件/哨兵未变、临时lake删除按producer receipt记录。审查仅新增这两份报告，未重跑worker/Docling、未读原PDF、未调用网络/模型、未改源码/测试/PWF/原件；旧v3内容报告与工程独审保持不变。
