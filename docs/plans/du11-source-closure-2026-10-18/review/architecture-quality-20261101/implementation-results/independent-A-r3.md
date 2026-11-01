# A 节点独立复审 r3 — 语法旁路已修，能力失败传播仍需修复

2026-11-01；审查者 `/root/rectification_review_a`。本轮只定点复查 R3，冻结文件5/5 SHA已匹配，绑定[本轮证据](independent-A-r3-evidence.json)及作者`Q01-rework-r3-evidence.json`；没有把R2收据当R3通过。没有修改产品/主PWF/Git/原件/配置/生产DB，没有模型收费/下载或重复88/100/118旧整套。

**结果：41项定点通过，原lexical bypass已修复；但仍有1个实质P2，A暂不签全部完成。** 新问题来自本任务明确要求检查的“缺资源/超界不能变成无业务成功”，不是扩展任意新语法难例。

## 本轮确认通过

- 旧EN/CN declaration regex和causal=True旁路已删，一般可读性由同一matrix owner决定；真正typed/event/measurement proof仍由原owner处理。
- 首轮六个relative/的名词化片段均不准入；同词完整matrix句保留。条件When/Where有matrix可读，单从句、倒装和无问号What/Which/Who不产生独立proof。
- 同scope observation只计一次32n+1工作，并由后续passage复用；预算停机先于模型，真实session为partial，重复访问无补扫/补费。
- 固定POS的中文作用域歧义按unresolved+relevant保留原话，通过真实_admitted，但Fact/事件/数字/issuer proof不升级；明确fragment不准入。
- 真实p12三unit及其他行业同构例仍可读；不能据此签112实际入选/真实摘要/RF使用已完成。
- 缺资源/4096char超界在直接grammar和简单无财务passage责任层返回明确unknown。问题出在下述混合scope和selection传播，不抹掉这些已经正确的层。
- PDF表格观测adapter变化的真实cache失效/text负例，以及语言资源bytes/推理包版本变化的实际cache反例继续通过。资源四文件及版本沿已核manifest，无新增资源或版本伪签；本轮不重建wheel。
- Q10/Q12没有新源码变化，本轮不重跑其旧大域，也不改此前无具体故障结论。

## A-r3-01 / P2 — 能力失败被金融分支吞掉并变成 skipped_no_narrative

位置：`source_catalog/narrative_source_passage.py::prepare_source_passage`尾部在`_grammar_uncertainty(...)`之前执行`if finance_seen: return context('financial_only', finance=True)`。下游`narrative_reading.py::scope_use`/`narrative_reading_admission.py::_admitted`没有把grammar能力失败作为明确未完成原因传到选择结果。

精确原文：

`Our vessels transport liquefied gas between coastal terminals. Net income was $20 million.`

在同一个纯内存真实assessment＋公开`select_narrative_evidence(selector_version='0.9.0')`单unit夹具中，仅改变grammar能力：

| 条件 | prepared passage | 实际selection |
|---|---|---|
| 正常 | support / mixed_narrative_context | selected，1span |
| `grammar._english_tagger`抛LookupError（模拟缺依赖/资源） | context_only / financial_only，relevant=False | **skipped_no_narrative**，0span，coverage_complete=True，diagnostics空，withheld0 |

这不是“不明数字必须拒绝”的正常质量边界：同一原文有完整具体业务句，纯粹能力不可用却被写成已知财务内容、不存在叙述。它可以让消费者/终态处理将本应恢复的能力故障当成无业务跳过。没有运行生产Store或付费流程，因此不声称已发生实际终态缓存污染或公司金额错误。

同一单业务句（没有末尾财务句）缺资源时公开selector为needs_review/0span，未伪称业务成功；但admission原`source_grammar_unavailable`仍被折成`unresolved_without_business_relevance`。此时仅是诊断丢失；混合例将它确认为实质P2，而非只要求增加字段的维护建议。

修复方向：能力unknown（unavailable/scope_limit）先于“纯财务”结论；在既有scope/selection诊断和partial/deferred责任内传播，保留原unit/locator和重试理由。语言歧义继续与能力失败区分，不能借此让全部未知材料变support。修复应使用同一原文在正常/缺资源/超界的对照，不新增人工review许可/第二任务库。若原件真是纯财务且从未请求grammar，仍可按原规则跳过。

## 验证、错误和恢复

实际定点41项：relative6、matrix6、真实/跨行业5、条件2、无问号/倒装8、单从句2、歧义2、资源缺2、超界1、预算先验1、session partial2、同scope复用1、真实cache3。**41P /23.20s**，两条既有jieba/pkg_resources弃用警告保留。

额外只做本任务要求的真实selection能力故障探针：简单句正常/不可用、混合句正常/不可用。首次探针尝试dataclasses.asdict遇mappingproxy不可深拷贝，属观察代码错误，已改直接读取字段；没有把它当产品失败、没有改生产类。

独占`tmp/a3r-20261101`初始absent、长度51，本轮未触发旧长TEMP重定位；结束前核绝对目标在本repo/tmp，再删除仅本轮目录，最终absent。无原件/DB复制，没有完整备份恢复演练。

ROOT已收到实质P2及精确重现；下一步仅根修能力状态传播后定点复查，不因41绿冒签A，也不重跑已过的大域。
