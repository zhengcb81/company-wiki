"""Bounded, path-free listing of one company's indexed source versions.

This is the company-level companion to ``source_query_cli``.  A per-kind query
answers "which version of *this kind* for *this period*"; it cannot answer
"which sources does this company have".  The index below answers exactly that
question without ever handing a consumer a physical coordinate: the response
carries logical ``SourceRef`` values plus the minimum manifest fields a reader
needs, and every read still goes through the existing exact-version reader.

Design constraints (frozen in ``tests/fixtures/company_source_index/wire_v1.json``):

* ordering is ``published_date`` descending then ``document_id`` ascending, so
  the concatenation of pages equals the unpaged listing;
* ``as_of_date`` is an inclusive publication bound.  A document whose
  publication date is unknown cannot be shown to be later than the bound, so it
  is listed (``published_date: null``) at the end rather than dropped — an
  unknown date is missing information, not a future publication;
* identical bytes in several roots are ONE source version (the catalog keys
  ``sources`` by content hash) with several indexed physical copies;
* a retired version or one whose bytes are gone is reported as such — never
  dropped, so "company has no sources" is never confused with "sources are
  unusable";
* the candidate scan is bounded, and no page carries more than
  ``MAX_PAGE_SIZE`` entries.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from company_wiki.source_contract.source_version import SourceRef

from .catalog_query_contract import (
    CatalogDocumentCandidate,
    CatalogDocumentCandidateQuery,
    CatalogQueryUnavailable,
)
from .document_kinds import SOURCE_FACT_KINDS
from .metadata_observation import observe_metadata
from .resolver import SourceResolver
from .security_code import canonical_security_code
from .service import SourceCatalog
from .models import SourceCopyAvailabilityRequest


REQUEST_SCHEMA_VERSION = "company-wiki-company-source-index-request/1"
RESPONSE_SCHEMA_VERSION = "company-wiki-company-source-index/1"
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
#: The same candidate ceiling the existing per-kind reader uses; it is a real
#: work bound, not a result-shaping gate.
MAX_CANDIDATES = 20_000
_MAX_REQUEST_BYTES = 1_048_576

_KNOWN_DOCUMENT_KINDS = frozenset(SOURCE_FACT_KINDS) | {"other"}
_STATUSES = frozenset({"ok", "not_found", "ambiguous", "unavailable", "blocked"})
_AVAILABILITY = frozenset({"available", "unreadable", "retired"})
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_REQUEST_FIELDS = frozenset(
    {"schema_version", "company", "as_of_date", "document_kinds", "page_size", "cursor"}
)
_COMPANY_FIELDS = frozenset({"entity", "market", "security_id"})


class CompanySourceIndexError(ValueError):
    """A named refusal that never carries a physical coordinate."""

    def __init__(self, status: str, reason: str):
        if status not in _STATUSES - {"ok"}:
            raise ValueError(f"unknown index status: {status}")
        self.status = status
        self.reason = reason
        super().__init__(f"{status}: {reason}")


@dataclass(frozen=True)
class CompanyIdentity:
    entity: str
    market: str | None = None
    security_id: str | None = None

    @property
    def narrowed(self) -> bool:
        return bool(self.market or self.security_id)

    def to_dict(self) -> dict[str, object]:
        return {
            "entity": self.entity,
            "market": self.market,
            "security_id": self.security_id,
        }


@dataclass(frozen=True)
class CompanySourceIndexRequest:
    company: CompanyIdentity
    as_of_date: str
    document_kinds: tuple[str, ...] = ()
    page_size: int = DEFAULT_PAGE_SIZE
    cursor: str | None = None
    schema_version: str = REQUEST_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, payload: object) -> "CompanySourceIndexRequest":
        if not isinstance(payload, dict) or set(payload) != _REQUEST_FIELDS:
            raise CompanySourceIndexError("blocked", "invalid_request")
        if payload["schema_version"] != REQUEST_SCHEMA_VERSION:
            raise CompanySourceIndexError("blocked", "invalid_request")
        company = payload["company"]
        if not isinstance(company, dict) or set(company) != _COMPANY_FIELDS:
            raise CompanySourceIndexError("blocked", "invalid_request")
        return cls(
            company=CompanyIdentity(
                entity=_required_text(company["entity"]),
                market=_text(company["market"], required=False, upper=True),
                security_id=_text(company["security_id"], required=False),
            ),
            as_of_date=_as_of_date(payload["as_of_date"]),
            document_kinds=_document_kinds(payload["document_kinds"]),
            page_size=_page_size(payload["page_size"]),
            cursor=_cursor(payload["cursor"]),
        )


def _required_text(value: object) -> str:
    text = _text(value, required=True)
    assert text is not None  # required=True either raises or returns text
    return text


def _text(value: object, *, required: bool, upper: bool = False) -> str | None:
    if value is None:
        if required:
            raise CompanySourceIndexError("blocked", "invalid_request")
        return None
    if not isinstance(value, str):
        raise CompanySourceIndexError("blocked", "invalid_request")
    stripped = value.strip()
    if not stripped:
        if required:
            raise CompanySourceIndexError("blocked", "invalid_request")
        return None
    return stripped.upper() if upper else stripped


def _as_of_date(value: object) -> str:
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise CompanySourceIndexError("blocked", "invalid_request")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise CompanySourceIndexError("blocked", "invalid_request") from None
    return value


def _document_kinds(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise CompanySourceIndexError("blocked", "invalid_request")
    kinds = tuple(value)
    if len(set(kinds)) != len(kinds) or any(
        kind not in _KNOWN_DOCUMENT_KINDS for kind in kinds
    ):
        raise CompanySourceIndexError("blocked", "invalid_request")
    return kinds


def _page_size(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CompanySourceIndexError("blocked", "invalid_request")
    if not 1 <= value <= MAX_PAGE_SIZE:
        raise CompanySourceIndexError("blocked", "invalid_request")
    return value


def _cursor(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CompanySourceIndexError("blocked", "invalid_request")
    _decode_cursor(value)
    return value


def encode_cursor(published_date: str, document_id: str, source_id: str) -> str:
    raw = json.dumps(
        {"d": document_id, "p": published_date, "s": source_id},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(value: str) -> tuple[str, str, str]:
    padding = "=" * (-len(value) % 4)
    try:
        raw = base64.urlsafe_b64decode(value + padding)
        payload = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeError, ValueError):
        raise CompanySourceIndexError("blocked", "invalid_request") from None
    if (
        not isinstance(payload, dict)
        or set(payload) != {"p", "d", "s"}
        or not isinstance(payload["p"], str)
        or not isinstance(payload["d"], str)
        or not payload["d"]
        or not isinstance(payload["s"], str)
        or not payload["s"]
    ):
        raise CompanySourceIndexError("blocked", "invalid_request")
    return payload["p"], payload["d"], payload["s"]


@dataclass
class _Entry:
    """One source version plus every indexed copy that carries those bytes."""

    source_id: str
    document_ids: list[str]
    document_id: str
    content_sha256: str
    byte_size: int
    mime_type: str
    published_date: str
    document_kind: str
    title: str
    metadata: dict[str, Any]
    active: bool

    def sort_key(self) -> tuple[str, str]:
        return self.published_date, self.document_id


class CompanySourceIndex:
    """Enumerate one company's indexed source versions, bounded and pathless."""

    def __init__(self, catalog: SourceCatalog):
        if not isinstance(catalog, SourceCatalog):
            raise TypeError("catalog must be SourceCatalog")
        self.catalog = catalog
        self._resolver = SourceResolver(catalog)

    def page(self, request: CompanySourceIndexRequest) -> dict[str, object]:
        """Answer with a page, or with a named non-page answer.

        ``not_found`` and ``ambiguous`` are ANSWERS (the caller asked a
        question the owner can answer); ``blocked``/``unavailable`` are
        refusals raised as ``CompanySourceIndexError``.  A consumer that only
        looks at ``sources`` therefore still sees the difference between "no
        such issuer" and "the catalog could not be read".
        """
        if not isinstance(request, CompanySourceIndexRequest):
            raise TypeError("request must be CompanySourceIndexRequest")
        tokens = self._resolver.issuer_identity_tokens(
            request.company.entity,
            market=request.company.market,
            security_id=request.company.security_id,
        )
        entries, security_ids = self._matched_versions(request, tokens)
        status, reason = "ok", ""
        if not entries:
            # An empty page caused by the caller's own filters is not the same
            # answer as an issuer the owner does not index at all.
            if self._company_known(request.company, tokens):
                status, reason = "ok", ""
            else:
                status, reason = "not_found", "company_not_indexed"
        elif not request.company.narrowed and len(security_ids) > 1:
            status, reason = "ambiguous", "company_identity_ambiguous"
        window: list[_Entry] = []
        offset = 0
        has_more = False
        if status == "ok":
            offset, cursor_source = self._offset(entries, request.cursor)
            if cursor_source:
                # The cursor version itself was already delivered: skip every
                # copy of it even if the canonical document moved on rescan.
                while (
                    offset < len(entries)
                    and entries[offset].source_id == cursor_source
                ):
                    offset += 1
            window = entries[offset:offset + request.page_size]
            has_more = offset + request.page_size < len(entries)
        return {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "status": status,
            "reason": reason,
            "company": request.company.to_dict(),
            "as_of_date": request.as_of_date,
            "page": {
                "cursor": request.cursor,
                "next_cursor": (
                    encode_cursor(
                        window[-1].published_date,
                        window[-1].document_id,
                        window[-1].source_id,
                    )
                    if has_more else None
                ),
                "has_more": has_more,
                "count": len(window),
            },
            "sources": [self._entry_payload(entry) for entry in window],
            "source_read_policy_sha256": self.catalog.source_read_policy_digest(),
        }

    def _company_known(self, identity: CompanyIdentity, tokens: tuple[str, ...]) -> bool:
        """Check issuer presence through Catalog's bounded query port."""
        after: str | None = None
        remaining = MAX_CANDIDATES
        try:
            while True:
                limit = min(500, remaining + 1)
                rows = tuple(
                    self._candidate_payload(candidate)
                    for candidate in self.catalog.document_candidates(
                        CatalogDocumentCandidateQuery(
                            identity_tokens=tokens,
                            limit=limit,
                            after_document_id=after,
                            order="document_id",
                        )
                    )
                )
                page = rows[:remaining]
                for row in page:
                    if self._resolver.entity_matches(
                        identity.entity,
                        row,
                        metadata=self._visible_metadata(row),
                        identity_tokens=tokens,
                    ):
                        return True
                if len(rows) > remaining:
                    raise CompanySourceIndexError(
                        "unavailable", "candidate_budget_exceeded"
                    )
                if len(rows) < limit:
                    return False
                remaining -= len(rows)
                after = rows[-1]["document_id"]
        except CatalogQueryUnavailable:
            raise CompanySourceIndexError(
                "unavailable", "catalog_unavailable"
            ) from None

    # -- candidate scan -----------------------------------------------------

    # -- candidate scan -----------------------------------------------------

    def _matched_versions(
        self, request: CompanySourceIndexRequest, tokens: tuple[str, ...],
    ) -> tuple[list[_Entry], set[str]]:
        rows = self._candidate_rows(request, tokens)
        entries: dict[str, _Entry] = {}
        security_ids: set[str] = set()
        for row in rows:
            metadata = self._visible_metadata(row)
            if not self._resolver.entity_matches(
                request.company.entity, row, metadata=metadata,
                identity_tokens=tokens,
            ):
                continue
            if not self._identity_matches(request.company, metadata):
                continue
            security_key = _security_key(metadata)
            if security_key:
                security_ids.add(security_key)
            self._merge(entries, row, metadata)
        # published_date descending, document_id ascending (stable two-pass
        # sort: the second key is applied first).
        ordered = sorted(entries.values(), key=lambda entry: entry.document_id)
        ordered.sort(key=lambda entry: entry.published_date, reverse=True)
        return ordered, security_ids

    def _identity_matches(self, identity: CompanyIdentity, metadata: dict[str, Any]) -> bool:
        """Use the resolver's public identity contract for company listings."""
        return self._resolver.match_source_identity(
            market=identity.market,
            security_id=identity.security_id,
            metadata=metadata,
        ) == "match"

    def _candidate_rows(
        self, request: CompanySourceIndexRequest, tokens: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        try:
            candidates = self.catalog.document_candidates(
                CatalogDocumentCandidateQuery(
                    identity_tokens=tokens,
                    limit=MAX_CANDIDATES + 1,
                    as_of_date=request.as_of_date,
                    document_kinds=request.document_kinds,
                    order="published_date",
                )
            )
        except CatalogQueryUnavailable:
            raise CompanySourceIndexError(
                "unavailable", "catalog_unavailable"
            ) from None
        if len(candidates) > MAX_CANDIDATES:
            raise CompanySourceIndexError("unavailable", "candidate_budget_exceeded")
        return [self._candidate_payload(candidate) for candidate in candidates]

    @staticmethod
    def _candidate_payload(candidate: CatalogDocumentCandidate) -> dict[str, Any]:
        """Adapt Catalog's detached record into the resolver's identity view."""
        return {
            "document_id": candidate.document_id,
            "source_id": candidate.source_id,
            "title": candidate.title,
            "document_kind": candidate.document_kind,
            "published_date": candidate.published_date,
            "source_status": candidate.source_status,
            "content_sha256": candidate.content_sha256,
            "byte_size": candidate.byte_size,
            "mime_type": candidate.mime_type,
            "metadata": candidate.metadata_as_dict(),
            "entities": [
                {
                    "entity_id": entity.entity_id,
                    "name": entity.name,
                    "entity_kind": entity.entity_kind,
                }
                for entity in candidate.entities
            ],
        }

    def _visible_metadata(self, row: dict[str, Any]) -> dict[str, Any]:
        document = observe_metadata(row.get("metadata")).project_document(dict(row))
        row["published_date"] = document.get("published_date")
        return self._resolver.project_source_metadata(document)

    @staticmethod
    def _merge(
        entries: dict[str, _Entry], row: dict[str, Any], metadata: dict[str, Any],
    ) -> None:
        source_id = str(row.get("source_id") or "")
        if not source_id or not row.get("content_sha256"):
            return
        active = str(row.get("source_status") or "") == "active"
        existing = entries.get(source_id)
        if existing is not None:
            existing.document_ids.append(str(row["document_id"]))
            if active and not existing.active:
                # Prefer a live copy as the canonical ref for this version.
                existing.document_id = str(row["document_id"])
                existing.active = True
                existing.byte_size = int(row["byte_size"])
                existing.mime_type = str(row["mime_type"])
                existing.title = str(row.get("title") or "")
                existing.metadata = metadata
            return
        entries[source_id] = _Entry(
            source_id=source_id,
            document_ids=[str(row["document_id"])],
            document_id=str(row["document_id"]),
            content_sha256=str(row["content_sha256"]),
            byte_size=int(row["byte_size"]),
            mime_type=str(row["mime_type"]),
            published_date=str(row.get("published_date") or ""),
            document_kind=str(row.get("document_kind") or ""),
            title=str(row.get("title") or ""),
            metadata=metadata,
            active=active,
        )

    # -- paging -------------------------------------------------------------

    @staticmethod
    def _offset(entries: list[_Entry], cursor: str | None) -> tuple[int, str]:
        """Resume strictly after the cursor entry.

        A rescan between pages can change which physical copy is canonical for
        one version, so the exact ``(published_date, document_id)`` pair may no
        longer exist.  The listing order is total, so resume after the last
        entry that still sorts at or before the cursor instead of failing the
        whole listing: a page boundary is not a correctness boundary here.
        """
        if cursor is None:
            return 0, ""
        published, document_id, source_id = _decode_cursor(cursor)
        for index, entry in enumerate(entries):
            if entry.sort_key() == (published, document_id):
                return index + 1, source_id
        cursor_key = (published, document_id)
        for index, entry in enumerate(entries):
            if _after(entry.sort_key(), cursor_key):
                return index, source_id
        return len(entries), source_id

    # -- payload ------------------------------------------------------------

    def _entry_payload(self, entry: _Entry) -> dict[str, object]:
        ref = SourceRef(
            document_id=entry.document_id,
            source_id=entry.source_id,
            content_sha256=entry.content_sha256,
            byte_size=entry.byte_size,
            mime_type=entry.mime_type,
        )
        availability, copies = self._copy_state(entry)
        return {
            "source_ref": {
                "document_id": ref.document_id,
                "source_id": ref.source_id,
                "content_sha256": ref.content_sha256,
                "byte_size": ref.byte_size,
                "mime_type": ref.mime_type,
                "schema_version": ref.schema_version,
            },
            "document_kind": entry.document_kind,
            "market": _claim(entry.metadata, "market"),
            "security_id": _claim(entry.metadata, "security_id"),
            "published_date": entry.published_date or None,
            "fiscal_year": _fiscal_year(entry.metadata),
            "fiscal_period": _claim(entry.metadata, "fiscal_period"),
            "period_end": _claim(entry.metadata, "period_end"),
            "language": _claim(entry.metadata, "language"),
            "title": entry.title,
            "form_type": _claim(entry.metadata, "form_type"),
            "availability": availability,
            "copies": copies,
        }

    def _copy_state(self, entry: _Entry) -> tuple[str, int]:
        """Ask Catalog's storage port for a pathless copy observation."""
        availability = self.catalog.source_copy_availability(
            SourceCopyAvailabilityRequest(
                document_id=entry.document_id,
                source_id=entry.source_id,
                document_kind=entry.document_kind,
                byte_size=entry.byte_size,
                content_sha256=entry.content_sha256,
            )
        )
        if not entry.active:
            return "retired", availability.copy_count
        status = "available" if availability.readable else "unreadable"
        return status, availability.copy_count


def _after(key: tuple[str, str], cursor: tuple[str, str]) -> bool:
    """Is ``key`` strictly later than ``cursor`` in (date desc, id asc) order?"""
    published, document_id = key
    cursor_published, cursor_document = cursor
    if published != cursor_published:
        return published < cursor_published
    return document_id > cursor_document


_SECURITY_CODE_RE = re.compile(
    r"(?:[0-9]{1,6}|[A-Za-z][A-Za-z0-9]{0,11})(?:[.\-][A-Za-z0-9]{1,4}){0,2}\Z"
)


def _security_key(metadata: dict[str, Any]) -> str:
    """A market-qualified SECURITY CODE, or "" when the field is not a code.

    Identity ambiguity means two competing securities, not two spellings of one
    issuer: a record whose ``security_id`` carries a company name (observed in
    production) must not turn a single-issuer company into an ambiguous one.
    """
    code = str(metadata.get("security_id") or "").strip()
    if not code or not _SECURITY_CODE_RE.fullmatch(code):
        return ""
    market = str(metadata.get("market") or "").strip().upper()
    return f"{market}:{canonical_security_code(code, market) or code}"


def _claim(metadata: dict[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _fiscal_year(metadata: dict[str, Any]) -> int | None:
    value = metadata.get("fiscal_year")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip() if value is not None else ""
    return int(text) if re.fullmatch(r"\d{4}", text) else None


__all__ = [
    "CompanyIdentity",
    "CompanySourceIndex",
    "CompanySourceIndexError",
    "CompanySourceIndexRequest",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "encode_cursor",
]
