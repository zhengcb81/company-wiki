"""High-level source catalog API and human-readable index exports."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

from .models import CatalogConfig, ProcessingReport, ScanReport
from .acquisition_journal import AcquisitionJournal
from .llm_summarizer import summarize_catalog_with_llm
from .lock import CatalogOperationLock
from .normalizer import backfill_text_fingerprints, normalize_catalog
from .section_extractor import extract_sections_catalog
from .scanner import scan_catalog, v2_scan_shadow_from_snapshot
from .store import CatalogStore
from .reader import ReadOnlyCatalogReader
from .summarizer import summarize_catalog


_EXACT_DUPLICATE_PREFIX = "urn:company-wiki:duplicate:exact:sha256:"


def _exact_duplicate_group_id(document_id: str, source_id: str) -> str:
    digest = hashlib.sha256(f"{document_id}\0{source_id}".encode("utf-8")).hexdigest()
    return _EXACT_DUPLICATE_PREFIX + digest


def _utc_now() -> str:
    """UTC wall-clock stamp for bundle queries without an explicit ``now``."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SourceCatalog:
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
            # Follow the activation snapshot (GP-002) on REAL scans: v2 when
            # the runtime policy's v2_scan_shadow is on, v1 when no snapshot
            # exists.  A plain dry-run stays v1 unless the caller explicitly
            # requests v2 — a v2 DRY shadow is a gated FC-305 operation that
            # records zero-diff rounds, not an ordinary CLI diagnostic.
            v2_scan_shadow = (
                False
                if dry_run
                else v2_scan_shadow_from_snapshot(self.config.catalog_dir)
            )
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

    def normalize(
        self,
        *,
        limit: int | None = None,
        force: bool = False,
        progress: Callable[..., None] | None = None,
        should_stop: Callable[[], bool] | None = None,
        parser_timeout_seconds: float = 3600,
        parser_heartbeat_interval_seconds: float = 15,
        parser_result_max_bytes: int = 268_435_456,
        retry_limit: int = 3,
        retry_backoff_seconds: int = 900,
    ) -> ProcessingReport:
        with CatalogOperationLock(self.config.catalog_dir, operation="normalize"):
            return normalize_catalog(
                self.config,
                self.store,
                limit=limit,
                force=force,
                progress=progress,
                should_stop=should_stop,
                parser_timeout_seconds=parser_timeout_seconds,
                parser_heartbeat_interval_seconds=parser_heartbeat_interval_seconds,
                parser_result_max_bytes=parser_result_max_bytes,
                retry_limit=retry_limit,
                retry_backoff_seconds=retry_backoff_seconds,
            )

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

    def extract_sections(
        self,
        *,
        limit: int | None = None,
        document_id: str | None = None,
        document_kind: str | None = None,
        force: bool = False,
        progress: Callable[..., None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> ProcessingReport:
        with CatalogOperationLock(
            self.config.catalog_dir, operation="extract_sections"
        ):
            return extract_sections_catalog(
                self.config,
                self.store,
                limit=limit,
                document_id=document_id,
                document_kind=document_kind,
                force=force,
                progress=progress,
                should_stop=should_stop,
            )

    def summarize(
        self, *, limit: int | None = None, force: bool = False
    ) -> ProcessingReport:
        with CatalogOperationLock(self.config.catalog_dir, operation="summarize"):
            return summarize_catalog(self.config, self.store, limit=limit, force=force)

    def summarize_with_llm(
        self,
        *,
        limit: int,
        llm_client_factory,
        max_input_chars: int,
        max_output_tokens: int,
        retry_backoff_seconds: int = 3600,
        progress: Callable[..., None] | None = None,
    ) -> ProcessingReport:
        with CatalogOperationLock(self.config.catalog_dir, operation="summarize_llm"):
            return summarize_catalog_with_llm(
                self.config,
                self.store,
                limit=limit,
                llm_client_factory=llm_client_factory,
                max_input_chars=max_input_chars,
                max_output_tokens=max_output_tokens,
                retry_backoff_seconds=retry_backoff_seconds,
                progress=progress,
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
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """WU-3.2: SQL-pushdown filing-candidate lookup (F-021/F-026).

        Filters in SQL: document_kind, source_status allowlist, and (when
        given) reusable root_ids via locations. ``entity`` is OPTIONAL and,
        when given, narrows via exact document_entities/entities name match.
        The resolver deliberately passes neither entity nor root_ids: its
        per-document gates (entity anchoring, identity conflict before the
        reusable-root check) are the authority, and a contradictory-identity
        document must surface as IDENTITY_CONFLICT even when its root is not
        reusable (fail-closed, Phase 15.3). This narrows the candidate set
        from a full-table materialization to the kind/status slice while
        keeping resolver semantics unchanged.
        """
        if limit <= 0:
            raise ValueError("limit must be positive")
        if not document_kind or not source_statuses:
            raise ValueError("document_kind/source_statuses required")
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
        fiscal_clause = (
            "AND (json_extract(d.metadata_json, '$.acquisition.fiscal_year') = ?"
            " OR json_extract(d.metadata_json, '$.dayu_meta.fiscal_year') = ?)"
            if fiscal_year is not None
            else ""
        )
        fiscal_params: tuple[int, ...] = (
            (fiscal_year, fiscal_year) if fiscal_year is not None else ()
        )
        entity_rows = self.reader.fetchall(
            f"""SELECT d.document_id, d.primary_source_id, d.title, d.source_type,
                       d.document_kind, d.published_date, d.source_status,
                       d.metadata_json, d.first_seen_at, d.last_seen_at,
                       s.content_sha256, s.byte_size
                FROM documents d
                LEFT JOIN sources s ON s.source_id = d.primary_source_id
                WHERE d.document_kind = ?
                  AND d.source_status IN ({placeholders})
                  {entity_clause}
                  {root_clause}
                  {fiscal_clause}
                ORDER BY d.published_date DESC, d.title, d.document_id
                LIMIT ?
                """,
            (
                document_kind,
                *source_statuses,
                *entity_params,
                *root_params,
                *fiscal_params,
                limit,
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
            doc_locations = self._annotate_locations(
                document_id, locations.get(document_id, [])
            )
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
                    "metadata": json.loads(row["metadata_json"]),
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
            locations = self._annotate_locations(
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
                    "metadata": json.loads(document["metadata_json"]),
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
    def _annotate_locations(
        document_id: str,
        locations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        for location in locations:
            location.update(
                {
                    "is_canonical": False,
                    "duplicate_relation": "",
                    "duplicate_group_id": "",
                    "canonical_location_id": "",
                }
            )
        original_groups: dict[str, list[dict[str, Any]]] = {}
        for location in locations:
            if (
                location["role"] == "original_primary"
                and location["location_status"] == "active"
                and location["source_id"]
            ):
                original_groups.setdefault(location["source_id"], []).append(location)
        for source_id, group in original_groups.items():
            ordered = sorted(
                group,
                key=lambda item: (
                    int(item["root_priority"]),
                    item["root_id"],
                    item["relative_path"],
                    item["location_id"],
                ),
            )
            canonical = ordered[0]
            canonical["is_canonical"] = True
            canonical["canonical_location_id"] = canonical["location_id"]
            if len(ordered) <= 1:
                continue
            group_id = _exact_duplicate_group_id(document_id, source_id)
            canonical["duplicate_group_id"] = group_id
            for duplicate in ordered[1:]:
                duplicate["duplicate_relation"] = "exact_copy"
                duplicate["duplicate_group_id"] = group_id
                duplicate["canonical_location_id"] = canonical["location_id"]
        return locations

    @staticmethod
    def _duplicate_summary(locations: list[dict[str, Any]]) -> dict[str, Any]:
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
        temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
        try:
            temporary.write_text(text, encoding="utf-8", newline="\n")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _write_csv(
        path: Path,
        rows: list[dict[str, Any]],
        *,
        fields: list[str] | None = None,
    ) -> None:
        output_fields = fields or (list(rows[0]) if rows else ["artifact_role"])
        temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
        try:
            with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=output_fields)
                writer.writeheader()
                writer.writerows(rows)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


__all__ = ["SourceCatalog"]
