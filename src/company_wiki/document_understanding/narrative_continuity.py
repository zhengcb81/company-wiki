"""Bounded native PDF continuity over already observed source units.

This is provenance/geometry context, not another parser or fact classifier.
Only original IDs and measured proof leave this helper; composed text is never
persisted or sent to a model. Non-overlapping closed windows prevent context
unions from growing into a chapter.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from typing import Any

NARRATIVE_CONTINUITY_FEATURE_VERSION = "native-narrative-continuity/2"
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


def _terminal(text: str) -> bool:
    return (
        text.rstrip()
        .rstrip("\"'”’）)]》")
        .endswith(("。", "！", "？", ".", "!", "?", ";", "；"))
    )


@dataclass(frozen=True)
class _Native:
    unit: Mapping[str, Any]
    provenance: Mapping[str, Any]
    source: str
    page: int
    ordinal: int
    paragraph: int
    block: int
    bbox: tuple[float, ...]
    frame: tuple[Any, ...]
    scope: tuple[Any, ...]
    column: Any
    font: tuple[float, str]
    left_closed: bool


class _Analysis:
    def __init__(self, limits: Mapping[str, Any] | None):
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
        self.stopped = False
        self.diagnostics: Counter[str] = Counter()
        self.deferred: list[str] = []
        self.deferred_ranges: list[dict[str, Any]] = []
        self.windows: list[dict[str, Any]] = []
        self.standalone_units = 0

    def charge(self, amount: int = 1) -> bool:
        if self.stopped:
            return False
        if self.work + amount > self.limits["max_work_units"]:
            self.stopped = True
            self.diagnostics["CONTINUITY_WORK_LIMIT"] += 1
            return False
        self.work += amount
        return True

    def font(self, unit: Mapping[str, Any], frame: str) -> tuple[float, str] | None:
        runs = unit.get("hints", {}).get("font_runs", ())
        if (
            not isinstance(runs, (tuple, list))
            or not runs
            or not self.charge(len(runs))
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

    def native(
        self,
        unit: Mapping[str, Any],
        provenance: Mapping[str, Any],
        profile: Mapping[str, Any],
        section: Any,
        headings: set[str],
        left_closed: bool,
    ) -> _Native | None:
        if not self.charge():
            return None
        uid = unit.get("unit_id")
        if (
            not isinstance(uid, str)
            or uid in headings
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
        font = self.font(unit, frame)
        if font is None:
            return None
        key = hints.get("section_key", section)
        scope = (key, profile.get("reading_profile_key"), profile.get("section_role"))
        return _Native(
            unit,
            provenance,
            source,
            page,
            ordinal,
            paragraph,
            block,
            actual,
            (frame, rotation, width, height),
            scope,
            layout.get("column"),
            font,
            left_closed,
        )

    def edge(self, left: _Native, right: _Native) -> dict[str, Any] | None:
        if not self.charge():
            return None
        if (
            left.source != right.source
            or left.page != right.page
            or right.ordinal != left.ordinal + 1
            or right.paragraph != left.paragraph + 1
            or left.frame != right.frame
            or left.scope != right.scope
            or left.font != right.font
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
        if _terminal(left.unit["text"]) or right.block != left.block + 1:
            return None
        a, b = left.bbox, right.bbox
        size = left.font[0]
        overlap = min(a[2], b[2]) - max(a[0], b[0])
        gap = b[1] - a[3]
        if (
            abs(a[0] - b[0]) > 2.1 * size
            or overlap <= 0
            or overlap < 0.8 * min(a[2] - a[0], b[2] - b[0])
            or not 0 <= gap <= size
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
                "page": run[0].page,
                "member_unit_ids": ids,
                "required_unit_ids": ids,
                "proof": proof,
            }
        )
        return True

    def defer(self, run: list[_Native]) -> None:
        if not run:
            return
        self.deferred.extend(item.unit["unit_id"] for item in run)
        self.deferred_ranges.append(
            {
                "source_id": run[0].source,
                "page": run[0].page,
                "first_ordinal": run[0].ordinal,
                "last_ordinal": run[-1].ordinal,
            }
        )

    def finish(self, run: list[_Native], proof: list[dict[str, Any]]) -> None:
        """Cut only at an observed complete statement, never a resource prefix.

        Multiple sentence fragments can occupy the same original block. If a
        measured run exceeds a window, the last actual terminator inside the
        bound closes the preceding statement. An unclosed long statement is
        deferred in full; its unsupported tail must not become a new fact.
        """
        start = 0
        if run and not run[0].left_closed:
            self.diagnostics["CONTINUITY_OPEN_START"] += 1
            self.defer(run)
            return
        while start < len(run):
            if len(run) - start < 2:
                if start > 0 and not _terminal(run[start].unit["text"]):
                    self.diagnostics["CONTINUITY_OPEN_END"] += 1
                    self.defer(run[start:])
                elif start == 0:
                    # No measured edge exists for a singleton. A physical
                    # block can contain headings, list introductions or several
                    # sentences, so missing terminal punctuation does not prove
                    # that all its original business material is incomplete.
                    # It remains unassessed, never a fabricated closed window.
                    self.standalone_units += 1
                return
            blocks: set[int] = set()
            chars = 0
            end = start
            limited = False
            for index in range(start, len(run)):
                if not self.charge():
                    self.defer(run[start:])
                    return
                item = run[index]
                blocks.add(item.block)
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
                return
            if not limited and end != len(run):
                # A complete first statement cannot confer completeness on an
                # observed open continuation at the end of the run.
                self.diagnostics["CONTINUITY_OPEN_END"] += 1
                self.defer(run[start:])
                return
            if not self.emit(run[start:end], proof[start : end - 1]):
                self.defer(run[start:])
                return
            start = end


def build_native_continuity(
    units: Sequence[Mapping[str, Any]],
    *,
    provenance: Mapping[str, Mapping[str, Any]],
    sections: Sequence[Mapping[str, Any]] = (),
    unit_profiles: Mapping[str, Mapping[str, Any]] | None = None,
    limits: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return only bounded original-ID context whose native continuity is proven."""
    state = _Analysis(limits)
    profiles = unit_profiles or {}
    headings: set[str] = set()
    unit_section = {}
    for section in sections:
        ids = tuple(section.get("heading_unit_ids", ())) + tuple(
            section.get("body_unit_ids", ())
        )
        if not state.charge(1 + len(ids)):
            break
        headings.update(section.get("heading_unit_ids", ()))
        for uid in ids:
            unit_section[uid] = section.get("section_id")
    run: list[_Native] = []
    proof: list[dict[str, Any]] = []
    seen = 0
    unexamined = None
    previous_observed = None
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
        left_closed = type(meta.get("block_char_start")) is int and meta["block_char_start"] == 0
        if not left_closed and previous_observed is not None:
            previous_meta = provenance.get(previous_observed.get("unit_id"), {})
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
        previous_observed = unit
        if state.stopped:
            unexamined = seen - 1
            break
        edge = state.edge(run[-1], current) if run and current is not None else None
        if edge:
            run.append(current)  # type: ignore[arg-type]
            proof.append(edge)
        else:
            state.finish(run, proof)
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
        "work_units": state.work,
        "observed_unit_count": seen,
        "standalone_unit_count": state.standalone_units,
        "semantic_status": "not_evaluated",
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
