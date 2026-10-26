from pathlib import Path
import types,hashlib,json,tempfile,shutil,socket,subprocess
from unittest.mock import patch
root=Path(__file__).resolve().parents[3];out=Path(__file__).parent;path=root/'tools/document_understanding_benchmark/phase_c_runner.py'
raw=path.read_bytes();digest=hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()
runner=types.ModuleType('independent_historical_runner');runner.__file__=str(path);exec(compile(raw,str(path),'exec'),runner.__dict__)
results=[];real_mkdtemp=tempfile.mkdtemp
with tempfile.TemporaryDirectory(prefix='c3ir-',dir=root) as folder:
 owned=Path(folder);runner.ROOT=owned;original=owned/'original.txt';original.write_text('Neutral source fixture',encoding='utf-8');gold=owned/'empty-gold.json';gold.write_text('{"facts":[]}',encoding='utf-8')
 provider=runner.loopback_preparation()['providers'][0]
 def sample():return {'sample_id':'brand-new-neutral-id','original':str(original),'fingerprint':runner.fingerprint(original),'gold':str(gold),'mime_type':'text/plain','source_metadata_observation':{'entity':'Neutral Issuer','market':'US','security_id':'NONE','title':'Neutral','document_kind':'investor_relations','language':None,'published_date':None,'filing_date':None},'verified_official_descriptor':{'title':'Only title verified'}}
 def denied(*a,**kw):raise AssertionError('no network allowed')
 with patch.object(socket.socket,'connect',denied),patch('socket.create_connection',denied):
  for case in ['primary_title_only_no_date','primary_title_only_observed_date','missing_original','invalid_gold_json']:
   value=sample();allocated=[];destination=owned/case;destination.mkdir()
   if case=='primary_title_only_observed_date':value['source_metadata_observation']['published_date']='2020-01-02'
   if case=='missing_original':value['original']=str(owned/'not-present.txt')
   if case=='invalid_gold_json':bad=owned/'bad-gold.json';bad.write_text('{',encoding='utf-8');value['gold']=str(bad)
   def allocate(*a,**kw):
    if len(a)>=3:a=(*a[:2],str(owned),*a[3:])
    else:kw['dir']=str(owned)
    p=real_mkdtemp(*a,**kw);allocated.append(Path(p));return p
   def held_identity(*a,**kw):raise RuntimeError('INDEPENDENT_HELD_BEFORE_MODEL')
   with patch.object(runner.tempfile,'gettempdir',return_value=str(owned)),patch.object(runner.tempfile,'mkdtemp',side_effect=allocate),patch.object(runner,'seed_identity',side_effect=held_identity),patch.object(runner,'_cli',side_effect=AssertionError('no CLI/model allowed')):
    try:actual=runner.run_pair(value,provider,runner.loopback_preparation(),mode='live',output=destination,selected_versions='0.9.0');error=None
    except Exception as exc:actual=None;error={'type':type(exc).__name__,'message':str(exc)}
   leaked=[str(p) for p in allocated if p.exists()]
   assert not leaked,(case,leaked)
   if case.startswith('primary_'):assert actual is not None,(case,error)
   else:assert error is not None and error['type']==('FileNotFoundError' if case=='missing_original' else 'JSONDecodeError'),(case,error)
   if actual is not None:
    expected_method='source_metadata_observation.published_date' if case=='primary_title_only_observed_date' else 'unknown_public_availability'
    assert actual['availability_date_provenance']['method']==expected_method
    assert actual['temporary_lake_removed'] and actual['model_post_attempts']==0
   results.append({'case':case,'provenance':actual.get('availability_date_provenance') if actual else None,'status':actual.get('status') if actual else None,'error':error,'allocated_roots':len(allocated),'leaked_before_independent_cleanup':leaked,'model_post_attempts':actual.get('model_post_attempts') if actual else 0})
   for p in allocated:
    assert p.resolve().parent==owned.resolve() and p.name.startswith('cwplC-')
    if p.exists():shutil.rmtree(p)
 evidence={'snapshot':'current C3 lifecycle/provenance fix','source_lf_sha256':digest,'results':results,'holdout_read':False,'network_calls':0,'model_calls':0,'manual_owned_cleanup_done':True}
(out/'independent-after-fix-probe-v2.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(evidence,ensure_ascii=False,indent=2))
