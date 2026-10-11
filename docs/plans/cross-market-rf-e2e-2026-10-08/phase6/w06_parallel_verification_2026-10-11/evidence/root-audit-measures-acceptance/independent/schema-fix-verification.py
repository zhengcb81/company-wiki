"""Focused verification of the one-field ROOT correction, preserving all pre-fix evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures-root')
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / 'skills/revenue-forecast-audit/scripts/financial_measure_audit.py'
spec = importlib.util.spec_from_file_location('final_frozen_measures', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
old = json.loads((OUT / 'final-counterexamples.json').read_text(encoding='utf-8'))
selected = [x for x in old['cases'] if x['id'] in ('independent_nonobject_ledger_report_contract',
    'independent_observations_object_report_contract', 'independent_legal_cross_entity_market_share')]
checks = []
for case in selected:
    report = module.audit_measures(case['ledger'])
    checks.append({'id': case['id'], 'report': report,
        'pass': report['overall'] == case['actual_status'] and report.get('source_qualification_verified') is False
            and report.get('source_truth_verified') is False and report.get('economic_reasonableness') == 'not_evaluated'})
scratch = OUT / '_schema_cli_scratch'
if scratch.exists():
    raise RuntimeError('owned scratch must initially be absent')
scratch.mkdir()
try:
    ledger_path = scratch / 'invalid-ledger.json'
    shape_case = next(c for c in selected if c['id'] == 'independent_observations_object_report_contract')
    ledger_path.write_text(json.dumps(shape_case['ledger']), encoding='utf-8')
    out_root = scratch / 'attempts'
    command = [sys.executable, '-B', '-X', 'utf8', str(SOURCE), '--ledger', str(ledger_path), '--out-root', str(out_root)]
    proc = subprocess.run(command, capture_output=True, encoding='utf-8', timeout=20, cwd=OUT)
    report_paths = list(out_root.rglob('report.json'))
    reports = [json.loads(p.read_text(encoding='utf-8')) for p in report_paths]
    cli = {'command': command, 'exit_code': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr,
           'reports': reports, 'pass': proc.returncode == 2 and len(reports) == 1
            and reports[0]['overall'] == 'INVALID' and reports[0].get('source_qualification_verified') is False
            and reports[0].get('source_truth_verified') is False
            and reports[0].get('economic_reasonableness') == 'not_evaluated'}
finally:
    if scratch.resolve().parent != OUT.resolve():
        raise RuntimeError('scratch escaped owned review directory')
    shutil.rmtree(scratch)
result = {'schema_version': 'w06-independent-report-boundary-verification/1',
          'frozen_product_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'previous_product_sha256': old['product_sha256'], 'pure_checks': checks, 'cli': cli,
          'scratch_initially_absent': True, 'scratch_finally_absent': not scratch.exists(),
          'original_failure_evidence_preserved': True, 'provider_calls': 0, 'llm_calls': 0, 'charged_cost_usd': '0',
          'pass': all(c['pass'] for c in checks) and cli['pass'] and not scratch.exists()}
(OUT / 'report-boundary-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'pass': result['pass'], 'sha256': result['frozen_product_sha256'],
                  'pure_checks': len(checks), 'cli_exit_code': proc.returncode, 'scratch_restored': not scratch.exists()}))
