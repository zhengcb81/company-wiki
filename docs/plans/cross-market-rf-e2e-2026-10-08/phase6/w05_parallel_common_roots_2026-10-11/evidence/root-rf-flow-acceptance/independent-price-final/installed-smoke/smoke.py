"""Small read-only smoke of two actually installed RF runtime closures."""
from __future__ import annotations
import hashlib, json, os, shutil, stat, subprocess, sys, time
from pathlib import Path

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
BASE=OUT.parents[1]
SCRATCH=OUT/'_owned_scratch'
if SCRATCH.exists() or (OUT/'results.json').exists():
    raise RuntimeError('Scratch must be absent; never overwrite review evidence')
plan=json.loads((BASE/'canonical-install-plan.json').read_text(encoding='utf-8'))
installation=json.loads((BASE/'installation.json').read_text(encoding='utf-8'))
old_metadata=json.loads((BASE/'canonical-install-unselected-before.json').read_text(encoding='utf-8'))
selected=set(plan['selected'])
assert len(selected)==17 and len(plan['targets'])==2
CANONICAL=Path(plan['canonical'])
fixture=CANONICAL/'docs/handoffs/w05-rf-flow/e2e/frozen/case1_acquisition.input.json'
negative=BASE/'independent-typed-final/same_price_cancels_inline.unexpected-accepted-input.json'
negative_output=BASE/'independent-typed-final/same_price_cancels_inline.unexpected-accepted-output.json'

def metadata(root):
    return {p.relative_to(root).as_posix():[p.stat().st_size,p.stat().st_mtime_ns]
            for p in root.rglob('*') if p.is_file() and p.relative_to(root).as_posix() not in selected
            and p.name!='.installation_manifest.json'}
def freeze():
    result=[]
    for target in plan['targets']:
        root=Path(target['target'])
        rows=[]
        for row in target['files']:
            body=(root/row['path']).read_bytes()
            canonical=(CANONICAL/row['path']).read_bytes()
            digest=hashlib.sha256(body).hexdigest()
            rows.append({'path':row['path'],'sha256':digest,'bytes':len(body),
                         'matches_install_plan':digest==row['source_sha256'],
                         'matches_canonical_bytes':body==canonical})
        result.append({'target':str(root),'selected':rows,'unselected_metadata':metadata(root)})
    return result
before=freeze()
assert all(len(t['selected'])==17 and all(r['matches_install_plan'] and r['matches_canonical_bytes'] for r in t['selected']) for t in before)

CHILD=r'''
import copy,hashlib,json,os,socket,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
root,fixture,negative,negative_output,scratch=map(Path,sys.argv[1:])
def deny(*a,**k): raise RuntimeError('Network forbidden by installed smoke')
socket.socket.connect=deny; socket.socket.connect_ex=deny
socket.create_connection=deny; socket.getaddrinfo=deny
sys.path.insert(0,str(root/'scripts'))
os.environ['REVENUE_PUBLICATION_REGISTRY']=str(scratch/'registry.jsonl')
from contracts import recognition
from revenue_core import ForecastInputError,run_forecast,validate_document
from revenue_report import validate_forecast_output,validate_published_forecast
assert Path(recognition.__file__).resolve().is_relative_to((root/'scripts').resolve())
assert callable(recognition.validate_recognition_metadata)
data=json.loads(fixture.read_text(encoding='utf-8'))
valid=validate_document(copy.deepcopy(data))
forecast=run_forecast(copy.deepcopy(data))
validate_published_forecast(forecast,copy.deepcopy(data))
validate_forecast_output(copy.deepcopy(forecast))
frozen=json.loads((fixture.parent/'case1_acquisition.forecast.json').read_text(encoding='utf-8'))
assert forecast==frozen
bad=json.loads(negative.read_text(encoding='utf-8'))
old=json.loads(negative_output.read_text(encoding='utf-8'))
checks=[]
for name,fn in [('validate_document',lambda:validate_document(copy.deepcopy(bad))),
                ('run_forecast',lambda:run_forecast(copy.deepcopy(bad))),
                ('validate_published_forecast',lambda:validate_published_forecast(copy.deepcopy(old),copy.deepcopy(bad))),
                ('validate_forecast_output',lambda:validate_forecast_output(copy.deepcopy(old)))]:
    try: fn()
    except ForecastInputError as exc:
        assert 'typed flow' in str(exc),str(exc)
        checks.append({'boundary':name,'actual':'reject','error':str(exc)})
    else: raise AssertionError(name+' accepted the original stock-price P1')
print(json.dumps({'status':'PASS','target':str(root),'recognition_import':str(recognition.__file__),
                  'native_prediction_equals_frozen':True,'positive_strong_readers':'PASS',
                  'negative_case':'exact_original_same_price_cancels_inline','negative_boundaries':checks,
                  'provider_calls':0,'llm_calls':0,'fees_usd':0},ensure_ascii=False))
'''

SCRATCH.mkdir()
commands=[];status='FAIL';start=time.monotonic()
env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','TEMP','TMP','COMSPEC','PATHEXT','USERPROFILE'}}
env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONNOUSERSITE='1')
try:
    for index,target in enumerate(plan['targets']):
        child=SCRATCH/str(index)
        child.mkdir()
        p=subprocess.run([sys.executable,'-X','utf8','-B','-c',CHILD,target['target'],str(fixture),str(negative),str(negative_output),str(child)],
                         cwd=child,env=env,capture_output=True,text=True,encoding='utf-8',timeout=20)
        (OUT/('target-'+str(index)+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8')
        row={'target':target['target'],'exit_code':p.returncode}
        if p.returncode==0:row['observed']=json.loads(p.stdout)
        else:row['error']=p.stderr[-5000:]
        commands.append(row)
        assert p.returncode==0,str(row)
    status='PASS_WITH_SCOPE'
finally:
    after=freeze()
    assert SCRATCH.resolve().parent==OUT.resolve() and SCRATCH.name=='_owned_scratch'
    owned_files=[{'path':p.relative_to(SCRATCH).as_posix(),'bytes':p.stat().st_size} for p in SCRATCH.rglob('*') if p.is_file()]
    for p in SCRATCH.rglob('*'):
        if p.is_file():p.chmod(stat.S_IREAD|stat.S_IWRITE)
    shutil.rmtree(SCRATCH)
    metadata_checks=[]
    for a,b in zip(before,after):
        old=old_metadata[a['target']]
        metadata_checks.append({'target':a['target'],'unselected_count':len(a['unselected_metadata']),
                                'all_unselected_unchanged_this_smoke':a['unselected_metadata']==b['unselected_metadata'],
                                'matches_installation_before_receipt':a['unselected_metadata']==old,
                                'preexisting_cache_files':sum('__pycache__/' in p for p in a['unselected_metadata']),
                                'new_cache_files':sorted(p for p in b['unselected_metadata'] if '__pycache__/' in p and p not in a['unselected_metadata'])})
    result={'schema':'w05-installed-runtime-smoke/1','status':status,'canonical_head':installation['canonical_head'],
            'before':before,'after':after,'selected_hashes_unchanged':all(a['selected']==b['selected'] for a,b in zip(before,after)),
            'metadata_checks':metadata_checks,'runtime_smokes':commands,'scratch_initial_exists':False,
            'scratch_final_exists':SCRATCH.exists(),'owned_files_cleaned':owned_files,'seconds':round(time.monotonic()-start,3),
            'provider_calls':0,'llm_calls':0,'fees_usd':0,'raw_writes':0,'installed_writes':0}
    (OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'two_targets':len(commands),'selected_hashes_unchanged':result['selected_hashes_unchanged'],
                      'metadata_checks':metadata_checks,'scratch_absent':not SCRATCH.exists()},ensure_ascii=False))
