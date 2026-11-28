"""Live subprocess checks at company-wiki's diagnostic boundary."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


_SRC = Path(__file__).resolve().parents[2] / "src"
_RUNTIME_ENV = {
    "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC", "PATH", "PATHEXT", "TEMP", "TMP",
    "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "LANG", "LC_ALL",
}
_RUN = "synthetic-s6-original-run"
_ATTEMPT = "synthetic-s6-original-attempt"


def _environment(root: Path) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key.upper() in _RUNTIME_ENV}
    env.update(
        LOCALAPPDATA=str(root / "state"),
        XDG_STATE_HOME=str(root / "state"),
        PYTHONUTF8="1",
        PYTHONPATH=str(_SRC),
        RESEARCH_FEEDBACK_RUN_ID=_RUN,
        RESEARCH_FEEDBACK_ATTEMPT_ID=_ATTEMPT,
    )
    return env


def _run(root: Path, env: dict[str, str], *argv: str, stdin: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-B", *argv], input=stdin, capture_output=True, cwd=root, env=env,
        timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False,
    )


def _cold_read(root: Path, env: dict[str, str]) -> dict:
    proc = _run(root, env, "-m", "company_wiki.runtime_trace",
                "--run-id", _RUN, "--attempt-id", _ATTEMPT)
    assert proc.returncode == 0
    return json.loads(proc.stdout)


def _block(path: Path) -> None:
    path.write_bytes(b"original blocker sentinel")


def _artifacts(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not path.name.endswith((".lock", ".py"))
    }


@pytest.mark.parametrize("layout", ("healthy", "fallback", "unavailable"))
def test_t3_preserves_failure_and_original_identity(tmp_path, layout):
    env = _environment(tmp_path)
    if layout != "healthy":
        primary = tmp_path / "occupied-primary"
        owner = tmp_path / "state"
        _block(primary)
        _block(owner)
        env["RESEARCH_FEEDBACK_OUT"] = str(primary / "feedback.jsonl")
        if layout == "fallback":
            env["RESEARCH_FEEDBACK_DIR"] = str(tmp_path / "fallback" / "observations")
    proc = _run(
        tmp_path, env, "-m", "company_wiki.source_catalog.t3_workspace_cli",
        "--workspace-root", str(tmp_path / "not-opened"),
        stdin=b'{"schema_version":"synthetic-invalid"}',
    )
    assert proc.returncode == 2
    assert json.loads(proc.stdout) == {
        "schema_version": "cwp-t3-workspace/1", "status": "failed", "error_code": "invalid_request",
    }
    assert not (tmp_path / "not-opened").exists()
    if layout == "unavailable":
        notice, = proc.stderr.decode("utf-8").splitlines()
        assert "diagnostic" in notice.lower()
        assert str(tmp_path) not in notice
        assert _artifacts(tmp_path) == {"occupied-primary": b"original blocker sentinel",
                                        "state": b"original blocker sentinel"}
        return
    assert proc.stderr == b""
    before = _artifacts(tmp_path)
    trace = _cold_read(tmp_path, env)
    assert _artifacts(tmp_path) == before
    assert trace["status"] == "available" and trace["run_id"] == _RUN and trace["attempt_id"] == _ATTEMPT
    assert trace["events"][0]["status"] == "started"
    assert trace["events"][-1]["status"] == "failed" and trace["events"][-1]["exit_code"] == 2
    assert all(len(event["implementation_sha256"]) == 64 for event in trace["events"])
    original, = trace["diagnostics"]
    assert original["reason"] == "invalid_request"
    assert original["exceptions"][0]["type"] == "WorkspaceError"
    assert original["exceptions"][0]["locations"][-1][0] == "t3_workspace_cli.py"


def test_original_machine_stderr_survives_lost_diagnostic_sinks(tmp_path):
    normal = _environment(tmp_path)
    request = ("-m", "company_wiki.source_catalog.source_stream_cli")
    baseline = _run(tmp_path, normal, *request)
    assert (baseline.returncode, baseline.stdout) == (2, b"")
    assert json.loads(baseline.stderr)["reason"] == "invalid_request"

    bad = tmp_path / "bad"
    bad.mkdir()
    broken = _environment(bad)
    explicit = bad / "occupied-primary"
    _block(explicit)
    _block(bad / "state")
    broken["RESEARCH_FEEDBACK_OUT"] = str(explicit / "feedback.jsonl")
    state = _artifacts(bad)
    outage = _run(bad, broken, *request)
    assert (outage.returncode, outage.stdout, outage.stderr) == (2, b"", baseline.stderr)
    assert _artifacts(bad) == state


def test_original_diagnostic_keeps_tail_stack_and_no_credential(tmp_path):
    fixture = tmp_path / "failing_owner_call.py"
    secrets = (
        "folded-opaque-S6-bearer-0123456789",
        "folded-opaque-S6-basic-0123456789",
        "synthetic-user-name", "synthetic-encoded-pass",
        "sk-S6Synth0001234567890", "tvly-S6Synth0001234567890",
        "ghp_S6Synth0001234567890", "AIzaS6Synth0001234567890",
    )
    unsafe = (
        "a" * 12_000 + "\nAuthorization: Bearer\n  " + secrets[0]
        + "\nAuthorization: Basic\n  " + secrets[1]
        + "\nurl https://" + secrets[2] + ":" + secrets[3] + "@127.0.0.1/example\n"
        + " ".join(secrets[4:]) + "\noriginal failure tail"
    )
    fixture.write_text(
        "from company_wiki import runtime_feedback\n"
        "class FixtureConfigFault(Exception): pass\n"
        "def open_configuration():\n"
        f"    raise FixtureConfigFault({unsafe!r})\n"
        "@runtime_feedback.entry('fixture-owner')\n"
        "def main():\n"
        "    try:\n"
        "        open_configuration()\n"
        "    except FixtureConfigFault as exc:\n"
        "        runtime_feedback.record('fixture-owner', 'failed', reason='fixture_input_fault', error=exc)\n"
        "        print('{\"status\":\"failed\"}')\n"
        "        return 41\n"
        "raise SystemExit(main())\n",
        encoding="utf-8",
    )
    env = _environment(tmp_path)
    output = _run(tmp_path, env, str(fixture))
    assert (output.returncode, json.loads(output.stdout), output.stderr) == (41, {"status": "failed"}, b"")
    trace = _cold_read(tmp_path, env)
    original, = trace["diagnostics"]
    cause, = original["exceptions"]
    assert cause["type"] == "FixtureConfigFault"
    assert cause["locations"][-1] == ["failing_owner_call.py", "open_configuration", 4]
    assert "original failure tail" in cause["messages"][0]
    assert "127.0.0.1/example" in cause["messages"][0]
    for marker in secrets:
        assert all(marker.encode() not in value for value in _artifacts(tmp_path).values())


def test_concurrent_library_invocations_do_not_duplicate_logger_outputs(tmp_path):
    fixture = tmp_path / "parallel_owner_calls.py"
    fixture.write_text(
        "from concurrent.futures import ThreadPoolExecutor\n"
        "import logging\n"
        "from threading import Barrier\n"
        "from company_wiki.runtime_feedback import entry\n"
        "barrier = Barrier(2, timeout=10)\n"
        "@entry('first-operation')\n"
        "def first():\n"
        "    barrier.wait()\n"
        "    logging.getLogger('company_wiki.fixture').warning('fixture phase first')\n"
        "    barrier.wait()\n"
        "    return 0\n"
        "@entry('second-operation')\n"
        "def second():\n"
        "    barrier.wait()\n"
        "    logging.getLogger('company_wiki.fixture').warning('fixture phase second')\n"
        "    barrier.wait()\n"
        "    return 0\n"
        "with ThreadPoolExecutor(max_workers=2) as executor:\n"
        "    pending = [executor.submit(first), executor.submit(second)]\n"
        "    assert [task.result() for task in pending] == [0, 0]\n",
        encoding="utf-8",
    )
    env = _environment(tmp_path)
    del env["RESEARCH_FEEDBACK_RUN_ID"], env["RESEARCH_FEEDBACK_ATTEMPT_ID"]
    output = _run(tmp_path, env, str(fixture))
    assert output.returncode == 0
    local = (tmp_path / "state" / "company-wiki" / "logs" / "runtime_errors.log").read_text("utf-8")
    assert local.count("fixture phase first") == local.count("fixture phase second") == 1



def test_automation_usage_error_is_observed_before_dispatch(tmp_path):
    env = _environment(tmp_path)
    opaque = "ghp_UsageFixtureOriginal000000"
    outcome = _run(tmp_path, env, "-m", "company_wiki.automation.cli", opaque)
    assert (outcome.returncode, outcome.stdout) == (2, b"")
    assert b"invalid choice" in outcome.stderr and opaque.encode() not in outcome.stderr
    trace = _cold_read(tmp_path, env)
    reason, = trace["diagnostics"]
    assert reason["reason"] == "invalid_arguments"
    assert trace["events"][-1]["exit_code"] == 2
    assert all(opaque.encode() not in data for data in _artifacts(tmp_path).values())


def test_feedback_recovery_failure_has_owner_trace_without_recursive_issue(tmp_path):
    env = _environment(tmp_path)
    env["PYTHONPATH"] += os.pathsep + str(_SRC.parent)
    outcome = _run(
        tmp_path, env, "-m", "tools.feedback_loop.local_host", "--config",
        str(tmp_path / "missing-settings.json"), "recover", "--save-result",
    )
    assert (outcome.returncode, outcome.stdout) == (1, b"")
    receipt = json.loads((tmp_path / "last-native-recovery.json").read_bytes())
    assert receipt["error_type"] == "FileNotFoundError"
    trace = _cold_read(tmp_path, env)
    assert trace["status"] == "available" and trace["events"][-1]["exit_code"] == 1
    native, = trace["diagnostics"]
    assert any(cause["type"] == "FileNotFoundError" for cause in native["exceptions"])
    assert not list(tmp_path.rglob("*.ready"))
    assert not list(tmp_path.rglob("feedback-*.jsonl"))


def test_bound_t3_cause_preserves_owner_class_for_f4(tmp_path):
    from tools.feedback_loop.observations import decode_observation
    from tools.feedback_loop.triage_diagnostic import native_diagnostic_facts

    env = _environment(tmp_path)
    outcome = _run(
        tmp_path, env, "-m", "company_wiki.source_catalog.t3_workspace_cli",
        "--workspace-root", str(tmp_path / "not-opened"), stdin=b"{}",
    )
    assert outcome.returncode == 2
    row_path, = tmp_path.rglob("feedback-*.jsonl")
    row = decode_observation(row_path.read_bytes())
    observed = native_diagnostic_facts(row, "company-wiki", [row_path.parent])
    assert observed["status"] == "available"
    assert observed["exceptions"] == [{"type": "WorkspaceError"}]


@pytest.mark.windows_native
@pytest.mark.skipif(os.name != "nt", reason="Windows readers can deny rename while permitting append")
def test_rotation_keeps_previous_log_when_reader_holds_active_file(tmp_path):
    current = tmp_path / "owner#%/runtime_errors.log"
    current.parent.mkdir()
    current.write_bytes(b"x" * (2 * 1024 * 1024))
    archived = current.with_suffix(".log.1")
    archived.write_bytes(b"earlier cold-read evidence\n")
    with current.open("rb"):
        outcome = _run(
            tmp_path, _environment(tmp_path), "-c",
            "import sys; from pathlib import Path; from company_wiki.diagnostic_logging import append_diagnostic; "
            "raise SystemExit(not append_diagnostic(Path(sys.argv[1]), 'original rollover event'))",
            str(current),
        )
    assert (outcome.returncode, outcome.stdout, outcome.stderr) == (0, b"", b"")
    assert archived.read_bytes() == b"earlier cold-read evidence\n"
    assert current.read_bytes().count(b"original rollover event") == 1




@pytest.mark.parametrize(("module", "arguments"), (
    ("company_wiki.runtime_trace", ("--run-id", "original", "--unknown={opaque}")),
    ("company_wiki.source_catalog.incremental_cli", ("--llm-provider", "{opaque}")),
    ("company_wiki.source_catalog.artifact_backfill", ("--catalog", "absent", "--mode", "{opaque}")),
    ("company_wiki.source_catalog.backfill_v2", ("--catalog", "absent", "--mode", "{opaque}")),
    ("company_wiki.source_catalog.t3_workspace_cli", ("--workspace-root", "--help")),
))
def test_all_outer_startup_parsers_redact_and_retain_original_usage_failure(tmp_path, module, arguments):
    env = _environment(tmp_path)
    opaque = "ghp_StrictUsageBoundaryFixture000"
    outcome = _run(tmp_path, env, "-m", module, *(value.format(opaque=opaque) for value in arguments))
    assert (outcome.returncode, outcome.stdout) == (2, b"")
    assert opaque.encode() not in outcome.stderr and b"usage:" in outcome.stderr
    trace = _cold_read(tmp_path, env)
    reason, = trace["diagnostics"]
    assert reason["reason"] == "invalid_arguments"
    assert trace["events"][-1]["exit_code"] == 2


def test_source_export_failure_keeps_typed_cause_and_redacts_terminal(tmp_path):
    env = _environment(tmp_path)
    opaque = "sk-SourceExportFixture000001"
    outcome = _run(
        tmp_path, env, "-m", "company_wiki.source_contract.cli", "export",
        "--root", str(tmp_path), "--manifests", str(tmp_path / (opaque + ".jsonl")),
    )
    assert (outcome.returncode, outcome.stdout) == (2, b"")
    assert opaque.encode() not in outcome.stderr and b"source export failed" in outcome.stderr
    trace = _cold_read(tmp_path, env)
    reason, = trace["diagnostics"]
    assert reason["reason"] == "source_export_failed"
    assert reason["exceptions"][0]["type"] == "FileNotFoundError"


def test_feedback_history_failure_remains_local_and_read_only(tmp_path):
    env = _environment(tmp_path)
    env["PYTHONPATH"] += os.pathsep + str(_SRC.parent)
    outcome = _run(
        tmp_path, env, "-m", "tools.feedback_loop.intake", "--settings",
        str(tmp_path / "missing-settings.json"), "history", "--run-id", "already-owned-run",
    )
    assert (outcome.returncode, outcome.stderr) == (0, b"")
    assert json.loads(outcome.stdout) == {
        "status": "unavailable", "processes": [], "error_type": "FileNotFoundError",
    }
    native, = _cold_read(tmp_path, env)["diagnostics"]
    assert native["reason"] == "history_read_unavailable"
    assert not list(tmp_path.rglob("*.ready"))
    assert not list(tmp_path.rglob("*.db"))


def test_ordinary_logging_reuses_configured_diagnostic_fallback(tmp_path):
    env = _environment(tmp_path)
    blocker = tmp_path / "occupied-primary"
    _block(blocker)
    env["RESEARCH_FEEDBACK_OUT"] = str(blocker / "feedback.jsonl")
    path = tmp_path / "fallback"
    env["RESEARCH_FEEDBACK_DIR"] = str(path / "observations")
    outcome = _run(
        tmp_path, env, "-c",
        "import logging; from company_wiki.runtime_feedback import entry; "
        "work=entry('test-library')(lambda: (logging.getLogger('company_wiki.fixture')"
        ".warning('known business warning'), 0)[1]); raise SystemExit(work())",
    )
    assert (outcome.returncode, outcome.stdout, outcome.stderr) == (0, b"", b"")
    log = path / "logs/runtime_errors.log"
    assert log.read_bytes().count(b"known business warning") == 1
    assert blocker.read_bytes() == b"original blocker sentinel"


def test_cold_absence_and_real_help_do_not_create_state(tmp_path):
    env = _environment(tmp_path)
    trace = _cold_read(tmp_path, env)
    assert trace["status"] == "not_found"
    outcome = _run(tmp_path, env, "-m", "company_wiki.source_catalog.t3_workspace_cli", "--help")
    assert outcome.returncode == 0 and b"--workspace-root" in outcome.stdout and outcome.stderr == b""
    assert not _artifacts(tmp_path)




@pytest.mark.parametrize(("module", "arguments", "stdin", "code", "root_type"), (
    ("company_wiki.source_catalog.identity_cli", ("ACME", "--market", "CN", "--cache-dir", "missing-cache"),
     b"", 1, "SecurityMasterUnavailableError"),
    ("company_wiki.source_catalog.transcript_import_cli", ("--wiki-root", "missing-root"),
     b"{", 2, "TranscriptImportCliError"),
    ("company_wiki.source_catalog.financial_statements.cli", ("--wiki-root", "missing-root"),
     b"{", 2, "JSONDecodeError"),
))
def test_mapped_cli_refusal_keeps_original_exception(tmp_path, module, arguments, stdin, code, root_type):
    env = _environment(tmp_path)
    outcome = _run(tmp_path, env, "-m", module, *arguments, stdin=stdin)
    assert outcome.returncode == code
    if module.endswith("identity_cli"):
        assert outcome.stdout == b""
        assert json.loads(outcome.stderr)["status"] == "failed"
    else:
        assert json.loads(outcome.stdout)["status"] in {"rejected", "request_error"}
    native, = _cold_read(tmp_path, env)["diagnostics"]
    names = [cause["type"] for cause in native["exceptions"]]
    assert names[0] == root_type
    if module.endswith("transcript_import_cli"):
        assert "JSONDecodeError" in names


def test_detached_recovery_terminal_sanitizes_credential_like_path(tmp_path):
    env = _environment(tmp_path)
    env["PYTHONPATH"] += os.pathsep + str(_SRC.parent)
    opaque = "sk-FourthStageRecoveryFixture012345"
    outcome = _run(
        tmp_path, env, "-m", "tools.feedback_loop.local_host", "--config",
        str(tmp_path / (opaque + ".json")), "recover", "--save-result",
    )
    assert (outcome.returncode, outcome.stdout) == (1, b"")
    assert b"FileNotFoundError" in outcome.stderr and opaque.encode() not in outcome.stderr
    native, = _cold_read(tmp_path, env)["diagnostics"]
    assert native["exceptions"][0]["type"] == "FileNotFoundError"
    assert all(opaque.encode() not in data for data in _artifacts(tmp_path).values())




def test_uncaught_catalog_startup_uses_machine_channel_and_actual_native_cause(tmp_path):
    env = _environment(tmp_path)
    opaque = "sk-PublicStartupFixture00000000"
    outcome = _run(
        tmp_path, env, "-m", "company_wiki.source_catalog.cli", "--config",
        str(tmp_path / (opaque + ".json")), "status",
    )
    assert (outcome.returncode, outcome.stdout, outcome.stderr) == (1, b"", b"")
    original, = _cold_read(tmp_path, env)["diagnostics"]
    assert original["exceptions"][0]["type"] == "FileNotFoundError"
    assert all(opaque.encode() not in artifact for artifact in _artifacts(tmp_path).values())




@pytest.mark.parametrize(("data", "mime", "reason", "cause_name"), (
    (b"%PDF-1.4\nbroken original body", "application/pdf", "invalid_pdf", "NativePdfError"),
    (b"\xff", "text/html", "invalid_html_encoding", "UnicodeDecodeError"),
))
def test_original_document_refusal_preserves_causal_type_and_public_reason(data, mime, reason, cause_name):
    from company_wiki.source_catalog.official_source_flow import OfficialSourceError, _validate_bytes

    with pytest.raises(OfficialSourceError, match=f"^{reason}$") as rejected:
        _validate_bytes(data, mime)
    assert type(rejected.value.__cause__).__name__ == cause_name
