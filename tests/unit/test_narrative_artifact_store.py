"""Contracts for narrative content-addressed storage and its narrow catalog table."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
from pathlib import Path
import sqlite3

import pytest

from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore,
    NarrativeArtifactConflictError,
    NarrativeArtifactDraft,
    NarrativeArtifactStore,
    NarrativeArtifactNotVisibleError,
    NarrativeObjectIntegrityError,
    NarrativeSourceNotCurrentError,
)
from company_wiki.source_catalog.store import CatalogStore


SOURCE_SHA = hashlib.sha256(b"raw-source").hexdigest()
OTHER_SOURCE_SHA = hashlib.sha256(b"other-raw-source").hexdigest()
POLICY_SHA = hashlib.sha256(b"read-policy").hexdigest()
WORK_KEY = hashlib.sha256(b"work-key").hexdigest()
T0 = "2026-09-29T10:00:00Z"


def _catalog(tmp_path: Path) -> CatalogStore:
    catalog = CatalogStore(tmp_path / "catalog.sqlite3")
    with catalog.transaction() as connection:
        connection.execute(
            "INSERT INTO sources "
            "(source_id, content_sha256, byte_size, mime_type, first_seen_at) "
            "VALUES (?,?,?,?,?)",
            ("source-1", SOURCE_SHA, 10, "text/plain", T0),
        )
        connection.execute(
            "INSERT INTO sources "
            "(source_id, content_sha256, byte_size, mime_type, first_seen_at) "
            "VALUES (?,?,?,?,?)",
            ("source-2", OTHER_SOURCE_SHA, 16, "text/plain", T0),
        )
        connection.execute(
            "INSERT INTO documents "
            "(document_id, primary_source_id, title, source_type, document_kind, "
            "published_date, source_status, metadata_priority, metadata_json, "
            "text_fingerprint, first_seen_at, last_seen_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "document-1",
                "source-1",
                "Example source",
                "file",
                "investor_call_transcript",
                None,
                "active",
                10,
                "{}",
                None,
                T0,
                T0,
            ),
        )
    return catalog


def _draft(*, source_id: str = "source-1", source_sha256: str = SOURCE_SHA) -> NarrativeArtifactDraft:
    return NarrativeArtifactDraft(
        effect_id="effect-1",
        work_key=WORK_KEY,
        document_id="document-1",
        source_id=source_id,
        source_sha256=source_sha256,
        producer_name="company_wiki.narrative_bundle",
        producer_version="2.0",
        policy_sha256=POLICY_SHA,
        selection_status="selected",
        quality_status="verified",
        metadata_json='{"summary_status":"completed"}',
        created_at=T0,
    )


def _count_versions(catalog: CatalogStore) -> int:
    with catalog.transaction() as connection:
        return int(
            connection.execute(
                "SELECT COUNT(*) FROM narrative_artifact_versions"
            ).fetchone()[0]
        )


def test_catalog_schema_is_additive_and_has_no_physical_path_column(
    tmp_path: Path,
) -> None:
    database = tmp_path / "catalog.sqlite3"
    catalog = CatalogStore(database)
    with catalog.transaction() as connection:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(narrative_artifact_versions)"
            )
        }
        assert {
            "artifact_version_id",
            "work_key",
            "effect_id",
            "document_id",
            "source_id",
            "source_sha256",
            "artifact_role",
            "object_key",
            "content_sha256",
            "byte_size",
            "producer_name",
            "producer_version",
            "policy_sha256",
            "selection_status",
            "quality_status",
            "metadata_json",
            "status",
            "created_at",
            "activated_at",
        } <= columns
        assert "path" not in columns
        connection.execute(
            "INSERT INTO sources "
            "(source_id, content_sha256, byte_size, mime_type, first_seen_at) "
            "VALUES (?,?,?,?,?)",
            ("legacy-source", SOURCE_SHA, 10, "text/plain", T0),
        )

    reopened = CatalogStore(database)
    with reopened.transaction() as connection:
        assert connection.execute(
            "SELECT value FROM catalog_meta WHERE key='schema_version'"
        ).fetchone() is not None
        assert connection.execute(
            "SELECT content_sha256 FROM sources WHERE source_id='legacy-source'"
        ).fetchone()[0] == SOURCE_SHA


def test_local_object_store_returns_logical_key_and_checks_existing_bytes(
    tmp_path: Path,
) -> None:
    root = tmp_path / ".source_catalog"
    objects = LocalNarrativeObjectStore(root)
    data = b'{"schema_version":"narrative-bundle/2.0"}'
    digest = hashlib.sha256(data).hexdigest()

    key = objects.put(data)

    assert key == f"objects/sha256/{digest[:2]}/{digest}.json"
    assert not Path(key).is_absolute()
    assert str(root) not in key
    assert objects.put(data) == key
    assert objects.read(
        key, expected_sha256=digest, expected_size=len(data)
    ) == data

    physical_object = root / Path(key)
    physical_object.write_bytes(b"tampered")
    with pytest.raises(NarrativeObjectIntegrityError):
        objects.put(data)
    assert physical_object.read_bytes() == b"tampered"


def test_prepare_is_idempotent_after_object_write_and_catalog_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalog = _catalog(tmp_path)
    objects = LocalNarrativeObjectStore(tmp_path / ".source_catalog")
    artifacts = NarrativeArtifactStore(catalog, objects)
    payload = b'{"schema_version":"narrative-bundle/2.0","version":1}'
    original_transaction = catalog.transaction
    calls = 0

    def fail_once():
        nonlocal calls
        calls += 1
        if calls == 2:
            @contextmanager
            def broken_transaction():
                raise sqlite3.OperationalError("simulated catalog outage")
                yield
            return broken_transaction()
        return original_transaction()

    monkeypatch.setattr(catalog, "transaction", fail_once)
    with pytest.raises(sqlite3.OperationalError):
        artifacts.prepare(_draft(), payload)
    monkeypatch.setattr(catalog, "transaction", original_transaction)
    assert _count_versions(catalog) == 0
    digest = hashlib.sha256(payload).hexdigest()
    orphan_key = f"objects/sha256/{digest[:2]}/{digest}.json"
    assert objects.read(
        orphan_key, expected_sha256=digest, expected_size=len(payload)
    ) == payload
    first = artifacts.prepare(_draft(), payload)
    second = artifacts.prepare(_draft(), payload)

    assert first.status == "prepared"
    assert second == first
    assert first.object_key == (
        f"objects/sha256/{first.content_sha256[:2]}/{first.content_sha256}.json"
    )
    assert _count_versions(catalog) == 1
    assert objects.read(
        first.object_key,
        expected_sha256=first.content_sha256,
        expected_size=first.byte_size,
    ) == payload

def test_same_work_key_with_different_bundle_hash_fails_closed(
    tmp_path: Path,
) -> None:
    catalog = _catalog(tmp_path)
    artifacts = NarrativeArtifactStore(
        catalog, LocalNarrativeObjectStore(tmp_path / ".source_catalog")
    )
    artifacts.prepare(_draft(), b'{"bundle":1}')

    with pytest.raises(NarrativeArtifactConflictError):
        artifacts.prepare(_draft(), b'{"bundle":2}')

    assert _count_versions(catalog) == 1


def test_prepare_rejects_a_source_that_is_not_current_primary(
    tmp_path: Path,
) -> None:
    catalog = _catalog(tmp_path)
    with catalog.transaction() as connection:
        connection.execute(
            "UPDATE documents SET primary_source_id='source-2' "
            "WHERE document_id='document-1'"
        )
    artifacts = NarrativeArtifactStore(
        catalog, LocalNarrativeObjectStore(tmp_path / ".source_catalog")
    )

    with pytest.raises(NarrativeSourceNotCurrentError):
        artifacts.prepare(_draft(), b'{"bundle":1}')

    assert _count_versions(catalog) == 0


def test_artifact_is_readable_only_after_hash_matched_activation(
    tmp_path: Path,
) -> None:
    catalog = _catalog(tmp_path)
    objects = LocalNarrativeObjectStore(tmp_path / ".source_catalog")
    artifacts = NarrativeArtifactStore(catalog, objects)
    payload = b'{"bundle":"verified"}'
    prepared = artifacts.prepare(_draft(), payload)

    with pytest.raises(NarrativeArtifactNotVisibleError):
        artifacts.read_visible(
            document_id="document-1",
            source_id="source-1",
            source_sha256=SOURCE_SHA,
        )
    with pytest.raises(NarrativeArtifactConflictError):
        artifacts.activate(
            prepared.effect_id,
            verified_after_hash=hashlib.sha256(b"wrong").hexdigest(),
            activated_at="2026-09-29T10:01:00Z",
        )

    visible = artifacts.activate(
        prepared.effect_id,
        verified_after_hash=prepared.content_sha256,
        activated_at="2026-09-29T10:01:00Z",
    )
    loaded_version, loaded_bytes = artifacts.read_visible(
        document_id="document-1",
        source_id="source-1",
        source_sha256=SOURCE_SHA,
    )

    assert visible.status == "visible"
    assert loaded_version == visible
    assert loaded_bytes == payload


def test_activation_and_read_refuse_a_replaced_primary_source(
    tmp_path: Path,
) -> None:
    catalog = _catalog(tmp_path)
    artifacts = NarrativeArtifactStore(
        catalog, LocalNarrativeObjectStore(tmp_path / ".source_catalog")
    )
    prepared = artifacts.prepare(_draft(), b'{"bundle":1}')
    with catalog.transaction() as connection:
        connection.execute(
            "UPDATE documents SET primary_source_id='source-2' "
            "WHERE document_id='document-1'"
        )

    with pytest.raises(NarrativeSourceNotCurrentError):
        artifacts.activate(
            prepared.effect_id,
            verified_after_hash=prepared.content_sha256,
            activated_at="2026-09-29T10:01:00Z",
        )
    with pytest.raises(NarrativeArtifactNotVisibleError):
        artifacts.read_visible(
            document_id="document-1",
            source_id="source-1",
            source_sha256=SOURCE_SHA,
        )
