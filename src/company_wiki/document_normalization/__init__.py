"""Deterministic HTML/PPTX normalization with versioned locator replay.

Public entry points (frozen by the R6-FORMAT construction card):

>>> from company_wiki.document_normalization import (
...     normalize_document, replay_unit, NormalizationLimits)
>>> limits = NormalizationLimits()
>>> doc = normalize_document(html_bytes, source_id=..., source_sha256=...,
...                          mime_type="text/html", limits=limits)
>>> text = replay_unit(html_bytes, source_sha256=...,
...                    unit=doc.units[0], limits=limits)

Default parsing and replay are pure. Explicit CPU local OCR enriches image
evidence in memory, with no network, downloads, database or durable full-text
or per-page image artifacts. Opaque image assets keep their byte identity.
"""

from __future__ import annotations

import hashlib

from .assets import OpaqueAsset
from .document import KNOWN_FORMATS, NormalizedDocument
from .errors import (
    NormalizationError,
    NormalizationLimitError,
    ReplayError,
    UnsupportedFormatError,
)
from .docx_parser import SUPPORTED_MIME_TYPES as _DOCX_MIME_TYPES
from .docx_parser import parse_docx
from .html_parser import SUPPORTED_MIME_TYPES as _HTML_MIME_TYPES
from .html_parser import parse_html
from .limits import DEFAULT_LIMITS, MAX_ZIP_MEMBERS, NormalizationLimits
from .local_ocr import (
    LocalOCRAdapter,
    LocalOCRConfig,
    LocalOCRError,
    OCRLimits,
    OCRModelFile,
    OCRLine,
    ImageOCRResult,
)
from .pptx_parser import SUPPORTED_MIME_TYPES as _PPTX_MIME_TYPES
from .pptx_parser import parse_pptx
from .replay import replay_unit, replay_units, replay_evidence_spans
from .units import (
    FORMAT_DOCX,
    DOCX_PARSER_VERSION,
    LEGACY_DOCX_PARSER_VERSION,
    FORMAT_HTML,
    FORMAT_PPTX,
    NORMALIZATION_SCHEMA,
    PARSER_NAME,
    PARSER_VERSION,
    PPTX_PARSER_VERSION,
    PPTX_OCR_PARSER_VERSION,
)

__all__ = [
    "DEFAULT_LIMITS",
    "FORMAT_DOCX",
    "DOCX_PARSER_VERSION",
    "LEGACY_DOCX_PARSER_VERSION",
    "FORMAT_HTML",
    "FORMAT_PPTX",
    "KNOWN_FORMATS",
    "MAX_ZIP_MEMBERS",
    "NORMALIZATION_SCHEMA",
    "NormalizationError",
    "NormalizationLimitError",
    "NormalizationLimits",
    "NormalizedDocument",
    "LocalOCRAdapter",
    "LocalOCRConfig",
    "LocalOCRError",
    "OCRLimits",
    "OCRModelFile",
    "OCRLine",
    "ImageOCRResult",
    "OpaqueAsset",
    "PARSER_NAME",
    "PARSER_VERSION",
    "ReplayError",
    "UnsupportedFormatError",
    "normalize_document",
    "replay_unit",
    "replay_units",
    "replay_evidence_spans",
    "normalization_identity",
    "PPTX_PARSER_VERSION",
    "PPTX_OCR_PARSER_VERSION",
]


def normalize_document(
    original: bytes,
    *,
    source_id: str,
    source_sha256: str,
    mime_type: str,
    limits: NormalizationLimits | None = None,
    parser_version: str | None = None,
    ocr=None,
    ocr_limits=None,
) -> NormalizedDocument:
    """Normalize one verified source document from its actual bytes."""
    if not isinstance(original, bytes):
        raise TypeError("original must be bytes")
    if not isinstance(source_id, str) or not source_id:
        raise TypeError("source_id must be non-empty text")
    if not isinstance(mime_type, str) or not mime_type.strip():
        raise UnsupportedFormatError("mime_type must be non-empty text")
    if limits is None:
        limits = DEFAULT_LIMITS
    if not isinstance(limits, NormalizationLimits):
        raise TypeError("limits must be a NormalizationLimits")
    if hashlib.sha256(original).hexdigest() != source_sha256:
        raise ValueError("source bytes do not match source_sha256")
    if len(original) > limits.max_source_bytes:
        raise NormalizationLimitError(
            "max_source_bytes", limits.max_source_bytes, f"got {len(original)}"
        )
    mime_main = mime_type.split(";")[0].strip().lower()
    if mime_main in _DOCX_MIME_TYPES:
        version = DOCX_PARSER_VERSION if parser_version is None else parser_version
        if version not in {LEGACY_DOCX_PARSER_VERSION, DOCX_PARSER_VERSION}:
            raise ValueError("unsupported DOCX parser_version")
        return parse_docx(
            original, source_id=source_id, source_sha256=source_sha256,
            mime_type=mime_type, limits=limits, parser_version=version,
        )
    if mime_main in _HTML_MIME_TYPES:
        if parser_version not in {None, PARSER_VERSION}:
            raise ValueError("unsupported HTML parser_version")
        return parse_html(
            original,
            source_id=source_id,
            source_sha256=source_sha256,
            mime_type=mime_type,
            limits=limits,
        )
    if mime_main in _PPTX_MIME_TYPES:
        version = (
            parser_version
            if parser_version is not None
            else (PPTX_OCR_PARSER_VERSION if ocr is not None else PPTX_PARSER_VERSION)
        )
        if version == PPTX_OCR_PARSER_VERSION and ocr is None:
            from .local_ocr import LocalOCRError

            raise LocalOCRError("OCR_ADAPTER_REQUIRED")
        if ocr is not None and version != PPTX_OCR_PARSER_VERSION:
            raise ValueError("OCR requires PPTX parser_version 2.0.0")
        document = parse_pptx(
            original,
            source_id=source_id,
            source_sha256=source_sha256,
            mime_type=mime_type,
            limits=limits,
            parser_version=PPTX_PARSER_VERSION
            if version == PPTX_OCR_PARSER_VERSION
            else version,
        )
        if version == PPTX_OCR_PARSER_VERSION:
            from .ocr_composition import enrich_pptx

            return enrich_pptx(document, ocr=ocr, limits=limits, ocr_limits=ocr_limits)
        return document
    raise UnsupportedFormatError(
        f"unsupported mime_type {mime_type!r}; supported: "
        f"{sorted(_HTML_MIME_TYPES | _PPTX_MIME_TYPES | _DOCX_MIME_TYPES)}"
    )


def normalization_identity(mime_type: str, *, ocr=None) -> dict:
    """Pathless derivation identity for MAIN's batch/artifact generation manifest."""
    mime_main = mime_type.split(";")[0].strip().lower()
    if mime_main in _DOCX_MIME_TYPES:
        return {"parser_name": PARSER_NAME, "parser_version": DOCX_PARSER_VERSION, "format": FORMAT_DOCX}
    if mime_main in _HTML_MIME_TYPES:
        return {
            "parser_name": PARSER_NAME,
            "parser_version": PARSER_VERSION,
            "format": "html",
        }
    if mime_main not in _PPTX_MIME_TYPES:
        raise UnsupportedFormatError("unsupported normalization MIME")
    identity = {
        "parser_name": PARSER_NAME,
        "parser_version": PPTX_OCR_PARSER_VERSION
        if ocr is not None
        else PPTX_PARSER_VERSION,
        "format": "pptx",
    }
    if ocr is not None:
        from .ocr_composition import adapter_identity

        manifest, fingerprint = adapter_identity(ocr)
        identity.update(ocr_identity=manifest, ocr_fingerprint=fingerprint)
    return identity
