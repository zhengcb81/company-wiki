"""New default execution is source-extractive; historical explicit modes remain."""
from dataclasses import replace
from contextlib import closing
from types import SimpleNamespace
import json
import sqlite3
import pytest

from company_wiki.automation.narrative_generation import generation_manifest
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from integration.test_narrative_legacy_effort_history import _request
from unit.test_narrative_extractive_runtime import selected
from unit.test_narrative_summarize_handler import _context
from support import narrative_batch_fixtures as fixtures
from support.narrative_batch_fixtures import (
    isolated_batch_directory, prepare_source_catalog,
    loopback_model_server as _loopback_model_server,
)

loopback_model_server = _loopback_model_server


def new_request():
    source = selected()
    state = SimpleNamespace(indexed={'source': (source.source_ref,)})
    request, _ = _request(state, 'http://127.0.0.1:9999/v1/chat/completions', '1')
    return source, replace(request, selector_version='0.9.0')


def test_new_reading_generation_default_selects_extractive_protocol_without_manual_flag():
    source, request = new_request()
    manifest = generation_manifest(request, _context(source).source_revision,
                                   execution_versions=request.execution_versions)
    assert manifest['reading_model_projection'] == 'reading-model-input/5'
    assert manifest['execution_versions']['prompt'] == 'reading-source-extractive/5.0.0'


def test_explicit_v5_request_roundtrip_and_explicit_v4_retains_its_original_protocol():
    source, request = new_request()
    wire = request.to_dict()
    wire['reading_model_projection'] = 'reading-model-input/5'
    parsed = NarrativeBatchRequest.from_dict(wire)
    assert parsed.reading_model_projection == 'reading-model-input/5'
    manifest = generation_manifest(request, _context(source).source_revision,
        execution_versions=request.execution_versions, reading_model_projection='reading-model-input/4')
    assert manifest['reading_model_projection'] == 'reading-model-input/4'
    assert manifest['execution_versions']['prompt'] == 'reading-source-scoped/4.0.3'


def test_legacy_nonreading_default_does_not_silently_opt_in():
    source, request = new_request()
    request = replace(request, selector_version='0.8.0')
    manifest = generation_manifest(request, _context(source).source_revision,
                                   execution_versions=request.execution_versions)
    assert 'reading_model_projection' not in manifest


def test_real_default_worker_preserves_paid_response_and_audit_after_compaction_and_reuse(
    tmp_path_factory, loopback_model_server, monkeypatch,
):
    from company_wiki.automation import narrative_batch as batch
    from company_wiki.automation.narrative_run_store import NarrativeRunStore
    from company_wiki.automation.store import AutomationStore
    from company_wiki.automation.narrative_summary_execution import extract_summary_execution
    from integration.test_narrative_legacy_effort_history import _database_dump

    def rank_reply(data):
        assert data['schema_version'] == 'narrative-model-request/6'
        return {'decisions': []}
    monkeypatch.setattr(fixtures, 'response_draft', rank_reply)
    with isolated_batch_directory(tmp_path_factory) as root:
        state = prepare_source_catalog(root, one_source=True, include_policy=False)
        try:
            request, _wire = _request(state, loopback_model_server.endpoint, '1')
            request = replace(request, selector_version='0.9.0', max_seconds=60)
            kwargs = dict(project_root=root, catalog_config_path=state.config_path,
                          db_path=root/'automation.db', work_dir=root/'work')
            first = batch.run_batch(request, **kwargs)
            diagnostics = [(job.job_type, job.last_error_code, job.last_error_detail)
                           for job in AutomationStore(root/'automation.db').list_jobs()]
            assert first['status'] == 'completed', (first, diagnostics)
            assert len(loopback_model_server.requests) == 1 and not loopback_model_server.errors
            runs = NarrativeRunStore(root/'automation.db')
            reservations = runs.reservations_for_run(request.run_id)
            assert len(reservations) == 1 and reservations[0].paid_response_json
            store = AutomationStore(root/'automation.db')
            summary_job = next(job for job in store.list_jobs() if job.job_type == 'source.narrative_summarize')
            receipt = json.loads(store.list_attempts(summary_job.job_id)[-1].result_json)['result']
            assert receipt['schema_version'] == 'narrative-terminal-receipt/1.0'
            report = extract_summary_execution(receipt)
            assert report and report['tasks'] and report['model_diagnostic'] == 'RANK_INCOMPLETE'
            assert first['documents'][0]['model_diagnostics'][0]['execution'] == report
            before = _database_dump(root/'automation.db')
            again = batch.run_batch(request, **kwargs)
            assert again['status'] == 'completed' and again['documents'] == first['documents']
            assert again['budget'] == first['budget']
            assert _database_dump(root/'automation.db') == before
            assert len(loopback_model_server.requests) == 1
            # A successful v5 terminal receipt must not silently lose the
            # report on an idempotent second compaction.
            from company_wiki.automation.terminal_receipt_contracts import FinalArtifactPin
            from company_wiki.automation.store import IntegrityViolationError
            attempt = store.list_attempts(summary_job.job_id)[-1]
            outer = json.loads(attempt.result_json)
            outer['result'].pop('execution')
            with closing(sqlite3.connect(root/'automation.db')) as connection:
                connection.execute('UPDATE attempts SET result_json=? WHERE attempt_id=?',
                                   (json.dumps(outer), attempt.attempt_id))
                connection.commit()
            with pytest.raises(IntegrityViolationError, match='execution'):
                store.compact_terminal_narrative_jobs(
                    job_ids=tuple(job.job_id for job in store.list_jobs()),
                    final_artifact=FinalArtifactPin(**receipt['final_artifact']), compacted_at=batch._now())
        finally:
            state.catalog.close()


def test_failed_batch_recovery_candidates_are_only_exact_frozen_v5_paid_operations():
    from company_wiki.automation.narrative_batch import _paid_summary_recovery_candidates
    from company_wiki.automation.narrative_paid_response import PaidResponsePin
    from company_wiki.automation.models import JobStatus
    from company_wiki.automation.narrative_model_extractive import EXTRACTIVE_PROMPT_VERSION
    pin = PaidResponsePin(request_sha256='a'*64, body_sha256='b'*64,
        object_key='objects/sha256/bb/'+'b'*64+'.json', byte_size=2,
        model_id='configured', adapter_id='offline', prompt_version=EXTRACTIVE_PROMPT_VERSION,
        http_status=200, duration_ms=0)
    record = SimpleNamespace(job_id='job', request_sha256='a'*64, paid_response_json=pin.to_json(),
                             output_bytes=0, output_sha256=None)
    run = SimpleNamespace(run_id='run', blocked=False, model_id='configured')
    job = SimpleNamespace(job_id='job', subject_id='doc', job_type='source.narrative_summarize',
                          status=JobStatus.DEAD_LETTER)
    binding = SimpleNamespace(generation_manifests={'doc': {'reading_model_projection':'reading-model-input/5'}})
    runs = SimpleNamespace(reservations_for_run=lambda _run: (record,))
    assert _paid_summary_recovery_candidates(binding, run, (job,), runs) == (('job', 'a'*64),)
    for field, value in [('paid_response_json', None), ('output_bytes', 1), ('request_sha256', 'c'*64)]:
        original = getattr(record, field)
        setattr(record, field, value)
        assert _paid_summary_recovery_candidates(binding, run, (job,), runs) == ()
        setattr(record, field, original)
    binding.generation_manifests['doc']['reading_model_projection'] = 'reading-model-input/4'
    assert _paid_summary_recovery_candidates(binding, run, (job,), runs) == ()
    binding.generation_manifests['doc']['reading_model_projection'] = 'reading-model-input/5'
    run.blocked = True
    assert _paid_summary_recovery_candidates(binding, run, (job,), runs) == ()


def test_coordinator_merges_committed_response_writer_observation_into_scratch_lower_bound():
    from company_wiki.automation.narrative_batch import _receipt
    from company_wiki.automation.narrative_paid_response import PaidResponsePin
    from company_wiki.automation.narrative_model_extractive import EXTRACTIVE_PROMPT_VERSION
    pin = PaidResponsePin(request_sha256='a'*64, body_sha256='b'*64,
        object_key='objects/sha256/bb/'+'b'*64+'.json', byte_size=128,
        model_id='configured', adapter_id='offline', prompt_version=EXTRACTIVE_PROMPT_VERSION,
        http_status=200, duration_ms=0)
    budget = SimpleNamespace(charged_tokens=92, charged_micro_usd=111,
                             unknown_reservations=0, unsettled_reservations=0)
    runs = SimpleNamespace(budget_snapshot=lambda _run: budget,
        reservations_for_run=lambda _run: (SimpleNamespace(paid_response_json=pin.to_json()),))
    class Guard:
        peak = 0
        def snapshot(self):
            return SimpleNamespace(persistent_added_bytes=128, scratch_peak_bytes=self.peak)
    result = _receipt('run', 'failed', [], runs, Guard())
    assert result['storage']['scratch_peak_bytes'] == 128
    assert result['storage']['scratch_peak_observation'] == 'committed_writer_lower_bound'


def test_real_default_policy_document_skips_model_and_does_not_require_fictional_execution(
    tmp_path_factory, loopback_model_server,
):
    from dataclasses import asdict
    from company_wiki.automation import narrative_batch as batch
    from company_wiki.automation.narrative_contracts import SourceRefValue
    from company_wiki.automation.narrative_run_store import NarrativeRunStore
    with isolated_batch_directory(tmp_path_factory) as root:
        state = prepare_source_catalog(root, include_policy=True)
        try:
            ref = next(ref for ref, _language, kind in state.indexed.values() if kind == 'ir_policy')
            request, _wire = _request(state, loopback_model_server.endpoint, '1')
            request = replace(request, sources=(SourceRefValue.from_dict(asdict(ref)),),
                              selector_version='0.9.0', max_seconds=60)
            first = batch.run_batch(request, project_root=root, catalog_config_path=state.config_path,
                                    db_path=root/'automation.db', work_dir=root/'work')
            assert first['status'] == 'completed', first
            assert first['documents'][0]['artifact_ref']
            assert not loopback_model_server.requests
            assert not NarrativeRunStore(root/'automation.db').reservations_for_run(request.run_id)
            again = batch.run_batch(request, project_root=root, catalog_config_path=state.config_path,
                                    db_path=root/'automation.db', work_dir=root/'work')
            assert again['status'] == 'completed' and again['documents'] == first['documents']
            assert again['budget'] == first['budget'] and not loopback_model_server.requests
        finally:
            state.catalog.close()
