"""Protocol results and native outcomes do not depend on diagnostic volume/I/O."""
from __future__ import annotations

import atexit
import hashlib
import http.client
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from company_wiki._bounded_process import ChildFailed, OutputLimitExceeded, pid_is_alive, run_bounded
from company_wiki.automation.models import HandlerOutcome
from company_wiki.automation.narrative_http_model import NarrativeHTTPModel
from company_wiki.automation.narrative_model_caller import BudgetedNarrativeCaller, NarrativeBudgetCallError
from company_wiki.automation.narrative_paid_response import PaidResponsePin
from company_wiki.automation.store import AutomationStore
from tools.document_understanding_benchmark import holdout_acceptance as controller
from tools.document_understanding_benchmark import holdout_acceptance_contracts as contracts
from tools.document_understanding_benchmark import holdout_acceptance_observer as observer


def _command(code):
    return [sys.executable, '-B', '-c', code]


def _spec(tmp_path):
    for filename in ('catalog.json','llm.json'):
        (tmp_path/filename).write_text('{}')
    return dict(schema_version='holdout-acceptance-request/1', company='Synthetic',
        audit_run_id='synthetic',audit_attempt_id='one',batch_run_id='native',
        project_root=str(tmp_path),catalog_config=str(tmp_path/'catalog.json'),
        automation_db=str(tmp_path/'never-created.sqlite'),work_root=str(tmp_path/'work'),
        receipt_dir=str(tmp_path/'receipts'),llm_config=str(tmp_path/'llm.json'),
        llm_provider='deepseek',as_of_date='2026-11-02',source_ref={},pricing={},
        limits=dict(max_log_bytes=4096,max_seconds=2,max_tokens=100,max_cost_usd='1',
                    max_final_bytes=100000,max_persistent_bytes=200000,max_scratch_bytes=200000))


@pytest.mark.parametrize('log_limit', [1, 2*1024*1024])
def test_explicit_diagnostic_retention_is_not_restricted_by_a_hidden_size_policy(tmp_path, log_limit):
    spec = _spec(tmp_path)
    spec['limits']['max_log_bytes'] = log_limit
    controller._validate(spec)


def test_protocol_stdout_is_complete_while_only_stderr_is_a_tail():
    command = _command("import sys;sys.stdout.write('{\"payload\":\"'+('原'*800000)+'\"}');"
                       "sys.stderr.write('noise'*4000+'END')")
    result = run_bounded(command, env=dict(os.environ, PYTHONIOENCODING='utf-8'),
                         timeout_seconds=5, stdout_cap_bytes=None,
                         stderr_cap_bytes=4096, stderr_log_tail=True)
    assert json.loads(result['stdout']) == {'payload': '原'*800000}
    assert result['stdout_bytes_read'] > 2*1024*1024
    assert len(result['stderr']) == 4096
    assert result['stderr'].endswith(b'END')
    assert result['stderr_bytes_read'] == 20003


def test_stderr_tail_does_not_turn_an_explicit_payload_budget_into_a_tail():
    with pytest.raises(OutputLimitExceeded):
        run_bounded(_command("print('x'*4097)"), timeout_seconds=5,
                    stdout_cap_bytes=4096, stderr_cap_bytes=4096, stderr_log_tail=True)


def test_noisy_nonzero_remains_nonzero_with_its_complete_protocol():
    with pytest.raises(ChildFailed) as caught:
        run_bounded(_command("import sys;print('{\"status\":\"native_error\"}');"
                             "sys.stderr.write('x'*20000);sys.exit(7)"),
                    timeout_seconds=5, stdout_cap_bytes=None,
                    stderr_cap_bytes=4096, stderr_log_tail=True)
    assert caught.value.returncode == 7
    assert json.loads(caught.value.stdout)['status'] == 'native_error'


def test_controller_retains_native_json_after_large_diagnostics(tmp_path):
    code, stdout, stderr = controller._process(_command(
        "import sys;print('{\"status\":\"completed\",\"payload\":\"'+('x'*2200000)+'\"}');"
        "sys.stderr.write('x'*20000+'END')"), env=dict(os.environ), root=tmp_path,
        output=tmp_path, label='native', timeout=5, log_limit=4096)
    assert code == 0
    assert len(json.loads(stdout)['payload']) == 2200000
    assert len(stderr) == 4096 and stderr.endswith(b'END')
    receipt = json.loads((tmp_path/'native.command.json').read_text())
    assert receipt['stdout_sha256'] == hashlib.sha256(stdout).hexdigest()
    assert receipt['stdout_bytes'] == len(stdout)
    assert receipt['stderr_bytes'] == 20003
    assert receipt['stderr_truncated'] is True


def test_controller_preserves_a_real_native_error(tmp_path):
    code, stdout, _ = controller._process(_command(
        "import sys;print('{\"status\":\"failed\"}');sys.stderr.write('x'*20000);sys.exit(3)"),
        env=dict(os.environ), root=tmp_path, output=tmp_path,
        label='native-error', timeout=5, log_limit=4096)
    assert code == 3
    assert json.loads(stdout)['status'] == 'failed'


def test_controller_timeout_still_stops_owned_child(tmp_path):
    with pytest.raises(controller.ControllerError, match='HOLDOUT_OWNED_CLI_TIMEOUT'):
        controller._process(_command('import time;time.sleep(20)'), env=dict(os.environ),
            root=tmp_path, output=tmp_path, label='timeout', timeout=0.2, log_limit=4096)


def test_controller_timeout_reclaims_a_real_owned_grandchild(tmp_path):
    pid_file = tmp_path/'owned-child.pid'
    child = "import time;time.sleep(30)"
    code = ("import subprocess,sys,time;from pathlib import Path;"
            f"p=subprocess.Popen([sys.executable,'-B','-c',{child!r}]);"
            f"Path({str(pid_file)!r}).write_text(str(p.pid));time.sleep(30)")
    with pytest.raises(controller.ControllerError, match='HOLDOUT_OWNED_CLI_TIMEOUT'):
        controller._process(_command(code), env=dict(os.environ), root=tmp_path,
            output=tmp_path, label='tree', timeout=2, log_limit=4096)
    assert pid_file.exists(), 'the child must actually start for this cleanup proof'
    assert not pid_is_alive(int(pid_file.read_text()))


def test_diagnostic_file_failure_does_not_discard_successful_protocol(tmp_path, monkeypatch):
    original = Path.write_bytes
    def fail_log(path, body):
        if path.name.endswith('.stderr.log'):
            raise OSError('synthetic observation storage failure')
        return original(path, body)
    monkeypatch.setattr(Path, 'write_bytes', fail_log)
    code, stdout, stderr = controller._process(_command("print('{\"status\":\"completed\"}')"),
        env=dict(os.environ), root=tmp_path, output=tmp_path, label='diagnostic',
        timeout=5, log_limit=4096)
    assert code == 0 and json.loads(stdout)['status'] == 'completed'
    assert b'HOLDOUT_OBSERVATION_INCOMPLETE' in stderr
    assert json.loads((tmp_path/'diagnostic.command.json').read_text())['exit'] == 0


def test_observation_status_does_not_depend_on_how_much_log_tail_is_displayed(tmp_path):
    marker = 'HOLDOUT_OBSERVATION_INCOMPLETE event_write:OSError'
    code, stdout, stderr = controller._process(_command(
        f"import sys;print('{{\"status\":\"completed\"}}');sys.stderr.write('x'*65525+{marker!r}+'\\n')"),
        env=dict(os.environ), root=tmp_path, output=tmp_path, label='tiny-tail', timeout=5, log_limit=1)
    assert code == 0 and json.loads(stdout)['status'] == 'completed'
    assert b'HOLDOUT_OBSERVATION_INCOMPLETE' in stderr
    assert (tmp_path/'tiny-tail.stderr.log').read_bytes() == b'\n'
    assert json.loads((tmp_path/'tiny-tail.command.json').read_text())['observation_incomplete'] is True


def test_a_diagnostic_chunk_observer_failure_does_not_change_the_native_outcome():
    def failed_observer(chunk):
        raise OSError('synthetic observer failure')
    result = run_bounded(_command("import sys;print('{\"status\":\"completed\"}');sys.stderr.write('notice')"),
        timeout_seconds=5, stdout_cap_bytes=None, stderr_cap_bytes=1,
        stderr_log_tail=True, stderr_observer=failed_observer)
    assert result['returncode'] == 0 and json.loads(result['stdout'])['status'] == 'completed'
    assert result['stderr_observation_complete'] is False
    assert result['stderr'] == b'e'


@pytest.mark.parametrize('failure', ['event_marker', 'receipt_disk', 'malformed_events'])
def test_controller_observation_failure_retains_paid_state_without_another_child(tmp_path, monkeypatch, failure):
    spec = _spec(tmp_path)
    native = dict(run={'state':'active'}, reservations=[{'paid_response_pin':{'durable':True}}],
                  generations={},charged_tokens=17,charged_micro_usd=3)
    monkeypatch.setattr(controller, '_native', lambda *a: native)
    calls = []
    def process(*args, **kwargs):
        calls.append(True)
        return 0, b'{"status":"completed","documents":[]}', (
            b'HOLDOUT_OBSERVATION_INCOMPLETE event_write:OSError' if failure=='event_marker' else b'')
    monkeypatch.setattr(controller, '_process', process)
    original_write = controller._write
    def write(path, value):
        if failure == 'receipt_disk' and path.name.startswith('cli-') and path.name.endswith('.result.json'):
            raise OSError('synthetic receipt disk failure')
        return original_write(path, value)
    monkeypatch.setattr(controller, '_write', write)
    if failure == 'malformed_events':
        (tmp_path/'receipts').mkdir()
        (tmp_path/'receipts/events.jsonl').write_text('{bad event')
    result = controller.run_controller(spec)
    assert result['status'] == 'observation_incomplete'
    assert result['native']['charged_tokens'] == 17
    assert result['native']['reservations'][0]['paid_response_pin'] == {'durable':True}
    assert len(calls) == (0 if failure=='malformed_events' else 1)
    if calls:
        assert result['stages'][0]['native_exit'] == 0
        assert result['stages'][0]['receipt']['status'] == 'completed'
    assert not Path(spec['automation_db']).exists()


@pytest.fixture
def observed(tmp_path, monkeypatch, request):
    config = tmp_path/'observer.json'
    config.write_text(json.dumps({'receipt_dir':str(tmp_path), 'stage':getattr(request,'param','cache'),
        'max_log_bytes':4096, 'allow_local_model_http':False}))
    monkeypatch.setenv('CWP_HOLDOUT_CONTROLLER', str(config))
    monkeypatch.setattr(observer, '_INSTALLED', False)
    callbacks = []
    monkeypatch.setattr(atexit, 'register', callbacks.append)
    sent = []
    monkeypatch.setattr(http.client.HTTPConnection, 'request', lambda *a, **k: sent.append(True))
    monkeypatch.setattr(BudgetedNarrativeCaller, 'generate', lambda *a: ('native-response', 'native-usage'))
    monkeypatch.setattr(BudgetedNarrativeCaller, '_recover', lambda *a: None)
    monkeypatch.setattr(NarrativeHTTPModel, 'replay_response', lambda *a, **k: SimpleNamespace(response_sha256='a'*64))
    monkeypatch.setattr(AutomationStore, 'finish_attempt', lambda *a, **k: 'native-finished')
    body = json.dumps({'model':'synthetic', 'messages':[{'role':'system','content':'synthetic'},
        {'role':'user','content':json.dumps({'schema_version':'narrative-model-request/5',
                                           'material':{'tasks':[]}})}]}).encode()
    monkeypatch.setattr(contracts, 'request_preflight', lambda *a: (body, {'http_body_sha256':hashlib.sha256(body).hexdigest()}))
    observer.install()
    return tmp_path, body, sent, callbacks


def test_accumulated_event_diagnostics_do_not_prevent_the_one_actual_transport(observed):
    root, body, sent, _ = observed
    (root/'events.jsonl').write_text(json.dumps({'event':'history','padding':'x'*8192})+'\n')
    http.client.HTTPConnection('offline.invalid').request('POST', '/', body=body)
    assert sent == [True]
    assert (root/'post-once').exists()
    assert json.loads((root/'events.jsonl').read_text().splitlines()[-1])['event'] == 'http_post'
    with pytest.raises(RuntimeError, match='HOLDOUT_SECOND_POST_REFUSED'):
        http.client.HTTPConnection('offline.invalid').request('POST', '/', body=body)
    assert len(sent) == 1


def test_event_io_failure_does_not_replace_native_success_or_allow_resend(observed, monkeypatch, capsys):
    root, body, sent, callbacks = observed
    original_open = Path.open
    def broken_event(path, *args, **kwargs):
        if path == root/'events.jsonl':
            raise OSError('synthetic diagnostic disk error')
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', broken_event)
    caller = SimpleNamespace(_model=None, _run_id='synthetic')
    context = SimpleNamespace(attempt=SimpleNamespace(attempt_id='worker'))
    assert BudgetedNarrativeCaller.generate(caller, context, None) == ('native-response','native-usage')
    http.client.HTTPConnection('offline.invalid').request('POST', '/', body=body)
    assert sent == [True]
    with pytest.raises(RuntimeError, match='HOLDOUT_SECOND_POST_REFUSED'):
        http.client.HTTPConnection('offline.invalid').request('POST', '/', body=body)
    assert len(sent) == 1
    assert callbacks
    for callback in callbacks:
        callback()
    assert 'HOLDOUT_OBSERVATION_INCOMPLETE' in capsys.readouterr().err


@pytest.mark.parametrize('fault', ['write', 'partial_write', 'read'])
def test_model_input_observation_io_cannot_replace_native_success_or_one_post(observed, monkeypatch, capsys, fault):
    root, body, sent, callbacks = observed
    body_path=root/'model-input.json'
    if fault=='read':
        body_path.write_bytes(body)
    original_read, original_write=Path.read_bytes, Path.write_bytes
    def fail_read(path):
        if path.name=='model-input.json' and fault=='read':
            raise OSError('synthetic snapshot read error')
        return original_read(path)
    def fail_write(path,value):
        if path.name=='model-input.json' and fault in ('write','partial_write'):
            if fault=='partial_write':
                original_write(path,value[:7])
            raise OSError('synthetic snapshot write error')
        return original_write(path,value)
    monkeypatch.setattr(Path,'read_bytes',fail_read)
    monkeypatch.setattr(Path,'write_bytes',fail_write)
    assert BudgetedNarrativeCaller.generate(SimpleNamespace(_model=None,_run_id='synthetic'),
        SimpleNamespace(attempt=SimpleNamespace(attempt_id='worker')),None)==('native-response','native-usage')
    http.client.HTTPConnection('offline.invalid').request('POST','/',body=body)
    assert sent == [True]
    with pytest.raises(RuntimeError,match='HOLDOUT_SECOND_POST_REFUSED'):
        http.client.HTTPConnection('offline.invalid').request('POST','/',body=body)
    assert sent == [True]
    for callback in callbacks:
        callback()
    assert 'HOLDOUT_OBSERVATION_INCOMPLETE' in capsys.readouterr().err
    if fault!='read':
        assert not body_path.exists(), 'a failed observation cannot publish a partial body as a mismatch baseline'


@pytest.mark.parametrize('entry',['generate','http'])
def test_successfully_read_real_model_input_mismatch_still_refuses(observed, entry):
    root, body, sent, _=observed
    (root/'model-input.json').write_bytes(b'a genuinely different observed request')
    with pytest.raises(RuntimeError,match='HOLDOUT_MODEL_INPUT_CHANGED'):
        if entry=='http':
            http.client.HTTPConnection('offline.invalid').request('POST','/',body=body)
        else:
            BudgetedNarrativeCaller.generate(SimpleNamespace(_model=None,_run_id='synthetic'),
                SimpleNamespace(attempt=SimpleNamespace(attempt_id='worker')),None)
    assert sent == []
    assert not (root/'post-once').exists()


@pytest.mark.parametrize('observed', ['after_paid'], indirect=True)
@pytest.mark.parametrize('durable', [True, False])
def test_diagnostic_failure_preserves_explicit_fault_and_durable_pin_requirement(observed, monkeypatch, durable):
    root, _, _, _ = observed
    original_open = Path.open
    def fail_event(path, *args, **kwargs):
        if path == root/'events.jsonl':
            raise OSError('synthetic event storage failure')
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', fail_event)
    record = SimpleNamespace(job_id='job', paid_response_json='{}' if durable else None,
        attempt_id='paid',request_sha256='a'*64,usage_status='known',charged_tokens=17,charged_micro_usd=3)
    monkeypatch.setattr(PaidResponsePin, 'from_json', staticmethod(lambda raw: SimpleNamespace(body_sha256='b'*64)))
    caller = SimpleNamespace(_model=None,_run_id='synthetic',
        _store=SimpleNamespace(reservations_for_run=lambda run: [record]))
    context = SimpleNamespace(job=SimpleNamespace(job_id='job'),
        attempt=SimpleNamespace(attempt_id='worker',runtime_generation=1,lease_token='lease'))
    if durable:
        with pytest.raises(NarrativeBudgetCallError) as caught:
            BudgetedNarrativeCaller.generate(caller, context, None)
        assert caught.value.code == 'IO_TRANSIENT'
        assert caught.value.outcome is HandlerOutcome.RETRYABLE
        assert caught.value.metrics == 'native-usage'
    else:
        with pytest.raises(RuntimeError, match='HOLDOUT_PAID_PIN_NOT_DURABLE'):
            BudgetedNarrativeCaller.generate(caller, context, None)


def test_native_failure_is_not_swallowed_by_observation_isolation(tmp_path, monkeypatch):
    # The original native callable is captured during install, not patched over afterwards.
    config = tmp_path/'observer.json'
    config.write_text(json.dumps({'receipt_dir':str(tmp_path),'stage':'cache',
                                 'max_log_bytes':4096,'allow_local_model_http':False}))
    monkeypatch.setenv('CWP_HOLDOUT_CONTROLLER', str(config))
    monkeypatch.setattr(observer, '_INSTALLED', False)
    monkeypatch.setattr(atexit, 'register', lambda f: f)
    def failed(*args):
        raise RuntimeError('actual native failure')
    monkeypatch.setattr(BudgetedNarrativeCaller, 'generate', failed)
    # Restore every patched class after this test, since install uses setattr.
    for cls, name in [(http.client.HTTPConnection,'request'), (BudgetedNarrativeCaller,'_recover'),
                       (NarrativeHTTPModel,'replay_response'), (AutomationStore,'finish_attempt')]:
        monkeypatch.setattr(cls, name, getattr(cls,name))
    monkeypatch.setattr(contracts, 'request_preflight', lambda *a: (b'synthetic',{}))
    observer.install()
    with pytest.raises(RuntimeError, match='actual native failure'):
        BudgetedNarrativeCaller.generate(SimpleNamespace(_model=None,_run_id='x'),
            SimpleNamespace(attempt=SimpleNamespace(attempt_id='w')), None)
