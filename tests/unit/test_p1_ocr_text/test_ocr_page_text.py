"""RED counterexample suite for ``order_page_lines`` (P1-OCR-TEXT card §6).

Every case is written against the frozen ``cwp-ocr-page-text/1`` output contract
so it fails on real assertions (not ImportError) before the geometry-driven
implementation lands.  Cases map 1:1 to card §6 bullets.
"""

from __future__ import annotations

import json
import socket

import synth
from company_wiki.document_normalization.ocr_page_text import (
    P1_PAGE_TEXT_SCHEMA,
    PageOrderLimits,
    order_page_lines,
)

# The card's deferred-line vocabulary (card §5.1 per-line field table).
DEFER_VOCAB = {
    "low_confidence",
    "ambiguous_order",
    "bbox_invalid",
    "limit",
    "column_overflow",
}
# INTERFACES §3 P1 diagnostic codes.
P1_DIAG_CODES = {
    "p1_line_confidence_low",
    "p1_order_ambiguous",
    "p1_bbox_invalid",
    "p1_page_limit",
}


def _codes(result):
    return {item["code"] for item in result["diagnostics"]}


def _by_index(result):
    return {line["line_index"]: line for line in result["lines"]}


# --------------------------------------------------------------------------
# §6.1 two-column page must not be concatenated in return order.
# --------------------------------------------------------------------------


def test_two_column_page_is_column_major_not_return_order():
    result = synth.load_fixture("two_column")

    out = order_page_lines(result)

    assert out["schema_version"] == P1_PAGE_TEXT_SCHEMA
    assert out["page"] == {"width": 800, "height": 1000}
    assert len(out["columns"]) == 2, "two-column page must split into 2 columns"
    # Reading order is column-major: whole left column, then whole right column.
    assert out["text"] == (
        "Alpha left one\nAlpha left two\nAlpha left three\n"
        "Beta right one\nBeta right two"
    )
    # Geometry, not the scrambled return order, decides the order.
    assert out["text"] != "\n".join(line.text for line in result.lines)
    # Left column = input indexes 1,3,4; right column = 0,2.
    columns = {c["column_id"]: c for c in out["columns"]}
    assert columns["col-0"]["x0"] == 50 and columns["col-0"]["x1"] == 300
    assert columns["col-1"]["x0"] == 500 and columns["col-1"]["x1"] == 750
    assert set(columns["col-0"]["line_indexes"]) == {1, 3, 4}
    assert set(columns["col-1"]["line_indexes"]) == {0, 2}


# --------------------------------------------------------------------------
# §6.2 indented single-column paragraph must not split into two columns.
# --------------------------------------------------------------------------


def test_indented_first_line_is_not_split_into_two_columns():
    result = synth.load_fixture("indented_paragraph")

    out = order_page_lines(result)

    assert len(out["columns"]) == 1, "a 2em first-line indent is not a column break"
    assert out["status"] == "ok"
    for line in out["lines"]:
        assert line["column_id"] == "col-0"
    # y0 order (geometry) puts the indented line first.
    assert out["text"] == "Indented first line\nBody second line\nBody third line"


# --------------------------------------------------------------------------
# §6.3 header/footer near page edges must not be inserted mid-paragraph.
# --------------------------------------------------------------------------


def test_header_and_footer_do_not_reorder_body_rows():
    result = synth.load_fixture("header_footer")

    out = order_page_lines(result)

    rows = out["text"].split("\n")
    body = ["Body paragraph one", "Body paragraph two", "Body paragraph three"]
    # The body rows keep their input relative order and stay contiguous.
    assert [r for r in rows if r in body] == body
    # Header sits at the top, footer at the bottom -- never mid-paragraph.
    assert rows[0] == "PAGE HEADER"
    assert rows[-1] == "PAGE FOOTER"
    assert "PAGE HEADER" not in body
    body_end = max(rows.index(b) for b in body)
    assert rows.index("PAGE FOOTER") > body_end


# --------------------------------------------------------------------------
# §6.4 low-confidence (0.42) line sandwiched between two normal lines.
# --------------------------------------------------------------------------


def test_low_confidence_line_is_deferred_and_excluded_from_body():
    result = synth.load_fixture("low_confidence")

    out = order_page_lines(result)

    # Body must not contain the 0.42 line.
    assert out["text"] == "Normal line one\nNormal line two"
    assert "Low confidence line" not in out["text"]
    # It must be reported as deferred, never silently dropped.
    assert out["deferred_line_indexes"] == [1]
    line = _by_index(out)[1]
    assert line["accepted"] is False
    assert line["defer_reasons"] == ["low_confidence"]
    assert line["char_start"] is None and line["char_end"] is None
    assert line["text"] == "Low confidence line", "deferred line keeps verbatim text"
    assert "p1_line_confidence_low" in _codes(out)
    assert out["status"] == "partial"


# --------------------------------------------------------------------------
# §6.5 fully shuffled return order -- geometry decides, stable across runs.
# --------------------------------------------------------------------------


def test_shuffled_return_order_is_resolved_by_geometry_and_is_stable():
    result = synth.load_fixture("shuffled")

    first = order_page_lines(result)
    second = order_page_lines(result)

    # Rows are emitted top-to-bottom by y0 regardless of scrambled input order.
    assert first["text"] == (
        "Zeta row one\nYankee row two\nXray row three\nWhiskey row four"
    )
    assert first["text"] != "\n".join(line.text for line in result.lines)
    # Two runs are byte-identical under canonical JSON.
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


# --------------------------------------------------------------------------
# §6.6 three segments of one visual line merge with contiguous char ranges.
# --------------------------------------------------------------------------


def test_three_segments_of_one_visual_line_merge_with_contiguous_ranges():
    result = synth.load_fixture("three_segment")

    out = order_page_lines(result)

    assert len(out["columns"]) == 1
    assert out["text"] == "SEGLEFTSEGMIDSEGRIGHT"
    lines = [out["lines"][i] for i in (0, 1, 2)]
    assert all(line["accepted"] for line in lines)
    # char ranges are contiguous and non-overlapping.
    assert lines[0]["char_start"] == 0 and lines[0]["char_end"] == 7
    assert lines[1]["char_start"] == 7 and lines[1]["char_end"] == 13
    assert lines[2]["char_start"] == 13 and lines[2]["char_end"] == 21
    assert lines[0]["char_end"] == lines[1]["char_start"]
    assert lines[1]["char_end"] == lines[2]["char_start"]
    for line in lines:
        assert out["text"][line["char_start"] : line["char_end"]] == line["text"]


# --------------------------------------------------------------------------
# §6.7 two lines with crossing x intervals both defer.
# --------------------------------------------------------------------------


def test_crossing_x_intervals_defer_both_lines():
    result = synth.load_fixture("crossing")

    out = order_page_lines(result)

    lines = _by_index(out)
    assert lines[0]["defer_reasons"] == ["ambiguous_order"]
    assert lines[1]["defer_reasons"] == ["ambiguous_order"]
    assert lines[0]["accepted"] is False and lines[1]["accepted"] is False
    # The independent normal line is unaffected and still accepted.
    assert lines[2]["accepted"] is True
    assert out["text"] == "Normal anchor"
    assert sorted(out["deferred_line_indexes"]) == [0, 1]
    assert "p1_order_ambiguous" in _codes(out)
    assert out["status"] == "partial"


# --------------------------------------------------------------------------
# §6.8 empty page -> unavailable + reason, no exception.
# --------------------------------------------------------------------------


def test_empty_page_is_unavailable_with_reason_and_no_exception():
    result = synth.load_fixture("empty_page")

    out = order_page_lines(result)

    assert out["status"] == "unavailable"
    assert out["reason"] == "p1_page_empty"
    assert out["text"] == ""
    assert out["lines"] == [] and out["columns"] == []
    assert out["deferred_line_indexes"] == []
    assert out["work_used"] == {"lines": 0, "chars": 0}


# --------------------------------------------------------------------------
# §6.9 line / char limits -> partial + limit, no in-line truncation.
# --------------------------------------------------------------------------


def test_max_lines_limit_defers_from_that_line_onward_without_truncation():
    result = synth.load_fixture("over_limit")
    limits = PageOrderLimits(max_lines=2)

    out = order_page_lines(result, limits=limits)

    assert out["status"] == "partial"
    assert out["text"] == "LINEZERO\nLINEONE"
    assert sorted(out["deferred_line_indexes"]) == [2, 3]
    lines = _by_index(out)
    assert lines[2]["defer_reasons"] == ["limit"]
    assert lines[3]["defer_reasons"] == ["limit"]
    # No in-line truncation: deferred lines keep their verbatim text.
    assert lines[2]["text"] == "LINETWO"
    assert lines[3]["text"] == "LINETHREE"
    assert "p1_page_limit" in _codes(out)


def test_max_chars_limit_counts_cumulative_chars_without_truncation():
    result = synth.load_fixture("over_limit")
    limits = PageOrderLimits(max_chars=9)

    out = order_page_lines(result, limits=limits)

    assert out["status"] == "partial"
    assert out["text"] == "LINEZERO"
    assert sorted(out["deferred_line_indexes"]) == [1, 2, 3]
    assert _by_index(out)[1]["defer_reasons"] == ["limit"]
    # Cumulative count includes the newline separators already emitted.
    assert out["work_used"]["chars"] == len(out["text"])


# --------------------------------------------------------------------------
# §6.10 page bounds consistent -> accepted; bounds violated -> bbox_invalid.
# --------------------------------------------------------------------------


def test_box_touching_page_boundary_is_accepted_not_bbox_invalid():
    result = synth.load_fixture("boundary")

    out = order_page_lines(result)

    assert out["status"] == "ok"
    assert out["lines"][0]["accepted"] is True
    assert out["lines"][0]["defer_reasons"] == []
    assert "p1_bbox_invalid" not in _codes(out)


def test_box_exceeding_page_bounds_defers_as_bbox_invalid():
    # ImageOCRResult rejects out-of-bounds boxes at construction, so the
    # defensive guard is exercised by shrinking the page after construction.
    result = synth.load_fixture("boundary")
    object.__setattr__(result, "width", 100)

    out = order_page_lines(result)

    assert out["lines"][0]["defer_reasons"] == ["bbox_invalid"]
    assert out["lines"][0]["accepted"] is False
    assert "p1_bbox_invalid" in _codes(out)


def test_non_finite_font_size_ratio_defers_as_bbox_invalid():
    result = synth.load_fixture("over_limit")

    out = order_page_lines(result, font_size=0.0)

    assert all(
        line["defer_reasons"] == ["bbox_invalid"] for line in out["lines"]
    )
    assert all(line["accepted"] is False for line in out["lines"])
    assert "p1_bbox_invalid" in _codes(out)


# --------------------------------------------------------------------------
# §6.11 font_size None vs explicit yields the same ordering.
# --------------------------------------------------------------------------


def test_font_size_none_matches_explicit_median_ordering():
    result = synth.load_fixture("two_column")
    median_height = 20.0  # every box is 20 units tall in this fixture.

    implicit = order_page_lines(result, font_size=None)
    explicit = order_page_lines(result, font_size=median_height)

    assert implicit["text"] == (
        "Alpha left one\nAlpha left two\nAlpha left three\n"
        "Beta right one\nBeta right two"
    )
    assert implicit["text"] == explicit["text"]
    assert implicit["columns"] == explicit["columns"]
    assert implicit["status"] == explicit["status"] == "ok"
    assert json.dumps(implicit, sort_keys=True) == json.dumps(explicit, sort_keys=True)


# --------------------------------------------------------------------------
# §5.1 rule 1: column overflow -> partial + column_overflow on unassigned lines
# (card §6 has no dedicated bullet for this rule).
# --------------------------------------------------------------------------


def test_column_overflow_defers_unassigned_lines_and_marks_partial():
    result = synth.load_fixture("three_column")
    limits = PageOrderLimits(max_columns=2)

    out = order_page_lines(result, limits=limits)

    assert out["status"] == "partial"
    assert len(out["columns"]) == 2, "only the first max_columns columns survive"
    # The third (right-most) column is unassigned and deferred.
    overflow = [line for line in out["lines"] if line["column_id"] is None]
    assert [line["line_index"] for line in overflow] == [2]
    assert overflow[0]["defer_reasons"] == ["column_overflow"]
    assert overflow[0]["accepted"] is False
    assert sorted(out["deferred_line_indexes"]) == [2]
    assert out["text"] == "ColA one\nColB one"


# --------------------------------------------------------------------------
# §6.14 input immutability -- ImageOCRResult is unchanged field by field.
# --------------------------------------------------------------------------


def test_input_result_is_not_mutated():
    result = synth.load_fixture("two_column")
    before = synth.snapshot(result)

    out = order_page_lines(result)

    assert out["text"] == (
        "Alpha left one\nAlpha left two\nAlpha left three\n"
        "Beta right one\nBeta right two"
    )
    assert synth.snapshot(result) == before


# --------------------------------------------------------------------------
# §7.3 dedicated determinism case -- canonical JSON bytes are identical.
# --------------------------------------------------------------------------


def test_canonical_json_bytes_are_identical_across_two_calls():
    result = synth.load_fixture("shuffled")

    first = order_page_lines(result)
    second = order_page_lines(result)

    assert first["text"] == (
        "Zeta row one\nYankee row two\nXray row three\nWhiskey row four"
    )
    dumped = json.dumps(
        first, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    assert dumped == json.dumps(
        second, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    assert dumped.encode("utf-8")


# --------------------------------------------------------------------------
# §8 resource boundary -- zero socket use, zero model/network calls.
# --------------------------------------------------------------------------


def test_no_network_or_socket_use(monkeypatch):
    result = synth.load_fixture("two_column")

    def _blocked(*args, **kwargs):  # pragma: no cover - defensive
        raise AssertionError("network use is forbidden in P1-OCR-TEXT")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)

    out = order_page_lines(result)
    assert out["status"] == "ok"
    assert out["text"] == (
        "Alpha left one\nAlpha left two\nAlpha left three\n"
        "Beta right one\nBeta right two"
    )


# --------------------------------------------------------------------------
# §5.1 schema sanity -- defer vocabulary and work_used accounting.
# --------------------------------------------------------------------------


def test_defer_reasons_stay_within_the_frozen_vocabulary():
    result = synth.load_fixture("low_confidence")

    out = order_page_lines(result)

    assert _by_index(out)[1]["defer_reasons"] == ["low_confidence"]
    for line in out["lines"]:
        assert set(line["defer_reasons"]) <= DEFER_VOCAB


def test_work_used_reports_accepted_lines_and_body_chars():
    result = synth.load_fixture("low_confidence")

    out = order_page_lines(result)

    accepted = [line for line in out["lines"] if line["accepted"]]
    assert out["work_used"] == {
        "lines": len(accepted),
        "chars": len(out["text"]),
    }
    assert out["work_used"] == {"lines": 2, "chars": len(out["text"])}


def test_every_input_line_is_present_in_the_output_lines():
    result = synth.load_fixture("two_column")

    out = order_page_lines(result)

    assert [line["line_index"] for line in out["lines"]] == list(
        range(len(result.lines))
    )


# --------------------------------------------------------------------------
# Review finding #2 (MAJOR): a full-width header/footer row must not collapse
# a multi-column split (card §6 case 3 floor: without page-margin detection at
# least do not change the order of the other rows).
# --------------------------------------------------------------------------


def test_full_width_header_and_footer_do_not_collapse_two_columns():
    result = synth.load_fixture("two_column_with_header")

    out = order_page_lines(result)

    # The full-width rows must not swallow the body's column split.
    assert len(out["columns"]) == 2, "full-width rows must not collapse columns"
    columns = {c["column_id"]: c for c in out["columns"]}
    assert set(columns["col-0"]["line_indexes"]) == {0, 1, 3, 5, 6}
    assert set(columns["col-1"]["line_indexes"]) == {2, 4}

    rows = out["text"].split("\n")
    assert rows[0] == "PAGE HEADER"
    body = [
        "Left one",
        "Left two",
        "Left three",
        "Right one",
        "Right two",
    ]
    # The other rows keep their column-major order (never interleaved by the
    # header/footer rows) and are never glued into a single row.
    assert [row for row in rows if row in body] == body
    # Header/footer land at the ends of their column, never mid-paragraph.
    assert rows.index("PAGE HEADER") < rows.index("Left one")
    assert rows.index("PAGE FOOTER") > rows.index("Left three")
    assert "Left oneRight one" not in out["text"]
    assert out["status"] == "ok"


# --------------------------------------------------------------------------
# Review finding #6 (MINOR): rule 6's "all lines from that one onward get
# limit" must also cover lines already deferred for another reason.
# --------------------------------------------------------------------------


def test_limit_also_marks_lines_already_deferred_for_another_reason():
    result = synth.load_fixture("over_limit_mixed")
    limits = PageOrderLimits(max_lines=1)

    out = order_page_lines(result, limits=limits)

    assert len(out["lines"]) == 3
    lines = _by_index(out)
    assert lines[0]["accepted"] is True
    assert lines[0]["defer_reasons"] == []
    assert lines[1]["defer_reasons"] == ["limit"]
    # line 2 was low_confidence AND sits after the limit cut point: both.
    assert lines[2]["defer_reasons"] == ["low_confidence", "limit"]
    assert lines[2]["accepted"] is False
    assert out["text"] == "AAAA"
    assert sorted(out["deferred_line_indexes"]) == [1, 2]
    assert out["status"] == "partial"
