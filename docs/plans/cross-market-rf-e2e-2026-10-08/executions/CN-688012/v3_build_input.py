"""Bounded CN01-04 repair of a new forecast version; old input is never changed."""
from pathlib import Path
import copy,datetime,hashlib,json
ROOT=Path(__file__).resolve().parent
OLD=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/CN-688012')
OUT=OLD/'v3';ASOF='2026-10-08'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def dump(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
data=copy.deepcopy(read(OLD/'input.json'))
def rename(x):
    if isinstance(x,str):return x.replace('Aftermarket','NonEquipmentResidual')
    if isinstance(x,list):return [rename(v) for v in x]
    if isinstance(x,dict):return {k:rename(v) for k,v in x.items()}
    return x
data=rename(data);data['forecast_version']='2026-10-08-cn688012-v3'
ap={p['page']:p['text'] for p in read(OLD/'annual2025_pages.json')}
hp={p['page']:p['text'] for p in read(OLD/'half2026_pages.json')}
annual=data['sources'][0];half=data['sources'][1];semi=next(s for s in data['sources'] if s['source_id']=='semi_wfe_20260714')
responsepath=sorted((ROOT/'commands').glob('*v3-half2026-corrected-url-reuse.stdout.txt'))[-1]
response=read(responsepath)
assert response['url']=='https://static.cninfo.com.cn/finalpage/2026-08-20/1225482884.PDF'
assert response['published_date']=='2026-08-20'
half.update({k:response[k] for k in ['source_id','source_type','title','publisher','url','published_date','accessed_date','page_or_section','capture']})
for c in data['evidence_claims']:
    if c['source_id']==half['source_id']:
        c['capture_receipt_sha256']=half['capture']['receipt_sha256']
        c['content_sha256']=half['capture']['snapshot_sha256']
sources={s['source_id']:s for s in data['sources']}
claims={c['claim_id']:c for c in data['evidence_claims']}
params={p['parameter_id']:p for p in data['parameters']}
drivers={d['driver_id']:d for d in data['growth_driver_tree']['drivers']}
change=[];context={}
def span(pages,p,start,end=None):
    text=pages[p];pos=text.index(start);text=text[pos:]
    if end:text=text[:text.index(end)+len(end)]
    return text.strip()
def makeclaim(cid,source,target_type,target_id,locator,text,**extra):
    assert text.strip()
    s=sources[source]
    c=dict(claim_id=cid,source_id=source,target_type=target_type,target_id=target_id,support_type='rationale_support',locator=locator,excerpt=text.strip(),excerpt_sha256=sha(text.strip().encode()),content_sha256=s['capture']['snapshot_sha256'],capture_receipt_sha256=s['capture']['receipt_sha256'],verification_status='opened_and_checked',verified_by='rf_cn_execution',verified_date=ASOF,**extra)
    if cid in claims:claims[cid].clear();claims[cid].update(c)
    else:data['evidence_claims'].append(c);claims[cid]=c
    context[cid]={'source_id':source,'locator':locator,'full_checked_context':text,'check':'Exact original opened text; rationale_support supports stated context/direction only and does not extract future parameter magnitudes'}
    change.append(cid);return cid
def node(driver,eid,conclusion,cids,distance='one_step',etype='company_business_context'):
    drivers[driver]['evidence_nodes'].append(dict(evidence_id=eid,evidence_type=etype,inference_distance=distance,conclusion=conclusion,claim_ids=cids))
service=span(ap,53,'半导体设备制造商的售后服务尤为关键','良好的品牌形象。')
platform=span(ap,48,'子公司中微汇链','85%。')
hservice=span(hp,23,'半导体设备制造商的售后服务尤为关键','良好的品牌形象。')
for p in data['parameters']:
    if p['parameter_id'].startswith('aftermarket_revenue_'):
        p['definition']='Analyst-assumed annual recognized non-equipment mathematical residual; no disclosed product/service disaggregation'
        p['rationale']='Transparent direct_revenue fallback on FY2025 total minus rounded dedicated-equipment revenue (1857.63826811m, rounding inherited). The group describes after-sales support and digital/gas purification activities, but their revenue allocations within this residual are unknown. Retained conditional low/base/high amounts are analyst stress assumptions, not a measured fleet, attach rate, renewal curve or quantified repeat-purchase forecast. No claim that the entire residual is aftermarket; no separate capacity or service-lag transform.'
        makeclaim('claim_'+p['parameter_id'],annual['source_id'],'parameter',p['parameter_id'],'FY2025 annual PDF p53, sales/service network; direction only, residual composition unknown',service)
params['aftermarket_base']['definition']='Unsplit non-equipment mathematical residual: group total minus rounded dedicated-equipment revenue'
params['aftermarket_base']['rationale']='Derived subtraction, not a disclosed spares/services amount; business classification and any recurring share unknown; inherits rounded equipment numerator.'
residual=drivers['afterm_support']
residual.update(title='未拆分非设备残差的透明假设路径',thesis='The unsplit non-equipment residual has a conditional analyst revenue path. Services and other group activities exist, but their shares and a quantitative growth mechanism are not disclosed.',causal_chain=['Company operates services and other activities alongside dedicated equipment','Their allocation within total-minus-equipment residual is undisclosed','Analyst explicitly assumes an already-recognized residual path with broad conditional stresses','Direct-revenue fallback enters consolidated annual revenue without implying measured repeat-purchase causality'],persistence='uncertain',persistence_rationale='Unsplit residual and uncalibrated future paths do not establish a durable installed-base monetization mechanism.',leading_indicators=['Future filing disaggregation of non-equipment revenue and activity definitions','Total recognized revenue minus consistently disclosed dedicated-equipment revenue','A measured service contract/fleet/renewal series if later disclosed'],falsifiers=['A future disaggregation reveals materially different residual composition or duplicate boundaries','Comparable recognized residual revenue falls below assumed low path','Evidence of sales/service/platform mix disproves the assumed residual growth path'],counterevidence_rationale='Read actual group technology risk H1 p33; it is broad contrary context, not a precise residual-business demand forecast. Missing composition, installed base and renewal statistics remain material gaps. Weight1 is an analyst allocation of the residual segment increment, not an identified causal contribution.')
makeclaim('claim_driver_afterm_support',annual['source_id'],'growth_driver','e_afterm_support','FY2025 annual PDF p53, actual after-sales context; no quantitative recurring revenue',service)
for n in residual['evidence_nodes']:
    if n['evidence_id']=='e_afterm_support':n.update(conclusion='After-sales support exists; the source does not quantify recurring revenue or identify the entire residual.',inference_distance='analogical',evidence_type='business_context_not_quantitative_calibration')
cid=makeclaim('claim_residual_platform_context',annual['source_id'],'growth_driver','residual_platform_context','FY2025 annual PDF p48, digital platform business; classification within residual unknown',platform)
node('afterm_support','residual_platform_context','Digital services are part of the group; allocation within non-equipment residual remains undisclosed.',[cid],'analogical')
cid=makeclaim('claim_residual_h1_service_context',half['source_id'],'growth_driver','residual_h1_service_context','2026H1 PDF p23, professional after-sales support; no revenue magnitude',hservice)
node('afterm_support','residual_h1_service_context','H1 confirms service support; no fleet, contract renewals or residual business revenue split.',[cid],'analogical')
cid=makeclaim('claim_residual_h1_other_business',half['source_id'],'growth_driver','residual_h1_other_business','2026H1 PDF p19, purification and digital platform businesses; their assignment to residual unknown',span(hp,19,'子公司中微惠创','的相关研究。'))
node('afterm_support','residual_h1_other_business','Other group businesses exist; their amount and assignment to dedicated equipment vs residual are undisclosed. This supports avoiding all-aftermarket classification, not quantitative residual growth.',[cid],'analogical','business_perimeter_context')
cid=makeclaim('claim_residual_boundary_annual',annual['source_id'],'growth_driver','residual_boundary_annual','FY2025 annual PDF p65, whole semiconductor equipment related revenue and rounded dedicated-equipment subset',span(ap,65,'报告期内，公司半导体设备收入','持续提高。'))
node('afterm_support','residual_boundary_annual','The dedicated-equipment disclosed subset and total permit a rounded residual subtraction; no source line calls that residual all spares/services.',[cid],'direct','reported_aggregate_boundary')
for s in data['segments']:
    if s['name']=='NonEquipmentResidual':
        s['recognition']['aggregation_boundary']='Unsplit mathematical non-equipment residual = total group recognized revenue minus rounded dedicated-equipment revenue; not official operating segment or all aftermarket. Actual spares/services/platform allocations unknown.'
        s['recognition']['trigger']='Already recognized aggregate residual; underlying group point-in-time control-transfer and cost-progress service policies describe accounting only, not future demand or precise residual composition.'
        for sc in s['scenarios'].values():sc['rationale']='Direct_revenue fallback with uncalibrated analyst paths; no fake fleet/renewal, quantity-price decomposition or all-aftermarket attribution.'

# Customer concentration facts bind each actually used future chamber assumption.
concentration=span(ap,219,'于2025 年度','22.15%)。')
for p in data['parameters']:
    if p['parameter_id'].startswith('equipment_units_') and p['kind']=='analyst_assumption':
        cid=makeclaim('claim_concentration_'+p['parameter_id'],annual['source_id'],'parameter',p['parameter_id'],'FY2025 annual PDF p219, customer A concentration, FY2025 39.99% / FY2024 22.15%',concentration)
        p['claim_ids'].append(cid);p['source_ids']=list(dict.fromkeys(p['source_ids']+[annual['source_id']]))
        p['rationale']+=' Checked annual p219 customerA concentration is39.99% vs22.15%; concentration increases vulnerability to a customer-specific pause. This fact does not reveal the client capex plan or quantify this assumed future chamber path.'

# Industry expectations for every cited year and explicit China contrary branch.
semitext=(OLD/'semi_web_open_snapshot.json').read_text(encoding='utf-8')
line168=semitext.split('L168: ',1)[1].split('\nL169:',1)[0].strip()
line181=semitext.split('L181: ',1)[1].split('\nL182:',1)[0].strip()
cid=makeclaim('claim_outside_wfe_2027_2028',semi['source_id'],'growth_driver','outside_wfe_reference','Actual opened official SEMI 2026-07-14 original line168, WFE forecast2027/2028',line168)
next(n for n in drivers['core_etch_acceptance']['evidence_nodes'] if n['evidence_id']=='outside_wfe_reference')['claim_ids'].append(cid)
for did in ['core_etch_acceptance','films_packaging']:
    eid='china_moderation_'+did
    cid=makeclaim('claim_'+eid,semi['source_id'],'growth_driver',eid,'Actual opened official SEMI2026-07-14 original line181, China 2026 growth moderation',line181)
    node(did,eid,'SEMI expects China equipment spending growth to moderate in2026 after elevated prior investment. This weakens automatic copying of global WFE growth into AMEC; no exact company effect estimated.',[cid],'contrary','industry_regional_counterevidence')
tsv=span(hp,16,'报告期内，公司ICP 刻蚀设备类中的8 英寸','新的市场。')
cid=makeclaim('claim_driver_tsv_packaging',half['source_id'],'growth_driver','e_films_packaging','2026H1 PDF p16, TSV equipment in wafer-level/2.5D packaging and 3D via qualification',tsv)
next(n for n in drivers['films_packaging']['evidence_nodes'] if n['evidence_id']=='e_films_packaging')['claim_ids'].append(cid)
drivers['films_packaging']['thesis']='Checked thin-film repeat volume orders and TSV wafer-level/2.5D packaging repeats provide directional opportunities; 3D qualification and future acceptance are not guaranteed revenue.'
next(n for n in drivers['films_packaging']['evidence_nodes'] if n['evidence_id']=='e_films_packaging')['conclusion']=drivers['films_packaging']['thesis']

# Every old contrary node now states only what its actual original risk block supports.
supply=span(hp,32,'近年来，受复杂的国际形势影响','公司销售。')
technology=span(hp,33,'4、研发投入不足导致技术被赶超或替代的风险','不利影响。')
merger=span(hp,33,'（2）并购风险','不利影响。')
for did,pageno,text,conclusion in [('core_etch_acceptance',32,supply,'Import/key-part procurement cycles may delay equipment delivery and sales; this block does not disclose client capex.'),('films_packaging',33,technology,'Inadequate R&D versus leading peers risks technology catch-up or substitution; exact unit/order effect is unknown.'),('afterm_support',33,technology,'Group technology substitution is broad contrary business context; it does not identify residual composition, installed-base contraction or quantified service demand.'),('cmp_ramp',33,merger,'Acquired-company underperformance and unrealized synergy may impair the CMP path; the risk block does not disclose customer capex or a quantified delay.')]:
    makeclaim('claim_contrary_'+did,half['source_id'],'growth_driver','contra_'+did,f'2026H1 PDF p{pageno}, complete relevant risk block',text)
    next(n for n in drivers[did]['evidence_nodes'] if n['evidence_id']=='contra_'+did)['conclusion']=conclusion
    drivers[did]['counterevidence_rationale']=conclusion+' Original fully read; numerical magnitude remains an assumption.'
for did in ['core_etch_acceptance','films_packaging']:
    drivers[did]['falsifiers']=['Actual equipment acceptance/recognized revenue falls below conditional low-path assumptions','Relevant product repeat orders fail to convert into recognized volume','Concentrated client or supply disruption materially reduces accepted units']

# Register actual downloaded official company releases, without pretending CWP ingestion.
receipts=read(ROOT/'announcements_v3_receipts.json')
annpages={r['announcement_id']:{x['page']:x['text'] for x in read(r['pages_path'])} for r in receipts}
annsource={}
for r in receipts:
    if r['announcement_id']=='1225482916':continue # Independent broker opinion, never company guidance.
    aid=r['announcement_id'];sid='amec_cninfo_'+aid
    event={'tool':'SID CninfoAnnouncementClient.fetch_pdf','command_id':'1791447960515666300-v3-official-material-announcements','receipt':r,'identity':'secCode688012 actual discovered official metadata','snapshot_kind':'immutable captured original PDF bytes; auxiliary research only'}
    host={'host_receipt_schema_version':'1.0','issuer':'rf_cn_execution','environment':'unsigned actual logged SID public HTTP transport','tool_name':'SID.fetch_pdf','action':'capture_official_pdf','event_sha256':sha(canonical(event)),'timestamp':r['timestamp_utc']}
    host['receipt_sha256']=sha(canonical(host))
    capture={'capture_schema_version':'1.0','capture_method':'api_response','tool_name':'SID.fetch_pdf','tool_call_id':event['command_id'],'captured_date':ASOF,'snapshot_sha256':r['sha256'],'content_treatment':'untrusted_data_only','prompt_injection_status':'not_reviewed','host_receipt':host}
    capture['receipt_sha256']=sha(canonical(capture))
    s=dict(source_id=sid,source_type='company_release',title=r['title'],publisher='中微公司董事会',url=r['source_url'],published_date=str(r['published_date']),accessed_date=ASOF,page_or_section='Complete original official disclosure PDF; deterministic local parse, no Worker/LLM',capture=capture)
    data['sources'].append(s);sources[sid]=s;annsource[aid]=sid

# New capacity/time facts alter rationale and contrary evidence, never become revenue.
delay=span(annpages['1225482911'],4,'中微临港总部和研发中心项目原计划','2027 年12 月。')
for did in ['core_etch_acceptance','films_packaging']:
    eid='hq_delay_'+did;cid=makeclaim('claim_'+eid,annsource['1225482911'],'growth_driver',eid,'Company disclosure1225482911 PDF p4, full-use date delayed to December2027',delay)
    node(did,eid,'HQ/R&D full predetermined use delayed to2027-12; partial floors already available. This limits assuming instant fully usable capacity, but no chamber ceiling or recognized-revenue loss is disclosed.',[cid],'contrary','official_project_schedule')
for p in data['parameters']:
    if p['parameter_id'].startswith('equipment_units_') and p['kind']=='analyst_assumption':
        p['rationale']+=' Company1225482911 p4 delays full HQ/R&D use to2027-12 with some floors already usable. Quantities retain independent conditional assumptions, not an instantaneous capacity conversion. No published chambers/year ceiling supports a mechanical numerical haircut.'
        cid=makeclaim('claim_capacity_'+p['parameter_id'],annsource['1225482911'],'parameter',p['parameter_id'],'Company1225482911 PDF p4, delayed full-use timing vs assumed accepted units',delay)
        p['claim_ids'].append(cid);p['source_ids'].append(annsource['1225482911'])
targetid='LingangPhaseII_local_sales_at_maturity'
targettext=span(annpages['1225482894'],4,'项目总投资人民币','800 人。')
targetclaim=makeclaim('claim_'+targetid,annsource['1225482894'],'management_target',targetid,'Company1225482894 PDF p4, investment and at-maturity local sales, period/perimeter ambiguous',targettext)
claims[targetclaim].update(support_type='exact_value',extracted_value=300000,unit='万元',period='达产后（未披露年份）')
data['management_targets'].append(dict(target_id=targetid,statement='项目达产后可实现属地贡献销售收入300,000 万元。',metric_name='Lingang PhaseII local contribution sales at maturity',metric_definition='Project local contribution sales after reaching planned operation; not explicitly consolidated external annual recognized revenue',target_period='达产后（未披露年份）',raw_unit='万元',raw_currency='CNY',raw_scale='ten_thousand',raw_target_value=300000,measurement_basis='ambiguous',measurement_periods=[],measurement_rationale='Company p4 does not specify annual vs cumulative revenue or maturity year. The adjacent7年内 modifies patents and cannot be assigned to sales without evidence.',materiality='material',commitment_strength='capacity_plan',scope={'type':'custom','name':'Lingang PhaseII local contribution sales'},perimeter_status='mismatch',perimeter_notes='Local/project contribution metric and maturity timing lack a reconciled external recognized group revenue bridge. Project papers not yet signed as p1/p5 disclose.',comparison='approximately',treatment='unmodeled_data_gap',comparison_value=None,comparison_currency='CNY',comparison_scale='million',normalization_rationale='Raw300000万元 equals3000CNYm only as scale arithmetic; not a normalized annual forecast comparison.',mapped_parameter_ids=[],mapped_scenarios=[],claim_ids=[targetclaim],rationale='Disclose material plan prominently. Do not add3000m to modeled group revenue or treat350000万元 investment as revenue; contract, timing, overlap and external-sales definition remain unresolved.'))

# Bounded triage of every announcement in the genuine19-record window.
reason={
'1225582793':('important','Fund setup/paid contribution progress, complete company original read. Investment/fund capital is not operating recognized revenue; no new dated operating-revenue target found.'),
'1225561867':('not_material_to_revenue','Director/executive completed share-sale notice; no operating activity acquisition/capacity/revenue target indicated in metadata. Metadata-only exclusion, not body checked.'),
'1225556622':('not_material_to_revenue','Existing major-shareholder disposal/1% crossing; no company acquisition/disposal or operating revenue target indicated. Metadata-only exclusion.'),
'1225540276':('superseded_event_notice','Invitation to collective results session; actual fullSeptember10 AMECQ&A already opened and registered, event metadata not substitute for Q&A.'),
'1225482918':('important','Complete loan/CMP project company original read; up-to73041.47万元 intra-group loan funds projects, not sales. p3 ShanghaiZhonggui2025 standalone24411.88万元 has pre-acquisition/subsidiary perimeter, cannot replace AMEC FY2025CMPzero incremental consolidation.'),
'1225482917':('important','Complete related-sales original read.2026 increase20000万元 to110000万元 transaction authorization/expected ceiling, not binding accepted recognized revenue target. Customers2/3 are external related法人 via director, not simply consolidated subsidiaries. No automatic intercompany elimination or revenue increment; disclosure narrows perimeter and customer-risk rationale.'),
'1225482916':('supporting_broker_opinion','Complete broker original read. GuotaiHaitong regulatory verification repeats capex/delay; companysource1225482911 is authoritative management statement. Not separate company revenue target.'),
'1225482915':('duplicate_summary','H1summary superseded by full210-page1225482884 actually opened. No claim summarybody independently read.'),
'1225482911':('important','Complete companycapex original read; fullHQ/R&D usable date2027-12 now checked contrary and parameter-bound rationale. Capital balance/phasecompletion is not chambers or revenue.'),
'1225482906':('duplicate_verification','Brokerverification of sameprepaidreplacement as company1225482893 actuallyread; excluded duplicate opinion, not independentlybodychecked.'),
'1225482905':('supporting_assurance','Auditorfundsverification cross-referenced in completecompany1225482893. Confirms use/replacement cash, not operating revenue target; body not independentlyread.'),
'1225482897':('nonoperating_verification','Brokercashmanagement opinion refersidlefund investment; nonoperating treasury authorization outside recognized company-sales model; body notread.'),
'1225482896':('duplicate_verification','Brokerloanverification duplicates completecompany1225482918; notcompanyguidance/bodychecked.'),
'1225482894':('important','Completecompanyinvestment original read; newlydiscovered300000万元 local-sales maturity plan registered ambiguous/mismatch/unmodeled target; unsignedagreement/capacity not annual revenue.'),
'1225482893':('important','Completecompanycapitalreplacement original read;6004.51万元 prepaidcashreplacement is purchaseconsideration/intermediaryexpense, no newlycommitted operatingrevenue target.'),
'1225482891':('not_material_to_operating_revenue','Idlemoneycashmanagement authorization concerns treasury income not consolidated operating sales. H1fundusecompany1225482882 original independentlyread clarifies existing scope; noticebody notread.'),
'1225482884':('important','Complete latestH1 officialfile alreadyverified viaRF/FF/CWP currentSourceRef, date+transport URL corrected append-only. SellerCMPtargets retained.'),
'1225482882':('important','Complete18-pagecompanyfunduse original read; capitalprojects/cashplacements and accountingfundtables, no new annual recognizedrevenue goal found. Notproductionthroughput estimates.'),
'1225482880':('important','Complete10-pagecompanystrategyassessment read;54products/cumulative8800reactionstages and historical35% average not futureannual revenue. Mentions revenuegrowth incentiveconditions without disclosing values/periods; precise incentive target remains explicit data gap, not silently treated asno target.')}
triage=[]
for raw in read(OLD/'recent_cninfo_metadata.json')['announcements']:
    aid=raw['announcementId'];importance,why=reason[aid];r=next((r for r in receipts if r['announcement_id']==aid),None)
    triage.append(dict(announcement_id=aid,title=raw['announcementTitle'],importance=importance,reason=why,read_status='complete_original_opened' if r else 'existing_full_h1_opened' if aid=='1225482884' else 'metadata_triage_only',body_path=r['path'] if r else None,body_sha256=r['sha256'] if r else None,source_id=annsource.get(aid),issuer_role='broker_verification' if aid=='1225482916' else 'company_statement' if aid in annsource else 'metadata_only',formal_mapping='target/rationale only when checked original and applicable; funds not revenue'))
dump(ROOT/'announcement_triage_v3.json',triage)
coverage=next(x for x in data['management_communication_coverage'] if x['category']=='material_announcements_since_last_filing')
coverage.update(status='checked',source_ids=[half['source_id']]+list(annsource.values()),conclusion='All19 genuineCNINFOrecords individuallytriaged in announcement_triage_v3.json; eightrelevant companyoriginals +onebrokerfullopinion actuallyopened. Othermetadata-only exclusions haveexplicit revenue-scope/duplicate reasons, are not claimedbodychecked. FoundPhaseII localmaturity300000万元 plan registeredambiguous+mismatch gap. HQ/R&Dfulldate2027-12 checked; funds/loans/treasury not revenue. Strategy1225482880 mentions equityincentive revenueconditions withoutnumber/date; exactincentive schedule remains unfetched/missing and not assumedabsent.',material_revenue_target_ids=[x['target_id'] for x in data['management_targets']])
# Checked strategy communicates qualitative incentive-target existence, no fabricated amount.
strategy=next(x for x in data['management_communication_coverage'] if x['category']=='latest_strategy_communication')
strategy['source_ids'].append(annsource['1225482880']);strategy['conclusion']+=' Complete2026strategyassessment1225482880 read; unspecified revenue-growth incentive thresholds remain a gap; historical35% is not forecast.'
for rec in data['research_coverage']:
    rec['rationale']+=' NonEquipmentResidual is unsplit total-minus-rounded-equipment, not all-aftermarket; its direct_revenue path is uncalibrated. All attribution weights are analyst allocations rather than measured causes.'
    if rec['dimension'] in ['company_foundation','growth_curve','demand']:
        rec['parameter_ids']+=['aftermarket_revenue_base_2026','aftermarket_revenue_base_2027','aftermarket_revenue_base_2028']
    if rec['dimension']=='demand':rec['conclusion']=rec['revenue_mechanism']='Accepted chambers drive Equipment. The unsplit non-equipment residual uses transparent conditional direct_revenue assumptions; service/platform context does not quantify repeat demand.'
    if rec['dimension']=='capacity':
        rec['conclusion']=rec['revenue_mechanism']='Sold/produced/inventory chambers are historical. HQ/R&D fulluse delayed2027-12; partialfloors alreadyusable. PhaseII local-sales plan has unclearperiod/perimeter. No hardfutureaccepted chamberceiling disclosed.'
        rec['source_ids']+= [annsource['1225482911'],annsource['1225482894']]
        rec['rationale']+=' Exact incentiveschedule mentionedstrategy1225482880 is not obtained; inability to numerically benchmark it is a gap.'
    if rec['dimension']=='customers':rec['rationale']+=' Annualp219 concentration fullsource nowbound to allninefutureunit assumptions. Relatedpartyexpected sales limits do not represent guaranteed recognizedrevenue.'
    if rec['dimension']=='industry_market':rec['rationale']+=' SEMI21.8%/14.1% andChina2026moderation have separate completeoriginal checkedgrowthclaims; no quantitative AMECelasticity inferred.'
for x in data.get('sensitivity_tests',[]):
    if 'aftermarket' in x.get('parameter_id',''):x['name']='终年未拆分非设备残差收入±20%（无量化复购机制）'
for rec in data['research_coverage']:rec['parameter_ids']=list(dict.fromkeys(rec.get('parameter_ids',[])))
dump(OUT/'input.json',data)
dump(ROOT/'v3_input_repair_receipt.json',{'forecast_version':data['forecast_version'],'changed_claim_ids':change,'claims_total':len(data['evidence_claims']),'sources_total':len(data['sources']),'new_targets':[targetid],'new_h1_response_path':str(responsepath),'new_h1_url':half['url'],'full_context':context,'retained_numeric_assumptions':True,'new_material_gaps':['Residual composition/renewal calibration unavailable','PhaseII targetyear/measurement/perimeter unclear','1225482880 equityincentive revenueconditions mention withoutnumeric/year original schedule; not yet obtained'],'status':'constructed, pending formal validation and independent review'})
print(json.dumps({'input_path':str(OUT/'input.json'),'sha256':sha((OUT/'input.json').read_bytes()),'changed_claims':len(change),'new_target':targetid},ensure_ascii=False))
