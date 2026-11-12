"""Public stream transport contract over the current stream_version owner.

The wire is additive to the whole-buffer reader's 2.1 receipts: one ``locked``
line, provisional bytes on stdout, one final ``ok`` or five-value refusal.
Admission, verification, budget and cancellation stay in the owner; this
contract pins what a consumer may rely on and what the transport refuses.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

REPO = Path(__file__).resolve().parents[2]
BODY = b"%PDF-1.4 stream-transport-original"
SHA = hashlib.sha256(BODY).hexdigest()


def _catalog(tmp_path: Path, *, body: bytes = BODY) -> tuple[SourceCatalog, Path, dict]:
    companies = tmp_path / "companies"
    target = companies / "Acme" / "raw"
    target.mkdir(parents=True)
    original = target / "2025.pdf"
    original.write_bytes(body)
    (target / "2025.pdf.source.json").write_text(json.dumps({
        "schema_version": "1.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "US",
        "security_id": "ACME",
        "document_kind": "annual_report",
        "filing_date": "2026-02-20",
        "form_type": "10-K",
        "provider": "sec",
        "provider_document_id": "doc-1",
        "content_sha256": hashlib.sha256(body).hexdigest(),
        "retrieved_at": "2026-02-21T00:00:00Z",
        "collector_name": "sec_edgar",
        "collector_version": "1.0",
    }), encoding="utf-8")
    config = CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        roots=(RootSpec("company_raw", companies, "company_raw", priority=10,
                        adapter_id="company_raw_v1", read_only=False,
                        reusable_for_filing=True, canonical_write_target="companies"),),
        reusable_root_kinds=("company_raw",),
    )
    catalog = SourceCatalog(config)
    catalog.scan()
    row = catalog.reader.fetchone(
        """SELECT d.document_id, d.primary_source_id AS source_id,
                  s.content_sha256, s.mime_type, s.byte_size
           FROM documents d JOIN sources s
             ON s.source_id=d.primary_source_id
           WHERE s.content_sha256=?""",
        (hashlib.sha256(body).hexdigest(),),
    )
    assert row is not None
    return catalog, original, dict(row)


def _run_cli(config: Path, *, document_id: str, source_id: str, sha: str,
             purpose: str = "preview") -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    env["COMPANY_WIKI_NETWORK"] = "blocked"
    return subprocess.run(
        [sys.executable, "-B", "-m", "company_wiki.source_catalog.source_stream_cli",
         "--config", str(config), "--document-id", document_id,
         "--source-id", source_id, "--content-sha256", sha,
         "--purpose", purpose],
        capture_output=True, cwd=str(REPO), env=env, timeout=60, check=False,
    )


def _receipts(stderr: bytes) -> list[dict]:
    return [json.loads(line) for line in stderr.decode("utf-8").strip().splitlines()]


@pytest.fixture()
def lake(tmp_path: Path):
    catalog, original, identity = _catalog(tmp_path)
    config_path = tmp_path / "source_catalog.yaml"
    config_path.write_text(json.dumps({
        "schema_version": "1.0",
        "catalog_dir": str(catalog.config.catalog_dir),
        "roots": [{
            "root_id": "company_raw", "path": str(tmp_path / "companies"),
            "kind": "company_raw", "priority": 10, "adapter_id": "company_raw_v1",
            "read_only": True, "reusable_for_filing": True,
        }],
        "reusable_root_kinds": ["company_raw"],
    }), encoding="utf-8")
    yield {"config": config_path, "identity": identity, "original": original}
    catalog.close()


def test_stream_cli_delivers_exact_verified_bytes_with_two_receipts(lake, tmp_path):
    result = _run_cli(
        lake["config"],
        document_id=lake["identity"]["document_id"],
        source_id=lake["identity"]["source_id"],
        sha=lake["identity"]["content_sha256"],
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert result.stdout == BODY
    receipts = _receipts(result.stderr)
    assert len(receipts) == 2
    locked, final = receipts
    assert locked["status"] == "locked"
    assert locked["schema_version"] == "2.2"
    assert locked["document_id"] == lake["identity"]["document_id"]
    assert locked["source_id"] == lake["identity"]["source_id"]
    assert locked["content_sha256"] == SHA
    assert locked["mime_type"] == lake["identity"]["mime_type"]
    assert locked["byte_size"] == len(BODY)
    assert final["status"] == "ok"
    assert final["schema_version"] == "2.2"
    assert final["content_sha256"] == SHA
    assert final["byte_size"] == len(BODY)
    assert hashlib.sha256(result.stdout).hexdigest() == SHA
    assert str(tmp_path) not in result.stdout.decode("utf-8", "replace")


def test_stream_cli_refuses_unknown_identity_with_one_receipt(lake):
    result = _run_cli(
        lake["config"],
        document_id=lake["identity"]["document_id"],
        source_id=lake["identity"]["source_id"],
        sha="b" * 64,
    )
    assert result.returncode == 2
    assert result.stdout == b""
    # The owner's gate names a digest mismatch; the transport only relays it.
    receipts = _receipts(result.stderr)
    assert receipts == [{"schema_version": "2.2", "status": "unavailable",
                         "reason": "expected_version_mismatch"}]


def test_stream_cli_refuses_filing_reuse_by_name(lake):
    result = _run_cli(
        lake["config"],
        document_id=lake["identity"]["document_id"],
        source_id=lake["identity"]["source_id"],
        sha=lake["identity"]["content_sha256"],
        purpose="filing_reuse",
    )
    assert result.returncode == 2
    assert result.stdout == b""
    assert _receipts(result.stderr) == [{"schema_version": "2.2", "status": "blocked",
                                         "reason": "purpose_not_streamable"}]


def test_stream_cli_rejects_malformed_digest(lake):
    result = _run_cli(
        lake["config"],
        document_id=lake["identity"]["document_id"],
        source_id=lake["identity"]["source_id"],
        sha="NOT-A-DIGEST",
    )
    assert result.returncode == 2
    assert result.stdout == b""
    assert _receipts(result.stderr) == [{"schema_version": "2.2", "status": "blocked",
                                         "reason": "invalid_request"}]


def test_stream_cli_refuses_when_no_candidate_is_admitted(lake, tmp_path):
    lake["original"].write_bytes(b"tampered bytes")
    result = _run_cli(
        lake["config"],
        document_id=lake["identity"]["document_id"],
        source_id=lake["identity"]["source_id"],
        sha=lake["identity"]["content_sha256"],
    )
    assert result.returncode == 2
    assert result.stdout == b""
    receipts = _receipts(result.stderr)
    # The owner staged the admitted candidate (locked), failed its byte
    # verification, and refused: no ok receipt, transfer incomplete.
    assert len(receipts) == 2
    assert receipts[0]["status"] == "locked"
    assert receipts[1]["status"] == "unavailable"
    assert "ok" not in {receipt["status"] for receipt in receipts}


def test_stream_cli_keeps_the_original_bytes_unchanged(lake):
    result = _run_cli(
        lake["config"],
        document_id=lake["identity"]["document_id"],
        source_id=lake["identity"]["source_id"],
        sha=lake["identity"]["content_sha256"],
    )
    assert result.returncode == 0
    assert lake["original"].read_bytes() == BODY
