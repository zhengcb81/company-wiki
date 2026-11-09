"""Strict v1 source manifest value object and deterministic file builder."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from datetime import date, datetime
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any


SOURCE_MANIFEST_SCHEMA_VERSION = "1.0.0"
SOURCE_SUBJECT_MANIFEST_SCHEMA_VERSION = "2.0.0"
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
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")


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


def _require_text(value: Any, field_name: str, *, require_nfc: bool = True) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if not value or value != value.strip():
        raise SourceManifestError(f"{field_name} must be non-empty trimmed text")
    if require_nfc and not unicodedata.is_normalized("NFC", value):
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
    value = _require_text(value, "original_path", require_nfc=False)
    if "\\" in value:
        raise SourceManifestError("original_path must use forward slashes")
    if value.startswith("/") or _WINDOWS_DRIVE_RE.match(value):
        raise SourceManifestError("original_path must be repository-relative")
    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise SourceManifestError("original_path must not contain empty or dot segments")
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


def _file_observation(path: Path) -> tuple[int, int, int, int, int]:
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def _stable_file_identity(
    path: Path, *, expected_byte_size: int | None = None,
) -> tuple[str, int]:
    before = _file_observation(path)
    byte_size = before[2]
    if expected_byte_size is not None and byte_size != expected_byte_size:
        raise SourceManifestMismatchError("source byte_size no longer matches manifest")
    if byte_size <= 0:
        raise SourceManifestError("source file is empty")
    content_sha256 = _hash_file(path)
    if before != _file_observation(path):
        raise SourceManifestMismatchError("source changed while hashing")
    return content_sha256, byte_size


def _resolve_root(root: Path) -> Path:
    if not isinstance(root, Path):
        raise TypeError("root must be pathlib.Path")
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise SourceManifestError("root must be an existing directory")
    return resolved


def _resolve_file(root: Path, file_path: Path) -> tuple[Path, str]:
    file_resolved = file_path.resolve(strict=True)
    try:
        relative = file_resolved.relative_to(root)
    except ValueError as exc:
        raise SourceManifestError("file_path must remain inside root") from exc
    if not file_resolved.is_file():
        raise SourceManifestError("file_path must identify a regular file")
    return file_resolved, _require_original_path(relative.as_posix())


def _legacy_nfc_path(root: Path, original_path: str) -> Path:
    """Recover a uniquely spelled old v1 location without leaving the root."""
    parent = root
    for segment in original_path.split("/"):
        matches = (
            entry for entry in parent.iterdir()
            if unicodedata.normalize("NFC", entry.name) == segment
        )
        match = next(matches, None)
        if match is None:
            raise SourceManifestMismatchError("legacy NFC source location was not found")
        if next(matches, None) is not None:
            raise SourceManifestMismatchError("legacy NFC source location is ambiguous")
        current = match.resolve(strict=True)
        if not current.is_relative_to(root):
            raise SourceManifestMismatchError("file_path must remain inside root")
        if (current.parent.as_posix() != parent.as_posix()
                or unicodedata.normalize("NFC", current.name) != segment):
            raise SourceManifestMismatchError("source location no longer matches manifest")
        parent = current
    return parent


def _manifest_file(root: Path, original_path: str) -> Path:
    try:
        resolved, observed = _resolve_file(root, root / original_path)
    except FileNotFoundError:
        if not unicodedata.is_normalized("NFC", original_path):
            raise
    else:
        if observed == original_path:
            return resolved
        if unicodedata.normalize("NFC", observed) != original_path:
            raise SourceManifestMismatchError("source location no longer matches manifest")
    # Some filesystems resolve canonically equivalent names implicitly. Confirm
    # that the physical spelling is unique before using that compatibility path.
    resolved, observed = _resolve_file(root, _legacy_nfc_path(root, original_path))
    if unicodedata.normalize("NFC", observed) != original_path:
        raise SourceManifestMismatchError("source location no longer matches manifest")
    return resolved


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
        if not isinstance(file_path, Path):
            raise TypeError("file_path must be pathlib.Path")
        resolved, original_path = _resolve_file(_resolve_root(root), file_path)
        content_sha256, byte_size = _stable_file_identity(resolved)
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
            byte_size=byte_size,
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
        return cls(**dict(data))

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

    def verify_file(self, *, root: Path, file_path: Path | None = None) -> None:
        """Check the pinned locator and bytes, optionally matching a caller's file."""
        if file_path is not None and not isinstance(file_path, Path):
            raise TypeError("file_path must be pathlib.Path")
        try:
            root_resolved = _resolve_root(root)
            requested = root_resolved / self.original_path
            if file_path is None or file_path.absolute().as_posix() == requested.as_posix():
                resolved = _manifest_file(root_resolved, self.original_path)
            else:
                resolved, observed = _resolve_file(root_resolved, file_path)
                if observed != self.original_path and (
                    unicodedata.normalize("NFC", observed) != self.original_path
                    or _manifest_file(root_resolved, self.original_path).as_posix() != resolved.as_posix()
                ):
                    raise SourceManifestMismatchError("source location no longer matches manifest")
        except SourceManifestMismatchError:
            raise
        except (FileNotFoundError, NotADirectoryError, SourceManifestError) as exc:
            raise SourceManifestMismatchError(str(exc)) from exc
        try:
            content_sha256, _ = _stable_file_identity(
                resolved, expected_byte_size=self.byte_size,
            )
        except FileNotFoundError as exc:
            raise SourceManifestMismatchError("source disappeared while hashing") from exc
        if content_sha256 != self.content_sha256:
            raise SourceManifestMismatchError("source SHA-256 no longer matches manifest")


_SUBJECT_KINDS = frozenset({"single_issuer", "multi_issuer_event", "unattributed"})
_SUBJECT_ATTRIBUTIONS = frozenset({"none", "partial", "full", "unknown"})
_SUBJECT_FIELDS = frozenset({
    "kind", "attribution_status", "event_namespace", "event_id", "issuer_refs",
})
_SUBJECT_ISSUER_REF_FIELDS = frozenset({
    "provider_company_id", "provider_activity_company_id", "stock_code",
    "company_name", "market", "security_id", "canonical_name",
})
_SUBJECT_MANIFEST_FIELDS = frozenset({
    "schema_version", "source_id", "subject", "original_path",
    "content_sha256", "mime_type", "byte_size", "collector_name",
    "collector_version", "retrieved_at", "published_date",
})


def _validate_subject(value: Any) -> dict[str, Any]:
    """Structural subject validation without importing the catalog layer.

    v2.0.0 exists because manifest 1.0.0 requires at least one entity id:
    shared pages with unknown or partial attribution need an honest subject
    instead of a fabricated entity.  Issuer refs stay associated subjects,
    never owners.
    """
    if not isinstance(value, dict) or not set(value) <= _SUBJECT_FIELDS:
        raise SourceManifestError("subject fields are invalid")
    kind = value.get("kind")
    if kind not in _SUBJECT_KINDS:
        raise SourceManifestError("subject kind is invalid")
    attribution = value.get("attribution_status")
    if attribution not in _SUBJECT_ATTRIBUTIONS:
        raise SourceManifestError("subject attribution_status is invalid")
    refs = value.get("issuer_refs", [])
    if not isinstance(refs, list):
        raise SourceManifestError("subject issuer_refs must be an array")
    normalized_refs = []
    for ref in refs:
        if not isinstance(ref, dict) or not set(ref) <= _SUBJECT_ISSUER_REF_FIELDS:
            raise SourceManifestError("subject issuer_ref fields are invalid")
        normalized_refs.append(dict(ref))
    if kind == "single_issuer" and len(normalized_refs) != 1:
        raise SourceManifestError("single_issuer subject requires one issuer ref")
    if kind == "unattributed" and normalized_refs:
        raise SourceManifestError("unattributed subject has no issuer refs")
    payload: dict[str, Any] = {
        "kind": kind,
        "attribution_status": attribution,
        "issuer_refs": normalized_refs,
    }
    if kind == "multi_issuer_event":
        for name in ("event_namespace", "event_id"):
            payload[name] = _require_text(value.get(name), "subject " + name)
    return payload


@dataclass(frozen=True)
class SourceSubjectManifest:
    """Manifest 2.0.0: byte identity plus an honest, typed source subject.

    Old manifests stay 1.0.0 and strictly unchanged; fully identified legacy
    sources are not rewritten.
    """

    schema_version: str
    source_id: str
    subject: dict[str, Any]
    original_path: str
    content_sha256: str
    mime_type: str
    byte_size: int
    collector_name: str
    collector_version: str
    retrieved_at: str
    published_date: str | None

    def __post_init__(self) -> None:
        if self.schema_version != SOURCE_SUBJECT_MANIFEST_SCHEMA_VERSION:
            raise SourceManifestError(
                f"schema_version must be {SOURCE_SUBJECT_MANIFEST_SCHEMA_VERSION}"
            )
        content_sha256 = _require_sha256(self.content_sha256, "content_sha256")
        if (not isinstance(self.source_id, str)
                or not _SOURCE_ID_RE.fullmatch(self.source_id)
                or self.source_id != source_id_for_sha256(content_sha256)):
            raise SourceManifestError("source_id must match content_sha256")
        object.__setattr__(self, "subject", _validate_subject(self.subject))
        object.__setattr__(
            self, "original_path", _require_original_path(self.original_path))
        object.__setattr__(
            self, "published_date", _require_published_date(self.published_date))
        object.__setattr__(self, "retrieved_at", _require_retrieved_at(self.retrieved_at))
        object.__setattr__(
            self, "collector_name", _require_text(self.collector_name, "collector_name"))
        object.__setattr__(
            self, "collector_version", _require_semver(self.collector_version))
        object.__setattr__(self, "mime_type", _require_mime(self.mime_type))
        if isinstance(self.byte_size, bool) or not isinstance(self.byte_size, int):
            raise TypeError("byte_size must be an integer")
        if self.byte_size <= 0:
            raise SourceManifestError("byte_size must be positive; empty sources are invalid")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SourceSubjectManifest":
        if not isinstance(data, Mapping):
            raise TypeError("source subject manifest input must be an object")
        supplied = set(data)
        unknown = supplied - _SUBJECT_MANIFEST_FIELDS
        if unknown:
            raise SourceManifestError(
                f"source subject manifest unknown fields: {sorted(unknown)}")
        missing = _SUBJECT_MANIFEST_FIELDS - supplied
        if missing:
            raise SourceManifestError(
                f"source subject manifest missing fields: {sorted(missing)}")
        return cls(**dict(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_id": self.source_id,
            "subject": {
                "kind": self.subject["kind"],
                "attribution_status": self.subject["attribution_status"],
                "issuer_refs": [dict(ref) for ref in self.subject["issuer_refs"]],
                **({
                    "event_namespace": self.subject["event_namespace"],
                    "event_id": self.subject["event_id"],
                } if self.subject["kind"] == "multi_issuer_event" else {}),
            },
            "original_path": self.original_path,
            "content_sha256": self.content_sha256,
            "mime_type": self.mime_type,
            "byte_size": self.byte_size,
            "collector_name": self.collector_name,
            "collector_version": self.collector_version,
            "retrieved_at": self.retrieved_at,
            "published_date": self.published_date,
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

__all__ = [
    'ImmutableStatus',
    'SOURCE_ID_PREFIX',
    'SOURCE_MANIFEST_SCHEMA_VERSION',
    'SourceManifest',
    'SourceManifestMismatchError',
    'source_id_for_sha256',
]
