from pathlib import Path
import hashlib,json,os,stat,subprocess,sys,time
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
ROOT=Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
OUT=Path(__file__).resolve().parent
SCRATCH=OUT/'owned-scratch'
assert not SCRATCH.exists(), 'must preserve preexisting scratch'
SCRATCH.mkdir()
env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','TEMP','TMP','COMSPEC','PATHEXT','USERPROFILE'}}
env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',REVENUE_PUBLICATION_REGISTRY=str(SCRATCH/'registry.jsonl'),FF_V2_CODE_ROOT='C:/Users/郑曾波/Projects/filing-fetch',CWP_V2_CODE_ROOT='C:/Users/郑曾波/Projects/company-wiki')
rows=[];comparisons=[];passed=True
network_wrapper="import socket,runpy,sys; sys.dont_write_bytecode=True;\ndef deny(*a,**k): raise RuntimeError('network forbidden by offline final replay')\nsocket.socket.connect=deny; socket.create_connection=deny; socket.getaddrinfo=deny; sys.path.insert(0,sys.argv[1]); sys.argv=sys.argv[2:]; runpy.run_path(sys.argv[0],run_name='__main__')"
def run(label,args,network_block=False):
    global passed
    command=[sys.executable,'-B',*args] if not network_block else [sys.executable,'-B','-c',network_wrapper,str(ROOT/'scripts'),*args]
    start=time.monotonic()
    r=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=120)
    rows.append({'label':label,'command':command,'exit_code':r.returncode,'seconds':round(time.monotonic()-start,3),'network_denied':network_block})
    with (OUT/'final-node.log').open('a',encoding='utf-8') as f:f.write(label+'\n'+r.stdout+r.stderr+'\n')
    print(label+': '+str(r.returncode))
    passed=passed and r.returncode==0
    return r.returncode==0
assert not (OUT/'final-node.log').exists(), 'do not overwrite gate evidence'
try:
    if run('existing single daily gate',['tools/pre_push_gate.py']):
        frozen=ROOT/'docs/handoffs/w05-rf-flow/e2e/frozen'
        for name in ('case1_acquisition','case2_offset_fy'):
            assert run(name+' native CLI',['scripts/revenue_forecast.py',str(frozen/(name+'.input.json')),'--output',str(SCRATCH/(name+'.forecast.json')),'--markdown',str(SCRATCH/(name+'.forecast.md'))],True)
            for suffix in ('forecast.json','forecast.md'):
                b=(SCRATCH/(name+'.'+suffix)).read_bytes();old=(frozen/(name+'.'+suffix)).read_bytes()
                comparisons.append({'path':name+'.'+suffix,'full_bytes_identical':b==old,'sha256':hashlib.sha256(b).hexdigest()})
            assert run(name+' strong readers and date tamper',['docs/handoffs/w05-rf-flow/e2e/read_and_tamper.py',str(SCRATCH/(name+'.forecast.json')),'window'],True)
        assert run('C1 currency tamper',['docs/handoffs/w05-rf-flow/e2e/read_and_tamper.py',str(SCRATCH/'case1_acquisition.forecast.json'),'currency'],True)
        assert run('C1 snapshot',['scripts/revenue_backtest.py','create',str(frozen/'case1_acquisition.input.json'),'--version','w05-root-cny-v1','--output',str(SCRATCH/'case1_acquisition.snapshot.json')],True)
        body=(SCRATCH/'case1_acquisition.snapshot.json').read_bytes();old=(frozen/'case1_acquisition.snapshot.json').read_bytes()
        comparisons.append({'path':'case1_acquisition.snapshot.json','full_bytes_identical':body==old,'sha256':hashlib.sha256(body).hexdigest()})
        passed=passed and all(x['full_bytes_identical'] for x in comparisons)
finally:
    inventory=[{'path':x.relative_to(SCRATCH).as_posix(),'bytes':x.stat().st_size} for x in SCRATCH.rglob('*') if x.is_file()]
    assert SCRATCH.resolve().parent==OUT.resolve() and SCRATCH.name=='owned-scratch'
    for x in sorted(SCRATCH.rglob('*'),key=lambda x:len(x.parts),reverse=True):
        if x.is_file(): x.chmod(stat.S_IREAD|stat.S_IWRITE); x.unlink()
        else:x.rmdir()
    SCRATCH.rmdir()
    payload={'status':'PASS' if passed else 'FAIL','commands':rows,'frozen_comparisons':comparisons,'scratch_initial_exists':False,'files_before_cleanup':inventory,'scratch_final_exists':SCRATCH.exists(),'scratch_restored':not SCRATCH.exists(),'provider_calls':0,'llm_calls':0,'fees_usd':0}
    (OUT/'final-node.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':payload['status'],'byte_equal':len(comparisons),'scratch_restored':not SCRATCH.exists()},ensure_ascii=False))
if not passed: raise SystemExit(1)
