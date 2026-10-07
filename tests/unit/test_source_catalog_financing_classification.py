"""Financing filings must reach narrative routing without changing raw identity."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from helpers.source_factory import canonical_source

from company_wiki.source_catalog import CatalogConfig, RootSpec
from company_wiki.source_contract import SourceType
from company_wiki.source_catalog.scanner import _classification, _merge_columns, scan_catalog
from company_wiki.source_catalog.store import CatalogStore


@pytest.mark.parametrize("kind", [
    "equity_offering_prospectus", "convertible_bond_prospectus",
])
def test_explicit_financing_kind_has_sidecar_priority(kind):
    assert _classification(
        Path("annual report.pdf"), root_kind="company_raw",
        metadata={"document_kind": kind, "form_type": "10-k"},
    ) == (kind, SourceType.PROSPECTUS)


@pytest.mark.parametrize(("title", "kind"), [
    ("某公司向特定对象发行股票募集说明书（注册稿）.PDF", "equity_offering_prospectus"),
    ("某公司公开发行股票募集说明书.pdf", "equity_offering_prospectus"),
    ("公司向不特定对象发行可转换公司债券证券募集说明书.PDF", "convertible_bond_prospectus"),
    ("公司可转换债券募集说明书.pdf", "convertible_bond_prospectus"),
    ("Equity Offering Prospectus.pdf", "equity_offering_prospectus"),
    ("Convertible Bond Prospectus.pdf", "convertible_bond_prospectus"),
])
def test_specific_financing_prospectus_titles(title, kind):
    assert _classification(Path(title), root_kind="company_raw", metadata={}) == (
        kind, SourceType.PROSPECTUS,
    )


@pytest.mark.parametrize(("title", "metadata", "kind", "source_type"), [
    ("发行股票董事会决议公告.pdf", {}, "other", SourceType.OTHER),
    ("发行可转换公司债券发行结果公告.pdf", {}, "other", SourceType.OTHER),
    ("公司债券募集说明书.pdf", {}, "other", SourceType.OTHER),
    ("可转换公司债券募集说明书点评.pdf", {}, "broker_research", SourceType.BROKER_RESEARCH),
    ("向特定对象发行股票募集说明书.pdf", {"document_kind": "news"}, "news", SourceType.ORIGINAL_NEWS),
    ("上市招股说明书.pdf", {}, "prospectus", SourceType.PROSPECTUS),
])
def test_notices_commentary_and_explicit_kind_are_not_misclassified(
    title, metadata, kind, source_type,
):
    assert _classification(Path(title), root_kind="company_raw", metadata=metadata) == (
        kind, source_type,
    )


@pytest.mark.parametrize(("declared", "incoming_source"), [
    ({"document_kind": True}, "source-a"),
    ({"source_type": True}, "source-a"),
    ({}, "source-b"),
])
def test_financing_refinement_preserves_declared_or_different_source_facts(declared, incoming_source):
    stored = {"primary_source_id": "source-a", "document_kind": "other",
              "source_type": "other", "published_date": "2025-01-01"}
    incoming = {"primary_source_id": incoming_source, "document_kind": "equity_offering_prospectus",
                "source_type": "prospectus", "published_date": "2025-02-01"}
    merged, fields, _ = _merge_columns(
        stored, incoming=incoming, source_id=incoming_source, observed_at="2026-10-07T00:00:00Z",
        fields={}, stored_declared=declared, incoming_declared={},
    )
    assert merged["document_kind"] == "other"
    assert merged["source_type"] == "other"
    assert merged["published_date"] == "2025-01-01"
    assert fields["published_date"]["conflicts"]


@pytest.mark.parametrize(("filename", "kind"), [
    ("公司向特定对象发行股票募集说明书.PDF", "equity_offering_prospectus"),
    ("公司可转换公司债券募集说明书.PDF", "convertible_bond_prospectus"),
])
def test_rescan_corrects_legacy_kind_without_new_source_or_raw_write(tmp_path, filename, kind):
    data = b"%PDF-1.4\nimmutable source for classification only"
    path = canonical_source(tmp_path, filename=filename, kind_dir="research",
                            source_title=Path(filename).stem, content=data)
    before_stat = path.stat()
    project = tmp_path / "project"
    config = CatalogConfig(project_root=project, catalog_dir=project / ".source_catalog",
                           roots=(RootSpec("company_raw", project / "companies", "company_raw"),))
    store = CatalogStore(config.database_path)
    report = scan_catalog(config, store)
    assert report.errors == 0
    row = store.fetchone("SELECT document_id,primary_source_id FROM documents WHERE title=?",
                         (Path(filename).stem,))
    document_id, source_id = row["document_id"], row["primary_source_id"]
    # Seed the real pre-upgrade classification; identity and bytes remain pinned.
    with store.transaction() as connection:
        connection.execute("UPDATE documents SET document_kind='other',source_type='other' WHERE document_id=?",
                           (document_id,))
    count = store.fetchone("SELECT COUNT(*) AS n FROM sources")["n"]
    for _ in range(2):
        report = scan_catalog(config, store)
        assert report.errors == 0
        current = store.fetchone("SELECT primary_source_id,document_kind,source_type FROM documents WHERE document_id=?",
                                 (document_id,))
        assert (current["primary_source_id"], current["document_kind"], current["source_type"]) == (
            source_id, kind, SourceType.PROSPECTUS.value,
        )
        assert store.fetchone("SELECT COUNT(*) AS n FROM sources")["n"] == count
    assert path.read_bytes() == data
    assert path.stat().st_mtime_ns == before_stat.st_mtime_ns
    assert hashlib.sha256(data).hexdigest() == source_id.rsplit(":", 1)[-1]
