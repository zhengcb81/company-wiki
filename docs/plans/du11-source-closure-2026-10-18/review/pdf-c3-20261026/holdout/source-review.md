# C3 来源侧冻结审查

结论：**SOURCE_GOLD_FROZEN_WITH_METADATA_GAPS**。两份新公司原生 PDF 各冻结 10 项检查点，来源内容足以进行后续有界摘要检查；这不是正式来源资格或摘要端到端通过。

- Berkshire Hathaway 2008 英文股东信，22 物理页，原件 SHA `46920242cbb861fd844453d5e20edd8b0ecea977d85111cf2a7cfb249913c6cf`。文内 p2 的发行人/年度与 p22 的 Buffett 署名建立文种和日期；该信不是完整 SEC 10-K。既有 SEC/Nasdaq 身份快照匹配 NYSE BRK-A/BRK-B、CIK 0001067983。当前目录误标 HK/Unresolved、broker_research，需由既有 source-facts owner 在隔离测试目录校正。署名日期 2009-02-27 单列，正式 published_date 未知。
- 华利集团 300979 中文投资者关系活动记录 2023-010，5 物理页，原件 SHA `d4cec6d382d1d26e441b240a914406ce66a8a304dc32ddbe0a283c540876c831`。实际会议日期为 2023-05-11、12、17、18，不把文件名 5月19日当发布日期。检查点涵盖品牌库存周期、订单差异、紧急订单不提价、印尼两期预计产能和分期投产条件、汇兑收益/损失、客户占比误归属与新品牌工厂安排。

通过 SourceCatalog 只读 reader、SourceVersionReader 精确字节验证、PdfReading 原生读取；没有调用 select、candidate、summary 或模型。Gold 含逐段精确原文、物理页/段落定位、parser/version、quote SHA、必须共同满足的 support sets 和误归属反例。源作者实读范围逐份声明，不把全量解析等同于人工全文阅读。

Berkshire 已看 p2/6/7/22 页图，华利已看 p1/2/3 页图；页图已在独审结束后删除，本机不留页面图片。PDF metadata 分别为 Acrobat Distiller 7.0.5 (2009) 与 Word 2016 (2023)，均为既有原生印刷/办公 PDF，本轮没有 HTML 转 PDF。元数据不能认证官方来源；Poppler 对 Unicode 路径错误显示零字节大小，身份采用 SourceVersionReader 实际 SHA/size，不采用该诊断大小。

两份均在本轮 candidate 前冻结；已对 DU/W18 清单及 DU11 review 的公司名/SHA 作有限字面排查，未见既有诊断曝光。不能据此证明全部历史无人读过。任何本轮 candidate 或后续规则调试后，它们都变为已曝光回归样本，不能重复称新盲测。

明确缺口：已标 US 的 7 份登记原件只有 6 HTML/1 TXT，没有 PDF。Berkshire 填的是 US 发行人原生股东信内容覆盖，**不填真实 SEC filing PDF** 缺口。两份均缺 source_url/官方字节获取回执，不能编造。需要将来补足时，最小补采是由既有配置采集 owner 获取一份新 US 发行人官网原生报告/申报 PDF，保存身份、文种、期间、网址和字节回执；本任务未下载。华利没有独立新业务分部或其收入数字，标为不适用，不强凑。

独立来源审查已完成：**PASS_WITH_GAPS，0 open gold defects**；101 支持单位原文/quote hash/unit ID/locator 全部复读一致，20项语义核完。最终实际 SHA 和问题修正由 `independent-source-review.json/md` 单列；当前明确发现的署名日/发布日期歧义已在 candidate 前修正。物理原件路径和完整本机 locations 仅保留在 `.planning/c3-20261026/holdout-source/`，持久产物不写 raw 路径。没有生产配置/原件/catalog 写入、付费、LLM、下载或提交。

独审进一步发现并修正：华利新客户订单“会弥补”保留预期语气；GEICO 新业务检查点补齐 p7 段5-9 的明确主体上下文；Berkshire 经营表现保留 Most。两份 gold 现为 v2，初冻与修正 SHA、时间和原因详见 `gold-corrections.json`，均在任何 candidate 前修正。

独审报告只签来源 gold 准确性与其可见反泄漏范围，不代签 candidate/summary/FF/RF。正式 US 来源事实校正、官方字节回执与真实 SEC filing PDF 缺口仍未关闭。
