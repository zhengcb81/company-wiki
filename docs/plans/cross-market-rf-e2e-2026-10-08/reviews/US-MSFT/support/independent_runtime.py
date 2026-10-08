import sys,os,json,hashlib,subprocess,math,copy
from pathlib import Path

HERE=Path(__file__).resolve().parent
EX=HERE.parents[2]/'executions'/'US-MSFT'
ORIG=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/US-MSFT')
ROOT=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-review-20261008-US-MSFT-independent')
RF=Path('C:/Users/郑曾波/.agents/skills/revenue-forecast')
REPO=Path('C:/Users/郑曾波/Projects/revenue-forecast')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,d):
    p=HERE/n;p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def run(cmd):
    p=subprocess.run(cmd,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',REVENUE_PUBLICATION_REGISTRY=str(ROOT/'publications.jsonl')),capture_output=True,timeout=90,cwd=RF)
    print(json.dumps(dict(cmd=cmd,returncode=p.returncode,stdout=p.stdout.decode('utf-8'),stderr=p.stderr.decode('utf-8')),ensure_ascii=False))
    if p.returncode:raise RuntimeError('independent command failed')

ROOT.mkdir(parents=True,exist_ok=True)
before={f:sha(ORIG/f) for f in ['input.json','forecast.json','forecast.md','snapshot.json']}
inp=read(ORIG/'input.json');forecast=read(ORIG/'forecast.json')
sys.path.insert(0,str(RF/'scripts'))
from revenue_report import validate_published_forecast,render_markdown
from revenue_backtest import validate_snapshot
validate_published_forecast(forecast,inp)
validate_snapshot(read(ORIG/'snapshot.json'))
assert render_markdown(forecast)==(ORIG/'forecast.md').read_text(encoding='utf-8')
(ROOT/'input.json').write_bytes((ORIG/'input.json').read_bytes())
run([sys.executable,'-B',str(RF/'scripts/revenue_forecast.py'),str(ROOT/'input.json'),'--validate-only','--verbose'])
run([sys.executable,'-B',str(RF/'scripts/revenue_forecast.py'),str(ROOT/'input.json'),'--output',str(ROOT/'forecast.json'),'--markdown',str(ROOT/'forecast.md')])
if not (ROOT/'snapshot.json').exists():
    run([sys.executable,'-B',str(RF/'scripts/revenue_backtest.py'),'create',str(ROOT/'input.json'),'--version',inp['forecast_version'],'--output',str(ROOT/'snapshot.json')])
fresh=read(ROOT/'forecast.json');validate_published_forecast(fresh,inp);validate_snapshot(read(ROOT/'snapshot.json'))
exclude={'publication_receipt','result_sha256','workflow_compliance_receipt'}
equal={k:forecast[k]==fresh[k] for k in forecast if k not in exclude}
assert all(equal.values()),[k for k,v in equal.items() if not v]
runtime={}
for rel in read(EX/'manifest.json')['runtime_file_sha256']:
    runtime[rel]=dict(installed_sha256=sha(RF/rel),repo_sha256=sha(REPO/rel),matches_manifest=sha(RF/rel)==read(EX/'manifest.json')['runtime_file_sha256'][rel]['installed_sha256'])
    assert runtime[rel]['matches_manifest'] and runtime[rel]['installed_sha256']==runtime[rel]['repo_sha256']
params={p['parameter_id']:p for p in inp['parameters']}
calc={'history':inp['historical_revenue'],'segments':{},'company':{},'ordering':[], 'sensitivity':[], 'growth_driver_analysis':forecast['growth_driver_analysis'],'confidence':forecast['confidence']}
print('OUTPUT SEGMENT SHAPE',json.dumps(forecast['segments'][0],ensure_ascii=False))
print('ATTRIBUTION SHAPE',json.dumps(forecast['growth_driver_analysis'],ensure_ascii=False))
print('SENSITIVITY SHAPE',json.dumps(forecast['sensitivities'],ensure_ascii=False))
base=sum(params[s['base_revenue_parameter_id']]['value'] for s in inp['segments'])+sum(params[p]['value'] for p in inp['base_adjustment_parameter_ids'])
assert base==params[inp['reported_total_revenue_parameter_id']]['value']==331839
for sc in ['low','base','high']:
    totals={str(y):0. for y in inp['forecast_years']}
    groups={g:{str(y):0. for y in inp['forecast_years']} for g in ['Agents and Infra','Devices and Consumer']}
    for seg in inp['segments']:
        b=params[seg['base_revenue_parameter_id']]['value'];v=b;annual={}
        for y,pid in zip(inp['forecast_years'],seg['scenarios'][sc]['driver_parameter_ids']['growth_rate']):
            v=v*(1+params[pid]['value']);annual[str(y)]=v;totals[str(y)]+=v;groups[seg['reporting_group']][str(y)]+=v
        observed=next(x for x in forecast['segments'] if x['name']==seg['name'])
        for field in ['modeled_activity','recognized_revenue','effective_revenue']:
            obs=observed['scenarios'][sc][field]
            assert all(math.isclose(v,obs[y],abs_tol=1e-7) for y,v in annual.items())
        calc['segments'][seg['name']+'|'+sc]={'annual_revenue':annual,'increment':v-b,'cagr':(v/b)**(1/3)-1}
    observed=forecast['consolidated_forecast'][sc]
    assert all(math.isclose(v,observed['annual_revenue'][y],abs_tol=1e-7) for y,v in totals.items())
    cagr=(totals['2029']/base)**(1/3)-1
    assert math.isclose(cagr,observed['cagr'],abs_tol=1e-12)
    calc['company'][sc]={'annual_revenue':totals,'reporting_groups':groups,'cagr':cagr,'increment':totals['2029']-base}
for name in [s['name'] for s in inp['segments']]+['company']:
    for y in inp['forecast_years']:
        vals=[calc['company'][s]['annual_revenue'][str(y)] if name=='company' else calc['segments'][name+'|'+s]['annual_revenue'][str(y)] for s in ['low','base','high']]
        assert vals==sorted(vals);calc['ordering'].append(dict(segment=name,year=y,values=vals,status='PASS'))
driver_values={}
weight_by_seg={s['name']:0. for s in inp['segments']}
for driver in forecast['growth_driver_analysis']['drivers']:
    total=0.
    for att in driver['segment_attribution']:
        name=att['segment_name'];weight=att['weight'];weight_by_seg[name]+=weight
        allocation=calc['segments'][name+'|base']['increment']*weight
        obs=next(x for x in driver['terminal_increment_by_segment'] if x['segment_name']==name)
        assert math.isclose(allocation,obs['terminal_incremental_revenue'],abs_tol=1e-7)
        total+=allocation
    assert math.isclose(total,driver['estimated_base_terminal_increment'],abs_tol=1e-7)
    driver_values[driver['driver_id']]=total
assert all(x==1. for x in weight_by_seg.values())
assert math.isclose(sum(driver_values.values()),calc['company']['base']['increment'],abs_tol=1e-7)
assert [d['driver_id'] for d in forecast['growth_driver_analysis']['top_drivers']]==[k for k,v in sorted(driver_values.items(),key=lambda x:x[1],reverse=True) if v>0]
calc['independent_driver_allocations']=driver_values
for shock in forecast['sensitivities']:
    pid=shock['parameter_id'];seg=next(s for s in inp['segments'] if pid in s['scenarios']['base']['driver_parameter_ids']['growth_rate'])
    b=params[seg['base_revenue_parameter_id']]['value'];rest=[params[p]['value'] for p in seg['scenarios']['base']['driver_parameter_ids']['growth_rate'][1:]]
    calcrow=dict(name=shock['name'],parameter_id=pid,stored_shock=shock['shock_value'],named_shock_ratio=0.05,semantic_status='FAIL')
    for direction,sign in [('down',-1),('up',1)]:
        req=params[pid]['value']+sign*shock['shock_value'];eff=max(-1.,req)
        changed=b*(1+eff)*math.prod(1+x for x in rest)
        result=calc['company']['base']['annual_revenue']['2029']-calc['segments'][seg['name']+'|base']['annual_revenue']['2029']+changed
        assert math.isclose(req,shock['requested_values'][direction],abs_tol=1e-12)
        assert math.isclose(result,shock[direction+'_terminal_revenue'],abs_tol=1e-7)
        intended=b*(1+params[pid]['value']+sign*.05)*math.prod(1+x for x in rest)
        calcrow[direction+'_actual']=result
        calcrow[direction+'_intended_5pp']=calc['company']['base']['annual_revenue']['2029']-calc['segments'][seg['name']+'|base']['annual_revenue']['2029']+intended
    calc['sensitivity'].append(calcrow)
after={f:sha(ORIG/f) for f in before};assert before==after
write('runtime_recompute.json',{'strong_original':'PASS','snapshot_original':'PASS','renderer_original':'PASS','independent_cli':'PASS','deterministic_fields':equal,'runtime':runtime,'owned_temp':str(ROOT),'original_hash_before':before,'original_hash_after':after})
write('independent_calculations.json',calc)
print('SUCCESS independent runtime and arithmetic')
