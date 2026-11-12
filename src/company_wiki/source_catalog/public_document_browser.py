"""Public, pathless, read-only browse over the local source catalog.

G-CWP-01 (Dashboard unified harness): the resolver picks ONE source for a
request, ``source_query_cli`` needs an explicit document_kind/as_of_date, and
neither can act as the paginated cabinet of EVERY logical document an entity
has (annual/interim reports, prospectuses, IR material, call transcripts…).
This module is that cabinet, on the same zero-write read model as the rest
of the v2 read slice:

- browse by canonical entity key (``document_entities.entity_id`` or the
  declared ``canonical_entity_id`` capture field), with optional
  market/document-kind/fiscal-year/language/status filters;
- every returned row is ONE frozen byte version of ONE logical document,
  carrying its complete SourceRef v2 (document_id + source_id +
  content_sha256 + byte_size + mime_type).  Multiple sources under one
  document_id are returned as separate items with separate
  ``document_version_id`` values; callers never guess a latest version from
  document_id alone;
- ``document_version_id`` is a deterministic, opaque, path-free token
  (``cwpdv1-<43 base64url chars>`` of the version triple) that reopens to
  exactly that SourceRef via
  :meth:`PublicDocumentBrowser.reopen_document_version`;
- pagination is pinned to a content-addressed catalog revision: the cursor
  and ``snapshot_id`` encode the entity, filters and revision digest, and a
  page is only served while the catalog still hashes to the pinned revision;
  otherwise the response state is ``stale`` and never silently mixes
  revisions;
- facets count the filtered snapshot only; ``total`` is exact;
- responses distinguish ``available`` / ``empty`` / ``partial`` / ``stale``
  (transport failures surface as ``unavailable`` from the CLI envelope);
- read-only: no download, OCR, parsing or summary is triggered, and no
  physical path, root path or catalog layout detail is ever emitted.
  ``storage_state`` reports whether an active original location has a
  configured root and a valid relative locator. On open, the source reader
  checks the current filesystem location, eligibility and original bytes.

"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from ..wire_json import parse_json
from .models import CatalogBrowseVersion
from .service import SourceCatalog
from .source_reader import SOURCE_REF_SCHEMA_VERSION


BROWSE_REQUEST_SCHEMA = "company-wiki-public-document-browse-request/1"
REOPEN_REQUEST_SCHEMA = "company-wiki-public-document-version-request/1"
BROWSE_RESPONSE_SCHEMA = "company-wiki-public-document-browse/1"
REOPEN_RESPONSE_SCHEMA = "company-wiki-public-document-version/1"

#: Stable prefix for the opaque, single-segment document version token.
DOCUMENT_VERSION_ID_PREFIX = "cwpdv1-"
_VERSION_ID_RE = re.compile(r"cwpdv1-[A-Za-z0-9_-]{43}\Z")
_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]+\Z")
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")

_MAX_LIMIT = 500
_DEFAULT_LIMIT = 50

_BROWSE_REQUEST_FIELDS = frozenset({
    "schema_version", "canonical_entity_id", "market", "document_kinds",
    "fiscal_years", "language", "source_statuses", "limit", "cursor",
    "snapshot_id",
})
_REOPEN_REQUEST_FIELDS = frozenset({
    "schema_version", "document_version_id",
})
_FILTER_KEYS = (
    "market", "document_kinds", "fiscal_years", "language", "source_statuses",
)
_SNAPSHOT_VERSION = 1

_UNKNOWN_FACET_KEY = "unknown"

class PublicBrowseError(RuntimeError):
    """A named, in-band refusal (invalid request or unusable token)."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class _Snapshot:
    """The pinned query identity: entity, filters and catalog revision."""

    entity: str
    filters: dict[str, Any]
    revision: str

    def encode(self) -> str:
        return _encode_token({
            "v": _SNAPSHOT_VERSION, "entity": self.entity,
            "filters": self.filters, "revision": self.revision,
        })


def _encode_token(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_token(token: Any, field: str) -> dict[str, Any]:
    if not isinstance(token, str) or not _TOKEN_RE.fullmatch(token):
        raise PublicBrowseError(f"invalid_{field}")
    try:
        padded = token + "=" * (-len(token) % 4)
        payload = parse_json(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except ValueError:
        raise PublicBrowseError(f"invalid_{field}") from None
    if not isinstance(payload, dict) or payload.get("v") != _SNAPSHOT_VERSION:
        raise PublicBrowseError(f"unsupported_{field}")
    return payload


def document_version_id(document_id: str, source_id: str,
                        content_sha256: str) -> str:
    """Deterministic opaque token bound to one complete version triple.

    The same triple always yields the same id; the same document_id with a
    different source/hash never shares it.  The id is a single path segment
    and carries no path, URL or locator.
    """
    digest = hashlib.sha256(
        "company-wiki:document-version:1\0".encode("utf-8")
        + document_id.encode("utf-8") + b"\0"
        + source_id.encode("utf-8") + b"\0"
        + content_sha256.encode("utf-8")
    ).digest()
    return DOCUMENT_VERSION_ID_PREFIX + base64.urlsafe_b64encode(
        digest).decode("ascii").rstrip("=")


def _required_text(value: Any, field: str, *, max_length: int = 300) -> str:
    if not isinstance(value, str) or not value.strip() \
            or len(value) > max_length:
        raise PublicBrowseError(f"invalid_{field}")
    return value.strip()


def _optional_text(value: Any, field: str, *, max_length: int = 200) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() \
            or len(value) > max_length:
        raise PublicBrowseError(f"invalid_{field}")
    return value.strip()


def _optional_text_list(value: Any, field: str) -> tuple[str, ...] | None:
    if value is None or value == []:
        # An explicitly empty list means "no filter", like an absent field.
        return None
    if not isinstance(value, list) or not value \
            or len(value) > 32 \
            or any(not isinstance(item, str) or not _TOKEN_RE.fullmatch(item)
                   for item in value):
        raise PublicBrowseError(f"invalid_{field}")
    # Sorted at the seam: filter identity is a set, so a replayed page may
    # re-send the same values in any order.
    return tuple(sorted(dict.fromkeys(value)))


def _optional_int_list(value: Any, field: str) -> tuple[int, ...] | None:
    if value is None or value == []:
        return None
    if not isinstance(value, list) or not value \
            or len(value) > 200 \
            or any(isinstance(item, bool) or not isinstance(item, int)
                   or not 1900 <= item <= 2200 for item in value):
        raise PublicBrowseError(f"invalid_{field}")
    return tuple(sorted(dict.fromkeys(value)))


def _normalize_filters(market: str | None,
                       document_kinds: tuple[str, ...] | None,
                       fiscal_years: tuple[int, ...] | None,
                       language: tuple[str, ...] | None,
                       source_statuses: tuple[str, ...] | None,
                       ) -> dict[str, Any]:
    return {
        "market": market,
        "document_kinds": list(document_kinds) if document_kinds else None,
        "fiscal_years": list(fiscal_years) if fiscal_years else None,
        "language": list(language) if language else None,
        "source_statuses": list(source_statuses) if source_statuses else None,
    }


def _filters_conflict(request_filters: dict[str, Any],
                      pinned_filters: dict[str, Any]) -> bool:
    """A replayed page takes its filters from the pinned snapshot; an
    explicitly re-sent filter may only repeat the pinned value."""
    for key in _FILTER_KEYS:
        requested = request_filters[key]
        if requested is None or requested == []:
            continue
        pinned = pinned_filters.get(key)
        if pinned is None or pinned == []:
            return True
        if list(requested) != list(pinned):
            return True
    return False


@dataclass(frozen=True)
class _VersionRow:
    """One frozen (document, source) version with its projected facts."""

    document_id: str
    source_id: str
    content_sha256: str
    byte_size: int
    mime_type: str
    primary: bool
    ordinal: int
    title: str | None
    document_kind: str | None
    published_date: str | None
    source_status: str | None
    fiscal_year: int | None
    period_start: str | None
    period_end: str | None
    language: str | None
    market: str | None
    canonical_entity_id: str | None
    display_name: str | None
    first_seen_at: str
    roles: tuple[str, ...]
    resolvable: bool

    def sort_key(self) -> tuple[Any, ...]:
        # Deterministic total order: kind, then newest fiscal year and
        # publication date first, then stable document identity; inside one
        # document the current version first, then older versions.  (The
        # ordinal alone cannot express this: sources first seen in the same
        # scan run tie on first_seen_at.)
        published = self.published_date or ""
        return (
            self.document_kind or "",
            -(self.fiscal_year or 0),
            0 if published else 1,
            tuple(-ord(ch) for ch in published),
            self.title or "",
            self.document_id,
            0 if self.primary else 1,
            -self.ordinal,
            self.source_id,
        )

    def revision_member(self) -> list[Any]:
        """Everything a response item can show — locations as ids/statuses
        only, never paths.  Any visible change must change the revision."""
        return [
            self.document_id, self.source_id, self.content_sha256,
            self.byte_size, self.mime_type, self.primary, self.ordinal,
            self.title, self.document_kind, self.published_date,
            self.source_status, self.fiscal_year, self.period_start,
            self.period_end, self.language, self.market,
            self.canonical_entity_id, self.display_name, self.first_seen_at,
            sorted(self.roles), self.resolvable,
        ]

    def to_item(self) -> dict[str, Any]:
        return {
            "document_version_id": document_version_id(
                self.document_id, self.source_id, self.content_sha256),
            "document_id": self.document_id,
            "title": self.title,
            "document_kind": self.document_kind,
            "published_at": self.published_date,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "fiscal_year": self.fiscal_year,
            "language": self.language,
            "market": self.market,
            "version_label": str(self.ordinal),
            "is_current_version": self.primary,
            "processing_state": self.source_status,
            "location_roles": sorted(self.roles),
            "first_seen_at": self.first_seen_at,
            "storage_state": (
                "resolvable" if self.resolvable else "not_resolvable"),
            "source_ref": {
                "document_id": self.document_id,
                "source_id": self.source_id,
                "content_sha256": self.content_sha256,
                "byte_size": self.byte_size,
                "mime_type": self.mime_type,
                "schema_version": SOURCE_REF_SCHEMA_VERSION,
            },
        }


class PublicDocumentBrowser:
    """Zero-write entity document browse and exact version reopen."""

    def __init__(self, catalog: SourceCatalog):
        if not isinstance(catalog, SourceCatalog):
            raise TypeError("catalog must be SourceCatalog")
        self.catalog = catalog

    # -- public entry points --------------------------------------------------

    def browse(self, request: dict[str, Any]) -> dict[str, Any]:
        """Serve one page of an entity's frozen document-version snapshot."""
        if not isinstance(request, dict) \
                or set(request) != _BROWSE_REQUEST_FIELDS:
            raise PublicBrowseError("request_fields_not_exact")
        if request["schema_version"] != BROWSE_REQUEST_SCHEMA:
            raise PublicBrowseError("unsupported_request_version")
        entity = _required_text(request["canonical_entity_id"],
                                "canonical_entity_id")
        limit = request["limit"]
        if limit is None:
            limit = _DEFAULT_LIMIT
        elif isinstance(limit, bool) or not isinstance(limit, int) \
                or not 1 <= limit <= _MAX_LIMIT:
            raise PublicBrowseError("invalid_limit")
        filters = _normalize_filters(
            _optional_text(request["market"], "market"),
            _optional_text_list(request["document_kinds"], "document_kinds"),
            _optional_int_list(request["fiscal_years"], "fiscal_years"),
            _optional_text_list(request["language"], "language"),
            _optional_text_list(request["source_statuses"],
                                "source_statuses"),
        )
        cursor_token = _optional_text(request["cursor"], "cursor",
                                      max_length=8192)
        snapshot_token = _optional_text(request["snapshot_id"], "snapshot_id",
                                        max_length=8192)

        pinned = self._pinned_snapshot(entity, filters, cursor_token,
                                       snapshot_token)
        versions = self._entity_versions(entity)
        revision = self._revision(versions)

        if pinned is not None and pinned.revision != revision:
            fresh = _Snapshot(entity, pinned.filters, revision)
            return _envelope(
                state="stale",
                reason_codes=["snapshot_stale", "catalog_revision_changed"],
                entity=entity, items=(), snapshot=fresh, facets=None,
                entity_facts=_entity_facts(versions), next_cursor=None,
                total=0,
            )

        snapshot = pinned or _Snapshot(entity, filters, revision)
        offset: int | None = 0
        if cursor_token is not None:
            cursor_payload = _decode_token(cursor_token, "cursor")
            if cursor_payload.get("snapshot") != snapshot.encode():
                raise PublicBrowseError("cursor_snapshot_mismatch")
            offset = cursor_payload.get("offset")
            if isinstance(offset, bool) or not isinstance(offset, int) \
                    or offset < 0:
                raise PublicBrowseError("invalid_cursor")
        assert offset is not None

        return self._serve(entity, versions, snapshot, offset, limit)

    def reopen_document_version(
        self, request_or_id: dict[str, Any] | str,
    ) -> dict[str, Any]:
        """Bind one opaque version token back to its complete SourceRef.

        The catalog has no id→triple registry and browse never writes one,
        so the binding is recomputed from the indexed (document, source)
        pairs in one bounded pass; the found triple is then re-projected
        through the same browse path so the reopened item is identical to
        the browsed item.
        """
        if isinstance(request_or_id, dict):
            if set(request_or_id) != _REOPEN_REQUEST_FIELDS:
                raise PublicBrowseError("request_fields_not_exact")
            if request_or_id["schema_version"] != REOPEN_REQUEST_SCHEMA:
                raise PublicBrowseError("unsupported_request_version")
            wanted = request_or_id["document_version_id"]
        else:
            wanted = request_or_id
        if not isinstance(wanted, str) or not _VERSION_ID_RE.fullmatch(wanted):
            raise PublicBrowseError("invalid_document_version_id")

        identity = next((
            candidate for candidate in self.catalog.iter_original_version_identities()
            if document_version_id(
                candidate.document_id, candidate.source_id,
                candidate.content_sha256,
            ) == wanted
        ), None)
        if identity is None:
            return {
                "schema_version": REOPEN_RESPONSE_SCHEMA,
                "state": "not_found",
                "reason_codes": ["document_version_not_indexed"],
                "document_version_id": wanted,
                "document": None,
            }
        versions = [
            self._version_row(record)
            for record in self.catalog.browse_document_records(identity.document_id)
            if record.source_id == identity.source_id
        ]
        if not versions:
            return {
                "schema_version": REOPEN_RESPONSE_SCHEMA,
                "state": "not_found",
                "reason_codes": ["document_version_not_indexed"],
                "document_version_id": wanted,
                "document": None,
            }
        item = versions[0].to_item()
        assert item["document_version_id"] == wanted
        return {
            "schema_version": REOPEN_RESPONSE_SCHEMA,
            "state": "available",
            "reason_codes": [],
            "document_version_id": wanted,
            "document": item,
        }

    # -- internals ------------------------------------------------------------

    def _pinned_snapshot(self, entity: str, filters: dict[str, Any],
                         cursor_token: str | None,
                         snapshot_token: str | None) -> _Snapshot | None:
        pinned_payload: dict[str, Any] | None = None
        if snapshot_token is not None:
            pinned_payload = _decode_token(snapshot_token, "snapshot_id")
        if cursor_token is not None:
            cursor_payload = _decode_token(cursor_token, "cursor")
            embedded = cursor_payload.get("snapshot")
            if not isinstance(embedded, str):
                raise PublicBrowseError("invalid_cursor")
            cursor_snapshot = _decode_token(embedded, "cursor")
            if pinned_payload is None:
                pinned_payload = cursor_snapshot
            elif _encode_token(pinned_payload) != embedded:
                raise PublicBrowseError("cursor_snapshot_mismatch")
        if pinned_payload is None:
            return None
        if pinned_payload.get("entity") != entity:
            raise PublicBrowseError("snapshot_entity_mismatch")
        pinned_filters = pinned_payload.get("filters")
        if not isinstance(pinned_filters, dict) \
                or set(pinned_filters) != set(_FILTER_KEYS):
            raise PublicBrowseError("invalid_snapshot_id")
        if _filters_conflict(filters, pinned_filters):
            raise PublicBrowseError("snapshot_filter_conflict")
        revision = pinned_payload.get("revision")
        if not isinstance(revision, str) or not _TOKEN_RE.fullmatch(revision):
            raise PublicBrowseError("invalid_snapshot_id")
        return _Snapshot(entity, pinned_filters, revision)

    def _entity_versions(self, entity: str) -> list[_VersionRow]:
        versions = [
            self._version_row(record)
            for record in self.catalog.browse_entity_records(entity)
        ]
        versions.sort(key=_VersionRow.sort_key)
        return versions

    def _document(self, document_id: str) -> dict[str, Any] | None:
        """One indexed document's pathless facts, or None when not indexed.

        Shared with the canonical browse consumer: read-only reuse of this
        browser's exact document/version enumeration, never a second query
        path of its own.
        """
        records = self.catalog.browse_document_records(document_id)
        if not records:
            return None
        primary = next((record for record in records if record.primary), None)
        head = records[0]
        return {
            "document_id": head.document_id,
            "primary_source_id": primary.source_id if primary else None,
            "title": head.title,
            "document_kind": head.document_kind,
            "published_date": head.published_date,
            "source_status": head.source_status,
            "market": head.market,
            "language": head.language,
            "canonical_entity_id": head.canonical_entity_id,
            "display_name": head.display_name,
            "fiscal_year": head.fiscal_year,
        }

    def _entity_documents_with_limit(
        self, entity: str, *, limit: int | None
    ) -> tuple[list[dict[str, Any]], bool, int]:
        """Bound entity enumeration for diagnostic-only callers.

        The default public browse remains complete. Bounded callers receive a
        deterministic prefix (ordered by document id), a truncation flag, and
        the number of documents read: at most ``limit + 1``, the same bounded
        read count the historical ``LIMIT ?`` query reported, so downstream
        scan budgets account identically through the typed port.
        """
        if limit is not None and (isinstance(limit, bool)
                                  or not isinstance(limit, int) or limit < 1):
            raise ValueError("entity document limit must be positive")
        document_ids = sorted({
            record.document_id
            for record in self.catalog.browse_entity_records(entity)
        })
        scanned = len(document_ids)
        truncated = limit is not None and scanned > limit
        if limit is not None:
            scanned = min(scanned, limit + 1)
            document_ids = document_ids[:limit]
        documents = [
            document for document_id in document_ids
            if (document := self._document(document_id)) is not None
        ]
        return documents, truncated, scanned

    def _document_versions_with_limit(
        self, document: dict[str, Any], *, limit: int | None
    ) -> tuple[list["_VersionRow"], bool, int]:
        """Enumerate a deterministic bounded prefix of exact source versions.

        ``rows_read`` keeps the bounded ``limit + 1`` accounting of the
        historical query so caller scan budgets stay unchanged.
        """
        if limit is not None and (isinstance(limit, bool)
                                  or not isinstance(limit, int) or limit < 1):
            raise ValueError("document version limit must be positive")
        versions = [
            self._version_row(record)
            for record in self.catalog.browse_document_records(
                str(document["document_id"])
            )
        ]
        versions.sort(key=_VersionRow.sort_key)
        scanned = len(versions)
        truncated = limit is not None and scanned > limit
        if limit is not None:
            scanned = min(scanned, limit + 1)
            versions = versions[:limit]
        return versions, truncated, scanned

    @staticmethod
    def _version_row(record: CatalogBrowseVersion) -> _VersionRow:
        return _VersionRow(
            document_id=record.document_id,
            source_id=record.source_id,
            content_sha256=record.content_sha256,
            byte_size=record.byte_size,
            mime_type=record.mime_type,
            primary=record.primary,
            ordinal=record.ordinal,
            title=record.title,
            document_kind=record.document_kind,
            published_date=record.published_date,
            source_status=record.source_status,
            fiscal_year=record.fiscal_year,
            period_start=record.period_start,
            period_end=record.period_end,
            language=record.language,
            market=record.market,
            canonical_entity_id=record.canonical_entity_id,
            display_name=record.display_name,
            first_seen_at=record.first_seen_at,
            roles=record.roles,
            resolvable=record.resolvable,
        )

    @staticmethod
    def _revision(versions: list[_VersionRow]) -> str:
        payload = json.dumps(
            [version.revision_member() for version in versions],
            ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _serve(self, entity: str, versions: list[_VersionRow],
               snapshot: _Snapshot, offset: int, limit: int) -> dict[str, Any]:
        filtered = [
            version for version in versions
            if self._matches(snapshot.filters, version)
        ]
        total = len(filtered)
        page_items = filtered[offset:offset + limit]
        next_cursor = None
        if offset + limit < total:
            next_cursor = _encode_token({
                "v": _SNAPSHOT_VERSION, "snapshot": snapshot.encode(),
                "offset": offset + limit,
            })
        state = "available" if total else "empty"
        reason_codes: list[str] = []
        if not versions:
            reason_codes.append("entity_not_indexed")
        elif not total:
            reason_codes.append("no_documents_match_filters")
        elif offset >= total:
            # A cursor past the end of the pinned snapshot (e.g. forged or
            # replayed after the snapshot shrank behind a stale check) is
            # reported honestly as an empty page, never as zero available
            # items.
            state = "empty"
            reason_codes.append("page_offset_beyond_total")
        if any(not version.resolvable for version in page_items):
            state = "partial"
            reason_codes.append("some_versions_not_resolvable")
        return _envelope(
            state=state, reason_codes=reason_codes, entity=entity,
            items=page_items, snapshot=snapshot,
            facets=self._facets(filtered),
            entity_facts=_entity_facts(versions), next_cursor=next_cursor,
            total=total,
        )

    @staticmethod
    def _matches(filters: dict[str, Any], version: _VersionRow) -> bool:
        if filters["market"] is not None \
                and version.market != filters["market"]:
            return False
        if filters["document_kinds"] is not None \
                and version.document_kind not in filters["document_kinds"]:
            return False
        if filters["fiscal_years"] is not None \
                and version.fiscal_year not in filters["fiscal_years"]:
            return False
        if filters["language"] is not None \
                and version.language not in filters["language"]:
            return False
        if filters["source_statuses"] is not None \
                and version.source_status not in filters["source_statuses"]:
            return False
        return True

    @staticmethod
    def _facets(versions: list[_VersionRow]) -> dict[str, dict[str, int]]:
        def counts(attribute: str, *, as_text: bool = False) -> dict[str, int]:
            result: dict[str, int] = {}
            for version in versions:
                value = getattr(version, attribute)
                key = (
                    str(value) if as_text and value is not None
                    else value if isinstance(value, str) and value
                    else _UNKNOWN_FACET_KEY)
                result[key] = result.get(key, 0) + 1
            return dict(sorted(result.items()))

        return {
            "document_kind": counts("document_kind"),
            "language": counts("language"),
            "source_status": counts("source_status"),
            "market": counts("market"),
            "fiscal_year": counts("fiscal_year", as_text=True),
        }


def _entity_facts(versions: list[_VersionRow]) -> dict[str, Any] | None:
    if not versions:
        return None
    facts: dict[str, Any] = {}
    for attribute in ("canonical_entity_id", "display_name", "market"):
        facts[attribute] = next(
            (getattr(version, attribute) for version in versions
             if getattr(version, attribute)),
            None,
        )
    return facts


def _envelope(state: str, reason_codes: list[str], entity: str,
              items: tuple[_VersionRow, ...] | list[_VersionRow],
              snapshot: _Snapshot,
              facets: dict[str, dict[str, int]] | None,
              entity_facts: dict[str, Any] | None,
              next_cursor: str | None, total: int) -> dict[str, Any]:
    return {
        "schema_version": BROWSE_RESPONSE_SCHEMA,
        "state": state,
        "reason_codes": reason_codes,
        "canonical_entity": {
            "requested_key": entity,
            **(entity_facts or {}),
        },
        "items": [version.to_item() for version in items],
        "page": {
            "next_cursor": next_cursor,
            "snapshot_id": snapshot.encode(),
            "total": total,
            "total_status": "exact",
        },
        "facets": facets,
        "catalog_revision": snapshot.revision,
    }
