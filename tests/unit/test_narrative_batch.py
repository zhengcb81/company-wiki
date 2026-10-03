"""Batch application contracts: deterministic work and physical byte limits."""

from dataclasses import replace
import importlib

import pytest

from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.source_catalog.source_reader import SourceRef
from company_wiki.source_contract.source_manifest import source_id_for_sha256


def _request():
    digest = "a" * 64
    return NarrativeBatchRequest.from_dict({
        "schema_version": "narrative-batch-request/1", "run_id": "batch-a",
        "sources": [{"schema_version": "2.0", "document_id": "doc-a",
                     "source_id": source_id_for_sha256(digest), "content_sha256": digest,
                     "byte_size": 123, "mime_type": "text/plain"}],
        "profile": "P2", "max_seconds": 30, "max_tokens": 100_000,
        "max_cost_usd": "0.1",
        "model": {"model_id": "local-model", "endpoint": "https://example.invalid/v1/chat/completions",
                  "api_key_env": "BATCH_TEST_KEY"},
        "pricing": {"version": "test/1", "input_micro_usd_per_million_tokens": 300_000,
                    "output_micro_usd_per_million_tokens": 1_200_000},
    })


class Reader:
    def __init__(self):
        self.metadata = {"title": "Company call", "document_kind": "investor_call_transcript", "language": "en"}

    def query_ref(self, document_id, source_id, content_sha256):
        return SourceRef(document_id, source_id, content_sha256, 123, "text/plain")

    def describe_version(self, ref):
        return dict(self.metadata)

    def read_policy_sha256(self):
        return "b" * 64


def _module():
    return importlib.import_module("company_wiki.automation.narrative_batch")


def test_batch_identity_binds_execution_configuration_and_preserves_source_metadata():
    module = _module()
    request, reader = _request(), Reader()
    first = module.build_batch_events(request, reader, now="2026-10-03T10:00:00Z")
    second = module.build_batch_events(request, reader, now="2026-10-03T11:00:00Z")
    assert first.input_hash == second.input_hash
    assert first.events[0].event_id == second.events[0].event_id
    payload = __import__("json").loads(first.events[0].payload_json)
    assert payload["source_metadata"] == {**reader.metadata, "source_class": "transcript"}
    for changed in (replace(request, run_id="batch-b"), replace(request, model_options_json=canonical_json({
        **request.model_options, "model_id": "other-model"})), replace(request, max_tokens=99_999)):
        assert module.build_batch_events(changed, reader, now="2026-10-03T10:00:00Z").events[0].event_id != first.events[0].event_id


def test_batch_identity_includes_catalog_metadata_and_read_policy():
    module = _module()
    request, reader = _request(), Reader()
    first = module.build_batch_events(request, reader, now="2026-10-03T10:00:00Z")
    reader.metadata["title"] = "New captured title"
    assert module.build_batch_events(request, reader, now="2026-10-03T10:00:00Z").input_hash != first.input_hash
    reader.metadata["title"] = "Company call"
    reader.read_policy_sha256 = lambda: "c" * 64
    assert module.build_batch_events(request, reader, now="2026-10-03T10:00:00Z").input_hash != first.input_hash


def test_batch_rejects_a_reference_whose_size_changed():
    reader = Reader()
    reader.query_ref = lambda *args: SourceRef(args[0], args[1], args[2], 124, "text/plain")
    with pytest.raises(ValueError, match="SOURCE_REF_CHANGED"):
        _module().build_batch_events(_request(), reader, now="2026-10-03T10:00:00Z")


def test_storage_guard_counts_database_wal_objects_and_logs_but_excludes_raw(tmp_path):
    raw = tmp_path / "raw.pdf"
    raw.write_bytes(b"original" * 100)
    db = tmp_path / "auto.db"
    db.write_bytes(b"old")
    objects = tmp_path / "objects"
    objects.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()
    guard = _module().BatchStorageBudget(files=(db, tmp_path / "auto.db-wal"),
        persistent_dirs=(objects, logs), scratch_dirs=(), max_persistent_bytes=10, max_scratch_bytes=10)
    db.write_bytes(b"old+new")
    (tmp_path / "auto.db-wal").write_bytes(b"12")
    (objects / "bundle.json").write_bytes(b"34")
    (logs / "compute.log").write_bytes(b"56")
    assert guard.snapshot().persistent_added_bytes == 10
    assert guard.snapshot().scratch_bytes == 0
    guard.check()
    (logs / "compute.log").write_bytes(b"567")
    with pytest.raises(ValueError, match="PERSISTENT_BYTES_EXCEEDED"):
        guard.check()
    assert raw.read_bytes() == b"original" * 100


def test_storage_guard_scratch_peak_is_not_reported_as_persistent_growth(tmp_path):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    guard = _module().BatchStorageBudget(files=(), persistent_dirs=(), scratch_dirs=(scratch,),
        max_persistent_bytes=10, max_scratch_bytes=5)
    (scratch / "partial").write_bytes(b"123456")
    with pytest.raises(ValueError, match="SCRATCH_BYTES_EXCEEDED"):
        guard.check()
    (scratch / "partial").unlink()
    assert guard.snapshot().scratch_peak_bytes == 6
    assert guard.snapshot().persistent_added_bytes == 0


def test_cli_error_is_static_and_does_not_echo_request_secrets(tmp_path, capsys):
    cli = importlib.import_module("company_wiki.automation.narrative_batch_cli")
    request = tmp_path / "request.json"
    request.write_text('{"api_key":"never-print-this-secret"}', encoding="utf-8")
    code = cli.main(["--project-root", str(tmp_path), "--catalog-config", str(tmp_path / "c.json"),
                     "--automation-db", str(tmp_path / "auto.db"), "--work-dir", str(tmp_path / "work"),
                     "--request", str(request)])
    assert code == 1
    captured = capsys.readouterr()
    assert "never-print-this-secret" not in captured.out + captured.err
    assert "NARRATIVE_BATCH_INVALID_REQUEST" in captured.out
