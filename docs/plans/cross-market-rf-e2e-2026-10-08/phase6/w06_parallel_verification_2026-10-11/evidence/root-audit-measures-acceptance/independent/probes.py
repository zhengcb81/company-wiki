"""Independent frozen-vector replay and bounded typed-contract probes; no providers."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures-root')
OUT = Path(__file__).resolve().parent
INTAKE = OUT.parent / 'intake'

def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

spec = importlib.util.spec_from_file_location('independent_helpers', ROOT / 'tests/test_financial_measure_audit.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
f, o, r, result, ledger = h.flow, h.obs, h.rel, h.res, h.ledger
module = h.module

cases = []
for original in json.loads((INTAKE / 'counterexamples.json').read_text(encoding='utf-8'))['cases']:
    cases.append((original['id'], copy.deepcopy(original['ledger']), set(original['expected_statuses']), 'unchanged_original_19'))

valid = ledger([f('source', '1.2', scale='billion')],
               [r('conv', 'scale_conversion', ['source'], f('output', '12', scale='亿'))])

market_share = ledger([f('company-sales', '20', entity='hk-company', definition='company_market_sales', currency='CNY'),
                       f('market-sales', '100', entity='cn-market', definition='defined_market_sales', currency='CNY')],
                     [r('market-share', 'share', ['company-sales', 'market-sales'],
                        result('share-out', '20', 'percent', None, 'ratio', entity='hk-company', definition='market_share',
                               period_start='2024-01-01', period_end='2024-12-31'),
                        scope_inclusion='company_market_sales is inside the explicitly defined CN market denominator')])
cases.append(('independent_legal_cross_entity_market_share', market_share, {'PASS'}, 'independent'))

sample = copy.deepcopy(valid)
sample['observations'][0]['source_ref'] = None
cases.append(('independent_missing_fact_source_unknown', sample, {'UNRESOLVED'}, 'independent'))

sample = copy.deepcopy(valid)
for row in [sample['observations'][0], sample['relations'][0]['result']]:
    row.update(period_start='2028-01-01', period_end='2028-12-31', evidence_role='analyst_assumption',
               source_ref=None, rationale='Explicit synthetic planning assumption; no factual source claimed')
cases.append(('independent_future_assumption_conversion_legal', sample, {'PASS'}, 'independent'))

sample = copy.deepcopy(valid)
sample['observations'][0]['source_ref'] = []
cases.append(('independent_invalid_source_shape_structured', sample, {'INVALID'}, 'independent'))

sample = copy.deepcopy(valid)
sample['relations'][0]['rounding'] = {'places': True, 'basis': 'literal display precision'}
cases.append(('independent_bool_rounding_is_not_integer', sample, {'INVALID'}, 'independent'))

sample = copy.deepcopy(valid)
sample['observations'][0]['available_by'] = '2026-10-12'
cases.append(('independent_source_after_asof_unresolved', sample, {'UNRESOLVED'}, 'independent'))

cases.append(('independent_nonobject_ledger_report_contract', [], {'INVALID'}, 'independent'))
cases.append(('independent_observations_object_report_contract', {'schema_version': 'financial-measure-ledger/1',
              'as_of_date': '2026-10-11', 'observations': {}, 'relations': []}, {'INVALID'}, 'independent'))

results = []
for name, sample, expected, group in cases:
    started = time.monotonic()
    try:
        report = module.audit_measures(sample)
        actual = report.get('overall')
        results.append({'id': name, 'group': group, 'expected_statuses': sorted(expected),
                        'actual_status': actual, 'passes_expectation': actual in expected,
                        'required_nonattestation_fields_present': all(k in report for k in
                            ('source_truth_verified', 'source_qualification_verified', 'economic_reasonableness')),
                        'ledger': sample, 'report': report,
                        'elapsed_seconds': round(time.monotonic() - started, 6)})
    except Exception as exc:
        results.append({'id': name, 'group': group, 'expected_statuses': sorted(expected),
                        'actual_status': 'EXCEPTION', 'passes_expectation': False,
                        'exception': type(exc).__name__ + ': ' + str(exc), 'ledger': sample})

dump('final-counterexamples.json', {'schema_version': 'w06-independent-measure-probes/2',
     'product_root': str(ROOT), 'product_sha256': hashlib.sha256((ROOT / 'skills/revenue-forecast-audit/scripts/financial_measure_audit.py').read_bytes()).hexdigest(),
     'source_truth_verified': False, 'economic_reasonableness': 'not_evaluated', 'cases': results})

scratch = OUT / '_cli_scratch'
if scratch.exists():
    raise RuntimeError('owned CLI scratch must initially be absent')
scratch.mkdir()
try:
    ledger_path = scratch / 'malformed-but-valid-json.json'
    ledger_path.write_text(json.dumps(cases[-1][1]), encoding='utf-8')
    out_root = scratch / 'attempts'
    command = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'skills/revenue-forecast-audit/scripts/financial_measure_audit.py'),
               '--ledger', str(ledger_path), '--out-root', str(out_root)]
    proc = subprocess.run(command, capture_output=True, encoding='utf-8', timeout=20, cwd=OUT)
    try:
        receipt = json.loads(proc.stdout)
    except (ValueError, TypeError):
        receipt = None
    report_paths = list(out_root.rglob('report.json')) if out_root.exists() else []
    reports = [json.loads(path.read_text(encoding='utf-8')) for path in report_paths]
    dump('cli-structured-invalid.json', {'command': command, 'exit_code': proc.returncode,
         'stdout': proc.stdout, 'stderr': proc.stderr, 'receipt': receipt, 'reports': reports,
         'structured_invalid_report': proc.returncode == 2 and len(reports) == 1 and reports[0]['overall'] == 'INVALID',
         'required_nonattestation_fields_present': all(k in reports[0] for k in
             ('source_truth_verified', 'source_qualification_verified', 'economic_reasonableness')) if reports else False})
finally:
    if scratch.resolve().parent != OUT.resolve():
        raise RuntimeError('scratch path escaped owned review directory')
    shutil.rmtree(scratch)
    dump('cleanup.json', {'owned_scratch': str(scratch), 'initially_absent': True,
         'finally_absent': not scratch.exists(), 'provider_calls': 0, 'model_calls': 0,
         'original_documents_changed': 0, 'charged_cost_usd': '0'})

print(json.dumps({'cases': len(results), 'expectation_failures': [x['id'] for x in results if not x['passes_expectation']],
      'report_contract_missing_fields': [x['id'] for x in results if not x.get('required_nonattestation_fields_present', False)],
      'scratch_restored': not scratch.exists()}, ensure_ascii=False))
