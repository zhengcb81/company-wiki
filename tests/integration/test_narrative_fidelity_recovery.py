"""Real loopback assessed transport, publication and zero-POST cache recovery.

Original-language fixture extracts test lifecycle, not summary semantics.
"""
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import UTC, datetime
import pytest

from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.store import AutomationStore
from support import narrative_batch_fixtures as batch_fixtures
from support.narrative_batch_fixtures import (
    isolated_batch_directory, prepare_source_catalog, loopback_model_server as _loopback_model_server,
)
from integration.test_narrative_legacy_effort_history import _request, _database_dump

loopback_model_server = _loopback_model_server


@pytest.mark.parametrize('projection,request_schema,assessor', [
    ('reading-model-input/6', 'narrative-model-request/7', 'source-summary-assessment/1.0.0'),
    ('reading-model-input/7', 'narrative-model-request/8', 'source-summary-assessment/1.1.0'),
])
def test_explicit_fidelity_actual_http_and_same_cross_run_cache(tmp_path_factory,loopback_model_server,monkeypatch,
                                                               projection,request_schema,assessor):
    def reply(data):
        assert data['schema_version']==request_schema
        material=data['material']
        if projection == 'reading-model-input/7':
            assert material['source_frame_hints']['schema_version']=='source-frame-hints/1'
        else:
            assert 'source_frame_hints' not in material
        result={}
        for task in material['tasks']:
            support=task.get('support_parts',material['task_defaults']['support_parts'])
            key=task['parts'][0]['key'] if support=='all_parts' else support[0]
            part=next(part for part in task['parts'] if part['key']==key)
            if 'shared_ref' in part:
                part=next(row for row in material['shared_fragments'] if row['source_key']==part['shared_ref'])
            result[task['key']]=[{'text':part['text'][:200],'basis_parts':[key],'modality':'uncertain'}]
        return {'drafts_by_task':result}
    monkeypatch.setattr(batch_fixtures,'response_draft',reply)
    with isolated_batch_directory(tmp_path_factory) as root:
        state=prepare_source_catalog(root,one_source=True,include_policy=False)
        try:
            request,_=_request(state,loopback_model_server.endpoint,'1')
            request=replace(request,selector_version='0.9.0',reading_model_projection=projection,max_seconds=90)
            options={'project_root':root,'catalog_config_path':state.config_path,
                     'db_path':root/'automation.db','work_dir':root/'work'}
            first=batch.run_batch(request,**options)
            assert first['status']=='completed',first
            assert len(loopback_model_server.requests)==1 and not loopback_model_server.errors
            assert first['documents'][0]['artifact_ref']
            store=AutomationStore(root/'automation.db')
            # Completed attempts are compact terminal receipts by design. Read
            # the actual published body through its public logical reference.
            pin=first['documents'][0]['artifact_ref']
            # This fixture originally supplies project_root explicitly to its
            # catalog.json. Public clients use the documented config/ layout.
            public_config=root/'config'/'source_catalog.json'
            public_config.parent.mkdir()
            public_config.write_bytes(state.config_path.read_bytes())
            ref={'schema_version':'narrative-ref/1','artifact_version_id':pin['artifact_version_id'],
                 'artifact_sha256':pin['content_sha256'],'byte_size':pin['byte_size'],
                 'source_ref':request.sources[0].to_dict()}
            read_request={'schema_version':'narrative-read-request/1','narrative_ref':ref,
                'as_of_date':datetime.now(UTC).date().isoformat(),
                'expected_source':dict.fromkeys(('canonical_entity_id','market','security_id','document_kind','fiscal_year','fiscal_period'))}
            proc=subprocess.run([sys.executable,'-B','-m','company_wiki.source_catalog.narrative_transport_cli',
                '--config',str(public_config),'--operation','read'],input=json.dumps(read_request).encode(),
                capture_output=True,cwd=root,timeout=30,
                env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]/'src')))
            assert proc.returncode==0,proc.stderr
            bundle=json.loads(proc.stdout)
            assert bundle['schema_version']=='narrative-bundle/2.1'
            assert bundle['summary_assessment']['semantic_status']=='not_evaluated'
            assert bundle['summary_assessment']['validator']['version']==assessor
            for job in store.list_jobs():
                if job.job_type=='source.narrative_summarize':
                    observations=batch._attempt_model_diagnostics(store,{},job)
                    assert observations and observations[0]['execution']['schema_version']=='summary-assessment/1'
                    assert observations[0]['execution']['validator']['version']==assessor
            run=NarrativeRunStore(root/'automation.db').get_run(request.run_id)
            manifests=batch._thaw_generations(json.loads(run.binding_json))
            assert all(value['bundle_schema']=='narrative-bundle/2.1' and value['bundle_producer']=='1.1.0'
                       for value in manifests.values())
            before=_database_dump(root/'automation.db')
            again=batch.run_batch(request,**options)
            assert again['status']=='completed' and again['documents']==first['documents']
            assert _database_dump(root/'automation.db')==before
            cross=batch.run_batch(replace(request,run_id='fidelity-cross-run'),
                                  **{**options,'work_dir':root/'cross-work'})
            assert cross['status']=='completed',cross
            assert cross['documents'][0]['artifact_ref']['content_sha256']==pin['content_sha256']
            assert len(loopback_model_server.requests)==1
        finally:
            state.catalog.close()
