"""Independent bounded RF temporal replay. Original probe builders/expectations unchanged."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
OUT = Path(__file__).resolve().parent
INTAKE = OUT.parent / 'intake'
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]

# Rebind only the product tree path; the fixed original builders and expectation
# strings below run without changes. Original source and FAIL outputs remain intact.
source = (INTAKE / 'probe_dated_flow.py').read_text(encoding='utf-8')
old = 'LEAF = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow")'
assert source.count(old) == 1
ns = {'__name__': 'original_probe_builders_replayed', '__file__': str(INTAKE / 'probe_dated_flow.py')}
exec(compile(source.replace(old, 'LEAF = Path("' + ROOT.as_posix() + '")'), str(INTAKE / 'probe_dated_flow.py'), 'exec'), ns)
run_forecast = ns['run_forecast']
validate_document = ns['validate_document']
window, parameter = ns['add_window_parameter'], ns['parameter']

cases = [
    ('valid_post_control_bridge', ns['valid_document'], 'accept', 'unchanged_original'),
    ('annual_alias_of_partial_flow', ns['annual_alias'], 'reject', 'unchanged_original'),
    ('rationale_cannot_move_2026_amount_to_2027', ns['outside_window'], 'reject', 'unchanged_original'),
    ('same_perimeter_h1_plus_own_q2', ns['overlap'], 'reject', 'unchanged_original'),
    ('negative_disposal_window_flow', ns['negative_disposal'], 'accept', 'unchanged_original'),
]

def stock_as_annual():
    data = ns['valid_document']()
    window(data, 'closing_stock', 20.0, None, None, 2026, time_basis='point_in_time', definition='Closing receivables stock')
    parameter(data, 'closing_stock')['dimension'] = 'monetary_balance'
    for scenario in ('low', 'base', 'high'):
        target = parameter(data, f'cmp_fy2026_{scenario}')
        target.update(time_basis='annual', formula='x0', input_parameter_ids=['closing_stock'], value=20.0,
                      definition='Recognized annual acquired business revenue', rationale='Renaming is not a stock-flow model')
        target.pop('period_start')
        target.pop('period_end')
    return data

cases.append(('independent_point_stock_cannot_be_annual_revenue_alias', stock_as_annual, 'reject', 'independent'))

def stock_as_dated():
    data = stock_as_annual()
    for scenario in ('low', 'base', 'high'):
        target = parameter(data, f'cmp_fy2026_{scenario}')
        target.update(time_basis='period_flow', period_start='2026-01-01', period_end='2026-12-31')
    return data

cases.append(('independent_point_stock_cannot_be_dated_revenue_alias', stock_as_dated, 'reject', 'independent'))

def zero_weight():
    data = ns['valid_document']()
    window(data, 'unused_fy', 50.0, '2026-01-01', '2026-12-31', 2026)
    for scenario in ('low', 'base', 'high'):
        target = parameter(data, f'cmp_fy2026_{scenario}')
        target.update(formula='x0+0*x1', input_parameter_ids=['cmp_post_2026', 'unused_fy'], value=1.29190208)
        target.pop('rationale')
    return data

cases.append(('independent_zero_weight_does_not_fill_fy', zero_weight, 'reject', 'independent'))

results = []
for name, builder, expected, group in cases:
    began = time.monotonic()
    data = builder()
    try:
        normalized = validate_document(data)
        forecast = run_forecast(data)
        ns['validate_published_forecast'](forecast, data)
        ns['validate_forecast_output'](forecast)
        actual = 'accepted'
        row = {'case': name, 'expected': expected, 'actual': actual, 'group': group,
               'pass': expected == 'accept', 'fy2026_low': forecast['consolidated_forecast']['low']['annual_revenue']['2026'],
               'strong_readers': 'PASS'}
    except Exception as exc:
        row = {'case': name, 'expected': expected, 'actual': 'rejected', 'group': group,
               'pass': expected == 'reject' and type(exc).__name__ == 'ForecastInputError',
               'exception': type(exc).__name__, 'detail': str(exc)}
    row['input'] = data
    row['elapsed_seconds'] = round(time.monotonic() - began, 6)
    results.append(row)

inventory = json.loads((OUT.parent / 'fix/root-product-inventory.json').read_text(encoding='utf-8'))
files = []
for item in inventory['files']:
    body = (ROOT / item['path']).read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    files.append({'path': item['path'], 'sha256': sha, 'bytes': len(body),
                  'matches_frozen_inventory': sha == item['sha256'] and len(body) == item['bytes']})
payload = {'schema_version': 'w05-independent-final-rf-probes/1', 'product_root': str(ROOT),
           'root_head_declared': inventory['base'], 'original_delivery': inventory['original_delivery'],
           'original_probe_sha256': hashlib.sha256((INTAKE / 'probe_dated_flow.py').read_bytes()).hexdigest(),
           'original_probe_change': 'Only LEAF path binding changed in memory; original file, builders and expectations unchanged.',
           'cases': results, 'frozen_files': files, 'provider_calls': 0, 'llm_calls': 0, 'fees_usd': 0,
           'product_writes': 0, 'raw_writes': 0}
(OUT / 'original-and-independent-probes.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'case_count': len(results), 'failed_expectations': [x['case'] for x in results if not x['pass']],
                  'freeze_mismatches': [x['path'] for x in files if not x['matches_frozen_inventory']]}))
