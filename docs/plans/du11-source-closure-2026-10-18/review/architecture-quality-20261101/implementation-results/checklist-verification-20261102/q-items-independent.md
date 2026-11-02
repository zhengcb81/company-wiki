# Q01–Q14 独立逐项核对（2026-11-02）

**原14项均找到当前工程处置：13项在定义范围完成，Q11有理由保留。真实C仍OPEN，另发现固定16MiB表示门遗漏，由ROOT接手；不签全项目完成。**

本核对读取原需求、当前源码/符号、测试责任、最终独审、Git祖先和精确发布CI收据，不以STATUS单独自证，也不把旧FAIL/暂停当最新。只写要求的两份报告，不改源/主PWF/历史收据/Git。

## 当前发布

CWP当前master bbbd3de46b6fc0c5995f78e28827c7215a298dab，origin/master跟踪同值；10767b86、ef3d92a2、runtime389a10fb均在祖先。389a10fb精确CI41450377163成功。HEAD相对该runtime工程目录差分：无。
StockWiki当前master e5a1be6523499ac1791805457f12229c98fbf10d 包含381811e5；历史无remote，只签本地主线并线，不冒已远端推送。
FF350cb39d/41450346468、RFe44c7e97/41444705227、invest9b68cc9b/41442479736均有成功收据。本次没有重新查GitHub，精确版本和证据SHA见JSON。

## 14项完整矩阵

|项|结论|要求及未闭边界|
|---|---|---|
|Q01|ENGINEERING_COMPLETE; REAL_ACCEPTANCE_OPEN|陌生行业完整经营陈述不因有限动词/对象词表被丢弃；可读资格与事件/量值/发行人证明分轴。 原70旧期待恢复；R5最终28唯一场景限定独审及精确完整CI通过，不借旧R3/R4局部PASS签全域。H1v4父链P2、新摘要/恢复/RF仍OPEN；POS不证明任意行业现实真伪。|
|Q02|ENGINEERING_COMPLETE; REAL_ACCEPTANCE_OPEN|实际阅读算法/数据/runtime依赖变化使真实缓存失效，不适用格式变化不误伤。 真实cache函数的PDF/text/data/runtime反例通过；不是任意动态Python依赖证明，新增跨边界算法需owner声明。新版真实付费artifact缓存恢复仍待C。|
|Q03|ENGINEERING_COMPLETE|精确公司查询不先受全库同文种20k计数拖累；保纠错/别名/冲突候选超集及最终语义。 15新候选例和最终owner反控已独审；旧库首次writer backfill/生产规模性能未测，不冒已迁移或全库零成本。|
|Q04|ENGINEERING_COMPLETE|空间增量归实际run；轮询不反复扫共享CAS；并发/崩溃不能降账或放大额度。 首审两个真实并发P2保留；R2独立5例和作者raw-v1 loopback通过。共享WAL不伪精确归run；旧floor是保守历史量，不是物理FS精确计量或生产吞吐基准。|
|Q05|ENGINEERING_COMPLETE_BY_RETIREMENT|去除旧parser-name全范围DELETE，不让一次性legacy prune删除当前引用证据。 没有重删生产span/原件或做完整恢复演练；保旧S5史料、现行只读inventory/vacuum，不承诺通用自动prune。|
|Q06|ENGINEERING_COMPLETE|CAS put现存对象及FileExists竞争分支都按expected_size+1有界验证。 小损坏/竞争/重复例及host验证已过；不冒任意大小OOM压力测试。WinError5为sandbox hardlink限制，未修改ACL/原子语义换绿。|
|Q07|ENGINEERING_COMPLETE_BY_RETIREMENT|退役硬机器目录复制及默认真实公司/原地清水印脚本，不依赖sitecustomize。 无需另造复制owner或“解锁”脚本；新采集走来源catalog。退役旧writer不代表所有历史脚本逐行重写。|
|Q08|ENGINEERING_COMPLETE_DEFINED_STATIC_SCOPE|架构测试用AST覆盖relative/qualified/alias/__init__/常量动态import；注释不误报，owner豁免不能basename绕过。 literal-import AST与已知root条件不是任意动态代码/全仓无硬编码证明；compat旧flag/bridge检查仍是有限历史规则，未夸成全部语义验证。|
|Q09|ENGINEERING_COMPLETE_LOCAL_MAIN; NO_REMOTE_CONFIGURED|StockWiki在读取期流式限制stdout/stderr并回收超额/超时进程树，避免全量缓冲。 381811e5已在当前StockWiki master祖先；历史无remote，不能称远端push/CI。独立2超额+孙进程marker和作者真实TXT端口已过，非全仓研究语义验收。新post-load16MiB另列，不混同原流式风险。|
|Q10|ENGINEERING_COMPLETE|纯SourceExport不强绑具体SourceVersionReader；writer不经高层reader构建身份。 替身backend/root relocation/坏bytes反控已有证据；新from_json16MiB是独立表示门遗漏，不是反向实现依赖未去除。|
|Q11|KEPT_BY_REASON|评估同次bytes重复SHA，只合并真正同owner热点；不删公开接收/跨时间复核。 不是所有重复CPU已消除；微观察不冒全链性能结论。将来证明同owner热点再局部优化。|
|Q12|ENGINEERING_COMPLETE_DEFINED_REFACTOR_SCOPE; REAL_ACCEPTANCE_OPEN|按原文材料、依赖闭合、准入与预算组合阶段拆责任，保单次准备和旧facade。 _candidates仍679行、prepare_native_materials约410行，不夸成所有复杂性消失；独审按责任边界/行为而非行数签。真实来源父链T4仍OPEN。|
|Q13|ENGINEERING_COMPLETE|reader CLI区分invalid_request与环境/存储unavailable，坏hash在catalog前验证且错误pathless。 改善诊断，不声称自动修复真实配置/存储；合法不可用拒绝没有改成功。|
|Q14|ENGINEERING_COMPLETE|正常scan/preview不依赖旧snapshot/伪两轮零diff；旧运维CLI退役，历史回放兼容。 兼容library/格式存在不是当前许可；没有误删合法source/narrative原子activation和恢复，也没有删历史assertion。|

## Q01

同prepared scope统一语法/上下文和text_fact/production fact；保原roles False/None；陌生具名范围/计划/定义可作为资料，weak目标/问句/完整金融句不借句法升级；资源缺失沿公开handler保持partial。

实现：src/company_wiki/source_catalog/narrative_source_passage.py — prepare_source_statement_scope:108, prepare_source_passage:356, _grammar_uncertainty:337；src/company_wiki/source_catalog/narrative_business_policy.py — prepare_reading_business_assessment:1116, detect_reading_business_fact:1023；src/company_wiki/source_catalog/narrative_operating_relations.py — SourceOperatingSession:138；src/company_wiki/document_understanding/statement_grammar/__init__.py — observe_statement:291。

测试责任：tests/unit/du11_production/test_source_readability_generalization.py；tests/unit/du11_production/test_source_semantic_axes.py；tests/unit/du11_production/test_source_preparation_axes.py；tests/unit/du11_production/test_source_argument_semantics.py；tests/unit/test_narrative_select_handler.py。

独审/证据：R6-source-contract-r5.md；R6-independent-ci-r5.json；R6-publication.json；Q01-rework-r4.md；Q01-rework-r5-integration.md；精确源码/报告SHA在JSON。

同Session/WorkBudget/memo保留；grammar unavailable/scope_limit不能伪报无业务或complete，unknown事实不升级。

## Q02

来源组合owner声明入口；literal-import闭包按实际bytes哈希并缓存AST，PDF table observations及grammar资源/runtime身份纳入；DU旧模块薄兼容，纯decision_dependencies不认识source实现。

实现：src/company_wiki/source_catalog/reading_recipe.py — algorithm_hashes:84, business_algorithm_hashes:115；src/company_wiki/source_catalog/narrative_decision_inventory.py — current_decision_trace:362, _versions:72；src/company_wiki/automation/narrative_generation.py — current_reading_decision_matches:632, ReadingReuseVerifier:513。

测试责任：tests/unit/document_understanding_selection/test_reading_recipe_closure.py；tests/unit/document_understanding_selection/test_reading_decision_inventory.py；tests/unit/du11_production/test_cache_identity.py；tests/unit/test_shared_reading_cache_precheck.py。

独审/证据：Q02.md；independent-A-r2.md；R6-owner-boundaries-ci.md；R6-independent-ci-r5.json；R7-RF-independent.json；精确源码/报告SHA在JSON。

partial inventory不判same，也不授权再买一次；可通过一次当前source重选与完整material比较证明等价。

## Q03

派生token索引+native SQL dirty triggers；writer同事务刷新；readonly含dirty/旧库SQL兼容不迁移；document_id稳定keyset+1 lookahead区分20k正好EOF。

实现：src/company_wiki/source_catalog/identity_candidates.py — identity_candidate_clause:187, request_identity_tokens:59, ensure_identity_projection:67, refresh_identity_projection:127；src/company_wiki/source_catalog/source_reader.py — _candidate_pages:151, _query_local:214；src/company_wiki/source_catalog/service.py — query_filing_candidates:232。

测试责任：tests/unit/test_source_identity_candidate_projection.py；tests/contract/test_source_version_reader.py；tests/unit/test_source_facts.py。

独审/证据：Q03.md；independent-B.md；independent-B-r2.md；R6-consumer-migration.md；精确源码/报告SHA在JSON。

实际相关候选20k预算和最终身份/期间/as-of保留；候选token不是事实有效或可用证明。

## Q04

原AUTO新增空间allocation账；实际put新增/复用量结算；短OS mutex覆盖admit/write/settle，已知量max单调；local-only snapshot避免双快照加回；poll force=False，私有目录至多5s采样，共享DB诊断。

实现：src/company_wiki/automation/narrative_run_store.py — account_storage_write:609, _admit_storage_object:637, _settle_storage_object:672, storage_bytes:582；src/company_wiki/automation/narrative_batch.py — BatchStorageBudget:1234, _storage_guard:1321, _BudgetedObjects:1368, _write_generation_owner:2136；src/company_wiki/automation/narrative_worker_factory.py — create_runtime:303。

测试责任：tests/unit/test_narrative_storage_ownership.py；tests/unit/test_automation_migrations.py；tests/unit/test_automation_migrations_v2.py；tests/unit/test_automation_migrations_v3.py；tests/integration/test_narrative_runtime_e2e.py。

独审/证据：Q04-Q06.md；independent-B-r2.md；Q04-Q06-seal.json；R6-consumer-migration.md；精确源码/报告SHA在JSON。

HTTP/解析锁外、pending未知占用不退款、原lease/outbox/AUTO账保留，未建任务/许可库。

## Q05

S5一次性清理已于Oct6完成，旧DELETE实现删除；API无I/O退休结果，CLI在config/selection/receipt I/O前退休，不新增许可文件。

实现：tools/legacy_storage/spans.py — run_prune_spans:10；tools/legacy_storage_retirement.py — main:35。

测试责任：tests/unit/test_maintenance_quality_remediation.py::test_completed_span_prune_never_opens_current_catalog；tests/unit/test_maintenance_quality_remediation.py::test_completed_prune_cli_never_loads_config。

独审/证据：Q05-Q07-Q08-Q13-Q14.md；independent-B.md；independent-B-r2.md；精确源码/报告SHA在JSON。

退休不靠keep_refs签收，人为授权不取代当前生命周期/事务范围。

## Q06

两分支统一read，不再read_bytes全盘读取损坏对象；复用新增0，创建返回实际bytes。

实现：src/company_wiki/source_catalog/narrative_artifact_store.py — LocalNarrativeObjectStore:153, put_with_usage:164, read:204, NarrativeObjectPut:148。

测试责任：tests/unit/test_narrative_storage_ownership.py::test_cas_existing_object_validation_never_reads_beyond_input_bound；tests/unit/test_narrative_storage_ownership.py::test_cas_reused_object_is_not_rewritten。

独审/证据：Q04-Q06.md；independent-B.md；independent-B-r2.md；精确源码/报告SHA在JSON。

实际size/SHA、atomic create-if-absent、fsync和失败临时清理保留。

## Q07

两脚本只打印退休并exit78；默认公司、物理路径、copy2/原地write实现均删除。

实现：scripts/copy_docs.py — main:8；scripts/clean_watermarks.py — main:8。

测试责任：tests/unit/test_maintenance_quality_remediation.py::test_obsolete_copy_and_cleanup_cli_retired_before_arguments。

独审/证据：Q05-Q07-Q08-Q13-Q14.md；independent-B.md；independent-B-r2.md；精确源码/报告SHA在JSON。

明确退休是去除无用功能，不是人工许可或环境变量审批。

## Q08

解析真实import和可执行root比较；精确相对owner路径；删除未用恒真/旧snapshot约束，真实当前树检查进现有Unit。

实现：src/company_wiki/source_catalog/architecture_gate.py — import_names:34, source_catalog_does_not_import_prohibited_modules:63, no_root_specific_hardcode:120。

测试责任：tests/unit/test_maintenance_quality_remediation.py::test_dependency_check_catches_import_forms_in_package_initializer；tests/unit/test_maintenance_quality_remediation.py::test_dependency_check_ignores_quotes_and_comments；tests/unit/test_maintenance_quality_remediation.py::test_nested_config_basename_cannot_exempt_root_conditional；tests/unit/test_maintenance_quality_remediation.py::test_current_source_catalog_has_no_research_imports；.github/workflows/ci.yml::Unit tests。

独审/证据：Q05-Q07-Q08-Q13-Q14.md；independent-B.md；R7-final-engineering-tests-independent.json；R7-final-closure.json；精确源码/报告SHA在JSON。

轻量Unit不膨胀为每commit全旧gate/E2E；诊断分数不拦正常业务。

## Q09

复用StockWiki自己已有bounded runner/进程树，limit+1即中止，保receipt/hash和deadline。CWP不反向提供私有进程helper。

实现：stockwiki/_source_reader_v2_transport.py — VerifiedOpenTransport:55, open_verified:114；stockwiki/_narrative_process.py — run_bounded:18；stockwiki/_narrative_process_tree.py — ProcessTree:11。

测试责任：StockWiki/tests/test_source_export_v2_bounded_transport.py；StockWiki真实CWP TXT verified-open/CLI既有E2E。

独审/证据：Q09.md；Q09-publication.json；independent-B.md；independent-B-r2.md；精确源码/报告SHA在JSON。

stdout来自显式reader-config，是实际读取预算；stderr256KiB也处在实际读取owner，不因常量单独判许可。depth64未证明有效拒绝。

## Q10

纯DTO/窄runtime-checkable Protocol；旧reader别名兼容；登记owner直接调用source_references。新进程-I/-S显式当前src并用catalog import firewall避免借editable旧树假绿。

实现：src/company_wiki/source_contract/source_version.py — SourceRef:23, VerifiedContent:44, SourceVersionPort:73；src/company_wiki/source_contract/source_export_v2.py — SourceExportBundleV2:65, build:99；src/company_wiki/source_catalog/source_references.py — query_source_reference:16；src/company_wiki/source_catalog/canonical_writer.py — CanonicalSourceWriter:257。

测试责任：tests/unit/test_source_contract_reader_port.py；tests/contract/test_source_export_v2.py；tests/contract/test_source_export_v2_cli.py。

独审/证据：ROOT.md；independent-A.md；R6-owner-boundaries-ci.md；R6-independent-consumers.json；精确源码/报告SHA在JSON。

接收实际bytes SHA保留，不用trusted标志或具体reader绑定省验证。

## Q11

公开Protocol backend可字段正确但携等长错bytes，独立接收SHA才能拒绝；小收益不引入可伪造trusted状态。

实现：src/company_wiki/source_contract/source_export_v2.py — SourceExportBundleV2:65, build:99；src/company_wiki/source_contract/source_version.py — VerifiedContent:44, SourceVersionPort:73。

测试责任：tests/unit/test_source_contract_reader_port.py::test_public_backend_cannot_attest_forged_bytes_using_correct_identity_fields；tests/unit/test_source_contract_reader_port.py::test_export_accepts_delegating_read_backend_without_concrete_inheritance。

独审/证据：Q11-disposition.md；independent-B.md；independent-B-r2.md；精确源码/报告SHA在JSON。

磁盘读、公开port接收、跨时间重开是不同信任事件；保必要实算，不制造信任注册/许可链。

## Q12

native_materials独占来源容器/闭合，不选budget winner/不IO；admission独立纯模块；facade注入continuity backend，selection继续唯一finalize/WorkBudget/Session。

实现：src/company_wiki/source_catalog/narrative_native_materials.py — prepare_native_materials:23；src/company_wiki/source_catalog/narrative_reading_admission.py — _admitted:20, _financial_only:12；src/company_wiki/source_catalog/narrative_reading.py — _prose_reading_packages:92, _candidates:101, select_reading_evidence:1152。

测试责任：tests/unit/document_understanding_selection/test_reading_native_material_mapping.py；tests/unit/document_understanding_selection/test_source_support_use.py；tests/unit/du11_production/test_source_preparation_axes.py；tests/unit/test_narrative_select_handler.py。

独审/证据：ROOT.md；independent-A.md；R6-independent-ci-r5.json；R6-T3-independent-r2.json；精确源码/报告SHA在JSON。

同scope预算/缓存/原始ID和既有回放保留，不为拆文件复制classifier或新增registry。

## Q13

缺参数/非法digest归blocked invalid_request；真实配置/IO/DB故障仍reader_unavailable，失败stdout不出原文。

实现：src/company_wiki/source_catalog/source_reader_cli.py — _digest_argument:39, _JsonArgumentParser:34, main:52。

测试责任：tests/unit/test_maintenance_quality_remediation.py::test_reader_bad_arguments_are_invalid_request；tests/unit/test_maintenance_quality_remediation.py::test_reader_bad_digest_is_invalid_before_database_access；tests/unit/test_maintenance_quality_remediation.py::test_reader_missing_configuration_remains_unavailable。

独审/证据：Q05-Q07-Q08-Q13-Q14.md；independent-B.md；independent-B-r2.md；精确源码/报告SHA在JSON。

必要参数/身份/真实I/O错误明确保留，无源字节泄露或新审批。

## Q14

scan按RootSpec.adapter_id；zero_diff_rounds丢弃仅留兼容参数；旧解码在compat；activation/runtime-policy等在config I/O前退休且隐藏。

实现：src/company_wiki/source_catalog/service.py — scan:152；src/company_wiki/source_catalog/scanner.py — scan_catalog:2045；src/company_wiki/source_catalog/compat_scan_rollout.py — ；src/company_wiki/source_catalog/cli.py — main:747。

测试责任：tests/unit/test_maintenance_quality_remediation.py::test_explicit_v2_preview_needs_no_rollout_rounds；tests/unit/test_maintenance_quality_remediation.py::test_current_scan_does_not_load_rollout_snapshot；tests/unit/test_maintenance_quality_remediation.py::test_historical_rollout_cli_retires_before_configuration。

独审/证据：Q05-Q07-Q08-Q13-Q14.md；independent-B.md；independent-B-r2.md；R7-core-implementation.md；R7-final-closure.json；精确源码/报告SHA在JSON。

dry-run零写、根配置有效性、CAS/事务/恢复保留，无epoch/reviewer/cohort日常人工签收。

## 新发现单列：R7-RESIDUAL-V2-WIRE-CAP

两个公开JSON入口 SourceExportBundleV2.from_json(raw: bytes) 与 StockWiki load_bundle(raw: bytes) 无max_bytes参数，原始bytes已在内存后还受固定16MiB顶帽。StockWiki真实CLI先Path.read_bytes，再load_bundle，后创建原件读取transport；该顶帽不受reader-config控制，与实际流式字节/超时预算是不同责任。

纯内存实际反例：合法exact-TXT原文16,777,233B、完整v2包16,779,115B、source/output/bundle SHA和locator一致；公开CWP from_dict接受，同一wire的两个JSON入口分别报exceeds read limit/bundle_over_limit（0.259s）。CWP当前只找到公开contract/CLI测试调用，不冒称全部生产下载受阻；StockWiki服务是活动caller。精确签名/5源SHA/完整小生成器/结果在JSON。ROOT已接手，待新源码冻结后另作独立增量审查。

Q09的显式stdout配置限额与第二receipt通道读取预算不是本项后置表示门，保留理由已分清。depth64计数未递增；deep structured_value探针本身不合exact-TXT合同，实际报ungroundable_span_shape，未据此造活动P2。首次大包fixture的semver1错误也保留，改为1.0.0后才得到真实结果。

## 未完成边界和过期文字

- H1v4实际12/12必需原文、101原生成员及完整收据不能代来源归属质量；独审仍有views25/28/65继承旧子标题的父链P2。按T4先根修/正向引介复验。
- 新runtime正式摘要、paid中断、same/cross零重复及同artifact真实RF参数/公式/报告/snapshot采用仍OPEN；原R4六issue和公司循环未完成。
- README/implementation开头仍是未实施/暂停/63失败恢复快照，STATUS.daily_feedback仍提167cases，findings的T3节仍说在途/H1未跑。ROOT应标历史或对齐CURRENT_STATUS；本核对没有改旧文件。
- Q12确已把native材料/依赖闭合与纯admission分开，但候选协调器仍长；不能只按行数否定，也不能称所有复杂性已消失。

## 本次验证与清理

没有重跑已绿Unit/完整focused/真实来源；没有收费、下载、原件读取/复制、DB复制、生产写入、索引初始化、commit/push。新探针仅内存生成数据，无临时文件/目录，只有本目录两报告写入。原初期失败和夹具错误均按版本保留。

原14工程处置可保留；ROOT还须关闭新16MiB遗漏、统一过期描述，随后继续T4→新真实C→公司循环，不能据此将整体目标标完。

补充：ROOT在本核对结束前已报告16MiB及额外PaidResponse262144B遗漏的TDD根修，54P/33P属于ROOT报告，最终7文件交另一独审。本报告保留BEFORE_ROOT_REPAIR原反例，不借该消息倒签新补丁通过。源码观测时已有这些已授权在途差分，工程结论绑定既有已发布祖先/收据；新变化SHA不冒旧CI通过。
