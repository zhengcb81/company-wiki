"""One offline production-source replay; compact observations, no raw copies."""
from pathlib import Path
import collections
import gzip
import hashlib
import json
import os
import socket
import sys
import tempfile
import time
import traceback
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
MOTHER = Path('C:/Users/郑曾波/Projects/company-wiki')
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['COMPANY_WIKI_NETWORK'] = 'blocked'
os.environ['COMPANY_WIKI_REAL_LLM'] = '0'
sys.dont_write_bytecode = True


def offline(*args, **kwargs):
    raise RuntimeError('OFFLINE_SOURCE_PROBE_NO_NETWORK')


socket.socket.connect = offline
socket.create_connection = offline

from company_wiki import resource_budget
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.automation.narrative_contracts import (
    SourceRevisionEventPayload, NarrativeSelectResult, PromptReviewValue,
)
from company_wiki.automation.narrative_model_extractive import compile_extractive_plan
from company_wiki.automation.models import canonical_json
from company_wiki.source_contract import source_id_for_sha256
from company_wiki.source_catalog.narrative_language import narrative_language_family
from tools.document_understanding_benchmark.closed_group_support import score_facts, score_claim_facts


def sha(data):
    return hashlib.sha256(data).hexdigest()


MODULES = [
    'company_wiki.automation.narrative_select',
    'company_wiki.source_catalog.narrative_evidence',
    'company_wiki.source_catalog.narrative_reading',
    'company_wiki.source_catalog.narrative_finalize',
    'company_wiki.source_catalog.narrative_document',
    'company_wiki.source_catalog.narrative_business_policy',
    'company_wiki.source_catalog.narrative_source_purpose',
    'company_wiki.source_catalog.narrative_operating_relations',
    'company_wiki.document_understanding.source_cards',
    'company_wiki.document_understanding.summary_tasks',
    'company_wiki.document_understanding.native_table_bridge',
    'company_wiki.document_understanding.narrative_continuity',
    'company_wiki.document_understanding.decision_inventory',
    'company_wiki.automation.narrative_model_extractive',
    'company_wiki.document_understanding.operating_states.product_reference',
    'company_wiki.document_understanding.operating_states.relations',
    'company_wiki.source_catalog.narrative_antecedent',
]


def bindings():
    result = []
    for name in MODULES:
        module = __import__(name, fromlist=[''])
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(ROOT / 'src'), (name, str(path))
        result.append({'module': name, 'path': str(path), 'sha256': sha(path.read_bytes())})
    return result


def compact_span(span):
    return {'id': span.span_id, 'locator': span.coordinates.locator(),
            'text_sha256': sha(span.raw_text.encode()), 'chars': len(span.raw_text),
            'prefix': span.raw_text[:100], 'suffix': span.raw_text[-55:],
            'flags': list(span.quality_flags),
            'reading_priority': span.structured_value.get('reading_priority'),
            'reading_value_band': span.structured_value.get('reading_value_band'),
            'reading_score': span.structured_value.get('reading_score')}


def score_claims(required, selected, claims):
    supported = {fact['id']: [] for fact in required}
    for claim in claims:
        rows = score_claim_facts([{**fact, 'claim_id': claim['claim_id']} for fact in required],
            claims=[claim], evidence_spans=selected.evidence_spans,
            reading_context=selected.reading_context, source_id=selected.source_ref.source_id)
        for row in rows:
            if row['supported']:
                supported[row['id']].append(claim['claim_id'])
    return [{'id': fact['id'], 'supported': bool(supported[fact['id']]),
             'claim_ids': supported[fact['id']]} for fact in required]


def incident_observation(sample, selected, claims):
    folder = MOTHER / '.planning/shared-reading-production/du11' / {
        'cn-h1': 'live-v5-cn-a8eef273-20261018',
        'hk-annual': 'live-v5-hk-a8eef273-20261018',
        'us-10k': 'live-v5-us-a8eef273-20261018',
    }[sample]
    bundle_files = list(folder.glob('*.bundle.json.gz'))
    if len(bundle_files) != 1:
        return {'status': 'OLD_BUNDLE_NOT_UNIQUE', 'count': len(bundle_files)}
    old = json.loads(gzip.decompress(bundle_files[0].read_bytes()))
    bad = {'cn-h1': ['t3', 't4', 't6', 't9', 't32', 't34', 't64'],
           'hk-annual': ['t7', 't8', 't36', 't37', 't38', 't52', 't55'],
           'us-10k': ['t3', 't22', 't26', 't39']}[sample]
    known_old = {span['span_id']: span for span in old['evidence_spans']}
    normalize = lambda text: ''.join(text.split())
    result = []
    for task in bad:
        original = next((c for c in old['summary']['draft']['claims']
                         if c['claim_id'] == task + '-source'), None)
        if original is None:
            continue
        # The largest actual support is an incident marker, not an eligibility
        # rule. A richer new mixed card containing it still needs human review.
        body = max((known_old[sid] for sid in original['evidence_ids']), key=lambda s: len(s['raw_text']))
        needle = normalize(body['raw_text'])
        hits = [c['claim_id'] for c in claims if needle and needle in normalize(c['text'])]
        selected_hits = [s for s in selected.evidence_spans if needle and needle in normalize(s.raw_text)]
        result.append({'old_task': task, 'old_body_text_sha256': sha(body['raw_text'].encode()),
                       'selected_matches': len(selected_hits), 'new_claim_ids': hits,
                       'source_sample': compact_span(selected_hits[0]) if selected_hits else None,
                       'scope': 'literal_incident_marker_presence_not_general_semantic_judgment'})
    return result


def run(sample):
    path = Path(sample['original'])
    stat_before = path.stat()
    data = path.read_bytes()
    source_sha = sha(data)
    assert source_sha == sample['fingerprint']['sha256']
    gold_path = Path(sample['gold'])
    gold_bytes = gold_path.read_bytes()
    gold = json.loads(gold_bytes)
    assert gold['source_sha256'] == source_sha
    required = [f for f in gold['facts'] if f.get('target_kind') == 'required_business']
    # The captured production DTO is the actual source-language/title context.
    # Gold is an oracle only; its annotation language is not source metadata.
    live_folder = MOTHER / '.planning/shared-reading-production/du11' / {
        'cn-h1': 'live-v5-cn-a8eef273-20261018',
        'hk-annual': 'live-v5-hk-a8eef273-20261018',
        'us-10k': 'live-v5-us-a8eef273-20261018',
    }[sample['sample_id']]
    previous_bundle = json.loads(gzip.decompress(next(live_folder.glob('*.bundle.json.gz')).read_bytes()))
    assert previous_bundle['source_ref']['content_sha256'] == source_sha
    actual_metadata = previous_bundle['source_metadata']
    payload = SourceRevisionEventPayload.from_dict({
        'schema_version': 'source-revision-event/2.0',
        'source_ref': {'schema_version': '2.0', 'document_id': 'offline-probe-' + sample['sample_id'],
            'source_id': source_id_for_sha256(source_sha), 'content_sha256': source_sha,
            'byte_size': len(data), 'mime_type': sample['mime_type']},
        'expected_read_policy_sha256': source_sha,
        'source_metadata': actual_metadata,
    })
    record = {'sample': sample['sample_id'], 'source_sha256': source_sha, 'source_bytes': len(data),
              'gold_sha256': sha(gold_bytes), 'actual_source_metadata': actual_metadata,
              'status': 'OPEN', 'scope': 'offline_engineering_not_final_content_acceptance'}
    started = time.monotonic()
    accounts = []
    factory = resource_budget.new_document_work_budget
    def observe_factory():
        account = factory()
        assert account.max_work_units == 16_000_000
        accounts.append(account)
        return account
    resource_budget.new_document_work_budget = observe_factory
    try:
        handler = NarrativeSelectHandler(reader=None, selector_version='0.9.0')
        work = handler._select(payload, data, SimpleNamespace(checkpoint=lambda: None))
        assert len(accounts) == 1, len(accounts)
        parse_select_seconds = time.monotonic() - started
        selected = NarrativeSelectResult.from_dict(handler._result_dict(payload,
            PromptReviewValue('not_reviewed', None, None, None, None), work, selector_version='0.9.0'))
        handler._verify_selected_material(work.parsed, work.package)
        assert len(selected.evidence_spans) <= 96
        assert sum(len(span.raw_text) for span in selected.evidence_spans) <= 48_000
        plan = compile_extractive_plan(selected)
        assert len(canonical_json(plan.draft).encode()) <= 56 * 1024
        assert len(canonical_json(plan.execution).encode()) <= 32 * 1024
        known = {span.span_id: span for span in selected.evidence_spans}
        for claim in plan.draft['claims']:
            assert claim['text'] == '\n'.join(known[sid].raw_text for sid in claim['evidence_ids'])
        ambiguous = {sid for sid, span in known.items() if 'table_structure_ambiguous' in span.quality_flags}
        assert not any(ambiguous.intersection(claim['evidence_ids']) for claim in plan.draft['claims'])
        facts = score_facts(required, evidence_spans=selected.evidence_spans,
            reading_context=selected.reading_context, source_id=selected.source_ref.source_id)
        canonical_facts = score_claims(required, selected, plan.draft['claims'])
        record.update(status='ENGINEERING_PASS_CONTENT_OPEN', parse_select_seconds=round(parse_select_seconds, 3),
            pages=work.parsed.page_count, pages_read=work.parsed.pages_read, parsed_units=len(work.parsed.units),
            source_errors=list(work.parsed.errors), source_coverage_complete=work.parsed.coverage_complete,
            selection_status=work.package.status, selected_count=len(selected.evidence_spans),
            selected_chars=sum(len(s.raw_text) for s in selected.evidence_spans),
            candidate_count=work.package.candidate_count, omitted_count=work.package.omitted_candidate_count,
            actual_work={'used': accounts[0].used, 'limit': accounts[0].max_work_units, 'exhausted': accounts[0].exhausted},
            draft_bytes=len(canonical_json(plan.draft).encode()),
            tasks=len(plan.execution['tasks']), claims=len(plan.draft['claims']),
            dispositions=dict(collections.Counter(row['source_disposition'] for row in plan.execution['tasks'])),
            selected_gold=facts, canonical_gold=canonical_facts,
            selected_required=sum(f['supported'] for f in facts),
            canonical_required=sum(f['supported'] for f in canonical_facts), required_total=len(required),
            ambiguous_raw_evidence_count=len(ambiguous), ambiguous_summary_support_count=0,
            ambiguous_samples=[compact_span(known[sid]) for sid in sorted(ambiguous)[:3]],
            exact_source_material_verified=True, canonical_claim_text_unchanged=True,
            source_priority_complete_count=sum(all(k in span.structured_value for k in
                ('reading_priority', 'reading_value_band', 'reading_score')) for span in selected.evidence_spans),
            incident_markers=incident_observation(sample['sample_id'], selected, plan.draft['claims']),
            deferral_reasons=dict(collections.Counter(str(row.get('reason')) for row in
                (selected.reading_context or {}).get('deferred', ()))),
        )
        if record['canonical_required'] < record['required_total']:
            record['status'] = 'ENGINEERING_PASS_REQUIRED_RECALL_FAIL_CONTENT_OPEN'
    except Exception as exc:
        record.update(status='FAIL', error_type=type(exc).__name__, error=str(exc)[:500],
                      traceback=traceback.format_exc(limit=5))
    finally:
        resource_budget.new_document_work_budget = factory
        record['actual_work_accounts'] = [{'used': a.used, 'limit': a.max_work_units,
                                           'exhausted': a.exhausted} for a in accounts]
        record['seconds'] = round(time.monotonic() - started, 3)
        after = path.stat()
        record['original_unchanged'] = (after.st_size == stat_before.st_size
            and after.st_mtime_ns == stat_before.st_mtime_ns and sha(path.read_bytes()) == source_sha)
        record['gold_unchanged'] = sha(gold_path.read_bytes()) == sha(gold_bytes)
        record['api_calls'] = 0
        record['raw_copies'] = 0
        (OUT / (sample['sample_id'] + '.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({k: record.get(k) for k in ('sample', 'status', 'seconds', 'selected_count',
            'claims', 'selected_required', 'canonical_required', 'required_total', 'actual_work_accounts',
            'original_unchanged', 'error')}, ensure_ascii=False), flush=True)
    return record


if __name__ == '__main__':
    initial = bindings()
    (OUT/('source-before-' + '-'.join(sys.argv[1:] or ['all']) + '.json')).write_text(json.dumps(initial, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    meta = MOTHER / '.planning/shared-reading-production/du11/metadata-registered-source-facts-20261017.json'
    samples = json.loads(meta.read_text(encoding='utf-8'))['samples']
    records = []
    with tempfile.TemporaryDirectory(prefix='du11-source-probe-') as temporary:
        owned_temp = Path(temporary)
        assert owned_temp.resolve().parent == Path(tempfile.gettempdir()).resolve()
        assert list(owned_temp.iterdir()) == []
        for sample in samples:
            if len(sys.argv) == 1 or sample['sample_id'] in sys.argv[1:]:
                records.append(run(sample))
        assert list(owned_temp.iterdir()) == []
    final = bindings()
    assert initial == final, 'SOURCE_CHANGED_DURING_PROBE'
    receipt = {'schema_version': 'du11-real-source-offline-probe/1', 'source_bindings': initial,
        'source_unchanged_during_probe': True, 'api_calls': 0, 'raw_copies': 0,
        'owned_temp_removed': not owned_temp.exists(), 'metadata_sha256': sha(meta.read_bytes()),
        'samples': [{'sample': r['sample'], 'status': r['status']} for r in records],
        'limits': {'work': 16_000_000, 'spans': 96, 'characters': 48_000, 'draft_bytes': 56*1024},
        'content_acceptance': 'OPEN; engineering/source-anchor observations are not final semantic or provider C acceptance'}
    (OUT/'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
