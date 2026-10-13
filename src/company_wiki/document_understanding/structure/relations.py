"""Semantic relations between source units.

Two hard rules govern this module:

* Every relation must cite units that exist in the input, and the relation set
  must be acyclic under the semantic-dependency kinds.  An unbounded chain of
  ``continuation`` edges is exactly the "infinite expansion" the contract
  forbids, so the graph is checked before it is emitted.
* ``language_parallel`` needs real evidence: an actual layout lane or a DOM/
  structural counterpart.  Language similarity is never enough, and the
  relation never replaces either side's units.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import layout as layout_mod
from .contract import RELATION_KINDS, ObservationUnit

# Cycle-prone kinds: these express "needs the other one first".
_ACYCLIC_KINDS = frozenset(
    {"continuation", "header_for", "footnote_for", "question_answer"}
)


class RelationBuilder:
    """Accumulate relations with dedup, existence checks, and cycle detection."""

    def __init__(self, known_ids: set[str], *, max_relations: int) -> None:
        self._known = known_ids
        self._max = max_relations
        self._items: list[dict] = []
        self._seen: set[tuple] = set()
        self.diagnostics: list[dict] = []
        self._truncated = False

    def add(
        self,
        *,
        from_ids: Sequence[str],
        to_ids: Sequence[str],
        kind: str,
        confidence: str,
    ) -> bool:
        if kind not in RELATION_KINDS:
            raise ValueError(f"unknown relation kind {kind!r}")
        sources = tuple(dict.fromkeys(unit for unit in from_ids if unit))
        targets = tuple(dict.fromkeys(unit for unit in to_ids if unit))
        if not sources or not targets:
            return False
        missing = [unit for unit in (*sources, *targets) if unit not in self._known]
        if missing:
            self.diagnostics.append(
                {
                    "code": "RELATION_UNIT_MISSING",
                    "unit_ids": missing,
                    "detail": "relation dropped: cited unit is not part of this source",
                }
            )
            return False
        key = (sources, targets, kind)
        if key in self._seen:
            return False
        if len(self._items) >= self._max:
            if not self._truncated:
                self._truncated = True
                self.diagnostics.append(
                    {
                        "code": "RELATION_BUDGET_EXCEEDED",
                        "unit_ids": [],
                        "detail": f"max_relations={self._max} reached",
                    }
                )
            return False
        self._seen.add(key)
        self._items.append(
            {
                "from_unit_ids": list(sources),
                "to_unit_ids": list(targets),
                "kind": kind,
                "confidence": confidence,
            }
        )
        return True

    def relations(self) -> tuple[dict, ...]:
        return tuple(self._items)

    def check_acyclic(self) -> tuple[dict, ...]:
        """Drop relations that close a cycle, reporting each removal."""
        dependencies: dict[str, set[str]] = {}
        for item in self._items:
            if item["kind"] not in _ACYCLIC_KINDS:
                continue
            for source in item["from_unit_ids"]:
                dependencies.setdefault(source, set()).update(item["to_unit_ids"])

        safe: list[dict] = []
        graph: dict[str, set[str]] = {}
        for item in self._items:
            if item["kind"] not in _ACYCLIC_KINDS:
                safe.append(item)
                continue
            # Adding from->to closes a cycle only when to already depends,
            # directly or transitively, on from.  Reaching to *from* from is
            # normal (one question and its continuation both point at the
            # answer) and must not be mistaken for a cycle.
            closes = any(
                target == source or source in _reachable(graph, target)
                for source in item["from_unit_ids"]
                for target in item["to_unit_ids"]
            )
            if closes:
                self.diagnostics.append(
                    {
                        "code": "RELATION_CYCLE",
                        "unit_ids": list(item["from_unit_ids"]),
                        "detail": f"{item['kind']} relation would close a dependency cycle",
                    }
                )
                continue
            safe.append(item)
            for source in item["from_unit_ids"]:
                graph.setdefault(source, set()).update(item["to_unit_ids"])
        self._items = safe
        return tuple(safe)


def _reachable(graph: dict[str, set[str]], start: str) -> set[str]:
    seen: set[str] = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(sorted(graph.get(node, ())))
    return seen


def continuation_relations(
    builder: RelationBuilder,
    units: Sequence[ObservationUnit],
    ordering: layout_mod.Ordering,
    member_of: dict[str, str],
) -> None:
    """Link consecutive members of one semantic package across a break."""
    for previous, current in zip(ordering.ordered, ordering.ordered[1:], strict=False):
        if previous.unit_id not in member_of or current.unit_id not in member_of:
            continue
        if member_of[previous.unit_id] != member_of[current.unit_id]:
            continue
        if layout_mod.continues_visually(previous, current):
            builder.add(
                from_ids=[previous.unit_id],
                to_ids=[current.unit_id],
                kind="continuation",
                confidence="high",
            )
            continue
        if previous.page != current.page and _page_chain(previous, current):
            builder.add(
                from_ids=[previous.unit_id],
                to_ids=[current.unit_id],
                kind="continuation",
                confidence="medium",
            )


def _page_chain(previous: ObservationUnit, current: ObservationUnit) -> bool:
    """Cross-page continuation needs an unfinished sentence, not just adjacency."""
    text = previous.text.rstrip()
    if not text:
        return False
    if text.endswith(("。", "！", "？", "；", ".", "!", "?", ";", "：", ":")):
        return False
    if current.page is None or previous.page is None:
        return False
    return current.page - previous.page == 1


def header_and_footnote_relations(
    builder: RelationBuilder,
    units: Sequence[ObservationUnit],
    ordering: layout_mod.Ordering,
) -> None:
    """Bind table headers to their rows and footnotes to what they annotate."""
    by_id = {unit.unit_id: unit for unit in units}
    headers_by_table: dict[str, list[str]] = {}
    captions_by_table: dict[str, list[str]] = {}
    for unit in ordering.ordered:
        if not unit.table_id:
            continue
        if unit.kind == "table_header":
            headers_by_table.setdefault(unit.table_id, []).append(unit.unit_id)
        elif unit.kind == "table_caption":
            captions_by_table.setdefault(unit.table_id, []).append(unit.unit_id)

    for unit in ordering.ordered:
        if unit.table_id is None:
            continue
        table = unit.table_id
        if unit.kind == "table_row" and headers_by_table.get(table):
            builder.add(
                from_ids=headers_by_table[table],
                to_ids=[unit.unit_id],
                kind="header_for",
                confidence="high",
            )
        if unit.is_footnote:
            targets = headers_by_table.get(table) or captions_by_table.get(table)
            if targets:
                builder.add(
                    from_ids=[unit.unit_id],
                    to_ids=targets,
                    kind="footnote_for",
                    confidence="medium",
                )

    # Footnotes without a table id attach to the nearest preceding table row
    # on the same page, and only when the spacing is genuinely tight.  The
    # per-page index keeps this linear: comparing every footnote against every
    # unit would be the quadratic pass the contract forbids.
    rows_by_page: dict[int | None, list[ObservationUnit]] = {}
    for other in ordering.ordered:
        if other.kind in {"table_row", "table_header"}:
            rows_by_page.setdefault(other.page, []).append(other)

    for unit in ordering.ordered:
        if unit.table_id is not None or not layout_mod.looks_like_footnote(unit):
            continue
        candidates = [
            other
            for other in rows_by_page.get(unit.page, ())
            if other.unit_id != unit.unit_id
        ]
        if not candidates:
            continue
        nearest = min(
            candidates,
            key=lambda other: abs((other.y0 or 0.0) - (unit.y0 or 0.0)),
        )
        previous = by_id.get(nearest.unit_id)
        if previous is None:
            continue
        if previous.bbox is not None and unit.bbox is not None:
            if unit.y0 - previous.y1 > 40:
                continue
        builder.add(
            from_ids=[unit.unit_id],
            to_ids=[nearest.unit_id],
            kind="footnote_for",
            confidence="low",
        )


def question_answer_relations(
    builder: RelationBuilder,
    exchanges: Sequence,
) -> None:
    for exchange in exchanges:
        if exchange.question_ids and exchange.answer_ids:
            builder.add(
                from_ids=exchange.question_ids,
                to_ids=exchange.answer_ids,
                kind="question_answer",
                confidence="high",
            )


def language_lane_relations(
    builder: RelationBuilder,
    units: Sequence[ObservationUnit],
    ordering: layout_mod.Ordering,
) -> None:
    """Emit ``language_parallel`` only with real lane/structural evidence.

    Two admissible evidence shapes:

    * an explicit ``layout.column`` lane index, or
    * two boxes on the same page that do not overlap horizontally, are
      vertically aligned, and carry different writing systems.

    The second shape exists because real parsed filings label both columns
    ``zh``; the writing system actually present in the text is the usable
    signal.  Either way the relation only *links* the two units -- neither is
    translated, dropped, or rewritten.
    """
    by_page_lane: dict[tuple[int | None, int], list[ObservationUnit]] = {}
    for unit in ordering.ordered:
        if unit.column is None:
            continue
        if unit.kind in {"header", "footer"}:
            continue
        by_page_lane.setdefault((unit.page, unit.column), []).append(unit)

    pages = {page for page, _ in by_page_lane}
    for page in sorted(pages, key=lambda value: (value is None, value or 0)):
        lanes = sorted(lane for candidate_page, lane in by_page_lane if candidate_page == page)
        for left_index, left_lane in enumerate(lanes):
            for right_lane in lanes[left_index + 1 :]:
                left_units = by_page_lane[(page, left_lane)]
                right_units = by_page_lane[(page, right_lane)]
                _pair_lanes(builder, left_units, right_units)

    by_dom_parent: dict[str, list[ObservationUnit]] = {}
    for unit in ordering.ordered:
        if unit.column is not None or not unit.dom_path:
            continue
        parent = unit.dom_path.rsplit(".", 1)[0]
        by_dom_parent.setdefault(parent, []).append(unit)
    for parent in sorted(by_dom_parent):
        group = by_dom_parent[parent]
        if len(group) < 2:
            continue
        _pair_lanes(builder, group, group, allow_self=True)

    _geometric_lane_pairs(builder, ordering)


def _geometric_lane_pairs(
    builder: RelationBuilder, ordering: layout_mod.Ordering
) -> None:
    """Pair side-by-side boxes with different writing systems.

    Units are bucketed by page first, so this stays linear in the unit count
    instead of comparing the whole document pairwise.
    """
    by_page: dict[int, list[ObservationUnit]] = {}
    for unit in ordering.ordered:
        if unit.page is None or unit.bbox is None or unit.column is not None:
            continue
        if unit.kind in {"header", "footer", "table_row", "table_header", "table_caption"}:
            continue
        script = layout_mod.script_of(unit.text)
        if script is None:
            continue
        by_page.setdefault(unit.page, []).append(unit)

    for page in sorted(by_page):
        bucket = sorted(by_page[page], key=lambda unit: (unit.y0, unit.x0))
        for index, left in enumerate(bucket):
            left_script = layout_mod.script_of(left.text)
            if left_script is None:
                continue
            for right in bucket[index + 1 :]:
                if right.y0 - left.y0 > 24:
                    break
                if layout_mod.script_of(right.text) == left_script:
                    continue
                if not layout_mod.vertically_aligned(left, right):
                    continue
                if not layout_mod.side_by_side(left, right):
                    continue
                builder.add(
                    from_ids=[left.unit_id],
                    to_ids=[right.unit_id],
                    kind="language_parallel",
                    confidence="medium",
                )


def _pair_lanes(
    builder: RelationBuilder,
    left_units: Sequence[ObservationUnit],
    right_units: Sequence[ObservationUnit],
    *,
    allow_self: bool = False,
) -> None:
    """Pair units positionally, refusing pairs without a language difference."""
    if allow_self:
        candidates = [
            (left, right)
            for index, left in enumerate(left_units)
            for right in left_units[index + 1 :]
        ]
    else:
        if len(left_units) != len(right_units):
            _pair_by_nearest(builder, left_units, right_units)
            return
        candidates = list(zip(left_units, right_units, strict=False))

    for left, right in candidates:
        if not _different_language(left, right):
            continue
        if not _aligned(left, right):
            continue
        builder.add(
            from_ids=[left.unit_id],
            to_ids=[right.unit_id],
            kind="language_parallel",
            confidence="medium",
        )


def _pair_by_nearest(
    builder: RelationBuilder,
    left_units: Sequence[ObservationUnit],
    right_units: Sequence[ObservationUnit],
) -> None:
    """Unequal lane lengths: pair by vertical position, never by count order."""
    for left in left_units:
        if left.y0 is None:
            continue
        best: ObservationUnit | None = None
        best_distance = None
        for right in right_units:
            if right.y0 is None or not _different_language(left, right):
                continue
            distance = abs(left.y0 - right.y0)
            if best_distance is None or distance < best_distance:
                best, best_distance = right, distance
        if best is None or best_distance is None or best_distance > 24:
            continue
        if not _aligned(left, best):
            continue
        builder.add(
            from_ids=[left.unit_id],
            to_ids=[best.unit_id],
            kind="language_parallel",
            confidence="low",
        )


def _different_language(left: ObservationUnit, right: ObservationUnit) -> bool:
    if not left.language or not right.language:
        return False
    left_family = left.language.split("-")[0].casefold()
    right_family = right.language.split("-")[0].casefold()
    return left_family != right_family


def _aligned(left: ObservationUnit, right: ObservationUnit) -> bool:
    """Structural alignment: comparable block class and no vertical collision."""
    if left.kind != right.kind:
        return False
    if left.bbox is None or right.bbox is None:
        return True
    return abs(left.y0 - right.y0) <= 24


__all__ = [
    "RelationBuilder",
    "continuation_relations",
    "header_and_footnote_relations",
    "language_lane_relations",
    "question_answer_relations",
]
