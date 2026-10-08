"""Strong input-required checks plus independent arithmetic for every path and sensitivity."""
from pathlib import Path
import json, sys, math, hashlib, datetime as dt, re
from bs4 import BeautifulSoup
HERE=Path(__file__).resolve().parent;OLD=Path(json.loads((HERE/'before.json').read_text(encoding='utf-8'))['output_root']);OUT=OLD/'v3'
SKILL=Path.home()/'.agents/skills/revenue-forecast';sys.path.insert(0,str(SKILL/'scripts'))
from revenue_report import validate_published_forecast,render_markdown
from revenue_backtest import validate_snapshot
from contracts.evidence import text_sha256
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
i=read(OUT/'input.json');f=read(OUT/'forecast.json');s=read(OUT/'snapshot.json');oldi=read(OLD/'input.json');oldf=read(OLD/'forecast.json')
validate_published_forecast(f,i);validate_snapshot(s)
assert render_markdown(f)==(OUT/'forecast.md').read_text(encoding='utf-8')
pi={p['parameter_id']:p for p in i['parameters']};fy=[str(y) for y in i['forecast_years']];scenarios=('low','base','high')
for p in oldi['parameters']:
 q=pi[p['parameter_id']]
 assert all(p[k]==q[k] for k in ('value','kind','period','scenario','unit','dimension','time_basis'))
calc={sc:{y:0.0 for y in fy} for sc in scenarios};curves=[];h2=[]
h1new=[130115,64409,81736,120171,4812];h1old=[118654,64847,67615,110443,2967]
def terminal(shock_id=None,value=None):
 result=0.0
 for seg in i['segments']:
  r=pi[seg['base_revenue_parameter_id']]['value']
  for pid in seg['scenarios']['base']['driver_parameter_ids']['growth_rate']:r*=1+(value if pid==shock_id else pi[pid]['value'])
  result+=r
 return result
for n,seg in enumerate(i['segments']):
 fseg=next(x for x in f['segments'] if x['name']==seg['name']);base=pi[seg['base_revenue_parameter_id']]['value']
 assert seg['recognition']['mode']=='modeled_as_recognized'
 assert all(seg['recognition'][k]=='mixed' for k in ('timing','presentation','modeled_presentation'))
 assert not any(k in seg['recognition'] for k in ('progress_parameter_ids','lag_years','carry_in_parameter_ids'))
 for sc in scenarios:
  r=float(base);path={}
  for y,pid in zip(fy,seg['scenarios'][sc]['driver_parameter_ids']['growth_rate']):
   r*=1+pi[pid]['value'];path[y]=r;calc[sc][y]+=r
   assert math.isclose(r,fseg['scenarios'][sc]['recognized_revenue'][y],abs_tol=1e-6,rel_tol=0)
   assert math.isclose(r,fseg['scenarios'][sc]['effective_revenue'][y],abs_tol=1e-6,rel_tol=0)
  old_h2=base-h1old[n];new_h2=path['2026']-h1new[n];assert old_h2>0 and new_h2>=0
  h2.append({'segment':seg['name'],'scenario':sc,'H2_2025':old_h2,'H2_2026_required':new_h2,'H2_required_yoy':new_h2/old_h2-1,'FY2026':path['2026'],'actual_H1_2026':h1new[n],'unit':'CNY million','economic_status':'conditional analyst requirement; non-negative does not establish demand/capacity or forecast accuracy'})
  curves.append({'segment':seg['name'],'scenario':sc,'annual':path})
for sc in scenarios:
 for y in fy:
  assert math.isclose(calc[sc][y],f['consolidated_forecast'][sc]['annual_revenue'][y],abs_tol=1e-6,rel_tol=0)
  assert math.isclose(calc[sc][y],oldf['consolidated_forecast'][sc]['annual_revenue'][y],abs_tol=1e-6,rel_tol=0),'Old forecast numbers changed'
 expected=(calc[sc]['2028']/751766)**(1/3)-1
 assert math.isclose(expected,f['consolidated_forecast'][sc]['cagr'],abs_tol=1e-10,rel_tol=0)
 assert math.isclose(calc[sc]['2028']-751766,f['consolidated_forecast'][sc]['incremental_revenue'],abs_tol=1e-6,rel_tol=0)
for y in fy:assert calc['low'][y]<=calc['base'][y]<=calc['high'][y]
sens=[]
for x in f['sensitivities']:
 assert x['shock_type']=='percentage_point' and x['shock_value']==.03
 pid=x['parameter_id'];assert pi[pid]['scenario']=='base'
 rec={'parameter_id':pid,'baseline_terminal':terminal(),'shocked_terminal':{}}
 assert math.isclose(terminal(),x['baseline_terminal_revenue'],abs_tol=1e-6,rel_tol=0)
 for direction,delta in [('down',-.03),('up',.03)]:
  expected_value=pi[pid]['value']+delta
  assert math.isclose(x['requested_values'][direction],expected_value,abs_tol=1e-12,rel_tol=0)
  assert math.isclose(x['effective_values'][direction],expected_value,abs_tol=1e-12,rel_tol=0)
  v=terminal(pid,expected_value);assert math.isclose(v,x[direction+'_terminal_revenue'],abs_tol=1e-6,rel_tol=0)
  rec['shocked_terminal'][direction]=v
 assert math.isclose(max(abs(v-terminal()) for v in rec['shocked_terminal'].values()),x['max_absolute_terminal_impact'],abs_tol=1e-6,rel_tol=0)
 sens.append(rec)
assert len(sens)==15 and len({x['parameter_id'] for x in sens})==15
# Byte-derived context checking of all 318? claims, rather than trusting the binder ledger.
sid25=i['sources'][0]['source_id'];sid24=i['sources'][1]['source_id'];SH='tencent_h1_2026_official';SI='tencent_corporate_overview_sep2026';SN='netease_results_2q2026'
pg={sid25:read(OLD/'annual_2025_pages.json'),sid24:read(OLD/'annual_2024_pages.json'),SH:read(OLD/'interim_2026_official_pages.json'),SI:read(OLD/'corporate_overview_pages.json'),'tencent_results_2q2026':read(OLD/'results_2q2026_pages.json')}
peer=' '.join(BeautifulSoup((OLD/'netease_2q2026.html').read_text(encoding='utf-8'),'html.parser').get_text(' ',strip=True).split());si={x['source_id']:x for x in i['sources']}
claimchecks=[]
for c in i['evidence_claims']:
 if c['source_id']==SN:t=peer
 else:
  m=re.search(r'PDF\s+page\s*(\d+)',c['locator'],re.I);assert m,c['locator'];t=' '.join(pg[c['source_id']][int(m.group(1))-1]['text'].split())
 assert c['excerpt'] in t,c['claim_id']
 assert text_sha256(c['excerpt'])==c['excerpt_sha256']
 assert c['content_sha256']==si[c['source_id']]['capture']['snapshot_sha256']
 assert c['capture_receipt_sha256']==si[c['source_id']]['capture']['receipt_sha256']
 claimchecks.append({'claim_id':c['claim_id'],'source_id':c['source_id'],'locator':c['locator'],'exact_original_context_containment':'PASS','target_type':c['target_type'],'target_id':c['target_id'],'claim_excerpt_sha256':'PASS','capture_binding':'PASS'})
ci={c['claim_id']:c for c in i['evidence_claims']}
for row in i['research_coverage']:
 for cid in row.get('evidence_claim_ids',[]):assert cid in ci
assert f['confidence']['components']['revenue_weighted_explicit_models']==0 and f['confidence']['components']['historical_accuracy']==0
checks={'timestamp_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'strong_input_required_validator':'PASS','immutable_snapshot_validator':'PASS','same_result_markdown':'PASS','all45_original_annual_growth_values':'UNCHANGED','all6_original_bases':'UNCHANGED','all45_segment_year_paths':'PASS','all9_company_year_paths':'PASS','CAGR_increment_bridges':'PASS','old_numeric_forecast_comparison':'UNCHANGED','all15_independent_sensitivities':'PASS','all_claim_original_context_checks':claimchecks,'context_check_count':len(claimchecks),'independent_paths':curves,'consolidated':calc,'H2_requirements':h2,'independent_sensitivity_details':sens,'recognition':'Already recognized mixed aggregate, no second progress/timing/gross-net transformation','confidence_score':f['confidence']['score'],'accuracy_claim':'NONE; workflow evidence score only','scope':'Execution verification only; independent reviewer must sign','future_backtest':'NOT_APPLICABLE: full FY2026-2028 actuals not published as of cutoff'}
(HERE/'v3_delivery_verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'strong_validation':'PASS','same_source_render':'PASS','snapshot':'PASS','old_forecast_numbers':'UNCHANGED','claim_count':len(claimchecks),'sensitivities':len(sens),'confidence':f['confidence']['score'],'consolidated':calc},ensure_ascii=False))
