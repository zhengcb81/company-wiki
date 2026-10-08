"""Construct real research input in isolated TEMP from checked official artifacts.

No shared code/config or original document mutations. All future driver values
are analyst assumptions, never described as management's forecasts.
"""
from pathlib import Path
import copy, datetime, hashlib, json, os
ROOT=Path(__file__).resolve().parent
OUT=Path(os.environ['TEMP'])/'cwp-rf-e2e-20261008'/'CN-688012'
SKILL=Path('C:/Users/郑曾波/.agents/skills/revenue-forecast')
ASOF='2026-10-08'; YEARS=[2026,2027,2028]; SC=['low','base','high']
def sha(x):return hashlib.sha256(x).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def formal_record(label):
    choices=[]
    for p in (ROOT/'commands').glob('*.stdout.txt'):
        if label not in p.name:continue
        try:v=read(p)
        except (ValueError,UnicodeError):continue
        if isinstance(v,dict) and 'company_wiki_trace' in v and v.get('source_id'):choices.append((p,v))
    assert choices,label+' has no successful real source-preparation response'
    p,v=sorted(choices,key=lambda x:x[0].name)[-1]
    fields=['source_id','source_type','title','publisher','url','published_date','accessed_date','page_or_section','capture']
    return {k:v[k] for k in fields},str(p),v
annual,annual_path,annual_full=formal_record('annual')
half,half_path,half_full=formal_record('half2026')
assert half['published_date']=='2026-08-20','Official China publication date must be producer-corrected before modeling'
ap={x['page']:x['text'] for x in read(OUT/'annual2025_pages.json')}
hp={x['page']:x['text'] for x in read(OUT/'half2026_pages.json')}
def excerpt(pages,page,start=None,end=None,maxchars=700):
    t=pages[page]
    if start:
        at=t.find(start);assert at>=0,(page,start);t=t[at:]
    if end:
        at=t.find(end);assert at>=0,(page,end);t=t[:at+len(end)]
    return t[:maxchars].strip()
facts=[];claims=[];params=[]
sources=[annual,half]
# This is the actual web.run parsed response, not a falsely claimed full HTML body.
semisnap=OUT/'semi_web_open_snapshot.json'
assert semisnap.exists()
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
sevent=dict(tool='web.run',action='official page open',url='https://www.semi.org/en/semi-press-release/global-semiconductor-equipment-sales-forecast-to-reach-a-record-229-billion-dollars-in-2028-semi-reports',tool_call_id='turn234view0',snapshot_sha256=sha(semisnap.read_bytes()),captured_at=now,artifact=str(semisnap),snapshot_kind='complete returned parsed tool output; not original HTML')
host=dict(host_receipt_schema_version='1.0',issuer='rf_cn_execution',environment='Codex local logged tools; unsigned',tool_name='web.run',action='capture_open',event_sha256=sha(canonical(sevent)),timestamp=now)
host['receipt_sha256']=sha(canonical(host))
capture=dict(capture_schema_version='1.0',capture_method='browser_open',tool_name='web.run',tool_call_id='turn234view0',captured_date=ASOF,snapshot_sha256=sevent['snapshot_sha256'],content_treatment='untrusted_data_only',prompt_injection_status='not_reviewed',host_receipt=host)
capture['receipt_sha256']=sha(canonical(capture))
semi=dict(source_id='semi_wfe_20260714',source_type='industry_association',title='SEMI Mid-Year Semiconductor Equipment Forecast',publisher='SEMI',url=sevent['url'],published_date='2026-07-14',accessed_date=ASOF,page_or_section='WFE Sales and Regional Outlook',capture=capture)
sources.append(semi)
ir_meta=read(ROOT/'roadshow_public_questions_receipt.json')
ir_payload=read(OUT/'roadshow_public_questions.json')
assert ir_payload['success'] and ir_payload['datas'][0]['total']==len(ir_payload['datas'][0]['records'])==195
ir_records=[x for x in ir_payload['datas'][0]['records'] if x.get('guestCompanyName')=='中微公司' and x.get('companyId')==145565]
assert len(ir_records)==8 and all('688012' in x.get('miniLogoPath','') for x in ir_records)
ir_by_id={x['id']:x for x in ir_records}
ir_event=dict(tool='urllib.request POST',url=ir_meta['url'],request=ir_meta['request'],observed_timestamp=ir_meta['captured_at'],response_sha256=ir_meta['sha256'],actual_command='1791445202091909100-roadshow-public-real-urlencoding',attribution='guestCompanyName=中微公司; companyId145565; stock-logo688012; exclude moderator mentions')
ir_host=dict(host_receipt_schema_version='1.0',issuer='rf_cn_execution',environment='unsigned logged official API response',tool_name='urllib.request',action='bounded_official_api_read',event_sha256=sha(canonical(ir_event)),timestamp=ir_meta['captured_at'])
ir_host['receipt_sha256']=sha(canonical(ir_host))
ir_capture=dict(capture_schema_version='1.0',capture_method='api_response',tool_name='urllib.request',tool_call_id=ir_event['actual_command'],captured_date=ASOF,snapshot_sha256=ir_meta['sha256'],content_treatment='untrusted_data_only',prompt_injection_status='not_reviewed',host_receipt=ir_host)
ir_capture['receipt_sha256']=sha(canonical(ir_capture))
ir=dict(source_id='amec_sse_results_qa_20260910',source_type='company_release',title='中微公司2026半年度业绩说明会官方网络问答',publisher='中微公司 / 上证路演中心',url='https://roadshow.sseinfo.com/activityDetails/40766',published_date='2026-09-10',accessed_date=ASOF,page_or_section='Official public API, all195 interactive replies; 8 AMEC records',capture=ir_capture)
sources.append(ir)
index={x['source_id']:x for x in sources}
(ROOT/'semi_capture_receipt.json').write_text(json.dumps(sevent,ensure_ascii=False,indent=2),encoding='utf-8')
def claim(cid,source,target_type,target_id,support,loc,text,value=None,unit=None,period=None):
    s=index[source]
    full_context=text
    text=text[:500].strip()
    c=dict(claim_id=cid,source_id=source,target_type=target_type,target_id=target_id,support_type=support,locator=loc,excerpt=text,excerpt_sha256=sha(text.strip().encode()),content_sha256=s['capture']['snapshot_sha256'],capture_receipt_sha256=s['capture']['receipt_sha256'],verification_status='opened_and_checked',verified_by='rf_cn_execution',verified_date=ASOF)
    if value is not None:c.update(extracted_value=value,unit=unit,period=period)
    claims.append(c)
    facts.append(dict(claim_id=cid,source_id=source,source_url=s['url'],locator=loc,excerpt=text,source_snapshot_sha256=s['capture']['snapshot_sha256'],claim_kind=support,target_type=target_type,target_id=target_id,value=value,unit=unit,period=period,verified_date=ASOF,check='checked exact original context; numerical assumptions are NOT extracted source forecasts' if support=='rationale_support' else 'original text and units checked',source_response=annual_path if source==annual['source_id'] else half_path if source==half['source_id'] else str(semisnap)))
    facts[-1]['full_checked_context']=full_context
    if source==ir['source_id']:facts[-1]['source_response']=str(OUT/'roadshow_public_questions.json')
    return cid
def param(pid,value,kind='analyst_assumption',year=2025,scenario=None,dim='revenue',unit='CNY million',definition='',rationale='',source=None,page=65,text=None,formula=None,inputs=None):
    p=dict(parameter_id=pid,kind=kind,value=value,unit=unit,period=f'FY{year}',definition=definition,dimension=dim,time_basis='annual',source_ids=[],scenario=scenario,rationale=rationale,claim_ids=[])
    if dim in {'revenue','revenue_per_unit','monetary_balance'}:p.update(currency='CNY',scale='million')
    if source:
        cid='claim_'+pid
        supp='exact_value' if kind in {'reported_fact','management_guidance'} else 'rationale_support'
        p['source_ids']=[source['source_id']]
        p['claim_ids']=[claim(cid,source['source_id'],'parameter',pid,supp,f'PDF page {page}' if source!=semi else 'WFE Sales by Segment and Region; web lines 167–181',text if text else excerpt(ap,page),value if supp=='exact_value' else None,unit if supp=='exact_value' else None,p['period'] if supp=='exact_value' else None)]
    if formula:p.update(formula=formula,input_parameter_ids=inputs)
    params.append(p);return p
total=12384.63826811; equip=10527.0; residual=total-equip
history_values={2023:6263.51358137,2024:9065.16509769,2025:total}
history=[]
for y,v in history_values.items():
    cid=claim(f'claim_history_{y}',annual['source_id'],'historical_revenue',f'historical_revenue:{y}','exact_value','PDF page 25, principal financial data, CNY yuan converted /1,000,000',excerpt(ap,25,'营业收入',maxchars=700),v,'CNY million',f'FY{y}')
    history.append(dict(year=y,value=v,source_ids=[annual['source_id']],claim_ids=[cid]))
param('reported_total',total,kind='reported_fact',definition='Consolidated external FY2025 recognized revenue',rationale='Original CNY yuan /1,000,000; reconciled to annual p218',source=annual,page=218,text=excerpt(ap,218,'61、'))
param('equipment_base',equip,kind='reported_fact',definition='FY2025 dedicated equipment revenue, disclosed rounded to 105.27亿元',rationale='Disclosed rounded magnitude; approximately ±0.5 CNY million, not false precision',source=annual,page=65,text=excerpt(ap,65,'报告期内，公司半导体设备收入',maxchars=360))
param('aftermarket_base',residual,kind='derived_fact',definition='Mathematical residual, not a precise published spares/services segment',rationale='Total minus rounded equipment; includes undisclosed residual and inherits rounding. Mixed already-recognized fallback.',formula='x0-x1',inputs=['reported_total','equipment_base'])
param('cmp_base',0,kind='analyst_assumption',definition='FY2025 incremental CMP revenue included in AMEC consolidation',rationale='CMP was acquired in 2026; zero incremental consolidation in FY2025 does NOT mean CMP standalone revenue zero',source=half,page=176,text=excerpt(hp,176,'九、合并范围的变更',maxchars=650))
param('equipment_units_2025',1240,kind='reported_fact',dim='quantity',unit='chambers',definition='Dedicated-equipment chambers sold; not all produced or shipped chambers',rationale='Annual physical-sales disclosure; accepted-chamber forecast is a proxy, not a shipment-to-revenue identity proven by the table',source=annual,page=65,text=excerpt(ap,65,'(2). 产销量',maxchars=300))
param('equipment_weighted_unit_revenue_2025',equip/1240,kind='derived_fact',dim='revenue_per_unit',unit='CNY million per chamber',definition='Rounded recognized equipment revenue per reported chamber, weighted product/configuration mix proxy',rationale='Not a quoted SKU ASP; rounded numerator limits precision',formula='x0/x1',inputs=['equipment_base','equipment_units_2025'])
units={'low':[1395,1470,1500],'base':[1620,2050,2500],'high':[1800,2500,3250]}
price={'low':[8.2,8.1,8.0],'base':[8.49,8.49,8.4],'high':[8.9,8.9,8.8]}
afterm={'low':[residual*1.10,residual*1.15,residual*1.20],'base':[residual*1.25,residual*1.50,residual*1.75],'high':[residual*1.35,residual*1.75,residual*2.2]}
cmp={'low':[40,180,260],'base':[120,400,550],'high':[220,520,750]}
for sc in SC:
    for i,y in enumerate(YEARS):
        common='Conditional scenario, not a probability band. Global WFE forecast is an outside reference, not copied into AMEC. Customer concentration, client capex, qualification-to-acceptance, price mix and production execution can all change revenue.'
        param(f'equipment_units_{sc}_{y}',units[sc][i],year=y,scenario=sc,dim='quantity',unit='chambers',definition='Assumed chambers achieving revenue recognition in calendar fiscal year',rationale=common+' Base year-on-year unit growth is 30.6%/26.5%/22.0%, starting from 2025 sold 1240; product qualification and domestic process coverage justify a premium to industry benchmark, but no specific capacity ceiling is reported. Low imposes concentrated-client capex/acceptance delays; high requires successful film and packaging ramps.',source=half,page=16,text=excerpt(hp,16,'公司的ICP',maxchars=650))
        param(f'equipment_unit_revenue_{sc}_{y}',price[sc][i],year=y,scenario=sc,dim='revenue_per_unit',unit='CNY million per chamber',definition='Assumed recognized weighted revenue per chamber, mix and discounts included',rationale='Independent pricing/mix assumption near rounded 2025 proxy 8.4895; low continuing discounts, high richer advanced equipment mix. No segment SKU price or client contract is known.',source=annual,page=65,text=excerpt(ap,65,'由于今年客户的结构性变化',maxchars=220))
        param(f'aftermarket_revenue_{sc}_{y}',afterm[sc][i],year=y,scenario=sc,definition='Assumed already-recognized non-equipment residual including spares and services',rationale='Fallback residual annual path: installed equipment supports repeat spares/services; no measured installed base, attach rate or service progress. Values are assumptions rather than a disaggregated reported segment. Avoids re-applying arbitrary progress or shipment lag.',source=annual,page=174,text=excerpt(ap,174,'本集团将备品备件',maxchars=700))
        param(f'cmp_revenue_{sc}_{y}',cmp[sc][i],year=y,scenario=sc,definition='Assumed incremental external CMP revenue included after control, full consolidated revenue not ownership multiplied',rationale=('2026 June–December after purchase on May31; June actual only1.29190208m. No mechanical 7/12 conversion of annual performance commitment; wide ramp/acceptance uncertainty.' if y==2026 else 'Full-year CMP operating ramp assumption. Independently benchmarked to seller annual commitment, not forced to meet it. Intra-group transactions would require elimination if evidence emerges.')+' Low includes integration/qualification delays; high requires customer conversions.',source=half,page=177,text=excerpt(hp,177,'业绩承诺的完成情况',maxchars=620))
data=read(OUT/'model_template.json')
data.pop('_comment',None)
data.update(company_name='中微半导体设备（上海）股份有限公司',as_of_date=ASOF,forecast_version='2026-10-08-cn688012-v2',sources=sources,parameters=params,evidence_claims=claims,historical_revenue=history,reported_total_revenue_parameter_id='reported_total',base_adjustment_parameter_ids=[],management_targets=[])
# Preserve disjoint consolidation perimeter across every future parameter;
# future Equipment/Aftermarket assumptions exclude the separately modeled CMP.
for p in params:
    if p['parameter_id'].startswith('equipment_') and p['period']!='FY2025':
        p['definition']+='; legacy AMEC operations excluding acquired CMP'
    elif p['parameter_id'].startswith('aftermarket_revenue_'):
        p['definition']+='; legacy AMEC residual excluding all acquired CMP revenue'
    if p['parameter_id'].startswith('equipment_units_') and p['period']!='FY2025':
        cid=claim('claim_ir_'+p['parameter_id'],ir['source_id'],'parameter',p['parameter_id'],'rationale_support','Official reply id2508385; 尹志尧; 2026-09-10 16:37:39; companyId145565',ir_by_id[2508385]['content'])
        p['source_ids'].append(ir['source_id']);p['claim_ids'].append(cid)
        p['rationale']+=' September10 official capacity plan supports expansion direction; 600,000m² current/900,000m² five-year plan and Guangzhou/Chengdu2027H1 commissioning are not converted mechanically into accepted chamber units or guaranteed revenue.'
for seg in data['segments']:
    n=seg['name']; r=seg['recognition']
    r.update(modeled_presentation='gross',presentation='gross',mode='modeled_as_recognized')
    if n=='Equipment':
        r.update(timing='point_in_time',trigger='Legacy AMEC equipment excluding acquired CMP: customer confirmation after installation, commissioning and acceptance; assumed units are already accepted rather than shipments')
        pol=excerpt(ap,174,'本集团将专用设备产品',end='相应确认收入。',maxchars=420)
    else:
        r.update(timing='mixed',trigger='Already recognized external revenue: equipment/spares control-transfer and any services cost-based progress are included without a second timing transform',aggregation_boundary=('Total group revenue minus rounded dedicated-equipment revenue; spares/services split unavailable, mathematical residual, not official segment' if n=='Aftermarket' else 'Incremental acquired CMP group external revenue included only after May31 2026 control; zero FY2025 AMEC-perimeter base; standalone annual commitment differs from 2026 partial consolidation'))
        pol=excerpt(ap,174,'本集团在客户取得',maxchars=1150)
    cid=claim('claim_recognition_'+n,annual['source_id'],'recognition_policy','recognition:'+n,'policy_support','PDF page174 revenue policy, complete equipment/spares/services context',pol)
    r['basis_claim_ids']=[cid]
    if n!='Equipment':
        # Separate checked policy spans keep every relevant policy under the
        # 500-character per-claim contract without losing services timing.
        for part,start,end in [('equipment','本集团将专用设备产品','相应确认收入。'),('spares','本集团将备品备件','相应确认收入。'),('services','本集团对外提供劳务','以使其能够反映履约情况的变化。')]:
            piece=excerpt(ap,174,start,end=end,maxchars=500)
            r['basis_claim_ids'].append(claim('claim_recognition_'+n+'_'+part,annual['source_id'],'recognition_policy','recognition:'+n,'policy_support','PDF page174, '+part+' policy',piece))
    for sc,x in seg['scenarios'].items():x['rationale']='Explicit conditional operating assumptions; mix and recognition limitations are disclosed, not management guidance.'
# Six official communication categories. Any unavailable label states retrieval
# failure, not a conclusion that the company made no targets.
target_ids=['CMP_annual_2026','CMP_annual_2027','CMP_annual_2028']
coverage=[]
for cat in ['latest_annual_filing','latest_results_release','latest_earnings_call','latest_investor_presentation','latest_strategy_communication','material_announcements_since_last_filing']:
    checked=cat in {'latest_annual_filing','latest_results_release','latest_strategy_communication','material_announcements_since_last_filing'}
    ids=[annual['source_id']] if cat=='latest_annual_filing' else [half['source_id'],ir['source_id']] if cat=='latest_strategy_communication' else [half['source_id']] if checked else []
    text={'latest_annual_filing':'2025 annual report opened, revenue and policy/risk/strategy checked. Does not falsely report March proposed acquisition as completed.','latest_results_release':'Latest 2026H1 filing opened and verified; H1 revenue6,691.28732767m is not doubled mechanically to annual revenue.','latest_earnings_call':'CN earnings-transcripts capability does not provide AMEC telephone-call TXT. Official September10 network Q&A page opened in browser; only first-page content captured, not a complete telephone transcript. Retrieval gap remains; no claim that management gave no target.','latest_investor_presentation':'Search identified August2026 IR record DOCX through secondary leads, but no verified official original or complete presentation captured. AMEC homepage and IR2 failed web access. Original unavailable to this run, not proof it does not exist.','latest_strategy_communication':'Latest H1 pages14–18 product strategy read; customer validations are distinct from accepted revenue.','material_announcements_since_last_filing':'2026H1 p53/176/177 verifies completed May31 acquisition and seller annual CMP commitments; official CNINFO recent announcement first-page titles checked. Complete post-H1 announcements and September Q&A not exhaustively captured, a prominent residual coverage limitation.'}[cat]
    rec=dict(category=cat,status='checked' if checked else 'not_available',source_ids=ids,checked_date=ASOF,conclusion=text,material_revenue_target_ids=target_ids if cat in {'latest_results_release','material_announcements_since_last_filing'} else [])
    if cat=='latest_strategy_communication':rec['conclusion']='H1 products and the complete September10 interactive dataset checked. All8 AMEC records are identity-filtered. Capacity/site plans and overseas cumulative approximately800 reaction stages are context, not annual revenue/accepted volume forecasts. Pre-collected responses are separately logged.'
    if cat=='latest_earnings_call':
        text='No AMEC telephone-call TXT obtained via ET. Full official September10 network results Q&A was read and registered separately as strategy communication; this is not falsely labeled an ET telephone transcript. No claim that missing telephone coverage proves management has no target.'
        rec['conclusion']=text
    if cat=='material_announcements_since_last_filing':rec['conclusion']='All19 official CNINFO announcement titles from August20 through October8 were read (metadata only). H1 pages53/176/177 acquisition/targets and complete September10 interactive Q&A checked in original. Post-H1 fund announcement and capex-delay documents are not fully downloaded/opened; no facts or targets inferred from titles alone.'
    if not checked:
        event=dict(query_scope='688012 official earnings-call/IR presentation, 2026H1 through information date; AMEC homepage, SSE IR2 and September10 roadshow, secondary leads for official originals',query_time=ASOF,event_ids=['turn231search2','turn231view0','turn232view0','turn235search0','cua-roadshow40766-actual-open'],generated_by='rf_cn_execution logged observed tool calls')
        event['event_sha256']=sha(canonical(event))
        rec.update(rationale=text,search_description=event['query_scope'],search_event=event)
    coverage.append(rec)
data['management_communication_coverage']=coverage
for y,v in zip(YEARS,[28000,43000,58000]):
    tid=f'CMP_annual_{y}'
    cid=claim('claim_'+tid,half['source_id'],'management_target',tid,'exact_value','PDF page177, seller commitment; table p53 states annual amounts not cumulative objective',excerpt(hp,177,'根据业绩承诺方',end='本期未到业绩承诺考核时点。',maxchars=550),v,'万元',f'FY{y}')
    mismatch=y==2026
    t=dict(target_id=tid,statement=f'中微众硅在{y}年度实现的合并报表范围营业收入不低于{v:,}.00万元',metric_name='CMP consolidated annual revenue commitment by transaction sellers',metric_definition='Full-year target company consolidated revenue independently audited under performance compensation agreement; not group AMEC revenue',target_period=f'FY{y}',raw_unit='万元',raw_currency='CNY',raw_scale='ten_thousand',raw_target_value=v,measurement_basis='annual_period',measurement_periods=[f'FY{y}'],measurement_rationale='Original says 在2026年度、2027年度和2028年度实现...分别; per-year amount. Cumulative compensation test elsewhere does not change annual target amounts.',materiality='material',commitment_strength='goal',scope=dict(type='segment',name='CMP'),perimeter_status='mismatch' if mismatch else 'matched',perimeter_notes='2026 annual standalone target includes pre-acquisition periods; model is only June–December consolidated contribution.' if mismatch else 'Full-year post-control external CMP revenue assumed comparable; unidentified internal transactions remain a reconciliation risk.',comparison='at_least',treatment='unmodeled_data_gap' if mismatch else 'independent_benchmark',comparison_value=None if mismatch else v/100,comparison_currency='CNY',comparison_scale='million',normalization_rationale='万元 /100 equals CNY million; no FX. No unsupported partial-year prorating.',mapped_parameter_ids=[] if mismatch else [f'cmp_revenue_{sc}_{y}' for sc in SC],mapped_scenarios=[] if mismatch else SC,claim_ids=[cid],rationale='Seller compensation commitment is an independent reference, not a guaranteed revenue guidance or forced base scenario.')
    if not mismatch:
        bc=claim('claim_benchmark_'+tid,half['source_id'],'management_target',tid,'rationale_support','PDF pages176–177, purchase and commitment scope',excerpt(hp,177,'业绩承诺的完成情况',maxchars=650))
        t.update(benchmark_rationale='Independent analyst CMP operating paths are compared against seller annual commitment under matching full-year scope; under-attainment is reported as computed, never forced up.',benchmark_claim_ids=[bc])
    data['management_targets'].append(t)
base_equipment=[f'equipment_units_base_{y}' for y in YEARS]+[f'equipment_unit_revenue_base_{y}' for y in YEARS]
base_after=[f'aftermarket_revenue_base_{y}' for y in YEARS]
base_cmp=[f'cmp_revenue_base_{y}' for y in YEARS]
dimensions={
'company_foundation':('Consolidated external revenue, China-heavy physical equipment portfolio; acquired CMP is a new perimeter.',base_equipment+base_cmp),
'growth_curve':('Mature etch plus commercializing film/CMP. Three annual historical totals are insufficient to estimate a full cycle; no historical statistical accuracy claim.',base_equipment+base_cmp),
'industry_market':('Outside WFE 23.1%/21.8%/14.1% reference does not mechanically identify AMEC growth; China moderation is counterevidence.',base_equipment),
'competition':('Client discounts and international peer technology competition constrain weighted price; no precise future market share invented.',[f'equipment_unit_revenue_base_{y}' for y in YEARS]),
'capacity':('1240 sold vs1660 produced and1010 inventory chambers in FY2025; inventory is not infinite immediately acceptable capacity. No measured FY2026–28 hard capacity ceiling.',base_equipment),
'technology':('H1 film/ICP repeat orders and validation expand process coverage; alpha/beta validation is not guaranteed recognized sales.',base_equipment+base_cmp),
'policy':('Export restrictions and critical component availability can delay accepted output; low case includes disruption, no unsupported legal-rule forecast.',base_equipment),
'customers':('Customer A39.99% FY2025 vs22.15% FY2024; client capex concentration raises low-case risk.',base_equipment),
'demand':('Chamber acceptance drives equipment; installed fleet supports residual spares/services but no measured fleet or attach rate.',base_equipment+base_after)}
data['research_coverage']=[dict(dimension=k,status='modeled_driver',conclusion=v[0],revenue_mechanism=v[0],rationale='Supported mechanisms map to actual base path; numerical magnitudes are conditional analyst assumptions. Short history, no hard throughput capacity and composite timing are disclosed. Official September10 site/overseas/supply-chain replies read; plant area and cumulative overseas deliveries are not annual recognized revenue.',parameter_ids=(['reported_total','equipment_base']+v[1] if k=='company_foundation' else v[1]),source_ids=([semi['source_id'],half['source_id']] if k=='industry_market' else [annual['source_id'],half['source_id'],ir['source_id']])) for k,v in dimensions.items()]
roots=[
('core_etch_acceptance','客户工序扩展及刻蚀验收','Current etch qualification and client investment convert into accepted chamber volume.',base_equipment,[('Equipment',.75)],half,16,excerpt(hp,16,'公司的ICP',maxchars=650),'cyclical'),
('films_packaging','薄膜及先进封装商业化','Repeated client validations/orders broaden accessible steps; commercial acceptance is uncertain.',base_equipment,[('Equipment',.25)],half,16,excerpt(hp,16,'（3）薄膜沉积',maxchars=650),'multi_year_structural'),
('afterm_support','安装设备带来的备件和服务','Installed operations support replacement parts and services; no invented fleet metric.',base_after,[('Aftermarket',1.0)],annual,174,excerpt(ap,174,'本集团将备品备件',maxchars=650),'multi_year_structural'),
('cmp_ramp','并购CMP收入并表及商业化','Control followed by customer qualification/acceptance gives incremental consolidated external revenue.',base_cmp,[('CMP',1.0)],half,177,excerpt(hp,177,'大额商誉形成',maxchars=400),'uncertain')]
drivers=[]
for did,title,thesis,pids,weights,src,page,text,persistence in roots:
    a=claim('claim_driver_'+did,src['source_id'],'growth_driver','e_'+did,'rationale_support',f'PDF page{page}',text)
    b=claim('claim_contrary_'+did,half['source_id'],'growth_driver','contra_'+did,'rationale_support','PDF page33, acquisition and technology execution risks',excerpt(hp,33,maxchars=850))
    drivers.append(dict(driver_id=did,title=title,thesis=thesis,causal_chain=['Customer process needs and capital investment','Qualification, manufacturing and installation execution','Customer acceptance or genuine service progress','Recognized external annual revenue'],parameter_ids=pids,segment_attribution=[dict(segment_name=n,weight=w) for n,w in weights],horizon=dict(start_year=2026,end_year=2028),persistence=persistence,persistence_rationale='Horizon spans current commercial ramps and equipment/client investment cycle; strength is an analyst judgment, not known outcome.',evidence_nodes=[dict(evidence_id='e_'+did,evidence_type='company_execution',inference_distance='one_step',conclusion=thesis,claim_ids=[a]),dict(evidence_id='contra_'+did,evidence_type='explicit_company_risk',inference_distance='contrary',conclusion='Delays, customer capex, competitive technology and acquired-business underperformance can defeat the path.',claim_ids=[b])],leading_indicators=['Accepted chamber sales and recurring customer orders','Half-year external revenue excluding acquisitions','Product validations reaching repeat volume orders'],falsifiers=['Acceptance/recognized revenue persistently below low-case driver values','New product validations fail to reach volume orders','CMP external annual revenue materially misses independent seller commitment'],counterevidence_status='found',counterevidence_rationale='Opened H1 p33 and annual p61–65 risks; no assumption that a positive product announcement proves future acceptance.'))
    if did in {'core_etch_acceptance','films_packaging'}:
        eid='ir_supply_'+did
        cid=claim('claim_'+eid,ir['source_id'],'growth_driver',eid,'rationale_support','Official reply id2508080, 尹志尧, companyId145565, 2026-09-10 15:37:45',ir_by_id[2508080]['content'])
        drivers[-1]['evidence_nodes'].append(dict(evidence_id=eid,evidence_type='official_results_question_answer',inference_distance='one_step',conclusion='Management describes strategic component stocking, domestic supplier alternatives and improved delivery/testing efficiency. No numeric accepted-volume guarantee.',claim_ids=[cid]))
    if did=='core_etch_acceptance':
        eid='outside_wfe_reference'
        raw=semisnap.read_text(encoding='utf-8')
        line=next(x for x in raw.splitlines() if x.startswith('L167: ')).split(': ',1)[1]
        snippet=line[:line.find('2026.')+5]
        cid=claim('claim_'+eid,semi['source_id'],'growth_driver',eid,'rationale_support','Official SEMI July14 release, parsed original line167; global WFE, not AMEC revenue',snippet)
        drivers[-1]['evidence_nodes'].append(dict(evidence_id=eid,evidence_type='industry_association_outside_reference',inference_distance='analogical',conclusion='Independent global WFE benchmark: +23.1% in2026, +21.8%2027, +14.1%2028. Directional context only; China moderation, domestic share, product mix and client acceptance create an explicit inferential gap.',claim_ids=[cid]))
data['growth_driver_tree']=dict(status='modeled',drivers=drivers)
data['sensitivity_tests']=[dict(name='终年设备验收腔数±10%',parameter_id='equipment_units_base_2028',shock_type='percent',shock_value=.10),dict(name='终年加权单腔收入±5%',parameter_id='equipment_unit_revenue_base_2028',shock_type='percent',shock_value=.05),dict(name='终年残差备件服务±20%',parameter_id='aftermarket_revenue_base_2028',shock_type='percent',shock_value=.20),dict(name='终年CMP收入±30%',parameter_id='cmp_revenue_base_2028',shock_type='percent',shock_value=.30)]
# Formal output itself is produced only by the installed engine later.
data['evidence_claims']=claims;data['parameters']=params
dest=OUT/'input.json';dest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'fact_checks.json').write_text(json.dumps(dict(schema_version='1.0',company='CN-688012',status='execution checks, pending independent reviewer',facts=facts,additional_checked_facts=[dict(source_id=half['source_id'],locator='PDF page7',raw_value='6,691,287,327.67 CNY yuan',converted_value=6691.28732767,unit='CNY million',period='2026H1',check='Not registered as FY2026 annual revenue parameter; not simply doubled'),dict(source_id=half['source_id'],locator='PDF page176',raw_value='1,291,902.08 CNY yuan',converted_value=1.29190208,unit='CNY million',period='purchase to June30 2026',check='Only June contribution; not annualized or ownership-multiplied'),dict(source_id=annual['source_id'],locator='PDF page219',raw_value='4,952,154,981.39 yuan /39.99%',period='FY2025',check='Customer A concentration risk, not identified client name')]),ensure_ascii=False,indent=2),encoding='utf-8')
fact_document=read(ROOT/'fact_checks.json')
fact_document.update(parameter_inventory=params,derived_fact_checks=[dict(parameter_id=p['parameter_id'],formula=p.get('formula'),inputs=p.get('input_parameter_ids'),stored_value=p['value'],check='Independent arithmetic and formal derived-DAG recomputation required') for p in params if p['kind']=='derived_fact'],official_ir_context=[dict(source_id=ir['source_id'],locator=f'Official interactive reply id{x["id"]}',companyId=x['companyId'],stock_code='688012',speaker=x['guestName'],title=x['guestTitle'],published_at=x['updTime'],answer_original=x['content'],not_a_forecast_fact='Current area and cumulative approximately800 overseas reaction stages are context; forward site dates/five-year area plan are management operating plans, not recognized revenue commitments') for x in ir_records],official_ir_source=ir_meta)
(ROOT/'fact_checks.json').write_text(json.dumps(fact_document,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'communication_coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2),encoding='utf-8')
notes=dict(output_root=str(OUT),input=str(dest),sha256=sha(dest.read_bytes()),parameters=len(params),claims=len(claims),sources=len(sources),preparation_responses=[annual_path,half_path],trust='unsigned actual tool logs; hashes provide integrity not external truth',limitations=['Rounded equipment basis and weighted chamber proxy','Mixed residual already-recognized direct-revenue fallback','New product sub-curves cannot be quantified separately without fabricating reported bases','CMP2026 seller annual target is a perimeter mismatch','Official August IR DOCX and post-H1 fund/capex-delay document bodies unavailable in verified original capture','No out-of-sample realized backtest yet'])
(ROOT/'input_construction_receipt.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(timestamp_utc=now,agent_id='rf_cn_execution',step='0–9',action='construct isolated forecast input from checked real sources and explicit analyst assumptions',tool='company-local build_forecast_input.py',input_summary=notes,source_url=None,artifacts=[str(dest),str(ROOT/'fact_checks.json'),str(ROOT/'communication_coverage.json')],outcome='input constructed; not yet validated or published',error=None),ensure_ascii=False)+'\n')
print(json.dumps(notes,ensure_ascii=False))
