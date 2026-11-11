"""High-level source catalog API and human-readable index exports."""

from __future__ import annotations

from contextlib import contextmanager
import csv
import json
import sqlite3
import re
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterator, Sequence

from company_wiki.atomic_file import atomic_output
from company_wiki.file_usage import database_file_sizes, file_tree_bytes
from company_wiki.source_contract.source_version import (
    SourceProcessingDescriptor,
    SourceRef,
)
from company_wiki.source_contract.source_manifest import SourceManifest

from .models import (
    CatalogBrowseVersion,
    CatalogConfig,
    ProcessingReport,
    RankedSourceLocation,
    ScanReport,
    SourceCopyAvailability,
    SourceCopyAvailabilityRequest,
    SourceVersionIdentity,
)
from .source_location import (
    SourceLocationError,
    relative_segments,
    resolve_source_location,
)
from .location_annotation import (
    CatalogLocationAnnotation,
    CatalogLocationCandidate,
    annotate_locations as rank_location_candidates,
)
from .catalog_query_contract import (
    CatalogDocumentCandidate,
    CatalogDocumentCandidateQuery,
    CatalogDuplicateLocationRecord,
    CatalogEntityRecord,
    CatalogQueryUnavailable,
)
from .acquisition_journal import AcquisitionJournal
from .lock import CatalogOperationLock
from .narrative_artifact_store import (
    LocalNarrativeObjectStore,
    NarrativeArtifactReader,
    NarrativeArtifactStore,
    NarrativeObjectAccess,
    NarrativeObjectWritePolicy,
)
from .normalizer import backfill_text_fingerprints
from .scanner import R4_PROVENANCE_KEY, scan_catalog
from .store import CatalogStore, metadata_object, metadata_state
from .reader import ReadOnlyCatalogReader
from .reader import CatalogReaderUnavailable

if TYPE_CHECKING:
    from .duplicate_cleanup import DuplicateCleanupJournal


# Capture facts are projected here because the catalog owns metadata layout.
# The browser consumes only CatalogBrowseVersion and never knows these paths.
# Acquisition and portfolio records retain their separate canonical containers.
_BROWSE_FACT_PATHS: dict[str, tuple[str, ...]] = {
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
_BROWSE_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_BROWSE_VERSION_ROLES = ("original_primary", "original_attachment", "indexed_only")


def _read_shared_metadata(raw: Any) -> dict[str, Any]:
    """The v1 adapter NAME for the single read chain (B10), not a second implementation.

    The column is written by several modules, so its shape is not this module's to
    assume (work package b05-read-side-malformed-columns).  Malformed content becomes an
    empty object here; the *state* is reported by the caller that also reads the reserved
    provenance key (`metadata_problem="unreadable_metadata"`), which is how a malformed
    document is distinguished from one that simply carries no metadata.

    B10 converged this function onto ``store.metadata_object``: the two were separate
    implementations of the SAME contract for every input the column can actually hold (both
    return ``{}`` for anything that is not a JSON object; equivalence measured on 24 inputs
    including deep-nesting ``RecursionError`` and non-UTF-8 bytes).  The catch sets are NOT
    identical - the chain catches ``json.JSONDecodeError``/``UnicodeDecodeError`` where this
    function caught the wider ``ValueError`` - so a hypothetical object whose ``__bool__``
    raises a bare ``ValueError`` would now propagate instead of degrading to ``{}``
    (B-VR-B10-07); the only caller passes sqlite TEXT, where that difference is unreachable.
    The name stays because callers use it, and it is registered in
    ``read_chain.LEGACY_READ_ADAPTERS`` with its removal condition; what must NOT come back
    is a second parse here, which ``tests/contract/test_b10_read_chain.py`` now refuses.
    """
    return metadata_object(raw)


def _utc_now() -> str:
    """UTC wall-clock stamp for bundle queries without an explicit ``now``."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _required_catalog_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be non-empty trimmed text")
    return value


def _browse_projection_sql(where_clause: str) -> str:
    fact_columns = ",\n".join(
        "CASE WHEN json_valid(d.metadata_json) THEN COALESCE("
        + ", ".join(f"json_extract(d.metadata_json, {path!r})" for path in paths)
        + ") END AS fact_" + name
        for name, paths in _BROWSE_FACT_PATHS.items()
    )
    return (
        "SELECT d.document_id, d.primary_source_id, d.title, d.document_kind, "
        "d.published_date, d.source_status, " + fact_columns
        + " FROM documents d" + where_clause
    )


def _browse_text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _browse_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _optional_catalog_integer(value: Any) -> int | None:
    """Read an optional diagnostic integer without making it a query gate."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        try:
            return int(value.strip())
        except (ValueError, OverflowError):
            return None
    return None


def _browse_date_or_none(value: Any) -> str | None:
    text = _browse_text_or_none(value)
    return text if text is not None and _BROWSE_DATE.fullmatch(text) else None


def _browse_document(row: Any) -> dict[str, Any]:
    facts = {name: row[f"fact_{name}"] for name in _BROWSE_FACT_PATHS}
    return {
        "document_id": str(row["document_id"]),
        "primary_source_id": (
            str(row["primary_source_id"]) if row["primary_source_id"] else None
        ),
        "title": str(row["title"] or "") or None,
        "document_kind": str(row["document_kind"] or "") or None,
        "published_date": str(row["published_date"] or "") or None,
        "source_status": str(row["source_status"] or "") or None,
        "market": _browse_text_or_none(facts.get("market")),
        "language": _browse_text_or_none(facts.get("language")),
        "canonical_entity_id": _browse_text_or_none(facts.get("canonical_entity_id")),
        "display_name": _browse_text_or_none(facts.get("display_name")),
        "fiscal_year": _browse_int_or_none(facts.get("fiscal_year")),
        "period_start": _browse_date_or_none(facts.get("period_start")),
        "period_end": _browse_date_or_none(facts.get("period_end")),
    }


class SourceCatalog:
    def duplicate_cleanup_journal(self) -> "DuplicateCleanupJournal":
        """Open the retired maintenance journal through its storage owner."""
        from .duplicate_cleanup import DuplicateCleanupJournal

        return DuplicateCleanupJournal(self.config.catalog_dir)

    def duplicate_cleanup_location_records(
        self,
    ) -> tuple[CatalogDuplicateLocationRecord, ...]:
        """Return typed exact-copy inventory rows from the catalog owner."""
        try:
            rows = self.reader.fetchall(
                """WITH duplicate_keys AS (
                    SELECT document_id,source_id
                    FROM locations
                    WHERE role='original_primary' AND location_status='active'
                      AND document_id IS NOT NULL AND source_id IS NOT NULL
                    GROUP BY document_id,source_id HAVING COUNT(*) > 1
                )
                SELECT l.location_id,l.document_id,l.root_id,l.relative_path,l.absolute_path,
                       l.source_id,l.role,l.location_status,l.observed_size,
                       l.observed_mtime_ns,r.priority AS root_priority,d.title,
                       d.document_kind,d.published_date,s.content_sha256,l.manifest_json
                FROM duplicate_keys k
                JOIN locations l ON l.document_id=k.document_id AND l.source_id=k.source_id
                JOIN roots r ON r.root_id=l.root_id
                JOIN documents d ON d.document_id=l.document_id
                JOIN sources s ON s.source_id=l.source_id
                WHERE l.role='original_primary' AND l.location_status='active'
                ORDER BY d.document_id,l.source_id,r.priority,l.root_id,
                         l.relative_path,l.location_id"""
            )
            document_ids = tuple(dict.fromkeys(str(row["document_id"]) for row in rows))
            entities_by_document: dict[str, list[str]] = {}
            for start in range(0, len(document_ids), 500):
                batch = document_ids[start:start + 500]
                for row in self.reader.fetchall(
                    """SELECT de.document_id,e.name FROM document_entities de
                       JOIN entities e ON e.entity_id=de.entity_id
                       WHERE de.document_id IN ({})
                       ORDER BY de.document_id,e.entity_id""".format(
                        ",".join("?" for _ in batch)
                    ),
                    batch,
                ):
                    entities_by_document.setdefault(str(row["document_id"]), []).append(
                        str(row["name"] or "")
                    )
        except (CatalogReaderUnavailable, sqlite3.Error) as exc:
            raise CatalogQueryUnavailable("catalog_unavailable") from exc

        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(
                (str(row["document_id"]), str(row["source_id"])), []
            ).append(dict(row))

        records: list[CatalogDuplicateLocationRecord] = []
        for (document_id, source_id), locations in grouped.items():
            candidates = tuple(
                CatalogLocationCandidate(
                    location_id=str(item["location_id"]),
                    source_id=source_id,
                    root_id=str(item["root_id"]),
                    relative_path=str(item["relative_path"]),
                    role=str(item["role"]),
                    location_status=str(item["location_status"]),
                    root_priority=int(item["root_priority"]),
                    manifest_json=(
                        str(item["manifest_json"])
                        if item.get("manifest_json") is not None else None
                    ),
                )
                for item in locations
            )
            annotations = {
                annotation.location_id: annotation
                for annotation in self.annotate_locations(document_id, candidates)
            }
            for item in locations:
                records.append(
                    CatalogDuplicateLocationRecord(
                        document_id=document_id,
                        source_id=source_id,
                        content_sha256=str(item["content_sha256"]),
                        title=str(item["title"] or ""),
                        document_kind=str(item["document_kind"] or ""),
                        published_date=(
                            str(item["published_date"])
                            if item["published_date"] is not None else None
                        ),
                        absolute_path=str(item["absolute_path"]),
                        observed_size=(
                            _optional_catalog_integer(item["observed_size"])
                        ),
                        observed_mtime_ns=(
                            _optional_catalog_integer(item["observed_mtime_ns"])
                        ),
                        entities=tuple(entities_by_document.get(document_id, ())),
                        annotation=annotations[str(item["location_id"])],
                    )
                )
        return tuple(records)

    def document_candidates(
        self, query: CatalogDocumentCandidateQuery,
    ) -> tuple[CatalogDocumentCandidate, ...]:
        """Return identity-matched document records without exposing SQL rows.

        The Catalog owns identity-index lookup, schema joins, and batched entity
        projection. Consumers receive detached pathless values and decide the
        domain-level identity match themselves.
        """
        from .identity_candidates import identity_candidate_clause

        conditions = ["d.source_status IN ('active', 'retired')"]
        parameters: list[Any] = []
        if query.as_of_date is not None:
            conditions.append("(d.published_date IS NULL OR d.published_date <= ?)")
            parameters.append(query.as_of_date)
        if query.document_kinds:
            marks = ",".join("?" for _ in query.document_kinds)
            conditions.append(f"d.document_kind IN ({marks})")
            parameters.extend(query.document_kinds)
        if query.after_document_id is not None:
            conditions.append("d.document_id > ?")
            parameters.append(query.after_document_id)

        order_by = (
            "d.document_id ASC"
            if query.order == "document_id"
            else "COALESCE(d.published_date, '') DESC, d.document_id ASC"
        )
        try:
            identity_clause, identity_params = identity_candidate_clause(
                self.reader, query.identity_tokens
            )
            rows = self.reader.fetchall(
                f"""SELECT d.document_id, d.primary_source_id AS document_source_id,
                           d.title, d.document_kind, d.published_date,
                           d.source_status, d.metadata_json,
                           s.content_sha256, s.byte_size, s.mime_type
                    FROM documents d
                    LEFT JOIN sources s ON s.source_id = d.primary_source_id
                    WHERE {' AND '.join(conditions)}
                      {identity_clause}
                    ORDER BY {order_by}
                    LIMIT ?""",
                (*parameters, *identity_params, query.limit),
            )
            document_ids = [str(row["document_id"]) for row in rows]
            entities_by_document = self._candidate_entities(document_ids)
        except (CatalogReaderUnavailable, sqlite3.Error) as exc:
            raise CatalogQueryUnavailable("catalog_unavailable") from exc

        candidates: list[CatalogDocumentCandidate] = []
        for row in rows:
            metadata, problem = metadata_state(row["metadata_json"])
            candidates.append(
                CatalogDocumentCandidate(
                    document_id=str(row["document_id"]),
                    source_id=(
                        str(row["document_source_id"])
                        if row["document_source_id"] is not None else None
                    ),
                    title=str(row["title"] or ""),
                    document_kind=str(row["document_kind"] or ""),
                    published_date=(
                        str(row["published_date"])
                        if row["published_date"] is not None else None
                    ),
                    source_status=str(row["source_status"] or ""),
                    metadata=metadata if problem is None else {},
                    content_sha256=(
                        str(row["content_sha256"])
                        if row["content_sha256"] is not None else None
                    ),
                    byte_size=(
                        int(row["byte_size"])
                        if row["byte_size"] is not None else None
                    ),
                    mime_type=(
                        str(row["mime_type"])
                        if row["mime_type"] is not None else None
                    ),
                    entities=tuple(entities_by_document.get(str(row["document_id"]), ())),
                )
            )
        return tuple(candidates)

    def _candidate_entities(
        self, document_ids: Sequence[str],
    ) -> dict[str, list[CatalogEntityRecord]]:
        entities: dict[str, list[CatalogEntityRecord]] = {}
        for start in range(0, len(document_ids), 500):
            batch = document_ids[start:start + 500]
            marks = ",".join("?" for _ in batch)
            for row in self.reader.fetchall(
                f"""SELECT de.document_id, e.entity_id, e.name, e.entity_kind
                    FROM document_entities de
                    JOIN entities e ON e.entity_id = de.entity_id
                    WHERE de.document_id IN ({marks})
                    ORDER BY de.document_id, e.entity_id""",
                tuple(batch),
            ):
                entities.setdefault(str(row["document_id"]), []).append(
                    CatalogEntityRecord(
                        entity_id=str(row["entity_id"]),
                        name=str(row["name"] or ""),
                        entity_kind=str(row["entity_kind"] or ""),
                    )
                )
        return entities

    def source_read_policy_digest(self) -> str:
        """Expose the configured read policy without exposing CatalogConfig."""
        from .source_read_policy import source_read_policy_sha256

        return source_read_policy_sha256(self.config, None)

    def source_location_candidates(
        self, document_id: str, source_id: str,
    ) -> tuple[RankedSourceLocation, ...]:
        """Return immutable catalog-ranked locations for one exact source.

        Ranking and duplicate annotation remain owned by the catalog. The
        resolver applies current RootSpec admission and verifies bytes through
        the SourceRef-bound read port. Physical locators are confined to this
        source-catalog package.
        """
        roots = {root.root_id: root for root in self.config.roots}
        locations: list[dict[str, Any]] = []
        for row in self.reader.exact_source_locations(document_id, source_id):
            location = dict(row)
            root = roots.get(str(location["root_id"]))
            if root is None:
                continue
            location["root_priority"] = root.priority
            locations.append(location)
        ranked = self._annotate_location_rows(document_id, locations)
        return tuple(
            RankedSourceLocation(
                location_id=str(item["location_id"]),
                source_id=str(item["source_id"]),
                root_id=str(item["root_id"]),
                relative_path=str(item["relative_path"]),
                role=str(item["role"]),
                location_status=str(item["location_status"]),
                candidate_rank=int(item["candidate_rank"]),
                exclusion_reason=str(item["exclusion_reason"]),
                manifest_json=(
                    str(item["manifest_json"])
                    if item.get("manifest_json") is not None else None
                ),
            )
            for item in ranked
        )

    def processing_descriptor(
        self, ref: SourceRef,
    ) -> SourceProcessingDescriptor | None:
        """Return pathless parser metadata for one exact registered source.

        Manifest JSON and physical locators stay within the catalog owner.
        Consumers receive only source identity, the logical format hint and
        validated provenance fields required by the parser runtime.
        """
        if not isinstance(ref, SourceRef):
            raise TypeError("ref must be SourceRef")
        for location in self.source_location_candidates(
            ref.document_id, ref.source_id,
        ):
            if location.candidate_rank <= 0 or not location.manifest_json:
                continue
            try:
                payload = json.loads(location.manifest_json)
                manifest = SourceManifest.from_dict(payload)
            except Exception:  # malformed location metadata is one bad candidate
                continue
            if (
                manifest.source_id != ref.source_id
                or manifest.content_sha256 != ref.content_sha256
                or manifest.byte_size != ref.byte_size
                or manifest.mime_type != ref.mime_type
            ):
                continue
            suffix = Path(manifest.original_path).suffix.lower()
            return SourceProcessingDescriptor(
                source_ref=ref,
                format_hint=suffix.lstrip(".") or None,
                source_type=manifest.source_type.value,
                entity_ids=manifest.entity_ids,
                published_date=manifest.published_date,
                retrieved_at=manifest.retrieved_at,
                collector_name=manifest.collector_name,
                collector_version=manifest.collector_version,
                immutable_status=manifest.immutable_status.value,
            )
        return None

    def source_copy_availability(
        self, request: SourceCopyAvailabilityRequest,
    ) -> SourceCopyAvailability:
        """Observe registered copies while keeping storage details in Catalog.

        Company-level projections need only copy count and current readability.
        This port intentionally returns no root objects or physical locators.
        The actual version read still verifies complete bytes through the
        SourceRef-bound reader.
        """
        try:
            rows = self.reader.exact_source_locations(
                request.document_id, request.source_id
            )
        except (CatalogReaderUnavailable, sqlite3.Error):
            return SourceCopyAvailability(copy_count=0, readable=False)

        roots = {root.root_id: root for root in self.config.roots}
        candidates: list[CatalogLocationCandidate] = []
        accepted_rows: list[tuple[dict[str, Any], Any]] = []
        for row in rows:
            location = dict(row)
            root = roots.get(str(location["root_id"]))
            if root is None:
                continue
            if relative_segments(str(location["relative_path"])) is None:
                continue
            candidates.append(
                CatalogLocationCandidate(
                    location_id=str(location["location_id"]),
                    source_id=(
                        str(location["source_id"])
                        if location.get("source_id") is not None else None
                    ),
                    root_id=str(location["root_id"]),
                    relative_path=str(location["relative_path"]),
                    role=str(location["role"]),
                    location_status=str(location["location_status"]),
                    root_priority=root.priority,
                    manifest_json=(
                        str(location["manifest_json"])
                        if location.get("manifest_json") is not None else None
                    ),
                )
            )
            accepted_rows.append((location, root))

        annotations = {
            item.location_id: item
            for item in self.annotate_locations(request.document_id, tuple(candidates))
        }
        copy_count = 0
        readable = False
        for location, root in accepted_rows:
            annotation = annotations[str(location["location_id"])]
            if annotation.candidate_rank <= 0:
                continue
            if root.allowed_document_kinds and request.document_kind not in (
                root.allowed_document_kinds
            ):
                continue
            if root.allowed_statuses and "active" not in root.allowed_statuses:
                continue
            if root.max_file_size is not None and request.byte_size > root.max_file_size:
                continue
            observed, problem = metadata_state(location.get("manifest_json"))
            if problem is not None:
                continue
            if observed.get("content_sha256") not in (
                None, "", request.content_sha256
            ):
                continue
            copy_count += 1
            try:
                path = resolve_source_location(root, annotation.relative_path)
            except SourceLocationError:
                continue
            if path.is_file():
                readable = True
        return SourceCopyAvailability(copy_count=copy_count, readable=readable)

    def browse_entity_records(self, canonical_entity_id: str) -> tuple[CatalogBrowseVersion, ...]:
        """Return the catalog-owned pathless browse projection for an entity."""
        entity = _required_catalog_text(canonical_entity_id, "canonical_entity_id")
        sql = _browse_projection_sql(
            " WHERE d.document_id IN ("
            "SELECT document_id FROM document_entities WHERE entity_id = ?)"
            " OR (json_valid(d.metadata_json) AND ("
            "json_extract(d.metadata_json, '$.acquisition.canonical_entity_id') = ?"
            " OR json_extract(d.metadata_json, '$.dayu_meta.canonical_entity_id') = ?))"
        )
        rows = self.reader.fetchall(sql, (entity, entity, entity))
        records: list[CatalogBrowseVersion] = []
        for row in rows:
            records.extend(self._browse_versions_for_document(_browse_document(row)))
        return tuple(records)

    def browse_document_records(self, document_id: str) -> tuple[CatalogBrowseVersion, ...]:
        """Return all original versions for one indexed document."""
        document = _required_catalog_text(document_id, "document_id")
        row = self.reader.fetchone(
            _browse_projection_sql(" WHERE d.document_id = ?"), (document,)
        )
        if row is None:
            return ()
        return tuple(self._browse_versions_for_document(_browse_document(row)))

    def iter_original_version_identities(self) -> tuple[SourceVersionIdentity, ...]:
        """Return pathless identities for exact reopen-token resolution."""
        role_clause = ", ".join("?" for _ in _BROWSE_VERSION_ROLES)
        location_rows = self.reader.fetchall(
            f"""SELECT l.document_id, l.source_id, s.content_sha256
                FROM locations l JOIN sources s ON s.source_id=l.source_id
                WHERE l.source_id IS NOT NULL AND l.role IN ({role_clause})""",
            _BROWSE_VERSION_ROLES,
        )
        primary_rows = self.reader.fetchall(
            """SELECT d.document_id, d.primary_source_id AS source_id,
                      s.content_sha256
               FROM documents d JOIN sources s ON s.source_id=d.primary_source_id
               WHERE d.primary_source_id IS NOT NULL"""
        )
        identities = {
            (str(row["document_id"]), str(row["source_id"])):
                str(row["content_sha256"])
            for row in (*location_rows, *primary_rows)
        }
        return tuple(
            SourceVersionIdentity(document_id, source_id, digest)
            for (document_id, source_id), digest in sorted(identities.items())
        )

    def _browse_versions_for_document(
        self, document: dict[str, Any],
    ) -> list[CatalogBrowseVersion]:
        document_id = str(document["document_id"])
        role_clause = ", ".join("?" for _ in _BROWSE_VERSION_ROLES)
        location_rows = self.reader.fetchall(
            f"""SELECT source_id, root_id, role, location_status, relative_path
               FROM locations
               WHERE document_id = ? AND source_id IS NOT NULL
                 AND role IN ({role_clause})""",
            (document_id, *_BROWSE_VERSION_ROLES),
        )
        source_ids = {str(item["source_id"]) for item in location_rows}
        if document["primary_source_id"]:
            source_ids.add(str(document["primary_source_id"]))
        if not source_ids:
            return []
        placeholders = ", ".join("?" for _ in source_ids)
        source_rows = self.reader.fetchall(
            f"""SELECT source_id, content_sha256, byte_size, mime_type, first_seen_at
                FROM sources WHERE source_id IN ({placeholders})
                ORDER BY first_seen_at, source_id""",
            tuple(sorted(source_ids)),
        )
        config_root_ids = {root.root_id for root in self.config.roots}
        from .source_location import relative_segments

        locations_by_source: dict[str, list[Any]] = {}
        for location in location_rows:
            locations_by_source.setdefault(str(location["source_id"]), []).append(location)
        records: list[CatalogBrowseVersion] = []
        for ordinal, source in enumerate(source_rows, start=1):
            source_id = str(source["source_id"])
            locations = locations_by_source.get(source_id, [])
            resolvable = any(
                str(location["location_status"]) == "active"
                and str(location["root_id"]) in config_root_ids
                and isinstance(location["relative_path"], str)
                and relative_segments(location["relative_path"]) is not None
                for location in locations
            )
            records.append(CatalogBrowseVersion(
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
                roles=tuple(sorted({str(item["role"]) for item in locations})),
                resolvable=resolvable,
            ))
        return records

    def identify_company(self, query: str, *, market: str):
        from .security_identity import (SecurityMasterStore, SecurityIdentityResolver,
            SecurityMasterUnavailableError, IdentityResult, IdentityStatus, load_identity_master)
        store = SecurityMasterStore(self.config.catalog_dir / "security_master")
        try:
            master = load_identity_master(store, market=market)
        except SecurityMasterUnavailableError:
            return IdentityResult(query=query, normalized_query=query, market_hint=market,
                exchange_hint=None, status=IdentityStatus.MISSING,
                reason="company_identity_snapshot_unavailable", resolved=None, candidates=())
        return SecurityIdentityResolver(master).identify(query, market=market)

    def register_sec_20f_listing_link(
        self, *, document_id: str, source_id: str, content_sha256: str,
    ) -> dict[str, Any]:
        """Import SEC cross-market listing rows from an exact CWP SourceRef.

        The caller supplies only the public source identifiers.  CWP resolves
        the exact SourceRef, reads it through SourceVersionReader, verifies its
        bytes, and stores a versioned issuer-link fact beside the owned market
        snapshots. No physical document path crosses the public boundary.
        """
        from .security_identity import SecurityMasterStore
        from .security_listing_evidence import build_sec_20f_listing_evidence
        from .source_reader import SourceVersionReader

        reader = SourceVersionReader(self)
        ref = reader.query_ref(document_id, source_id, content_sha256)
        content, metadata = reader.open_described_version(ref, purpose="filing_reuse")
        store = SecurityMasterStore(self.config.catalog_dir / "security_master")
        master = store.load()
        evidence = build_sec_20f_listing_evidence(
            content, metadata=metadata, master=master,
        )
        if evidence is None:
            return {
                "status": "no_verified_cross_market_equity_rows",
                "source_id": ref.source_id,
                "content_sha256": ref.content_sha256,
            }
        with self.operation_lock(operation="source-identity-link"):
            created = store.register_issuer_link_evidence(evidence)
        return {
            "status": "registered" if created else "already_registered",
            "issuer_link_id": evidence.issuer_link_id,
            "issuer_cik": evidence.issuer_cik,
            "source_id": evidence.source_id,
            "content_sha256": evidence.source_sha256,
            "listing_count": len(evidence.listings),
            "markets": sorted({item.market for item in evidence.listings}),
        }

    def __init__(self, config: CatalogConfig):
        if not isinstance(config, CatalogConfig):
            raise TypeError("config must be CatalogConfig")
        self.config = config
        self._store: CatalogStore | None = None
        self._reader: ReadOnlyCatalogReader | None = None

    @property
    def store(self) -> CatalogStore:
        if self._store is None:
            self._store = CatalogStore(self.config.database_path)
        return self._store

    @property
    def reader(self) -> ReadOnlyCatalogReader:
        """Zero-write read model (ZR-203): read entrypoints use this reader,
        never the writable store.  Opening the real catalog is therefore
        possible under OS-read-only permissions."""
        if self._reader is None:
            self._reader = ReadOnlyCatalogReader(self.config.database_path)
        return self._reader

    def open_narrative_artifact_reader(self) -> NarrativeArtifactReader:
        """Open a caller-owned read-only artifact session without initializing storage."""
        return NarrativeArtifactStore.for_reading(
            self.config.database_path, self._narrative_objects(),
        )

    def open_narrative_artifact_store(
        self, *, write_policy: NarrativeObjectWritePolicy | None = None,
    ) -> NarrativeArtifactStore:
        """Open the artifact writer, optionally with caller-owned write accounting."""
        return NarrativeArtifactStore(
            self.store, self._narrative_objects(write_policy=write_policy),
        )

    def open_narrative_object_access(
        self, *, write_policy: NarrativeObjectWritePolicy,
    ) -> NarrativeObjectAccess:
        """Open the paid-response byte port without initializing the catalog database."""
        return NarrativeObjectAccess(self._narrative_objects(write_policy=write_policy))

    def _narrative_objects(
        self, *, write_policy: NarrativeObjectWritePolicy | None = None,
    ) -> LocalNarrativeObjectStore:
        return LocalNarrativeObjectStore(self.config.catalog_dir, write_policy=write_policy)

    @contextmanager
    def operation_lock(self, *, operation: str) -> Iterator[None]:
        """Use the same catalog lock as source registration and publication."""
        with CatalogOperationLock(self.config.catalog_dir, operation=operation):
            yield

    def narrative_database_sizes(self) -> tuple[int, int, int]:
        """Read catalog SQLite/WAL/SHM sizes for legacy budget and diagnostics."""
        return database_file_sizes(self.config.database_path)

    def narrative_object_bytes(self) -> int:
        """Read CAS bytes for frozen pre-ledger storage baselines."""
        return file_tree_bytes(self.config.catalog_dir / "objects")

    def legacy_narrative_generation_directory(self) -> Path:
        """Keep the existing AUTO-owned recovery locator across upgrades."""
        return self.config.catalog_dir / "narrative-generations"

    def storage_is_within(self, directory: Path) -> bool:
        """Check a work-directory ancestor without disclosing catalog or raw paths."""
        directory = directory.resolve()
        return any(path.resolve().is_relative_to(directory) for path in (
            self.config.catalog_dir, *(root.path for root in self.config.roots),
        ))

    def close(self) -> None:
        """Release the cached reader connection (ZR-203).  Callers that keep
        a SourceCatalog alive across temp-directory teardown (tests, runners)
        must close it so Windows can delete the catalog file."""
        if self._reader is not None:
            self._reader.close()
            self._reader = None

    def scan(
        self,
        *,
        dry_run: bool = False,
        root_ids: set[str] | None = None,
        progress: Callable[..., None] | None = None,
        v2_scan_shadow: bool | None = None,
    ) -> ScanReport:
        if v2_scan_shadow is None:
            # Root.adapter_id selects its configured adapter in the scanner.
            # Do not force the historical 2.x-only mode onto compatible roots
            # without an adapter, or let rollout snapshots change the choice.
            v2_scan_shadow = False
        if dry_run:
            return scan_catalog(
                self.config,
                None,
                dry_run=True,
                root_ids=root_ids,
                progress=progress,
                v2_scan_shadow=v2_scan_shadow,
            )
        with CatalogOperationLock(self.config.catalog_dir, operation="scan"):
            return scan_catalog(
                self.config,
                self.store,
                dry_run=False,
                root_ids=root_ids,
                progress=progress,
                v2_scan_shadow=v2_scan_shadow,
            )

    def register_sources(self, *, root_id: str, relative_paths: set[str], budget=None) -> ScanReport:
        """Register explicit groups without full-root discovery or reconciliation."""
        from .registration_scope import SourceRegistrationScope, register_catalog_sources

        scope = SourceRegistrationScope(root_id, frozenset(relative_paths))
        with CatalogOperationLock(self.config.catalog_dir, operation="source_registration"):
            return register_catalog_sources(self.config, self.store, scope, budget=budget)

    def record_source_facts(self, *, ref: Any, facts: dict[str, Any],
                            evidence: dict[str, Any]) -> dict[str, Any]:
        """Verify bytes and atomically append facts plus their query projection."""
        from .assertion_service import record_source_facts

        return record_source_facts(self, ref=ref, facts=facts, evidence=evidence)

    def backfill_text_fingerprints(
        self,
        *,
        limit: int | None = None,
        progress: Callable[..., None] | None = None,
        should_stop: Callable[[], bool] | None = None,
        retry_limit: int = 3,
        retry_backoff_seconds: int = 900,
        now_epoch: float | None = None,
        parser_timeout_seconds: float = 3600,
        parser_heartbeat_interval_seconds: float = 15,
        parser_result_max_bytes: int = 268_435_456,
    ) -> ProcessingReport:
        with CatalogOperationLock(
            self.config.catalog_dir, operation="backfill_text_fingerprints"
        ):
            return backfill_text_fingerprints(
                self.config,
                self.store,
                limit=limit,
                progress=progress,
                should_stop=should_stop,
                retry_limit=retry_limit,
                retry_backoff_seconds=retry_backoff_seconds,
                now_epoch=now_epoch,
                parser_timeout_seconds=parser_timeout_seconds,
                parser_heartbeat_interval_seconds=parser_heartbeat_interval_seconds,
                parser_result_max_bytes=parser_result_max_bytes,
            )

    def status(self) -> dict[str, int]:
        return self.reader.status()

    def query_filing_candidates(
        self,
        *,
        entity: str | None = None,
        document_kind: str,
        source_statuses: tuple[str, ...],
        root_ids: tuple[str, ...] | None = None,
        fiscal_year: int | None = None,
        published_on_or_before: str | None = None,
        limit: int = 100,
        offset: int = 0,
        identity_tokens: tuple[str, ...] | None = None,
        after_document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """WU-3.2: SQL-pushdown filing-candidate lookup (F-021/F-026).

        ``identity_tokens`` uses the source identity projection and supports
        paging by document ID. It narrows to a superset, including dirty and
        historical declarations. The resolver qualifies current identity,
        period and location after lookup. The legacy ``entity`` filter uses
        exact document-entity names and is useful for inventory queries.
        """
        if limit <= 0:
            raise ValueError("limit must be positive")
        if offset < 0:
            raise ValueError("offset must be non-negative")
        if not document_kind or not source_statuses:
            raise ValueError("document_kind/source_statuses required")
        from .document_kinds import requested_kind_candidates
        kind_values=requested_kind_candidates(document_kind)
        kind_clause=('d.document_kind = ?' if len(kind_values)==1 else
                     'd.document_kind IN ('+', '.join('?' for _ in kind_values)+')')
        placeholders = ", ".join("?" for _ in source_statuses)
        root_clause = ""
        root_params: tuple[str, ...] = ()
        if root_ids:
            root_placeholders = ", ".join("?" for _ in root_ids)
            root_clause = (
                "AND d.document_id IN ("
                f"SELECT document_id FROM locations WHERE root_id IN ({root_placeholders}) "
                "AND role = 'original_primary' AND location_status = 'active')"
            )
            root_params = root_ids
        entity_clause = (
            "AND d.document_id IN (SELECT document_id FROM document_entities de "
            "JOIN entities e ON e.entity_id = de.entity_id WHERE e.name = ?)"
            if entity
            else ""
        )
        entity_params = (entity,) if entity else ()
        # fiscal_year lives inside metadata_json (no dedicated column); an
        # advisory json_extract filter narrows the slice so a 100-cap cannot
        # shadow an older-period request. The resolver's Python _fiscal_year
        # gate remains authoritative.
        #
        # json_valid() guard (B-VR05M-01, P0): without it, json_extract on a malformed
        # value raises `sqlite3.OperationalError: malformed JSON` IN SQL, before the
        # Python guard below can turn it into a state - measured for `{not json` AND for
        # the empty string.
        #
        # The row is EXCLUDED when filtered (B-VR05M2-05, correction): an earlier attempt
        # kept unreadable rows visible via `NOT json_valid(...) OR ...`, and a verifier
        # then measured that a corrupted row could occupy the `limit` and SHADOW a genuine
        # period match - losing a valid answer is worse than not listing a row whose
        # period cannot be established.  An unreadable row cannot be shown to match a
        # period, so it is not a match; the UNFILTERED read still reports it as
        # blocked/unreadable_metadata.
        fiscal_clause = (
            "AND (json_valid(d.metadata_json)"
            " AND (json_extract(d.metadata_json, '$.acquisition.fiscal_year') = ?"
            " OR json_extract(d.metadata_json, '$.dayu_meta.fiscal_year') = ?))"
            if fiscal_year is not None
            else ""
        )
        fiscal_params: tuple[int, ...] = (
            (fiscal_year, fiscal_year) if fiscal_year is not None else ()
        )
        published_clause = (
            "AND d.published_date <= ?" if published_on_or_before is not None else ""
        )
        published_params = (
            (published_on_or_before,) if published_on_or_before is not None else ()
        )
        identity_clause, identity_params = "", ()
        if identity_tokens is not None:
            from .identity_candidates import identity_candidate_clause
            identity_clause, identity_params = identity_candidate_clause(self.reader, identity_tokens)
        cursor_clause = "AND d.document_id > ?" if after_document_id is not None else ""
        cursor_params = (after_document_id,) if after_document_id is not None else ()
        order = "d.document_id" if identity_tokens is not None else "d.published_date DESC, d.title, d.document_id"
        entity_rows = self.reader.fetchall(
            f"""SELECT d.document_id, d.primary_source_id, d.title, d.source_type,
                       d.document_kind, d.published_date, d.source_status,
                       d.metadata_json, d.first_seen_at, d.last_seen_at,
                       s.content_sha256, s.byte_size
                FROM documents d
                LEFT JOIN sources s ON s.source_id = d.primary_source_id
                WHERE {kind_clause}
                  AND d.source_status IN ({placeholders})
                  {entity_clause}
                  {root_clause}
                  {fiscal_clause}
                  {published_clause}
                  {identity_clause}
                  {cursor_clause}
                ORDER BY {order}
                LIMIT ? OFFSET ?
                """,
            (
                *kind_values,
                *source_statuses,
                *entity_params,
                *root_params,
                *fiscal_params,
                *published_params,
                *identity_params,
                *cursor_params,
                limit,
                offset,
            ),
        )
        if not entity_rows:
            return []
        ids = [row["document_id"] for row in entity_rows]
        id_placeholders = ", ".join("?" for _ in ids)
        # WU-3.2 reviewer: batch entities/locations in 2 queries instead of
        # N+1 per-document lookups (100-doc cap previously meant 200 queries).
        entities: dict[str, list[dict[str, Any]]] = {}
        for row in self.reader.fetchall(
            f"""SELECT de.document_id, e.entity_id, e.name, e.entity_kind,
                       de.confidence, de.method
                FROM document_entities de
                JOIN entities e ON e.entity_id = de.entity_id
                WHERE de.document_id IN ({id_placeholders})
                ORDER BY de.document_id, e.entity_id""",
            tuple(ids),
        ):
            entities.setdefault(row["document_id"], []).append(dict(row))
        locations: dict[str, list[dict[str, Any]]] = {}
        for row in self.reader.fetchall(
            f"""SELECT l.location_id, l.document_id, l.root_id, l.relative_path,
                       l.absolute_path, l.source_id, l.role, l.location_status,
                       l.observed_size, l.observed_mtime_ns, l.error,
                       l.manifest_json, l.metadata_json, r.priority AS root_priority
                FROM locations l
                JOIN roots r ON r.root_id = l.root_id
                WHERE l.document_id IN ({id_placeholders})
                ORDER BY l.document_id, r.priority, l.root_id, l.relative_path""",
            tuple(ids),
        ):
            locations.setdefault(row["document_id"], []).append(dict(row))
        results: list[dict[str, Any]] = []
        for row in entity_rows:
            document_id = row["document_id"]
            doc_locations = self._annotate_location_rows(
                document_id, locations.get(document_id, [])
            )
            # B05 read contract (work package b05-read-side-malformed-columns, from
            # B-VR06-02's second half): the shared column is written by several modules,
            # so the READ side must not assume its shape.  It used to raise straight out
            # of here - JSONDecodeError for invalid JSON, TypeError for NULL,
            # AttributeError when `r4_provenance.fields` was a list - turning a data
            # problem into a process failure and disagreeing with the B06 envelope,
            # which called the same document verified_input.  Malformed content is now a
            # named state (`metadata_problem`), blocked, with no provenance claims.
            metadata: Any = {}
            metadata_problem: str | None = None
            provenance_fields: dict[str, Any] = {}
            # B10-3: the parse is the single chain's reporting half (store.metadata_state);
            # both of its states map to this caller's named state below.  History
            # (B-VR05M-02): RecursionError is a RuntimeError, NOT a ValueError - deeply
            # nested JSON raised straight past the first version of this guard, so "never a
            # crash" was literally false for that shape.  The chain's catch set covers it
            # now (and is narrower than the old bare ValueError - B-VR-B10-07).
            payload, parse_state = metadata_state(row["metadata_json"])
            if parse_state is not None:
                metadata_problem = "unreadable_metadata"
            else:
                metadata = payload
                reserved = metadata.get(R4_PROVENANCE_KEY)
                if reserved is not None and not isinstance(reserved, dict):
                    metadata_problem = "unreadable_metadata"
                else:
                    candidate_fields = (
                        reserved.get("fields") if isinstance(reserved, dict) else None
                    )
                    if candidate_fields is None:
                        provenance_fields = {}
                    elif isinstance(candidate_fields, dict):
                        provenance_fields = candidate_fields
                    else:
                        metadata_problem = "unreadable_metadata"
            conflicted_fields = sorted(
                name
                for name, record in provenance_fields.items()
                if isinstance(record, dict) and record.get("conflicts")
            )
            if conflicted_fields and metadata_problem is None:
                metadata_problem = "field_conflicts"
            results.append(
                {
                    "document_id": document_id,
                    "source_id": row["primary_source_id"],
                    "content_sha256": row["content_sha256"],
                    "byte_size": row["byte_size"],
                    "title": row["title"],
                    "source_type": row["source_type"],
                    "document_kind": row["document_kind"],
                    "published_date": row["published_date"],
                    "source_status": row["source_status"],
                    "metadata": metadata,
                    "provenance": provenance_fields,
                    "conflicts": conflicted_fields,
                    "metadata_status": "blocked" if metadata_problem else "ok",
                    "metadata_problem": metadata_problem,
                    "entities": entities.get(document_id, []),
                    "locations": doc_locations,
                    **self._duplicate_summary(doc_locations),
                    "artifacts": [],
                }
            )
        return results

    def explain_filing_candidates_plan(
        self,
        *,
        entity: str | None = None,
        document_kind: str,
        source_statuses: tuple[str, ...],
        root_ids: tuple[str, ...] | None = None,
    ) -> list[str]:
        """WU-3.2: EXPLAIN QUERY PLAN for the pushdown query (index gate)."""
        placeholders = ", ".join("?" for _ in source_statuses)
        root_clause = ""
        root_params: tuple[str, ...] = ()
        if root_ids:
            root_placeholders = ", ".join("?" for _ in root_ids)
            root_clause = (
                "AND d.document_id IN ("
                f"SELECT document_id FROM locations WHERE root_id IN ({root_placeholders}) "
                "AND role = 'original_primary' AND location_status = 'active')"
            )
            root_params = root_ids
        entity_clause = (
            "AND d.document_id IN (SELECT document_id FROM document_entities de "
            "JOIN entities e ON e.entity_id = de.entity_id WHERE e.name = ?)"
            if entity
            else ""
        )
        entity_params = (entity,) if entity else ()
        rows = self.reader.fetchall(
            f"""EXPLAIN QUERY PLAN
                SELECT d.document_id
                FROM documents d
                WHERE d.document_kind = ?
                  AND d.source_status IN ({placeholders})
                  {entity_clause}
                  {root_clause}
                LIMIT 1
                """,
            (document_kind, *source_statuses, *entity_params, *root_params),
        )
        return [str(row[3]) for row in rows]

    def query_source_bundle(
        self,
        *,
        document_id: str,
        registry: dict[str, set[str]],
        allowed_roots: tuple[Path, ...],
        now: str,
        expected_content_sha256: str | None = None,
    ) -> dict[str, Any] | None:
        """WU-5.3 + FC-902: one query returns the source document + verified
        artifacts as a SourceBundle (None when the document is unknown).

        ``expected_content_sha256`` (FC-902 snapshot consistency): when the
        caller's handle claims a content hash that differs from the catalog's
        current source bytes, NO bundle is served — a bundle built from other
        bytes would be a stale/forged derivation.  Fail closed.
        """
        row = self.reader.fetchone(
            "SELECT * FROM documents WHERE document_id = ?", (document_id,)
        )
        if row is None:
            return None
        document = dict(row)
        source = dict(
            document_id=document["document_id"],
            primary_source_id=document["primary_source_id"] or "",
            source_sha256="",
            as_of_date=document["published_date"] or "",
        )
        if document.get("primary_source_id"):
            src = self.reader.fetchone(
                "SELECT content_sha256 FROM sources WHERE source_id = ?",
                (document["primary_source_id"],),
            )
            if src is not None:
                if (
                    expected_content_sha256 is not None
                    and expected_content_sha256 != src["content_sha256"]
                ):
                    return None  # fail closed: bytes drifted from the claim
                source["source_sha256"] = src["content_sha256"]
        artifacts = [
            dict(artifact)
            for artifact in self.reader.fetchall(
                """SELECT artifact_id,artifact_role,source_id,path,content_sha256,
                          byte_size,mime_type,generator_name,generator_version,status,
                          error,schema_version,source_sha256,created_at
                   FROM artifacts WHERE document_id = ?
                   ORDER BY artifact_role,created_at,artifact_id""",
                (document_id,),
            )
        ]
        from .source_bundle import build_source_bundle

        bundle = build_source_bundle(
            source=source,
            artifacts=artifacts,
            registry=registry,
            allowed_roots=allowed_roots,
            now=now,
        )
        return bundle.to_dict()

    def bundle_for_resolution(
        self,
        resolution: Any,
        *,
        registry: dict[str, set[str]] | None = None,
        allowed_roots: tuple[Path, ...] | None = None,
        now: str | None = None,
    ) -> dict[str, Any] | None:
        """FC-902: production bundle builder for the resolve/envelope path.

        Returns the snapshot-consistent SourceBundle for a reuse outcome, or
        None when no bundle can honestly be built (non-reuse outcome, unknown
        document, or a content-hash drift vs the handle — the caller then
        reports bundle_status=unavailable, never a faked green).
        """
        if not getattr(resolution, "matches", None):
            return None
        status = getattr(resolution, "status", None)
        if status is None or status.value not in ("reused_exact", "reused_equivalent"):
            return None
        match = resolution.matches[0]
        from .source_bundle import GENERATOR_REGISTRY

        effective_registry = registry if registry is not None else GENERATOR_REGISTRY
        effective_roots = (
            allowed_roots
            if allowed_roots is not None
            else tuple(root.path for root in self.config.roots)
            + (self.config.derived_dir,)
        )
        effective_now = now or _utc_now()
        return self.query_source_bundle(
            document_id=match.document_id,
            registry=effective_registry,
            allowed_roots=effective_roots,
            now=effective_now,
            expected_content_sha256=match.content_sha256,
        )

    def query(
        self,
        *,
        text: str | None = None,
        entity: str | None = None,
        document_kind: str | None = None,
        source_status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        documents = self.reader.fetchall(
            "SELECT * FROM documents ORDER BY published_date DESC,title,document_id"
        )
        entity_rows = self.reader.fetchall(
            """SELECT de.document_id,e.entity_id,e.name,e.entity_kind,de.confidence,de.method
            FROM document_entities de JOIN entities e ON e.entity_id=de.entity_id
            ORDER BY de.document_id,e.entity_id"""
        )
        location_rows = self.reader.fetchall(
            """SELECT l.location_id,l.document_id,l.root_id,l.relative_path,l.absolute_path,
            l.source_id,l.role,l.location_status,l.observed_size,l.observed_mtime_ns,l.error,l.manifest_json,
            l.metadata_json,r.priority AS root_priority
            FROM locations l JOIN roots r ON r.root_id=l.root_id
            WHERE l.document_id IS NOT NULL
            ORDER BY l.document_id,r.priority,l.root_id,l.relative_path"""
        )
        artifact_rows = self.reader.fetchall(
            """SELECT document_id,artifact_role,path,status,content_sha256,byte_size,generator_name,
            generator_version,error,source_id,schema_version,source_sha256,created_at
            FROM artifacts ORDER BY document_id,artifact_role,created_at"""
        )
        source_rows = self.reader.fetchall(
            "SELECT source_id,content_sha256,byte_size FROM sources"
        )
        source_by_id = {row["source_id"]: row for row in source_rows}
        entities_by_document: dict[str, list[Any]] = {}
        locations_by_document: dict[str, list[Any]] = {}
        artifacts_by_document: dict[str, list[Any]] = {}
        for item in entity_rows:
            entities_by_document.setdefault(item["document_id"], []).append(item)
        for item in location_rows:
            locations_by_document.setdefault(item["document_id"], []).append(item)
        for item in artifact_rows:
            artifacts_by_document.setdefault(item["document_id"], []).append(item)
        results: list[dict[str, Any]] = []
        for document in documents:
            document_id = document["document_id"]
            entities = entities_by_document.get(document_id, [])
            locations = self._annotate_location_rows(
                document_id,
                [dict(item) for item in locations_by_document.get(document_id, [])],
            )
            artifacts = artifacts_by_document.get(document_id, [])
            searchable = "\n".join(
                [
                    document["document_id"],
                    document["primary_source_id"] or "",
                    document["title"],
                    document["document_kind"],
                    document["source_type"],
                    document["published_date"] or "",
                    *(item["name"] for item in entities),
                    *(item["relative_path"] for item in locations),
                    *(item["absolute_path"] for item in locations),
                    *(item["source_id"] or "" for item in locations),
                ]
            ).casefold()
            if text and text.casefold() not in searchable:
                continue
            if entity and not any(
                entity.casefold() in item["name"].casefold() for item in entities
            ):
                continue
            if document_kind and document["document_kind"] != document_kind:
                continue
            if source_status:
                if document["source_status"] != source_status:
                    continue
            elif document["source_status"] != "active":
                # WU-3.1 (F-024): the default view is active-only. Retired
                # was already hidden (Phase 15.5); quarantined and
                # upstream_rejected are now hidden too. Only an explicit
                # source_status query sees non-active documents.
                continue
            artifact_map = {item["artifact_role"]: dict(item) for item in artifacts}
            primary_source_id = document["primary_source_id"]
            primary_source = (
                source_by_id.get(primary_source_id) if primary_source_id else None
            )
            results.append(
                {
                    "document_id": document["document_id"],
                    "source_id": document["primary_source_id"],
                    "content_sha256": (
                        primary_source["content_sha256"] if primary_source else None
                    ),
                    "byte_size": (
                        int(primary_source["byte_size"]) if primary_source else None
                    ),
                    "title": document["title"],
                    "source_type": document["source_type"],
                    "document_kind": document["document_kind"],
                    "published_date": document["published_date"],
                    "source_status": document["source_status"],
                    "metadata": _read_shared_metadata(document["metadata_json"]),
                    "entities": [dict(item) for item in entities],
                    "locations": locations,
                    **self._duplicate_summary(locations),
                    "normalized_path": artifact_map.get("normalized", {}).get("path"),
                    "summary_path": artifact_map.get("summary", {}).get("path"),
                    "artifacts": [dict(item) for item in artifacts],
                }
            )
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def annotate_locations(
        document_id: str,
        locations: tuple[CatalogLocationCandidate, ...],
    ) -> tuple[CatalogLocationAnnotation, ...]:
        """Return immutable ranking results for pathless logical candidates."""
        return rank_location_candidates(document_id, locations)

    @classmethod
    def _annotate_location_rows(
        cls,
        document_id: str,
        locations: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Adapt database rows to the immutable ranking contract internally."""
        candidates = tuple(
            CatalogLocationCandidate(
                location_id=str(location["location_id"]),
                source_id=(
                    str(location["source_id"])
                    if location.get("source_id") is not None else None
                ),
                root_id=str(location["root_id"]),
                relative_path=str(location["relative_path"]),
                role=str(location["role"]),
                location_status=str(location["location_status"]),
                root_priority=int(location["root_priority"]),
                manifest_json=(
                    str(location["manifest_json"])
                    if location.get("manifest_json") is not None else None
                ),
            )
            for location in locations
        )
        annotations = {
            item.location_id: asdict(item)
            for item in cls.annotate_locations(document_id, candidates)
        }
        return [
            {**location, **annotations[str(location["location_id"])]}
            for location in locations
        ]

    @staticmethod
    def _duplicate_summary(locations: list[dict[str, Any]]) -> dict[str, Any]:
        # Unchanged from before B02 (the duplicate/cleanup view must not lose
        # provider-rejected rows: they are exactly what an operator reclaims).
        active_originals = [
            item
            for item in locations
            if item["role"] == "original_primary"
            and item["location_status"] == "active"
            and item["source_id"]
        ]
        duplicates = [
            item
            for item in active_originals
            if item["duplicate_relation"] == "exact_copy"
        ]
        group_ids = sorted(
            {
                item["duplicate_group_id"]
                for item in active_originals
                if item["duplicate_group_id"]
            }
        )
        canonical = next(
            (item for item in active_originals if item["is_canonical"]), None
        )
        return {
            "duplicate_status": "exact_copy" if duplicates else "none",
            "exact_original_copy_count": len(active_originals),
            "exact_duplicate_location_count": len(duplicates),
            "exact_duplicate_group_id": ";".join(group_ids),
            "canonical_location_id": canonical["location_id"] if canonical else "",
            "canonical_path": canonical["absolute_path"] if canonical else "",
        }

    @staticmethod
    def _duplicate_groups_from_documents(
        documents: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        groups: list[dict[str, Any]] = []
        for document in documents:
            by_group: dict[str, list[dict[str, Any]]] = {}
            for location in document["locations"]:
                group_id = location["duplicate_group_id"]
                if group_id:
                    by_group.setdefault(group_id, []).append(location)
            for group_id, locations in sorted(by_group.items()):
                canonical = next(item for item in locations if item["is_canonical"])
                duplicates = sorted(
                    (
                        item
                        for item in locations
                        if item["duplicate_relation"] == "exact_copy"
                    ),
                    key=lambda item: (
                        item["root_priority"],
                        item["root_id"],
                        item["relative_path"],
                    ),
                )
                groups.append(
                    {
                        "duplicate_group_id": group_id,
                        "relation_type": "exact_copy",
                        "document_id": document["document_id"],
                        "source_id": canonical["source_id"],
                        "canonical_location_id": canonical["location_id"],
                        "canonical_path": canonical["absolute_path"],
                        "exact_original_copy_count": 1 + len(duplicates),
                        "exact_duplicate_location_count": len(duplicates),
                        "duplicate_location_ids": ";".join(
                            item["location_id"] for item in duplicates
                        ),
                        "duplicate_paths": ";".join(
                            item["absolute_path"] for item in duplicates
                        ),
                        "match_basis": "document_id+source_id+sha256",
                        "confidence": 1.0,
                    }
                )
        return sorted(
            groups,
            key=lambda item: (
                item["document_id"],
                item["source_id"],
                item["duplicate_group_id"],
            ),
        )

    def duplicate_groups(self) -> list[dict[str, Any]]:
        """Return deterministic exact-copy groups over active original-primary locations."""
        return self._duplicate_groups_from_documents(self.query(limit=10_000_000))

    def semantic_duplicate_groups(self) -> list[dict[str, Any]]:
        """Groups of documents sharing a normalized-text fingerprint but differing bytes.

        Each group has ``relation_type='semantic_copy'`` and
        ``match_basis='normalized_text'``. Exact byte-identical copies collapse to
        one source/content hash, so a semantic group requires >=2 distinct
        ``content_sha256`` values. Members carry their canonical primary location
        so the same public shape as exact-copy groups can be derived downstream.
        """
        rows = self.reader.fetchall(
            """WITH ranked_locations AS (
                   SELECT l.location_id,l.document_id,l.source_id,l.root_id,
                          l.relative_path,l.absolute_path,l.observed_size,
                          r.priority AS root_priority,
                          ROW_NUMBER() OVER (
                              PARTITION BY l.document_id,l.source_id
                              ORDER BY r.priority,l.root_id,l.relative_path,l.location_id
                          ) AS location_rank
                   FROM locations l
                   JOIN roots r ON r.root_id=l.root_id
                   WHERE l.role='original_primary'
                     AND l.location_status='active'
               )
               SELECT d.document_id, d.title, d.document_kind, d.published_date,
               d.text_fingerprint, s.content_sha256, s.source_id,
               l.location_id, l.root_id, l.relative_path, l.absolute_path,
               l.observed_size, l.root_priority,
               (SELECT e.name FROM document_entities de
                  JOIN entities e ON e.entity_id=de.entity_id
                  WHERE de.document_id=d.document_id ORDER BY de.entity_id LIMIT 1) AS entity_name
               FROM documents d
               JOIN sources s ON s.source_id=d.primary_source_id
               JOIN ranked_locations l
                 ON l.document_id=d.document_id
                AND l.source_id=s.source_id
                AND l.location_rank=1
               WHERE d.text_fingerprint IS NOT NULL
               ORDER BY d.text_fingerprint, d.document_id"""
        )
        by_fingerprint: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_fingerprint.setdefault(row["text_fingerprint"], []).append(dict(row))
        groups: list[dict[str, Any]] = []
        for fingerprint, members in sorted(by_fingerprint.items()):
            distinct_shas = {item["content_sha256"] for item in members}
            if len(distinct_shas) <= 1:
                continue
            members_sorted = sorted(members, key=lambda item: item["document_id"])
            canonical = members_sorted[0]
            public_members = [
                {
                    "location_id": item["location_id"],
                    "root_id": item["root_id"],
                    "root_priority": int(item["root_priority"]),
                    "relative_path": item["relative_path"],
                    "absolute_path": item["absolute_path"],
                    "observed_size": item["observed_size"],
                    "is_canonical": item is canonical,
                    "duplicate_relation": "semantic_copy",
                    "document_id": item["document_id"],
                    "source_id": item["source_id"],
                    "content_sha256": item["content_sha256"],
                    "title": item["title"],
                    "document_kind": item["document_kind"],
                    "published_date": item["published_date"],
                    "entity": item["entity_name"] or "",
                }
                for item in members_sorted
            ]
            groups.append(
                {
                    "duplicate_group_id": "urn:company-wiki:duplicate:semantic:sha256:"
                    + fingerprint,
                    "relation_type": "semantic_copy",
                    "match_basis": "normalized_text",
                    "confidence": 0.95,
                    "text_fingerprint": fingerprint,
                    "member_count": len(public_members),
                    "distinct_byte_hashes": len(distinct_shas),
                    "document_id": canonical["document_id"],
                    "source_id": canonical["source_id"],
                    "title": canonical["title"],
                    "document_kind": canonical["document_kind"],
                    "published_date": canonical["published_date"],
                    "entities": [canonical["entity_name"]]
                    if canonical["entity_name"]
                    else [],
                    "content_sha256": canonical["content_sha256"],
                    "copy_count": len(public_members),
                    "reclaimable_copy_count": 0,
                    "reclaimable_bytes": 0,
                    "canonical": public_members[0],
                    "duplicates": public_members[1:],
                    "members": public_members,
                }
            )
        return groups

    @staticmethod
    def _duplicate_group_summaries(
        documents: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Exact-copy groups with human-readable fields, sorted by reclaimable bytes desc.

        Reclaims the bytes of non-canonical exact-copy locations only; the canonical
        copy is always preserved. Used for the index.md duplicate surfacing.
        """
        summaries: list[dict[str, Any]] = []
        for document in documents:
            by_group: dict[str, list[dict[str, Any]]] = {}
            for location in document["locations"]:
                group_id = location["duplicate_group_id"]
                if group_id:
                    by_group.setdefault(group_id, []).append(location)
            for locations in by_group.values():
                duplicates = [
                    item
                    for item in locations
                    if item["duplicate_relation"] == "exact_copy"
                ]
                if not duplicates:
                    continue
                entity = document["entities"][0]["name"] if document["entities"] else ""
                summaries.append(
                    {
                        "entity": entity,
                        "title": document["title"],
                        "document_kind": document["document_kind"],
                        "copy_count": 1 + len(duplicates),
                        "reclaimable_bytes": sum(
                            int(item.get("observed_size") or 0) for item in duplicates
                        ),
                    }
                )
        summaries.sort(
            key=lambda item: (-item["reclaimable_bytes"], item["entity"], item["title"])
        )
        return summaries

    def export_indexes(
        self,
        *,
        progress: Callable[..., None] | None = None,
    ) -> dict[str, Path]:
        with CatalogOperationLock(self.config.catalog_dir, operation="export"):
            return self._export_indexes(progress=progress)

    def _export_indexes(
        self,
        *,
        progress: Callable[..., None] | None = None,
    ) -> dict[str, Path]:
        output_dir = self.config.export_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        def emit(current: int, detail: str) -> None:
            if progress is not None:
                progress(
                    current_path=str(output_dir.resolve(strict=False)),
                    current=current,
                    total=12,
                    detail=detail,
                )

        emit(1, "loading catalog documents")
        documents = self.query(limit=10_000_000)
        emit(2, "building exact duplicate groups")
        duplicate_rows = self._duplicate_groups_from_documents(documents)
        emit(3, "building semantic duplicate groups")
        semantic_groups = self.semantic_duplicate_groups()
        semantic_rows = [
            {
                "duplicate_group_id": group["duplicate_group_id"],
                "relation_type": group["relation_type"],
                "match_basis": group["match_basis"],
                "confidence": group["confidence"],
                "text_fingerprint": group["text_fingerprint"],
                "member_count": group["member_count"],
                "distinct_byte_hashes": group["distinct_byte_hashes"],
                "member_document_ids": ";".join(
                    item["document_id"] for item in group["members"]
                ),
                "member_paths": ";".join(
                    item["absolute_path"] for item in group["members"]
                ),
            }
            for group in semantic_groups
        ]
        emit(4, "loading export journals")
        acquisition_rows = [
            item.to_dict()
            for item in AcquisitionJournal(self.config.catalog_dir).read_all()
        ]
        from .duplicate_cleanup import DuplicateCleanupJournal

        cleanup_rows = list(DuplicateCleanupJournal(self.config.catalog_dir).read_all())
        emit(5, "building export rows")
        artifact_rows: list[dict[str, Any]] = []
        document_rows: list[dict[str, Any]] = []
        location_rows: list[dict[str, Any]] = []
        for document in documents:
            entity_names = "; ".join(item["name"] for item in document["entities"])
            for location in document["locations"]:
                location_rows.append(
                    {
                        "location_id": location["location_id"],
                        "document_id": document["document_id"],
                        "source_id": location["source_id"] or "",
                        "root_id": location["root_id"],
                        "root_priority": location["root_priority"],
                        "role": location["role"],
                        "status": location["location_status"],
                        "path": location["absolute_path"],
                        "relative_path": location["relative_path"],
                        "is_canonical": location["is_canonical"],
                        "duplicate_relation": location["duplicate_relation"],
                        "duplicate_group_id": location["duplicate_group_id"],
                        "canonical_location_id": location["canonical_location_id"],
                    }
                )
                artifact_rows.append(
                    {
                        "artifact_role": "original",
                        "document_id": document["document_id"],
                        "source_id": location["source_id"] or "",
                        "entity": entity_names,
                        "document_kind": document["document_kind"],
                        "title": document["title"],
                        "published_date": document["published_date"] or "",
                        "status": location["location_status"],
                        "path": location["absolute_path"],
                        "sha256": (location["source_id"] or "").rsplit(":", 1)[-1]
                        if location["source_id"]
                        else "",
                        "byte_size": location["observed_size"] or "",
                        "generator": "filesystem",
                        "version": "1.0.0",
                    }
                )
            for artifact in document["artifacts"]:
                artifact_rows.append(
                    {
                        "artifact_role": artifact["artifact_role"],
                        "document_id": document["document_id"],
                        "source_id": document["source_id"] or "",
                        "entity": entity_names,
                        "document_kind": document["document_kind"],
                        "title": document["title"],
                        "published_date": document["published_date"] or "",
                        "status": artifact["status"],
                        "path": artifact["path"],
                        "sha256": artifact["content_sha256"],
                        "byte_size": artifact["byte_size"],
                        "generator": artifact["generator_name"],
                        "version": artifact["generator_version"],
                    }
                )
            document_rows.append(
                {
                    "document_id": document["document_id"],
                    "source_id": document["source_id"] or "",
                    "entity": entity_names,
                    "document_kind": document["document_kind"],
                    "source_type": document["source_type"],
                    "title": document["title"],
                    "published_date": document["published_date"] or "",
                    "source_status": document["source_status"],
                    "location_count": len(document["locations"]),
                    "exact_original_copy_count": document["exact_original_copy_count"],
                    "exact_duplicate_location_count": document[
                        "exact_duplicate_location_count"
                    ],
                    "duplicate_status": document["duplicate_status"],
                    "exact_duplicate_group_id": document["exact_duplicate_group_id"],
                    "canonical_location_id": document["canonical_location_id"],
                    "canonical_path": document["canonical_path"],
                    "normalized_path": document["normalized_path"] or "",
                    "summary_path": document["summary_path"] or "",
                }
            )
        artifacts_csv = output_dir / "artifacts.csv"
        documents_csv = output_dir / "documents.csv"
        locations_csv = output_dir / "locations.csv"
        duplicates_csv = output_dir / "duplicates.csv"
        acquisition_attempts_csv = output_dir / "acquisition_attempts.csv"
        duplicate_cleanup_events_csv = output_dir / "duplicate_cleanup_events.csv"
        self._write_csv(artifacts_csv, artifact_rows)
        emit(6, "wrote artifacts CSV")
        self._write_csv(documents_csv, document_rows)
        emit(7, "wrote documents CSV")
        self._write_csv(locations_csv, location_rows)
        emit(8, "wrote locations CSV")
        self._write_csv(
            duplicates_csv,
            duplicate_rows,
            fields=[
                "duplicate_group_id",
                "relation_type",
                "document_id",
                "source_id",
                "canonical_location_id",
                "canonical_path",
                "exact_original_copy_count",
                "exact_duplicate_location_count",
                "duplicate_location_ids",
                "duplicate_paths",
                "match_basis",
                "confidence",
            ],
        )
        emit(9, "wrote exact duplicate CSV")
        semantic_duplicates_csv = output_dir / "semantic_duplicates.csv"
        self._write_csv(
            semantic_duplicates_csv,
            semantic_rows,
            fields=[
                "duplicate_group_id",
                "relation_type",
                "match_basis",
                "confidence",
                "text_fingerprint",
                "member_count",
                "distinct_byte_hashes",
                "member_document_ids",
                "member_paths",
            ],
        )
        emit(10, "wrote semantic duplicate CSV")
        self._write_csv(
            acquisition_attempts_csv,
            acquisition_rows,
            fields=[
                "schema_version",
                "attempt_id",
                "recorded_at",
                "request_id",
                "outcome",
                "adapter_name",
                "candidate_id",
                "provider",
                "provider_document_id",
                "source_url",
                "content_sha256",
                "canonical_path",
                "reason",
                "error_type",
                "error",
            ],
        )
        self._write_csv(
            duplicate_cleanup_events_csv,
            cleanup_rows,
            fields=[
                "schema_version",
                "event_id",
                "action_id",
                "event",
                "recorded_at",
                "location_id",
                "absolute_path",
                "canonical_location_id",
                "canonical_path",
                "source_id",
                "content_sha256",
                "error_type",
                "error",
            ],
        )
        emit(11, "wrote journal CSVs")
        status = self.status()
        kinds: dict[str, int] = {}
        for document in documents:
            kinds[document["document_kind"]] = (
                kinds.get(document["document_kind"], 0) + 1
            )
        index_md = output_dir / "index.md"
        lines = [
            "# Source Catalog Index",
            "",
            f"- Documents: {status['documents']}",
            f"- Content-addressed sources: {status['sources']}",
            f"- Active locations: {status['active_locations']}",
            f"- Missing locations: {status['missing_locations']}",
            f"- Normalized Markdown: {status['normalized_artifacts']}",
            f"- Summary Markdown: {status['summary_artifacts']}",
            f"- Evidence spans: {status['evidence_spans']}",
            f"- Exact duplicate groups: {len(duplicate_rows)}",
            f"- Extra exact-copy locations: {sum(row['exact_duplicate_location_count'] for row in duplicate_rows)}",
            f"- Semantic duplicate groups: {len(semantic_groups)}",
            f"- Acquisition attempts: {len(acquisition_rows)}",
            f"- Duplicate cleanup events: {len(cleanup_rows)}",
            "",
            "## Duplicate groups (top 20 by reclaimable bytes)",
            "",
        ]
        summaries = self._duplicate_group_summaries(documents)[:20]
        if not summaries:
            lines.append("_No exact-copy duplicate groups._")
        else:
            lines.extend(
                (
                    "_Display-only summary of exact byte-identical copies. "
                    "Full list: `duplicates` CLI and `duplicates.csv`. "
                    "Recycle only via the control center._",
                    "",
                    "| Entity | Title | Kind | Copies | Reclaimable bytes |",
                    "|---|---|---|---:|---:|",
                )
            )
            lines.extend(
                f"| {item['entity'] or '—'} | {item['title'] or '—'} | {item['document_kind']} | {item['copy_count']} | {item['reclaimable_bytes']} |"
                for item in summaries
            )
        lines.extend(
            (
                "",
                "## Semantic duplicate groups (same text, different bytes — review only, not recyclable)",
                "",
            )
        )
        if not semantic_groups:
            lines.append("_No semantic duplicate groups._")
        else:
            lines.extend(
                (
                    "_Documents whose normalized text is identical but bytes differ "
                    "(re-encoded/watermarked/re-saved). Display-only; not eligible for recycle. "
                    "Full detail: `duplicates --include-semantic` and `semantic_duplicates.csv`._",
                    "",
                    "| Entity | Title | Kind | Members | Distinct byte hashes |",
                    "|---|---|---|---:|---:|",
                )
            )
            top_semantic = sorted(
                semantic_groups,
                key=lambda item: (-item["member_count"], item["title"]),
            )[:20]
            lines.extend(
                f"| {item['entities'][0] if item['entities'] else '—'} | {item['title'] or '—'} | {item['document_kind']} | {item['member_count']} | {item['distinct_byte_hashes']} |"
                for item in top_semantic
            )
        lines.extend(
            (
                "",
                "## Document kinds",
                "",
                "| Kind | Count |",
                "|---|---:|",
            )
        )
        lines.extend(f"| {kind} | {count} |" for kind, count in sorted(kinds.items()))
        lines.extend(
            (
                "",
                "## Full tables",
                "",
                f"- Documents CSV: `{documents_csv}`",
                f"- Locations CSV: `{locations_csv}`",
                f"- Exact duplicates CSV: `{duplicates_csv}`",
                f"- Semantic duplicates CSV: `{semantic_duplicates_csv}`",
                f"- Acquisition attempts CSV: `{acquisition_attempts_csv}`",
                f"- Duplicate cleanup audit CSV: `{duplicate_cleanup_events_csv}`",
                f"- Original and derived artifacts CSV: `{artifacts_csv}`",
                "",
            )
        )
        self._atomic_write(index_md, "\n".join(lines))
        emit(12, "wrote source catalog index")
        return {
            "artifacts_csv": artifacts_csv.resolve(),
            "documents_csv": documents_csv.resolve(),
            "locations_csv": locations_csv.resolve(),
            "duplicates_csv": duplicates_csv.resolve(),
            "semantic_duplicates_csv": semantic_duplicates_csv.resolve(),
            "acquisition_attempts_csv": acquisition_attempts_csv.resolve(),
            "duplicate_cleanup_events_csv": duplicate_cleanup_events_csv.resolve(),
            "index_md": index_md.resolve(),
        }

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        with atomic_output(path, mode="w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)

    @staticmethod
    def _write_csv(
        path: Path,
        rows: list[dict[str, Any]],
        *,
        fields: list[str] | None = None,
    ) -> None:
        output_fields = fields or (list(rows[0]) if rows else ["artifact_role"])
        with atomic_output(path, mode="w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=output_fields)
            writer.writeheader()
            writer.writerows(rows)


__all__ = ["SourceCatalog"]
