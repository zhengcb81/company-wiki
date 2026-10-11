"""Independent synthetic typed/temporal final review, no product writes."""
from __future__ import annotations
import copy, hashlib, json, os, shutil, socket, stat, subprocess, sys, time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
OUT = Path(__file__).resolve().parent
BASE = OUT.parent
SCRATCH = OUT / '_owned_scratch'
if SCRATCH.exists():
    raise RuntimeError('Independent scratch was not initially absent')
inventory = json.loads((BASE/'fix/root-product-inventory.json').read_text(encoding='utf-8'))
def frozen():
    return [{'path': row['path'], 'bytes': len(body := (ROOT/row['path']).read_bytes()),
             'sha256': hashlib.sha256(body).hexdigest(),
             'matches': len(body) == row['bytes'] and hashlib.sha256(body).hexdigest() == row['sha256']}
            for row in inventory['files']]
before = frozen()
assert len(before) == 30 and all(row['matches'] for row in before)
original = BASE/'independent-final/original-point-stock-annual-fail.json'
original_sha = hashlib.sha256(original.read_bytes()).hexdigest()
old = json.loads(original.read_text(encoding='utf-8'))
SCRATCH.mkdir()
os.environ['REVENUE_PUBLICATION_REGISTRY'] = str(SCRATCH/'registry.jsonl')
os.environ.pop('REVENUE_ATTESTATION_PROVIDER', None)
network_attempts = []
def deny_network(*args, **kwargs):
    network_attempts.append('blocked')
    raise AssertionError('Independent test forbids network')
socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.create_connection = deny_network
socket.getaddrinfo = deny_network
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'tests')]
from revenue_core import ForecastInputError, canonical_sha256, run_forecast, validate_document
from revenue_report import validate_forecast_output, validate_published_forecast
from test_data_contract import apply_parameter_contract
from test_industry_end_to_end import model_document

def param(data, name):
    return next(p for p in data['parameters'] if p['parameter_id'] == name)
def fresh():
    return copy.deepcopy(old['cases'][0]['input'])
def add(data, name, value, dim, basis='annual', formula=None, inputs=None):
    item = {'parameter_id': name, 'kind': 'analyst_assumption', 'value': value,
            'unit': {'ratio':'ratio','quantity':'units','revenue_per_unit':'USD million per unit'}.get(dim,'USD million'),
            'period':'FY2026', 'definition': 'Independent synthetic ' + name, 'scenario':None,
            'rationale':'Synthetic mathematical probe only', 'source_ids':[]}
    apply_parameter_contract(data,item,dim)
    item['time_basis'] = basis
    if formula is not None:
        item.update(kind='derived_fact',formula=formula,input_parameter_ids=inputs)
    data['parameters'].append(item)
    return item
def bind(data, formula, inputs, value):
    for s in ('low','base','high'):
        p = param(data,'cmp_fy2026_'+s)
        p.update(time_basis='annual',formula=formula,input_parameter_ids=inputs,value=value,
                 definition='Synthetic annual contribution',rationale='Independent typed proof')
        p.pop('period_start',None); p.pop('period_end',None)
    return data
def formula_case(kind):
    d = fresh()
    add(d,'stock',20.0,'monetary_balance','point_in_time')
    add(d,'flow',10.0,'revenue')
    add(d,'count',10.0,'quantity','point_in_time')
    add(d,'annual_price',2.0,'revenue_per_unit')
    add(d,'scalar',2.0,'ratio')
    if kind == 'rate_only': return bind(d,'100*x0',['scalar'],200.0)
    if kind == 'quantity_only': return bind(d,'x0',['count'],10.0)
    if kind == 'stock_plus_flow': return bind(d,'x0+x1',['stock','flow'],30.0)
    if kind == 'nested_stock':
        add(d,'alias',20.0,'monetary_balance','annual','x0',['stock'])
        return bind(d,'x0',['alias'],20.0)
    if kind == 'flow_cancelled_to_stock':
        add(d,'duration',2.0,'ratio','annual','x0/x1',['stock','flow'])
        return bind(d,'x0*x1',['flow','duration'],20.0)
    if kind == 'stock_price_alias':
        add(d,'price_alias',2.0,'revenue_per_unit','annual','x0/x1',['stock','count'])
        return bind(d,'x0*x1',['count','price_alias'],20.0)
    if kind == 'zero_weight_price': return bind(d,'x0+0*x1*x2',['stock','count','annual_price'],20.0)
    if kind == 'same_price_cancels_inline': return bind(d,'x0*(x1/x1)',['stock','annual_price'],20.0)
    if kind == 'same_price_cancels_derived':
        add(d,'price_ratio',1.0,'ratio','annual','x0/x0',['annual_price'])
        return bind(d,'x0*x1',['stock','price_ratio'],20.0)
    if kind == 'distinct_equal_prices_cancel':
        add(d,'annual_price_2',2.0,'revenue_per_unit')
        add(d,'price_ratio',1.0,'ratio','annual','x0/x1',['annual_price','annual_price_2'])
        return bind(d,'x0*x1',['stock','price_ratio'],20.0)
    if kind == 'arpu': return bind(d,'x0*x1',['count','annual_price'],20.0)
    if kind == 'derived_arpu':
        add(d,'derived_price',1.0,'revenue_per_unit','annual','x0/x1',['flow','count'])
        return bind(d,'x0*x1',['count','derived_price'],10.0)
    if kind == 'turnover':
        add(d,'annual_turnover',0.5,'ratio','annual','x0/x1',['flow','stock'])
        return bind(d,'x0*x1',['stock','annual_turnover'],10.0)
    raise ValueError(kind)

cases = [(row['case'],copy.deepcopy(row['input']),row['expected'],'unchanged_original') for row in old['cases']]
for name in ('rate_only','quantity_only','stock_plus_flow','nested_stock','flow_cancelled_to_stock','stock_price_alias',
             'zero_weight_price','same_price_cancels_inline','same_price_cancels_derived','distinct_equal_prices_cancel',
             'arpu','derived_arpu','turnover'):
    cases.append((name,formula_case(name),'accept' if name in ('arpu','derived_arpu','turnover') else 'reject','independent'))
results=[]; readers=[]; cli=[]
start=time.monotonic()
try:
    for name,data,expected,group in cases:
        boundaries=[]; forecast=None
        for boundary,operation in [('validate_document',lambda:validate_document(copy.deepcopy(data))),
                                   ('run_forecast',lambda:run_forecast(copy.deepcopy(data)))]:
            try:
                value=operation()
                if boundary == 'run_forecast': forecast=value
                boundaries.append({'boundary':boundary,'actual':'accept','pass':expected=='accept'})
            except Exception as exc:
                boundaries.append({'boundary':boundary,'actual':'reject','error_type':type(exc).__name__,
                    'error':str(exc),'pass':expected=='reject' and isinstance(exc,ForecastInputError) and 'publication failed' not in str(exc)})
        if forecast is not None:
            for boundary,operation in [('validate_published_forecast',lambda:validate_published_forecast(copy.deepcopy(forecast),copy.deepcopy(data))),
                                       ('validate_forecast_output',lambda:validate_forecast_output(copy.deepcopy(forecast)))]:
                try:
                    operation(); boundaries.append({'boundary':boundary,'actual':'accept','pass':expected=='accept'})
                except Exception as exc:
                    boundaries.append({'boundary':boundary,'actual':'reject','error_type':type(exc).__name__,'error':str(exc),
                                       'pass':expected=='reject' and isinstance(exc,ForecastInputError)})
        row={'name':name,'group':group,'expected':expected,'boundaries':boundaries,'pass':all(x['pass'] for x in boundaries),
             'input_sha256':canonical_sha256(data)}
        if forecast is not None: row['fy2026_low']=forecast['consolidated_forecast']['low']['annual_revenue']['2026']
        results.append(row)
        if expected == 'reject' and forecast is not None:
            (OUT/(name+'.unexpected-accepted-input.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            (OUT/(name+'.unexpected-accepted-output.json')).write_text(json.dumps(forecast,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    exact=copy.deepcopy(old['cases'][5]['input'])
    valid=copy.deepcopy(exact)
    param(valid,'closing_stock').update(dimension='revenue',time_basis='annual',definition='Synthetic actual income control')
    forged=run_forecast(valid)
    forged['input_document']=exact
    forged['parameter_trace']=copy.deepcopy(exact['parameters'])
    forged['input_sha256']=canonical_sha256(exact)
    forged['result_sha256']=canonical_sha256({k:v for k,v in forged.items() if k!='result_sha256'})
    for boundary,operation in [('validate_forecast_output',lambda:validate_forecast_output(copy.deepcopy(forged))),
                               ('validate_published_forecast',lambda:validate_published_forecast(copy.deepcopy(forged),copy.deepcopy(exact)))]:
        try: operation(); readers.append({'boundary':boundary,'pass':False,'actual':'accept'})
        except Exception as exc:
            readers.append({'boundary':boundary,'pass':isinstance(exc,ForecastInputError) and 'typed flow' in str(exc),
                            'actual':'reject','error':str(exc),'error_type':type(exc).__name__})
    for model,roles in [('subscription',{'average_customers'}),('asset_management',{'average_aum'}),
                        ('bank_revenue',{'average_earning_assets','average_interest_bearing_liabilities'})]:
        d=model_document(model)
        baseline=run_forecast(copy.deepcopy(d))
        d['schema_version']='3.10'
        for scenario in d['segments'][0]['scenarios'].values():
            for role in roles:
                for id in scenario['driver_parameter_ids'][role]: param(d,id)['time_basis']='point_in_time'
        f=run_forecast(d); validate_forecast_output(f); validate_published_forecast(f,d)
        results.append({'name':'native_'+model,'expected':'accept','pass':f['consolidated_forecast']==baseline['consolidated_forecast'],
                        'unchanged_consolidated_numbers':f['consolidated_forecast']==baseline['consolidated_forecast']})
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','TEMP','TMP','COMSPEC','PATHEXT','USERPROFILE'}}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',REVENUE_PUBLICATION_REGISTRY=str(SCRATCH/'cli-registry.jsonl'))
    frozen_input=ROOT/'docs/handoffs/w05-rf-flow/e2e/frozen/case1_acquisition.input.json'
    wrapper="import socket,runpy,sys; sys.dont_write_bytecode=True;\ndef deny(*a,**k): raise RuntimeError('network forbidden by independent review')\nsocket.socket.connect=deny; socket.create_connection=deny; socket.getaddrinfo=deny; sys.path.insert(0,sys.argv[1]); sys.argv=sys.argv[2:]; runpy.run_path(sys.argv[0],run_name='__main__')"
    command=[sys.executable,'-X','utf8','-B','-c',wrapper,str(ROOT/'scripts'),str(ROOT/'scripts/revenue_forecast.py'),
             str(frozen_input),'--output',str(SCRATCH/'cli.forecast.json'),'--markdown',str(SCRATCH/'cli.forecast.md')]
    p=subprocess.run(command,cwd=SCRATCH,env=env,capture_output=True,text=True,encoding='utf-8',timeout=30)
    (OUT/'native-cli.log').write_text(p.stdout+p.stderr,encoding='utf-8')
    cli.append({'exit_code':p.returncode,'network_denied':True,'synthetic_input':str(frozen_input)})
    if p.returncode==0:
        for suffix in ('forecast.json','forecast.md'):
            body=(SCRATCH/('cli.'+suffix)).read_bytes()
            target=(frozen_input.parent/('case1_acquisition.'+suffix)).read_bytes()
            cli.append({'artifact':suffix,'identical_frozen_bytes':body==target,'sha256':hashlib.sha256(body).hexdigest()})
        artifact=json.loads((SCRATCH/'cli.forecast.json').read_text(encoding='utf-8'))
        validate_forecast_output(artifact); validate_published_forecast(artifact,json.loads(frozen_input.read_text(encoding='utf-8')))
finally:
    assert SCRATCH.resolve().parent == OUT.resolve() and SCRATCH.name == '_owned_scratch'
    for path in SCRATCH.rglob('*'):
        if path.is_file(): path.chmod(stat.S_IREAD|stat.S_IWRITE)
    shutil.rmtree(SCRATCH)
    after=frozen()
    payload={'schema_version':'w05-independent-typed-final/1','before':before,'after':after,
             'frozen_unchanged':before==after,'original_fail_unchanged':hashlib.sha256(original.read_bytes()).hexdigest()==original_sha,
             'original_fail_sha256':original_sha,'cases':results,'exact_rehashed_strong_readers':readers,'native_cli':cli,
             'seconds':round(time.monotonic()-start,3),'scratch_initial_exists':False,'scratch_final_exists':SCRATCH.exists(),
             'provider_calls':0,'llm_calls':0,'network_attempts':network_attempts,'fees_usd':0,'raw_writes':0,'product_writes':0}
    (OUT/'results.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(results),'failed_expectations':[r['name'] for r in results if not r['pass']],
                      'readers':readers,'cli':cli,'freeze_unchanged':before==after,'scratch_absent':not SCRATCH.exists()},ensure_ascii=False))
