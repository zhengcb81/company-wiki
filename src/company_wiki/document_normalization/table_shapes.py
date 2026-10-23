"""Literal native value-cell shapes; no inferred column names or business meaning."""
from __future__ import annotations

import re
import unicodedata

_NUMBER_CELL = re.compile(r"[+−-]?\d(?:[\d., \u00a0\u202f]*\d)?[%％]?")
_FOOTNOTE_MARKERS = "*†‡¹²³⁴⁵⁶⁷⁸⁹⁰"


def _is_value_cell(cell: str) -> bool:
    """Recognize visible numeric formatting without converting a numeric value."""
    text = cell.rstrip(_FOOTNOTE_MARKERS).strip()
    if text in {"-", "−", "—", "–", "－"}:
        return True
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()
    # Source currency glyphs, grouping/decimal separators and footnote marks
    # are formatting evidence only, never a currency/unit/amount assertion.
    text = "".join(char for char in text if unicodedata.category(char) != "Sc").strip()
    return _NUMBER_CELL.fullmatch(text) is not None


def has_tabular_value_tail(text: str) -> bool:
    """A label followed by two or more literal value cells is not title evidence.

    Require actual source separators. Ordinary prose mentioning numbers, a
    numbered title, or a single year on a following line proves no data row.
    This shape neither assigns a table/header nor interprets its numbers.
    """
    cells = [cell.strip() for cell in re.split(r"[\r\n\t]+", text) if cell.strip()]
    return (len(cells) >= 3 and any(char.isalpha() for char in cells[0])
            and all(_is_value_cell(cell) for cell in cells[1:]))
