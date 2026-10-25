"""Test-only faults and observations inherited by the owned batch workers.

No gold, provider headers, credential values, or production flag is involved.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
from pathlib import Path
import socket

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    config_path = os.environ.get('CWP_HOLDOUT_CONTROLLER')
    if _INSTALLED or not config_path:
        return
    config = json.loads(Path(config_path).read_text(encoding='utf-8'))
    root = Path(config['receipt_dir']).resolve()
    events = root / 'events.jsonl'

    def event(kind, **fields):
        body = json.dumps({'event': kind, 'stage': config['stage'], 'pid': os.getpid(), **fields},
                          sort_keys=True, separators=(',', ':')).encode('utf-8') + b'\n'
        if events.exists() and events.stat().st_size + len(body) > config['max_log_bytes']:
            raise RuntimeError('HOLDOUT_EVENT_BYTES_EXCEEDED')
        with events.open('ab') as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())

    original_request = http.client.HTTPConnection.request

    def observed_http(connection, method, url, body=None, headers=None, **kwargs):
        if method.upper() == 'POST':
            body_path = root / 'model-input.json'
            if not isinstance(body, bytes):
                raise RuntimeError('HOLDOUT_HTTP_BODY_NOT_BYTES')
            if body_path.exists() and body_path.read_bytes() != body:
                event('request_preflight_mismatch', expected_body_sha256=hashlib.sha256(body_path.read_bytes()).hexdigest(),
                      actual_body_sha256=hashlib.sha256(body).hexdigest(), actual_body_bytes=len(body))
                raise RuntimeError('HOLDOUT_MODEL_INPUT_CHANGED')
            # The only resend guard is at the real transport boundary. Paid
            # generate/_recover/replay_response are allowed to run normally.
            latch = root / 'post-once'
            try:
                fd = os.open(latch, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                event('post_refused')
                raise RuntimeError('HOLDOUT_SECOND_POST_REFUSED') from None
            with os.fdopen(fd, 'wb') as stream:
                stream.write(b'one actual POST attempted\n')
                stream.flush()
                os.fsync(stream.fileno())
            envelope = json.loads(body)
            material = json.loads(envelope['messages'][1]['content'])
            if material['schema_version'] != 'narrative-model-request/5':
                raise RuntimeError('HOLDOUT_MODEL_SCHEMA_MISMATCH')
            event('http_post', body_sha256=hashlib.sha256(body).hexdigest(),
                  body_bytes=len(body), request_schema=material['schema_version'],
                  model_id=envelope['model'], max_output_tokens=envelope.get('max_tokens',
                      envelope.get('max_completion_tokens')), task_count=len(material['material']['tasks']))
            # Exact secret-free input is retained once, not as another raw lake.
            if not body_path.exists():
                body_path.write_bytes(body)
        return original_request(connection, method, url, body=body, headers=headers or {}, **kwargs)

    setattr(http.client.HTTPConnection, 'request', observed_http)
    if config['allow_local_model_http']:
        original_connect = socket.socket.connect

        def local_only(sock, address):
            if address[0] not in ('127.0.0.1', '::1'):
                raise RuntimeError('HOLDOUT_OFFLINE_EXTERNAL_SOCKET_REFUSED')
            return original_connect(sock, address)

        setattr(socket.socket, 'connect', local_only)

    from company_wiki.automation.models import HandlerOutcome, RuntimeState
    from company_wiki.automation.narrative_model_caller import BudgetedNarrativeCaller, NarrativeBudgetCallError
    from company_wiki.automation.narrative_http_model import NarrativeHTTPModel
    from company_wiki.automation.narrative_paid_response import PaidResponsePin
    from company_wiki.automation.store import AutomationStore

    from tools.document_understanding_benchmark.holdout_acceptance_contracts import request_preflight

    owned_after_paid = {}  # This process only; never a supplier error or stored permission.
    original_generate = BudgetedNarrativeCaller.generate

    def observed_generate(caller, context, request):
        body, facts = request_preflight(caller._model, request)
        body_path = root / 'model-input.json'
        if body_path.exists() and body_path.read_bytes() != body:
            event('request_preflight_mismatch', expected_body_sha256=hashlib.sha256(body_path.read_bytes()).hexdigest(),
                  actual_body_sha256=facts['http_body_sha256'], actual_body_bytes=len(body),
                  actual_max_output_tokens=facts['max_output_tokens'])
            raise RuntimeError('HOLDOUT_MODEL_INPUT_CHANGED')
        if not body_path.exists():
            body_path.write_bytes(body)
        event('request_preflight', **facts, run_id=caller._run_id,
              worker_attempt_id=context.attempt.attempt_id)
        response, metrics = original_generate(caller, context, request)
        if config['stage'] == 'after_paid':
            records = caller._store.reservations_for_run(caller._run_id)
            matching = [row for row in records if row.job_id == context.job.job_id]
            if len(matching) != 1 or not matching[0].paid_response_json:
                raise RuntimeError('HOLDOUT_PAID_PIN_NOT_DURABLE')
            record = matching[0]
            pin = PaidResponsePin.from_json(record.paid_response_json)
            event('after_paid', attempt_id=record.attempt_id, request_sha256=record.request_sha256,
                  body_sha256=pin.body_sha256, usage_status=record.usage_status,
                  charged_tokens=record.charged_tokens, charged_micro_usd=record.charged_micro_usd,
                  worker_attempt_id=context.attempt.attempt_id,
                  runtime_generation=context.attempt.runtime_generation,
                  injected_error_code='IO_TRANSIENT', fault_scope='test_local_after_paid', supplier_failure=False)
            owned_after_paid[context.attempt.attempt_id] = (context.job.job_id, context.attempt.lease_token,
                context.attempt.runtime_generation)
            raise NarrativeBudgetCallError('IO_TRANSIENT', HandlerOutcome.RETRYABLE, metrics)
        return response, metrics

    setattr(BudgetedNarrativeCaller, 'generate', observed_generate)
    original_recover = BudgetedNarrativeCaller._recover

    def observed_recover(caller, context, request, request_sha256):
        result = original_recover(caller, context, request, request_sha256)
        if result is not None:
            record, pin, _ = result
            event('paid_recover', paid_attempt_id=record.attempt_id,
                  worker_attempt_id=context.attempt.attempt_id,
                  request_sha256=request_sha256, body_sha256=pin.body_sha256,
                  runtime_generation=context.attempt.runtime_generation)
        return result

    setattr(BudgetedNarrativeCaller, '_recover', observed_recover)
    original_replay = NarrativeHTTPModel.replay_response

    def observed_replay(model, request, body, *, http_status, duration_ms):
        result = original_replay(model, request, body, http_status=http_status, duration_ms=duration_ms)
        event('paid_replay', body_sha256=hashlib.sha256(body).hexdigest(),
              response_sha256=result.response_sha256, request_input_sha256=request.input_sha256)
        return result

    setattr(NarrativeHTTPModel, 'replay_response', observed_replay)
    original_finish = AutomationStore.finish_attempt

    def finish_and_pause(store, *args, **kwargs):
        result = original_finish(store, *args, **kwargs)
        marker = owned_after_paid.get(kwargs.get('attempt_id'))
        if config['stage'] == 'after_paid' and marker is not None:
            native = store.get_attempt(kwargs['attempt_id'])
            if (native is None or native.outcome is not HandlerOutcome.RETRYABLE
                    or native.error_code != 'IO_TRANSIENT' or native.finished_at is None
                    or (native.job_id, native.lease_token, native.runtime_generation) != marker):
                event('after_paid_native_outcome_invalid', attempt_id=kwargs['attempt_id'])
                raise RuntimeError('HOLDOUT_NATIVE_RETRYABLE_NOT_PROVEN')
            # Only this process's injected attempt, after the native classified
            # RETRYABLE finish committed. Unrelated IO failures cannot pause it.
            gate = store.set_runtime_gate(RuntimeState.PAUSED, updated_at=kwargs['finished_at'])
            owned_after_paid.pop(native.attempt_id)
            event('after_paid_paused', attempt_id=native.attempt_id,
                  native_outcome=native.outcome.value, native_error_code=native.error_code,
                  fault_scope='test_local_after_paid', control_generation=gate.control_generation)
        return result

    setattr(AutomationStore, 'finish_attempt', finish_and_pause)
    if config['stage'] == 'activation_pending':
        from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactStore
        from company_wiki.source_catalog.lock import CatalogOperationLockedError

        def hold_activation(*_args, **_kwargs):
            event('activation_held')
            raise CatalogOperationLockedError('holdout test activation boundary')

        setattr(NarrativeArtifactStore, 'activate', hold_activation)
    _INSTALLED = True
