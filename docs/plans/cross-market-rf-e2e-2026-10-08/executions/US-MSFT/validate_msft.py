from lane_tools import OUTPUT,LANE,RF,write,event
import sys,json,math,hashlib
sys.path.insert(0,str(RF/'scripts'))
from revenue_report import validate_published_forecast,render_markdown
from revenue_backtest import validate_snapshot
data=json.loads((OUTPUT/'input.json').read_text())
result=json.loads((OUTPUT/'forecast.json').read_text())
validate_published_forecast(result,data)
assert (OUTPUT/'forecast.md').read_text(encoding='utf-8')==render_markdown(result)
independent={}; groups=json.loads((OUTPUT/'reporting_groups.json').read_text())
params={p['parameter_id']:p for p in data['parameters']}
for scenario in ['low','base','high']:
    years={str(y):0.0 for y in data['forecast_years']};group_years={g:{str(y):0.0 for y in data['forecast_years']} for g in groups['groups']}
    for seg in data['segments']:
        prev=params[seg['base_revenue_parameter_id']]['value']
        growth=seg['scenarios'][scenario]['driver_parameter_ids']['growth_rate']
        for year,pid in zip(data['forecast_years'],growth):
            prev*=1+params[pid]['value'];years[str(year)]+=prev
            group=next(g for g,names in groups['groups'].items() if seg['name'] in names);group_years[group][str(year)]+=prev
    observed=result['consolidated_forecast'][scenario]['annual_revenue']
    assert all(math.isclose(years[y],observed[y],rel_tol=1e-10) for y in years)
    independent[scenario]=dict(annual_revenue=years,reporting_groups=group_years,cagr=(years['2029']/331839)**(1/3)-1)
    assert math.isclose(independent[scenario]['cagr'],result['consolidated_forecast'][scenario]['cagr'],rel_tol=1e-10)
snapshot_state='not_created_yet'
if (OUTPUT/'snapshot.json').exists():
    snapshot=json.loads((OUTPUT/'snapshot.json').read_text());validate_snapshot(snapshot);assert snapshot['input_document']==data;snapshot_state='validated'
write(LANE/'formal_validation.json',dict(strong_input_required_validation='PASS',markdown_same_json='PASS',independent_arithmetic='PASS',snapshot=snapshot_state,input_sha256=hashlib.sha256((OUTPUT/'input.json').read_bytes()).hexdigest(),forecast_sha256=hashlib.sha256((OUTPUT/'forecast.json').read_bytes()).hexdigest(),guarantee='Technical conformance/recomputation only; unsigned provenance and economic assumptions need independent review.'))
write(OUTPUT/'independent_arithmetic_and_groups.json',independent)
event('10','strong input-required formal validation, same-JSON renderer, independent arithmetic',outcome='PASS',artifacts=[str(LANE/'formal_validation.json'),str(OUTPUT/'independent_arithmetic_and_groups.json')])
print(json.dumps(dict(strong_validation='PASS',markdown='PASS',arithmetic='PASS',snapshot=snapshot_state)))
