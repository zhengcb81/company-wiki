"""Independent read-only P7-RF reception; all runtime outputs owned TEMP."""
from __future__ import annotations
import hashlib, json, os, shutil, stat, subprocess, sys, tempfile, time
from pathlib import Path
RF=Path(r"C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/revenue-forecast")
EVIDENCE=Path(__file__).resolve().parent
sys.path[:0]=[str(RF/'scripts'),str(RF/'tests')]
from test_research_evidence_roles import calibrated_document
from company_wiki_source_v2 import build_revenue_source_record_from_verified_read
from test_company_wiki_source_reader_v2 import BODY, _ref, _receipt
from revenue_core import validate_document
from research.evidence_roles import analyze_operating_research
from schema_compatibility import validating_engine_allowed

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(RF),*args],text=True,encoding='utf-8').strip()
def snapshot():
 paths=git('ls-files').splitlines()
 delivery=set(git('diff','--name-only','6883bf00548abb9891eab6762aeaa89e3898b202','HEAD').splitlines())
 focused={'tests/test_research_evidence_roles.py','tests/test_company_wiki_source_reader_v2.py','tests/test_recognition_bridge.py','tests/test_data_contract.py','tests/conftest.py','tools/build_auditable_case.py','tools/run_target_measurement_e2e.py'}
 return {x:sha(RF/x) for x in paths if (x in delivery or x in focused or x.startswith(('scripts/','config/'))) and (RF/x).is_file()}

def main():
 started=time.monotonic();before=snapshot();head=git('rev-parse','HEAD');status=git('status','--porcelain=v1')
 owned=Path(tempfile.mkdtemp(prefix='p7-rf-readonly-reception-'))
 receipt={'schema_version':'p7-rf-readonly-reception/1','head':head,'base':'6883bf00548abb9891eab6762aeaa89e3898b202','status_before':status,'provider_calls':0,'model_calls':0,'new_cost_usd':0,'runs':[],'cases':[],'owned_temp':str(owned),'cli_probes':[]}
 env=dict(os.environ);env.update(PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONUTF8='1',PYTHONIOENCODING='utf-8',REVENUE_PUBLICATION_REGISTRY=str(owned/'registry'/'publications.jsonl'))
 def is_owned(path):return Path(path).resolve().is_relative_to(owned.resolve())
 def run(name,args):
  assert is_owned(env['REVENUE_PUBLICATION_REGISTRY'])
  t=time.monotonic();done=subprocess.run([sys.executable,'-X','utf8','-B',*map(str,args)],cwd=owned,env=env,capture_output=True,text=True,encoding='utf-8',timeout=150)
  record={'name':name,'argv':done.args,'exit_code':done.returncode,'seconds':time.monotonic()-t,'stdout':done.stdout,'stderr':done.stderr,'registry':env['REVENUE_PUBLICATION_REGISTRY']};receipt['runs'].append(record)
  print(json.dumps({'name':name,'exit_code':done.returncode,'seconds':record['seconds']},ensure_ascii=False),flush=True)
  return done
 def case(name,mutation=None):
  case_root=owned/name;case_root.mkdir();d=calibrated_document()
  if mutation:mutation(d)
  raw_receipt=_receipt();manifest=raw_receipt.pop('manifest')
  candidate={'status':'source_candidate','source_ref':_ref(),'byte_verification':'pending_verified_open','document_kind':manifest['document_kind'],'fiscal_year':manifest['fiscal_year'],'fiscal_period':manifest['fiscal_period'],'resolution_outcome':'reused_existing','download_events':0}
  source=build_revenue_source_record_from_verified_read(source_ref=_ref(),read_receipt=raw_receipt,source_bytes=BODY,source_manifest=manifest,source_candidate=candidate,as_of_date=d['as_of_date'],source_type='regulatory_filing',publisher='independent synthetic reception fixture',page_or_section='1')
  sid=source['source_id']
  def rekey(v):
   if isinstance(v,dict):return {k:rekey(x) for k,x in v.items()}
   if isinstance(v,list):return [rekey(x) for x in v]
   return sid if v=='filing' else v
  d=rekey(d);d['sources'][0]=source
  for claim in d['evidence_claims']:
   if claim['source_id']==sid:
    claim['content_sha256']=source['capture']['snapshot_sha256'];claim['capture_receipt_sha256']=source['capture']['receipt_sha256']
  research=d.pop('operating_research')
  objects={'input':d,'research':research,'preparation':{'schema_version':'source-preparation-result/1','source':source,'filing_fetch':None,'narrative':None},'discovery':{'schema_version':'synthetic-discovery-receipt/1','items':[],'coverage_complete':False}}
  for label,obj in objects.items():(case_root/(label+'.json')).write_text(json.dumps(obj,ensure_ascii=False),encoding='utf-8')
  assembled=case_root/'assembled';native=case_root/'native'
  assert all(is_owned(x) for x in (case_root,assembled,native))
  build=run(name+'-assemble',[RF/'tools/build_auditable_case.py','--company','independent synthetic','--input',case_root/'input.json','--research',case_root/'research.json','--preparation',case_root/'preparation.json','--discovery',case_root/'discovery.json','--as-of',d['as_of_date'],'--output-root',assembled])
  assert build.returncode==0,build.stderr
  actual=run(name+'-native',[RF/'tools/run_target_measurement_e2e.py','--input',assembled/'linked-input.json','--output-root',native])
  assert actual.returncode==0,actual.stderr
  diag=run(name+'-diagnostic',[RF/'scripts/research_support_diagnostics.py','--input',assembled/'linked-input.json'])
  assert diag.returncode==0,diag.stderr
  forecast=json.loads((native/'forecast.json').read_text(encoding='utf-8'));diagnostic=json.loads(diag.stdout);assembly=json.loads((assembled/'assembly.json').read_text(encoding='utf-8'))
  cal=forecast['confidence']['research_adequacy']['calibrations'][0]
  entries=next(s for s in diagnostic['segments'] if s['segment']=='Segment A')['entries']
  item={'name':name,'assembly_supplier_calls':assembly['new_supplier_calls'],'assembly_model_calls':assembly['new_model_calls'],'calibration_status':cal['adequacy_status'],'calibration_reasons':cal['reasons'],'engine_version':forecast['engine_version'],'confidence_calculation_version':forecast['confidence']['calculation_version'],'confidence_score':forecast['confidence']['score'],'consolidated_forecast':forecast['consolidated_forecast'],'magnitude_ids':forecast['confidence']['research_adequacy']['magnitude_adequacy']['supported_parameter_ids'],'source_ref':assembly['source_bindings'][0]['source_ref'],'diagnostic':diagnostic,'sha256':{str(p.relative_to(case_root)):sha(p) for p in case_root.rglob('*') if p.is_file()},'registry_inside_owned':all(is_owned(p) for p in owned.rglob('publications.jsonl')),'real_snapshot':(native/'snapshot.json').is_file(),'report_matches_diagnostic':cal['adequacy_status'] in (native/'forecast.md').read_text(encoding='utf-8'),'native_events':json.loads((native/'commands.json').read_text(encoding='utf-8'))}
  assert assembly['new_supplier_calls']==assembly['new_model_calls']==0
  assert diagnostic['input_sha256']==sha(assembled/'linked-input.json')
  assert item['real_snapshot'] and item['registry_inside_owned'] and item['report_matches_diagnostic']
  receipt['cases'].append(item)
  return item
 try:
  (owned/'registry').mkdir()
  responsibility=run('concentrated-responsibility',['-m','pytest','-p','pytest_timeout','-p','no:cacheprovider','--basetemp',owned/'pytest','--timeout=60','-q',RF/'tests/test_scoped_calibration_support.py',RF/'tests/test_research_support_diagnostics.py',RF/'tests/test_research_evidence_roles.py'])
  assert responsibility.returncode==0,responsibility.stdout+responsibility.stderr
  receipt['responsibility']='25 PASS'
  positive=case('positive')
  assert positive['calibration_status']=='referenced_range' and positive['calibration_reasons']==[]
  assert positive['engine_version']=='4.2.1' and positive['confidence_calculation_version']=='stable-fsum/1'
  cells=next(s for s in positive['diagnostic']['segments'] if s['segment']=='Segment A')['entries']
  assert all(e['status']=='supported' for e in cells if e['year']=='2026')
  assert all(e['status']=='unsupported' for e in cells if e['year']=='2027')
  def observation_period(d):
   for o in d['operating_research']['observations']:
    if o['observation_kind']=='conversion':o['period']='FY2031'
  negative=case('observation-period-negative',observation_period)
  assert negative['calibration_status']=='unverified' and any('unverified_period' in r for r in negative['calibration_reasons'])
  assert negative['consolidated_forecast']==positive['consolidated_forecast'] and negative['confidence_score']==positive['confidence_score']
  def synchronize_period(d):
   for p in d['parameters']:
    if p['parameter_id'].startswith('conversion_'):p['period']='FY2031'
   for c in d['evidence_claims']:
    if c['target_id'].startswith('conversion_'):c['period']='FY2031'
   observation_period(d)
  adversarial=case('synchronized-future-conversion-period',synchronize_period)
  receipt['synchronized_period_expectation']={'expected':'unverified','actual':adversarial['calibration_status'],'met':adversarial['calibration_status']=='unverified','original_output_period':'FY2026','conversion_parameter_claim_observation_period':'FY2031'}
  for label,mut in [('unknown-range',lambda d:d['operating_research']['calibrations'][0].update(observed_range=None)),('stress',lambda d:d['operating_research']['calibrations'][0].update(status='stress'))]:
   doc=calibrated_document();mut(doc);cal=analyze_operating_research(doc,validate_document(doc))['calibrations'][0];receipt['cli_probes'].append({'name':label,'status':cal['adequacy_status'],'range':cal['observed_range'],'reasons':cal['reasons']})
  def reject_probe(label,mut):
   doc=calibrated_document();mut(doc);path=owned/(label+'.json');path.write_text(json.dumps(doc,ensure_ascii=False),encoding='utf-8');done=run(label,[RF/'scripts/research_support_diagnostics.py','--input',path]);receipt['cli_probes'].append({'name':label,'rejected':done.returncode!=0,'error':done.stderr});assert done.returncode!=0
  reject_probe('scenario-output-crossborrow',lambda d:d['operating_research']['calibrations'][0]['scenario_output_parameter_ids'].update(low='0_base_2026'))
  reject_probe('stale-claim-excerpt-sha',lambda d:d['evidence_claims'][0].update(excerpt_sha256='0'*64))
  receipt['emitter_compatibility']={schema:{v:validating_engine_allowed(schema,v,'output') for v in ('4.2.0','4.2.1')} for schema in ('3.7','3.8','3.9')}
  receipt['status']='source_partial' if not receipt['synchronized_period_expectation']['met'] else 'accepted'
 except BaseException as exc:
  receipt['status']='reception_failed';receipt['exception']=repr(exc)
  raise
 finally:
  after=snapshot();receipt['tracked_sha_unchanged']=before==after;receipt['tracked_sha_count']=len(before);receipt['sha_scope']='all runtime scripts/config, delivery paths and actual CLI/test fixture dependency files; full tracked status checked without hashing historical planning records';receipt['status_after']=git('status','--porcelain=v1');receipt['head_after']=git('rev-parse','HEAD');receipt['seconds']=time.monotonic()-started
  assert receipt['tracked_sha_unchanged'] and receipt['status_after']==status and receipt['head_after']==head
  assert owned.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
  def writable_retry(function,path,exception):
   assert Path(path).resolve().is_relative_to(owned.resolve())
   os.chmod(path,stat.S_IWRITE|stat.S_IREAD);function(path)
  receipt['cleanup']={'removed':False,'environment_restored':True,'no_rf_repository_write':True}
  (EVIDENCE/'readonly-reception-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  shutil.rmtree(owned,onexc=writable_retry);receipt['cleanup']['removed']=not owned.exists()
  out=EVIDENCE/'readonly-reception-receipt.json';out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print(json.dumps({'status':receipt['status'],'tracked_sha_unchanged':receipt['tracked_sha_unchanged'],'owned_temp_removed':receipt['cleanup']['removed'],'receipt':str(out)},ensure_ascii=False),flush=True)
 return 1 if receipt['status']=='source_partial' else 0
if __name__=='__main__':raise SystemExit(main())
