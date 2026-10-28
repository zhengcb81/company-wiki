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


@pytest.mark.parametrize("language,text", [
    ("en", "The company expanded overseas capacity and began product delivery. " * 3),
    ("zh", "公司海外新业务完成认证并开始批量交付，新增客户订单持续增长。" * 3),
])
def test_partial_docx_body_language_matches_composed_normalization(language, text):
    from document_normalization.test_docx import package, para, norm, MIME
    from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization

    data = package(para(text), {"word/header1.xml": "<header/>"})
    document = norm(data)
    assert not document.structure.coverage_complete
    assert "docx_header_footer_not_parsed" in document.structure.errors
    assert detect_narrative_language(data, MIME, normalization=NarrativeNormalization()) == language
    assert detect_narrative_language(data, MIME) == language


@pytest.mark.parametrize("data", [b"invalid zip", b"PK\x03\x04truncated"])
def test_invalid_docx_still_has_named_extraction_failure(data):
    from document_normalization.test_docx import MIME

    with pytest.raises(NarrativeLanguageError, match="SOURCE_LANGUAGE_TEXT_EXTRACTION_FAILED"):
        detect_narrative_language(data, MIME)


def test_batch_preparation_retains_configured_normalization_owner():
    import hashlib
    import json
    from unit.test_narrative_batch import _request, _module, SparseMetadataReader
    from document_normalization.test_docx import MIME, package, para
    from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
    from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization

    body = package(para("The new product completed customer qualification and began commercial delivery."))
    digest = hashlib.sha256(body).hexdigest()
    wire = _request().to_dict()
    wire["sources"][0].update(source_id="urn:company-wiki:source:sha256:" + digest,
        content_sha256=digest, byte_size=len(body), mime_type=MIME)
    seen = []
    class Normalization(NarrativeNormalization):
        def sample_text(self, data, mime_type, **kwargs):
            seen.append((data, mime_type))
            return super().sample_text(data, mime_type, **kwargs)
    result = _module().build_batch_events(NarrativeBatchRequest.from_dict(wire),
        SparseMetadataReader(body, MIME), now="2026-10-25T00:00:00Z", normalization=Normalization())
    assert seen == [(body, MIME)]
    assert json.loads(result.events[0].payload_json)["source_metadata"]["language"] == "en"
