"""G1e original-to-TXT byte locator replay on small synthetic material."""

from __future__ import annotations

from dataclasses import replace
from copy import deepcopy

import pytest

from company_wiki.source_catalog.transcript_material import (
    TranscriptMaterialError,
    extract_transcript_material,
    load_transcript_material,
)


def test_html_original_maps_each_english_line_to_immutable_bytes():
    original = (
        '<html><head><script>ignore_me()</script></head><body>\n'
        '<p>Presentation</p>\n'
        '<p>CEO: We expanded overseas &amp; added a new product.</p>\n'
        '<p>Analyst: When will production start?</p>\n'
        '<p>CEO: It is planned for next year, not completed.</p>\n'
        '</body></html>'
    ).encode("utf-8")
    material = extract_transcript_material(original, mime_type="text/html")
    assert material.text_utf8.splitlines() == [
        "Presentation",
        "CEO: We expanded overseas & added a new product.",
        "Analyst: When will production start?",
        "CEO: It is planned for next year, not completed.",
    ]
    assert len(material.lines) == 4
    assert material.lines[1].source_locator.startswith("byte:")
    assert b"&amp;" in original[
        material.lines[1].source_byte_start : material.lines[1].source_byte_end
    ]
    material.verify(original)
    replay = load_transcript_material(
        material.lineage_dict(), original=original,
        text_utf8=material.text_utf8.encode("utf-8"), expected_mime_type="text/html",
    )
    assert replay == material
    compact_lineage = material.lineage_dict()
    assert "text_utf8" not in compact_lineage
    assert "lines" not in compact_lineage
    assert compact_lineage["line_count"] == len(material.lines)
    damaged_lineage = deepcopy(material.lineage_dict())
    damaged_lineage["line_count"] += 1
    with pytest.raises(TranscriptMaterialError, match="deterministic extraction"):
        load_transcript_material(
            damaged_lineage, original=original,
            text_utf8=material.text_utf8.encode("utf-8"), expected_mime_type="text/html",
        )
    with pytest.raises(TranscriptMaterialError, match="trusted source receipt"):
        load_transcript_material(
            compact_lineage, original=original,
            text_utf8=material.text_utf8.encode("utf-8"), expected_mime_type="text/plain",
        )
    with pytest.raises(TranscriptMaterialError, match="original bytes changed"):
        material.verify(original.replace(b"overseas", b"domestic"))
    with pytest.raises(TranscriptMaterialError, match="derived text bytes changed"):
        replace(material, text_utf8=material.text_utf8.replace("planned", "completed")).verify(
            original
        )
    with pytest.raises(TranscriptMaterialError, match="derived line does not replay"):
        bad_line = replace(
            material.lines[1],
            source_byte_start=material.lines[1].source_byte_start + 1,
        )
        replace(material, lines=(material.lines[0], bad_line, *material.lines[2:])).verify(
            original
        )


def test_plain_txt_keeps_language_and_literal_entities():
    original = b"Operator: Welcome\r\nCEO: R&D &amp; export expansion\r\n"
    material = extract_transcript_material(original, mime_type="text/plain")
    assert material.text_utf8 == "Operator: Welcome\nCEO: R&D &amp; export expansion\n"
    assert material.lines[1].source_byte_start == len(b"Operator: Welcome\r\n")
    material.verify(original)
    replay = load_transcript_material(
        material.lineage_dict(), original=original,
        text_utf8=material.text_utf8.encode("utf-8"), expected_mime_type="text/plain",
    )
    assert replay == material


def test_xhtml_original_is_supported_and_replayable():
    original = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<html xmlns="http://www.w3.org/1999/xhtml"><body>'
        b'<p>CEO: We entered a new market &amp; expanded supply.</p>'
        b'</body></html>'
    )
    material = extract_transcript_material(original, mime_type="application/xhtml+xml")
    assert material.text_utf8 == "CEO: We entered a new market & expanded supply.\n"
    replay = load_transcript_material(
        material.lineage_dict(), original=original,
        text_utf8=material.text_utf8.encode("utf-8"),
        expected_mime_type="application/xhtml+xml",
    )
    assert replay == material


def test_html_multibyte_prefix_keeps_exact_byte_offsets():
    original = "<p>Café</p><p>CEO: New market opened.</p>".encode("utf-8")
    material = extract_transcript_material(original, mime_type="text/html")
    assert material.text_utf8 == "Café\nCEO: New market opened.\n"
    assert material.lines[0].source_byte_start == original.index("Café".encode("utf-8"))
    assert material.lines[1].source_byte_start == original.index(b"CEO:")
    material.verify(original)


@pytest.mark.parametrize(
    ("body", "mime"),
    [(b"", "text/plain"), (b"\xff", "text/plain"), (b"hello", "application/pdf")],
)
def test_invalid_original_is_rejected(body: bytes, mime: str):
    with pytest.raises(TranscriptMaterialError):
        extract_transcript_material(body, mime_type=mime)
