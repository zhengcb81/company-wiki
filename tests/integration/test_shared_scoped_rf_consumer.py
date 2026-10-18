"""Explicit v4 worker output -> public verified reads -> actual RF consumer.

Opt in with CWP_RF_E2E_REPO pointing at a local RF checkout. No supplier call,
forecast, registry publication, download or synthetic artifact construction.
The model fixture copies one selected source fragment; this proves engineering
transport/recovery and does not establish paraphrase quality or filing recall.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

import pytest

from company_wiki._bounded_process import ChildFailed, run_bounded
from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.store import AutomationStore
from support import narrative_batch_fixtures as fixtures
from integration.test_narrative_legacy_effort_history import _database_dump, _request


REPO = Path(__file__).resolve().parents[2]
loopback_model_server = fixtures.loopback_model_server


@pytest.fixture(scope='module')
def rf_checkout():
    configured = os.environ.get('CWP_RF_E2E_REPO')
    if not configured:
        pytest.skip('set CWP_RF_E2E_REPO to opt into the local cross-repository RF consumer E2E')
    root = Path(configured).expanduser().resolve()
    assert (root/'scripts/narrative_source_preparation.py').is_file(), 'configured RF checkout lacks its actual consumer CLI'
    return root


def _fingerprint(path):
    if not path.exists():
        return None
    raw = path.read_bytes()
    return (len(raw), path.stat().st_mtime_ns, sha256(raw).hexdigest())


def _tree_fingerprint(root, pattern='*'):
    return {str(path.relative_to(root)): _fingerprint(path)
            for path in root.rglob(pattern) if path.is_file()} if root.exists() else None


@pytest.fixture
def protected_sources(rf_checkout):
    """Read-only source/config/default registry protection on success and error."""
    trees = {REPO/'src/company_wiki': '*.py', rf_checkout/'scripts': '*.py',
             REPO/'config': '*', rf_checkout/'config': '*',
             rf_checkout/'artifacts/registry': '*'}
    files = [REPO/'config.yaml', REPO/'config/source_catalog.yaml',
             REPO/'config/source_acquisition.yaml']
    before_trees = {root: _tree_fingerprint(root, pattern) for root, pattern in trees.items()}
    before_files = {path: _fingerprint(path) for path in files}
    try:
        yield
    finally:
        assert {root: _tree_fingerprint(root, pattern) for root, pattern in trees.items()} == before_trees
        assert {path: _fingerprint(path) for path in files} == before_files


def _source_fragment_reply(data):
    assert data['schema_version']=='narrative-model-request/5'
    material = data['material']
    task = material['tasks'][0]
    support = task.get('support_parts', material['task_defaults']['support_parts'])
    key = task['parts'][0]['key'] if support=='all_parts' else support[0]
    part = next(part for part in task['parts'] if part['key']==key)
    if 'shared_ref' in part:
        part = next(row for row in material['shared_fragments'] if row['source_key']==part['shared_ref'])
    return {'drafts_by_task': {task['key']: [
        {'text': part['text'][:200], 'basis_parts': [key], 'modality': 'uncertain'}]}}


def _invoke(command, request, *, root, env):
    try:
        result = run_bounded(command, input_bytes=json.dumps(request).encode(),
            timeout_seconds=45, cwd=str(root), env=env,
            stdout_cap_bytes=1_310_720, stderr_cap_bytes=16_384)
    except ChildFailed as exc:
        pytest.fail(f'actual child failed ({exc.returncode}): {exc.stderr.decode(errors="replace")[:4000]}')
    assert fixtures.KEY.encode() not in result['stdout'] + result['stderr']
    return result['stdout'], result['stderr']


@pytest.mark.e2e
def test_explicit_scoped_worker_public_locator_and_actual_rf_consumer_recover_without_post(
    rf_checkout, protected_sources, tmp_path_factory, loopback_model_server, monkeypatch,
):
    monkeypatch.setattr(fixtures, 'response_draft', _source_fragment_reply)
    with fixtures.isolated_batch_directory(tmp_path_factory) as root:
        state = fixtures.prepare_source_catalog(root, one_source=True, include_policy=False)
        try:
            # Public config inference and batch's explicit project-root share
            # one real isolated catalog, not a copied/fabricated artifact.
            config = root/'config/catalog.json'
            config.parent.mkdir()
            config.write_bytes(state.config_path.read_bytes())
            protected = [state.config_path, config, *state.raw_paths.values(),
                *(path.with_name(path.name+'.source.json') for path in state.raw_paths.values())]
            baseline = {path: _fingerprint(path) for path in protected}
            try:
                request, _wire = _request(state, loopback_model_server.endpoint, '1')
                request = replace(request, selector_version='0.9.0')
                original = batch.generation_manifest

                def explicit_v4(*args, **kwargs):
                    return original(*args, **{**kwargs, 'reading_model_projection':'reading-model-input/4'})

                with monkeypatch.context() as patch:
                    patch.setattr(batch, 'generation_manifest', explicit_v4)
                    first = batch.run_batch(request, project_root=root, catalog_config_path=config,
                        db_path=root/'automation.db', work_dir=root/'work')
                store = AutomationStore(root/'automation.db')
                attempts = [str(attempt)[:4000] for job in store.list_jobs()
                            for attempt in store.list_attempts(job.job_id)]
                assert first['status']=='completed', (first, attempts)
                assert len(loopback_model_server.requests)==1 and not loopback_model_server.errors
                runs = NarrativeRunStore(root/'automation.db')
                run = runs.get_run(request.run_id)
                manifests = batch._thaw_generations(json.loads(run.binding_json))
                assert all(m['reading_model_projection']=='reading-model-input/4' for m in manifests.values())
                assert all(m['execution_versions']['prompt']=='reading-source-scoped/4.0.2'
                           for m in manifests.values())

                isolated_registry = root/'rf-isolation/publications.jsonl'
                env = dict(os.environ, PYTHONPATH=str(REPO/'src'), PYTHONDONTWRITEBYTECODE='1',
                    PYTHONUTF8='1', PYTHON_DOTENV_DISABLED='1',
                    REVENUE_PUBLICATION_REGISTRY=str(isolated_registry))
                producer = [sys.executable, '-B', '-m', 'company_wiki.source_catalog.narrative_transport_cli',
                            '--config', str(config)]
                consumer = [sys.executable, '-B', str(rf_checkout/'scripts/narrative_source_preparation.py'),
                            '--company-wiki-catalog-config', str(config)]
                ref, _language, _kind = next(iter(state.indexed.values()))
                source_ref = asdict(ref)
                ref_request = {'schema_version':'narrative-reference-request/1', 'source_ref':source_ref}
                reference_bytes, reference_receipt = _invoke(producer+['--operation','reference'],
                    ref_request, root=root, env=env)
                reference = json.loads(reference_bytes)
                assert json.loads(reference_receipt)['status']=='metadata_only'
                published = first['documents'][0]['artifact_ref']
                assert reference['artifact_version_id']==published['artifact_version_id']
                assert reference['artifact_sha256']==published['content_sha256']
                assert reference['source_ref']==source_ref
                rf_reference, _ = _invoke(consumer+['--operation','reference'], ref_request, root=root, env=env)
                assert json.loads(rf_reference)==reference

                read_request = {'schema_version':'narrative-read-request/1', 'narrative_ref':reference,
                    'as_of_date':'2026-10-16', 'expected_source':{
                        'canonical_entity_id':'ent-acme','market':'US','security_id':'ACME',
                        'document_kind':'investor_call_transcript','fiscal_year':2026,'fiscal_period':'Q1'}}
                body, receipt_bytes = _invoke(producer+['--operation','read'], read_request, root=root, env=env)
                bundle, receipt = json.loads(body), json.loads(receipt_bytes)
                assert len(body)==reference['byte_size']
                assert sha256(body).hexdigest()==reference['artifact_sha256']
                assert receipt['narrative_ref']==reference and receipt['replay_status']=='verified'
                assert bundle['source_ref']==source_ref
                assert bundle['summary']['model']['prompt_version']=='reading-source-scoped/4.0.2'
                assert bundle['reading_context']['groups'] and bundle['evidence_spans']
                spans = {span['span_id']: span for span in bundle['evidence_spans']}
                for span in spans.values():
                    assert span['source_id']==source_ref['source_id']
                    viewed, lookup_receipt = _invoke(producer+['--operation','evidence-lookup',
                        '--locator',span['locator']], read_request, root=root, env=env)
                    assert json.loads(viewed)['items']==[span]
                    assert json.loads(lookup_receipt)['replay_status']=='verified'
                for claim in bundle['summary']['draft']['claims']:
                    assert claim['claim_id'].startswith('t') and claim['evidence_ids']
                    assert set(claim['evidence_ids'])<=spans.keys()
                    assert set(claim.get('context_evidence_ids', ()))<=spans.keys()

                # Actual RF CLI calls read_narrative_context, which starts the
                # public reader subprocess and runs its own strict contracts.
                rf_bytes, _ = _invoke(consumer, read_request, root=root, env=env)
                context = json.loads(rf_bytes)
                assert context['narrative_ref']==reference and context['source_ref']==source_ref
                for key in ('reading_context','summary','evidence_spans','selection','source_metadata'):
                    assert context[key]==bundle[key]
                assert context['read_receipt']['replay_status']=='verified'
                assert context['read_receipt']['narrative_ref']==reference
                assert context['read_receipt']['manifest']==receipt['manifest']

                auto = _database_dump(root/'automation.db')
                catalog = _database_dump(state.catalog.config.database_path)
                reservations = runs.reservations_for_run(request.run_id)
                again = batch.run_batch(request, project_root=root, catalog_config_path=config,
                    db_path=root/'automation.db', work_dir=root/'work')
                assert again['status']=='completed', again
                assert again['documents']==first['documents'] and again['budget']==first['budget']
                ref_again, _ = _invoke(producer+['--operation','reference'], ref_request, root=root, env=env)
                body_again, replay_again = _invoke(producer+['--operation','read'], read_request, root=root, env=env)
                rf_again, _ = _invoke(consumer, read_request, root=root, env=env)
                assert ref_again==reference_bytes and body_again==body
                assert json.loads(replay_again)['replay_status']=='verified'
                context_again = json.loads(rf_again)
                assert {k:v for k,v in context_again.items() if k!='read_receipt'} == {
                    k:v for k,v in context.items() if k!='read_receipt'}
                assert len(loopback_model_server.requests)==1 and not loopback_model_server.errors
                assert runs.reservations_for_run(request.run_id)==reservations
                assert runs.get_run(request.run_id)==run
                assert _database_dump(root/'automation.db')==auto
                assert _database_dump(state.catalog.config.database_path)==catalog
                assert not isolated_registry.exists(), 'a read-only consumer unexpectedly published a forecast'
                print('SCOPED_RF_E2E '+json.dumps({'supplier_calls':0,'initial_loopback_posts':1,
                    'recovery_new_posts':0,'artifact_sha256':reference['artifact_sha256'],
                    'source_sha256':source_ref['content_sha256'],'verified_locator_count':len(spans),
                    'rf_reading_context_preserved':True,'budget':again['budget']}))
            finally:
                assert {path:_fingerprint(path) for path in protected}==baseline
        finally:
            state.catalog.close()
