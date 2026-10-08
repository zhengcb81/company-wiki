"""Source bytes, selected facts and historical availability have separate owners."""

from dataclasses import replace
import json

import pytest

from company_wiki.source_catalog.resolver import SourceRequest, SourceResolver
from company_wiki.source_catalog.source_reader import SourceReadError, SourceVersionReader
from company_wiki.source_contract.source_export_v2 import SourceExportBundleV2
from contract.test_source_version_reader import BODY, SHA, _fixture


@pytest.fixture
def lake(tmp_path):
    catalog, paths, _, ids = _fixture(tmp_path)
    reader = SourceVersionReader(catalog)
    ref = reader.query_ref(ids['document_id'], ids['source_id'], SHA)
    try:
        yield catalog, reader, ref, paths[0]
    finally:
        catalog.close()


def dispute(catalog, ref, *fields):
    row = catalog.reader.exact_source_version(ref.document_id)
    metadata = json.loads(row['metadata_json'])
    provenance = metadata.setdefault('r4_provenance', {}).setdefault('fields', {})
    for field in fields:
        provenance[field] = {'value': 'old-hash', 'sources': [],
                             'conflicts': [{'source_id': 'different-observation', 'value_hash': 'other'}]}
    with catalog.store.transaction() as connection:
        connection.execute('UPDATE documents SET metadata_json=? WHERE document_id=?',
                           (json.dumps(metadata), ref.document_id))


def request(**kwargs):
    return SourceRequest(entity='Acme', document_kind='annual_report',
                         as_of_date='2026-10-08', **kwargs)


@pytest.mark.parametrize('field,manifest_field', [
    ('acquisition.source_url', 'source_url'), ('title', 'title'),
    ('acquisition.collector_name', 'collector_name'),
    ('acquisition.provider_document_id', 'provider_document_id'),
])
def test_disputed_auxiliary_facts_are_unknown_and_do_not_block_bytes_or_export(lake, field, manifest_field):
    catalog, reader, ref, original = lake
    dispute(catalog, ref, field)
    manifest = reader.describe_version(ref)
    assert manifest[manifest_field] is None
    assert reader.open_version(ref).data == BODY
    exported = SourceExportBundleV2.build(source_reader=reader, refs=[ref], evidence_spans=[]).to_dict()
    assert exported['manifests'][0][manifest_field] is None
    assert original.read_bytes() == BODY
    observed = reader.metadata_diagnostics(ref)
    assert field in observed['conflicted_fields']
    assert 'path' not in json.dumps(observed)


def test_auxiliary_conflict_does_not_remove_company_anchored_query_result(lake):
    catalog, reader, ref, _ = lake
    dispute(catalog, ref, 'acquisition.source_url')
    assert reader.query_local(request(fiscal_year=2025)).matches == (ref,)
    assert SourceResolver(catalog).resolve(request(fiscal_year=2025)).matches


def test_disputed_period_is_not_inferred_again_from_filename(lake):
    catalog, reader, ref, _ = lake
    dispute(catalog, ref, 'acquisition.fiscal_year')
    assert reader.describe_version(ref)['fiscal_year'] is None
    assert reader.open_version(ref).data == BODY
    assert reader.query_local(request(fiscal_year=2025)).matches == ()
    assert SourceResolver(catalog).resolve(request(fiscal_year=2025)).matches == ()
    assert reader.query_local(request()).matches == (ref,)


def test_disputed_publication_only_excludes_historical_selection(lake):
    catalog, reader, ref, _ = lake
    dispute(catalog, ref, 'published_date')
    assert reader.describe_version(ref)['published_date'] is None
    assert reader.open_version(ref).data == BODY
    assert reader.query_local(request()).matches == ()
    assert SourceResolver(catalog).resolve(request()).matches == ()


@pytest.mark.parametrize('invalid', ['[', '[]', '{"r4_provenance":false}', '{"r4_provenance":{"fields":[]}}'])
def test_unreadable_auxiliary_metadata_does_not_make_raw_inaccessible(lake, invalid):
    catalog, reader, ref, _ = lake
    with catalog.store.transaction() as connection:
        connection.execute('UPDATE documents SET metadata_json=? WHERE document_id=?', (invalid, ref.document_id))
    assert reader.open_version(ref).data == BODY
    assert reader.describe_version(ref)['content_sha256'] == SHA
    assert reader.metadata_diagnostics(ref)['problems']


@pytest.mark.parametrize('runtime', ['{', '{"schema_version":"1.0","activation_enabled":true}', 'null'])
def test_legacy_runtime_file_cannot_deny_current_bytes(lake, runtime):
    catalog, reader, ref, _ = lake
    (catalog.config.catalog_dir / 'runtime_policy.json').write_text(runtime, encoding='utf-8')
    assert reader.open_version(ref).data == BODY
    assert reader.query_local(request()).matches == (ref,)


def test_old_read_fingerprint_is_observation_and_actual_corruption_still_refused(lake):
    _, reader, ref, original = lake
    opened = reader.open_version(ref, expected_read_policy_sha256='a' * 64)
    assert opened.data == BODY
    assert opened.source_read_policy_sha256 != 'a' * 64
    original.write_bytes(b'X' * len(BODY))
    with pytest.raises(SourceReadError, match='no_verified_location'):
        reader.open_version(ref, expected_read_policy_sha256='a' * 64)


def test_current_root_limits_still_apply_when_fingerprint_drifts(lake):
    catalog, reader, ref, _ = lake
    pin = reader.read_policy_sha256(ref)
    catalog.config = replace(catalog.config, roots=(replace(catalog.config.roots[0], max_file_size=1),))
    with pytest.raises(SourceReadError, match='root_admission_denied'):
        reader.open_version(ref, expected_read_policy_sha256=pin)


def test_exact_open_does_not_reselect_period_or_require_publication(lake):
    catalog, reader, ref, _ = lake
    catalog.record_source_facts(ref=ref, facts={'published_date': None},
                               evidence={'published_date': {'locator': 'fixture:unknown', 'value': None}})
    assert reader.open_version(ref, purpose='filing_reuse').data == BODY
    assert reader.query_local(request()).matches == ()


@pytest.mark.parametrize('field', ['capture.market', 'capture.security_id', 'capture.canonical_entity_id'])
def test_actual_disputed_requested_identity_is_excluded_without_denying_raw(lake, field):
    catalog, reader, ref, _ = lake
    dispute(catalog, ref, field)
    scoped = request(market='US', security_id='ACME')
    assert reader.query_local(scoped).matches == ()
    assert SourceResolver(catalog).resolve(scoped).matches == ()
    assert reader.open_version(ref).data == BODY


def test_explicit_source_fact_correction_resolves_publication_without_rewriting_capture(lake):
    catalog, reader, ref, original = lake
    dispute(catalog, ref, 'published_date')
    original_metadata = catalog.reader.exact_source_version(ref.document_id)['metadata_json']
    assert reader.query_local(request()).matches == ()
    catalog.record_source_facts(ref=ref, facts={'published_date': '2026-10-01'},
        evidence={'published_date': {'locator': 'fixture:explicit-correction', 'value': '2026-10-01'}})
    assert reader.query_local(request()).matches == (ref,)
    assert reader.describe_version(ref)['published_date'] == '2026-10-01'
    assert catalog.reader.exact_source_version(ref.document_id)['metadata_json'] == original_metadata
    assert original.read_bytes() == BODY
