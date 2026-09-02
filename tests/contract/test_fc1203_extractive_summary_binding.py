"""FC-1203 RED: the extractive summarizer must emit v2-bindable artifacts.

The extractive summarizer has a production entry (``SourceCatalog.summarize``
→ CLI ``summarize`` + the ``run`` pipeline), but its artifacts can NEVER pass
``validate_artifact`` (findings 59): the INSERT omits the schema_version
column, the generator ``source_catalog_extractive_summary`` is not in
GENERATOR_REGISTRY, and created_at is written with ``datetime('now')``
(SQLite space format, not the ISO-8601 the binding gate requires).

These contracts drive the fix: run the real summarizer on a real temp
catalog and assert the produced summary artifact is reusable under the
single fail-closed binding gate — the same contract FC-906-a established for
the three registered producers.
"""

from __future__ import annotations

import json
from pathlib import Path

from company_wiki.source_catalog import (
    CatalogConfig,
    RootSpec,
    SourceCatalog,
)
from company_wiki.source_catalog.artifact_handle import (
    ARTIFACT_HANDLE_SCHEMA_VERSION,
    validate_artifact,
)
from company_wiki.source_catalog.source_bundle import GENERATOR_REGISTRY

# Far-future stamp so producer-written created_at (real wall-clock) is never future.
_NOW = "2099-12-31T23:59:59Z"

_SOURCE_TEXT = """\
artifact_role: normalized
document_id: urn:test:annual

# 某公司2023年年度报告

第一节 释义

本节为释义内容。

第二节 公司简介

公司简介。

第三节 公司业务概要

主营业务概况。

第四节 经营情况讨论与分析

本年度经营情况详述，含主营业务分析。
"""


def _external_catalog(tmp_path: Path) -> SourceCatalog:
    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    (source_root / "annual.txt").write_text(_SOURCE_TEXT, encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("external", source_root, "directory"),),
        )
    )
    catalog.scan()
    catalog.normalize()
    return catalog


def _summary_handle(catalog: SourceCatalog, allowed_root: Path):
    """Run the produced summary artifact through the binding gate."""
    row = catalog.store.fetchone(
        "SELECT * FROM artifacts WHERE artifact_role='summary' "
        "AND generator_name='source_catalog_extractive_summary' "
        "ORDER BY artifact_id LIMIT 1",
    )
    assert row is not None, "no extractive summary artifact was produced"
    meta = json.loads(row["metadata_json"] or "{}")
    doc = catalog.store.fetchone(
        "SELECT primary_source_id FROM documents WHERE document_id=?",
        (row["document_id"],),
    )
    src = catalog.store.fetchone(
        "SELECT content_sha256 FROM sources WHERE source_id=?",
        (doc["primary_source_id"],),
    )
    artifact = {
        "artifact_id": row["artifact_id"],
        "document_id": row["document_id"],
        "source_id": row["source_id"],
        "artifact_role": row["artifact_role"],
        "path": row["path"],
        "content_sha256": row["content_sha256"],
        "generator_name": row["generator_name"],
        "generator_version": row["generator_version"],
        "status": row["status"],
        "created_at": row["created_at"],
        "schema_version": row["schema_version"] or meta.get("schema_version", ""),
        "source_sha256": row["source_sha256"] or meta.get("source_sha256", ""),
    }
    source = {
        "document_id": row["document_id"],
        "primary_source_id": doc["primary_source_id"],
        "source_sha256": src["content_sha256"] if src else "",
        "as_of_date": "",
    }
    handle = validate_artifact(
        artifact,
        source=source,
        registry=GENERATOR_REGISTRY,
        allowed_roots=(allowed_root,),
        now=_NOW,
    )
    return handle, meta


def test_extractive_summary_generator_is_registered() -> None:
    assert "source_catalog_extractive_summary" in GENERATOR_REGISTRY, (
        "extractive summarizer must be registered (FC-1203): its artifacts "
        "can never be reusable otherwise"
    )


def test_extractive_summary_artifact_is_v2_bindable(tmp_path: Path) -> None:
    catalog = _external_catalog(tmp_path)
    report = catalog.summarize()
    assert report.completed >= 1, f"summarize did not complete: {report!r}"
    handle, meta = _summary_handle(catalog, tmp_path)
    assert meta.get("schema_version") == ARTIFACT_HANDLE_SCHEMA_VERSION
    assert handle.reusable is True, (
        f"extractive summary artifact not bindable: {handle.reason}"
    )


def test_extractive_summary_writes_schema_version_column(tmp_path: Path) -> None:
    # FC-906-d contract: the bundle consumer reads the COLUMN — metadata-only
    # stamping leaves production bundles empty (the exact gap FC-906-d fixed).
    catalog = _external_catalog(tmp_path)
    catalog.summarize()
    row = catalog.store.fetchone(
        "SELECT schema_version FROM artifacts WHERE artifact_role='summary' "
        "AND generator_name='source_catalog_extractive_summary' LIMIT 1"
    )
    assert row is not None, "no extractive summary artifact produced"
    assert row["schema_version"] == ARTIFACT_HANDLE_SCHEMA_VERSION, (
        "artifacts.schema_version column must be stamped by the summarizer "
        f"(got {row['schema_version']!r})"
    )
