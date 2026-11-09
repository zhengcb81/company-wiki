"""Wire values and validation for one immutable official announcement receipt."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import date
import hashlib
import json
import unicodedata
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .source_manifest import SourceManifest, SourceType


ANNOUNCEMENT_COLLECTION_SCHEMA_VERSION = "1.0.0"
ANNOUNCEMENT_COLLECTION_ID_PREFIX = (
    "urn:company-wiki:announcement-collection:sha256:"
)
ANNOUNCEMENT_COLLECTOR_NAME = "company-wiki-explicit-announcement"
ANNOUNCEMENT_COLLECTOR_VERSION = "1.0.0"
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
OFFICIAL_EXCHANGE_DOMAINS = ("sse.com.cn", "szse.cn")

class AnnouncementCollectionError(ValueError):
    """Base error for invalid or unsafe announcement collection."""


class AnnouncementURLPolicyError(AnnouncementCollectionError):
    """Raised before a request to a URL outside the official-domain policy."""


class AnnouncementDownloadError(AnnouncementCollectionError):
    """Raised when the bounded HTTP download cannot complete safely."""


class AnnouncementContentError(AnnouncementCollectionError):
    """Raised when the response is not a bounded PDF document."""


class AnnouncementConflictError(AnnouncementCollectionError):
    """Raised when an existing immutable path disagrees with collected bytes."""


@dataclass(frozen=True)
class DownloadedAnnouncement:
    """Bounded HTTP response material needed for provenance."""

    body: bytes
    final_url: str
    content_type: str
    etag: str | None = None
    last_modified: str | None = None


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def require_announcement_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if not value or value != value.strip():
        raise AnnouncementCollectionError(
            f"{field_name} must be non-empty trimmed text"
        )
    if unicodedata.normalize("NFC", value) != value:
        raise AnnouncementCollectionError(f"{field_name} must use Unicode NFC")
    if any(ord(character) < 32 for character in value):
        raise AnnouncementCollectionError(
            f"{field_name} must not contain control characters"
        )
    return value


def optional_announcement_header(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return require_announcement_text(value, field_name)


def require_announcement_date(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError("published_date must be YYYY-MM-DD text")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise AnnouncementCollectionError(
            "published_date must be a valid YYYY-MM-DD"
        ) from exc
    if parsed.isoformat() != value:
        raise AnnouncementCollectionError(
            "published_date must be canonical YYYY-MM-DD"
        )
    return value


def _official_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    normalized = hostname.casefold().rstrip(".")
    return any(
        normalized == domain or normalized.endswith("." + domain)
        for domain in OFFICIAL_EXCHANGE_DOMAINS
    )


def validate_official_announcement_url(url: str) -> str:
    """Return a canonical HTTPS URL only for official SSE/SZSE domains."""

    url = require_announcement_text(url, "announcement URL")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise AnnouncementURLPolicyError("announcement URL is invalid") from exc
    if parts.scheme.casefold() != "https":
        raise AnnouncementURLPolicyError("announcement URL must use HTTPS")
    if parts.username is not None or parts.password is not None:
        raise AnnouncementURLPolicyError("announcement URL must not contain credentials")
    if port not in (None, 443):
        raise AnnouncementURLPolicyError("announcement URL must use the default HTTPS port")
    if not _official_host(parts.hostname):
        raise AnnouncementURLPolicyError(
            "announcement URL host is not an official SSE/SZSE domain"
        )
    if parts.fragment:
        raise AnnouncementURLPolicyError("announcement URL must not contain a fragment")
    if not parts.path or parts.path == "/":
        raise AnnouncementURLPolicyError("announcement URL must identify a document path")
    if "\\" in parts.path:
        raise AnnouncementURLPolicyError("announcement URL path must not contain backslashes")
    host = (parts.hostname or "").casefold().rstrip(".")
    return urlunsplit(("https", host, parts.path, parts.query, ""))


@dataclass(frozen=True)
class AnnouncementCollectionReceipt:
    schema_version: str
    collection_id: str
    collector_name: str
    collector_version: str
    source_url: str
    final_url: str
    title: str
    published_date: str
    retrieved_at: str
    content_type: str
    etag: str | None
    last_modified: str | None
    manifest_path: str
    provenance_path: str
    manifest: SourceManifest

    @classmethod
    def create(
        cls,
        *,
        source_url: str,
        final_url: str,
        title: str,
        published_date: str,
        retrieved_at: str,
        content_type: str,
        etag: str | None,
        last_modified: str | None,
        manifest_path: str,
        provenance_path: str,
        manifest: SourceManifest,
    ) -> "AnnouncementCollectionReceipt":
        payload = {
            "schema_version": ANNOUNCEMENT_COLLECTION_SCHEMA_VERSION,
            "collector_name": ANNOUNCEMENT_COLLECTOR_NAME,
            "collector_version": ANNOUNCEMENT_COLLECTOR_VERSION,
            "source_url": source_url,
            "final_url": final_url,
            "title": title,
            "published_date": published_date,
            "retrieved_at": retrieved_at,
            "content_type": content_type,
            "etag": etag,
            "last_modified": last_modified,
            "manifest_path": manifest_path,
            "provenance_path": provenance_path,
            "manifest": manifest.to_dict(),
        }
        return cls(
            schema_version=ANNOUNCEMENT_COLLECTION_SCHEMA_VERSION,
            collection_id=(
                ANNOUNCEMENT_COLLECTION_ID_PREFIX + _canonical_sha256(payload)
            ),
            collector_name=ANNOUNCEMENT_COLLECTOR_NAME,
            collector_version=ANNOUNCEMENT_COLLECTOR_VERSION,
            source_url=source_url,
            final_url=final_url,
            title=title,
            published_date=published_date,
            retrieved_at=retrieved_at,
            content_type=content_type,
            etag=etag,
            last_modified=last_modified,
            manifest_path=manifest_path,
            provenance_path=provenance_path,
            manifest=manifest,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AnnouncementCollectionReceipt":
        if not isinstance(data, Mapping):
            raise TypeError("announcement collection receipt must be an object")
        known = {field.name for field in fields(cls)}
        supplied = set(data)
        if supplied != known:
            raise AnnouncementCollectionError(
                "announcement collection receipt fields do not match v1"
            )
        manifest = SourceManifest.from_dict(data["manifest"])
        prepared = dict(data)
        prepared["manifest"] = manifest
        receipt = cls(**prepared)
        expected = cls.create(
            source_url=receipt.source_url,
            final_url=receipt.final_url,
            title=receipt.title,
            published_date=receipt.published_date,
            retrieved_at=receipt.retrieved_at,
            content_type=receipt.content_type,
            etag=receipt.etag,
            last_modified=receipt.last_modified,
            manifest_path=receipt.manifest_path,
            provenance_path=receipt.provenance_path,
            manifest=receipt.manifest,
        )
        if receipt.collection_id != expected.collection_id:
            raise AnnouncementCollectionError(
                "announcement collection_id does not match canonical payload"
            )
        receipt.validate()
        return receipt

    def validate(self) -> None:
        if self.schema_version != ANNOUNCEMENT_COLLECTION_SCHEMA_VERSION:
            raise AnnouncementCollectionError("unsupported announcement schema version")
        if self.collector_name != ANNOUNCEMENT_COLLECTOR_NAME:
            raise AnnouncementCollectionError("unexpected announcement collector name")
        if self.collector_version != ANNOUNCEMENT_COLLECTOR_VERSION:
            raise AnnouncementCollectionError("unexpected announcement collector version")
        validate_official_announcement_url(self.source_url)
        validate_official_announcement_url(self.final_url)
        require_announcement_text(self.title, "title")
        require_announcement_date(self.published_date)
        require_announcement_text(self.retrieved_at, "retrieved_at")
        require_announcement_text(self.content_type, "content_type")
        optional_announcement_header(self.etag, "ETag")
        optional_announcement_header(self.last_modified, "Last-Modified")
        require_announcement_text(self.manifest_path, "manifest_path")
        require_announcement_text(self.provenance_path, "provenance_path")
        if self.manifest.source_type is not SourceType.COMPANY_ANNOUNCEMENT:
            raise AnnouncementCollectionError("manifest is not a company announcement")
        if self.manifest.published_date != self.published_date:
            raise AnnouncementCollectionError("manifest published_date mismatch")
        if self.manifest.retrieved_at != self.retrieved_at:
            raise AnnouncementCollectionError("manifest retrieved_at mismatch")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "collection_id": self.collection_id,
            "collector_name": self.collector_name,
            "collector_version": self.collector_version,
            "source_url": self.source_url,
            "final_url": self.final_url,
            "title": self.title,
            "published_date": self.published_date,
            "retrieved_at": self.retrieved_at,
            "content_type": self.content_type,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "manifest_path": self.manifest_path,
            "provenance_path": self.provenance_path,
            "manifest": self.manifest.to_dict(),
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.to_dict())


__all__ = [
    "ANNOUNCEMENT_COLLECTION_ID_PREFIX",
    "ANNOUNCEMENT_COLLECTION_SCHEMA_VERSION",
    "ANNOUNCEMENT_COLLECTOR_NAME",
    "ANNOUNCEMENT_COLLECTOR_VERSION",
    "DEFAULT_MAX_BYTES",
    "OFFICIAL_EXCHANGE_DOMAINS",
    "AnnouncementCollectionError",
    "AnnouncementCollectionReceipt",
    "AnnouncementConflictError",
    "AnnouncementContentError",
    "AnnouncementDownloadError",
    "AnnouncementURLPolicyError",
    "DownloadedAnnouncement",
    "optional_announcement_header",
    "require_announcement_date",
    "require_announcement_text",
    "validate_official_announcement_url",
]
