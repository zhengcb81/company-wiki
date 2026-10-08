"""Single-batch MSFT v2 repair. Frozen v1 and executor manifest are read-only."""
from pathlib import Path
from lane_tools import LANE, OUTPUT, RF, event, write
import argparse, copy, datetime, hashlib, json, math, os, re, subprocess, sys
sys.path.insert(0,str(RF/'scripts'))
from contracts.evidence import text_sha256
V2=OUTPUT/'v2'; VERSION='2026-10-08-MSFT-v2'
REVIEW=LANE.parents[1]/'reviews/US-MSFT'
FROZEN=[OUTPUT/'input.json',OUTPUT/'forecast.json',OUTPUT/'forecast.md',OUTPUT/'snapshot.json',LANE/'manifest.json']

def load(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def environment():
    env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',REVENUE_PUBLICATION_REGISTRY=str(V2/'publications.jsonl'),CWP_AUDIT_PROCESS_DIR=str(LANE/'processes'))
    env['PYTHONPATH']=str(LANE.parents[1]/'process_trace')+os.pathsep+str(RF/'scripts')+os.pathsep+env.get('PYTHONPATH','')
    return env

def run_cli(name,args,expected=0):
    proc=subprocess.run([sys.executable,'-X','utf8',*map(str,args)],capture_output=True,env=environment(),cwd=RF,timeout=90)
    (LANE/(name+'_stdout.txt')).write_bytes(proc.stdout);(LANE/(name+'_stderr.txt')).write_bytes(proc.stderr)
    ok=proc.returncode==expected
    event('repair-v2',name,tool='installed RF CLI',outcome='PASS' if ok else 'FAIL',returncode=proc.returncode,command=list(map(str,args)),registry=str(V2/'publications.jsonl'))
    sys.stdout.buffer.write(proc.stdout);sys.stderr.buffer.write(proc.stderr)
    return proc.returncode

def build():
    V2.mkdir(exist_ok=True)
    if (V2/'snapshot.json').exists():raise RuntimeError('v2 already frozen; preserve it and use a new version for further changes')
    old=load(OUTPUT/'input.json');data=copy.deepcopy(old)
    before={str(p):sha(p) for p in FROZEN};write(LANE/'v1_frozen_before_v2.json',before)
    review=load(REVIEW/'review.json');recommendations=load(REVIEW/'support/assumption_support_recommendations.json')
    assert {f['id'] for f in review['findings']}=={'US-01','US-02','US-03','US-04','US-05','US-06','US-07','US-08'}
    sources={s['source_id']:s for s in data['sources']};claims={c['claim_id']:c for c in data['evidence_claims']};params={p['parameter_id']:p for p in data['parameters']}
    call=(OUTPUT/'call.txt').read_text(encoding='utf-8').splitlines();fragments={};fullcontexts={}
    def text(lines):return '\n'.join(call[i-1] for i in lines)
    def set_claim(cid,sid,excerpt,locator):
        c=claims[cid];s=sources[sid]
        chunks=[excerpt[i:i+450] for i in range(0,len(excerpt),450)]
        if len(chunks)>1 and len(chunks[-1])<10:
            tail=chunks.pop();chunks[-1]+=tail
        c.update(source_id=sid,excerpt=chunks[0],locator=locator,excerpt_sha256=text_sha256(chunks[0]),content_sha256=s['capture']['snapshot_sha256'],capture_receipt_sha256=s['capture']['receipt_sha256'],verification_status='opened_and_checked',verified_by='/root/rf_us_execution',verified_date='2026-10-08')
        fragments[cid]=[]
        fullcontexts[cid]=dict(source_id=sid,locator=locator,full_checked_context=excerpt,excerpt_sha256=text_sha256(excerpt),schema_fragment_reason='each evidence excerpt maximum500characters; all fragments referenced together')
        for i,chunk in enumerate(chunks[1:],2):
            fragment=copy.deepcopy(c);newid=cid+'_part'+str(i)
            fragment.update(claim_id=newid,excerpt=chunk,excerpt_sha256=text_sha256(chunk),locator=locator+f'; checked-context fragment{i}/{len(chunks)}')
            data['evidence_claims'].append(fragment);claims[newid]=fragment;fragments[cid].append(newid)
        return cid
    def add_claim(cid,target,typ,sid,excerpt,locator,support='rationale_support'):
        c=dict(claim_id=cid,target_type=typ,target_id=target,support_type=support)
        data['evidence_claims'].append(c);claims[cid]=c
        return set_claim(cid,sid,excerpt,locator)
    specs={
      'Azure':dict(prior=72610,base=101938,positive=[243,318,319,320],contrary=[317,332,337],context=[274],limits='New Azure excludes GitHub/developer/security and healthcare shifted in FY27. The Q1 44–45% constant-currency guide and FX less-than1point drag are quarterly context, with no valid equation to annual reported growth. Demand is not delivery; annual rate depends on capacity live dates, monetized usage, pricing and FX.',fade='FY28/29 assume incremental delivered usage remains positive but growth moderates on a larger revenue base and normalization of early capacity gains; no dated company target proves this fade.',range='FY27 low30/base38/high45% bracket weaker capacity conversion versus continued efficient delivery. These are independent annual reported choices informed by restated FY26 40.4% growth, not a same-basis conservative bound from quarter CC guidance.'),
      'Microsoft 365 cloud':dict(prior=84605,base=100299,positive=[236,238,361,362],contrary=[268],context=[177,183,365,366,367],limits='Whole annual stream includes consumer and newly moved developer/security cloud. Commercial-only growth/paid period-end seats, premium-SKU mix and Q1 CC guide do not equal its annual recognized revenue. No paid-user average or realized ARPU was disclosed for this perimeter.',fade='FY28/29 assume paid deployment and usage monetize, with slower growth as the base expands and new lower-ARPU seats dilute mix. Rollout/preview timing alone does not establish adoption, usage billing or retention.',range='FY27 low12/base17/high22% express weak versus sustained premium/consumption adoption around restated whole-cloud FY26 growth18.6%; later paths retain explicit paid-monetization uncertainty, not a conversion of commercial-quarter targets.'),
      'Productivity and server licensing':dict(prior=35391,base=37285,positive=[237,244],contrary=[255,275],context=[269],limits='New stream combines server/M365 commercial and consumer licenses. July full-year mid-single decline applies named old product KPIs, not a precise-5% new aggregate. Q1 new low-single decline is quarter-only; in-period long-contract/control-transfer timing causes seasonality.',fade='FY28/29 assume launch comparables normalize while cloud migration continues. Smaller declines or high-case slight growth require new licensing/renewal delivery, not merely cloud TAM; no supporting multi-year license guidance exists.',range='FY27 low-8/base-5/high-2% are analyst downside/central/less-severe ranges after FY26 recognized licensing growth5.35%, considering launch-comparable reversals and actual renewal timing. Base-5 is not a sourced midpoint of mid-single.'),
      'Industry solutions':dict(prior=18417,base=20345,positive=[191,192,193,240],contrary=[240],context=[272],limits='New stream includes Dynamics, LinkedIn Talent/Sales, healthcare cloud and products. Industry-cloud subset12%reported/10%CC and new quarter high-single do not determine combined annual recognized revenue. Patient encounters/utilization do not specify fees, contract mix or recognized sales.',fade='FY28/29 assume ERP/healthcare delivered adoption persists while CRM and customer implementation cycles limit acceleration. Changes are conditional forecast ranges; no quantified cohort, fee or renewal bridge is available.',range='FY27 low5/base9/high13% surround reduced versus durable delivered expansion after new-perimeter FY26 growth10.47%, balancing ERP strength/healthcare usage against disclosed CRM moderation and longer sales cycles.'),
      'Frontier and support services':dict(prior=7760,base=8260,positive=[198,199,200,201,202],contrary=[200],context=[198,199],limits='New-name stream is unchanged Enterprise/partner services.6000 experts and330 completed projects/164 customers are delivery/capability facts, not billed volumes, rates or future backlog. Support/consulting is recognized as service is delivered; fee/milestone and renewal bridges remain missing.',fade='FY28/29 assume steady paid implementation/support attach with gradual slower growth as the base expands. Low case assumes poor conversion of engagements to payable delivery; high case assumes stronger attach. No headcount-times-rate forecast is fabricated.',range='FY27 low2/base6/high9% are conditional paid-delivery paths around FY26 actual growth6.44%; project examples support capability, not the exact future rate. The observed completed-project scale constrains claims of explosive new revenue, but is not an observed declining-demand counterexample.'),
      'Search and advertising':dict(prior=22171,base=24835,positive=[208,239,248],contrary=[248,278],context=[278],limits='New annual gross/mixed advertising stream includes LinkedIn Marketing/Premium. Restated exTAC annual14% and quarter mid-to-high-single are net KPI/context, not a same-basis growth rate for the entire recognized stream. Volume/yield, TAC and principal-agent mix are not quantified separately.',fade='FY28/29 assume demand/yield persists at moderating growth while partnership effects constrain distribution. No extrapolation of share gains or engagement counts directly into revenue.',range='FY27 low3/base8/high12% bracket partnership drag versus continued monetized yield/volume after new annual stream FY26 growth12.01%; all remain analyst annual gross/mixed recognized ranges, not exTAC-to-gross conversions.'),
      'XBOX':dict(prior=23455,base=21790,positive=[204,249,279],contrary=[205],context=[279],limits='Xbox perimeter unchanged: content/services and hardware. FY26 total declined7.1% and Q4 old total declined10%; future content/hardware decline statements are quarter-only. CEO expects total gaming FY27 growth, a genuine opposing annual expectation. Base-4% openly disagrees.',fade='FY28/29 base2/4% and high8/8% require successful content/platform reset and paid monetization; no verified launch schedule, delivery fees or cohort retention proves that recovery. Low-5/0% keeps reset ineffective. These are conditional choices.',range='FY27 low-10/base-4/high2% express failed/partial/successful reset after actual annual decline, with high case allowing the management-positive annual direction; no cases are forced to the management expectation.'),
      'Windows OEM and devices':dict(prior=17315,base=17087,positive=[247,256,277],contrary=[247],context=[256,277],limits='New stream includes small Other reclassification; devices/OEM demand and elevated inventory, component prices and Windows10-end-support comparable drive headwinds. Management high-teens is retained wording; base-18% is an independent assumption. Q1 low20s is not an annual bridge.',fade='FY28/29 stabilization assumes inventories normalize and component/comparable pressure eases. There is no observed Windows recovery evidence at asof; low continues declines, base moves-3/0%, high3/5%, all conditional.',range='FY27 low-23/base-18/high-13% explicitly bracket severe versus milder annual headwinds. Management wording informs direction only, not an invented exact18% target. FY26 annual-1.32% is historical context, not proof of future decline magnitude.')}
    support_map=[]
    for seg in data['segments']:
        name=seg['name'];s=specs[name];slug=re.sub(r'[^a-z0-9]+','_',name.lower()).strip('_')
        history_excerpt=f'{name}; Fiscal Year 2025 ${s["prior"]:,}; Fiscal Year 2026 ${s["base"]:,}. ($ in millions).'
        historical_growth=s['base']/s['prior']-1
        for scenario in ['low','base','high']:
            for pid in seg['scenarios'][scenario]['driver_parameter_ids']['growth_rate']:
                p=params[pid];year=int(p['period'][2:]);original=p['claim_ids'][0]
                assert original in recommendations[name]['claim_ids']
                set_claim(original,'src_call',text(s['positive']),f'Official complete FY26Q4 call.txt lines {s["positive"]}; operating mechanism; July old perimeter reconciled using PPT7/8/13')
                hist=add_claim('v2_history_'+pid,pid,'parameter','src_presentation',history_excerpt,'PPT17 As Restated, FY2025/FY2026 annual row; manually checked image17.png; normalized two-cell visual transcription')
                downside=add_claim('v2_constraint_'+pid,pid,'parameter','src_call',text(s['contrary']),f'Complete official call.txt lines {s["contrary"]}; constraint/opposing gaming expectation; scope stated in parameter rationale')
                qcontext={'Azure':'Growth of 44% to 45% in constant currency, with FX expected to decrease revenue by less than 1 point','Microsoft 365 cloud':'Growth of approximately 17% in constant currency; Growth of approximately 18% in constant currency when adjusting for prior-year in-period revenue recognition','Productivity and server licensing':'Decline in low-single digits','Industry solutions':'Growth in high-single digits','Search and advertising':'Growth in mid- to high-single digits','XBOX':'Content and services revenue expected to decline in mid-single digits; Hardware revenue should decline year-over-year','Windows OEM and devices':'Decline in low-twenties'}
                context=add_claim('v2_context_'+pid,pid,'parameter','src_presentation',qcontext[name],f'PPT21 adjusted FY27Q1 outlook row for {name}; named subset/CC/exTAC qualifications in parameter rationale; no annual conversion') if name in qcontext else None
                # All newly bound claims are context/rationale, never exact future extracted values.
                p['claim_ids']=[original,hist,downside]+([context] if context else []);p['source_ids']=['src_call','src_presentation']
                p['rationale']=f'{name}: same-perimeter FY25→FY26 recognized history {s["prior"]}→{s["base"]} USDmillion ({historical_growth:.3%}, calculated history). '+s['range']+' '+s['limits']+' '+(s['fade'] if year>2027 else 'FY27 range is judgment about how observed mechanisms and constraints translate to paid annual delivery.')+f' This {scenario} {year} value {p["value"]:.0%} is an analyst assumption, not a quoted company forecast, calibrated bound or predicted probability.'
                p['definition']=p['rationale']
                support_map.append(dict(parameter_id=pid,old_claim_id=original,new_claim_ids=p['claim_ids'],historical_growth_calculated=historical_growth,mechanism_call_lines=s['positive'],constraint_call_lines=s['contrary'],perimeter_limits=s['limits'],analyst_range_and_fade=s['range']+' '+s['fade'],future_value_unchanged=p['value']==next(x['value'] for x in old['parameters'] if x['parameter_id']==pid)))
            seg['scenarios'][scenario]['rationale']=s['range']+' '+s['limits']+' '+s['fade']+' Independent conditional '+scenario+' path; no scenario probability.'
    assert len(support_map)==72
    for test in data['sensitivity_tests']:test['shock_value']=0.05
    data['forecast_version']=VERSION

    def tree_claim(cid,lines):return set_claim(cid,'src_call',text(lines),f'Complete official call.txt lines {lines}; exact paragraphs, evidence-node scope explicitly limited')
    tree={r['driver_id']:r for r in data['growth_driver_tree']['drivers']}
    tree_claim('claim_102_cloud_ai_company',[243,236]);tree_claim('claim_103_cloud_ai_contrary',[317,268])
    tree_claim('claim_105_enterprise_migration_company',[191,198,199,200,240])
    tree_claim('claim_106_enterprise_migration_contrary',[240])
    tree_claim('claim_107_advertising_company',[248,239]);tree_claim('claim_108_advertising_contrary',[278])
    tree_claim('claim_109_consumer_cycle_company',[256,249,279]);tree_claim('claim_110_consumer_cycle_contrary',[205])
    tree['enterprise_migration']['evidence_nodes'][0]['conclusion']='Observed delivered Frontier projects and healthcare/ERP adoption support service/industry capability and activity, not exact future sales. Licensing has a separate negative path from cloud migration and launch comparables.'
    tree['enterprise_migration']['evidence_nodes'][1]['conclusion']='CRM bookings moderation and longer sales cycles oppose sustained enterprise solutions expansion. This is actual contrary context for Industry solutions; it is not a claimed direct Frontier backlog decline.'
    # A separate negative-flow node avoids pretending license headwinds support service upside.
    licensecid=add_claim('v2_license_headwind','enterprise_migration_license_headwind','growth_driver','src_call',text([255,275]),'call.txt255 full-year named-product decline and275 old-server Q1 migration; not exact new-aggregate magnitude')
    tree['enterprise_migration']['evidence_nodes'].append(dict(evidence_id='enterprise_migration_license_headwind',evidence_type='company_license_migration_headwind',inference_distance='one_step',conclusion='Negative license curve is a distinct component: migration/comparable headwinds lower recognized product revenue; do not use it as positive service evidence.',claim_ids=[licensecid]))
    tree['consumer_cycle']['evidence_nodes'][1]['conclusion']='CEO FY27 gaming return-to-growth expectation directly opposes negative FY27 Xbox base thesis; gaming only, not Windows. It is expectation, not delivered recovery. No Windows stabilization counterevidence found asof.'
    tree['consumer_cycle']['counterevidence_rationale']='Actual annual gaming-positive management expectation binds contrary node. It can weaken Xbox headwind magnitude; cannot prove Windows recovery. Windows stabilization in FY28/29 is an explicit evidence gap.'
    mechanisms={
      'cloud_ai':dict(causal_chain=['Enterprise workloads and paid Copilot deployments create demand, not yet revenue','Capacity live dates and CPU/GPU efficiency permit Azure consumed usage; paid tiers plus delivered usage monetize M365','Azure recognizes consumed services and M365 subscription/usage service delivery under policy; no RPO or period-end-seat multiplication','Direct annual growth fallback approximates these separate paid-delivery flows without undisclosed volume/price data'],leading_indicators=['Azure delivered usage/capacity timing and pricing, qualitative quarterly diagnostic without modeled threshold','M365 commercial premium mix and paid deployment/consumption; commercial subset and period-end seats are not whole annual cloud','Restated annual external Azure and whole M365cloud revenue in USD'],falsifiers=['FY2027 restated annual reported Azure growth below low-case30% would reject the chosen sustained-demand/delivery magnitude; below that is not simply a quarter CC miss','FY2027 whole Microsoft365cloud annual recognized growth below low-case12% would reject the chosen paid-monetization magnitude; use same restated perimeter','No quantified quarterly falsifier: capacity/usage shifts are diagnostics until a same-perimeter quarterly model exists']),
      'enterprise_migration':dict(causal_chain=['Cloud migration and launch comparables reduce delivered product/license revenue as a distinct negative curve','ERP/healthcare workflows and delivered consulting/support engagements generate separate positive industry/services activity','License control transfers/in-period allocations and delivered services/cloud usage determine recognized annual flows; their mix is undisclosed','Sum licensing negative and industry/support conditional positive curves on the FY27 restated perimeter; direct fallback does not infer fees from projects'],leading_indicators=['ERP bookings versus CRM implementation-cycle moderation, diagnostic only','Actually billable Frontier/support delivery and renewals; completed projects/headcount alone lack fee bridge','Same-perimeter annual licensing, industry solutions and Frontier/support revenue separately'],falsifiers=['FY2027 Industry solutions annual growth below low-case5% or Frontier/support below2% rejects the positive expansion magnitude on each named flow','FY2027 annual licensing growth above high-case-2% weakens the negative migration/comparable severity; stronger negative growth reinforces headwind rather than falsifies it','No quarter threshold or assumed fee per project; future annual flow disclosures must match new perimeter']),
      'advertising':dict(causal_chain=['Bing/Edge monetized search volume/yield and LinkedIn Marketing/Premium paid activity support demand','Distribution partnerships and TAC influence monetized reach/net yield and therefore constrain annual sales','Advertising delivery/actions and subscription service delivery recognize the reported gross/mixed annual stream; exTAC KPI is distinct','Direct recognized growth fallback combines flows without inventing searches, CPM, TAC or principal-agent conversion'],leading_indicators=['Monetized search volume and revenue per search with third-party partnership effects, qualitative diagnostics','LinkedIn Marketing/Premium paid activity on new scope, not LinkedIn total membership','Restated annual Search/advertising recognized revenue; distinguish exTAC net KPI'],falsifiers=['FY2027 same-perimeter annual recognized Search/advertising growth below low-case3% rejects the positive monetization magnitude','A disclosed loss of distribution/paid ad demand that stops monetized delivery would challenge the mechanism; no numeric threshold claimed without source','A low quarterly exTAC print alone is not a same-basis annual gross falsifier']),
      'consumer_cycle':dict(causal_chain=['PC component prices, lower demand, inventory and end-support comparable lower OEM/device delivered transactions','Xbox weak content comparable and reset constrain content/services and hardware separately; annual positive gaming expectation is contrary evidence','OEM licenses/devices recognize control-transfer deliveries and gaming recognizes content/control or delivered subscriptions, aggregated mixed','FY27 negative Windows/Xbox paths and later conditional stabilization are annual direct fallback; no unproved AI TAM or launch uplift'],leading_indicators=['OEM/channel inventory and pricing/comparable developments, qualitative diagnostics only','Paid gaming content/hardware delivery and actual reset outcomes; annual management expectation alone is not actual recovery','Same-perimeter annual Xbox and WindowsOEM/devices recognized revenue, independently'],falsifiers=['FY2027 Xbox annual recognized growth above high-case+2% rejects the chosen negative FY27 gaming severity; below-low-10% reinforces the headwind and challenges range, not its negative direction','FY2027 WindowsOEM/devices annual growth above high-case-13% rejects the assumed negative PC severity; gaming recovery says nothing about Windows','For FY2028/29 Xbox base+2/+4% and Windows-3/0%, continued annual declines below those respective conditional stabilization paths reject that recovery assumption; no quarterly threshold is claimed'])}
    for rid,fields in mechanisms.items():tree[rid].update(fields)

    annualtarget=data['management_targets'][-1];tid=annualtarget['target_id']
    histall='; '.join(f'{n}: FY2025 {s["prior"]}, FY2026 {s["base"]}' for n,s in specs.items())+'; consolidated FY2025 281724, FY2026 331839 USDmillion.'
    set_claim('claim_122_company_fy27_double_digit','src_presentation',histall,'PPT17 As Restated all8 annual rows and total; normalized visual table transcription, historical scale/changes only')
    bclaims=['claim_122_company_fy27_double_digit']
    for name,s in specs.items():
        slug=re.sub(r'[^a-z0-9]+','_',name.lower()).strip('_')
        bclaims.append(add_claim('v2_benchmark_mechanism_'+slug,tid,'management_target','src_call',text(s['positive']),f'call.txt{s["positive"]}; observed mechanism used in independently chosen annual {name} path'))
        bclaims.append(add_claim('v2_benchmark_constraint_'+slug,tid,'management_target','src_call',text(s['contrary']),f'call.txt{s["contrary"]}; opposing constraint/scope used in annual {name} assumptions'))
    annualtarget['benchmark_claim_ids']=bclaims
    annualtarget['benchmark_rationale']='Independent eight-stream annual recognized paths derive from FY25/FY26 restated history plus each stream delivered-use/paid-mix/license/ERP/services/advertising/device mechanisms and opposing constraints; precise ranges remain analyst judgment with fallback and evidence gaps. AWS37% remains analogical category context in cloud evidence only, not consolidated magnitude support. All three cases are compared after construction to the >=10% linguistic floor; they are not forced to meet guidance.'
    data['data_gaps'].extend(['V2:72 future annual ranges/fades are analyst judgments, not source point forecasts or calibrated intervals; operating quantity/price bridges remain unavailable.','V2:All material qualitative targets and launch/usage commitments are mapped individually in qualitative_targets_v2.json; numeric-only formal ledger cannot encode them without invented points. Its presence gates do not certify semantic completion.','V2:Azure38%annual reported is independent; Q144–45%CC cannot prove a same-basis conservative bound.','V2:US07 acquisition/FF-ET/CWP canonical HTML and latest annual policy remain BLOCKED; only observed existing-source reuse was successful.'])
    def expand_refs(obj):
        if isinstance(obj,dict):
            for key,value in obj.items():
                if key.endswith('claim_ids') and isinstance(value,list):
                    obj[key]=[item for cid in value for item in [cid,*fragments.get(cid,[])]]
                else:expand_refs(value)
        elif isinstance(obj,list):
            for value in obj:expand_refs(value)
    expand_refs(data);expand_refs(support_map)
    write(V2/'input.json',data);write(LANE/'assumption_support_v2.json',support_map)
    write(LANE/'claim_contexts_v2.json',fullcontexts)
    build_qualitative(data,call,specs)
    write(LANE/'repair_v2_build.json',dict(version=VERSION,findings=[x['id'] for x in review['findings']],future_parameter_count=len(support_map),all_growth_values_preserved=all(x['future_value_unchanged'] for x in support_map),claim_count=len(data['evidence_claims']),frozen_before=before,us07='BLOCKED',review_files=dict(review_sha256=sha(REVIEW/'review.json'),recommendations_sha256=sha(REVIEW/'support/assumption_support_recommendations.json'))))
    event('repair-v2','build v2 with all72 supported assumptions,8 ratio0.05 shocks,4 scoped mechanisms,benchmark and mapped qualitative ledger',outcome='built_not_self_accepted',artifacts=[str(V2/'input.json'),str(LANE/'assumption_support_v2.json'),str(LANE/'qualitative_targets_v2.json')],frozen_v1_unchanged=all(sha(Path(p))==h for p,h in before.items()),new_web_source=str(V2/'strategy_reopen_web.json'),source_slides_reread=[7,13,17,18,21])
    print(json.dumps(dict(version=VERSION,claims=len(data['evidence_claims']),future_parameters=72,us07='BLOCKED')))

def build_qualitative(data,call,specs):
    oldrows=load(LANE/'communication_coverage.json')['qualitative_targets']
    params={p['parameter_id']:p for p in data['parameters']};rows=[]
    # Original sixteen full-call passages receive an explicit, individual scope and treatment.
    mapping={108:('Infrastructure capacity','two years; terminal date unstated',['Azure'],'Capacity is only an enablement condition; no capacity-to-utilization/price revenue bridge. Retain roughly double wording, not a 100% revenue target.'),205:('XBOX total','FY2027',['XBOX'],'Compare annual same-perimeter direction: management expects positive growth; analyst low-10/base-4 disagree, high+2 agrees direction. No exact management rate is invented.'),255:('Old M365commercial/server product KPIs','FY2027',['Productivity and server licensing'],'Directionally consistent with negative FY27 three scenarios(-8,-5,-2%); new aggregate includes consumer/licenses and reclass, so no exact target attainment. Base-5 is assumption, not mid-single normalization.'),256:('Windows OEM and devices','FY2027',['Windows OEM and devices'],'Compare negative annual direction only; low-23/base-18/high-13 are assumptions, not inferred endpoints of high-teens. Scope has small Other reclass.'),257:('Company FX effect','FY2027',[],'Conditional current-rates FX<1pp drag; no annual currency bridge or FX adjustment parameter. Explicit unmodeled risk; cannot subtract from CC quarterly guidance to derive an annual rate.'),258:('Company total revenue','FY2027',[*specs],'Formal numeric ledger records only >=10% linguistic floor, compares all scenarios after construction. Non-revenue opex/CapEx/tax portions are outside revenue scope.'),264:('Commercial bookings excluding OpenAI','FY2027Q1',['Azure','Microsoft 365 cloud','Industry solutions'],'Bookings is not recognized revenue; healthy growth no numeric point, expiry-base/OpenAI volatility matters. No conversion model, unmodeled with context mappings only.'),268:('Old M365commercial cloud','FY2027Q1 and throughFY2027',['Microsoft 365 cloud'],'Old Q1 15%CC/16%adjusted superseded mechanically by PPT21 17/18 on new commercial scope; whole annual cloud includes consumer/developer. Annual case12/17/22 not same-basis target attainment. Acceleration-through-year remains qualitative.'),269:('Old M365commercial products','FY2027Q1',['Productivity and server licensing'],'Quarter mid-single positive differs from annual negative and new quarter aggregate low-single decline; only directional contract-timing context, no quarterly model or target comparison.'),270:('M365consumer cloud','FY2027Q1',['Microsoft 365 cloud'],'Quarter mid-teens subset unchanged under PPT21; full annual cloud cannot be mapped quantitatively without consumer weight/mix; no midpoint invented.'),271:('Old LinkedIn total','FY2027Q1',['Industry solutions','Search and advertising'],'High-single old total splits Talent/Sales into Industry and Marketing/Premium into Search; no component bridge. Explicit mismatch, no annual comparison.'),272:('Dynamics365','FY2027Q1',['Industry solutions'],'Low-teens cloud subset includes ERP strength and CRM moderation; new Industrycloud quarter high-single on wider scope. No quarterly/whole annual conversion.'),274:('Old Azure and other cloud services','FY2027Q1 and H1FY2027',['Azure'],'Old45%CC quarter mechanically new44–45%CC on narrower Azure scope; H1acceleration is expectation. Annual38reported separate, FX/capacity uncertain; no conservative same-basis bound.'),275:('Old onpremserver','FY2027Q1',['Productivity and server licensing'],'Low-to-mid-single decline quarter on old subset; new licensing aggregate quarter low-single decline. No annual midpoint or quantitative same-basis comparison.'),278:('Old search advertising exTAC','FY2027Q1',['Search and advertising'],'Old mid-single quarter mechanically new mid-to-high-single exTAC including LinkedInMarketing/Premium. Net KPI cannot convert to recognized gross/mixed annual rate.'),279:('Xbox content/services and hardware','FY2027Q1',['XBOX'],'Content mid-single decline and hardware decline are subsets/quarter; annual total base-4 is independently judged and disagrees with annual positive management expectation. No quarter model.')}
    def ids(names,year=None):
        prefixes=[re.sub(r'[^a-z0-9]+','_',n.lower()).strip('_')+'_growth_' for n in names]
        return [pid for pid in params if any(pid.startswith(pre) for pre in prefixes) and (year is None or pid.endswith('_'+str(year)))]
    for i,original in enumerate(oldrows):
        row=copy.deepcopy(original);qid=f'v2_qualitative_original_{i+1:02d}'
        if i<16:
            line=int(re.search(r'line (\d+)',row['locator']).group(1));scope,period,names,treatment=mapping[line]
            row['exact_wording']=call[line-1]
        else:
            scope='FY27Q1 licensing/Industrycloud/exTAC/Xbox/Windows rows (five distinct scopes)';period='FY2027Q1';names=['Productivity and server licensing','Industry solutions','Search and advertising','XBOX','Windows OEM and devices']
            treatment='Split explicit quarter-row statements into children below. No quarter or CC/exTAC conversion to annual recognized revenue.'
        row.update(qualitative_target_id=qid,metric_perimeter=scope,source_period=period,commitment_strength='expectation/guidance' if i<16 else 'mechanical_reclassification_of_prior_outlook',mapped_parameter_ids=ids(names,2027),mapped_scenarios=['low','base','high'] if names else [],mapping_usage='qualitative_context_only_unless_explicit_annual_direction_comparison',comparison_or_gap=treatment,numeric_normalization_performed=False,source_publication_date=row['published_date'])
        row.pop('formal_numeric_ledger_coverage',None);rows.append(row)
    srcs={s['source_id']:s for s in data['sources']}
    def extra(qid,sid,excerpt,locator,period,scope,names,treatment,commitment):
        s=srcs[sid];rows.append(dict(qualitative_target_id=qid,source_id=sid,source_url=s['url'],source_sha256=s['capture']['snapshot_sha256'],source_publication_date=s['published_date'],exact_wording=excerpt,locator=locator,source_period=period,metric_perimeter=scope,commitment_strength=commitment,mapped_parameter_ids=ids(names),mapped_scenarios=['low','base','high'] if names else [],mapping_usage='context_only_not_numeric_forecast_bridge',comparison_or_gap=treatment,numeric_normalization_performed=False))
    extra('v2_cobalt_month_end','src_call',call[117],'call.txt line118 CEO infrastructure','end July2026 (this month relative to July29)','Cobalt200 racks in over25 data centers',['Azure'],'Deployment expectation is past its dated endpoint at asof but no actual completion source verified. No paid workload/price/utilization bridge; do not imply fulfillment or revenue. Retain >25 capability claim only.','dated_operating_expectation')
    extra('v2_healthcare_calendar2026','src_call',call[190],'call.txt line191 CEO healthcare','calendar2026','over100million patient encounters',['Industry solutions'],'Calendar-year usage target with28M quarter actual is not fiscal-year recognized dollars. No fee perencounter or paid-counterparty/recognition bridge; explicitly unmodeled numeric operating target with qualitative linkage.','operating_expectation_on_pace')
    extra('v2_frontier_experts','src_call',call[198],'call.txt line199 CEO Frontier','future deployment timing unstated','6000 industry/engineering experts',['Frontier and support services'],'Capacity commitment, not billable-hour forecast; fees/utilization/paid-milestones unavailable. No headcount-times-rate revenue calculation.','deployment_intention')
    extra('v2_copilot_call_superapp','src_call',call[161],'call.txt line162 CEO knowledge work','this quarter relative to July29 FY2027Q1','Copilot consumer/commercial superapp',['Microsoft 365 cloud'],'Later September25 announcement gives availability windows but no realized usage/contract bridge. Do not assert rollout promise fulfilled solely from preview availability.','product_launch_expectation')
    extra('v2_cowork_usage_billing','src_call',call[176],'call.txt line177 CEO knowledge work','earlier July2026','Cowork usage billing and active paying customers',['Microsoft 365 cloud'],'Actual billing-start statement with no revenue amount/cohort retention. Supports monetization mechanism, not exact future growth or annual average seats.','reported_billing_start')
    strategy=load(V2/'strategy_reopen_web.json')
    if not isinstance(strategy,str):strategy=json.dumps(strategy,ensure_ascii=False)
    sentences=[('v2_copilot_frontier_rollout','Home and Code will start rolling out in our Frontier program in the coming weeks and Autopilot is expanding to private preview at the end of the month.','blog September25 paragraph after Home/Code/Autopilot introduction; fresh web lines8','weeks after September25 /endSeptember2026','Home/Code Frontier and Autopilot private preview','Announcement/preview is not delivered paid customer adoption. As-of completion not independently measured; annual consumption increment unmodeled.'),('v2_code_broad_availability','Code is rolling out to Frontier at the end of the month, with broad availability in the coming weeks.','fresh blog web lines19','endSeptember/comingweeks2026','Code roll-out','Future availability commitment; no billed usage trajectory or price path verified. Do not treat source schedule as realized rollout.'),('v2_copilot_consumer_preview','It will be in preview for Microsoft 365 Premium and Pro subscribers later this year.','fresh blog web line20','later calendar2026','Consumer Premium/Pro Code preview','Preview timing only; no incremental paid conversion/share of annual whole-cloud revenue.'),('v2_ubb_scope','Cowork, Code, and Autopilot, new long-running agentic capabilities, and frontier models like Astra and Fable all run on UBB.','fresh blog web line35','at September25 announcement; feature delivery follows stated availability windows','usage-based billing product scope','Supports delivered-usage monetization contract; not an amount or proof all preview products already generate revenue.'),('v2_finops_october','Cost management in Agent 365 is expanding beyond Cowork and Work IQ APIs to include Code and Copilot Managed Runtime, with support for agents built in Microsoft Copilot Studio planned for October.','fresh blog web line36','October2026 planned','FinOps support for CopilotStudio agents','Spend controls may constrain or facilitate adoption; no outcome sign or revenue amount proven. Future after-asof portions not counted as fulfilled.')]
    for qid,excerpt,loc,period,scope,treatment in sentences:
        assert excerpt in strategy, qid+' missing from actual re-opened primary content'
        extra(qid,'src_strategy',excerpt,loc,period,scope,['Microsoft 365 cloud'],treatment,'dated_product_availability_or_billing_announcement')
        rows[-1]['fresh_reopen_path']=str(V2/'strategy_reopen_web.json');rows[-1]['fresh_reopen_sha256']=sha(V2/'strategy_reopen_web.json')
    for qid,wording,scope,names in [('v2_q1_licensing','Decline in low-single digits','Productivity/serverlicensing',['Productivity and server licensing']),('v2_q1_industry','Growth in high-single digits','Industrysolutionscloud',['Industry solutions']),('v2_q1_search','Growth in mid- to high-single digits','Search/advertising exTAC',['Search and advertising']),('v2_q1_xbox_content','Content and services revenue expected to decline in mid-single digits','XBOXcontent/services',['XBOX']),('v2_q1_xbox_hardware','Hardware revenue should decline year-over-year','XBOXhardware',['XBOX']),('v2_q1_windows','Decline in low-twenties','WindowsOEM/devices',['Windows OEM and devices'])]:
        extra(qid,'src_presentation',wording,'PPT21 adjusted outlook row named metric, visual read image21.png','FY2027Q1',scope,names,'Quarter qualitative statement only; subset/new scope/exTAC distinctions retained. Annual scenarios not compared numerically and no midpoint or x4 conversion.','mechanical_quarter_guidance')
    assert len(rows)>=28 and len({r['qualitative_target_id'] for r in rows})==len(rows)
    write(LANE/'qualitative_targets_v2.json',dict(schema_version='1.0',forecast_version=VERSION,as_of_date='2026-10-08',original_rows_preserved_and_individually_mapped=17,target_count=len(rows),targets=rows,runtime_boundary='Numeric-only formal management ledger cannot express these lexical/operating/availability statements; sidecar preserves scope/comparison/gap without invented numbers. No full acquisition acceptance inferred.'))

def verify():
    from revenue_report import validate_published_forecast,render_markdown
    from revenue_backtest import validate_snapshot
    d=load(V2/'input.json');r=load(V2/'forecast.json');snap=load(V2/'snapshot.json')
    validate_published_forecast(r,d);assert (V2/'forecast.md').read_text(encoding='utf-8')==render_markdown(r)
    validate_snapshot(snap);assert snap['input_document']==d
    params={p['parameter_id']:p for p in d['parameters']};scenarios={}
    for scenario in ['low','base','high']:
        totals={str(y):0 for y in d['forecast_years']}
        for seg in d['segments']:
            prev=params[seg['base_revenue_parameter_id']]['value']
            for y,pid in zip(d['forecast_years'],seg['scenarios'][scenario]['driver_parameter_ids']['growth_rate']):
                prev*=1+params[pid]['value'];totals[str(y)]+=prev
        assert all(math.isclose(totals[y],r['consolidated_forecast'][scenario]['annual_revenue'][y],rel_tol=1e-12) for y in totals)
        assert math.isclose((totals['2029']/331839)**(1/3)-1,r['consolidated_forecast'][scenario]['cagr'],rel_tol=1e-12)
        scenarios[scenario]=totals
    before=load(LANE/'v1_frozen_before_v2.json');after={p:sha(Path(p)) for p in before};assert before==after
    sensitivity_checks=[];baseline=scenarios['base']['2029']
    for t in d['sensitivity_tests']:
        assert t['shock_value']==0.05
        pid=t['parameter_id'];seg=next(s for s in d['segments'] if pid in s['scenarios']['base']['driver_parameter_ids']['growth_rate'])
        rateids=seg['scenarios']['base']['driver_parameter_ids']['growth_rate'];base=params[seg['base_revenue_parameter_id']]['value']
        impact=base*0.05*(1+params[rateids[1]]['value'])*(1+params[rateids[2]]['value'])
        stored=next(s for s in r['sensitivities'] if s['parameter_id']==pid)
        for direction,sign in [('down',-1),('up',1)]:
            expected=params[pid]['value']+sign*0.05
            assert math.isclose(stored['requested_values'][direction],expected,abs_tol=1e-12)
            assert math.isclose(stored['effective_values'][direction],expected,abs_tol=1e-12)
            assert not stored['clamped'][direction]
            assert math.isclose(stored[direction+'_terminal_revenue'],baseline+sign*impact,abs_tol=1e-7)
        sensitivity_checks.append(dict(parameter_id=pid,ratio_delta=0.05,down_terminal=baseline-impact,up_terminal=baseline+impact,clamped=False,status='PASS'))
    concentration=max(s['up_terminal']-baseline for s in sensitivity_checks)/sum(s['up_terminal']-baseline for s in sensitivity_checks)
    assert math.isclose(concentration,r['confidence']['sensitivity_concentration'],rel_tol=1e-10)
    write(LANE/'validation_v2.json',dict(strong_input_required='PASS',same_json_renderer='PASS',independent_annual_arithmetic='PASS',independent_all8_sensitivity_units_requested_effective_clamps_terminals='PASS',snapshot='PASS',frozen_v1_unchanged=True,frozen_before_sha256=before,frozen_after_sha256=after,annual_paths=scenarios,sensitivities=r['sensitivities'],independent_sensitivity_checks=sensitivity_checks,confidence=r['confidence'],confidence_note='Score legitimately unchanged after actual full recomputation: identical linear first-year shocks scale all impacts proportionally; concentration and covered revenue weights are unchanged. Sensitivity intervals changed100fold. Score does not certify exact future rate evidence.',input_sha256=sha(V2/'input.json'),forecast_sha256=sha(V2/'forecast.json'),acceptance='executor technical checks; independent review pending; US07 BLOCKED'))
    event('repair-v2','strong/render/snapshot/independent annual arithmetic/v1 preservation verification',outcome='PASS',artifacts=[str(LANE/'validation_v2.json')],independent_acceptance='pending')
    print(json.dumps(dict(strong='PASS',render='PASS',arithmetic='PASS',snapshot='PASS',v1_unchanged=True,confidence=r['confidence']['score'],sensitivity_count=len(r['sensitivities'])),ensure_ascii=False))

def handoff():
    d=load(V2/'input.json');r=load(V2/'forecast.json');old=load(OUTPUT/'input.json')
    oldclaims={c['claim_id']:c for c in old['evidence_claims']};changes=[]
    for c in d['evidence_claims']:
        if c['claim_id'] not in oldclaims or c!=oldclaims[c['claim_id']]:changes.append(dict(claim_id=c['claim_id'],old=oldclaims.get(c['claim_id']),new=c))
    checks=load(LANE/'validation_v2.json');q=load(LANE/'qualitative_targets_v2.json')
    repair=dict(schema_version='1.0',forecast_version=VERSION,independent_review='pending',findings=[dict(id='US-01',executor_state='implemented_pending_review',old_shock_value=5,new_shock_value=0.05,ids=[t['parameter_id'] for t in d['sensitivity_tests']],test=str(LANE/'validation_v2.json')),dict(id='US-02',executor_state='implemented_pending_review',old='72 claims bind dollar-base only',new='Each72 mechanism+history+constraint+quarter context; precise future ranges/fades remain assumptions',ids=str(LANE/'assumption_support_v2.json')),dict(id='US-03',executor_state='implemented_pending_review',ids=['claim_105_enterprise_migration_company','claim_106_enterprise_migration_contrary','claim_110_consumer_cycle_contrary','v2_license_headwind'],new='Actual Frontier/ERP/healthcare delivery and CRM constraint separated from license negative path; annual gaming growth is gaming-only contrary evidence'),dict(id='US-04',executor_state='implemented_pending_review',ids=['cloud_ai','enterprise_migration','advertising','consumer_cycle'],new='Four unique delivered-use/accounting mechanisms and FY27 annual same-perimeter directional thresholds; no invented quarterly test'),dict(id='US-05',executor_state='implemented_pending_review',ids=d['management_targets'][-1]['benchmark_claim_ids'],old='OnlyAWS37% benchmark',new='Whole restated annual history+eight operating mechanisms/constraints; AWS remainsanalogical, comparison unchanged and not forced'),dict(id='US-06',executor_state='implemented_pending_review',ids=[t['qualitative_target_id'] for t in q['targets']],new='All17 original rows individually scoped/mapped/compared, plus missing timed capability/rollout/billing promises and adjusted quarter row children',remaining_boundary=q['runtime_boundary']),dict(id='US-07',executor_state='BLOCKED',new='No new download, newfile repeat, latest annual policy, integratedFF-ET successfulTXT or canonical HTML Worker claimed'),dict(id='US-08',executor_state='implemented_pending_review',ids=[p['parameter_id'] for p in d['parameters'] if p['parameter_id'].startswith('azure_growth')],new='38% independent annual reported choice; quarter44–45%CC context cannot prove conservative bound')],changed_claims=changes,all_future_annual_values_preserved=True,v1_preservation=checks['frozen_after_sha256'],formal_tests=str(LANE/'validation_v2.json'),command_index=str(LANE/'commands/index.jsonl'))
    oldparams={p['parameter_id']:p for p in old['parameters']}
    assert all(p['value']==oldparams[p['parameter_id']]['value'] for p in d['parameters'])
    repair['parameter_changes']=[dict(parameter_id=p['parameter_id'],old=oldparams[p['parameter_id']],new=p) for p in d['parameters'] if p!=oldparams[p['parameter_id']]]
    repair['growth_driver_tree_change']=dict(old=old['growth_driver_tree'],new=d['growth_driver_tree'])
    repair['annual_management_benchmark_change']=dict(old=old['management_targets'][-1],new=d['management_targets'][-1])
    repair['confidence_recomputed']=dict(old=load(OUTPUT/'forecast.json')['confidence'],new=r['confidence'],explanation=checks['confidence_note'])
    repair['qualitative_ledger_change']=dict(old_path=str(LANE/'communication_coverage.json'),old_target_count=17,new_path=str(LANE/'qualitative_targets_v2.json'),new_target_count=q['target_count'])
    repair['claim_full_context_path']=str(LANE/'claim_contexts_v2.json')
    repair['actual_download_requests']=dict(prepared_not_successfully_executed=str(LANE/'request_fy2026_fetch.json'),actual_failed_legacy_without_companion=str(LANE/'request_fy2026_fetch_legacy.json'),standalone_et_not_integrated=True)
    currentref=LANE.parents[1]/'existing_narrative_current_vs_asof.json'
    existing_summary=None
    if currentref.exists():
        current=load(currentref)
        existing_summary=dict(path=str(currentref),sha256=sha(currentref),artifact_already_existed=current['artifact_already_existed'],new_worker_runs=current['new_worker_runs'],new_model_calls=current['new_model_calls'],published_date_invented=current['published_date_invented'],forecast_input_consumption_proven=current['forecast_input_consumption_proven'],qualification=[dict(consumer=x['consumer'],as_of_date=x['request']['as_of_date'],returncode=x['returncode']) for x in current['checks']],scope='MAIN executed read-only current-consumer check of prior production TXT/narrative; not this batch newWorker or model consumption. Explicit asof rejected unknown published_date. FY25 SEC HTML remains unprocessed by canonical narrative.')
        repair['existing_production_narrative_reference']=existing_summary
    write(LANE/'repair_v2.json',repair)
    sources={s['source_id']:s for s in d['sources']};params={p['parameter_id']:p for p in d['parameters']}
    facts=[]
    for c in d['evidence_claims']:
        s=sources[c['source_id']];p=params.get(c['target_id'])
        facts.append(dict(claim_id=c['claim_id'],target_type=c['target_type'],target_id=c['target_id'],parameter_kind=p['kind'] if p else None,value=p['value'] if p else c.get('extracted_value'),unit=p['unit'] if p else c.get('unit'),period=p['period'] if p else c.get('period'),source_id=s['source_id'],source_url=s['url'],source_publication_date=s['published_date'],source_sha256=c['content_sha256'],locator=c['locator'],excerpt=c['excerpt'],excerpt_sha256=c['excerpt_sha256'],source_bytes_path=str(OUTPUT/'fy2025_verified_raw.html') if s['source_id'].startswith('urn:') else s['capture']['tool_call_id'],verification_scope='Exact history/operating context checked; conditional future values NOT exact source predictions; visual PPT excerpts normalized and reviewer must reopen.',support_type=c['support_type']))
    write(LANE/'fact_checks_v2.json',facts)
    (LANE/'repair_v2.md').write_text('''# MSFT v2 单批修复交接

独立v1审查FAIL已保留。v2仅在TEMP/US-MSFT/v2，原根目录input/result/md/snapshot与原manifest全部路径及字节不改。独立签收待复查，不由执行者签收。

US01：8条ratio增长的shock从5改0.05，真正重算全部敏感性、置信度和报告。US02：72future参数改绑逐流实际机制、同口径两年历史、约束/反证及季度口径；未来区间和两年fade/recovery仍是条件分析假设，不是source点预测。US03：Frontier/ERP/healthcare正向能力/活动与license负向迁移分开；CRM周期是实际反证；Xbox年度回增期望只反驳gaming headwind，不能证明Windows复苏。US04：四根真实确认链、不同indicator和年度同口径方向证伪，没有伪造季度阈值。US05：年度公司独立benchmark使用八流重述历史与机制/约束，AWS37%仅analogical；情景不被迫满足管理层。US06：17原定性行各自scope/period/IDs/比较或缺口，并补Cobalt、healthcare、Frontier、Copilot rollout/UBB时点等。US08：年度Azure38不是相对Q1CC的同口径保守界限。

US07保持BLOCKED：未成功的新文件下载/复用、最新年报policy、FF-ET成功TXT入库和CWPcanonicalHTMLWorker，不能用正式模型green代替。定性旁表是显式完整语义记录；数值runtime无法容纳词语/经营/availability承诺的边界继续披露，未改共享runtime。

MAIN另行只读验证了此前已存在的微软英文TXT及正式narrative：当前无as-of消费者能读，明确2026-10-08请求因原manifest公开日未知被拒。它证明生产TXT处理/消费者链有效，并不证明本轮FY25 SEC HTML已处理或该TXT具有本预测时点资格。未补造日期、未消费该旧artifact、未重复Worker/模型生成；收据路径与SHA见repair_v2.json。

详见repair_v2.json中的旧/新claim与finding ID、assumption_support_v2.json、qualitative_targets_v2.json、fact_checks_v2.json、validation_v2.json、commands/index.jsonl和processes。v2 input/forecast/json同源MD、snapshot和registry由真实安装工具生成；最终路径与SHA见manifest_v2.json。没有外部LLM、翻译、付费升级、共享配置或Dayu变更。
''',encoding='utf-8')
    (V2/'TRUST_BOUNDARY.md').write_text((OUTPUT/'TRUST_BOUNDARY.md').read_text(encoding='utf-8')+'\n\nV2 repair: corrected sensitivities and separately source-bound72 future assumptions. Qualitative commitments now individually scoped/mapped/compared. Future values remain analyst assumptions; technical checks are not economic approval. Independent v2 review pending; US07 remains BLOCKED. All v1 paths and byte hashes retained.\n',encoding='utf-8')
    matrix=load(LANE/'skill_step_matrix.json');matrix['forecast_version']=VERSION;matrix['independent_review']='pending'
    matrix['v2_repair_evidence']=[str(LANE/'repair_v2.json'),str(LANE/'validation_v2.json'),str(LANE/'qualitative_targets_v2.json')]
    for row in matrix['steps']:
        if row['step'] in ['3','5']:row['status']='BLOCKED';row['v2_note']='US07 remains blocked for current-asof latestfiling/HTMLcanonical/FFcompanion; prior production TXT narrative exists but cannot qualify unknown publication date.'
        else:row['v2_note']='Repair technical tests passed where applicable; economic/semantic independent v2 acceptance pending.'
    write(LANE/'skill_step_matrix_v2.json',matrix)
    finalhash={}
    for rel in load(LANE/'runtime_hashes_final.json'):
        ins=RF/rel;repo=Path('C:/Users/郑曾波/Projects/revenue-forecast')/rel
        finalhash[rel]=dict(installed_sha256=sha(ins),repo_sha256=sha(repo),same=ins.read_bytes()==repo.read_bytes())
    for rel in ['scripts/lint_input.py','scripts/fix_hashes.py','scripts/publication_registry.py']:
        ins=RF/rel;repo=Path('C:/Users/郑曾波/Projects/revenue-forecast')/rel
        finalhash[rel]=dict(installed_sha256=sha(ins),repo_sha256=sha(repo),same=ins.read_bytes()==repo.read_bytes())
    assert all(v['same'] for v in finalhash.values())
    artifacts=[dict(absolute_path=str(p),sha256=sha(p),bytes=p.stat().st_size,role='v2_research') for p in V2.iterdir() if p.is_file()]
    manifest=dict(schema_version='1.0',company='Microsoft',security_id='MSFT',market='US',agent_id='/root/rf_us_execution',as_of_date='2026-10-08',forecast_version=VERSION,output_root=str(V2),status='partial',independent_review_status='pending',formal_paths={name:str(V2/name) for name in ['input.json','forecast.json','forecast.md','snapshot.json']},registry_path=str(V2/'publications.jsonl'),runtime_file_sha256=finalhash,artifacts=artifacts,repair_report=str(LANE/'repair_v2.md'),repair_details=str(LANE/'repair_v2.json'),fact_checks=str(LANE/'fact_checks_v2.json'),qualitative_coverage=str(LANE/'qualitative_targets_v2.json'),assumption_support=str(LANE/'assumption_support_v2.json'),validation=str(LANE/'validation_v2.json'),command_index=str(LANE/'commands/index.jsonl'),process_trace_dir=str(LANE/'processes'),v1_paths_and_unchanged_sha256=checks['frozen_after_sha256'],blocked=['US-07'],remaining_limits=['Numeric-only management runtime; qualitative ledger separate and reviewed semantically','Direct-growth fallback and all future ranges/fades remain conditional analyst judgment','No host signer or future actual backtest'],calls_and_cost=dict(external_llm_calls=0,external_llm_tokens=0,provider_paid_calls=0,new_download_attempts=0),created_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    manifest.update(runtime_version='4.1.0',formal_technical_status='PASS',sources=load(LANE/'manifest.json')['sources'],step_matrix_path=str(LANE/'skill_step_matrix_v2.json'),claim_full_context_path=str(LANE/'claim_contexts_v2.json'),existing_production_narrative_reference=existing_summary)
    manifest['artifacts'].extend(dict(absolute_path=str(p),sha256=sha(p),bytes=p.stat().st_size,role='v2_engineering_handoff') for p in [LANE/'repair_v2.json',LANE/'repair_v2.md',LANE/'fact_checks_v2.json',LANE/'qualitative_targets_v2.json',LANE/'assumption_support_v2.json',LANE/'claim_contexts_v2.json',LANE/'validation_v2.json',LANE/'skill_step_matrix_v2.json'])
    write(LANE/'manifest_v2.json',manifest)
    event('repair-v2','handoff v2; all findings mapped, blocked chain explicit; independent review pending',outcome='partial',artifacts=[str(LANE/'manifest_v2.json'),str(LANE/'repair_v2.json')])
    print(json.dumps(dict(manifest=str(LANE/'manifest_v2.json'),claims=len(facts),qualitative_targets=q['target_count'],v1_unchanged=True,independent_review='pending',us07='BLOCKED'),ensure_ascii=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['build','lint','hash','validate','forecast','snapshot','registry','verify','handoff']);a=ap.parse_args().action
    if a=='build':build()
    elif a=='lint':sys.exit(run_cli('v2_lint',[RF/'scripts/lint_input.py',V2/'input.json']))
    elif a=='hash':sys.exit(run_cli('v2_hash',[RF/'scripts/fix_hashes.py',V2/'input.json','--check']))
    elif a=='validate':sys.exit(run_cli('v2_validate',[RF/'scripts/revenue_forecast.py',V2/'input.json','--validate-only','--verbose']))
    elif a=='forecast':sys.exit(run_cli('v2_forecast',[RF/'scripts/revenue_forecast.py',V2/'input.json','--output',V2/'forecast.json','--markdown',V2/'forecast.md']))
    elif a=='snapshot':sys.exit(run_cli('v2_snapshot',[RF/'scripts/revenue_backtest.py','create',V2/'input.json','--version',VERSION,'--output',V2/'snapshot.json']))
    elif a=='registry':sys.exit(run_cli('v2_registry',[RF/'scripts/publication_registry.py','audit','--result',V2/'forecast.json']))
    elif a=='verify':verify()
    else:handoff()
