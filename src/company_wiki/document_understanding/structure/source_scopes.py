"""Bounded source-marked note membership, not a second section tree.

Only original unit IDs and existing source proofs leave this observer. Sections
owns parent frames; this module never identifies an actor or classifies facts.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from ..narrative_continuity import NativeSourceContext
from ..layout_hints.contract import WorkBudget
from .contract import MAX_CONTINUATION_PAGES, MAX_CONTINUATION_UNITS, ObservationUnit
from .layout import Ordering, is_heading

SOURCE_NOTE_SCOPE_FEATURE_VERSION = "source-note-scope/1"
_MARKER = re.compile(r"^\s*(?:备注|備註)\s*([0-9０-９一二三四五六七八九十百零〇]+)\s*[:：]")
_ITEM = re.compile(r"^\s*[\"“‘']?\s*(?:[0-9０-９]+[、.．)）]|[（(][0-9０-９]+[)）])")


@dataclass(frozen=True)
class NoteMarker:
    start: int
    end: int
    label: str


def match_source_note_marker(text: str) -> NoteMarker | None:
    match = _MARKER.match(text)
    return NoteMarker(match.start(), match.end(), match.group(1)) if match else None


@dataclass(frozen=True)
class SourceMarkedScope:
    intro_ids: tuple[str, ...]
    member_ids: frozenset[str]
    context_by_unit: dict[str, tuple[str, ...]]
    source_by_unit: dict[str, tuple[str, ...]]
    proofs_by_unit: dict[str, tuple[dict[str, Any], ...]]
    unresolved_unit_ids: frozenset[str]


def _source_body(unit: ObservationUnit, excluded: set[str] | frozenset[str]) -> bool:
    return bool(unit.source_id and unit.unit_id not in excluded
                and not unit.table_id and not unit.table_region
                and not unit.is_table_furniture and not unit.is_footnote
                and not unit.is_header_furniture)


def build_source_marked_scopes(ordering: Ordering, *, native_context: NativeSourceContext | None,
                               limits: dict[str, int], work_budget: WorkBudget | None):
    """Observe each explicit note once, bounded by the existing scope limits.

    A missing proof ends inheritance and marks only the potential local targets
    partial. It never borrows the prior note, and missing geometry alone does
    not invalidate parser-owned exact membership.
    """
    account = native_context.work_budget if native_context is not None else work_budget
    ordered = ordering.ordered
    if account is not None:
        account.charge(1 + len(ordering.toc_ids) + len(ordering.running_header_ids))
    excluded = ordering.toc_ids | ordering.running_header_ids
    scopes: dict[str, SourceMarkedScope] = {}
    diagnostics: list[dict] = []
    bound = min(MAX_CONTINUATION_UNITS, limits["max_group_members"])
    for index, opener in enumerate(ordered):
        if account is not None:
            account.charge(1 + len(opener.text))
        marker = match_source_note_marker(opener.text)
        if marker is None or not _source_body(opener, excluded):
            continue
        intros = [opener.unit_id]
        members = [opener.unit_id]
        unresolved: set[str] = set()
        contexts: dict[str, tuple[str, ...]] = {}
        sources: dict[str, tuple[str, ...]] = {}
        proofs_by_unit: dict[str, tuple[dict[str, Any], ...]] = {}
        page_proofs: list[dict[str, Any]] = []
        previous = opener
        unproven = False
        marker_only = not opener.text[marker.end:].strip()
        intake_intro = marker_only or not opener.text.rstrip().endswith((":", "："))
        for cursor in range(index + 1, len(ordered)):
            unit = ordered[cursor]
            if account is not None:
                account.charge(1 + len(unit.text))
            if (unit.source_id != opener.source_id or unit.role != opener.role
                    or unit.speaker != opener.speaker or unit.turn_id != opener.turn_id
                    or match_source_note_marker(unit.text) is not None):
                break
            if unit.unit_id in ordering.running_header_ids:
                if cursor - index >= bound:
                    break
                continue
            if (not _source_body(unit, excluded)
                    or is_heading(unit, toc_ids=ordering.toc_ids)):
                break
            if cursor - index >= bound:
                unresolved.add(unit.unit_id)
                diagnostics.append({"code": "SOURCE_SCOPE_LIMIT_REACHED",
                    "unit_ids": [unit.unit_id], "detail": "source-marked note member bound reached"})
                break
            edge = None
            if not unproven and native_context is not None:
                if unit.page == previous.page:
                    edge = native_context.member_neighbour(previous.unit_id, unit.unit_id)
                    if edge is None:
                        edge = native_context.same_page_neighbour(previous.unit_id, unit.unit_id)
                elif (unit.page is not None and previous.page is not None
                      and opener.page is not None
                      and 0 < unit.page - opener.page < MAX_CONTINUATION_PAGES):
                    edge = native_context.page_neighbour(previous.unit_id, unit.unit_id,
                        furniture_unit_ids=ordering.running_header_ids)
            if unproven or edge is None:
                unproven = True
                unresolved.add(unit.unit_id)
                continue
            is_intro = (intake_intro and not _ITEM.match(unit.text)
                        and unit.page == opener.page
                        and (unit.text.rstrip().endswith((":", "："))
                             or edge["basis"] == "native_block_character_ranges"))
            if is_intro:
                intros.append(unit.unit_id)
                intake_intro = not unit.text.rstrip().endswith((":", "："))
            else:
                intake_intro = False
                if marker_only and len(intros) == 1:
                    unproven = True
                    unresolved.add(unit.unit_id)
                    continue
                if edge["basis"] == "observed_adjacent_page_flow":
                    page_proofs.append(edge)
                if account is not None:
                    account.charge(len(intros) + sum(3 + len(p["furniture_unit_ids"]) for p in page_proofs))
                contexts[unit.unit_id] = tuple(intros)
                if page_proofs:
                    proofs_by_unit[unit.unit_id] = tuple(page_proofs)
                    sources[unit.unit_id] = tuple(dict.fromkeys(uid
                        for proof in page_proofs
                        for uid in (proof["left"], proof["right"], *proof["furniture_unit_ids"])
                        if uid != unit.unit_id))
            members.append(unit.unit_id)
            previous = unit
        if unresolved:
            diagnostics.append({"code": "SOURCE_SCOPE_UNPROVEN", "unit_ids": sorted(unresolved),
                "detail": "source-marked local note relationship lacks original adjacency or complete introduction"})
        if account is not None:
            account.charge(1 + len(intros) + len(members) + len(unresolved))
        scopes[opener.unit_id] = SourceMarkedScope(tuple(intros), frozenset(members),
            contexts, sources, proofs_by_unit, frozenset(unresolved))
    return scopes, tuple(diagnostics)
