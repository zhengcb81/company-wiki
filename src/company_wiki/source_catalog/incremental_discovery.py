"""Bounded public metadata enumeration for the scheduled source refresh.

The refresh caller owns the list, the window and the cadence.  This module
owns one thing: enumerate the provider metadata that exists inside a declared
range, say honestly how much of that range was actually covered, and hand back
exact provider identities so the bytes can be fetched later through the
existing ``ensure`` interface.

It never downloads an original, never exposes a provider's internal URL as a
download target, and never claims a complete range it cannot prove.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
import hashlib
import json
import re
import time
from typing import Any

from .acquisition import AcquisitionCoordinator, DiscoveryPage, DownloadCandidate
from .download_budget import AcquisitionBudget
from .resolver import ResolutionStatus, SourceRequest, SourceResolver
from .service import SourceCatalog


INCREMENTAL_DISCOVERY_REQUEST_SCHEMA = "cwp-incremental-discovery-request/1"
INCREMENTAL_DISCOVERY_SCHEMA = "cwp-incremental-discovery/1"

#: The three states a caller may act on.  ``unavailable`` means no enumeration
#: could be performed at all; ``partial`` means real candidates were returned
#: but the range is not proven complete, so a watermark must not advance past
#: the gap.
COVERAGE_COMPLETE = "complete"
COVERAGE_PARTIAL = "partial"
COVERAGE_UNAVAILABLE = "unavailable"

_MARKETS = ("CN", "HK", "US")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ISSUER_LINK_ID_RE = re.compile(r"issuer-link-v1:[0-9a-f]{64}")
_MAX_KINDS = 16
_MAX_CURSOR_CHARS = 4096


class IncrementalDiscoveryError(ValueError):
    """The discovery request or its result cannot be represented honestly."""


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise IncrementalDiscoveryError(f"{name} must be nonempty unpadded text")
    return value


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _text(value, name)


def _date(value: Any, name: str) -> str:
    text = _text(value, name)
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        raise IncrementalDiscoveryError(f"{name} must be a canonical YYYY-MM-DD date") from None
    if parsed.isoformat() != text:
        raise IncrementalDiscoveryError(f"{name} must be a canonical YYYY-MM-DD date")
    return text


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise IncrementalDiscoveryError(f"{name} must be a positive integer")
    return value


def _exact(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IncrementalDiscoveryError(f"{name} must be an object")
    if set(value) != keys:
        raise IncrementalDiscoveryError(f"{name} has unsupported or missing fields")
    return value


@dataclass(frozen=True)
class DiscoveryIdentity:
    """The public issuer/listing coordinates of the documents to enumerate."""

    entity: str
    security_id: str | None = None
    identity_scope: str | None = None
    issuer_link_id: str | None = None

    @classmethod
    def from_dict(cls, value: Any) -> "DiscoveryIdentity":
        item = _exact(
            value,
            {"entity", "security_id", "identity_scope", "issuer_link_id"},
            "identity",
        )
        identity = cls(
            entity=_text(item["entity"], "identity.entity"),
            security_id=_optional_text(item["security_id"], "identity.security_id"),
            identity_scope=_optional_text(item["identity_scope"], "identity.identity_scope"),
            issuer_link_id=_optional_text(item["issuer_link_id"], "identity.issuer_link_id"),
        )
        if identity.identity_scope not in {None, "listing", "issuer"}:
            raise IncrementalDiscoveryError(
                "identity.identity_scope must be 'listing' or 'issuer'"
            )
        if (identity.identity_scope is None) != (identity.issuer_link_id is None):
            raise IncrementalDiscoveryError(
                "identity_scope and issuer_link_id must be supplied together"
            )
        if identity.identity_scope == "listing" and not identity.security_id:
            raise IncrementalDiscoveryError(
                "listing identity scope requires security_id"
            )
        if identity.identity_scope == "issuer" and identity.security_id:
            raise IncrementalDiscoveryError(
                "issuer identity scope must not carry a listing id"
            )
        if identity.issuer_link_id is not None and _ISSUER_LINK_ID_RE.fullmatch(
            identity.issuer_link_id
        ) is None:
            raise IncrementalDiscoveryError("identity.issuer_link_id is malformed")
        return identity

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "security_id": self.security_id,
            "identity_scope": self.identity_scope,
            "issuer_link_id": self.issuer_link_id,
        }


@dataclass(frozen=True)
class DiscoveryLimits:
    """The caller's ceiling for this enumeration."""

    max_candidates: int = 100
    max_pages: int = 8
    max_requests: int = 8
    max_seconds: float = 120.0

    @classmethod
    def from_dict(cls, value: Any) -> "DiscoveryLimits":
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise IncrementalDiscoveryError("limits must be an object")
        allowed = {"max_candidates", "max_pages", "max_requests", "max_seconds"}
        if set(value) - allowed:
            raise IncrementalDiscoveryError("limits has unsupported fields")
        seconds = value.get("max_seconds", cls.max_seconds)
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, (int, float))
            or seconds <= 0
        ):
            raise IncrementalDiscoveryError("limits.max_seconds must be positive")
        return cls(
            max_candidates=_positive_int(
                value.get("max_candidates", cls.max_candidates), "limits.max_candidates"
            ),
            max_pages=_positive_int(
                value.get("max_pages", cls.max_pages), "limits.max_pages"
            ),
            max_requests=_positive_int(
                value.get("max_requests", cls.max_requests), "limits.max_requests"
            ),
            max_seconds=float(seconds),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_candidates": self.max_candidates,
            "max_pages": self.max_pages,
            "max_requests": self.max_requests,
            "max_seconds": self.max_seconds,
        }


@dataclass(frozen=True)
class IncrementalDiscoveryRequest:
    """One bounded enumeration scope."""

    request_id: str
    identity: DiscoveryIdentity
    source_market: str
    document_kinds: tuple[str, ...]
    since_date: str
    as_of_date: str
    cursor: str | None = None
    limits: DiscoveryLimits = DiscoveryLimits()

    @classmethod
    def from_dict(cls, value: Any) -> "IncrementalDiscoveryRequest":
        item = _exact(
            value,
            {
                "schema_version",
                "request_id",
                "identity",
                "source_market",
                "document_kinds",
                "since_date",
                "as_of_date",
                "cursor",
                "limits",
            },
            "discovery request",
        )
        if item["schema_version"] != INCREMENTAL_DISCOVERY_REQUEST_SCHEMA:
            raise IncrementalDiscoveryError("unsupported discovery request schema")
        market = _text(item["source_market"], "source_market").upper()
        if market not in _MARKETS:
            raise IncrementalDiscoveryError("source_market must be CN, HK or US")
        kinds = item["document_kinds"]
        if not isinstance(kinds, list) or not kinds:
            raise IncrementalDiscoveryError("document_kinds must be a nonempty list")
        if len(kinds) > _MAX_KINDS:
            raise IncrementalDiscoveryError("document_kinds has too many entries")
        normalized = tuple(_text(kind, "document_kind").lower() for kind in kinds)
        if len(set(normalized)) != len(normalized):
            raise IncrementalDiscoveryError("document_kinds must be unique")
        since = _date(item["since_date"], "since_date")
        as_of = _date(item["as_of_date"], "as_of_date")
        if since > as_of:
            raise IncrementalDiscoveryError("since_date must not be after as_of_date")
        cursor = item["cursor"]
        if cursor is not None:
            cursor = _text(cursor, "cursor")
            if len(cursor) > _MAX_CURSOR_CHARS:
                raise IncrementalDiscoveryError("cursor is too long")
        return cls(
            request_id=_text(item["request_id"], "request_id"),
            identity=DiscoveryIdentity.from_dict(item["identity"]),
            source_market=market,
            document_kinds=normalized,
            since_date=since,
            as_of_date=as_of,
            cursor=cursor,
            limits=DiscoveryLimits.from_dict(item["limits"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": INCREMENTAL_DISCOVERY_REQUEST_SCHEMA,
            "request_id": self.request_id,
            "identity": self.identity.to_dict(),
            "source_market": self.source_market,
            "document_kinds": list(self.document_kinds),
            "since_date": self.since_date,
            "as_of_date": self.as_of_date,
            "cursor": self.cursor,
            "limits": self.limits.to_dict(),
        }


@dataclass(frozen=True)
class DiscoveryCandidate:
    """One provider document identity inside the requested range.

    The provider's own URL is deliberately absent: the bytes are fetched
    through the existing ``ensure`` interface by this exact provider identity,
    never by a URL handed across the boundary.
    """

    candidate_key: str
    provider: str
    provider_document_id: str
    source_market: str
    document_kind: str
    published_at: str | None
    fiscal_year: int | None
    fiscal_period: str | None
    amended: bool
    listing: str | None
    title: str | None
    existing_source_ref: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_key": self.candidate_key,
            "provider": self.provider,
            "provider_document_id": self.provider_document_id,
            "source_market": self.source_market,
            "document_kind": self.document_kind,
            "published_at": self.published_at,
            "fiscal_year": self.fiscal_year,
            "fiscal_period": self.fiscal_period,
            "amended": self.amended,
            "listing": self.listing,
            "title": self.title,
            "existing_source_ref": self.existing_source_ref,
        }


@dataclass(frozen=True)
class IncrementalDiscoveryResponse:
    """The bounded enumeration result the caller acts on."""

    request_id: str
    scope: dict[str, Any]
    coverage: str
    next_cursor: str | None
    candidates: tuple[DiscoveryCandidate, ...]
    usage: dict[str, Any]
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": INCREMENTAL_DISCOVERY_SCHEMA,
            "request_id": self.request_id,
            "scope": self.scope,
            "coverage": self.coverage,
            "next_cursor": self.next_cursor,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "usage": self.usage,
            "reason_codes": list(self.reason_codes),
        }


def _candidate_key(candidate: DownloadCandidate) -> str:
    """A stable identity for one provider document, independent of the range.

    The provider's revision discriminators ride in the key: a correction that
    reuses the accession stays a distinct candidate from the original.
    """
    payload = json.dumps(
        {
            "provider": candidate.provider,
            "provider_document_id": candidate.provider_document_id,
            "market": candidate.market,
            "document_kind": candidate.document_kind,
            "fiscal_year": candidate.fiscal_year,
            "fiscal_period": candidate.fiscal_period,
            "form_type": candidate.form_type,
            "amended": candidate.amended,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _encode_cursor(kind_index: int, page_cursor: str | None) -> str:
    return json.dumps(
        {"kind_index": kind_index, "page_cursor": page_cursor},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _decode_cursor(cursor: str | None) -> tuple[int, str | None]:
    """Read the resume point.  An unreadable cursor is a refusal, not a guess."""
    if cursor is None:
        return 0, None
    try:
        payload = json.loads(cursor)
    except json.JSONDecodeError:
        raise IncrementalDiscoveryError("cursor is not a discovery cursor") from None
    if not isinstance(payload, dict) or set(payload) != {"kind_index", "page_cursor"}:
        raise IncrementalDiscoveryError("cursor is not a discovery cursor")
    kind_index = payload["kind_index"]
    if isinstance(kind_index, bool) or not isinstance(kind_index, int) or kind_index < 0:
        raise IncrementalDiscoveryError("cursor kind_index is invalid")
    page_cursor = payload["page_cursor"]
    if page_cursor is not None and (
        not isinstance(page_cursor, str) or not page_cursor.strip()
    ):
        raise IncrementalDiscoveryError("cursor page_cursor is invalid")
    return kind_index, page_cursor


class IncrementalDiscoveryService:
    """Enumerate provider metadata for a declared identity, range and kinds."""

    def __init__(self, *, catalog: SourceCatalog, coordinator: AcquisitionCoordinator) -> None:
        if not isinstance(catalog, SourceCatalog):
            raise TypeError("catalog must be SourceCatalog")
        if not isinstance(coordinator, AcquisitionCoordinator):
            raise TypeError("coordinator must be AcquisitionCoordinator")
        self._catalog = catalog
        self._coordinator = coordinator

    def discover(
        self,
        request: IncrementalDiscoveryRequest,
        *,
        budget: AcquisitionBudget | None = None,
    ) -> IncrementalDiscoveryResponse:
        """Enumerate one scope; a bounded failure keeps a resumable state."""
        if not isinstance(request, IncrementalDiscoveryRequest):
            raise TypeError("request must be IncrementalDiscoveryRequest")
        started = time.monotonic()
        kind_index, page_cursor = _decode_cursor(request.cursor)
        kinds = request.document_kinds
        if kind_index > len(kinds):
            raise IncrementalDiscoveryError("cursor points past the requested kinds")
        reason_codes: list[str] = []
        candidates: dict[str, DiscoveryCandidate] = {}
        pages = 0
        requests_made = 0
        unproved_dates = 0
        coverage = COVERAGE_COMPLETE
        next_cursor: str | None = None
        local = self._local_sources(request)
        for index in range(kind_index, len(kinds)):
            kind = kinds[index]
            cursor = page_cursor if index == kind_index else None
            while True:
                if requests_made >= request.limits.max_requests:
                    coverage = COVERAGE_PARTIAL
                    reason_codes.append("discovery_request_limit_reached")
                    next_cursor = _encode_cursor(index, cursor)
                    break
                if pages >= request.limits.max_pages:
                    coverage = COVERAGE_PARTIAL
                    reason_codes.append("discovery_page_limit_reached")
                    next_cursor = _encode_cursor(index, cursor)
                    break
                if time.monotonic() - started >= request.limits.max_seconds:
                    coverage = COVERAGE_PARTIAL
                    reason_codes.append("discovery_time_limit_reached")
                    next_cursor = _encode_cursor(index, cursor)
                    break
                adapter_request = self._adapter_request(request, kind, cursor)
                try:
                    page = self._coordinator.discover_page(adapter_request, budget=budget)
                except Exception as exc:
                    coverage = COVERAGE_PARTIAL
                    reason_codes.append(f"discovery_failed:{type(exc).__name__}")
                    next_cursor = _encode_cursor(index, cursor)
                    break
                requests_made += 1
                pages += 1
                unproved = sum(
                    1 for candidate in page.candidates
                    if candidate.filing_date is None
                )
                if unproved:
                    # An unproven publish date never advances a complete
                    # watermark: the caller keeps the diagnostic and the
                    # partial state (interfaces: 未证发布时间保留诊断).
                    unproved_dates += unproved
                    reason_codes.append("candidate_date_unproved")
                    if page.coverage == COVERAGE_COMPLETE:
                        page = replace(page, coverage=COVERAGE_PARTIAL)
                coverage = self._merge_coverage(coverage, page, request, reason_codes)
                for candidate in page.candidates:
                    if not self._in_range(candidate, request):
                        continue
                    key = _candidate_key(candidate)
                    if key in candidates:
                        continue
                    if len(candidates) >= request.limits.max_candidates:
                        coverage = COVERAGE_PARTIAL
                        reason_codes.append("discovery_candidate_limit_reached")
                        next_cursor = _encode_cursor(index, page.next_cursor)
                        break
                    candidates[key] = self._candidate(candidate, request, local)
                if len(candidates) >= request.limits.max_candidates:
                    break
                if page.next_cursor:
                    cursor = page.next_cursor
                    continue
                break
            if next_cursor is not None:
                break
        if not requests_made and not candidates:
            coverage = COVERAGE_UNAVAILABLE
        usage = {
            "requests": requests_made,
            "pages": pages,
            "candidates": len(candidates),
            "unproved_dates": unproved_dates,
            "seconds": round(time.monotonic() - started, 6),
        }
        if budget is not None:
            usage["response_bytes"] = budget.response_bytes_used
        return IncrementalDiscoveryResponse(
            request_id=request.request_id,
            scope={
                "identity": request.identity.to_dict(),
                "source_market": request.source_market,
                "document_kinds": list(request.document_kinds),
                "since_date": request.since_date,
                "as_of_date": request.as_of_date,
            },
            coverage=coverage,
            next_cursor=next_cursor,
            candidates=tuple(candidates.values()),
            usage=usage,
            reason_codes=tuple(dict.fromkeys(reason_codes)),
        )

    @staticmethod
    def _merge_coverage(
        coverage: str,
        page: DiscoveryPage,
        request: IncrementalDiscoveryRequest,
        reason_codes: list[str],
    ) -> str:
        """Keep the weakest statement any page made about the requested range."""
        if coverage == COVERAGE_UNAVAILABLE:
            coverage = COVERAGE_PARTIAL
        if page.coverage != COVERAGE_COMPLETE:
            coverage = COVERAGE_PARTIAL
            reason_codes.extend(page.reason_codes or ("adapter_coverage_partial",))
            return coverage
        if (
            page.covered_from is not None
            and page.covered_from > request.since_date
        ) or (
            page.covered_to is not None
            and page.covered_to < request.as_of_date
        ):
            coverage = COVERAGE_PARTIAL
            reason_codes.append("adapter_window_does_not_cover_range")
        return coverage

    @staticmethod
    def _in_range(candidate: DownloadCandidate, request: IncrementalDiscoveryRequest) -> bool:
        """Both ends are inclusive; unproved dates never enter the listing.

        Their count and the resulting partial coverage are reported by the
        caller loop (``candidate_date_unproved``), never silently dropped.
        """
        published = candidate.filing_date
        if published is None:
            return False
        return request.since_date <= published <= request.as_of_date

    @staticmethod
    def _adapter_request(
        request: IncrementalDiscoveryRequest, document_kind: str, cursor: str | None,
    ) -> SourceRequest:
        """Reuse the existing request contract; the cursor rides in provider scope."""
        identity = request.identity
        return SourceRequest(
            entity=identity.entity,
            document_kind=document_kind,
            as_of_date=request.as_of_date,
            market=request.source_market,
            security_id=identity.security_id,
            identity_scope=identity.identity_scope,
            issuer_link_id=identity.issuer_link_id,
            cursor=cursor,
            schema_version=(
                "1.1"
                if identity.identity_scope is not None or identity.issuer_link_id is not None
                else "1.0"
            ),
        )

    def _local_sources(
        self, request: IncrementalDiscoveryRequest,
    ) -> dict[tuple[str, str], dict[str, Any]]:
        """Index the already-registered originals for this identity and kind."""
        indexed: dict[tuple[str, str], dict[str, Any]] = {}
        resolver = SourceResolver(self._catalog)
        for kind in request.document_kinds:
            source_request = SourceRequest(
                entity=request.identity.entity,
                document_kind=kind,
                as_of_date=request.as_of_date,
                market=request.source_market,
                security_id=request.identity.security_id,
                identity_scope=request.identity.identity_scope,
                issuer_link_id=request.identity.issuer_link_id,
                schema_version=(
                    "1.1"
                    if request.identity.identity_scope is not None
                    or request.identity.issuer_link_id is not None
                    else "1.0"
                ),
            )
            try:
                resolution = resolver.resolve_for_acquisition(source_request)[0]
            except Exception:
                continue
            if resolution.status not in {
                ResolutionStatus.REUSED_EXACT,
                ResolutionStatus.REUSED_EQUIVALENT,
                ResolutionStatus.AMBIGUOUS,
                ResolutionStatus.MISSING,
            }:
                continue
            for handle in resolution.matches:
                if not handle.provider or not handle.provider_document_id:
                    continue
                indexed[(handle.provider, handle.provider_document_id)] = {
                    "schema_version": "2.0",
                    "document_id": handle.document_id,
                    "source_id": handle.source_id,
                    "content_sha256": handle.content_sha256,
                    "byte_size": handle.byte_size,
                    "mime_type": handle.mime_type,
                }
        return indexed

    @staticmethod
    def _candidate(
        candidate: DownloadCandidate,
        request: IncrementalDiscoveryRequest,
        local: dict[tuple[str, str], dict[str, Any]],
    ) -> DiscoveryCandidate:
        listing = candidate.security_id or request.identity.security_id
        existing = local.get((candidate.provider, candidate.provider_document_id))
        return DiscoveryCandidate(
            candidate_key=_candidate_key(candidate),
            provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            source_market=candidate.market,
            document_kind=candidate.document_kind,
            published_at=candidate.filing_date,
            fiscal_year=candidate.fiscal_year,
            fiscal_period=candidate.fiscal_period,
            amended=candidate.amended,
            listing=listing,
            title=candidate.title,
            existing_source_ref=existing,
        )


__all__ = [
    "COVERAGE_COMPLETE",
    "COVERAGE_PARTIAL",
    "COVERAGE_UNAVAILABLE",
    "INCREMENTAL_DISCOVERY_REQUEST_SCHEMA",
    "INCREMENTAL_DISCOVERY_SCHEMA",
    "DiscoveryCandidate",
    "DiscoveryIdentity",
    "DiscoveryLimits",
    "IncrementalDiscoveryError",
    "IncrementalDiscoveryRequest",
    "IncrementalDiscoveryResponse",
    "IncrementalDiscoveryService",
]
