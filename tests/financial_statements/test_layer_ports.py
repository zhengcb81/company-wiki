"""Exercise storage/provider substitutions without exposing physical layouts."""
import hashlib
import sqlite3
from types import SimpleNamespace
from contextlib import closing

import pytest

from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter, CanonicalImportError
from company_wiki.source_catalog.financial_statements.service import handle_reuse_only_request
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
from .test_service_contracts import _recorder, _zhongwei_lrb, _service
from .test_root_acceptance_regressions import request, report
from .test_canonical_writer_third_party import _original
from . import test_service_contracts as service_fixtures

catalog = service_fixtures.catalog


def test_service_passes_bytes_to_writer_without_staging_knowledge(catalog, monkeypatch):
    service = _service(catalog, _recorder(_zhongwei_lrb()))
    actual_writer = service.writer
    calls = []
    def store_bytes(**arguments):
        calls.append(arguments)
        return actual_writer.import_third_party_dataset_bytes(**arguments)
    service.writer = SimpleNamespace(import_third_party_dataset_bytes=store_bytes)
    identify = catalog.identify_company
    resolutions = []
    def identify_once(*args, **kwargs):
        resolutions.append((args, kwargs))
        return identify(*args, **kwargs)
    monkeypatch.setattr(catalog, "identify_company", identify_once)
    response = service.handle_request(request())
    assert response["status"] == "complete" and calls
    assert len(resolutions) == 1
    assert all(isinstance(call["data"], bytes) and "staged_path" not in call for call in calls)
    ref = SourceRef(**report(response)["source_ref"])
    assert SourceVersionReader(catalog).open_version(ref, purpose="preview").data


def test_readonly_reuse_never_opens_writable_store(catalog, monkeypatch):
    _service(catalog, _recorder(_zhongwei_lrb())).handle_request(request())
    def forbidden(_):
        raise AssertionError("readonly query reached CatalogStore")
    monkeypatch.setattr(type(catalog), "store", property(forbidden))
    response = handle_reuse_only_request(request(intent="reuse_only", acquisition_limits=None), catalog.config)
    assert response["status"] == "complete"
    assert response["usage"]["http_requests"] == 0
    assert report(response)["source_ref"]["byte_size"] > 0


def _import(writer, data, *, sha=None):
    return writer.import_third_party_dataset_bytes(request_id="same-request",
        original=_original(), data=data, content_sha256=sha or hashlib.sha256(data).hexdigest(),
        mime_type="application/json", retrieved_at="2026-10-25T12:00:00Z", capture_receipt={})


def test_writer_owns_unique_staging_for_interleaved_requests(catalog, monkeypatch):
    writer = CanonicalSourceWriter(catalog)
    commit = writer.import_third_party_dataset_staged
    staged_paths = []
    nested = []
    outer_data, inner_data = b'{"capture":1}', b'{"capture":2}'
    def interleave(**arguments):
        staged_paths.append(arguments["staged_path"])
        if len(staged_paths) == 1:
            nested.append(_import(writer, inner_data))
            assert arguments["staged_path"].read_bytes() == outer_data
        return commit(**arguments)
    monkeypatch.setattr(writer, "import_third_party_dataset_staged", interleave)
    outer = _import(writer, outer_data)
    reader = SourceVersionReader(catalog)
    assert reader.open_version(outer.source_ref, purpose="preview").data == outer_data
    assert reader.open_version(nested[0].source_ref, purpose="preview").data == inner_data
    assert len(set(staged_paths)) == 2
    assert all(not path.parent.exists() for path in staged_paths)


def test_writer_cleans_private_staging_when_bytes_rejected(catalog):
    writer = CanonicalSourceWriter(catalog)
    with pytest.raises(CanonicalImportError, match="byte identity mismatch"):
        _import(writer, b'{"capture":1}', sha="f" * 64)
    assert not list(writer.staging_root.glob("dataset-*"))
    assert not list(catalog.config.roots[0].path.rglob("*.json"))


def test_legacy_capture_migration_preserves_sources_without_inventing_order(catalog, monkeypatch):
    from company_wiki.source_catalog.store import CatalogStore
    from company_wiki.source_catalog.financial_statements import service as module
    monkeypatch.setattr(module, "_utc_now", lambda: "2026-10-01T00:00:00Z")
    service = _service(catalog, _recorder(_zhongwei_lrb()))
    original = report(service.handle_request(request()))
    with sqlite3.connect(catalog.config.database_path) as connection:
        connection.execute("DROP TABLE financial_statement_observations")
        connection.execute("UPDATE catalog_meta SET value='1.3.0' WHERE key='schema_version'")
    CatalogStore(catalog.config.database_path)
    with sqlite3.connect(catalog.config.database_path) as connection:
        count, verified = connection.execute("SELECT COUNT(*), SUM(order_verified) "
            "FROM financial_statement_observations").fetchone()
        assert count == 36 and verified == 0
    current = report(service.handle_request(request(intent="reuse_only", acquisition_limits=None)))
    assert current["source_ref"] == original["source_ref"]
    assert current["rows"] == original["rows"]
    assert current["observation_order_verified"] is False
    response = service.handle_request(request(intent="reuse_only", acquisition_limits=None))
    assert response["status"] == "partial"
    assert response["statements"][0]["version_selection_quality"] == "legacy_observation_order_unverified"
    monkeypatch.setattr(module, "_utc_now", lambda: "2026-10-20T00:00:00Z")
    confirmed = service.handle_request(request(intent="refresh"))
    assert confirmed["status"] == "complete"
    assert report(confirmed)["observation_order_verified"] is True
    past = handle_reuse_only_request(request(intent="reuse_only", acquisition_limits=None,
        knowledge_mode="point_in_time", as_of_date="2026-10-10"), catalog.config)
    assert report(past)["pit_verified"] is False
    assert report(past)["observation_order_verified"] is False
    count = catalog.store.fetchone("SELECT COUNT(*) AS n FROM financial_statement_observations")["n"]
    assert count == 72
    service.handle_request(request(intent="refresh"))
    assert catalog.store.fetchone("SELECT COUNT(*) AS n FROM financial_statement_observations")["n"] == count


@pytest.mark.parametrize("intent", ["reuse_only", "fetch_if_missing"])
def test_missing_identity_snapshot_is_named_and_does_not_create_catalog(tmp_path, intent):
    from company_wiki.source_catalog.models import CatalogConfig, RootSpec
    from company_wiki.source_catalog.service import SourceCatalog
    config = CatalogConfig(project_root=tmp_path, catalog_dir=tmp_path / "db",
        roots=(RootSpec("company_raw", tmp_path / "c", "company_raw", priority=10),))
    if intent == "reuse_only":
        response = handle_reuse_only_request(request(intent=intent, acquisition_limits=None), config)
    else:
        response = _service(SourceCatalog(config), _recorder(_zhongwei_lrb())).handle_request(request())
    assert response["reason"] == "company_identity_snapshot_unavailable"
    assert response["status"] == "not_found"
    assert response["usage"]["http_requests"] == 0
    assert not config.database_path.exists()


@pytest.mark.parametrize("old_schema", ["1.2.0", "1.3.0"])
def test_additive_financial_upgrade_does_not_gate_existing_original_reader(catalog, old_schema):
    original = report(_service(catalog, _recorder(_zhongwei_lrb())).handle_request(request()))
    ref = SourceRef(**original["source_ref"])
    expected = SourceVersionReader(catalog).open_version(ref, purpose="preview").data
    catalog.close()
    database = catalog.config.database_path
    with closing(sqlite3.connect(database)) as connection:
        for table in ("financial_statement_observations", "financial_statement_values",
                      "financial_statement_coverage", "financial_statement_versions"):
            connection.execute(f"DROP TABLE {table}")
        connection.execute("UPDATE catalog_meta SET value=? WHERE key='schema_version'", (old_schema,))
        connection.commit()
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    assert SourceVersionReader(catalog).open_version(ref, purpose="preview").data == expected
    catalog.close()
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    gap = handle_reuse_only_request(request(intent="reuse_only", acquisition_limits=None), catalog.config)
    assert gap["status"] == "not_found" and gap["reason"] == "financial_statements_unavailable"
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT value FROM catalog_meta WHERE key='schema_version'").fetchone()[0] == old_schema
