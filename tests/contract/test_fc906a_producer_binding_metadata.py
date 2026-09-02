"""FC-906-a RED: registered producers must emit v2-binding-compliant artifacts.

FC-906 preflight proved 0/7718 production artifacts are bindable: producers never
stamped ``schema_version`` (and wrote ``created_at`` in SQLite space format, not
the ISO-8601 the binding gate requires).  These contracts drive the fix by
running each registered producer (normalizer / section_extractor / llm_summarizer)
on a real temp catalog and asserting the produced artifact passes the single
fail-closed gate ``validate_artifact`` (``reusable=True``) AND carries
``schema_version == ARTIFACT_HANDLE_SCHEMA_VERSION`` in its metadata.

The extractive summarizer (``source_catalog_extractive_summary``) is intentionally
out of scope: its generator is not in GENERATOR_REGISTRY and it has 0 production
artifacts (FC-1203 candidate).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from company_wiki.source_catalog import (
    CatalogConfig,
    RootSpec,
    SourceCatalog,
)
from company_wiki.source_catalog.admission import (
    FOCUS_RELATIVE_PREFIX,
    FOCUS_ROOT_ID,
)
from company_wiki.source_catalog.artifact_handle import (
    ARTIFACT_HANDLE_SCHEMA_VERSION,
    validate_artifact,
)
from company_wiki.source_catalog.source_bundle import GENERATOR_REGISTRY

# Far-future stamp so producer-written created_at (real wall-clock) is never future.
_NOW = "2099-12-31T23:59:59Z"

# External-root fixture: annual-report text with chapter headings so it
# normalizes to `completed` AND yields section slices (mda / business_overview).
# Mirrors the proven test_source_catalog_section_extractor ANNUAL fixture.
_SOURCE_TEXT = """\
---
artifact_role: normalized
document_id: urn:test:annual
---

# 某公司2023年年度报告

第一节 释义

本节为释义内容。

第二节 公司简介

公司简介。

第三节 公司业务概要

主营业务概况。

第四节 经营情况讨论与分析

本年度经营情况详述，含主营业务分析。

第五节 重要事项

不重要。

第十一节 财务报告

财务数据。
"""

# Focus-root fixture: a prospectus-named file (high-value kind, LLM-summary eligible).
_PROSPECTUS_TEXT = """\
Acme 招股说明书。本文件包含可核对的招股资料事实，足以生成确定性摘要。
主营业务：制造与销售。主要风险：市场竞争与原材料价格波动。
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


def _focus_catalog(tmp_path: Path) -> SourceCatalog:
    project = tmp_path / "projectf"
    root = tmp_path / "Dropbox" / "Stock"
    focus = root / FOCUS_RELATIVE_PREFIX
    focus.mkdir(parents=True)
    (focus / "Acme招股说明书.txt").write_text(_PROSPECTUS_TEXT, encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec(FOCUS_ROOT_ID, root, "directory", priority=30),),
        )
    )
    catalog.scan()
    catalog.normalize()
    return catalog


def _review_documents(catalog: SourceCatalog) -> None:
    """GP-003: give every document a valid source-bound prompt-injection
    review receipt (the LLM exit gate requires one before the LLM sees a
    document)."""
    from company_wiki.source_catalog.prompt_injection import (
        record_prompt_injection_review,
    )

    rows = catalog.store.fetchall(
        "SELECT d.document_id, s.content_sha256 FROM documents d "
        "JOIN sources s ON s.source_id = d.primary_source_id"
    )
    with catalog.store.transaction() as connection:
        for row in rows:
            record_prompt_injection_review(
                connection,
                str(row["document_id"]),
                status="not_detected",
                reviewer="gp003-test-fixture",
                evidence_sha256=hashlib.sha256(
                    str(row["content_sha256"]).encode()
                ).hexdigest(),
                now="2026-09-02T12:00:00Z",
                source_sha256=str(row["content_sha256"]),
                policy_hash="c" * 64,
            )


def _binding_handle(catalog: SourceCatalog, role: str, allowed_root: Path):
    """Run the produced artifact + its source lineage through the binding gate."""
    row = catalog.store.fetchone(
        "SELECT * FROM artifacts WHERE artifact_role=? ORDER BY artifact_id LIMIT 1",
        (role,),
    )
    assert row is not None, f"no '{role}' artifact was produced"
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


# --- RED (expected to fail: schema_version absent + created_at non-ISO) ---


def test_normalized_artifact_is_v2_bindable(tmp_path: Path):
    catalog = _external_catalog(tmp_path)
    handle, meta = _binding_handle(catalog, "normalized", tmp_path)
    assert meta.get("schema_version") == ARTIFACT_HANDLE_SCHEMA_VERSION
    assert handle.reusable is True, f"normalized artifact not bindable: {handle.reason}"


def test_sections_artifact_is_v2_bindable(tmp_path: Path):
    catalog = _external_catalog(tmp_path)
    doc_id = catalog.store.fetchone("SELECT document_id FROM documents")["document_id"]
    report = catalog.extract_sections(document_id=doc_id)
    assert report.completed == 1, f"sections did not complete: {report!r}"
    handle, meta = _binding_handle(catalog, "sections", tmp_path)
    assert meta.get("schema_version") == ARTIFACT_HANDLE_SCHEMA_VERSION
    assert handle.reusable is True, f"sections artifact not bindable: {handle.reason}"


def test_llm_summary_artifact_is_v2_bindable(tmp_path: Path):
    catalog = _focus_catalog(tmp_path)
    _review_documents(catalog)

    class _Response:
        success = True
        provider = "test"
        model = "test-model"
        usage: dict[str, int] = {}
        content = json.dumps(
            {
                "overview": "招股资料概述",
                "key_facts": ["可核对的招股资料事实。"],
                "topics": ["招股资料"],
                "limitations": [],
            },
            ensure_ascii=False,
        )

    class _Client:
        provider = "test"
        model = "test-model"

        def generate(self, prompt: str, **_kwargs):
            return _Response()

    report = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=_Client,
        max_input_chars=10_000,
        max_output_tokens=500,
    )
    assert report.completed == 1, f"LLM summary did not complete: {report!r}"
    handle, meta = _binding_handle(catalog, "summary", tmp_path)
    assert meta.get("schema_version") == ARTIFACT_HANDLE_SCHEMA_VERSION
    assert handle.reusable is True, f"llm summary artifact not bindable: {handle.reason}"


def test_producer_writes_schema_version_COLUMN(tmp_path: Path):
    """FC-906-d RED: producers must also write the artifacts.schema_version
    COLUMN (not just metadata_json).

    FC-906-a wrote schema_version into artifact metadata_json, but the
    FC-902 production bundle consumer (query_source_bundle) reads the COLUMN —
    which stayed NULL on every row.  With the column NULL, every bundle
    reports artifact_schema_unsupported and valid_handles is empty even for
    REUSABLE artifacts: the real consumption chain (revenue source_preparation)
    could never read a bound artifact.  This contract pins the column write.
    """
    catalog = _external_catalog(tmp_path)
    row = catalog.store.fetchone(
        "SELECT schema_version, source_sha256 FROM artifacts "
        "WHERE artifact_role='normalized' LIMIT 1"
    )
    assert row is not None, "no normalized artifact produced"
    assert row["schema_version"] == ARTIFACT_HANDLE_SCHEMA_VERSION, (
        "artifacts.schema_version column must be stamped by the producer "
        f"(got {row['schema_version']!r}) — the bundle consumer reads this column"
    )
    # And the FC-902 bundle path (query_source_bundle — what the resolve
    # envelope rides on) must yield a valid handle for the produced artifact.
    doc_id = catalog.store.fetchone("SELECT document_id FROM documents")["document_id"]
    bundle = catalog.query_source_bundle(
        document_id=doc_id,
        registry=GENERATOR_REGISTRY,
        allowed_roots=(tmp_path,),
        now=_NOW,
    )
    assert bundle is not None
    handles = (bundle.get("valid_handles") or {})
    assert handles, (
        f"bundle must carry at least one valid handle for a produced artifact, "
        f"got invalid={sorted((bundle.get('invalid') or {}).keys())}"
    )
    # FC-906-d: bundle_for_resolution DEFAULT allowed_roots must include the
    # derived dir (artifacts live there; config.roots alone => every artifact
    # is path_outside_allowed_root and the resolve envelope carries no valid
    # handles in production — exactly the FC-902-tests-green/production-empty
    # gap this FC closes).
    from types import SimpleNamespace

    fake_resolution = SimpleNamespace(
        matches=[SimpleNamespace(document_id=doc_id, content_sha256=None)],
        status=SimpleNamespace(value="reused_equivalent"),
    )
    envelope_bundle = catalog.bundle_for_resolution(fake_resolution)
    assert envelope_bundle is not None
    assert (envelope_bundle.get("valid_handles") or {}), (
        "bundle_for_resolution defaults must include derived_dir; "
        f"got invalid={sorted((envelope_bundle.get('invalid') or {}).keys())}"
    )
