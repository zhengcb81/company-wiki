"""F-B10R2-MISSINGFILE family: the four in-package unguarded column parses.

Each site used to let a MALFORMED column value escape as a raw parse exception, which for the
scan meant aborting the whole batch.  The owner instructed the fix on 2026-09-18.  The
contracts differ per site, and the tests pin the DIFFERENCE rather than a single blanket
behaviour:

* `scanner._observe_file` (the size+mtime reuse shortcut) - a manifest that cannot be read is
  not a reuse candidate, so the scan FALLS THROUGH and re-hashes the file.  The batch keeps
  running and the manifest is repaired; nothing is silently served from the damaged value.
* `remediation.approve_proposal` - the proposal is required evidence; an unreadable one is
  refused BY NAME (`RemediationError`) instead of a bare `JSONDecodeError`.
* `activation.rollback_activation` - reading the assertion list as `[]` would report success
  while restoring nothing, so an unreadable value refuses by name (`ActivationError`).
* `assertion_service.verify_assertion` - evidence that cannot be read must not be copied
  forward as if it had been verified: a named `ValueError`.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from company_wiki.source_catalog import CatalogConfig, SourceCatalog
from company_wiki.source_catalog.activation import ActivationError, rollback_activation
from company_wiki.source_catalog.assertion_service import verify_assertion
from company_wiki.source_catalog.models import RootSpec
from company_wiki.source_catalog.remediation import RemediationError, approve_proposal
from company_wiki.source_catalog.store import CatalogStore

BODY = b"%PDF-1.4\n% f-b10r2-missingfile family fixture\n"
BROKEN = '{"collector_name": "x"'  # truncated JSON: unreadable, and not a JSON object either
POLICY_HASH = "a" * 64


def _store(tmp_path: Path) -> CatalogStore:
    return CatalogStore(tmp_path / "catalog.sqlite3")


def _write_filing(directory: Path) -> None:
    import hashlib

    directory.mkdir(parents=True, exist_ok=True)
    (directory / "2025.pdf").write_bytes(BODY)
    (directory / "2025.pdf.source.json").write_text(json.dumps({
        "schema_version": "1.0",
        "canonical_entity_id": "ent-fb10r2",
        "display_name": "FB10R2 Acme",
        "market": "US",
        "security_id": "FB10R2",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "published_at": "2026-02-20",
        "provider": "sec",
        "provider_document_id": "doc-1",
        "source_url": "https://sec.gov/doc-1",
        "content_sha256": hashlib.sha256(BODY).hexdigest(),
    }), encoding="utf-8")


def _catalog(tmp_path: Path) -> SourceCatalog:
    root_dir = tmp_path / "roots" / "r"
    _write_filing(root_dir)
    return SourceCatalog(CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        reusable_root_kinds=("company_raw", "directory"),
        roots=(RootSpec("r", root_dir, "directory", priority=10,
                        adapter_id="sidecar_filing_v1", read_only=True,
                        reusable_for_filing=True),),
    ))


def _scan_report_ok(catalog: SourceCatalog) -> None:
    report = catalog.scan()
    assert report.errors == 0, report


def test_scan_survives_a_damaged_manifest_and_repairs_it(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    _scan_report_ok(catalog)
    connection = sqlite3.connect(catalog.config.database_path)
    try:
        before = connection.execute(
            "SELECT COUNT(*) FROM locations WHERE manifest_json LIKE '%collector_name%'"
        ).fetchone()[0]
        # damage the manifest WITHOUT touching size/mtime, so the reuse shortcut is taken
        connection.execute("UPDATE locations SET manifest_json=?", (BROKEN,))
        connection.commit()
    finally:
        connection.close()
    assert before == 1

    # the whole point: a single damaged row must not abort the scan
    _scan_report_ok(catalog)

    connection = sqlite3.connect(f"file:{catalog.config.database_path}?mode=ro", uri=True)
    try:
        repaired = connection.execute(
            "SELECT manifest_json FROM locations").fetchone()[0]
    finally:
        connection.close()
    payload = json.loads(repaired)  # raises if the repair did not happen
    assert payload.get("content_sha256"), payload


def test_approve_proposal_refuses_by_name_on_an_unreadable_proposal(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with store.transaction() as connection:
        connection.execute(
            "INSERT INTO remediation_proposals (proposal_id,source_id,document_id,"
            "content_sha256,proposal_json,policy_hash,proposed_by,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            ("p" * 32, "s1", "d1", "c" * 64, BROKEN, POLICY_HASH, "author", "2026-09-18"),
        )
    with pytest.raises(RemediationError) as excinfo:
        approve_proposal(store, proposal_id="p" * 32, policy_hash=POLICY_HASH,
                         approved_by="owner")
    assert "unreadable" in str(excinfo.value), str(excinfo.value)


def test_rollback_refuses_by_name_on_an_unreadable_assertion_list(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with store.transaction() as connection:
        connection.execute(
            "INSERT INTO activation_journal (receipt_id,schema_version,kind,epoch,cohort,"
            "assertion_ids_json,policy_hash,reviewer,reason,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("apply-1", "1.0", "apply", "epoch-1", "cohort-1", BROKEN, POLICY_HASH,
             "reviewer", "apply", "2026-09-18"),
        )
    with pytest.raises(ActivationError) as excinfo:
        rollback_activation(store, receipt_id="apply-1", reviewer="owner", reason="test")
    assert "unreadable" in str(excinfo.value), str(excinfo.value)


def test_rollback_refuses_a_readable_value_that_is_not_a_list(tmp_path: Path) -> None:
    """Readable JSON that is the WRONG SHAPE is refused too - `{"a": 1}` is not a list."""
    store = _store(tmp_path)
    with store.transaction() as connection:
        connection.execute(
            "INSERT INTO activation_journal (receipt_id,schema_version,kind,epoch,cohort,"
            "assertion_ids_json,policy_hash,reviewer,reason,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("apply-2", "1.0", "apply", "epoch-1", "cohort-1", '{"a": 1}', POLICY_HASH,
             "reviewer", "apply", "2026-09-18"),
        )
    with pytest.raises(ActivationError) as excinfo:
        rollback_activation(store, receipt_id="apply-2", reviewer="owner", reason="test")
    assert "not a list" in str(excinfo.value), str(excinfo.value)


def test_verify_refuses_by_name_on_unreadable_evidence(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with store.transaction() as connection:
        # parents first: source_metadata_assertions carries FKs to sources/documents
        connection.execute(
            "INSERT INTO sources (source_id, content_sha256, byte_size, mime_type, "
            "first_seen_at) VALUES ('s1','src-hash',10,'application/pdf','2026-01-01')")
        connection.execute(
            "INSERT INTO documents (document_id, title, source_status, source_type, "
            "document_kind, metadata_priority, metadata_json, first_seen_at, last_seen_at) "
            "VALUES ('d1','Acme 2025','active','file','annual_report',10,'{}',"
            "'2026-01-01','2026-01-01')")
        connection.execute(
            "INSERT INTO source_metadata_assertions (assertion_id,schema_version,source_id,"
            "document_id,document_kind,content_sha256,evidence_basis,evidence_json,decision,"
            "created_at,created_by,visibility_state) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            ("a1", "2.0", "s1", "d1", "annual_report", "c" * 64, "sidecar", BROKEN,
             "candidate", "2026-09-18", "author", "shadow"),
        )
    with pytest.raises(ValueError) as excinfo:
        verify_assertion(store, assertion_id="a1", current_sha256="c" * 64,
                         confirmed_by="owner")
    assert "unreadable" in str(excinfo.value), str(excinfo.value)
