"""Read-only W08 contract counterexamples; all run inputs live in fresh temp."""
from pathlib import Path
import importlib.util
import json
import math
import sys
import tempfile

AUTHOR = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w08/audit-evidence')
TEST = AUTHOR / 'tests/test_w08_review_evidence.py'
spec = importlib.util.spec_from_file_location('independent_w08_fixtures', TEST)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def sample(name, change, view):
    with tempfile.TemporaryDirectory(prefix='w08-independent-review-', dir=Path(__file__).parent) as temp:
        builder = module.PackageBuilder(temp)
        run = builder.build()
        change(builder, run)
        node = builder.reconcile(run)
        return {'case': name, 'actual': view(node)}

def events_change(run, function):
    path = run / 'roles/storage/events.jsonl'
    records = [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines()]
    function(records)
    path.write_text(''.join(json.dumps(r) + '\n' for r in records), encoding='utf-8')

def report_change(builder, run):
    path = run / 'reports/attempt-1/storage.json'
    payload = json.loads(path.read_text(encoding='utf-8'))
    payload.update(run_id='old-run', role='analyst', review_attempt='old-attempt')
    path.write_text(json.dumps(payload), encoding='utf-8')

results = []
results.append(sample('mismatched_capture_ids',
    lambda b, r: events_change(r, lambda rows: rows[1]['data'].update(capture_id='other-capture')),
    lambda n: {'storage_events': n['events']['storage'], 'unchecked': n['unchecked']}))
results.append(sample('wrong_role_events',
    lambda b, r: events_change(r, lambda rows: [x.update(role='analyst') for x in rows]),
    lambda n: {'storage_events': n['events']['storage'], 'unchecked': n['unchecked']}))
results.append(sample('stale_current_report_contents', report_change,
    lambda n: {'storage_report': n['role_reports']['storage'], 'unchecked': n['unchecked'],
               'diagnostics': n['diagnostics']}))
results.append(sample('unresolved_free_text_numeric',
    lambda b, r: b.payload['numeric_coverage']['verified'][0]['recompute'].update(locator='invented result paragraph'),
    lambda n: {'numeric': n['numeric_reconciliation'], 'row': next(x for x in n['rows'] if x['row_id']=='V1')}))
results.append(sample('same_locator_two_value_ids',
    lambda b, r: b.payload['numeric_coverage']['verified'][1].update(recompute=dict(b.payload['numeric_coverage']['verified'][0]['recompute'])),
    lambda n: {'numeric': n['numeric_reconciliation']}))

limits = {}
for key, value in [('max_seconds', float('nan')), ('max_seconds', float('inf')), ('max_files', 999999), ('max_files', 0.5)]:
    try:
        limits[f'{key}:{value}'] = module.EVIDENCE.normalize_limits({key:value})
    except Exception as exc:
        limits[f'{key}:{value}'] = {'error': str(exc)}
results.append({'case': 'limits_normalization', 'actual': limits})

with tempfile.TemporaryDirectory(prefix='w08-independent-review-', dir=Path(__file__).parent) as temp:
    root = Path(temp)
    (root/'deep.json').write_text('['*1500+'0'+']'*1500, encoding='utf-8')
    reader = module.EVIDENCE.EvidenceReader(root)
    try:
        actual = module.EVIDENCE.inspect_reference(reader, {'artifact':'deep.json','locator':'/0'})
    except Exception as exc:
        actual = {'raised':type(exc).__name__, 'detail':str(exc)}
    results.append({'case':'deep_json_row_isolation', 'actual':actual})

with tempfile.TemporaryDirectory(prefix='w08-independent-review-', dir=Path(__file__).parent) as temp:
    root = Path(temp)
    path = root/'growing.txt'
    path.write_bytes(b'x')
    reader = module.EVIDENCE.EvidenceReader(root, limits={'max_file_bytes':4, 'max_total_bytes':8})
    class GrowingPath:
        def stat(self): return path.stat()
        def read_bytes(self):
            path.write_bytes(b'x'*40)
            return path.read_bytes()
    record = reader.read_bytes(GrowingPath())
    results.append({'case':'file_growth_between_stat_and_read', 'actual': {
        'record_bytes':record['bytes'], 'error':record['error'], 'budget':reader.budget.snapshot()}})

def portable(value):
    if isinstance(value, float) and not math.isfinite(value): return str(value)
    if isinstance(value, dict): return {k: portable(v) for k,v in value.items()}
    if isinstance(value, list): return [portable(v) for v in value]
    return value
out = Path(__file__).with_name('reproduction.json')
out.write_text(json.dumps(portable(results), ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
print(json.dumps(portable(results), ensure_ascii=False, indent=2, allow_nan=False))
