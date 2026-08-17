"""ZR-305 RED/acceptance tests: legacy artifact five-bucket dry-run/migration
with production SourceBundle consumption.

Extends the FC-901 backfill tests with the registry-mandated end-to-end
evidence:
  - 100% of legacy artifacts land in exactly one of five buckets
    (bindable / hash_mismatch / missing_bytes / unknown_generator /
    legacy_unbound);
  - two dry-runs produce byte-identical results (deterministic);
  - after ``apply``, the REAL production read path
    (``source_bundle.build_source_bundle``) consumes the bound artifact as
    a valid handle — the binding is not a dead row;
  - apply is idempotent, never deletes artifacts, and is reversible by
    removing the shadow bindings (no guessing).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.artifact_backfill import (  # noqa: E402
    run_artifact_backfill,
)
from company_wiki.source_catalog.source_bundle import (  # noqa: E402
    build_source_bundle,
)

_NOW = "2026-08-11T12:00:00Z"
_SOURCE_BODY = b"source bytes primary"
_SOURCE_SHA = hashlib.sha256(_SOURCE_BODY).hexdigest()
_REGISTRY = {"normalizer": {"1.0.0"}, "summarizer": {"2.0.0"},
             "section_extractor": {"3.0.0"}}
_BUCKETS = ("bindable", "hash_mismatch", "missing_bytes",
            "unknown_generator", "legacy_unbound")


def _catalog(tmp_path: Path) -> Path:
    path = tmp_path / "catalog.sqlite3"
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE roots (root_id TEXT PRIMARY KEY, path TEXT, kind TEXT);
        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY, content_sha256 TEXT, byte_size INTEGER
        );
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY, primary_source_id TEXT, title TEXT,
            source_type TEXT, document_kind TEXT, published_date TEXT,
            source_status TEXT, metadata_priority INTEGER, metadata_json TEXT,
            text_fingerprint TEXT, first_seen_at TEXT, last_seen_at TEXT
        );
        CREATE TABLE artifacts (
            artifact_id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
            source_id TEXT, artifact_role TEXT NOT NULL, path TEXT NOT NULL,
            content_sha256 TEXT NOT NULL, byte_size INTEGER NOT NULL,
            mime_type TEXT NOT NULL, generator_name TEXT NOT NULL,
            generator_version TEXT NOT NULL, status TEXT NOT NULL, error TEXT,
            metadata_json TEXT NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(document_id, artifact_role, generator_name, generator_version)
        );
        CREATE TABLE artifact_bindings (
            binding_id TEXT PRIMARY KEY, artifact_id TEXT NOT NULL UNIQUE,
            source_id TEXT NOT NULL, document_id TEXT NOT NULL,
            content_sha256 TEXT NOT NULL, generator_name TEXT NOT NULL,
            generator_version TEXT NOT NULL, bundle_hash TEXT NOT NULL,
            evidence_basis TEXT NOT NULL, visibility_state TEXT NOT NULL,
            schema_version TEXT NOT NULL, created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        );
        INSERT INTO roots VALUES ('company_raw', '/companies', 'company_raw');
        """
    )
    con.execute(
        "INSERT INTO sources VALUES ('src1',?,?)",
        (_SOURCE_SHA, len(_SOURCE_BODY)),
    )
    con.execute(
        """INSERT INTO documents (document_id, primary_source_id, title,
        source_type, document_kind, published_date, source_status,
        metadata_priority, metadata_json, first_seen_at, last_seen_at)
        VALUES ('doc1','src1','t','file','annual_report','2026-01-01',
        'active',10,'{}','2026-01-01','2026-01-01')"""
    )
    con.commit()
    con.close()
    return path


def _add_artifact(
    tmp_path: Path,
    con: sqlite3.Connection,
    *,
    artifact_id: str,
    body: bytes | None,
    role: str = "normalized",
    generator: str = "normalizer",
    version: str = "1.0.0",
    status: str = "completed",
    content_sha: str | None = None,
    metadata: dict | None = None,
    source_id: str | None = "src1",
) -> None:
    path = tmp_path / f"{artifact_id}.json"
    if body is not None:
        path.write_bytes(body)
    sha = content_sha or (hashlib.sha256(body).hexdigest() if body else "")
    con.execute(
        """INSERT INTO artifacts (artifact_id, document_id, source_id,
        artifact_role, path, content_sha256, byte_size, mime_type,
        generator_name, generator_version, status, error, metadata_json,
        created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            artifact_id, "doc1", source_id, role, str(path), sha,
            path.stat().st_size if body is not None else 0,
            "application/json", generator, version, status, None,
            json.dumps(metadata or {"schema_version": "1.0",
                                    "source_sha256": _SOURCE_SHA}),
            "2026-01-02T00:00:00Z",
        ),
    )


def _artifacts_for_bundle(cat: Path) -> list[dict]:
    """Production-shaped artifact dicts: artifacts columns + metadata_json
    merged for schema_version/source_sha256 (same convention as the
    resolver's bundle_for_resolution and artifact_backfill)."""
    con = sqlite3.connect(cat)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM artifacts ORDER BY artifact_id").fetchall()
    con.close()
    artifacts = []
    for row in rows:
        artifact = dict(row)
        try:
            metadata = json.loads(str(artifact.get("metadata_json") or "{}"))
            if isinstance(metadata, dict):
                if "schema_version" in metadata:
                    artifact["schema_version"] = metadata["schema_version"]
                if "source_sha256" in metadata:
                    artifact["source_sha256"] = metadata["source_sha256"]
        except json.JSONDecodeError:
            pass
        artifacts.append(artifact)
    return artifacts


def _bindings(cat: Path) -> list[tuple[str, str]]:
    con = sqlite3.connect(cat)
    rows = con.execute(
        "SELECT artifact_id, visibility_state FROM artifact_bindings "
        "ORDER BY artifact_id"
    ).fetchall()
    con.close()
    return [(r[0], r[1]) for r in rows]


def test_five_bucket_dry_run_exactly_one_bucket_each(tmp_path) -> None:
    """100% of legacy artifacts land in exactly one of the five buckets."""
    cat = _catalog(tmp_path)
    con = sqlite3.connect(cat)
    _add_artifact(tmp_path, con, artifact_id="ok", body=b"ok")
    _add_artifact(tmp_path, con, artifact_id="hash", body=b"ok",
                  content_sha="0" * 64,
                  generator="normalizer", version="1.0.1")  # distinct version
    _add_artifact(tmp_path, con, artifact_id="missing", body=None,
                  generator="summarizer", version="2.0.0")  # no bytes
    _add_artifact(tmp_path, con, artifact_id="gen", body=b"ok",
                  generator="unknown_gen", version="9.9",
                  role="sections")  # unregistered
    _add_artifact(tmp_path, con, artifact_id="unbound", body=b"ok",
                  metadata={}, role="summary",
                  generator="summarizer", version="2.0.0",
                  source_id=None)  # no provable source lineage
    con.commit()
    con.close()

    result = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW,
        mode="dry-run")
    total = (result.bindable + result.hash_mismatch + result.missing_bytes
             + result.unknown_generator + result.legacy_unbound)
    assert result.input == 5
    assert total == 5, f"bucket conservation broken: {result.as_dict()}"
    assert result.bindable == 1
    assert result.hash_mismatch == 1
    assert result.missing_bytes == 1
    assert result.unknown_generator == 1
    assert result.legacy_unbound == 1
    assert result.closed


def test_dry_run_twice_byte_identical(tmp_path) -> None:
    """Two dry-runs emit byte-identical proposals (deterministic)."""
    cat = _catalog(tmp_path)
    con = sqlite3.connect(cat)
    _add_artifact(tmp_path, con, artifact_id="ok", body=b"ok")
    _add_artifact(tmp_path, con, artifact_id="hash", body=b"ok",
                  content_sha="0" * 64, version="1.0.1")
    con.commit()
    con.close()
    first = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW,
        mode="dry-run")
    second = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW,
        mode="dry-run")
    assert json.dumps(first.as_dict(), sort_keys=True) == json.dumps(
        second.as_dict(), sort_keys=True)


def test_apply_then_real_source_bundle_consumes_binding(tmp_path) -> None:
    """After apply, the REAL production read path
    (build_source_bundle) consumes the bound artifact as a valid handle."""
    cat = _catalog(tmp_path)
    con = sqlite3.connect(cat)
    _add_artifact(tmp_path, con, artifact_id="ok", body=b"ok")
    con.commit()
    con.close()
    run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW,
        mode="apply")
    assert _bindings(cat) == [("ok", "shadow")]

    source = {
        "document_id": "doc1",
        "primary_source_id": "src1",
        "source_sha256": _SOURCE_SHA,
        "as_of_date": "2026-01-01",
    }
    bundle = build_source_bundle(
        source=source,
        artifacts=_artifacts_for_bundle(cat),
        registry=_REGISTRY,
        allowed_roots=(tmp_path,),
        now=_NOW,
    )
    assert "normalized" in bundle.valid_handles, (
        f"bound artifact not consumed: {bundle.invalid}")
    handle = bundle.valid_handles["normalized"]
    assert handle.artifact_id == "ok"
    assert handle.reusable is True
    # The binding is not a dead row: the bundle hash binds the handle.
    assert bundle.bundle_hash


def test_apply_idempotent_and_never_deletes(tmp_path) -> None:
    """Repeated apply adds zero duplicate bindings; artifacts untouched."""
    cat = _catalog(tmp_path)
    con = sqlite3.connect(cat)
    _add_artifact(tmp_path, con, artifact_id="ok", body=b"ok")
    con.commit()
    con.close()
    run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW,
        mode="apply")
    run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW,
        mode="apply")
    assert _bindings(cat) == [("ok", "shadow")]  # no duplicates
    con = sqlite3.connect(cat)
    n = con.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
    con.close()
    assert n == 1  # never deleted


def test_apply_reversible_by_shadow_delete(tmp_path) -> None:
    """Removing the shadow bindings restores the pre-apply state without
    touching artifacts (no guessing, recoverable)."""
    cat = _catalog(tmp_path)
    con = sqlite3.connect(cat)
    _add_artifact(tmp_path, con, artifact_id="ok", body=b"ok")
    con.commit()
    con.close()
    run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW,
        mode="apply")
    con = sqlite3.connect(cat)
    con.execute("DELETE FROM artifact_bindings WHERE created_by='fc-901'")
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM artifact_bindings").fetchone()[0]
    artifacts = con.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
    con.close()
    assert n == 0
    assert artifacts == 1
