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

from collections.abc import Iterable, Sequence

from ..layout_hints.contract import WorkBudget
from ._work import reserve
from . import layout as layout_mod
from .contract import RELATION_KINDS, ObservationUnit

# Cycle-prone kinds: these express "needs the other one first".
_ACYCLIC_KINDS = frozenset(
    {"continuation", "header_for", "footnote_for", "question_answer"}
)


class RelationBuilder:
    """Accumulate relations with dedup, existence checks, and cycle detection."""

    def __init__(
        self,
        known_ids: set[str],
        *,
        max_relations: int,
        work_budget: WorkBudget | None = None,
    ) -> None:
        self._budget = work_budget
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
        reserve(self._budget, len(from_ids) + len(to_ids))
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
        safe: list[dict] = []
        graph: dict[str, set[str]] = {}
        for item in self._items:
            reserve(
                self._budget, 1 + len(item["from_unit_ids"]) * len(item["to_unit_ids"])
            )
            if item["kind"] not in _ACYCLIC_KINDS:
                safe.append(item)
                continue
            # Adding from->to closes a cycle only when to already depends,
            # directly or transitively, on from.  Reaching to *from* from is
            # normal (one question and its continuation both point at the
            # answer) and must not be mistaken for a cycle.
            closes = any(
                target == source
                or source in _reachable(graph, target, work_budget=self._budget)
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


def _reachable(
    graph: dict[str, set[str]], start: str, *, work_budget: WorkBudget | None = None
) -> set[str]:
    seen: set[str] = set()
    stack = [start]
    while stack:
        reserve(work_budget)
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        edges = graph.get(node, ())
        reserve(work_budget, len(edges) * (1 + len(edges).bit_length()))
        stack.extend(sorted(edges))
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
        reserve(builder._budget, len(rows_by_page.get(unit.page, ())))
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
            if unit.bbox[1] - previous.bbox[3] > 40:
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
    # Index source/page once. Looking through every page/lane for each page
    # was quadratic even when no page contained a possible pair.
    reserve(builder._budget, len(ordering.ordered))
    by_page: dict[tuple[str | None, int | None], dict[int, list[ObservationUnit]]] = {}
    for unit in ordering.ordered:
        if unit.column is None:
            continue
        if unit.kind in {"header", "footer"}:
            continue
        page_lanes = by_page.setdefault((unit.source_id, unit.page), {})
        page_lanes.setdefault(unit.column, []).append(unit)

    reserve(builder._budget, len(by_page) * (1 + len(by_page).bit_length()))
    for scope in sorted(by_page, key=lambda value: (value[1] is None, value[1] or 0, value[0] or "")):
        lane_units = by_page[scope]
        reserve(builder._budget, len(lane_units) * (1 + len(lane_units).bit_length()))
        lanes = sorted(lane_units)
        for left_index, left_lane in enumerate(lanes):
            for right_index in range(left_index + 1, len(lanes)):
                reserve(builder._budget)
                right_lane = lanes[right_index]
                left_units = lane_units[left_lane]
                right_units = lane_units[right_lane]
                _pair_lanes(
                    builder, left_units, right_units, work_budget=builder._budget
                )

    by_dom_parent: dict[tuple[str | None, str], list[ObservationUnit]] = {}
    reserve(builder._budget, len(ordering.ordered))
    for unit in ordering.ordered:
        if unit.column is not None or not unit.dom_path:
            continue
        parent = unit.dom_path.rsplit(".", 1)[0]
        by_dom_parent.setdefault((unit.source_id, parent), []).append(unit)
    reserve(builder._budget, len(by_dom_parent) * (1 + len(by_dom_parent).bit_length()))
    for dom_scope in sorted(by_dom_parent, key=lambda value: (value[0] or "", value[1])):
        group = by_dom_parent[dom_scope]
        if len(group) < 2:
            continue
        _pair_lanes(builder, group, group, allow_self=True, work_budget=builder._budget)

    _geometric_lane_pairs(builder, ordering)


def _geometric_lane_pairs(
    builder: RelationBuilder, ordering: layout_mod.Ordering
) -> None:
    """Pair side-by-side boxes with different writing systems.

    Units are bucketed by page first, so this stays linear in the unit count
    instead of comparing the whole document pairwise.
    """
    by_page: dict[tuple[str | None, int], list[ObservationUnit]] = {}
    reserve(builder._budget, len(ordering.ordered))
    scripts: dict[str, str] = {}
    page_scripts: dict[tuple[str | None, int], set[str]] = {}
    for unit in ordering.ordered:
        if unit.page is None or unit.bbox is None or unit.column is not None:
            continue
        if unit.kind in {
            "header",
            "footer",
            "table_row",
            "table_header",
            "table_caption",
        }:
            continue
        reserve(builder._budget, (len(unit.text) + 63) // 64)
        script = layout_mod.script_of(unit.text)
        if script is None:
            continue
        scope = (unit.source_id, unit.page)
        by_page.setdefault(scope, []).append(unit)
        scripts[unit.unit_id] = script
        page_scripts.setdefault(scope, set()).add(script)

    for page in sorted(by_page, key=lambda value: (value[1], value[0] or "")):
        if len(page_scripts[page]) < 2:
            continue
        reserve(builder._budget, len(by_page[page]) * len(by_page[page]).bit_length())
        bucket = sorted(by_page[page], key=lambda unit: (unit.y0, unit.x0))
        for index, left in enumerate(bucket):
            left_script = scripts[left.unit_id]
            for right_index in range(index + 1, len(bucket)):
                reserve(builder._budget)
                right = bucket[right_index]
                right_y, left_y = right.y0, left.y0
                if right_y is None or left_y is None or right_y - left_y > 24:
                    break
                if scripts[right.unit_id] == left_script:
                    continue
                if left.kind != right.kind:
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
    work_budget: WorkBudget | None = None,
) -> None:
    """Pair units positionally, refusing pairs without a language difference."""
    candidates: Iterable[tuple[ObservationUnit, ObservationUnit]]
    if allow_self:
        if not _possible_language_pair(left_units, left_units, work_budget=work_budget):
            return
        # Reserve the exact possible pairs before expansion; keep them lazy.
        reserve(work_budget, len(left_units) * (len(left_units) - 1) // 2)
        candidates = (
            (left_units[i], left_units[j])
            for i in range(len(left_units))
            for j in range(i + 1, len(left_units))
        )
    else:
        if len(left_units) != len(right_units):
            _pair_by_nearest(builder, left_units, right_units, work_budget=work_budget)
            return
        reserve(work_budget, len(left_units))
        candidates = zip(left_units, right_units, strict=False)

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
    *,
    work_budget: WorkBudget | None = None,
) -> None:
    """Unequal lane lengths: pair by vertical position, never by count order."""
    if not _possible_language_pair(left_units, right_units, work_budget=work_budget):
        return
    reserve(work_budget, len(left_units) * len(right_units))
    for left in left_units:
        left_y = left.y0
        if left_y is None:
            continue
        best: ObservationUnit | None = None
        best_distance = None
        for right in right_units:
            right_y = right.y0
            if right_y is None or not _different_language(left, right):
                continue
            distance = abs(left_y - right_y)
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


def _possible_language_pair(
    left_units: Sequence[ObservationUnit],
    right_units: Sequence[ObservationUnit],
    *,
    work_budget: WorkBudget | None,
) -> bool:
    """Reject impossible expansions with a paid linear eligibility pass.

    This does not pick counterparts. Eligible inputs still follow the old
    positional/nearest/DOM pairing and tie order. Missing language stays
    unknown, and original attribution is a grouping boundary, not a new
    identity verification or cache.
    """
    same = left_units is right_units
    reserve(work_budget, len(left_units) + (0 if same else len(right_units)))

    def families(units: Sequence[ObservationUnit]) -> dict[tuple[str | None, str], set[str]]:
        groups: dict[tuple[str | None, str], set[str]] = {}
        for unit in units:
            if unit.language:
                family = unit.language.split("-")[0].casefold()
                if family:
                    groups.setdefault((unit.source_id, unit.kind), set()).add(family)
        return groups

    left = families(left_units)
    right = left if same else families(right_units)
    reserve(work_budget, len(left))
    return any(right.get(key) and (len(values) > 1 or values != right[key])
               for key, values in left.items())


def _different_language(left: ObservationUnit, right: ObservationUnit) -> bool:
    if left.source_id != right.source_id:
        return False
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
    return abs(left.bbox[1] - right.bbox[1]) <= 24


__all__ = [
    "RelationBuilder",
    "continuation_relations",
    "header_and_footnote_relations",
    "language_lane_relations",
    "question_answer_relations",
]
