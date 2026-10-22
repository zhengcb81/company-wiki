"""Real configured HTTP/paid pin/outbox/cache, with synthetic source only."""
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from tools.document_understanding_benchmark.holdout_acceptance import run_controller
from support import narrative_batch_fixtures as fixtures
from support.narrative_batch_fixtures import (
    KEY, isolated_batch_directory, prepare_source_catalog,
    loopback_model_server as _loopback_model_server,
)

loopback_model_server = _loopback_model_server


@pytest.fixture
def prepared(tmp_path_factory, loopback_model_server, monkeypatch):
    def ranking(data):
        assert data['schema_version'] == 'narrative-model-request/6'
        return {'decisions': [{'task': task['key'], 'priority': 'high', 'disposition': 'consider'}
                              for task in data['material']['tasks']]}
    monkeypatch.setattr(fixtures, 'response_draft', ranking)
    monkeypatch.setenv('DEEPSEEK_API_KEY', KEY)
    monkeypatch.setenv('PYTHON_DOTENV_DISABLED', '1')
    with isolated_batch_directory(tmp_path_factory) as root:
        state = prepare_source_catalog(root, one_source=True, include_policy=False)
        try:
            original = {path: path.read_bytes() for path in state.raw_paths.values()}
            config = root / 'llm.json'
            config.write_text(json.dumps({'llm': {'provider': 'deepseek', 'model': 'stub-model',
                'base_url': loopback_model_server.endpoint.removesuffix('/chat/completions'),
                'max_tokens': 400, 'temperature': 1.0,
                'generation_policy': {'deepseek': {'narrative': {'thinking': 'disabled'}}}}}), encoding='utf-8')
            ref = next(iter(state.indexed.values()))[0]
            spec = {'schema_version': 'holdout-acceptance-request/1', 'company': 'Example Holdings',
                'audit_run_id': 'offline-audit', 'audit_attempt_id': 'attempt-one', 'batch_run_id': 'offline-v5',
                'project_root': str(root), 'catalog_config': str(state.config_path),
                'automation_db': str(root/'AUTO.sqlite'), 'work_root': str(root/'work'),
                'receipt_dir': str(root/'receipts'), 'llm_config': str(config), 'llm_provider': 'deepseek',
                'allow_local_model_http': True, 'as_of_date': '2026-10-22', 'source_ref': asdict(ref),
                'limits': {'max_seconds': 45, 'max_tokens': 200000, 'max_cost_usd': '1',
                    'max_final_bytes': 2097152, 'max_persistent_bytes': 67108864,
                    'max_scratch_bytes': 67108864, 'max_log_bytes': 1048576},
                'pricing': {'version': 'offline/1', 'input_micro_usd_per_million_tokens': 1000000,
                            'output_micro_usd_per_million_tokens': 2000000}}
            yield spec, state, loopback_model_server
            assert {path: path.read_bytes() for path in original} == original
        finally:
            state.catalog.close()


def test_controller_requires_real_configured_paid_replay_activation_and_cache(prepared):
    spec, _state, server = prepared
    result = run_controller(spec)
    assert result['status'] == 'passed', json.dumps({'reason': result.get('reason'), 'stages': [{'stage': row['stage'], 'exit': row['native_exit'], 'receipt': row['receipt']} for row in result['stages']], 'posts': result['model_post_count']})
    assert result['model_post_count'] == len(server.requests) == 1
    assert not server.errors
    assert result['paid_replay']['executed'] is True
    assert result['activation_recovery']['executed'] is True
    assert result['cross_run_cache']['new_reservations'] == 0
    assert result['cross_run_cache']['new_tokens'] == 0
    assert result['rf_consumption']['status'] == 'not_consumed'
    assert result['native']['reservations'][0]['paid_response_pin']
    assert result['native']['generations'][spec['source_ref']['document_id']]['reading_model_projection'] == 'reading-model-input/5'
    print('HOLDOUT_LIFECYCLE_PROOF ' + json.dumps({
        'source_ref': spec['source_ref'], 'model_post_count': result['model_post_count'],
        'paid_operation': result['native']['reservations'][0],
        'generation': result['native']['generations'][spec['source_ref']['document_id']],
        'paid_replay': result['paid_replay'], 'activation_recovery': result['activation_recovery'],
        'cross_run_cache': result['cross_run_cache'], 'public_read': result['public_read'],
        'protected_configs_unchanged': result['protected_configs_unchanged'],
        'rf_consumption': result['rf_consumption']}, sort_keys=True))



def test_controller_resumes_from_observed_paid_pause_without_another_post(prepared):
    spec, _state, server = prepared
    paused = run_controller(spec, stop_after='after_paid')
    assert paused['status'] == 'paused_for_test', paused
    assert paused['native']['reservations'][0]['paid_response_pin']
    original_paid = paused['native']['reservations'][0]['attempt_id']
    result = run_controller(spec)
    assert result['status'] == 'passed', json.dumps({'reason': result.get('reason'), 'stages': [{'stage': row['stage'], 'exit': row['native_exit'], 'receipt': row['receipt']} for row in result['stages']], 'posts': result['model_post_count']})
    assert result['native']['reservations'][0]['attempt_id'] == original_paid
    assert result['model_post_count'] == len(server.requests) == 1
    again = run_controller(spec)
    assert again['status'] == 'passed', again
    assert again['model_post_count'] == len(server.requests) == 1


@pytest.mark.parametrize('change', ['missing_body', 'tampered_body', 'changed_request', 'current_parent'])
def test_incomplete_paid_replay_never_reposts_or_refunds(prepared, change):
    spec, state, server = prepared
    paused = run_controller(spec, stop_after='after_paid')
    assert paused['status'] == 'paused_for_test', paused
    before = paused['native']['charged_tokens'], paused['native']['charged_micro_usd']
    pin = paused['native']['reservations'][0]['paid_response_pin']
    if change == 'changed_request':
        spec = {**spec, 'limits': {**spec['limits'], 'max_tokens': 190000}}
    elif change == 'current_parent':
        target = next(iter(state.raw_paths.values()))
        original = target.read_bytes()
        target.write_bytes(original + b' changed owned fixture')
    else:
        target = state.catalog.config.catalog_dir / pin['object_key']
        assert target.resolve().is_relative_to(state.catalog.config.catalog_dir.resolve())
        if change == 'missing_body':
            target.unlink()
        else:
            target.write_bytes(b'changed test-only paid object')
    try:
        result = run_controller(spec)
    finally:
        if change == 'current_parent':
            target.write_bytes(original)
    assert result['status'] == 'failed', result
    assert result['model_post_count'] == len(server.requests) == 1
    assert (result['native']['charged_tokens'], result['native']['charged_micro_usd']) == before
    assert len(result['native']['reservations']) == 1




def test_unknown_usage_hold_survives_real_paid_replay_and_cache(prepared):
    spec, _state, server = prepared
    server.response_usage = {}
    paused = run_controller(spec, stop_after='after_paid')
    assert paused['status'] == 'paused_for_test', paused
    assert paused['native']['unknown_reservations'] == 1
    held = paused['native']['charged_tokens'], paused['native']['charged_micro_usd']
    result = run_controller(spec)
    assert result['status'] == 'passed', result.get('reason')
    assert result['native']['unknown_reservations'] == 1
    assert (result['native']['charged_tokens'], result['native']['charged_micro_usd']) == held
    assert result['model_post_count'] == len(server.requests) == 1


def test_preflight_is_non_native_and_formal_configured_body_is_identical(prepared):
    spec, state, server = prepared
    catalog_root = state.catalog.config.catalog_dir
    before = {path.relative_to(catalog_root): path.read_bytes() for path in catalog_root.rglob('*') if path.is_file()}
    preview = run_controller(spec, stop_after='preflight')
    assert {path.relative_to(catalog_root): path.read_bytes() for path in catalog_root.rglob('*') if path.is_file()} == before
    assert not Path(spec['automation_db']).exists()
    assert not (state.catalog.config.catalog_dir/'narrative-generations').exists()
    assert preview['status'] == 'preflight_ready', preview
    assert preview['model_post_count'] == len(server.requests) == 0
    assert not preview['native']['reservations']
    assert preview['native']['run'] is None
    assert preview['preflight']['preview_kind'] == 'non-native'
    body = (Path(spec['receipt_dir'])/'model-input.json').read_bytes()
    observed = preview['preflight']
    assert observed['conservative_token_bound'] == len(body) + 128 + json.loads(body)['max_tokens']
    assert observed['max_output_tokens'] == 400  # configured fixture, unchanged by controller
    result = run_controller(spec)
    assert result['status'] == 'passed', json.dumps(result)
    assert result['model_post_count'] == len(server.requests) == 1
    assert server.requests[0][1] == body
    assert result['preflight']['http_body_sha256'] == observed['http_body_sha256']


@pytest.mark.parametrize('change', ['configured_output', 'token_limit'])
def test_preflight_mismatch_or_budget_is_explicit_and_never_posts(prepared, change):
    spec, _state, server = prepared
    if change == 'token_limit':
        spec['limits']['max_tokens'] = 1
    preview = run_controller(spec, stop_after='preflight')
    assert preview['model_post_count'] == len(server.requests) == 0
    assert not preview['native']['reservations']
    assert preview['native']['run'] is None
    assert preview['preflight']['max_output_tokens'] == 400
    if change == 'token_limit':
        assert preview['status'] == 'preflight_budget_exceeded'
        assert preview['reason'] == 'HOLDOUT_PREFLIGHT_TOKEN_BOUND_EXCEEDED'
    else:
        assert preview['status'] == 'preflight_ready'
        config_path = Path(spec['llm_config'])
        config = json.loads(config_path.read_bytes())
        config['llm']['max_tokens'] = 401
        config_path.write_text(json.dumps(config), encoding='utf-8')
        result = run_controller(spec)
        assert result['status'] == 'failed'
        assert result['reason'] == 'HOLDOUT_MODEL_INPUT_CHANGED'
        assert not result['native']['reservations']
        assert result['model_post_count'] == len(server.requests) == 0
