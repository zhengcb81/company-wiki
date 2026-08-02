"""Strict v1 source manifest value object and deterministic file builder."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from datetime import date, datetime
from enum import Enum
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import unicodedata
from typing import Any


SOURCE_MANIFEST_SCHEMA_VERSION = "1.0.0"
SOURCE_ID_PREFIX = "urn:company-wiki:source:sha256:"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
    r"(?:\+[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$"
)
_MIME_RE = re.compile(r"^[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*$")
_SOURCE_ID_RE = re.compile(rf"^{re.escape(SOURCE_ID_PREFIX)}[0-9a-f]{{64}}$")


class SourceManifestError(ValueError):
    """Base error for invalid source-manifest data."""


class SourceManifestMismatchError(SourceManifestError):
    """Raised when raw bytes or their location no longer match a manifest."""


class SourceType(str, Enum):
    """Physical upstream source types; model output is deliberately excluded."""

    REGULATORY_FILING = "regulatory_filing"
    COMPANY_ANNOUNCEMENT = "company_announcement"
    INVESTOR_RELATIONS = "investor_relations"
    BROKER_RESEARCH = "broker_research"
    ORIGINAL_NEWS = "original_news"
    AGGREGATED_NEWS = "aggregated_news"
    PROSPECTUS = "prospectus"
    OTHER = "other"


class ImmutableStatus(str, Enum):
    VERIFIED = "verified"
    QUARANTINED = "quarantined"


def source_id_for_sha256(content_sha256: str) -> str:
    _require_sha256(content_sha256, "content_sha256")
    return SOURCE_ID_PREFIX + content_sha256


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if not value or value != value.strip():
        raise SourceManifestError(f"{field_name} must be non-empty trimmed text")
    if unicodedata.normalize("NFC", value) != value:
        raise SourceManifestError(f"{field_name} must use Unicode NFC")
    if any(ord(char) < 32 for char in value):
        raise SourceManifestError(f"{field_name} must not contain control characters")
    return value


def _require_sha256(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise SourceManifestError(
            f"{field_name} must be a lowercase 64-character SHA-256"
        )
    return value


def _require_original_path(value: Any) -> str:
    value = _require_text(value, "original_path")
    if "\\" in value:
        raise SourceManifestError("original_path must use forward slashes")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise SourceManifestError("original_path must be repository-relative")
    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise SourceManifestError("original_path must not contain empty or dot segments")
    if PurePosixPath(value).as_posix() != value:
        raise SourceManifestError("original_path is not canonical POSIX text")
    return value


def _normalize_entity_ids(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError("entity_ids must be an array of stable entity IDs")
    normalized = {_require_text(item, "entity_id") for item in value}
    if not normalized:
        raise SourceManifestError("entity_ids must contain at least one stable entity ID")
    return tuple(sorted(normalized))


def _require_published_date(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("published_date must be YYYY-MM-DD text or null")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SourceManifestError("published_date must be a valid YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise SourceManifestError("published_date must be canonical YYYY-MM-DD")
    return value


def _require_retrieved_at(value: Any) -> str:
    if not isinstance(value, str) or not _UTC_RE.fullmatch(value):
        raise SourceManifestError("retrieved_at must be UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise SourceManifestError("retrieved_at must be a valid UTC timestamp") from exc
    return value


def _require_semver(value: Any) -> str:
    value = _require_text(value, "collector_version")
    if not _SEMVER_RE.fullmatch(value):
        raise SourceManifestError("collector_version must be semantic version text")
    return value


def _require_mime(value: Any) -> str:
    value = _require_text(value, "mime_type")
    if not _MIME_RE.fullmatch(value):
        raise SourceManifestError("mime_type must be a lowercase type/subtype")
    return value


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_source(root: Path, file_path: Path) -> tuple[Path, str]:
    if not isinstance(root, Path) or not isinstance(file_path, Path):
        raise TypeError("root and file_path must be pathlib.Path values")
    root_resolved = root.resolve(strict=True)
    if not root_resolved.is_dir():
        raise SourceManifestError("root must be an existing directory")
    file_resolved = file_path.resolve(strict=True)
    if not file_resolved.is_file():
        raise SourceManifestError("file_path must identify a regular file")
    try:
        relative = file_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise SourceManifestError("file_path must remain inside root") from exc
    original_path = unicodedata.normalize("NFC", relative.as_posix())
    return file_resolved, _require_original_path(original_path)


@dataclass(frozen=True)
class SourceManifest:
    schema_version: str
    source_id: str
    entity_ids: tuple[str, ...]
    original_path: str
    content_sha256: str
    source_type: SourceType
    published_date: str | None
    retrieved_at: str
    collector_name: str
    collector_version: str
    mime_type: str
    byte_size: int
    immutable_status: ImmutableStatus

    def __post_init__(self) -> None:
        if self.schema_version != SOURCE_MANIFEST_SCHEMA_VERSION:
            raise SourceManifestError(
                f"schema_version must be {SOURCE_MANIFEST_SCHEMA_VERSION}"
            )

        content_sha256 = _require_sha256(self.content_sha256, "content_sha256")
        if not isinstance(self.source_id, str) or not _SOURCE_ID_RE.fullmatch(
            self.source_id
        ):
            raise SourceManifestError("source_id must be the canonical SHA-256 URN")
        if self.source_id != source_id_for_sha256(content_sha256):
            raise SourceManifestError("source_id must match content_sha256")

        object.__setattr__(self, "entity_ids", _normalize_entity_ids(self.entity_ids))
        object.__setattr__(self, "original_path", _require_original_path(self.original_path))
        object.__setattr__(self, "published_date", _require_published_date(self.published_date))
        object.__setattr__(self, "retrieved_at", _require_retrieved_at(self.retrieved_at))
        object.__setattr__(self, "collector_name", _require_text(self.collector_name, "collector_name"))
        object.__setattr__(self, "collector_version", _require_semver(self.collector_version))
        object.__setattr__(self, "mime_type", _require_mime(self.mime_type))

        if isinstance(self.byte_size, bool) or not isinstance(self.byte_size, int):
            raise TypeError("byte_size must be an integer")
        if self.byte_size <= 0:
            raise SourceManifestError("byte_size must be positive; empty sources are invalid")

        if not isinstance(self.source_type, SourceType):
            try:
                object.__setattr__(self, "source_type", SourceType(self.source_type))
            except (TypeError, ValueError) as exc:
                raise SourceManifestError("source_type is not an upstream source type") from exc
        if not isinstance(self.immutable_status, ImmutableStatus):
            try:
                object.__setattr__(
                    self, "immutable_status", ImmutableStatus(self.immutable_status)
                )
            except (TypeError, ValueError) as exc:
                raise SourceManifestError("immutable_status is invalid") from exc

    @classmethod
    def from_file(
        cls,
        *,
        root: Path,
        file_path: Path,
        entity_ids: Sequence[str],
        source_type: SourceType,
        published_date: str | None,
        retrieved_at: str,
        collector_name: str,
        collector_version: str,
        mime_type: str,
    ) -> "SourceManifest":
        resolved, original_path = _resolve_source(root, file_path)
        before = resolved.stat()
        if before.st_size <= 0:
            raise SourceManifestError("source file is empty")
        content_sha256 = _hash_file(resolved)
        after = resolved.stat()
        if (
            before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
        ):
            raise SourceManifestMismatchError("source changed while hashing")
        return cls(
            schema_version=SOURCE_MANIFEST_SCHEMA_VERSION,
            source_id=source_id_for_sha256(content_sha256),
            entity_ids=_normalize_entity_ids(entity_ids),
            original_path=original_path,
            content_sha256=content_sha256,
            source_type=source_type,
            published_date=published_date,
            retrieved_at=retrieved_at,
            collector_name=collector_name,
            collector_version=collector_version,
            mime_type=mime_type,
            byte_size=after.st_size,
            immutable_status=ImmutableStatus.VERIFIED,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SourceManifest":
        if not isinstance(data, Mapping):
            raise TypeError("source manifest input must be an object")
        known = {field.name for field in fields(cls)}
        supplied = set(data)
        unknown = supplied - known
        if unknown:
            raise SourceManifestError(f"source manifest unknown fields: {sorted(unknown)}")
        missing = known - supplied
        if missing:
            raise SourceManifestError(f"source manifest missing fields: {sorted(missing)}")
        prepared = dict(data)
        try:
            prepared["source_type"] = SourceType(prepared["source_type"])
        except (TypeError, ValueError) as exc:
            raise SourceManifestError("source_type is not an upstream source type") from exc
        try:
            prepared["immutable_status"] = ImmutableStatus(
                prepared["immutable_status"]
            )
        except (TypeError, ValueError) as exc:
            raise SourceManifestError("immutable_status is invalid") from exc
        prepared["entity_ids"] = _normalize_entity_ids(prepared["entity_ids"])
        return cls(**prepared)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_id": self.source_id,
            "entity_ids": list(self.entity_ids),
            "original_path": self.original_path,
            "content_sha256": self.content_sha256,
            "source_type": self.source_type.value,
            "published_date": self.published_date,
            "retrieved_at": self.retrieved_at,
            "collector_name": self.collector_name,
            "collector_version": self.collector_version,
            "mime_type": self.mime_type,
            "byte_size": self.byte_size,
            "immutable_status": self.immutable_status.value,
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    def verify_file(self, *, root: Path, file_path: Path) -> None:
        try:
            resolved, original_path = _resolve_source(root, file_path)
        except (FileNotFoundError, SourceManifestError) as exc:
            raise SourceManifestMismatchError(str(exc)) from exc
        if original_path != self.original_path:
            raise SourceManifestMismatchError("source location no longer matches manifest")
        stat = resolved.stat()
        if stat.st_size != self.byte_size:
            raise SourceManifestMismatchError("source byte_size no longer matches manifest")
        if _hash_file(resolved) != self.content_sha256:
            raise SourceManifestMismatchError("source SHA-256 no longer matches manifest")
