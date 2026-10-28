# HK quality-v3：来源闭合只读诊断

当前只确认“连接在哪一层已经丢失”，尚不签定增强超时或缓存根因。19份工程源码保持冻结，无产品改动、PDF重跑、模型、下载或费用。

旧 paid bundle 的行业云支持是原生group中的4个原span（p13段9–12），同一task t37同时携带现期收入、同期数值、7.6%和两项原因。新实际request仍有这些文字，但源任务已经拆开：t4/background仅支持段9首片；t35/native_continuity只支持后三片的carrier。“首片+尾片”的引用隔离使各任务不能独立闭合，预留前gold拒绝正确，不能在summary compiler跨task拼接弥补。

当前纯helper对照：四片整体仍得到 business_revenue_measure / operating_metric / meaningful_fact、financial_only=False；首片也仍是明确业务收入；尾三片整体为unknown/description。后者缺主体，不应重新授予财务豁免或提升为事实。

精确局部反控已执行：从旧bundle重建标题+4支持的5个typed NarrativeUnit，逐个原text、locator/coordinates及投影EvidenceSpan ID完全一致；不补造 transient reading_layout、font_runs或native_source_view。把旧已证闭合group作为给定输入交给当前纯 `_candidates`，仍返回同4支持一组、4×meaningful_fact/operating_metric、0withheld。**这只证明当前用途/准入/前指不会拆开给定的完整group，不是全原文selector、新native连接或新Docling行为已复验。** fixture明确 document coverage incomplete，pages_read=0。

旧实际reading_execution为Docling 2.96.0，enhanced、pages [12,13,17]、accepted3/rejected128、103.7925秒；旧首片到下一片的公开x0差约22.68，fontsize9，超过普通native_wrapped_line的2.1em阈值18.9。因此缺少额外source-exact paragraph membership等既有证明时，普通原生行流本来就不能直接保障该连接。不能据此发明bbox特例或宣称新运行必然超时。

新actual request的coverage投影未保留reading_execution，也不含全部原始native membership/font输入；清理后的收据不足以判断新增强是否降级、提案是否缺首片或闭合/cache哪一环变化。下一步由ROOT在已有测试观察中保留selected.reading_context，再查共享PDF增强与原生闭合的执行事实。不能靠抬120秒、改gold、恢复unknown豁免或调整该公司页码修复。

文件：

- `closure-diagnosis.json`：输入SHA、旧group/支持ID、新任务metadata、纯helper及局部selector收据。
- `closure-5unit-fixture.json`：可复用5unit typed局部fixture和已证group/pipeline，缺失的transient原生证据未编造。
- `closure_probe.py`：读取现有gz与fixture重建的纯Python复现，无PDF/API。复现：配置PYTHONPATH=src后以Conda `-B -X utf8`运行。

已停止进一步产品改动，工程冻结延续。
