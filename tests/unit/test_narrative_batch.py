"""Batch application contracts: deterministic work and physical byte limits."""

from dataclasses import replace
import hashlib
import importlib
from pathlib import Path
from types import SimpleNamespace

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


class SparseMetadataReader(Reader):
    def __init__(self, body, mime_type="text/plain"):
        super().__init__()
        self.metadata.update(title=None, language=None)
        self.body = body
        self.mime_type = mime_type
        self.open_calls = []
        self.sha256 = hashlib.sha256(body).hexdigest()

    def query_ref(self, document_id, source_id, content_sha256):
        return SourceRef(
            document_id, source_id, content_sha256, len(self.body), self.mime_type
        )

    def open_version(
        self, ref, *, purpose, expected_read_policy_sha256=None
    ):
        self.open_calls.append((purpose, expected_read_policy_sha256))
        return SimpleNamespace(
            document_id=ref.document_id,
            source_id=ref.source_id,
            content_sha256=self.sha256,
            data=self.body,
            byte_size=len(self.body),
            source_read_policy_sha256=expected_read_policy_sha256,
        )


def _module():
    return importlib.import_module("company_wiki.automation.narrative_batch")


@pytest.mark.parametrize("name", ["catalog.db-shm", "artifact.tmp"])
def test_owned_storage_sample_tolerates_file_removal_between_stats(tmp_path, monkeypatch, name):
    transient = tmp_path / name
    transient.write_bytes(b"transient")
    original_stat = Path.stat
    seen = False

    def stat_then_remove(path, *args, **kwargs):
        nonlocal seen
        result = original_stat(path, *args, **kwargs)
        if path == transient and not seen:
            seen = True
            path.unlink()
        return result

    monkeypatch.setattr(Path, "stat", stat_then_remove)
    # The file existed for one instant during the sample. Either observation
    # is valid; aborting a whole batch because it was reclaimed is not.
    assert _module()._tree_bytes(tmp_path) in {0, len(b"transient")}
    assert seen and not transient.exists()


def test_owned_storage_sample_preserves_access_errors(tmp_path, monkeypatch):
    inaccessible = tmp_path / "catalog.db"
    inaccessible.write_bytes(b"retained")
    original_stat = Path.stat

    def reject_stat(path, *args, **kwargs):
        if path == inaccessible:
            raise PermissionError("fixture storage is inaccessible")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", reject_stat)
    with pytest.raises(PermissionError):
        _module()._tree_bytes(tmp_path)


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


def test_batch_thinking_control_is_optional_and_binds_run_generation():
    original = _request()
    wire = original.to_dict()
    assert "thinking" not in wire["model"]
    assert NarrativeBatchRequest.from_dict(wire).input_hash == original.input_hash
    wire["model"]["thinking"] = "disabled"
    disabled = NarrativeBatchRequest.from_dict(wire)
    assert disabled.model_options["thinking"] == "disabled"
    assert disabled.input_hash != original.input_hash
    wire["model"]["thinking"] = "adaptive"
    assert NarrativeBatchRequest.from_dict(wire).input_hash != disabled.input_hash


def test_current_selection_never_reuses_pre_n4t2_batch_hash(monkeypatch):
    # Published 0.2.0 predates the Chinese business-progress/empty-result fix.
    # Reusing its run identity would silently retain old selected evidence.
    request_module = importlib.import_module(
        "company_wiki.automation.narrative_batch_request"
    )
    module = _module()
    request, reader = _request(), Reader()
    current = module.build_batch_events(request, reader, now="2026-10-05T12:00:00Z")
    with monkeypatch.context() as legacy:
        legacy.setattr(request_module, "NARRATIVE_SELECTOR_VERSION", "0.2.0")
        previous = module.build_batch_events(
            request, reader, now="2026-10-05T12:00:00Z"
        )

    assert current.input_hash != previous.input_hash
    assert current.events[0].event_id != previous.events[0].event_id


def test_batch_infers_missing_language_from_verified_source_bytes_and_pins_it():
    body = (
        "Full Conference Call Transcript\nCEO: 公司完成海外产能扩张，"
        "新产品已进入量产。\n"
    ).encode("utf-8")
    digest = hashlib.sha256(body).hexdigest()
    request_wire = _request().to_dict()
    request_wire["sources"][0].update(
        source_id=source_id_for_sha256(digest), content_sha256=digest,
        byte_size=len(body), mime_type="text/plain",
    )
    request = NarrativeBatchRequest.from_dict(request_wire)
    reader = SparseMetadataReader(body)

    first = _module().build_batch_events(
        request, reader, now="2026-10-03T10:00:00Z"
    )
    second = _module().build_batch_events(
        request, reader, now="2026-10-03T11:00:00Z"
    )
    payload = __import__("json").loads(first.events[0].payload_json)

    assert payload["source_metadata"]["language"] == "zh"
    assert payload["source_metadata"]["title"] is None
    assert first.input_hash == second.input_hash
    assert len(reader.open_calls) == 2
    assert all(
        call == ("narrative_derivation", "b" * 64)
        for call in reader.open_calls
    )


def test_batch_infers_missing_language_from_verified_pdf_bytes():
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    try:
        document.new_page().insert_text(
            (72, 72),
            "The company expanded overseas capacity and launched a new product.",
        )
        body = document.tobytes()
    finally:
        document.close()
    digest = hashlib.sha256(body).hexdigest()
    request_wire = _request().to_dict()
    request_wire["sources"][0].update(
        source_id=source_id_for_sha256(digest), content_sha256=digest,
        byte_size=len(body), mime_type="application/pdf",
    )
    request = NarrativeBatchRequest.from_dict(request_wire)
    reader = SparseMetadataReader(body, mime_type="application/pdf")

    events = _module().build_batch_events(
        request, reader, now="2026-10-03T10:00:00Z"
    )
    payload = __import__("json").loads(events.events[0].payload_json)

    assert payload["source_metadata"]["language"] == "en"
    assert reader.open_calls == [("narrative_derivation", "b" * 64)]


def test_batch_rejects_language_bytes_that_do_not_match_the_source_ref():
    body = b"Full Conference Call Transcript\nCEO: New product launch.\n"
    digest = hashlib.sha256(body).hexdigest()
    request_wire = _request().to_dict()
    request_wire["sources"][0].update(
        source_id=source_id_for_sha256(digest), content_sha256=digest,
        byte_size=len(body), mime_type="text/plain",
    )
    request = NarrativeBatchRequest.from_dict(request_wire)
    reader = SparseMetadataReader(body)
    reader.sha256 = "0" * 64

    with pytest.raises(ValueError, match="SOURCE_LANGUAGE_SOURCE_MISMATCH"):
        _module().build_batch_events(
            request, reader, now="2026-10-03T10:00:00Z"
        )


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
