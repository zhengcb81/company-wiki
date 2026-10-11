"""Independent pure-memory P7-RF reception probes. No providers, publication or RF writes."""
from pathlib import Path
from copy import deepcopy
import sys, os, json, hashlib, subprocess, time
sys.dont_write_bytecode = True
rf=Path(sys.argv[1]).resolve()
out=Path(__file__).resolve().parent
sys.path.insert(0,str(rf/'scripts'));sys.path.insert(0,str(rf/'tests'))
from test_research_evidence_roles import calibrated_document
from test_scoped_calibration_support import synchronized_conversion_period, target_period_bridge_document
from revenue_core import validate_document
from research.evidence_roles import analyze_operating_research
from research_support_diagnostics import build_support_diagnostics
from schema_compatibility import validating_engine_allowed

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):
 env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
 r=subprocess.run(['git',*args],cwd=rf,env=env,text=True,encoding='utf-8',capture_output=True)
 return {'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
def replace_ids(v,m):
 if isinstance(v,str):return m.get(v,v)
 if isinstance(v,list):
  a=[replace_ids(x,m) for x in v]
  return list(dict.fromkeys(a)) if all(isinstance(x,str) for x in a) else a
 if isinstance(v,dict):return {k:replace_ids(x,m) for k,x in v.items()}
 return v
protected=json.loads((rf/'.planning/p7-rf-scoped-calibration/main_reception/protected-before.json').read_text(encoding='utf-8'))
expected=json.loads((rf/'.planning/p7-rf-scoped-calibration/main_reception/protected-after.json').read_text(encoding='utf-8'))['source_sha256']
before={p:sha(rf/p) for p in expected}
assert before==expected, 'Source differs from source-stable handoff; review scope must be refreshed'
head_before=git('rev-parse','HEAD')
environment_before=dict(os.environ)
records=[];start=time.perf_counter()

def probe(name,d,expectation,check):
 v=validate_document(d)
 a=analyze_operating_research(d,v)
 native=build_support_diagnostics(d,sha_input(d))
 row={'name':name,'native_validation':'passed','expectation':expectation,
      'calibration':a['calibrations'][0] if a is not None and a['calibrations'] else None,
      'cells':native['segments'],'economic_truth_inferred':native['economic_truth_inferred']}
 row['expectation_met']=bool(check(a,native));records.append(row)
 return row

def sha_input(d):return hashlib.sha256(json.dumps(d,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def cell(n,segment,scenario,year):return next(e for s in n['segments'] if s['segment']==segment for e in s['entries'] if e['scenario']==scenario and e['year']==str(year))

# 1. Legitimate shared native roots. Keep two annual cells; update only actual
# research-reference ID sets. All original parameter/claim/calibration scope
# facts remain unchanged. No business-name exception or new identity gate.
d=calibrated_document();mapping={}
for scenario in ('low','base','high'):
 old=f'1_{scenario}_2026';new=f'0_{scenario}_2026';mapping[old]=new
 d['segments'][1]['scenarios'][scenario]['driver_parameter_ids']['revenue'][0]=new
d['research_coverage']=replace_ids(d['research_coverage'],mapping)
d['growth_driver_tree']=replace_ids(d['growth_driver_tree'],mapping)
(out/'shared_root_minimal_input.json').write_text(json.dumps(d,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
probe('shared-root-cross-segment',d,'Segment A FY2026 supported; Segment B FY2026 unsupported because calibration scope remains Segment A',
 lambda a,n: all(cell(n,'Segment A',s,2026)['status']=='supported' and cell(n,'Segment B',s,2026)['status']=='unsupported' for s in ('low','base','high')))

# 2. Same direct output consumed by two fiscal cells must not gain support for
# the second one. Do not deduplicate the actual two-year driver arrays.
d=calibrated_document();mapping={}
for scenario in ('low','base','high'):
 old=f'0_{scenario}_2027';new=f'0_{scenario}_2026';mapping[old]=new
 d['segments'][0]['scenarios'][scenario]['driver_parameter_ids']['revenue'][1]=new
d['research_coverage']=replace_ids(d['research_coverage'],mapping)
d['growth_driver_tree']=replace_ids(d['growth_driver_tree'],mapping)
probe('shared-root-cross-year',d,'actual FY2027 direct consumption mismatch diagnoses unverified; optional diagnostic only',
 lambda a,n: a['calibrations'][0]['adequacy_status']=='unverified' and any('FY2027' in r and r.startswith('calibration_output_consumption_period_mismatch:') for r in a['calibrations'][0]['reasons']))

# 3. Source disclosure and original measurement date are independent of the
# parameter applicability date. They are not an equality approval gate.
d=calibrated_document()
for p in d['parameters']:
 if p['parameter_id'].startswith('conversion_'):p['measurement_period']='FY2025'
for o in d['operating_research']['observations']:
 if o['observation_kind']=='conversion':o['period']='FY2025'
for c in d['evidence_claims']:
 if c['target_id'].startswith('conversion_'):c['period']='FY2024'
probe('historical-measurement-and-disclosure',d,'FY2025 measurement / FY2024 disclosure / FY2026 applicability remains referenced_range',
 lambda a,n:a['calibrations'][0]['adequacy_status']=='referenced_range' and a['calibrations'][0]['reasons']==[])

# 4. Company scope must still inspect the actual segment/scenario/cell.
d=calibrated_document();cal=d['operating_research']['calibrations'][0]
synchronized_conversion_period(d,'FY2031');cal['scope']=d['company_name']
for o in d['operating_research']['observations']:o['scope']=d['company_name']
outputs=set(cal['scenario_output_parameter_ids'].values())
for p in d['parameters']:
 if p['parameter_id'] in outputs:p['period']='FY2031'
for c in d['evidence_claims']:
 if c['target_id'] in outputs:c['period']='FY2031'
probe('company-scope-direct-wrong-period',d,'internally consistent FY2031 output still mismatches real Segment A FY2026 direct cell',
 lambda a,n:a['calibrations'][0]['adequacy_status']=='unverified' and all(cell(n,'Segment A',s,2026)['status']=='unsupported' for s in ('low','base','high')))

# 5. Explicit historical->target native bridge stays valid after retaining
# even older claim disclosure provenance. No repeated public E2E is run.
d=target_period_bridge_document()
for c in d['evidence_claims']:
 if c['target_id'].startswith('conversion_'):c['period']='FY2024'
probe('explicit-native-bridge-older-disclosure',d,'real FY2025 factor -> FY2026 derived conversion remains valid with FY2024 source disclosure',
 lambda a,n:a['calibrations'][0]['adequacy_status']=='referenced_range' and a['calibrations'][0]['reasons']==[])

# Read-only old optional / archived emitter controls, not another full suite.
legacy=calibrated_document();legacy.pop('operating_research')
legacy_control=analyze_operating_research(legacy,validate_document(legacy)) is None
emit_control={s:{e:validating_engine_allowed(s,e,'output') for e in ('4.2.0','4.2.1')} for s in ('3.7','3.8','3.9')}
after={p:sha(rf/p) for p in expected}
protected_actual={p:sha(rf/p)==v for p,v in protected['rf_sha256'].items()}
assert before==after, 'SOURCE_CHANGED'
assert all(protected_actual.values()), 'PROTECTED_SOURCE_CHANGED'
assert environment_before==dict(os.environ),'ENVIRONMENT_CHANGED'
receipt={'schema_version':'p7-rf-independent-final-review/1','head_before':head_before,
 'head_after':git('rev-parse','HEAD'),'source_before_sha256':before,'source_after_sha256':after,
 'source_unchanged':True,'protected_originals':protected_actual,'probe_count':len(records),
 'probes':records,'legacy_absent_optional_none':legacy_control,'archived_emitter_output_controls':emit_control,
 'seconds':time.perf_counter()-start,'provider_calls':0,'model_calls':0,'new_cost_usd':0,
 'publication_registry_calls':0,'temp_created':False,'environment_unchanged':True,
 'status':'specific_blocker' if any(not x['expectation_met'] for x in records) else 'pass',
 'scope':'pure memory actual validate_document -> analyze_operating_research -> build_support_diagnostics; no run_forecast, no publication, no project writes'}
(out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
for x in records:print(json.dumps({'probe':x['name'],'native_validation':x['native_validation'],'expectation_met':x['expectation_met'],'calibration':x['calibration']['adequacy_status'] if x['calibration'] else None},ensure_ascii=False))
print(json.dumps({'status':receipt['status'],'source_unchanged':True,'protected_original_count':len(protected_actual),'all_protected_unchanged':all(protected_actual.values()),'seconds':receipt['seconds']},ensure_ascii=False))
