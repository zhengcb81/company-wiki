"""Content identity and declared holdout scope are not stale-file permissions."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from types import SimpleNamespace

import pytest

from tools.document_understanding_benchmark import phase_c_runner as phase_c
from tools.holdout_replay import __main__ as cli
from tools.holdout_replay import manifest as manifest_owner
from tools.holdout_replay.producer import ProducerError, verify_producer
from tools.holdout_replay.runner import run_replay

REPO = Path(__file__).resolve().parents[2]


def _prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(phase_c, 'ROOT', tmp_path/'unconfigured-project')
    original = tmp_path/'prepared.txt'
    original.write_text('same source bytes', encoding='utf-8')
    return original, {'protected_fingerprints':{str(original):phase_c.fingerprint(original)},
                      'mother_budget':{'native_observations':[]}}


def _touch(path):
    stamp = path.stat()
    os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns+1_000_000_000))


def test_preparation_touch_only_is_observed_without_refusing_same_source(tmp_path, monkeypatch):
    original, metadata = _prepared(tmp_path, monkeypatch)
    before = dict(metadata['protected_fingerprints'][str(original)])
    _touch(original)
    result = phase_c.verify_preparation(metadata, mode='live')
    assert result['protected'][str(original)]['sha256'] == before['sha256']
    assert result['metadata_changes'][str(original)]['before']['mtime_ns'] == before['mtime_ns']
    assert result['metadata_changes'][str(original)]['after']['mtime_ns'] != before['mtime_ns']
    assert metadata['protected_fingerprints'][str(original)] == before


@pytest.mark.parametrize('fault', ['content', 'missing_sha', 'missing_bytes'])
def test_preparation_keeps_real_content_identity_validation(tmp_path, monkeypatch, fault):
    original, metadata = _prepared(tmp_path, monkeypatch)
    if fault == 'content':
        original.write_text('changed raw bytes', encoding='utf-8')
    else:
        metadata['protected_fingerprints'][str(original)].pop('sha256' if fault=='missing_sha' else 'bytes')
    with pytest.raises(ValueError, match='PREPARATION_FINGERPRINT_CHANGED'):
        phase_c.verify_preparation(metadata, mode='live')


def test_same_native_database_touch_keeps_actual_attempt_history(tmp_path, monkeypatch):
    _, metadata = _prepared(tmp_path, monkeypatch)
    database = tmp_path/'native.sqlite'
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE narrative_model_reservations(attempt_id TEXT)')
        connection.execute("INSERT INTO narrative_model_reservations VALUES ('existing-attempt')")
    before = phase_c.fingerprint(database)
    metadata['mother_budget']['native_observations']=[dict(database=str(database),fingerprint=before,
                                                         current_attempt_ids=['existing-attempt'])]
    _touch(database)
    result = phase_c.verify_preparation(metadata, mode='live')
    assert result['native'][0]['attempts'] == 1
    assert result['native'][0]['unchanged'] is True
    assert str(database) in result['metadata_changes']


def test_post_execution_content_and_optional_usage_observations_ignore_only_metadata(tmp_path):
    path=tmp_path/'usage.jsonl'
    path.write_text('{"tokens":17}\n',encoding='utf-8')
    before=phase_c.fingerprint(path)
    _touch(path)
    observed=phase_c._observe_fingerprints({str(path):before})
    assert observed['unchanged'] is True and str(path) in observed['metadata_changes']
    assert phase_c._optional_content_unchanged(path,before) is True
    path.write_text('{"tokens":18}\n',encoding='utf-8')
    assert phase_c._observe_fingerprints({str(path):before})['unchanged'] is False
    assert phase_c._optional_content_unchanged(path,before) is False
    assert phase_c._same_content({'bytes':1},{'bytes':1}) is False


def _manifest(tmp_path, *, frozen=False, prior='development'):
    original = tmp_path/'source.html'
    quote = 'Example Issuer signed a distribution agreement covering eleven new overseas countries.'
    original.write_text('<html><body><h1>Business update</h1><p>'+quote+'</p></body></html>', encoding='utf-8')
    sha=hashlib.sha256(original.read_bytes()).hexdigest()
    gold=dict(schema_version='du-gold/1',sample_id='example-ir',scope='holdout',market='US',
        company='Example Issuer',language='en',source_sha256=sha,support_set_frozen_before_output=frozen,
        expected_route_families=['investor_relations'],notes='Synthetic declared development sample',facts=[dict(
            id='distribution',importance='critical',target_kind='required_business',quantity_basis='period_flow',
            modality='actual',role='company_statement',fact_scope='narrative',
            any_support_sets=[[dict(location_kind='document',exact_quote=quote)]],
            must_preserve=['overseas agreement'],must_not_assert=['revenue guidance'],reason='synthetic')])
    gold_path=tmp_path/'gold.json'
    gold_path.write_text(json.dumps(gold),encoding='utf-8')
    sample=dict(sample_id='example-ir',gold_file='gold.json',gold_sha256=hashlib.sha256(gold_path.read_bytes()).hexdigest(),
        document_kind='investor_relations',market='US',language='en',carrier='.html',
        source_ref=dict(document_id='urn:company-wiki:document:sha256:'+sha,
            source_id='urn:company-wiki:source:sha256:'+sha,content_sha256=sha,
            byte_size=original.stat().st_size,mime_type='text/html',schema_version='2.0'),
        identity_evidence=dict(method='synthetic',entity='Example Issuer',security_id='EXAMPLE',evidence=quote),
        prior_use=dict(status=prior,known_prior_sightings='explicit development use'),
        reading_scope={'fully_read':'whole synthetic fixture'},designated_trap='Do not infer revenue guidance')
    record=dict(schema_version='w18-holdout-manifest/1',frozen_before_candidate_output=frozen,samples=[sample])
    path=tmp_path/'manifest.json'
    path.write_text(json.dumps(record),encoding='utf-8')
    bindings=tmp_path/'bindings.json'
    bindings.write_text(json.dumps({'example-ir':str(original)}),encoding='utf-8')
    return path, original, gold_path, bindings


@pytest.mark.parametrize('frozen,prior,eligible', [(False,'development',False),(False,'fresh',False),
                                                 (True,'development',False),(True,'local-unseen',True)])
def test_replay_manifest_acceptance_and_declared_clean_eligibility_are_separate(tmp_path, frozen, prior, eligible):
    path, _, _, _ = _manifest(tmp_path, frozen=frozen, prior=prior)
    record = manifest_owner.load_manifest(path)
    result = manifest_owner.declared_holdout_qualification(record)
    assert result['eligible_for_clean_holdout'] is eligible
    assert result['eligible_sample_count'] == int(eligible)
    assert result['samples'][0]['eligible_for_clean_holdout'] is eligible
    assert result['scope'] == 'declared_sample_independence_not_quality_or_loop_stopping'
    assert record == json.loads(path.read_text(encoding='utf-8'))


@pytest.mark.parametrize('prior', [None, {'status':'unknown'}, {'status':{'untrusted':'metadata'}}])
def test_unknown_or_missing_prior_use_is_not_an_execution_permission(tmp_path, prior):
    path, _, _, _ = _manifest(tmp_path,frozen=True)
    record=json.loads(path.read_text(encoding='utf-8'))
    if prior is None:
        record['samples'][0].pop('prior_use')
    else:
        record['samples'][0]['prior_use']=prior
    path.write_text(json.dumps(record), encoding='utf-8')
    loaded=manifest_owner.load_manifest(path)
    qualification=manifest_owner.declared_holdout_qualification(loaded)
    assert qualification['eligible_for_clean_holdout'] is False
    assert qualification['eligible_sample_count'] == 0
    assert 'prior_use_not_declared_fresh_or_unseen' in qualification['samples'][0]['reasons']


def test_verify_cli_reports_unfrozen_development_scope_without_refusing(tmp_path, capsys):
    path, _, _, _ = _manifest(tmp_path)
    commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
    assert cli.cmd_verify_freeze(SimpleNamespace(producer_repo=REPO,producer_commit=commit,manifest=path)) == 0
    response=json.loads(capsys.readouterr().out)
    assert response['status'] == 'verified'
    assert response['holdout_qualification']['eligible_for_clean_holdout'] is False
    assert response['holdout_qualification']['eligible_sample_count'] == 0


def test_bootstrap_and_run_cli_preserve_qualification_in_their_outward_receipts(tmp_path, monkeypatch, capsys):
    path, _, _, bindings = _manifest(tmp_path)
    monkeypatch.setattr(cli,'verify_producer',lambda *args: {'producer_commit':'observed-revision'})
    requests=[]
    def register(command,**kwargs):
        requests.append(command)
        assert 'company_wiki.source_catalog.cli' in command
        return SimpleNamespace(returncode=0,stdout='{"synthetic_register":true}',stderr='')
    monkeypatch.setattr(cli.subprocess,'run',register)
    args=SimpleNamespace(producer_repo=REPO,producer_commit='observed-revision',manifest=path,
                         bindings=bindings,lake_dir=tmp_path/'owned-lake',source_root=tmp_path)
    assert cli.cmd_bootstrap_lake(args) == 0
    bootstrap=json.loads(capsys.readouterr().out)
    assert len(requests)==1 and bootstrap['holdout_qualification']['eligible_sample_count']==0
    receipt = json.loads((args.lake_dir/'bootstrap.json').read_text(encoding='utf-8'))
    assert receipt['holdout_qualification'] == bootstrap['holdout_qualification']
    monkeypatch.setattr(cli,'run_replay',lambda **kwargs: dict(overall='ok',attempt_dir='synthetic-observation',
        samples=[{'sample_id':'example-ir','status':'ok'}],holdout_qualification=bootstrap['holdout_qualification']))
    for name,value in dict(out_dir=tmp_path/'not-created',sample=None,lake_config=None,lake_root=None,
                           llm_config=None,llm_provider='unused',per_sample_timeout=3,external_cwd=tmp_path,
                           extra_pythonpath=None,compile_selector_version='0.9.0').items():
        setattr(args,name,value)
    args.bindings=bindings
    args.source_root=None
    assert cli.cmd_run(args)==0
    summary=json.loads(capsys.readouterr().out)
    assert summary['overall']=='ok' and summary['holdout_qualification']['eligible_sample_count']==0
    assert summary['holdout_qualification']['eligible_for_clean_holdout'] is False


def test_real_replay_runs_development_source_but_does_not_count_it_as_clean_holdout(tmp_path):
    path, original, gold, bindings = _manifest(tmp_path)
    source_before=original.read_bytes()
    gold_before=gold.read_bytes()
    commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
    receipt=run_replay(producer_root=REPO,producer_commit=commit,manifest_path=path,
        out_dir=tmp_path/'out',bindings_path=bindings,external_cwd=tmp_path,per_sample_timeout=35)
    assert receipt['overall'] == 'ok', receipt['samples']
    assert receipt['holdout_qualification']['eligible_sample_count'] == 0
    row=receipt['samples'][0]
    assert row['status'] == 'ok' and row['worker_exit'] == 0
    assert row['holdout_qualification']['eligible_for_clean_holdout'] is False
    assert row['result_path']['holdout_qualification']['eligible_sample_count'] == 0
    assert row['result_path']['holdout_qualification']['eligible_for_clean_holdout'] is False
    assert original.read_bytes()==source_before and gold.read_bytes()==gold_before
    assert receipt['network_calls'] == receipt['model_posts'] == 0
    # Actual source/gold truth stays enforced regardless of qualification.
    original.write_bytes(source_before+b'changed synthetic source')
    rejected=run_replay(producer_root=REPO,producer_commit=commit,manifest_path=path,
        out_dir=tmp_path/'out',bindings_path=bindings,external_cwd=tmp_path,per_sample_timeout=35)
    assert rejected['overall'] == 'has_failures'
    assert rejected['samples'][0]['status'] == 'unavailable'
    gold.write_bytes(gold_before+b' ')
    with pytest.raises(manifest_owner.ManifestError, match='gold sha mismatch'):
        manifest_owner.verify_manifest_gold(manifest_owner.load_manifest(path),path)


def test_explicit_requested_producer_mismatch_is_still_rejected():
    with pytest.raises(ProducerError,match='HEAD'):
        verify_producer(REPO,'0'*40)
