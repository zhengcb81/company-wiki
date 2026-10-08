"""Strong input-required validator, same-source renderer, independent arithmetic."""
from pathlib import Path
import json, os, sys, math, hashlib, datetime as dt
HERE=Path(__file__).resolve().parent
OUT=Path(json.loads((HERE/'before.json').read_text(encoding='utf-8'))['output_root'])
os.environ['REVENUE_PUBLICATION_REGISTRY']=str(OUT/'publications.jsonl')
SKILL=Path.home()/'.agents/skills/revenue-forecast';sys.path.insert(0,str(SKILL/'scripts'))
from revenue_report import validate_published_forecast, render_markdown
from revenue_backtest import validate_snapshot
def read(p):return json.loads(p.read_text(encoding='utf-8'))
i=read(OUT/'input.json');f=read(OUT/'forecast.json');s=read(OUT/('snapshot-v2.json' if (OUT/'snapshot-v2.json').exists() else 'snapshot.json'))
validate_published_forecast(f,i);validate_snapshot(s)
rendered=render_markdown(f);md=(OUT/'forecast.md').read_text(encoding='utf-8')
assert md==rendered,'Markdown is not exact same-result runtime render'
pi={p['parameter_id']:p for p in i['parameters']};fy=[str(x) for x in i['forecast_years']]
calc={sc:{y:0 for y in fy} for sc in ('low','base','high')};h1_26=[130115,64409,81736,120171,4812];h1_25=[118654,64847,67615,110443,2967];old=[197712,121456,121374,211956,7759]
h2=[];curves=[]
for n,seg in enumerate(i['segments']):
 base=pi[seg['base_revenue_parameter_id']]['value'];fseg=next(x for x in f['segments'] if x['name']==seg['name'])
 assert fseg['recognition']['timing']=='mixed' and fseg['recognition']['presentation']=='mixed'
 assert not any(k in fseg['recognition'] for k in ('progress_parameter_ids','lag_years','carry_in_parameter_ids'))
 for sc in ('low','base','high'):
  revenue=float(base);path=[]
  for y,pid in zip(fy,seg['scenarios'][sc]['driver_parameter_ids']['growth_rate']):
   revenue*=1+pi[pid]['value'];path.append(revenue);calc[sc][y]+=revenue
   assert math.isclose(fseg['scenarios'][sc]['recognized_revenue'][y],revenue,rel_tol=0,abs_tol=1e-6)
  assert path[0]>=h1_26[n],'Forecast below already reported H1'
  prev_h2=base-h1_25[n];new_h2=path[0]-h1_26[n]
  h2.append({'segment':seg['name'],'scenario':sc,'FY2025':base,'H1_2025':h1_25[n],'H2_2025':prev_h2,'H1_2026':h1_26[n],'FY2026_forecast':path[0],'implied_H2_2026':new_h2,'implied_H2_yoy':new_h2/prev_h2-1,'unit':'CNY million','check':'Non-negative residual; seasonal compare uses H2, not twice H1.'})
  curves.append({'segment':seg['name'],'scenario':sc,'independent_annual_revenue':dict(zip(fy,path))})
for sc in ('low','base','high'):
 conf=f['consolidated_forecast'][sc]
 for y,value in calc[sc].items():assert math.isclose(conf['annual_revenue'][y],value,rel_tol=0,abs_tol=1e-6)
 expected=(calc[sc]['2028']/751766)**(1/3)-1
 assert math.isclose(conf['cagr'],expected,rel_tol=0,abs_tol=1e-10)
 assert math.isclose(conf['incremental_revenue'],calc[sc]['2028']-751766,rel_tol=0,abs_tol=1e-6)
for y in fy:assert calc['low'][y]<=calc['base'][y]<=calc['high'][y]
checks={'timestamp_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'strong_input_required_validator':'PASS','snapshot_validator':'PASS','same_result_markdown':'PASS','independent_segment_consolidation_cagr':'PASS','recognized_revenue_transform':'mixed no second transformation','all_base_assumptions_sensitivity':len(f['sensitivities']),'independent_paths':curves,'consolidated':calc,'H1_implied_H2_checks':h2,'publication_registry_effective_path':os.environ['REVENUE_PUBLICATION_REGISTRY'],'signer':'No fabricated external signature; preserve actual engine receipts','future_actual_backtest':'NOT_APPLICABLE: full FY2026–2028 actuals unavailable as of 2026-10-08'}
(HERE/'delivery_verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'verification_path':str(HERE/'delivery_verification.json'),'strong_validation':'PASS','markdown':'PASS','arithmetic':'PASS','consolidated':calc,'sensitivities':len(f['sensitivities'])},ensure_ascii=False))
