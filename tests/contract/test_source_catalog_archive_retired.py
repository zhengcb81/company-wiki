"""Retired-evidence archiving is retired (G3-CWP-MAINT).

The legacy ``archive_retired_evidence`` entry — CLI shape without ``now``,
explicit ``now``, or no catalog at all — must fail closed with the unified
retirement signal BEFORE opening the catalog or creating any archive
directory: 0 Store, 0 lock, 0 files.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from company_wiki.source_catalog.archive_retired_evidence import (
    archive_retired_evidence,
)
from company_wiki.source_catalog.maintenance_retirement import (
    RetiredMaintenanceError,
)
from company_wiki.source_catalog.store import retire_document
from support.legacy_source_artifact_fixture import legacy_normalize


ANNUAL = """\
第一节 释义

释义：本报告使用的术语与定义说明，包括公司与关联方的界定，以及财务指标的计量口径说明。

第三节 公司业务概要

主营业务：公司主要从事半导体设备的研发、生产与销售，产品覆盖刻蚀、薄膜沉积、清洗等关键工艺环节。

第四节 经营情况讨论与分析

经营情况：报告期内公司营业收入稳步增长，主要得益于先进制程设备出货量提升与国产替代进程加速。
"""

NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _count(db: Path, table: str) -> int:
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as con:
        return int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _tree(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*"))


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
    legacy_normalize(catalog)
    doc = catalog.store.fetchone("SELECT document_id FROM documents")
    retire_document(
        catalog.store,
        document_id=doc["document_id"],
        reason="test",
        created_by="test",
    )
    return catalog


def test_archive_entry_retires_for_cli_shape_and_with_now_with_zero_writes(tmp_path):
    catalog = _catalog_with_retired_doc(tmp_path)
    manifests = tmp_path / "manifests"
    database = catalog.config.database_path
    db_sha = _sha(database)
    spans_before = _count(database, "evidence_spans")
    tree_before = _tree(tmp_path)

    for kwargs in ({}, {"now": NOW}):  # CLI passes no ``now``
        with pytest.raises(RetiredMaintenanceError) as exc:
            archive_retired_evidence(database, manifests, **kwargs)
        assert exc.value.operation == "archive-retired-evidence"
        assert not isinstance(exc.value, TypeError)

    assert not manifests.exists()
    assert _sha(database) == db_sha
    assert _count(database, "evidence_spans") == spans_before
    assert _tree(tmp_path) == tree_before


def test_archive_entry_retires_without_any_catalog(tmp_path):
    missing_db = tmp_path / "missing.sqlite3"
    manifests = tmp_path / "manifests"

    with pytest.raises(RetiredMaintenanceError) as exc:
        archive_retired_evidence(missing_db, manifests, now=NOW)
    assert exc.value.operation == "archive-retired-evidence"

    assert not missing_db.exists()
    assert not manifests.exists()
    assert _tree(tmp_path) == []
