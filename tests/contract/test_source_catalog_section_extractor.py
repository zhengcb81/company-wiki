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
    # Explicit sidecar: a bare "directory"-root file defaults to
    # document_kind=broker_research; this fixture IS an annual report and
    # must flow through the annual (第X节) extraction path.
    (source_root / "annual.txt.source.json").write_text(
        _json.dumps({"document_kind": "annual_report"}, ensure_ascii=False),
        encoding="utf-8",
    )
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


# ---------------------------------------------------------------------------
# Broker research report sectioning (BR-11~17 product gap)
# ---------------------------------------------------------------------------


BROKER_REPORT = """\
---
artifact_role: normalized
document_id: urn:test:broker
---

紫金矿业深度报告

一、报告要点

紫金矿业是全球领先的铜金矿企，铜金双主业驱动。

二、投资建议

我们预计2025-2027年公司归母净利415亿元、451亿元、479亿元，
维持"推荐"评级。

三、风险提示

项目进度不及预期，铜金锂等金属价格下跌，地缘政治风险。

四、盈利预测

2025E 2026E 2027E
营业收入 329,675 352,355 368,693

五、财务分析

公司毛利率提升，单位成本下降。
"""


def test_broker_report_extracts_known_keywords():
    """Broker research reports use investment keywords like 报告要点/
    投资建议/风险提示/盈利预测 — these must be recognized and mapped
    to semantic roles even without the 第X节 convention."""
    from company_wiki.source_catalog.section_extractor import (
        extract_broker_sections_from_text,
    )

    slices = extract_broker_sections_from_text(BROKER_REPORT)
    by_role = {s.role: s for s in slices}
    assert "investment_highlights" in by_role, [s.role for s in slices]
    assert "earnings_forecast" in by_role
    assert "risk_warning" in by_role
    assert "financial_forecast" in by_role
    assert by_role["investment_highlights"].title == "报告要点"
    assert by_role["risk_warning"].title == "风险提示"


def test_broker_report_unknown_numbered_sections_not_emitted():
    """Numbered headings whose title does not match any keyword are
    silently skipped and do NOT act as boundaries (unlike annual reports
    where SECTION_RE matches all 第X节 lines — broker regex only matches
    keyword lines, so non-keyword headings are absorbed into the
    preceding keyword section's body)."""
    from company_wiki.source_catalog.section_extractor import (
        extract_broker_sections_from_text,
    )

    slices = extract_broker_sections_from_text(BROKER_REPORT)
    roles = {s.role for s in slices}
    # "五、财务分析" is not a known keyword — not emitted as a role
    assert "financial_analysis" not in roles
    # But since it's not a boundary either, it IS absorbed into
    # the preceding keyword section's body:
    fin = next(s for s in slices if s.role == "financial_forecast")
    assert "财务分析" in fin.body  # non-keyword headings are absorbed


def test_broker_report_contiguous_slices():
    from company_wiki.source_catalog.section_extractor import (
        extract_broker_sections_from_text,
    )

    slices = extract_broker_sections_from_text(BROKER_REPORT)
    for s in slices:
        assert s.char_end > s.char_start
        assert len(s.body) == s.char_end - s.char_start


def test_broker_no_sections_for_prose_report():
    """A broker report that is pure flowing prose with no recognized
    keywords returns zero slices (fail-closed; no fake sections)."""
    from company_wiki.source_catalog.section_extractor import (
        extract_broker_sections_from_text,
    )

    prose = "紫金矿业铜金双主业驱动，ROE稳步提升，估值合理。" * 5
    assert extract_broker_sections_from_text(prose) == []


def test_broker_keyword_investment_rating_variant():
    """投资评级 is a common synonym for 投资建议."""
    from company_wiki.source_catalog.section_extractor import (
        extract_broker_sections_from_text,
    )

    text = "投资评级\n\n维持买入，目标价19.5元。\n\n风险提示\n\n铜价下跌。"
    slices = extract_broker_sections_from_text(text)
    roles = {s.role for s in slices}
    assert "earnings_forecast" in roles
    assert "risk_warning" in roles


def test_broker_skips_cover_page_matches():
    """Broker reports' cover pages carry keyword-like labels (投资评级/
    盈利预测与财务指标 appear on page 1 as cover fields, not sections) —
    matching must start AFTER page 1 when `## Page` markers exist, so the
    cover hit does not produce a section that swallows the whole body."""
    from company_wiki.source_catalog.section_extractor import (
        extract_broker_sections_from_text,
    )

    text = (
        "---\nartifact_role: normalized\n---\n"
        "## Page 1\n\n"
        "投资评级\n\n"
        "盈利预测与财务指标\n\n"
        "## Page 2\n\n"
        "报告正文开始。\n\n"
        "风险提示\n\n"
        "铜价下跌风险。\n"
    )
    slices = extract_broker_sections_from_text(text)
    # Cover-page hits (投资评级/盈利预测) must be excluded; the only
    # section is the post-page-1 风险提示.
    roles = [s.role for s in slices]
    assert roles == ["risk_warning"], roles
    risk = slices[0]
    assert "风险提示" in risk.body
    assert "盈利预测与财务指标" not in risk.body
    # Char offsets must remain body-relative (start after the cover text).
    assert risk.char_start > 0
