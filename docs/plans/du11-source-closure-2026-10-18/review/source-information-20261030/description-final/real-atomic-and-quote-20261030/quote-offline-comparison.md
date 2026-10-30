# 原始支持 quote 作为资料层 primary 的独立对照

结论：**现有 `/5` rank-only/source-extractive 已有可用的 owner 基础，值得以原始支持 quote 作为 CWP 资料阅读的 primary；本次仅代码审查与离线对照，不签 `/5` 正式模型或生产验收。** 这更直接限制了问句关系、跨条归属和口径解释进入正文的路径。原文引用仍是来源陈述，不等于外部事实核实。

## 已查实际实现

`document_understanding/source_cards.py` 的 `SourceCard.text` 只把完整 support spans 原文用换行连接，不做改写、切句、代词修复或表格推数。`source_cards` 检查原生成员解析及结构歧义；context 只以 task 引用单独保留，不能升级成 support。`source_card_generation_reason` 尊重源层 support use，不二次猜测可写事实。

`automation/narrative_model_extractive.py` 的 `compile_extractive_plan` 先按已有源阅读政策做整卡准入，文本由实际 UTF-8 canonical bytes 决定是否能进入 56KiB draft 子预算，最终 summary 仍有 64KiB 上限。它先计算大小，只在准入后物化 quote，超长/超预算整卡 deferred，不按 280 字或其他字数截断来“凑得下”；极多 task 的执行报告超过 32KiB 会在 POST 前报错。

`extractive_response_schema` / `decode_extractive_result` 只接受 task、high/normal/low priority、consider/redundant/unclear disposition。模型不能返回替换正文、数值、模态或引用；它只能排序。即使认为 redundant，已准入 quote 也不被删除；缺失/无效 decision 显式记录 RANK_INCOMPLETE/RANK_INVALID，安全原文不依赖模型把每条处理完。

## 实际 captured selection 的离线结果

直接调用 `compile_extractive_plan`，没有构造 `/5` 模型回复、没有创建正式 SummaryResult/Bundle 或 accepted 状态。selection SHA `beabd01dfa743cc8c285620ea80c1987367a27c3f672d9aba7c9656b1077e7ae`。

- 8 个完整支持 quote，draft 5719 字节，默认上限 57344 字节；8 个既有 gold 原文全部完整出现。
- 本样本最长 quote 114 字，实际没有超长真实 IR quote 试验；长文本行为另由源码与下面 19 项永久测试证明。
- 全部 text 精确等于 support 原文连接；问句中的“九目客户三星/第一大客户”没有出现在 quote 正文。question 仍是 context，不能据此说已经独立核实客户关系。
- 每个事实 quote 的 modality 都是 uncertain，needs_review=true；这是保守来源展示，不给原文整段混合动作强加单一实际/计划语态。
- model_coverage_complete=false / RANK_INCOMPLETE，因为根本没有运行排名模型；source_coverage_complete=true 仅指本 selection 的 8 个卡片，并非全文覆盖。
- 将同一真实 selection 的 draft 预算显式降到 1500 字节，得到 1470 字节：保留 t5/t8、整卡延期 t1/t2/t3/t4/t6/t7，source coverage=false，0 正文截断。这个受限探针不代表推荐如此小预算。

可复查数据 `source-quote-offline-data.json`，脚本 `compare_source_quotes.py`。限定现有 `test_narrative_extractive_runtime.py` 重新执行 19 PASS / 2.26 秒，包含长于 280 字原文、完整卡片延期、超大重复 scope 不物化、问句/context 分离、无效排名以及 handler 在 POST 前拒绝不可表示计划等案例。

## 与 /7 具体问题对照

| /7 问题 | 完整 source quote 的效果 | 剩余边界 |
|---|---|---|
| t2-1/t2-2 借问句客户关系、扩大新闻范围 | 保留报道/家电/重大影响否定在同一原文段；没有新增客户关系 | 该公司仍需相邻 question/context 消歧，不能单独把它当独立事实卡 |
| t6-3 漏报告来源 | 联系及希望仍与根据控股股东信息处于同一支持段 | 只是公司转述股东信息，非直接合作核实 |
| t8-2 新增设计/投产解释 | 保留原项目包含751吨/年、建成后保障，不补解释用语 | 原文有实际启动与未来保障的混合状态，quote 不承诺精细事件分类 |
| t3-2 省主要 | 原词主要仍在 | 原文下游分类不是所有终端客户的独立清单 |

## primary 展示的必要条件

建议 primary 是带来源角色、locator、完整 support 的引用卡；question/context 要可见且与答复明确分开。对于“该公司/该事项”，展示相关 context 比无标记补写关系可靠。可折叠长文，但展开/原文链接必须拿到完整范围，截断预览不能成为 canonical 内容。

LLM 排序或可选改写放在单独阅读辅助位置，标明派生且不替换 quotes；不能因模型未返回、说 redundant 或 prose 更简洁而丢掉已准入 source cards。源 selection partial、unread、预算 deferred、未知角色和混合模态继续显式显示，不把它们转成业务缺失。

现有 `/5` 正式路径依然要求一次模型排名及 model metadata、wrapper1。本次 pure compile 不等于 `/5` 已收费/正式完成。若要让模型真正可选，须明确设计 source-view/无排名协议及身份、报告、缓存版本，沿用已有 SourceRef/EvidenceSpan/export 所属责任；不能伪造模型调用、静默切换生产默认或另建研究 authoritative state。该架构选择也不需要新增逐材料人工许可。

## 实际 8 段支持 quotes（离线资料对照，不是正式产物）

### t1

support locator: loc:v1/page:1/table:0/row:6/column:1/chars:57-143

context roles: company_filing, investor_question（独立引用，不混入下方正文）

> 答：您好，公司积极开发国内市场，持续完善国内市场战略布局，提
> 高公司的抗风险能力，2025 年度公司境内收入约8.19 亿元，占比约22%，
> 较比 2024 年度有所提升。

### t2

support locator: loc:v1/page:2/table:0/row:0/column:1/chars:69-120

context roles: company_filing, investor_question, investor_question（独立引用，不混入下方正文）

> 答：您好，根据相应新闻报道，您所描述的情况涉及该公司的家电产
> 品，该事项未对九目化学经营构成重大影响。

### t3

support locator: loc:v1/page:2/table:0/row:0/column:1/chars:120-222

context roles: company_filing, investor_question, investor_question（独立引用，不混入下方正文）

> 九目化学主要产品为 OLED
> 升华前材料，下游客户为国内外OLED 成品材料企业，OLED 成品材料生产
> 企业下游主要为 OLED 显示面板生产企业，OLED 显示面板生产企业下游为
> 各类显示屏应用企业。

### t4

support locator: loc:v1/page:2/table:0/row:0/column:1/chars:222-308

context roles: company_filing, investor_question, investor_question（独立引用，不混入下方正文）

> 九目化学已于 3 月11 日收到北交所第二轮审核问
> 询函，因前期报送的财务数据有效期已过，九目化学申请了中止审核，待
> 财务数据按要求完成更新后，将申请恢复审核，并回复问询。

### t5

support locator: loc:v1/page:2/table:0/row:0/column:1/chars:412-489

context roles: investor_question（独立引用，不混入下方正文）

> 公司 2024 年度影响收入的主要原因为沸石系列环保材料
> 业务及部分医药业务下游需求减少，公司 2025 年度沸石分子筛产品收入
> 略低于 2024 年度。

### t6

support locator: loc:v1/page:3/table:0/row:0/column:1/chars:336-409

context roles: investor_question（独立引用，不混入下方正文）

> 答：您好，公司现无生产 VC（碳酸亚乙烯酯）的情况，根据公司控
> 股股东中国节能信息，中国节能与宁德时代已经建立了联系，并希望建立
> 业务协同与合作。

### t7

support locator: loc:v1/page:5/table:0/row:0/column:1/chars:464-554

context roles: investor_question（独立引用，不混入下方正文）

> 目前公司在半导体制造材料领域已销售的产品主要为光刻
> 胶单体、树脂、光酸以及半导体制程中清洗剂添加材料等，现已开发了超
> 300 种化合物，在所涉足的产品方面技术已经处于国内领先水平。

### t8

support locator: loc:v1/page:5/table:0/row:0/column:1/chars:554-668

context roles: investor_question（独立引用，不混入下方正文）

> 公司结
> 合实际情况与下游客户需求，在新产能方面积极布局，2025 年公司启动
> 了万润工业园二期 C05 建设项目，该项目包含半导体光刻胶用相关材料产
> 能约 751 吨/年，项目建成后将为公司半导体制造材料业务发展提供产能
> 保障。

