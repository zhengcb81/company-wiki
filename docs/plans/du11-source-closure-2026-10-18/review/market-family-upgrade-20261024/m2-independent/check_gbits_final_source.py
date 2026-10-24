"""Read real original once; use isolated in-memory selection and no model calls."""
from pathlib import Path
from hashlib import sha256
import json,io,zipfile,xml.etree.ElementTree as ET
from unit.test_narrative_select_handler import _payload,_context,FakeReader
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_replay import replay_narrative_evidence
from company_wiki.automation.narrative_model_runtime import build_model_request
from company_wiki.automation.models import HandlerOutcome
from company_wiki.document_understanding.summary_tasks import build_summary_task_plan
from company_wiki.document_understanding.source_cards import source_cards
from company_wiki.document_normalization.text import normalize_text
from run_final_review import tree,OUT,MODULES,imports
ORIGINAL=Path('C:/Users/郑曾波/Projects/company-wiki/companies/吉比特/raw/research/中泰-吉比特财报交流会0409.mp3-文稿-转写结果.docx')
EXPECTED='63777874f5956f37ed32f4839c170340af4f61ee7594b99423acc698968a158a'
before=tree();loaded=imports();raw=ORIGINAL.read_bytes();h=sha256(raw).hexdigest();assert h==EXPECTED
payload=_payload(raw,title='中泰-吉比特财报交流会0409',document_kind='investor_relations',language='zh',mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
result=NarrativeSelectHandler(reader=FakeReader(payload,raw),selector_version='0.9.0')(_context(payload,lambda:None))
assert result.outcome is HandlerOutcome.SUCCEEDED,result.error
s0=NarrativeSelectResult.from_dict(result.result)
s=NarrativeSelectResult.from_dict(json.loads(json.dumps(s0.to_dict())))
assert replay_narrative_evidence(raw,s)==len(s.evidence_spans)
request=build_model_request(s,reading_projection_version='reading-model-input/5')
model=json.loads(request.data_json);assert model['schema_version']=='narrative-model-request/6'
plan=build_summary_task_plan(s.evidence_spans,reading_context=s.reading_context,max_claims=40)
cards=list(source_cards(plan,{span.span_id:span for span in s.evidence_spans}))
w='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def visible(n):
 if n.tag==w+'t':return n.text or ''
 if n.tag in {w+'tab',w+'br',w+'cr'}:return ' '
 if n.tag in {w+'del',w+'moveFrom'}:return ''
 return ''.join(visible(c) for c in n)
with zipfile.ZipFile(io.BytesIO(raw)) as z:
 ps=ET.fromstring(z.read('word/document.xml')).findall(w+'body/'+w+'p')
text=[normalize_text(visible(p).strip()) for p in ps]
rows=[]
for span in s.evidence_spans:
 d=span.structured_value;locator=d.get('locator') or span.coordinates.locator()
 index=int(locator.rsplit(':',1)[1]);assert span.raw_text==text[index],(locator,span.raw_text,text[index])
 assert d['source_role']=='unknown'
 rows.append({'locator':locator,'text_sha256':sha256(span.raw_text.encode()).hexdigest(),'source_role':d['source_role'],'text_chars':len(span.raw_text)})
# The previously missed four source paragraphs must remain represented. Paragraph
# 16 carries an explicit unfinalized-plan caveat; preserve its raw ambiguity.
locators={r['locator'] for r in rows}
assert {'loc:v1/paragraph:'+str(i) for i in (5,6,16,89)}<=locators
assert text[16] in request.data_json
assert any(text[16] in (c.text or '') for c in cards)
after=tree();assert before==after
assert sha256(ORIGINAL.read_bytes()).hexdigest()==h
receipt={'status':'PASS_SOURCE_SEAM_ONLY','original_sha256':h,'original_unchanged':True,'source_before':before,'source_after':after,'source_unchanged':True,'imports':loaded,'selected_span_count':len(rows),'selected':rows,'model_schema':model['schema_version'],'model_request_sha256':sha256(request.data_json.encode()).hexdigest(),'model_request_chars':len(request.data_json),'source_card_count':len(cards),'critical_new_locators_5_6_16_89_retained':True,'paragraph16_caveat_in_model_and_card':True,'roles':['unknown'],'model_calls':0,'limits':'Real original bytes with isolated FakeReader only; no manifest, dates, filing provider or RF validation claimed. Old content gold remains a separate quality question. No source correction or translation.'}
(OUT/'real-gbits-final-source-seam.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in receipt.items() if k not in {'source_before','source_after','imports','selected'}},ensure_ascii=False,indent=2))

