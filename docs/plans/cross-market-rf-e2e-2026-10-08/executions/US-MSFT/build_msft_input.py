"""Build source-bound MSFT research input; no research state in CWP."""
from lane_tools import LANE,RF,OUTPUT,write,event
import sys,json,hashlib,datetime,re
sys.path.insert(0,str(RF/'scripts'))
from generate_input_template import build_template
from contracts.evidence import canonical_sha256,text_sha256,build_host_receipt
ASOF='2026-10-08'; AGENT='/root/rf_us_execution'
def capture_source(ident,path,url,date,title,publisher='Microsoft',method='api_response',tool='requests'):
    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    host=build_host_receipt(issuer='local execution audit (unsigned)',environment='Codex Windows task TEMP',tool_name=tool,action='retain_opened_primary_source',event_sha256=sha,timestamp=timestamp)
    cap=dict(capture_schema_version='1.0',capture_method=method,tool_name=tool,tool_call_id=str(path),captured_date=ASOF,snapshot_sha256=sha,content_treatment='untrusted_data_only',prompt_injection_status='not_reviewed',host_receipt=host)
    cap['receipt_sha256']=canonical_sha256(cap)
    stype='investor_presentation' if ident=='src_presentation' else ('earnings_transcript' if ident=='src_call' else 'company_release')
    return dict(source_id=ident,source_type=stype,title=title,publisher=publisher,url=url,published_date=date,accessed_date=ASOF,page_or_section='retained official source; locators on claims',capture=cap)
def main():
    sources=[json.loads((LANE/'request_fy2025_reuse_response.json').read_text())]
    rows=json.loads((OUTPUT/'ancillary_page_receipts.json').read_text())
    for row in rows:
        sources.append(capture_source('src_'+row['id'],__import__('pathlib').Path(row['path']),row['url'],row['published_date'],row['id']+' official communication','Amazon' if row['id']=='aws' else 'Microsoft'))
    ppt=capture_source('src_presentation',OUTPUT/'fy2027_segments_metrics.pptx','https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/FY27ExternalKPIs.pptx','2026-09-02','FY27 Segments and Investor Metrics',method='local_document',tool='requests+view_image')
    sources.append(ppt)
    # Blogs were actually opened by web.run; direct HTTP returned 403. Preserve web tool view bytes honestly.
    blogfile=OUTPUT/'web_material_announcements.json'
    for ident,date,slug in [('strategy','2026-09-25','introducing-the-new-copilot-with-home-code-and-autopilot'),('data_innovation','2026-09-28','new-microsoft-data-innovations-unlock-what-only-your-business-knows'),('leadership','2026-10-01','microsoft-365-and-linkedin-leadership-update')]:
        sources.append(capture_source('src_'+ident,blogfile,f'https://blogs.microsoft.com/blog/{date[:4]}/{date[5:7]}/{date[8:]}/{slug}/',date,slug,method='browser_open',tool='web.run retained multi-view response'))
    source_index={s['source_id']:s for s in sources}; claims=[];params=[];checks=[]
    annual_id=sources[0]['source_id']
    def claim(target,typ,sid,excerpt,locator,support='rationale_support',value=None,unit=None,period=None):
        cid='claim_'+str(len(claims)+1)+'_'+re.sub(r'[^a-zA-Z0-9]','_',target)
        s=source_index[sid]
        c=dict(claim_id=cid,source_id=sid,target_type=typ,target_id=target,support_type=support,locator=locator,excerpt=excerpt,excerpt_sha256=text_sha256(excerpt),content_sha256=s['capture']['snapshot_sha256'],capture_receipt_sha256=s['capture']['receipt_sha256'],verification_status='opened_and_checked',verified_by=AGENT,verified_date=ASOF)
        if value is not None:c.update(extracted_value=value,unit=unit,period=period)
        claims.append(c);return cid
    def parameter(pid,value,kind,dim,period,scenario,rationale,sid,excerpt,locator):
        unit='USD million' if dim=='revenue' else 'ratio'
        cid=claim(pid,'parameter',sid,excerpt,locator,'exact_value' if kind=='reported_fact' else 'rationale_support',value if kind=='reported_fact' else None,unit,period)
        p=dict(parameter_id=pid,kind=kind,value=value,unit=unit,period=period,definition=rationale,dimension=dim,time_basis='annual',source_ids=[sid],scenario=scenario,rationale=rationale,claim_ids=[cid])
        if dim=='revenue':p.update(currency='USD',scale='million')
        params.append(p);checks.append(dict(parameter_id=pid,kind=kind,value=value,unit=unit,period=period,source_id=sid,claim_id=cid,locator=locator,status='exact_primary_fact_checked' if kind=='reported_fact' else 'analyst_assumption_supported_direction_not_source_forecast',rationale=rationale));return pid
    # All eight are mutually exclusive external product/service revenues under FY27 restatement, not the old three segments.
    businesses=[
      ('Azure',101938,72610,'Agents and Infra',[.30,.22,.16],[.38,.30,.24],[.45,.38,.30],'Cloud consumption and AI demand; supply/compute execution constraints. FY26 restated growth40%; Q1 FY27 CC guide44-45%; annual FY27 base38% reported deliberately below a full-year extrapolation of Q1, then fades.'),
      ('Microsoft 365 cloud',100299,84605,'Agents and Infra',[.12,.10,.08],[.17,.16,.14],[.22,.21,.19],'Paid seat growth and Copilot/E7 mix, with consumption monetization; FY26 commercial restated18% and new Q1 CC17% guidance apply only to commercial subset, not all cloud.'),
      ('Productivity and server licensing',37285,35391,'Agents and Infra',[-.08,-.06,-.05],[-.05,-.03,-.02],[-.02,0,.01],'Cloud migration and FY26 launch transactional comparable; full-year products decline mid-single digits guides direction; component mix undisclosed.'),
      ('Industry solutions',20345,18417,'Agents and Infra',[.05,.04,.03],[.09,.09,.08],[.13,.13,.12],'Dynamics and LinkedIn talent/sales plus healthcare; new cloud FY26 restated12% and Q1 high-single-digit guide inform direction, while products mix and CRM cycles constrain magnitude.'),
      ('Frontier and support services',8260,7760,'Agents and Infra',[.02,.02,.01],[.06,.05,.04],[.09,.08,.07],'Consulting/support services attach to enterprise implementation; FY26 growth6.4%, no signed future pipeline amount disclosed.'),
      ('Search and advertising',24835,22171,'Devices and Consumer',[.03,.02,.01],[.08,.07,.06],[.12,.11,.10],'Search demand/price plus LinkedIn Marketing and Premium; Q1 exTAC mid-to-high-single growth is net KPI, not this gross revenue, so only directional check.'),
      ('XBOX',21790,23455,'Devices and Consumer',[-.10,-.05,0],[-.04,.02,.04],[.02,.08,.08],'Reset and weaker hardware; management expects FY27 gaming return to growth but first quarter content decline. Base annual-4% is an explicit independent disagreement; excludes unproven launch uplift.'),
      ('Windows OEM and devices',17087,17315,'Devices and Consumer',[-.23,-.10,-.05],[-.18,-.03,0],[-.13,.03,.05],'Higher component prices, inventory and end-support comparable drive FY27 high-teens decline; stabilization years2-3 is conditional, not management commitment.')]
    names=[b[0] for b in businesses]
    data=build_template('Microsoft',2026,[2027,2028,2029],'USD','million',names,{n:'direct_growth' for n in names})
    data.pop('_comment',None);data.update(as_of_date=ASOF,fiscal_year_end='06-30',forecast_version='2026-10-08-MSFT-v1',sources=sources,parameters=params,evidence_claims=claims,management_targets=[],data_gaps=[])
    total=parameter('reported_total',331839,'reported_fact','revenue','FY2026',None,'Microsoft consolidated GAAP annual revenue, fiscal year ended June30 2026','src_results','Revenue 331,839','FY2026 release Income Statements, Revenue row, year ended 2026')
    data['reported_total_revenue_parameter_id']=total
    for segment,b in zip(data['segments'],businesses):
        name,value,prior,group,*paths,rationale=b;slug=re.sub(r'[^a-z0-9]+','_',name.lower()).strip('_')
        base=parameter(slug+'_base',value,'reported_fact','revenue','FY2026',None,name+' external annual recognized revenue restated on FY27 perimeter','src_presentation',f'{name} ${value:,}','PPT slide17 As Restated, Fiscal Year2026 column; image17.png visual check')
        segment['base_revenue_parameter_id']=base
        segment['reporting_group']=group
        for scen,path in zip(['low','base','high'],paths):
            ids=[]
            for year,growth in zip([2027,2028,2029],path):
                pid=parameter(f'{slug}_growth_{scen}_{year}',growth,'analyst_assumption','ratio',f'FY{year}',scen,rationale+f' {scen} FY{year} annual recognized revenue growth {growth:.0%}; a research assumption, not source guidance.','src_presentation',name+' '+f'${value:,}','PPT slide17 restated history + slides20-21 outlook; causal memo links full call and independent AWS benchmark')
                ids.append(pid)
            segment['scenarios'][scen].update(model='direct_growth',driver_parameter_ids={'growth_rate':ids},rationale=rationale+' Conditional '+scen+' case; no calibrated probability.')
        # This model forecasts revenue already recognized within each annual fiscal period, never total contract value.
        cloud=name in ['Azure','Microsoft 365 cloud','Frontier and support services']
        mixed=name in ['Industry solutions','XBOX','Productivity and server licensing','Search and advertising','Windows OEM and devices']
        policy_excerpt='Revenue related to cloud services provided on a consumption basis' if name=='Azure' else ('recognized ratably over the contract period' if name=='Microsoft 365 cloud' else ('recognized as services are provided' if name=='Frontier and support services' else 'Revenue is recognized upon transfer of control'))
        pc=claim('recognition:'+name,'recognition_policy',annual_id,policy_excerpt,'FY2025 10K Note1 Revenue Recognition; cloud/consulting/license/advertising/hardware paragraphs','policy_support')
        recognition=dict(mode='modeled_as_recognized',timing='over_time' if cloud else 'mixed' if mixed else 'point_in_time',trigger='Already-recognized annual external revenue forecast. Actual underlying recognition follows Note1: usage/service delivery, or control/ad serving. Mixed components are aggregated due undisclosed split; this annual model cannot produce quarterly or contract-level recognition.',presentation='mixed' if name in ['XBOX','Search and advertising'] else 'gross',modeled_presentation='mixed' if name in ['XBOX','Search and advertising'] else 'gross',basis_claim_ids=[pc])
        if mixed:recognition['aggregation_boundary']='FY27 restated external annual recognized '+name+' revenue only. Underlying license/control transfer, subscriptions/service delivery, principal/agent components follow original policy; no forecasted billings, bookings or RPO converted. Component splits undisclosed; annual direct fallback preserves the reported aggregate and cannot support intra-year timing.'
        if cloud:
            recognition['progress_measure']='annual recognized-flow identity factor; 1 is not completion of backlog/RPO and does not accelerate any contract revenue'
            progress=[]
            for year in [2027,2028,2029]:
                progress.append(parameter(f'{slug}_recognition_identity_{year}',1,'analyst_assumption','ratio',f'FY{year}',None,'Annual growth model already projects recognized service flow; factor1 prevents double timing multiplication. Mixed components must be split before any intra-year use.',annual_id,policy_excerpt,'FY2025 10K Note1 Revenue Recognition'))
            recognition['progress_parameter_ids']={s:progress for s in ['low','base','high']}
        segment['recognition']=recognition
        data['data_gaps'].append(name+': operating quantity, realized price/mix, churn and timing split undisclosed; direct_growth fallback reduces explicit-model confidence. No unit/ARPU is fabricated.')
    data['historical_revenue']=[]
    for year,value,sid in [(2024,245122,annual_id),(2025,281724,'src_results'),(2026,331839,'src_results')]:
        excerpt=f'{value:,}'
        cid=claim(f'historical_revenue:{year}','historical_revenue',sid,('Revenue '+excerpt),f'Consolidated annual Income Statements Revenue row FY{year}','exact_value',value,'USD million',f'FY{year}')
        data['historical_revenue'].append(dict(year=year,value=value,source_ids=[sid],claim_ids=[cid]))
    data['growth_driver_tree']=dict(status='modeled',drivers=[])
    roots=[('cloud_ai','Cloud usage and Copilot mix',['Azure','Microsoft 365 cloud'],'multi_year_structural','Usage delivery and enterprise paid monetization, constrained by GPUs and budgets.','src_call','demand exceeds available supply'),('enterprise_migration','Enterprise solutions and cloud migration',['Productivity and server licensing','Industry solutions','Frontier and support services'],'multi_year_structural','Enterprise migration expands services but cannibalizes licenses; signed pipeline and cohort margins are unavailable.','src_call','decline in the mid-single digits'),('advertising','Advertising usage and monetized mix',['Search and advertising'],'uncertain','Search/ad usage and yield increase, but third-party partnerships and the LinkedIn perimeter prevent extrapolating old net KPI as gross revenue.','src_call','revenue per search and volume'),('consumer_cycle','Device and content reset',['XBOX','Windows OEM and devices'],'cyclical','PC inventories, component prices and XBOX reset create headwinds; no arbitrary AI uplift in Windows.','src_call','elevated inventory levels')]
    for rid,title,streams,persistence,thesis,sid,excerpt in roots:
        c=claim(rid+'_company','growth_driver',sid,excerpt,'Official FY26Q4 full call: CFO outlook and Q&A','rationale_support')
        nodes=[dict(evidence_id=rid+'_company',evidence_type='company_operating_disclosure',inference_distance='one_step',conclusion=thesis,claim_ids=[c])]
        negative='demand exceeds available supply' if rid=='cloud_ai' else 'impact of third-party partnerships' if rid=='advertising' else 'decline in the mid-single digits' if rid=='enterprise_migration' else 'elevated inventory levels'
        nc=claim(rid+'_contrary','growth_driver','src_call',negative,'Official full call CFO outlook / complete Q&A counterevidence','rationale_support')
        nodes.append(dict(evidence_id=rid+'_contrary',evidence_type='company_counterevidence',inference_distance='contrary',conclusion='This observed constraint weakens magnitude or continuation; wide scenarios and future fades remain analyst judgment.',claim_ids=[nc]))
        if rid=='cloud_ai' and 'src_aws' in source_index:
            ac=claim(rid+'_peer','growth_driver','src_aws','AWS net sales increased 37%','Amazon July30 Q22026 official release opening results','rationale_support')
            nodes.append(dict(evidence_id=rid+'_peer',evidence_type='independent_peer_cloud_demand',inference_distance='analogical',conclusion='AWS Q2 cloud37% corroborates category demand; AWS annualized169B is not MSFT annual revenue and not used numerically.',claim_ids=[ac]))
        data['growth_driver_tree']['drivers'].append(dict(driver_id=rid,title=title,thesis=thesis,causal_chain=['Capability and customer demand','Delivered usage/seats or device/content transactions','Source-supported direction and conditional annual growth','Annual recognized external product revenue'],parameter_ids=[p['parameter_id'] for p in params if p.get('scenario')=='base' and any(p['parameter_id'].startswith(re.sub(r'[^a-z0-9]+','_',n.lower()).strip('_')+'_growth') for n in streams)],segment_attribution=[dict(segment_name=n,weight=1) for n in streams],horizon=dict(start_year=2027,end_year=2029),persistence=persistence,persistence_rationale=thesis,evidence_nodes=nodes,leading_indicators=['Quarterly restated revenue growth','Paid adoption vs unmonetized users','Supply/utilization and renewals'],falsifiers=['Two successive quarters below low-case growth','Contract delays or price/cost pressure erode realized revenue'],counterevidence_status='found',counterevidence_rationale='Explicit constraints opened in full official call and Q&A; contrary nodes bind those observations. Independent customer-budget/usage data insufficient; search is not exhaustive.'))
    dimensions={
      'company_foundation':('Eight product streams reconcile to official two reporting groups; FY26 total331839','reported_total','src_presentation'),
      'growth_curve':('Cloud adoption vs legacy migration and consumer cycle separated','azure_growth_base_2027','src_call'),
      'industry_market':('AWS cloud37% offers an independent category reference, not identical market share or company forecast','azure_growth_base_2027','src_aws'),
      'competition':('Multi-model enterprise demand faces AWS competition and customer spending choices','azure_growth_base_2028','src_aws'),
      'capacity':('Demand exceeds supply and DC deployment is prerequisite; capacity is not recognized revenue','azure_growth_base_2027','src_call'),
      'technology':('Copilot preview and usage billing create potential monetization but rollout is not booked revenue','microsoft_365_cloud_growth_base_2028','src_strategy'),
      'policy':('No quantitative policy-to-revenue bridge established; regulatory and trust exposure unmodeled',None,'src_call'),
      'customers':('Paid enterprise adoption improves mix; registered users and period-end seats are not annual paying averages','microsoft_365_cloud_growth_base_2027','src_call'),
      'demand':('Supply constrained commercial demand coexists with weak PCs/gaming','windows_oem_and_devices_growth_base_2027','src_call')}
    data['research_coverage']=[]
    for dim,(con,pid,sid) in dimensions.items():
        data['research_coverage'].append(dict(dimension=dim,status='modeled_driver' if pid else 'data_gap',conclusion=con,revenue_mechanism=con,parameter_ids=[pid] if pid else [],source_ids=[sid] if sid in source_index else [],rationale=con))
    # Every numeric quarterly guide is retained; contract only admits annual FY measurement periods.
    quarter=[('company_q1_low',89850,'company','Microsoft','src_presentation','Revenue of $89.85 to $90.95 billion',20),('company_q1_high',90950,'company','Microsoft','src_presentation','Revenue of $89.85 to $90.95 billion',20),('agents_q1_low',75150,'custom','Agents and Infra','src_presentation','Revenue of $75.15 to $75.75 billion',20),('agents_q1_high',75750,'custom','Agents and Infra','src_presentation','Revenue of $75.15 to $75.75 billion',20),('devices_q1_low',14700,'custom','Devices and Consumer','src_presentation','Revenue of $14.7 to $15.2 billion',20),('devices_q1_high',15200,'custom','Devices and Consumer','src_presentation','Revenue of $14.7 to $15.2 billion',20),('azure_q1_cc_low',44,'custom','Azure','src_presentation','Growth of 44% to 45% in constant currency',21),('azure_q1_cc_high',45,'custom','Azure','src_presentation','Growth of 44% to 45% in constant currency',21),('m365_q1_cc',17,'custom','Microsoft365 commercial cloud','src_presentation','Growth of approximately 17% in constant currency',21),('m365_q1_adjusted_cc',18,'custom','Microsoft365 commercial cloud adjusted','src_presentation','Growth of approximately 18% in constant currency',21)]
    for tid,val,scope,name,sid,excerpt,slide in quarter:
        if '_cc' not in tid:val=val/1000
        unit='percent' if '_cc' in tid else 'USD billion'
        cid=claim(tid,'management_target',sid,excerpt,f'PPT slide{slide} adjusted FY27Q1 outlook','exact_value',val,unit,'FY2027Q1')
        data['management_targets'].append(dict(target_id=tid,statement=excerpt,metric_name=name+' quarterly guidance',metric_definition='FY2027Q1 only; currency/gross perimeter as explicitly named',target_period='FY2027Q1',raw_target_value=val,raw_unit=unit,raw_currency='USD' if unit=='USD billion' else 'constant currency',raw_scale='billion' if unit=='USD billion' else 'percent',measurement_basis='ambiguous',measurement_periods=[],measurement_rationale='Source period is unambiguous Q1. Ambiguous here ONLY denotes missing quarterly-to-annual mapping in an annual-only runtime; never reinterpret as annual guidance.',materiality='material',commitment_strength='guidance',perimeter_status='mismatch',perimeter_notes='Quarterly period and/or constant-currency KPI is not full-year reported recognized revenue; no supported conversion.',comparison='approximately',comparison_value=None,scope=dict(type=scope,name=name),treatment='unmodeled_data_gap',mapped_parameter_ids=[],mapped_scenarios=[],rationale='Keep exact quarterly target visible; annual model does not multiply by4. See sidecar quarterly guidance comparison.',claim_ids=[cid]))
    tid='company_fy27_double_digit';raw=10
    cid=claim(tid,'management_target','src_call','another fiscal year of double-digit revenue','Official FY26Q4 full call CFO FY27 outlook paragraph','exact_value',raw,'percent linguistic lower bound','FY2027')
    bc=claim(tid,'management_target','src_aws','AWS net sales increased 37%','Amazon July30 Q22026 official release opening results','rationale_support')
    data['management_targets'].append(dict(target_id=tid,statement='Another fiscal year of double-digit revenue growth',metric_name='annual company recognized revenue growth',metric_definition='Full FY2027 vs FY2026 GAAP annual consolidated revenue; double-digit interpreted as >=10%, not an exact10% forecast',target_period='FY2027',raw_target_value=10,raw_unit='percent linguistic lower bound',raw_currency='USD',raw_scale='percent',measurement_basis='annual_period',measurement_periods=['FY2027'],measurement_rationale='CFO explicitly says fiscal year; FYendJune30. Ten is a linguistic lower-bound normalization, not a quoted point estimate.',materiality='material',commitment_strength='guidance',perimeter_status='reconciled',perimeter_notes='Company annual growth converted against FY2026 official base331839; no constant-currency or runrate substitution.',comparison='at_least',comparison_value=331839*1.10,comparison_currency='USD',comparison_scale='million',comparison_tolerance=0,normalization_rationale='Double digit means at least10%; 331839*(1+10/100)=365022.9. No raw exact numeric quote implied.',scope=dict(type='company',name='Microsoft'),treatment='independent_benchmark',mapped_parameter_ids=[p['parameter_id'] for p in params if '_growth_' in p['parameter_id']],mapped_scenarios=['low','base','high'],rationale='Operating streams independently modeled before comparison; management aspiration does not set scenario probability.',benchmark_rationale='MSFT restated history, supply caveats and AWS category demand support an independent range; future3years not forced to management wording.',benchmark_claim_ids=[bc],claim_ids=[cid]))
    categories=[('latest_annual_filing',[],[]),('latest_results_release',['src_results'],[]),('latest_earnings_call',['src_call'],[tid]),('latest_investor_presentation',['src_presentation'],[q[0] for q in quarter]),('latest_strategy_communication',['src_strategy','src_data_innovation'],[]),('material_announcements_since_last_filing',['src_leadership','src_strategy','src_data_innovation','src_presentation'],[])]
    data['management_communication_coverage']=[]
    for cat,sids,tids in categories:
        row=dict(category=cat,status='checked' if sids else 'not_available',source_ids=sids,checked_date=ASOF,conclusion='Opened retained original-language primary communications; numeric targets in ledger, qualitative targets preserved in sidecar.' if sids else 'FY2026 annual exists in official SEC listing, but current mandatory RF→FF→CWP ensure failed; latest annual cannot be marked checked. FY2025 verified original only.',material_revenue_target_ids=tids)
        if not sids:row.update(rationale='Actual acquisition failure, not absence of published filing.',search_description='Official SEC-filing listing checked, FF exact FY26 no_local_match then true ensure failed.',search_event=dict(query_scope='MSFT FY2026 10K official listing and actual RF source preparation',query_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),event_ids=['1791442398164187200-fetch-fy2026-legacy'],generated_by='run_logged.py',event_sha256=hashlib.sha256((LANE/'request_fy2026_fetch_legacy_response.json').read_bytes()).hexdigest()))
        data['management_communication_coverage'].append(row)
    data['sensitivity_tests']=[dict(name=n+' FY27 growth ±5pp',parameter_id=re.sub(r'[^a-z0-9]+','_',n.lower()).strip('_')+'_growth_base_2027',shock_type='percentage_point',shock_value=5) for n in names]
    data['data_gaps'] += ['Official FY26 filing acquisition not yet successful; FY25 recognition policy may be superseded.','Latest FY27 two-segment historical reclassification covers only FY25/FY26; FY24 product-group history not invented.','Mixed-recognition XBOX/Industry solutions and licensing/support allocation cannot be decomposed from reported data; annual recognized-flow fallback unsuitable for intra-year timing.','Qualitative targets are retained in sidecar because numeric-only target schema cannot encode mid-single/high-teens without invented precision.','Self-generated capture receipts are unsigned: provenance metadata and SHA integrity are verified; host identity is not cryptographically attested.','No historical immutable MSFT forecast+actual pairs available; no backtest accuracy claimed.']
    write(OUTPUT/'input.json',data);write(LANE/'fact_checks.json',dict(agent=AGENT,checked_at=ASOF,parameters=checks,original_language=True,raw_shas={s['source_id']:s['capture']['snapshot_sha256'] for s in sources},manual_visual_source='PPT all22slides opened via view_image, individual images retained. Claims use original PPT SHA; vision transcription not machine OCR.'))
    write(OUTPUT/'reporting_groups.json',dict(basis='FY27 restated',groups={g:[b[0] for b in businesses if b[3]==g] for g in ['Agents and Infra','Devices and Consumer']},base={g:sum(b[1] for b in businesses if b[3]==g) for g in ['Agents and Infra','Devices and Consumer']},prior={g:sum(b[2] for b in businesses if b[3]==g) for g in ['Agents and Infra','Devices and Consumer']}))
    event('6','construct source-bound annual input on eight restated businesses; conditional operating fallback, not fabricated granularity',outcome='input_ready_for_lint',artifacts=[str(OUTPUT/'input.json'),str(LANE/'fact_checks.json')],parameters=len(params),claims=len(claims))
    print(json.dumps(dict(parameters=len(params),claims=len(claims),segments=len(data['segments']),output=str(OUTPUT/'input.json'))))
if __name__=='__main__':main()
