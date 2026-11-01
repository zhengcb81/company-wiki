"""A single import must not rehash or retire the rest of the data lake."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.scanner import scan_catalog
from company_wiki.source_catalog.store import CatalogStore


def _lake(tmp_path):
    root = tmp_path / "companies"
    directory = root / "示例公司" / "raw"
    directory.mkdir(parents=True)
    first, second = directory / "2025年年度报告.pdf", directory / "2025年半年度报告.pdf"
    first.write_bytes(b"%PDF first")
    second.write_bytes(b"%PDF second")
    config = CatalogConfig(project_root=tmp_path, catalog_dir=tmp_path / ".source_catalog",
                           roots=(RootSpec("company_raw", root, "company_raw"),))
    return config, first, second


@pytest.mark.parametrize("root_kind", ["company_raw", "directory", "dayu_portfolio"])
def test_scoped_scan_does_not_rehash_touch_or_mark_unselected_locations_missing(tmp_path, monkeypatch, root_kind):
    from company_wiki.source_catalog import scanner

    config, first, second = _lake(tmp_path)
    config = replace(config, roots=(replace(config.roots[0], kind=root_kind),))
    store = CatalogStore(config.database_path)
    scan_catalog(config, store)
    untouched = dict(store.fetchone("SELECT * FROM locations WHERE relative_path=?",
                                    (second.relative_to(config.roots[0].path).as_posix(),)))
    root_before = dict(store.fetchone("SELECT * FROM roots WHERE root_id='company_raw'"))
    second.unlink()  # A finite request cannot infer that another document was deleted.
    first.write_bytes(b"%PDF first revised")
    observed = []
    original = scanner._observe_file

    def observe(candidate, **kwargs):
        observed.append(candidate.path)
        return original(candidate, **kwargs)

    monkeypatch.setattr(scanner, "_observe_file", observe)
    def no_walk(_root):
        raise AssertionError("finite company scan must not walk the whole raw directory")
    original_walk = scanner._walk_files
    monkeypatch.setattr(scanner, "_walk_files", no_walk)
    def no_external_metadata(_config):
        raise AssertionError("explicit registration must not discover Dayu metadata")
    monkeypatch.setattr(scanner, "_load_dayu_portfolio_urls", no_external_metadata)
    fetched = []
    original_fetch = store.fetchall
    def fetch(sql, params=()):
        if "relative_path,source_id,document_id" in sql:
            assert "relative_path IN" in sql
            fetched.append(params)
        return original_fetch(sql, params)
    monkeypatch.setattr(store, "fetchall", fetch)
    relative = first.relative_to(config.roots[0].path).as_posix()
    report = scan_catalog(config, store, root_ids={"company_raw"}, relative_paths={relative})
    assert report.errors == 0 and report.files_seen == 1 and report.files_hashed == 1
    assert observed == [first]
    assert dict(store.fetchone("SELECT * FROM locations WHERE location_id=?",
                              (untouched["location_id"],))) == untouched
    assert dict(store.fetchone("SELECT * FROM roots WHERE root_id='company_raw'")) == root_before
    repeated = scan_catalog(config, store, root_ids={"company_raw"}, relative_paths={relative})
    assert repeated.files_hashed == 0 and repeated.files_reused == 1
    assert all(tuple(params) == ("company_raw", relative) for params in fetched)
    monkeypatch.setattr(scanner, "_walk_files", original_walk)
    monkeypatch.undo()
    # Only a complete root scan is allowed to discover missing originals.
    scan_catalog(config, store)
    assert store.fetchone("SELECT location_status FROM locations WHERE location_id=?",
                          (untouched["location_id"],))["location_status"] == "missing"


@pytest.mark.parametrize("paths", [set(), {"../outside.pdf"}, {"/absolute.pdf"},
                                   {"host_absolute"}, {"示例公司\\file.pdf"}])
def test_invalid_finite_scope_rejected_before_catalog_created(tmp_path, paths):
    config, _, _ = _lake(tmp_path)
    if paths == {"host_absolute"}:
        paths = {(Path(tmp_path.anchor) / "absolute.pdf").as_posix()}
    with pytest.raises(ValueError):
        scan_catalog(config, None, dry_run=True, root_ids={"company_raw"}, relative_paths=paths)
    assert not config.catalog_dir.exists()


def test_finite_scope_requires_one_root_and_an_existing_candidate(tmp_path):
    config, _, _ = _lake(tmp_path)
    with pytest.raises(ValueError):
        scan_catalog(config, None, dry_run=True, relative_paths={"示例公司/missing.pdf"})
    with pytest.raises(ValueError):
        scan_catalog(config, None, dry_run=True, root_ids={"company_raw"},
                     relative_paths={"示例公司/missing.pdf"})
    assert not config.catalog_dir.exists()


def test_finite_scan_keeps_the_complete_source_metadata_group(tmp_path):
    config, first, _ = _lake(tmp_path)
    first.with_name(first.name + ".source.json").write_text(
        '{"filing_date":"2026-03-31","market":"CN","security_id":"688012"}', encoding="utf-8")
    store = CatalogStore(config.database_path)
    relative = first.relative_to(config.roots[0].path).as_posix()
    report = scan_catalog(config, store, root_ids={"company_raw"}, relative_paths={relative})
    assert report.files_seen == 2 and report.errors == 0
    row = store.fetchone("SELECT published_date FROM documents")
    assert row["published_date"] == "2026-03-31"
    assert store.fetchone("SELECT COUNT(*) AS n FROM locations")["n"] == 2
    assert store.fetchone("SELECT COUNT(*) AS n FROM documents")["n"] == 1


def test_registration_service_uses_configured_reader_without_old_rollout_scan(tmp_path, monkeypatch):
    from company_wiki.source_catalog import service
    config, first, _ = _lake(tmp_path)
    def obsolete_snapshot(_directory):
        raise AssertionError("registration cannot use an old discovery rollout switch")
    monkeypatch.setattr(service, "v2_scan_shadow_from_snapshot", obsolete_snapshot)
    catalog = service.SourceCatalog(config)
    try:
        result = catalog.register_sources(root_id="company_raw", relative_paths={
            first.relative_to(config.roots[0].path).as_posix()})
        assert result.files_seen == 1 and result.errors == 0
    finally:
        catalog.close()


@pytest.mark.parametrize("declared_kind", ["ir_policy", "meeting_notice", "10-K", "Annual_Report"])
def test_repeated_registration_preserves_capture_kind_without_inventing_conflict(tmp_path, declared_kind):
    from company_wiki.source_catalog.service import SourceCatalog
    from company_wiki.source_catalog.source_reader import SourceVersionReader

    config, first, _ = _lake(tmp_path)
    config = replace(config, roots=(replace(config.roots[0], adapter_id="company_raw_v1"),))
    first.with_name(first.name + ".source.json").write_text(json.dumps({
        "source_title": "Investor relations record", "document_kind": declared_kind,
        "market": "CN", "security_id": "688012", "filing_date": "2026-03-31",
    }), encoding="utf-8")
    catalog = SourceCatalog(config)
    try:
        catalog.scan()
        row = catalog.reader.fetchone("SELECT d.document_id,d.primary_source_id,s.content_sha256 "
            "FROM documents d JOIN sources s ON s.source_id=d.primary_source_id "
            "WHERE d.title='Investor relations record'")
        reader = SourceVersionReader(catalog)
        ref = reader.query_ref(row["document_id"], row["primary_source_id"], row["content_sha256"])
        before = reader.describe_version(ref)
        for _ in range(2):
            catalog.register_sources(root_id="company_raw", relative_paths={
                first.relative_to(config.roots[0].path).as_posix()})
            assert reader.describe_version(ref) == before
        metadata = json.loads(catalog.reader.fetchone("SELECT metadata_json FROM documents "
            "WHERE document_id=?", (ref.document_id,))["metadata_json"])
        assert not any(item.get("conflicts") for item in metadata["r4_provenance"]["fields"].values())
        assert metadata["acquisition"]["document_kind"].casefold() == declared_kind.casefold()
        # A disputed declaration becomes unknown; bytes remain available.
        sidecar = first.with_name(first.name + ".source.json")
        changed = json.loads(sidecar.read_text(encoding="utf-8"))
        changed["document_kind"] = "prospectus"
        sidecar.write_text(json.dumps(changed), encoding="utf-8")
        catalog.register_sources(root_id="company_raw", relative_paths={
            first.relative_to(config.roots[0].path).as_posix()})
        disputed = reader.describe_version(ref)
        assert disputed["document_kind"] is None
        assert reader.metadata_diagnostics(ref)["conflicted_fields"]
        assert reader.open_version(ref, purpose="source_export").content_sha256 == ref.content_sha256
    finally:
        catalog.close()
