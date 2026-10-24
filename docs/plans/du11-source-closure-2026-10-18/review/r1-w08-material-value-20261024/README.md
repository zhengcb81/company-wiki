# W08 source材料价值、覆盖和对象绑定（2026-10-24）

## 变更与责任

Source owner分开admission和材料价值，补业务范围、客户收入地域、合同存量与收入确认安排的用途；现有planner只读value_band/topics，不重读正文，不改权重、96/48000/16M或任务8/4/2048限额。OperatingFact DTO及显式0.8兼容保持。泛效益、通用活动/口号composition为description；实际渠道、明确范围、来源关系中的未知状态仍可有材料价值，未知不得写成已完成里程碑。

合同及地区关系只从自身断言和直接谓词观察。合同数量、同主体协调、数量partitive和被动确认小语法复用predicate_scope；删除reading中的重复整句转换fallback。客户合同对象要求performance义务、RPO或明确订单，裸一般义务不算客户订单。地区金额支持中英文通用区域语法，缺market/region修饰的英文地区专名仍是覆盖限制，不新增国家/公司名单。

独审发现carrier重复金额正则指数回溯，已改为单向贪婪token消费；独立输入12–2048位数字排除import开销后最高约0.0017秒。不提高timeout或work预算掩盖；来源session预留扫描工作由原6×变为9×文本，仍在16M统一上限下。

新模块加入原decision_inventory business_algorithms字节依赖。测试通过实际完整decision freeze/current比较证明模块变化使缓存失效，不建新缓存状态库。

## 实际结果

同一SourceRef真实249页年报，1526候选，96选中、8109字符，9,540,035/16,000,000 work，55个模型任务。两个原业务归属checkpoint仍通过。

独立14项由7pass/5partial/2missing改善到8pass/6partial/0missing：A04订单/RPO/确认排程missing→pass，A03地区收入missing→partial；旧7pass保持。A02旧15.84%子事实的已选支持丢失已单列，不以缺表头终止经营数字擅自赋值。真实表歧义已有table_structure_ambiguous，消费者必须保留。

[独立内容审查](content-review/report.md)、[增量](content-review/delta.md)只签来源选材及局部任务可见性，不签正式摘要、RF采用或公司研究质量。最终源码再次真实实读的全部EvidenceSpan、task-local groups和55tasks逐项等于独审输入，见final-source-receipt.json；selection.json/trace.json保留初始生产绑定，不改旧SHA。

## 验证与历史失败

- 首批TDD18F/7P→25P，见tdd-receipt.json。后续永久中性用例32项，覆盖真实公开selector、长数字、泛结构、非客户合同义务。
- 独立首次21例13F/8P，整句借员工/现金、差旅费地区、供应商转换已共因修复；后续同主体/数量关系/缓存/效率反控见independent/。
- 一次自然包2330P/11skip/1F（initial）发现误降待验证产品材料，旧断言未删；后续回溯挂起仅终止已核对自有pytest，backtrack-terminated收据如实保留。
- 线性版自然2336P/11skip/177.76秒，涵盖来源/结构/默认兼容/缓存/闭包；此结果在最后裸义务对象收敛前，不能冒称最终版本。最终聚焦128P/27.85秒，Ruff PASS、mypy src374文件0错。
- 最终独立工程410P/31.85秒（含34独立），374源树执行前后SHA一致，全部内部发现已修，见independent/final-report.md/json。正常commit和pre-push/精确远端CI另以最终收据为准。没有跳hook，没有减少断言，没有用旧CI代签新代码。

## 剩余与下一步

当前6项partial为A01/A02/A03/A05/A09/A13：继续来源业务父子、产能日期、地区口径局部依赖；精确财表可以由已实读SourceRef/API补齐，不强迫财务全文切片。之后正式摘要/cache、RF实际采用矩阵及W12四审；原公司复验后药明合联、Snowflake与完整循环。无收费调用、下载或原件副本；原文、生产配置/目录库、旧封存保留，Dayu/IQS及W13–W15独占范围未改。
