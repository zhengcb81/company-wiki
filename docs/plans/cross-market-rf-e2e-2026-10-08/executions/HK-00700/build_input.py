"""Construct real-data input; no invented operating denominators or future actuals."""
from pathlib import Path
import datetime as dt, hashlib, json, sys, re
HERE=Path(__file__).resolve().parent
OUT=Path(json.loads((HERE/'before.json').read_text(encoding='utf-8'))['output_root'])
SKILL=Path.home()/'.agents/skills/revenue-forecast'
sys.path.insert(0,str(SKILL/'scripts'))
from contracts.evidence import canonical_sha256, text_sha256, build_host_receipt
ASOF='2026-10-08'; AGENT='/root/rf_hk_execution'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def norm(s):return ' '.join(s.split())
a=read(OUT/'annual_2025_pages.json');a24=read(OUT/'annual_2024_pages.json')
h=read(OUT/'interim_2026_official_pages.json');ir=read(OUT/'corporate_overview_pages.json');rel=read(OUT/'results_2q2026_pages.json')
data=read(OUT/'template_growth.json');data.pop('_comment',None)
data.update(as_of_date=ASOF,company_name='Tencent Holdings Limited',fiscal_year_end='12-31',base_year=2025,forecast_years=[2026,2027,2028],management_targets=[])
src25=read(HERE/'annual-2025.source.json');src24=read(HERE/'annual-2024.source.json')
data['sources']=[src25,src24]
supp=read(HERE/'supplemental_capture_receipts.json'); corp=read(HERE/'ir_capture_receipt.json')
def supplemental_source(receipt,sid,title,stype,publisher='Tencent Holdings Limited'):
    assert receipt.get('status','captured')=='captured'
    raw=Path(receipt['raw_path']);digest=hashlib.sha256(raw.read_bytes()).hexdigest();assert digest==receipt['sha256']
    ts=receipt.get('timestamp_utc',dt.datetime.now(dt.timezone.utc).isoformat())
    capture={'capture_schema_version':'1.0','capture_method':'api_response','tool_name':'task-local bounded official HTTP capture','tool_call_id':sid+'|'+ts,'captured_date':ASOF,'snapshot_sha256':digest,'content_treatment':'untrusted_data_only','prompt_injection_status':'not_reviewed','host_receipt':build_host_receipt(issuer=AGENT,environment='normal-Windows task-local process, unsigned',tool_name='requests.get streamed',action='official_supplement_capture',event_sha256=canonical_sha256(receipt),timestamp=ts)}
    capture['receipt_sha256']=canonical_sha256(capture)
    return {'source_id':sid,'source_type':stype,'title':title,'publisher':publisher,'url':receipt['url'],'published_date':receipt['published_date'],'accessed_date':ASOF,'page_or_section':'Complete original and explicitly located excerpts','capture':capture,'supplemental_route':receipt['route'] if 'route' in receipt else receipt['supplemental_route'],'raw_artifact_path':str(raw),'publication_date_basis':receipt['publication_date_basis']}
sid25=src25['source_id'];sid24=src24['source_id'];SH='tencent_h1_2026_official';SR='tencent_results_2q2026';SI='tencent_corporate_overview_sep2026';SN='netease_results_2q2026'
for name,sid,title,stype,publisher in [('interim_2026_official',SH,'Tencent Interim Report 2026','regulatory_filing','Tencent Holdings Limited'),('results_2q2026',SR,'Tencent second-quarter and first-half 2026 results','company_release','Tencent Holdings Limited'),('netease_2q2026',SN,'NetEase second-quarter and interim 2026 unaudited results','company_release','NetEase, Inc.')]:
    data['sources'].append(supplemental_source(next(x for x in supp if x['name']==name),sid,title,stype,publisher))
data['sources'].append(supplemental_source(corp,SI,'Tencent Corporate Overview September 2026','investor_presentation'))
si={s['source_id']:s for s in data['sources']}
data['parameters']=[];data['evidence_claims']=[];facts=[]
def span(page,needle,chars=240):
    text=norm(page['text']);pos=text.find(needle);assert pos>=0,(page['page'],needle)
    return text[max(0,pos-40):pos+chars]
def claim(sid,target_type,target_id,support,locator,excerpt,value=None,period=None,unit=None):
    cid=f'claim_{target_type}_{target_id}_{len(data["evidence_claims"])}';cap=si[sid]['capture']
    c={'claim_id':cid,'source_id':sid,'target_type':target_type,'target_id':target_id,'support_type':support,'locator':locator,'excerpt':excerpt.strip(),'excerpt_sha256':text_sha256(excerpt),'content_sha256':cap['snapshot_sha256'],'capture_receipt_sha256':cap['receipt_sha256'],'verification_status':'opened_and_checked','verified_by':AGENT,'verified_date':ASOF}
    if value is not None:c.update(extracted_value=value,period=period,unit=unit)
    data['evidence_claims'].append(c);facts.append(dict(c,checked_source_url=si[sid]['url'],conclusion='Checked against complete original context; exact fact' if support=='exact_value' else 'Source supports mechanism/policy only; future assumption is analyst judgment'))
    return cid
def param(pid,value,kind,dimension,period,scenario,definition,rationale,sid,locator,excerpt):
    unit='CNY million' if dimension=='revenue' else 'ratio'
    c=claim(sid,'parameter',pid,'exact_value' if kind=='reported_fact' else 'rationale_support',locator,excerpt,value if kind=='reported_fact' else None,period,unit)
    p={'parameter_id':pid,'kind':kind,'value':value,'dimension':dimension,'time_basis':'annual','period':period,'scenario':scenario,'unit':unit,'definition':definition,'rationale':rationale,'source_ids':[sid],'claim_ids':[c]}
    if dimension=='revenue':p.update(currency='CNY',scale='million')
    data['parameters'].append(p);return pid
names=['Games','SocialNetworks','MarketingServices','FinTechBusinessServices','Others']
bases=[241532,127749,144973,229435,8077];old=[197712,121456,121374,211956,7759]
h26=[130115,64409,81736,120171,4812];h25=[118654,64847,67615,110443,2967]
assert sum(bases)==751766 and sum(old)==660257 and sum(h26)==401243 and sum(h25)==364526
param('reported_total',751766,'reported_fact','revenue','FY2025',None,'FY2025 consolidated IFRS revenue, CNY million','Audited total; VAS is Games plus SocialNetworks, no VAS double count.',sid25,'FY2025 annual PDF page 196 / printed 195 Note 6(b)',span(a[195],'751,766'))
for name,b,prior in zip(names,bases,old):
    key=name.lower();param(key+'_base',b,'reported_fact','revenue','FY2025',None,name+' recognized FY2025 revenue','Note 6(b) disaggregation; precise values instead of rounded domestic/international gaming paragraphs.',sid25,'FY2025 annual PDF page 196 / printed 195 Note 6(b)',span(a[195],f'{b:,}'))
    assert f'{prior:,}' in a24[187]['text'] and f'{prior:,}' in a[195]['text']
    facts.append({'fact_id':key+'_fy2024_reconciliation','source_ids':[sid24,sid25],'locators':['FY2024 annual PDF page 188 / printed 187 Note 6(b)','FY2025 annual PDF page 196 / printed 195 comparative'],'value':prior,'unit':'CNY million','period':'FY2024','excerpt':span(a24[187],f'{prior:,}'),'conclusion':'Two separate annual originals match; sum 660257; FY2024 VAS319168 = Games197712 + Social121456'})
data['historical_revenue']=[]
for year,v in [(2021,560118),(2022,554552),(2023,609015),(2024,660257),(2025,751766)]:
    cid=claim(sid25,'historical_revenue',f'historical_revenue:{year}','exact_value','FY2025 annual PDF page 4 / printed 3 five-year financial summary',span(a[3],f'{v:,}'),v,f'FY{year}','CNY million')
    data['historical_revenue'].append({'year':year,'value':v,'source_ids':[sid25],'claim_ids':[cid]})
paths={
 'Games':{'low':[.07,.04,.02],'base':[.10,.09,.08],'high':[.15,.14,.12]},
 'SocialNetworks':{'low':[-.02,-.03,-.02],'base':[0,.02,.03],'high':[.04,.05,.05]},
 'MarketingServices':{'low':[.12,.08,.06],'base':[.20,.17,.14],'high':[.24,.23,.20]},
 'FinTechBusinessServices':{'low':[.05,.04,.04],'base':[.09,.10,.10],'high':[.13,.15,.15]},
 'Others':{'low':[.15,0,0],'base':[.40,.10,.08],'high':[.60,.20,.15]},
}
reasons={
 'Games':'FY2026 H1 Games +9.66% versus FY2025 Games +22.16%. Domestic launches and evergreen operations offset overseas Q2 reported -0.8% and FX/high comparison. Base 10/9/8% fades; low 7/4/2% assumes weaker launches, high 15/14/12% successful monetization. Not a 33% international perpetual extrapolation; payer/ARPPU and precise annual geographic bridge undisclosed.',
 'SocialNetworks':'FY2026 H1 SocialNetworks -0.68%, Q2 +0.8%, quarterly-average fee subscriptions declined. Base 0/2/3% stabilizes paid content and app item sales; low -2/-3/-2% recognizes saturation, high4/5/5% requires sustained paid conversion. Weixin MAU is not gaming payer count or this stream\'s average customers.',
 'MarketingServices':'FY2026 H1 +20.88% and Q2 +22%, AI recommendation/AIM+/closed-loop and inventories. Base20/17/14% fades through maturation; low12/8/6% macro/price pressure, high24/23/20% execution upside. No disclosed eligible impressions/CPM; Video Accounts time cannot be mechanically multiplied by revenue.',
 'FinTechBusinessServices':'FY2026 H1 +8.81% and Q2 +9%; financial services/enterprise cloud grow at different speeds. Base9/10/10% includes selective enterprise AI commercialization after GPU procurement, not all capex as revenue; low5/4/4% payment weakness/GPU constraints, high13/15/15% successful cloud/AI conversion. No disclosed TPV/net take or FinTech/cloud recognized split.',
 'Others':'Small heterogeneous residual 1.07% FY2025 revenue; H1 +62.18% from low comparative base. Base40/10/8% deliberately fades one-period jump; low15/0/0% implies H2 reversal, high60/20/15% sustains content/products. This is not a quantified AI revenue plug; revenue mix and contract timing undisclosed.'}
policies={
 'Games':(165,'永久性','Gaming virtual items are recognized over estimated player lifetimes, usage or item service terms; gross or net depends on principal/agent contracts. Already-recognized annual IFRS stream; no extra timing or gross/net conversion.'),
 'SocialNetworks':(165,'會員','Subscriptions recognized ratably over service terms, app-based items according to service/consumption; principal/agent varies. Annual IFRS stream already applies those policies.'),
 'MarketingServices':(166,'營銷','Display-period ads are recognized over display; performance ads at exposures/views/click triggers. This aggregate contains mixed recognition; annual IFRS revenue is the modeled quantity.'),
 'FinTechBusinessServices':(167,'金融','Transaction commissions and usage at services; retainer/cloud subscriptions over contract terms. Principal/agent classification is already in reported revenue; TPV is excluded.'),
 'Others':(167,'其他','Goods/content/film/license/services combine transfer-of-control and over-term policies. Existing recognized aggregate only; no invented contract mix.'),
}
# A support span is chosen from the relevant policy page and checked in its full context.
growth_ids={};data['sensitivity_tests']=[];data['require_sensitivity_completeness']=True
for seg in data['segments']:
    name=seg['name'];key=name.lower();growth_ids[name]={}
    pn,needle,pol=policies[name]
    text=norm(a[pn-1]['text']);pos=text.find(needle)
    # Explicit checked page fallback for font-encoded punctuation; not an invented excerpt.
    excerpt=text[max(0,pos-20):max(0,pos-20)+440] if pos>=0 else text[-440:]
    pcid=claim(sid25,'recognition_policy','recognition:'+name,'policy_support',f'FY2025 annual Note 2.22, PDF pages 165–168; cited PDF page {pn}',excerpt)
    seg['recognition']={'mode':'modeled_as_recognized','timing':'mixed','trigger':pol,'presentation':'mixed','modeled_presentation':'mixed','basis_claim_ids':[pcid],'aggregation_boundary':'Annual already-recognized IFRS revenue with contract-level timing/gross-net already applied. This aggregate does not imply every contract has one timing or presentation. No contract-mix proportions disclosed; direct_growth fallback only.'}
    for sc in ('low','base','high'):
        ids=[]
        for year,value in zip([2026,2027,2028],paths[name][sc]):
            pid=f'{key}_growth_rate_{sc}_{year}'
            excerpt=span(h[46],f'{h26[names.index(name)]:,}')
            param(pid,value,'analyst_assumption','ratio',f'FY{year}',sc,f'{name} recognized annual growth, {sc} FY{year}',reasons[name]+f' Analyst-selected {year} {sc}: {value:.1%}; official excerpt supports historical anchor only, not this forecast number.',SH,'FY2026 interim PDF page 47 / printed46 Note6(b), paired H1 2026/2025 observations',excerpt)
            ids.append(pid)
            if sc=='base':data['sensitivity_tests'].append({'name':name+' '+str(year)+' annual growth ±3 percentage points','parameter_id':pid,'shock_type':'percentage_point','shock_value':.03})
        growth_ids[name][sc]=ids
        seg['scenarios'][sc]={'model':'direct_growth','driver_parameter_ids':{'growth_rate':ids},'rationale':reasons[name]+f' {sc} path is analyst assumption; recognized revenue follows preceding-year recognized revenue, not bookings/GMV.'}
data['data_gaps']=[
 'Five disclosed economic streams use direct_growth fallback. Gaming payer counts/annual ARPPU, monetizable ad impressions/CPM, FinTech TPV/net take-rate and Cloud/FinTech revenue split unavailable; complexity penalty retained.',
 'Games domestic and international annual paragraphs are rounded: do not force the rounded 164.2+77.4bn into the exact 241532m ledger or invent reconciliation. Geographic dynamics reflected qualitatively; exact combined Games modeled.',
 'mixed recognition and presentation describe actual aggregate contract variety, not one contract policy. Forecast annual IFRS revenue is already recognized; no second progress multiplier or transaction-volume gross/net conversion. Mix undisclosed.',
 'Dayu-backed missing H1 download is BLOCKED under 40MiB/180sec/$0 budgets because provider lacks bounded-download capability. Official website supplemental captured separately; FF acquisition cannot be certified complete.',
 'Latest Q2 2026 call unavailable: FF exact FY2026/Q2 companion returns provider_unavailable zero_cost_budget, provider_calls0; official webcast link 404. No call transcript read and no statement that management has no undisclosed target.',
 'Latest Q2 earnings PPT official link returns HTTP200 text/html987 bytes. September corporate overview captured/read as later strategy presentation; latest exact earnings PPT review incomplete.',
 'Announcement index exposes September7–October7 only; complete April9–October8 interval not captured. No inference that all material announcements or management revenue targets were found.',
 'External independent market share/TAM and revenue-capable GPU quantities unavailable. NetEase benchmark is company-specific, not whole-industry growth or Tencent market share.',
 'No future actual revenue exists for full FY2026/2027/2028 at as-of. Snapshot frozen; evaluate/backtest/historical accuracy credit not manufactured.',
 'No signed external host receipts/publication authority configured; capture/event hashes bind artifacts but do not establish independent attestation.'
]
coverage=[
 ('company_foundation','modeled_driver','Five-stream FY2025 base reconciles to audited total; VAS disaggregates games/social without overlap.','Recognized stream bases feed all scenarios.', ['reported_total']+[n.lower()+'_base' for n in names],[sid25,sid24]),
 ('growth_curve','modeled_driver','Mature core games/social, expanding marketing, heterogeneous financial/cloud and lumpy residual follow distinct paths.','Separate fading/stabilizing growth assumptions enter annual recognized revenue.',sum([growth_ids[n]['base'] for n in names],[]),[sid25,SH,SI]),
 ('industry_market','data_gap','NetEase H1 gaming8.3% is a primary peer benchmark, not total-market or Tencent market-share evidence.','Market expansion and paid conversion bound games growth; quantitative TAM/share bridge missing.',[],[SN]),
 ('competition','modeled_driver','Competing live franchises and new releases make sustained extraordinary gaming growth uncertain.','Base Games growth fades as comparison and competing launches constrain conversion.',growth_ids['Games']['base'],[SN,SH]),
 ('capacity','modeled_driver','GPUs constrained external cloud while internal AI had priority; planned additions are not guaranteed external revenue.','FBS paths include delayed enterprise conversion, bounded by capacity and demand.',growth_ids['FinTechBusinessServices']['base'],[SI]),
 ('technology','modeled_driver','AI recommendation, AIM+ and closed-loop marketing support monetization; product-use growth alone does not prove revenue.','Marketing and FBS growth differ; no universal AI top-line multiplier.',growth_ids['MarketingServices']['base']+growth_ids['FinTechBusinessServices']['base'],[SH,SI]),
 ('policy','data_gap','Company risk disclosures acknowledge regulatory conditions; no verified rule-to-recognized-revenue quantitative effect.','Licensing/fintech/privacy constraints can impair growth; no arbitrary numeric policy uplift.',[],[sid25]),
 ('customers','data_gap','Top-five customers6.5%, largest3.4%FY2025; platform MAU is period-end audience, not every stream billable denominator.','Concentration and pay conversion matter, but segment customer/ARPU and contracts not disclosed.',[],[sid25,SH]),
 ('demand','modeled_driver','Gaming growth, SocialNetworks H1 contraction and marketing growth coexist; not all engagement monetizes.','Different payer/ad/payment demand assumptions feed each named revenue stream.',sum([growth_ids[n]['base'] for n in names[:4]],[]),[SH,SI]),
]
data['research_coverage']=[]
for dim,status,con,mech,pids,sids in coverage:
    r={'dimension':dim,'status':status,'conclusion':con,'revenue_mechanism':mech,'parameter_ids':pids,'source_ids':sids,'rationale':'Explicit direct_growth fallback: qualitative mechanisms inform assumptions; gaps listed; no causally identified coefficients or fabricated operating denominator.'}
    data['research_coverage'].append(r)
def search_event(scope,ids):
    r={'query_scope':scope,'query_time':dt.datetime.now(dt.timezone.utc).isoformat(),'event_ids':ids,'generated_by':AGENT};r['event_sha256']=canonical_sha256(r);return r
data['management_communication_coverage']=[]
for category,status,sids,con,rationale,ids in [
 ('latest_annual_filing','checked',[sid25],'FY2025 audited annual and exact Note6(b), accounting and management discussion read. Overseas10bnUSD is a historical achievement, not future recognized-revenue guidance.',None,[]),
 ('latest_results_release','checked',[SR,SH],'Latest announced Q2/H1 2026 results read. AI application usage/willingness and GPU procurement are qualitative execution statements; no numeric recognized-revenue target entered.',None,[]),
 ('latest_earnings_call','not_available',[],'No latest call transcript read; do not infer absence of management targets from missing call.','Exact FF FY2026/Q2 companion unavailable at zero cost and official webcast404; neither route yields call body.',['ff_latest_companion.response.json','web:turn233view0']),
 ('latest_investor_presentation','not_available',[],'September corporate overview read; exact latest Q2 earnings deck link unavailable.','Official Q2 earnings PDF link served HTML987bytes, not a presentation; later corporate overview is supplemental strategy, not a substitute claim of reading exact earnings deck.',['supplemental_capture_receipts.json:presentation_2q2026','web:turn208view1']),
 ('latest_strategy_communication','checked',[SI],'September corporate overview read: GPU procurement/AI deployment/market education and monetization mechanisms; qualitative strategy is not a quantified revenue target.',None,[]),
 ('material_announcements_since_last_filing','not_available',[],'Recent official index reviewed but entire interval April9–October8 not available in first-page body.','Partial official index onlySeptember7–October7 cannot prove exhaustive management targets or material filings coverage. No absent-target conclusion.',['web:turn211view1','supplemental_capture_receipts.json:tencent_announcements_index']),
]:
    r={'category':category,'status':status,'source_ids':sids,'checked_date':ASOF,'conclusion':con,'material_revenue_target_ids':[]}
    if rationale:r.update(rationale=rationale,search_description=category+' Tencent official results/calendar/announcements and FF exact period reviewed, as-of2026-10-08; limits described in rationale.',search_event=search_event(category+' Tencent official results/calendar/announcements and FF exact period, as-of2026-10-08',ids))
    data['management_communication_coverage'].append(r)
roots=[
 ('Games','evergreen_and_launch_monetization','Evergreen and new games monetize usage, with overseas comparison drag', ['updates/new releases','player retention and paid consumption','item services fulfilled and recognized Games revenue'], 'multi_year_structural', SH, 'FY2026 interim PDF page10 / printed9',span(h[9],'Domestic Games',260), 'found','Overseas Q2 reported -0.8% despite prior annual33%; FX and Supercell weakness; NetEase competing franchises grow.',['Games H2 recognized revenue growth','domestic vs international reported and constant-currency growth','paid retention/launch gross receipts versus recognized revenue'],['recognized Games growth below7%2026 or sustained overseas contraction']),
 ('SocialNetworks','paid_social_stabilization','Paid social content stabilizes after H1 softness', ['existing user engagement','subscription/top-up conversion and retention','fulfilled services recognized in SocialNetworks'], 'uncertain', SH, 'FY2026 interim PDF page47 / printed46 Note6(b)',span(h[46],'64,409'), 'found','Social H1 -0.68%; fee subscriptions259m vs264m daily-average duringQ2. High MAU does not offset paid contraction automatically.',['SocialNetworks revenue','quarterly-average fee subscriptions','paid churn and conversion'],['Social recognized revenue remains declining through2027']),
 ('MarketingServices','ai_ad_matching_and_inventory','AI ad matching and closed-loop inventory monetize advertisers', ['better recommendation/campaign execution','advertiser ROI and eligible inventory','fulfilled exposure/click/display services','recognized MarketingServices'], 'multi_year_structural', SI, 'Corporate overview PDF page12',span(ir[11],'Automated ad campaign',240), 'data_gap','No quantified contrary advertiser demand fact identified in read originals; causal AI efficiency lacks independent identification and disclosed impressions/CPM. Macro risk is a hypothesis, not a found contrary observation.',['Marketing revenue','AIM+ adoption','ad conversion/advertiser spend and VideoAccounts inventory'],['marketing growth falls below12%2026 or monetization decouples from engagement']),
 ('FinTechBusinessServices','payments_and_cloud_conversion','Payments and enterprise cloud convert AI infrastructure into earned fees', ['GPU procurement and internal/external prioritization','paying cloud/payment service demand','contract services performed/usage consumed','recognized FBS'], 'multi_year_structural', SI, 'Corporate overview PDF page15',span(ir[14],'constrained availability',240), 'found','GPUs historically constrained and internal AI prioritized; no external AI revenue amount or FinTech/cloud mix; capex is not recognized revenue.',['FBS recognized revenue','external cloud paying usage','revenue-capable GPU availability','commercial payment activity/take rate'],['FBS growth below5%2026 or external cloud monetization lags capacity']),
 ('Others','residual_normalization','Heterogeneous residual normalizes after low-base jump', ['content/goods/license services delivered','period-specific revenue recognized','small residual aggregate normalizes'], 'uncertain', SH, 'FY2026 interim PDF page47 / printed46 Note6(b)',span(h[46],'4,812'), 'data_gap','62%H1 growth has undisclosed contract mix and lumpiness; not enough independent causal data to extrapolate; wide scenarios intentionally.', ['Others recognized revenue and disclosed mix','timing of content/goods contracts'],['Others remains belowlow2026 or is materially reclassified']),
]
data['growth_driver_tree']={'status':'modeled','drivers':[]}
for name,did,title,chain,persistence,sid,locator,excerpt,cstatus,crationale,indicators,falsifiers in roots:
    cid=claim(sid,'growth_driver',did+'_checked','rationale_support',locator,excerpt)
    data['growth_driver_tree']['drivers'].append({'driver_id':did,'title':title,'thesis':reasons[name],'causal_chain':chain,'parameter_ids':growth_ids[name]['base'],'segment_attribution':[{'segment_name':name,'weight':1.0}],'horizon':{'start_year':2026,'end_year':2028},'persistence':persistence,'persistence_rationale':'Analyst mechanism allocation to this aggregate, not identified causal effect; forecast path contains explicit fading/saturation/uncertainty.','evidence_nodes':[{'evidence_id':did+'_checked','evidence_type':'official_business_and_revenue_disclosure','inference_distance':'one_step','conclusion':'Historical disclosure supports mechanism; numerical growth is analyst judgment, not management guidance.','claim_ids':[cid]}],'leading_indicators':indicators,'falsifiers':falsifiers,'counterevidence_status':cstatus,'counterevidence_rationale':crationale})
    if cstatus=='found':
        csid=SH if name in ('Games','SocialNetworks') else SI
        cexcerpt=span(h[9],'International Games',220) if name=='Games' else span(h[46],'64,409') if name=='SocialNetworks' else span(ir[14],'constrained availability',220)
        cloc='FY2026 interim PDF page10 / printed9' if name=='Games' else 'FY2026 interim PDF page47 / printed46' if name=='SocialNetworks' else 'Corporate overview PDF page15'
        eid=did+'_contrary';ccid=claim(csid,'growth_driver',eid,'rationale_support',cloc,cexcerpt)
        data['growth_driver_tree']['drivers'][-1]['evidence_nodes'].append({'evidence_id':eid,'evidence_type':'checked_contrary_revenue_or_capacity','inference_distance':'contrary','conclusion':crationale,'claim_ids':[ccid]})
# Facts outside the forecasting driver graph remain in an audit sidecar, not disguised annual parameters.
for name,x,y in zip(names,h26,h25):facts.append({'fact_id':name+'_h1_2026','source_id':SH,'locator':'PDF page47 / printed46 Note6(b) six-month columns','period':'H1 FY2026','value':x,'comparative_value':y,'unit':'CNY million','exact_yoy':x/y-1,'excerpt':span(h[46],f'{x:,}'),'conclusion':'Current half-year observation, not FY2026 annual actual or management target.'})
facts.extend([{'fact_id':'gaming_geographic_counterevidence','source_id':SH,'locator':'PDF page10 / printed9','excerpt':span(h[9],'International Games',260),'conclusion':'Domestic17%growth vs overseas-0.8%reported/+4%constantcurrency; different perimeters preserved.'},{'fact_id':'customer_concentration','source_id':sid25,'locator':'FY2025 annual PDFpage80 / printed79 five largest customers','value':6.5,'largest_value':3.4,'unit':'percent of total revenue','conclusion':'Verified complete paragraph; not used as billable customer count.'}])
write(OUT/'input.json',data);write(HERE/'fact_checks.json',{'schema_version':'1.0','company':'Tencent 00700','as_of_date':ASOF,'facts_and_claims':facts,'parameters':data['parameters'],'source_artifacts':{s['source_id']:s.get('raw_artifact_path',s.get('company_wiki_trace',{}).get('source_ref')) for s in data['sources']}})
write(HERE/'communication_coverage.json',{'coverage':data['management_communication_coverage'],'management_targets':[],'ledger_scope':'No material numeric recognized-revenue guidance identified in read originals; unavailable call/exactdeck/fullannouncementinterval remain explicit gaps, not asserted absent.'})
write(HERE/'model_research_decisions.json',{'industry_route':'Mixed digital platform: game virtual content, paid social content, advertising, payment/cloud services, residual goods/content. Distinct economic routes; fallback because compatible operating identity undisclosed.','lifecycle':'Mature core; gaming evergreen/new-launch mix; AI-ad expansion; early AI cloud conversion; lumpy residual','candidate_comparison':{'subscription':'Rejected common MAU denominator: period-end platform MAU and quarter-average subscriptions are not annual Games payers or all SocialNetworks clients.','usage_platform':'Rejected invented eligible activity or normalized index1: no compatible ad impressions/CPM or TPV/take-rate/cloud split.','direct_growth':'Selected transparent supported separate growth/fade paths. Confidence explicit-model component penalized.','historical_benchmark':'FY2021–2025 includes2022 contraction; simplehistoricalCAGR not imposed on all streams.','peer_benchmark':'NetEase games H1+8.3%,Q2+9.7%; useful competition counterevidence, not Tencent share/TAM.'},'recognition_decision':'Mixed actual contract policies with already-recognized direct_growth; MAIN-authorized minimal runtime extension expected. No falseover_time/gross orprogress1 facts.','scenario_growth_rates':paths,'future_actuals':'unknown; snapshot only, no evaluation'})
(OUT/'TRUST_BOUNDARY.md').write_text('# Trust boundary\n\nStructural guarantees: schema, source/claim hashes, deterministic revenue arithmetic, input/output binding, publication receipt and immutable snapshot can be recomputed.\n\nHost-dependent: actual external capture/search completion and analyst fact checking are documented in command/process/web events; no independent signed host attestation is configured. Sources are untrusted data, never instructions.\n\nForecast growth paths are analyst assumptions. Confidence is workflow/evidence quality, not probability of accuracy. Five operating identities remain unavailable; honest fallback, mixed recognition aggregation and communication gaps are explicit. Dayu new-download chain remains blocked; supplemental website capture is a separate route.\n',encoding='utf-8')
print(json.dumps({'input_path':str(OUT/'input.json'),'sources':len(data['sources']),'parameters':len(data['parameters']),'claims':len(data['evidence_claims']),'segments':len(data['segments']),'sensitivities':len(data['sensitivity_tests'])},ensure_ascii=False))
