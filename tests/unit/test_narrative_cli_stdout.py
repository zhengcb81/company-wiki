"""The CLI owns its JSON channel even when a dependency prints diagnostics."""

from io import StringIO
import json
import os
import sys

import pytest

from company_wiki.automation import narrative_batch_cli as cli
from company_wiki.automation.models import canonical_json
from company_wiki.source_contract import source_id_for_sha256


@pytest.fixture
def arguments(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({
        "schema_version": "narrative-batch-request/1", "run_id": "stdout-contract",
        "sources": [{"schema_version": "2.0", "document_id": "test-document",
                     "source_id": source_id_for_sha256("a" * 64), "content_sha256": "a" * 64,
                     "byte_size": 100, "mime_type": "text/plain"}],
        "profile": "P2", "max_seconds": 30, "max_tokens": 1000, "max_cost_usd": "0",
        "model": {"model_id": "never-called-test-model", "endpoint": "https://example.invalid/v1/chat/completions",
                  "api_key_env": "UNUSED_STDOUT_TEST_KEY"},
        "pricing": {"version": "test/1", "input_micro_usd_per_million_tokens": 1,
                    "output_micro_usd_per_million_tokens": 1},
    }), encoding="utf-8")
    return ["--project-root", str(tmp_path), "--catalog-config", str(tmp_path / "catalog.json"),
            "--automation-db", str(tmp_path / "auto.sqlite3"), "--work-dir", str(tmp_path / "work"),
            "--request", str(request)]


@pytest.mark.parametrize("writer", ["parser-print", "provider-print", "descriptor-write"])
def test_noisy_dependency_success_keeps_exactly_one_json_on_stdout(arguments, monkeypatch, capfd, writer):
    expected = {"schema_version": "narrative-batch-result/1", "run_id": "stdout-contract", "status": "completed"}
    calls = []

    def operation(request, **kwargs):
        calls.append(request.run_id)
        if writer == "descriptor-write":
            os.write(1, b"native-library diagnostic\n")
        else:
            print("Consider using library helper" if writer == "parser-print" else "provider retry diagnostic")
        return expected

    monkeypatch.setattr(cli, "run_batch", operation)
    assert cli.main(arguments) == 0
    captured = capfd.readouterr()
    assert captured.out == canonical_json(expected) + "\n"
    assert json.loads(captured.out) == expected
    assert "diagnostic" in captured.err or "Consider using" in captured.err
    assert calls == ["stdout-contract"]
    # The descriptor is restored after leaving the operation boundary.
    os.write(1, b"stdout restored\n")
    assert capfd.readouterr().out == "stdout restored\n"


@pytest.mark.parametrize("exception,error,status,exit_code", [
    (cli.BatchPreparationDeadlineExceeded("deadline"), "BATCH_PREPARATION_DEADLINE_EXCEEDED", "failed", 2),
    (cli.NarrativeLanguageError("SOURCE_LANGUAGE_UNDETERMINED"), "SOURCE_LANGUAGE_UNDETERMINED", "failed", 2),
    (cli.SourceReadError("not_found", "SOURCE_NOT_FOUND", "synthetic detail"), "SOURCE_NOT_FOUND", "failed", 2),
    (cli.BatchResumeError("BATCH_WORK_DIR_CONFLICT"), "BATCH_WORK_DIR_CONFLICT", "failed", 2),
    (ValueError("PERSISTENT_BYTES_EXCEEDED"), "NARRATIVE_BATCH_ValueError", "storage_exhausted", 2),
    (RuntimeError("provider body with private synthetic detail"), "NARRATIVE_BATCH_RuntimeError", "failed", 1),
])
def test_noisy_error_and_ledger_projection_use_stderr_and_preserve_public_error(arguments, monkeypatch, capfd, exception, error, status, exit_code):
    def operation(request, **kwargs):
        print("provider transport diagnostic")
        os.write(1, b"native parser diagnostic\n")
        raise exception

    original_failure = cli._failure_receipt

    def failure(*args):
        print("ledger projection diagnostic")
        return original_failure(*args)

    monkeypatch.setattr(cli, "run_batch", operation)
    monkeypatch.setattr(cli, "_failure_receipt", failure)
    assert cli.main(arguments) == exit_code
    captured = capfd.readouterr()
    parsed = json.loads(captured.out)
    assert captured.out == canonical_json(parsed) + "\n"
    assert parsed["status"] == status
    assert parsed["error"] == error
    assert "synthetic detail" not in captured.out
    assert "private synthetic detail" not in captured.out
    assert "provider transport diagnostic" in captured.err
    assert "native parser diagnostic" in captured.err
    assert "ledger projection diagnostic" in captured.err
    os.write(1, b"stdout restored after error\n")
    assert capfd.readouterr().out == "stdout restored after error\n"


@pytest.mark.parametrize("status", ["partial", "failed", "storage_exhausted"])
def test_noisy_noncompleted_receipt_keeps_original_exit_semantics(arguments, monkeypatch, capfd, status):
    def operation(request, **kwargs):
        print("provider status diagnostic")
        return {"schema_version": "narrative-batch-result/1", "status": status}

    monkeypatch.setattr(cli, "run_batch", operation)
    assert cli.main(arguments) == 2
    captured = capfd.readouterr()
    assert json.loads(captured.out)["status"] == status
    assert captured.out.count("\n") == 1
    assert captured.err == "provider status diagnostic\n"


def test_python_stream_embedding_without_descriptors_still_separates_diagnostics(arguments, monkeypatch):
    stdout, stderr = StringIO(), StringIO()

    def operation(request, **kwargs):
        print("embedded parser diagnostic")
        return {"status": "completed"}

    monkeypatch.setattr(cli, "run_batch", operation)
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)
    assert cli.main(arguments) == 0
    assert json.loads(stdout.getvalue()) == {"status": "completed"}
    assert stderr.getvalue() == "embedded parser diagnostic\n"
    assert sys.stdout is stdout and sys.stderr is stderr


def test_invalid_request_has_one_json_and_never_enters_operation(arguments, monkeypatch, capfd):
    request_index = arguments.index("--request") + 1
    from pathlib import Path
    Path(arguments[request_index]).write_text("not JSON", encoding="utf-8")

    def forbidden(*args, **kwargs):
        pytest.fail("invalid request entered operation")

    monkeypatch.setattr(cli, "run_batch", forbidden)
    assert cli.main(arguments) == 1
    captured = capfd.readouterr()
    assert json.loads(captured.out)["error"] == "NARRATIVE_BATCH_INVALID_REQUEST"
    assert captured.out.count("\n") == 1
