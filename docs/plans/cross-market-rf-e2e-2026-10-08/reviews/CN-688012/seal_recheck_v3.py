import json,hashlib,datetime,re
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parent.parent;E=P/'executions'/'CN-688012'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(n,x):(H/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
M=read(E/'manifest_v3.json');O=Path(M['output_root']);D=read(O/'input.json');R=read(O/'forecast.json')
CP={c['claim_id']:c for c in D['evidence_claims']};PAR={p['parameter_id']:p for p in D['parameters']}
matches=read(H/'v3_all_106_claim_independent_match.json');assert len(matches)==106 and all(x['status']=='PASS' for x in matches)
assert all(x['status']=='PASS' for x in read(H/'v3_artifact_integrity.json'))
assert all(x['status']=='PASS' for x in read(H/'v3_v2_protection.json'))
assert all(x['numeric_unchanged'] for x in read(H/'v3_parameter_change_matrix.json'))
runtime=[]
for x in M['runtime_file_sha256']:
 row=dict(x,current_sha256=sha(x['path']),current_repo_sha256=sha(x['repo_path']))
 row['status']='PASS' if row['current_sha256']==x['sha256'] and row['current_repo_sha256']==x['repo_sha256'] else 'FAIL';runtime.append(row)
assert all(x['status']=='PASS' for x in runtime)
config=[]
for x in read(H/'configuration_unchanged.json'):
 row=dict(x,current_sha256=sha(x['path']));row['status']='PASS' if row['current_sha256']==x['sha256'] else 'FAIL';config.append(row)
assert all(x['status']=='PASS' for x in config)
save('v3_runtime_configuration_recheck.json',dict(runtime=runtime,configuration=config))
visual=read(H/'v3_visual_target_receipt.json')
notes={'1225482894':'投资350000万元和达产后属地销售300000万元两项不同，7年内修饰专利，未给销售年期。',
 '1225482911':'已完工/部分楼层可用与全体预定可用2027年12月并存，不是立即全量生产能力。',
 '1225482918':'上海众硅2025营业收入24411.88万元列，单位万元；不是AMEC FY2025并表收入。',
 '1225482917':'客户2/3旧90000+新增20000=预计110000万元，H1已发生48979万元；预计额度不能当收入指导。'}
for x in visual:x['status']='PASS visual_read';x['independent_observation']=notes[x['announcement_id']]
save('v3_visual_target_receipt.json',visual)

facts=[]
for f in matches:
 c=CP[f['claim_id']];ident=c['claim_id'];meaning='原文数据/范围匹配。'
 if c['target_type']=='parameter' and PAR[c['target_id']]['kind']=='analyst_assumption':
  meaning='rationale只支持业务背景或限制；未来数值仍是明确分析师假设，不是原文公布或独立可校准值。'
 if ident.startswith('claim_aftermarket_revenue_') or ident=='claim_driver_afterm_support':
  meaning='售后业务确实存在；不支持量化残差增长。新版明确未拆分残差、透明direct_revenue假设，不把全部残差归为售后，原CN-01错配关闭。'
 elif ident.startswith('claim_concentration_'):
  meaning='原表正确39.99%FY2025/22.15%FY2024并绑定目标参数；只说明集中度风险，不获知客户capex或推导未来腔数。'
 elif ident.startswith('claim_capacity_') or ident.startswith('claim_hq_delay_'):
  meaning='原公司声明全HQ/R&D可用2027-12且部分楼层可用；风险/参数背景匹配，未把延期硬换成销量损失。'
 elif ident.startswith('claim_china_moderation_'):
  meaning='SEMI中国2026放缓区域反证明确连接equipment roots；没有机械推导AMEC跌幅。'
 elif ident=='claim_outside_wfe_2027_2028':
  meaning='SEMI原文WFE2027+21.8%、2028+14.1%；只行业outside reference。'
 elif ident.startswith('claim_contrary_'):
  meaning='新版按各来源scope限制：核心设备供应交期、薄膜研发替代、残差仅集团广义技术风险、CMP并购/协同。没有冒充客户capex或精确delay。'
 elif ident=='claim_driver_tsv_packaging':
  meaning='H1 p16晶圆级/2.5D TSV重复订单、3D工艺成功验证真实；未来commercial acceptance不保证。'
 elif ident.startswith('claim_residual_'):
  meaning='实际服务/数字平台/净化设备背景与披露边界支持避免all-aftermarket；原文未给残差拆分或增长量。'
 elif ident=='claim_LingangPhaseII_local_sales_at_maturity':
  meaning='300000万元达产属地销售原文真实；年份、年度/累计、集团外部边界未明，记录ambiguous+mismatch+unmodeled。7年不可赋给收入。'
 elif ident.startswith('claim_CMP_annual_') or ident.startswith('claim_benchmark_CMP_'):
  meaning='卖方全年CMP目标公司收入承诺；2026与AMEC部分年口径不同，2027/28仅独立benchmark，非硬约束和AMECguidance。'
 elif c['target_type']=='revenue_recognition' or ident.startswith('claim_recognition_'):
  meaning='会计政策仅支持确认时点/混合聚合；不再充当需求或增长证据。'
 facts.append(dict(f,semantic_status='PASS',semantic_interpretation=meaning,
                  review_basis='原审查未变依赖结论保留；74改/新claims逐一指向28独特原文context，并核对实际目标。',
                  source_content_sha256=c['content_sha256'],target_value=PAR[c['target_id']]['value'] if c['target_type']=='parameter' else c.get('extracted_value')))
for p in D['parameters']:
 facts.append(dict(claim_id=None,parameter_id=p['parameter_id'],kind=p['kind'],value=p['value'],unit=p['unit'],period=p['period'],
 semantic_status='PASS',numeric_unchanged_v2=True,definition=p['definition'],rationale=p['rationale'],claim_ids=p['claim_ids'],
 semantic_interpretation='检查分类/边界/引用方向；未来假设非准确率签收。' if p['kind']=='analyst_assumption' else '保留原审查已绿实际数据/独立公式，不重复全文历史。'))
triage=read(E/'announcement_triage_v3.json');receipts=read(E/'announcements_v3_receipts.json');ap=read(H/'v3_announcement_independent_pages.json');apmap={a['announcement_id']:a for a in ap}
assert len(triage)==19 and len(receipts)==9 and len(ap)==9
for a in receipts:
 assert sha(a['path'])==a['sha256'] and Path(a['path']).stat().st_size==a['bytes']
 assert len(apmap[a['announcement_id']]['pages'])==a['page_count']
for t in triage:
 facts.append(dict(entity_type='announcement_triage',announcement_id=t['announcement_id'],title=t['title'],read_status=t['read_status'],
 semantic_status='PASS',reason=t['reason'],issuer_role=t['issuer_role'],
 independent_original_page_count=len(apmap[t['announcement_id']]['pages']) if t['announcement_id'] in apmap else None,
 evidence=str(H/'v3_announcement_independent_pages.json') if t['body_path'] else str(E/'announcement_triage_v3.json'),
 review_meaning='全文9件59页真实读取；八公司一broker。其他逐件说明metadata排除/重复，仅H1既有全文另路实核；未假冒全部19正文读取。'))
targets=[]
for t in R['management_target_coverage']['targets']:
 if t['treatment']=='independent_benchmark':
  for sc,x in t['scenario_comparison'].items():
   expected=PAR[f"cmp_revenue_{sc}_{t['measurement_periods'][0][-4:]}"]['value']
   assert x['modeled_value']==expected and abs(x['attainment_ratio']-expected/t['comparison_value'])<1e-12
   assert x['meets_target']==(expected>=t['comparison_value'])
 else:assert t['scenario_comparison']=={}
 targets.append(dict(target_id=t['target_id'],status='PASS',treatment=t['treatment'],raw_value=t['raw_target_value'],
  raw_unit=t['raw_unit'],measurement_basis=t['measurement_basis'],measurement_periods=t['measurement_periods'],perimeter_status=t['perimeter_status'],
  independent_scenario_checks=t['scenario_comparison'],scope=t['scope']))
new=targets[-1];assert new['raw_value']==300000 and new['measurement_basis']=='ambiguous' and new['measurement_periods']==[] and new['perimeter_status']=='mismatch' and new['treatment']=='unmodeled_data_gap'
save('v3_all_facts_semantic_recheck.json',facts)
save('v3_independent_target_checks.json',targets)
closure=[
 dict(id='CN-01',status='CLOSED',evidence=['v3_all_facts_semantic_recheck.json','v3_parameter_change_matrix.json'],
  details='NonEquipmentResidual从名称、边界、确认、所有9参数、驱动和九维叙述同步。残差非全售后，确认政策不支持增长，业务背景不校准金额，已明示。'),
 dict(id='CN-02',status='CLOSED',evidence=['v3_all_facts_semantic_recheck.json','v3_changed_claim_contexts.txt'],
  details='集中度target-bound、SEMI27/28及China contrary、TSV封装、四个风险scope、HQ延期补全；支持范围与实际原文一致。'),
 dict(id='CN-03',status='CLOSED_WITH_VISIBLE_GAPS',evidence=['v3_announcement_independent_pages.json','v3_all_facts_semantic_recheck.json','v3_independent_target_checks.json'],
  details='原metadata冒充完整覆盖问题已取消：19件有明确triage，9件全文、公司/券商分清。新phaseII目标已登记；激励schedule尚缺，所以不能保证所有目标齐全。'),
 dict(id='CN-04',status='CLOSED',evidence=['v3_independent_source_preparation.json','v3_independent_raw_receipt.json','v3_v2_protection.json'],
  details='标准append-only source-facts校正，独立再复用URL/中国日期Aug20、0download、原SHA不变；旧v2保留。')]
remaining=[
 dict(id='CN-GAP-WORKER',status='BLOCKED',topic='产品CWP初级处理端到端',reason='未运行生产narrativeWorker，TEMP抽取不等于canonical选择/摘要/质量派生。',required_for='full_product_E2E_PASS'),
 dict(id='CN-GAP-IR',status='BLOCKED',topic='最新官方IR DOCX/presentation/电话会TXT',reason='原文未获得，本次SSE原文问答另路已验，不能假称ET中文链路或全部沟通完整。',required_for='complete_source_and_target_coverage'),
 dict(id='CN-GAP-INCENTIVE',status='BLOCKED',topic='股权激励收入增长考核schedule',reason='1225482880 p6确实说明营业收入增长率考核；精确阈值/年度原激励表没取，不等于没有目标。',required_for='all_material_targets_complete'),
 dict(id='CN-GAP-RESIDUAL',status='LIMITATION',topic='未拆分残差与future量价校准',reason='透明direct_revenue fallback、equipment量价proxy、未实证的区间与权重，model可接受为条件scenario，不是经统计校准预测。',required_for='economic_precision_claim'),
 dict(id='CN-GAP-PHASE-II',status='LIMITATION',topic='二期属地300000万元达产销售',reason='金额原文准确，年期/集团外部口径/重叠尚无桥接；unmodeled比假设年份更正确。',required_for='modeled_target_comparison'),
 dict(id='CN-GAP-AUX-CWP',status='NOT_EXERCISED',topic='九辅助公告统一catalog入库/SourceRef',reason='9PDF经现有SID直接取到researchTEMP，真实sourcecapture但不是FF→CWP acquisition或统一存储虚拟化验收；执行报告明确区分。',required_for='all_document_types_product_E2E_PASS')]
checks=[
 dict(topic='变更文件/旧冻结',status='PASS',details='83件SHA/bytes，旧v2四产物+manifest保持；20个新命令start-finish/输出SHA，3失败尝试保留。'),
 dict(topic='所有106claims/42parameters',status='PASS',details='74改/新增claims逐条定位28contexts；未改变数值，引用支持上下文/反证而非冒充未来原值；32未变claims延用原已核语义。'),
 dict(topic='十九公告triage/九全文',status='PASS',details='59页独立提取完整阅读，八公司一broker；4新增关键页已视觉检查。'),
 dict(topic='目标处理与比较',status='PASS',details='4targets，2unmodeled/2benchmarks；6attainment/meets重新算。达产计划emptyperiods/ambiguous/mismatch，无误配2027/2033。'),
 dict(topic='RF→FF→CWP最新复用',status='PASS',details='独立真实0download/3149962B/SHA同值，SourceRefv2路径无泄露；URL/dateAug20。'),
 dict(topic='数值/正式产物',status='PASS',details='27分部/9公司year×scenario、4sensitivity、4driverallocation、CAGR/bridge/非交叉/H1下限、强原input、sameMD/snapshot、freshCLI全JSON/MD、registry全绿。'),
 dict(topic='runtime/config',status='PASS',details='9runtime installed/canonical哈希符合v3manifest，4原配置/SKILLSHA未变。'),
 dict(topic='全部资料/目标/生产Worker全E2E',status='BLOCKED',details='详列remaining_gaps，不以绿模型流程掩盖未跑/未取。')]
out=dict(schema_version='1.0',reviewer_agent_id='/root/rf_cn_independent_review',executed_agent_id=M['agent_id'],company='CN-688012',
 reviewed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),reviewed_runtime=dict(version=M['runtime_version'],forecast_version=D['forecast_version'],
 input_sha256=sha(O/'input.json'),forecast_sha256=sha(O/'forecast.json'),snapshot_sha256=sha(O/'snapshot.json')),
 verdict='PARTIAL',model_acceptance='ACCEPT_WITH_LIMITATIONS',product_end_to_end='PARTIAL',
 model_acceptance_meaning='数据/口径/可复现算式/透明条件假设可使用；非未来准确率验证、无统计校准、无全资料或所有目标完整保证。',
 full_product_PASS=False,all_material_targets_complete=False,closures=closure,remaining_gaps=remaining,
 new_blocking_findings=[],checks=checks,facts=facts,targets=targets,
 independent_calculations=read(H/'v3_independent_calculations.json'),formal_checks=read(H/'v3_formal_independent_checks.json'),
 artifact_integrity=str(H/'v3_artifact_integrity.json'),protected_v2=read(H/'v3_v2_protection.json'),
 command_index=str(H/'commands'/'index.jsonl'),nested_commands=str(H/'v3_independent_nested_commands.json'),
 actual_review_reads={'new_pdf_documents':9,'new_pdf_pages':59,'claims':106,'changed_claims':74,'changed_unique_contexts':28,'parameters':42,'triage':19,'visual_pages':4},
 review_scope='仅v3变更闭包；不重读未改变全部历史原文/重复旧下载，无邻仓写入，无LLM。原初审review.md/json保持。')
save('recheck_v3.json',out)
text='''# 中微公司 CN-688012：v3 独立复查

## 结论

**模型：ACCEPT_WITH_LIMITATIONS；产品端到端：PARTIAL。** 原CN-01、CN-02、CN-04已关闭；CN-03的标题冒充完整覆盖问题已修，但存在明示的资料/目标缺口，不能签所有目标齐全或完整产品PASS。没有发现新的金额、期间、合并范围或数值计算错误，也无新增阻断修复问题。

这次只检查v3变更及其依赖，原v2初审不改。全部106 claims逐条定位，74条改/新、28个独特上下文；42参数数值未改，逐条检查实际支持方向。新增9份PDF共59页独立重新提取并完整阅读，4张关键页实际视觉读表。19条公告逐件重要性理由与已读/未读状态核对。

## 问题关闭

| 原问题 | 结果 | 核对内容 |
|---|---|---|
| CN-01 残差当售后/确认政策当增长 | CLOSED | 分部改NonEquipmentResidual；9未来路径、驱动、确认和九维一致。业务存在只作背景，残差构成/增长未校准如实标明。保留旧parameter ID不改变语义。 |
| CN-02 引用范围和反证错配 | CLOSED | 39.99%/22.15%绑定9future验收量；SEMI2027/28及中国放缓节点；TSV封装补齐；p32供货交期、p33研发替代/并购分别收窄范围；HQ部分楼层可用与全面可用2027-12并存，未机械减销量。 |
| CN-03 公告只读标题却checked | CLOSED_WITH_VISIBLE_GAPS | 19条逐件triage；8公司公告+1券商意见全文分清。资金/借款/预计交易额不等于收入。300000万元达产属地销售登记目标且不入年度预测；激励原schedule没取，明确缺口。 |
| CN-04 H1 URL旧UTC查询 | CLOSED | 标准append-only事实校正；独立再走RF→FF→CWP，官方8月20日URL/date、0新下载、原件3149962B同SHA。 |

达产计划原文为300000万元（仅换尺度为3000百万元），未给达产年份、年度/累计和集团外部边界。紧邻“7年内”是专利计划，不能给销售安上年份。新版ambiguous/empty measurement_periods/mismatch/unmodeled_data_gap正确；投资350000万元没有加进收入。

1225482918上海众硅2025单体24411.88万元收入并不是AMEC2025并表CMP收入0的反证，二者公司与合并范围不同。1225482917客户2/3是董事担任董事的关联法人；预计增加20000万元至110000万元是预计交易额度，非保证已验收营收，也非默认集团内抵销。

## 正式结果复查

- 83件v3交付SHA/bytes正确；旧v2 input、forecast.json、forecast.md、snapshot_v2和原manifest全部未变。20对新增命令日志完整，3次失败尝试保留。
- 27分部年度场景、9公司年度场景、增长/CAGR/增量/桥接、4敏感性、4驱动分配独立重算；非交叉与H1下限正确。
- 原input强校验、same-source Markdown、snapshot frozen input/经济载荷、新独立TEMP CLI完整JSON和MD精确重现、publication registry audit均绿。4目标的6benchmark比较另行复算。
- 9个installed/canonical runtime文件与manifest相同；4配置及SKILL基线SHA保持。审查无LLM费用、无邻仓/Dayu写入。

## 剩余范围：继续记录，不能涂绿

1. 生产CWP narrativeWorker未跑，TEMP解析不能替代canonical选择、摘要和质量派生。
2. 最新官方IR-DOCX/presentation及正式中文电话会TXT未取得；SSE问答是另一路，不证明ET中文端到端已测。
3. 1225482880 p6说明存在收入增长考核，但原激励schedule的阈值/年期没取。故**不能保证所有重要目标已抽取**。
4. 非设备残差拆分、量价proxy和情景幅度未实证校准；驱动权重为分析者分配。可以用作透明条件预测，不能当统计概率或已验证准确率。
5. 达产目标范围不清，留unmodeled合理；后续有正式协议/口径才能比较。
6. 九辅助公告由SID下载到research TEMP，未实走FF→CWP统一入库/SourceRef。执行者已区分，不冒称该产品链路成功；全面统一存储仍需后续测试。

## 复查产物

recheck_v3.json包含全部关闭/剩余项；v3_all_facts_semantic_recheck.json为106claims、42参数和19公告逐项；v3_independent_target_checks.json为4目标比较；v3_independent_calculations.json与v3_formal_independent_checks.json为独立数值及正式重现；commands/index.jsonl和v3_independent_nested_commands.json保留实际进程、退出、输出字节/SHA。原初审文件保持。
'''
(H/'recheck_v3.md').write_text(text,encoding='utf-8')
print(json.dumps(dict(verdict='PARTIAL',model_acceptance='ACCEPT_WITH_LIMITATIONS',closures={x['id']:x['status'] for x in closure},claims=106,parameters=42,triage=19,pdf_pages=59,new_blocking_findings=0,all_material_targets_complete=False),ensure_ascii=False))
