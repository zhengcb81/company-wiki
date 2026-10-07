"""A spent batch budget must stop preparing subsequent sources and new jobs."""
from dataclasses import replace
import hashlib
from types import SimpleNamespace

import pytest

from unit.test_narrative_batch import SparseMetadataReader, _module, _request
from company_wiki.source_contract import source_id_for_sha256


@pytest.mark.parametrize('spent_in', ['configuration', 'catalog', 'metadata', 'language', 'verification'])
@pytest.mark.parametrize('existing_auto', [False, True])
def test_expired_preparation_never_starts_next_source_or_materializes_jobs(tmp_path, monkeypatch, spent_in, existing_auto):
    module = _module()
    clock = SimpleNamespace(now=10.0)
    body = b'Full Conference Call Transcript\nCEO: We launched a new product.\n'
    digest = hashlib.sha256(body).hexdigest()
    raw = _request().to_dict()
    raw['sources'][0].update(source_id=source_id_for_sha256(digest), content_sha256=digest, byte_size=len(body))
    raw['sources'].append({**raw['sources'][0], 'document_id': 'doc-b'})
    request = type(_request()).from_dict(raw)
    observed = SimpleNamespace(queries=[], opens=[], created=False, closed=False)
    auto_path = tmp_path / 'auto.db'
    if existing_auto:
        from company_wiki.automation.store import AutomationStore
        AutomationStore(auto_path)
    auto_before = auto_path.read_bytes() if auto_path.exists() else None

    class ExpiringReader(SparseMetadataReader):
        def query_ref(self, *args):
            observed.queries.append(args[0])
            return super().query_ref(*args)

        def describe_version(self, ref):
            if spent_in == 'metadata':
                clock.now = 100.0
            return super().describe_version(ref)

        def open_version(self, ref, **kwargs):
            observed.opens.append(ref.document_id)
            if spent_in in {'language', 'verification'}:
                clock.now = 100.0
            return super().open_version(ref, **kwargs)

    reader = ExpiringReader(body)
    if spent_in not in {'metadata', 'language'}:
        reader.metadata['language'] = 'en'
    config = SimpleNamespace(catalog_dir=tmp_path/'catalog', database_path=tmp_path/'catalog.db', roots=())

    def load(*args, **kwargs):
        if spent_in == 'configuration':
            clock.now = 100.0
        return config

    def catalog(_config):
        observed.created = True
        if spent_in == 'catalog':
            clock.now = 100.0
        return SimpleNamespace(config=config, close=lambda: setattr(observed, 'closed', True))

    def materialize(_path):
        pytest.fail('expired preparation reached AUTO initialization')

    monkeypatch.setattr(module.time, 'monotonic', lambda: clock.now)
    monkeypatch.setattr(module, 'load_catalog_config', load)
    monkeypatch.setattr(module, 'SourceCatalog', catalog)
    monkeypatch.setattr(module, 'SourceVersionReader', lambda _catalog: reader)
    monkeypatch.setattr(module, 'AutomationStore', materialize)
    with pytest.raises(TimeoutError, match='BATCH_PREPARATION_DEADLINE_EXCEEDED'):
        module.run_batch(replace(request, max_seconds=1), project_root=tmp_path,
                         catalog_config_path=tmp_path/'config.json', db_path=tmp_path/'auto.db',
                         work_dir=tmp_path/'work')
    # Verification follows metadata collection. Metadata collected while time
    # remained is valid; no second raw may be opened after the first expires.
    assert observed.queries == ([] if spent_in in {'configuration','catalog'} else
                                ['doc-a','doc-b'] if spent_in == 'verification' else ['doc-a'])
    assert observed.opens == (['doc-a'] if spent_in in {'language','verification'} else [])
    assert not observed.created or observed.closed
    assert spent_in != 'configuration' or not observed.created
    assert (auto_path.read_bytes() if auto_path.exists() else None) == auto_before
    assert not (tmp_path/'work').exists()
