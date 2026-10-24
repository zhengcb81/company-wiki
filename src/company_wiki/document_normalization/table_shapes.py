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


def has_unbound_numeric_cells(text: str) -> bool:
    """Observe several separate values; prove no column, unit or period.

    A descriptive change cell may follow the values. This deliberately does
    not relax the stricter heading veto above. Prose numbers embedded in a
    sentence and a label plus one value are not evidence of multiple cells.
    Require a consecutive value run: a number wrapped between ordinary prose
    fragments does not become a cell merely because another number follows.
    """
    cells = [cell.strip() for cell in re.split(r"[\r\n\t|]+", text) if cell.strip()]
    has_label = False
    numeric_run = 0
    has_values = False
    for cell in cells:
        if _is_value_cell(cell):
            numeric_run += any(char.isdigit() for char in cell)
            has_values = has_values or numeric_run >= 2
        else:
            has_label = has_label or any(char.isalpha() for char in cell)
            numeric_run = 0
    return has_label and has_values
