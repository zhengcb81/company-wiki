"""Run the unchanged six-original checkpoints against the phase2 freeze."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
TREE = Path(r'C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki')
OUT = Path(__file__).resolve().parent
STEM = 'native-novelty-six-quality-v2'
FREEZE = TREE / '.planning/w04-root-novelty-recall/phase2-real-recall/product-freeze.json'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
freeze = json.loads(FREEZE.read_text(encoding='utf-8'))

def verify():
    for name, row in freeze['products'].items():
        assert sha(TREE / name) == row['sha256'], name

assert not (OUT / (STEM + '.json.gz')).exists(), 'Preserve earlier attempts'
verify()
configs = [ROOT / 'config.yaml', ROOT / 'config/source_catalog.yaml', ROOT / 'config/local_ocr.json']
before = {str(path): sha(path) for path in configs}
env = {name: os.environ[name] for name in ('PATH', 'PATHEXT', 'SYSTEMROOT', 'WINDIR',
       'COMSPEC', 'TEMP', 'TMP') if name in os.environ}
env.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', PYTHON_DOTENV_DISABLED='1')
command = [sys.executable, '-X', 'utf8', '-B', str(OUT / 'native_novelty_replay.py'), STEM]
started = time.monotonic()
proc = subprocess.run(command, cwd=TREE, env=env, capture_output=True, timeout=240)
(OUT / (STEM + '-stdout.log')).write_bytes(proc.stdout)
(OUT / (STEM + '-stderr.log')).write_bytes(proc.stderr)
verify()
record = {'schema': 'root-w04-phase2-native-execution/1', 'exit_code': proc.returncode,
          'seconds': round(time.monotonic() - started, 4), 'command': command,
          'cwd': str(TREE), 'product_freeze_sha256': sha(FREEZE),
          'unchanged_checkpoint_script_sha256': sha(OUT / 'native_novelty_replay.py'),
          'frozen_products_unchanged': True,
          'production_config_unchanged': before == {str(path): sha(path) for path in configs},
          'provider_llm_fees': 0}
(OUT / (STEM + '-execution.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(proc.stdout.decode('utf-8', errors='replace'), flush=True)
print(json.dumps(record, ensure_ascii=False), flush=True)
if proc.stderr:
    print(proc.stderr.decode('utf-8', errors='replace')[-1500:], file=sys.stderr, flush=True)
raise SystemExit(proc.returncode)
