"""B2 bounded source predecessors for product-reference closure.

A read-only view over the observed original units. It owns which earlier
original bodies may be examined; it never resolves meaning, copies text,
reruns the parser or invents a second store. Ordering is the actual source
ordinal, not page paragraph index, hash order or package priority.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

ANTECEDENT_SCHEMA = "du11-antecedent-window/1"
MAX_WINDOW_UNITS = 8
MAX_ENVELOPE_UNITS = 8
MAX_ENVELOPE_BLOCKS = 4
MAX_ENVELOPE_CHARS = 2048


def _field(unit: Any, name: str, default: Any = None) -> Any:
    if isinstance(unit, Mapping):
        return unit.get(name, default)
    return getattr(unit, name, default)


def _text(unit: Any) -> str:
    value = _field(unit, "raw_text")
    if value is None:
        value = _field(unit, "text", "")
    return str(value or "")


def _block(unit: Any) -> Any:
    metadata = _field(unit, "metadata") or {}
    if isinstance(metadata, Mapping):
        return metadata.get("pdf_block")
    return None


def _page(unit: Any) -> int | None:
    coordinates = _field(unit, "coordinates")
    page = getattr(coordinates, "page_number", None) if coordinates is not None else None
    if page is None and isinstance(coordinates, Mapping):
        page = coordinates.get("page_number")
    return None if page is None else int(page)


def _ordinal(unit: Any) -> int | None:
    coordinates = _field(unit, "coordinates")
    ordinal = getattr(coordinates, "paragraph_index", None) if coordinates is not None else None
    if ordinal is None and isinstance(coordinates, Mapping):
        ordinal = coordinates.get("paragraph_index")
    return None if ordinal is None else int(ordinal)


def _scope(unit: Any, section: str | None, projects: tuple[str, ...]) -> tuple:
    return (_field(unit, "source_id"), section, projects,
            _field(unit, "source_role"), _field(unit, "unit_kind"))


def _adjacent(left: Any, right: Any, carries: frozenset[tuple[str, str]],
              require_proof: bool, skipped: int = 0) -> bool:
    """Compare a candidate with the kept neighbour, allowing proven furniture."""
    left_page, right_page = _page(left), _page(right)
    left_ordinal, right_ordinal = _ordinal(left), _ordinal(right)
    if left_page is None or right_page is None or left_ordinal is None or right_ordinal is None:
        return False if require_proof else True
    if left_page == right_page:
        return right_ordinal == left_ordinal + 1 + skipped
    if right_page == left_page + 1:
        return (_field(left, "unit_id"), _field(right, "unit_id")) in carries
    return False


def build_antecedent_windows(parsed: Any, pipeline: Mapping[str, Any], *,
                             prose_unit_ids: set[str], blocked: frozenset[str] = frozenset(),
                             excluded: frozenset[str] = frozenset(),
                             furniture: frozenset[str] = frozenset(),
                             page_carries: frozenset[tuple[str, str]] = frozenset(),
                             project_for: Mapping[str, tuple[str, ...]] | None = None,
                             require_adjacency_proof: bool = False,
                             work_budget: Any = None,
                             max_units: int = MAX_WINDOW_UNITS) -> dict[str, dict[str, Any]]:
    """Return one finite predecessor window per eligible prose original unit.

    The complete flag is True only for a proven beginning or a proven scope
    boundary. An unread/blocked unit, an unproved physical order and a cap hit
    return complete=False so no caller can infer absence from an unexamined
    tail. Proven running furniture is skipped without becoming a predecessor.
    """
    order = [unit.unit_id for unit in parsed.units]
    units = {unit.unit_id: unit for unit in parsed.units}
    section_for: dict[str, str | None] = {}
    for section in pipeline.get("structure", {}).get("sections", ()):
        for uid in (*section.get("heading_unit_ids", ()), *section.get("body_unit_ids", ())):
            section_for[uid] = section.get("section_id")
    hints = {wire["unit_id"]: wire.get("hints", {})
             for wire in pipeline.get("observation", {}).get("units", ())}
    project_for = project_for or {}
    unread = set(blocked)
    excluded_ids = set(excluded) | set(pipeline.get("non_selectable_unit_ids", ()))
    proven_furniture = set(furniture)
    if work_budget is not None:
        work_budget.charge(2 * len(order) + 1)

    def scope_of(uid: str) -> tuple:
        section = section_for.get(uid)
        if section is None:
            section = hints.get(uid, {}).get("section_key") or None
        return _scope(units[uid], section, tuple(project_for.get(uid, ())))

    windows: dict[str, dict[str, Any]] = {}
    for index, uid in enumerate(order):
        if uid not in prose_unit_ids or uid in unread or uid in excluded_ids:
            continue
        if work_budget is not None:
            work_budget.charge(1)
        target_scope = scope_of(uid)
        predecessors: list[str] = []
        complete, reason = True, "beginning"
        # Compare each candidate with the last kept unit, not with a skipped
        # furniture neighbour: a proven running header between two pages must
        # not become the thing a page carry is checked against.
        previous = units[uid]
        skipped = 0
        cursor = index - 1
        while cursor >= 0:
            other = order[cursor]
            current = units[other]
            if other in proven_furniture and other not in prose_unit_ids:
                skipped += 1
                cursor -= 1
                continue
            if other in unread:
                complete, reason = False, "unread"
                break
            if other not in prose_unit_ids or other in excluded_ids:
                reason = "source_boundary"
                break
            if scope_of(other) != target_scope:
                reason = "source_boundary"
                break
            if not _adjacent(current, previous, page_carries, require_adjacency_proof,
                             skipped=skipped):
                complete, reason = False, "unproved_order"
                break
            if len(predecessors) >= max_units:
                complete, reason = False, "cap"
                break
            predecessors.append(other)
            previous = current
            skipped = 0
            cursor -= 1
        windows[uid] = {"schema_version": ANTECEDENT_SCHEMA, "target_unit_id": uid,
                        "predecessor_unit_ids": tuple(reversed(predecessors)),
                        "complete": complete, "stop_reason": reason}
    return windows


def within_reference_envelope(target_ids, context_ids, declaration_ids, units: Mapping[str, Any],
                              *, expand=None, max_units: int = MAX_ENVELOPE_UNITS,
                              max_blocks: int = MAX_ENVELOPE_BLOCKS,
                              max_chars: int = MAX_ENVELOPE_CHARS) -> bool:
    """Count body, existing context and declarations in one original envelope.

    The optional expand callable maps a final carrier id to every original unit
    it replaced, so a carrier can never under-count units, characters or
    blocks. Absent block coordinates cannot prove PDF block compliance.
    """
    requested = list(dict.fromkeys((*target_ids, *context_ids, *declaration_ids)))
    ids: list[str] = []
    for uid in requested:
        members = tuple(expand(uid)) if expand is not None else (uid,)
        for member in members or (uid,):
            if member not in ids:
                ids.append(member)
    if len(ids) > max_units:
        return False
    total, blocks, saw_block = 0, set(), False
    for uid in ids:
        unit = units.get(uid)
        if unit is None:
            return False
        total += len(_text(unit))
        block = _block(unit)
        if block is not None:
            saw_block = True
            blocks.add((_field(unit, "source_id"), _page(unit), block))
    if total > max_chars:
        return False
    if saw_block:
        if any(_block(units[uid]) is None for uid in ids):
            return False
        if len(blocks) > max_blocks:
            return False
    return True
