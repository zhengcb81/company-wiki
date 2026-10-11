from __future__ import annotations
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
EVIDENCE = Path(__file__).resolve().parent
WORKER = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow')
CANONICAL = Path('C:/Users/郑曾波/Projects/revenue-forecast')
DELIVERY = 'f1a782a478d255b9b4b8f531e7a3961134e257ba'
BASE = '1b616622763ece6549676f2a74f596e6c65244af'
ENV = os.environ.copy()
ENV.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE', 'GIT_PREFIX'):
    ENV.pop(key, None)

def git(root, *arguments):
    return subprocess.run(['git', *arguments], cwd=root, env=ENV, text=True, encoding='utf-8',
                          capture_output=True, timeout=30, check=True).stdout.strip()

def record(path, base):
    return {'path': path.relative_to(base).as_posix(), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

changed = git(ROOT, 'diff', '--name-only', DELIVERY).splitlines()
new = ['scripts/contracts/recognition.py', 'tests/test_w05_root_temporal_lineage.py',
       'docs/handoffs/w05-rf-flow/ROOT-reception.md']
new += [path.relative_to(ROOT).as_posix() for path in (ROOT / 'docs/handoffs/w05-rf-flow/e2e/frozen').iterdir() if path.is_file()]
files = [record(ROOT / name, ROOT) for name in sorted(set(changed + new))]
lint = subprocess.run(['python', '-B', '-m', 'ruff', 'check', 'compatibility/compatibility_manifest.py',
                       'compatibility/contract_registry.py', 'docs/handoffs/w05-rf-flow/e2e/build_inputs.py',
                       'docs/handoffs/w05-rf-flow/e2e/read_and_tamper.py', 'scripts/generate_input_template.py'],
                      cwd=ROOT, env=ENV, text=True, encoding='utf-8', capture_output=True, timeout=30)
(EVIDENCE / 'final-supplemental-lint.log').write_text(lint.stdout + lint.stderr + '\nexit=' + str(lint.returncode) + '\n', encoding='utf-8')
assert lint.returncode == 0
status = {
    'root_branch': git(ROOT, 'branch', '--show-current'), 'root_head': git(ROOT, 'rev-parse', 'HEAD'),
    'merge_head': git(ROOT, 'rev-parse', 'MERGE_HEAD'), 'root_status': git(ROOT, 'status', '--short'),
    'original_worker_head': git(WORKER, 'rev-parse', 'HEAD'), 'original_worker_status': git(WORKER, 'status', '--short'),
    'canonical_head': git(CANONICAL, 'rev-parse', 'HEAD'), 'canonical_status': git(CANONICAL, 'status', '--short'),
    'scratch_absent': not (EVIDENCE / 'e2e-scratch').exists(),
    'template_scratch_absent': not (EVIDENCE / 'template-doc-scratch').exists(),
    'no_commit_push_install': True, 'provider_calls': 0, 'llm_calls': 0, 'fees_usd': 0,
}
assert status['root_head'] == BASE and status['merge_head'] == DELIVERY
assert status['original_worker_head'] == DELIVERY and status['original_worker_status'] == ''
manifest = {'schema': 'w05-root-fix-product-inventory/1', 'base': BASE, 'original_delivery': DELIVERY,
            'tracked_modified_after_delivery': changed, 'new_files': sorted(new), 'files': files,
            'file_count': len(files), 'total_bytes': sum(item['bytes'] for item in files), 'status': status,
            'scope': 'ROOT changes relative to original delivery; original staged worker delivery remains in pending merge'}
(EVIDENCE / 'root-product-inventory.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'file_count': len(files), 'total_bytes': manifest['total_bytes'], 'tracked_modified': len(changed),
                  'new': len(new), 'canonical_status': status['canonical_status'], 'worker_clean': True}, ensure_ascii=False))
