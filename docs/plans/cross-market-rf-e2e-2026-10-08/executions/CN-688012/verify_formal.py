"""Execution checks; independent reviewer must still repeat every fact check."""
from pathlib import Path
import datetime, hashlib, json, math, os, sys
ROOT=Path(__file__).resolve().parent
OUT=Path(os.environ['TEMP'])/'cwp-rf-e2e-20261008'/'CN-688012'
SKILL=Path('C:/Users/郑曾波/.agents/skills/revenue-forecast')
sys.path.insert(0,str(SKILL/'scripts'))
from revenue_report import validate_published_forecast, render_markdown
from revenue_backtest import validate_snapshot
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def equal(a,b):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8),(a,b)
def sh(p):return hashlib.sha256(p.read_bytes()).hexdigest()
data=read(OUT/'input.json'); result=read(OUT/'forecast.json')
ctx=validate_published_forecast(result,data)
assert (OUT/'forecast.md').read_bytes()==render_markdown(result).encode('utf-8')
params={p['parameter_id']:p for p in data['parameters']}
segments={s['name']:s for s in result['segments']}
records=[]
for scenario in ['low','base','high']:
    previous=result['base_revenue']
    for y in [2026,2027,2028]:
        equipment=params[f'equipment_units_{scenario}_{y}']['value']*params[f'equipment_unit_revenue_{scenario}_{y}']['value']
        aftermarket=params[f'aftermarket_revenue_{scenario}_{y}']['value']
        cmp=params[f'cmp_revenue_{scenario}_{y}']['value']
        equal(equipment,segments['Equipment']['scenarios'][scenario]['recognized_revenue'][str(y)])
        equal(aftermarket,segments['Aftermarket']['scenarios'][scenario]['recognized_revenue'][str(y)])
        equal(cmp,segments['CMP']['scenarios'][scenario]['recognized_revenue'][str(y)])
        expected=equipment+aftermarket+cmp
        path=result['consolidated_forecast'][scenario]
        equal(expected,path['annual_revenue'][str(y)])
        equal(expected/previous-1,path['annual_growth'][str(y)])
        records.append(dict(scenario=scenario,year=y,independent_sum=expected,engine_total=path['annual_revenue'][str(y)],check='PASS'))
        previous=expected
    equal((previous/result['base_revenue'])**(1/3)-1,path['cagr'])
    equal(previous-result['base_revenue'],path['incremental_revenue'])
for y in [2026,2027,2028]:
    vals=[result['consolidated_forecast'][s]['annual_revenue'][str(y)] for s in ['low','base','high']]
    assert vals==sorted(vals)
for scenario in ['low','base','high']:
    assert result['consolidated_forecast'][scenario]['annual_revenue']['2026']>6691.28732767,'Full FY2026 must exceed already reported H1'
equal(params['equipment_base']['value']+params['aftermarket_base']['value']+params['cmp_base']['value'],result['base_revenue'])
assert params['cmp_base']['kind']=='analyst_assumption'
assert result['publication_receipt']['attestation_status']=='unattested'
registry=Path(os.environ['REVENUE_PUBLICATION_REGISTRY'])
assert registry==OUT/'publications.jsonl' and registry.exists()
snapshot_check='not_created_yet'
snapshot_path=OUT/('snapshot_v2.json' if (OUT/'snapshot_v2.json').exists() else 'snapshot.json')
if snapshot_path.exists():
    snapshot=read(snapshot_path);validate_snapshot(snapshot)
    assert snapshot['forecast_version']==result['forecast_version']
    # Documented create_snapshot freezes an explicit forecast_version. The
    # original CLI input omitted that optional field and the engine defaulted
    # to the same date-v1 value. Preserve both original and immutable snapshot;
    # compare their complete economic payload while validating each binding.
    expected_input=dict(data,forecast_version=result['forecast_version'])
    assert snapshot['input_document']==expected_input
    binding_fields={'input_sha256','input_document','workflow_compliance_receipt','publication_receipt','result_sha256'}
    assert set(snapshot['forecast_result'])==set(result)
    for key,value in result.items():
        if key not in binding_fields:assert snapshot['forecast_result'][key]==value,key
    snapshot_check='PASS: explicit-version frozen input and complete economic result match; both input bindings independently strong-validated'
receipt=dict(schema_version='1.0',timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS execution verification; not independent acceptance',strong_validator='validate_published_forecast(result, original_input)',markdown='byte-identical to render_markdown of the same JSON',arithmetic=records,snapshot=snapshot_check,publication_registry=str(registry),attestation_status='unattested',registry_entries=sum(1 for x in registry.read_text(encoding='utf-8').splitlines() if x.strip()),artifacts=[dict(path=str(OUT/n),sha256=sh(OUT/n)) for n in ['input.json','forecast.json','forecast.md']])
(ROOT/'formal_verification_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(receipt,ensure_ascii=False))
