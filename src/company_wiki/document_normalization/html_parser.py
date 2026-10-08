"""Deterministic HTML normalization with versioned DOM-path locators.

Locator schema ``cwp-html-dom/1``: ``cwp-html-dom/1|n=<dotted element-child
indexes>`` where the indexes count only element children along the path from
``html`` to the owning element.  The same path plus the same parser version
must reproduce the same unit text, so replay verifies both.

Core rules (fixed by the construction card):

- Parse from actual bytes with an explicit encoding strategy; never fetch
  anything (no JS, no CSS, no images).
- Text ownership: a visible text string belongs to its nearest block-owner
  ancestor (``p``, ``div``, ``li``, ``td``, ...).  Owner text excludes text
  owned by deeper owners, so nested nodes are never double-counted, while the
  same text appearing at two locations yields two independent units.  Loose
  text directly inside ``body`` or inside block containers is attributed to
  the nearest owner rather than silently dropped.
- Excluded: ``script``/``style``/``head``/``nav``/``header``/``footer``/
  ``aside``/``template``/``noscript`` subtrees and explicitly hidden elements
  (``hidden`` attribute, ``aria-hidden="true"``, ``display:none`` /
  ``visibility:hidden`` inline styles, ``hidden``/``ix-hidden`` classes,
  inline-XBRL hidden facts).  Visible inline-XBRL body text is retained.
  Inline SVG is a named opaque gap, never transcribed text.
- Tables: every visible table cell (``td``/``th``) becomes one unit with
  stable ``table_index``/``row_index``/``column_index`` coordinates.  Tables
  are flagged ``financial`` (with matched-term evidence) or ``unknown`` for
  MAIN to route; the parser never drops business tables.
"""

from __future__ import annotations

import hashlib
import re
import sys
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

from company_wiki.source_contract.evidence_span import EvidenceCoordinates

from .assets import GAP_SVG_NOT_TRANSCRIBED, OpaqueAsset
from .document import NormalizedDocument
from .errors import (
    NormalizationLimitError,
    UnsupportedFormatError,
)
from .limits import NormalizationLimits
from .text import normalize_text
from .units import (
    FORMAT_HTML,
    HTML_LOCATOR_SCHEMA,
    build_unit,
)

BACKEND = "html.parser"
TRANSFORM = "html_visible_text_v1"

SUPPORTED_MIME_TYPES = frozenset({"text/html", "application/xhtml+xml"})

EXCLUDE_TAGS = frozenset(
    {
        "script", "style", "template", "noscript", "head", "nav", "header",
        "footer", "aside", "link", "meta", "title", "iframe", "frame",
        "frameset", "option", "select", "datalist", "dialog", "base",
    }
)

OWNER_TAGS = frozenset(
    {
        "p", "div", "li", "dt", "dd", "blockquote", "pre", "figcaption",
        "caption", "td", "th", "section", "article", "main", "body", "html",
        "h1", "h2", "h3", "h4", "h5", "h6", "address",
    }
)

# Block containers that never own text themselves: scan() descends them to
# find owners, and their loose strings fall back to the nearest outer owner.
BLOCK_NON_OWNER_TAGS = frozenset(
    {
        "table", "thead", "tbody", "tfoot", "tr", "colgroup", "col",
        "ul", "ol", "dl", "form", "fieldset", "details", "summary",
        "figure", "center", "optgroup", "video", "audio", "canvas",
        "object", "embed", "map", "picture", "source", "button",
    }
)

HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})

_HIDDEN_STYLE_RE = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden", re.IGNORECASE
)
_HIDDEN_CLASSES = frozenset({"hidden", "ix-hidden", "ix_hidden"})
_META_CHARSET_RE = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9_.:-]+)""",
    re.IGNORECASE,
)
_BOMS = (
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\x00\x00\xfe\xff", "utf-32-be"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
)
_FALLBACK_ENCODING = "windows-1252"

_FINANCIAL_TERMS = re.compile(
    r"revenue|net\s+income|operating\s+income|gross\s+margin|earnings|eps\b"
    r"|fiscal\s+year|in\s+millions|in\s+thousands|\$|€|£"
    r"|营业[收额]|净利[润额]|毛利|每股[收益]|百万|万元|亿元",
    re.IGNORECASE,
)

_UNIT_KINDS = {
    "heading": "html_heading",
    "paragraph": "html_paragraph",
    "list_item": "html_list_item",
    "table_cell": "html_table_cell",
    "footnote": "html_footnote",
}

_MAX_RECURSION = 30_000


def decode_html_bytes(data: bytes) -> tuple[str, str, str, bool]:
    """Decode HTML bytes with a deterministic, fully offline strategy.

    Returns ``(text, encoding_used, strategy, encoding_repaired)``.
    """
    if not isinstance(data, bytes):
        raise TypeError("HTML data must be bytes")
    if not data:
        return "", "utf-8", "empty_input", False
    for bom, encoding in _BOMS:
        if data.startswith(bom):
            try:
                return data.decode(encoding), encoding, "bom", False
            except UnicodeDecodeError:  # pragma: no cover - BOM implies validity
                break
    declared = None
    match = _META_CHARSET_RE.search(data[:4096])
    if match:
        candidate = match.group(1).decode("ascii", "replace").strip().lower()
        if candidate:
            declared = candidate
    if declared:
        try:
            return data.decode(declared), declared, "meta_charset", False
        except (UnicodeDecodeError, LookupError):
            pass
    try:
        return data.decode("utf-8"), "utf-8", "utf8_strict", False
    except UnicodeDecodeError:
        return (
            data.decode(_FALLBACK_ENCODING, "replace"),
            _FALLBACK_ENCODING,
            "fallback_repair",
            True,
        )


def _element_children(tag: Any) -> list[Tag]:
    return [child for child in tag.children if isinstance(child, Tag)]


def _is_hidden(tag: Tag) -> bool:
    attrs = tag.attrs
    if attrs.get("hidden") is not None:
        return True
    if str(attrs.get("aria-hidden", "")).strip().lower() == "true":
        return True
    style = attrs.get("style")
    if isinstance(style, str) and _HIDDEN_STYLE_RE.search(style):
        return True
    classes = attrs.get("class")
    if classes:
        tokens = classes if isinstance(classes, list) else classes.split()
        if any(str(token).lower() in _HIDDEN_CLASSES for token in tokens):
            return True
    return False


def _unit_kind_for(tag: Tag) -> str:
    identity = " ".join(
        [str(tag.get("id") or "")] + [str(c) for c in (tag.get("class") or [])]
    ).lower()
    if "footnote" in identity:
        return _UNIT_KINDS["footnote"]
    if tag.name in HEADING_TAGS:
        return _UNIT_KINDS["heading"]
    if tag.name == "li":
        return _UNIT_KINDS["list_item"]
    if tag.name in {"td", "th"}:
        return _UNIT_KINDS["table_cell"]
    return _UNIT_KINDS["paragraph"]


def _classify_table(table: Tag) -> tuple[str, tuple[str, ...]]:
    """Flag a table ``financial`` or ``unknown``; MAIN makes the final call."""
    rows = table.find_all("tr", recursive=True)
    texts: list[str] = []
    for row in rows[:2]:
        for cell in row.find_all(["td", "th"], recursive=False):
            texts.append(cell.get_text(" ", strip=True))
    header_text = " ".join(texts)
    matches = tuple(
        sorted({m.group(0).lower() for m in _FINANCIAL_TERMS.finditer(header_text)})
    )
    if matches:
        return "financial", matches
    table_text = table.get_text(" ", strip=True)[:4000]
    matches = tuple(
        sorted({m.group(0).lower() for m in _FINANCIAL_TERMS.finditer(table_text)})
    )
    if matches:
        return "financial", matches
    return "unknown", ()


class _HtmlScanState:
    def __init__(
        self,
        *,
        source_id: str,
        source_sha256: str,
        limits: NormalizationLimits,
        encoding_used: str,
        encoding_strategy: str,
        encoding_repaired: bool,
    ) -> None:
        self.source_id = source_id
        self.source_sha256 = source_sha256
        self.limits = limits
        self.encoding_used = encoding_used
        self.encoding_strategy = encoding_strategy
        self.encoding_repaired = encoding_repaired
        self.units: list[Any] = []
        self.assets: list[OpaqueAsset] = []
        self.errors: list[str] = []
        self.text_bytes = 0
        self.element_count = 0
        self.skipped_hidden = 0
        self.table_index_by_id: dict[int, int] = {}
        self.table_classes: dict[int, tuple[str, tuple[str, ...]]] = {}
        self.visible_tables: list[Tag] = []
        # Per-table row lists and per-row cell lists, computed once per
        # table/row and reused by every cell coordinate lookup.
        self.table_rows_by_id: dict[int, list[Tag]] = {}
        self.row_cells_by_id: dict[int, list[Tag]] = {}

    def check_deadline(self, where: str) -> None:
        self.limits.check_deadline(f"html:{where}")


def _collect_visible(tag: Tag, state: _HtmlScanState, path: tuple[int, ...]) -> None:
    """Pre-pass: number visible tables and locate inline SVG gaps."""
    for index, child in enumerate(_element_children(tag)):
        state.check_deadline("prepass")
        child_path = path + (index,)
        if child.name in EXCLUDE_TAGS or _is_hidden(child):
            continue
        if child.name == "svg":
            state.assets.append(
                OpaqueAsset(
                    asset_kind="svg",
                    slide_number=None,
                    shape_path=".".join(str(p) for p in child_path),
                    gap_reason=GAP_SVG_NOT_TRANSCRIBED,
                )
            )
            continue
        if child.name == "table":
            state.table_index_by_id[id(child)] = len(state.visible_tables)
            state.visible_tables.append(child)
        state.element_count += 1
        _collect_visible(child, state, child_path)


def _inline_text(tag: Tag) -> str:
    """Text of a transparent inline subtree, stopping at owners and blocks."""
    parts: list[str] = []
    for child in tag.children:
        if isinstance(child, NavigableString):
            normalized = normalize_text(str(child))
            if normalized:
                parts.append(normalized)
        elif isinstance(child, Tag):
            if (
                child.name in OWNER_TAGS
                or child.name in BLOCK_NON_OWNER_TAGS
                or child.name in EXCLUDE_TAGS
                or _is_hidden(child)
            ):
                continue
            inner = _inline_text(child)
            if inner:
                parts.append(inner)
    return normalize_text(" ".join(parts))


def _direct_strings(owner: Tag) -> list[str]:
    """Strings the owner holds outside any deeper owner or block container."""
    collected: list[str] = []
    for child in owner.children:
        if isinstance(child, NavigableString):
            normalized = normalize_text(str(child))
            if normalized:
                collected.append(normalized)
        elif isinstance(child, Tag):
            if (
                child.name in OWNER_TAGS
                or child.name in BLOCK_NON_OWNER_TAGS
                or child.name in EXCLUDE_TAGS
                or _is_hidden(child)
                or child.name == "svg"
            ):
                continue
            inner = _inline_text(child)
            if inner:
                collected.append(inner)
    return collected


def _table_rows(table: Tag, state: _HtmlScanState) -> list[Tag]:
    cached = state.table_rows_by_id.get(id(table))
    if cached is not None:
        return cached
    rows = [
        candidate
        for candidate in table.find_all("tr", recursive=True)
        if candidate.find_parent("table") is table
    ]
    state.table_rows_by_id[id(table)] = rows
    return rows


def _row_cells(row: Tag, state: _HtmlScanState) -> list[Tag]:
    cached = state.row_cells_by_id.get(id(row))
    if cached is not None:
        return cached
    cells = [c for c in row.find_all(["td", "th"], recursive=False) if isinstance(c, Tag)]
    state.row_cells_by_id[id(row)] = cells
    return cells


def _cell_coordinates(cell: Tag, state: _HtmlScanState) -> tuple[int, int, int] | None:
    table = cell.find_parent("table")
    if table is None:
        return None
    table_index = state.table_index_by_id.get(id(table))
    if table_index is None:
        return None
    row = cell.find_parent("tr")
    rows = _table_rows(table, state)
    row_index = rows.index(row) if row in rows else 0
    siblings = _row_cells(row, state) if row is not None else []
    column_index = siblings.index(cell) if cell in siblings else 0
    return table_index, row_index, column_index


def _emit(
    state: _HtmlScanState,
    *,
    owner: Tag,
    path: tuple[int, ...],
    text: str,
    unit_kind: str,
) -> None:
    limits = state.limits
    if len(state.units) >= limits.max_units:
        raise NormalizationLimitError(
            "max_units", limits.max_units, "html block emission"
        )
    text_bytes = len(text.encode("utf-8"))
    if state.text_bytes + text_bytes > limits.max_text_output_bytes:
        raise NormalizationLimitError(
            "max_text_output_bytes",
            limits.max_text_output_bytes,
            f"at html node {'.'.join(map(str, path))}",
        )
    state.text_bytes += text_bytes
    locator_path = ".".join(str(p) for p in path)
    source_locator = f"{HTML_LOCATOR_SCHEMA}|n={locator_path}"
    extra: dict[str, Any] = {"dom_path": locator_path, "backend": BACKEND}
    coordinates: EvidenceCoordinates
    if unit_kind == _UNIT_KINDS["table_cell"]:
        cell_coords = _cell_coordinates(owner, state)
        if cell_coords is None:  # pragma: no cover - prepass numbers all tables
            return
        table_index, row_index, column_index = cell_coords
        table_class, basis = state.table_classes[table_index]
        extra["table_index"] = table_index
        extra["row_index"] = row_index
        extra["column_index"] = column_index
        extra["table_class"] = table_class
        extra["table_class_basis"] = basis
        coordinates = EvidenceCoordinates(
            table_index=table_index, row_index=row_index, column_index=column_index
        )
    else:
        coordinates = EvidenceCoordinates(paragraph_index=len(state.units))
    state.units.append(
        build_unit(
            source_id=state.source_id,
            source_sha256=state.source_sha256,
            format_name=FORMAT_HTML,
            coordinates=coordinates,
            raw_text=text,
            unit_kind=unit_kind,
            source_locator=source_locator,
            transform=TRANSFORM,
            extra_metadata=extra,
            quality_flags=(
                ("encoding_repaired",) if state.encoding_repaired else ()
            ),
        )
    )


def _scan_children(
    node: Any, state: _HtmlScanState, node_path: tuple[int, ...], own_parts: list[str]
) -> None:
    """Collect this owner's strings in document order; emit deeper owners.

    Transparent inline elements and block containers both recurse: every
    string lands on its nearest block owner exactly once, and each owner
    descendant emits its own separate unit through ``_walk_owner``.  Table
    cells are special: their whole body belongs to the cell unit, so they
    dispatch to ``_walk_cell`` instead.
    """
    state.check_deadline("walk")
    index = 0
    for child in node.children:
        if isinstance(child, NavigableString):
            normalized = normalize_text(str(child))
            if normalized:
                own_parts.append(normalized)
            continue
        if not isinstance(child, Tag):
            continue
        child_path = node_path + (index,)
        index += 1
        if child.name in EXCLUDE_TAGS:
            continue
        if _is_hidden(child):
            state.skipped_hidden += 1
            continue
        if child.name == "svg":
            continue  # registered as an opaque gap in the prepass
        if child.name in {"td", "th"}:
            _walk_cell(child, state, child_path)
        elif child.name in OWNER_TAGS:
            _walk_owner(child, state, child_path)
        else:
            _scan_children(child, state, child_path, own_parts)


def _scan_cell_body(
    cell: Any, state: _HtmlScanState, node_path: tuple[int, ...], own_parts: list[str]
) -> None:
    """Collect a cell's whole visible body; nested tables keep their cells."""
    state.check_deadline("cell")
    index = 0
    for child in cell.children:
        if isinstance(child, NavigableString):
            normalized = normalize_text(str(child))
            if normalized:
                own_parts.append(normalized)
            continue
        if not isinstance(child, Tag):
            continue
        child_path = node_path + (index,)
        index += 1
        if child.name in EXCLUDE_TAGS:
            continue
        if _is_hidden(child):
            state.skipped_hidden += 1
            continue
        if child.name == "svg":
            continue
        if child.name == "table":
            # Loose text in the nested table still belongs to this cell;
            # its own td/th dispatch to their own cell units.
            _scan_children(child, state, child_path, own_parts)
        else:
            # Paragraphs, divs, lists inside a cell are formatting wrappers:
            # their text belongs to the cell, not to separate paragraph units.
            _scan_cell_body(child, state, child_path, own_parts)


def _walk_cell(cell: Any, state: _HtmlScanState, path: tuple[int, ...]) -> str:
    """Emit the table-cell unit owning every string in the cell body."""
    own_parts: list[str] = []
    _scan_cell_body(cell, state, path, own_parts)
    text = normalize_text(" ".join(own_parts))
    if not text:
        return ""
    _emit(
        state, owner=cell, path=path, text=text, unit_kind=_UNIT_KINDS["table_cell"]
    )
    return text


def _walk_owner(owner: Any, state: _HtmlScanState, path: tuple[int, ...]) -> str:
    """Emit the unit owned by ``owner``; return its own visible text.

    The unit text contains only strings whose nearest block owner is this
    element — never the text of deeper owners, which emit their own units —
    so nested nodes are never double-counted.  ``html`` aggregates only and
    never becomes a unit itself.
    """
    if owner.name in EXCLUDE_TAGS:
        return ""
    own_parts: list[str] = []
    _scan_children(owner, state, path, own_parts)
    text = normalize_text(" ".join(own_parts))
    if not text:
        return ""
    if owner.name == "html":
        return text
    _emit(
        state, owner=owner, path=path, text=text, unit_kind=_unit_kind_for(owner)
    )
    return text


def parse_html(
    data: bytes,
    *,
    source_id: str,
    source_sha256: str,
    mime_type: str,
    limits: NormalizationLimits,
) -> NormalizedDocument:
    """Normalize one verified HTML document into narrative units."""
    if not isinstance(data, bytes):
        raise TypeError("HTML data must be bytes")
    mime_main = mime_type.split(";")[0].strip().lower()
    if mime_main not in SUPPORTED_MIME_TYPES:
        raise UnsupportedFormatError(
            f"mime_type {mime_type!r} is not an HTML document type"
        )
    if len(data) > limits.max_source_bytes:
        raise NormalizationLimitError(
            "max_source_bytes", limits.max_source_bytes, f"got {len(data)}"
        )
    if hashlib.sha256(data).hexdigest() != source_sha256:
        raise ValueError("HTML bytes do not match source_sha256")
    text, encoding_used, encoding_strategy, encoding_repaired = decode_html_bytes(
        data
    )
    state = _HtmlScanState(
        source_id=source_id,
        source_sha256=source_sha256,
        limits=limits,
        encoding_used=encoding_used,
        encoding_strategy=encoding_strategy,
        encoding_repaired=encoding_repaired,
    )
    document = BeautifulSoup(text, BACKEND)
    state.check_deadline("parse")
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old_limit, _MAX_RECURSION))
    try:
        if document.html is not None:
            root = document.html
            root_path = (0,)
        else:
            root = document
            root_path = ()
            # Fragment or non-HTML bytes declared as HTML: parse anyway,
            # flag the missing root so the result is not an empty success.
            state.errors.append("no_html_root")
        _collect_visible(root, state, root_path)
        for table in state.visible_tables:
            state.table_classes[
                state.table_index_by_id[id(table)]
            ] = _classify_table(table)
        _walk_owner(root, state, root_path)
    finally:
        sys.setrecursionlimit(old_limit)
    if not state.units:
        state.errors.append("no_visible_text_blocks")
    from company_wiki.source_catalog.narrative_document import DocumentStructure

    structure = DocumentStructure(
        source_id=state.source_id,
        source_sha256=state.source_sha256,
        language="und",
        units=tuple(state.units),
        page_count=0,
        pages_read=0,
        opaque_pages=(),
        table_scan_pages=(),
        deferred_table_pages=(),
        line_count=len(state.units),
        errors=tuple(state.errors),
    )
    metadata: dict[str, Any] = {
        "encoding_used": encoding_used,
        "encoding_strategy": encoding_strategy,
        "encoding_repaired": encoding_repaired,
        "backend": BACKEND,
        "element_count": state.element_count,
        "visible_table_count": len(state.visible_tables),
        "skipped_hidden_count": state.skipped_hidden,
    }
    return NormalizedDocument(
        source_id=state.source_id,
        source_sha256=state.source_sha256,
        format_name=FORMAT_HTML,
        parser_name="cwp_document_normalization",
        parser_version="1.0.0",
        structure=structure,
        opaque_assets=tuple(state.assets),
        metadata=metadata,
    )


__all__ = [
    "BACKEND",
    "SUPPORTED_MIME_TYPES",
    "TRANSFORM",
    "decode_html_bytes",
    "parse_html",
]
