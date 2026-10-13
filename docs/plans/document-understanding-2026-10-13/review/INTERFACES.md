# DU2 三包增量数据与交接接口

这是实现规格，非许可文件。原 DU/1 保持冻结，既有来源验真继续由原责任层执行。本文件由 ROOT 维护；worker不改公共字段语义，缺字段在handoff记录。三个包可在当前主线之上独立完成，不需要import原DU三个分支。

## 1. 共同约定

- 所有可执行接口用JSON可序列化Mapping，纯函数、确定性、稳定排序，不读配置/目录/网络/时钟，不包含公司特判。
- 原件/source locator透传；测试片段用明确synthetic或真实短引文，不能伪造SourceRef。真实原件只读，引用SHA及本机bindings，绝对路径不进入可移植fixture。
- 数据中的事实类别为 required_business / disposition_context / correctness_if_emitted，只服务质量评价/阅读目标，不是权限。
- 字段未披露为null/unknown，不按模板造数。必要上下文指“如果断言该事实就必须同时保留”，不是要求每份文档都披露所有槽位。
- 原文不翻译。网页研究只作为策略依据；真正业务gold须核实完整原件/可定位正文，不能用搜索摘要建金标。

## 2. FAMILIES 数据（du2-family-spec/1）

每记录必填：schema_version、id、version、applies_to、recognition、sections、reading_questions、context_requirements、deprioritize、fallback、evidence_status、case_ids。

- id：稳定用途ID，例 sec_registration_business；不可含公司名。
- version：语义版本字符串，内容变动必须变化；ROOT导入后沿唯一profile内容摘要机制。
- applies_to：{regimes:[str], forms:[str], family:str, purposes:[str], modifiers:{extent:[full|summary|unknown], revision:[original|amended|supplement|unknown]}}；carrier/language可选，不把其混进用途。
- recognition：{positive:[{signal:{kind:literal_phrase|metadata_equals,value:str,field:null|str},location,reason}],counterexamples:[str]}。literal_phrase只提交短语，不交regex/DSL；metadata_equals的field限title/regime/form_type/declared_kind/mime_type/language/revision。location为metadata/cover/toc/body/attachment，不写公司页码/证券代码。普通字面比较规范化NFKC/空白/casefold，不擅自简繁翻译；识别组合逻辑仍由ROOT现有router执行。
- sections：[{role,aliases:[str],heading_path:[[str]],priority:1..3,questions:[str]}]；heading_path从父到子，每层数组内别名OR，层间层级AND，空数组表示无层级限制。role复用DU/1角色，新role只作提议；保留CN/HK/US合法语境，层级用于10-Q Part重复Item。
- reading_questions：[str]；描述需保留的信息，非要求LLM回答一切。
- context_requirements：[{when:always_for_assertion|quantity_emitted|project_emitted|explicit_condition_present,slots:[str],missing_behavior:unknown|partial|deferred,reason:str}]。reading_questions/summary_focus/reason都是说明文字，不按代码执行；复杂语义只交说明给ROOT，不自创可执行条件语言。
- deprioritize：[{content,unless}]，软降权；禁止所有数字/所有财务章硬删除。
- fallback：{unread,ambiguous,no_business}，描述如何进入现有generic/缺口/合法skip，不新增审批。
- evidence_status：{design:verified|proposed,real_samples:[case_id],missing_shapes:[str]}。

输出目录下 index.json 为 {schema_version:"du2-family-index/1",records:[相对JSON路径],coverage:[{shape,spec_status:implemented|proposed,evidence_status:real|synthetic_only|missing,integration_status:not_integrated,case_ids,gaps:[str]}]}。有真实样本与规格完工是独立状态。记录同role别名可组合，不写第二registry loader/路由器。ROOT在单一profiles中接入规格；运行时不同时读deliverables与旧代码两套规则，导入后deliverables仅留版本化设计/证据，后续运行规则维护在唯一registry。

## 3. FACETS 数据（du2-facet-spec/1）

必填：schema_version、id、version、business_questions、applicable_mechanisms、positive_evidence、required_context、confusions、absence_rules、summary_focus、case_ids。

- business_questions：[str]，如“新产品处在哪一商业化阶段、证据何在”。
- applicable_mechanisms：[generic|subscription|consumption|store_network|manufacturing|biopharma|cdmo]；只是内容修饰，不是股票行业分类器。
- positive_evidence：[{description,unit_kinds:[DU/1语义包类型],signals:[str]}]；关键词仅提示。
- required_context：[{assertion:str,slots:[subject,product,project,geography,period,role,modality,stage,quantity,unit,denominator,condition],required_when:always_for_assertion|quantity_emitted|project_emitted|explicit_condition_present,missing_behavior:unknown|partial|deferred,reason:str}]。按断言条件要求，文档没有某属性时允许不输出；assertion/reason仅说明，不交自创DSL。
- confusions：[{source_meaning,wrong_assertion,why_wrong,required_context_slots:[str]}]。
- absence_rules：[str]，涵盖未披露/管理层未答/否定/未读的区别。
- summary_focus：[str]，原语言业务问题，不产生投资结论。

输出 index.json 为 {schema_version:"du2-facet-index/1",records:[相对路径],coverage:[{facet,mechanism,spec_status:implemented|proposed,evidence_status:real|synthetic_only|missing,integration_status:not_integrated,case_ids,gaps:[str]}]}。不要设计公司实体词表、财务模型或新研究状态。运行时归属同第2节。

## 4. 两数据包共用 case（du2-reading-case/1）

必填：case_id、kind=synthetic|real_excerpt、source、observation、expectations。

source = {sample_id,source_sha256,origin,local_binding_key}；synthetic的sha可null。origin保存已核出处/资料属性，不含密钥。真实读取用未提交bindings.local.json，从sample_id映射实际路径，优先用母计划sample_manifest定位；不复制原件。

observation = {metadata,units:[{unit_id,locator:null|str,anchor:null|{physical_page:null|int,line:null|int,exact_quote:str},page,text,role,hints}]}。unit_id仅case内引用键；locator必须来自公共解析器，否则填null并给页/行+exact_quote，ROOT将quote anchor解析为正式定位。不伪造看似正式的SourceRef。真实原文摘录每source所有case合计≤8KiB，源允许更少引用时遵从其限额。full original SHA固定版本，摘录不是独立原件。

expectations = {routing_notes:[str],facts:[{id,objective,importance,any_support_sets:[[unit_id]],must_preserve:[str],must_not_assert:[str]}],disposition,not_evaluated:[str]}。

- 支持集外OR、内AND；一个项目的主体和建设期不能分别拿两个不相干项目拼接。
- disposition为read/generic_read/eligible_skip_after_read/needs_source/unread；它是case期待行为，不能靠记录本身放行生产。
- 反例可加 mutations:[{id,change,expected_failure,reason}]；数值反例不强制原模型必须抽该数字。
- ROOT将这些映射到同一个du-gold/1，不允许数据包写新的recall检查器或复制整份baseline输出充gold。

两数据包自动测试只查结构不变量：枚举/引用、明确的必要槽位、支持集完整、正反例变更字段、合法空值、组合别名不丢。语义反例的生产执行写 execution_status=NOT_RUN_ROOT_INTEGRATION，不声称本包已证明引擎理解正确。需要可执行槽位反例时，case可增 candidate_claim:{subject,modality,quantity,unit,period,condition,…}（均可null）及expected_missing_slots:[str]，只做明确结构字段检查，不自制自然语言蕴含判断器。真实含义对照集中在C节点。

## 5. LAYOUT 纯函数（du2-layout-input/1 → du2-layout-hints/1）

公开入口：company_wiki.document_understanding.layout_hints.derive_layout_hints(observation: Mapping, *, limits: Mapping|None=None) -> dict。

输入：{schema_version:"du2-layout-input/1",source_ref:{…opaque…},pages:[{page,width,height,units:[{unit_id,ordinal,locator,text,bbox:[x0,y0,x1,y1],font_size:null|number,font_weight:null|str,kind,upstream_hints:{…}}]}],coverage:{opaque_pages:[],deferred_pages:[]}}。

- unit_id/locator已由调用方创建并绑定原件；辅助函数不能分配新来源locator。bbox单页同坐标系；PDF/HTML/PPT差异由现有前端适配，输入不允许单位混用。可缺字体/几何，缺失不等于零。
- 只处理已读的布局证据，不直接打开PDF/HTML/PPT或OCR；真实测试可用既有parser/PyMuPDF只读采集显式probe IDs，必须标测试映射，不冒充生产locator。
- 恢复表列需足够细的块/span几何及到原文定位的映射；一个unit包住整行而无格子坐标时无法证明列归属，应返回NEEDS_UPSTREAM_GRANULARITY/partial，不按空格虚构格子。ROOT负责前端保留细粒度span并映射原locator；C节点分别报告“充分输入下能力”和“当前生产输入是否满足”。

输出：{schema_version:"du2-layout-hints/1",source_ref,unit_hints:[{unit_id,heading_level:null|int,text_column:null|int,confidence:high|medium|low|unknown,basis:[str]}],groups:[{group_id,kind:heading|column_lane|table_region|table_row|caption|footnote,parent_table_id:null|str,member_unit_ids:[str],required_context_unit_ids:[str],cells:[{member_unit_ids:[str],row:null|int,column:null|int,row_span:null|int,column_span:null|int}],confidence,basis:[str]}],relations:[{from_group_id,to_group_id,kind:header_for|caption_for|footnote_for|continuation,confidence,basis:[str]}],reading_order:[{page,ordered_unit_ids:[str],confidence,basis:[str]}],coverage:{processed_unit_count,deferred_unit_ids,opaque_pages,deferred_pages,complete},diagnostics:[{code,unit_ids,detail}]}。

text_column仅表示正文分栏；cells行列为表内0基坐标，不混用。表行/表注归属已存在的table_region ID，未知留null；没有可靠表格结构的组cells=[]。header/caption/footnote关系从上下文组指向被解释组，continuation从前组到续组。reading_order是可选阅读视图提示，不修改原ordinal；仅纳入有支持的已读unit，无法排序的明确diagnostic而非丢弃。组内member顺序按此视图，视图缺失时按原ordinal。两相邻表的表头/脚注隔离必须测试。

- groups只是结构提示，不算新事实，不输出投资含义或从像素猜数；保留单位/期间/表头/脚注的依赖，歧义就unknown。
- 同source成员引用必须存在；顺序稳定；跨页只在明确表头/列几何等证据下延续，并保留页差；不因两个金额相同强行配对。
- 默认limits：max_units=50000、max_groups=10000、max_work_units=2000000；调用方可收紧。按页/邻接排序，避免全量两两比较。工作计数实际累计，超限partial/deferred，不能提高外部时间/像素/OCR/模型预算。
- 不创建父包init，不改DU/1；ROOT将输出映射到既有hints/relations/section识别，统一消除旧重复column/heading推断。

## 6. 三包所有权与交接

| owner | 可写 | 不可写 |
|---|---|---|
| DU2-FAMILIES | docs/plans/document-understanding-2026-10-13/review/deliverables/families/**；.planning/du2-families/** | 其他策略数据、任何src、旧DU三包、共享计划 |
| DU2-FACETS | docs/plans/document-understanding-2026-10-13/review/deliverables/facets/**；.planning/du2-facets/** | 同上；不可改FAMILIES |
| DU2-LAYOUT | src/company_wiki/document_understanding/layout_hints/**；tests/unit/document_understanding_layout_hints/**；tests/fixtures/document_understanding_layout_hints/**；.planning/du2-layout/** | 任何旧parser/adapter/root模块、其他卡、共享init/config/CI |
| ROOT | 共享接口、原DU接收、原benchmark/profile/structure/production接线、总计划 | 不覆盖新卡在制路径 |

各包自建 own PWF；只写 .planning/du2-<lane>/handoff.json、handoff.md，格式：{schema_version:"du2-handoff/1",lane,base_sha,implementation_commits,worktree,owned_paths,status,public_interfaces,interface_deviations,A_B_C:[{node,command,exit_code,elapsed_seconds,result_path}],real_samples,synthetic_cases,known_gaps,resources:{model_calls,paid_usd,persistent_bytes,scratch_peak_bytes},raw_preservation,scratch_restore,next_root_action}。

handoff可在实现commit后再提交一次以准确记录SHA；不要求expectedHEAD许可。保持正常git hooks，提交本分支停止，不合主线/push主线/安装技能。缺真实样本可交诚实gap，不能把synthetic或结构PASS当模型语义PASS。

## ROOT接收的兼容扩展（2026-10-13）

布局输出同du2-layout-hints/1新增唯一feature_version=1.1.0，用于实际layout内容版本；不是来源locator或许可。upstream_hints.geometry_granularity=row|block|table_region明确聚合框，不能造cells。PDF同一次dict snapshot尺寸/字体与bbox同frame，原text/ID/locator/raw parser版本不改。公共pipeline和summary同schema/1 additive feature_version1.1.0；summary layout_coverage与原生来源覆盖分开。facet运行返回confusion_checks={risk:why_wrong,required_context_slots}和applicable_mechanisms作为指令，不发送case/source_meaning/wrong_assertion示例数。策略局部hash、source原文实物化和预算不放松。
