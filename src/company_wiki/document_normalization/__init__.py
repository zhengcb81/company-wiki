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

from company_wiki.source_contract.source_version import VerifiedContent

from ._source_input import _NormalizationSource
from .assets import OpaqueAsset
from .document import KNOWN_FORMATS, NormalizedDocument
from .errors import (
    NormalizationError,
    NormalizationLimitError,
    ReplayError,
    UnsupportedFormatError,
)
from .docx_parser import SUPPORTED_MIME_TYPES as _DOCX_MIME_TYPES
from .docx_parser import _parse_docx, parse_docx as parse_docx
from .html_parser import SUPPORTED_MIME_TYPES as _HTML_MIME_TYPES
from .html_parser import _parse_html, parse_html as parse_html
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
from .pptx_parser import _parse_pptx, parse_pptx as parse_pptx
from .replay import replay_unit, replay_units, replay_evidence_spans, replay_verified_evidence_spans
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
    require_parser_version,
)
from . import table_shapes as table_shapes, text_matching as text_matching

__all__ = [
    'DEFAULT_LIMITS',
    'FORMAT_DOCX',
    'DOCX_PARSER_VERSION',
    'LEGACY_DOCX_PARSER_VERSION',
    'FORMAT_HTML',
    'FORMAT_PPTX',
    'KNOWN_FORMATS',
    'MAX_ZIP_MEMBERS',
    'NORMALIZATION_SCHEMA',
    'NormalizationError',
    'NormalizationLimitError',
    'NormalizationLimits',
    'NormalizedDocument',
    'LocalOCRAdapter',
    'LocalOCRConfig',
    'LocalOCRError',
    'OCRLimits',
    'OCRModelFile',
    'OCRLine',
    'ImageOCRResult',
    'OpaqueAsset',
    'PARSER_NAME',
    'PARSER_VERSION',
    'ReplayError',
    'UnsupportedFormatError',
    'normalize_document',
    'normalize_verified_document',
    'replay_unit',
    'replay_units',
    'replay_evidence_spans',
    'replay_verified_evidence_spans',
    'normalization_identity',
    'PPTX_PARSER_VERSION',
    'PPTX_OCR_PARSER_VERSION',
    'table_shapes',
    'text_matching',
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
    """Verify raw source bytes and normalize exactly that source version."""
    limits = DEFAULT_LIMITS if limits is None else limits
    source = _NormalizationSource.from_bytes(
        original, source_id=source_id, source_sha256=source_sha256, limits=limits,
    )
    return _normalize_source(
        source, mime_type=mime_type, limits=limits, parser_version=parser_version,
        ocr=ocr, ocr_limits=ocr_limits,
    )


def normalize_verified_document(
    content: VerifiedContent,
    *,
    mime_type: str,
    limits: NormalizationLimits | None = None,
    parser_version: str | None = None,
    ocr=None,
    ocr_limits=None,
) -> NormalizedDocument:
    """Normalize an immutable source-owner observation within the parser's limits."""
    limits = DEFAULT_LIMITS if limits is None else limits
    source = _NormalizationSource.from_verified(content, limits=limits)
    return _normalize_source(
        source, mime_type=mime_type, limits=limits, parser_version=parser_version,
        ocr=ocr, ocr_limits=ocr_limits,
    )


def _normalize_source(
    source: _NormalizationSource,
    *,
    mime_type: str,
    limits: NormalizationLimits,
    parser_version: str | None,
    ocr=None,
    ocr_limits=None,
) -> NormalizedDocument:
    if not isinstance(mime_type, str) or not mime_type.strip():
        raise UnsupportedFormatError("mime_type must be non-empty text")
    mime_main = mime_type.split(";")[0].strip().lower()
    if mime_main in _DOCX_MIME_TYPES:
        version = DOCX_PARSER_VERSION if parser_version is None else parser_version
        require_parser_version(FORMAT_DOCX, version)
        return _parse_docx(
            source, limits=limits, parser_version=version,
        )
    if mime_main in _HTML_MIME_TYPES:
        if parser_version not in {None, PARSER_VERSION}:
            raise ValueError("unsupported HTML parser_version")
        return _parse_html(source, limits=limits)
    if mime_main in _PPTX_MIME_TYPES:
        version = (
            parser_version
            if parser_version is not None
            else (PPTX_OCR_PARSER_VERSION if ocr is not None else PPTX_PARSER_VERSION)
        )
        if version == PPTX_OCR_PARSER_VERSION and ocr is None:
            raise LocalOCRError("OCR_ADAPTER_REQUIRED")
        if ocr is not None and version != PPTX_OCR_PARSER_VERSION:
            raise ValueError(f"OCR requires PPTX parser_version {PPTX_OCR_PARSER_VERSION}")
        document = _parse_pptx(
            source,
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
