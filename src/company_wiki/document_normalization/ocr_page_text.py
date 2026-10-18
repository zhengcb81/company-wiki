"""RED-phase placeholder for P1-OCR-TEXT (frozen API only).

This module declares the frozen interface from
``docs/plans/parallel-packages-2026-10-18/P1-OCR-TEXT/card.md`` §5.1 but does
not implement the ordering/deferral judgement rules yet.  The RED unit tests
run against this placeholder so they fail with real assertion messages (not
ImportError) before the implementation lands; the GREEN commit replaces every
body with the geometry-driven implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .local_ocr import ImageOCRResult

P1_PAGE_TEXT_SCHEMA = "cwp-ocr-page-text/1"
P1_PAGE_TEXT_VERSION = "1.0.0"


@dataclass(frozen=True)
class PageOrderLimits:
    """Per-call ordering budget (not a shared resource-limit object)."""

    max_lines: int = 2000
    max_chars: int = 20000
    max_columns: int = 4
    min_confidence: float = 0.60
    column_gap_em: float = 2.0
    line_tolerance_em: float = 0.60


def order_page_lines(
    result: ImageOCRResult,
    *,
    limits: PageOrderLimits = PageOrderLimits(),
    font_size: float | None = None,
) -> dict[str, Any]:
    """Order one page's OCR lines into bounded, locatable body text.

    RED placeholder: returns the schema shell with empty content so the
    counterexample suite fails on assertions rather than on a missing import.
    """
    del limits, font_size
    return {
        "schema_version": P1_PAGE_TEXT_SCHEMA,
        "page": {"width": result.width, "height": result.height},
        "status": "ok",
        "columns": [],
        "lines": [],
        "text": "",
        "deferred_line_indexes": [],
        "diagnostics": [],
        "work_used": {"lines": 0, "chars": 0},
        "reason": None,
    }


__all__ = [
    "P1_PAGE_TEXT_SCHEMA",
    "P1_PAGE_TEXT_VERSION",
    "PageOrderLimits",
    "order_page_lines",
]
