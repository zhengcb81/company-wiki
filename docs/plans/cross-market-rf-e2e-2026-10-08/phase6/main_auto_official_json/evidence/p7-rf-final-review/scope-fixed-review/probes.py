"""Final independent scope correction review: six pure-memory native probes."""
from pathlib import Path
from copy import deepcopy
import sys,os,hashlib,json,subprocess,time
sys.dont_write_bytecode=True
rf=Path(sys.argv[1]).resolve();out=Path(__file__).resolve().parent;base=out.parent
sys.path.insert(0,str(rf/'scripts'));sys.path.insert(0,str(rf/'tests'))
from research_support_diagnostics import build_support_diagnostics
from research.evidence_roles import analyze_operating_research
from revenue_core import validate_document
from test_research_evidence_roles import calibrated_document
from test_scoped_calibration_support import target_period_bridge_document

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def head():
 e={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
 p=subprocess.run(['git','rev-parse','HEAD'],cwd=rf,env=e,text=True,capture_output=True,encoding='utf-8');return {'exit':p.returncode,'head':p.stdout.strip()}
def cell(d,segment,s,year=2026):return next(e for row in d['segments'] if row['segment']==segment for e in row['entries'] if e['scenario']==s and e['year']==str(year))
def comparison(d):
 return [(r['segment'],e['scenario'],e['year'],e['status'],e['supported_parameter_ids'],e['unsupported_parameter_ids'],e['calibration_ids'],e['claim_ids'],sorted(e['reasons'])) for r in d['segments'] for e in r['entries']]
def add_scoped_calibration(d, scope, calid, suffix):
 research=d['operating_research'];c=deepcopy(research['calibrations'][0]);c['scope']=scope;c['calibration_id']=calid
 claims={x['claim_id']:x for x in d['evidence_claims']};obs={x['claim_id']:x for x in research['observations']};newids=[]
 for old in c['source_claim_ids']:
  new=old+suffix;claim=deepcopy(claims[old]);claim['claim_id']=new;d['evidence_claims'].append(claim)
  next(p for p in d['parameters'] if p['parameter_id']==claim['target_id'])['claim_ids'].append(new)
  ob=deepcopy(obs[old]);ob['claim_id']=new;ob['scope']=scope;research['observations'].append(ob);newids.append(new)
 c['source_claim_ids']=newids;research['calibrations'].append(c);return sorted(newids)
source_expected=json.loads((rf/'.planning/p7-rf-scoped-calibration/main_reception/protected-after.json').read_text(encoding='utf-8'))['source_sha256']
source_expected.update({'scripts/research_support_diagnostics.py':'dd09b7088c691205950413adafaf9604e303966c6aada7c344d63486dec12902','tests/test_research_support_diagnostics.py':'af2a5c81895b1ec1b450a553331852261eba9d2f908ec99959bc3d31b801e12f'})
source_before={p:sha(rf/p) for p in source_expected};assert source_before==source_expected,'Source differs from scope-stable handoff'
original_expected={'probes.log':'728a341d8d82b6563ae9bc67f3a86e8d036271101cc22ea331e374b40363c3e3','probes.py':'2bc1491dde0c02d335847aafd6e212088b59d7473128afa72009828e82ffc9dd','receipt.json':'85cea978199666ec0178f35f2f82abdc1be740c4f500c8246463c6e9318817b3','review.md':'c06b604af4e3fde98d4da026e2d37f113de077af4ce911f68d18cc8ff50c59b3','shared_root_minimal_input.json':'3353ccb20511e42a86ca3a8bc1e4e3bce6dad483c4c481e32e6276bedb506ef7'}
original_before={p:sha(base/p) for p in original_expected};assert original_before==original_expected
protect=json.loads((rf/'.planning/p7-rf-scoped-calibration/main_reception_scope_fix/before.json').read_text(encoding='utf-8'))['protected']
start=time.perf_counter();env_before=dict(os.environ);head_before=head();records=[]
shared=json.loads((base/'shared_root_minimal_input.json').read_text(encoding='utf-8'))

def run(name,d,check,extra=None):
 before=deepcopy(d);validated=validate_document(d);adequacy=analyze_operating_research(d,validated)
 diag=build_support_diagnostics(d,hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest())
 assert before==d, 'Native pure projection mutated its input'
 x={'name':name,'native_validation':'passed','expectation_met':bool(check(diag)),
    'adequacy_status':[c['adequacy_status'] for c in adequacy['calibrations']],
    'diagnostic':diag,'input_unmodified':True}
 if extra:x['extra']=extra
 records.append(x);return diag

# 1 Exact saved independent failure, no new fixture reconstruction.
run('saved-shared-root-scope-attack',deepcopy(shared),lambda n:all(cell(n,'Segment A',s)['status']=='supported' and cell(n,'Segment B',s)['status']=='unsupported' and cell(n,'Segment B',s)['calibration_ids']==cell(n,'Segment B',s)['claim_ids']==[] for s in ('low','base','high')))

# 2 Distinct valid A/B scoped calibrations for the same roots, in both orders.
d=deepcopy(shared);a_claims=sorted(d['operating_research']['calibrations'][0]['source_claim_ids']);b_claims=add_scoped_calibration(d,'Segment B','calibration_b','_independent_b')
forward=run('distinct-scopes-claim-isolation-and-order',d,lambda n:all(cell(n,'Segment A',s)['claim_ids']==a_claims and cell(n,'Segment B',s)['claim_ids']==b_claims and cell(n,'Segment A',s)['calibration_ids']==['reference_bridge'] and cell(n,'Segment B',s)['calibration_ids']==['calibration_b'] for s in ('low','base','high')))
reverse=deepcopy(d);reverse['operating_research']['calibrations'].reverse();reverse_diag=build_support_diagnostics(reverse,'0'*64)
records[-1]['order_independent']=comparison(forward)==comparison(reverse_diag);records[-1]['expectation_met'] &= records[-1]['order_independent']

# 3 Multiple applicable IDs for one actual A cell: retain both, keep company
# calibration only for B, and never choose the first ID/borrow the A claims.
d=deepcopy(shared);a_claims=sorted(d['operating_research']['calibrations'][0]['source_claim_ids']);co_claims=add_scoped_calibration(d,d['company_name'],'calibration_company','_independent_company')
forward=run('multiple-calibration-ids-for-same-cell',d,lambda n:all(cell(n,'Segment A',s)['calibration_ids']==['calibration_company','reference_bridge'] and cell(n,'Segment A',s)['claim_ids']==sorted(a_claims+co_claims) and cell(n,'Segment B',s)['calibration_ids']==['calibration_company'] and cell(n,'Segment B',s)['claim_ids']==co_claims for s in ('low','base','high')))
reverse=deepcopy(d);reverse['operating_research']['calibrations'].reverse();reverse_diag=build_support_diagnostics(reverse,'0'*64)
records[-1]['order_independent']=comparison(forward)==comparison(reverse_diag);records[-1]['expectation_met'] &= records[-1]['order_independent']

# 4 An actual company-scoped calibration is allowed, not a blanket ban on
# sharing native roots. Its FY2026 relation cannot support the FY2027 cells.
d=deepcopy(shared);d['operating_research']['calibrations'][0]['scope']=d['company_name']
for o in d['operating_research']['observations']:o['scope']=d['company_name']
run('explicit-company-scope-positive',d,lambda n:all(cell(n,seg,s)['status']=='supported' and cell(n,seg,s,2027)['status']=='unsupported' for seg in ('Segment A','Segment B') for s in ('low','base','high')))

# 5 Disclosure / measurement / applicability remain independent meanings.
d=calibrated_document()
for p in d['parameters']:
 if p['parameter_id'].startswith('conversion_'):p['measurement_period']='FY2025'
for o in d['operating_research']['observations']:
 if o['observation_kind']=='conversion':o['period']='FY2025'
for c in d['evidence_claims']:
 if c['target_id'].startswith('conversion_'):c['period']='FY2024'
run('historical-measurement-and-disclosure-positive',d,lambda n:all(cell(n,'Segment A',s)['status']=='supported' for s in ('low','base','high')))

# 6 True historical source->target derived bridge is still permitted.
d=target_period_bridge_document()
for c in d['evidence_claims']:
 if c['target_id'].startswith('conversion_'):c['period']='FY2024'
run('explicit-native-target-bridge-positive',d,lambda n:all(cell(n,'Segment A',s)['status']=='supported' for s in ('low','base','high')))
source_after={p:sha(rf/p) for p in source_expected};assert source_after==source_before
original_after={p:sha(base/p) for p in original_expected};assert original_after==original_before
protected_match={p:sha(rf/p)==h for p,h in protect.items()};assert all(protected_match.values())
assert dict(os.environ)==env_before
receipt={'schema_version':'p7-rf-scope-fixed-independent-review/1','status':'pass' if all(x['expectation_met'] for x in records) else 'specific_blocker','probes':records,'probe_count':len(records),'head_before':head_before,'head_after':head(),'source_sha256':source_after,'source_unchanged':True,'original_failure_evidence_sha256':original_after,'original_failure_evidence_unchanged':True,'protected_match':protected_match,'environment_unchanged':True,'temp_created':False,'provider_calls':0,'model_calls':0,'new_cost_usd':0,'publication_registry_calls':0,'seconds':time.perf_counter()-start}
(out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
for x in records:print(json.dumps({'probe':x['name'],'expectation_met':x['expectation_met'],'native_validation':x['native_validation'],'order_independent':x.get('order_independent')},ensure_ascii=False))
print(json.dumps({'status':receipt['status'],'source_sha_count':len(source_after),'protected_count':len(protected_match),'seconds':receipt['seconds'],'original_failure_evidence_unchanged':True},ensure_ascii=False))
