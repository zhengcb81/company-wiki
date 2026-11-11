"""Typed, storage-independent document candidate query contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal

from .location_annotation import CatalogLocationAnnotation

CandidateOrder = Literal["document_id", "published_date"]


@dataclass(frozen=True)
class CatalogDocumentCandidateQuery:
    """A bounded query for document candidates matching logical identity tokens."""

    identity_tokens: tuple[str, ...]
    limit: int
    as_of_date: str | None = None
    document_kinds: tuple[str, ...] = ()
    after_document_id: str | None = None
    order: CandidateOrder = "published_date"

    def __post_init__(self) -> None:
        if isinstance(self.limit, bool) or not isinstance(self.limit, int):
            raise TypeError("limit must be an integer")
        if self.limit <= 0:
            raise ValueError("limit must be positive")
        if self.order not in {"document_id", "published_date"}:
            raise ValueError("unsupported candidate order")
        if not isinstance(self.identity_tokens, tuple):
            raise TypeError("identity_tokens must be a tuple")
        if not all(isinstance(token, str) and token for token in self.identity_tokens):
            raise ValueError("identity_tokens must contain non-empty text")
        if not isinstance(self.document_kinds, tuple):
            raise TypeError("document_kinds must be a tuple")
        if not all(isinstance(kind, str) and kind for kind in self.document_kinds):
            raise ValueError("document_kinds must contain non-empty text")
        if self.as_of_date is not None and not self.as_of_date:
            raise ValueError("as_of_date must be non-empty text")
        if self.after_document_id is not None:
            if not self.after_document_id:
                raise ValueError("after_document_id must be non-empty text")
            if self.order != "document_id":
                raise ValueError("document_id cursors require document_id ordering")


@dataclass(frozen=True)
class CatalogEntityRecord:
    """Pathless entity identity projected with a document candidate."""

    entity_id: str
    name: str
    entity_kind: str


@dataclass(frozen=True)
class CatalogDocumentCandidate:
    """Detached catalog metadata required by company source listing."""

    document_id: str
    source_id: str | None
    title: str
    document_kind: str
    published_date: str | None
    source_status: str
    metadata: Mapping[str, Any]
    content_sha256: str | None
    byte_size: int | None
    mime_type: str | None
    entities: tuple[CatalogEntityRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        object.__setattr__(self, "metadata", _freeze_json_value(self.metadata))

    def metadata_as_dict(self) -> dict[str, Any]:
        """Return an independent mutable JSON-shaped copy for a consumer."""
        thawed = _thaw_json_value(self.metadata)
        if not isinstance(thawed, dict):
            raise TypeError("metadata root must be an object")
        return thawed


@dataclass(frozen=True)
class CatalogDuplicateLocationRecord:
    """Catalog-owned exact-copy inventory row for the retired read-only view."""

    document_id: str
    source_id: str
    content_sha256: str
    title: str
    document_kind: str
    published_date: str | None
    absolute_path: str
    observed_size: int | None
    observed_mtime_ns: int | None
    entities: tuple[str, ...]
    annotation: CatalogLocationAnnotation


class CatalogQueryUnavailable(RuntimeError):
    """Storage-level query failure translated at the Catalog boundary."""


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"metadata contains a non-JSON value: {type(value).__name__}")


def _thaw_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value
