"""Non-author bounded verification; frozen products remain read-only."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
WORKTREE = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-portability-root')
FREEZE = BASE / 'fix/product-freeze.json'
EXPECTED_FREEZE = 'b1662c806216a8c2e729ae7a48fda6b83a741a552e0e60323b1a662854dd715b'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


assert sha(FREEZE) == EXPECTED_FREEZE
freeze = json.loads(FREEZE.read_text(encoding='utf-8'))
final_path = BASE / 'fix/final-refresh/final-node.json'
real_path = BASE / 'fix/final-refresh/real-run-report.json'
assert sha(final_path) == freeze['final_node_sha256']
assert sha(real_path) == freeze['real_report_sha256']
final = json.loads(final_path.read_text(encoding='utf-8'))
record = json.loads(real_path.read_text(encoding='utf-8'))
inputs = freeze['files'] + final['production_before']
before = {item['path']: sha(WORKTREE / item['path']) for item in inputs}
assert all(before[item['path']] == item['sha256'] for item in inputs)
old_files = sorted((BASE / 'intake').glob('*'))
old_sha = {str(p.relative_to(BASE)): sha(p) for p in old_files if p.is_file()}

sys.path[:0] = [str(WORKTREE / 'src'), str(WORKTREE)]
from tools.source_root_portability import oracle, run, scenarios
from tools.source_root_portability.runtime import (
    OwnedAttempt, child_env, offline_guard, synthetic_environment, validate_roots,
)
from tools.source_root_portability.fixture_builder import build_fixture

observations = []
started = time.monotonic()


def scene(value, name):
    return next(item for item in value['scenarios'] if item['id'] == name)


def observe(name, fn, expected):
    value = copy.deepcopy(record)
    fn(value)
    try:
        verdict = oracle.evaluate_run(value)
        actual = verdict.overall
        result = {'name': name, 'actual': actual, 'expected': expected,
                  'as_expected': actual in expected,
                  'findings': [{'code': f.code, 'scenario': f.scenario_id,
                                'detail': f.detail} for f in verdict.findings]}
    except Exception as exc:
        result = {'name': name, 'actual': 'CRASH', 'expected': expected,
                  'as_expected': False, 'exception': type(exc).__name__}
    observations.append(result)


observe('frozen_legitimate_seven_scene_control', lambda r: None, ['PASS'])
observe('original_omitted_S2_to_S7',
        lambda r: r.update(scenarios=[scene(r, 'S1')]), ['FAIL', 'INVALID_RECORD'])
observe('original_S2_only_one_ref_reopened',
        lambda r: scene(r, 'S2')['evidence'].update(
            reads_after_move=scene(r, 'S2')['evidence']['reads_after_move'][:1]),
        ['FAIL'])
observe('original_S5_new_version_read_failed',
        lambda r: scene(r, 'S5')['evidence']['new_version'].update(
            new_ref_read={'status': 'error'}), ['FAIL'])
observe('original_receipt_only_method_claims_bytes',
        lambda r: scene(r, 'S1')['evidence']['reads'][0].update(method='verify_version'), ['FAIL'])
observe('original_wrong_root_after_move',
        lambda r: scene(r, 'S2')['evidence']['move'].update(
            after_roots=[{'root_id': 'WRONG', 'path_ref': 'wrong/root'}]), ['FAIL'])
observe('original_S7_export_path_fields_present',
        lambda r: scene(r, 'S7')['evidence']['export_process'].update(path_fields_present=True), ['FAIL'])
observe('original_malformed_S2_actual', lambda r: scene(r, 'S2').update(actual=[]), ['INVALID_RECORD'])


def unknown_annual(value):
    def visit(item):
        if isinstance(item, dict):
            if item.get('doc_key') == 'pdf' or item.get('document_kind') == 'annual_report':
                item.update(fiscal_year=None, period_end=None)
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
    visit(value)
    for name, key in (('S1', 'export'), ('S7', 'export_process')):
        export = scene(value, name)['evidence'][key]
        export['stdout'] = json.dumps(export['bundle'])


observe('original_annual_truth_and_observations_self_rewritten_unknown', unknown_annual, ['FAIL'])
observe('raw_CLI_stdout_bundle_disagree',
        lambda r: scene(r, 'S1')['evidence']['export'].update(stdout='{}'), ['FAIL'])
observe('raw_CLI_manifests_replaced',
        lambda r: scene(r, 'S7')['evidence']['export_process'].update(manifests=[]), ['FAIL'])
observe('read_byte_count_bool',
        lambda r: scene(r, 'S2')['evidence']['reads_after_move'][0].update(byte_size=True), ['FAIL'])
observe('new_malformed_read_shape',
        lambda r: scene(r, 'S1')['evidence'].update(reads=[None]), ['FAIL', 'INVALID_RECORD'])
observe('new_malformed_cost_shape', lambda r: r.update(cost=[]), ['INVALID_RECORD'])
observe('new_model_calls_nonzero', lambda r: r['cost'].update(model_calls=1), ['FAIL'])
observe('new_final_recovery_one_ref_missing',
        lambda r: r['fixture'].update(final_reads=r['fixture']['final_reads'][:-1]), ['FAIL'])
observe('new_move_denies_same_root_ids',
        lambda r: scene(r, 'S2')['evidence']['move'].update(same_root_ids=False), ['FAIL'])
observe('new_move_denies_same_relative_paths',
        lambda r: scene(r, 'S2')['evidence']['move'].update(same_relative_paths=False), ['FAIL'])
observe('new_policy_change_is_auth_gate',
        lambda r: scene(r, 'S2')['evidence']['policy_observation'].update(change_is_auth_gate=True), ['FAIL'])
observe('new_old_ref_identity_not_preserved',
        lambda r: scene(r, 'S2')['evidence']['reads_after_move'][0].update(ref_identity_preserved=False), ['FAIL'])

# Accurate incomplete reports should remain honest, not be fabricated PASS.
observe('honest_PARTIAL_control', lambda r: scene(r, 'S2').update(status='PARTIAL',
        failure={'code': 'synthetic_gap', 'detail': 'coverage unavailable'}), ['PARTIAL'])
observe('honest_UNKNOWN_control', lambda r: scene(r, 'S3').update(status='UNKNOWN'), ['UNKNOWN'])

pure_summary = {'schema_version': 'w06-portability-independent-pure/1',
                'results': observations,
                'unexpected': [r for r in observations if not r['as_expected']]}
(HERE / 'oracle-results-final.json').write_text(json.dumps(pure_summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'pure_cases': len(observations),
                  'unexpected': [{'name': r['name'], 'actual': r['actual']} for r in pure_summary['unexpected']]}, ensure_ascii=False), flush=True)

scratch = Path(tempfile.mkdtemp(prefix='w6-pind-', dir='C:/Users/郑曾波/Projects/company-wiki/.tmp')).resolve()
scratch_parent = scratch.parent
runtime_results = {}
cat_open = None
owned_attempt = None
blocked = []
try:
    owned, output = scratch / 'owned', scratch / 'output'
    names = ('cfg', 'lake_A', 'lake_B', 'catalog', 'logs', 'scratch')
    sentinels = {}
    empty_dirs = []
    for name in names:
        p = owned / name / 'keep.bin'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'independent baseline ' + name.encode())
        sentinels[str(p.relative_to(scratch))] = sha(p)
        q = p.parent / 'empty'
        q.mkdir()
        empty_dirs.append(q)
    marker = output / 'keep.bin'
    marker.parent.mkdir()
    marker.write_bytes(b'independent output baseline')
    sentinels[str(marker.relative_to(scratch))] = sha(marker)
    baseline = run.snapshot_baseline(owned)
    assert run.cleanup_owned_root(owned, baseline) == (True, True)
    assert all(sha(scratch / p) == h for p, h in sentinels.items())
    assert all(p.is_dir() for p in empty_dirs)
    runtime_results['legacy_cleanup_sentinels_preserved'] = True
    owned_attempt = OwnedAttempt(owned)
    env = child_env(WORKTREE, owned_attempt.path / 'runtime')
    env_names = sorted(env)
    assert not any(('KEY' in key or 'TOKEN' in key or 'SECRET' in key) for key in env_names)
    assert Path(env['HOME']).is_relative_to(owned_attempt.path)
    assert Path(env['TEMP']).is_relative_to(owned_attempt.path)
    assert env['PYTHON_DOTENV_DISABLED'] == '1'
    runtime_results['minimal_env_names'] = env_names
    runtime_results['synthetic_home_temp'] = True
    with synthetic_environment(env), offline_guard() as blocked:
        lake = build_fixture(owned_attempt.path)
        harness = scenarios.Harness(owned_attempt.path, output / 'independent', lake)
        cat_open = harness
        harness.open_catalog(lake.config_path)
        for root_id in lake.root_dirs:
            harness.register(root_id, {d.relative_path for d in lake.docs.values() if d.root_id == root_id})
        doc = lake.docs['txt']
        ref = harness.ref_for(doc)
        ref_results = []
        for name, payload, expected_reason in (
            ('valid_full_ref', ref, None),
            ('wrong_byte_size', replace(ref, byte_size=ref.byte_size + 1), 'source_ref_changed'),
            ('wrong_mime_type', replace(ref, mime_type='application/pdf'), 'source_ref_changed'),
            ('wrong_schema_version', replace(ref, schema_version='1.0'), 'unsupported_version'),
        ):
            before_queries = harness.reader.calls.get('query_ref', 0)
            probe = harness.consumer_probe(payload, name)
            after_queries = harness.reader.calls.get('query_ref', 0)
            if expected_reason is None:
                assert probe['exit_code'] == 0
                assert probe['probe']['status'] == 'ok'
                assert probe['probe']['read_sha256'] == doc.content_sha256
                assert probe['probe']['byte_size'] == doc.byte_size
                assert probe['probe']['raw_non_reader_opens'] == 0
                assert any(entry['path_class'] == 'raw' for entry in probe['probe']['open_log'])
            else:
                assert probe['exit_code'] != 0
                assert probe['probe']['reason'] == expected_reason
            assert before_queries == after_queries
            ref_results.append({'name': name, 'expected_reason': expected_reason, 'actual': probe})
        runtime_results['actual_complete_ref_child_results'] = ref_results
        # Deliberately supply broken external CLI output: storage reads may not replace it.
        malformed_wire = {'schema_version': '2.0.0', 'manifests': [], 'bundle_sha256': 'a'*64}
        captured = json.dumps(malformed_wire).encode()
        original_run = scenarios.subprocess.run
        def wrong_export(argv, **kwargs):
            if 'company_wiki.source_catalog.source_export_v2_cli' in argv:
                return SimpleNamespace(returncode=0, stdout=captured, stderr=b'independent marker')
            return original_run(argv, **kwargs)
        with patch.object(scenarios.subprocess, 'run', wrong_export):
            actual = scenarios.scenario_s1(harness)['evidence']['export']
        assert actual['bundle'] == malformed_wire
        assert actual['manifests'] == []
        assert actual['stdout'].encode() == captured
        assert actual['stderr'] == 'independent marker'
        runtime_results['raw_CLI_failure_preserved'] = actual
        harness.close_catalog()
        cat_open = None
    restored, _ = run.cleanup_owned_root(owned, baseline, owned_attempt)
    assert restored
    runtime_results['owned_child_absent'] = not owned_attempt.path.exists()
    assert runtime_results['owned_child_absent']
    owned_attempt = None
    after_sentinels = {p: sha(scratch / p) for p in sentinels}
    assert after_sentinels == sentinels
    assert all(p.is_dir() for p in empty_dirs)
    runtime_results['sentinels_before'] = sentinels
    runtime_results['sentinels_after'] = after_sentinels
    runtime_results['all_six_empty_dirs_preserved'] = True
    # Disjointness is a runtime safety assertion, not permission machinery.
    untouched = scratch / 'untouched'
    overlap_results = []
    for a, b in ((untouched, untouched), (untouched, untouched / 'out'), (untouched / 'owned', untouched)):
        try:
            validate_roots(a, b)
            raise AssertionError('overlap unexpectedly accepted')
        except ValueError:
            overlap_results.append(True)
    assert not untouched.exists()
    runtime_results['all_three_overlap_refusals_without_write'] = overlap_results
except Exception as exc:
    runtime_results['unexpected_exception'] = {'type': type(exc).__name__, 'detail': str(exc)[:600]}
finally:
    if cat_open is not None:
        cat_open.close_catalog()
    if owned_attempt is not None:
        owned_attempt.cleanup()
    assert scratch.parent == Path('C:/Users/郑曾波/Projects/company-wiki/.tmp').resolve()
    assert scratch.parent == scratch_parent and scratch.name.startswith('w6-pind-')
    assert scratch.resolve() == scratch and not scratch.is_symlink()
    shutil.rmtree(scratch)
    runtime_results['scratch_restored_absent'] = not scratch.exists()

after = {item['path']: sha(WORKTREE / item['path']) for item in inputs}
assert after == before
assert all(sha(BASE / p) == h for p, h in old_sha.items())
result = {'schema_version': 'w06-portability-independent-final/1',
          'verdict': 'FAIL_NEW_ORACLE_EXPECTATION_CLASSIFICATION' if pure_summary['unexpected'] else
                     ('FAIL_RUNTIME' if 'unexpected_exception' in runtime_results else 'PASS_WITH_SCOPE'),
          'seconds': round(time.monotonic()-started, 3),
          'oracle_cases': observations,
          'runtime': runtime_results,
          'freeze_sha256': sha(FREEZE),
          'product_and_producer_before': before,
          'product_and_producer_after': after,
          'all_frozen_shas_match': before == after,
          'old_intake_preserved': True,
          'hygiene': {'blocked_actions': blocked, 'network_calls': 0, 'LLM_calls': 0,
                      'provider_calls': 0, 'fees_usd': 0, 'real_originals_accessed': 0},
          'author_final': {'tests': final['tests'], 'runner': final['runner'],
                           'real_report_sha256': sha(real_path),
                           'scene_statuses': final['runner_oracle']['statuses'],
                           'three_logical_sources_four_doc_keys': True},
          'scope': 'Windows synthetic tool/catalog/Reader/CLI only; no real OCR, LLM, cloud, POSIX or research certification'}
(HERE / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'verdict': result['verdict'], 'seconds': result['seconds'],
                  'oracle_case_count': len(observations),
                  'runtime_exception': runtime_results.get('unexpected_exception'),
                  'scratch_restored': runtime_results['scratch_restored_absent'],
                  'all_frozen_shas_match': before == after}, ensure_ascii=False), flush=True)
