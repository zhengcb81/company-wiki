"""Contracts for the read-only catalog size report (catalog-space-remediation Phase 4)."""

from __future__ import annotations

from pathlib import Path

from company_wiki.source_catalog.catalog_size_report import catalog_size_report


ANNUAL = """\
第一节 释义

释义：本报告使用的术语与定义说明，包括公司与关联方的界定，以及财务指标的计量口径说明。

第三节 公司业务概要

主营业务：公司主要从事半导体设备的研发、生产与销售，产品覆盖刻蚀、薄膜沉积、清洗等关键工艺环节。

第四节 经营情况讨论与分析

经营情况：报告期内公司营业收入稳步增长，主要得益于先进制程设备出货量提升与国产替代进程加速。
"""


def _catalog(tmp_path: Path):
    import company_wiki.source_catalog as module

    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    (source_root / "a.txt").write_text(ANNUAL, encoding="utf-8")
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("external", source_root, "directory"),),
        )
    )
    catalog.scan()
    return catalog


def test_size_report_fields_are_consistent(tmp_path):
    catalog = _catalog(tmp_path)
    report = catalog_size_report(catalog.config.database_path)
    assert report.database_bytes > 0
    assert report.page_count > 0
    assert report.freelist_count >= 0
    assert report.documents_total == 1
    assert report.documents_retired == 0
    assert report.evidence_spans_total == 0  # not normalized
    assert report.disk_free_bytes > 0
    assert isinstance(report.warnings, tuple)


def test_size_report_reflects_retired_and_spans(tmp_path):
    catalog = _catalog(tmp_path)
    catalog.normalize()
    from company_wiki.source_catalog.store import retire_document

    doc = catalog.store.fetchone("SELECT document_id FROM documents")
    retire_document(
        catalog.store,
        document_id=doc["document_id"],
        reason="test",
        created_by="test",
    )
    report = catalog_size_report(catalog.config.database_path)
    assert report.documents_retired == 1
    assert report.evidence_spans_total > 0
