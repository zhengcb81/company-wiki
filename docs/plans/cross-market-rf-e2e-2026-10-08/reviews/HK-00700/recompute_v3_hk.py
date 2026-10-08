import sys, os, json, math, hashlib, shutil, subprocess, datetime as dt
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
EX=HERE.parents[1]/'executions/HK-00700'
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
old_m=load(EX/'manifest.json');m=load(EX/'manifest_v3.json');OUT=Path(m['output_root']);SKILL=Path(old_m['skill_root'])
REPLAY=OUT.parent/'review-HK-00700-rf_hk_independent_review-v3'
REPLAY.mkdir(exist_ok=True)
os.environ['REVENUE_PUBLICATION_REGISTRY']=str(REPLAY/'publications.jsonl')
sys.path.insert(0,str(SKILL/'scripts'))
from revenue_report import validate_published_forecast,render_markdown
from revenue_backtest import validate_snapshot
i=load(OUT/'input.json'); f=load(OUT/'forecast.json');s=load(OUT/'snapshot.json')
validate_published_forecast(f,i);validate_snapshot(s)
assert render_markdown(f)==(OUT/'forecast.md').read_text(encoding='utf-8')
shutil.copyfile(OUT/'input.json',REPLAY/'input.json')
cmd=[sys.executable,'-B',str(SKILL/'scripts/revenue_forecast.py'),str(REPLAY/'input.json'),'--output',str(REPLAY/'forecast.json'),'--markdown',str(REPLAY/'forecast.md')]
started=dt.datetime.now(dt.timezone.utc).isoformat();r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8')
(REPLAY/'cli.stdout.txt').write_text(r.stdout,encoding='utf-8');(REPLAY/'cli.stderr.txt').write_text(r.stderr,encoding='utf-8')
assert r.returncode==0,(r.returncode,r.stderr)
fresh=load(REPLAY/'forecast.json');validate_published_forecast(fresh,i)
def scrub(v):
 if isinstance(v,dict):return {k:scrub(x) for k,x in v.items() if k not in ['publication_receipt','result_sha256','generated_at','created_at','timestamp','receipt_sha256']}
 if isinstance(v,list):return [scrub(x) for x in v]
 return v
assert scrub(f)==scrub(fresh),'independent CLI deterministic payload mismatch'
pi={p['parameter_id']:p for p in i['parameters']};years=[str(y) for y in i['forecast_years']]
close=lambda a,b:math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-6)
curves={};totals={sc:{y:0.0 for y in years} for sc in ['low','base','high']};paths=[]
for seg in i['segments']:
 base=pi[seg['base_revenue_parameter_id']]['value'];curves[seg['name']]={}
 emitted=next(q for q in f['segments'] if q['name']==seg['name'])
 assert seg['recognition']['mode']=='modeled_as_recognized'
 assert seg['recognition']['timing']==seg['recognition']['presentation']==seg['recognition']['modeled_presentation']=='mixed'
 assert not any(q in seg['recognition'] for q in ['progress_parameter_ids','carry_in_parameter_ids','lag_years'])
 for sc in totals:
  rv=float(base);path={}
  for y,pid in zip(years,seg['scenarios'][sc]['driver_parameter_ids']['growth_rate']):
   prior=rv;rv*=1+pi[pid]['value'];path[y]=rv;totals[sc][y]+=rv
   assert close(emitted['scenarios'][sc]['recognized_revenue'][y],rv)
   assert close(emitted['scenarios'][sc]['effective_revenue'][y],rv)
  curves[seg['name']][sc]=path;paths.append(dict(segment=seg['name'],scenario=sc,base=base,path=path))
  cagr=(rv/base)**(1/3)-1
  for key in ['cagr','incremental_revenue']:
   if key in emitted['scenarios'][sc]:assert close(emitted['scenarios'][sc][key],cagr if key=='cagr' else rv-base)
 for y in years:assert curves[seg['name']]['low'][y]<=curves[seg['name']]['base'][y]<=curves[seg['name']]['high'][y]
base=pi[i['reported_total_revenue_parameter_id']]['value'];assert sum(pi[s['base_revenue_parameter_id']]['value'] for s in i['segments'])==base==751766
assert not i['base_adjustment_parameter_ids']
companies=[]
for sc,t in totals.items():
 prior=base
 for y,val in t.items():
  assert close(f['consolidated_forecast'][sc]['annual_revenue'][y],val)
  companies.append(dict(scenario=sc,year=int(y),revenue=val,growth=val/prior-1,bridge_adjustment=0));prior=val
 assert close(f['consolidated_forecast'][sc]['cagr'],(t['2028']/base)**(1/3)-1)
 assert close(f['consolidated_forecast'][sc]['incremental_revenue'],t['2028']-base)
sens=[]
for q in f['sensitivities']:
 p=pi[q['parameter_id']];seg=next(s for s in i['segments'] if q['parameter_id'] in s['scenarios']['base']['driver_parameter_ids']['growth_rate'])
 terminal=totals['base']['2028'];base_seg=curves[seg['name']]['base']['2028'];calcs={}
 for direction,sign in [('down',-1),('up',1)]:
  val=p['value']+sign*q['shock_value'];assert close(q['requested_values'][direction],val)
  assert close(q['effective_values'][direction],val);assert q['clamped'][direction]==False
  rv=pi[seg['base_revenue_parameter_id']]['value']
  for pid in seg['scenarios']['base']['driver_parameter_ids']['growth_rate']:rv*=1+(val if pid==q['parameter_id'] else pi[pid]['value'])
  calcs[direction]=terminal-base_seg+rv;assert close(q[direction+'_terminal_revenue'],calcs[direction])
 impact=max(abs(v-terminal) for v in calcs.values());assert close(q['max_absolute_terminal_impact'],impact);assert close(q['max_relative_terminal_impact'],impact/terminal)
 sens.append(dict(parameter_id=q['parameter_id'],baseline=terminal,**calcs,max_absolute_impact=impact))
assert len(sens)==15 and len(set(q['parameter_id'] for q in sens))==15
alloc=[]
for d in i['growth_driver_tree']['drivers']:
 increment=sum((curves[w['segment_name']]['base']['2028']-pi[next(s for s in i['segments'] if s['name']==w['segment_name'])['base_revenue_parameter_id']]['value'])*w['weight'] for w in d['segment_attribution'])
 alloc.append(dict(driver_id=d['driver_id'],increment=increment))
assert close(sum(q['increment'] for q in alloc),totals['base']['2028']-base)
h1_2026=[130115,64409,81736,120171,4812];h1_2025=[118654,64847,67615,110443,2967]
residual=[]
for k,seg in enumerate(i['segments']):
 prior=pi[seg['base_revenue_parameter_id']]['value']-h1_2025[k]
 for sc in totals:
  h2=curves[seg['name']][sc]['2026']-h1_2026[k];assert h2>=0
  residual.append(dict(segment=seg['name'],scenario=sc,H1_2025=h1_2025[k],H1_2026=h1_2026[k],H2_2025=prior,implied_H2_2026=h2,implied_H2_growth=h2/prior-1))
report=dict(timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),original_input_sha=sha(OUT/'input.json'),original_forecast_sha=sha(OUT/'forecast.json'),replay_root=str(REPLAY),strong_input_required_validation='PASS',snapshot_validation='PASS',same_result_markdown='PASS',independent_cli=dict(command=cmd,started_at=started,returncode=r.returncode,deterministic_payload_equality=True),manual_arithmetic=dict(all45_segment_year_scenario_values=True,company_values=companies,paths=paths,sensitivities=sens,driver_allocation=sorted(alloc,key=lambda q:-q['increment']),H1_H2_period_bridge=residual),registry_original_sha=sha(OUT/'publications.jsonl'),originals_unmodified=True)
(HERE/'recheck_v3_independent_calculations.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(strong_validation='PASS',snapshot='PASS',markdown='PASS',deterministic_replay='PASS',all45_segment_year_scenario_values='PASS',all15_sensitivities='PASS',driver_allocation='PASS',replay_root=str(REPLAY),consolidated=totals),ensure_ascii=False))
