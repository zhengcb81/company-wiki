"""A paid native success is not permissioned by observer representation size."""
from copy import deepcopy
import gzip
import hashlib
import json

import pytest

from tools.document_understanding_benchmark import phase_c_runner as runner


def captured(tmp_path, raw):
    path = tmp_path / 'run.attempt.response.json.gz'
    path.write_bytes(gzip.compress(raw))
    digest = hashlib.sha256(raw).hexdigest()
    receipt = {'status': 'completed', 'documents': []}
    native = [{'attempt_id': 'attempt', 'response_sha256': digest,
               'usage_status': 'known', 'charged_tokens': 321, 'charged_micro_usd': 2000}]
    events = [{'event': 'model_final_observed', 'run_id': 'run', 'attempt_id': 'attempt',
               'final_sha256': digest, 'final_bytes': len(raw)}]
    return path, receipt, native, events


def test_complete_capture_over_old_cap_is_streamed_and_hash_bound(tmp_path, monkeypatch):
    raw = json.dumps({'draft': '完整原语言🙂' * 18000}, ensure_ascii=False).encode()
    assert len(raw) > 128 * 1024
    _, receipt, native, events = captured(tmp_path, raw)
    before = deepcopy((receipt, native, events))
    reads = []
    read = gzip.GzipFile.read

    def record_read(stream, size=-1):
        reads.append(size)
        return read(stream, size)

    monkeypatch.setattr(gzip.GzipFile, 'read', record_read)
    observed = runner.successful_model_observation(receipt, native, events, tmp_path, 'run',
        reading_model_projection='reading-model-input/4')
    assert observed['paid_response_capture'] == [{'attempt_id': 'attempt',
        'status': 'CAPTURED_AND_NATIVE_HASH_MATCHED', 'sha256': hashlib.sha256(raw).hexdigest(),
        'bytes': len(raw), 'usage_status': 'known'}]
    assert len(reads) > 2 and all(0 < size <= 65536 for size in reads)
    assert '完整原语言' not in json.dumps(observed, ensure_ascii=False)
    assert (receipt, native, events) == before


@pytest.mark.parametrize('fault,reason', [
    ('missing', 'PHASE_C_CAPTURE_UNAVAILABLE'),
    ('broken_gzip', 'PHASE_C_CAPTURE_UNAVAILABLE'),
    ('native_hash', 'PHASE_C_CAPTURE_IDENTITY_DIFFERS'),
    ('event_bytes', 'PHASE_C_CAPTURE_IDENTITY_DIFFERS'),
    ('event_hash', 'PHASE_C_CAPTURE_IDENTITY_DIFFERS'),
    ('utf8', 'PHASE_C_CAPTURE_UTF8_INVALID'),
])
def test_real_capture_errors_remain_explicit_without_size_permission(tmp_path, fault, reason):
    raw = b'\xff\xfe' if fault == 'utf8' else b'{"final":"valid"}'
    path, receipt, native, events = captured(tmp_path, raw)
    if fault == 'missing':
        path.unlink()
    elif fault == 'broken_gzip':
        path.write_bytes(b'not a gzip stream')
    elif fault == 'native_hash':
        native[0]['response_sha256'] = 'e' * 64
    elif fault == 'event_bytes':
        events[0]['final_bytes'] += 1
    elif fault == 'event_hash':
        events[0]['final_sha256'] = 'e' * 64
    with pytest.raises(ValueError, match=reason):
        runner.successful_model_observation(receipt, native, events, tmp_path, 'run',
            reading_model_projection='reading-model-input/4')


@pytest.mark.parametrize('fault', ['missing_capture', 'malformed_events'])
def test_observation_io_or_event_failure_preserves_native_receipt_and_usage(tmp_path, fault):
    path, receipt, native, events = captured(tmp_path, b'{"final":"complete"}')
    event_path = tmp_path / 'events.jsonl'
    if fault == 'missing_capture':
        path.unlink()
        event_path.write_text(json.dumps(events[0]) + '\n', encoding='utf-8')
    else:
        event_path.write_text('{invalid observation detail', encoding='utf-8')
    state = {'exit': 0, 'receipt': receipt, 'native_usage': native}
    before = deepcopy(state)
    runner.record_successful_model_observation(state, receipt, native, event_path, tmp_path, 'run',
        reading_model_projection='reading-model-input/4')
    assert {k: state[k] for k in before} == before
    assert state['model_observation']['status'] == 'INCOMPLETE'
    assert state['model_observation']['native_exit'] == 0
    assert state['model_observation']['native_batch_status'] == 'completed'
    assert state['model_observation']['reason'] == (
        'PHASE_C_CAPTURE_UNAVAILABLE' if fault == 'missing_capture' else 'PHASE_C_OBSERVATION_FAILED')
    assert 'paid_response_capture' not in state
    assert 'invalid observation detail' not in json.dumps(state)


@pytest.mark.timeout(120)
def test_real_owned_run_keeps_native_success_and_cache_after_observer_failure(tmp_path_factory, monkeypatch):
    # The child batch creates nested worker paths. Use a short pytest-owned root.
    tmp_path = tmp_path_factory.mktemp('pc')
    monkeypatch.setattr(runner.tempfile, 'gettempdir', lambda: str(tmp_path))
    monkeypatch.setattr(runner, 'seed_identity', lambda *args, **kwargs: {})
    observed = []

    def observer_fails(receipt, native, events, *_args, **_kwargs):
        assert receipt['status'] == 'completed' and native
        observed.append(deepcopy(native))
        raise OSError('untrusted observation detail must not enter the report')

    monkeypatch.setattr(runner, 'successful_model_observation', observer_fails)
    metadata = runner.loopback_preparation()
    provider = next(row for row in metadata['providers'] if row['provider'] == 'deepseek')
    output = tmp_path / 'receipts'
    output.mkdir()
    with runner.Loopback() as server:
        result = runner.run_pair({'sample_id': 'loopback-fixture'}, provider, metadata,
            mode='loopback', output=output, fixture_endpoint=server.endpoint,
            selected_versions='0.9.0', reading_model_projection='reading-model-input/5')
        assert len(server.requests) == 1, (
            result.get('error'), [state['receipt'] for state in result['states']],
        )
    assert len(observed) == 1
    assert result['status'] == 'OBSERVATION_INCOMPLETE', result
    state = result['states'][0]
    assert state['exit'] == 0 and state['receipt']['status'] == 'completed'
    assert state['native_usage'] == observed[0]
    assert state['model_observation'] == {'status': 'INCOMPLETE', 'error_type': 'OSError',
        'reason': 'PHASE_C_OBSERVATION_FAILED', 'native_exit': 0, 'native_batch_status': 'completed'}
    assert state['same_run_zero_POST'] and state['cross_run_zero_POST']
    assert state['public_replay']
    assert result['model_post_attempts'] == 1 and result['temporary_lake_removed']
    assert 'untrusted observation detail' not in json.dumps(result)
    assert not list(tmp_path.glob('cwplC-*'))
    assert json.loads((output / 'receipt.json').read_text(encoding='utf-8')) == result
