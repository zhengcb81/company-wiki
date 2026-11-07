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
  ``storage_state`` only says whether an active original location for the
  version resolves inside the CURRENT configured roots, so a migrated
  storage root keeps every SourceRef openable by the owner reader.

Field provenance: fiscal_year / period_start / period_end / market /
language / canonical_entity_id / display_name live inside
``documents.metadata_json`` (``$.acquisition.*`` capture containers,
``$.dayu_meta.*`` portfolio containers — the same two containers
``query_filing_candidates`` reads).  ``language`` additionally falls back
to ``$.dayu_meta.source_language``, mirroring the portfolio promoter's
mapping.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

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

#: Only these location roles carry original document bytes.  Sidecars and
#: derived JSON are hashed as their own sources under the same document_id
#: but are not byte versions of the document (scanner roles: ``metadata``,
#: ``processed_docling`` …).  ``indexed_only`` is an original file whose
#: sidecar was too incomplete to qualify for filing reuse — the bytes are
#: still the document, so the cabinet lists it (with its degraded status).
_VERSION_LOCATION_ROLES = (
    "original_primary", "original_attachment", "indexed_only",
)

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

# metadata_json containers read per projected fact.  Order = precedence.
_FACT_PATHS: dict[str, tuple[str, ...]] = {
    "market": ("$.acquisition.market", "$.dayu_meta.market"),
    "language": ("$.acquisition.language", "$.dayu_meta.language",
                 "$.dayu_meta.source_language"),
    "canonical_entity_id": ("$.acquisition.canonical_entity_id",
                            "$.dayu_meta.canonical_entity_id"),
    "display_name": ("$.acquisition.display_name",
                     "$.dayu_meta.display_name"),
    "fiscal_year": ("$.acquisition.fiscal_year", "$.dayu_meta.fiscal_year"),
    "period_start": ("$.acquisition.period_start", "$.dayu_meta.period_start"),
    "period_end": ("$.acquisition.period_end", "$.dayu_meta.period_end"),
}


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
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (binascii.Error, UnicodeError, json.JSONDecodeError):
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


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date_or_none(value: Any) -> str | None:
    text = _text_or_none(value)
    if text is None or not _ISO_DATE_RE.fullmatch(text):
        return None
    return text


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

        # Spill-free on purpose: DISTINCT/GROUP BY over the full locations
        # table forces a temp b-tree; on Windows hosts whose %TEMP% path
        # cannot host SQLite temp files that fails with "unable to open
        # database file".  Deduplicate and order in Python instead.
        candidates: dict[tuple[str, str], str] = {}
        role_clause = " OR ".join("l.role = ?" for _ in _VERSION_LOCATION_ROLES)
        for row in self.catalog.reader.fetchall(
            f"""SELECT l.document_id, l.source_id, s.content_sha256
               FROM locations l JOIN sources s ON s.source_id = l.source_id
               WHERE l.source_id IS NOT NULL AND ({role_clause})""",
            _VERSION_LOCATION_ROLES,
        ):
            candidates[(str(row["document_id"]), str(row["source_id"]))] = \
                str(row["content_sha256"])
        for row in self.catalog.reader.fetchall(
            """SELECT d.document_id, d.primary_source_id, s.content_sha256
               FROM documents d JOIN sources s ON s.source_id = d.primary_source_id
               WHERE d.primary_source_id IS NOT NULL""",
        ):
            candidates.setdefault(
                (str(row["document_id"]), str(row["primary_source_id"])),
                str(row["content_sha256"]),
            )
        match = next(
            ((document_id, source_id)
             for (document_id, source_id), sha in sorted(candidates.items())
             if document_version_id(document_id, source_id, sha) == wanted),
            None,
        )
        if match is None:
            return {
                "schema_version": REOPEN_RESPONSE_SCHEMA,
                "state": "not_found",
                "reason_codes": ["document_version_not_indexed"],
                "document_version_id": wanted,
                "document": None,
            }
        document_id, source_id = match
        document = self._document(document_id)
        versions = (
            [version for version in self._document_versions(document)
             if version.source_id == source_id]
            if document is not None else []
        )
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

    def _entity_documents(self, entity: str) -> list[dict[str, Any]]:
        """Documents linked to the entity key, with projected capture facts.

        Matching mirrors the two canonical channels the writer maintains:
        the ``document_entities`` link and the declared
        ``canonical_entity_id`` capture field (both containers).  json_valid
        guards json_extract the same way the filing-candidate pushdown does.
        """
        sql = self._projection_sql(
            " WHERE d.document_id IN ("
            "     SELECT document_id FROM document_entities WHERE entity_id = ?)"
            " OR (json_valid(d.metadata_json)"
            "     AND (json_extract(d.metadata_json,"
            "                       '$.acquisition.canonical_entity_id') = ?"
            "          OR json_extract(d.metadata_json,"
            "                          '$.dayu_meta.canonical_entity_id') = ?))")
        return [self._project_row(row) for row
                in self.catalog.reader.fetchall(sql, (entity, entity, entity))]

    def _document(self, document_id: str) -> dict[str, Any] | None:
        sql = self._projection_sql(" WHERE d.document_id = ?")
        row = self.catalog.reader.fetchone(sql, (document_id,))
        return None if row is None else self._project_row(row)

    @staticmethod
    def _projection_sql(where_clause: str) -> str:
        fact_columns = ",\n".join(
            "CASE WHEN json_valid(d.metadata_json) THEN "
            + "COALESCE("
            + ", ".join(f"json_extract(d.metadata_json, {path!r})"
                        for path in paths)
            + ") END AS fact_" + name
            for name, paths in _FACT_PATHS.items()
        )
        return ("""SELECT d.document_id, d.primary_source_id, d.title,
                         d.document_kind, d.published_date, d.source_status,
                         """ + fact_columns
                + """ FROM documents d""" + where_clause)

    @staticmethod
    def _project_row(row: Any) -> dict[str, Any]:
        facts = {name: row[f"fact_{name}"] for name in _FACT_PATHS}
        return {
            "document_id": str(row["document_id"]),
            "primary_source_id": (
                str(row["primary_source_id"])
                if row["primary_source_id"] else None),
            "title": str(row["title"] or "") or None,
            "document_kind": str(row["document_kind"] or "") or None,
            "published_date": (
                str(row["published_date"] or "") or None),
            "source_status": str(row["source_status"] or "") or None,
            "market": _text_or_none(facts.get("market")),
            "language": _text_or_none(facts.get("language")),
            "canonical_entity_id": _text_or_none(
                facts.get("canonical_entity_id")),
            "display_name": _text_or_none(facts.get("display_name")),
            "fiscal_year": _int_or_none(facts.get("fiscal_year")),
            "period_start": _date_or_none(facts.get("period_start")),
            "period_end": _date_or_none(facts.get("period_end")),
        }

    def _document_versions(self, document: dict[str, Any]) -> list[_VersionRow]:
        """Every frozen byte version of one document (originals only)."""
        document_id = document["document_id"]
        role_placeholders = ", ".join("?" for _ in _VERSION_LOCATION_ROLES)
        location_rows = self.catalog.reader.fetchall(
            f"""SELECT source_id, root_id, role, location_status
               FROM locations
               WHERE document_id = ? AND source_id IS NOT NULL
                 AND role IN ({role_placeholders})""",
            (document_id, *_VERSION_LOCATION_ROLES),
        )
        source_ids = {str(item["source_id"]) for item in location_rows}
        if document["primary_source_id"]:
            source_ids.add(document["primary_source_id"])
        if not source_ids:
            return []
        placeholders = ", ".join("?" for _ in source_ids)
        source_rows = self.catalog.reader.fetchall(
            f"""SELECT source_id, content_sha256, byte_size, mime_type,
                       first_seen_at FROM sources
                WHERE source_id IN ({placeholders})
                ORDER BY first_seen_at, source_id""",
            tuple(sorted(source_ids)),
        )
        config_root_ids = {root.root_id for root in self.catalog.config.roots}
        locations_by_source: dict[str, list[Any]] = {}
        for item in location_rows:
            locations_by_source.setdefault(
                str(item["source_id"]), []).append(item)
        versions: list[_VersionRow] = []
        for ordinal, source in enumerate(source_rows, start=1):
            source_id = str(source["source_id"])
            locations = locations_by_source.get(source_id, [])
            roles = sorted({str(item["role"]) for item in locations})
            resolvable = any(
                str(item["location_status"]) == "active"
                and str(item["root_id"]) in config_root_ids
                for item in locations
            )
            versions.append(_VersionRow(
                document_id=document_id,
                source_id=source_id,
                content_sha256=str(source["content_sha256"]),
                byte_size=int(source["byte_size"]),
                mime_type=str(source["mime_type"]),
                primary=document["primary_source_id"] == source_id,
                ordinal=ordinal,
                title=document["title"],
                document_kind=document["document_kind"],
                published_date=document["published_date"],
                source_status=document["source_status"],
                fiscal_year=document["fiscal_year"],
                period_start=document["period_start"],
                period_end=document["period_end"],
                language=document["language"],
                market=document["market"],
                canonical_entity_id=document["canonical_entity_id"],
                display_name=document["display_name"],
                first_seen_at=str(source["first_seen_at"]),
                roles=tuple(roles),
                resolvable=resolvable,
            ))
        return versions

    def _entity_versions(self, entity: str) -> list[_VersionRow]:
        versions: list[_VersionRow] = []
        for document in self._entity_documents(entity):
            versions.extend(self._document_versions(document))
        versions.sort(key=_VersionRow.sort_key)
        return versions

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


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


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
