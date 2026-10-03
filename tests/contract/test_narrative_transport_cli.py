"""Public subprocess contract: pathless JSON in, exact stored bytes out."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from company_wiki.automation.models import canonical_json
from support.narrative_transport_fixture import published_fixture
from company_wiki.source_contract import source_id_for_sha256


REPO = Path(__file__).resolve().parents[2]
READ_RECEIPT_KEYS = {
    "schema_version", "status", "narrative_ref", "as_of_date", "manifest",
    "source_read_policy_sha256", "read_at", "locator_count", "selection_status",
    "quality_status", "replay_status",
}


def _cli(fixture, operation: str, payload: dict | bytes):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHON_DOTENV_DISABLED"] = "1"
    env["COMPANY_WIKI_NETWORK"] = "blocked"
    data = json.dumps(payload).encode("utf-8") if isinstance(payload, dict) else payload
    return subprocess.run(
        [sys.executable, "-m", "company_wiki.source_catalog.narrative_transport_cli",
         "--config", str(fixture.config_path), "--operation", operation],
        input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=fixture.root, env=env, timeout=30, check=False,
    )


def _reference(fixture):
    result = _cli(fixture, "reference", {
        "schema_version": "narrative-reference-request/1",
        "source_ref": fixture.source_ref.to_dict(),
    })
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    reference = json.loads(result.stdout)
    assert set(reference) == {
        "schema_version", "artifact_version_id", "artifact_sha256", "byte_size", "source_ref",
    }
    assert reference["source_ref"] == fixture.source_ref.to_dict()
    receipt = json.loads(result.stderr)
    assert receipt["status"] == "metadata_only"
    assert "metadata" in json.dumps(receipt).lower()
    assert str(fixture.root) not in result.stdout.decode("utf-8")
    return reference


@pytest.mark.parametrize("kind", ["txt", "json", "pdf", "skip"])
def test_public_cli_reads_generated_persisted_bundle_without_rewriting(tmp_path: Path, kind) -> None:
    with published_fixture(tmp_path, kind=kind) as fixture:
        database = fixture.catalog.store.database_path
        before = hashlib.sha256(database.read_bytes()).hexdigest()
        before_wal = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in fixture.root.rglob("*-wal")
        }
        reference = _reference(fixture)
        result = _cli(fixture, "read", {
            "schema_version": "narrative-read-request/1", "narrative_ref": reference,
            "as_of_date": "2026-09-01", "expected_source": fixture.expected_source,
        })
        assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
        assert result.stdout == fixture.payload
        assert len(result.stdout) == reference["byte_size"]
        assert hashlib.sha256(result.stdout).hexdigest() == reference["artifact_sha256"]
        assert not result.stdout.endswith(b"\n")
        assert result.stderr.count(b"\n") == 1
        receipt = json.loads(result.stderr)
        assert set(receipt) == READ_RECEIPT_KEYS
        assert receipt["schema_version"] == "narrative-read-receipt/1"
        assert receipt["replay_status"] == "verified"
        assert receipt["narrative_ref"] == reference
        assert receipt["locator_count"] == len(json.loads(fixture.payload)["evidence_spans"])
        assert str(fixture.root) not in result.stderr.decode("utf-8")
        assert hashlib.sha256(database.read_bytes()).hexdigest() == before
        assert {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in before_wal
        } == before_wal


@pytest.mark.parametrize("body", [
    b'{"schema_version":"narrative-reference-request/1","schema_version":"x"}',
    b'{"schema_version":NaN}', b'\xff', b'{}',
    b'{"schema_version":"narrative-reference-request/1","object_key":"local"}',
    b" " * (64 * 1024 + 1),
    b"[" * 1100 + b"0" + b"]" * 1100,
], ids=["duplicate-key", "nan", "invalid-utf8", "missing-fields", "unknown-path",
        "oversize", "deeply-nested"])
def test_cli_rejects_malformed_input_with_empty_stdout_and_bounded_refusal(tmp_path: Path, body) -> None:
    with published_fixture(tmp_path) as fixture:
        result = _cli(fixture, "reference", body)
        assert result.returncode == 2
        assert result.stdout == b""
        assert result.stderr.count(b"\n") == 1
        refusal = json.loads(result.stderr)
        assert set(refusal) == {"schema_version", "status", "reason"}
        assert refusal["status"] != "ok"
        assert refusal["reason"]
        assert len(result.stderr) < 4096
        assert b"Traceback" not in result.stderr
        assert str(fixture.root) not in result.stderr.decode("utf-8")


def test_unknown_publication_json_refuses_historical_cli_read(tmp_path: Path) -> None:
    with published_fixture(tmp_path, kind="json") as fixture:
        reference = _reference(fixture)
        with fixture.catalog.store.transaction() as connection:
            connection.execute("UPDATE documents SET published_date=NULL")
        result = _cli(fixture, "read", {
            "schema_version": "narrative-read-request/1", "narrative_ref": reference,
            "as_of_date": "2026-09-01", "expected_source": fixture.expected_source,
        })
        assert result.returncode == 2
        assert result.stdout == b""
        assert json.loads(result.stderr)["status"] != "ok"


def test_missing_catalog_cli_does_not_create_or_migrate_storage(tmp_path: Path) -> None:
    root = tmp_path / "missing-catalog"
    root.mkdir()
    config = root / "config.json"
    raw = root / "raw"
    raw.mkdir()
    missing = root / "not-created"
    config.write_text(json.dumps({
        "schema_version": "1.0", "catalog_dir": str(missing),
        "roots": [{"root_id": "isolated", "path": str(raw), "kind": "directory",
                   "adapter_id": "sidecar_filing_v1", "read_only": True,
                   "reusable_for_filing": True}],
        "reusable_root_kinds": ["directory"],
    }), encoding="utf-8")
    before = tuple(sorted(p.relative_to(root).as_posix() for p in root.rglob("*")))
    try:
        result = _cli(SimpleNamespace(root=root, config_path=config), "reference", {
            "schema_version": "narrative-reference-request/1",
            "source_ref": {
                "schema_version": "2.0", "document_id": "missing-document",
                "source_id": source_id_for_sha256("a" * 64),
                "content_sha256": "a" * 64, "byte_size": 1, "mime_type": "text/plain",
            },
        })
        assert result.returncode == 2
        assert result.stdout == b""
        assert not missing.exists()
        assert tuple(sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))) == before
    finally:
        import shutil
        shutil.rmtree(root)


def test_current_public_producer_regenerates_normalized_txt_golden(tmp_path: Path) -> None:
    directory = REPO / "tests" / "fixtures" / "narrative_transport_v1"
    with published_fixture(tmp_path) as fixture:
        reference = _reference(fixture)
        result = _cli(fixture, "read", {
            "schema_version": "narrative-read-request/1", "narrative_ref": reference,
            "as_of_date": "2026-09-01", "expected_source": fixture.expected_source,
        })
        assert result.returncode == 0
        bundle = json.loads(result.stdout)
        # Deployment policy hashes and generated version IDs differ per scratch
        # installation; all semantic fields and source/span hashes remain exact.
        bundle["expected_read_policy_sha256"] = "f" * 64
        normalized_bytes = canonical_json(bundle).encode("utf-8")
        assert normalized_bytes == (directory / "bundle.json").read_bytes()
        reference["artifact_version_id"] = "narrative-golden-txt-v1"
        reference["artifact_sha256"] = hashlib.sha256(normalized_bytes).hexdigest()
        reference["byte_size"] = len(normalized_bytes)
        assert reference == json.loads((directory / "reference.json").read_bytes())
        receipt = json.loads(result.stderr)
        receipt["narrative_ref"] = reference
        receipt["source_read_policy_sha256"] = "f" * 64
        receipt["read_at"] = "2026-10-03T00:00:00Z"
        assert receipt == json.loads((directory / "read_receipt.json").read_bytes())
