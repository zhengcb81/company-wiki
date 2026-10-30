"""Actual runner DTO -> actual RF pure validator. No source open/model/network."""
from pathlib import Path
import json, os, subprocess, sys

root=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(root),str(root/'src'),str(root/'tests')]
from tools.document_understanding_benchmark import phase_c_runner as runner
out=Path(__file__).parent
record=json.loads((root/'.planning/summary-quality-20261030/real-registered-ir-v2/source-preparation.json').read_text('utf-8'))
trace=record['source']['company_wiki_trace']
ref,manifest=trace['source_ref'],trace['source_manifest']
request={'narrative_ref':{'source_ref':ref}}
bundle={'source_ref':ref,'reading_context':{},'evidence_spans':[],'summary':{}}
descriptor={key:manifest.get(key) for key in ('security_id','market','document_kind','fiscal_year','fiscal_period')}
script="""import json,sys
sys.path.insert(0,sys.argv[1])
from company_wiki_source_v2 import _validate_candidate
from company_wiki_source import CompanyWikiSourceError
r=json.load(sys.stdin)
c=r['candidate']
assert _validate_candidate(c,r['ref'],r['manifest'])==c
rejected=[]
for value in ([],False,'0',0.0,None,1):
 bad={**c,'download_events':value}
 try: _validate_candidate(bad,r['ref'],r['manifest'])
 except CompanyWikiSourceError: rejected.append(type(value).__name__+':'+repr(value))
 else: raise AssertionError('bad event shape accepted')
print(json.dumps({'status':'PASS','valid_download_events':c['download_events'],'type':type(c['download_events']).__name__,'negative_shapes_rejected':rejected}))
"""
observed=[]
def cli(base,output,name,command,env,data=None,**kwargs):
 observed.append(name)
 if name=='rf-registered-source':
  assert data['candidate']['source_ref']==ref
  proc=subprocess.run([sys.executable,'-B','-X','utf8','-c',script,str(root.parent/'revenue-forecast/scripts')],input=json.dumps({'candidate':data['candidate'],'ref':ref,'manifest':manifest}),capture_output=True,text=True,encoding='utf-8',cwd=root.parent/'revenue-forecast',timeout=30)
  (out/'actual-rf-candidate-stderr.txt').write_text(proc.stderr,encoding='utf-8')
  assert proc.returncode==0,proc.stderr
  actual=json.loads(proc.stdout)
  (out/'actual-rf-candidate.json').write_text(json.dumps(actual,indent=2)+'\n',encoding='utf-8')
  return 0,{'filing_fetch':None},'',b''
 assert name=='rf-narrative'
 return 0,{**bundle,**request,'read_receipt':{'replay_status':'verified'}},'',b''
runner._cli=cli
with __import__('tempfile').TemporaryDirectory(prefix='rf-dto-',dir=out) as name:
 runner.consumers(Path(name),Path(name),{},Path(name)/'config.yaml',descriptor,request,bundle,projects=root.parent)
assert observed==['rf-registered-source','rf-narrative']
print(json.dumps({'status':'PASS_ACTUAL_RF_CANDIDATE_BOUNDARY_ONLY','pure_validator_calls':7,'source_opens':0,'downloads':0,'model_posts':0,'no_real_narrative_or_forecast_acceptance':True}))
