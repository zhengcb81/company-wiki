"""Maintenance failures must preserve rows and report actual operation state."""

from support.p5_storage_catalog_fixture import build_catalog
from company_wiki.source_catalog.lock import CatalogOperationLock
from legacy_storage.shrink import run_vacuum


def test_current_catalog_writer_refuses_active_vacuum(tmp_path):
    config, store, _ = build_catalog(tmp_path)
    count = store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"]
    with CatalogOperationLock(config.catalog_dir, operation="fixture-current-writer"):
        reports = [run_vacuum(config)]
    assert all(r["status"] == "refused" and r["error_code"] == "catalog_busy" for r in reports)
    assert store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"] == count
