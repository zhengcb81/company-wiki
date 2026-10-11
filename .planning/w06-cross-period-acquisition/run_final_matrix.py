"""Replay the original fixed 41 cases on frozen cutoff/source implementations."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
FF = ROOT.parent / '_harness_worktrees/w06/ff-contract-matrix-root'
CWP = ROOT.parent / '_harness_worktrees/w06/cwp-acquisition-scope-root'
ET = ROOT.parent / '_harness_worktrees/w06/et-cutoff-root'
E = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance'
tag = sys.argv[1] if len(sys.argv) in (2, 3) else ''
assert tag and tag.replace('-', '').isalnum(), 'Supply a new readable attempt tag'
OUT = E / tag
assert not OUT.exists(), 'Preserve prior attempts'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
tool = json.loads((E / 'fix/case-authority/manifest.json').read_text(encoding='utf-8'))
source_path = E / 'source-publication/root-product-freeze.json'
source = json.loads(source_path.read_text(encoding='utf-8'))
cutoff_name = sys.argv[2] if len(sys.argv) == 3 else 'product-freeze.json'
assert cutoff_name in ('product-freeze.json', 'product-freeze-v2.json')
cutoff_path = ROOT / '.planning/w06-cross-period-acquisition/cutoff-implementation' / cutoff_name
cutoff = json.loads(cutoff_path.read_text(encoding='utf-8'))
roots = {'ff': FF, 'et': ET}

def verify():
    for row in tool['files']:
        assert sha(FF / row['path']) == row['sha256'], row['path']
    for name, row in source['product_files'].items():
        assert sha(CWP / name) == row['sha256'], name
    for row in cutoff['files']:
        assert sha(roots[row['repository']] / row['path']) == row['sha256'], row['path']

verify()
configs = [ROOT / 'config.yaml', ROOT / 'config/source_catalog.yaml', ROOT / 'config/local_ocr.json']
before = {str(p): sha(p) for p in configs}
key = ROOT.parent / 'filing-fetch/config/FMP_API_KEY.txt'
key_stat = lambda: (key.stat().st_size, key.stat().st_mtime_ns)
before_key = key_stat()
scratch = ROOT / '.tmp' / ('mx-' + uuid.uuid4().hex[:8])
output = ROOT / '.tmp/w06-root-matrix-evidence'
assert not scratch.exists()
OUT.mkdir(parents=True)
env = {k: os.environ[k] for k in ('PATH', 'PATHEXT', 'SYSTEMROOT', 'WINDIR', 'COMSPEC',
                                 'TEMP', 'TMP', 'NUMBER_OF_PROCESSORS') if k in os.environ}
env.update(PYTHONUTF8='1', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1',
           PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHON_DOTENV_DISABLED='1')
command = [sys.executable, '-X', 'utf8', '-B', 'tools/offline_contract_matrix/run.py',
           '--cwp-project', str(CWP), '--et-project', str(ET),
           '--owned-root', str(scratch), '--out-root', str(output)]
print('Original 41 cases; unchanged 30s/case and 180s/batch; synthetic/offline', flush=True)
start = time.monotonic()
result = subprocess.run(command, cwd=FF, env=env, capture_output=True, timeout=240)
(OUT / 'stdout.log').write_bytes(result.stdout)
(OUT / 'stderr.log').write_bytes(result.stderr)
stdout = result.stdout.decode('utf-8', errors='replace')
reports = [line.removeprefix('report: ').strip() for line in stdout.splitlines() if line.startswith('report: ')]
report_path = Path(reports[-1]) if reports else None
record = {'schema': 'root-w06-final-original-matrix/1', 'exit_code': result.returncode,
          'seconds': round(time.monotonic()-start, 4), 'command': command,
          'tool_freeze_sha256': sha(E / 'fix/case-authority/manifest.json'),
          'source_freeze_sha256': sha(source_path), 'cutoff_freeze_sha256': sha(cutoff_path),
          'actual_report': str(report_path) if report_path else None,
          'production_config_unchanged': before == {str(p): sha(p) for p in configs},
          'real_key_stat_unchanged': before_key == key_stat(),
          'scratch_restored_absent': not scratch.exists(), 'real_provider_llm_fees': 0}
if report_path and report_path.exists():
    raw = report_path.read_bytes()
    (OUT / 'original-report.json').write_bytes(raw)
    report = json.loads(raw)
    record.update(report_sha256=hashlib.sha256(raw).hexdigest(),
                  counts=dict(Counter(case['result'] for case in report['cases'])),
                  oracle=report.get('oracle'), restore=report.get('restore'),
                  scope=report.get('scope'), cost=report.get('cost'))
    cutoff_case = next(case for case in report['cases'] if case['id'] == 'call_past_cutoff')
    record['cutoff_observation'] = {k: cutoff_case['actual'].get(k) for k in (
        'status', 'reason', 'eligible', 'cutoff_diagnostic', 'as_of_cutoff_verified')}
verify()
record['all_frozen_products_unchanged'] = True
(OUT / 'execution.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(stdout, flush=True)
print(json.dumps({k: record.get(k) for k in ('exit_code', 'seconds', 'counts', 'cutoff_observation',
                                          'production_config_unchanged', 'scratch_restored_absent')}, ensure_ascii=False), flush=True)
raise SystemExit(result.returncode)
