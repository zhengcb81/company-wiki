"""Real v3 completion and CLI recovery across a simulated validator upgrade.

Loopback is an actual HTTP transport, never a supplier. Historical artifacts
are produced by the original v3 runtime, not hand-written or relabelled v4.
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
            request=replace(request,selector_version='0.9.0')
            original=batch.generation_manifest
            def explicit_v4(*args,**kwargs):
                return original(*args,**{**kwargs,'reading_model_projection':'reading-model-input/4'})
            with monkeypatch.context() as patch:
                patch.setattr(batch,'generation_manifest',explicit_v4)
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
            assert all(m['execution_versions']['prompt']=='reading-source-scoped/4.0.8'
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
    tmp_path_factory, loopback_model_server, monkeypatch,
):
    with isolated_batch_directory(tmp_path_factory) as root:
        state = prepare_source_catalog(root, one_source=True, include_policy=False)
        try:
            request, wire = _request(state, loopback_model_server.endpoint, '1')
            request = replace(request, selector_version='0.9.0')
            wire = request.to_dict()
            original = batch.generation_manifest
            def explicit_v3(*args, **kwargs):
                return original(*args, **{**kwargs, 'reading_model_projection': 'reading-model-input/3'})
            with monkeypatch.context() as patch:
                patch.setattr(batch, 'generation_manifest', explicit_v3)
                first = batch.run_batch(request, project_root=root,
                    catalog_config_path=state.config_path, db_path=root/'automation.db',
                    work_dir=root/'work')
            assert first['status']=='completed', first
            assert len(loopback_model_server.requests)==1
            assert loopback_model_server.requests[0][0]['schema_version']=='narrative-model-request/4'
            runs=NarrativeRunStore(root/'automation.db')
            original_run=runs.get_run(request.run_id)
            frozen=batch._thaw_generations(json.loads(original_run.binding_json))
            assert all(m['reading_model_projection']=='reading-model-input/3' for m in frozen.values())
            before_auto=_database_dump(root/'automation.db')
            before_catalog=_database_dump(state.catalog.config.database_path)
            originals={p:p.read_bytes() for p in state.raw_paths.values()}
            request_path=root/'request.json'
            request_path.write_text(json.dumps(wire),encoding='utf-8')
            launcher=root/'upgraded_runtime.py'
            launcher.write_text('''import company_wiki.automation.narrative_summarize as summary
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
        finally:
            state.catalog.close()
