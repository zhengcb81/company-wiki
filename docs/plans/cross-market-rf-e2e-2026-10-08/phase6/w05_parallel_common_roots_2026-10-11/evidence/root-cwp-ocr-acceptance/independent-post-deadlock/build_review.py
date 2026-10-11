"""Read-only evidence reconciliation; writes only this independent review folder."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
PROJECT = Path('C:/Users/郑曾波/Projects/company-wiki')
TREE = PROJECT.parent / '_harness_worktrees/w05/cwp-ocr-root'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


source_paths = (
    'src/company_wiki/document_normalization/isolated_ocr.py',
    'src/company_wiki/document_normalization/local_ocr.py',
    'src/company_wiki/document_normalization/ocr_composition.py',
    'src/company_wiki/document_normalization/ocr_region_recovery.py',
    'src/company_wiki/source_catalog/narrative_normalization.py',
    'tests/document_normalization/test_isolated_ocr.py',
    'tests/document_normalization/test_local_ocr_adapter.py',
    'tests/document_normalization/test_ocr_region_composition.py',
    'tests/document_normalization/test_ocr_region_recovery.py',
    'src/company_wiki/_bounded_process.py',
    'src/company_wiki/_process_tree.py',
)
frozen = {path: sha(TREE / path) for path in source_paths}
expected = {
    'src/company_wiki/document_normalization/isolated_ocr.py': 'edade53c3c0fed2cb47ab115dbc969e1bd18be183280ee67a086fc876623d396',
    'src/company_wiki/source_catalog/narrative_normalization.py': 'b29a4fe2069713800d171c30ecd09d7bcf3a35984ef2f872ed85d8d4986ccbfd',
    'tests/document_normalization/test_isolated_ocr.py': 'cae823beff8cf78d49fd28cd4621aa12596868b517f462d9fcd7dfeba5013c04',
}
assert all(frozen[path] == value for path, value in expected.items())
old_manifest = load(EVIDENCE / 'independent/manifest.json')
retained = [{**record, 'actual_sha256': sha(EVIDENCE / 'independent' / record['path'])}
            for record in old_manifest['files']]
assert all(record['sha256'] == record['actual_sha256'] for record in retained)
old_fail = []
for name in ('root-real-e2e-original-fail-result.json',
             'root-real-e2e-original-fail-receipt.json',
             'root-real-e2e-original-fail.log'):
    path = EVIDENCE / name
    relative = path.relative_to(PROJECT).as_posix()
    original_blob = subprocess.check_output(['git', 'show', 'c145da9b:' + relative], cwd=PROJECT)
    actual = sha(path)
    committed = hashlib.sha256(original_blob).hexdigest()
    assert actual == committed, (relative, actual, committed)
    old_fail.append({'path': relative, 'sha256': actual, 'committed_sha256': committed,
                     'commit': 'c145da9b', 'bytes': path.stat().st_size})

probe = load(HERE / 'hard-startup-result.json')
assert probe['status'] == 'PASS' and probe['owned_root_restored']
assert probe['elapsed_seconds'] < 1.0 and probe['all_bootstraps_reaped']
assert not probe['remaining_proxy_scratch'] and not probe['backend_started']
assert not Path(probe['owned_root']).exists()

real = load(EVIDENCE / 'root-real-e2e-result.json')
receipt = load(EVIDENCE / 'root-real-e2e-receipt.json')
assert real['status'] == 'COMPLETED' and receipt['status'] == 'PASS'
assert receipt['input_before'] == receipt['input_after'] and receipt['raw_config_unchanged']
assert receipt['scratch_before'] == receipt['scratch_after'] == 'absent'
assert real['baseline_match']['lines_compared'] == 22
assert real['baseline_match']['text_box_confidence_exact']
assert real['replay']['exact_match'] and real['replay']['fresh_adapter']
assert len(real['slide7']['recovered_lines']) == 2
assert all(p['status'] == 'COMPLETED' and p['elapsed_seconds'] < 90
           for p in real['phases'].values())
assert all(abs(a - b) < 1e-9 for a, b in zip(
    real['slide7']['recovered_confidences'], [0.98912, 0.99044], strict=True))

config_paths = (TREE / 'config/local_ocr.json', PROJECT / 'config.yaml', PROJECT / 'config/source_catalog.yaml')
config = {str(path): sha(path) for path in config_paths}
for path, value in config.items():
    assert receipt['input_after'][path.replace('/', '\\')] == value

old_probes = load(EVIDENCE / 'independent/frozen-counterexamples.json')
assert len(old_probes['results']) == 6 and all(r['status'] == 'PASS' for r in old_probes['results'])
for path, value in old_probes['source_sha256'].items():
    assert frozen[path] == value

reviewed_evidence = (
    'runtime-boundary.md',
    'root-real-e2e-result.json', 'root-real-e2e-receipt.json',
    'hard-boundary/performance/runtime-import-deadlock.md',
    'hard-boundary/performance/red-stdin.log',
    'hard-boundary/performance/red-crt-stdin.log',
    'hard-boundary/performance/green-crt-stdin-and-owned-tree.log',
    'hard-boundary/performance/probe-import-stack-after-fix.json',
    'hard-boundary/performance/probe-import-stack-after-fix-trace.jsonl',
    'independent/manifest.json',
    'independent/final-review.json',
    'independent/frozen-counterexamples.json',
)
record = {
    'schema_version': 'root-w05-ocr-independent-post-deadlock/1',
    'date': '2026-10-11',
    'status': 'PASS_NATIVE_BOUNDARY_PENDING_PREALLOCATION',
    'merge_recommendation': 'Native-runtime correction is acceptable for frozen SHA; overall resource-cap acceptance waits for ROOT preallocation repair and concentrated geometry verification',
    'reviewer_is_product_non_author': True,
    'tree': str(TREE),
    'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=TREE, text=True).strip(),
    'source_sha256': frozen,
    'config_sha256': config,
    'old_independent_manifest_matches': retained,
    'original_real_fail_matches_committed_bytes': old_fail,
    'reviewed_evidence_sha256': {p: sha(EVIDENCE / p) for p in reviewed_evidence},
    'independently_executed': {
        'cold_start_50ms_probe': probe,
        'bulk_suite_repeated': False,
        'focused_22_repeated': False,
        'real_ocr_repeated': False,
        'posix_executed': False,
    },
    'root_execution_reviewed': {
        'post_fix_focused_22': {'passed': 22, 'seconds': 25.58},
        'pre_fix_combined_184': {'passed': 184, 'post_fix': False},
        'real_e2e': {'status': receipt['status'], 'seconds': receipt['elapsed_seconds'],
            'phase_seconds': {k: v['elapsed_seconds'] for k, v in real['phases'].items()},
            'product_native_phase1_deadline_seconds': 85,
            'product_native_replay_fallback_seconds': 90,
            'emergency_harness_per_phase_seconds': 90,
            'outer_harness_seconds': 195,
            'old_22_exact': True, 'recovered_confidences': real['slide7']['recovered_confidences'],
            'locator_replay_exact': True, 'config_raw_before_after_equal': True,
            'scratch_before_after': ['absent', 'absent'],
            'scratch_peak_retained_bytes': receipt['scratch_peak_retained_bytes']},
    },
    'checks': [
        {'id': 'OCR-POST-01', 'status': 'PASS', 'check': 'No native worker EOF/stdin monitor; UCRT _fstat64 regression retained at identical 1s budget; native import RED/GREEN causal evidence supports common root cause'},
        {'id': 'OCR-POST-02', 'status': 'PASS_WINDOWS', 'check': 'Non-inheritable Windows Job KILL_ON_JOB_CLOSE assigned before bootstrap release; native worker and descendants inherit job; close/timeout/owner death independent of native GIL'},
        {'id': 'OCR-POST-03', 'status': 'STATIC_ONLY_POSIX', 'check': 'Separate guardian watches parent pipe, owns process session and kills group; no native-process EOF thread'},
        {'id': 'OCR-POST-04', 'status': 'PASS', 'check': 'One pinned minimum absolute deadline includes startup/preflight/native/IPC; fallback starts once; repeated image/ROI and later deadline cannot renew it'},
        {'id': 'OCR-POST-05', 'status': 'PASS', 'check': 'Bounded per-call image/result files, bounded atomic controls, owned generated temp root; native tree reaped before normal cleanup; 2.5s cleanup grace separate from request work'},
        {'id': 'OCR-POST-06', 'status': 'PASS', 'check': 'enrich_pptx auto-isolates configured LocalOCRAdapter; NarrativeNormalization default preflight/sample/normalize/replay already uses isolated adapter; injected legacy protocol retained'},
        {'id': 'OCR-POST-07', 'status': 'PENDING_PREALLOCATION_REPAIR', 'check': 'Shared full-image/ROI pixels reserved before native inference; PIL ROI transformation precedes reserve. Valid 15.996M-pixel source can render 63.984M-pixel upscale before rejection; default caps do not currently bound render allocation'},
        {'id': 'OCR-POST-08', 'status': 'PASS', 'check': 'Engine model/config fingerprint and source identities unchanged; low confidence and undetected recall remain diagnostic/unverified; no new permissions/reviews/providers'},
    ],
    'limitations': [
        'POSIX behavior received static review only; no claim of POSIX runtime acceptance',
        '184 combined suite is a pre-EOF-correction baseline; post-correction execution is 22 focused plus configured real E2E and this independent 50ms probe',
        'Kernel-forced owner death kills job-owned native tree, but may leave bounded owned TEMP files; exact scratch restoration is only claimed for handled success/failure',
        'ROI PIL transform/PNG allocation occurs before pixel reservation. Over-budget native inference is rejected, but over-budget render is a concrete common resource-cap gap. ROOT has assigned unified geometry planning, reservation-before-render, and focused TDD. Overall resource contract remains pending that repair',
        'Low-level LocalOCRAdapter is a cooperative primitive; bypassing configured composition/NarrativeNormalization by directly invoking it is outside reviewed public entrypoints',
        'No claims for W04 summary selection, RF company factual correctness, or investment economic quality',
    ],
    'resources': {'provider_calls': 0, 'cloud_ocr_calls': 0, 'model_downloads': 0,
                  'independent_real_native_inference_calls': 0, 'fees_usd': 0,
                  'raw_bytes_opened_by_independent_review': 0},
    'writes': {'only': str(HERE), 'product_changed': False, 'shared_pwf_changed': False,
               'original_fail_overwritten': False, 'config_changed': False, 'git_committed': False},
    'preallocation_static_geometry_bounds': load(HERE / 'geometry-bounds.json'),
}
(HERE / 'review.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
files = [{ 'path': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)}
         for p in sorted(HERE.iterdir()) if p.is_file() and p.name != 'manifest.json']
(HERE / 'manifest.json').write_text(json.dumps({'schema_version': 'root-w05-ocr-independent-post-deadlock-manifest/1',
    'status': record['status'], 'files': files}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': record['status'], 'old_manifest_files_verified': len(retained),
    'original_real_fail_committed_files_verified': len(old_fail), 'independent_probe_seconds': probe['elapsed_seconds'],
    'real_e2e_seconds_reviewed': receipt['elapsed_seconds'], 'product_sha_pins_match': True,
    'retained_review_bytes': sum(p.stat().st_size for p in HERE.iterdir() if p.is_file())}))
