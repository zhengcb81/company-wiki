"""FC-901 RED tests: legacy artifact binding migration (dry-run bucketing).

Reuses the WU-5.1 ``validate_artifact`` gate as the single source of truth for
"bindable". Each legacy artifact is classified into exactly one of five buckets;
an authorized apply writes shadow source-bindings for the bindable subset only.
The legacy ``artifacts`` table is never mutated or deleted.

Mutations guarded:
  MIG-01  dry-run must leave the catalog byte/row counts unchanged AND emit a
          complete proposal (per-bucket counts + capacity + per-bindable binding)
  MIG-03  re-running a completed migration is idempotent (identical result hash)
          and apply creates zero duplicate bindings
  MIG-05  unprovable provenance -> legacy_unbound; bindings are never guessed

Acceptance (task_plan FC-901):
  - input == bindable + hash_mismatch + missing_bytes + unknown_generator
            + legacy_unbound  (exactly one bucket per artifact; MIG-01 closure)
  - bindable ONLY when source/document/content/generator/schema are all provable
  - dry-run = zero writes; apply = shadow inserts into artifact_bindings, zero
    deletions, reversible

RED phase: the module ``artifact_backfill`` does not exist (ImportError).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.artifact_backfill import (  # noqa: E402
    ArtifactBackfillResult,
    run_artifact_backfill,
)

_NOW = "2026-08-11T12:00:00Z"
_SOURCE_BODY = b"source bytes primary"
_SOURCE_SHA = hashlib.sha256(_SOURCE_BODY).hexdigest()
_REGISTRY = {"normalizer": {"1.0.0"}, "summarizer": {"2.0.0"},
             "section_extractor": {"3.0.0"}}


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
    con.commit()
    con.close()
    return path


def _add_source(con: sqlite3.Connection, source_id: str = "src1") -> None:
    con.execute(
        "INSERT OR REPLACE INTO sources VALUES (?,?,?)",
        (source_id, _SOURCE_SHA, len(_SOURCE_BODY)),
    )


def _add_doc(con: sqlite3.Connection, *, doc_id: str = "doc1",
             source_id: str = "src1") -> None:
    con.execute(
        """INSERT OR REPLACE INTO documents
        (document_id, primary_source_id, title, source_type, document_kind,
         published_date, source_status, metadata_priority, metadata_json,
         first_seen_at, last_seen_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (doc_id, source_id, f"title-{doc_id}", "regulatory_filing",
         "annual_report", "2025-12-31", "active", 0, "{}",
         "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
    )


def _add_artifact(
    tmp_path: Path,
    path: Path,
    *,
    artifact_id: str = "art1",
    doc_id: str = "doc1",
    source_id: str = "src1",
    role: str = "normalized",
    body: bytes | None = _SOURCE_BODY,
    status: str = "completed",
    generator: str = "normalizer",
    generator_version: str = "1.0.0",
    schema_version: str = "1.0",
    source_sha: str | None = _SOURCE_SHA,
    source_missing: bool = False,
) -> None:
    """Insert one artifact row + its source bytes on disk.

    ``body is None`` -> the artifact file is NOT written (missing_bytes case).
    """
    if body is not None:
        path.write_bytes(body)
    content_sha = hashlib.sha256(body).hexdigest() if body is not None else "0" * 64
    meta = {"schema_version": schema_version}
    if source_sha is not None:
        meta["source_sha256"] = source_sha
    con = sqlite3.connect(path.parent / "catalog.sqlite3")
    _add_source(con, source_id=source_id)
    _add_doc(con, doc_id=doc_id, source_id=source_id)
    effective_source = None if source_missing else source_id
    con.execute(
        """INSERT OR REPLACE INTO artifacts
        (artifact_id, document_id, source_id, artifact_role, path,
         content_sha256, byte_size, mime_type, generator_name,
         generator_version, status, error, metadata_json, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (artifact_id, doc_id, effective_source, role, str(path), content_sha,
         len(body) if body else 0, "text/markdown", generator, generator_version,
         status, None, json.dumps(meta), "2026-08-01T00:00:00Z"),
    )
    con.commit()
    con.close()


def _counts(path: Path) -> dict[str, int]:
    con = sqlite3.connect(path)
    try:
        return {
            "artifacts": con.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0],
            "bindings": con.execute(
                "SELECT COUNT(*) FROM artifact_bindings").fetchone()[0],
        }
    finally:
        con.close()


# --- MIG-01: dry-run is zero-write and emits a complete proposal ---------------

def test_ab01_dry_run_writes_nothing(tmp_path):
    """MIG-01: dry-run classifies but leaves artifact_bindings empty and the
    artifacts table byte/row counts unchanged."""
    cat = _catalog(tmp_path)
    _add_artifact(tmp_path, tmp_path / "a1.md", artifact_id="a1")
    before = _counts(cat)
    result = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW,
        mode="dry-run")
    after = _counts(cat)
    assert after == before                      # zero writes
    assert after["bindings"] == 0               # no shadow binding written
    assert result.input == 1                    # classification still computed
    assert isinstance(result, ArtifactBackfillResult)


def test_ab02_dry_run_complete_proposal_and_capacity(tmp_path):
    """MIG-01: the result carries per-bucket counts, a per-bucket byte capacity
    estimate, and a per-bindable binding proposal — enough to plan apply."""
    cat = _catalog(tmp_path)
    _add_artifact(tmp_path, tmp_path / "bind.md", artifact_id="bind",
                  body=b"bindable body")            # bindable
    _add_artifact(tmp_path, tmp_path / "miss.md", artifact_id="miss",
                  body=None, role="markdown")        # missing_bytes (distinct role)
    result = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW)
    assert result.input == 2
    assert result.bindable == 1
    assert result.missing_bytes == 1
    # capacity is reported per bucket (bytes), at least for the populated ones
    assert "bindable" in result.capacity
    assert result.capacity["bindable"] == len(b"bindable body")
    # the bindable artifact has a concrete binding proposal
    assert "bind" in result.proposals
    proposal = result.proposals["bind"]
    assert proposal["source_id"] == "src1"
    assert "bundle_hash" in proposal and proposal["bundle_hash"]


# --- MIG-03: idempotent re-run, zero duplicate bindings ------------------------

def test_ab03_rerun_is_byte_identical(tmp_path):
    """MIG-03: two dry-runs over an unchanged catalog produce identical result
    hashes (deterministic ordering by artifact_id)."""
    cat = _catalog(tmp_path)
    _add_artifact(tmp_path, tmp_path / "x.md", artifact_id="b", body=b"bb")
    _add_artifact(tmp_path, tmp_path / "y.md", artifact_id="a", body=b"aa",
                  role="markdown")
    r1 = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW)
    r2 = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW)
    assert r1.result_hash == r2.result_hash
    assert r1.as_dict() == r2.as_dict()


def test_ab04_apply_twice_zero_duplicate_bindings(tmp_path):
    """MIG-03: applying twice creates each binding exactly once (UNIQUE
    artifact_id); the second pass is a skip, not an insert."""
    cat = _catalog(tmp_path)
    _add_artifact(tmp_path, tmp_path / "z.md", artifact_id="z", body=b"zz")
    run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW,
        mode="apply")
    run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW,
        mode="apply")
    con = sqlite3.connect(cat)
    try:
        n = con.execute(
            "SELECT COUNT(*) FROM artifact_bindings WHERE artifact_id='z'"
        ).fetchone()[0]
        vis = con.execute(
            "SELECT visibility_state FROM artifact_bindings WHERE artifact_id='z'"
        ).fetchone()[0]
    finally:
        con.close()
    assert n == 1
    assert vis == "shadow"


# --- MIG-05: unprovable provenance -> legacy_unbound, never guessed ------------

def test_ab05_null_source_id_is_legacy_unbound(tmp_path):
    """MIG-05: an artifact with no source binding (source_id NULL) cannot have
    its provenance proven -> legacy_unbound, never bindable, never guessed."""
    cat = _catalog(tmp_path)
    _add_artifact(tmp_path, tmp_path / "n.md", artifact_id="n",
                  source_missing=True)
    result = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW)
    assert result.bindable == 0
    assert result.legacy_unbound == 1
    assert result.proposals == {}


def test_ab06_source_sha_mismatch_is_legacy_unbound(tmp_path):
    """MIG-05: an artifact derived from different source bytes than the catalog
    holds has unverifiable lineage -> legacy_unbound (NOT hash_mismatch)."""
    cat = _catalog(tmp_path)
    _add_artifact(tmp_path, tmp_path / "lin.md", artifact_id="lin",
                  source_sha="c" * 64)  # differs from catalog source sha
    result = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW)
    assert result.legacy_unbound == 1
    assert result.hash_mismatch == 0
    assert result.bindable == 0


# --- bucket conservation + per-bucket classification --------------------------

def test_ab07_bucket_conservation(tmp_path):
    """MIG-01 closure: input == bindable + hash_mismatch + missing_bytes +
    unknown_generator + legacy_unbound (exactly one bucket per artifact)."""
    cat = _catalog(tmp_path)
    _add_artifact(tmp_path, tmp_path / "ok.md", artifact_id="ok", body=b"ok")     # bindable
    _add_artifact(tmp_path, tmp_path / "hm.md", artifact_id="hm",
                  body=b"real", role="markdown")          # content_sha will mismatch
    # force hash mismatch: rewrite the file after insert so bytes != content_sha
    (tmp_path / "hm.md").write_bytes(b"tampered")
    _add_artifact(tmp_path, tmp_path / "mb.md", artifact_id="mb",
                  body=None, role="summary")              # missing_bytes
    _add_artifact(tmp_path, tmp_path / "ug.md", artifact_id="ug",
                  generator="rogue", generator_version="9.9.9",
                  body=b"ug", role="sections")            # unknown_generator
    _add_artifact(tmp_path, tmp_path / "lu.md", artifact_id="lu",
                  status="pending", body=b"lu",
                  role="consumer_analysis")              # legacy_unbound
    result = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW)
    total = (result.bindable + result.hash_mismatch + result.missing_bytes
             + result.unknown_generator + result.legacy_unbound)
    assert total == result.input == 5
    assert result.bindable == 1
    assert result.hash_mismatch == 1
    assert result.missing_bytes == 1
    assert result.unknown_generator == 1
    assert result.legacy_unbound == 1


def test_ab08_each_artifact_has_one_bucket_and_reason(tmp_path):
    """Every row carries exactly one bucket + a non-empty reason code; nothing
    is left unclassified."""
    cat = _catalog(tmp_path)
    _add_artifact(tmp_path, tmp_path / "ok.md", artifact_id="ok", body=b"ok")
    result = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW)
    assert len(result.rows) == result.input
    for row in result.rows:
        assert row["bucket"] in {"bindable", "hash_mismatch", "missing_bytes",
                                 "unknown_generator", "legacy_unbound"}
        assert row["reason"]


# --- apply semantics: shadow insert, zero deletion, reversible ----------------

def test_ab09_apply_only_binds_bindable_and_never_deletes(tmp_path):
    """Apply writes shadow bindings for bindable artifacts only; the artifacts
    table row count and every artifact row are unchanged (zero deletion/mutation)."""
    cat = _catalog(tmp_path)
    _add_artifact(tmp_path, tmp_path / "ok.md", artifact_id="ok", body=b"ok")
    _add_artifact(tmp_path, tmp_path / "miss.md", artifact_id="miss",
                  body=None, role="markdown")
    con = sqlite3.connect(cat)
    artifacts_before = con.execute(
        "SELECT artifact_id, content_sha256, status, source_id FROM artifacts "
        "ORDER BY artifact_id").fetchall()
    con.close()
    run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW,
        mode="apply")
    con = sqlite3.connect(cat)
    artifacts_after = con.execute(
        "SELECT artifact_id, content_sha256, status, source_id FROM artifacts "
        "ORDER BY artifact_id").fetchall()
    bindings = con.execute(
        "SELECT artifact_id, visibility_state FROM artifact_bindings").fetchall()
    con.close()
    assert artifacts_after == artifacts_before          # artifacts untouched
    assert bindings == [("ok", "shadow")]               # only bindable bound


def test_ab10_apply_is_reversible_by_shadow_delete(tmp_path):
    """Reversal = delete the shadow binding rows; artifacts table never touched."""
    cat = _catalog(tmp_path)
    _add_artifact(tmp_path, tmp_path / "ok.md", artifact_id="ok", body=b"ok")
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


def test_ab11_unknown_mode_rejected(tmp_path):
    """Fail fast on an unknown mode rather than silently defaulting."""
    cat = _catalog(tmp_path)
    _add_artifact(tmp_path, tmp_path / "ok.md", artifact_id="ok", body=b"ok")
    try:
        run_artifact_backfill(
            cat, registry=_REGISTRY, allowed_roots=(tmp_path,), now=_NOW,
            mode="wipe")
    except ValueError:
        return
    raise AssertionError("mode='wipe' must be rejected")
