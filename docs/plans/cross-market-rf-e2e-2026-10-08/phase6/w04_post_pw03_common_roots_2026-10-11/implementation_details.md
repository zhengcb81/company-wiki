# W04 实施细则（全新独立方案；没有实施源码）

## 输入事实与裁决

all12-index SHA=a811d4fc08972f1331c60294fc22f24cea5068d408b2ccda07694b6595c7e49e，12 JSON/MD 的24实际SHA逐项匹配；229 checks/89新 findings。旧 coverage SHA=bf523eaa37bb28b1e414ae3e6d6c09e38e0ba2d65638bf25ef6776fb134df64a 的157 keys（155 company +2 expert）逐项读取；155新复验原行全部对应，无改旧status。coverage.json 246 keys，duplicates/unmapped=0。原 absent review_attempt 保存null并带 absence，不根据MD或source attempt_id捏字段。未来真正review可由ROOT明确赋attempt，不能补造旧event。

P7已STOP技术 JSON SHA259ed822fdc747e3a364e58a1bf08055c5906b4f13062ac10ef9d71528407f21、MD SHA8b013e286d3d24b3d370f80a05c1d85bb5040852d5ad1aaa8910b7b1de56c766均实核。三项technical和W01–W08另列auxiliary，不膨胀246。P7 source18a52f16/docs40b38103已真实交接；源码/安装仍未切。已有96/59接受和W11 unchanged引用既有收据，无重跑、无改37既有断言。

本轮专家及只读helper 0 GET/provider/model/new费用。USD20/2M沿母账413778tokens、334463µUSD+FX2764，余1586222tokens/$19.662773，旧 unknown hold不核销。03:06:57原执行截止不延长；晚本地独立审查另记录真实时间。所有历史partial/unknown与failure不重写。

## 独立状态和工作分配

20共因的不同责任层落实到7个排他包。每个key在coverage有一个primary root/owner work package/test，其他root只表示依赖或 residual。原PASS仅签其原症状；当前consumer residual由新key施工，不倒签旧source。原NOT_RUN即使generic工程已接受也不改成研究PASS。2expert signed adjustments/role reconstruction收实际owner证据；不重复改assurance。

并发≤3。Wave1：WP01 CWP叶、WP03 RF叶、WP05 audit叶在公共字段卡已冻结后可并行；WP03 v3分支等WP01真实producer输出后串行整合。Wave2：WP02 CWP语义残余和WP04 FF命名原因并行，ROOT WP07接shared runtime/config/purpose与install seams。WP06研究规范只改RF skills文档，新真实authoring数据归ROOT未来ownedattempt（不是旧run）。G1/G3完成并独立审查后集中安装；G2→G4按预算实施。任何跨包修改都交ROOT串行收敛。

## 公共字段/原生接口
## 已冻结公共接口与类型

- SourceRef 2.0 六字段：schema_version:str="2.0", document_id:str, source_id:str, content_sha256:str64, byte_size:int>0, mime_type:str。无物理路径。CWP exact open 是原字节身份责任层；消费者不重建第二身份证明。
- SourceMetadataValue 已有 source_class:str, title:str|null, document_kind:str, language:str, declared_language:str|null。四字段老包仍可读；可选第五键保留真实语言声明，未知多键仍按版本契约有限拒绝。
- RF request/source prep 现有 prepare_registered_source_result(candidate:dict, as_of_date:str, company_wiki_catalog_config:Path, timeout_seconds:float=30, source_reader_receipt_version:str="2.1")，返回 {schema_version:"source-preparation-result/1",source:RevenueSourceRecord,filing_fetch:null,narrative:null}。pinned 非财报不伪造 FY；unpinned latest 保留按能力有界发现语义。
- 投影 compact 是新设计，不是已存在 API：NarrativeSubjectRef/1={schema_version:"narrative-subject-ref/1",kind:"official_json",item_key:str,subject_sha256:str64}；item_key 应与现 PROJECTION_ID_PREFIX+SHA 关系一致。NarrativeRef/3={schema_version:"narrative-ref/3",artifact_version_id:str,artifact_sha256:str64,byte_size:int>0,generation_sha256:str64,subject_ref:NarrativeSubjectRef}。reference-request/3={schema_version,subject_ref,generation_sha256}；read-request/3={schema_version,narrative_ref,as_of_date:str|null,expected_issuer:现约束dict|null}。请求、reference输出、read收据、evidence-list收据均≤16384B；read bundle保持实际1310720B body限制。
- projected receipt/3 只含compact ref、asof/observed_at、locator/parent count、lineage hash、selection/quality/replay标量；完整父链和每个原pointer仍在已pin bundle body。CWP load_projection(catalog,projection_id)→既有 `_verify_projection_from_parents` public exact-open/rebuild。无新 registry；不得把投影伪装成single raw SourceRef或把JSON pointer强塞raw loc:v1坐标。RF必须新增显式 projected DTO分支，保留原v1有限读取，不默默混类。
- EvidenceSpan 真实字段 source_id, locator, coordinates, raw_text/structured_value, parser_name/version, output_sha256, parse_status, quality_flags。原text-offset SourceExport2不支持PDF span，PDF/PPTX/投影证据走verified narrative transport。完整原文引用、摘要claim角色、RF numerical facts互为不同对象。


### Source qualification

保持 SourceRequest fiscal_year:int|null/fiscal_period:str|null、query_local仅匹配明确值。period_known属于periodic kind的资格，不对所有资料强要FY；capture_ready保持bool，仍需capture完整、HTTPS、published_date以及periodic需要period_known。最终exact SourceRef open验证字节/identity/asof。不要用“非金融”词删除deck的guidance数字。已pin材料先沿现RF prepare_registered_source_result，不让它陷入财报only fallback；其验证支持真实nonperiod null。只有 unpinned latest 才进入能力匹配、限额明确的发现，不把latest金融发现一律改成query_local，避免回归latest-filing语义。FF request exact仍尊重财报合同；边界采用typed入口，不魔改FY/kind。

### Purpose/output

真实配置在 llm.generation_policy:dict[provider,dict[purpose,dict[str,str]]]，先 general 再 purpose；保持canonical purpose="narrative"和现resolver；可选--purpose:str仅在实际工作流需要其它policy时从configured wrapper接到model_options_from_config及可观察记录，effective wire改变进入现有generation/cache SHA；用途标签单独可观察，标签改变而prompt/model/endpoint/thinking/reasoning/maxoutput相同不强制新cache或重复收费。thinking/reasoning_effort等只取当前选定provider配置及实际adapter支持，不猜新模型或私设token上限。当前 main/worktree config无该映射，PW03 actual --llm-provider及request已封存；ROOT检查实际任务配置并做tmp配置，生产config不写穿。没有配置或adapter不支持返回具体命名诊断，不新增许可JSON。

本地截断夹具先证明bounded final/usage/finish原因；真实已计费annual/deck/call只有未来新bounded大节点成功、完整原语言summary、verified public read、RF消费才可验收。空final保持死信和费用，不自动收费重试，不提高全局cap掩错。旧完整supplier response缺失永久保留unknown，当前response字节/sha观察不是已经保留完整响应body。

### Audit opt-in controls 与冻结

P7 outer envelope决定 requested/effective cap，native正文由native owner负责enforcement。adapter只读取声明的形状：FF acquisition_limits.max_bytes:int>0,timeout_seconds:finite>0,max_cost_usd:decimal string>=0；CWP profile/resource_caps及actualgeneration config；RF普通业务输入无resource字段观察为unknown。输出 requested/effective/observed/owner-enforced四层，未知不把outer当native执行。禁止递归扫业务金额/profile字符串或公司特判。

money0合法：P7只修money finite>=0（bool拒），其他尺寸/token/time严格>0。builder frozen record expected SHA应传至既有freeze_command_inputs流式拷贝边界，在digest结束与原source stat检查同一次逻辑中比 expected；不一致named input failure并child_started=false，再由现capture错误记录落地。不要先额外hash或改老W11默认语义；legacy无expected时行为相同。consumed tamper仍由现observed_input_integrity核后态，原失败优先级不改变。

### Audit真实状态与用量

document_status_join.join_status_index现仅检查artifact/locator字符串，不能证明目标真实存在或result对具体document。新增owner可注入bounded located-result resolver，在已有capture/index根读取指定JSON pointer和限定result，不读取整个资料湖、不任意执行。真实表需 request→call→document/source→具体result pointer；result不存在/类型不符/跨source复用均diagnostic。call transport0和business failed/gap/unknown独立。one call multi-doc cost一次，operation/newdownload/wirebytes与旧全部历史分别保留；未观测usage/invoice null、lower_bound不变known。不为成绿补0。

W01–W08吸收为诊断/authoring方法：纯quote/value/unit/period/actor/definition核验；source namespace fact dedup/duplicate_of/version；实际step_ledger 15steps+6A/step8 halves与call/input/output绑定；producer/source/generation历史；限定已消费数字的denominator与unverified清单；A10无共识就无beat。它们不产生research authority或新的全局hard-block许可层。明确native无效输入可在owner局部named拒绝，diagnostic quality_status始终not_evaluated。

## RF经济研究合同：未来assumption允许，量级仍要解释

当前native input schema_version=3.9，parameters字段 parameter_id/kind/value/period/definition/scenario/dimension/unit/time_basis/source_ids/claim_ids/rationale/currency/scale；period_flow另有period_start/end。operating_research/1 已有 inventory、observations、calibrations；不另造第二研究数据库。calibration已有 calibration_id/status/scope/observed_period/source_claim_ids/counterevidence_claim_ids/observed_range/conversion_formula/output_unit/scenario_input_parameter_ids/scenario_output_parameter_ids/rationale/limitations；用现字段绑定真实DAG。

明确区分4类支持：原文已读事实；机制/政策/历史量级；未来明确assumption及公司范围转换；外部/未执行/未知。source出未来预测可以是reference case，不能说future actual。observed_range是已可核参考范围；未来选值来自清晰转换/商业推断，可以非null、可以低confidence；没有范围时不造上下限或status verified。native支持诊断不因旧FY25 subtraction在FY26桥中祖先日期不同就机械拒绝，亦不要求所有日期等于预测年。

最少经营桥按原资料先少自由度：需求/数量/净价mix/交付验收/收入确认/控制口径；aggregate fallback可合法，但对物质增量做独立挑战。CN FY25设备10527/1240=8.489516百万元/销售腔只是mixed realization proxy，FY25生产1660、库存1010不构成可用cap；面积和全球WFE不直接生公司订单。CMP 1.29190208是真May31–Jun30贡献，可把集团H1报表Jan1–Jun30和贡献measurement窗口分别表达（新schema可选扩展由ROOT收口，或现definition/rationale明确）；不能强迫period_start都同source日、stake×总收入、机械7/12。2027/28全年持续控制假设下已无购买前月份，但内部抵销仍需桥。

HK逐游戏/广告/支付云/社交Others角色，Arrows归Marketing、FTBcompute constrained和付费意愿可挑战幅度；GMV/tokens/时长不是收入。财务确认定义不是正向增长机制，Ximalaya407已included不重复新增。最新filing日Aug25后的公告窗口明确，May18事实可真却不能签窗口checked。低基高不是概率区间，0.95共同折扣是illustrative而非经济floor。

US八现有产品不重叠，财年06-30与CY市场季度明确。RPO总684000×约30%=205200属于expected timing参照，不是floor；商业678000×30%=203400与之重叠不能相加，mean2.3yr为commercial。Q1公司89.85–90.95B和Azure CC44–45%非全年直接年化，M365 reported/CC/adjusted及FX，Search gross/netexTAC分别映射。30M paid seats是期末不是平均，50M GitHub users/40M registered不是billable；预览不是GA。CN/HK已有recognized金额不再乘第二确认率；US原72null诚实但任务仍未完成，新assumption可填，经少参数桥、三年低基高和真实DAG cross-check验证。

shared压力以真实共同需求/算力/资金/客户暴露进入数量、价格、确认、延期/catchup/cancel，不能加27单敏感性。RPO/AR回款延迟不等于收入取消。缺订单或cloud commissioning量就用显式有界分析师假设和缺口，不能造GPUcap、内部reserve比例或恢复概率。研究审查判断经济论证，工程只保证公式/lineage。

## 快照 native 契约、精简与交付

实核HK native snapshot-v2.json 2283328B，header.forecast_schema_version=3.7；input_document.schema_version=3.9、forecast_result.schema_version=3.9，engine4.2.1。create_snapshot只取常量FORECAST_SCHEMA_VERSION，是身份元数据差异；旧数值独立复算正确。新builder取真实输入/结果 schema_version并验证一致、兼容engine，然后identity/snapshot_id/registry保持一致。历史冻结ID/3.7header不可重写；validator对旧版可给diagnostic和recorded-compatibility策略，不以此宣称金额错或篡旧注册锚。新严格snapshot与旧read策略显式版本隔离。

write_new_json可选择native compact serialization（标准JSON separators保持UTF-8+newline）或owner新增compact flag；这产生新的真实native artifact/ID与registry，不拿distinct projection充旧native。max_final_bytes在实际序列化写出前/过程中测，超限保持具体failure，不删除字段/摘要研究来压体积。renderer仍从同publish JSON生成；forecast目录相邻TRUST_BOUNDARY.md说明source untrusted、input binding、partial status、information date，并MD实际链接。US无formalartifact需先nativevalid research input，不补假报告。

## 物理留存、MAX_PATH、CAS、恢复与cleanup

原run目录、locator和失败历史不变。深evidence/requests/attempt/... MAX_PATH实遇可扩展物理路径读取，不是文件缺失。future runtime使用短owned TEMP（ROOT选择真实可写短绝对根）和平坦内容寻址档案，PWF只存清单引用，不把执行fixtures嵌几十层计划目录。路径长度由native所属filesystem/audit内部存储处理，无全局路径许可层。

immutable input bytes CAS cas/<sha>.json一次原子write-new，不第二registry；每call consumed/<call-id>.json独立普通副本，绝不hardlink mutable到shared CAS。每call manifest保留原path、logicalref、CAS sha、byte_size、argindices、actualcaptured/consumed integrity及producerSHA。相同源要测unique bytes和actual retained physical bytes两类；scope persistent counts实际duplicates+日志+新原件+registry/index，scratchpeak按实际观测，RAM无观测null。已有105副本理论去重30220885B不是已经减少的空间。

HK新HTTP两原件目前唯一明确原bytes在TEMP；evidence/hk_raw2_retention_plan.json列精确path/SHA/size/sidecar及HTTPcall，合计788213B，本专家只hash这2指定原件及2sidecar、没有整湖hash。execution/source-read抽取JSON不是原bytes，报告/MD/SHA引用也不是保存。不得删唯一原件。

ROOT清理顺序：1冻结cleanup前baseline/git/config与owned根边界；2在短持久owned artifact root平坦保存2原bytes+exactsidecar，分别verifySHA和524112/264101B，保留旧SourceRef/URL/日期/request/tool IDs，封存migration receipt；3以tmp新source_catalog.yaml映射只读CAS目录、独立tmp catalog重建/scan sidecar，公共describe/open重现原六字段Ref和元数据，关联当前original catalog/version/official receipt，不凭sidecar自行改变原资格；4原catalog/AUTO/WAL/SHM状态按既有owner closure保存必要replay与版本映射，读取immutable只读，不专家checkpoint；5实际public replay成功+持久bytes完整+receipt封存后才可按baseline处理本task ownedTEMP；6精确核resolved target在owned boundary，生产raw/Dayu/邻仓WIP不动。仍有唯一raw或独有AUTO恢复必要状态则TEMP保留并解释，不能为声称空间通过删证据。

审计CAS archive是证据保留，不是生产source lake迁移；baseline测试目录恢复和immutable审计证据保留分别结账。源rawread-only old32refs保留路径，不能把Dayu整目录copy/hash。历史old files不移动；未来短存储只迁移newowned bytes。清理receipt含deleted_owned_paths、retained_evidence/CASRefs、raw2 exact mappings、before/after stats、catalog replay outputs、remaining_unknowns。不复制全旧审查报告。

## 大节点验收与退出

TDD完整条目见test_matrix.md，每包已复制自身RED/GREEN规格。ROOT做G1/G3工程核心public路径与独立技术审查后集中source/install/skill版本同步；配置purpose的G2再用真实配置有界新执行；G4三公司原需求新attempt及12独立研究审查。先工程闭包再消耗真实费用，不对每文档/小节点追加人工许可。

版本diff/日志/旧WIP和installed快照由ROOT集中收口，执行前后实际gitstatus/configdoctor仅有配置变更才需要，无修改受保护原件。新失败保留exactinput/command/usage/final/unknown、新scope实际deadline，不复用旧期限。预算不足或来源externalgap具体说明partial，完成可行路径而不偷改研究目标。各worker只写自身leaf/test/docs与ownednewattempt，STOP交真实SHA。专家本包交接完成即停写。


## 命名 request 拒绝的明确新增 sibling 契约

实读 FF scripts/ff_provider_cause.py 的 filing-upstream-cause/1 为六键 exact闭集 {schema_version,operation,code,provider_started,usage_complete,retry_scope}，不能加入任意field_path破兼容。拟在失败envelope增加可选 request_diagnostic:{schema_version:"filing-request-diagnostic/1",reason:str closed enum,field_path:str closed path}，由 FilingFetchError 可选 typed属性在 validate_request 抛出时生成，不反向解析任意错误字符串。初始枚举按四实际拒绝冻结：exact_requires_fiscal_year / latest_forbids_fiscal_year / latest_reuse_requires_acquisition_limits / acquisition_limits_invalid；路径限定 fiscal_year、acquisition_limits 及 max_bytes/timeout_seconds/max_cost_usd。普通request_error旧code和retry=false不改；无新属性时旧unknown不补造。FF WP04负责生产与精确校验，RF WP03排他负责 scripts/filing_upstream_cause.py 和 scripts/filing_fetch_client.py 只读/传可选sibling，不拓展旧six-keycause或copysecret。audit WP05消费typed sibling诊断。测试用sealed四失败实际原requests，extra未知reason/path拒且原0provider/usageunknown保持。


## G5 未参与修复的泛化验收（原卡要求，尚未执行）

G4原CN688012/HK00700/USMSFT新executor完整15steps+四独立审查通过或明确partial之后，ROOT按母账真实剩余额度准备 A300750、HK00175、USCOST（没有用作修复fixtures）的新source/method验证；随后NVDA及pool loop有界实测。每个stage具独立actualdeadline/plan/profile、source kind matrix与latestwindow、现model配置effectivewire、原件reuse-first/零重复下载、publicsource/narrative→RF实际消费、nativeforecast/render/snapshot、真实预算和环境/持久/最终空间、ownedTEMP恢复/CAS持久引用。未经执行维持NOT_RUN，不以3公司fixture/137smoke/全suite绿签泛化。若剩余成本/时间不足，ROOT说明具体partial及未执行项，旧母账hold不重置，不把同一美元分配给并行多包。


## Capture/CAS 进一步明确的兼容接口（新设计，未实现）

保留旧 freeze_command_inputs(directory,command,inputs,max_bytes,argument_indices=()) 语义：128-file边界、argv ambiguity/index-binding、无implicit scan、frozen_path/consumed_path为实际物理path。拟新增 keyword-only expected_digests:Mapping[int,tuple[str,int]]|None（key为原command argv index，value为builder expected SHA/byte_size）、retention_mode:str="legacy"、blob_store:AuditBlobStore|None、deadline:float|None。legacy默认无expected参数零行为变化；P7 opt-in composer由实际builder record的request_sha256/request_bytes/input_argv_positions形成预期映射，在现freeze streamed exact snapshot digest完成时比同representationSHA及size；不额外预hash，不由HTTP/providerSHA代请求SHA。具名input_snapshot_expected_sha256_mismatch且child_startedfalse。

三个对象严格分开：source_bytes=原件；frozen_blob=调用准确输入；consume_workcopy=CLI可改工作副本。新的opaque FrozenBlobRef={schema_version:"audit-frozen-blob-ref/1",sha256:str64,byte_size:int>=0,blob_key:"auditblob:sha256:<fullsha>"}。audit空/invalidUTF8输入也可完整CAS保存，不能复用SourceRef positive-size校验或把它登记有效source。opt-in row增加frozen_ref，不能把opaqueURI塞旧frozen_path。唯一resolver `open_frozen(ref)->verified stream/bytes`, `materialize_workcopy(ref,attempt,suffix)->owned private file`, `seal_attempt(refs,observations)`复用现attempt/event/capture，无第二DB。shared CAS writablepath不直接给child；任意可写CLI默认private ordinarycopy，不hardlink。若将来新增immutableCLI模式，adapter需证明纯读取契约且持WindowsREAD/noWRITE/DELETEshare lease到child与postcheck结束，否则仍privatecopy；ReadOnlyattribute不是保护证明。

CAS shortdurableownerroot/fullSHA.blob。向owned xb staging逐块写/hash/cap/fsync，比这次exactbytes expected后no-replace publish；已有同名目标bounded lockread验size/hash才reuse，损坏明确corruption不覆盖。并发EEXIST重验；禁止os.replace覆盖已commitblob。fstat前后/同size+mtime只能变化诊断，不证明不存在竞争。no-replace commit link+unlink仅限内部ownedCAS发布，不将CAS和childworkcopy硬链接。

opt-in新的failed-input-envelope先独占分配attempt，再bounded freeze scope/deploy/template原bytes后parse/build；badJSON、control mismatch、builder mismatch完整原输入可各自pinnedCAS，修正版另attempt。overflow partial只声明partial/limit，不冒充完整sourceSHA。legacyfreeze失败cleanup不改；opt-incleanup仅删已知owned uncommitted staging/private copies，已commit pinned失败输入/unique原件/sealedrefs保留。cleanup异常作secondary cleanup_pending，原超时/拒绝优先级不覆盖；rollforward依existingmanifest/event发布封存。

当前max_input_bytes仅logical输入一次总量，不等于物理peak。新opt-in使用现scope retained/peak/scratch预算reservation，不全湖scan。保守peak至少既有owned allocated+新uniqueCAS staging+并发privateconsume+最大logs+结果/atomic暂存+所属SQLiteWALSHM+finalizationreserve。记录logical_reference_bytes、unique_content_bytes、apparent_file_bytes、allocated_bytes；WindowsfileID/volume区分hardlink实际分配，无法观察allocated就null或明确保守reservation，不能uniqueSHA当physical空间省掉。freeze chunk/publish/prelaunch/postcheck同一monotonic stage deadline，childtimeout=remaining；现只process.wait timeout未覆盖freeze的缺口在opt-in修，deadline耗尽nochild且具体stage。CASwhole-file只能消exactSHA重复；含全文但其他JSON字段变化仍各存大JSON。未来native已有SourceRef/FrozenBlobRef可由adapter在消费边界解析，禁止事后改旧builder bytes。

所有immutable raw/manifest/export/request历史exactbytes/hash保持。SourceRef无path；SourceVersionReader按root_id+relative_path重新验字节，newownedreplaycatalog可重映location，不改doc/sourceID/URL/retrieved_at/期间/asof/collector/HTTP事实。SourceManifest.original_path严格且verify_file用它，不能将旧manifest改CASpath：独立replay_locations映旧logiclocator+sourceidentity→CAS/root，原manifest留下，旧需要originalpath的consumer经boundedadapter或compatmaterialization。被hash引用的冻结DB留一份exactbytes；working/newreplayDB用一致sqlitebackup/事务重建且新SHA实际不同，不能活WAL裸copy或fake同hash。extract text只derived，不替PDF/HTML。上述适用于全部ownednewsource，HKraw2只为实际不可删反例。

增量有意义TDD：旧59/96保留；builder后变更前launchfail；stream同size替换/mtime恢复；CAS已存在corrupt/并发publish；child改privatecopy旧frozen可重开；badJSON/修正两refs不覆盖；logicalcap与physicalpeak分别越界nochild；cleanup异常主错不变可恢复；freeze耗尽deadline nochild；HTML/PDF exactrawreplay与originalmanifest locator兼容；SQLite一致备份SHA不伪装历史DB。避免另跑旧fullsuite/六probe。


## Actual configured purpose 与 equivalent-generation cache（只读支援已STOP）

当前main config.yaml llm.generation_policy absent，SHA2f4df37c3d39ef380caf476b6b678949a1e4b7604bdb95b73b0033804209c589；frozen model-purpose-diagnosis.json SHA4d859763e00b1cdd1ba6fc6ddf369b8f3f1f3a123d092c3ee5392a6e558ff83c当时为null，不能把拟disabled当actual。Config.generation_options默认general；只支持thinking/reasoning_effort overlay，不支持purpose-specificoutputcap，不发明此字段。configured有限wrapper未传purpose，目前实际固定narrative，可新增显式purpose参数/可观察记录，但同wire不新cache。SDK/urllib config-backed generationresolver已有，explicitprovider无Config latentpolicy路径不在此次冻结legacywriter扩修范围。

现 raw generation modelfields对 thinking=None/temperature=None/reasoning_split=None 与 omitted产生不同SHA，而HTTP/projection有效wire相同；reasoning_effort=None已有历史省略身份。WP07共享canonicaleffective-generation投影，normalize可选null/omitted同effectivewire且保留旧省略manifestSHA，不重写旧generation/ledger；新真实wire thinking/effort/maxoutput变化才miss。T24=仅purpose变化effectivewire相同hit；三optionalnull/omittedhit；actualthinking/effort/outputcap变化miss；旧artifact读取仍沿原generation和显式compatmapping，不以强行重新算旧SHA让旧artifact消失。不创造第二权限标签/registry，不从label或policy诊断推provider已执行。


## ROOT已准备的未来施工baseline

ROOT实际已准备RF clean隔离47f497ad9dee9dc47f66fca37016e9ba6b6b6f33；FF clean tree正常ff至e1e3ad8679e21264258e48006786fbf01a6991bd。此为ROOT已给baseline，不宣称专家新安装验收。canonical密钥及ownerWIP不触；leaf只从这些cleanbaseline隔离进行后续排他源改。CWPdocs21a8d20/源116a39d8正常主线push，137smoke已由ROOT接受，无重复跑。


## 第一版排除不必要新系统及 inventory 边界

ROOT最新裁决：第一版只有immutableCAS+privateworkcopy执行与收尾清理，保留legacy默认；不实现Windows immutable-CLI lease新系统、不将裸CASpath交child。上文lease仅记录未来契约条件，无当前施工/TDD义务。canonical固定narrative接线已有效，actualpolicyabsent是配置事实；explicitthinking/effort/maxoutput既已正确入generationidentity，不写缺key。真正新增NULL效率RED独立auxiliary，三technical项独立auxiliary。246company/expertfinding主inventory =157old+89new；aux TECH-P7-001/002/003共3与CONFIG-EFFICIENCY-NULL-001共1均未计入246，不合并报249/250主findings。配置缺policy已属于RC05，不新增duplicatefinding。
