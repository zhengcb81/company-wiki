"""Inspect frozen real support only; never rewrite the recorded model output."""
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

root = Path.cwd()
sys.path.insert(0, str(root / 'src'))
from company_wiki.document_understanding.assertion_frames import source_assertion_frames

work = root / '.planning/summary-quality-20261030'
out = work / 'assertion-frames-real-r2.json'
assert not out.exists()
live = work / 'real-fidelity-v1'
bundle_path = next(live.glob('*.bundle.json.gz'))
payload = gzip.decompress(bundle_path.read_bytes())
bundle = json.loads(payload)
ledger = root / '.planning/shared-reading-production/live/usage.jsonl'
ledger_sha = hashlib.sha256(ledger.read_bytes()).hexdigest()
owner = root / 'src/company_wiki/document_understanding/assertion_frames.py'
owner_sha = hashlib.sha256(owner.read_bytes()).hexdigest()
start = time.perf_counter()
index = {span['span_id']: span for span in bundle['evidence_spans']}
frames_by_span = {sid: source_assertion_frames(span['raw_text']) for sid, span in index.items()}
rows = []
for claim in bundle['summary']['draft']['claims']:
    if claim['claim_id'] not in ('t1-1', 't6-3', 't8-2'):
        continue
    rows.append({'claim_id': claim['claim_id'], 'source_frames': [
        {'span_id': sid, 'frames': [asdict(frame) for frame in frames_by_span[sid]]}
        for sid in claim['evidence_ids']]})

def frames_for(claim_id):
    return [frame for row in rows if row['claim_id'] == claim_id
            for group in row['source_frames'] for frame in group['frames']]

checks = {
    'current_ongoing_observed_not_future': any(
        frame['ongoing_activity'] and not frame['future_marker'] for frame in frames_for('t1-1')),
    'coordinated_wish_keeps_reporting_scope': any(
        frame['reporting_inherited'] and frame['reporting_prefix'] for frame in frames_for('t6-3')),
    'project_capacity_keeps_completion_condition': any(
        frame['quantity_basis'] == 'project_capacity_specification' and frame['project_condition']
        for frame in frames_for('t8-2')),
}
assert owner_sha == hashlib.sha256(owner.read_bytes()).hexdigest()
assert ledger_sha == hashlib.sha256(ledger.read_bytes()).hexdigest()
result = {'status': 'PASS_SOURCE_HINTS_ONLY_NOT_SUMMARY_FIX' if all(checks.values()) else 'FAIL',
          'checks': checks, 'rows': rows, 'source_spans_examined': len(index),
          'elapsed_seconds': round(time.perf_counter() - start, 6),
          'owner_sha256': owner_sha, 'artifact_body_sha256': hashlib.sha256(payload).hexdigest(),
          'model_posts': 0, 'pdf_reparses': 0, 'ledger_unchanged': True,
          'recorded_summary_text_modality_unchanged': True,
          'production_wiring': 'NOT_IMPLEMENTED', 'actual_rf_forecast_adoption': 'OPEN'}
out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({key: value for key, value in result.items() if key != 'rows'}, ensure_ascii=False))
assert all(checks.values()), checks
