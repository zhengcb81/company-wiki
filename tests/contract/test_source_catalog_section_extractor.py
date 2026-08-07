"""Contracts for section_extractor (core-chapter splitting), Phase 1 pure functions."""

from __future__ import annotations

from company_wiki.source_catalog.section_extractor import (
    SECTION_ARTIFACT_ROLE,
    SectionSlice,
    chapter_page_range,
    extract_sections_from_text,
)


ANNUAL = """\
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

PROSPECTUS = """\
第一章 释义

第二章 概览

第四章 风险因素

第六章 业务与技术

发行人业务与技术详情。

第十一章 管理层讨论与分析

MD&A 内容。
"""


def test_annual_report_extracts_mda_and_business_overview():
    slices = extract_sections_from_text(ANNUAL)
    by_role = {s.role: s for s in slices}
    assert "mda" in by_role
    assert "business_overview" in by_role
    assert by_role["mda"].title == "经营情况讨论与分析"
    assert by_role["mda"].ordinal == "第四节"
    assert by_role["business_overview"].ordinal == "第三节"


def test_management_discussion_keyword_variant():
    # The half-year report heading variant must also map to mda.
    text = "第三节 管理层讨论与分析\n\n内容。\n"
    slices = extract_sections_from_text(text)
    assert len(slices) == 1
    assert slices[0].role == "mda"


def test_prospectus_uses_zhang_heading():
    slices = extract_sections_from_text(PROSPECTUS)
    roles = {s.role for s in slices}
    assert "business_and_technology" in roles  # 第六章 业务与技术
    assert "mda" in roles  # 第十一章 管理层讨论与分析
    bt = next(s for s in slices if s.role == "business_and_technology")
    assert bt.ordinal == "第六章"


def test_non_keyword_sections_not_emitted_but_act_as_boundary():
    slices = extract_sections_from_text(ANNUAL)
    titles = [s.title for s in slices]
    # Headings without a keyword are not emitted as slices...
    assert "释义" not in titles
    assert "公司简介" not in titles
    # ...but they still terminate the previous slice's body.
    mda = next(s for s in slices if s.role == "mda")
    assert "经营情况" in mda.body
    assert "第五节" not in mda.body


def test_strips_frontmatter():
    # The ANNUAL fixture has a frontmatter block; extraction must still work.
    slices = extract_sections_from_text(ANNUAL)
    assert slices


def test_no_sections_returns_empty():
    assert extract_sections_from_text("无章节标题的纯文本。") == []


def test_slice_offsets_are_body_relative_and_contiguous():
    slices = extract_sections_from_text(PROSPECTUS)
    # Each slice body must be non-empty and offsets must be consistent.
    for s in slices:
        assert s.char_end > s.char_start
        assert len(s.body) == s.char_end - s.char_start


def test_artifact_role_constant():
    assert SECTION_ARTIFACT_ROLE == "sections"
    assert isinstance(SectionSlice, type)


def test_extract_sections_writes_artifact_and_is_idempotent(tmp_path):
    import json as _json

    import company_wiki.source_catalog as module

    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    (source_root / "annual.txt").write_text(ANNUAL, encoding="utf-8")
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("external", source_root, "directory"),),
        )
    )
    catalog.scan()
    catalog.normalize()
    doc_id = catalog.store.fetchone("SELECT document_id FROM documents")["document_id"]

    report = catalog.extract_sections(document_id=doc_id)
    assert report.completed == 1

    row = catalog.store.fetchone(
        "SELECT generator_name, status, metadata_json FROM artifacts "
        "WHERE artifact_role='sections'"
    )
    assert row["generator_name"] == "source_catalog_section_extractor"
    assert row["status"] == "completed"
    meta = _json.loads(row["metadata_json"])
    roles = {entry["role"] for entry in meta["sections"]}
    assert "mda" in roles
    assert "business_overview" in roles
    # Phase 5: page/span association fields present; the .txt fixture has no
    # "## Page N" markers, so no page range or span association is expected.
    first = meta["sections"][0]
    assert "page_start" in first and "page_end" in first and "span_ids" in first
    assert first["page_start"] is None
    assert first["span_ids"] == []

    # Idempotent: a second run finds the artifact already present and does nothing.
    report2 = catalog.extract_sections(document_id=doc_id)
    assert report2.completed == 0

    # --force re-runs and rewrites the artifact.
    report3 = catalog.extract_sections(document_id=doc_id, force=True)
    assert report3.completed == 1

    # SectionQueryService reads the artifact back read-only.
    from company_wiki.source_catalog.section_query import SectionQueryService

    queried = SectionQueryService(catalog.config.database_path).list_sections(
        document_id=doc_id
    )
    assert queried.document_id == doc_id
    qroles = {entry.role for entry in queried.sections}
    assert "mda" in qroles
    assert "business_overview" in qroles
    # Phase 5: SectionEntry carries the page/span association fields.
    qfirst = queried.sections[0]
    assert qfirst.page_start is None
    assert qfirst.span_ids == ()


def test_chapter_page_range_maps_char_range_to_pages():
    body = (
        "## Page 1\n\n第一节 释义\n\n"
        "## Page 2\n\n第三节 公司业务概要\n\n"
        "## Page 3\n\n第四节 经营情况讨论与分析\n"
    )
    pos2 = body.find("第三节")
    pos3 = body.find("第四节")
    assert chapter_page_range(body, pos2, pos3) == (2, 3)
    assert chapter_page_range(body, 0, len(body)) == (1, 3)
    # A range strictly inside page 1 stays on page 1.
    pos1 = body.find("第一节")
    assert chapter_page_range(body, pos1, pos1 + 4) == (1, 1)


def test_chapter_page_range_none_without_markers():
    assert chapter_page_range("无页标记的纯文本", 0, 5) is None
