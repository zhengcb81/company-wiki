"""Pure controls: retained real case + independent unrelated-sidecar handler probe.
No processes/provider requests; not a fresh full E2E. Run python -B script --ff-root <author worktree>.
"""
import argparse,json,pathlib,sys
from types import SimpleNamespace
from unittest.mock import patch
p=argparse.ArgumentParser();p.add_argument('--ff-root',type=pathlib.Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.ff_root/'tools/offline_contract_matrix'),str(a.ff_root/'scripts')]
import w20_fault_cases as f
from w20_case_specs import get_w20_spec
c=json.loads(pathlib.Path(__file__).with_name('retained-case.json').read_text('utf-8'))['case']
probes=[]
def prepare(*args,**kw): return {'index':args[5]}
def execute(ctx,prepared,**kw):
 if kw.get('kill_when'): probes.append({'index':prepared['index'],'triggered_on_unrelated_preexisting_sidecar':kw['kill_when']()})
 return {'response':{'transcript':{'status':'downloaded'}},'et_fixture_requests':1,'kill_reason':'probe'}
with patch.object(f,'_prepare_run',side_effect=prepare),patch.object(f,'_execute',side_effect=execute),patch.object(f,'_transcript_sidecars',return_value=[pathlib.Path('unrelated-period.source.json')]),patch.object(f,'_result',side_effect=lambda *a:a[-1]):
 f.case_call_kill_after_import(SimpleNamespace())
print(json.dumps({'actual_retained_case':{'result':c['result'],'recovery_branch':c['actual']['recovery_branch'],'recovery_extra_gets':c['actual']['runs'][1]['et_fixture_requests'],'assertion_errors_now':get_w20_spec(c['id']).assertion_errors(c)},'synthetic_handler_probe':probes,'probe_scope':'pure handler control flow only, not E2E'},indent=2))
