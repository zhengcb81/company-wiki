"""Immutable, storage-independent location ranking contracts."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


_EXACT_DUPLICATE_PREFIX = "urn:company-wiki:duplicate:exact:sha256:"
_REJECTIONS_SEGMENT = ".rejections"


@dataclass(frozen=True)
class CatalogLocationCandidate:
    """The logical fields required to rank one registered source location."""

    location_id: str
    source_id: str | None
    root_id: str
    relative_path: str
    role: str
    location_status: str
    root_priority: int
    manifest_json: str | None


@dataclass(frozen=True)
class CatalogLocationAnnotation:
    """Immutable ranking result; it carries no root object or absolute path."""

    location_id: str
    source_id: str | None
    root_id: str
    relative_path: str
    role: str
    location_status: str
    root_priority: int
    manifest_json: str | None
    is_canonical: bool
    duplicate_relation: str
    duplicate_group_id: str
    canonical_location_id: str
    candidate_rank: int
    exclusion_reason: str


def annotate_locations(
    document_id: str,
    locations: tuple[CatalogLocationCandidate, ...],
) -> tuple[CatalogLocationAnnotation, ...]:
    """Rank candidates without mutating caller-owned rows.

    Duplicate canonical selection intentionally considers all active original
    locations, while candidate rank only includes reuse-qualified locations.
    """
    annotations = {
        location.location_id: CatalogLocationAnnotation(
            location_id=location.location_id,
            source_id=location.source_id,
            root_id=location.root_id,
            relative_path=location.relative_path,
            role=location.role,
            location_status=location.location_status,
            root_priority=location.root_priority,
            manifest_json=location.manifest_json,
            is_canonical=False,
            duplicate_relation="",
            duplicate_group_id="",
            canonical_location_id="",
            candidate_rank=0,
            exclusion_reason=_exclusion_reason(location),
        )
        for location in locations
    }
    if len(annotations) != len(locations):
        raise ValueError("location_id values must be unique within a document")

    groups: dict[str, list[CatalogLocationCandidate]] = {}
    for location in locations:
        if (
            location.role == "original_primary"
            and location.location_status == "active"
            and location.source_id
        ):
            groups.setdefault(location.source_id, []).append(location)

    for source_id, group in groups.items():
        ordered = sorted(group, key=_order_key)
        rank = 0
        for location in ordered:
            annotation = annotations[location.location_id]
            if not annotation.exclusion_reason:
                rank += 1
                annotations[location.location_id] = _replace_annotation(
                    annotation, candidate_rank=rank
                )

        canonical = ordered[0]
        annotations[canonical.location_id] = _replace_annotation(
            annotations[canonical.location_id],
            is_canonical=True,
            canonical_location_id=canonical.location_id,
        )
        if len(ordered) <= 1:
            continue
        group_id = _duplicate_group_id(document_id, source_id)
        annotations[canonical.location_id] = _replace_annotation(
            annotations[canonical.location_id], duplicate_group_id=group_id
        )
        for duplicate in ordered[1:]:
            annotations[duplicate.location_id] = _replace_annotation(
                annotations[duplicate.location_id],
                duplicate_relation="exact_copy",
                duplicate_group_id=group_id,
                canonical_location_id=canonical.location_id,
            )

    return tuple(annotations[item.location_id] for item in locations)


def _exclusion_reason(location: CatalogLocationCandidate) -> str:
    if location.role != "original_primary":
        return "role_not_original_primary"
    if location.location_status != "active":
        return f"location_status_{location.location_status}"
    if not location.source_id:
        return "source_id_missing"
    segments = location.relative_path.replace("\\", "/").split("/")
    if _REJECTIONS_SEGMENT in segments:
        return "rejections_path"
    return ""


def _order_key(location: CatalogLocationCandidate) -> tuple[int, str, str, str]:
    return (
        location.root_priority,
        location.root_id,
        location.relative_path,
        location.location_id,
    )


def _duplicate_group_id(document_id: str, source_id: str) -> str:
    digest = hashlib.sha256(f"{document_id}\0{source_id}".encode("utf-8")).hexdigest()
    return _EXACT_DUPLICATE_PREFIX + digest


def _replace_annotation(annotation: CatalogLocationAnnotation, **changes: object) -> CatalogLocationAnnotation:
    values = {
        field: getattr(annotation, field)
        for field in annotation.__dataclass_fields__
    }
    values.update(changes)
    return CatalogLocationAnnotation(**values)
