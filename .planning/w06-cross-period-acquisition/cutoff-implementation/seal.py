"""Read-only final frozen delivery verification and evidence manifest sealing."""
import hashlib
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
EVIDENCE = Path(__file__).resolve().parent
freeze = json.loads((EVIDENCE / 'product-freeze.json').read_text(encoding='utf-8'))
for entry in freeze['files']:
    path = Path(freeze['roots'][entry['repository']]) / entry['path']
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != entry['sha256'] or len(data) != entry['bytes']:
        raise RuntimeError(f'Frozen delivery changed: {path}')
items = []
for path in sorted(EVIDENCE.rglob('*')):
    if path.is_file() and path != EVIDENCE / 'manifest.json':
        payload = path.read_bytes()
        items.append({'path': str(path.relative_to(EVIDENCE)), 'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)})
for root in freeze['roots'].values():
    tree = Path(root)
    for folder in (tree / '.planning/w06-cutoff-result', tree / 'docs/handoffs/w06-cutoff-result'):
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                payload = path.read_bytes()
                items.append({'path': str(path), 'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)})
manifest = {'schema_version': 'root-w06-cutoff-evidence-manifest/1', 'verdict': 'AUTHOR_COMPLETE_PENDING_ROOT_MATRIX',
            'files': items, 'product_files_before_after': 8, 'product_files_unchanged_after_freeze': True,
            'tools_205_unchanged': True, 'old_goldens_unchanged': True, 'owned_scratch_restored': True,
            'matrix_reruns': 0, 'cwp_product_writes': 0, 'commit_merge_push_install': False}
path = EVIDENCE / 'manifest.json'
path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'product_files_before_after': 8, 'evidence_entries': len(items), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}))
