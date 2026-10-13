"""Frozen wire contract for the DU-STRUCTURE lane.

Everything here is a pure, JSON-serialisable view over an already-normalised
``du-input/1`` observation.  The module never opens a file, never reads
configuration, never calls a model, and never imports the profiles package.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA_VERSION = "du-structure/1"
INPUT_SCHEMA_VERSION = "du-input/1"

SECTION_ROLES = (
    "business",
    "industry",
    "management_discussion",
    "outlook",
    "risk",
    "operating_metrics",
    "fundraising",
    "financial_notes",
    "questions",
    "administrative",
    "unknown",
)

SEMANTIC_KINDS = (
    "paragraph_event",
    "qa_exchange",
    "project",
    "operating_table",
    "risk",
    "background",
)

RELATION_KINDS = (
    "continuation",
    "header_for",
    "footnote_for",
    "question_answer",
    "language_parallel",
    "section_cross_reference",
)

COMPLETENESS = ("complete", "partial", "unknown")
CONFIDENCE = ("high", "medium", "low", "unknown")
NATIVE_SCAN = ("complete", "partial", "unavailable")

DEFAULT_LIMITS: dict[str, int] = {
    "max_units": 50_000,
    "max_relations": 100_000,
    "max_group_members": 64,
    "max_work_units": 2_000_000,
}

# Continuation windows are deliberately small: an unbounded "carry the last
# section forward" rule is what let a page reset silently drop context in the
# legacy selector, and an unbounded forward carry would be just as wrong.
MAX_CONTINUATION_PAGES = 2
MAX_CONTINUATION_UNITS = 24


class StructureInputError(ValueError):
    """The observation is not a usable du-input/1 document."""


def resolve_limits(limits: Mapping[str, Any] | None) -> dict[str, int]:
    """Caller limits win when lower; the defaults are the ceiling."""
    resolved = dict(DEFAULT_LIMITS)
    if not limits:
        return resolved
    for name, ceiling in DEFAULT_LIMITS.items():
        if name not in limits:
            continue
        value = limits[name]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise StructureInputError(f"{name} must be a strictly positive int")
        resolved[name] = min(value, ceiling)
    return resolved


def _require_mapping(value: Any, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise StructureInputError(f"{what} must be a mapping")
    return value


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _bbox(value: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    coords = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            return None
        coords.append(float(item))
    x0, y0, x1, y1 = coords
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1, y1)


class ObservationUnit:
    """One input unit with its optional layout/hint evidence already parsed.

    Missing layout or hint values stay ``None``: the contract forbids guessing
    them into definite values.
    """

    __slots__ = (
        "unit_id",
        "ordinal",
        "locator",
        "page",
        "text",
        "kind",
        "language",
        "role",
        "bbox",
        "page_width",
        "page_height",
        "column",
        "heading_level",
        "table_id",
        "row",
        "column_index",
        "speaker",
        "turn_id",
        "dom_path",
        "has_layout",
        "has_hints",
        "layout_inconsistent",
    )

    def __init__(self, payload: Mapping[str, Any], position: int) -> None:
        unit_id = payload.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id:
            raise StructureInputError(f"unit at position {position} has no unit_id")
        text = payload.get("text")
        if not isinstance(text, str):
            raise StructureInputError(f"unit {unit_id} has no text")
        layout_value = payload.get("layout")
        hints_value = payload.get("hints")
        layout = layout_value if isinstance(layout_value, Mapping) else {}
        hints = hints_value if isinstance(hints_value, Mapping) else {}

        self.unit_id = unit_id
        ordinal = _optional_int(payload.get("ordinal"))
        self.ordinal = position if ordinal is None else ordinal
        self.locator = _optional_str(payload.get("locator"))
        self.page = _optional_int(payload.get("page"))
        self.text = text
        self.kind = (_optional_str(payload.get("kind")) or "unknown").lower()
        self.language = _optional_str(payload.get("language"))
        self.role = _optional_str(payload.get("role"))
        self.bbox = _bbox(layout.get("bbox"))
        self.page_width = _optional_float(layout.get("page_width"))
        self.page_height = _optional_float(layout.get("page_height"))
        self.column = _optional_int(layout.get("column"))
        self.heading_level = _optional_int(hints.get("heading_level"))
        self.table_id = _optional_str(hints.get("table_id"))
        self.row = _optional_int(hints.get("row"))
        self.column_index = _optional_int(hints.get("column"))
        self.speaker = _optional_str(hints.get("speaker"))
        self.turn_id = _optional_str(hints.get("turn_id"))
        self.dom_path = _optional_str(hints.get("dom_path"))
        self.has_layout = bool(layout)
        self.has_hints = bool(hints)
        # A declared box that cannot be used is not the same as no box: the
        # contradiction itself is evidence and must survive into diagnostics.
        raw_bbox = layout.get("bbox")
        self.layout_inconsistent = (
            raw_bbox is not None and self.bbox is None
        ) or self._column_conflicts_with_box()

    def _column_conflicts_with_box(self) -> bool:
        """A lane index that disagrees with the box's own half of the page."""
        if self.column is None or self.bbox is None or self.page_width is None:
            return False
        if self.page_width <= 0:
            return True
        midpoint = self.page_width / 2
        centre = (self.bbox[0] + self.bbox[2]) / 2
        if self.bbox[0] < 0 or self.bbox[2] > self.page_width:
            return True
        return (centre > midpoint) != (self.column > 0)

    @property
    def y0(self) -> float | None:
        return None if self.bbox is None else self.bbox[1]

    @property
    def y1(self) -> float | None:
        return None if self.bbox is None else self.bbox[3]

    @property
    def x0(self) -> float | None:
        return None if self.bbox is None else self.bbox[0]

    @property
    def x1(self) -> float | None:
        return None if self.bbox is None else self.bbox[2]

    @property
    def is_heading_kind(self) -> bool:
        return self.kind in {"heading", "html_heading"} or self.heading_level is not None

    @property
    def is_table_furniture(self) -> bool:
        return self.kind in {
            "table_caption",
            "table_header",
            "table_row",
            "html_table_cell",
        }

    @property
    def is_footnote(self) -> bool:
        return self.kind in {"footnote", "html_footnote"}

    @property
    def is_header_furniture(self) -> bool:
        return self.kind in {"header", "footer", "page_header", "page_footer"}

    def reference(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "ordinal": self.ordinal,
            "locator": self.locator,
            "page": self.page,
        }


def parse_observation(observation: Mapping[str, Any]) -> tuple[dict[str, Any], list[ObservationUnit]]:
    """Validate the envelope and return ``(envelope, units)``.

    Raises :class:`StructureInputError` for real data errors only: a wrong
    schema version, a malformed source reference, duplicate unit ids, a missing
    unit id, or units that cannot be ordered.  Optional fields are never a
    reason to reject a document.
    """
    document = _require_mapping(observation, "observation")
    if document.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise StructureInputError(
            f"schema_version must be {INPUT_SCHEMA_VERSION!r}"
        )
    source_ref = _require_mapping(document.get("source_ref"), "source_ref")
    source_id = source_ref.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        raise StructureInputError("source_ref.source_id is required")

    raw_units = document.get("units")
    if isinstance(raw_units, (str, bytes)) or not isinstance(raw_units, Sequence):
        raise StructureInputError("units must be a sequence")

    units: list[ObservationUnit] = []
    seen: set[str] = set()
    for position, payload in enumerate(raw_units):
        unit = ObservationUnit(_require_mapping(payload, "unit"), position)
        if unit.unit_id in seen:
            raise StructureInputError(f"duplicate unit_id {unit.unit_id!r}")
        seen.add(unit.unit_id)
        units.append(unit)

    coverage = document.get("coverage")
    metadata = document.get("metadata")
    envelope = {
        "source_id": source_id,
        "source_ref": {
            "source_id": source_id,
            "source_sha256": source_ref.get("source_sha256"),
        },
        "metadata": dict(metadata) if isinstance(metadata, Mapping) else {},
        "coverage": dict(coverage) if isinstance(coverage, Mapping) else {},
    }
    return envelope, units


__all__ = [
    "COMPLETENESS",
    "CONFIDENCE",
    "DEFAULT_LIMITS",
    "INPUT_SCHEMA_VERSION",
    "MAX_CONTINUATION_PAGES",
    "MAX_CONTINUATION_UNITS",
    "NATIVE_SCAN",
    "ObservationUnit",
    "RELATION_KINDS",
    "SCHEMA_VERSION",
    "SECTION_ROLES",
    "SEMANTIC_KINDS",
    "StructureInputError",
    "parse_observation",
    "resolve_limits",
]
