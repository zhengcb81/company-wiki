"""Logical storage for durable narrative bundles.

This module owns content-addressed bytes and a narrow additive catalog table.
It deliberately knows nothing about automation jobs, handlers, or physical data
lake locations outside the configured object-store root.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import tempfile
import uuid

from company_wiki._id_scope import normalize_id_scope

from .store import CatalogStore
from .reader import ReadOnlyCatalogReader


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_OBJECT_KEY = re.compile(r"objects/sha256/([0-9a-f]{2})/([0-9a-f]{64})\.json\Z")
_SELECTION_STATUSES = frozenset(
    {"selected", "partial", "skipped_no_narrative", "needs_review", "blocked"}
)
_QUALITY_STATUSES = frozenset(
    {"verified", "needs_review", "skipped_no_narrative"}
)
_LATEST_VISIBLE_SQL = """SELECT * FROM narrative_artifact_versions
    WHERE document_id=? AND source_id=? AND source_sha256=? AND status='visible'
    ORDER BY activated_at DESC, created_at DESC, artifact_version_id DESC LIMIT 1"""
_EXACT_VISIBLE_SQL = """SELECT * FROM narrative_artifact_versions
    WHERE artifact_version_id=? AND document_id=? AND source_id=?
      AND source_sha256=? AND status='visible'"""
_CURRENT_SOURCE_SQL = """SELECT d.primary_source_id, d.source_status, s.content_sha256
    FROM documents AS d LEFT JOIN sources AS s ON s.source_id=d.primary_source_id
    WHERE d.document_id=?"""
_CURRENT_ARTIFACT_SQL = """SELECT 1 FROM narrative_artifact_versions AS v
    JOIN documents AS d ON d.document_id=v.document_id
    JOIN sources AS s ON s.source_id=d.primary_source_id
    WHERE v.artifact_version_id=? AND v.status='visible'
      AND d.primary_source_id=? AND d.source_status='active' AND s.content_sha256=?"""


class NarrativeArtifactError(ValueError):
    """Base error for narrative artifact persistence."""


class NarrativeArtifactConflictError(NarrativeArtifactError):
    """A durable work/effect identity is already bound to different content."""


class NarrativeObjectIntegrityError(NarrativeArtifactError):
    """An object key or stored object does not match its content hash."""


class NarrativeSourceNotCurrentError(NarrativeArtifactError):
    """The requested source is not the document's current active primary."""


class NarrativeArtifactNotVisibleError(NarrativeArtifactError):
    """No visible artifact version is available for the exact source identity."""


@dataclass(frozen=True)
class NarrativeArtifactDraft:
    effect_id: str
    work_key: str
    document_id: str
    source_id: str
    source_sha256: str
    producer_name: str
    producer_version: str
    policy_sha256: str
    selection_status: str
    quality_status: str
    metadata_json: str
    created_at: str
    artifact_role: str = "narrative_bundle"

    def __post_init__(self) -> None:
        if self.artifact_role != "narrative_bundle":
            raise ValueError("artifact_role must be narrative_bundle")
        for name in (
            "effect_id", "document_id", "source_id", "producer_name",
            "producer_version", "created_at",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError(f"{name} must be non-empty trimmed text")
        if not _SHA256.fullmatch(self.work_key):
            raise ValueError("work_key must be lowercase SHA-256")
        if not _SHA256.fullmatch(self.source_sha256):
            raise ValueError("source_sha256 must be lowercase SHA-256")
        if not _SHA256.fullmatch(self.policy_sha256):
            raise ValueError("policy_sha256 must be lowercase SHA-256")
        if self.selection_status not in _SELECTION_STATUSES:
            raise ValueError("selection_status is invalid")
        if self.quality_status not in _QUALITY_STATUSES:
            raise ValueError("quality_status is invalid")
        try:
            metadata = json.loads(self.metadata_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("metadata_json must be valid JSON") from exc
        if not isinstance(metadata, dict):
            raise ValueError("metadata_json must encode an object")


@dataclass(frozen=True)
class NarrativeArtifactVersion:
    artifact_version_id: str
    work_key: str
    effect_id: str
    document_id: str
    source_id: str
    source_sha256: str
    artifact_role: str
    object_key: str
    content_sha256: str
    byte_size: int
    producer_name: str
    producer_version: str
    policy_sha256: str
    selection_status: str
    quality_status: str
    metadata_json: str
    status: str
    created_at: str
    activated_at: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "NarrativeArtifactVersion":
        return cls(**{key: row[key] for key in cls.__dataclass_fields__})


class LocalNarrativeObjectStore:
    """Persist immutable bytes under a hash-derived logical key."""

    def __init__(self, root: Path) -> None:
        if not isinstance(root, Path):
            raise TypeError("root must be pathlib.Path")
        self.root = root

    def put(self, data: bytes) -> str:
        if not isinstance(data, bytes):
            raise TypeError("narrative object data must be bytes")
        digest = hashlib.sha256(data).hexdigest()
        key = f"objects/sha256/{digest[:2]}/{digest}.json"
        target = self._physical_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            self._verify(target.read_bytes(), digest, len(data))
            return key

        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", delete=False, dir=target.parent,
                prefix=".narrative-", suffix=".partial",
            ) as temporary:
                temporary_name = temporary.name
                temporary.write(data)
                temporary.flush()
                os.fsync(temporary.fileno())
            try:
                # A hard link is an atomic create-if-absent operation. It avoids
                # replacing a concurrent or tampered object at the same key.
                os.link(temporary_name, target)
            except FileExistsError:
                self._verify(target.read_bytes(), digest, len(data))
            return key
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)

    def read(self, key: str, *, expected_sha256: str, expected_size: int) -> bytes:
        if not _SHA256.fullmatch(expected_sha256):
            raise NarrativeObjectIntegrityError("expected_sha256 is invalid")
        if type(expected_size) is not int or expected_size < 0:
            raise NarrativeObjectIntegrityError("expected_size is invalid")
        match = _OBJECT_KEY.fullmatch(key)
        if match is None or match.group(2) != expected_sha256:
            raise NarrativeObjectIntegrityError("object key does not match expected hash")
        target = self._physical_path(key)
        try:
            with target.open("rb") as stream:
                data = stream.read(expected_size + 1)
        except OSError as exc:
            raise NarrativeObjectIntegrityError("narrative object is unavailable") from exc
        self._verify(data, expected_sha256, expected_size)
        return data

    def _physical_path(self, key: str) -> Path:
        match = _OBJECT_KEY.fullmatch(key)
        if match is None or match.group(1) != match.group(2)[:2]:
            raise NarrativeObjectIntegrityError("object key is invalid")
        relative = Path(*PurePosixPath(key).parts)
        return self.root / relative

    @staticmethod
    def _verify(data: bytes, digest: str, size: int) -> None:
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise NarrativeObjectIntegrityError("stored narrative object failed verification")


class NarrativeArtifactStore:
    """Prepare idempotent bundle versions after writing their immutable bytes."""

    def __init__(self, catalog: CatalogStore, objects: LocalNarrativeObjectStore) -> None:
        if not isinstance(catalog, CatalogStore):
            raise TypeError("catalog must be CatalogStore")
        if not isinstance(objects, LocalNarrativeObjectStore):
            raise TypeError("objects must be LocalNarrativeObjectStore")
        self._catalog = catalog
        self._objects = objects

    @classmethod
    def for_reading(
        cls, database_path: Path, objects: LocalNarrativeObjectStore,
    ) -> "NarrativeArtifactReader":
        """Open an existing catalog without initialization or any writer surface."""
        return NarrativeArtifactReader(database_path, objects)

    @property
    def catalog_dir(self) -> Path:
        """Directory containing the catalog-wide operation lock."""
        return self._catalog.database_path.parent

    def prepare(self, draft: NarrativeArtifactDraft, payload: bytes) -> NarrativeArtifactVersion:
        if not isinstance(draft, NarrativeArtifactDraft):
            raise TypeError("draft must be NarrativeArtifactDraft")
        if not isinstance(payload, bytes):
            raise TypeError("payload must be bytes")

        content_sha256 = hashlib.sha256(payload).hexdigest()
        with self._catalog.transaction() as connection:
            self._require_source_identity(
                connection, draft.document_id, draft.source_id, draft.source_sha256
            )
            existing = self._existing(connection, draft, content_sha256)
            if existing is not None:
                return existing

        # Bytes are durable before the short catalog transaction. If that
        # transaction fails, the next attempt reuses this content-addressed
        # object; no catalog lock is held while the filesystem is written.
        object_key = self._objects.put(payload)
        with self._catalog.transaction() as connection:
            self._require_source_identity(
                connection, draft.document_id, draft.source_id, draft.source_sha256
            )
            existing = self._existing(connection, draft, content_sha256)
            if existing is not None:
                return existing

            version = NarrativeArtifactVersion(
                artifact_version_id=f"narrative-{uuid.uuid4().hex}",
                work_key=draft.work_key,
                effect_id=draft.effect_id,
                document_id=draft.document_id,
                source_id=draft.source_id,
                source_sha256=draft.source_sha256,
                artifact_role=draft.artifact_role,
                object_key=object_key,
                content_sha256=content_sha256,
                byte_size=len(payload),
                producer_name=draft.producer_name,
                producer_version=draft.producer_version,
                policy_sha256=draft.policy_sha256,
                selection_status=draft.selection_status,
                quality_status=draft.quality_status,
                metadata_json=draft.metadata_json,
                status="prepared",
                created_at=draft.created_at,
                activated_at=None,
            )
            connection.execute(
                """INSERT INTO narrative_artifact_versions (
                    artifact_version_id, work_key, effect_id, document_id,
                    source_id, source_sha256, artifact_role, object_key,
                    content_sha256, byte_size,
                    producer_name, producer_version, policy_sha256, selection_status,
                    quality_status, metadata_json, status, created_at, activated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                tuple(getattr(version, field) for field in version.__dataclass_fields__),
            )
            return version

    def _existing(
        self,
        connection: sqlite3.Connection,
        draft: NarrativeArtifactDraft,
        content_sha256: str,
    ) -> NarrativeArtifactVersion | None:
        row = connection.execute(
            """SELECT * FROM narrative_artifact_versions
               WHERE work_key=? OR effect_id=?""",
            (draft.work_key, draft.effect_id),
        ).fetchone()
        if row is None:
            return None
        matches = (
            row["work_key"] == draft.work_key
            and row["effect_id"] == draft.effect_id
            and row["document_id"] == draft.document_id
            and row["source_id"] == draft.source_id
            and row["source_sha256"] == draft.source_sha256
            and row["artifact_role"] == draft.artifact_role
            and row["content_sha256"] == content_sha256
            and row["producer_name"] == draft.producer_name
            and row["producer_version"] == draft.producer_version
            and row["policy_sha256"] == draft.policy_sha256
            and row["selection_status"] == draft.selection_status
            and row["quality_status"] == draft.quality_status
            and row["metadata_json"] == draft.metadata_json
        )
        if not matches or row["status"] not in {"prepared", "visible"}:
            raise NarrativeArtifactConflictError(
                "work/effect identity is already bound to different content"
            )
        version = NarrativeArtifactVersion.from_row(row)
        self._objects.read(
            version.object_key,
            expected_sha256=version.content_sha256,
            expected_size=version.byte_size,
        )
        return version

    @staticmethod
    def _require_source_identity(
        connection: sqlite3.Connection,
        document_id: str,
        source_id: str,
        source_sha256: str,
    ) -> None:
        source = connection.execute(
            """SELECT d.primary_source_id, d.source_status, s.content_sha256
               FROM documents AS d
               LEFT JOIN sources AS s ON s.source_id=d.primary_source_id
               WHERE d.document_id=?""",
            (document_id,),
        ).fetchone()
        if (
            source is None
            or source["primary_source_id"] != source_id
            or source["content_sha256"] != source_sha256
            or source["source_status"] != "active"
        ):
            raise NarrativeSourceNotCurrentError(
                "source is not the active primary for this document"
            )

    def activate(
        self,
        effect_id: str,
        *,
        verified_after_hash: str,
        activated_at: str,
    ) -> NarrativeArtifactVersion:
        if not isinstance(effect_id, str) or not effect_id:
            raise ValueError("effect_id must be non-empty")
        if not _SHA256.fullmatch(verified_after_hash):
            raise ValueError("verified_after_hash must be lowercase SHA-256")
        if not isinstance(activated_at, str) or not activated_at:
            raise ValueError("activated_at must be non-empty")

        with self._catalog.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM narrative_artifact_versions WHERE effect_id=?",
                (effect_id,),
            ).fetchone()
            if row is None:
                raise NarrativeArtifactNotVisibleError("prepared artifact not found")
            if row["content_sha256"] != verified_after_hash:
                raise NarrativeArtifactConflictError(
                    "verified effect hash differs from prepared bundle"
                )
            self._require_current_source(connection, row)
            if row["status"] == "visible":
                return NarrativeArtifactVersion.from_row(row)
            if row["status"] != "prepared":
                raise NarrativeArtifactNotVisibleError(
                    f"artifact cannot activate from {row['status']!r}"
                )
            changed = connection.execute(
                """UPDATE narrative_artifact_versions
                   SET status='visible', activated_at=?
                   WHERE effect_id=? AND status='prepared' AND content_sha256=?""",
                (activated_at, effect_id, verified_after_hash),
            )
            if changed.rowcount != 1:
                raise NarrativeArtifactConflictError(
                    "prepared artifact changed during activation"
                )
            activated = connection.execute(
                "SELECT * FROM narrative_artifact_versions WHERE effect_id=?",
                (effect_id,),
            ).fetchone()
            return NarrativeArtifactVersion.from_row(activated)

    def prepared_effects(
        self, *, limit: int = 100, allowed_effect_ids: tuple[str, ...] | None = None,
    ) -> tuple[NarrativeArtifactVersion, ...]:
        if type(limit) is not int or limit < 1:
            raise ValueError("limit must be a positive integer")
        allowed_effect_ids = normalize_id_scope(allowed_effect_ids, name="allowed_effect_ids")
        if allowed_effect_ids == ():
            return ()
        scope_sql = ""
        parameters: tuple[object, ...] = ()
        if allowed_effect_ids is not None:
            scope_sql = "AND effect_id IN (" + ",".join("?" for _ in allowed_effect_ids) + ") "
            parameters = allowed_effect_ids
        with self._catalog.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM narrative_artifact_versions WHERE status='prepared' "
                f"{scope_sql}"
                "ORDER BY created_at, artifact_version_id LIMIT ?",
                parameters + (limit,),
            ).fetchall()
            return tuple(NarrativeArtifactVersion.from_row(row) for row in rows)

    def read_visible(
        self,
        *,
        document_id: str,
        source_id: str,
        source_sha256: str,
    ) -> tuple[NarrativeArtifactVersion, bytes]:
        version = self.latest_visible_version(
            document_id=document_id, source_id=source_id, source_sha256=source_sha256,
        )
        return version, self._read_current_payload(version)

    def latest_visible_version(
        self,
        *,
        document_id: str,
        source_id: str,
        source_sha256: str,
    ) -> NarrativeArtifactVersion:
        """Discover a logical reference without reading artifact or source bytes."""
        if not _SHA256.fullmatch(source_sha256):
            raise ValueError("source_sha256 must be lowercase SHA-256")
        with self._catalog.transaction() as connection:
            row = connection.execute(
                _LATEST_VISIBLE_SQL,
                (document_id, source_id, source_sha256),
            ).fetchone()
            if row is None:
                raise NarrativeArtifactNotVisibleError(
                    "no visible artifact for the requested source"
                )
            self._require_current_source(connection, row)
            return NarrativeArtifactVersion.from_row(row)

    def read_exact(
        self,
        *,
        artifact_version_id: str,
        document_id: str,
        source_id: str,
        source_sha256: str,
        expected_sha256: str | None = None,
        expected_size: int | None = None,
    ) -> tuple[NarrativeArtifactVersion, bytes]:
        """Read the referenced version, even when a newer summary is visible."""
        if not isinstance(artifact_version_id, str) or not artifact_version_id.strip():
            raise ValueError("artifact_version_id must be non-empty text")
        if not _SHA256.fullmatch(source_sha256):
            raise ValueError("source_sha256 must be lowercase SHA-256")
        with self._catalog.transaction() as connection:
            row = connection.execute(
                _EXACT_VISIBLE_SQL,
                (artifact_version_id, document_id, source_id, source_sha256),
            ).fetchone()
            if row is None:
                raise NarrativeArtifactNotVisibleError(
                    "the exact narrative artifact is not visible"
                )
            self._require_current_source(connection, row)
            version = NarrativeArtifactVersion.from_row(row)
            if (
                expected_sha256 is not None and version.content_sha256 != expected_sha256
            ) or (expected_size is not None and version.byte_size != expected_size):
                raise NarrativeArtifactConflictError(
                    "exact artifact metadata differs from its reference"
                )
        return version, self._read_current_payload(version)

    def _read_current_payload(self, version: NarrativeArtifactVersion) -> bytes:
        payload = self._objects.read(
            version.object_key,
            expected_sha256=version.content_sha256,
            expected_size=version.byte_size,
        )
        with self._catalog.transaction() as connection:
            still_current = connection.execute(
                _CURRENT_ARTIFACT_SQL,
                (version.artifact_version_id, version.source_id, version.source_sha256),
            ).fetchone()
            if still_current is None:
                raise NarrativeSourceNotCurrentError(
                    "source changed while reading the narrative artifact"
                )
        return payload

    @staticmethod
    def _require_current_source(
        connection: sqlite3.Connection, row: sqlite3.Row
    ) -> None:
        source = connection.execute(
            _CURRENT_SOURCE_SQL,
            (row["document_id"],),
        ).fetchone()
        _require_current_identity(row, source)


def _require_current_identity(row: sqlite3.Row, source: sqlite3.Row | None) -> None:
    if (
        source is None
        or source["primary_source_id"] != row["source_id"]
        or source["content_sha256"] != row["source_sha256"]
        or source["source_status"] != "active"
    ):
        raise NarrativeSourceNotCurrentError(
            "artifact source is no longer the active primary"
        )


class NarrativeArtifactReader:
    """Narrow read facade; it cannot create, migrate, prepare or publish artifacts."""

    def __init__(self, database_path: Path, objects: LocalNarrativeObjectStore) -> None:
        self._reader = ReadOnlyCatalogReader(database_path)
        self._objects = objects

    def close(self) -> None:
        self._reader.close()

    def _version(self, sql: str, params: tuple[str, ...]) -> NarrativeArtifactVersion:
        row = self._reader.fetchone(sql, params)
        if row is None:
            raise NarrativeArtifactNotVisibleError("the narrative artifact is not visible")
        source = self._reader.fetchone(_CURRENT_SOURCE_SQL, (row["document_id"],))
        _require_current_identity(row, source)
        return NarrativeArtifactVersion.from_row(row)

    def latest_visible_version(
        self, *, document_id: str, source_id: str, source_sha256: str,
    ) -> NarrativeArtifactVersion:
        if not _SHA256.fullmatch(source_sha256):
            raise ValueError("source_sha256 must be lowercase SHA-256")
        return self._version(_LATEST_VISIBLE_SQL, (document_id, source_id, source_sha256))

    def read_exact(
        self, *, artifact_version_id: str, document_id: str, source_id: str,
        source_sha256: str, expected_sha256: str | None = None,
        expected_size: int | None = None,
    ) -> tuple[NarrativeArtifactVersion, bytes]:
        if not isinstance(artifact_version_id, str) or not artifact_version_id.strip():
            raise ValueError("artifact_version_id must be non-empty text")
        if not _SHA256.fullmatch(source_sha256):
            raise ValueError("source_sha256 must be lowercase SHA-256")
        version = self._version(
            _EXACT_VISIBLE_SQL, (artifact_version_id, document_id, source_id, source_sha256),
        )
        if (expected_sha256 is not None and version.content_sha256 != expected_sha256) or (
            expected_size is not None and version.byte_size != expected_size
        ):
            raise NarrativeArtifactConflictError("exact artifact differs from its reference")
        data = self._objects.read(
            version.object_key, expected_sha256=version.content_sha256,
            expected_size=version.byte_size,
        )
        if self._reader.fetchone(
            _CURRENT_ARTIFACT_SQL, (artifact_version_id, source_id, source_sha256),
        ) is None:
            raise NarrativeSourceNotCurrentError("source changed while reading the artifact")
        return version, data


__all__ = [
    "LocalNarrativeObjectStore",
    "NarrativeArtifactConflictError",
    "NarrativeArtifactDraft",
    "NarrativeArtifactError",
    "NarrativeArtifactNotVisibleError",
    "NarrativeArtifactStore",
    "NarrativeArtifactReader",
    "NarrativeArtifactVersion",
    "NarrativeObjectIntegrityError",
    "NarrativeSourceNotCurrentError",
]
