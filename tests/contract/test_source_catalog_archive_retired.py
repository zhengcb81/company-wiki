"""Contracts for retired-evidence archiving (catalog-space-remediation Phase 2.1)."""

from __future__ import annotations

import gzip
from pathlib import Path

from company_wiki.source_catalog.archive_retired_evidence import (
    archive_retired_evidence,
)
from company_wiki.source_catalog.store import retire_document


ANNUAL = """\
第一节 释义

释义：本报告使用的术语与定义说明，包括公司与关联方的界定，以及财务指标的计量口径说明。

第三节 公司业务概要

主营业务：公司主要从事半导体设备的研发、生产与销售，产品覆盖刻蚀、薄膜沉积、清洗等关键工艺环节。

第四节 经营情况讨论与分析

经营情况：报告期内公司营业收入稳步增长，主要得益于先进制程设备出货量提升与国产替代进程加速。
"""


def _catalog_with_retired_doc(tmp_path: Path):
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
    catalog.normalize()
    doc = catalog.store.fetchone("SELECT document_id FROM documents")
    retire_document(
        catalog.store,
        document_id=doc["document_id"],
        reason="test",
        created_by="test",
    )
    return catalog


def test_archive_exports_retired_evidence_with_row_reconciliation(tmp_path):
    catalog = _catalog_with_retired_doc(tmp_path)
    manifests = tmp_path / "manifests"
    report = archive_retired_evidence(catalog.config.database_path, manifests)

    assert report.ok
    assert report.rows_written == report.rows_in_catalog
    assert report.rows_written > 0

    path = Path(report.archive_path)
    assert path.exists()
    assert path.name == "retired-evidence.jsonl.gz"
    assert "archive" in str(path)

    with gzip.open(path, "rt", encoding="utf-8") as fh:
        lines = sum(1 for _ in fh)
    assert lines == report.rows_written

    # First line carries the document/source/locator contract fields.
    import json

    with gzip.open(path, "rt", encoding="utf-8") as fh:
        first = json.loads(fh.readline())
    assert first["document_id"] == catalog.store.fetchone(
        "SELECT document_id FROM documents"
    )["document_id"]
    for key in (
        "source_id",
        "locator",
        "page_number",
        "paragraph_index",
        "span_json",
        "parser_name",
        "parser_version",
        "parse_status",
    ):
        assert key in first


def test_archive_empty_when_no_retired_documents(tmp_path):
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
    report = archive_retired_evidence(catalog.config.database_path, tmp_path / "manifests")
    assert report.ok
    assert report.rows_written == 0
