"""Infer narrative language from a small sample of verified source bytes."""

from __future__ import annotations

from collections import Counter
import hashlib
import unicodedata


_LANGUAGE_REASON_CODES = frozenset({
    "SOURCE_LANGUAGE_TEXT_INVALID", "SOURCE_LANGUAGE_TEXT_EXTRACTION_FAILED",
    "SOURCE_LANGUAGE_PDF_UNAVAILABLE", "SOURCE_LANGUAGE_PDF_INVALID",
    "SOURCE_LANGUAGE_UNSUPPORTED_MIME", "SOURCE_LANGUAGE_UNSUPPORTED_SCRIPT",
    "SOURCE_LANGUAGE_UNDETERMINED",
})


class NarrativeLanguageError(ValueError):
    """A source cannot be classified safely for narrative processing."""

    @property
    def code(self) -> str:
        reason = str(self)
        return reason if reason in _LANGUAGE_REASON_CODES else "SOURCE_LANGUAGE_FAILURE"


_SUPPORTED_TEXT_MIME_TYPES = {
    "text/plain",
    "text/html",
    "application/xhtml+xml",
    "application/json",
}
_MAX_TEXT_SAMPLE_BYTES = 256 * 1024
_MAX_SAMPLE_CHARS = 100_000
_MIN_CLASSIFIABLE_LETTERS = 20
_MIN_MIXED_SCRIPT_LETTERS = 12
_MIXED_SCRIPT_SHARE = 0.12
_BOILERPLATE_LINES = {
    "annual report",
    "conference call transcript",
    "earnings call transcript",
    "full conference call transcript",
    "investor relations",
    "quarterly report",
    "semi-annual report",
    "transcript",
}


def _decode_sample(data: bytes) -> str:
    sample = data[:_MAX_TEXT_SAMPLE_BYTES]
    # A byte cap can end in the middle of a UTF-8 character. Trim only that
    # incomplete tail; invalid bytes earlier in the sample remain a hard error.
    for trailing in range(4):
        candidate = sample[: len(sample) - trailing] if trailing else sample
        try:
            return candidate.decode("utf-8-sig", errors="strict")[:_MAX_SAMPLE_CHARS]
        except UnicodeDecodeError as exc:
            if exc.end != len(candidate) or trailing == 3:
                raise NarrativeLanguageError("SOURCE_LANGUAGE_TEXT_INVALID") from None
    raise NarrativeLanguageError("SOURCE_LANGUAGE_TEXT_INVALID")


def _text_for_mime(data: bytes, mime_type: str, *, normalization=None) -> str:
    if mime_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
        if normalization is not None:
            return normalization.sample_text(data, mime_type)
        from company_wiki.document_normalization import normalize_document
        try:
            digest = hashlib.sha256(data).hexdigest()
            document = normalize_document(data, source_id="urn:company-wiki:source:sha256:" + digest,
                                          source_sha256=digest, mime_type=mime_type)
            if document.structure.errors:
                raise NarrativeLanguageError("SOURCE_LANGUAGE_TEXT_EXTRACTION_FAILED")
            return "\n".join(unit.raw_text for unit in document.units)[:_MAX_SAMPLE_CHARS]
        except (RuntimeError, ValueError) as exc:
            raise NarrativeLanguageError("SOURCE_LANGUAGE_TEXT_EXTRACTION_FAILED") from exc
    if mime_type == "application/pdf":
        try:
            import fitz  # type: ignore[import-untyped]
        except ImportError:
            raise NarrativeLanguageError("SOURCE_LANGUAGE_PDF_UNAVAILABLE") from None
        try:
            with fitz.open(stream=data, filetype="pdf") as document:
                return "\n".join(
                    document.load_page(index).get_text()
                    for index in range(min(5, document.page_count))
                )[:_MAX_SAMPLE_CHARS]
        except Exception as exc:
            raise NarrativeLanguageError("SOURCE_LANGUAGE_PDF_INVALID") from exc

    if mime_type not in _SUPPORTED_TEXT_MIME_TYPES:
        raise NarrativeLanguageError("SOURCE_LANGUAGE_UNSUPPORTED_MIME")
    if mime_type == "text/plain":
        return _decode_sample(data)

    # HTML and JSON transcript sources already have a bounded, untranslated
    # extractor. Reuse it so tags and JSON structure do not skew script counts.
    from .transcript_text_extract import (
        TranscriptMaterialError,
        extract_transcript_material,
    )

    try:
        material = extract_transcript_material(data, mime_type=mime_type)
    except TranscriptMaterialError as exc:
        detail = str(exc).lower()
        code = (
            "SOURCE_LANGUAGE_TEXT_INVALID"
            if "utf-8" in detail or "utf8" in detail
            else "SOURCE_LANGUAGE_TEXT_EXTRACTION_FAILED"
        )
        raise NarrativeLanguageError(code) from exc
    return material.text_utf8[:_MAX_SAMPLE_CHARS]


def _script_counts(text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    unsupported = False
    usable_lines = (
        line for line in text.splitlines()
        if line.strip().casefold() not in _BOILERPLATE_LINES
    )
    for char in "\n".join(usable_lines):
        if not char.isalpha():
            continue
        name = unicodedata.name(char, "")
        if "LATIN" in name:
            counts["en"] += 1
        elif "CJK UNIFIED IDEOGRAPH" in name or "CJK COMPATIBILITY IDEOGRAPH" in name:
            counts["zh"] += 1
        else:
            unsupported = True
    if unsupported:
        raise NarrativeLanguageError("SOURCE_LANGUAGE_UNSUPPORTED_SCRIPT")
    return counts


def detect_narrative_language(data: bytes, mime_type: str, *, normalization=None) -> str:
    """Return ``zh``, ``en``, or ``mixed``; never guess from entity or market."""
    if not isinstance(data, bytes) or not data:
        raise NarrativeLanguageError("SOURCE_LANGUAGE_TEXT_INVALID")
    return detect_narrative_text_language(_text_for_mime(data, mime_type, normalization=normalization))


def detect_narrative_text_language(text: str) -> str:
    """Classify a bounded actual native/OCR sample, without entity guesses."""
    counts = _script_counts(text)
    chinese = counts["zh"]
    english = counts["en"]
    total = chinese + english
    if total < _MIN_CLASSIFIABLE_LETTERS:
        raise NarrativeLanguageError("SOURCE_LANGUAGE_UNDETERMINED")
    minority = min(chinese, english)
    if minority >= _MIN_MIXED_SCRIPT_LETTERS and minority / total >= _MIXED_SCRIPT_SHARE:
        return "mixed"
    return "zh" if chinese > english else "en"


__all__ = ["NarrativeLanguageError", "detect_narrative_language"]
