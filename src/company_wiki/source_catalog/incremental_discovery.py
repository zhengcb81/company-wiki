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
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re
import time
from typing import Any

from company_wiki.source_contract.source_version import SourceReadError

from .acquisition import AcquisitionCoordinator, AcquisitionError, DiscoveryPage, DownloadCandidate
from .adapter_process import AdapterProcessError
from .document_kinds import PERIODIC_DOCUMENT_KINDS
from .download_budget import AcquisitionBudget, AcquisitionBudgetExceeded
from .resolver import SourceRequest, SourceResolver
from .security_code import security_codes_equivalent
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
_PERIODS = frozenset({"FY", "H1", "H2", "Q1", "Q2", "Q3", "Q4"})


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
    except ValueError as original_error:
        raise IncrementalDiscoveryError(f"{name} must be a canonical YYYY-MM-DD date") from original_error
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
    entity_id: str | None = None
    listing_id: str | None = None
    market: str | None = None
    ticker: str | None = None
    exchange: str | None = None

    @classmethod
    def from_dict(cls, value: Any) -> "DiscoveryIdentity":
        if isinstance(value, dict) and "entity_id" in value:
            return cls._from_listing(value)
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

    @classmethod
    def _from_listing(cls, value: dict[str, Any]) -> "DiscoveryIdentity":
        required = {"entity_id", "listing_id", "market", "ticker"}
        if not required.issubset(value) or set(value) - (required | {"exchange", "issuer_link_id"}):
            raise IncrementalDiscoveryError("identity has unsupported or missing listing fields")
        market = _text(value["market"], "identity.market")
        if market not in _MARKETS:
            raise IncrementalDiscoveryError("identity.market must be CN, HK or US")
        ticker = _text(value["ticker"], "identity.ticker")
        link = _optional_text(value.get("issuer_link_id"), "identity.issuer_link_id")
        if link is not None and _ISSUER_LINK_ID_RE.fullmatch(link) is None:
            raise IncrementalDiscoveryError("identity.issuer_link_id is malformed")
        return cls(
            # The ticker is only a lookup input. The CWP owner supplies the
            # canonical entity and security ID before any provider action.
            entity=ticker,
            issuer_link_id=link,
            entity_id=_text(value["entity_id"], "identity.entity_id"),
            listing_id=_text(value["listing_id"], "identity.listing_id"),
            market=market,
            ticker=ticker,
            exchange=_optional_text(value.get("exchange"), "identity.exchange"),
        )

    def to_dict(self) -> dict[str, Any]:
        if self.entity_id is not None:
            return {
                "entity_id": self.entity_id,
                "listing_id": self.listing_id,
                "market": self.market,
                "ticker": self.ticker,
                **({"exchange": self.exchange} if self.exchange else {}),
            }
        return {
            "entity": self.entity,
            "security_id": self.security_id,
            "identity_scope": self.identity_scope,
            "issuer_link_id": self.issuer_link_id,
        }


def bind_discovery_identity(
    catalog: SourceCatalog, identity: DiscoveryIdentity, market: str,
) -> DiscoveryIdentity:
    """Bind the caller's correlation IDs to the owner's exact market ticker."""
    if identity.entity_id is None:
        return identity
    if identity.market != market or identity.ticker is None:
        raise IncrementalDiscoveryError("discovery_source_market_mismatch")
    selected = catalog.identify_company(identity.ticker, market=market).resolved
    if (selected is None or not selected.verified or not selected.active
            or selected.match_basis != "ticker_exact" or selected.market != market
            or not security_codes_equivalent(
                identity.ticker, selected.security_id,
                left_market=market, right_market=selected.market,
            )):
        raise IncrementalDiscoveryError("discovery_listing_unverified")
    if identity.issuer_link_id is not None and identity.issuer_link_id != selected.issuer_link_id:
        raise IncrementalDiscoveryError("discovery_issuer_link_mismatch")
    return replace(
        identity,
        entity=selected.canonical_name,
        security_id=selected.security_id,
        identity_scope="listing" if selected.issuer_link_id is not None else None,
        issuer_link_id=selected.issuer_link_id,
    )


@dataclass(frozen=True)
class DiscoveryLimits:
    """The caller's ceiling for this enumeration."""

    max_candidates: int = 100
    max_pages: int = 8
    max_requests: int = 8
    max_seconds: float = 120.0
    max_bytes: int = 16 * 1024 * 1024
    max_cost_usd: str = "0"

    @classmethod
    def from_dict(cls, value: Any) -> "DiscoveryLimits":
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise IncrementalDiscoveryError("limits must be an object")
        allowed = {
            "max_candidates", "max_pages", "max_requests", "max_seconds",
            "max_bytes", "timeout_seconds", "max_cost_usd",
        }
        if set(value) - allowed:
            raise IncrementalDiscoveryError("limits has unsupported fields")
        time_limits = [value[key] for key in ("max_seconds", "timeout_seconds") if key in value]
        if any(type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0
               for seconds in time_limits):
            raise IncrementalDiscoveryError("discovery time limit must be finite and positive")
        cost = _text(value.get("max_cost_usd", cls.max_cost_usd), "limits.max_cost_usd")
        try:
            amount = Decimal(cost)
        except InvalidOperation as original_error:
            raise IncrementalDiscoveryError("limits.max_cost_usd must be decimal text") from original_error
        if not amount.is_finite() or amount < 0:
            raise IncrementalDiscoveryError("limits.max_cost_usd must be finite and non-negative")
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
            max_seconds=float(min(time_limits, default=cls.max_seconds)),
            max_bytes=_positive_int(value.get("max_bytes", cls.max_bytes), "limits.max_bytes"),
            max_cost_usd=cost,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_candidates": self.max_candidates,
            "max_pages": self.max_pages,
            "max_requests": self.max_requests,
            "max_seconds": self.max_seconds,
            "max_bytes": self.max_bytes,
            "max_cost_usd": self.max_cost_usd,
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
        period = None
        if self.fiscal_year is not None and self.fiscal_period is not None:
            period = {"fiscal_year": self.fiscal_year, "name": self.fiscal_period}
            if self.fiscal_period in {"Q1", "Q2", "Q3", "Q4"}:
                period["fiscal_quarter"] = int(self.fiscal_period[1:])
        return {
            "candidate_key": self.candidate_key,
            "provider": self.provider,
            "provider_document_id": self.provider_document_id,
            "source_market": self.source_market,
            "document_kind": self.document_kind,
            "published_at": self.published_at,
            "fiscal_year": self.fiscal_year,
            "fiscal_period": period,
            "amended": self.amended,
            "listing": self.listing,
            "title": self.title,
            "source_ref": self.existing_source_ref,
            "existing_source_ref": self.existing_source_ref,
            **({"revision_id": self.existing_source_ref["content_sha256"]}
               if self.existing_source_ref is not None else {}),
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
            "filing_date": candidate.filing_date,
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


@dataclass(frozen=True)
class _ResumePoint:
    kind_index: int
    page_cursor: str | None
    offset: int = 0
    page_sha256: str | None = None


def _encode_cursor(point: _ResumePoint) -> str:
    return json.dumps(
        {"kind_index": point.kind_index, "page_cursor": point.page_cursor,
         "offset": point.offset, "page_sha256": point.page_sha256},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _decode_cursor(cursor: str | None) -> _ResumePoint:
    """Read the resume point.  An unreadable cursor is a refusal, not a guess."""
    if cursor is None:
        return _ResumePoint(0, None)
    try:
        payload = json.loads(cursor)
    except json.JSONDecodeError as original_error:
        raise IncrementalDiscoveryError("cursor is not a discovery cursor") from original_error
    if not isinstance(payload, dict) or set(payload) not in (
        {"kind_index", "page_cursor"}, {"kind_index", "page_cursor", "offset", "page_sha256"},
    ):
        raise IncrementalDiscoveryError("cursor is not a discovery cursor")
    kind_index = payload["kind_index"]
    if isinstance(kind_index, bool) or not isinstance(kind_index, int) or kind_index < 0:
        raise IncrementalDiscoveryError("cursor kind_index is invalid")
    page_cursor = payload["page_cursor"]
    if page_cursor is not None and (
        not isinstance(page_cursor, str) or not page_cursor.strip()
    ):
        raise IncrementalDiscoveryError("cursor page_cursor is invalid")
    offset = payload.get("offset", 0)
    page_sha256 = payload.get("page_sha256")
    if type(offset) is not int or offset < 0 or bool(offset) != (page_sha256 is not None):
        raise IncrementalDiscoveryError("cursor page offset is invalid")
    if page_sha256 is not None and (
        not isinstance(page_sha256, str) or _SHA256_RE.fullmatch(page_sha256) is None
    ):
        raise IncrementalDiscoveryError("cursor page identity is invalid")
    return _ResumePoint(kind_index, page_cursor, offset, page_sha256)


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
        deadline = started + request.limits.max_seconds
        initial_point = _decode_cursor(request.cursor)
        kinds = request.document_kinds
        if initial_point.kind_index >= len(kinds):
            raise IncrementalDiscoveryError("cursor points past the requested kinds")
        point: _ResumePoint | None = initial_point
        identity = bind_discovery_identity(self._catalog, request.identity, request.source_market)
        resolver = SourceResolver(self._catalog)
        reason_codes: list[str] = []
        candidates: dict[str, DiscoveryCandidate] = {}
        pages = 0
        requests_made = 0
        unproved_dates = 0
        coverage = COVERAGE_COMPLETE
        visited: set[tuple[int, str | None]] = set()
        while point is not None:
            if requests_made >= request.limits.max_requests:
                reason_codes.append("discovery_request_limit_reached")
                break
            if pages >= request.limits.max_pages:
                reason_codes.append("discovery_page_limit_reached")
                break
            if time.monotonic() >= deadline:
                reason_codes.append("discovery_time_limit_reached")
                break
            if budget is not None and budget.remaining_transport_bytes == 0:
                reason_codes.append("discovery_byte_limit_reached")
                break
            index, cursor = point.kind_index, point.page_cursor
            next_kind = _ResumePoint(index + 1, None) if index + 1 < len(kinds) else None
            if (index, cursor) in visited:
                coverage = COVERAGE_PARTIAL
                reason_codes.append("provider_discovery_cursor_repeated")
                point = next_kind
                continue
            visited.add((index, cursor))
            adapter_request = self._adapter_request(request, identity, kinds[index], cursor)
            requests_made += 1
            try:
                page = self._coordinator.discover_page(
                    adapter_request, budget=budget, since_date=request.since_date,
                )
            except (AcquisitionError, AcquisitionBudgetExceeded, AdapterProcessError, OSError, ValueError) as exc:
                coverage = COVERAGE_PARTIAL
                code = getattr(exc, "error_code", None) or type(exc).__name__
                reason_codes.append(f"discovery_failed:{code}")
                # A provider capability gap for one kind cannot suppress its
                # siblings. FF retains this window as incomplete for retry.
                point = next_kind
                continue
            pages += 1
            unproved = sum(candidate.filing_date is None for candidate in page.candidates)
            if unproved:
                unproved_dates += unproved
                reason_codes.append("candidate_date_unproved")
                coverage = COVERAGE_PARTIAL
            coverage = self._merge_coverage(coverage, page, request, reason_codes)
            page_hits = {
                _candidate_key(candidate): candidate for candidate in page.candidates
                if self._in_range(candidate, request)
            }
            keys = tuple(page_hits)
            page_sha = hashlib.sha256("".join(keys).encode("ascii")).hexdigest()
            if point.offset and (point.page_sha256 != page_sha or point.offset >= len(keys)):
                coverage = COVERAGE_PARTIAL
                reason_codes.append("provider_discovery_page_changed")
                point = _ResumePoint(index, cursor)
                break
            stop_reason = None
            for position in range(point.offset, len(keys)):
                key = keys[position]
                if key in candidates:
                    continue
                if len(candidates) >= request.limits.max_candidates:
                    stop_reason = "discovery_candidate_limit_reached"
                elif time.monotonic() >= deadline:
                    stop_reason = "discovery_time_limit_reached"
                if stop_reason is not None:
                    point = (_ResumePoint(index, cursor, position, page_sha)
                             if position else _ResumePoint(index, cursor))
                    break
                candidate = page_hits[key]
                candidates[key] = self._candidate(candidate, adapter_request, resolver)
            else:
                point = _ResumePoint(index, page.next_cursor) if page.next_cursor else next_kind
            if stop_reason is not None:
                reason_codes.append(stop_reason)
                break
            if point is not None and len(candidates) >= request.limits.max_candidates:
                reason_codes.append("discovery_candidate_limit_reached")
                break
        if pages == 0:
            coverage = COVERAGE_UNAVAILABLE
        usage = {
            "requests": requests_made,
            "pages": pages,
            "candidates": len(candidates),
            "unproved_dates": unproved_dates,
            "seconds": round(time.monotonic() - started, 6),
        }
        if budget is not None and budget.usage_reported:
            usage["response_bytes"] = budget.response_bytes_used
            if budget.http_exchanges_complete is True:
                usage["http_requests"] = budget.http_exchanges_used
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
            next_cursor=_encode_cursor(point) if point is not None else None,
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
        request: IncrementalDiscoveryRequest, identity: DiscoveryIdentity,
        document_kind: str, cursor: str | None,
    ) -> SourceRequest:
        """Use a bounded as-of search, without asking the provider for bytes."""
        return SourceRequest(
            entity=identity.entity,
            document_kind=document_kind,
            as_of_date=request.as_of_date,
            market=request.source_market,
            security_id=identity.security_id,
            identity_scope=identity.identity_scope,
            issuer_link_id=identity.issuer_link_id,
            cursor=cursor,
            mode="latest_as_of",
            schema_version=(
                "1.1"
                if identity.identity_scope is not None or identity.issuer_link_id is not None
                else "1.0"
            ),
        )

    @staticmethod
    def _candidate(
        candidate: DownloadCandidate, request: SourceRequest, resolver: SourceResolver,
    ) -> DiscoveryCandidate:
        period = candidate.fiscal_period
        periodic = candidate.document_kind in PERIODIC_DOCUMENT_KINDS.union({"earnings_transcript"})
        year = candidate.fiscal_year if periodic and period in _PERIODS else None
        ref = None
        exact = replace(
            request, mode=None, cursor=None, provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            fiscal_year=year, fiscal_period=period if year is not None else None,
            form_type=candidate.form_type,
        )
        try:
            resolution, verified = resolver.resolve_for_acquisition(
                exact, observed_original_url=candidate.source_url,
            )
        except SourceReadError:
            verified = None
        if verified is not None and resolution.matches[0].published_date == candidate.filing_date:
            ref = verified.source_ref.to_dict()
        return DiscoveryCandidate(
            candidate_key=_candidate_key(candidate),
            provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            source_market=candidate.market,
            document_kind=candidate.document_kind,
            published_at=candidate.filing_date,
            fiscal_year=year,
            fiscal_period=period if year is not None else None,
            amended=candidate.amended,
            listing=candidate.security_id or request.security_id,
            title=candidate.title,
            existing_source_ref=ref,
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
    "bind_discovery_identity",
    "IncrementalDiscoveryError",
    "IncrementalDiscoveryRequest",
    "IncrementalDiscoveryResponse",
    "IncrementalDiscoveryService",
]
