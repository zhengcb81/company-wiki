"""Deterministic HTML/PPTX normalization with versioned locator replay.

Public entry points (frozen by the R6-FORMAT construction card):

>>> from company_wiki.document_normalization import (
...     normalize_document, replay_unit, NormalizationLimits)
>>> limits = NormalizationLimits()
>>> doc = normalize_document(html_bytes, source_id=..., source_sha256=...,
...                          mime_type="text/html", limits=limits)
>>> text = replay_unit(html_bytes, source_sha256=...,
...                    unit=doc.units[0], limits=limits)

The layer is pure parsing and replay: no network, no models, no database,
no durable full-text or per-page image artifacts.  Opaque assets carry byte
identity (images also in-memory bytes for MAIN's budgeted model work).
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
from .html_parser import SUPPORTED_MIME_TYPES as _HTML_MIME_TYPES
from .html_parser import parse_html
from .limits import DEFAULT_LIMITS, MAX_ZIP_MEMBERS, NormalizationLimits
from .pptx_parser import SUPPORTED_MIME_TYPES as _PPTX_MIME_TYPES
from .pptx_parser import parse_pptx
from .replay import replay_unit
from .units import (
    FORMAT_HTML,
    FORMAT_PPTX,
    NORMALIZATION_SCHEMA,
    PARSER_NAME,
    PARSER_VERSION,
)

__all__ = [
    "DEFAULT_LIMITS",
    "FORMAT_HTML",
    "FORMAT_PPTX",
    "KNOWN_FORMATS",
    "MAX_ZIP_MEMBERS",
    "NORMALIZATION_SCHEMA",
    "NormalizationError",
    "NormalizationLimitError",
    "NormalizationLimits",
    "NormalizedDocument",
    "OpaqueAsset",
    "PARSER_NAME",
    "PARSER_VERSION",
    "ReplayError",
    "UnsupportedFormatError",
    "normalize_document",
    "replay_unit",
]


def normalize_document(
    original: bytes,
    *,
    source_id: str,
    source_sha256: str,
    mime_type: str,
    limits: NormalizationLimits | None = None,
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
    if mime_main in _HTML_MIME_TYPES:
        return parse_html(
            original,
            source_id=source_id,
            source_sha256=source_sha256,
            mime_type=mime_type,
            limits=limits,
        )
    if mime_main in _PPTX_MIME_TYPES:
        return parse_pptx(
            original,
            source_id=source_id,
            source_sha256=source_sha256,
            mime_type=mime_type,
            limits=limits,
        )
    raise UnsupportedFormatError(
        f"unsupported mime_type {mime_type!r}; supported: "
        f"{sorted(_HTML_MIME_TYPES | _PPTX_MIME_TYPES)}"
    )
