"""Strict read-only source resolver for query-before-download reuse."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .service import SourceCatalog


SOURCE_RESOLVER_SCHEMA_VERSION = "1.0"
_YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2}|21\d{2})(?!\d)")


class SourceResolutionError(ValueError):
    """Raised when a source request violates the resolver contract."""


class ResolutionStatus(str, Enum):
    REUSED_EXACT = "reused_exact"
    REUSED_EQUIVALENT = "reused_equivalent"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise SourceResolutionError(f"{name} must be non-empty trimmed text")
    return value


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, name)


def _canonical_date(value: Any, name: str) -> str:
    value = _required_text(value, name)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SourceResolutionError(f"{name} must be a valid YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise SourceResolutionError(f"{name} must be canonical YYYY-MM-DD")
    return value


def _json_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourceRequest:
    entity: str
    document_kind: str
    as_of_date: str
    market: str | None = None
    security_id: str | None = None
    form_type: str | None = None
    fiscal_year: int | None = None
    fiscal_period: str | None = None
    language: str | None = None
    provider: str | None = None
    provider_document_id: str | None = None
    allow_download: bool = False
    schema_version: str = SOURCE_RESOLVER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SOURCE_RESOLVER_SCHEMA_VERSION:
            raise SourceResolutionError(
                f"schema_version must be {SOURCE_RESOLVER_SCHEMA_VERSION}"
            )
        object.__setattr__(self, "entity", _required_text(self.entity, "entity"))
        object.__setattr__(
            self,
            "document_kind",
            _required_text(self.document_kind, "document_kind").lower(),
        )
        object.__setattr__(self, "as_of_date", _canonical_date(self.as_of_date, "as_of_date"))
        market = _optional_text(self.market, "market")
        provider = _optional_text(self.provider, "provider")
        object.__setattr__(self, "market", market.upper() if market else None)
        object.__setattr__(
            self,
            "security_id",
            _optional_text(self.security_id, "security_id"),
        )
        object.__setattr__(self, "provider", provider.lower() if provider else None)
        object.__setattr__(self, "form_type", _optional_text(self.form_type, "form_type"))
        object.__setattr__(
            self, "fiscal_period", _optional_text(self.fiscal_period, "fiscal_period")
        )
        object.__setattr__(self, "language", _optional_text(self.language, "language"))
        object.__setattr__(
            self,
            "provider_document_id",
            _optional_text(self.provider_document_id, "provider_document_id"),
        )
        if self.fiscal_year is not None:
            if isinstance(self.fiscal_year, bool) or not isinstance(self.fiscal_year, int):
                raise SourceResolutionError("fiscal_year must be an integer or null")
            if self.fiscal_year < 1900 or self.fiscal_year > 2200:
                raise SourceResolutionError("fiscal_year is outside the supported range")
        if not isinstance(self.allow_download, bool):
            raise SourceResolutionError("allow_download must be boolean")

    def identity_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "entity": self.entity,
            "market": self.market,
            "security_id": self.security_id,
            "document_kind": self.document_kind,
            "form_type": self.form_type,
            "fiscal_year": self.fiscal_year,
            "fiscal_period": self.fiscal_period,
            "language": self.language,
            "provider": self.provider,
            "provider_document_id": self.provider_document_id,
            "as_of_date": self.as_of_date,
        }

    @property
    def request_id(self) -> str:
        return "urn:company-wiki:source-request:sha256:" + _json_hash(self.identity_dict())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_dict(), "allow_download": self.allow_download}


@dataclass(frozen=True)
class SourceHandle:
    schema_version: str
    document_id: str
    source_id: str
    entity_ids: tuple[str, ...]
    title: str
    source_type: str
    document_kind: str
    published_date: str
    fiscal_year: int | None
    fiscal_period: str | None
    form_type: str | None
    language: str | None
    provider: str | None
    provider_document_id: str | None
    https_url: str | None
    canonical_location_id: str
    canonical_path: str
    content_sha256: str
    snapshot_sha256: str
    mime_type: str
    byte_size: int
    retrieved_at: str
    collector_name: str
    collector_version: str
    source_status: str
    duplicate_group_id: str
    exact_duplicate_location_count: int
    capture_ready: bool
    missing_capture_fields: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.__dict__,
            "entity_ids": list(self.entity_ids),
            "missing_capture_fields": list(self.missing_capture_fields),
        }


@dataclass(frozen=True)
class ResolutionResult:
    schema_version: str
    request_id: str
    status: ResolutionStatus
    reason: str
    download_required: bool
    download_allowed: bool
    matches: tuple[SourceHandle, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "status": self.status.value,
            "reason": self.reason,
            "download_required": self.download_required,
            "download_allowed": self.download_allowed,
            "matches": [item.to_dict() for item in self.matches],
        }


def _source_metadata(document: dict[str, Any]) -> dict[str, Any]:
    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        return {}
    for key in ("acquisition", "dayu_meta"):
        value = metadata.get(key)
        if isinstance(value, dict) and value:
            return value
    return {}


def _fiscal_year(document: dict[str, Any], metadata: dict[str, Any]) -> int | None:
    value = metadata.get("fiscal_year")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    years = [int(item) for item in _YEAR_RE.findall(document["title"])]
    return years[-1] if years else None


def _provider_identity(metadata: dict[str, Any]) -> tuple[str | None, str | None, set[str]]:
    provider_value = metadata.get("provider")
    provider = str(provider_value).strip().lower() if provider_value else None
    form_type = str(metadata.get("form_type") or "").upper()
    if provider is None and (metadata.get("accession_number") or form_type.startswith(("10-", "20-", "6-"))):
        provider = "sec"
    identities = {
        str(value).strip()
        for value in (
            metadata.get("accession_number"),
            metadata.get("provider_document_id"),
            metadata.get("source_id"),
            metadata.get("document_id"),
        )
        if value is not None and str(value).strip()
    }
    preferred = next(
        (
            str(value).strip()
            for value in (
                metadata.get("accession_number"),
                metadata.get("provider_document_id"),
                metadata.get("source_id"),
                metadata.get("document_id"),
            )
            if value is not None and str(value).strip()
        ),
        None,
    )
    return provider, preferred, identities


class SourceResolver:
    """Resolve existing catalog sources without performing acquisition side effects."""

    def __init__(self, catalog: SourceCatalog):
        if not isinstance(catalog, SourceCatalog):
            raise TypeError("catalog must be SourceCatalog")
        self.catalog = catalog

    def resolve(self, request: SourceRequest) -> ResolutionResult:
        if not isinstance(request, SourceRequest):
            raise TypeError("request must be SourceRequest")
        semantic: list[SourceHandle] = []
        exact: list[SourceHandle] = []
        future_matches = 0
        unknown_date_matches = 0
        for document in self.catalog.query(limit=10_000_000):
            if not self._entity_matches(request.entity, document):
                continue
            if document["document_kind"] != request.document_kind:
                continue
            metadata = _source_metadata(document)
            year = _fiscal_year(document, metadata)
            if request.fiscal_year is not None and year != request.fiscal_year:
                continue
            form_type = str(metadata.get("form_type") or "").strip() or None
            if request.form_type and form_type != request.form_type:
                continue
            fiscal_period = str(metadata.get("fiscal_period") or "").strip() or None
            if request.fiscal_period and fiscal_period != request.fiscal_period:
                continue
            language = str(metadata.get("language") or "").strip() or None
            if request.language and language != request.language:
                continue
            provider, provider_document_id, identities = _provider_identity(metadata)
            if request.provider and provider and provider != request.provider:
                continue
            strong_identity = bool(
                request.provider_document_id
                and request.provider_document_id in identities
                and (not request.provider or provider == request.provider)
            )
            if request.provider_document_id and not strong_identity:
                continue
            published = document["published_date"]
            if not published:
                unknown_date_matches += 1
                continue
            if published > request.as_of_date:
                future_matches += 1
                continue
            handle = self._handle(
                document,
                metadata=metadata,
                fiscal_year=year,
                fiscal_period=fiscal_period,
                form_type=form_type,
                language=language,
                provider=provider,
                provider_document_id=provider_document_id,
            )
            if handle is None:
                continue
            semantic.append(handle)
            if strong_identity:
                exact.append(handle)
        if len(exact) == 1:
            return self._result(
                request,
                ResolutionStatus.REUSED_EXACT,
                "one_existing_source_matches_provider_identity",
                (exact[0],),
            )
        if len(exact) > 1:
            return self._result(
                request,
                ResolutionStatus.AMBIGUOUS,
                "multiple_existing_sources_match_provider_identity",
                tuple(exact),
            )
        if len(semantic) == 1:
            return self._result(
                request,
                ResolutionStatus.REUSED_EQUIVALENT,
                "one_existing_source_satisfies_semantic_request",
                (semantic[0],),
            )
        if len(semantic) > 1:
            return self._result(
                request,
                ResolutionStatus.AMBIGUOUS,
                "multiple_existing_sources_match_semantic_request",
                tuple(semantic),
            )
        if future_matches:
            reason = "only_sources_published_after_as_of_date"
        elif unknown_date_matches:
            return self._result(
                request,
                ResolutionStatus.AMBIGUOUS,
                "matching_sources_have_unknown_published_date",
                (),
            )
        else:
            reason = "no_existing_source_satisfies_request"
        return self._result(request, ResolutionStatus.MISSING, reason, ())

    @staticmethod
    def _entity_matches(entity: str, document: dict[str, Any]) -> bool:
        wanted = entity.casefold()
        values = {
            str(item.get("entity_id") or "").casefold()
            for item in document["entities"]
        } | {
            str(item.get("name") or "").casefold()
            for item in document["entities"]
        }
        metadata = _source_metadata(document)
        values.update(
            str(value).casefold()
            for value in (
                metadata.get("ticker"),
                metadata.get("security_id"),
                metadata.get("company_name"),
            )
            if value
        )
        return wanted in values

    @staticmethod
    def _handle(
        document: dict[str, Any],
        *,
        metadata: dict[str, Any],
        fiscal_year: int | None,
        fiscal_period: str | None,
        form_type: str | None,
        language: str | None,
        provider: str | None,
        provider_document_id: str | None,
    ) -> SourceHandle | None:
        canonical = next(
            (
                item
                for item in document["locations"]
                if item["is_canonical"]
                and item["role"] == "original_primary"
                and item["location_status"] == "active"
            ),
            None,
        )
        if canonical is None or not Path(canonical["absolute_path"]).is_file():
            return None
        try:
            manifest = json.loads(canonical["manifest_json"] or "{}")
        except json.JSONDecodeError:
            manifest = {}
        source_id = str(canonical["source_id"] or document["source_id"] or "")
        content_sha256 = str(manifest.get("content_sha256") or source_id.rsplit(":", 1)[-1])
        url_value = metadata.get("source_url") or metadata.get("https_url")
        https_url = str(url_value).strip() if url_value else None
        if https_url and not https_url.startswith("https://"):
            https_url = None
        missing: list[str] = []
        if not https_url:
            missing.append("https_url")
        if not document["published_date"]:
            missing.append("published_date")
        if not source_id or len(content_sha256) != 64:
            missing.append("snapshot_sha256")
        retrieved_at = str(manifest.get("retrieved_at") or "")
        collector_name = str(manifest.get("collector_name") or "")
        collector_version = str(manifest.get("collector_version") or "")
        if not retrieved_at or not collector_name or not collector_version:
            missing.append("capture_trace")
        return SourceHandle(
            schema_version=SOURCE_RESOLVER_SCHEMA_VERSION,
            document_id=document["document_id"],
            source_id=source_id,
            entity_ids=tuple(sorted(item["entity_id"] for item in document["entities"])),
            title=document["title"],
            source_type=document["source_type"],
            document_kind=document["document_kind"],
            published_date=document["published_date"],
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            form_type=form_type,
            language=language,
            provider=provider,
            provider_document_id=provider_document_id,
            https_url=https_url,
            canonical_location_id=canonical["location_id"],
            canonical_path=canonical["absolute_path"],
            content_sha256=content_sha256,
            snapshot_sha256=content_sha256,
            mime_type=str(manifest.get("mime_type") or "application/octet-stream"),
            byte_size=int(manifest.get("byte_size") or canonical["observed_size"] or 0),
            retrieved_at=retrieved_at,
            collector_name=collector_name,
            collector_version=collector_version,
            source_status=document["source_status"],
            duplicate_group_id=document["exact_duplicate_group_id"],
            exact_duplicate_location_count=document["exact_duplicate_location_count"],
            capture_ready=not missing,
            missing_capture_fields=tuple(missing),
        )

    @staticmethod
    def _result(
        request: SourceRequest,
        status: ResolutionStatus,
        reason: str,
        matches: tuple[SourceHandle, ...],
    ) -> ResolutionResult:
        return ResolutionResult(
            schema_version=SOURCE_RESOLVER_SCHEMA_VERSION,
            request_id=request.request_id,
            status=status,
            reason=reason,
            download_required=status is ResolutionStatus.MISSING,
            download_allowed=request.allow_download,
            matches=matches,
        )


__all__ = [
    "ResolutionResult",
    "ResolutionStatus",
    "SOURCE_RESOLVER_SCHEMA_VERSION",
    "SourceHandle",
    "SourceRequest",
    "SourceResolutionError",
    "SourceResolver",
]
