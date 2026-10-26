"""Independent, metadata-only entrypoint probe; no PDF or model work."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
WORKER = ROOT / 'src/company_wiki/source_catalog/_paragraph_worker.py'
CONFIG = OUT.parent / 'runtime-4g-v2.json'
legacy_config = ROOT / '.planning/pdf-c2-enhancement-20261025/runtime-4g.json'
config = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
old = json.loads(legacy_config.read_text(encoding='utf-8-sig'))
variants = {
    'single_src': [ROOT / 'src'],
    'duplicate_src_and_root': [ROOT / 'src', ROOT, ROOT / 'src', ROOT / 'scripts'],
}
receipts = {}
for name, paths in variants.items():
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(map(str, paths)), PYTHONDONTWRITEBYTECODE='1')
    proc = subprocess.run([sys.executable, '-B', str(WORKER), '--describe-environment',
                           '--runtime-config', str(CONFIG)], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding='utf-8', timeout=25)
    (OUT / f'entry-{name}.stderr.txt').write_text(proc.stderr, encoding='utf-8')
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    (OUT / f'entry-{name}.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    receipts[name] = data
assert receipts['single_src'] == receipts['duplicate_src_and_root']
assert receipts['single_src']['environment_sha256'] == config['environment_sha256']

# Separate fresh process proves base import and legacy identity do not depend
# on packaging, Docling, or Torch imports. Its inventory algorithm is derived
# independently rather than comparing two wrappers of the same function.
code = '''
import importlib.abc, importlib.metadata, hashlib, json, re, sys
class BlockOptional(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'packaging', 'docling', 'torch'}:
            raise AssertionError('optional import on legacy path: '+fullname)
sys.meta_path.insert(0, BlockOptional())
from company_wiki.source_catalog import narrative_pdf_enhancement, _paragraph_worker
expected = hashlib.sha256(json.dumps(sorted((re.sub(r'[-_.]+', '-', d.metadata['Name'] or '').lower(), d.version)
    for d in importlib.metadata.distributions()), separators=(',', ':')).encode()).hexdigest()
assert _paragraph_worker.environment_sha256() == expected
assert not any(n.split('.')[0] in {'packaging','docling','torch'} for n in sys.modules)
print(json.dumps({'v1_algorithm_equal': True, 'optional_imports': []}))
'''
proc = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT,
                      env=dict(os.environ, PYTHONPATH=str(ROOT / 'src')),
                      capture_output=True, text=True, encoding='utf-8', timeout=25)
assert proc.returncode == 0, proc.stderr
legacy = json.loads(proc.stdout)
changed = sorted(k for k in old.keys() | config.keys() if old.get(k) != config.get(k))
assert changed == ['environment_algorithm', 'environment_sha256', 'schema_version']
summary = {
    'schema_version': 'independent-pdf-env-probe/1',
    'status': 'PASS', 'worker_entrypoint_equal': True,
    'python': sys.executable, 'python_version': sys.version.split()[0],
    'closure_count': len(receipts['single_src']['distributions']),
    'environment_sha256': config['environment_sha256'], 'legacy': legacy,
    'changed_config_fields': changed,
    'frozen_v1_config_sha256': sha256(legacy_config.read_bytes()).hexdigest(),
    'v2_config_sha256': sha256(CONFIG.read_bytes()).hexdigest(),
    'heavy_sdk_imports': False, 'pdf_conversion': False,
}
(OUT / 'entrypoint-summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
