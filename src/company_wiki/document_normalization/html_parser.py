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

import re
from collections.abc import Iterator
from dataclasses import replace
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Comment, NavigableString, Tag

from company_wiki.source_contract.evidence_span import EvidenceCoordinates

from ._source_input import _NormalizationSource
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


def _element_children(tag: Tag) -> Iterator[Tag]:
    return (child for child in tag.children if isinstance(child, Tag))


def _is_hidden(tag: Tag) -> bool:
    if tag.name == "ix:hidden":
        return True
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
        # One actual native fact may cross several text owners. Preserve all
        # their refs so the existing collector can diagnose split ownership.
        self.document_type_facts: dict[int, dict[str, Any]] = {}
        self.native_tables: list[dict[str, Any]] = []
        self.native_cells: dict[int, dict[str, Any]] = {}
        self.legacy_cell_coordinates: dict[int, tuple[int, int, int]] = {}
        self.native_cell_count = 0

    def check_deadline(self, where: str) -> None:
        self.limits.check_deadline(f"html:{where}")

    def document_type_fact(self, node: Any, active: int | None) -> int | None:
        if (
            isinstance(node, Tag)
            and node.name == "ix:nonnumeric"
            and str(node.get("name", "")).casefold() == "dei:documenttype"
        ):
            key = id(node)
            self.document_type_facts.setdefault(
                key, {"concept": node.get("name"), "refs": []}
            )
            return key
        return active


class _OwnedText(list[str]):
    """Observe offsets while the existing visible owner text is accumulated."""

    def __init__(self) -> None:
        super().__init__()
        self.length = 0
        self.fact_ranges: dict[int, list[tuple[int, int]]] = {}
        self.has_link = False
        self.fragments: list[tuple[int, int]] = []

    def observe(self, text: str, native_fact: int | None) -> None:
        start = self.length + bool(self)
        self.append(text)
        self.length = start + len(text)
        self.fragments.append((start, self.length))
        if native_fact is not None:
            ranges = self.fact_ranges.setdefault(native_fact, [])
            if ranges and ranges[-1][1] + 1 == start:
                # The normalized owner inserts this actual separating space;
                # include it rather than inventing a joined form token.
                ranges[-1] = (ranges[-1][0], self.length)
            else:
                ranges.append((start, self.length))


_OWN_FORM_LABEL = re.compile(
    r"FORM[\s:：]+[A-Z]{0,2}\d{0,3}-[A-Z0-9]{1,3}(?:/[A-Z0-9]{1,3})?",
    re.IGNORECASE,
)


def _attach_carriers(
    state: _HtmlScanState, index: int, carriers: list[dict[str, Any]]
) -> None:
    unit = state.units[index]
    view = dict(unit.metadata.get("native_source_view", {}))
    view["carriers"] = [*view.get("carriers", []), *carriers]
    state.units[index] = replace(
        unit, metadata={**unit.metadata, "native_source_view": view}
    )


def _attach_document_type_facts(state: _HtmlScanState) -> None:
    by_owner: dict[int, list[dict[str, Any]]] = {}
    for fact in state.document_type_facts.values():
        state.check_deadline("form_carriers")
        ranges = fact["refs"]
        if not ranges:
            continue  # An attribute/value with no original visible text is unknown.
        indices = list(dict.fromkeys(index for index, _, _ in ranges))
        by_owner.setdefault(indices[0], []).append(
            {
                "kind": "visible_inline_xbrl_document_type",
                "unit_ids": [state.units[index].unit_id for index in indices],
                "parent_id": state.source_id,
                "value_refs": [
                    {"unit_id": state.units[index].unit_id, "char_start": start, "char_end": end}
                    for index, start, end in ranges
                ],
                "attributes": {"concept": fact["concept"], "visibility": "visible"},
            },
        )
    # One owner can contain many inline facts: do not repeatedly copy its
    # growing carrier list and materialize a new NarrativeUnit per fact.
    for index, carriers in by_owner.items():
        state.check_deadline("form_carriers")
        _attach_carriers(state, index, carriers)


def _collect_visible(tag: Tag, state: _HtmlScanState, root_path: tuple[int, ...]) -> None:
    """Pre-pass: number visible tables and locate inline SVG gaps."""
    path = list(root_path)
    stack = [enumerate(_element_children(tag))]
    while stack:
        item = next(stack[-1], None)
        if item is None:
            stack.pop()
            if stack:
                path.pop()
            continue
        index, child = item
        state.check_deadline("prepass")
        if child.name in EXCLUDE_TAGS or _is_hidden(child):
            continue
        if child.name == "svg":
            state.assets.append(
                OpaqueAsset(
                    asset_kind="svg",
                    slide_number=None,
                    shape_path=".".join(map(str, (*path, index))),
                    gap_reason=GAP_SVG_NOT_TRANSCRIBED,
                )
            )
            continue
        if child.name == "table":
            state.table_index_by_id[id(child)] = len(state.visible_tables)
            state.visible_tables.append(child)
        state.element_count += 1
        path.append(index)
        stack.append(enumerate(_element_children(child)))


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
    if id(cell) in state.legacy_cell_coordinates:
        return state.legacy_cell_coordinates[id(cell)]
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


def _native_span(cell: Tag, name: str, remaining_rows: int) -> int | None:
    value = cell.get(name)
    if value is None:
        return 1
    value = str(value).strip()
    if not value.isascii() or not value.isdecimal() or len(value) > 6:
        return None
    number = int(value)
    if name == 'rowspan' and number == 0:
        return remaining_rows
    return number if number > 0 else None


def _native_table_grid(table: Tag, state: _HtmlScanState) -> None:
    """Cache native slots once; legacy sibling coordinates remain untouched.

    Invisible cells have no observed value. Keeping their explicit DOM slots
    unavailable avoids moving a neighbouring value into their column. This is
    native DOM provenance, not inferred PDF/browser-rendered geometry.
    """
    index = state.table_index_by_id[id(table)]
    rows = _table_rows(table, state)
    grid: dict[str, Any] = {'scope': {'parent_id': state.source_id,
        'table_id': f'html:t{index}', 'page': None}, 'cells': [],
        'header_rows': [], 'context_refs': [], 'position_complete': True}
    active: list[tuple[int, int, int]] = []
    group_first: dict[int, int] = {}
    group_remaining: dict[int, int] = {}
    for row_index, row in enumerate(rows):
        state.check_deadline('table_grid')
        key = id(row.parent)
        group_first.setdefault(key, row_index)
        group_remaining[key] = group_remaining.get(key, 0) + 1
    for row_index, row in enumerate(rows):
        state.check_deadline('table_grid')
        active = [slot for slot in active if slot[0] > row_index]
        occupied = sorted(active, key=lambda slot: slot[1])
        slot_index = 0
        cells = _row_cells(row, state)
        group = row.parent
        remaining = group_remaining[id(group)]
        group_remaining[id(group)] -= 1
        column = 0
        row_cells = []
        for sibling_index, cell in enumerate(cells):
            state.check_deadline('table_grid')
            if state.native_cell_count >= state.limits.max_units:
                raise NormalizationLimitError('max_units', state.limits.max_units, 'html native table slots')
            state.native_cell_count += 1
            while slot_index < len(occupied):
                _end_row, start, end = occupied[slot_index]
                if end <= column:
                    slot_index += 1
                elif start <= column:
                    column = end
                    slot_index += 1
                else:
                    break
            row_span = _native_span(cell, 'rowspan', remaining)
            column_span = _native_span(cell, 'colspan', remaining)
            if row_span is None or column_span is None:
                grid['position_complete'] = False
            current: Any = cell
            visible = True
            while current is not table:
                if current.name in EXCLUDE_TAGS or _is_hidden(current):
                    visible = False
                    break
                current = current.parent
            scope = str(cell.get('scope') or '').casefold()
            raw_headers = cell.get('headers')
            headers = (raw_headers.split() if isinstance(raw_headers, str)
                       else list(raw_headers) if isinstance(raw_headers, list) else [])
            descriptor = {'cell_id': f'html:t{index}:r{row_index}:c{sibling_index}',
                'row': row_index, 'column': column, 'row_span': row_span,
                'column_span': column_span, 'presence': 'unavailable',
                'text_refs': [], 'fragment_refs': [], 'is_header': cell.name == 'th',
                'header_scope': scope if scope in {'row','rowgroup','col','colgroup'} else None,
                'html_id': cell.get('id'), 'headers': list(headers),
                'row_group': group_first[id(group)], 'visible': visible}
            grid['cells'].append(descriptor)
            row_cells.append(descriptor)
            state.native_cells[id(cell)] = descriptor
            state.legacy_cell_coordinates[id(cell)] = (index, row_index, sibling_index)
            if (row_span or 1) > 1:
                active.append((row_index + (row_span or 1), column, column + (column_span or 1)))
            column += column_span or 1
        visible_cells = [cell for cell in row_cells if cell['visible']]
        native_head = row.find_parent('thead')
        if (native_head is not None and native_head.find_parent('table') is table) or (
            visible_cells and all(cell['is_header'] and cell['header_scope'] not in {'row','rowgroup'}
                                  for cell in visible_cells)):
            grid['header_rows'].append(row_index)
    state.native_tables.append(grid)


def _attach_native_tables(state: _HtmlScanState) -> None:
    if not state.native_tables or not state.units:
        return  # No visible owner means unavailable, never a fabricated unit.
    for table in state.native_tables:
        for cell in table['cells']:
            cell.pop('visible')
            if not table['position_complete'] and cell['presence'] == 'present':
                cell['presence'] = 'merged_unknown'
    unit = state.units[0]
    view = {**unit.metadata.get('native_source_view', {}), 'tables': state.native_tables}
    state.units[0] = replace(unit, metadata={**unit.metadata, 'native_source_view': view})


def _emit(
    state: _HtmlScanState,
    *,
    owner: Tag,
    path: tuple[int, ...],
    text: str,
    unit_kind: str,
    observed: _OwnedText,
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
    if unit_kind == _UNIT_KINDS["heading"] and re.fullmatch(r"h[1-6]", owner.name or ""):
        extra["tag_name"] = owner.name
        extra["heading_level"] = int(owner.name[1])
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
    index = len(state.units) - 1
    unit_id = state.units[index].unit_id
    native_cell = state.native_cells.get(id(owner))
    if native_cell is not None:
        native_cell['presence'] = 'present'
        native_cell['text_refs'] = [{'unit_id': unit_id, 'char_start': 0, 'char_end': len(text)}]
        native_cell['fragment_refs'] = [
            {'unit_id': unit_id, 'char_start': start, 'char_end': end}
            for start, end in observed.fragments]
    caption = owner if owner.name == 'caption' else owner.find_parent('caption')
    if caption is not None:
        table = caption.find_parent('table')
        if table is not None and id(table) in state.table_index_by_id:
            state.native_tables[state.table_index_by_id[id(table)]]['context_refs'].append(
                {'unit_id': unit_id, 'char_start': 0, 'char_end': len(text)})
    for fact, ranges in observed.fact_ranges.items():
        state.document_type_facts[fact]["refs"].extend(
            (index, start, end) for start, end in ranges
        )
    if not observed.has_link and _OWN_FORM_LABEL.fullmatch(text):
        _attach_carriers(
            state, index,
            [{"kind": "visible_own_form_label", "unit_ids": [unit_id],
             "parent_id": state.source_id,
             "value_refs": [{"unit_id": unit_id, "char_start": 0, "char_end": len(text)}],
             "attributes": {"visibility": "visible"}}],
        )


class _TextFrame:
    def __init__(
        self, node: Tag, state: _HtmlScanState, *, owns_text: bool, in_cell: bool,
        parent: _TextFrame | None = None,
    ) -> None:
        state.check_deadline("cell" if in_cell else "walk")
        self.node = node
        self.children = iter(node.children)
        self.element_index = 0
        self.owns_text = owns_text
        self.in_cell = in_cell
        self.parts: _OwnedText = _OwnedText() if owns_text or parent is None else parent.parts
        self.native_fact: int | None = state.document_type_fact(
            node, None if parent is None else parent.native_fact,
        )
        self.linked: bool = (parent is not None and parent.linked) or (
            node.name == "a" and bool(node.get("href"))
        )
        self.parts.has_link |= self.linked

    def emit(self, state: _HtmlScanState, path: tuple[int, ...]) -> None:
        if self.node.name == "html":
            return
        text = normalize_text(" ".join(self.parts))
        if text:
            _emit(
                state, owner=self.node, path=path, text=text,
                unit_kind=_unit_kind_for(self.node), observed=self.parts,
            )
        elif id(self.node) in state.native_cells:
            state.native_cells[id(self.node)]["presence"] = "empty"


def _walk_visible_text(root: Tag, state: _HtmlScanState, root_path: tuple[int, ...]) -> None:
    """Walk visible owners in post-order without changing the process stack."""
    if root.name in EXCLUDE_TAGS or _is_hidden(root):
        return
    path = list(root_path)
    stack = [_TextFrame(root, state, owns_text=True, in_cell=False)]
    while stack:
        frame = stack[-1]
        child = next(frame.children, None)
        if child is None:
            if frame.owns_text:
                frame.emit(state, tuple(path))
            stack.pop()
            if stack:
                path.pop()
            continue
        if isinstance(child, Comment):
            continue
        if isinstance(child, NavigableString):
            text = normalize_text(str(child))
            if text:
                frame.parts.observe(text, frame.native_fact)
            continue
        if not isinstance(child, Tag):
            continue
        index = frame.element_index
        frame.element_index += 1
        if child.name in EXCLUDE_TAGS:
            continue
        if _is_hidden(child):
            state.skipped_hidden += 1
            continue
        if child.name == "svg":
            continue  # The pre-pass records the opaque asset.
        # Wrappers inside a cell share that cell's text. A nested table
        # starts a fresh table scope, so its cells own their own text again.
        cell_wrapper = frame.in_cell and child.name != "table"
        path.append(index)
        stack.append(
            _TextFrame(
                child, state,
                owns_text=not cell_wrapper and child.name in OWNER_TAGS,
                in_cell=cell_wrapper or child.name in {"td", "th"},
                parent=frame,
            )
        )


def parse_html(
    data: bytes,
    *,
    source_id: str,
    source_sha256: str,
    mime_type: str,
    limits: NormalizationLimits,
) -> NormalizedDocument:
    """Verify raw HTML bytes and normalize them into narrative units."""
    mime_main = mime_type.split(";")[0].strip().lower()
    if mime_main not in SUPPORTED_MIME_TYPES:
        raise UnsupportedFormatError(
            f"mime_type {mime_type!r} is not an HTML document type"
        )
    source = _NormalizationSource.from_bytes(
        data, source_id=source_id, source_sha256=source_sha256, limits=limits,
    )
    return _parse_html(source, limits=limits)


def _parse_html(source: _NormalizationSource, *, limits: NormalizationLimits) -> NormalizedDocument:
    text, encoding_used, encoding_strategy, encoding_repaired = decode_html_bytes(
        source.data
    )
    state = _HtmlScanState(
        source_id=source.source_id,
        source_sha256=source.source_sha256,
        limits=limits,
        encoding_used=encoding_used,
        encoding_strategy=encoding_strategy,
        encoding_repaired=encoding_repaired,
    )
    document = BeautifulSoup(text, BACKEND)
    state.check_deadline("parse")
    root_path: tuple[int, ...]
    if document.html is not None:
        root = document.html
        root_path = (0,)
    else:
        root = document
        root_path = ()
        # A fragment can have readable text while lacking the complete root.
        state.errors.append("no_html_root")
    _collect_visible(root, state, root_path)
    for table in state.visible_tables:
        state.table_classes[state.table_index_by_id[id(table)]] = _classify_table(table)
        _native_table_grid(table, state)
    _walk_visible_text(root, state, root_path)
    _attach_document_type_facts(state)
    _attach_native_tables(state)
    if not state.units:
        state.errors.append("no_visible_text_blocks")
    from company_wiki.document_model.narrative import DocumentStructure

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
