"""Finite, reentrant test-side acceptance of the configured narrative lifecycle.

The existing AUTO/catalog remain authoritative. This module stores observations,
not another fee ledger, and never initializes sources or downloads documents.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys

CODE_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'holdout-acceptance-request/1'


class ControllerError(ValueError):
    pass


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _events(root):
    path = root / 'events.jsonl'
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []


def _native(database, run_id):
    from company_wiki.automation.narrative_run_store import NarrativeRunStore
    if not database.exists():
        return {'run': None, 'reservations': [], 'generations': {}, 'charged_tokens': 0,
                'charged_micro_usd': 0}
    owner = NarrativeRunStore(database)
    run = owner.get_run(run_id)
    if run is None:
        return {'run': None, 'reservations': [], 'generations': {}, 'charged_tokens': 0,
                'charged_micro_usd': 0}
    rows = owner.reservations_for_run(run_id)
    reservations = []
    for row in rows:
        value = asdict(row)
        pin = value.pop('paid_response_json')
        value['paid_response_pin'] = json.loads(pin) if pin is not None else None
        reservations.append(value)
    budget = owner.budget_snapshot(run_id)
    return {'run': {'run_id': run.run_id, 'input_hash': run.input_hash,
                    'binding_sha256': hashlib.sha256(run.binding_json.encode()).hexdigest(),
                    'model_id': run.model_id, 'state': run.state},
            'reservations': reservations, 'generations': owner.final_generations(run_id),
            'charged_tokens': budget.charged_tokens, 'charged_micro_usd': budget.charged_micro_usd,
            'unknown_reservations': budget.unknown_reservations}


def _identity(snapshot):
    fields = ('attempt_id', 'request_sha256', 'response_sha256', 'paid_response_pin',
              'usage_status', 'input_tokens', 'output_tokens', 'estimated_micro_usd')
    return [{key: row[key] for key in fields} for row in snapshot['reservations']]


def _validate(spec):
    required = {'schema_version', 'company', 'audit_run_id', 'audit_attempt_id', 'batch_run_id',
                'project_root', 'catalog_config', 'automation_db', 'work_root', 'receipt_dir',
                'llm_config', 'llm_provider', 'as_of_date', 'source_ref', 'limits', 'pricing'}
    if not isinstance(spec, dict) or not required <= spec.keys() or spec['schema_version'] != SCHEMA:
        raise ControllerError('HOLDOUT_INVALID_SPEC')
    if spec.keys() - (required | {'allow_local_model_http', 'expected_source'}):
        raise ControllerError('HOLDOUT_UNKNOWN_SPEC_FIELDS')
    for key in ('audit_run_id', 'audit_attempt_id', 'batch_run_id'):
        if not isinstance(spec[key], str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', spec[key]):
            raise ControllerError('HOLDOUT_INVALID_IDENTIFIER')
    date.fromisoformat(spec['as_of_date'])
    if spec['llm_provider'] not in ('deepseek', 'mimo', 'minimax', 'openai'):
        raise ControllerError('HOLDOUT_INVALID_PROVIDER')
    for key in ('project_root', 'catalog_config', 'llm_config'):
        if not Path(spec[key]).exists():
            raise ControllerError('HOLDOUT_EXISTING_INPUT_MISSING')
    if Path(spec['receipt_dir']).resolve() == Path(spec['work_root']).resolve():
        raise ControllerError('HOLDOUT_RECEIPT_WORK_OVERLAP')
    limits = spec['limits']
    if type(limits.get('max_log_bytes')) is not int or not 4096 <= limits['max_log_bytes'] <= 1048576:
        raise ControllerError('HOLDOUT_INVALID_LOG_BOUND')


def _process(command, *, env, root, output, label, timeout, payload=None, log_limit=1048576):
    process = subprocess.Popen(command, cwd=root, env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
        start_new_session=os.name != 'nt')
    try:
        stdout, stderr = process.communicate(None if payload is None else json.dumps(payload).encode(),
                                              timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, check=False)
        elif sys.platform != 'win32':
            # start_new_session makes this owned process the group leader.
            os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate(timeout=15)
        (output / (label + '.stderr.log')).write_bytes(stderr[:log_limit])
        raise ControllerError('HOLDOUT_OWNED_CLI_TIMEOUT') from None
    (output / (label + '.stderr.log')).write_bytes(stderr[:log_limit])
    _write(output / (label + '.command.json'), {'command': command, 'exit': process.returncode,
        'stdout_bytes': len(stdout), 'stdout_sha256': hashlib.sha256(stdout).hexdigest(),
        'stderr_bytes': len(stderr), 'stderr_truncated': len(stderr) > log_limit})
    if len(stdout) > max(log_limit, 2097152) or len(stderr) > log_limit:
        raise ControllerError('HOLDOUT_CLI_LOG_BOUND_EXCEEDED')
    return process.returncode, stdout, stderr


def _request(spec, run_id):
    limits = spec['limits']
    return {'schema_version': 'narrative-batch-request/1', 'run_id': run_id,
        'sources': [spec['source_ref']], 'selector_version': '0.9.0',
        'reading_model_projection': 'reading-model-input/5', 'profile': 'P1',
        **{key: limits[key] for key in ('max_seconds', 'max_tokens', 'max_cost_usd',
              'max_final_bytes', 'max_persistent_bytes', 'max_scratch_bytes')},
        'model': {}, 'pricing': spec['pricing']}


def run_controller(spec, *, stop_after=None):
    """Observe one paid call, paid replay, activation recovery and a cache run.

    Reentry consults native state and immutable event observations. Runtime pause
    uses the existing public gate after a real RETRYABLE result, not SQL edits.
    No supplier authorization, company fact, gold or availability claim is added.
    """
    _validate(spec)
    if stop_after not in (None, 'preflight', 'after_paid', 'activation_pending'):
        raise ControllerError('HOLDOUT_INVALID_STOP_STAGE')
    root = Path(spec['receipt_dir']).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = Path(spec['automation_db']).resolve()
    run_id = spec['batch_run_id']
    bootstrap = root / 'bootstrap'
    bootstrap.mkdir(exist_ok=True)
    (bootstrap / 'sitecustomize.py').write_text(
        'from tools.document_understanding_benchmark.holdout_acceptance_observer import install\ninstall()\n',
        encoding='utf-8')
    observer = root / 'observer.json'
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(map(str,
        (bootstrap, CODE_ROOT, CODE_ROOT/'src', CODE_ROOT/'scripts'))),
        PYTHONDONTWRITEBYTECODE='1', PYTHON_DOTENV_DISABLED='1',
        CWP_HOLDOUT_CONTROLLER=str(observer))
    result = {'schema_version': 'holdout-acceptance-result/1', 'status': 'running',
        'company': spec['company'], 'audit_run_id': spec['audit_run_id'],
        'audit_attempt_id': spec['audit_attempt_id'], 'batch_run_id': run_id,
        'as_of_date': spec['as_of_date'], 'source_ref': spec['source_ref'],
        'fingerprints': {'catalog_config': _digest(Path(spec['catalog_config'])),
                         'llm_config': _digest(Path(spec['llm_config']))},
        'stages': [], 'rf_consumption': {'status': 'not_consumed',
            'reason': 'ROOT must bind this public read to an actually used RF parameter and segment formula'}}
    initial_fingerprints = dict(result['fingerprints'])

    def call(stage, selected_run=run_id):
        request = _request(spec, selected_run)
        digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        request_path = root / ('request-' + digest + '.json')
        _write(request_path, request)
        _write(observer, {'receipt_dir': str(root), 'stage': stage,
            'max_log_bytes': spec['limits']['max_log_bytes'],
            'allow_local_model_http': spec.get('allow_local_model_http', False)})
        command = [sys.executable, '-B', '-X', 'utf8', '-m',
            'tools.document_understanding_benchmark.holdout_acceptance_launcher',
            '--llm-config', str(Path(spec['llm_config']).resolve()),
            '--llm-provider', spec['llm_provider'], '--project-root', spec['project_root'],
            '--catalog-config', spec['catalog_config'], '--automation-db', str(database),
            '--work-dir', str(Path(spec['work_root'])/selected_run), '--request', str(request_path)]
        if spec.get('allow_local_model_http'):
            command.append('--allow-local-model-http')
        number = len(list(root.glob('cli-*.command.json'))) + 1
        label = f'cli-{number:03}-{stage}'
        before = _native(database, selected_run)
        code, stdout, _stderr = _process(command, env=env, root=Path(spec['project_root']), output=root, label=label,
            timeout=spec['limits']['max_seconds'] + 30, log_limit=spec['limits']['max_log_bytes'])
        try:
            receipt = json.loads(stdout)
        except (UnicodeError, ValueError):
            raise ControllerError('HOLDOUT_NATIVE_STDOUT_NOT_JSON') from None
        _write(root / (label + '.result.json'), receipt)
        after = _native(database, selected_run)
        observation = {'stage': stage, 'native_exit': code, 'receipt': receipt,
                       'before': before, 'after': after, 'request_sha256': _digest(request_path)}
        _write(root / (label + '.native.json'), observation)
        result['stages'].append(observation)
        return observation

    def require(condition, code):
        if not condition:
            raise ControllerError(code)

    try:
        if stop_after == 'preflight':
            from tools.document_understanding_benchmark.holdout_acceptance_contracts import configured_preview
            require(_native(database, run_id)['run'] is None, 'HOLDOUT_PREFLIGHT_FORMAL_RUN_ALREADY_EXISTS')
            body, facts = configured_preview(spec, _request(spec, run_id))
            body_path = root / 'model-input.json'
            require(not body_path.exists() or body_path.read_bytes() == body, 'HOLDOUT_MODEL_INPUT_CHANGED')
            body_path.write_bytes(body)
            facts['fits_token_limit'] = facts['conservative_token_bound'] <= spec['limits']['max_tokens']
            result['preflight'] = facts
            _write(root / 'preflight.json', facts)
            if facts['fits_token_limit']:
                result['status'] = 'preflight_ready'
            else:
                result.update(status='preflight_budget_exceeded', reason='HOLDOUT_PREFLIGHT_TOKEN_BOUND_EXCEEDED')
        else:
            seen = _events(root)
            if not any(row['event'] == 'after_paid_paused' for row in seen):
                observed = call('after_paid')
                seen = _events(root)
                require(observed['native_exit'] != 0 and any(row['event'] == 'after_paid_paused' for row in seen),
                        'HOLDOUT_AFTER_PAID_BOUNDARY_NOT_REACHED')
            paid = _native(database, run_id)
            require(len(paid['reservations']) == 1 and paid['reservations'][0]['paid_response_pin'],
                    'HOLDOUT_NO_UNIQUE_DURABLE_PAID_PIN')
            from company_wiki.automation.models import HandlerOutcome
            from company_wiki.automation.store import AutomationStore
            boundary = next((row for row in reversed(seen) if row['event'] == 'after_paid_paused'), None)
            native_attempt = AutomationStore(database).get_attempt(boundary['attempt_id']) if boundary else None
            if native_attempt is None:
                raise ControllerError('HOLDOUT_NATIVE_RETRYABLE_NOT_PROVEN')
            require(native_attempt.outcome is HandlerOutcome.RETRYABLE
                    and native_attempt.error_code == 'IO_TRANSIENT'
                    and native_attempt.job_id == paid['reservations'][0]['job_id'],
                    'HOLDOUT_NATIVE_RETRYABLE_NOT_PROVEN')
            result['injected_fault'] = {'scope': 'test_local_after_paid', 'supplier_failure': False,
                'native_attempt_id': native_attempt.attempt_id, 'native_outcome': native_attempt.outcome.value,
                'native_error_code': native_attempt.error_code}

            require(all(value.get('reading_model_projection') == 'reading-model-input/5'
                        for value in paid['generations'].values()) and paid['generations'],
                    'HOLDOUT_NO_FROZEN_V5_GENERATION')
            if stop_after == 'after_paid':
                result['status'] = 'paused_for_test'
            else:
                if not any(row['event'] == 'activation_held' for row in seen):
                    observed = call('activation_pending')
                    require(observed['receipt']['documents'][0]['status'] == 'activation_pending',
                            'HOLDOUT_ACTIVATION_BOUNDARY_NOT_REACHED')
                seen = _events(root)
                replayed = _native(database, run_id)
                require(_identity(paid) == _identity(replayed), 'HOLDOUT_PAID_OPERATION_CHANGED')
                require(paid['generations'] == replayed['generations'], 'HOLDOUT_GENERATION_CHANGED')
                require(any(row['event'] == 'paid_recover' for row in seen)
                        and any(row['event'] == 'paid_replay' for row in seen),
                        'HOLDOUT_PAID_REPLAY_NOT_EXECUTED')
                result['paid_replay'] = {'executed': True, 'new_reservations': 0,
                                         'new_tokens': replayed['charged_tokens']-paid['charged_tokens']}
                if stop_after == 'activation_pending':
                    result['status'] = 'paused_for_test'
                else:
                    completed = call('complete')
                    require(completed['native_exit'] == 0 and completed['receipt']['status'] == 'completed',
                            'HOLDOUT_ACTIVATION_RECOVERY_FAILED')
                    require(_identity(paid) == _identity(completed['after']), 'HOLDOUT_FINAL_PAID_OPERATION_CHANGED')
                    artifact = completed['receipt']['documents'][0]['artifact_ref']
                    require(artifact is not None, 'HOLDOUT_FINAL_ARTIFACT_MISSING')
                    result['activation_recovery'] = {'executed': True, 'artifact_ref': artifact}
                    cached = call('cache', run_id + '-cache')
                    require(cached['native_exit'] == 0 and cached['receipt']['status'] == 'completed',
                            'HOLDOUT_CROSS_RUN_CACHE_FAILED')
                    require(not cached['after']['reservations'] and cached['after']['charged_tokens'] == 0,
                            'HOLDOUT_CACHE_CHARGED')
                    require(cached['receipt']['documents'][0]['artifact_ref'] == artifact,
                            'HOLDOUT_CACHE_ARTIFACT_CHANGED')
                    result['cross_run_cache'] = {'new_reservations': 0, 'new_tokens': 0,
                        'artifact_ref': artifact, 'run_id': run_id + '-cache'}
                    reference = {'schema_version': 'narrative-ref/1',
                        'artifact_version_id': artifact['artifact_version_id'],
                        'artifact_sha256': artifact.get('artifact_sha256', artifact.get('content_sha256')),
                        'byte_size': artifact['byte_size'], 'source_ref': spec['source_ref']}
                    from company_wiki.automation.narrative_transport_contracts import EXPECTED_SOURCE_FIELDS
                    constraints = {key: None for key in EXPECTED_SOURCE_FIELDS}
                    constraints.update(spec.get('expected_source', {}))
                    read_request = {'schema_version': 'narrative-read-request/1', 'narrative_ref': reference,
                        'as_of_date': spec['as_of_date'], 'expected_source': constraints}
                    _write(root / 'narrative-read-request.json', read_request)
                    # The public library has an explicit composition root. The
                    # transport CLI infers it from config/ placement and would
                    # misresolve a valid nonstandard isolated catalog.json path.
                    from company_wiki.source_catalog import SourceCatalog
                    from company_wiki.source_catalog.config import load_catalog_config
                    from company_wiki.source_catalog.source_reader import SourceVersionReader
                    from company_wiki.source_catalog.narrative_artifact_store import (
                        LocalNarrativeObjectStore, NarrativeArtifactStore)
                    from company_wiki.automation.narrative_transport import NarrativeTransportReader
                    from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest
                    catalog = SourceCatalog(load_catalog_config(Path(spec['catalog_config']),
                        project_root=Path(spec['project_root'])))
                    artifacts = NarrativeArtifactStore.for_reading(catalog.config.database_path,
                        LocalNarrativeObjectStore(catalog.config.catalog_dir))
                    try:
                        public = NarrativeTransportReader(artifacts, SourceVersionReader(catalog)).read(
                            NarrativeReadRequest.from_dict(read_request))
                        body, public_receipt = public.data, public.receipt
                    finally:
                        artifacts.close()
                        catalog.close()
                    require(hashlib.sha256(body).hexdigest() == reference['artifact_sha256'],
                            'HOLDOUT_PUBLIC_READ_FAILED')
                    _write(root / 'public-read.receipt.json', public_receipt)
                    require(public_receipt['replay_status'] == 'verified', 'HOLDOUT_PUBLIC_REPLAY_UNVERIFIED')
                    result['public_read'] = {'verified': True, 'receipt': public_receipt,
                        'request_path': str(root/'narrative-read-request.json'),
                        'reading_context_sha256': hashlib.sha256(json.dumps(json.loads(body)['reading_context'],
                            sort_keys=True).encode()).hexdigest()}
                    result['status'] = 'passed'
    except (ControllerError, ValueError, KeyError) as exc:
        result.update(status='failed', reason=str(exc))
    result['native'] = _native(database, run_id)
    result['preflight'] = result.get('preflight') or next((row for row in reversed(_events(root))
        if row['event'] == 'request_preflight'), None)
    events = _events(root)
    result['model_post_count'] = sum(row['event'] == 'http_post' for row in events)
    result['native_causes'] = [cause for stage in result['stages']
        for cause in ([stage['receipt'].get('error')] +
            [error for item in stage['receipt'].get('documents', []) for error in item.get('errors', [])])
        if cause]
    if any(row['event'] == 'request_preflight_mismatch' for row in events):
        result.update(status='failed', reason='HOLDOUT_MODEL_INPUT_CHANGED')
    elif any(row['event'] == 'post_refused' for row in events):
        result.update(status='failed', reason='HOLDOUT_SECOND_POST_REFUSED')
    elif result['status'] in ('passed', 'paused_for_test') and result['model_post_count'] != 1:
        result.update(status='failed', reason='HOLDOUT_ACTUAL_POST_COUNT_INVALID')
    elif result['status'] in ('preflight_ready', 'preflight_budget_exceeded') and result['model_post_count'] != 0:
        result.update(status='failed', reason='HOLDOUT_PREFLIGHT_POSTED')
    result['protected_configs_unchanged'] = initial_fingerprints == {
        'catalog_config': _digest(Path(spec['catalog_config'])), 'llm_config': _digest(Path(spec['llm_config']))}
    if not result['protected_configs_unchanged']:
        result.update(status='failed', reason='HOLDOUT_INPUT_CONFIG_CHANGED')
    _write(root / 'controller-result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True, type=Path)
    parser.add_argument('--stop-after', choices=('preflight', 'after_paid', 'activation_pending'))
    args = parser.parse_args()
    result = run_controller(json.loads(args.spec.read_text(encoding='utf-8')), stop_after=args.stop_after)
    print(json.dumps({'schema_version': result['schema_version'], 'status': result['status'],
                      'reason': result.get('reason'), 'model_post_count': result['model_post_count']}))
    return 0 if result['status'] in ('passed', 'paused_for_test', 'preflight_ready') else 2


if __name__ == '__main__':
    raise SystemExit(main())
