"""Captured native units -> current selector -> source cards, zero PDF/LLM IO."""
from pathlib import Path
from dataclasses import fields, is_dataclass
from collections.abc import Mapping
from enum import Enum
from hashlib import sha256
import gzip, json, time
import sys
sys.path.insert(0,str(Path.cwd()))

from company_wiki.source_catalog.narrative_document import DocumentStructure, NarrativeUnit
from company_wiki.source_contract import EvidenceCoordinates
from company_wiki.resource_budget import new_document_work_budget
from company_wiki.source_catalog.narrative_evidence import select_narrative_evidence
from company_wiki.document_understanding.summary_tasks import build_summary_task_plan
from company_wiki.document_understanding.source_cards import source_cards, source_task_admission
from tools.document_understanding_benchmark.closed_group_support import score_facts
from tools.document_understanding_benchmark.phase_c_observer import _oracle_reading_context

work=Path('.planning/summary-quality-20261030')
out=work/'source-scope-real-v2'
assert not out.exists()
out.mkdir()
base=Path('.planning/source-description-20261030/qa-range-real-v1')
raw=json.loads(gzip.decompress((base/'parsed.json.gz').read_bytes()))
raw['units']=tuple(NarrativeUnit(**{**u,'coordinates':EvidenceCoordinates(**u['coordinates'])}) for u in raw['units'])
parsed=DocumentStructure(**raw)
original=Path('companies/万润股份/raw/research/万润股份：投资者关系活动记录表20260515.pdf')
before=(sha256(original.read_bytes()).hexdigest(),original.stat().st_mtime_ns)
assert before[0]==parsed.source_sha256
budget=new_document_work_budget()
tick=time.monotonic()
selected=select_narrative_evidence(parsed,title=original.name,existing_kind='investor_relations',selector_version='0.9.0',work_budget=budget)
plan=build_summary_task_plan(selected.evidence_spans,reading_context=selected.reading_context,max_claims=20)
cards=tuple(source_cards(plan,{s.span_id:s for s in selected.evidence_spans}))
admission=source_task_admission(cards)
rows=[{'task_key':card.task.key,'support':[s.raw_text for s in card.support],'admission':admission[card.task.key],'reading_hint':card.reading_hint()} for card in cards]
chain=[row for row in rows if any('下游客户' in text and 'OLED' in text for text in row['support'])]
roster=[row for row in rows if any('已销售' in text and '300' in text for text in row['support'])]
assert chain and roster
assert all(row['reading_hint']['value_band']=='meaningful_fact' and row['admission']['status']=='admitted' for row in chain+roster)
gold=json.loads(Path('.planning/source-description-20261030/cn-ir-development-gold-v3.json').read_text('utf-8'))
scores=score_facts(gold['facts'],evidence_spans=selected.evidence_spans,reading_context=_oracle_reading_context(selected.reading_context),source_id=parsed.source_id)
assert all(score['supported'] for score in scores)
assert before==(sha256(original.read_bytes()).hexdigest(),original.stat().st_mtime_ns)
def plain(v):
    if is_dataclass(v): return {f.name:plain(getattr(v,f.name)) for f in fields(v)}
    if isinstance(v,Enum): return v.value
    if isinstance(v,Mapping): return {k:plain(x) for k,x in v.items()}
    if isinstance(v,(tuple,list,set,frozenset)): return [plain(x) for x in v]
    return v
(out/'selection.json.gz').write_bytes(gzip.compress(json.dumps(plain(selected),ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
receipt={'status':'PASS','scope':'current selection/source cards on captured real native; not new PDF replay, summary or forecast','seconds':round(time.monotonic()-tick,3),'source_sha256':before[0],'selected':len(selected.evidence_spans),'source_cards':rows,'business_input_scores':scores,'work':budget.used,'new_pdf_parses':0,'new_model_posts':0,'downloads':0,'original_unchanged':True,'selection_status':selected.status,'full_document_coverage_complete':selected.coverage_complete}
(out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:receipt[key] for key in ('status','seconds','selected','work','selection_status','full_document_coverage_complete')},ensure_ascii=False))
