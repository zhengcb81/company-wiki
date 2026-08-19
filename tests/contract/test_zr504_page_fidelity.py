"""ZR-504 acceptance tests: page-number fidelity — the normalized Markdown
locator stream must preserve the source PDF's physical page order, reading
order, per-page paragraph indices, and globally contiguous char offsets;
error/empty pages keep their page number without corrupting later pages.

  C1  multi-page locator golden: page order 1..N, per-page paragraph_index
      from 0, char_start/end globally contiguous (page "\n\n" separators
      counted), normalized_text joined in page order.
  C2  reading order: the rendered normalized body emits locators in
      physical page order; page-1 spans feed first-page extraction.
  C3  page_count cross-check: parser page_count == max locator page ==
      frontmatter page_count (ZR-501 contract).
  C4  error/empty page fidelity: failed/empty spans keep their page
      number; later pages and char offsets are unaffected.
  C5  golden-corpus anchor: the seven broker-report samples' frozen hashes
      are referenced read-only; published_date=null current state is
      recorded for the ZR-504/505 rebuild extension.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.parser_adapters.pdf_page_aware import (  # noqa: E402
    PAGE_AWARE_PDF_PARSER_NAME,
    PageAwarePDFAdapterError,
    adapt_pdf_pages,
)
from company_wiki.source_catalog.normalizer import (  # noqa: E402
    _Normalized,
    _frontmatter,
    _render_page_aware_markdown,
)
from company_wiki.source_contract.source_manifest import (  # noqa: E402
    ImmutableStatus,
    SourceManifest,
    SourceType,
)

_CHANGJIANG_SHA256 = (
    "273d450887eff7c079b28f394c4831092fa3abbb81db86f2544cab425c2719d7"
)


def _manifest() -> SourceManifest:
    return SourceManifest(
        schema_version="1.0.0",
        source_id="urn:company-wiki:source:sha256:" + "b" * 64,
        entity_ids=("x",),
        original_path="doc.pdf",
        content_sha256="b" * 64,
        source_type=SourceType.REGULATORY_FILING,
        published_date="2026-03-01",
        retrieved_at="2026-03-01T00:00:00Z",
        collector_name="c",
        collector_version="1.0.0",
        mime_type="application/pdf",
        byte_size=100,
        immutable_status=ImmutableStatus.VERIFIED,
    )


def _page(
    n: int,
    text: str = "",
    *,
    error: str | None = None,
    tables: tuple[dict, ...] = (),
) -> dict:
    return {
        "page_number": n,
        "text": text,
        "tables": tables,
        "quality_score": 0.9,
        "ocr_used": False,
        "ocr_confidence": None,
        "layout_ambiguous": False,
        "encoding_repaired": False,
        "error": error,
    }


# ---------------------------------------------------------------------------
# C1 — multi-page locator golden
# ---------------------------------------------------------------------------


def test_c1_three_page_locator_stream_is_faithful():
    result = adapt_pdf_pages(
        manifest=_manifest(),
        pages=[
            _page(1, "紫金矿业集团股份有限公司2025年年度报告\n\n营业收入：3036亿元"),
            _page(2, "净利润：321亿元\n\n分季度表现如下"),
            _page(3, "附录：主要财务指标"),
        ],
        parser_version="1.0.0",
    )
    assert result.page_count == 3
    spans = [
        (r.coordinates.page_number, r.coordinates.paragraph_index,
         r.coordinates.char_start, r.coordinates.char_end)
        for r in result.parser_results
    ]
    assert spans == [
        (1, 0, 0, 21),
        (1, 1, 23, 34),
        (2, 0, 36, 45),
        (2, 1, 47, 54),
        (3, 0, 56, 65),
    ]
    assert result.normalized_text.startswith("紫金矿业集团股份有限公司2025年年度报告")
    assert "\n\n" in result.normalized_text  # page separator preserved


def test_c1_paragraph_index_resets_per_page():
    result = adapt_pdf_pages(
        manifest=_manifest(),
        pages=[_page(1, "一段\n\n二段"), _page(2, "三段")],
        parser_version="1.0.0",
    )
    indices = [(r.coordinates.page_number, r.coordinates.paragraph_index)
               for r in result.parser_results]
    assert indices == [(1, 0), (1, 1), (2, 0)]


# ---------------------------------------------------------------------------
# C2 — reading order and body rendering
# ---------------------------------------------------------------------------


def test_c2_rendered_body_locators_follow_physical_page_order():
    result = adapt_pdf_pages(
        manifest=_manifest(),
        pages=[_page(1, "第一页"), _page(2, "第二页"), _page(3, "第三页")],
        parser_version="1.0.0",
    )
    body = _render_page_aware_markdown(result)
    first = body.index("loc:v1/page:1/paragraph:0")
    second = body.index("loc:v1/page:2/paragraph:0")
    third = body.index("loc:v1/page:3/paragraph:0")
    assert first < second < third
    assert body.index("第一页") < body.index("第二页") < body.index("第三页")


def test_c2_page_one_spans_feed_first_page_text():
    result = adapt_pdf_pages(
        manifest=_manifest(),
        pages=[_page(1, "首页标题行\n\n首页第二段"), _page(2, "第二页内容")],
        parser_version="1.0.0",
    )
    page_one = [r for r in result.parser_results if r.coordinates.page_number == 1]
    assert page_one
    first_text = "\n".join(r.raw_text or "" for r in page_one)
    assert "首页标题行" in first_text
    assert "第二页内容" not in first_text


# ---------------------------------------------------------------------------
# C3 — page_count cross-check
# ---------------------------------------------------------------------------


def test_c3_page_count_matches_max_locator_page():
    result = adapt_pdf_pages(
        manifest=_manifest(),
        pages=[_page(1, "一"), _page(2, "二"), _page(3, "三")],
        parser_version="1.0.0",
    )
    max_page = max(r.coordinates.page_number for r in result.parser_results)
    assert result.page_count == 3 == max_page
    pages_with_spans = {r.coordinates.page_number for r in result.parser_results}
    assert pages_with_spans == {1, 2, 3}


def test_c3_frontmatter_page_count_matches_parser():
    import yaml

    result = adapt_pdf_pages(
        manifest=_manifest(),
        pages=[_page(1, "一"), _page(2, "二")],
        parser_version="1.0.0",
    )
    normalized = _Normalized(
        body=_render_page_aware_markdown(result),
        parser_results=result.parser_results,
        parser_name=PAGE_AWARE_PDF_PARSER_NAME,
        parser_version="1.0.0",
        status="completed",
        quality_flags=(),
        error=None,
        page_count=result.page_count,
        first_page_text="一",
    )
    document = {
        "document_id": "d1",
        "primary_source_id": "s1",
        "content_sha256": "b" * 64,
        "title": "t",
        "document_kind": "annual_report",
        "published_date": "2026-03-01",
        "metadata_json": {},
    }
    payload = yaml.safe_load(_frontmatter(document, normalized).split("---\n", 2)[1])
    assert payload["page_count"] == 2


# ---------------------------------------------------------------------------
# C4 — error / empty page fidelity
# ---------------------------------------------------------------------------


def test_c4_error_page_keeps_number_and_does_not_corrupt_later_pages():
    result = adapt_pdf_pages(
        manifest=_manifest(),
        pages=[
            _page(1, "第一页正文"),
            _page(2, "", error="renderer crashed"),
            _page(3, "第三页正文"),
        ],
        parser_version="1.0.0",
    )
    spans = [
        (r.coordinates.page_number, r.parse_status.value, tuple(r.quality_flags),
         r.coordinates.char_start, r.coordinates.char_end)
        for r in result.parser_results
    ]
    assert spans == [
        (1, "parsed", (), 0, 5),
        (2, "failed", ("parser_error",), None, None),
        (3, "parsed", (), 7, 12),
    ]


def test_c4_empty_page_keeps_number():
    result = adapt_pdf_pages(
        manifest=_manifest(),
        pages=[_page(1, "一"), _page(2), _page(3, "三")],
        parser_version="1.0.0",
    )
    empty = next(r for r in result.parser_results if r.coordinates.page_number == 2)
    assert empty.parse_status.value == "failed"
    assert tuple(empty.quality_flags) == ("empty_output",)
    after = [r for r in result.parser_results if r.coordinates.page_number == 3]
    assert after and after[0].coordinates.char_end > 0


def test_c4_non_contiguous_page_numbers_are_rejected():
    with pytest.raises(PageAwarePDFAdapterError):
        adapt_pdf_pages(
            manifest=_manifest(),
            pages=[_page(1, "a"), _page(3, "b")],
            parser_version="1.0.0",
        )


# ---------------------------------------------------------------------------
# C5 — golden-corpus anchor (read-only)
# ---------------------------------------------------------------------------


def test_c5_golden_broker_samples_anchored_read_only():
    corpus = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / ".."
            / "revenue-forecast"
            / "assurance"
            / "unified_completion"
            / "corpus"
            / "golden_corpus.json"
        ).read_text(encoding="utf-8")
    )
    broker = [item for item in corpus["samples"] if item["role"] == "broker_research"]
    assert len(broker) >= 7  # the seven broker-report corpus
    changjiang = next(
        item for item in broker if item["sample_id"] == "zijin_broker_20240304_changjiang"
    )
    assert changjiang["sha256"] == _CHANGJIANG_SHA256
    # ZR-504/505 rebuild extension: published_date is currently null in the
    # catalog for the broker reports — recorded, not fabricated.
    assert changjiang.get("published_date") is None


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
