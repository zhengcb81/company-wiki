"""RED-phase placeholder for P1-OCR-TEXT (frozen API only).

Declares the frozen ``adapt_ocr_pages`` signature from the P1 card §5.2 but
does not map pages yet.  The RED suite runs against this placeholder so it
fails with assertion messages instead of ImportError; the GREEN commit
replaces every body with the real adapter.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .pdf_page_aware import PageAwarePDFResult

PDF_OCR_PAGE_ADAPTER_ID = "pdf-ocr-page-adapter/1"


def adapt_ocr_pages(
    manifest: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
) -> PageAwarePDFResult:
    """Map OCR/text pages into canonical page-aware parser results.

    RED placeholder: returns an empty shell so the counterexample suite fails
    on assertions rather than on a missing import.
    """
    del manifest, pages
    return PageAwarePDFResult(normalized_text="", parser_results=(), page_count=1)


__all__ = [
    "PDF_OCR_PAGE_ADAPTER_ID",
    "adapt_ocr_pages",
]
