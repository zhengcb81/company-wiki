"""Exact-content reads and durable prepared-byte test evidence are distinct."""

from dataclasses import replace
import gzip
import hashlib
import json

import pytest

from tools.document_understanding_benchmark import phase_c_observer as observer
from tools.document_understanding_benchmark import phase_c_runner as runner


@pytest.mark.parametrize('selection,qualified', [
    (None, True),
    ({'mode': 'qualified_source_request', 'filing_identity_period_asof_qualification': 'REQUEST_APPLIED'}, True),
    ({'mode': 'exact_source_version', 'filing_identity_period_asof_qualification': 'NOT_EVALUATED'}, False),
])
def test_public_read_preserves_content_vs_qualified_request_semantics(tmp_path, monkeypatch, selection, qualified):
    seen = []
    descriptor = {'canonical_entity_id': 'entity-from-observation', 'market': 'CN',
                  'security_id': 'observed-code', 'document_kind': 'investor_relations',
                  'fiscal_year': None, 'fiscal_period': None}
    ref = {'document_id': 'opaque-document', 'source_id': 'opaque-source', 'content_sha256': 'a' * 64}

    def cli(root, output, label, command, env, payload=None, **kwargs):
        seen.append(payload)
        if label.endswith('-reference'):
            return 0, {'artifact_sha256': 'b' * 64}, '', b''
        # Even in exact mode the real public reader can still refuse a read.
        return 1, {'error': 'fixture-refusal-no-model'}, '', b''

    monkeypatch.setattr(runner, '_cli', cli)
    with pytest.raises(AssertionError):
        runner.public_bundle(tmp_path, tmp_path, {}, tmp_path / 'config.yaml',
                             {'source_ref': ref}, descriptor, 'owned-read', source_selection=selection)
    expected = seen[-1]['expected_source']
    assert expected == (descriptor if qualified else dict.fromkeys(descriptor))
    assert (seen[-1]['as_of_date'] is not None) == qualified
    assert seen[0]['source_ref'] == ref
    assert (tmp_path / 'owned-read.read-request.json').exists(), 'failed read request must remain inspectable'


@pytest.mark.parametrize('selection', [
    {'mode': 'exact_source_version', 'filing_identity_period_asof_qualification': 'REQUEST_APPLIED'},
    {'mode': 'unknown', 'filing_identity_period_asof_qualification': 'NOT_EVALUATED'},
])
def test_unknown_or_contradictory_read_selection_cannot_disable_filters(tmp_path, monkeypatch, selection):
    monkeypatch.setattr(runner, '_cli', lambda *args, **kwargs: pytest.fail('invalid mode must refuse before IO'))
    with pytest.raises(ValueError, match='selection'):
        runner.public_bundle(tmp_path, tmp_path, {}, tmp_path / 'config.yaml',
                             {'source_ref': {}}, {}, 'owned-read', source_selection=selection)


@pytest.mark.parametrize('fault', [None, 'artifact_sha', 'source_ref'])
def test_exact_content_read_keeps_artifact_sha_and_full_source_ref_binding(tmp_path, monkeypatch, fault):
    from company_wiki.automation.models import canonical_json
    from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
    from unit.test_narrative_fidelity_artifacts import materials

    source, summary = materials()
    bundle = NarrativeVerifyHandler._bundle(source, summary, source.prompt_review)
    wire = bundle.to_dict()
    raw = canonical_json(wire).encode()
    ref = source.source_ref.to_dict()
    reference = {'artifact_sha256': hashlib.sha256(raw).hexdigest(), 'source_ref': ref}
    if fault == 'artifact_sha':
        reference['artifact_sha256'] = 'f' * 64
    imported = {'source_ref': {**ref, 'document_id': 'another-document'} if fault == 'source_ref' else ref}

    def cli(root, output, label, command, env, payload=None, **kwargs):
        if label.endswith('-reference'):
            return 0, reference, '', b''
        assert all(value is None for value in payload['expected_source'].values())
        assert payload['as_of_date'] is None
        receipt = {'replay_status': 'verified', 'narrative_ref': reference}
        return 0, wire, json.dumps(receipt), raw

    monkeypatch.setattr(runner, '_cli', cli)
    selection = {'mode': 'exact_source_version', 'filing_identity_period_asof_qualification': 'NOT_EVALUATED'}
    args = (tmp_path, tmp_path, {}, tmp_path / 'config.yaml', imported, {}, 'content-read')
    if fault is None:
        actual_ref, actual, _, _ = runner.public_bundle(*args, source_selection=selection)
        assert actual_ref == reference and actual.to_dict() == wire
        assert gzip.decompress((tmp_path / 'content-read.bundle.json.gz').read_bytes()) == raw
    else:
        with pytest.raises(AssertionError):
            runner.public_bundle(*args, source_selection=selection)


def prepared_materials(tmp_path):
    from company_wiki.source_catalog.narrative_artifact_store import LocalNarrativeObjectStore, NarrativeArtifactStore
    from unit.test_narrative_artifact_store import _catalog, _draft, SOURCE_SHA

    catalog = _catalog(tmp_path)
    store = NarrativeArtifactStore(catalog, LocalNarrativeObjectStore(tmp_path / 'objects'))
    draft = replace(_draft(), metadata_json=json.dumps({'generation_sha256': 'c' * 64,
                                                       'generation_manifest': {'fixture': 'owner-metadata'}}))
    materials = tmp_path / 'materials'
    materials.mkdir()
    config = {'materials': str(materials), 'activation_run_id': 'owned-run', 'source_sha256': SOURCE_SHA}
    return catalog, store, draft, config


def test_formal_prepare_is_captured_before_activation_and_repeated_bytes_are_immutable(tmp_path, monkeypatch):
    from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactStore, NarrativeArtifactNotVisibleError

    catalog, store, draft, config = prepared_materials(tmp_path)
    original = NarrativeArtifactStore.prepare
    monkeypatch.setattr(NarrativeArtifactStore, 'prepare', observer.prepared_artifact_observer(original, config))
    payload = b'{"actual_owner_payload":"source excerpt"}'
    first = store.prepare(draft, payload)
    assert first.status == 'prepared'
    with pytest.raises(NarrativeArtifactNotVisibleError):
        store.latest_visible_version(document_id=draft.document_id, source_id=draft.source_id,
                                     source_sha256=draft.source_sha256)
    files = list((tmp_path / 'materials').glob('*.prepared.bundle.json.gz'))
    assert len(files) == 1 and gzip.decompress(files[0].read_bytes()) == payload
    capsules = list((tmp_path / 'materials').glob('*.prepared.capsule.json.gz'))
    assert len(capsules) == 1
    capsule = json.loads(gzip.decompress(capsules[0].read_bytes()))
    assert capsule['checkpoint_stage'] == 'prepared_not_activation_proof'
    assert capsule['prepared_draft']['metadata_json'] == draft.metadata_json
    assert capsule['prepared_draft']['created_at'] == first.created_at
    assert capsule['payload']['sha256'] == hashlib.sha256(payload).hexdigest()
    before = {path.name: path.read_bytes() for path in (tmp_path / 'materials').iterdir()}
    # The owner reuses its original durable creation time; the observer must
    # not replace the historical capsule with a retry's transient timestamp.
    store.prepare(replace(draft, created_at='2026-10-31T00:00:00Z'), payload)
    assert {path.name: path.read_bytes() for path in (tmp_path / 'materials').iterdir()} == before


def test_failed_formal_prepare_does_not_create_a_prepared_checkpoint(tmp_path):
    def failed(*args, **kwargs):
        raise RuntimeError('owner refused')

    wrapped = observer.prepared_artifact_observer(failed, {'materials': str(tmp_path)})
    with pytest.raises(RuntimeError, match='owner refused'):
        wrapped(None, None, b'not accepted')
    assert not list(tmp_path.iterdir())


def test_capture_rejects_changed_history_wrong_source_and_oversize_without_overwrite(tmp_path):
    catalog, store, draft, config = prepared_materials(tmp_path)
    payload = b'{"actual":"owner bytes"}'
    version = store.prepare(draft, payload)
    first = observer.capture_prepared_checkpoint(draft, payload, version, config)
    files = {path.name: path.read_bytes() for path in (tmp_path / 'materials').iterdir()}
    with pytest.raises(ValueError):
        observer.capture_prepared_checkpoint(draft, payload, version, {**config, 'source_sha256': 'f' * 64})
    changed = b'{"actual":"changed bytes"}'
    changed_version = replace(version, content_sha256=hashlib.sha256(changed).hexdigest(), byte_size=len(changed))
    with pytest.raises(ValueError, match='CHANGED'):
        observer.capture_prepared_checkpoint(draft, changed, changed_version, config)
    with pytest.raises(ValueError, match='BOUND'):
        observer.capture_prepared_checkpoint(draft, payload, version, {**config, 'prepared_payload_max_bytes': 1})
    assert {path.name: path.read_bytes() for path in (tmp_path / 'materials').iterdir()} == files
    assert first['payload']['bytes'] == len(payload)


def test_actual_generation_checkpoint_is_bounded_and_does_not_overwrite_a_changed_run(tmp_path):
    generation = {'reading_model_projection': 'reading-model-input/7', 'selection_generation': {'material_sha256': 'a' * 64}}
    first = observer.capture_generation_checkpoint(generation, tmp_path, 'owned-run')
    assert json.loads(gzip.decompress((tmp_path / first['file']).read_bytes())) == generation
    assert observer.capture_generation_checkpoint(generation, tmp_path, 'owned-run') == first
    with pytest.raises(ValueError, match='CHANGED'):
        observer.capture_generation_checkpoint({**generation, 'new': 'different'}, tmp_path, 'owned-run')
    with pytest.raises(ValueError, match='PATH'):
        observer.capture_generation_checkpoint(generation, tmp_path, '../escape')


def test_prepared_capsule_binds_actual_generation_and_survives_owner_activation(tmp_path):
    from company_wiki.automation.models import canonical_json_hash

    _, store, draft, config = prepared_materials(tmp_path)
    generation = {'reading_model_projection': 'reading-model-input/7', 'actual_owner_generation': True}
    generation_pin = observer.capture_generation_checkpoint(generation, tmp_path / 'materials', 'owned-run')
    draft = replace(draft, metadata_json=json.dumps({'generation_sha256': canonical_json_hash(generation)}))
    payload = b'{"actual":"prepared bytes"}'
    prepared = store.prepare(draft, payload)
    pin = observer.capture_prepared_checkpoint(draft, payload, prepared, config)
    capsule_path = tmp_path / 'materials' / pin['capsule']['file']
    capsule = json.loads(gzip.decompress(capsule_path.read_bytes()))
    assert capsule['generation_checkpoint'] == generation_pin
    before = capsule_path.read_bytes()
    visible = store.activate(draft.effect_id, verified_after_hash=prepared.content_sha256,
                             activated_at='2026-10-31T00:00:00Z')
    assert visible.status == 'visible'
    assert observer.capture_prepared_checkpoint(draft, payload, visible, config) == pin
    assert capsule_path.read_bytes() == before
    assert capsule['checkpoint_stage'] == 'prepared_not_activation_proof'


def test_generation_or_capsule_bound_refusal_writes_no_payload(tmp_path):
    _, store, draft, config = prepared_materials(tmp_path)
    oversized = {'padding': 'x' * (observer.CHECKPOINT_METADATA_MAX_BYTES + 1)}
    with pytest.raises(ValueError, match='BOUND'):
        observer.capture_generation_checkpoint(oversized, tmp_path / 'materials', 'owned-run')
    draft = replace(draft, metadata_json=json.dumps(oversized))
    payload = b'{"actual":"prepared bytes"}'
    version = store.prepare(draft, payload)
    with pytest.raises(ValueError, match='BOUND'):
        observer.capture_prepared_checkpoint(draft, payload, version, config)
    assert not list((tmp_path / 'materials').iterdir())


def test_prepared_capsule_cannot_borrow_another_generations_checkpoint(tmp_path):
    _, store, draft, config = prepared_materials(tmp_path)
    observer.capture_generation_checkpoint({'actual_generation': 'one'}, tmp_path / 'materials', 'owned-run')
    payload = b'{"actual":"prepared bytes"}'
    version = store.prepare(draft, payload)
    with pytest.raises(ValueError, match='GENERATION_CHANGED'):
        observer.capture_prepared_checkpoint(draft, payload, version, config)
    assert [p.name for p in (tmp_path / 'materials').iterdir()] == ['owned-run.generation.json.gz']
