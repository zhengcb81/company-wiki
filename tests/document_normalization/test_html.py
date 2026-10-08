"""HTML normalization mechanism tests (hidden, ownership, tables, encoding)."""

from __future__ import annotations

import pytest

from company_wiki.document_normalization import NormalizationLimits
from company_wiki.document_normalization.errors import UnsupportedFormatError
from company_wiki.document_normalization.html_parser import decode_html_bytes

from conftest import html_page, normalize_html


def texts(doc, kind=None):
    return [u.raw_text for u in doc.units if kind is None or u.unit_kind == kind]


class TestExclusionAndVisibility:
    def test_script_style_and_head_never_contribute(self):
        doc = normalize_html(
            html_page(
                "<script>var x = 'ignored';</script>"
                "<style>.a { color: red }</style>"
                "<p>Visible statement</p>"
            )
        )
        assert texts(doc) == ["Visible statement"]

    def test_nav_subtree_excluded(self):
        doc = normalize_html(
            html_page(
                "<nav><p>Navigation label</p></nav><main><p>Body content</p></main>"
            )
        )
        assert "Navigation label" not in texts(doc)
        assert "Body content" in texts(doc)

    def test_hidden_ancestor_excludes_descendants(self):
        doc = normalize_html(
            html_page(
                '<div style="display:none"><p>Hidden by style</p></div>'
                '<div hidden><p>Hidden attribute</p></div>'
                '<div aria-hidden="true"><p>Hidden aria</p></div>'
                '<div class="ix-hidden"><p>Hidden ix class</p></div>'
                "<p>Shown</p>"
            )
        )
        assert texts(doc) == ["Shown"]
        assert doc.metadata["skipped_hidden_count"] >= 4

    def test_inline_xbrl_hidden_fact_excluded_but_visible_fact_kept(self):
        doc = normalize_html(
            html_page(
                "<p>Revenue "
                '<ix:nonFraction name="dei:Visible" contextRef="c">245</ix:nonFraction> '
                '<ix:nonFraction name="dei:Hidden" contextRef="c" '
                'style="display:none">999</ix:nonFraction> '
                "million</p>"
            )
        )
        joined = " ".join(texts(doc))
        assert "245" in joined
        assert "999" not in joined

    def test_hidden_inline_child_does_not_leak_into_owner(self):
        doc = normalize_html(
            html_page(
                "<p>Keep "
                '<span style="visibility:hidden">drop this</span> part</p>'
            )
        )
        assert texts(doc) == ["Keep part"]


class TestOwnershipNoDoubleCount:
    def test_nested_owners_counted_once(self):
        doc = normalize_html(
            html_page(
                "<div><p>Inner paragraph</p>tail of div</div>"
            )
        )
        found = texts(doc)
        assert "Inner paragraph" in found
        # The div owns only its loose text, never the paragraph's text again.
        assert sum("Inner paragraph" in t for t in found) == 1
        assert "tail of div" in " ".join(found)

    def test_same_text_at_two_locations_is_two_units(self):
        doc = normalize_html(
            html_page(
                "<section><p>Identical sentence.</p></section>"
                "<article><p>Identical sentence.</p></article>"
            )
        )
        matches = [u for u in doc.units if u.raw_text == "Identical sentence."]
        assert len(matches) == 2
        assert len({u.unit_id for u in matches}) == 2
        assert len({u.metadata["source_locator"] for u in matches}) == 2

    def test_inline_elements_join_owner_text(self):
        doc = normalize_html(
            html_page("<p>Award of <b>$1.2 billion</b> for <i>cloud</i></p>")
        )
        assert texts(doc) == ["Award of $1.2 billion for cloud"]

    def test_body_loose_text_is_kept(self):
        doc = normalize_html(
            html_page("Stray body text<p>Owned</p>")
        )
        assert "Stray body text" in texts(doc)
        assert "Owned" in texts(doc)


class TestTables:
    def test_financial_table_flagged_with_basis(self):
        doc = normalize_html(
            html_page(
                "<table><tr><th>Year</th><th>Revenue</th></tr>"
                "<tr><td>FY2025</td><td>$245,122</td></tr></table>"
            )
        )
        cells = [u for u in doc.units if u.unit_kind == "html_table_cell"]
        assert len(cells) == 4
        for cell in cells:
            assert cell.metadata["table_class"] == "financial"
            assert cell.metadata["table_class_basis"]
        coordinates = sorted(
            (u.metadata["table_index"], u.metadata["row_index"], u.metadata["column_index"])
            for u in cells
        )
        assert coordinates == [(0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1)]

    def test_business_table_flagged_unknown_and_kept(self):
        doc = normalize_html(
            html_page(
                "<table><tr><th>Datacenter</th><th>Region</th></tr>"
                "<tr><td>Boydton</td><td>Virginia</td></tr></table>"
            )
        )
        cells = [u for u in doc.units if u.unit_kind == "html_table_cell"]
        assert len(cells) == 4  # never dropped, MAIN routes it
        assert all(u.metadata["table_class"] == "unknown" for u in cells)

    def test_two_tables_get_distinct_table_index(self):
        doc = normalize_html(
            html_page(
                "<table><tr><td>a1</td></tr></table>"
                "<p>middle</p>"
                "<table><tr><td>b1</td></tr></table>"
            )
        )
        indexes = {
            u.metadata["table_index"]
            for u in doc.units
            if u.unit_kind == "html_table_cell"
        }
        assert indexes == {0, 1}

    def test_rowspan_table_cells_use_direct_row_index(self):
        doc = normalize_html(
            html_page(
                "<table><tr><td>top</td><td>right</td></tr>"
                "<tr><td>bottom</td></tr></table>"
            )
        )
        cells = {
            (u.metadata["row_index"], u.metadata["column_index"]): u.raw_text
            for u in doc.units
            if u.unit_kind == "html_table_cell"
        }
        assert cells[(0, 0)] == "top"
        assert cells[(0, 1)] == "right"
        assert cells[(1, 0)] == "bottom"


class TestFootnotesAndContext:
    def test_footnote_identity_by_class(self):
        doc = normalize_html(
            html_page(
                "<p>See note 1</p>"
                '<p class="footnote">1. Adjusted EBITDA excludes stock compensation</p>'
            )
        )
        footnotes = [u for u in doc.units if u.unit_kind == "html_footnote"]
        assert len(footnotes) == 1
        assert "Adjusted EBITDA" in footnotes[0].raw_text


class TestEncoding:
    def test_meta_charset_gb18030(self):
        body = "<p>营业收入增长</p>".encode("gb18030")
        head = b'<meta charset="gb18030">'
        data = b"<html><head>" + head + b"</head><body>" + body + b"</body></html>"
        text, encoding, strategy, repaired = decode_html_bytes(data)
        assert encoding == "gb18030"
        assert strategy == "meta_charset"
        assert "营业收入增长" in text
        assert repaired is False

    def test_utf8_bom_strategy(self):
        payload = "<html><body><p>hi</p></body></html>".encode("utf-8")
        data = b"\xef\xbb\xbf" + payload
        _, encoding, strategy, repaired = decode_html_bytes(data)
        assert encoding == "utf-8-sig"
        assert strategy == "bom"
        assert repaired is False

    def test_undeclared_non_utf8_falls_back_and_flags_repair(self):
        from company_wiki.document_normalization import normalize_document
        from conftest import sha256_hex, source_id_for

        data = "<html><body><p>caf\xe9 figures</p></body></html>".encode("latin-1")
        doc = normalize_document(
            data,
            source_id=source_id_for(data),
            source_sha256=sha256_hex(data),
            mime_type="text/html",
            limits=NormalizationLimits(),
        )
        assert doc.metadata["encoding_strategy"] == "fallback_repair"
        assert doc.metadata["encoding_repaired"] is True
        assert any(
            "encoding_repaired" in u.quality_flags for u in doc.units
        )

    def test_empty_bytes_error_not_empty_success(self):
        doc = normalize_html("")
        assert doc.units == ()
        assert "no_visible_text_blocks" in doc.structure.errors
        assert doc.structure.coverage_complete is False

    def test_non_html_bytes_with_html_mime_flagged_not_clean(self):
        doc = normalize_html("PK\x03\x04 not html at all")
        # Whatever text the bytes contain is kept, but the missing html root
        # and honest error list prevent this from reading as a clean parse.
        assert "no_html_root" in doc.structure.errors
        assert doc.structure.coverage_complete is False

    def test_truncated_markup_still_counts_visible_blocks(self):
        doc = normalize_html("<html><body><p>complete</p><p>broken")
        assert "complete" in " ".join(texts(doc))


class TestMimeRouting:
    def test_application_pdf_rejected(self):
        from company_wiki.document_normalization import normalize_document
        from conftest import sha256_hex, source_id_for

        data = b"%PDF-1.7 minimal"
        with pytest.raises(UnsupportedFormatError):
            normalize_document(
                data,
                source_id=source_id_for(data),
                source_sha256=sha256_hex(data),
                mime_type="application/pdf",
                limits=NormalizationLimits(),
            )


class TestCoverageContract:
    def test_line_count_expresses_scan_completeness(self):
        doc = normalize_html(html_page("<p>one</p><p>two</p>"))
        assert doc.structure.line_count == len(doc.units)
        assert doc.structure.page_count == 0
        assert doc.structure.coverage_complete is True

    def test_svg_is_named_gap_not_lost_and_not_an_error(self):
        doc = normalize_html(
            html_page("<p>chart below</p><svg><path d='M0 0'/></svg>")
        )
        svg_assets = [a for a in doc.opaque_assets if a.asset_kind == "svg"]
        assert len(svg_assets) == 1
        assert svg_assets[0].gap_reason == "svg_not_transcribed"
        assert "chart below" in texts(doc)
