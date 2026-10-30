"""Saved native structure -> actual reading -> source cards; no parser/model IO."""
from pathlib import Path
from dataclasses import fields, is_dataclass
from collections.abc import Mapping
from enum import Enum
import gzip
import json
import time

from company_wiki.source_catalog.narrative_document import DocumentStructure, NarrativeUnit
from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan
from company_wiki.resource_budget import new_document_work_budget
from company_wiki.source_catalog.narrative_evidence import select_narrative_evidence
from company_wiki.document_understanding.summary_tasks import build_summary_task_plan
from company_wiki.document_understanding.source_cards import source_cards, source_task_admission

base = Path('.planning/source-information-20261029/cn-ir-native-v4')
out = Path(__file__).parent / 'real-frozen'
assert not out.exists(), 'Keep old receipts immutable'
out.mkdir()
raw = json.loads(gzip.decompress((base/'parsed.json.gz').read_bytes()))
raw['units'] = tuple(NarrativeUnit(**{**u,'coordinates':EvidenceCoordinates(**u['coordinates'])}) for u in raw['units'])
parsed = DocumentStructure(**raw)
budget = new_document_work_budget()
budget.charge(json.loads((base/'result.json').read_text(encoding='utf-8'))['parse_work'])
tick=time.monotonic()
selected=select_narrative_evidence(parsed,title='万润股份：投资者关系活动记录表20260515.pdf',
    existing_kind='investor_relations',selector_version='0.9.0',work_budget=budget)

def plain(x):
    if is_dataclass(x): return {f.name:plain(getattr(x,f.name)) for f in fields(x)}
    if isinstance(x,Enum): return x.value
    if isinstance(x,Mapping): return {str(k):plain(v) for k,v in x.items()}
    if isinstance(x,(tuple,list,set,frozenset)): return [plain(v) for v in x]
    return x

timing={'seconds':round(time.monotonic()-tick,3),'work':budget.used}
snapshot=plain(selected)
(out/'selection.json.gz').write_bytes(gzip.compress(json.dumps(snapshot,ensure_ascii=False,
    separators=(',',':')).encode(),mtime=0))

def cards_for(spans,context):
    plan=build_summary_task_plan(spans,reading_context=context,max_claims=64)
    by_id={s.span_id:s for s in spans}
    cards=tuple(source_cards(plan,by_id))
    admission=source_task_admission(cards)
    return [{'task':card.task.to_binding(),'admission':admission[card.task.key],
        'support':[s.raw_text for s in card.support],
        'context':[by_id[eid].raw_text for eid in card.task.context_ids],
        'raw_member_bytes':sum(len((by_id[eid].raw_text or '').encode()) for eid in card.task.member_ids)}
        for card in cards]

current=cards_for(selected.evidence_spans,selected.reading_context)
old_path=Path('.planning/source-information-20261030/saved-replay-release/selection.json.gz')
old=json.loads(gzip.decompress(old_path.read_bytes()))
before=cards_for(tuple(EvidenceSpan.from_dict(s) for s in old['evidence_spans']),old['reading_context'])
result={**timing,'source_sha256':parsed.source_sha256,'status':selected.status,
    'coverage_complete':selected.coverage_complete,'spans':len(selected.evidence_spans),
    'source_cards':current,'before':{'spans':len(old['evidence_spans']),'source_cards':before},
    'partial_not_full_recall':True,'open_checkpoints':['offering roster/300 compounds','subsidiary product/client chain','listing inquiry/suspension/restart'],
    'new_model_posts':0,'new_downloads':0,'pdf_parse_calls':0,
    'member_bytes_are_only_source_text_proxy_not_final_prompt_or_billed_cost':True}
(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({**timing,'spans':len(selected.evidence_spans),
    'tasks':len(current),'admitted':sum(c['admission']['status']=='admitted' for c in current),
    'raw_member_bytes':sum(c['raw_member_bytes'] for c in current),
    'before_tasks':len(before),'before_raw_member_bytes':sum(c['raw_member_bytes'] for c in before),
    'status':selected.status},ensure_ascii=False))
