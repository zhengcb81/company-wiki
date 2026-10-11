from __future__ import annotations
import copy
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
EVIDENCE = Path(__file__).resolve().parent
environment = os.environ.copy()
environment.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
arguments = [sys.executable, '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q',
             'tests/test_w05_root_temporal_lineage.py', 'tests/test_mixed_aggregate_recognition.py',
             'tests/test_m3_period_flow_contract.py', 'tests/test_m3_period_flow_consumers.py',
             'tests/test_m3_period_flow_annual_consumers.py', 'tests/test_m3_schema_compatibility.py',
             'tests/test_schema_compatibility.py', 'tests/test_w05_dated_contribution_contract.py',
             'tests/test_w05_dated_contribution_composition.py', 'tests/test_w05_dated_contribution_output.py']
process = subprocess.run(arguments, cwd=ROOT, env=environment, capture_output=True, text=True,
                         encoding='utf-8', timeout=60)
(EVIDENCE / 'typed-boundary-supplement.log').write_text(json.dumps(arguments) + '\n' + process.stdout + process.stderr, encoding='utf-8')
print(process.stdout[-6000:])
if process.returncode:
    raise SystemExit(process.returncode)
sys.path[:0] = [str(ROOT / 'scripts')]
from revenue_core import ForecastInputError, canonical_sha256, run_forecast, validate_document
from revenue_report import validate_forecast_output, validate_published_forecast
exact = json.loads((EVIDENCE / 'typed-boundary-exact-independent-red.json').read_text(encoding='utf-8'))['case']['input']
outcomes = []
with tempfile.TemporaryDirectory(prefix='w05-typed-exact-') as directory:
    os.environ['REVENUE_PUBLICATION_REGISTRY'] = str(Path(directory) / 'publications.jsonl')
    for label, operation in [('validate_document', lambda: validate_document(copy.deepcopy(exact))),
                             ('run_forecast', lambda: run_forecast(copy.deepcopy(exact)))]:
        try:
            operation()
        except ForecastInputError as error:
            assert 'typed flow' in str(error)
            outcomes.append({'path': label, 'actual': 'rejected', 'error': str(error)})
        else:
            raise AssertionError(label + ' accepted original independent P1 input')
    valid = copy.deepcopy(exact)
    origin = next(item for item in valid['parameters'] if item['parameter_id'] == 'closing_stock')
    origin.update(dimension='revenue', time_basis='annual', definition='Synthetic actual annual revenue control')
    result = run_forecast(valid)
    forged = copy.deepcopy(result)
    forged['input_document'] = copy.deepcopy(exact)
    forged['parameter_trace'] = copy.deepcopy(exact['parameters'])
    forged['input_sha256'] = canonical_sha256(exact)
    forged['result_sha256'] = canonical_sha256({key: value for key, value in forged.items() if key != 'result_sha256'})
    for label, operation in [('validate_forecast_output', lambda: validate_forecast_output(copy.deepcopy(forged))),
                             ('validate_published_forecast', lambda: validate_published_forecast(copy.deepcopy(forged), copy.deepcopy(exact)))]:
        try:
            operation()
        except ForecastInputError as error:
            assert 'typed flow' in str(error), str(error)
            outcomes.append({'path': label, 'actual': 'rejected', 'error': str(error)})
        else:
            raise AssertionError(label + ' accepted rehashed original independent P1 input')
    for item in Path(directory).rglob('*'):
        if item.is_file():
            item.chmod(stat.S_IREAD | stat.S_IWRITE)
(EVIDENCE / 'typed-boundary-exact-replay.json').write_text(json.dumps({
    'original_input': 'typed-boundary-exact-independent-red.json', 'paths': outcomes,
    'old_invalid_annual_contribution': 20.0, 'old_fy2026_low': 170.0,
    'new_invalid_forecast_written': False, 'scratch_restored': not Path(directory).exists(),
    'provider_calls': 0, 'llm_calls': 0, 'fees_usd': 0}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(outcomes, ensure_ascii=False))
