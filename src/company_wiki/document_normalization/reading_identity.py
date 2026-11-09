"""Public implementation identities for normalized reading and replay."""

from __future__ import annotations

from pathlib import Path

from company_wiki.document_model.reading_identity import (
    reading_algorithm_hashes as shared_reading_algorithm_hashes,
    table_shapes_sha256 as table_shapes_sha256,
    text_matching_sha256 as text_matching_sha256,
)
from company_wiki.implementation_identity import code_sha256, owned_algorithm_hashes


_OWNER = "company_wiki.document_normalization"
_ROOT = Path(__file__).resolve().parent
_LEGACY_MODEL_NAMES = ("form_fields", "table_shapes", "text_matching")


def reading_algorithm_hashes(*, pdf_frontend: bool) -> dict[str, str]:
    """Retain the former labels for the neutral helper implementations."""
    shared = shared_reading_algorithm_hashes()
    hashes = {
        f"{_OWNER}.{name}": shared[f"company_wiki.document_model.{name}"]
        for name in _LEGACY_MODEL_NAMES
    }
    if pdf_frontend:
        hashes.update(pdf_layout_algorithm_hashes())
    return hashes


def pdf_layout_algorithm_hashes() -> dict[str, str]:
    """Return the actual normalization rules used for PDF layout snapshots."""
    return owned_algorithm_hashes(
        _OWNER,
        _ROOT,
        (f"{_OWNER}.layout_snapshots",),
        includes=lambda name: name != _OWNER,
    )


def normalized_replay_sha256() -> str:
    from . import replay

    return code_sha256(replay.__file__)


def normalized_parser_sha256(mime_type: str) -> str:
    """Identify the parser implementation for one known normalized carrier."""
    from . import docx_parser, html_parser, pptx_parser
    from .errors import UnsupportedFormatError

    mime_main = mime_type.partition(";")[0].strip().lower()
    for parser in (html_parser, docx_parser, pptx_parser):
        if mime_main in parser.SUPPORTED_MIME_TYPES:
            return code_sha256(parser.__file__)
    raise UnsupportedFormatError(f"unsupported normalization MIME {mime_type!r}")


__all__ = [
    "normalized_parser_sha256",
    "normalized_replay_sha256",
    "pdf_layout_algorithm_hashes",
    "reading_algorithm_hashes",
    "table_shapes_sha256",
    "text_matching_sha256",
]
