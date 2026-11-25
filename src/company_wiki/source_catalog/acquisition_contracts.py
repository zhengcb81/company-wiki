"""Values exchanged by discovery, staging adapters and the canonical writer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
import re
from typing import Any


__all__ = [
    "ACQUISITION_SCHEMA_VERSION",
    "DOWNLOAD_CANDIDATE_SCHEMA_VERSION",
    "DiscoveryPage",
    "DownloadCandidate",
    "DownloadReceipt",
    "require_acquisition_date",
    "require_acquisition_text",
]


ACQUISITION_SCHEMA_VERSION = "1.0"
DOWNLOAD_CANDIDATE_SCHEMA_VERSION = "1.1"
_DOWNLOAD_CANDIDATE_SCHEMA_VERSIONS = {"1.0", DOWNLOAD_CANDIDATE_SCHEMA_VERSION}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
    r"(?:\+[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$"
)


def require_acquisition_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be non-empty trimmed text")
    return value


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return require_acquisition_text(value, name)


def require_acquisition_date(value: Any, name: str) -> str:
    value = require_acquisition_text(value, name)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{name} must be canonical YYYY-MM-DD")
    return value


def _optional_date(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return require_acquisition_date(value, name)


@dataclass(frozen=True)
class DownloadCandidate:
    candidate_id: str
    provider: str
    provider_document_id: str
    market: str
    entity: str
    title: str
    source_url: str
    document_kind: str
    filing_date: str | None
    fiscal_year: int
    form_type: str | None = None
    fiscal_period: str | None = None
    language: str | None = None
    amended: bool = False
    etag: str | None = None
    last_modified: str | None = None
    remote_size: int | None = None
    adapter_payload_json: str | None = None
    # The provider's exact market-local listing identifier. It is optional
    # for legacy adapters, but mandatory when a schema-1.1 identity scope is
    # being enforced at selection/import boundaries.
    security_id: str | None = None
    schema_version: str = DOWNLOAD_CANDIDATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version not in _DOWNLOAD_CANDIDATE_SCHEMA_VERSIONS:
            raise ValueError(
                "schema_version must be one of "
                f"{', '.join(sorted(_DOWNLOAD_CANDIDATE_SCHEMA_VERSIONS))}"
            )
        for name in (
            "candidate_id",
            "provider",
            "provider_document_id",
            "market",
            "entity",
            "title",
            "source_url",
            "document_kind",
        ):
            object.__setattr__(self, name, require_acquisition_text(getattr(self, name), name))
        object.__setattr__(self, "provider", self.provider.lower())
        object.__setattr__(self, "market", self.market.upper())
        object.__setattr__(self, "document_kind", self.document_kind.lower())
        if self.market not in {"CN", "HK", "US"}:
            raise ValueError("market must be CN, HK, or US")
        if not self.source_url.startswith("https://"):
            raise ValueError("source_url must be HTTPS")
        object.__setattr__(self, "filing_date", _optional_date(self.filing_date, "filing_date"))
        for name in (
            "form_type",
            "fiscal_period",
            "language",
            "etag",
            "last_modified",
            "adapter_payload_json",
            "security_id",
        ):
            object.__setattr__(self, name, _optional_text(getattr(self, name), name))
        if self.adapter_payload_json is not None:
            try:
                adapter_payload = json.loads(self.adapter_payload_json)
            except json.JSONDecodeError as exc:
                raise ValueError("adapter_payload_json must be valid JSON") from exc
            if not isinstance(adapter_payload, dict):
                raise ValueError("adapter_payload_json must contain a JSON object")
        if isinstance(self.fiscal_year, bool) or not isinstance(self.fiscal_year, int):
            raise TypeError("fiscal_year must be an integer")
        if not 1900 <= self.fiscal_year <= 2200:
            raise ValueError("fiscal_year is outside the supported range")
        if not isinstance(self.amended, bool):
            raise TypeError("amended must be boolean")
        if self.remote_size is not None and (
            isinstance(self.remote_size, bool)
            or not isinstance(self.remote_size, int)
            or self.remote_size <= 0
        ):
            raise ValueError("remote_size must be a positive integer or null")

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class DownloadReceipt:
    candidate_id: str
    provider: str
    provider_document_id: str
    source_url: str
    staged_path: str
    content_sha256: str
    byte_size: int
    mime_type: str
    retrieved_at: str
    http_status: int
    adapter_name: str
    adapter_version: str
    etag: str | None = None
    last_modified: str | None = None
    schema_version: str = ACQUISITION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ACQUISITION_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {ACQUISITION_SCHEMA_VERSION}")
        for name in (
            "candidate_id",
            "provider",
            "provider_document_id",
            "source_url",
            "staged_path",
            "mime_type",
            "retrieved_at",
            "adapter_name",
            "adapter_version",
        ):
            object.__setattr__(self, name, require_acquisition_text(getattr(self, name), name))
        object.__setattr__(self, "provider", self.provider.lower())
        if not self.source_url.startswith("https://"):
            raise ValueError("source_url must be HTTPS")
        if not _SHA256_RE.fullmatch(self.content_sha256):
            raise ValueError("content_sha256 must be lowercase SHA-256")
        if (
            isinstance(self.byte_size, bool)
            or not isinstance(self.byte_size, int)
            or self.byte_size <= 0
        ):
            raise ValueError("byte_size must be a positive integer")
        if (
            isinstance(self.http_status, bool)
            or not isinstance(self.http_status, int)
            or not 100 <= self.http_status <= 599
        ):
            raise ValueError("http_status must be an HTTP status integer")
        if not _UTC_RE.fullmatch(self.retrieved_at):
            raise ValueError("retrieved_at must be UTC YYYY-MM-DDTHH:MM:SSZ")
        try:
            datetime.strptime(self.retrieved_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:
            raise ValueError("retrieved_at must be a valid UTC timestamp") from exc
        object.__setattr__(self, "etag", _optional_text(self.etag, "etag"))
        object.__setattr__(
            self, "last_modified", _optional_text(self.last_modified, "last_modified")
        )
        if not _SEMVER_RE.fullmatch(self.adapter_version):
            raise ValueError("adapter_version must be semantic version text")

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class DiscoveryPage:
    """One bounded provider enumeration page and the coverage it can prove.

    ``coverage`` is the adapter's own statement about the enumeration it just
    performed.  A provider that cannot enumerate a whole range must not claim
    ``complete``; the caller keeps the partial state and does not advance a
    watermark past the gap.  ``covered_from`` / ``covered_to`` are the dates
    the enumeration actually covered, so the caller can compare them with the
    range it asked for instead of assuming the range was reached.
    """

    candidates: tuple[DownloadCandidate, ...]
    coverage: str = "partial"
    next_cursor: str | None = None
    reason_codes: tuple[str, ...] = ()
    covered_from: str | None = None
    covered_to: str | None = None

    def __post_init__(self) -> None:
        if self.coverage not in {"complete", "partial"}:
            raise ValueError("coverage must be 'complete' or 'partial'")
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        for name in ("next_cursor", "covered_from", "covered_to"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be nonempty text or None")
