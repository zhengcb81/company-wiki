"""All configured adapters discover only explicit groups; scanner owns hashing."""

import json

import pytest


@pytest.mark.parametrize("kind", ["company_raw", "sidecar", "dayu"])
def test_registration_adapter_does_not_read_unselected_originals_or_hash_candidates(tmp_path, monkeypatch, kind):
    from company_wiki.source_catalog.adapters import company_raw, dayu, sidecar

    if kind == "company_raw":
        module, cls = company_raw, company_raw.CompanyRawAdapter
        relative = "示例公司/raw/one.pdf"
        other = "其他公司/raw/other.pdf"
    elif kind == "dayu":
        module, cls = dayu, dayu.DayuAdapter
        relative = "MSFT/filings/one/one.pdf"
        other = "MSFT/filings/two/two.pdf"
    else:
        module, cls = sidecar, sidecar.SidecarFilingAdapter
        relative = "one/one.pdf"
        other = "two/two.pdf"
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_bytes(b"%PDF selected source")
    unselected = tmp_path / other
    unselected.parent.mkdir(parents=True)
    unselected.write_bytes(b"unselected source")
    if kind == "dayu":
        (target.parent / "meta.json").write_text(json.dumps({"title":"selected"}), encoding="utf-8")
    def must_not_hash(_path):
        raise AssertionError("adapter registration must defer byte verification to scanner")
    monkeypatch.setattr(module, "_sha256_file", must_not_hash)
    adapter = cls()
    selected = adapter.enumerate(tmp_path, relative_paths={relative}, compute_hash=False)
    assert selected and all(item.group_key not in {other, "MSFT/filings/two"} for item in selected)
    assert {item.relative_path for item in selected} <= {relative, "MSFT/filings/one/meta.json"}
    assert all(item.content_sha256 == "" for item in selected)


def test_deferred_adapter_hash_still_rejects_wrong_declared_source_bytes(tmp_path):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    root = tmp_path / "lake"
    root.mkdir()
    primary = root / "one.pdf"
    primary.write_bytes(b"%PDF actual original")
    primary.with_name(primary.name + ".source.json").write_text(json.dumps({
        "schema_version":"1.0", "canonical_entity_id":"cn:688012", "market":"CN", "security_id":"688012",
        "document_kind":"annual_report", "fiscal_year":2025, "period_end":"2025-12-31",
        "content_sha256":"0"*64, "provider":"cninfo", "provider_document_id":"one",
    }), encoding="utf-8")
    catalog = SourceCatalog(CatalogConfig(project_root=tmp_path, catalog_dir=tmp_path / ".source_catalog",
        roots=(RootSpec("lake", root, "directory", adapter_id="sidecar_filing_v1"),)))
    try:
        report = catalog.register_sources(root_id="lake", relative_paths={"one.pdf"})
        assert report.errors == 1
        assert catalog.store.fetchone("SELECT location_status FROM locations")["location_status"] == "quarantined"
        assert catalog.store.fetchone("SELECT COUNT(*) AS n FROM sources")["n"] == 0
    finally:
        catalog.close()


def test_unchanged_original_cannot_bypass_new_sidecar_sha_disagreement(tmp_path):
    import hashlib
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    root = tmp_path / "companies"
    original = root / "示例公司/raw/one.pdf"
    original.parent.mkdir(parents=True)
    data = b"%PDF same immutable original"
    original.write_bytes(data)
    sidecar = original.with_name(original.name + ".source.json")
    sidecar.write_text(json.dumps({"content_sha256":hashlib.sha256(data).hexdigest()}), encoding="utf-8")
    catalog = SourceCatalog(CatalogConfig(project_root=tmp_path, catalog_dir=tmp_path / ".source_catalog",
        roots=(RootSpec("company_raw", root, "company_raw"),)))
    try:
        scope = {original.relative_to(root).as_posix()}
        assert catalog.register_sources(root_id="company_raw", relative_paths=scope).errors == 0
        sidecar.write_text(json.dumps({"content_sha256":"0"*64}), encoding="utf-8")
        report = catalog.register_sources(root_id="company_raw", relative_paths=scope)
        assert report.errors == 1
        assert catalog.store.fetchone("SELECT location_status FROM locations WHERE role='original_primary'")["location_status"] == "quarantined"
        assert original.read_bytes() == data
    finally:
        catalog.close()
