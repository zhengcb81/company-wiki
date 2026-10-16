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

from dataclasses import dataclass, replace
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
    text_clipped: bool = False
    parent_id: str | None = None


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
    probe_limits: Limits = Limits()
    native_source_signals: Mapping[str, Any] | None = None
    reserved_unit_ids: tuple[str, ...] = ()
    is_attachment_scope: bool = False

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
                parent_id=_optional_str((item.get("hints") or {}).get("source_id"))
                if isinstance(item.get("hints"), Mapping) else None,
            )
        )
    return tuple(units)


def _spread_sample(units: list[UnitRef], count: int) -> list[UnitRef]:
    """Deterministic endpoints and evenly spaced interior positions."""
    if count <= 0 or not units:
        return []
    if len(units) <= count:
        return units
    if count == 1:
        return [units[len(units) // 2]]
    return [units[index * (len(units) - 1) // (count - 1)] for index in range(count)]


def _stratified_probes(units: tuple[UnitRef, ...], limit: int,
                       reserved_unit_ids: tuple[str, ...] = ()) -> tuple[UnitRef, ...]:
    """Reserve opportunities for cover, span headings and ordinary body.

    A dense front TOC cannot exhaust the heading allocation. Sampling each lane
    across its own span retains tail headings and non-heading paragraphs within
    the same caller budget. Ordinal values and IDs do not affect this allocation.
    """
    if limit <= 0:
        return ()
    if len(units) <= limit:
        return units
    cover_count = min(3, max(1, limit // 4))
    reserved = set(reserved_unit_ids[:limit])
    selected = {unit.unit_id for unit in units if unit.unit_id in reserved}
    for unit in units[:cover_count]:
        if len(selected) < limit:
            selected.add(unit.unit_id)
    remainder = [unit for unit in units if unit.unit_id not in selected]
    headings = [unit for unit in remainder if _is_heading_like(unit)]
    body = [unit for unit in remainder if not _is_heading_like(unit)]
    available = limit - len(selected)
    heading_count = min(len(headings), (available + 1) // 2)
    body_count = min(len(body), available - heading_count)
    # If one lane is short, transfer its unused places to the other lane.
    heading_count = min(len(headings), available - body_count)
    body_count = min(len(body), available - heading_count)
    selected.update(unit.unit_id for unit in _spread_sample(headings, heading_count))
    selected.update(unit.unit_id for unit in _spread_sample(body, body_count))
    return tuple(unit for unit in units if unit.unit_id in selected)


def _bounded_probe_texts(
    probes: tuple[UnitRef, ...], budget: int
) -> tuple[tuple[UnitRef, ...], int, bool]:
    """Share character budget before consuming any front unit's long text.

    Short units retain their full text. Long units receive a bounded prefix under
    fair allocation; any prefix is explicitly reported as limited coverage. No
    copy of the caller observation is altered and only consumed characters count.
    """
    costs = [len(unit.text) for unit in probes]
    total = sum(costs)
    if total <= budget:
        return probes, total, False
    allowances = [0] * len(probes)
    remaining = budget
    pending = list(range(len(probes)))
    while pending and remaining:
        share = remaining // len(pending)
        if share == 0:
            for index in pending[:remaining]:
                allowances[index] += 1
            break
        next_pending = []
        for index in pending:
            consumed = min(costs[index] - allowances[index], share)
            allowances[index] += consumed
            remaining -= consumed
            if allowances[index] < costs[index]:
                next_pending.append(index)
        pending = next_pending
    kept = tuple(
        replace(unit, text=unit.text[:allowed], text_clipped=True) if allowed < len(unit.text) else unit
        for unit, allowed in zip(probes, allowances)
        if allowed or not unit.text
    )
    return kept, sum(len(unit.text) for unit in kept), True


def _is_heading_like(unit: UnitRef) -> bool:
    if unit.kind in {"heading", "title"}:
        return True
    return unit.heading_level is not None


def parse_observation(
    observation: Mapping[str, Any] | Observation, limits: Mapping[str, Any] | None = None
) -> Observation:
    """Validate and reduce a ``du-input/1`` observation. Never mutates the input."""
    if isinstance(observation, Observation):
        resolved = Limits.from_mapping(limits) if limits is not None else observation.probe_limits
        if resolved == observation.probe_limits:
            return observation
        return reprobe_observation(observation, limits=resolved)
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
    kept, probed_chars, char_limited = _bounded_probe_texts(
        probes, resolved_limits.max_probe_chars
    )
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
        probes=kept,
        probed_chars=probed_chars,
        probe_limited=len(probes) < len(units) or char_limited,
        char_limited=char_limited,
        probe_limits=resolved_limits,
    )


def reprobe_observation(observation: Observation, *, units: tuple[UnitRef, ...] | None = None,
                        limits: Limits | None = None, reserved_unit_ids: tuple[str, ...] | None = None) -> Observation:
    """Project a known native scope with the one existing bounded allocator."""
    actual = observation.units if units is None else units
    resolved = observation.probe_limits if limits is None else limits
    reserved = observation.reserved_unit_ids if reserved_unit_ids is None else reserved_unit_ids
    probes = _stratified_probes(actual, resolved.max_probe_units, reserved)
    kept, chars, clipped = _bounded_probe_texts(probes, resolved.max_probe_chars)
    return replace(observation, units=actual, probes=kept, probed_chars=chars,
                   probe_limited=len(probes) < len(actual) or clipped, char_limited=clipped,
                   probe_limits=resolved, reserved_unit_ids=reserved)


__all__ = [
    "Limits",
    "Observation",
    "ObservationError",
    "UnitRef",
    "parse_observation",
]
