"""Freeze current ET/FF delivery, preserving all historical source/tool evidence."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
EVIDENCE = Path(__file__).resolve().parent
CWP = Path('C:/Users/郑曾波/Projects/company-wiki')
roots = {
    'et': Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/et-cutoff-root'),
    'ff': Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root'),
}
products = {
    'et': ('transcript_api.py', 'tests/test_transcript_api.py', 'tests/test_retrieval_cli_e2e.py'),
    'ff': ('scripts/transcript_tool_transport.py', 'scripts/et_v2_contract.py',
           'tests/test_transcript_launch_contract.py', 'tests/test_transcript_companion_transport.py',
           'tests/test_et_s0b_contract.py'),
}
et_before = json.loads((EVIDENCE / 'et/before.json').read_text(encoding='utf-8'))
ff_before = json.loads((EVIDENCE / 'ff/baseline.json').read_text(encoding='utf-8'))
head_before = {'et': et_before['base_head'], 'ff': ff_before['base']}
head_after = {}
for repository, root in roots.items():
    result = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True, encoding='utf-8', check=True)
    head_after[repository] = result.stdout.strip()
if head_before != head_after:
    raise RuntimeError('Unauthorized head movement in delivery trees')

def file_entry(root, relative):
    raw = (root / relative).read_bytes()
    return {'path': relative.replace('\\', '/'), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}

def verify_entries(root, entries):
    for entry in entries:
        current = file_entry(root, entry['path'])
        if current['sha256'] != entry['sha256'] or current['bytes'] != entry['bytes']:
            raise RuntimeError(f'Frozen input drift: {root / entry["path"]}')

et_goldens = [entry for entry in et_before['files'] if entry['path'].replace('\\', '/').startswith('tests/golden/')]
ff_goldens = [entry for entry in ff_before['protected'] if entry['path'].startswith(('tests/golden/', 'tests/fixtures/et_s0b/'))]
verify_entries(roots['et'], et_goldens)
verify_entries(roots['ff'], ff_before['protected'])
tool_manifest = CWP / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance/fix/case-authority/manifest.json'
tool = json.loads(tool_manifest.read_text(encoding='utf-8'))
if len(tool['files']) != 205:
    raise RuntimeError('Unexpected original case-authority tool freeze')
verify_entries(roots['ff'], tool['files'])
files = []
for repository, names in products.items():
    for name in names:
        files.append({'repository': repository, **file_entry(roots[repository], name)})
scratch_records = []
for relative in ('et/red.json', 'et/green.json', 'et/golden.json', 'et/lint.json',
                 'ff/concentrated.json', 'ff/concentrated-final.json', 'ff/concentrated-final2.json'):
    record = json.loads((EVIDENCE / relative).read_text(encoding='utf-8'))
    scratch = Path(record['scratch'])
    if scratch.resolve().parent != (CWP / '.tmp').resolve() or scratch.exists():
        raise RuntimeError('Owned responsibility scratch not restored')
    scratch_records.append({'record': relative, 'scratch': str(scratch), 'restored_absent': True})
freeze = {
    'schema_version': 'root-w06-cutoff-product-freeze/1',
    'frozen_at': datetime.now(timezone.utc).isoformat(),
    'verdict': 'AUTHOR_COMPLETE_PENDING_ROOT_MATRIX',
    'roots': {name: str(path) for name, path in roots.items()},
    'head_before': head_before, 'head_after': head_after,
    'files': files,
    'old_author_freezes': [
        {'path': str(tool_manifest), 'sha256': hashlib.sha256(tool_manifest.read_bytes()).hexdigest(), 'files': 205, 'unchanged': True},
        {'path': str(EVIDENCE / 'ff/product-freeze.json'), 'sha256': hashlib.sha256((EVIDENCE / 'ff/product-freeze.json').read_bytes()).hexdigest(), 'role': 'historical first author freeze; not final delivery'},
    ],
    'old_goldens': {'et': et_goldens, 'ff': ff_goldens, 'unchanged': True},
    'ff_protected_before_after': {'baseline': str(EVIDENCE / 'ff/baseline.json'), 'sha256': hashlib.sha256((EVIDENCE / 'ff/baseline.json').read_bytes()).hexdigest(), 'files': len(ff_before['protected']), 'unchanged': True},
    'final_responsibility_tests': {'et': {'passed': 56, 'seconds': 40.37, 'record': 'et/green.json'},
                                 'ff': {'passed': 134, 'skipped': 4, 'seconds': 1.90, 'record': 'ff/concentrated-final2.json'}},
    'existing_golden_check': '10 matched',
    'owned_scratch': scratch_records,
    'original_matrix_attempt_preserved': 'attempt-1f64f745d3a94506ae4bc35c8997b562',
    'original_matrix_result': '40 PASS / 1 FAIL / 164.62s',
    'matrix_reruns_by_author': 0,
    'real_network_requests': 0, 'real_key_reads': 0, 'llm_calls': 0,
    'commit_merge_push_install': False,
    'cwp_product_writes': 0,
    'next_step': 'ROOT unchanged 41-case matrix with these two roots and the separately frozen published CWP source tree; independent review and normal publication',
}
target = EVIDENCE / 'product-freeze.json'
if target.exists():
    raise RuntimeError('Refusing to overwrite combined ROOT freeze')
target.write_text(json.dumps(freeze, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'product_files': len(files), 'tools_unchanged': len(tool['files']),
                  'ff_protected_unchanged': len(ff_before['protected']), 'goldens_unchanged': {'et': len(et_goldens), 'ff': len(ff_goldens)},
                  'head_after': head_after, 'freeze_sha256': hashlib.sha256(target.read_bytes()).hexdigest()}, ensure_ascii=False))
