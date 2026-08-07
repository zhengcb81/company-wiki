"""Contracts for retired-evidence pruning (catalog-space-remediation Phase 2.3)."""

from __future__ import annotations

from pathlib import Path

from company_wiki.source_catalog.prune_retired_evidence import (
    prune_retired_evidence,
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


def _retired_catalog(tmp_path: Path):
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


def test_prune_dry_run_reports_span_volume(tmp_path):
    catalog = _retired_catalog(tmp_path)
    archive = tmp_path / "manifests"
    (archive / "archive" / "2026-05-01").mkdir(parents=True)  # > 90 days old
    report = prune_retired_evidence(catalog.config, archive)
    assert report.dry_run is True
    assert report.span_rows > 0
    assert report.retired_documents == 1
    assert report.oldest_archive == "2026-05-01"
    assert report.due is True


def test_prune_apply_deletes_spans_when_due(tmp_path):
    catalog = _retired_catalog(tmp_path)
    archive = tmp_path / "manifests"
    (archive / "archive" / "2026-05-01").mkdir(parents=True)
    before = catalog.store.fetchone(
        "SELECT COUNT(*) FROM evidence_spans"
    )[0]

    report = prune_retired_evidence(
        catalog.config, archive, apply=True, retention_days=0
    )
    assert report.dry_run is False
    assert report.due is True
    assert report.deleted_rows == before
    assert report.receipt_path is not None
    assert Path(report.receipt_path).exists()

    remaining = catalog.store.fetchone("SELECT COUNT(*) FROM evidence_spans")[0]
    assert remaining == 0


def test_prune_apply_within_retention_does_nothing(tmp_path):
    catalog = _retired_catalog(tmp_path)
    archive = tmp_path / "manifests"
    (archive / "archive" / "2026-08-07").mkdir(parents=True)  # today
    report = prune_retired_evidence(catalog.config, archive, apply=True)
    assert report.due is False
    assert report.deleted_rows == 0
    remaining = catalog.store.fetchone("SELECT COUNT(*) FROM evidence_spans")[0]
    assert remaining > 0
