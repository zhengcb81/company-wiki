import sys,json,pathlib,threading
from types import SimpleNamespace
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import argparse
p=argparse.ArgumentParser();p.add_argument('--ff-root',type=pathlib.Path,required=True);args=p.parse_args();base=args.ff_root;sys.path[:0]=[str(base/'tools/offline_contract_matrix'),str(base/'scripts')]
import w20_fault_cases as f
barrier=threading.Barrier(2);saved_in,saved_out=sys.stdin,sys.stdout
seen=[]
def child(*args,**kw):
 p=json.loads(kw['input']);barrier.wait(timeout=3)
 seen.append({'entity':p['identity_request']['entity'],'wiki':p['wiki'],'sha':p['content_sha']})
 return SimpleNamespace(returncode=0,stderr=b'',stdout=json.dumps({'state':'confirmed','ref':{'content_sha256':p['content_sha']},'error':None}).encode())
def work(name):
 return f.probe_catalog(wiki_root=pathlib.Path('unused-'+name),identity_request={'entity':name},content_sha=name*64,cwp_src='unused-code',env={})
with patch('subprocess.run',side_effect=child),ThreadPoolExecutor(max_workers=2) as pool:
 a=pool.submit(work,'a');b=pool.submit(work,'b');results={'a':a.result(),'b':b.result()}
with patch('subprocess.run',return_value=SimpleNamespace(returncode=7,stdout=b'',stderr=b'query failed')):
 err=work('e')
r={'scope':'pure per-call subprocess boundary concurrency probe, not actual CWP reader E2E','requests':seen,'results':results,'stdio_unchanged':sys.stdin is saved_in and sys.stdout is saved_out,'nonzero_child_result':err,'old_process_global_readback_removed':not hasattr(f,'cwp_public_readback'),'shared_last_error_removed':not hasattr(f,'_CWP_PROBE_LAST_ERROR')}

print(json.dumps(r,indent=2))
