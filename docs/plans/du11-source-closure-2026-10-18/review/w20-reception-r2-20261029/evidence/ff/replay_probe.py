import json,pathlib,sys,threading,types
from unittest.mock import patch
from types import SimpleNamespace
from dataclasses import dataclass
import argparse
p=argparse.ArgumentParser();p.add_argument('--ff-root',type=pathlib.Path,required=True);args=p.parse_args();base=args.ff_root
sys.path[:0]=[str(base/'tools/offline_contract_matrix'),str(base/'scripts')]
import w20_fault_cases as f
from w20_case_specs import get_w20_spec
case=json.loads(pathlib.Path(__file__).with_name('retained-case.json').read_text('utf-8'))['case']
a_enter=threading.Event();b_enter=threading.Event();a_read=threading.Event();b_done=threading.Event();seen=[];errs=[]
def query_main(args):
 name=threading.current_thread().name
 if name=='probe-A':
  a_enter.set()
  if not b_enter.wait(5): raise RuntimeError('B did not enter')
  payload=json.loads(sys.stdin.read())
  seen.append({'thread':'A','expected_entity':'Company A','observed_entity':payload['source_request']['entity']})
  a_read.set()
  if not b_done.wait(5):raise RuntimeError('B did not finish')
 else:
  b_enter.set()
  if not a_read.wait(5): raise RuntimeError('A did not read')
 return 1
mods={}
for n in ['company_wiki','company_wiki.source_catalog','company_wiki.source_catalog.config','company_wiki.source_catalog.service','company_wiki.source_catalog.source_query_cli','company_wiki.source_catalog.source_reader']:
 mods[n]=types.ModuleType(n)
mods['company_wiki'].__path__=[];mods['company_wiki.source_catalog'].__path__=[]
mods['company_wiki.source_catalog.config'].load_catalog_config=lambda *a,**kw:None
mods['company_wiki.source_catalog.service'].SourceCatalog=lambda *a,**kw:None
mods['company_wiki.source_catalog.source_query_cli'].main=query_main
@dataclass
class DummyRef:content_sha256:str=''
mods['company_wiki.source_catalog.source_reader'].SourceRef=DummyRef
mods['company_wiki.source_catalog.source_reader'].SourceVersionReader=lambda *a,**kw:None
ctx=SimpleNamespace(env=SimpleNamespace(wiki=pathlib.Path('synthetic-unused-wiki')))
def worker(name):
 try:
  identity=SimpleNamespace(canonical_name='Company '+name,market='US',security_id=name)
  f.cwp_public_readback(ctx,identity=identity,fiscal_year=2036,fiscal_quarter=1,as_of_date='2026-12-31',content_sha='a'*64)
 except BaseException as e:errs.append(repr(e))
 finally:
  if name=='B':b_done.set()
original_in,original_out=sys.stdin,sys.stdout
try:
 with patch.dict(sys.modules,mods),patch.object(f,'_cwp_probe_modules',lambda:None):
  a=threading.Thread(target=worker,args=('A',),name='probe-A');b=threading.Thread(target=worker,args=('B',),name='probe-B')
  a.start();assert a_enter.wait(5);b.start();a.join(8);b.join(8)
  assert not a.is_alive() and not b.is_alive()
finally:sys.stdin,sys.stdout=original_in,original_out
result={'retained_actual_case':{'id':case['id'],'result':case['result'],'current_assertion_errors':get_w20_spec(case['id']).assertion_errors(case),'first_run_success_delivered':case['actual']['runs'][0]['response'].get('transcript',{}).get('status'),'second_run_immediate_kill':case['actual']['runs'][1].get('killed'),'second_run_provider_gets':case['actual']['runs'][1].get('et_fixture_requests')},'threaded_stdin_probe':seen,'probe_errors':errs,'scope':'pure boundary control-flow concurrency probe; no CWP data/code invoked; actual retained case only re-evaluated with current assertion, NOT a new live E2E'}
print(json.dumps(result,indent=2))
