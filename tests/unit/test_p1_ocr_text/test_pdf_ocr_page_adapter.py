"""RED counterexample suite for ``adapt_ocr_pages`` (P1-OCR-TEXT card §5.2).

Cases are written against the frozen adapter contract so they fail on real
assertions (not ImportError) before the mapping lands.  OCR page documents are
hand-built ``cwp-ocr-page-text/1`` dicts so the adapter cases do not depend on
``order_page_lines`` being implemented first.
"""

from __future__ import annotations

import copy
import dataclasses

import pytest

import synth
from company_wiki.document_normalization.ocr_page_text import P1_PAGE_TEXT_SCHEMA
from company_wiki.parser_adapters.pdf_ocr_page_adapter import adapt_ocr_pages
from company_wiki.source_contract import ImmutableStatus, ParseStatus, QualityFlag


def _line(index, text, start, end, *, accepted=True, defer_reasons=()):
    return {
        "line_index": index,
        "column_id": "col-0",
        "text": text,
        "box": [50.0, 100.0, 400.0, 120.0],
        "confidence": 0.95,
        "char_start": start if accepted else None,
        "char_end": end if accepted else None,
        "accepted": accepted,
        "defer_reasons": list(defer_reasons),
    }


def _ocr_doc(page_text, lines, *, status="ok", schema_version=P1_PAGE_TEXT_SCHEMA):
    accepted = [line for line in lines if line["accepted"]]
    deferred = [line["line_index"] for line in lines if not line["accepted"]]
    return {
        "schema_version": schema_version,
        "page": {"width": 800, "height": 1000},
        "status": status,
        "columns": [
            {
                "column_id": "col-0",
                "x0": 50.0,
                "x1": 400.0,
                "line_indexes": [line["line_index"] for line in lines],
            }
        ],
        "lines": lines,
        "text": page_text,
        "deferred_line_indexes": deferred,
        "diagnostics": [],
        "work_used": {"lines": len(accepted), "chars": len(page_text)},
        "reason": None,
    }


def _ocr_page(page_number, ocr_doc):
    return {"page_number": page_number, "ocr": ocr_doc}


def _text_page(page_number, text, quality_score=0.95):
    return {"page_number": page_number, "text": text, "quality_score": quality_score}


def _flags(result):
    return set(result.quality_flags)


# --------------------------------------------------------------------------
# Full OCR page with accepted text -> parsed + ocr_used.
# --------------------------------------------------------------------------


def test_all_ocr_pages_are_parsed_with_ocr_used(tmp_path):
    manifest = synth.build_manifest(tmp_path)
    pages = [
        _ocr_page(
            1,
            _ocr_doc("Hello", [_line(0, "Hello", 0, 5)]),
        )
    ]

    out = adapt_ocr_pages(manifest, pages)

    assert out.page_count == 1
    assert out.normalized_text == "Hello"
    assert len(out.parser_results) == 1
    result = out.parser_results[0]
    assert result.parse_status == ParseStatus.PARSED
    assert QualityFlag.OCR_USED in _flags(result)
    assert result.raw_text == "Hello"


# --------------------------------------------------------------------------
# Mixed accepted + deferred page -> partial, with mapped quality flags.
# --------------------------------------------------------------------------


def test_page_mixing_accepted_and_deferred_lines_is_partial(tmp_path):
    manifest = synth.build_manifest(tmp_path)
    lines = [
        _line(0, "Keep me", 0, 7),
        _line(1, "Drop me", 8, 15, accepted=False, defer_reasons=["low_confidence"]),
    ]
    pages = [_ocr_page(1, _ocr_doc("Keep me", lines, status="partial"))]

    out = adapt_ocr_pages(manifest, pages)

    assert out.normalized_text == "Keep me"
    assert len(out.parser_results) == 1
    result = out.parser_results[0]
    assert result.parse_status == ParseStatus.PARTIAL
    assert QualityFlag.OCR_USED in _flags(result)
    assert QualityFlag.LOW_OCR_CONFIDENCE in _flags(result)


def test_ambiguous_order_defer_maps_to_layout_ambiguous(tmp_path):
    manifest = synth.build_manifest(tmp_path)
    lines = [
        _line(0, "Anchor", 0, 6),
        _line(
            1,
            "Crossed",
            7,
            14,
            accepted=False,
            defer_reasons=["ambiguous_order"],
        ),
    ]
    pages = [_ocr_page(1, _ocr_doc("Anchor", lines, status="partial"))]

    out = adapt_ocr_pages(manifest, pages)

    result = out.parser_results[0]
    assert QualityFlag.LAYOUT_AMBIGUOUS in _flags(result)


def test_limit_defer_maps_to_truncated(tmp_path):
    manifest = synth.build_manifest(tmp_path)
    lines = [
        _line(0, "Head", 0, 4),
        _line(1, "Cut", 5, 8, accepted=False, defer_reasons=["limit"]),
    ]
    pages = [_ocr_page(1, _ocr_doc("Head", lines, status="partial"))]

    out = adapt_ocr_pages(manifest, pages)

    result = out.parser_results[0]
    assert QualityFlag.TRUNCATED in _flags(result)


# --------------------------------------------------------------------------
# All-deferred -> failed, never an empty string posing as success.
# --------------------------------------------------------------------------


def test_all_deferred_page_is_failed_and_empty_output(tmp_path):
    manifest = synth.build_manifest(tmp_path)
    lines = [
        _line(0, "Gone", 0, 4, accepted=False, defer_reasons=["low_confidence"]),
    ]
    pages = [_ocr_page(1, _ocr_doc("", lines, status="unavailable"))]

    out = adapt_ocr_pages(manifest, pages)

    assert out.normalized_text == ""
    assert len(out.parser_results) == 1
    result = out.parser_results[0]
    assert result.parse_status == ParseStatus.FAILED
    assert result.raw_text is None
    assert QualityFlag.EMPTY_OUTPUT in _flags(result)


# --------------------------------------------------------------------------
# Mixing OCR and plain-text pages is allowed.
# --------------------------------------------------------------------------


def test_mixed_ocr_and_text_pages_both_become_results(tmp_path):
    manifest = synth.build_manifest(tmp_path)
    pages = [
        _ocr_page(1, _ocr_doc("Ocr text", [_line(0, "Ocr text", 0, 8)])),
        _text_page(2, "Plain text"),
    ]

    out = adapt_ocr_pages(manifest, pages)

    assert out.page_count == 2
    assert out.normalized_text == "Ocr text\n\nPlain text"
    ocr_result = out.parser_results[0]
    text_result = out.parser_results[1]
    assert ocr_result.coordinates.page_number == 1
    assert text_result.coordinates.page_number == 2
    assert QualityFlag.OCR_USED in _flags(ocr_result)
    assert QualityFlag.OCR_USED not in _flags(text_result)
    assert ocr_result.parse_status == ParseStatus.PARSED
    assert text_result.parse_status == ParseStatus.PARSED


# --------------------------------------------------------------------------
# OCR line char ranges bind into that page's text.
# --------------------------------------------------------------------------


def test_ocr_line_char_ranges_bind_into_the_page_text(tmp_path):
    manifest = synth.build_manifest(tmp_path)
    pages = [
        _ocr_page(
            1,
            _ocr_doc("Alpha", [_line(0, "Alpha", 0, 5)]),
        ),
        _ocr_page(
            2,
            _ocr_doc("Beta", [_line(0, "Beta", 0, 4)]),
        ),
    ]

    out = adapt_ocr_pages(manifest, pages)

    first, second = out.parser_results
    page2_start = out.normalized_text.index("Beta")
    assert first.coordinates.char_start == 0
    assert first.coordinates.char_end == 5
    assert second.coordinates.char_start == page2_start
    assert second.coordinates.char_end == page2_start + 4
    assert out.normalized_text[
        second.coordinates.char_start : second.coordinates.char_end
    ] == "Beta"


# --------------------------------------------------------------------------
# Failure semantics: duplicate / <=0 page numbers, bad ocr schema.
# --------------------------------------------------------------------------


def test_duplicate_page_number_raises_value_error(tmp_path):
    manifest = synth.build_manifest(tmp_path)
    pages = [
        _ocr_page(1, _ocr_doc("One", [_line(0, "One", 0, 3)])),
        _ocr_page(1, _ocr_doc("Two", [_line(0, "Two", 0, 3)])),
    ]

    with pytest.raises(ValueError):
        adapt_ocr_pages(manifest, pages)


def test_zero_page_number_raises_value_error(tmp_path):
    manifest = synth.build_manifest(tmp_path)
    pages = [_ocr_page(0, _ocr_doc("One", [_line(0, "One", 0, 3)]))]

    with pytest.raises(ValueError):
        adapt_ocr_pages(manifest, pages)


def test_wrong_ocr_schema_version_raises_value_error(tmp_path):
    manifest = synth.build_manifest(tmp_path)
    doc = _ocr_doc(
        "One",
        [_line(0, "One", 0, 3)],
        schema_version="cwp-ocr-page-text/9",
    )
    pages = [_ocr_page(1, doc)]

    with pytest.raises(ValueError):
        adapt_ocr_pages(manifest, pages)


def test_empty_pages_raise_value_error(tmp_path):
    manifest = synth.build_manifest(tmp_path)

    with pytest.raises(ValueError):
        adapt_ocr_pages(manifest, [])


def test_non_pdf_manifest_raises_value_error(tmp_path):
    pdf_manifest = synth.build_manifest(tmp_path)
    bad_manifest = dataclasses.replace(pdf_manifest, mime_type="text/html")
    pages = [_ocr_page(1, _ocr_doc("One", [_line(0, "One", 0, 3)]))]

    with pytest.raises(ValueError):
        adapt_ocr_pages(bad_manifest, pages)


def test_unverified_manifest_raises_value_error(tmp_path):
    pdf_manifest = synth.build_manifest(tmp_path)
    bad_manifest = dataclasses.replace(
        pdf_manifest, immutable_status=ImmutableStatus.QUARANTINED
    )
    pages = [_ocr_page(1, _ocr_doc("One", [_line(0, "One", 0, 3)]))]

    with pytest.raises(ValueError):
        adapt_ocr_pages(bad_manifest, pages)


# --------------------------------------------------------------------------
# Non-contiguous page order is tolerated but flagged locator_unstable.
# --------------------------------------------------------------------------


def test_non_contiguous_page_order_sets_locator_unstable(tmp_path):
    manifest = synth.build_manifest(tmp_path)
    pages = [
        _ocr_page(1, _ocr_doc("One", [_line(0, "One", 0, 3)])),
        _ocr_page(3, _ocr_doc("Three", [_line(0, "Three", 0, 5)])),
    ]

    out = adapt_ocr_pages(manifest, pages)

    assert len(out.parser_results) == 2, "both pages must produce a result"
    for result in out.parser_results:
        assert QualityFlag.LOCATOR_UNSTABLE in _flags(result)


# --------------------------------------------------------------------------
# §8 resource boundary -- no network, no model calls.
# --------------------------------------------------------------------------


def test_adapter_uses_no_network(tmp_path, monkeypatch):
    import socket

    manifest = synth.build_manifest(tmp_path)
    pages = [_ocr_page(1, _ocr_doc("One", [_line(0, "One", 0, 3)]))]

    def _blocked(*args, **kwargs):  # pragma: no cover - defensive
        raise AssertionError("network use is forbidden in P1-OCR-TEXT")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)

    out = adapt_ocr_pages(manifest, pages)
    assert out.page_count == 1
    assert out.normalized_text == "One"
    assert len(out.parser_results) == 1


# --------------------------------------------------------------------------
# Review finding #5 (MINOR): card §5.2 read at document level -- when any page
# yields no accepted body the surviving pages must read PARTIAL, not PARSED.
# --------------------------------------------------------------------------


def test_document_with_a_failed_page_marks_surviving_page_partial(tmp_path):
    manifest = synth.build_manifest(tmp_path)
    pages = [
        _ocr_page(1, _ocr_doc("Keep", [_line(0, "Keep", 0, 4)])),
        _ocr_page(
            2,
            _ocr_doc(
                "",
                [
                    _line(
                        0,
                        "Gone",
                        0,
                        4,
                        accepted=False,
                        defer_reasons=["low_confidence"],
                    )
                ],
                status="unavailable",
            ),
        ),
    ]

    out = adapt_ocr_pages(manifest, pages)

    assert out.normalized_text == "Keep"
    assert len(out.parser_results) == 2
    surviving, failed = out.parser_results
    # §5.2: "部分 → partial" applies to the document, so the page that still
    # has body is PARTIAL (it no longer stands alone as a clean success).
    assert surviving.parse_status == ParseStatus.PARTIAL
    assert failed.parse_status == ParseStatus.FAILED
    assert failed.raw_text is None
    assert QualityFlag.LOW_OCR_CONFIDENCE in _flags(failed)


# --------------------------------------------------------------------------
# Review finding #10 (NIT): scope item 6 also covers manifest/pages immutability.
# --------------------------------------------------------------------------


def test_adapter_does_not_mutate_manifest_or_pages(tmp_path):
    manifest = synth.build_manifest(tmp_path)
    pages = [_ocr_page(1, _ocr_doc("One", [_line(0, "One", 0, 3)]))]
    manifest_before = manifest.to_dict()
    pages_before = copy.deepcopy(pages)

    out = adapt_ocr_pages(manifest, pages)

    assert out.normalized_text == "One"
    assert manifest.to_dict() == manifest_before
    assert pages == pages_before
