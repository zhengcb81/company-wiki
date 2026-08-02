"""CW-2.28 Phase 5 contract tests: source metadata assertions."""

from __future__ import annotations

from pathlib import Path

import pytest


def _temp_store(tmp_path: Path):
    """Create a temporary catalog with one document for assertion tests."""
    from company_wiki.source_catalog.store import CatalogStore

    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO sources(source_id,content_sha256,byte_size,mime_type,first_seen_at) VALUES(?,?,?,?,?)",
            ("s:test", "abc123", 100, "text/plain", "2026-01-01T00:00:00Z"),
        )
        conn.execute(
            """INSERT INTO documents(document_id,primary_source_id,title,source_type,document_kind,
            source_status,metadata_priority,metadata_json,first_seen_at,last_seen_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                "d:test",
                "s:test",
                "Test Doc",
                "news",
                "news",
                "active",
                0,
                "{}",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z",
            ),
        )
    return store


def _temp_placeholder_store(tmp_path: Path):
    """A temporary catalog with a placeholder document (primary_source_id
    NULL) — the Phase 15.5 shape whose source_id lookups can never match."""
    from company_wiki.source_catalog.store import CatalogStore

    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO sources(source_id,content_sha256,byte_size,mime_type,first_seen_at) VALUES(?,?,?,?,?)",
            ("s:placeholder-meta", "hash-placeholder", 10, "application/json", "2026-01-01T00:00:00Z"),
        )
        conn.execute(
            """INSERT INTO documents(document_id,primary_source_id,title,source_type,document_kind,
            source_status,metadata_priority,metadata_json,first_seen_at,last_seen_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                "d:placeholder",
                None,
                "Placeholder doc",
                "regulatory_filing",
                "annual_report",
                "incomplete",
                0,
                "{}",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z",
            ),
        )
    return store


def test_verified_assertion_resolves_by_document_id(tmp_path):
    """An assertion for a document without a primary source (placeholder) must
    be resolvable by document_id — a source_id-based lookup can never match a
    NULL-primary document (Phase 15.5)."""
    from company_wiki.source_catalog.assertion_service import (
        get_verified_assertion,
        get_verified_assertion_by_document,
        preview_assertion,
        verify_assertion,
    )

    store = _temp_placeholder_store(tmp_path)

    p = preview_assertion(
        store,
        source_id="s:placeholder-meta",
        document_id="d:placeholder",
        content_sha256="hash-placeholder",
        entity="Zijin",
        market="CN",
        security_id="601899",
        evidence_basis="test",
    )
    verify_assertion(
        store, assertion_id=p["assertion_id"], current_sha256="hash-placeholder"
    )

    # The resolver sees source_id = primary_source_id = NULL for placeholder
    # documents (service.py), so the source_id path can never match
    # (WHERE source_id = NULL never evaluates true).
    assert get_verified_assertion(store, None, "hash-placeholder") is None
    # document_id path must resolve the identity
    found = get_verified_assertion_by_document(store, "d:placeholder", "hash-placeholder")
    assert found is not None
    assert found["security_id"] == "601899"
    assert found["market"] == "CN"


def test_preview_writes_candidate_and_verify_promotes(tmp_path):
    from company_wiki.source_catalog.assertion_service import (
        get_verified_assertion,
        preview_assertion,
        verify_assertion,
    )

    store = _temp_store(tmp_path)

    p = preview_assertion(
        store,
        source_id="s:test",
        document_id="d:test",
        content_sha256="abc123",
        entity="Test Corp",
        market="CN",
        security_id="000001",
        evidence_basis="test",
    )
    assert p["decision"] == "candidate"

    v = verify_assertion(store, assertion_id=p["assertion_id"], current_sha256="abc123")
    assert v["decision"] == "verified"
    assert v["supersedes_assertion_id"] == p["assertion_id"]

    gv = get_verified_assertion(store, "s:test", "abc123")
    assert gv is not None
    assert gv["entity"] == "Test Corp"


def test_candidate_not_returned_by_get_verified(tmp_path):
    from company_wiki.source_catalog.assertion_service import (
        get_verified_assertion,
        preview_assertion,
    )

    store = _temp_store(tmp_path)
    preview_assertion(
        store,
        source_id="s:test",
        document_id="d:test",
        content_sha256="abc123",
        entity="Test Corp",
        market="CN",
        security_id="000001",
        evidence_basis="test",
    )
    # Candidate only — not verified yet
    assert get_verified_assertion(store, "s:test", "abc123") is None


def test_hash_mismatch_rejected(tmp_path):
    from company_wiki.source_catalog.assertion_service import (
        get_verified_assertion,
        preview_assertion,
    )

    store = _temp_store(tmp_path)
    preview_assertion(
        store,
        source_id="s:test",
        document_id="d:test",
        content_sha256="abc123",
        entity="Test Corp",
        market="CN",
        security_id="000001",
        evidence_basis="test",
    )
    # Hash changed → no verified assertion returned
    assert get_verified_assertion(store, "s:test", "xyz789") is None


def test_append_only_no_update_delete(tmp_path):
    from company_wiki.source_catalog.assertion_service import (
        preview_assertion,
        reject_assertion,
        verify_assertion,
    )

    store = _temp_store(tmp_path)
    p = preview_assertion(
        store,
        source_id="s:test",
        document_id="d:test",
        content_sha256="abc123",
        entity="Test Corp",
        evidence_basis="test",
    )

    count_before = store.fetchone("SELECT COUNT(*) FROM source_metadata_assertions")[0]

    verify_assertion(store, assertion_id=p["assertion_id"], current_sha256="abc123")

    count_mid = store.fetchone("SELECT COUNT(*) FROM source_metadata_assertions")[0]
    assert count_mid == count_before + 1  # candidate → verified adds 1 row (append)

    p2 = preview_assertion(
        store,
        source_id="s:test",
        document_id="d:test",
        content_sha256="abc123",
        entity="Bad Corp",
        evidence_basis="test",
    )
    reject_assertion(store, assertion_id=p2["assertion_id"], reason="wrong")
    count_after = store.fetchone("SELECT COUNT(*) FROM source_metadata_assertions")[0]
    assert count_after == count_mid + 2  # preview adds 1 + reject adds 1

    # Check all rows still exist (no deletes)
    decisions = [
        row["decision"]
        for row in store.fetchall("SELECT decision FROM source_metadata_assertions")
    ]
    assert "candidate" in decisions
    assert "verified" in decisions
    assert "rejected" in decisions


def test_second_verify_supersedes_prior_verified_same_evidence(tmp_path):
    """Phase 18.2 contract change: a second verify on the same evidence
    supersedes the first; the lookup resolves to the latest (Corp B) instead of
    failing closed with None."""
    from company_wiki.source_catalog.assertion_service import (
        get_verified_assertion,
        preview_assertion,
        verify_assertion,
    )

    store = _temp_store(tmp_path)

    p1 = preview_assertion(
        store,
        source_id="s:test",
        document_id="d:test",
        content_sha256="abc123",
        entity="Corp A",
        evidence_basis="test",
    )
    verify_assertion(store, assertion_id=p1["assertion_id"], current_sha256="abc123")

    p2 = preview_assertion(
        store,
        source_id="s:test",
        document_id="d:test",
        content_sha256="abc123",
        entity="Corp B",
        evidence_basis="test",
    )
    v2 = verify_assertion(store, assertion_id=p2["assertion_id"], current_sha256="abc123")

    gv = get_verified_assertion(store, "s:test", "abc123")
    assert gv is not None
    assert gv["entity"] == "Corp B"
    assert gv["assertion_id"] == v2["assertion_id"]


def test_conflict_on_different_evidence_returns_none(tmp_path):
    """Phase 18.2 control: verified assertions with genuinely different
    evidence (content hash) on the same document stay an unresolved conflict
    when looked up without a content filter (fail closed preserved)."""
    from company_wiki.source_catalog.assertion_service import (
        get_verified_assertion_by_document,
        preview_assertion,
        verify_assertion,
    )

    store = _temp_store(tmp_path)

    p1 = preview_assertion(
        store,
        source_id="s:test",
        document_id="d:test",
        content_sha256="abc123",
        entity="Corp A",
        evidence_basis="test",
    )
    verify_assertion(store, assertion_id=p1["assertion_id"], current_sha256="abc123")

    p2 = preview_assertion(
        store,
        source_id="s:test",
        document_id="d:test",
        content_sha256="xyz789",
        entity="Corp B",
        evidence_basis="test",
    )
    verify_assertion(store, assertion_id=p2["assertion_id"], current_sha256="xyz789")

    assert get_verified_assertion_by_document(store, "d:test", None) is None


def test_reject_only_candidate(tmp_path):
    from company_wiki.source_catalog.assertion_service import (
        preview_assertion,
        reject_assertion,
        verify_assertion,
    )

    store = _temp_store(tmp_path)
    p = preview_assertion(
        store,
        source_id="s:test",
        document_id="d:test",
        content_sha256="abc123",
        entity="Test Corp",
        evidence_basis="test",
    )
    v = verify_assertion(store, assertion_id=p["assertion_id"], current_sha256="abc123")

    # Now trying to reject the original (already-superseded) candidate must fail
    with pytest.raises(ValueError, match="superseded"):
        reject_assertion(store, assertion_id=p["assertion_id"], reason="trying")
    # Rejecting a verified assertion must also fail
    with pytest.raises(ValueError, match="cannot be rejected"):
        reject_assertion(store, assertion_id=v["assertion_id"], reason="trying")
    # Rejecting an already-rejected must also fail
    p2 = preview_assertion(
        store,
        source_id="s:test",
        document_id="d:test",
        content_sha256="abc123",
        entity="Bad Corp",
        evidence_basis="test",
    )
    reject_assertion(store, assertion_id=p2["assertion_id"], reason="wrong")
    with pytest.raises(ValueError, match="superseded"):
        reject_assertion(store, assertion_id=p2["assertion_id"], reason="double")


def test_second_verify_supersedes_prior_verified_and_resolves_to_latest(tmp_path):
    """Phase 18.2: verifying a corrected candidate on the same
    (source, document, content) must supersede the prior verified assertion,
    and lookups must resolve to the latest (GOOGL -> GOOG correction flow).
    Today the second verify self-supersedes its own candidate, so two verified
    assertions stay active and lookups fail closed with None."""
    from company_wiki.source_catalog.assertion_service import (
        get_verified_assertion,
        get_verified_assertion_by_document,
        preview_assertion,
        verify_assertion,
    )

    store = _temp_store(tmp_path)

    p1 = preview_assertion(
        store,
        source_id="s:test",
        document_id="d:test",
        content_sha256="abc123",
        entity="Alphabet Inc.",
        market="US",
        security_id="GOOGL",
        evidence_basis="test",
    )
    v1 = verify_assertion(store, assertion_id=p1["assertion_id"], current_sha256="abc123")

    p2 = preview_assertion(
        store,
        source_id="s:test",
        document_id="d:test",
        content_sha256="abc123",
        entity="Alphabet Inc.",
        market="US",
        security_id="GOOG",
        evidence_basis="test",
    )
    v2 = verify_assertion(store, assertion_id=p2["assertion_id"], current_sha256="abc123")

    # The correction chains: v2 supersedes v1 (not its own candidate).
    assert v2["supersedes_assertion_id"] == v1["assertion_id"]

    found = get_verified_assertion(store, "s:test", "abc123")
    assert found is not None
    assert found["security_id"] == "GOOG"

    by_doc = get_verified_assertion_by_document(store, "d:test", "abc123")
    assert by_doc is not None
    assert by_doc["security_id"] == "GOOG"
