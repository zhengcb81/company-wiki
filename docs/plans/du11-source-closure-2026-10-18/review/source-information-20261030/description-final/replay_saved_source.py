"""Saved native structure -> actual reading -> source cards; no parser/model IO."""
from pathlib import Path
from dataclasses import fields, is_dataclass
from collections.abc import Mapping
from enum import Enum
import gzip
import json
import time
import sys
from hashlib import sha256

from company_wiki.source_catalog.narrative_document import DocumentStructure, NarrativeUnit
from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan
from company_wiki.resource_budget import new_document_work_budget
from company_wiki.source_catalog.narrative_evidence import select_narrative_evidence
from company_wiki.document_understanding.summary_tasks import build_summary_task_plan
from company_wiki.document_understanding.source_cards import source_cards, source_task_admission

base = Path(__file__).parent
out = Path(sys.argv[1]) if len(sys.argv)>1 else Path('.planning/source-description-replay-new')
assert not out.exists(), 'Keep old receipts immutable'
out.mkdir()
raw = json.loads(gzip.decompress((base/'parsed-input.json.gz').read_bytes()))
raw['units'] = tuple(NarrativeUnit(**{**u,'coordinates':EvidenceCoordinates(**u['coordinates'])}) for u in raw['units'])
parsed = DocumentStructure(**raw)
original = Path('companies/万润股份/raw/research/万润股份：投资者关系活动记录表20260515.pdf')
assert sha256(original.read_bytes()).hexdigest()==parsed.source_sha256
budget = new_document_work_budget()
budget.charge(json.loads((base/'parse-receipt.json').read_text(encoding='utf-8'))['parse_work'])
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
old_path=base.parent.parent/'qa-closed-scope-20261030/real-selection.json.gz'
old=json.loads(gzip.decompress(old_path.read_bytes()))
before=cards_for(tuple(EvidenceSpan.from_dict(s) for s in old['evidence_spans']),old['reading_context'])
def compact(text): return ''.join(text.split())
admitted=[c for c in current if c['admission']['status']=='admitted']
supports=[' '.join(compact(t) for t in c['support']) for c in admitted]
# Frozen source checkpoints: observe what actually reaches SourceCard.support;
# no generated response or metadata is allowed to stand in for input recall.
checks={
    'sold_roster_and_300_compounds': any(all(t in s for t in ('光刻胶单体','300种化合物')) for s in supports),
    'subsidiary_customer_chain': any(all(t in s for t in ('九目化学主要产品','下游客户','显示面板生产企业')) for s in supports),
    'listing_receipt_application_and_conditional_resume': any(all(t in s for t in ('第二轮审核问询函','申请了中止审核','将申请恢复审核')) for s in supports),
    'reported_material_impact_denial': any(all(t in s for t in ('根据相应新闻报道','未对九目化学经营构成重大影响')) for s in supports),
    'demand_cause_preserved': any(all(t in s for t in ('沸石系列','下游需求减少')) for s in supports),
    'vc_denial_and_contact_not_approved_cooperation': any(all(t in s for t in ('现无生产VC','已经建立了联系','希望建立')) for s in supports),
    'capacity_plan_751': any(all(t in s for t in ('751吨/年','项目建成后')) for s in supports),
    'future_generic_rhetoric_not_admitted': not any('未来公司也会努力' in s for s in supports),
}
assert sha256(original.read_bytes()).hexdigest()==parsed.source_sha256
result={**timing,'source_sha256':parsed.source_sha256,'status':selected.status,
    'coverage_complete':selected.coverage_complete,'spans':len(selected.evidence_spans),
    'source_cards':current,'before':{'spans':len(old['evidence_spans']),'source_cards':before},
    'partial_not_full_recall':True,'source_checkpoints':checks,'open_checkpoints':[k for k,v in checks.items() if not v],
    'new_model_posts':0,'new_downloads':0,'pdf_parse_calls':0,
    'member_bytes_are_only_source_text_proxy_not_final_prompt_or_billed_cost':True}
(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({**timing,'spans':len(selected.evidence_spans),
    'tasks':len(current),'admitted':sum(c['admission']['status']=='admitted' for c in current),
    'raw_member_bytes':sum(c['raw_member_bytes'] for c in current),
    'before_tasks':len(before),'before_raw_member_bytes':sum(c['raw_member_bytes'] for c in before),
    'status':selected.status},ensure_ascii=False))
