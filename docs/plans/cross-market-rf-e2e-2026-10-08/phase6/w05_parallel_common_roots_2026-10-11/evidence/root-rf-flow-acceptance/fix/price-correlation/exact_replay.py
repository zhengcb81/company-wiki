from pathlib import Path
import copy, hashlib, json, os, socket, subprocess, sys, tempfile, time
sys.dont_write_bytecode=True
ROOT=Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
OUT=Path(__file__).resolve().parent
ORIGINAL=OUT.parent.parent/'independent-typed-final'
network=[]
def deny(*a,**k):
    network.append('denied')
    raise AssertionError('No network authorized for offline acceptance')
socket.socket.connect=deny
socket.create_connection=deny
socket.getaddrinfo=deny
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from revenue_core import ForecastInputError,run_forecast,validate_document
from revenue_report import validate_forecast_output,validate_published_forecast
mode=sys.argv[1]
result=[]
with tempfile.TemporaryDirectory(prefix='rf-price-exact-') as scratch:
    os.environ['REVENUE_PUBLICATION_REGISTRY']=str(Path(scratch)/'registry.jsonl')
    os.environ.pop('REVENUE_ATTESTATION_PROVIDER',None)
    for name in ('same_price_cancels_inline','same_price_cancels_derived','distinct_equal_prices_cancel'):
        inp=ORIGINAL/(name+'.unexpected-accepted-input.json')
        op=ORIGINAL/(name+'.unexpected-accepted-output.json')
        data=json.loads(inp.read_text(encoding='utf-8'))
        old=json.loads(op.read_text(encoding='utf-8'))
        entries=[]
        operations=[('validate_document',lambda:validate_document(copy.deepcopy(data))),
                    ('run_forecast',lambda:run_forecast(copy.deepcopy(data))),
                    ('validate_forecast_output',lambda:validate_forecast_output(copy.deepcopy(old))),
                    ('validate_published_forecast',lambda:validate_published_forecast(copy.deepcopy(old),copy.deepcopy(data)))]
        for boundary,operation in operations:
            try:
                operation()
                entries.append({'boundary':boundary,'actual':'accept','expected':'reject','pass':False})
            except Exception as exc:
                entries.append({'boundary':boundary,'actual':'reject','expected':'reject','error_type':type(exc).__name__,
                    'error':str(exc),'pass':isinstance(exc,ForecastInputError) and 'typed flow' in str(exc)})
        result.append({'name':name,'unchanged_input_sha256':hashlib.sha256(inp.read_bytes()).hexdigest(),
            'unchanged_original_output_sha256':hashlib.sha256(op.read_bytes()).hexdigest(),'boundaries':entries})
    if mode=='red':
        command=[sys.executable,'-B','-m','pytest','-q','--tb=short','-p','no:cacheprovider',
            'tests/test_w05_root_temporal_lineage.py','-k','price_cancellation or annual_operating_flow',
            '--basetemp',str(Path(scratch)/'pytest')]
        env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONUTF8']='1'
        proc=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
        (OUT/'business-red.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
        result.append({'label':'portable business RED','command':command,'exit_code':proc.returncode})
payload={'mode':mode,'cases':result,'scratch_removed':not Path(scratch).exists(),'network_attempts':network,'provider_calls':0,'llm_calls':0,'fees_usd':0}
(OUT/('exact-'+mode+'.json')).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(payload,ensure_ascii=False))
if mode!='red' and not all(row['pass'] for case in result for row in case['boundaries']): raise SystemExit(1)
