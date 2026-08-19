"""ZR-506 acceptance tests: section / chunk / tag / fact assertion.

  C1  detect_sections recognizes chapter-heading lines (CJK ordinal,
      "第X章/第X节", numeric "1.1") with zero hardcoded names; body
      noise lines (page headers, locator comments) are excluded.
  C2  chunk_spans groups line ranges between section headers; implicit
      single chunk without sections; bounds clamped.
  C3  extract_facts parses "指标名：数字+单位" (negative/percent/unit-less);
      no match -> [] (never fabricated).
  C4  normalize wiring: frontmatter `document_structure` key coexists with
      ZR-501..505 fields.
  C5  zero hardcoding: no entity/metric names in the product module.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.normalizer import (  # noqa: E402
    _Normalized,
    _frontmatter,
)
from company_wiki.source_catalog.section_chunk_fact import (  # noqa: E402
    chunk_spans,
    detect_sections,
    extract_facts,
)

BODY = """## Page 1

<!-- locator: loc:v1/page:1/paragraph:0/chars:0-6 -->

一、经营概况

<!-- locator: loc:v1/page:1/paragraph:1/chars:8-32 -->

紫金矿业集团股份有限公司2025年经营情况良好。

<!-- locator: loc:v1/page:1/paragraph:2/chars:34-45 -->

营业收入：3036亿元

## Page 2

<!-- locator: loc:v1/page:2/paragraph:0/chars:47-53 -->

二、成本分析

<!-- locator: loc:v1/page:2/paragraph:1/chars:55-70 -->

单位成本下降至每吨2.1万元，同比下降12.5%。
"""


# ---------------------------------------------------------------------------
# C1 — section detection
# ---------------------------------------------------------------------------


def test_c1_detects_cjk_ordinal_and_chapter_headings():
    sections = detect_sections(BODY)
    assert [item["title"] for item in sections] == ["一、经营概况", "二、成本分析"]
    assert [item["index"] for item in sections] == [0, 1]
    # line offsets are content-line offsets (noise lines excluded)
    assert sections[0]["line_offset"] == 0
    assert sections[1]["line_offset"] > sections[0]["line_offset"]


def test_c1_detects_chapter_and_numeric_headings():
    text = "第一章 总则\n\n第一条 适用范围\n\n1.1 背景\n\n正文"
    sections = detect_sections(text)
    titles = [item["title"] for item in sections]
    assert "第一章 总则" in titles
    assert "1.1 背景" in titles


def test_c1_no_false_positive_mid_sentence_ordinal():
    text = "所述一、二点均不构成承诺。\n\n以上为总结。"
    assert detect_sections(text) == []


def test_c1_no_sections_for_plain_text():
    assert detect_sections("纯文本没有章节标题\n第二行") == []


# ---------------------------------------------------------------------------
# C2 — chunk grouping
# ---------------------------------------------------------------------------


def test_c2_chunks_between_sections():
    sections = detect_sections(BODY)
    content_lines = [line for line in BODY.splitlines() if line.strip()]
    chunks = chunk_spans(len(content_lines), sections)
    assert len(chunks) == 3  # [0, s1), [s1, s2), [s2, end)
    assert chunks[0] == [0, sections[0]["line_offset"]]
    assert chunks[1][0] == sections[0]["line_offset"]
    assert chunks[2][0] == sections[1]["line_offset"]


def test_c2_implicit_single_chunk_without_sections():
    chunks = chunk_spans(5, [])
    assert chunks == [[0, 5]]


def test_c2_bounds_clamped():
    chunks = chunk_spans(3, [{"line_offset": 7, "title": "x", "index": 0}])
    assert chunks == [[0, 3]]


# ---------------------------------------------------------------------------
# C3 — fact extraction
# ---------------------------------------------------------------------------


def test_c3_fact_with_unit():
    facts = extract_facts("营业收入：3036亿元")
    assert facts == [{"metric": "营业收入", "value": 3036, "unit": "亿元"}]


def test_c3_fact_negative_percent_and_unitless():
    assert extract_facts("亏损：-2.1亿元") == [
        {"metric": "亏损", "value": -2.1, "unit": "亿元"}
    ]
    assert extract_facts("同比增长：12.5%") == [
        {"metric": "同比增长", "value": 12.5, "unit": "%"}
    ]
    assert extract_facts("数值：42") == [{"metric": "数值", "value": 42, "unit": None}]


def test_c3_facts_collected_in_order_and_no_match_is_empty():
    facts = extract_facts("营业收入：3036亿元\n\n单位成本：2.1万元")
    assert [item["metric"] for item in facts] == ["营业收入", "单位成本"]
    assert extract_facts("没有数字模式的普通文本") == []


def test_c3_int_vs_float_preserved():
    assert extract_facts("指标：100")[0]["value"] == 100
    assert isinstance(extract_facts("指标：100")[0]["value"], int)
    assert extract_facts("指标：10.50")[0]["value"] == 10.5
    assert isinstance(extract_facts("指标：10.50")[0]["value"], float)


# ---------------------------------------------------------------------------
# C4 — normalize wiring
# ---------------------------------------------------------------------------


def _doc() -> dict:
    return {
        "document_id": "doc-1",
        "primary_source_id": "src-1",
        "content_sha256": "a" * 64,
        "title": "t",
        "document_kind": "broker_research",
        "published_date": "2026-03-01",
        "metadata_json": {"acquisition": {"publisher": "长江证券"}},
    }


def _norm() -> _Normalized:
    return _Normalized(
        body=BODY,
        parser_results=(),
        parser_name="pdf_page_aware_core",
        parser_version="1.0.0",
        status="completed",
        quality_flags=(),
        error=None,
        page_count=2,
        first_page_text="一、经营概况",
    )


def test_c4_frontmatter_has_document_structure():
    import yaml

    payload = yaml.safe_load(_frontmatter(_doc(), _norm()).split("---\n", 2)[1])
    structure = payload["document_structure"]
    assert [s["title"] for s in structure["sections"]] == ["一、经营概况", "二、成本分析"]
    assert structure["chunk_count"] == 3
    metrics = [f["metric"] for f in structure["facts"]]
    assert "营业收入" in metrics
    assert any(f["metric"] == "营业收入" and f["value"] == 3036 and f["unit"] == "亿元"
               for f in structure["facts"])


def test_c4_zr501_505_fields_coexist():
    import yaml

    payload = yaml.safe_load(_frontmatter(_doc(), _norm()).split("---\n", 2)[1])
    assert payload["page_count"] == 2          # ZR-501
    assert "homepage_identity" in payload       # ZR-502
    assert "detected_entities" in payload       # ZR-503
    assert "document_structure" in payload      # ZR-506


# ---------------------------------------------------------------------------
# C5 — zero hardcoding
# ---------------------------------------------------------------------------


def test_c5_no_entity_or_metric_names_in_product_module():
    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "company_wiki"
        / "source_catalog"
        / "section_chunk_fact.py"
    ).read_text(encoding="utf-8")
    for name in ("紫金矿业", "陕西煤业", "营业收入", "单位成本"):
        assert name not in source


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
