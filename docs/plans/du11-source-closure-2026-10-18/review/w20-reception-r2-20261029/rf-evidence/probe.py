import sys, json, copy, hashlib, gzip
from pathlib import Path
sys.dont_write_bytecode=True
root=Path('C:/Users/郑曾波/Projects/revenue-forecast-w20-adoption')
for p in (root,root/'scripts',root/'tests'): sys.path.insert(0,str(p))
import test_w20_narrative_adoption_audit as t
from tools.narrative_adoption_audit import cli, audit
from unittest.mock import patch
from source_narrative_context import consume_narrative_input
from revenue_core import run_forecast
out=Path(__file__).parent
results={}
value,linked,receipt,forecast=t.real_chain()
sid=t.span_id(value,'answer')
results['baseline']=t.find(t.build(forecast,receipts=[receipt],contexts=[value]),'span',sid)
# A genuine source-B wire is submitted with a receipt pointing at source-A's
# captured SHA and local claim/parameter. The supplied span ID is B's canonical
# urn; the entire received wire is unchanged and was publicly validated.
other,_=t._second_source_context('other-summary')
foreign_sid=t.span_id(other,'answer', t._second_source_context('other-summary')[1])
forged=copy.deepcopy(receipt)
forged['dependencies'][0]['span_id']=foreign_sid
report=t.build(forecast,receipts=[forged],contexts=[other])
results['foreign_span_with_existing_capture']={'span':t.find(report,'span',foreign_sid),'diagnostics':report['diagnostics'],'dependency':forged['dependencies'][0], 'wire_source':other['source_ref']}
# An unrelated claim/parameter pair is claimed without an actual linkage.
forged=copy.deepcopy(receipt)
forged['dependencies'][0]['source_id']='urn:fake:source'
report=t.build(forecast,receipts=[forged],contexts=[value])
results['wrong_explicit_source_id']={'span':t.find(report,'span',sid),'diagnostics':report['diagnostics']}
# Two valid bindings of the same canonical span into distinct years.
context=t.validated('2')
data=t.document(context)
bindings=[t.binding(value,'answer',claim_id='first',parameter_id='0_base_2026'),
          t.binding(value,'answer',claim_id='second',parameter_id='0_base_2027')]
with patch('source_narrative_context.read_narrative_context',return_value=context):
 two_linked,two_receipt=consume_narrative_input(data,request={'as_of_date':value['as_of_date']},bindings=bindings,source_id='filing',catalog_config=Path('isolated-not-opened.json'))
two_forecast=run_forecast(two_linked,mode='draft')
two_report=t.build(two_forecast,receipts=[two_receipt],contexts=[value])
results['two_valid_bindings']={'span':t.find(two_report,'span',sid),'diagnostics':two_report['diagnostics'],'dependencies':two_receipt['dependencies'],'claims':[t.find(two_report,'claim',c) for c in ('first','second')]}
# Explicit compressed-byte bound must also bound decompressed payload.
payload=b' '*100000
compressed=out/'compressed.json.gz'
compressed.write_bytes(gzip.compress(payload))
try:
 result=cli._read_bytes(compressed,1024)
 results['gzip_bound']={'physical_bytes':compressed.stat().st_size,'limit':1024,'returned_bytes':len(result),'rejected':False}
except Exception as e:
 results['gzip_bound']={'rejected':True,'error':str(e)}
compressed.unlink()
json.dump(results,(out/'probe-results.json').open('w',encoding='utf-8'),ensure_ascii=False,indent=2)
print(json.dumps({k:({'status':v['span']['status'],'diagnostic_codes':[d['code'] for d in v['diagnostics']]} if isinstance(v,dict) and 'span' in v else v) for k,v in results.items()},ensure_ascii=False))
