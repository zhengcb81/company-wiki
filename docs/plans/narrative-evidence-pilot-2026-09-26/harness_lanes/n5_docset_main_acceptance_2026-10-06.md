# N5-DOCSET：MAIN接收、当前主线对照与缺口归因

## 范围与已知状态

交付分支codex/n5-document-quality，HEAD2c3583e084a6fc632bd0970db02a439187214c0f，代码9ff251ec9ce5b29b294477d66f84336a464fc29c，写集只有benchmarks/narrative_document_types、本线PWF和handoff。9份真实资料/86标注点；基线e46108b4、selector0.3.1，报告required11/33、712个定位全回放。不能把它当当前selector0.3.2或付费摘要质量。

MAIN拥有接收与总PWF，保留用户source_acquisition修改SHA3609e707、RF main6e6b817a与两owner日志；Dayu/IQS/StockWiki/ET零写。复用现有parser/selector/来源reader，不新增数据库、模型调用或配置。此节点零网络采集/LLM/费用，不重复N4 Worker/已绿并发包。

## 一次集中接收节点

1. 对照交接/PWF/Git写集，审查评估器、CLI、标注、tests的分母与引文实读；特别核多span完整覆盖、PDF页码、TXT字节/行、parser scope、角色/情态、实际基线标记、输出与临时目录保护。工具错误先写反例RED，不将量测缺陷当selector缺陷。
2. 暂存真实merge，不提前完成合并commit。带本机只读根配置运行MAIN责任Unit/Integration/E2E：正式SourceVersionReader→半年报/季报/增发→解析/选择/回放，复制件仅独立短tmp内，finally核原件和生产/用户/RF指纹、恢复absent。只在本节点集中检查。
3. 在当前主线用9原件跑一次零LLM对照。报告另命名，不覆盖旧基线报告/golden/生产配置；记录实际Git、parser/selector、不同解析scope与全表选项。原件不复制到Git，报告持久≤2MiB、本次测试与解析scratch结束清理。
4. 对照逐条miss：引文无法定位/不在生产解析scope、实际完整内容分散多span、候选缺信号、排名/截断、重复消耗、跨块断句；不只凭全局33%结论。IR needs_review已有正式可读证明，不恢复人工门。
5. 工具正确/标注可追溯即验收本卡，不把产品效果全绿当交付门。当前主线真实残留缺口写入S7详细TDD实施细则再执行；不改golden凑绿、不自动增额度/全文永久切片，不将缺信号季报一律skip。
6. MAIN合并commit/push并核精确CI，小收据与总PWF同步。CI不扩benchmarks真实样本长测；干净clone缺local原件可显式skip，但本机验收不能拿skip作完成。

## 完成定义与交接

工具量测可信、当前主线实读结果与旧报告分清、三份正式来源E2E通过、原件/配置/生产/owner保持、测试根原状、分支成为主线祖先且代码CI绿。剩余产品缺口必须有具体样本ID/golden ID/locator/期望与实际/归因及重放步骤；本只读基准接收不等于主体质量任务完成。

## MAIN实际结果

10个量测/路径/清理反例先全RED→32单测绿；标注辅助覆盖原件/旧输出两反例RED→修复；最终本线14单测绿。一次集中39项/57.83秒，含6 Integration与正式catalog三原件E2E，271定位回放，默认自动表扫描、未全表回退。不同case合计43，另一个clean-clone case只验证缺本机根时显式skip，不替代真实E2E。Ruff绿。

真实9类当前主线报告另存`benchmarks/narrative_document_types/report-main-2026-10-06.json`：c8bf461c/selector0.3.2，12/33 required、4/17 optional、744定位全回放、48重复span、全表378.983秒、scratch峰值76302 B。噪声2/25只代表可判定范围；角色/情态零只测问题/陈述。输出旧卡基线、实际HEAD与工具源码SHA分开，不改旧golden或11/33旧报告。限定页候选诊断与[S7后续细则](../s7_document_quality_implementation_2026-10-06.md)已写，工具绿不等于语义完成。

修复实际HEAD标记、TXT字节/行双核、范围外golden拒绝、输出/未知旧文件/生产根保护、失败scratch恢复absent、事后真实SHA、2MiB原子报告及重复计算peak。标注抽页只写tmp新目录、不覆原件/预存材料。9原件+2配置+生产DB+RF两owner的14份SHA/size/mtime始终保持；0模型/下载/费用/原件删除。不扩日常CI。

**Status: acceptance_passed，待完成本次merge/push与精确CI收口。** 后续产品工作按S7施工，不重派N5工具卡。
