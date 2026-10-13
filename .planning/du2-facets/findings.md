# Findings — DU2-FACETS

## 契约要点（INTERFACES.md §3/§4）

- du2-facet-spec/1 必填：schema_version、id、version、business_questions、applicable_mechanisms、
  positive_evidence、required_context、confusions、absence_rules、summary_focus、case_ids。
- required_context.required_when ∈ {always_for_assertion, quantity_emitted, project_emitted,
  explicit_condition_present}；slots ∈ {subject,product,project,geography,period,role,modality,
  stage,quantity,unit,denominator,condition}；missing_behavior ∈ {unknown,partial,deferred}。
- applicable_mechanisms ∈ {generic,subscription,consumption,store_network,manufacturing,
  biopharma,cdmo}；只是内容修饰，不是股票行业分类器。
- du2-reading-case/1：case_id/kind/source/observation/expectations；支持组外OR、内AND；
  mutation 必带 expected_failure+reason；可选 candidate_claim+expected_missing_slots（纯结构检查）。
- 语义反例生产执行写 execution_status=NOT_RUN_ROOT_INTEGRATION。
- 每 source 引文合计 ≤8KiB；持久数据建议 ≤512KiB；0 原件复制；绝对路径不进可移植 fixture。

## DU/1 unit_kinds（positive_evidence.unit_kinds 词汇，取自现有前端代码）

pdf_text_block, pdf_table_row, pdf_table_qa_fragment, transcript_speaker_block, official_json_field,
html_heading, html_paragraph, html_list_item, html_table_cell, html_footnote,
pptx_paragraph, pptx_table_cell, pptx_notes_paragraph, pptx_image_ocr_line,
docx_heading, docx_paragraph, docx_table_cell。

## 真实锚点（C节点，SHA 与 sample_manifest 全部一致，引文21/21逐字命中原文）

| sample | 公司/市场 | 锚定风险 | 关键原文含义（已核对） |
|---|---|---|---|
| cn-equity | 恒锋工具 / A股 | 分期先后和建设期 | 建设期两期：一期2019-01拿地→2020-12建成厂房→2021-01一期建成投产（陈述为已发生）；二期以“一期建设完成+老厂区设备搬迁至一期新厂房”为前置条件，“预计2021-01启动、2021-12完成、2022二期建成投产”（计划语态，不是实际）。p68“建成达产后”才“优化升级原有产能12万件套+年新增营业收入2.60亿元”——回报测算带达产条件，原有/新增口径不同 |
| cn-convertible | 金禾实业 / A股 | 原有/新增产能与资金缺口 | 2016上半年已完成年产500吨三氯蔗糖项目（既有）；本次募投是400吨吡啶盐+1,500吨三氯蔗糖两个独立项目（26,527.49/46,220.20万元总投资；拟投入募集资金20,000/40,000万元，合计6亿≠总投资72,747.69万元）；“若实际募集资金净额低于拟投入…不足部分由公司自筹解决”是资金缺口条件 |
| cn-ir | 万润股份 / A股 | 问句前提、管理层否定、股东vs上市公司 | 问句自带前提（“断崖式下降”“有没有存在涨价预期”）不是公司事实；“公司现无生产VC（碳酸亚乙烯酯）的情况”是对“推动VC带量采购”设想的明确否定；“中国节能与宁德时代已经建立了联系”属控股股东层面，上市公司层面“现无生产VC”；九目化学是被问主体（北交所审核中止），不能把其进展当万润自身 |
| hk-annual | 名创优品 / 港股 | 门店模式/总数/地域/期后 | 门店按直营/名创合伙人/代理三种模式×内地/海外拆分（6,413→7,504家，其中内地3,926→4,386、海外2,487→3,118）；TOP TOY 148→276（272家在内地）；集团GMV约304亿元≠收入；期后回购事项属期后，“除本年报披露外无其他重大事项”是期后事件的边界句 |
| us-release / us-txt | 微软 / 美股 | 消费/订阅与电话会角色 | M365 Commercial cloud +16%（调整上年同期2点期内收入确认影响后口径）vs reported +14%；M365 Consumer cloud +24%（up 22% in constant currency）——消费/订阅分开、constant currency 全局限定随局部事实；commercial RPO +84% 至 $678 billion≠当期收入；电话会区分 prepared remarks / Q&A，发言角色（Chairman&CEO、CFO、VP IR、analyst）决定陈述归属，non-GAAP 全局说明 |

## 缺样（→ acquisition_requests.json）

生物医药/CDMO 真实原文（临床阶段/里程碑/版税）、修订/补充版本对、8-K/6-K 容器+附件端到端、
真正制度/通知负例（cn-ir-policy 实为活动记录）、消费型软件队列指标（NRR/递延收入细节）文档、
募投变更/延期/终止公告、A股季报“业务验证进展”正例与稀疏负例成对样本。
