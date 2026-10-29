import pathlib,json,sys,copy
from types import SimpleNamespace
from unittest.mock import patch
import argparse
p=argparse.ArgumentParser();p.add_argument('--ff-root',type=pathlib.Path,required=True);args=p.parse_args();base=args.ff_root;sys.path[:0]=[str(base/'tools/offline_contract_matrix'),str(base/'scripts')]
import w20_fault_cases as f
from w20_case_specs import get_w20_spec
data=json.loads(pathlib.Path(__file__).with_name('case-evidence.json').read_text('utf-8'))
old=next(c for x in data['reports'] for c in x['cases'] if c['id']=='w20_call_kill_after_import');cid=old['id'];spec=get_w20_spec(cid)
results=[]
for state in ('not_found','probe_error','confirmed'):
 ctx=SimpleNamespace(active_case_spec=spec,traces={cid:copy.deepcopy(old['actual']['runs'])},env=SimpleNamespace(wiki=pathlib.Path('unused-wiki')),cwp_root=pathlib.Path('unused-cwp'),artifacts=pathlib.Path('unused-artifacts'),child_env=lambda:{})
 def prepare(*args,**kw):return {'index':args[5]}
 def execute(ctx,p,**kw):return ctx.traces[cid][p['index']]
 with patch.object(f,'_prepare_run',side_effect=prepare),patch.object(f,'_execute',side_effect=execute),patch.object(f,'probe_catalog',return_value={'state':state,'ref':None,'error':None}):
  actual=f.case_call_kill_after_import(ctx)
 results.append({'probe_state':state,'handler_result':actual.result,'actual':{k:v for k,v in actual.actual.items() if k!='runs'},'diagnostics':actual.diagnostics})
print(json.dumps(results,indent=2))

