"""Real v3 completion and CLI recovery across a simulated validator upgrade.

Loopback is an actual HTTP transport, never a supplier. The historical case
deploys one exact pre-use source producer plus typed-v3 model protocol; other
modules are current. It is not an entire old release or relabelled v4 output.
"""
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys

from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.store import AutomationStore
from support import narrative_batch_fixtures as batch_fixtures
from support.legacy_reading_producer import deploy_historical_reading_producer
from support.narrative_batch_fixtures import (
    isolated_batch_directory, prepare_source_catalog,
    loopback_model_server as _loopback_model_server,
)
from integration.test_narrative_legacy_effort_history import _request, _database_dump

loopback_model_server = _loopback_model_server


def test_explicit_v4_manifest_drives_actual_worker_http_verify_and_completed_recovery(
    tmp_path_factory, loopback_model_server, monkeypatch,
):
    """One real v4 HTTP POST through unchanged caller and one published result.

    Fixture prose is copied from the selected source; this tests transport and
    lifecycle, not paraphrase quality or coverage of a complete real filing.
    """
    def scoped_reply(data):
        assert data['schema_version']=='narrative-model-request/5'
        material=data['material']
        task=material['tasks'][0]
        support=task.get('support_parts',material['task_defaults']['support_parts'])
        key=task['parts'][0]['key'] if support=='all_parts' else support[0]
        part=next(part for part in task['parts'] if part['key']==key)
        if 'shared_ref' in part:
            part=next(row for row in material['shared_fragments']
                      if row['source_key']==part['shared_ref'])
        return {'drafts_by_task':{task['key']:[{
            'text':part['text'][:200],'basis_parts':[key],'modality':'uncertain'}]}}
    monkeypatch.setattr(batch_fixtures,'response_draft',scoped_reply)
    with isolated_batch_directory(tmp_path_factory) as root:
        state=prepare_source_catalog(root,one_source=True,include_policy=False)
        try:
            request,_wire=_request(state,loopback_model_server.endpoint,'1')
            # Lifecycle correctness is not a 30-second host-speed benchmark.
            # Keep HTTP timeout/fee/recovery assertions; allow concurrent CI startup.
            request=replace(request,selector_version='0.9.0',max_seconds=90)
            first=batch.run_batch(request,project_root=root,
                catalog_config_path=state.config_path,db_path=root/'automation.db',work_dir=root/'work')
            observed=AutomationStore(root/'automation.db')
            diagnostics=[str(attempt)[:6000] for job in observed.list_jobs()
                         for attempt in observed.list_attempts(job.job_id)]
            assert first['status']=='completed', (first,diagnostics)
            assert len(loopback_model_server.requests)==1 and not loopback_model_server.errors
            assert first['documents'][0]['artifact_ref']
            runs=NarrativeRunStore(root/'automation.db')
            run=runs.get_run(request.run_id)
            frozen=batch._thaw_generations(json.loads(run.binding_json))
            assert all(m['reading_model_projection']=='reading-model-input/4' for m in frozen.values())
            # Run's compatibility container retains the request's original
            # default; each actual source execution freezes its own protocol.
            assert run.prompt_version==request.execution_versions['prompt']
            assert all(m['execution_versions']['prompt']=='reading-source-scoped/4.1.0'
                       for m in frozen.values())
            auto=_database_dump(root/'automation.db')
            catalog=_database_dump(state.catalog.config.database_path)
            again=batch.run_batch(request,project_root=root,
                catalog_config_path=state.config_path,db_path=root/'automation.db',work_dir=root/'work')
            assert again['status']=='completed', again
            assert again['documents']==first['documents'] and again['budget']==first['budget']
            assert len(loopback_model_server.requests)==1
            assert _database_dump(root/'automation.db')==auto
            assert _database_dump(state.catalog.config.database_path)==catalog
            assert runs.get_run(request.run_id)==run
        finally:
            state.catalog.close()


def test_real_paid_v3_typed_stage_recovers_with_zero_new_posts_after_validator_upgrade(
    tmp_path_factory, loopback_model_server, record_testsuite_property,
):
    """Real old producer component + v3 codec, then current-only CLI recovery."""
    with isolated_batch_directory(tmp_path_factory) as root:
        state = prepare_source_catalog(root, one_source=True, include_policy=False)
        try:
            request, wire = _request(state, loopback_model_server.endpoint, '1')
            # Source/worker startup shares CPU with other CI workers. This test
            # verifies historical recovery, not a production throughput deadline.
            request = replace(request, selector_version='0.9.0', max_seconds=90)
            wire = request.to_dict()
            prepared_originals={p:p.read_bytes() for p in state.raw_paths.values()}
            bootstrap, observations, producer = deploy_historical_reading_producer(root)
            request_path=root/'request.json'
            request_path.write_text(json.dumps(wire),encoding='utf-8')
            historical_launcher=root/'historical_v3_runtime.py'
            historical_launcher.write_text('''from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.narrative_batch_cli import main
original = batch.generation_manifest
def explicit_v3(*args, **kwargs):
    return original(*args, **{**kwargs, 'reading_model_projection': 'reading-model-input/3'})
batch.generation_manifest = explicit_v3
if __name__ == '__main__':
    raise SystemExit(main())
''',encoding='utf-8')
            current_sources=Path(__file__).resolve().parents[2]/'src'
            historical_process=subprocess.run([sys.executable,'-B','-X','utf8',str(historical_launcher),
                '--project-root',str(root),'--catalog-config',str(state.config_path),
                '--automation-db',str(root/'automation.db'),'--work-dir',str(root/'work'),
                '--request',str(request_path)],cwd=root,
                env=dict(os.environ,PYTHONPATH=os.pathsep.join((str(bootstrap),str(current_sources))),
                         PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1'),
                capture_output=True,text=True,encoding='utf-8',timeout=120)
            first=json.loads(historical_process.stdout)
            observed_store=AutomationStore(root/'automation.db')
            diagnostics=[(job.job_type,attempt.error_code,attempt.error_detail)
                         for job in observed_store.list_jobs()
                         for attempt in observed_store.list_attempts(job.job_id)]
            assert historical_process.returncode==0 and first['status']=='completed', (first,historical_process.stderr,diagnostics)
            observed=[json.loads(line) for line in observations.read_text(encoding='utf-8').splitlines()]
            selected=[row for row in observed if row['phase']=='selected']
            assert selected and all(row['reading_schema']=='du-production-reading/3'
                                    and not row['has_support_use'] for row in selected)
            assert all(Path(row['producer']).resolve()==producer.resolve() for row in observed)
            frozen_observations=observations.read_bytes()
            assert {p:p.read_bytes() for p in prepared_originals}==prepared_originals
            assert len(loopback_model_server.requests)==1
            assert loopback_model_server.requests[0][0]['schema_version']=='narrative-model-request/4'
            runs=NarrativeRunStore(root/'automation.db')
            original_run=runs.get_run(request.run_id)
            frozen=batch._thaw_generations(json.loads(original_run.binding_json))
            assert all(m['reading_model_projection']=='reading-model-input/3' for m in frozen.values())
            before_auto=_database_dump(root/'automation.db')
            before_catalog=_database_dump(state.catalog.config.database_path)
            originals={p:p.read_bytes() for p in state.raw_paths.values()}
            launcher=root/'upgraded_runtime.py'
            launcher.write_text('''import json
from pathlib import Path
import company_wiki.source_catalog.narrative_reading as source_producer
Path(__file__).with_name('upgraded-source.json').write_text(json.dumps({
    'producer': source_producer.__file__,
    'legacy_bootstrap_loaded': 'historical-v3-bootstrap' in str(__import__('sys').path),
}), encoding='utf-8')
import company_wiki.automation.narrative_summarize as summary
import company_wiki.automation.narrative_worker_factory as factory
from company_wiki.automation.narrative_batch_cli import main
original = summary.reading_summary_validation_identity
def upgraded():
    return {**original(), "summary_handler_sha256": "0" * 64}
summary.reading_summary_validation_identity = upgraded
def forbidden(*args, **kwargs):
    raise AssertionError("completed typed v3 must not construct or call a model")
factory.NarrativeHTTPModel = forbidden
factory.BudgetedNarrativeCaller = forbidden
raise SystemExit(main())
''',encoding='utf-8')
            process=subprocess.run([sys.executable,'-B','-X','utf8',str(launcher),
                '--project-root',str(root),'--catalog-config',str(state.config_path),
                '--automation-db',str(root/'automation.db'),'--work-dir',str(root/'work'),
                '--request',str(request_path)],cwd=root,
                env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]/'src'),
                         PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1'),
                capture_output=True,text=True,encoding='utf-8',timeout=45)
            resumed=json.loads(process.stdout)
            assert process.returncode==0 and resumed['status']=='completed', (process.stderr,resumed)
            assert resumed['documents']==first['documents']
            assert resumed['budget']==first['budget']
            assert len(loopback_model_server.requests)==1 and not loopback_model_server.errors
            assert _database_dump(root/'automation.db')==before_auto
            assert _database_dump(state.catalog.config.database_path)==before_catalog
            assert runs.get_run(request.run_id)==original_run
            assert {p:p.read_bytes() for p in originals}==originals
            upgraded=json.loads((root/'upgraded-source.json').read_text(encoding='utf-8'))
            assert Path(upgraded['producer']).resolve()==current_sources/'company_wiki/source_catalog/narrative_reading.py'
            assert upgraded['legacy_bootstrap_loaded'] is False
            assert observations.read_bytes()==frozen_observations
            record_testsuite_property('legacy_producer_recovery',json.dumps({
                'scope':'one actual pre-use source component plus typed-v3 protocol; other runtime current',
                'producer_observations':observed,
                'historical_model_request_schema':loopback_model_server.requests[0][0]['schema_version'],
                'historical_projection':'reading-model-input/3',
                'total_loopback_posts':len(loopback_model_server.requests),
                'upgraded_runtime':upgraded,
                'automation_catalog_run_budget_originals_unchanged':True,
            },sort_keys=True))
        finally:
            state.catalog.close()
