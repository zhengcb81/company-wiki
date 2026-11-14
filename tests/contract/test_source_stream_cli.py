"""Public stream transport contract over the current stream_version owner.

The wire is additive to the whole-buffer reader's 2.1 receipts: one ``locked``
line, provisional bytes on stdout, one final ``ok`` or five-value refusal.
Admission, verification, budget and cancellation stay in the owner; this
contract pins what a consumer may rely on and what the transport refuses.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

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
    scratch = config.parent / "stream-scratch"
    scratch.mkdir(exist_ok=True)
    for key in ("TMP", "TEMP", "TMPDIR"):
        env[key] = str(scratch)
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
def lake(tmp_path: Path, request):
    catalog, original, identity = _catalog(tmp_path, body=getattr(request, "param", BODY))
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
    # No byte crossed the pipe, so no lock line precedes the refusal and no
    # ok ever exists: the consumer's first receipt is the refusal itself.
    assert len(receipts) == 1
    assert receipts[0]["status"] == "unavailable"
    assert "ok" not in {receipt["status"] for receipt in receipts}


def test_stream_cli_same_size_tamper_refuses_before_exposing_any_bytes(lake):
    original = lake["original"].read_bytes()
    tampered = bytes((byte + 7) % 256 for byte in original)
    assert len(tampered) == len(original)
    old_stat = lake["original"].stat()
    lake["original"].write_bytes(tampered)
    os.utime(lake["original"], ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
    result = _run_cli(
        lake["config"],
        document_id=lake["identity"]["document_id"],
        source_id=lake["identity"]["source_id"],
        sha=lake["identity"]["content_sha256"],
    )
    assert result.returncode == 2
    assert result.stdout == b""
    receipts = _receipts(result.stderr)
    assert [receipt["status"] for receipt in receipts] == ["unavailable"]
    assert list(lake["config"].parent.joinpath("stream-scratch").iterdir()) == []


@pytest.mark.parametrize("lake", [BODY + b"a" * (2 * 1024 * 1024)], indirect=True, ids=["multi-chunk"])
def test_stream_cli_first_stdout_write_cannot_change_the_committed_snapshot(lake, capsys, monkeypatch):
    from company_wiki.source_catalog.source_stream_cli import main

    original = lake["original"].read_bytes()
    replacement = original[:len(BODY)] + b"b" * (len(original) - len(BODY))

    class ReplaceDuringTransfer(io.BytesIO):
        changed = False

        def write(self, data):
            if not self.changed:
                lake["original"].write_bytes(replacement)
                self.changed = True
            return super().write(data)

    stdout = ReplaceDuringTransfer()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", SimpleNamespace(buffer=stdout))
        assert main([
            "--config", str(lake["config"]),
            "--document-id", lake["identity"]["document_id"],
            "--source-id", lake["identity"]["source_id"],
            "--content-sha256", lake["identity"]["content_sha256"],
        ]) == 0
    assert stdout.changed
    assert hashlib.sha256(stdout.getvalue()).digest() == hashlib.sha256(original).digest()
    assert hashlib.sha256(lake["original"].read_bytes()).digest() == hashlib.sha256(replacement).digest()
    assert [r["status"] for r in _receipts(capsys.readouterr().err.encode())] == ["locked", "ok"]


def test_stream_staging_does_not_publish_on_scratch_failure(lake, capsys, monkeypatch):
    import tempfile

    from company_wiki.source_catalog.source_stream_cli import main

    def disk_full(**_):
        raise OSError("scratch volume full")

    stdout = io.BytesIO()
    with monkeypatch.context() as patch:
        patch.setattr(tempfile, "TemporaryFile", disk_full)
        patch.setattr(sys, "stdout", SimpleNamespace(buffer=stdout))
        with pytest.raises(SystemExit) as refusal:
            main([
                "--config", str(lake["config"]),
                "--document-id", lake["identity"]["document_id"],
                "--source-id", lake["identity"]["source_id"],
                "--content-sha256", lake["identity"]["content_sha256"],
            ])
    assert refusal.value.code == 2
    assert stdout.getvalue() == b""
    assert _receipts(capsys.readouterr().err.encode()) == [
        {"schema_version": "2.2", "status": "unavailable", "reason": "stream_staging_unavailable"},
    ]


def test_stream_cli_keeps_the_original_bytes_unchanged(lake):
    result = _run_cli(
        lake["config"],
        document_id=lake["identity"]["document_id"],
        source_id=lake["identity"]["source_id"],
        sha=lake["identity"]["content_sha256"],
    )
    assert result.returncode == 0
    assert lake["original"].read_bytes() == BODY
    assert list(lake["config"].parent.joinpath("stream-scratch").iterdir()) == []


def _run_with_stream_pipes(lake, monkeypatch, *, stdout, stderr):
    from company_wiki.source_catalog.source_stream_cli import main

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", SimpleNamespace(buffer=stdout))
        patch.setattr(sys, "stderr", stderr)
        return main([
            "--config", str(lake["config"]),
            "--document-id", lake["identity"]["document_id"],
            "--source-id", lake["identity"]["source_id"],
            "--content-sha256", lake["identity"]["content_sha256"],
        ])


@pytest.mark.parametrize("failed_receipt", ["locked", "ok"])
def test_stream_cli_cannot_succeed_without_a_delivered_receipt(lake, monkeypatch, failed_receipt):
    class BrokenReceiptPipe(io.StringIO):
        def write(self, line):
            if json.loads(line)["status"] == failed_receipt:
                raise BrokenPipeError("consumer closed diagnostics pipe")
            return super().write(line)

    stdout, stderr = io.BytesIO(), BrokenReceiptPipe()
    with pytest.raises(SystemExit) as refusal:
        _run_with_stream_pipes(lake, monkeypatch, stdout=stdout, stderr=stderr)
    assert refusal.value.code == 2
    if failed_receipt == "locked":
        assert not stdout.getvalue()
    assert all(row["status"] != "ok" for row in _receipts(stderr.getvalue().encode()))


def test_stream_cli_reports_success_only_after_a_complete_stdout_write(lake, monkeypatch):
    class ShortOutputPipe(io.BytesIO):
        def write(self, data):
            return super().write(data[:7])

    stdout, stderr = ShortOutputPipe(), io.StringIO()
    assert _run_with_stream_pipes(lake, monkeypatch, stdout=stdout, stderr=stderr) == 0
    assert stdout.getvalue() == BODY
    assert [row["status"] for row in _receipts(stderr.getvalue().encode())] == ["locked", "ok"]
