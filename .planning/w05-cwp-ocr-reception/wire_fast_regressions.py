"""TDD registration in the existing shared CI/local smoke; no new gate."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT.parent / '_harness_worktrees/w05/cwp-ocr-root'
OUT = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-cwp-ocr-acceptance/smoke-registration'
NODES = (
    'tests/document_normalization/test_ocr_region_recovery.py::test_roi_budget_preflight_never_calls_rejected_renderer',
    'tests/document_normalization/test_ocr_region_recovery.py::test_rejected_render_attempt_keeps_reserved_budget',
    'tests/document_normalization/test_ocr_region_recovery.py::test_upscale_preflight_accounts_for_64m_canvas_without_allocating_it',
    'tests/document_normalization/test_isolated_ocr.py::test_noncooperative_native_stops_at_product_deadline[gil-block-inference-infer]',
    'tests/document_normalization/test_isolated_ocr.py::test_native_crt_stdin_probe_does_not_deadlock_liveness_monitor[_fstat64]',
    'tests/document_normalization/test_isolated_ocr.py::test_narrative_default_proxy_carries_deadline_without_starting_native',
)
TEST = TREE / 'tests/unit/test_ci_push_selection.py'
GATE = TREE / 'tools/pre_push_gate.py'
NAME = 'test_ocr_resource_regressions_share_ci_and_local_smoke'
OUT.mkdir(exist_ok=True)
env = {**os.environ, 'PYTHONPATH': str(TREE/'src'), 'PYTHONDONTWRITEBYTECODE': '1',
       'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
if sys.argv[1:] == ['--red']:
    assert NAME.encode() not in TEST.read_bytes()
    added = '\n\n@pytest.mark.parametrize("node", ' + repr(NODES) + ')\n'
    added += f'def {NAME}(node):\n    assert node in gate.FAST_CONTRACT_CASES\n'
    TEST.write_bytes(TEST.read_bytes() + added.encode('utf-8'))
    with tempfile.TemporaryDirectory(prefix='cwproi-registration-') as scratch:
        result = subprocess.run([sys.executable, '-X', 'utf8', '-B', '-m', 'pytest',
            f'tests/unit/test_ci_push_selection.py::{NAME}', '-q', '--tb=short',
            '--basetemp', scratch, '-p', 'no:cacheprovider'], cwd=TREE, env=env,
            capture_output=True, text=True, encoding='utf-8', errors='replace')
    (OUT/'red.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    assert result.returncode == 1 and '6 failed' in result.stdout, result.stdout + result.stderr
    print('6 registration regressions RED; scratch restored')
elif sys.argv[1:] == ['--fix']:
    old = GATE.read_bytes()
    anchor = b'FAST_CONTRACT_CASES = ('
    assert old.count(anchor) == 1
    assert all(node.encode() not in old for node in NODES)
    registration = ('\n    # Small OCR resource regressions; real model replay remains a major-node test.\n'
                    + ''.join('    ' + repr(node) + ',\n' for node in NODES)).encode()
    GATE.write_bytes(old.replace(anchor, anchor + registration))
    result = subprocess.run([sys.executable, '-X', 'utf8', '-B', 'tools/pre_push_gate.py',
        '--fast-contracts-only'], cwd=TREE, env=env,
        capture_output=True, text=True, encoding='utf-8', errors='replace')
    (OUT/'green.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    print(result.stdout + result.stderr)
    assert result.returncode == 0
else:
    raise SystemExit('choose --red or --fix; both are one-shot')
