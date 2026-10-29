import sys, json, copy
from pathlib import Path
from unittest.mock import patch
root=Path('C:/Users/郑曾波/Projects/revenue-forecast-w20-adoption')
for p in (root,root/'scripts',root/'tests'):sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
import test_w20_narrative_adoption_audit as t
from source_narrative_context import consume_narrative_input
value,linked,receipt,forecast=t.real_chain()
context=t.validated('2')
table_span=next(s for s in value['evidence_spans'] if s['raw_text']=='Overseas | 1,240')
binding={'span_id':table_span['span_id'],'claim_id':'w20_cl','parameter_id':t.PARAMETER,'support_type':'rationale_support','citation_group_id':value['reading_context']['groups'][1]['group_id'],'citation_view':0}
with patch('source_narrative_context.read_narrative_context',return_value=context):
 other_input,other_receipt=consume_narrative_input(t.document(context),request={'as_of_date':value['as_of_date']},bindings=[binding],source_id='filing',catalog_config=Path('isolated-not-opened.json'))
report=t.build(forecast,receipts=[other_receipt],contexts=[value])
result={'scenario':'same source, source-validated table receipt belongs to different claim material than final CEO-claim forecast; same local claim/parameter IDs and same formula graph',
 'actual_forecast_claim':next(c for c in linked['evidence_claims'] if c['claim_id']=='w20_cl'),
 'different_real_consumed_claim':next(c for c in other_input['evidence_claims'] if c['claim_id']=='w20_cl'),
 'different_real_receipt':other_receipt,
 'reported_span':t.find(report,'span',table_span['span_id']),
 'diagnostics':report['diagnostics']}
Path(__file__).with_name('material-probe-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':result['reported_span']['status'],'actual_claim_excerpt':result['actual_forecast_claim']['excerpt'],'receipt_claim_excerpt':result['different_real_consumed_claim']['excerpt'],'diagnostics':report['diagnostics']},ensure_ascii=False))
