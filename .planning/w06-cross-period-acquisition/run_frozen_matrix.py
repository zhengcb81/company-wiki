"""One real offline matrix on frozen producer/tools, with no original copies."""
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
FF = ROOT.parent/'_harness_worktrees/w06/ff-contract-matrix-root'
CWP = ROOT.parent/'_harness_worktrees/w06/cwp-acquisition-scope-root'
ET = ROOT.parent/'earnings-transcripts/earnings-transcripts'
E = ROOT/'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance'
OUT = E/'root-matrix-replay'
assert not OUT.exists(), 'a new matrix needs a new evidence directory'
review = json.loads((E/'independent-case-authority-final/report.json').read_text(encoding='utf-8'))
assert review['verdict'] == 'PASS_WITH_SCOPE' and all(p['pass'] for p in review['probes'])
hash_bytes = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert hash_bytes(E/'fix/case-authority/manifest.json') == 'e2bf72bde855935db1beeca45ad10d4a9b205f4ca1137dab07db4d827e3f7fe3'
assert hash_bytes(E/'producer-scope-fix/product-freeze.json') == '1a753dd95c8e897891c48ee5e00e47bde0723a21741aae823af9806619ecdc91'
ff_freeze = json.loads((E/'fix/case-authority/manifest.json').read_text(encoding='utf-8'))
producer = json.loads((E/'producer-scope-fix/product-freeze.json').read_text(encoding='utf-8'))
for row in ff_freeze['files']:
    assert hash_bytes(FF/row['path']) == row['sha256'], row['path']
for name, row in producer['product_files'].items():
    assert hash_bytes(CWP/name) == row['sha256'], name
config_paths = [ROOT/'config.yaml', ROOT/'config/source_catalog.yaml', ROOT/'config/local_ocr.json']
before = {str(p): hash_bytes(p) for p in config_paths}
key = ROOT.parent/'filing-fetch/config/FMP_API_KEY.txt'
def stat_key():
    stat = key.stat()
    return {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
key_before = stat_key()
scratch = ROOT/'.tmp'/('mx-'+uuid.uuid4().hex[:8])
output = ROOT/'.tmp/w06-root-matrix-evidence'
assert not scratch.exists()
OUT.mkdir(parents=True)
env = {k: os.environ[k] for k in ('PATH','PATHEXT','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','NUMBER_OF_PROCESSORS') if k in os.environ}
env.update(PYTHONUTF8='1', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1',
           PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHON_DOTENV_DISABLED='1')
command = [sys.executable, '-X', 'utf8', '-B', 'tools/offline_contract_matrix/run.py',
           '--cwp-project', str(CWP), '--et-project', str(ET),
           '--owned-root', str(scratch), '--out-root', str(output)]
print('Starting original 41-vector offline matrix; frozen source/tools, 180s internal deadline', flush=True)
start = time.monotonic()
result = subprocess.run(command, cwd=FF, env=env, capture_output=True, timeout=240)
(OUT/'stdout.log').write_bytes(result.stdout)
(OUT/'stderr.log').write_bytes(result.stderr)
text = result.stdout.decode('utf-8', errors='replace')
reports = [line.removeprefix('report: ').strip() for line in text.splitlines() if line.startswith('report: ')]
report_path = Path(reports[-1]) if reports else None
summary = {'schema': 'root-w06-original-matrix-replay/1', 'exit_code': result.returncode,
           'seconds': round(time.monotonic()-start, 4), 'command': command,
           'ff_case_authority_manifest_sha256': hash_bytes(E/'fix/case-authority/manifest.json'),
           'cwp_product_freeze_sha256': hash_bytes(E/'producer-scope-fix/product-freeze.json'),
           'actual_report': str(report_path) if report_path else None,
           'production_config_unchanged': before == {str(p):hash_bytes(p) for p in config_paths},
           'real_key_stat_unchanged': key_before == stat_key(), 'scratch_restored_absent': not scratch.exists(),
           'budget': 'Synthetic/offline; no project LLM or provider expense'}
if report_path and report_path.exists():
    raw = report_path.read_bytes()
    (OUT/'original-report.json').write_bytes(raw)
    report = json.loads(raw)
    summary.update(report_sha256=hashlib.sha256(raw).hexdigest(),
                   counts=dict(Counter(c['result'] for c in report['cases'])),
                   oracle=report.get('oracle'), restore=report.get('restore'),
                   scope=report.get('scope'), cost=report.get('cost'))
for row in ff_freeze['files']:
    assert hash_bytes(FF/row['path']) == row['sha256'], row['path']
for name, row in producer['product_files'].items():
    assert hash_bytes(CWP/name) == row['sha256'], name
summary['frozen_product_files_unchanged'] = True
(OUT/'execution.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(text, flush=True)
print('ROOT summary:', json.dumps({k:summary.get(k) for k in ['exit_code','seconds','counts','scratch_restored_absent','frozen_product_files_unchanged']}), flush=True)
raise SystemExit(result.returncode)
