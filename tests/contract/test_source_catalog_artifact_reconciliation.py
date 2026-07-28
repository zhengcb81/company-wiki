"""§10.6.9 + §10.7.6: artifact reconciliation contract tests."""

from __future__ import annotations

import sqlite3



SHA = "abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234"
SRC = f"urn:company-wiki:source:sha256:{SHA}"
DOC = f"urn:company-wiki:document:sha256:{SHA}"


def _make_temp_catalog(
    tmp_path,
    *,
    with_source=True,
    with_document=True,
    with_artifact=False,
    role="normalized",
):
    db = tmp_path / "catalog.sqlite3"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE sources (source_id TEXT PRIMARY KEY, content_sha256 TEXT, byte_size INTEGER, mime_type TEXT, first_seen_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE documents (document_id TEXT PRIMARY KEY, primary_source_id TEXT, title TEXT, source_type TEXT, document_kind TEXT, published_date TEXT, source_status TEXT, metadata_priority TEXT, metadata_json TEXT, text_fingerprint TEXT, first_seen_at TEXT, last_seen_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE artifacts (artifact_id TEXT PRIMARY KEY, document_id TEXT, source_id TEXT, artifact_role TEXT, path TEXT, content_sha256 TEXT, byte_size INTEGER, mime_type TEXT, generator_name TEXT, generator_version TEXT, status TEXT, error TEXT, metadata_json TEXT, created_at TEXT)"
    )
    if with_source:
        conn.execute(
            "INSERT INTO sources VALUES (?,?,0,'application/pdf','')", (SRC, SHA)
        )
    if with_document:
        conn.execute(
            "INSERT INTO documents (document_id, primary_source_id) VALUES (?,?)",
            (DOC, SRC),
        )
    if with_artifact:
        conn.execute(
            "INSERT INTO artifacts (artifact_id,document_id,source_id,artifact_role,path,content_sha256,byte_size,mime_type,generator_name,generator_version,status,created_at) VALUES ('art-1',?,?,?,'x',?,0,'text/md','p','1','completed','')",
            (DOC, SRC, role, SHA),
        )
    conn.commit()
    conn.close()
    return db


def _make_derived_file(
    parent, sha, role="normalized", doc_id=None, src_id=None, fm_sha=None
):
    doc_id = doc_id or DOC
    src_id = src_id or SRC
    fm_sha = fm_sha or SHA
    p = parent / sha[:2] / sha / f"{role}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"""---
schema_version: 1.0.0
artifact_role: {role}
document_id: {doc_id}
source_id: {src_id}
source_sha256: {fm_sha}
parser_name: p
parser_version: "1"
normalization_status: completed
---
body
""",
        encoding="utf-8",
    )
    return p


def test_matching_normalized_file_in_catalog(tmp_path):
    from company_wiki.source_catalog.reconciliation import reconcile

    db = _make_temp_catalog(tmp_path)
    derived = tmp_path / "derived"
    _make_derived_file(derived, SHA)
    r = reconcile(db, derived, role="normalized", limit=10)
    assert r.matched == 1
    assert r.detached == 0


def test_detached_when_source_missing(tmp_path):
    from company_wiki.source_catalog.reconciliation import reconcile

    db = _make_temp_catalog(tmp_path, with_source=False, with_document=False)
    derived = tmp_path / "derived"
    _make_derived_file(derived, SHA)
    r = reconcile(db, derived, limit=10)
    assert r.matched == 0
    assert any(
        row.verdict == "detached" and "source_not_in_catalog" in row.reason
        for row in r.rows
    )


def test_detached_when_document_missing(tmp_path):
    from company_wiki.source_catalog.reconciliation import reconcile

    db = _make_temp_catalog(tmp_path, with_source=True, with_document=False)
    derived = tmp_path / "derived"
    _make_derived_file(derived, SHA)
    r = reconcile(db, derived, limit=10)
    assert any(
        row.verdict == "detached" and "document_not_in_catalog" in row.reason
        for row in r.rows
    )


def test_hash_mismatch(tmp_path):
    from company_wiki.source_catalog.reconciliation import reconcile

    db = _make_temp_catalog(tmp_path)
    derived = tmp_path / "derived"
    _make_derived_file(derived, SHA, fm_sha="f" * 64)
    r = reconcile(db, derived, limit=10)
    assert r.hash_mismatch == 1


def test_already_indexed_skipped(tmp_path):
    from company_wiki.source_catalog.reconciliation import reconcile

    db = _make_temp_catalog(tmp_path, with_artifact=True)
    derived = tmp_path / "derived"
    _make_derived_file(derived, SHA)
    r = reconcile(db, derived, limit=10)
    assert r.already_indexed == 1
    assert r.matched == 0


def test_missing_frontmatter(tmp_path):
    from company_wiki.source_catalog.reconciliation import reconcile

    derived = tmp_path / "derived"
    p = derived / SHA[:2] / SHA / "normalized.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("no frontmatter", encoding="utf-8")
    db = _make_temp_catalog(tmp_path)
    r = reconcile(db, derived, limit=10)
    assert r.missing_frontmatter >= 1


def test_dry_run_does_not_write_artifacts(tmp_path):
    from company_wiki.source_catalog.reconciliation import reconcile

    db = _make_temp_catalog(tmp_path)
    derived = tmp_path / "derived"
    _make_derived_file(derived, SHA)
    r = reconcile(db, derived, limit=10, dry_run=True)
    assert r.matched == 1
    c = sqlite3.connect(str(db)).execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
    assert c == 0


def test_apply_inserts_artifacts(tmp_path):
    from company_wiki.source_catalog.reconciliation import reconcile

    db = _make_temp_catalog(tmp_path)
    derived = tmp_path / "derived"
    _make_derived_file(derived, SHA)
    r = reconcile(db, derived, limit=10, dry_run=False)
    assert r.matched == 1
    c = sqlite3.connect(str(db)).execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
    assert c == 1


def test_role_mismatch(tmp_path):
    from company_wiki.source_catalog.reconciliation import reconcile

    db = _make_temp_catalog(tmp_path)
    derived = tmp_path / "derived"
    # Create normalized.md but with frontmatter artifact_role=summary
    p = derived / SHA[:2] / SHA / "normalized.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"""---
schema_version: 1.0.0
artifact_role: summary
document_id: {DOC}
source_id: {SRC}
source_sha256: {SHA}
parser_name: p
parser_version: "1"
normalization_status: completed
---
body
""",
        encoding="utf-8",
    )
    r = reconcile(db, derived, role="normalized", limit=10)
    assert any(
        row.verdict == "detached" and "role_mismatch" in row.reason for row in r.rows
    )
