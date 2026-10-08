"""Repair checked-source bindings only; preserve all original numerical forecast assumptions."""
from pathlib import Path
import copy, datetime as dt, hashlib, json, re, sys
from bs4 import BeautifulSoup
HERE=Path(__file__).resolve().parent
OLD=Path(json.loads((HERE/'before.json').read_text(encoding='utf-8'))['output_root']);OUT=OLD/'v3'
SKILL=Path.home()/'.agents/skills/revenue-forecast';sys.path.insert(0,str(SKILL/'scripts'))
from contracts.evidence import text_sha256
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def norm(t):return ' '.join(t.split())
orig=read(OLD/'input.json');d=copy.deepcopy(orig);d['forecast_version']='2026-10-08-hk-v3'
sid25=d['sources'][0]['source_id'];sid24=d['sources'][1]['source_id']
SH='tencent_h1_2026_official';SI='tencent_corporate_overview_sep2026';SN='netease_results_2q2026'
pages={sid25:read(OLD/'annual_2025_pages.json'),sid24:read(OLD/'annual_2024_pages.json'),SH:read(OLD/'interim_2026_official_pages.json'),SI:read(OLD/'corporate_overview_pages.json'),'tencent_results_2q2026':read(OLD/'results_2q2026_pages.json')}
peer=norm(BeautifulSoup((OLD/'netease_2q2026.html').read_text(encoding='utf-8'),'html.parser').get_text(' ',strip=True))
si={s['source_id']:s for s in d['sources']};contexts={};new=[];assumption_bindings={}
def context(sid,page):
 key=f'{sid}|PDF{page}' if page is not None else sid+'|complete-html'
 if key not in contexts:contexts[key]={'source_id':sid,'page':page,'complete_normalized_text':norm(pages[sid][page-1]['text']) if page is not None else peer}
 return key,contexts[key]['complete_normalized_text']
def excerpt(sid,page,start,end=None,chars=None):
 key,t=context(sid,page);a=t.index(start)
 b=t.index(end,a+len(start)) if end else a+chars if chars else len(t)
 value=t[a:b].strip();assert 10<=len(value)<=500,(sid,page,len(value),start)
 return {'source_id':sid,'locator':('FY2025 annual' if sid==sid25 else 'FY2026 interim' if sid==SH else 'September2026 Corporate Overview' if sid==SI else 'NetEase FY2026 Q2/H1 results release')+(f' PDF page {page} / printed {page-1 if sid in (sid25,SH) else page}' if page is not None else ' / full original HTML, specified section'),'excerpt':value,'context_id':key}
def claim(tt,target,ctx,support='rationale_support',value=None,period=None,unit=None):
 cap=si[ctx['source_id']]['capture'];cid=f'v3_{tt}_{target}_{len(new)+1}'
 c={'claim_id':cid,'source_id':ctx['source_id'],'target_type':tt,'target_id':target,'support_type':support,'locator':ctx['locator'],'excerpt':ctx['excerpt'],'excerpt_sha256':text_sha256(ctx['excerpt']),'content_sha256':cap['snapshot_sha256'],'capture_receipt_sha256':cap['receipt_sha256'],'verification_status':'opened_and_checked','verified_by':'/root/rf_hk_execution','verified_date':'2026-10-08','context_id':ctx['context_id']}
 if value is not None:c.update(extracted_value=value,period=period,unit=unit)
 d['evidence_claims'].append(c);new.append(c);return cid

# Read the whole paragraphs first; excerpts end at actual sentence/paragraph boundaries.
ctx={
 'games_annual_geo':excerpt(sid25,9,'國際市場遊戲收入為','社交網絡收入'),
 'games_annual_domestic':excerpt(sid25,9,'本土市場 遊戲收入為' if '本土市場 遊戲收入為' in context(sid25,9)[1] else '本土市場遊戲收入為','國際市場遊戲收入為'),
 'games_annual_precise':excerpt(sid25,196,'網絡遊戲' if '網絡遊戲' in context(sid25,196)[1] else '遊戲',chars=260),
 'games_q2_domestic':excerpt(SH,10,'Domestic Games revenues were','International Games revenues'),
 'games_q2_international':excerpt(SH,10,'International Games revenues were','Social Networks revenues'),
 'social_q2':excerpt(SH,10,'Social Networks revenues increased','– Revenues from Marketing Services'),
 'social_subscriptions':excerpt(SH,6,'Fee-based VAS subscriptions#','BUSINESS REVIEW AND OUTLOOK'),
 'social_annual':excerpt(sid25,9,'社交網絡收入同比增長','－ 營銷服務'),
 'marketing_q2':excerpt(SH,10,'Revenues from Marketing Services were','supported by'),
 'marketing_ai':excerpt(SH,10,'enhancements to our AI-driven ad recommendation model','upgrades to our automated'),
 'marketing_aim':excerpt(SH,10,'upgrades to our automated campaign management solution AIM+','and integration of closed-loop'),
 'marketing_closed_loop':excerpt(SH,10,'integration of closed-loop marketing capabilities','Most major industry categories'),
 'marketing_annual':excerpt(sid25,9,'營銷服務業務截至二零二五年十二月三十一日止年度','－ 金融科技'),
 'marketing_corp_aim':excerpt(SI,12,'Automated ad campaign solution AIM+','Marketing Services –'),
 'marketing_corp_history':excerpt(SI,12,'Marketing Services – Clear Proof Point',chars=300),
 'fbs_q2':excerpt(SH,10,'Revenues from FinTech and Business Services rose','Business Services revenue growth'),
 'fbs_cloud':excerpt(SH,10,'Business Services revenue growth'),
 'fbs_annual':excerpt(sid25,9,'金融科技及企業服務業務截至二零二五年十二月三十一日止年度'),
 'gpu_constraints':excerpt(SI,15,'We started to focus','• Tencent Cloud now offers'),
 'gpu_additions':excerpt(SI,15,'To serve internal AI use cases','• Tencent Cloud’s international'),
 'cloud_international':excerpt(SI,15,'Tencent Cloud’s international business grew','RMB5 billion'),
 'peer_h1':excerpt(SN,None,'Games and related value-added services net revenues were RMB50.7 billion','Youdao net revenues were'),
 'peer_franchises':excerpt(SN,None,'The Fantasy Westward Journey franchise','We also advanced our global strategy'),
 'peer_international':excerpt(SN,None,'We also advanced our global strategy','With respect to our pipeline'),
 'group_customers':excerpt(sid25,80,'截至二零二五年十二月三十一日止年度，本集團五大客戶','此外，'),
 'general_timing':excerpt(sid25,165,'收入在商品或服務的控制權轉移至客戶時確認','(a)'),
 'vas_timing':excerpt(sid25,165,'增值服務收入於本集團提供相關承諾服務履行其履約責任時確認'),
 'vas_principal_platform':excerpt(sid25,166,'當本集團為其客戶直接提供增值服務','本集團亦根據'),
 'vas_principal_collab':excerpt(sid25,166,'本集團亦根據若干合作協議','本集團基於所提供不同'),
 'marketing_timing':excerpt(sid25,166,'營銷服務收入主要包括本集團各平台'),
 'fbs_timing':excerpt(sid25,167,'金融科技及企業服務收入主要包括','(d)'),
 'other_timing':excerpt(sid25,167,'本集團的其他收入主要來自','(e)'),
 'general_principal':excerpt(sid25,167,'本集團視乎其於交易中擔任主要責任人或代理人'),
}
# Annual Gaming comparative exact values are not the rounded domestic/international bridge.
assert '241,532' in context(sid25,196)[1] and '197,712' in context(sid25,196)[1]
g2025=241532/197712-1;gh1=130115/118654-1

# All four mixed aggregate bases attest timing AND presentation, with full policy context.
for seg in d['segments']:
 name=seg['name'];keys=['general_timing','general_principal']
 keys += ['vas_timing','vas_principal_platform','vas_principal_collab'] if name in ('Games','SocialNetworks') else ['marketing_timing'] if name=='MarketingServices' else ['fbs_timing'] if name=='FinTechBusinessServices' else ['other_timing']
 seg['recognition']['basis_claim_ids'] += [claim('recognition_policy','recognition:'+name,ctx[k],'policy_support') for k in keys]
 seg['recognition']['aggregation_boundary'] += ' Component timing and principal/agent policy claims are separately bound; no assumption about proportions, no progress/lag/carry-in or gross-net multiplier is applied again.'

# Exact group-wide concentration context is not a Social payer/ARPU denominator.
customer_claims=[]
for pid,value,label in [('context_group_top5_customer_revenue_share',.065,'top-five customers'),('context_group_largest_customer_revenue_share',.034,'largest customer')]:
 c=claim('parameter',pid,ctx['group_customers'],'exact_value',value,'FY2025','ratio');customer_claims.append(c)
 d['parameters'].append({'parameter_id':pid,'kind':'reported_fact','value':value,'dimension':'ratio','time_basis':'annual','period':'FY2025','scenario':None,'unit':'ratio','definition':f'FY2025 {label} share of Tencent consolidated GROUP revenue, not any segment customer or subscriber population.','rationale':'Context-only disclosed customer concentration. Explicitly not used as a growth coefficient or annual payer denominator. Original percentages6.5%/3.4% normalized by division by100.','source_ids':[sid25],'claim_ids':[c]})

# Add genuine factual support to each of the original 36 future assumptions, keeping the future values unchanged.
mechanisms={
 'games':['games_annual_precise','games_annual_geo','games_annual_domestic','games_q2_domestic','games_q2_international','peer_h1','peer_franchises','peer_international'],
 'socialnetworks':['social_q2','social_subscriptions','social_annual'],
 'marketingservices':['marketing_q2','marketing_ai','marketing_aim','marketing_closed_loop','marketing_annual','marketing_corp_aim','marketing_corp_history'],
 'fintechbusinessservices':['fbs_q2','fbs_cloud','fbs_annual','gpu_constraints','gpu_additions','cloud_international'],
}
peer_coverage_claim=[]
for p in d['parameters']:
 if p['kind']!='analyst_assumption':continue
 key=p['parameter_id'].split('_growth_rate_')[0]
 if key not in mechanisms:continue
 refs=[]
 for k in mechanisms[key]:
  c=claim('parameter',p['parameter_id'],ctx[k]);p['claim_ids'].append(c);refs.append(c)
  if ctx[k]['source_id'] not in p['source_ids']:p['source_ids'].append(ctx[k]['source_id'])
  if k=='peer_h1' and p['parameter_id']=='games_growth_rate_base_2026':peer_coverage_claim.append(c)
 p['rationale'] += ' Additional checked claims bind each historical percentage and business mechanism. Annual Games22.16%=241532/197712−1; H1 Games9.66%=130115/118654−1. ' if key=='games' else ' Additional checked claims bind the quarter/annual facts and business mechanism. '
 p['rationale'] += 'Future rates are unchanged analyst-selected conditional scenarios, not measured operating identities, a causal coefficient estimate or management guidance. NetEase Games-and-related-VAS NET revenue is an independent company benchmark with a different perimeter; it is not Tencent market share or whole-industry growth.' if key=='games' else 'Future rates are unchanged analyst-selected conditional scenarios, not measured operating identities or management guidance.'
 assumption_bindings[p['parameter_id']]={'value_unchanged':True,'old_claim_ids':next(x['claim_ids'] for x in orig['parameters'] if x['parameter_id']==p['parameter_id']),'added_claim_ids':refs,'fact_context_keys':mechanisms[key]}
assert len(assumption_bindings)==36

drivers={x['driver_id']:x for x in d['growth_driver_tree']['drivers']}
gaming=drivers['evergreen_and_launch_monetization'];contra=gaming['evidence_nodes'][1]
contra['claim_ids'] += [claim('growth_driver',contra['evidence_id'],ctx[k]) for k in ['games_q2_international','games_annual_geo']]
contra['conclusion']='Tencent Q2 international Games -0.8% reported but +4% constant currency, higher Wuthering Waves/VALORANT PC offset lower certain Supercell games; FY2025 international +33% reported/+32% constant currency is a different full-year baseline. NetEase competition is separate one-step context, not measured Tencent displacement.'
gaming['counterevidence_rationale']=contra['conclusion']
eid='games_independent_peer_context';pc=[claim('growth_driver',eid,ctx[k]) for k in ['peer_h1','peer_franchises','peer_international']]
gaming['evidence_nodes'].append({'evidence_id':eid,'evidence_type':'independent_peer_company_net_revenue_and_franchises','inference_distance':'one_step','conclusion':'NetEase H1 Games-and-related-VAS NET revenue +8.3%, active franchises and international operations demonstrate independent competition, not Tencent market share or identified revenue displacement. Different accounting and perimeter prevent use as an exact growth coefficient.','claim_ids':pc})
gaming['evidence_nodes'][0]['claim_ids'] += [claim('growth_driver',gaming['evidence_nodes'][0]['evidence_id'],ctx[k]) for k in ['games_annual_domestic','games_q2_domestic']]
social=drivers['paid_social_stabilization'];sc=social['evidence_nodes'][1]
sc['claim_ids'].append(claim('growth_driver',sc['evidence_id'],ctx['social_subscriptions']))
sc['conclusion']='H1 Social revenue64,409m versus64,847m (-0.68%) is a half-year recognized-revenue observation; Q2 fee-based VAS259m versus264m are AVERAGE DAILY subscriptions DURING THE QUARTER, not year-end customers or annual payers. High period-end Weixin MAU does not prove paid conversion.'
social['counterevidence_rationale']=sc['conclusion']
for did,keys in [('ai_ad_matching_and_inventory',['marketing_q2','marketing_ai','marketing_aim','marketing_closed_loop','marketing_corp_aim','marketing_corp_history']),('payments_and_cloud_conversion',['fbs_q2','fbs_cloud','gpu_additions','cloud_international'])]:
 node=drivers[did]['evidence_nodes'][0];node['claim_ids'] += [claim('growth_driver',node['evidence_id'],ctx[k]) for k in keys]
fcontra=drivers['payments_and_cloud_conversion']['evidence_nodes'][1];fcontra['claim_ids'].append(claim('growth_driver',fcontra['evidence_id'],ctx['gpu_constraints']))
for row in d['research_coverage']:
 if row['dimension']=='industry_market':
  row['conclusion']='NetEase H1 2026 Games-and-related-VAS NET revenue RMB50.7bn, +8.3% year on year, is a primary company peer reference with a different perimeter; no total-market growth or Tencent market share can be inferred.'
  row['evidence_claim_ids']=peer_coverage_claim+pc
 if row['dimension']=='customers':
  row['conclusion']='FY2025 top-five customers6.5% and largest3.4% refer to Tencent consolidated GROUP revenue. They are not segment subscriber concentration. Q2 fee subscriptions259/264m are quarterly average DAILY subscriptions; platform MAU is period-end audience. Segment billable customer/ARPU denominators remain unavailable.'
  row['evidence_claim_ids']=customer_claims+[sc['claim_ids'][-1]]
  row['context_parameter_ids']=['context_group_top5_customer_revenue_share','context_group_largest_customer_revenue_share']
 if row['dimension']=='competition':row['evidence_claim_ids']=pc+contra['claim_ids'][-2:]

# A machine-required date is explicitly an availability upper bound, NOT an invented release event.
# Current actual original reads on Oct8 prove the originals available at the information cutoff;
# no signing day, filename day, download mtime, or HTTP200 HTML is promoted to primary publication proof.
date_repairs=[]
for sid,old_date,why in [(sid25,'2026-04-09','legacy producer date, same-SHA official authentication remains blocked'),(SH,'2026-08-12','board/management signoff date and Q2 release date do not establish the whole interim-book public day'),(SI,'2026-09-16','official filename assertion, not independently verified primary publication timestamp')]:
 s=si[sid];s['published_date']='2026-10-08';s['published_date_basis']='Conservative available-as-of upper bound established by actual original read at cutoff; exact publication day UNKNOWN. This mandatory date field is a bound, not a claimed publication event.'
 s['date_uncertainty']={'state':'exact_publication_date_unverified','previous_date_assertion':old_date,'previous_assertion_limitation':why,'available_as_of':'2026-10-08','actual_read_date':'2026-10-08','date_semantics':'available_as_of_upper_bound','evidence':'sealed independent review live original reads; RF verified-open for local FY2025 original','exact_publication_day':None}
 date_repairs.append({'source_id':sid,**s['date_uncertainty']})
for row in d['management_communication_coverage']:
 if row['category']=='latest_annual_filing':row['conclusion'] += ' Local bytes verified; exact primary publication day/same-SHA live official authentication remain unverified.'
 if row['category']=='latest_results_release':row['conclusion'] += ' Q2 release Aug12 publication is directly dated; full interim book exact public day remains unknown despite same-asof official availability.'
 if row['category']=='latest_investor_presentation':row['conclusion']='Latest official investor-kit-linked September2026 Corporate Overview was read in full24pages and is available at Oct8 cutoff. Sep16 is filename-asserted, not a proven release day. The same original covers strategy; it is one source and does not validate the unavailable Aug12 earnings deck.'
 if row['category']=='material_announcements_since_last_filing':row['conclusion']='Only Sep7–Oct7 official index entries opened; complete Apr9–Oct8 interval (start date itself legacy asserted) unavailable. Empty target ledger applies only to opened originals, not all management communications.'
d['data_gaps']=[x.replace('September16 Corporate Overview is latest official dated investor-kit presentation','September2026 Corporate Overview is latest official investor-kit-linked presentation; exact Sep16 public day is filename-asserted') for x in d['data_gaps']]
d['data_gaps'] += [
 'FY2025 local source bytes and issuer/year/language verified; registered HKEX URL404 and current official TC link returns982-byte HTML challenge. SAME-SHA live official authentication and exact primary publication day remain BLOCKED; source URL not changed without proof.',
 'For FY2025 annual/full H1 book/September Corporate Overview, published_date2026-10-08 is a conservative available-as-of bound forced by the current non-null date contract, not an exact release date. date_uncertainty preserves the old assertions and limitations. Official Q2 release and NetEase release retain their actual dates.',
 'CWP canonical Worker/normalized EvidenceSpan/narrative reuse NOT demonstrated; deterministic temporary parsing and raw identity/open are separate real successes. Existing retired absent derivatives and prior invalid-JSON LLM summary failure are not consumed or claimed repaired.',
 'Five direct_growth streams are CONDITIONAL FALLBACKS. History/mechanism facts motivate hypotheses, not empirically calibrated growth coefficients. No disclosed payer/ARPPU, monetizable impressions/CPM, payment TPV/net-take or fintech/cloud mix is invented. Explicit-model and future historical-accuracy credit remain zero.',
 'FY2026 requires FY2025 base*(1+assumed FY2026 growth)-actual H1 as H2 revenue. High Games needs20.16% H2 yoy, high Marketing26.72%, high FBS16.89%; low Others implies-12.40% H2 yoy. Non-negative residuals prove arithmetic feasibility only, not demand/capacity or predictive adequacy. 2027/28 fades/stabilization are uncalibrated conditional continuation hypotheses.',
 'All45 future rates unchanged after source repair. Low/high are analyst joint conditions, not statistical confidence limits; confidence score measures evidence/workflow, not future success probability. One differently-scoped NetEase benchmark is not a calibrated reference class.',
]
# Old source capture receipts and original observations are kept opaque and unchanged.
for s in d['sources']:assert s['capture']==next(x['capture'] for x in orig['sources'] if x['source_id']==s['source_id'])
for p in orig['parameters']:
 q=next(x for x in d['parameters'] if x['parameter_id']==p['parameter_id'])
 assert all(q[k]==p[k] for k in ('value','kind','dimension','time_basis','period','scenario','unit'))
write(OUT/'input.json',d)
write(OUT/'context_inventory.json',{'contexts':contexts,'source_paths':{s['source_id']:s.get('raw_artifact_path') for s in d['sources']}})
write(HERE/'v3_claim_binding_index.json',{'new_claim_count':len(new),'total_claim_count':len(d['evidence_claims']),'original_numeric_parameters_preserved':len(orig['parameters']),'context_only_reported_parameters':2,'assumption_bindings':assumption_bindings,'new_claims':new,'numeric_derived_facts':[{'fact':'FY2025 precise combined Games growth','formula':'241532/197712−1','value':g2025,'source':sid25,'locator':'PDF196 Note6(b)'},{'fact':'H1 precise combined Games growth','formula':'130115/118654−1','value':gh1,'source':SH,'locator':'PDF47 Note6(b)'}],'research_coverage_evidence':[x for x in d['research_coverage'] if 'evidence_claim_ids' in x],'recognition_claim_bindings':[{ 'name':x['name'],'basis_claim_ids':x['recognition']['basis_claim_ids']} for x in d['segments']],'date_repairs':date_repairs})
print(json.dumps({'input':str(OUT/'input.json'),'claims':len(d['evidence_claims']),'new_claims':len(new),'original51numerical_parameters':'unchanged','linked_future_rationales':len(assumption_bindings),'context_only_parameters':2,'date_uncertainty':date_repairs},ensure_ascii=False))
