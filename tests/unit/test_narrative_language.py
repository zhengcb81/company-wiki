"""Language inference is deterministic and reads only bounded verified bytes."""

from __future__ import annotations

import pytest

from company_wiki.source_catalog.narrative_language import (
    NarrativeLanguageError,
    detect_narrative_language,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "公司完成海外产能扩张，新产品已进入批量交付。" * 8,
            "zh",
        ),
        (
            "The company expanded overseas capacity and began product delivery. " * 6,
            "en",
        ),
        (
            "The company expanded overseas capacity. " * 5
            + "公司完成海外产能扩张。" * 5,
            "mixed",
        ),
    ],
)
def test_detects_chinese_english_and_mixed_text(text: str, expected: str) -> None:
    assert detect_narrative_language(text.encode("utf-8"), "text/plain") == expected


def test_detects_language_from_pdf_text_without_writing_a_temp_file() -> None:
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    try:
        document.new_page().insert_text(
            (72, 72),
            "The company expanded overseas capacity and began product delivery.",
        )
        original = document.tobytes()
    finally:
        document.close()

    assert detect_narrative_language(original, "application/pdf") == "en"


def test_undetectable_and_unsupported_scripts_fail_with_named_errors() -> None:
    with pytest.raises(NarrativeLanguageError, match="SOURCE_LANGUAGE_UNDETERMINED"):
        detect_narrative_language(b"12345 --", "text/plain")

    japanese = "日本語の事業説明と製品開発を進めています。".encode("utf-8") * 4
    with pytest.raises(NarrativeLanguageError, match="SOURCE_LANGUAGE_UNSUPPORTED_SCRIPT"):
        detect_narrative_language(japanese, "text/plain")


def test_rejects_unsupported_mime_and_non_utf8_text() -> None:
    with pytest.raises(NarrativeLanguageError, match="SOURCE_LANGUAGE_UNSUPPORTED_MIME"):
        detect_narrative_language(b"content", "application/octet-stream")

    with pytest.raises(NarrativeLanguageError, match="SOURCE_LANGUAGE_TEXT_INVALID"):
        detect_narrative_language(b"\xff" * 64, "text/plain")
