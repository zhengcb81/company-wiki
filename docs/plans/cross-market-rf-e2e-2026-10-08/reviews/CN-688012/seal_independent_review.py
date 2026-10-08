"""Seal independent CN audit; writes only this review directory."""
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE.parent.parent
EX = PLAN / 'executions' / 'CN-688012'
def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))
def save(name, obj):
    (HERE / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
M = read(EX / 'manifest.json')
OUT = Path(M['output_root'])
D = read(OUT / 'input.json')
R = read(OUT / 'forecast.json')
MATCH = {f['claim_or_parameter_id']: f for f in read(HERE / 'all_claim_original_match.json')}
CP = {c['claim_id']: c for c in D['evidence_claims']}
PARAMS = {p['parameter_id']: p for p in D['parameters']}
after_ids = [p for p in PARAMS if p.startswith('aftermarket_revenue_')]
unit_ids = [p for p in PARAMS if p.startswith('equipment_units_') and p != 'equipment_units_2025']
contra_ids = [c for c in CP if c.startswith('claim_contrary_')]
bad = {f'claim_{p}': 'CN-01' for p in after_ids}
bad['claim_driver_afterm_support'] = 'CN-01'
bad.update({c: 'CN-02' for c in contra_ids})
bad['claim_outside_wfe_reference'] = 'CN-02'
bad['claim_driver_films_packaging'] = 'CN-02'

findings = [
 dict(id='CN-01', severity='P2', category='semantic_rationale_and_residual_perimeter',
      description='九个非设备残差路径和 aftem_support 驱动仅绑定年报 p174 备件/劳务确认政策。政策证明何时确认，不能证明安装基数、需求或重复服务增长。1857.63826811m 是非设备残差，未拆出的其他业务也可能在内，不能把其全部增量归因为备件服务。',
      paths=[str(OUT / 'input.json'), str(OUT / 'forecast.md')],
      claim_ids=[f'claim_{p}' for p in after_ids] + ['claim_driver_afterm_support'],
      parameter_ids=after_ids, driver_ids=['afterm_support'], evidence_ids=['e_afterm_support'],
      coverage_ids=['research_coverage:demand'],
      reproduction='将以上 claims.excerpt 与独立年报 p174 完整上下文比较；对照 annual p48/p53/p65、H1 p19/p23，不把混合残差当公开纯服务分部。',
      requested_fix='在新 forecast_version 中引用实际售后业务/已售设备背景，明确只是方向性支持；保留未测装机量/attach rate/服务进度的 data_gap。将驱动及叙述限定为未拆开的非设备残差，或为纯售后归因提供分部范围证据。路径可以保留透明假设，但不能把会计政策充当增长证据。'),
 dict(id='CN-02', severity='P2', category='claim_scope_and_counterevidence_binding',
      description='客户集中度实际正确但没有对应 checked claim；WFE claim 只摘2026而节点扩展到2027/28和中国放缓；四个 contrary 节点共享 H1 p33 却同时声称客户 capex/延期；films_packaging 的摘录只涵盖薄膜，未涵盖标题中的先进封装。',
      paths=[str(OUT / 'input.json'), str(HERE / 'all_claim_original_match.json')],
      claim_ids=['claim_outside_wfe_reference', 'claim_driver_films_packaging'] + contra_ids,
      parameter_ids=unit_ids,
      driver_ids=['core_etch_acceptance', 'films_packaging', 'afterm_support', 'cmp_ramp'],
      evidence_ids=['outside_wfe_reference', 'e_films_packaging'] + ['contra_' + x for x in ['core_etch_acceptance', 'films_packaging', 'afterm_support', 'cmp_ramp']],
      coverage_ids=['research_coverage:customers', 'research_coverage:industry_market', 'research_coverage:policy', 'research_coverage:technology'],
      reproduction='原文 annual p219=39.99%/22.15%；SEMI 2026-07-14原文 WFE 下一段=21.8%/14.1%、区域段=China moderate；H1 p32=供应/政策等风险，p33=并购/R&D；H1 p16/17另有TSV/封装上下文。77条摘录存在不等于77条结论全部获支持。',
      requested_fix='为集中度增加真实 checked 的 target-bound claims；SEMI 扩展/拆分完整年份及中国区域 claims，将区域放缓作为 equipment contrary node。按每个驱动实际适用范围拆出风险或收窄原结论；为封装补真实上下文或收窄名称。禁止仅把新引用塞到 source 列表而不绑定目标。'),
 dict(id='CN-03', severity='P2', category='communication_coverage_overstatement',
      description='material_announcements_since_last_filing 标为 checked，但19项只读元数据；关于私募基金进展及募投项目延期的原文尚未打开。H1及9月问答不能代替这些公告。',
      paths=[str(OUT / 'input.json'), str(EX / 'recent_announcements_receipt.json'), str(EX / 'skill_step_matrix.json')],
      claim_ids=[], parameter_ids=unit_ids,
      coverage_ids=['management_communication_coverage:material_announcements_since_last_filing'],
      document_ids=['1225582793', '1225482911', '1225482916'],
      reproduction='recent_announcements_receipt 明确 metadata only；原 input 的该类别结论承认 bodies 未开但 status=checked。',
      requested_fix='为19条标题分别记录重要/不重要的理由，读取涉及业务或产能时间的公司官方全文（先1225582793、1225482911；1225482916区分公司公告和核查意见）。确认目标/产能是否影响年度路径后更新目标与假设；取不到则有真实失败记录并标 not_available/明确gap，不能保持全覆盖 checked。'),
 dict(id='CN-04', severity='P3', category='source_url_timestamp_diagnostic',
      description='H1公开日已纠正为中国日期2026-08-20，source_url 的 detail 查询仍带 UTC误转的2026-08-19 16:00；provider id 与官方PDF SHA完全一致，不构成金额/身份错误。',
      paths=[str(OUT / 'input.json'), str(HERE / 'actual_independent_chain.json')],
      claim_ids=[], parameter_ids=[], source_ids=[D['sources'][1]['source_id']],
      reproduction='对照 independent official_pdf_current_sha_checks 与来源URL查询日期。',
      requested_fix='可通过正常 source-facts 校正为实核的官方PDFURL或中国日期detailURL，保留旧收据；无需重下原件。')
]

facts = []
for c in D['evidence_claims']:
    f = dict(MATCH[c['claim_id']])
    f.update(source_id=c['source_id'], quoted_original_excerpt=c['excerpt'],
             excerpt_sha256=c['excerpt_sha256'], original_byte_sha256=c['content_sha256'],
             semantic_support_status='FAIL' if c['claim_id'] in bad else 'PASS',
             status='FAIL' if c['claim_id'] in bad else f['status'],
             finding_id=bad.get(c['claim_id']),
             review_meaning='摘录匹配与目标含义分开；rationale_support 不验证未来数值。')
    facts.append(f)
for p in D['parameters']:
    attached = [CP[c] for c in p.get('claim_ids', [])]
    failing = [c['claim_id'] for c in attached if c['claim_id'] in bad]
    if p['kind'] == 'derived_fact':
        values = [PARAMS[x]['value'] for x in p['input_parameter_ids']]
        independent = values[0] - values[1] if p['formula'] == 'x0-x1' else values[0]/values[1]
        note = '独立公式重算；残差继承设备披露舍入，单位收入仅混合proxy。'
    elif p['kind'] == 'analyst_assumption':
        independent = p['value']
        note = '值来自输入，独立核对分类、口径与范围；不表示审查员验证未来数值为事实。方向性材料不能唯一确定假设。'
    else:
        independent = p['value']
        note = '原件完整表头/单位/期间独立复核，关键表格视觉检查通过。'
    facts.append(dict(claim_or_parameter_id=p['parameter_id'], entity_type='parameter', kind=p['kind'],
      source_locator=[c['locator'] for c in attached] or {'formula':p.get('formula'), 'inputs':p.get('input_parameter_ids')},
      independent_value=independent, unit=p['unit'], period=p['period'],
      status='FAIL' if failing else 'PASS', evidence=[str(OUT/'input.json')] + [MATCH[c['claim_id']]['evidence'] for c in attached],
      claim_ids=p.get('claim_ids', []), finding_ids=sorted({bad[c] for c in failing}),
      definition=p['definition'], review_meaning=note))
for h in D['historical_revenue']:
    facts.append(dict(claim_or_parameter_id='history:'+str(h.get('year')), entity_type='historical_revenue',
      source_locator='2025 annual PDF p25 comparative consolidated table', independent_value=h,
      unit='CNY million', period=str(h.get('year')), status='PASS',
      evidence=[str(HERE/'annual2025_independent_pages.json'),str(HERE/'visual_table_render_receipt.json')]))
for t in D['management_targets']:
    normalized = t['raw_target_value']/100
    facts.append(dict(claim_or_parameter_id=t['target_id'], entity_type='management_target',
      source_locator='2026 H1 PDF p53/177', independent_value=normalized,
      unit='CNY million', period=t['target_period'], status='PASS',
      evidence=[str(HERE/'half2026_current_independent_pages.json'),str(HERE/'visual_table_render_receipt.json')],
      review_meaning='卖方约定的目标公司全年合并收入，非AMEC管理层集团guarantee；2026与部分年并表范围不同。'))
for r in D['research_coverage']:
    affected = [f['id'] for f in findings if 'research_coverage:'+r['dimension'] in f.get('coverage_ids', [])]
    facts.append(dict(claim_or_parameter_id='research_coverage:'+r['dimension'], entity_type='research_dimension',
      source_locator=r['source_ids'], independent_value=r['conclusion'], unit=None, period=D['as_of_date'],
      status='FAIL' if affected else 'PASS', evidence=[str(OUT/'input.json')], finding_ids=affected,
      review_meaning='九维均检查；FAIL表示引用/范围缺口，非否定全文所有正确事实。'))
for r in D['management_communication_coverage']:
    status = 'FAIL' if r['category']=='material_announcements_since_last_filing' else 'BLOCKED' if r['status']=='not_available' else 'PASS'
    facts.append(dict(claim_or_parameter_id='management_communication_coverage:'+r['category'], entity_type='communication_category',
      source_locator=r.get('source_ids',[]), independent_value=r['conclusion'],unit=None,period=r.get('checked_date'),
      status=status,evidence=[str(OUT/'input.json'),str(EX/'communication_coverage.json')],
      finding_ids=['CN-03'] if status=='FAIL' else [],
      review_meaning='not_available 是本次原文获取缺口，不是证明原文不存在；metadata不能等价正文完整覆盖。'))
for r in D['growth_driver_tree']['drivers']:
    affected = sorted({bad[c] for e in r['evidence_nodes'] for c in e['claim_ids'] if c in bad})
    facts.append(dict(claim_or_parameter_id='driver:'+r['driver_id'],entity_type='growth_driver',
      source_locator=[CP[c]['locator'] for e in r['evidence_nodes'] for c in e['claim_ids']],
      independent_value=r['thesis'],unit=None,period=r['horizon'],status='FAIL' if affected else 'PASS',
      evidence=[str(OUT/'input.json'),str(HERE/'independent_calculations.json')],finding_ids=affected,
      review_meaning='权重和增量计算PASS，结论范围单独审查；分配权重属于分析师归因假设。'))
for s in D['sources']:
    facts.append(dict(claim_or_parameter_id=s['source_id'],entity_type='source',source_locator=s['url'],
      independent_value={'sha256':s['capture']['snapshot_sha256'],'published_date':s['published_date']},
      unit=None,period=s['published_date'],status='PASS',
      evidence=[str(HERE/'official_pdf_current_sha_checks.json')] if s['source_type']=='regulatory_filing' else [str(HERE/'live_official_ir_check.json')] if s['source_id']=='amec_sse_results_qa_20260910' else [str(HERE/'web_open_review_receipt.json')]))
for x in read(HERE/'independent_ir_identity.json')['selected']:
    facts.append(dict(claim_or_parameter_id='official_IR:'+str(x['id']),entity_type='company_reply',
      source_locator='SSE activity40766 id'+str(x['id']),independent_value=x['content'],unit=None,
      period=x.get('crtTime'),status='PASS',evidence=[str(HERE/'independent_ir_identity.json'),str(HERE/'live_official_ir_check.json')],
      review_meaning='精确companyId145565+guestCompanyName中微公司+688012过滤；全文中文读取，问句传言不作公司事实。'))
facts.extend([
 dict(claim_or_parameter_id='independent:CMP_purchase_date',source_locator='H1 p176',independent_value='2026-05-31',unit='date',period='2026H1',status='PASS',evidence=[str(HERE/'visual_table_render_receipt.json')]),
 dict(claim_or_parameter_id='independent:CMP_postpurchase_income',source_locator='H1 p176',independent_value=1.29190208,unit='CNY million',period='purchase date to2026-06-30',status='PASS',evidence=[str(HERE/'visual_table_render_receipt.json')]),
 dict(claim_or_parameter_id='independent:H1_actual',source_locator='H1 p7/p33',independent_value=6691.28732767,unit='CNY million',period='2026H1',status='PASS',evidence=[str(HERE/'half2026_current_independent_pages.json')]),
 dict(claim_or_parameter_id='independent:CustomerA2025',source_locator='annual p219',independent_value=39.99,unit='percent',period='FY2025',status='PASS',evidence=[str(HERE/'visual_table_render_receipt.json')],review_meaning='真实正确，但输入缺target-bound checked claim，见CN-02。'),
 dict(claim_or_parameter_id='independent:CustomerA2024',source_locator='annual p219',independent_value=22.15,unit='percent',period='FY2024',status='PASS',evidence=[str(HERE/'visual_table_render_receipt.json')]),
])

save('web_open_review_receipt.json',dict(tool='web.run', independent=True, observed_tool_call_id='turn250view0',
    checked_at='2026-10-08',url=D['sources'][2]['url'],source_published_date='2026-07-14',
    actual_open_lines=215, support={'line167':'Global WFE2026+23.1%,143.9B','line168':'2027+21.8%,2028+14.1%','line181':'China2026moderation'},
    conclusion='真实独立primary打开；不能将WFE机械代入AMEC增长。'))
save('facts_full.json',facts)
checks=[]
def check(id,topic,status,files,details):
    checks.append(dict(id=id,topic=topic,status=status,evidence=[str(HERE/f) for f in files],details=details))
check('A1','执行artifacts/log pairing','PASS',['artifact_integrity.json','command_integrity.json'],
      '344 artifacts SHA/bytes正确，73命令成对、16个非零尝试保留；84Python启动/84退出/39spawn。早期日志没有kernel-wide trace，不作完整系统调用保证。')
check('B1','真实CN下载及复用','PASS',['actual_independent_chain.json','annual_independent_raw_receipt.json','half_independent_raw_receipt.json'],
      '执行日志记录RF→FF→CWP→SID真实H1新下载1；审查独立再次RF→FF→CWP两份reuse_only，各download_calls0，打开原件SHA一致。下载caps40MiB/180s/$0.00传递。')
check('B2','虚拟化SourceRef与company/period/date','PASS',['actual_independent_chain.json','official_pdf_current_sha_checks.json'],
      'SourceRefv2仅ID/hash/size/mime；consumer通过producer实读；annual2025/H12026、688012，中文原件；公开日中国日期H1Aug20。两份官方HTTP200PDF实际全流SHA相同。')
check('B3','CWP生产Worker/narrative全流程','BLOCKED',['actual_independent_chain.json'],
      '本次只TEMP确定性PDF解析，未运行生产Worker或发布叙述派生；生产parser/LLM调用计数null仍未知。不能声称完整初级处理已验收。')
check('B4','ET中文电话会能力','NOT_APPLICABLE',[],
      'CN未实调ET，当前工具无已验证CN文本覆盖；正式电话会原文not_available；SSE公开问答是另一路，不能冒称FF→ET验收。')
check('C1','金额/单位/并购及合并范围','PASS',['facts_full.json','visual_table_render_receipt.json'],
      '全42参数/77claims/3historical/3targets检查；重点6页实际PNG视觉检查；1240腔非设备机器，800海外累计非年度量；CMP64.69%不乘收入。280/430/580m卖方全年目标不当AMEC部分年指导。')
check('C2','77excerpt匹配','PASS',['all_claim_original_match.json'],
      '77/77摘录与独立原件完整上下文一致；文本存在不代表rationale支持目标。')
check('C3','每claim语义/因果及反证','FAIL',['facts_full.json'],
      'CN-01/CN-02：10个残差增长/驱动claims和6个扩展范围claims需要修正。未来值全部假设，direction支持不能校准区间。')
check('C4','九维及六类沟通','FAIL',['facts_full.json','independent_ir_identity.json','live_official_ir_check.json'],
      '九维六类均枚举。SSE195回帖精确8公司回复，29预征集精确1公司回复，独立live557100bytes同SHA；最新material公告checked只metadata，CN-03；IR-DOCX原文缺口保留。')
check('D1','27segment/9company/4sensitivity/4allocation','PASS',['independent_calculations.json'],
      '全部年度每场景计算/recognized/bridge/growth/CAGR/noncrossing/分配重算；H1未机械年化；sensitivity分数正确。')
check('D2','正式validator/render/snapshot/registry','PASS',['formal_independent_checks.json','independent_fresh_cli_reproduction.json','publication_registry_independent_audit.json'],
      '原input strongvalidator，exactMD，snapshotv2冻结input及经济载荷；独立TEMP CLI完整JSON/MD完全相同；修复tuplekey误报后的registry auditRC0。不把旧registry误报算预测错误。')
check('D3','confidence','PASS',['formal_independent_checks.json'],
      '组件和65.59226677110698、medium、历史actualobservations0正确；这是结构/流程评分，语义缺口意味着不能解释为经济准确率。')
check('D4','backtest futureactual','NOT_APPLICABLE',[],
      'as-of尚无FY2026–28完整actual，没有拿预测假冒历史实绩。')
check('D5','原件/配置/费用/隔离','PASS',['configuration_unchanged.json','official_pdf_current_sha_checks.json'],
      '四份配置/SKILL哈希未变，producer当前原件hash未变；审查无LLM/$0公开接口；只写审查目录与ownedTEMP，未动Dayu等邻仓。已授权新下载原件在producer，保留不清理。')

matrix = read(EX/'skill_step_matrix.json')
step_findings = {'0':['CN-01','CN-02'],'1A':['CN-03'],'1B':['CN-02'],'4':['CN-01'],'6':['CN-01','CN-02'],'6A':['CN-01','CN-02'],'9':['CN-01','CN-02']}
for step in matrix['steps']:
    name=step['step']
    status='BLOCKED' if name=='CWP-worker' else 'NOT_APPLICABLE' if name=='11-evaluate' else 'FAIL' if name in step_findings else 'PASS'
    checks.append(dict(id='SKILL:'+name,topic='RF技能步骤'+name,status=status,evidence=step['artifacts'],
       details={'executor_detail':step['detail'],'independent_finding_ids':step_findings.get(name,[]),
                'interpretation':'FAIL为证据覆盖/语义范围，数值计算是否正确见D1/D2；未跑不写PASS。'}))

review = dict(schema_version='1.0',reviewer_agent_id='/root/rf_cn_independent_review',company='CN-688012 中微公司',
 reviewed_at=dt.datetime.now(dt.timezone.utc).isoformat(),executed_agent_id=M['agent_id'],
 reviewed_runtime={'engine_version':'4.1.0','result_schema_version':R.get('schema_version'),
 'input_sha256':sha(OUT/'input.json'),'forecast_sha256':sha(OUT/'forecast.json'),
 'snapshot_sha256':sha(OUT/'snapshot_v2.json'),'registry_fix':'RF08673cf8 parent reports installed; independent canonical audit PASS'},
 verdict='PARTIAL',axes={'actual_data_reliability':'PASS','numerical_workflow':'PASS','forward_semantic_support':'FAIL','complete_CWP_processing':'PARTIAL'},
 checks=checks,facts=facts,independent_calculations=read(HERE/'independent_calculations.json'),
 missing_steps=['生产CWP narrativeWorker/选择/摘要派生未跑','最新IR记录DOCX/完整投资者presentation未获得已验证官方原文',
 'material公告正文及逐件重要性归档CN-03','中文电话会正式TXT未获取，SSE问答不可等价ET'],
 findings=findings,artifact_integrity={'record_count':len(read(HERE/'artifact_integrity.json')),'file':str(HERE/'artifact_integrity.json'),
 'command_pair_count':len(read(HERE/'command_integrity.json')),'independent_review_owned_only':True},
 limits=['77摘录匹配不等于77结论获支持；future假设审查不等于预测准确率。',
 '三年history总额没有统计校准；equipment units×weighted recognized unit proxy和非设备fallback均有限。',
 '采集captureunsigned/unattested，SHA只证明保存字节；不保证hostattestation。',
 '早期nestedtrace不覆盖所有系统调用；审查失败尝试保留。',
 '生产readerparser/LLM计数null/unknown未当作0；审查ownedTEMP保留至主线收尾清理，生产原件绝不删除。'],
 command_index=str(HERE/'commands'/'index.jsonl'),
 recheck_contract={'do_not_self_repair':True,'single_executor_batch':True,'new_forecast_version_required':True,
 'recheck_only_changed_dependency_closure':['claims/parameters/growth_driver/coverage/source_facts','new official material bodies/targets','formal engine/render/snapshot/registry for newversion'],
 'already_green_repeated_read_not_required':['unchanged original wholePDF','unchangedrawSHA/config','unchangedSIDdownload','unchanged numericruntime']})
save('review.json',review)
md = '''# CN-688012 中微公司：独立全量审查（v2）

## 结论：PARTIAL

原文历史数据、并购口径、真实下载复用链路及正式数值工作流通过。前瞻引用与最新重要公告的覆盖仍有三组 P2 问题；生产 CWP Worker 未运行，不能签完整端到端 PASS。本审查未替执行者改 input 或签收。

## 已通过的核验

- 344 个交付文件的字节与 SHA，73 对 start/finish；16 次失败尝试保留。嵌套进程记录 84 启动、84 退出、39 spawn。
- RF→FF→CWP→SID 的真实 H1 首次下载及随后0新下载。独立再次走 RF→FF→CWP 两份 reuse_only，SourceRef v2 原件实开；annual 9,165,875B、H1 3,149,962B。两份官方网原PDF独立HTTP200实际全流SHA与本地相同。
- 年报259页、半年报210页独立提取。77/77摘录匹配；全部42参数、3历史总额、3目标、9维、6沟通类、4驱动逐条记录在 facts_full.json。6张重要表格实际渲染并视觉读表头/列/单位。
- FY2023/24/25营收6263.51358137/9065.16509769/12384.63826811百万元；equipment10527.0百万元是舍入披露。1240为售出腔数，单位收入8.489516仅混合proxy。
- CMP控制日2026-05-31，控制后至6月30日收入1.29190208百万元，64.69%持股不乘合并收入。卖方2026/27/28全年280/430/580百万元承诺不等于AMEC部分年指导；2026范围不匹配已保留。
- 独立实时读取SSE195条互动，精确公司身份过滤8条；29条预征集精确1条。8条全部原中文读完，独立响应557100B同SHA。800海外累计腔未当年度销量，厂房面积未机械换收入。
- 所有27个分部年度场景、9个公司年度场景、增长/CAGR/增量、4敏感性、4驱动分配通过。strong原input校验、Markdown精确渲染、snapshotv2、独立TEMP新CLI全JSON/MD精确相同；修复后registry audit RC0。
- 配置及SKILL的4份基线SHA未变；原件未改。审查无LLM调用/无费用，Dayu未改。

## 一次性交给原执行者修复的完整问题

'''
for f in findings:
    md += f"### {f['id']} / {f['severity']}：{f['category']}\n\n{f['description']}\n\n"
    if f.get('claim_ids'): md += '精准 claim IDs：`'+'`, `'.join(f['claim_ids'])+'`。\n\n'
    if f.get('parameter_ids'): md += '精准 parameter IDs：`'+'`, `'.join(f['parameter_ids'])+'`。\n\n'
    if f.get('coverage_ids'): md += '覆盖接口：`'+'`, `'.join(f['coverage_ids'])+'`。\n\n'
    md += '复现：'+f['reproduction']+'\n\n改法：'+f['requested_fix']+'\n\n'
md += '''## 如实保留的范围缺口

本次只在TEMP确定性解析PDF，生产CWP的叙述选择/摘要Worker未跑，parser/LLM计数null仍未知；不能用raw成功替代完整初级处理成功。最新IR-DOCX/完整presentation、正式中文电话会TXT原文未取得；SSE网络问答是独立补充路线，不能冒称FF→ET中文链路成功。未来年度实绩尚未知，回测evaluate不适用。

当前65.5923 medium是runtime结构评分，历史准确率观察0；引用文字错配会使表面覆盖率高估，不能将这个分数解释为预测经济准确率。所有未来路径均是条件性分析师假设，非概率区间或公司指导。

## 修复与复查接口

原执行者按CN-01/02/03一次处理，创建新forecast_version，保留v1/v2冻结文件与旧失败记录。CN-04为来源诊断建议，原件已经相同SHA，勿重下。独立复查只检查改变的source/claim/parameter/coverage/target依赖及新版正式engine/render/snapshot/registry；不重复读取无变化全文、不重复已绿真实下载。CWP未跑/官方原文缺口仍按真实情况记录。

## 交付索引

- review.json：规定格式，包括每个技能步骤、全量事实、独立计算、精确问题范围。
- facts_full.json：159条实体/事实/参数/claim逐条记录（实际数量以review.json为准）；摘录匹配与语义支持分开。
- all_claim_original_match.json：77条原文匹配；它不是语义全PASS签收。
- independent_calculations.json / formal_independent_checks.json / independent_fresh_cli_reproduction.json：独立复算和正式重现。
- commands/index.jsonl：审查实际命令开始/结束/退出/输出SHA；失败尝试保留。
- official_pdf_current_sha_checks.json / visual_table_render_receipt.json / live_official_ir_check.json / configuration_unchanged.json：实际官方原件、视觉表格、实时问答与配置核验。

审查ownedTEMP保留供主线收尾与复查；不会删除生产原件或覆盖执行产物。
'''
md = md.replace('159条实体/事实/参数/claim', str(len(facts))+'条实体/事实/参数/claim')
(HERE/'review.md').write_text(md,encoding='utf-8')
print(json.dumps({'verdict':'PARTIAL','facts':len(facts),'claims':len(CP),'parameters':len(PARAMS),'semantic_claim_fail':len(bad),'checks':len(checks),'findings':[f['id'] for f in findings],'input_sha256':sha(OUT/'input.json')},ensure_ascii=False))
