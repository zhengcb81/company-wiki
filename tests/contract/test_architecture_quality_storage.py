"""Canonical import must use current registered storage, not stale paths."""
from dataclasses import replace
from pathlib import Path

from company_wiki.source_catalog import CanonicalImportStatus, CanonicalSourceWriter, SourceCatalog
from test_source_catalog_canonical_writer import _catalog, _staged_contract


def _import(tmp_path):
    catalog = _catalog(tmp_path)
    request, candidate, receipt, _ = _staged_contract(tmp_path)
    result = CanonicalSourceWriter(catalog).import_staged(request, candidate, receipt)
    catalog.close()
    return catalog, Path(result.canonical_path), receipt.content_sha256


def _relocated_catalog(catalog, new_root, *, root_id=None):
    root = replace(catalog.config.roots[0], path=new_root,
                   root_id=root_id or catalog.config.roots[0].root_id)
    return SourceCatalog(replace(catalog.config, roots=(root,)))


def test_dedup_follows_registered_root_relocation_without_full_scan(tmp_path):
    catalog, original, sha = _import(tmp_path)
    old_root = catalog.config.roots[0].path
    new_root = old_root.with_name("moved-companies")
    old_root.rename(new_root)
    relocated = _relocated_catalog(catalog, new_root)
    expected = new_root / original.relative_to(old_root)
    try:
        assert CanonicalSourceWriter(relocated)._existing_original(sha) == expected.resolve()
        assert expected.is_file()
    finally:
        relocated.close()


def test_dedup_never_adopts_historical_path_outside_current_root(tmp_path):
    catalog, original, sha = _import(tmp_path)
    new_root = catalog.config.project_root / "new-companies"
    new_root.mkdir()
    relocated = _relocated_catalog(catalog, new_root)
    try:
        assert CanonicalSourceWriter(relocated)._existing_original(sha) is None
        assert original.is_file()
    finally:
        relocated.close()


def test_removed_root_is_not_a_dedup_candidate(tmp_path):
    catalog, original, sha = _import(tmp_path)
    relocated = _relocated_catalog(catalog, catalog.config.roots[0].path,
                                   root_id="replacement-root")
    try:
        assert CanonicalSourceWriter(relocated)._existing_original(sha) is None
        assert original.is_file()
    finally:
        relocated.close()


def test_invalid_relative_locator_cannot_be_hidden_by_valid_absolute_path(tmp_path):
    catalog, original, sha = _import(tmp_path)
    with catalog.store.transaction() as connection:
        connection.execute("UPDATE locations SET relative_path='../outside.pdf' WHERE source_id=?",
                           ("urn:company-wiki:source:sha256:" + sha,))
    try:
        assert CanonicalSourceWriter(catalog)._existing_original(sha) is None
        assert original.is_file()
    finally:
        catalog.close()


def test_full_import_reuses_moved_raw_and_public_reader_rechecks_bytes(tmp_path):
    from company_wiki.source_catalog.source_reader import SourceVersionReader

    catalog, original, sha = _import(tmp_path)
    old_root = catalog.config.roots[0].path
    new_root = old_root.with_name("moved-companies")
    old_root.rename(new_root)
    relocated = _relocated_catalog(catalog, new_root)
    expected = new_root / original.relative_to(old_root)
    before = {p.relative_to(new_root): p.read_bytes() for p in new_root.rglob("*") if p.is_file()}
    (catalog.config.catalog_dir / "staging" / "request").rmdir()
    request, candidate, receipt, staged = _staged_contract(tmp_path)
    try:
        imported = CanonicalSourceWriter(relocated).import_staged(request, candidate, receipt)
        assert imported.status is CanonicalImportStatus.DEDUPLICATED_AFTER_DOWNLOAD
        assert Path(imported.canonical_path) == expected.resolve()
        assert imported.content_sha256 == sha
        assert not staged.exists()
        assert SourceVersionReader(relocated).open_version(imported.source_ref).data == expected.read_bytes()
        assert {p.relative_to(new_root): p.read_bytes() for p in new_root.rglob("*") if p.is_file()} == before
    finally:
        relocated.close()


def test_moved_location_still_must_match_actual_sha(tmp_path):
    catalog, original, sha = _import(tmp_path)
    original.write_bytes(b"corrupt bytes in isolated fixture")
    try:
        assert CanonicalSourceWriter(catalog)._existing_original(sha) is None
        assert original.read_bytes() == b"corrupt bytes in isolated fixture"
    finally:
        catalog.close()
