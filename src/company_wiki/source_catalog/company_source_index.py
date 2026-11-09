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
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Any, cast

from company_wiki.source_contract.source_version import SourceRef

from .document_kinds import SOURCE_FACT_KINDS
from .identity_candidates import identity_candidate_clause
from .metadata_observation import metadata_state, observe_metadata
from .reader import CatalogReaderUnavailable
from .resolver import SourceResolver, _source_metadata
from .security_code import canonical_security_code
from .service import SourceCatalog
from .source_location import relative_segments as _relative_segments
from .source_read_policy import source_read_policy_sha256


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
class _IdentityNarrowing:
    """The two fields the resolver's identity gate actually reads."""

    market: str | None
    security_id: str | None


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
        tokens = self._resolver.issuer_identity_tokens(request.company.entity)
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
            "source_read_policy_sha256": source_read_policy_sha256(
                self.catalog.config, None
            ),
        }

    def _company_known(self, identity: CompanyIdentity, tokens: tuple[str, ...]) -> bool:
        """Is this issuer indexed at all, regardless of the caller's filters?

        A dirty projection row is a candidate, not proof of identity. A
        complete search or a qualified match is required to answer.
        """
        after: str | None = None
        remaining = MAX_CANDIDATES
        try:
            identity_clause, identity_params = identity_candidate_clause(
                self.catalog.reader, tokens
            )
            while True:
                limit = min(500, remaining + 1)
                cursor_clause = "AND d.document_id > ?" if after is not None else ""
                cursor_params = (after,) if after is not None else ()
                rows = self.catalog.reader.fetchall(
                    f"""SELECT d.document_id, d.primary_source_id AS document_source_id,
                               d.title, d.document_kind, d.published_date,
                               d.source_status, d.metadata_json,
                               s.content_sha256, s.byte_size, s.mime_type
                        FROM documents d
                        LEFT JOIN sources s ON s.source_id = d.primary_source_id
                        WHERE d.source_status IN ('active', 'retired')
                          {identity_clause}
                          {cursor_clause}
                        ORDER BY d.document_id
                        LIMIT ?""",
                    (*identity_params, *cursor_params, limit),
                )
                page = rows[:remaining]
                entities = self._entities_for([row["document_id"] for row in page])
                for row in page:
                    payload = self._row_dict(row, entities)
                    if self._resolver._entity_matches(
                        identity.entity, payload, metadata=self._visible_metadata(payload),
                        identity_tokens=tokens,
                    ):
                        return True
                if len(rows) > remaining:
                    raise CompanySourceIndexError("unavailable", "candidate_budget_exceeded")
                if len(rows) < limit:
                    return False
                remaining -= len(rows)
                after = rows[-1]["document_id"]
        except (CatalogReaderUnavailable, sqlite3.Error):
            raise CompanySourceIndexError("unavailable", "catalog_unavailable") from None

    # -- candidate scan -----------------------------------------------------

    def _matched_versions(
        self, request: CompanySourceIndexRequest, tokens: tuple[str, ...],
    ) -> tuple[list[_Entry], set[str]]:
        rows = self._candidate_rows(request, tokens)
        entries: dict[str, _Entry] = {}
        security_ids: set[str] = set()
        for row in rows:
            metadata = self._visible_metadata(row)
            if not self._resolver._entity_matches(
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

    @staticmethod
    def _identity_matches(identity: CompanyIdentity, metadata: dict[str, Any]) -> bool:
        """Reuse the resolver's market/security gate without a per-kind request.

        The owner's gate reads exactly ``market`` and ``security_id`` from the
        request, so a two-field stand-in is passed instead of inventing a
        document kind and period this endpoint does not have.  A future change
        to that gate would be a contract change, not a silent bypass.
        """
        narrowed = _IdentityNarrowing(identity.market, identity.security_id)
        return SourceResolver._identity_matches(
            cast(Any, narrowed), metadata,
        ) == "match"

    def _candidate_rows(
        self, request: CompanySourceIndexRequest, tokens: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        kind_clause, kind_params = _kind_clause(request.document_kinds)
        try:
            identity_clause, identity_params = identity_candidate_clause(
                self.catalog.reader, tokens
            )
            rows = self.catalog.reader.fetchall(
                f"""SELECT d.document_id, d.primary_source_id AS document_source_id,
                           d.title, d.document_kind, d.published_date,
                           d.source_status, d.metadata_json,
                           s.content_sha256, s.byte_size, s.mime_type
                    FROM documents d
                    LEFT JOIN sources s ON s.source_id = d.primary_source_id
                    WHERE d.source_status IN ('active', 'retired')
                      AND (d.published_date IS NULL OR d.published_date <= ?)
                      {kind_clause}
                      {identity_clause}
                    ORDER BY COALESCE(d.published_date, '') DESC, d.document_id ASC
                    LIMIT ?""",
                (request.as_of_date, *kind_params, *identity_params, MAX_CANDIDATES + 1),
            )
        except (CatalogReaderUnavailable, sqlite3.Error):
            raise CompanySourceIndexError("unavailable", "catalog_unavailable") from None
        if len(rows) > MAX_CANDIDATES:
            raise CompanySourceIndexError("unavailable", "candidate_budget_exceeded")
        entities = self._entities_for([row["document_id"] for row in rows])
        return [self._row_dict(row, entities) for row in rows]

    def _row_dict(
        self, row: sqlite3.Row, entities: dict[str, list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        payload = dict(row)
        observed, problem = metadata_state(payload.pop("metadata_json", None))
        payload["metadata"] = observed if problem is None else {}
        payload["source_id"] = payload.pop("document_source_id", None)
        document_id = payload["document_id"]
        if entities is None:
            entities = self._entities_for([document_id])
        payload["entities"] = entities.get(document_id, [])
        return payload

    def _entities_for(
        self, document_ids: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """One batched lookup, so a wide candidate set is not N+1 queries."""
        found: dict[str, list[dict[str, Any]]] = {}
        if not document_ids:
            return found
        chunk = 500
        try:
            for start in range(0, len(document_ids), chunk):
                batch = document_ids[start:start + chunk]
                marks = ", ".join("?" for _ in batch)
                for item in self.catalog.reader.fetchall(
                    f"""SELECT de.document_id, e.entity_id, e.name, e.entity_kind
                        FROM document_entities de
                        JOIN entities e ON e.entity_id = de.entity_id
                        WHERE de.document_id IN ({marks})
                        ORDER BY de.document_id, e.entity_id""",
                    tuple(batch),
                ):
                    row = dict(item)
                    found.setdefault(row.pop("document_id"), []).append(row)
        except (CatalogReaderUnavailable, sqlite3.Error):
            raise CompanySourceIndexError("unavailable", "catalog_unavailable") from None
        return found

    def _visible_metadata(self, row: dict[str, Any]) -> dict[str, Any]:
        document = observe_metadata(row.get("metadata")).project_document(dict(row))
        row["published_date"] = document.get("published_date")
        return _source_metadata(
            document,
            store=self.catalog.reader,
            reader=self._resolver.reader,
            current_epoch=self._resolver.current_epoch,
            active_cohorts=self._resolver.active_cohorts,
            legacy_bridge_allowed=self._resolver.legacy_bridge_allowed,
        )

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
        """Report the owner's copy count and whether any copy is readable now.

        Copies are the indexed original locations of this source version; the
        catalog keys versions by content hash, so identical bytes in several
        roots are one version with several copies.  Readability is one bounded
        existence check per copy — the read itself re-verifies the bytes.
        """
        copies = 0
        readable = False
        for location in self._annotated_locations(entry.document_id, entry.source_id):
            root = location["root"]
            if location["candidate_rank"] <= 0:
                continue
            if root.allowed_document_kinds and entry.document_kind not in (
                root.allowed_document_kinds
            ):
                continue
            if root.allowed_statuses and "active" not in root.allowed_statuses:
                continue
            if root.max_file_size is not None and entry.byte_size > root.max_file_size:
                continue
            observed, problem = metadata_state(location["manifest_json"])
            if problem is not None:
                continue
            if observed.get("content_sha256") not in (None, "", entry.content_sha256):
                continue
            copies += 1
            if os.path.isfile(root.path / str(location["relative_path"])):
                readable = True
        if not entry.active:
            return "retired", copies
        return ("available" if readable else "unreadable"), copies

    def _annotated_locations(
        self, document_id: str, source_id: str,
    ) -> list[dict[str, Any]]:
        try:
            indexed = self.catalog.reader.exact_source_locations(document_id, source_id)
        except (CatalogReaderUnavailable, sqlite3.Error):
            return []
        roots = {root.root_id: root for root in self.catalog.config.roots}
        annotated: list[dict[str, Any]] = []
        for item in indexed:
            location = dict(item)
            root = roots.get(location["root_id"])
            if root is None:
                continue
            if _relative_segments(str(location["relative_path"])) is None:
                continue
            location["root_priority"] = root.priority
            location["root"] = root
            annotated.append(location)
        return self.catalog._annotate_locations(document_id, annotated)


def _after(key: tuple[str, str], cursor: tuple[str, str]) -> bool:
    """Is ``key`` strictly later than ``cursor`` in (date desc, id asc) order?"""
    published, document_id = key
    cursor_published, cursor_document = cursor
    if published != cursor_published:
        return published < cursor_published
    return document_id > cursor_document


def _kind_clause(kinds: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    if not kinds:
        return "", ()
    marks = ", ".join("?" for _ in kinds)
    return f"AND d.document_kind IN ({marks})", kinds


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
