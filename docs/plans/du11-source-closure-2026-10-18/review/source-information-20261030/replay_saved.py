"""Reuse one saved native snapshot: no document IO, parsing or provider calls."""
from pathlib import Path
import gzip
import json
import time
import sys
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from company_wiki.source_catalog.narrative_document import NarrativeUnit, DocumentStructure
from company_wiki.source_contract import EvidenceCoordinates
from company_wiki.source_catalog.narrative_evidence import select_narrative_evidence
from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
from company_wiki.resource_budget import new_document_work_budget
from unit.du11_production.test_source_information_binding import observed_use

base = Path('.planning/source-information-20261029/cn-ir-native-v4')
out = Path(__file__).parent / (sys.argv[1] if len(sys.argv) == 2 else 'saved-replay-final')
out.mkdir(exist_ok=True)
raw = json.loads(gzip.decompress((base / 'parsed.json.gz').read_bytes()))
raw['units'] = tuple(NarrativeUnit(**{**u, 'coordinates': EvidenceCoordinates(**u['coordinates'])})
                     for u in raw['units'])
parsed = DocumentStructure(**raw)

def plain(value):
    if is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [plain(v) for v in value]
    return value

snapshot = out / 'selection.json.gz'
if snapshot.exists():
    selected_plain = json.loads(gzip.decompress(snapshot.read_bytes()))
    timing = {'seconds': None, 'work': None,
              'note': 'Selection captured before diagnostic AttributeError(text/raw_text); reused without rerun.'}
else:
    budget = new_document_work_budget()
    budget.charge(json.loads((base / 'result.json').read_text(encoding='utf-8'))['parse_work'])
    tick = time.monotonic()
    selected = select_narrative_evidence(parsed, title='万润股份：投资者关系活动记录表20260515.pdf',
        existing_kind='investor_relations', selector_version='0.9.0', work_budget=budget)
    selected_plain = plain(selected)
    snapshot.write_bytes(gzip.compress(json.dumps(selected_plain,
        ensure_ascii=False, separators=(',', ':')).encode(), mtime=0))
    timing = {'seconds': round(time.monotonic() - tick, 3), 'work': budget.used}
    (out / 'timing.json').write_text(json.dumps(timing), encoding='utf-8')
result = {**timing, 'status': selected_plain['status'],
          'coverage_complete': selected_plain['coverage_complete'],
          'spans': [{'page': s['coordinates']['page_number'], 'text': s['raw_text'],
                     'role': s['structured_value'].get('source_role')} for s in selected_plain['evidence_spans']]}
observations = []
for unit in parsed.units:
    if unit.unit_id.endswith(('0af71b078ebaa7425962f65aeb74a0352eeab0b68a7404729be53aa7bf84a6da',
                              'bd75a8c377fefb5f82492bb8191c62d815aa2dae2233cdb3e077107a2dc0b087')):
        # Same production owner, one isolated source unit; no synthetic text.
        session = SourceOperatingSession({unit.unit_id: unit}, work_budget=new_document_work_budget())
        observations.append({'unit_id': unit.unit_id, 'text': unit.raw_text,
            'use': observed_use(session, unit.unit_id),
            'bindings': session.engine.relation_bindings(unit.unit_id),
            'unknown_argument': session.engine.unknown_argument(unit.unit_id),
            'relations': session.relations(unit.unit_id)})
result['isolated_owners'] = observations
(out / 'result.json').write_text(json.dumps(plain(result), ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': result['status'], 'spans': len(result['spans']),
    'coverage_complete': result['coverage_complete'], 'seconds': result['seconds'],
    'work': result['work'], 'owners': len(observations)}, ensure_ascii=False))
