"""Non-author scenarios. Shared source/server builders are setup only."""
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

import pytest

from support import narrative_batch_fixtures as source_fixtures
from support.narrative_batch_fixtures import (
    KEY, isolated_batch_directory, prepare_source_catalog,
    loopback_model_server as _loopback_model_server,
)
from company_wiki.automation.store import (
    AutomationStore, LeaseLostError, RuntimeGateClosedError, RuntimeGenerationError,
)
from company_wiki.automation.models import HandlerMetrics, HandlerOutcome, HandlerResult
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from tools.document_understanding_benchmark.holdout_acceptance import run_controller

loopback_model_server = _loopback_model_server
EVIDENCE = Path(__file__).parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def tree(root):
    return {str(p.relative_to(root)): digest(p.read_bytes()) for p in root.rglob('*') if p.is_file()}


def events(spec):
    return [json.loads(row) for row in (Path(spec['receipt_dir'])/'events.jsonl').read_text().splitlines()]


def account(result):
    native = result['native']
    return {
        'rows': len(native['reservations']), 'tokens': native['charged_tokens'],
        'micro_usd': native['charged_micro_usd'],
        'unknown': native.get('unknown_reservations', 0),
        'paid': [{k: r.get(k) for k in (
            'attempt_id', 'request_sha256', 'response_sha256', 'paid_response_pin',
            'usage_status', 'input_tokens', 'output_tokens', 'estimated_micro_usd')}
            for r in native['reservations']],
        'generations': native['generations'],
    }


def proof(name, value):
    target = EVIDENCE/'proofs'
    target.mkdir(exist_ok=True)
    (target/(name+'.json')).write_text(json.dumps(value, sort_keys=True, indent=2)+'\n', encoding='utf-8')


@pytest.fixture
def scenario(tmp_path_factory, loopback_model_server, monkeypatch):
    def rank_from_wire_only(data):
        assert data['schema_version'] == 'narrative-model-request/6'
        return {'decisions': [{'task': task['key'], 'priority': 'high', 'disposition': 'consider'}
                              for task in data['material']['tasks']]}

    monkeypatch.setattr(source_fixtures, 'response_draft', rank_from_wire_only)
    monkeypatch.setenv('DEEPSEEK_API_KEY', KEY)
    with isolated_batch_directory(tmp_path_factory) as root:
        state = prepare_source_catalog(root, one_source=True, include_policy=False)
        try:
            originals = {p: p.read_bytes() for p in state.raw_paths.values()}
            config = root/'llm.json'
            config.write_text(json.dumps({'llm': {
                'provider': 'deepseek', 'model': 'stub-model',
                'base_url': loopback_model_server.endpoint.removesuffix('/chat/completions'),
                'max_tokens': 400, 'temperature': 1.0,
                'generation_policy': {'deepseek': {'narrative': {'thinking': 'disabled'}}},
            }}), encoding='utf-8')
            ref = next(iter(state.indexed.values()))[0]
            spec = {
                'schema_version': 'holdout-acceptance-request/1', 'company': 'Independent Example',
                'audit_run_id': 'review-audit', 'audit_attempt_id': 'review-attempt',
                'batch_run_id': 'review-native', 'project_root': str(root),
                'catalog_config': str(state.config_path), 'automation_db': str(root/'AUTO.sqlite'),
                'work_root': str(root/'work'), 'receipt_dir': str(root/'receipts'),
                'llm_config': str(config), 'llm_provider': 'deepseek',
                'allow_local_model_http': True, 'as_of_date': '2026-10-22', 'source_ref': asdict(ref),
                'limits': {'max_seconds': 45, 'max_tokens': 200000, 'max_cost_usd': '1',
                    'max_final_bytes': 2097152, 'max_persistent_bytes': 67108864,
                    'max_scratch_bytes': 67108864, 'max_log_bytes': 1048576},
                'pricing': {'version': 'independent/1', 'input_micro_usd_per_million_tokens': 1000000,
                            'output_micro_usd_per_million_tokens': 2000000},
            }
            yield spec, state, loopback_model_server
            assert {p: p.read_bytes() for p in originals} == originals
        finally:
            state.catalog.close()


@pytest.mark.parametrize('unknown_usage', [False, True], ids=['known', 'unknown'])
def test_full_native_chain_exact_preview_new_lease_and_stale_worker(scenario, unknown_usage):
    spec, state, server = scenario
    if unknown_usage:
        server.response_usage = {}
    catalog_before = tree(state.catalog.config.catalog_dir)
    preview = run_controller(spec, stop_after='preflight')
    body = (Path(spec['receipt_dir'])/'model-input.json').read_bytes()
    envelope = json.loads(body)
    assert preview['status'] == 'preflight_ready', preview.get('reason')
    assert preview['preflight']['preview_kind'] == 'non-native'
    assert preview['preflight']['conservative_token_bound'] == len(body)+128+envelope['max_tokens']
    assert envelope['max_tokens'] == 400
    assert json.loads(envelope['messages'][1]['content'])['schema_version'] == 'narrative-model-request/6'
    assert preview['native']['run'] is None and not preview['native']['reservations']
    assert not Path(spec['automation_db']).exists()
    assert tree(state.catalog.config.catalog_dir) == catalog_before
    assert not server.requests
    # Exercise the actual native exact bound, not a large arbitrary allocation.
    spec['limits']['max_tokens'] = preview['preflight']['conservative_token_bound']
    first = run_controller(spec, stop_after='after_paid')
    assert first['status'] == 'paused_for_test', first.get('reason')
    assert first['stages'][0]['native_exit'] != 0
    paid_account = account(first)
    assert paid_account['rows'] == 1 and paid_account['paid'][0]['paid_response_pin']
    assert paid_account['unknown'] == int(unknown_usage)
    assert first['model_post_count'] == len(server.requests) == 1
    assert server.requests[0][1] == body
    first_events = events(spec)
    paid_event = next(e for e in first_events if e['event'] == 'after_paid')
    old_worker = AutomationStore(Path(spec['automation_db'])).get_attempt(paid_event['worker_attempt_id'])
    assert old_worker is not None and old_worker.outcome is HandlerOutcome.RETRYABLE

    pending = run_controller(spec, stop_after='activation_pending')
    assert pending['status'] == 'paused_for_test', pending.get('reason')
    assert pending['stages'][0]['receipt']['documents'][0]['status'] == 'activation_pending'
    assert account(pending) == paid_account
    pending_events = events(spec)
    recovered = next(e for e in pending_events if e['event'] == 'paid_recover')
    replayed = next(e for e in pending_events if e['event'] == 'paid_replay')
    assert recovered['paid_attempt_id'] == paid_account['paid'][0]['attempt_id']
    assert recovered['worker_attempt_id'] != paid_event['worker_attempt_id']
    assert recovered['pid'] != paid_event['pid']
    assert recovered['runtime_generation'] > paid_event['runtime_generation']
    assert recovered['body_sha256'] == replayed['body_sha256']
    new_worker = AutomationStore(Path(spec['automation_db'])).get_attempt(recovered['worker_attempt_id'])
    assert new_worker is not None and new_worker.job_id == old_worker.job_id
    assert new_worker.lease_token != old_worker.lease_token
    assert new_worker.runtime_generation > old_worker.runtime_generation
    # An old completed lease must not publish over the new valid recovery owner.
    # Bounded batch completion may first close its native runtime gate; that
    # explicit native refusal is valid too, and must not be bypassed by a test.
    with pytest.raises((LeaseLostError, RuntimeGenerationError, RuntimeGateClosedError)):
        AutomationStore(Path(spec['automation_db'])).finish_attempt(
            attempt_id=old_worker.attempt_id, lease_token=old_worker.lease_token,
            runtime_generation=old_worker.runtime_generation,
            finished_at=datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
            result=HandlerResult(HandlerOutcome.SUCCEEDED, {}, (), (), HandlerMetrics(0, 0, 0), None),
        )
    directly_observed = NarrativeRunStore(Path(spec['automation_db'])).budget_snapshot(spec['batch_run_id'])
    assert directly_observed.charged_tokens == paid_account['tokens']
    assert directly_observed.charged_micro_usd == paid_account['micro_usd']
    assert directly_observed.unknown_reservations == paid_account['unknown']
    final = run_controller(spec)
    assert final['status'] == 'passed', final.get('reason')
    assert account(final) == paid_account
    assert final['paid_replay'] == {'executed': True, 'new_reservations': 0, 'new_tokens': 0}
    assert final['cross_run_cache']['new_tokens'] == final['cross_run_cache']['new_reservations'] == 0
    assert final['activation_recovery']['artifact_ref'] == final['cross_run_cache']['artifact_ref']
    cache = next(s for s in final['stages'] if s['stage'] == 'cache')
    assert cache['before']['run'] is None
    assert not cache['after']['reservations'] and cache['after']['charged_micro_usd'] == 0
    assert final['public_read']['verified'] and final['rf_consumption']['status'] == 'not_consumed'
    assert final['model_post_count'] == len(server.requests) == 1 and not server.errors
    again = run_controller(spec)
    assert again['status'] == 'passed' and account(again) == paid_account
    assert again['model_post_count'] == len(server.requests) == 1
    proof('full-'+str(unknown_usage), {'preflight': preview['preflight'], 'account': paid_account,
        'after_paid': paid_event, 'recovered': recovered, 'replayed': replayed,
        'final_status': final['status'], 'post_count': len(server.requests),
        'activation_recovery': final['activation_recovery'], 'cross_run_cache': final['cross_run_cache'],
        'public_read': final['public_read'], 'rf_consumption': final['rf_consumption'],
        'events': events(spec)})


@pytest.mark.parametrize('change', ['missing_pin_object', 'tampered_pin_object', 'changed_request', 'current_parent'])
def test_failed_reentry_is_repeatable_without_repost_or_unknown_refund(scenario, change):
    spec, state, server = scenario
    server.response_usage = {}
    first = run_controller(spec, stop_after='after_paid')
    assert first['status'] == 'paused_for_test', first.get('reason')
    baseline = account(first)
    assert baseline['unknown'] == 1 and baseline['rows'] == 1
    changed = None
    original = None
    if change == 'changed_request':
        spec = {**spec, 'limits': {**spec['limits'], 'max_tokens': 190000}}
    elif change == 'current_parent':
        changed = next(iter(state.raw_paths.values()))
        original = changed.read_bytes()
        changed.write_bytes(original + b' test-only changed parent')
    else:
        pin = baseline['paid'][0]['paid_response_pin']
        changed = state.catalog.config.catalog_dir/pin['object_key']
        assert changed.resolve().is_relative_to(state.catalog.config.catalog_dir.resolve())
        original = changed.read_bytes()
        if change == 'missing_pin_object':
            changed.unlink()
        else:
            changed.write_bytes(b'independent test damaged response bytes')
    results = []
    try:
        for _ in range(2):
            result = run_controller(spec)
            results.append({'status': result['status'], 'reason': result.get('reason'),
                            'native_causes': result['native_causes']})
            assert result['status'] == 'failed', result
            assert result['model_post_count'] == len(server.requests) == 1
            assert account(result) == baseline
            assert not any(row['event'] == 'post_refused' for row in events(spec))
    finally:
        if changed is not None and original is not None:
            changed.write_bytes(original)
    proof(change, {'reentries': results, 'account': baseline, 'posts': len(server.requests), 'events': events(spec)})


@pytest.mark.parametrize('field,new', [('max_tokens', 401), ('model', 'changed-stub-model')])
def test_formal_different_actual_body_refused_before_any_reservation(scenario, field, new):
    spec, _state, server = scenario
    preview = run_controller(spec, stop_after='preflight')
    assert preview['status'] == 'preflight_ready'
    config_path = Path(spec['llm_config'])
    config = json.loads(config_path.read_bytes())
    config['llm'][field] = new
    config_path.write_text(json.dumps(config), encoding='utf-8')
    result = run_controller(spec)
    assert result['status'] == 'failed' and result['reason'] == 'HOLDOUT_MODEL_INPUT_CHANGED'
    assert not result['native']['reservations'] and result['native']['charged_tokens'] == 0
    assert result['model_post_count'] == len(server.requests) == 0
    proof('body-'+field, {'reason': result['reason'], 'native': account(result), 'posts': len(server.requests)})


def test_insufficient_exact_preview_then_formal_never_posts_or_reserves(scenario):
    spec, state, server = scenario
    before = tree(state.catalog.config.catalog_dir)
    initial = run_controller(spec, stop_after='preflight')
    spec['limits']['max_tokens'] = initial['preflight']['conservative_token_bound']-1
    preview = run_controller(spec, stop_after='preflight')
    assert preview['status'] == 'preflight_budget_exceeded'
    assert preview['preflight']['max_output_tokens'] == 400
    assert tree(state.catalog.config.catalog_dir) == before
    assert not Path(spec['automation_db']).exists() and not preview['native']['reservations']
    result = run_controller(spec)
    assert result['status'] == 'failed'
    assert not result['native']['reservations'] and result['native']['charged_tokens'] == 0
    assert result['model_post_count'] == len(server.requests) == 0
    assert not server.errors
    proof('budget-boundary', {'bound': initial['preflight'], 'preview': preview['status'],
        'formal_reason': result.get('reason'), 'native_causes': result['native_causes'],
        'account': account(result), 'posts': len(server.requests)})
