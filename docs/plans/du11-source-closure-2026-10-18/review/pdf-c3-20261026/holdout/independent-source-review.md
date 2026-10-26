# 独立来源金标审查

结论：**PASS_WITH_GAPS；来源金标缺陷 0 OPEN**。仅审来源侧金标，不代签候选选择、正式摘要、FF/RF采用或US SEC完整财报PDF覆盖。

独立经 SourceVersionReader.open_version(preview) 核原件字节，再用 PdfReading.read(selector_version=0.8.0) 复读，未调用 select、模型或下载。生产 catalog 始终 query-only。最终 v2 共 101 个支持单位的原文、SHA、unit ID、locator 全部一致，20 项检查点逐项核对主体、期间、单位、否定、计划和上下文；另核 Berkshire 实体/署名页及GEICO页、华利三页业务正文图。

独审发现并复验修复四项：署名日不作为 published_date；华利新客户补单保留预期语气；GEICO新业务支持集合纳入明确主体上下文；Berkshire经营描述保留 most。修正来自原件，不参考候选结果。

剩余缺口：Berkshire目录误标HK/Unresolved/broker_research；缺正式来源网址/取得收据；原件是股东信而非SEC10-K。华利会议日期不等同发布日期/财季。已有SEC/Nasdaq snapshot仅能支持主体身份，不能认证该PDF字节来源。两份可作来源内容holdout，不能据此宣称正式US filing端到端资格通过。

可见反泄漏范围通过：独审未读候选/摘要或调用producer；提供的源作者执行也未见此类动作。独立复查W18、DU holdout、DU5三份排除清单未命中两份SHA/公司名。不能证明所有历史会话绝未读过；首次候选使用或规则调试后应按exposed/regression对待。

最终绑定（字节改变须重新审查）：

| 文件 | SHA-256 |
|---|---|
| manifest.json | e8f794fb4b62ac776ace25de6dccfba42c2a1ea2fd0d4d217f005db96189528a |
| c3-us-berkshire-letter-2008.gold.json | a5db9f9f7eeb536c3cbab367aa7b172a8f39268bdbca6f9c0b0bdf7e55a2ee22 |
| c3-cn-huali-ir-202305.gold.json | f00f127585d4015fbb8592a8254327f205386877cbc03481b39eeb294932f6f9 |

完整计数、修正项与不适用范围见独立JSON收据。

绑定收尾复核：manifest 中 verdict_location 由 report_json.status 改为 report_json.verdict，与独审实际schema一致。反向替换精确复现此前已审manifest的SHA；两份gold未变，结论不变。
