"""Bounded native PDF continuity over already observed source units.

This is provenance/geometry context, not another parser or fact classifier.
Only original IDs and measured proof leave this helper; composed text is never
persisted or sent to a model. Non-overlapping closed windows prevent context
unions from growing into a chapter.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from itertools import chain, groupby
from math import isfinite
from typing import Any

from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded

from .indented_tail_geometry import indented_terminal_tail_proof

NARRATIVE_CONTINUITY_FEATURE_VERSION = "native-narrative-continuity/8"
_LIMITS = {
    "max_units": 50_000,
    "max_window_units": 8,
    "max_window_blocks": 4,
    "max_window_chars": 2048,
    "max_windows": 4096,
    "max_work_units": 200_000,
}
_FRAMES = frozenset({"dict", "rawdict", "text", "words", "span"})
_NATIVE_FONTS = frozenset({"pdf_native_single_textpage", "pdf_dict_native_span"})


def _number(value: Any) -> float | None:
    return (
        float(value)
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        else None
    )


def _integer(value: Any) -> int | None:
    return value if type(value) is int else None


def native_section_key(hints: Mapping[str, Any], fallback: Any) -> Any:
    """Unknown optional hints never override an observed structural section."""
    value = hints.get("section_key")
    return fallback if value is None or (isinstance(value, str) and not value.strip()) else value


def _terminal(text: str) -> bool:
    return (
        text.rstrip()
        .rstrip("\"'”’）)]》")
        .endswith(("。", "！", "？", ".", "!", "?", ";", "；"))
    )


@dataclass(frozen=True)
class SourcePageFlow:
    """Source-owned complete observation, with positively identified furniture.

    Direct native callers have no such observation and remain same-page.
    The boundary veto is supplied by the source's existing statement policy.
    """
    running_furniture_unit_ids: frozenset[str]
    independent_start: Callable[[str], Any]
    coarse_complete: bool = True
    unproven_pages: frozenset[int] = frozenset()


@dataclass(frozen=True)
class NativePhysicalObservation:
    unit: Mapping[str, Any]
    provenance: Mapping[str, Any]
    source: str
    page: int
    ordinal: int
    paragraph: int
    block: int
    bbox: tuple[float, ...]
    frame: tuple[Any, ...]
    column: Any
    font: tuple[float, str]


@dataclass(frozen=True)
class _Native(NativePhysicalObservation):
    scope: tuple[Any, ...]
    left_closed: bool


def _observe_native_font(unit: Mapping[str, Any], frame: str, charge: Callable[[int], bool]) -> tuple[float, str] | None:
    runs = unit.get("hints", {}).get("font_runs", ())
    if (
        not isinstance(runs, (tuple, list))
        or not runs
        or not charge(len(runs))
    ):
        return None
    measured: Counter[tuple[float, str]] = Counter()
    previous = 0
    for run in runs:
        if not isinstance(run, Mapping):
            return None
        start, end = _integer(run.get("char_start")), _integer(run.get("char_end"))
        size, weight = _number(run.get("font_size")), run.get("font_weight")
        if (
            start is None
            or end is None
            or not previous <= start < end <= len(unit["text"])
            or size is None
            or size <= 0
            or weight not in {"regular", "bold"}
            or run.get("source") not in _NATIVE_FONTS
            or run.get("coordinate_frame") != frame
            or run.get("char_alignment") != "exact"
        ):
            return None
        measured[(size, weight)] += end - start
        previous = end
    covered = sum(measured.values())
    if covered < len(unit["text"]) * 0.9:
        return None
    style, weight = measured.most_common(1)[0]
    return style if 2 * weight >= covered else None


def observe_native_source_unit(
    unit: Mapping[str, Any], provenance: Mapping[str, Any],
    charge: Callable[[int], bool],
) -> NativePhysicalObservation | None:
    """Observe actual source geometry/font/provenance without sentence or section policy."""
    if not charge(1):
        return None
    uid = unit.get("unit_id")
    if (
        not isinstance(uid, str)
        or unit.get("kind") != "paragraph"
        or unit.get("role") not in {"company_filing", "management", "unknown"}
        or not isinstance(unit.get("text"), str)
        or not unit["text"]
    ):
        return None
    hints, layout = unit.get("hints", {}), unit.get("layout", {})
    if (
        not isinstance(hints, Mapping)
        or not isinstance(layout, Mapping)
        or hints.get("table_id") is not None
        or hints.get("heading_level")
    ):
        return None
    source = hints.get("source_id")
    page, ordinal = _integer(unit.get("page")), _integer(unit.get("ordinal"))
    paragraph, block = (
        _integer(provenance.get("paragraph_index")),
        _integer(provenance.get("pdf_block")),
    )
    frame, rotation = (
        layout.get("coordinate_frame"),
        _integer(layout.get("rotation")),
    )
    width, height = (
        _number(layout.get("page_width")),
        _number(layout.get("page_height")),
    )
    if (
        not isinstance(source, str)
        or not source
        or source != provenance.get("source_id")
        or page is None
        or ordinal is None
        or paragraph is None
        or block is None
        or frame not in _FRAMES
        or rotation not in {0, 90, 180, 270}
        or width is None
        or height is None
        or width <= 0
        or height <= 0
    ):
        return None
    value = layout.get("bbox")
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    box = tuple(_number(item) for item in value)
    if any(item is None for item in box):
        return None
    actual = tuple(float(item) for item in box if item is not None)
    if (
        not 0 <= actual[0] < actual[2] <= width
        or not 0 <= actual[1] < actual[3] <= height
    ):
        return None
    font = _observe_native_font(unit, frame, charge)
    if font is None:
        return None
    return NativePhysicalObservation(unit, provenance, source, page, ordinal, paragraph,
                                     block, actual, (frame, rotation, width, height),
                                     layout.get("column"), font)


def _native_page_candidate(left: NativePhysicalObservation, right: NativePhysicalObservation) -> bool:
    return bool(right.page == left.page + 1 and left.source == right.source
        and left.frame == right.frame and left.font == right.font
        and left.unit.get("role") == right.unit.get("role")
        and left.bbox[3] >= 0.8 * left.frame[3]
        and right.bbox[1] <= 0.2 * right.frame[3])


def native_page_neighbour(
    left: NativePhysicalObservation, right: NativePhysicalObservation, *,
    furniture: Sequence[Mapping[str, Any]], coarse_complete: bool,
    unproven_pages: frozenset[int],
) -> tuple[dict[str, Any] | None, str | None]:
    """One pure physical proof. Completion, parent identity and business syntax are clients."""
    if not _native_page_candidate(left, right):
        return None, None
    previous_page, previous_paragraph = left.page, left.paragraph
    for offset, item in enumerate(furniture, 1):
        page, paragraph = item.get("page"), item.get("paragraph_index")
        # Both normalized paragraphs/headings and native header/footer roles
        # can be positively proved running furniture by the source producer.
        # Sentence callers predate the normalized list view; narrowing their
        # observed roles here would add a new format requirement. Semantic
        # footnotes and table content still cannot be skipped as furniture.
        if (item.get("kind") not in {"paragraph", "heading", "header", "footer"}
                or item.get("ordinal") != left.ordinal + offset or type(paragraph) is not int
                or type(page) is not int or page not in (left.page, right.page)
                or page < previous_page
                or (page == previous_page and paragraph != previous_paragraph + 1)):
            return None, "CONTINUITY_PAGE_ORDER_UNPROVEN"
        previous_page, previous_paragraph = page, paragraph
    if (right.ordinal != left.ordinal + 1 + len(furniture)
            or (furniture and furniture[-1]["page"] == right.page
                and right.paragraph != furniture[-1]["paragraph_index"] + 1)):
        return None, "CONTINUITY_PAGE_ORDER_UNPROVEN"
    if not coarse_complete or left.page in unproven_pages or right.page in unproven_pages:
        return None, "CONTINUITY_PAGE_COVERAGE_UNPROVEN"
    column = left.column
    valid = ((type(column) is int and column >= 0)
             or (isinstance(column, str) and 0 < len(column.strip()) <= 128))
    if not valid or type(column) is not type(right.column) or column != right.column:
        return None, "CONTINUITY_PAGE_COLUMN_UNPROVEN"
    a, b, size = left.bbox, right.bbox, left.font[0]
    overlap = min(a[2], b[2]) - max(a[0], b[0])
    if (abs(a[0] - b[0]) > 2.1 * size or overlap <= 0
            or overlap < 0.8 * min(a[2] - a[0], b[2] - b[0])):
        return None, "CONTINUITY_PAGE_LANE_UNPROVEN"
    return {"basis": "observed_adjacent_page_flow", "left": left.unit["unit_id"],
            "right": right.unit["unit_id"], "left_page": left.page, "right_page": right.page,
            "left_ordinal": left.ordinal, "right_ordinal": right.ordinal,
            "column": column, "coordinate_frame": left.frame[0],
            "furniture_unit_ids": [unit["unit_id"] for unit in furniture]}, None


class NativeSourceContext:
    """Borrowed, call-local source observation; one precharged index, no source-state schema."""
    def __init__(self, units: Sequence[Mapping[str, Any]], *,
                 provenance: Mapping[str, Mapping[str, Any]], coverage: Mapping[str, Any],
                 work_budget: WorkBudget):
        # No field read, copying or indexing may precede this reservation.
        work_budget.charge(1 + 3 * len(units) + len(provenance))
        self.work_budget = work_budget
        self.provenance = provenance
        self.units = {unit["unit_id"]: unit for unit in units}
        self.ordinals = {unit.get("ordinal"): unit for unit in units}
        self.unique = len(self.units) == len(units) == len(self.ordinals)
        opaque, deferred = coverage.get("opaque_pages"), coverage.get("deferred_pages")
        self.unproven_pages: frozenset[int] = frozenset()
        if isinstance(opaque, (tuple, list)) and isinstance(deferred, (tuple, list)):
            work_budget.charge(1 + len(opaque) + len(deferred))
            known = all(type(page) is int and page >= 0 for page in chain(opaque, deferred))
            if known:
                self.unproven_pages = frozenset(chain(opaque, deferred))
        else:
            work_budget.charge()
            known = False
        self.coverage_complete = coverage.get("native_scan") == "complete" and known
        self.native_text_source: str | None = None
        self.native_text_pages: frozenset[int] = frozenset()
        self.native_text_supplied = "native_text" in coverage
        text = coverage.get("native_text")
        if isinstance(text, Mapping):
            statuses, count = text.get("page_statuses"), text.get("page_count")
            if isinstance(statuses, (tuple, list)):
                work_budget.charge(1 + 2 * len(statuses))
                if (text.get("schema_version") == "native-text-coverage/1"
                        and isinstance(text.get("source_id"), str) and text["source_id"]
                        and type(count) is int and count > 0 and count == len(statuses)
                        and all(isinstance(status, str) and status in {
                            "observed", "empty", "read_failed", "emission_failed"}
                            for status in statuses)):
                    self.native_text_source = text["source_id"]
                    self.native_text_pages = frozenset(page for page, status in enumerate(statuses, 1)
                                                       if status == "observed")
        self.observations: dict[str, NativePhysicalObservation | None] = {}
        self.diagnostics: Counter[str] = Counter()

    def page_coverage(self, left: NativePhysicalObservation, right: NativePhysicalObservation
                      ) -> tuple[bool, frozenset[int]]:
        """Use positive base-text facts without promoting whole-source completeness."""
        if self.native_text_supplied:
            return (left.source == right.source == self.native_text_source
                    and left.page in self.native_text_pages and right.page in self.native_text_pages,
                    frozenset())
        return self.coverage_complete, self.unproven_pages

    def _charge(self, amount: int = 1) -> bool:
        self.work_budget.charge(amount)
        return True

    def observe(self, uid: str, *, charge: Callable[[int], bool] | None = None
                ) -> NativePhysicalObservation | None:
        debit = self._charge if charge is None else charge
        if uid not in self.observations:
            if not debit(1):
                return None
            unit = self.units.get(uid)
            self.observations[uid] = (observe_native_source_unit(
                unit, self.provenance.get(uid, {}), debit) if unit else None)
        return self.observations[uid]

    def page_neighbour(self, left_id: str, right_id: str, *,
                       furniture_unit_ids: frozenset[str]) -> dict[str, Any] | None:
        self._charge()
        left, right = self.observe(left_id), self.observe(right_id)
        if not self.unique or left is None or right is None:
            return None
        gap = right.ordinal - left.ordinal - 1
        if gap < 0 or gap > len(self.units):
            return None
        self._charge(1 + gap)
        furniture = []
        for ordinal in range(left.ordinal + 1, right.ordinal):
            unit = self.ordinals.get(ordinal)
            if not unit or unit["unit_id"] not in furniture_unit_ids:
                return None
            uid = unit["unit_id"]
            meta = self.provenance.get(uid, {})
            if (meta.get("source_id") != left.source
                    or unit.get("hints", {}).get("source_id") != left.source):
                return None
            furniture.append({"unit_id": uid, "page": unit.get("page"), "ordinal": ordinal,
                              "kind": unit.get("kind"), "paragraph_index": meta.get("paragraph_index")})
        complete, unproven = self.page_coverage(left, right)
        proof, diagnostic = native_page_neighbour(left, right, furniture=furniture,
            coarse_complete=complete, unproven_pages=unproven)
        if diagnostic:
            self.diagnostics[diagnostic] += 1
        return proof


class _Analysis:
    def __init__(self, limits: Mapping[str, Any] | None, work_budget: WorkBudget | None = None,
                 source_page_flow: SourcePageFlow | None = None,
                 source_contexts: Mapping[str, NativeSourceContext] | None = None):
        self.source_contexts = source_contexts
        self.limits = dict(_LIMITS)
        if limits is not None:
            if not isinstance(limits, Mapping):
                raise ValueError("continuity limits must be a mapping")
            for key, ceiling in _LIMITS.items():
                if key in limits:
                    value = limits[key]
                    if type(value) is not int or value < 0:
                        raise ValueError(f"{key} must be a nonnegative integer")
                    self.limits[key] = min(value, ceiling)
        self.work = 0
        self.account = (work_budget.scoped(self.limits["max_work_units"])
                        if work_budget is not None else WorkBudget(self.limits["max_work_units"]))
        self.stopped = False
        self.diagnostics: Counter[str] = Counter()
        self.deferred: list[str] = []
        self.deferred_ids: set[str] = set()
        self.deferred_ranges: list[dict[str, Any]] = []
        self.windows: list[dict[str, Any]] = []
        self.adjacency_edges: list[dict[str, Any]] = []
        self.standalone_units = 0
        self.source_page_flow = source_page_flow

    def charge(self, amount: int = 1) -> bool:
        if self.stopped:
            return False
        try:
            self.account.charge(amount)
        except WorkBudgetExceeded:
            self.stopped = True
            self.diagnostics["CONTINUITY_WORK_LIMIT"] += 1
            return False
        self.work = self.account.used
        return True

    def native(
        self, unit: Mapping[str, Any], provenance: Mapping[str, Any],
        profile: Mapping[str, Any], section: Any, headings: set[str], left_closed: bool,
    ) -> _Native | None:
        if unit.get("unit_id") in headings:
            self.charge()
            return None
        # A semantic view may veto a paragraph or add scope, but its already
        # observed source geometry/font still has one call-local producer.
        if unit.get("kind") != "paragraph":
            self.charge()
            return None
        source_id = provenance.get("source_id")
        context = ((self.source_contexts or {}).get(source_id)
                   if isinstance(source_id, str) else None)
        if context is None:
            actual = observe_native_source_unit(unit, provenance, self.charge)
        else:
            if not self.charge():
                return None
            actual = context.observe(str(unit.get("unit_id") or ""), charge=self.charge)
        if actual is None:
            return None
        key = native_section_key(unit.get("hints", {}), section)
        return _Native(unit, actual.provenance, actual.source, actual.page,
                       actual.ordinal, actual.paragraph, actual.block, actual.bbox,
                       actual.frame, actual.column, actual.font,
                       (key, profile.get("reading_profile_key"), profile.get("section_role")),
                       left_closed)

    def tail_column_proof(self, left: _Native, right: _Native,
                          witnesses: Sequence[_Native]) -> dict[str, Any] | None:
        """Observed column or at most three contiguous original body witnesses.

        A witness establishes a physical body band only. It supplies no words,
        antecedent or semantic scope to the statement being grouped.
        """
        column = left.column
        if ((type(column) is int and column >= 0)
                or (isinstance(column, str) and 0 < len(column.strip()) <= 128)):
            return {"basis": "observed_column", "column": column}
        previous = right
        chain = []
        size = left.font[0]
        for anchor in witnesses[:3]:
            if not self.charge():
                return None
            if (anchor.source != left.source or anchor.page != left.page
                    or anchor.frame != left.frame or anchor.scope != left.scope
                    or anchor.font != left.font or anchor.column != column
                    or anchor.unit.get("role") != left.unit.get("role")
                    or anchor.ordinal != previous.ordinal + 1
                    or anchor.paragraph != previous.paragraph + 1):
                return None
            if anchor.block == previous.block:
                end = _integer(previous.provenance.get("block_char_end"))
                start = _integer(anchor.provenance.get("block_char_start"))
                if (anchor.bbox != previous.bbox or end is None or start is None
                        or not 0 <= start - end <= 2
                        or not anchor.provenance.get("block_sha256")
                        or anchor.provenance.get("block_sha256") != previous.provenance.get("block_sha256")):
                    return None
            elif (anchor.block != previous.block + 1
                    or not 0 <= anchor.bbox[1] - previous.bbox[3] <= 2 * size):
                return None
            box = anchor.bbox
            if (not right.bbox[0] - 0.25 * size <= box[0] <= left.bbox[0] + 0.25 * size
                    or abs(box[2] - left.bbox[2]) > size
                    or box[2] - box[0] < left.bbox[2] - left.bbox[0] - size):
                return None
            chain.append({"unit_id": anchor.unit["unit_id"], "bbox": box})
            if (abs(box[0] - right.bbox[0]) <= 0.25 * size
                    and box[2] - box[0] >= left.bbox[2] - left.bbox[0] - 0.25 * size):
                return {"basis": "contiguous_native_body_band",
                        "anchor_unit_id": anchor.unit["unit_id"],
                        "flow_witnesses": chain,
                        "left_margin_error": abs(box[0] - right.bbox[0]),
                        "right_margin_error": abs(box[2] - left.bbox[2])}
            previous = anchor
        return None

    def pending_page_transition(self, left: _Native, right: _Native) -> bool:
        flow = self.source_page_flow
        if (flow is None or not _native_page_candidate(left, right)
                or left.scope != right.scope or _terminal(left.unit["text"])):
            return False
        if not self.charge(8 * len(right.unit["text"])):
            return False
        return not flow.independent_start(right.unit["text"])

    def page_edge(self, left: _Native, right: _Native,
                  furniture: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
        if not self.pending_page_transition(left, right):
            return None
        flow = self.source_page_flow
        context = (self.source_contexts or {}).get(left.source)
        complete, unproven = (context.page_coverage(left, right) if context is not None else (
            flow.coarse_complete if flow is not None else False,
            flow.unproven_pages if flow is not None else frozenset()))
        proof, diagnostic = native_page_neighbour(left, right, furniture=furniture,
            coarse_complete=complete, unproven_pages=unproven)
        if diagnostic:
            self.diagnostics[diagnostic] += 1
            self.defer([left, right])
        return proof

    def edge(self, left: _Native, right: _Native, *,
             column_witnesses: Sequence[_Native] = (),
             furniture: Sequence[Mapping[str, Any]] = (),
             allow_complete_boundary: bool = False) -> dict[str, Any] | None:
        if not self.charge():
            return None
        if left.page != right.page:
            return self.page_edge(left, right, furniture)
        if furniture:
            return None
        if (
            left.source != right.source
            or left.page != right.page
            or right.ordinal != left.ordinal + 1
            or right.paragraph != left.paragraph + 1
            or left.frame != right.frame
            or left.scope != right.scope
            or left.font != right.font
            or left.unit.get("role") != right.unit.get("role")
        ):
            return None
        if left.column != right.column:
            return None
        if left.block == right.block:
            left_meta, right_meta = left.provenance, right.provenance
            end, start = (
                _integer(left_meta.get("block_char_end")),
                _integer(right_meta.get("block_char_start")),
            )
            if (
                not left_meta.get("block_sha256")
                or left_meta.get("block_sha256") != right_meta.get("block_sha256")
                or end is None
                or start is None
                or not 0 <= start - end <= 2
                or left.bbox != right.bbox
            ):
                return None
            return {
                "left": left.unit["unit_id"],
                "right": right.unit["unit_id"],
                "basis": "native_block_character_ranges",
            }
        if (not allow_complete_boundary and _terminal(left.unit["text"])) or right.block != left.block + 1:
            return None
        a, b = left.bbox, right.bbox
        size = left.font[0]
        # All source/page/scope/font/role/ordinal/column barriers above remain
        # authoritative. This shape is a second measured line-flow proof,
        # never a relaxation of the positive-overlap proof below.
        tail = indented_terminal_tail_proof(a, b, size, left.unit["text"], right.unit["text"])
        if tail is not None:
            column_proof = self.tail_column_proof(left, right, column_witnesses)
            if column_proof is None:
                if self.stopped:
                    return None  # The caller defers the whole pending run once.
                self.diagnostics["CONTINUITY_TAIL_COLUMN_UNPROVEN"] += 1
                self.defer([left, right])
                return None
            return {**tail, "left": left.unit["unit_id"], "right": right.unit["unit_id"],
                    "font_weight": left.font[1], "coordinate_frame": left.frame[0],
                    "column_proof": column_proof}
        overlap = min(a[2], b[2]) - max(a[0], b[0])
        gap = b[1] - a[3]
        if (
            abs(a[0] - b[0]) > 2.1 * size
            or overlap <= 0
            or overlap < 0.8 * min(a[2] - a[0], b[2] - b[0])
            # Native PDF baselines can drift slightly beyond one em even on
            # adjacent wrapped lines. Keep the tolerance font-relative and
            # bounded; source, block order, scope, font and horizontal-flow
            # proofs above still have to agree.
            or not 0 <= gap <= 1.15 * size
        ):
            return None
        return {
            "left": left.unit["unit_id"],
            "right": right.unit["unit_id"],
            "basis": "native_wrapped_line",
            "x0_delta": b[0] - a[0],
            "vertical_gap": gap,
            "measured_font_size": size,
            "font_weight": left.font[1],
            "coordinate_frame": left.frame[0],
        }

    def emit(self, run: list[_Native], proof: list[dict[str, Any]]) -> bool:
        if len(run) < 2:
            return True
        if len(self.windows) >= self.limits["max_windows"]:
            self.diagnostics["CONTINUITY_COUNT_LIMIT"] += 1
            return False
        if not self.charge(len(run) + len(proof)):
            return False
        ids = [item.unit["unit_id"] for item in run]
        self.windows.append(
            {
                "window_id": "native-continuity:"
                + sha256("\0".join(ids).encode()).hexdigest(),
                "source_id": run[0].source,
                "page": run[0].page if all(item.page == run[0].page for item in run) else None,
                "pages": list(dict.fromkeys(item.page for item in run)),
                "member_unit_ids": ids,
                "required_unit_ids": ids,
                "proof": proof,
            }
        )
        return True

    def defer(self, run: list[_Native]) -> None:
        if not run:
            return
        pending = [item for item in run if item.unit["unit_id"] not in self.deferred_ids]
        if not pending:
            return
        self.deferred.extend(item.unit["unit_id"] for item in pending)
        self.deferred_ids.update(item.unit["unit_id"] for item in pending)
        for (source, page), sequence in groupby(pending, key=lambda item: (item.source, item.page)):
            members = list(sequence)
            self.deferred_ranges.append({"source_id": source, "page": page,
                "first_ordinal": members[0].ordinal, "last_ordinal": members[-1].ordinal})

    def finish(self, run: list[_Native], proof: list[dict[str, Any]]) -> list[_Native]:
        """Cut only at an observed complete statement, never a resource prefix.

        Multiple sentence fragments can occupy the same original block. If a
        measured run exceeds a window, the last actual terminator inside the
        bound closes the preceding statement. An unclosed long statement is
        deferred in full; its unsupported tail must not become a new fact.

        Return only the unresolved suffix, so a later unproved page boundary
        can retain the pending left fragment without reclassifying a closed
        prefix as uncertain.
        """
        start = 0
        if run and not run[0].left_closed:
            self.diagnostics["CONTINUITY_OPEN_START"] += 1
            self.defer(run)
            return run
        while start < len(run):
            if len(run) - start < 2:
                if start > 0 and not _terminal(run[start].unit["text"]):
                    self.diagnostics["CONTINUITY_OPEN_END"] += 1
                    self.defer(run[start:])
                    return run[start:]
                elif start == 0:
                    # No measured edge exists for a singleton. A physical
                    # block can contain headings, list introductions or several
                    # sentences, so missing terminal punctuation does not prove
                    # that all its original business material is incomplete.
                    # It remains unassessed, never a fabricated closed window.
                    self.standalone_units += 1
                return []
            blocks: set[tuple[str, int, int]] = set()
            chars = 0
            end = start
            limited = False
            for index in range(start, len(run)):
                if not self.charge():
                    self.defer(run[start:])
                    return run[start:]
                item = run[index]
                blocks.add((item.source, item.page, item.block))
                chars += len(item.unit["text"])
                if (
                    index - start + 1 > self.limits["max_window_units"]
                    or len(blocks) > self.limits["max_window_blocks"]
                    or chars > self.limits["max_window_chars"]
                ):
                    limited = True
                    break
                if _terminal(item.unit["text"]):
                    end = index + 1
            if end == start:
                self.diagnostics[
                    "CONTINUITY_WINDOW_LIMIT" if limited else "CONTINUITY_OPEN_END"
                ] += 1
                self.defer(run[start:])
                return run[start:]
            if not limited and end != len(run):
                # A trailing open continuation cannot make a prior closed
                # statement incomplete. Keep only the closed prefix; the
                # suffix remains withheld and keeps the document partial.
                self.diagnostics["CONTINUITY_OPEN_END"] += 1
                prefix = run[start:end]
                if len(prefix) == 1:
                    # One complete original unit needs no borrowed continuity
                    # window. Its source owner can assess that unit alone.
                    self.standalone_units += 1
                elif not self.emit(prefix, proof[start : end - 1]):
                    self.defer(run[start:])
                    return run[start:]
                self.defer(run[end:])
                return run[end:]
            if not self.emit(run[start:end], proof[start : end - 1]):
                self.defer(run[start:])
                return run[start:]
            start = end
        return []


def build_native_continuity(
    units: Sequence[Mapping[str, Any]],
    *,
    provenance: Mapping[str, Mapping[str, Any]],
    sections: Sequence[Mapping[str, Any]] = (),
    unit_profiles: Mapping[str, Mapping[str, Any]] | None = None,
    limits: Mapping[str, Any] | None = None,
    work_budget: WorkBudget | None = None,
    source_page_flow: SourcePageFlow | None = None,
    source_contexts: Mapping[str, NativeSourceContext] | None = None,
) -> dict[str, Any]:
    """Return bounded original-ID context, reusing a supplied call-local physical owner."""
    state = _Analysis(limits, work_budget, source_page_flow, source_contexts)
    profiles = unit_profiles or {}
    headings: set[str] = set()
    unit_section = {}
    for section in sections:
        heads = section.get("heading_unit_ids", ())
        body = section.get("body_unit_ids", ())
        # Reserve before visiting IDs; exhausted callers must not copy a
        # document-sized section merely to discover that work cannot start.
        if not state.charge(1 + 2 * len(heads) + len(body)):
            break
        headings.update(heads)
        for uid in chain(heads, body):
            unit_section[uid] = section.get("section_id")
    run: list[_Native] = []
    proof: list[dict[str, Any]] = []
    seen = 0
    unexamined = None
    previous_observed = None
    furniture: list[Mapping[str, Any]] = []
    unresolved_page_tail: list[_Native] = []
    for unit in units:
        if state.stopped:
            break
        if seen >= state.limits["max_units"]:
            state.diagnostics["CONTINUITY_INPUT_LIMIT"] += 1
            unexamined = seen
            break
        seen += 1
        uid = str(unit.get("unit_id") or "")
        meta = provenance.get(uid, {})
        if (run and source_page_flow is not None and uid in source_page_flow.running_furniture_unit_ids
                and unit.get("hints", {}).get("source_id") == run[-1].source
                and unit.get("page") in (run[-1].page, run[-1].page + 1)
                and unit.get("ordinal") == run[-1].ordinal + 1 + len(furniture)
                and type(meta.get("paragraph_index")) is int and meta["paragraph_index"] >= 0
                and (not furniture or unit.get("page") >= furniture[-1]["page"])
                and (unit.get("page") != (furniture[-1]["page"] if furniture else run[-1].page)
                     or meta["paragraph_index"] == (furniture[-1]["paragraph_index"] if furniture else run[-1].paragraph) + 1)):
            if not state.charge():
                unexamined = seen - 1
                break
            furniture.append({"unit_id": uid, "page": unit["page"], "ordinal": unit["ordinal"],
                              "kind": meta.get("observed_kind", unit.get("kind")),
                              "paragraph_index": meta["paragraph_index"]})
            continue
        left_closed = type(meta.get("block_char_start")) is int and meta["block_char_start"] == 0
        if not left_closed and previous_observed is not None:
            previous_unit_id = previous_observed.get("unit_id")
            previous_meta = provenance.get(previous_unit_id, {}) if isinstance(previous_unit_id, str) else {}
            end, start = previous_meta.get("block_char_end"), meta.get("block_char_start")
            left_closed = bool(
                type(end) is int and type(start) is int and 0 <= start - end <= 2
                and meta.get("block_sha256") and meta.get("block_sha256") == previous_meta.get("block_sha256")
                and meta.get("source_id") == previous_meta.get("source_id")
                and unit.get("page") == previous_observed.get("page")
                and (_terminal(previous_observed.get("text", ""))
                     or previous_observed.get("unit_id") in headings))
        current = state.native(
            unit,
            provenance.get(uid, {}),
            profiles.get(uid, {}),
            unit_section.get(uid),
            headings,
            left_closed,
        )
        page_tail_candidate = bool(
            current is None and run and source_page_flow is not None
            and not _terminal(run[-1].unit["text"])
            and run[-1].bbox[3] >= 0.8 * run[-1].frame[3]
        )
        if current is not None and unresolved_page_tail:
            if state.pending_page_transition(unresolved_page_tail[-1], current):
                # Unproved headers/footers cannot be silently filtered into a
                # positive edge, nor can their gap certify the right fragment.
                # finish() supplies only the unresolved left suffix. Preserve
                # it with the right fragment; defer() removes any duplicates
                # and the closed prefix can never be reclassified as pending.
                state.diagnostics["CONTINUITY_PAGE_BOUNDARY_UNPROVEN"] += 1
                state.defer([*unresolved_page_tail, current])
                unresolved_page_tail = []
            elif not (current.page == unresolved_page_tail[-1].page + 1
                      and current.bbox[1] > 0.2 * current.frame[3]):
                unresolved_page_tail = []
        elif page_tail_candidate:
            unresolved_page_tail = list(run)
        previous_observed = unit
        if state.stopped:
            unexamined = seen - 1
            break
        column_witnesses = []
        if (run and current is not None and run[-1].column is None and current.column is None
                and indented_terminal_tail_proof(run[-1].bbox, current.bbox, run[-1].font[0],
                                                run[-1].unit["text"], current.unit["text"]) is not None):
            # Bounded read-only lookahead: do not cross an excluded unit or an
            # input limit, and charge each validation to this same analysis.
            for witness_index in range(seen, min(len(units), seen + 3, state.limits["max_units"])):
                witness_wire = units[witness_index]
                witness_uid = str(witness_wire.get("unit_id") or "")
                witness = state.native(witness_wire, provenance.get(witness_uid, {}),
                    profiles.get(witness_uid, {}), unit_section.get(witness_uid), headings, False)
                if witness is None or state.stopped:
                    break
                column_witnesses.append(witness)
        # A positively measured body neighbour is not necessarily a wrapped
        # sentence. Preserve the statement boundary while making its physical
        # proof available to the source-owned explicit-qualifier closure.
        adjacent = state.edge(run[-1], current, column_witnesses=column_witnesses,
                              furniture=furniture, allow_complete_boundary=True
                              ) if run and current is not None else None
        edge = adjacent
        if adjacent is not None and run and current is not None:
            left = run[-1]
            if (2 <= state.limits["max_window_units"]
                    and len({(left.source, left.page, left.block),
                             (current.source, current.page, current.block)}) <= state.limits["max_window_blocks"]
                    and len(left.unit["text"]) + len(current.unit["text"]) <= state.limits["max_window_chars"]
                    and state.charge()):
                state.adjacency_edges.append({**adjacent, "source_id": left.source,
                    "basis": "source_body_adjacency", "physical_basis": adjacent["basis"]})
            if left.page == current.page and left.block != current.block and _terminal(left.unit["text"]):
                edge = None
        if (run and current is not None and edge is None and source_page_flow is not None
                and current.page == run[-1].page + 1
                and current.bbox[1] > 0.2 * current.frame[3]
                and run[-1].bbox[3] >= 0.8 * run[-1].frame[3]
                and not _terminal(run[-1].unit["text"]) and state.charge(len(run))):
            # PDF block order may put a bottom page counter before that page's
            # first body. It is not positive furniture proof, but cannot erase
            # a pending dependency before the actual top-body is observed.
            unresolved_page_tail = list(run)
        furniture = []
        if state.stopped:
            # Exhausting lookahead/edge work cannot turn the left half of an
            # unproven pair back into an independently admissible singleton.
            state.defer([*run, *([current] if current is not None else [])])
            unexamined = max(0, seen - 1 - len(run))
            run, proof = [], []
            break
        if edge:
            run.append(current)  # type: ignore[arg-type]
            proof.append(edge)
        else:
            unfinished_tail = state.finish(run, proof)
            if page_tail_candidate:
                # A nonterminal singleton is intentionally left unassessed by
                # finish(), but at a page edge it may continue behind an
                # excluded header/footer. Retain it until that boundary has
                # positive furniture proof or the transition is explicitly
                # deferred. A closed prefix before an open suffix is already
                # removed by finish() and is never revived here.
                unresolved_page_tail = unfinished_tail or (
                    run if run and not _terminal(run[-1].unit["text"]) else []
                )
            elif unresolved_page_tail and unfinished_tail:
                # The run may contain an already emitted closed prefix followed
                # by a still-open tail. Keep only finish()'s actual unresolved
                # suffix when the later page-boundary decision is made.
                tail_ids = {item.unit["unit_id"] for item in unresolved_page_tail}
                if any(item.unit["unit_id"] in tail_ids for item in run):
                    unresolved_page_tail = [
                        item for item in unfinished_tail if item.unit["unit_id"] in tail_ids
                    ]
            run, proof = ([current] if current is not None else []), []
    if not state.stopped and unexamined is None:
        state.finish(run, proof)
    else:
        state.defer(run)
        if unexamined is None:
            unexamined = seen
    return {
        "feature_version": NARRATIVE_CONTINUITY_FEATURE_VERSION,
        "windows": state.windows,
        "adjacency_edges": state.adjacency_edges,
        "work_units": state.work,
        "observed_unit_count": seen,
        "standalone_unit_count": state.standalone_units,
        "semantic_status": "not_evaluated",
        "source_page_flow": {"enabled": source_page_flow is not None,
            "coarse_complete": source_page_flow.coarse_complete if source_page_flow else None,
            "unproven_page_count": len(source_page_flow.unproven_pages) if source_page_flow else 0},
        "complete": not state.diagnostics and not state.stopped,
        "deferred_unit_count": len(state.deferred),
        "deferred_unit_ids": state.deferred[:128],
        "deferred_limited": len(state.deferred) > 128,
        # Complete source-local ranges let callers withhold every known open
        # statement. The 128 example IDs above must never control admission.
        "deferred_unit_ranges": state.deferred_ranges,
        "unexamined_from_index": unexamined,
        "diagnostics": [
            {"code": code, "count": count}
            for code, count in sorted(state.diagnostics.items())
        ],
    }


__all__ = ["NARRATIVE_CONTINUITY_FEATURE_VERSION", "build_native_continuity"]
