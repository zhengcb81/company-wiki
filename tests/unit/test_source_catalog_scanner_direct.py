"""Direct unit coverage for ``scan_catalog`` (Phase 6 D2).

The scanner is on the hot path of every canonical write, but it had no direct
test — only indirect coverage through writer/acquisition tests and two focus
admission cases.  These tests call ``scan_catalog`` directly so its report
shape, dry-run behaviour, and transaction/error handling are pinned.
"""

from __future__ import annotations

import pytest

from helpers.source_factory import canonical_source

from company_wiki.source_catalog import CatalogConfig, RootSpec
from company_wiki.source_catalog.scanner import scan_catalog
from company_wiki.source_catalog.store import CatalogStore


def _config(tmp_path) -> CatalogConfig:
    project = tmp_path / "project"
    return CatalogConfig(
        project_root=project,
        catalog_dir=project / ".source_catalog",
        roots=(
            RootSpec("company_raw", project / "companies", "company_raw", priority=10),
        ),
    )


def _store(tmp_path) -> CatalogStore:
    return CatalogStore(_config(tmp_path).catalog_dir)


def test_scan_catalog_indexes_one_canonical_source(tmp_path):
    canonical_source(tmp_path)
    config = _config(tmp_path)
    store = _store(tmp_path)
    report = scan_catalog(config, store, root_ids={"company_raw"})
    # The primary file and its sidecar are scanned; the primary document is
    # indexed as an active location.
    assert report.files_seen >= 1
    assert report.locations_active >= 1
    assert report.errors == 0


def test_scan_catalog_dry_run_returns_report_without_store(tmp_path):
    canonical_source(tmp_path)
    config = _config(tmp_path)
    report = scan_catalog(config, None, dry_run=True, root_ids={"company_raw"})
    assert report is not None
    assert report.dry_run is True


def test_scan_catalog_requires_store_for_real_run(tmp_path):
    canonical_source(tmp_path)
    config = _config(tmp_path)
    with pytest.raises(TypeError):
        scan_catalog(config, None, root_ids={"company_raw"})


def test_scan_catalog_interrupts_run_on_error(tmp_path, monkeypatch):
    canonical_source(tmp_path)
    config = _config(tmp_path)
    store = _store(tmp_path)

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(store, "coalesced_transactions", _boom)
    with pytest.raises(RuntimeError):
        scan_catalog(config, store, root_ids={"company_raw"})
    # The interrupted scan run is recorded so no run is left dangling.
    with store.transaction() as connection:
        rows = connection.execute(
            "SELECT status FROM scan_runs WHERE status='running'"
        ).fetchall()
    assert rows == []
