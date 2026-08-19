"""ZR-505 acceptance tests: typed table artifact — table fidelity golden.

  C1  table locator stream: every cell span carries (page, table_index,
      row_index, column_index) in row-major order; paragraphs and cells
      coexist on the page in document order.
  C2  structured value fidelity: str/int/float/bool/null cells keep their
      raw type; the text `value` serializes correctly; rows x cols spans
      cover the whole rectangle.
  C3  rendering: the normalized body renders `- Table cell [r, c]: value`
      rows in row-major order after the page's paragraph spans.
  C4  validation rejection: non-rectangular data, rows != len(data),
      non-JSON-scalar cells, and inexact table field sets raise
      PageAwarePDFAdapterError.
  C5  multi-table / cross-page: table_index resets per page; the
      golden-corpus broker samples are anchored read-only (>= 7).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.parser_adapters.pdf_page_aware import (  # noqa: E402
    PageAwarePDFAdapterError,
    adapt_pdf_pages,
)
from company_wiki.source_catalog.normalizer import (  # noqa: E402
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


def _page(n: int, text: str = "", tables: tuple[dict, ...] = ()) -> dict:
    return {
        "page_number": n,
        "text": text,
        "tables": tables,
        "quality_score": 0.9,
        "ocr_used": False,
        "ocr_confidence": None,
        "layout_ambiguous": False,
        "encoding_repaired": False,
        "error": None,
    }


def _table(rows: list[list], *, markdown: str = "|m|") -> dict:
    cols = len(rows[0]) if rows else 0
    return {"markdown": markdown, "rows": len(rows), "cols": cols, "data": rows}


# ---------------------------------------------------------------------------
# C1 — table locator stream
# ---------------------------------------------------------------------------


def test_c1_cell_locators_are_row_major_and_coexist_with_paragraphs():
    result = adapt_pdf_pages(
        manifest=_manifest(),
        pages=[
            _page(1, "第一页正文"),
            _page(2, "经营数据表", tables=(_table([["产量", 100], [True, None]]),)),
        ],
        parser_version="1.0.0",
    )
    locators = [
        (r.coordinates.page_number, r.coordinates.table_index,
         r.coordinates.row_index, r.coordinates.column_index)
        for r in result.parser_results
    ]
    assert locators == [
        (1, None, None, None),
        (2, None, None, None),
        (2, 0, 0, 0),
        (2, 0, 0, 1),
        (2, 0, 1, 0),
        (2, 0, 1, 1),
    ]


def test_c1_cell_text_matches_paragraph_spans_on_same_page():
    result = adapt_pdf_pages(
        manifest=_manifest(),
        pages=[_page(1, "标题", tables=(_table([["a", "b"]]),))],
        parser_version="1.0.0",
    )
    texts = [r.raw_text for r in result.parser_results]
    assert texts == ["标题", "a", "b"]


# ---------------------------------------------------------------------------
# C2 — structured value fidelity
# ---------------------------------------------------------------------------


def test_c2_cell_types_are_preserved_and_text_serialized():
    result = adapt_pdf_pages(
        manifest=_manifest(),
        pages=[_page(1, tables=(_table([["文本", 100, 2.5, True, None]]),))],
        parser_version="1.0.0",
    )
    cells = [r for r in result.parser_results if r.coordinates.table_index is not None]
    assert len(cells) == 5
    raw = [r.structured_value["raw_value"] for r in cells]
    assert raw == ["文本", 100, 2.5, True, None]
    text = [r.structured_value["value"] for r in cells]
    assert text == ["文本", "100", "2.5", "true", None]
    kinds = [r.structured_value["kind"] for r in cells]
    assert kinds == ["table_cell"] * 5


def test_c2_full_rectangle_covered():
    result = adapt_pdf_pages(
        manifest=_manifest(),
        pages=[_page(1, tables=(_table([["a", "b"], ["c", "d"]]),))],
        parser_version="1.0.0",
    )
    cells = [r for r in result.parser_results if r.coordinates.table_index is not None]
    assert len(cells) == 4
    assert {(r.coordinates.row_index, r.coordinates.column_index) for r in cells} == {
        (0, 0), (0, 1), (1, 0), (1, 1),
    }


# ---------------------------------------------------------------------------
# C3 — rendering
# ---------------------------------------------------------------------------


def test_c3_rendered_body_has_row_major_table_cells_after_paragraphs():
    result = adapt_pdf_pages(
        manifest=_manifest(),
        pages=[_page(1, "经营数据表", tables=(_table([["产量", 100], [True, None]]),))],
        parser_version="1.0.0",
    )
    body = _render_page_aware_markdown(result)
    assert body.index("经营数据表") < body.index("Table cell [0, 0]")
    assert body.index("Table cell [0, 0]") < body.index("Table cell [0, 1]")
    assert body.index("Table cell [0, 1]") < body.index("Table cell [1, 0]")
    assert body.index("Table cell [1, 0]") < body.index("Table cell [1, 1]")
    assert "Table cell [0, 0]: 产量" in body
    assert "Table cell [1, 1]: " in body  # None renders as empty


# ---------------------------------------------------------------------------
# C4 — validation rejection
# ---------------------------------------------------------------------------


def test_c4_non_rectangular_data_rejected():
    with pytest.raises(PageAwarePDFAdapterError):
        adapt_pdf_pages(
            manifest=_manifest(),
            pages=[_page(1, tables=({"markdown": "m", "rows": 2, "cols": 2,
                                     "data": [["a"]]},))],
            parser_version="1.0.0",
        )


def test_c4_rows_mismatch_rejected():
    with pytest.raises(PageAwarePDFAdapterError):
        adapt_pdf_pages(
            manifest=_manifest(),
            pages=[_page(1, tables=({"markdown": "m", "rows": 3, "cols": 1,
                                     "data": [["a"], ["b"]]},))],
            parser_version="1.0.0",
        )


def test_c4_non_scalar_cell_rejected():
    with pytest.raises(PageAwarePDFAdapterError):
        adapt_pdf_pages(
            manifest=_manifest(),
            pages=[_page(1, tables=({"markdown": "m", "rows": 1, "cols": 1,
                                     "data": [[{"nested": True}]]},))],
            parser_version="1.0.0",
        )


def test_c4_inexact_table_fields_rejected():
    with pytest.raises(PageAwarePDFAdapterError):
        adapt_pdf_pages(
            manifest=_manifest(),
            pages=[_page(1, tables=({"markdown": "m", "rows": 1, "cols": 1},))],
            parser_version="1.0.0",
        )


# ---------------------------------------------------------------------------
# C5 — multi-table / cross-page + golden anchor
# ---------------------------------------------------------------------------


def test_c5_table_index_resets_per_page():
    result = adapt_pdf_pages(
        manifest=_manifest(),
        pages=[
            _page(1, tables=(_table([["a"]]), _table([["b"]]))),
            _page(2, tables=(_table([["c"]]),)),
        ],
        parser_version="1.0.0",
    )
    table_indices = [
        r.coordinates.table_index
        for r in result.parser_results
        if r.coordinates.table_index is not None
    ]
    assert table_indices == [0, 1, 0]


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
    assert len(broker) >= 7
    changjiang = next(
        item for item in broker if item["sample_id"] == "zijin_broker_20240304_changjiang"
    )
    assert changjiang["sha256"] == _CHANGJIANG_SHA256


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
