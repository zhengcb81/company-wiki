"""Contracts for phase-15.6 retire-audit reconciliation (catalog-space-remediation Phase 1.2)."""

from __future__ import annotations

from pathlib import Path

from company_wiki.source_catalog.reconcile_retire_state import ReconcileRetireStateService


ANNUAL = """\
第一节 释义

释义：本报告使用的术语与定义说明，包括公司与关联方的界定，以及财务指标的计量口径说明。

第三节 公司业务概要

主营业务：公司主要从事半导体设备的研发、生产与销售，产品覆盖刻蚀、薄膜沉积、清洗等关键工艺环节，下游客户包括晶圆制造、封装测试等领域的头部厂商。

第四节 经营情况讨论与分析

经营情况：报告期内公司营业收入稳步增长，主要得益于先进制程设备出货量提升与国产替代进程加速，毛利率保持稳定，研发投入持续加大。
"""


def _catalog_with_audit(tmp_path: Path):
    import company_wiki.source_catalog as module

    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    (source_root / "a.txt").write_text("short stub", encoding="utf-8")
    (source_root / "b.txt").write_text(ANNUAL, encoding="utf-8")
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("external", source_root, "directory"),),
        )
    )
    catalog.scan()
    with catalog.store.transaction() as conn:
        for row in catalog.store.fetchall("SELECT document_id FROM documents"):
            conn.execute(
                """INSERT INTO document_retire_audit(audit_id,document_id,reason,created_by,created_at)
                   VALUES(?,?,?,?,datetime('now'))""",
                (
                    f"test-{row['document_id']}",
                    row["document_id"],
                    "test audit",
                    "test",
                ),
            )
    return catalog


def test_reconcile_dry_run_classifies(tmp_path):
    catalog = _catalog_with_audit(tmp_path)
    report = ReconcileRetireStateService(catalog.config).reconcile()
    assert report.dry_run is True
    # a.txt is a <200B stub; b.txt (ANNUAL body) is a non-stub active candidate.
    assert report.stub_physically_deleted == 1
    assert report.retire_candidates == 1
    assert report.mismatch_remaining == 2
    assert report.receipt_path is None


def test_reconcile_apply_retires_and_deletes_stub(tmp_path):
    catalog = _catalog_with_audit(tmp_path)
    report = ReconcileRetireStateService(catalog.config).reconcile(apply=True)
    assert report.dry_run is False
    assert report.stub_physically_deleted == 1
    assert report.retire_candidates == 1
    assert report.mismatch_remaining == 0  # audit vs status reconciled
    assert report.receipt_path is not None
    assert Path(report.receipt_path).exists()

    remaining = catalog.store.fetchall(
        "SELECT d.document_id, d.source_status FROM documents d "
        "JOIN document_retire_audit a ON a.document_id=d.document_id"
    )
    # Exactly one distinct document survives (b.txt, retired); the stub was
    # physically deleted. retire_document adds a second audit row, so the join
    # may list the surviving document twice.
    distinct = {row["document_id"] for row in remaining}
    assert len(distinct) == 1
    assert all(row["source_status"] == "retired" for row in remaining)

    # The stub source file is gone.
    assert not (tmp_path / "sources" / "a.txt").exists()

    # Receipt file: summary line + one line per affected document.
    lines = Path(report.receipt_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3  # summary + stub + retired document


def test_reconcile_apply_idempotent(tmp_path):
    catalog = _catalog_with_audit(tmp_path)
    svc = ReconcileRetireStateService(catalog.config)
    svc.reconcile(apply=True)
    report2 = svc.reconcile(apply=True)
    # Nothing left to reconcile: stub already deleted, remaining doc retired.
    assert report2.retire_candidates == 0
    assert report2.stub_physically_deleted == 0
    assert report2.mismatch_remaining == 0
