"""Replay the unchanged real assertions in a fresh, immutable evidence directory."""
from pathlib import Path
import hashlib
import json
import runpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TREE = ROOT.parent / '_harness_worktrees/w05/cwp-ocr-root'
OUT = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-cwp-ocr-acceptance/preallocation-real-e2e'
assert not OUT.exists(), 'one-shot evidence directory already exists'
files = ['src/company_wiki/document_normalization/ocr_composition.py',
         'src/company_wiki/document_normalization/ocr_region_recovery.py',
         'src/company_wiki/document_normalization/isolated_ocr.py',
         'src/company_wiki/document_normalization/local_ocr.py']
# Source filenames are intentionally checked before starting; no model/provider fetch.
assert all((TREE / name).is_file() for name in files)
def hashes():
    return {name: hashlib.sha256((TREE/name).read_bytes()).hexdigest() for name in files}
before = hashes()
OUT.mkdir()
scope = runpy.run_path(str(HERE / 'run_real_e2e.py'), run_name='preallocation_root_replay')
scope['parent'].__globals__['EVIDENCE'] = OUT
try:
    scope['parent']()
finally:
    after = hashes()
    (OUT / 'product-freeze.json').write_text(json.dumps({'before': before, 'after': after,
        'unchanged': before == after}, indent=2) + '\n', encoding='utf-8')
    assert before == after, 'product changed during real acceptance'
