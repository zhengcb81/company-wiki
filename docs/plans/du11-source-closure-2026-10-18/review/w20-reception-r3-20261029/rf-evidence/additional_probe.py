import sys,json,copy,subprocess,os
from pathlib import Path
from unittest.mock import patch
root=Path('C:/Users/郑曾波/Projects/revenue-forecast-w20-adoption')
for p in (root,root/'scripts',root/'tests'):sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
import test_w20_narrative_adoption_audit as t
from test_shared_reading_narrative_contract import projected_context
from test_recognition_bridge import forecast_document
from fix_hashes import apply_hash_fixes
from source_narrative_context import consume_narrative_input
from revenue_core import run_forecast
request,body,read_receipt=projected_context()
context=t.validate_narrative_response(request,body,read_receipt)
value=context.to_dict()
span=value['evidence_spans'][0]
parent=next(r for r in value['parent_source_refs'] if r['source_id']==span['source_id'])
data=forecast_document();data['as_of_date']=value['as_of_date'];data['sources'][0]['capture']['snapshot_sha256']=parent['content_sha256'];apply_hash_fixes(data)
with patch('source_narrative_context.read_narrative_context',return_value=context):
 linked,receipt=consume_narrative_input(data,request={'as_of_date':value['as_of_date']},bindings=[{'span_id':span['span_id'],'claim_id':'probe_projected','parameter_id':t.PARAMETER,'support_type':'rationale_support'}],source_id='filing',catalog_config=Path('isolated-not-opened.json'))
forecast=run_forecast(linked,mode='draft')
results={'projected_actual_parent_index':value['parent_source_refs'].index(parent)}
for name in ('normal','missing_hash','wrong_parent_hash'):
 r=copy.deepcopy(receipt)
 if name=='missing_hash':del r['dependencies'][0]['source_sha256']
 if name=='wrong_parent_hash':r['dependencies'][0]['source_sha256']=value['parent_source_refs'][0]['content_sha256']
 report=t.build(forecast,receipts=[r],contexts=[value])
 item=t.find(report,'span',span['span_id'])
 results[name]={'item':item,'diagnostics':report['diagnostics']}
out=Path(__file__).parent
bad=out/'invalid-deflate.json.gz';bad.write_bytes(bytes.fromhex('1f8b0800000000000003')+b'\x07'+b'\0'*8)
target=out/'should-not-exist.json'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
proc=subprocess.run([sys.executable,'-B','-X','utf8',str(root/'tools/narrative_adoption_audit/cli.py'),'--forecast',str(bad),'--output',str(target)],env=env,capture_output=True,text=True,timeout=15)
results['invalid_deflate_cli']={'exit':proc.returncode,'stderr':proc.stderr,'stdout':proc.stdout,'output_exists':target.exists(),'gzip_bytes_hex':bad.read_bytes().hex()}
bad.unlink()
assert not target.exists()
(out/'additional-probe-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:({'status':v['item']['status'],'codes':[d['code'] for d in v['diagnostics']]} if isinstance(v,dict) and 'item' in v else v) for k,v in results.items()},ensure_ascii=False))
