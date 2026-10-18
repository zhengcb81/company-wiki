"""Bounded DOCX/PPTX table structure extraction for ``cwp-office-table/1``.

The module reads the OOXML package bytes directly — DOCX through ``zipfile`` and
``lxml`` (never python-docx), PPTX through the existing optional ``python-pptx``
dependency — and reports the structure today's parsers drop: merge spans, header
rows, footnote text, and the page-break hints that mark a continuation table.

What this module is *not*:

* it never rewrites or re-derives an existing unit locator; a cell's ``locator``
  is either byte-identical to what ``docx_parser.table()`` / ``pptx_parser``
  already emit for that cell, or ``None`` when no such unit exists;
* it makes no header guess from formatting (bold, centring, font size): a DOCX
  header row exists only when ``w:trPr/w:tblHeader`` does, and a PPTX table has
  no header because PresentationML has no such attribute;
* it parses no numbers, converts no units, classifies no financial table, and
  reads no PDF (P1 scope);
* it performs no IO beyond the caller's bytes, no network call, and no model
  call.

Bounded work: ``OfficeTableLimits`` caps tables, cells, cell text and footnote
text per call.  A table is always kept whole or dropped whole, so a limit can
never produce a truncated table; a dropped or over-wide item sets the overall
status to ``partial`` and records a ``p2_table_limit`` / ``p2_span_out_of_grid``
diagnostic instead of silently shrinking the result.  ``work_used`` counts the
*emitted* cells (a ``gridSpan=2`` cell is one cell), so the budget and the
structure it describes can never disagree.

Unknown is never a number: an absent ``w:gridSpan`` is a confirmed ``1``, but a
present non-positive ``w:gridSpan`` (no card rule covers it), a span past the
declared grid, a conflicting PPTX merge flag, and a footnote whose text cannot
be read all report ``null`` plus a diagnostic — never ``1`` or ``""``.  For the
non-positive ``w:gridSpan`` this review chose ``p2_span_out_of_grid`` with
``column_span=None`` (the width is out of the legal domain, not a merge-chain
break) and it does not advance or close the open ``w:vMerge`` chain.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import io
import json
import posixpath
import unicodedata
import zipfile
from typing import Any

from lxml import etree  # type: ignore[import-untyped]

from .units import DOCX_LOCATOR_SCHEMA, FORMAT_DOCX, FORMAT_PPTX, PPTX_LOCATOR_SCHEMA

P2_OFFICE_TABLE_SCHEMA = "cwp-office-table/1"
P2_OFFICE_TABLE_VERSION = "1.0.0"
PARSER_NAME = "cwp_office_table_structure"

DOCX_MAIN_PART = "word/document.xml"
PPTX_MAIN_PART = "ppt/presentation.xml"
DOCX_FOOTNOTES_PART = "word/footnotes.xml"
FOOTNOTE_REFERENCE = "footnoteReference"
# `w:footnote/@w:type` values that carry layout glyphs, never footnote content.
FOOTNOTE_LAYOUT_TYPES = frozenset(
    {"separator", "continuationseparator", "continuationnotice"}
)
LAST_RENDERED_PAGE_BREAK = "lastRenderedPageBreak"

# Fixed safety bound mirrored from document_normalization.limits: a package with
# more members than this is not a plausible document and is cheaper to refuse.
MAX_ZIP_MEMBERS = 10_000
MAX_XML_PART_BYTES = 16 * 1024 * 1024

# Merge vocabulary (card §5.3).
MERGE_NONE = "none"
MERGE_HORIZONTAL = "horizontal"
MERGE_VERTICAL_START = "vertical_start"
MERGE_VERTICAL_CONTINUE = "vertical_continue"
MERGE_BOTH = "both"

STATUS_OK = "ok"
STATUS_PARTIAL = "partial"
STATUS_UNAVAILABLE = "unavailable"

CONTINUATION_UNKNOWN = "unknown"
CONTINUATION_NOT_APPLICABLE = "not_applicable"

HEADER_SOURCE_TBLHEADER = "tblHeader"
HEADER_SOURCE_NONE = "none"

# Replay compares these per table and per cell (card §5.5).  `cells` is handled
# separately because it is a list, and `table_id` because it keys the message.
TABLE_FIELDS = (
    "package_part",
    "native_index",
    "grid",
    "column_widths",
    "header",
    "footnotes",
    "continuation",
    "diagnostics",
)
CELL_FIELDS = (
    "row",
    "column",
    "locator",
    "merge",
    "row_span",
    "column_span",
    "text",
    "text_refs",
    "footnote_refs",
)

P2_SPAN_OUT_OF_GRID = "p2_span_out_of_grid"
P2_MERGE_UNRESOLVED = "p2_merge_unresolved"
P2_FOOTNOTE_UNRESOLVED = "p2_footnote_unresolved"
P2_CONTINUATION_UNKNOWN = "p2_continuation_unknown"
P2_TABLE_LIMIT = "p2_table_limit"
DEPENDENCY_UNAVAILABLE = "dependency_unavailable"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
LAST_RENDERED_BREAK_TAG = W + LAST_RENDERED_PAGE_BREAK
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


@dataclass(frozen=True)
class OfficeTableLimits:
    """Finite per-call budget for one ``parse_office_tables`` call.

    This is a call-scoped limit, not a new human approval artifact: callers bound
    their own work and a smaller budget only narrows this one call.
    """

    max_tables: int = 64
    max_cells: int = 20000
    max_text_chars: int = 200000
    max_footnote_chars: int = 20000

    def __post_init__(self) -> None:
        for name in (
            "max_tables",
            "max_cells",
            "max_text_chars",
            "max_footnote_chars",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be a strictly positive int")
            if value <= 0:
                raise ValueError(f"{name} must be a strictly positive int")


def canonical_json(value: object) -> str:
    """Canonical JSON used for ``structure_sha256`` (INTERFACES §1)."""
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _cell_text(value: str) -> str:
    """Cell text is NFC-normalized and trimmed only (card §5.3)."""
    return _nfc(value).strip()


def _diagnostic(code: str, table_id: str | None, detail: str) -> dict[str, object]:
    return {"code": code, "table_id": table_id, "detail": detail}


class _Work:
    """Running budget for one parse; the only mutable parse state."""

    def __init__(self, limits: OfficeTableLimits) -> None:
        self.limits = limits
        self.tables = 0
        self.cells = 0
        self.chars = 0
        self.exhausted = False

    def admits_table(self, cells: int, chars: int) -> bool:
        if self.tables + 1 > self.limits.max_tables:
            return False
        if self.cells + cells > self.limits.max_cells:
            return False
        if self.chars + chars > self.limits.max_text_chars:
            return False
        return True

    def take(self, cells: int, chars: int) -> None:
        self.tables += 1
        self.cells += cells
        self.chars += chars


class _Package:
    """Read-only view of one OOXML ZIP with the repository's safety checks."""

    def __init__(self, original: bytes) -> None:
        try:
            archive = zipfile.ZipFile(io.BytesIO(original))
        except (zipfile.BadZipFile, OSError) as exc:
            raise ValueError("invalid archive") from exc
        self._archive = archive
        self.parts: dict[str, zipfile.ZipInfo] = {}
        try:
            infos = archive.infolist()
            if len(infos) > MAX_ZIP_MEMBERS:
                raise ValueError("archive member limit exceeded")
            for info in infos:
                name = info.filename
                normalized = posixpath.normpath(name.replace("\\", "/"))
                if (
                    normalized.startswith(("/", ".."))
                    or ":" in normalized
                    or (not info.is_dir() and normalized != name)
                ):
                    raise ValueError("unsafe archive member")
                if normalized in self.parts:
                    raise ValueError("duplicate archive member")
                if info.flag_bits & 1:
                    raise ValueError("encrypted archive member")
                self.parts[normalized] = info
        except Exception:
            archive.close()
            raise

    def has(self, name: str) -> bool:
        return name in self.parts

    def read(self, name: str) -> bytes:
        info = self.parts[name]
        if info.file_size > MAX_XML_PART_BYTES:
            raise ValueError("archive part too large")
        with self._archive.open(info) as stream:
            return stream.read(MAX_XML_PART_BYTES + 1)

    def xml(self, name: str) -> Any:
        parser = etree.XMLParser(
            resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False
        )
        try:
            root = etree.fromstring(self.read(name), parser=parser)
        except etree.XMLSyntaxError as exc:
            raise ValueError("invalid office XML") from exc
        if root.getroottree().docinfo.doctype:
            raise ValueError("office XML doctype is unsupported")
        return root

    def close(self) -> None:
        self._archive.close()

    def __enter__(self) -> "_Package":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


# --------------------------------------------------------------------- DOCX text


def _docx_visible_text(node: Any) -> str:
    """Visible text of one DOCX node, mirroring the parser's selection rules."""
    tag = node.tag
    if tag in {W + "del", W + "moveFrom"}:
        return ""
    if tag == W + "r":
        hidden = node.find(W + "rPr/" + W + "vanish")
        if hidden is not None and hidden.get(W + "val", "true").casefold() not in {
            "false",
            "off",
            "0",
        }:
            return ""
    if tag in {W + "drawing", W + "pict", W + "object", W + "altChunk"}:
        return ""
    if tag == W + "t":
        return node.text or ""
    if tag in {W + "tab", W + "br", W + "cr"}:
        return " "
    return "".join(_docx_visible_text(child) for child in node)


def _docx_paragraph_text(node: Any) -> str:
    return _cell_text(_docx_visible_text(node))


def _docx_cell_paragraphs(cell_node: Any) -> list[Any]:
    return [child for child in cell_node if child.tag == W + "p"]


def _docx_first_visible_index(paragraphs: Sequence[Any]) -> int | None:
    for index, node in enumerate(paragraphs):
        if _docx_paragraph_text(node):
            return index
    return None


def _docx_cell_text(paragraphs: Sequence[Any]) -> str:
    for node in paragraphs:
        text = _docx_paragraph_text(node)
        if text:
            return text
    return ""


def _paragraph_has_page_break(paragraph_node: Any) -> bool:
    """True when the paragraph itself carries ``w:lastRenderedPageBreak``.

    Runs, hyperlinks, smart tags and other inline wrappers are descended into; a
    nested ``w:tbl`` is not, because its page breaks are the nested table's
    evidence, not this cell's.
    """
    stack = [paragraph_node]
    while stack:
        node = stack.pop()
        for child in node:
            if child.tag == LAST_RENDERED_BREAK_TAG:
                return True
            if child.tag != W + "tbl":
                stack.append(child)
    return False


def _docx_cell_locator(
    *,
    table_index: int,
    row_index: int,
    column_index: int,
    paragraphs: Sequence[Any],
) -> str | None:
    """The locator ``docx_parser.table()`` already emits for this cell, or None.

    ``docx_parser`` numbers paragraphs over the cell's direct ``w:p`` children
    and skips blank ones, so the first *emitted* unit for a cell carries the
    index of the first paragraph with visible text.  A cell with no paragraph
    (or no visible text) has no unit at all and therefore no locator.
    """
    index = _docx_first_visible_index(paragraphs)
    if index is None:
        return None
    return (
        f"{DOCX_LOCATOR_SCHEMA}|t={table_index}"
        f"|r={row_index}|c={column_index}|p={index}"
    )


# ------------------------------------------------------------------ DOCX merges


def _docx_int_attribute(node: Any, name: str) -> int | None:
    if node is None:
        return None
    raw = node.get(W + name)
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _docx_grid(node: Any) -> tuple[int | None, list[int] | None]:
    grid = node.find(W + "tblGrid")
    if grid is None:
        return None, None
    columns = grid.findall(W + "gridCol")
    widths = [_docx_int_attribute(column, "w") for column in columns]
    if any(width is None for width in widths):
        return len(columns), None
    return len(columns), [int(width) for width in widths if width is not None]


def _docx_header_rows(rows: Sequence[Any]) -> list[int]:
    marked: list[int] = []
    for index, node in enumerate(rows):
        marker = node.find(W + "trPr/" + W + "tblHeader")
        if marker is None:
            continue
        value = marker.get(W + "val", "true")
        if value.casefold() in {"false", "off", "0"}:
            continue
        marked.append(index)
    return marked


def _docx_vmerge(cell_node: Any) -> str | None:
    """``"restart"``, ``"continue"``, or ``None`` for no ``w:vMerge`` at all."""
    marker = cell_node.find(W + "tcPr/" + W + "vMerge")
    if marker is None:
        return None
    value = marker.get(W + "val")
    if value is None or value.casefold() == "continue":
        return "continue"
    if value.casefold() == "restart":
        return "restart"
    return "continue"


# ---------------------------------------------------------------- generic table


def _table_codes(table_structure: Mapping[str, object]) -> set[str]:
    """Diagnostic codes attached to one table structure."""
    diagnostics = table_structure.get("diagnostics")
    if not isinstance(diagnostics, list):
        return set()
    return {
        str(entry["code"])
        for entry in diagnostics
        if isinstance(entry, Mapping) and "code" in entry
    }


def _empty_continuation(status: str) -> dict[str, object]:
    return {
        "page_break_hints": [],
        "repeated_header": False,
        "continuation_of": None,
        "status": status,
    }


def _finish_structure(
    *,
    format_name: str,
    source_sha256: str,
    tables: list[dict[str, object]],
    status: str,
    diagnostics: list[dict[str, object]],
    work: _Work,
) -> dict[str, object]:
    return {
        "schema_version": P2_OFFICE_TABLE_SCHEMA,
        "format": format_name,
        "source_sha256": source_sha256,
        "parser": {"name": PARSER_NAME, "version": P2_OFFICE_TABLE_VERSION},
        "tables": tables,
        "structure_sha256": _sha256(canonical_json(tables).encode("utf-8")),
        "status": status,
        "diagnostics": diagnostics,
        "work_used": {
            "tables": work.tables,
            "cells": work.cells,
            "chars": work.chars,
        },
    }


# ---------------------------------------------------------------------- DOCX run


def _docx_footnote_texts(package: _Package) -> tuple[dict[str, str], bool]:
    """``(id -> text, part_present)`` for ``word/footnotes.xml``.

    Only notes that actually carry visible text are returned.  A ``w:footnote``
    that exists but yields no text is therefore indistinguishable from an absent
    id, which is exactly card §5.5's rule: the cell reference keeps
    ``text=None`` and records ``p2_footnote_unresolved`` instead of claiming an
    empty footnote (INTERFACES §1: ``""`` is never a stand-in for unknown).
    The ``separator``/``continuationSeparator``/``continuationNotice`` notes hold
    layout glyphs, never content, so they are skipped outright.
    """
    if not package.has(DOCX_FOOTNOTES_PART):
        return {}, False
    root = package.xml(DOCX_FOOTNOTES_PART)
    texts: dict[str, str] = {}
    for note in root.findall(W + "footnote"):
        footnote_id = note.get(W + "id")
        if footnote_id is None or footnote_id in texts:
            continue
        if (note.get(W + "type") or "").casefold() in FOOTNOTE_LAYOUT_TYPES:
            continue
        text = _cell_text(" ".join(_docx_visible_text(node) for node in note))
        if not text:
            continue
        texts[footnote_id] = text
    return texts, True


def _docx_table_structure(
    *,
    node: Any,
    table_index: int,
    work: _Work,
    footnote_texts: Mapping[str, str],
    footnotes_present: bool,
    footnote_budget: list[int],
) -> tuple[dict[str, object], bool]:
    """Build one table; returns ``(structure, over_grid)``."""
    rows = node.findall(W + "tr")
    columns, widths = _docx_grid(node)
    header_rows = _docx_header_rows(rows)

    cells: list[dict[str, object]] = []
    table_diagnostics: list[dict[str, object]] = []
    page_break_hints: list[str] = []
    table_footnotes: list[dict[str, object]] = []
    seen_footnotes: set[str] = set()
    over_grid = False
    # Per grid column: the cell id of the open vertical merge, if one is open.
    open_vertical: dict[int, str] = {}

    for row_index, row_node in enumerate(rows):
        column = 0
        for column_index, cell_node in enumerate(row_node.findall(W + "tc")):
            paragraphs = _docx_cell_paragraphs(cell_node)
            grid_span = _docx_int_attribute(
                cell_node.find(W + "tcPr/" + W + "gridSpan"), "val"
            )
            vmerge = _docx_vmerge(cell_node)
            cell_id = f"r{row_index}c{column}"
            # `w:gridSpan` absent confirms one column (card §5.3 rule 1).  A
            # present but non-positive value is not a confirmed width, so it is
            # treated like an out-of-grid span: `column_span=None`, never a
            # silent 1, and `occupied` records the one grid position the cell is
            # still known to sit on so the merge chain stays consistent.
            if grid_span is None:
                # No `w:gridSpan`: one column, confirmed (card §5.3 rule 1).
                span, column_span, occupied = 1, 1, 1
            elif grid_span <= 0:
                span, column_span, occupied = 1, None, 1
                over_grid = True
                table_diagnostics.append(
                    _diagnostic(
                        P2_SPAN_OUT_OF_GRID,
                        f"tbl-{table_index}",
                        f"{cell_id} gridSpan={grid_span} is not a positive "
                        "column count",
                    )
                )
            elif columns is not None and column + grid_span > columns:
                span, column_span, occupied = grid_span, None, 1
                over_grid = True
                table_diagnostics.append(
                    _diagnostic(
                        P2_SPAN_OUT_OF_GRID,
                        f"tbl-{table_index}",
                        f"{cell_id} gridSpan={grid_span} exceeds grid "
                        f"columns={columns}",
                    )
                )
            else:
                span, column_span, occupied = grid_span, grid_span, grid_span

            row_span: int | None = 1
            if vmerge == "restart":
                merge = MERGE_VERTICAL_START
                for offset in range(occupied):
                    open_vertical[column + offset] = cell_id
            elif vmerge == "continue":
                merge = MERGE_VERTICAL_CONTINUE
                if column not in open_vertical:
                    table_diagnostics.append(
                        _diagnostic(
                            P2_MERGE_UNRESOLVED,
                            f"tbl-{table_index}",
                            f"{cell_id} vertical continue without an upper start",
                        )
                    )
                for offset in range(occupied):
                    open_vertical.setdefault(column + offset, cell_id)
            else:
                merge = MERGE_NONE
                for offset in range(occupied):
                    open_vertical.pop(column + offset, None)

            text = "" if merge == MERGE_VERTICAL_CONTINUE else _docx_cell_text(paragraphs)
            locator = _docx_cell_locator(
                table_index=table_index,
                row_index=row_index,
                column_index=column_index,
                paragraphs=paragraphs,
            )

            footnote_refs: list[dict[str, object]] = []
            for reference in cell_node.iter(W + FOOTNOTE_REFERENCE):
                footnote_id = reference.get(W + "id")
                if footnote_id is None:
                    continue
                text_value: str | None = None
                if footnote_id in footnote_texts:
                    candidate = footnote_texts[footnote_id]
                    if footnote_budget[0] + len(candidate) <= work.limits.max_footnote_chars:
                        footnote_budget[0] += len(candidate)
                        text_value = candidate
                        if footnote_id not in seen_footnotes:
                            seen_footnotes.add(footnote_id)
                            table_footnotes.append(
                                {
                                    "footnote_id": footnote_id,
                                    "text": candidate,
                                    "text_refs": [],
                                }
                            )
                    else:
                        table_diagnostics.append(
                            _diagnostic(
                                P2_FOOTNOTE_UNRESOLVED,
                                f"tbl-{table_index}",
                                f"footnote {footnote_id} exceeds max_footnote_chars",
                            )
                        )
                else:
                    table_diagnostics.append(
                        _diagnostic(
                            P2_FOOTNOTE_UNRESOLVED,
                            f"tbl-{table_index}",
                            "part_absent"
                            if not footnotes_present
                            else f"footnote {footnote_id} not found",
                        )
                    )
                footnote_refs.append(
                    {"footnote_id": footnote_id, "text": text_value}
                )

            for paragraph_node in paragraphs:
                # Scan only this cell's own paragraphs: a `w:lastRenderedPageBreak`
                # inside a nested `w:tbl` belongs to the nested table, and the
                # hint must name a cell of *this* table (card §5.4).
                if _paragraph_has_page_break(paragraph_node):
                    page_break_hints.append(cell_id)
                    break

            cells.append(
                {
                    "cell_id": cell_id,
                    "row": row_index,
                    "column": column,
                    "row_span": row_span,
                    "column_span": column_span,
                    "merge": merge,
                    "locator": locator,
                    "text_refs": [],
                    "footnote_refs": footnote_refs,
                    "text": text,
                }
            )
            column += span

    has_header = bool(header_rows)
    continuation = _empty_continuation(CONTINUATION_UNKNOWN)
    continuation["page_break_hints"] = page_break_hints
    continuation["repeated_header"] = bool(page_break_hints) and has_header
    if page_break_hints and has_header:
        continuation["status"] = STATUS_OK
    elif not page_break_hints:
        # Word writes `w:lastRenderedPageBreak` only after a paged preview, so an
        # absent hint is genuinely unknown, never "no page break".
        table_diagnostics.append(
            _diagnostic(
                P2_CONTINUATION_UNKNOWN,
                f"tbl-{table_index}",
                "no lastRenderedPageBreak hint in the package",
            )
        )

    structure = {
        "table_id": f"tbl-{table_index}",
        "package_part": DOCX_MAIN_PART,
        "native_index": table_index,
        "grid": {"rows": len(rows), "columns": columns},
        "column_widths": widths,
        "header": {
            "rows": header_rows,
            "source": HEADER_SOURCE_TBLHEADER if has_header else HEADER_SOURCE_NONE,
        },
        "cells": cells,
        "footnotes": table_footnotes,
        "continuation": continuation,
        "diagnostics": table_diagnostics,
    }
    return structure, over_grid


def _docx_header_signature(table_structure: Mapping[str, object]) -> tuple[tuple[str, ...], ...] | None:
    header = table_structure.get("header")
    if not isinstance(header, Mapping):
        return None
    marked = header.get("rows")
    if not isinstance(marked, list) or not marked:
        return None
    cells = table_structure.get("cells")
    if not isinstance(cells, list):
        return None
    signature: list[tuple[str, ...]] = []
    for row_index in sorted(marked):
        texts = tuple(
            str(entry.get("text", ""))
            for entry in cells
            if entry.get("row") == row_index
        )
        signature.append(texts)
    return tuple(signature)


def _docx_continuation_links(tables: list[dict[str, object]]) -> None:
    """A table continues the previous one only on identical repeated headers."""
    previous: dict[str, object] | None = None
    for structure in tables:
        continuation = structure["continuation"]
        assert isinstance(continuation, dict)
        if previous is not None:
            earlier = previous["continuation"]
            assert isinstance(earlier, Mapping)
            if earlier.get("repeated_header") is True:
                left = _docx_header_signature(previous)
                right = _docx_header_signature(structure)
                if left is not None and left == right:
                    continuation["continuation_of"] = previous["table_id"]
        previous = structure


def _docx_table_work(node: Any) -> tuple[int, int]:
    """``(emitted cells, cell text chars)`` a DOCX table would consume.

    The unit is the emitted cell, not the raw ``w:tc`` position: a ``gridSpan=2``
    cell is one cell in ``cells``, so it must cost one, otherwise ``work_used``
    and ``max_cells`` would disagree with the structure they describe
    (card §5.1 "实际处理量").  A vertical continuation is still an emitted cell
    and still costs one, even though it carries no text.
    """
    cells = 0
    chars = 0
    for row_node in node.findall(W + "tr"):
        for cell_node in row_node.findall(W + "tc"):
            cells += 1
            if _docx_vmerge(cell_node) != "continue":
                chars += len(_docx_cell_text(_docx_cell_paragraphs(cell_node)))
    return cells, chars


def _docx_table_order(body: Any) -> list[Any | None]:
    """Tables in the order ``docx_parser`` numbers them (``t=<i>``).

    ``body.iter(W + "tbl")`` yields every table in document order, but the
    parser numbers a different subset: ``table()`` numbers a table on entry
    and recurses only into a ``w:tbl`` that is a *direct* child of a cell
    (a ``w:sdt``-wrapped nested table inside a cell is reported as an
    unsupported element and never entered), while ``body()`` descends the
    ``w:sdt`` / ``w:customXml`` / ``w:ins`` / ``w:moveTo`` wrappers.  A real
    research note whose cells carry ``w:sdt``-wrapped nested tables shifted
    every later ``t=`` index under ``body.iter``, so this walk replicates the
    parser exactly.

    ``w:del`` / ``w:moveFrom`` regions never *emit* a table (``body`` walks
    them with ``visible=False``), but ``docx_parser`` still advances the very
    counter ``table()`` reads for ``t=``: inside an invisible walk a ``w:tbl``
    child adds its whole raw subtree (``child.iter(W + "tbl")``) and only the
    ``sdt`` / ``customXml`` / ``ins`` / ``moveTo`` / nested ``del`` /
    ``moveFrom`` wrappers are descended — a table inside a ``w:p`` is never
    reached, exactly as ``body()`` never descends a paragraph.  Every such
    deleted-region table therefore consumes a ``t=`` index without yielding a
    structure: it is emitted here as ``None``, so a visible table's *position*
    in the returned list is exactly the parser's ``t=`` index, and the caller
    skips the placeholders without spending budget on them.
    """

    order: list[Any | None] = []

    def walk_table(table_node: Any) -> None:
        order.append(table_node)
        for row_node in table_node.findall(W + "tr"):
            for cell_node in row_node.findall(W + "tc"):
                for child in cell_node:
                    if child.tag == W + "tbl":
                        walk_table(child)

    def walk_body(node: Any, visible: bool = True) -> None:
        for child in node:
            if child.tag == W + "tbl":
                if visible:
                    walk_table(child)
                else:
                    # body(visible=False) counts the whole raw subtree of a
                    # direct w:tbl child and never emits anything from it.
                    order.extend(None for _ in child.iter(W + "tbl"))
            elif child.tag in {W + "del", W + "moveFrom"}:
                walk_body(child, visible=False)
            elif child.tag in {
                W + "sdt",
                W + "customXml",
                W + "ins",
                W + "moveTo",
            }:
                # ``docx_parser.body()`` descends into ``w:sdtContent`` for a
                # ``w:sdt`` and into the wrapper itself otherwise, keeping the
                # current visibility; following the same shape keeps the
                # numbering aligned.
                content = (
                    child.find(W + "sdtContent")
                    if child.tag == W + "sdt"
                    else None
                )
                walk_body(content if content is not None else child, visible)

    walk_body(body, visible=True)
    return order


def _parse_docx(
    package: _Package, source_sha256: str, work: _Work
) -> dict[str, object]:
    document = package.xml(DOCX_MAIN_PART)
    body = document.find(W + "body")
    if body is None:
        raise ValueError("DOCX document body is missing")
    footnote_texts, footnotes_present = _docx_footnote_texts(package)

    table_nodes = _docx_table_order(body)
    tables: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    status = STATUS_OK
    footnote_budget = [0]
    seen_in_tables = 0

    for position, node in enumerate(table_nodes):
        if node is None:
            # A deleted-region table consumed the parser's t= index without
            # being processed: no structure, no budget, no cells — but every
            # later table keeps the index the parser gives it.
            continue
        if seen_in_tables >= work.limits.max_tables:
            diagnostics.append(
                _diagnostic(P2_TABLE_LIMIT, None, f"max_tables={work.limits.max_tables}")
            )
            status = STATUS_PARTIAL
            work.exhausted = True
            break
        cell_count, chars = _docx_table_work(node)
        if not work.admits_table(cell_count, chars):
            limit = (
                "max_cells"
                if work.cells + cell_count > work.limits.max_cells
                else "max_text_chars"
            )
            diagnostics.append(
                _diagnostic(
                    P2_TABLE_LIMIT,
                    None,
                    f"{limit} reached before table {seen_in_tables}",
                )
            )
            status = STATUS_PARTIAL
            work.exhausted = True
            break
        structure, over_grid = _docx_table_structure(
            node=node,
            table_index=position,
            work=work,
            footnote_texts=footnote_texts,
            footnotes_present=footnotes_present,
            footnote_budget=footnote_budget,
        )
        work.take(cell_count, chars)
        seen_in_tables += 1
        tables.append(structure)
        diagnostics.extend(structure["diagnostics"])  # type: ignore[arg-type]
        if over_grid:
            status = STATUS_PARTIAL

    _docx_continuation_links(tables)
    return _finish_structure(
        format_name=FORMAT_DOCX,
        source_sha256=source_sha256,
        tables=tables,
        status=status,
        diagnostics=diagnostics,
        work=work,
    )


# --------------------------------------------------------------------- PPTX run


def _pptx_module() -> Any:
    try:
        import pptx as module
    except ImportError:
        return None
    return module


def _pptx_cell_text(cell: Any) -> str:
    return _cell_text(cell.text or "")


def _pptx_hmerge_overflows(
    cells: Sequence[Mapping[str, object]],
    columns: int | None,
    row_index: int,
    column: int,
) -> bool:
    """True when an ``hMerge="1"`` cell cannot be placed inside the grid.

    PresentationML keeps one ``a:tc`` per grid position, so a merged run is an
    origin cell that declares ``@gridSpan`` followed by ``@hMerge="1"`` cells.
    The run overflows when there is no origin at or before this column *in this
    row* whose declared span (or span-less single column) still reaches it, or
    when the position itself is already outside ``a:tblGrid``.  Either way the
    covered origin is unknown, so the span must be ``null`` rather than ``1``.
    """
    if columns is not None and column >= columns:
        return True
    origin_column: int | None = None
    for entry in cells:
        if entry.get("row") != row_index:
            continue
        if entry.get("merge") == MERGE_HORIZONTAL:
            continue
        origin_column = entry["column"]  # type: ignore[assignment]
    if origin_column is None:
        return True
    return column <= origin_column and column != origin_column


def _pptx_table_structure(
    *,
    table: Any,
    table_index: int,
    slide_number: int,
    shape_path: str,
    package_part: str,
    native_index: int,
) -> dict[str, object]:
    grid_column = table._tbl.tblGrid  # noqa: SLF001 - python-pptx exposes no public grid
    width_nodes = (
        grid_column.findall(A + "gridCol") if grid_column is not None else []
    )
    widths = [int(node.get("w")) for node in width_nodes if node.get("w")]
    columns = len(width_nodes) if grid_column is not None else None

    cells: list[dict[str, object]] = []
    table_diagnostics: list[dict[str, object]] = []
    origin_by_column: dict[int, str] = {}
    table_id = f"tbl-{table_index}"

    for row_index, row in enumerate(table.rows):
        column = 0
        for cell_index, cell in enumerate(row.cells):
            tc = cell._tc  # noqa: SLF001 - merge attributes live only on a:tc
            grid_span = tc.get("gridSpan")
            h_merge = tc.get("hMerge")
            v_merge = tc.get("vMerge")
            span_value = int(grid_span) if grid_span is not None else None

            signals = sum(
                1
                for flag in (
                    span_value is not None and span_value > 1,
                    h_merge == "1",
                    v_merge == "1",
                )
                if flag
            )
            # Unlike DOCX (where a `w:vMerge` continue cell carries no content of
            # its own), PresentationML still stores text in a `@vMerge="1"` cell
            # and `pptx_parser` emits a unit for it.  Keeping the text is what
            # preserves locator/text parity; the covered position is expressed by
            # `merge` alone.
            text = _pptx_cell_text(cell)

            if signals > 1:
                merge = MERGE_NONE
                column_span: int | None = None
                row_span: int | None = None
                table_diagnostics.append(
                    _diagnostic(
                        P2_MERGE_UNRESOLVED,
                        table_id,
                        f"r{row_index}c{cell_index} conflicting merge signals",
                    )
                )
            elif span_value is not None and span_value > 1:
                if columns is not None and column + span_value > columns:
                    column_span = None
                    row_span = 1
                    merge = MERGE_NONE
                    table_diagnostics.append(
                        _diagnostic(
                            P2_SPAN_OUT_OF_GRID,
                            table_id,
                            f"r{row_index}c{cell_index} gridSpan={span_value} "
                            f"exceeds grid columns={columns}",
                        )
                    )
                else:
                    column_span = span_value
                    row_span = 1
                    merge = MERGE_NONE
            elif h_merge == "1":
                merge = MERGE_HORIZONTAL
                row_span = 1
                # A horizontal continuation must sit under an origin in the same
                # row.  When it has none (or the row already ran past the grid),
                # the covered origin is unknown: report it exactly like an
                # over-wide `@gridSpan` instead of claiming a confirmed 1
                # (card §5.3 rule 4 covers both carriers).
                if _pptx_hmerge_overflows(
                    cells, columns, row_index, column
                ):
                    column_span = None
                    table_diagnostics.append(
                        _diagnostic(
                            P2_SPAN_OUT_OF_GRID,
                            table_id,
                            f"r{row_index}c{column} hMerge has no origin left "
                            f"within grid columns={columns}",
                        )
                    )
                else:
                    column_span = 1
            elif v_merge == "1":
                merge = MERGE_VERTICAL_CONTINUE
                column_span = 1
                row_span = 1
                if column not in origin_by_column:
                    table_diagnostics.append(
                        _diagnostic(
                            P2_MERGE_UNRESOLVED,
                            table_id,
                            f"r{row_index}c{cell_index} vertical continue "
                            "without an upper start",
                        )
                    )
            else:
                merge = MERGE_NONE
                column_span = 1
                row_span = 1

            if v_merge != "1":
                origin_by_column[column] = f"r{row_index}c{column}"

            cell_id = f"r{row_index}c{column}"
            locator = (
                f"{PPTX_LOCATOR_SCHEMA}|s={slide_number}"
                f"|p={shape_path}|c={row_index},{cell_index}"
            )
            cells.append(
                {
                    "cell_id": cell_id,
                    "row": row_index,
                    "column": column,
                    "row_span": row_span,
                    "column_span": column_span,
                    "merge": merge,
                    "locator": locator if _pptx_cell_text(cell) else None,
                    "text_refs": [],
                    "footnote_refs": [],
                    "text": text,
                }
            )
            # PresentationML keeps one `a:tc` per grid position: a spanned origin
            # declares `gridSpan` and the positions it covers keep their own
            # `hMerge="1"` cells.  The cursor therefore advances one column per
            # `a:tc`, and `column_span`/`merge` describe the coverage.
            column += 1

    # PresentationML marks only the continuation of a vertical merge (`vMerge="1"`);
    # the cell directly above an open merge is its start.
    for entry in cells:
        if entry["merge"] is not None and entry["merge"] == MERGE_NONE and entry[
            "column_span"
        ] in (1, None):
            below = next(
                (
                    candidate
                    for candidate in cells
                    if candidate["row"] == entry["row"] + 1  # type: ignore[operator]
                    and candidate["column"] == entry["column"]
                    and candidate["merge"] == MERGE_VERTICAL_CONTINUE
                ),
                None,
            )
            if below is not None:
                entry["merge"] = MERGE_VERTICAL_START

    return {
        "table_id": table_id,
        "package_part": package_part,
        "native_index": native_index,
        "grid": {"rows": len(table.rows), "columns": columns},
        "column_widths": widths or None,
        "header": {"rows": [], "source": HEADER_SOURCE_NONE},
        "cells": cells,
        "footnotes": [],
        "continuation": _empty_continuation(CONTINUATION_NOT_APPLICABLE),
        "diagnostics": table_diagnostics,
    }

def _pptx_shape_tables(shape: Any, path: tuple[int, ...], out: list[Any]) -> None:
    shape_type = getattr(shape, "shape_type", None)
    if shape_type is not None and "GROUP" in str(shape_type).upper():
        for index, member in enumerate(shape.shapes):
            _pptx_shape_tables(member, path + (index,), out)
        return
    if getattr(shape, "has_table", False):
        out.append((".".join(str(part) for part in path), shape.table))


def _parse_pptx(
    package: _Package, original: bytes, source_sha256: str, work: _Work
) -> dict[str, object]:
    module = _pptx_module()
    if module is None:
        return _finish_structure(
            format_name=FORMAT_PPTX,
            source_sha256=source_sha256,
            tables=[],
            status=STATUS_UNAVAILABLE,
            diagnostics=[
                _diagnostic(
                    DEPENDENCY_UNAVAILABLE, None, "python-pptx is not installed"
                )
            ],
            work=work,
        )
    try:
        presentation = module.Presentation(io.BytesIO(original))
    except Exception as exc:  # pragma: no cover - depends on the broken package
        raise ValueError("invalid PPTX package") from exc

    tables: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    status = STATUS_OK
    seen = 0

    for slide_number, slide in enumerate(presentation.slides, start=1):
        found: list[tuple[str, Any]] = []
        for index, shape in enumerate(slide.shapes):
            _pptx_shape_tables(shape, (index,), found)
        part = posixpath.normpath(
            str(slide.part.partname).lstrip("/")
        )
        for native_index, (shape_path, table) in enumerate(found):
            if seen >= work.limits.max_tables:
                diagnostics.append(
                    _diagnostic(
                        P2_TABLE_LIMIT, None, f"max_tables={work.limits.max_tables}"
                    )
                )
                status = STATUS_PARTIAL
                work.exhausted = True
                break
            cell_count = sum(len(row.cells) for row in table.rows)
            chars = sum(
                len(_pptx_cell_text(cell))
                for row in table.rows
                for cell in row.cells
            )
            if not work.admits_table(cell_count, chars):
                limit = (
                    "max_cells"
                    if work.cells + cell_count > work.limits.max_cells
                    else "max_text_chars"
                )
                diagnostics.append(
                    _diagnostic(
                        P2_TABLE_LIMIT, None, f"{limit} reached before table {seen}"
                    )
                )
                status = STATUS_PARTIAL
                work.exhausted = True
                break
            structure = _pptx_table_structure(
                table=table,
                table_index=work.tables,
                slide_number=slide_number,
                shape_path=shape_path,
                package_part=part,
                native_index=native_index,
            )
            work.take(cell_count, chars)
            seen += 1
            tables.append(structure)
            diagnostics.extend(structure["diagnostics"])  # type: ignore[arg-type]
            if P2_SPAN_OUT_OF_GRID in _table_codes(structure):
                status = STATUS_PARTIAL
        if work.exhausted:
            break

    return _finish_structure(
        format_name=FORMAT_PPTX,
        source_sha256=source_sha256,
        tables=tables,
        status=status,
        diagnostics=diagnostics,
        work=work,
    )


# ------------------------------------------------------------------- public API


def parse_office_tables(
    original: bytes,
    *,
    source_sha256: str,
    limits: OfficeTableLimits = OfficeTableLimits(),
) -> dict[str, object]:
    """Read the table structure of one DOCX/PPTX package.

    ``original`` is the immutable source bytes and ``source_sha256`` its verified
    digest; a mismatch raises ``ValueError("source_sha256 mismatch")`` before any
    parsing.  The format follows the package parts, not a caller-declared MIME
    type: ``word/document.xml`` means DOCX, ``ppt/presentation.xml`` means PPTX,
    and neither raises ``ValueError("unsupported_office_format")``.
    """
    if hashlib.sha256(original).hexdigest() != source_sha256:
        raise ValueError("source_sha256 mismatch")
    with _Package(original) as package:
        work = _Work(limits)
        if package.has(DOCX_MAIN_PART):
            return _parse_docx(package, source_sha256, work)
        if package.has(PPTX_MAIN_PART):
            return _parse_pptx(package, original, source_sha256, work)
        raise ValueError("unsupported_office_format")


def replay_office_tables(
    original: bytes,
    structure: Mapping[str, object],
) -> dict[str, object]:
    """Recompute ``structure`` from ``original`` and refuse any difference.

    The accepted structure must carry exactly ``cwp-office-table/1``.  The replay
    compares per cell the ``locator``, ``merge``, ``row_span``, and
    ``column_span``, then the ``structure_sha256`` over the whole table list, so
    a single edited field is always detected.
    """
    if not isinstance(structure, Mapping):
        raise ValueError("unsupported structure version")
    if structure.get("schema_version") != P2_OFFICE_TABLE_SCHEMA:
        raise ValueError("unsupported structure version")
    claimed_sha = structure.get("source_sha256")
    if not isinstance(claimed_sha, str) or not claimed_sha:
        raise ValueError("structure lacks source_sha256")
    if hashlib.sha256(original).hexdigest() != claimed_sha:
        raise ValueError("source_sha256 mismatch")

    recomputed = parse_office_tables(original, source_sha256=claimed_sha)

    claimed_tables = structure.get("tables")
    observed_tables = recomputed["tables"]
    if not isinstance(claimed_tables, list) or not isinstance(observed_tables, list):
        raise ValueError("structure tables are invalid")
    if len(claimed_tables) != len(observed_tables):
        raise ValueError(
            "replay mismatch: table count "
            f"expected {len(claimed_tables)} observed {len(observed_tables)}"
        )

    for claimed, observed in zip(claimed_tables, observed_tables, strict=True):
        if not isinstance(claimed, Mapping):
            raise ValueError("structure tables are invalid")
        table_id = observed["table_id"]
        if claimed.get("table_id") != table_id:
            raise ValueError(
                f"replay mismatch: {table_id} table_id "
                f"expected {canonical_json(claimed.get('table_id'))} "
                f"observed {canonical_json(table_id)}"
            )
        # Every table-level field is compared, not only the cells, so a changed
        # header/grid/footnotes cannot be silently recomputed away (card §5.5).
        for field in TABLE_FIELDS:
            expected = claimed.get(field)
            seen = observed[field]
            if expected != seen:
                raise ValueError(
                    f"replay mismatch: {table_id} {field} "
                    f"expected {canonical_json(expected)} "
                    f"observed {canonical_json(seen)}"
                )
        claimed_cells = claimed.get("cells")
        observed_cells = observed["cells"]
        if not isinstance(claimed_cells, list) or len(claimed_cells) != len(
            observed_cells
        ):
            raise ValueError(
                f"replay mismatch: {table_id} cells "
                f"expected {len(claimed_cells) if isinstance(claimed_cells, list) else 'invalid'} "
                f"observed {len(observed_cells)}"  # type: ignore[arg-type]
            )
        for claimed_cell, observed_cell in zip(
            claimed_cells, observed_cells, strict=True
        ):
            if not isinstance(claimed_cell, Mapping):
                raise ValueError(f"replay mismatch: {table_id} cell is invalid")
            cell_id = observed_cell["cell_id"]  # type: ignore[index]
            if claimed_cell.get("cell_id") != cell_id:
                raise ValueError(
                    f"replay mismatch: {table_id} {cell_id} cell_id "
                    f"expected {canonical_json(claimed_cell.get('cell_id'))} "
                    f"observed {canonical_json(cell_id)}"
                )
            for field in CELL_FIELDS:
                expected = claimed_cell.get(field)
                seen = observed_cell[field]  # type: ignore[index]
                if expected != seen:
                    raise ValueError(
                        f"replay mismatch: {table_id} {cell_id} {field} "
                        f"expected {canonical_json(expected)} "
                        f"observed {canonical_json(seen)}"
                    )

    # Backstop, deliberately last: the field comparisons above name the culprit,
    # so this only fires when the supplied tables differ in some field this
    # version does not know about (a future key, a dropped key).  It never
    # replaces the precise message.
    claimed_hash = structure.get("structure_sha256")
    if claimed_hash != _sha256(canonical_json(claimed_tables).encode("utf-8")):
        raise ValueError(
            "replay mismatch: structure_sha256 does not match the supplied tables "
            f"expected {canonical_json(claimed_hash)} "
            f"observed {canonical_json(_sha256(canonical_json(claimed_tables).encode('utf-8')))}"
        )
    observed_hash = recomputed["structure_sha256"]
    if claimed_hash != observed_hash:
        raise ValueError(
            "replay mismatch: structure_sha256 "
            f"expected {canonical_json(claimed_hash)} "
            f"observed {canonical_json(observed_hash)}"
        )
    return recomputed


__all__ = [
    "OfficeTableLimits",
    "P2_OFFICE_TABLE_SCHEMA",
    "P2_OFFICE_TABLE_VERSION",
    "PARSER_NAME",
    "canonical_json",
    "parse_office_tables",
    "replay_office_tables",
]
