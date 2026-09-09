# ZR601–604 上游资产事实补审

2026-09-06，主审补查，防止把revenue同号测试误当company-wiki完成。只读。

原registry 80–83行明确owner=company-wiki：601 AssetFact schema/type/canonical alias（时效/证据/循环/碰撞）；602 resource/reserve/grade/capacity/permit + basis/标准/measurement date/单位；603 ownership/consolidation及地区层级；604表格提取冲突和人工review。它们不是单纯的下游收入乘法。

现有证据：ZR601 11receipt explicitly test-only、新增revenue test_zr601_asset_facts，wiki未改；ZR604改revenue contracts/constants/document及冲突参数测试，未实现上游表格→事实→review存储链。其他两项的收入侧实际单位/持股问题已在revenue-audit列明。

先用CodeGraph查资产上下文，未得到对应目标；再对src/scripts具体字面AssetFact、asset_fact、asset_alias、ownership_timeline、reserve_classification、contained_metal检索无匹配。名称未匹配本身不能证明不存在等效代码，但结合已定位的实际extractor/产物合同和收据，可以确定现有验收不能证明原owner要求。

`src/company_wiki/source_catalog/section_chunk_fact.py::extract_facts`实际只用regex生成metric/value/unit；无asset身份、有效日期、basis、classification、来源locator、冲突及review决策字段。normalizer将这些置frontmatter，不能由此推导具备canonical asset alias和含证据的资产事实registry。

判定：601/602/604至少PARTIAL且上游原链UNVERIFIED（原完整完成主张不获认可）；603收入侧期内持股反例已CONTRADICTED。后续不能只修revenue helper就关闭四项。需要独立资产/单位合同、source locator与parser version绑定、别名collision/循环/时效、原值和标准化值并存、冲突不覆盖、人工review可追溯以及只读export消费，严守wiki不持有投资研究结论边界。

本补审不是新模型设计授权；未创建asset事实、修改schema或读取真实矿业内容。后续真实样本与独立会计/计量review见总修复计划。
