"""Validation and normalization of a ``du-input/1`` observation.

The router consumes the frozen observation shape and must reject *real* data errors
(wrong type, wrong schema, duplicate unit ids, unreferenceable units) while treating a
missing optional field as ``unknown``. Nothing here reads files, the clock, config or the
network, and nothing mutates the caller's mapping.

The module also owns the two input-side budgets the card requires: a unit budget and a
character budget. Probes are selected by document span rather than by taking the first N
units, because ``design.md`` section 2 shows the head of a 259-page report is cover and
TOC while the business narrative sits far later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from . import vocabulary as v


class ObservationError(ValueError):
    """A real data error in the observation; not a review gate."""


@dataclass(frozen=True)
class Limits:
    """Probe budgets. Profiles cannot raise these; only the caller can lower them."""

    max_probe_units: int = v.DEFAULT_MAX_PROBE_UNITS
    max_probe_chars: int = v.DEFAULT_MAX_PROBE_CHARS
    max_child_routes: int = v.DEFAULT_MAX_CHILD_ROUTES

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> "Limits":
        defaults = cls()
        if raw is None:
            return defaults
        if not isinstance(raw, Mapping):
            raise ObservationError(f"limits must be a mapping, got {type(raw)!r}")
        resolved: dict[str, int] = {}
        for field_name in ("max_probe_units", "max_probe_chars", "max_child_routes"):
            if field_name not in raw or raw[field_name] is None:
                resolved[field_name] = getattr(defaults, field_name)
                continue
            value = raw[field_name]
            if isinstance(value, bool) or not isinstance(value, int):
                raise ObservationError(f"{field_name} must be an int, got {value!r}")
            if value < 0:
                raise ObservationError(f"{field_name} must not be negative, got {value!r}")
            resolved[field_name] = value
        return cls(**resolved)


@dataclass(frozen=True)
class UnitRef:
    """One input unit, reduced to what routing needs."""

    unit_id: str
    ordinal: int
    locator: str | None
    page: int | None
    text: str
    kind: str | None
    language: str | None
    role: str | None
    heading_level: int | None


@dataclass(frozen=True)
class Observation:
    """A validated observation plus the probing view derived from it."""

    source_id: str | None
    source_sha256: str | None
    title: str | None
    declared_kind: str | None
    regime_claim: str | None
    form_type: str | None
    mime_type: str | None
    language: str | None
    revision: str | None
    native_scan: str
    opaque_pages: tuple[int, ...]
    deferred_pages: tuple[int, ...]
    units: tuple[UnitRef, ...]
    probes: tuple[UnitRef, ...]
    probed_chars: int
    probe_limited: bool
    char_limited: bool

    @property
    def unit_ids(self) -> tuple[str, ...]:
        return tuple(unit.unit_id for unit in self.units)

    def text_of(self, unit_id: str) -> str | None:
        for unit in self.units:
            if unit.unit_id == unit_id:
                return unit.text
        return None


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ObservationError(f"{label} must be a mapping, got {type(value)!r}")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _coerce_page(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    return None


def _int_pages(value: Any) -> tuple[int, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    pages: list[int] = []
    for item in value:
        page = _coerce_page(item)
        if page is not None and page not in pages:
            pages.append(page)
    return tuple(sorted(pages))


def _heading_level(hints: Any) -> int | None:
    if not isinstance(hints, Mapping):
        return None
    level = hints.get("heading_level")
    if isinstance(level, bool) or not isinstance(level, int):
        return None
    return level


def _parse_units(raw_units: Any) -> tuple[UnitRef, ...]:
    if not isinstance(raw_units, list):
        raise ObservationError(f"units must be a list, got {type(raw_units)!r}")
    units: list[UnitRef] = []
    seen: set[str] = set()
    for position, raw in enumerate(raw_units):
        item = _as_mapping(raw, f"units[{position}]")
        unit_id = item.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id:
            raise ObservationError(f"units[{position}].unit_id must be a non-empty string")
        if unit_id in seen:
            raise ObservationError(f"duplicate unit_id: {unit_id!r}")
        seen.add(unit_id)
        ordinal = item.get("ordinal")
        if isinstance(ordinal, bool) or not isinstance(ordinal, int):
            raise ObservationError(f"units[{position}].ordinal must be an int")
        text = item.get("text")
        if text is None:
            text = ""
        elif not isinstance(text, str):
            raise ObservationError(f"units[{position}].text must be a string or null")
        units.append(
            UnitRef(
                unit_id=unit_id,
                ordinal=ordinal,
                locator=_optional_str(item.get("locator")),
                page=_coerce_page(item.get("page")),
                text=text,
                kind=_optional_str(item.get("kind")),
                language=_optional_str(item.get("language")),
                role=_optional_str(item.get("role")),
                heading_level=_heading_level(item.get("hints")),
            )
        )
    return tuple(units)


def _stratified_probes(units: tuple[UnitRef, ...], limit: int) -> tuple[UnitRef, ...]:
    """Pick probe units across the document span, not just from the front.

    The strategy is deliberately simple and deterministic:

    1. keep every heading-like unit while the budget allows -- headings carry the
       section vocabulary that decides the family;
    2. fill the remainder with a stratified sample across the document span so a
       259-page report contributes evidence from the middle and the end, not only the
       cover and TOC.

    Ties keep the original order, so the same input always yields the same probes.
    """
    if limit <= 0:
        return ()
    if len(units) <= limit:
        return units
    selected: list[UnitRef] = []
    selected_ids: set[str] = set()

    def add(unit: UnitRef) -> None:
        if len(selected) >= limit or unit.unit_id in selected_ids:
            return
        selected_ids.add(unit.unit_id)
        selected.append(unit)

    for unit in units:
        if _is_heading_like(unit):
            add(unit)

    remaining = limit - len(selected)
    if remaining > 0:
        unfilled = [unit for unit in units if unit.unit_id not in selected_ids]
        if unfilled:
            step = len(unfilled) / remaining
            for index in range(remaining):
                offset = min(int(index * step), len(unfilled) - 1)
                add(unfilled[offset])

    for unit in units:
        if len(selected) >= limit:
            break
        add(unit)

    order = {unit.unit_id: position for position, unit in enumerate(units)}
    selected.sort(key=lambda unit: order[unit.unit_id])
    return tuple(selected)


def _is_heading_like(unit: UnitRef) -> bool:
    if unit.kind in {"heading", "title"}:
        return True
    return unit.heading_level is not None


def parse_observation(
    observation: Mapping[str, Any], limits: Mapping[str, Any] | None = None
) -> Observation:
    """Validate and reduce a ``du-input/1`` observation. Never mutates the input."""
    raw = _as_mapping(observation, "observation")
    schema_version = raw.get("schema_version")
    if schema_version != v.SCHEMA_VERSION_INPUT:
        raise ObservationError(
            f"unsupported schema_version: {schema_version!r}; expected {v.SCHEMA_VERSION_INPUT!r}"
        )
    if "units" not in raw:
        raise ObservationError("observation is missing the required 'units' key")

    resolved_limits = Limits.from_mapping(limits)
    source_ref = raw.get("source_ref")
    source_ref = source_ref if isinstance(source_ref, Mapping) else {}
    metadata = raw.get("metadata")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    coverage = raw.get("coverage")
    coverage = coverage if isinstance(coverage, Mapping) else {}

    units = _parse_units(raw.get("units"))

    native_scan = coverage.get("native_scan")
    native_scan = native_scan if isinstance(native_scan, str) and native_scan else "unknown"

    probes = _stratified_probes(units, resolved_limits.max_probe_units)
    probed_chars = 0
    kept: list[UnitRef] = []
    char_limited = False
    for unit in probes:
        cost = len(unit.text)
        if probed_chars + cost > resolved_limits.max_probe_chars:
            char_limited = True
            continue
        probed_chars += cost
        kept.append(unit)

    return Observation(
        source_id=_optional_str(source_ref.get("source_id")),
        source_sha256=_optional_str(source_ref.get("source_sha256")),
        title=_optional_str(metadata.get("title")),
        declared_kind=_optional_str(metadata.get("declared_kind")),
        regime_claim=_optional_str(metadata.get("regime")),
        form_type=_optional_str(metadata.get("form_type")),
        mime_type=_optional_str(metadata.get("mime_type")),
        language=_optional_str(metadata.get("language")),
        revision=_optional_str(metadata.get("revision")),
        native_scan=native_scan,
        opaque_pages=_int_pages(coverage.get("opaque_pages")),
        deferred_pages=_int_pages(coverage.get("deferred_pages")),
        units=units,
        probes=tuple(kept),
        probed_chars=probed_chars,
        probe_limited=len(probes) < len(units) or char_limited,
        char_limited=char_limited,
    )


__all__ = [
    "Limits",
    "Observation",
    "ObservationError",
    "UnitRef",
    "parse_observation",
]
