"""Run the actual Windows-compatible process and public CLI boundaries offline."""
from __future__ import annotations

import json
import io
import os
from pathlib import Path
import subprocess
import sys

import pytest

from support.sr_cwp_fixtures import build_catalog


ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_VALUE = "fixture-holdout-opaque"
FOLDED_VALUE = "fixture-continued-opaque"


@pytest.fixture
def environment(tmp_path):
    env = {key: value for key, value in os.environ.items() if not key.startswith("RESEARCH_FEEDBACK_")}
    env.update(
        LOCALAPPDATA=str(tmp_path / "state"), XDG_STATE_HOME=str(tmp_path / "state"),
        PYTHONPATH=os.pathsep.join((str(tmp_path), str(ROOT / "src"))),
        RESEARCH_FEEDBACK_RUN_ID="lifecycle-test", RESEARCH_FEEDBACK_ATTEMPT_ID="caller-attempt",
    )
    return env


def _run(cwd, env, *args):
    return subprocess.run([sys.executable, "-B", *args], cwd=cwd, env=env,
                          check=False, capture_output=True, timeout=20)


def _cold_trace(cwd, env, *, attempt=None):
    args = ("--attempt-id", attempt) if attempt else ()
    result = _run(cwd, env, "-m", "company_wiki.runtime_trace", "--run-id", "lifecycle-test", *args)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["events"]


def _worker_trial(tmp_path, env, mode):
    (tmp_path / "fixture_worker.py").write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "import time\n"
        "def crash(spec):\n"
        "    sys.stdout.write('Author')\n"
        "    sys.stdout.write('ization: Bearer\\n')\n"
        f"    print('  {SYNTHETIC_VALUE}')\n"
        f"    print('Authorization: Bearer {SYNTHETIC_VALUE}')\n"
        f"    print('  {FOLDED_VALUE}')\n"
        f"    raise ValueError('startup fixture failed; Authorization: Bearer {SYNTHETIC_VALUE}\\n  {FOLDED_VALUE}')\n"
        "def wait(spec):\n"
        "    Path('factory.ready').touch()\n"
        "    time.sleep(60)\n",
        encoding="utf-8",
    )
    (tmp_path / "launch.py").write_text(
        "import json\n"
        "from pathlib import Path\n"
        "import time\n"
        "from company_wiki.automation.supervisor import AutomationSupervisor, SupervisorConfig\n"
        "def run():\n"
        "    sup = AutomationSupervisor(SupervisorConfig(Path('auto.db'), Path('child'), 'P1',\n"
        f"          'fixture_worker:{mode}', '{{}}', ('fixture.compute',), ('fixture.model',), max_restarts_per_slot=0))\n"
        "    try:\n"
        "        sup.start()\n"
        "        deadline = time.monotonic() + 10\n"
        f"        if {mode!r} == 'wait':\n"
        "            while not Path('factory.ready').exists() and time.monotonic() < deadline:\n"
        "                time.sleep(.025)\n"
        "            assert Path('factory.ready').exists()\n"
        "            sup.terminate_worker('mixed-1')\n"
        "        else:\n"
        "            while sup.children()[0].alive and time.monotonic() < deadline:\n"
        "                time.sleep(.025)\n"
        "        child, = sup.children()\n"
        "        print(json.dumps({'attempt': getattr(child, 'attempt_id', None), 'exit': child.exitcode}))\n"
        "    finally:\n"
        "        sup.stop()\n"
        "if __name__ == '__main__':\n"
        "    run()\n",
        encoding="utf-8",
    )
    result = _run(tmp_path, env, "launch.py")
    assert result.returncode == 0, result.stderr
    return result


@pytest.mark.parametrize(("mode", "status"), (("crash", "failed"), ("wait", "interrupted")))
def test_original_preclaim_worker_attempt_can_be_cold_read(tmp_path, environment, mode, status):
    result = _worker_trial(tmp_path, environment, mode)
    for value in (SYNTHETIC_VALUE, FOLDED_VALUE):
        assert value.encode() not in result.stderr
        for path in tmp_path.rglob("*.log"):
            assert value.encode() not in path.read_bytes()
        for path in tmp_path.rglob("*.diagnostic.json"):
            assert value.encode() not in path.read_bytes()
    evidence = json.loads(result.stdout)
    assert evidence["attempt"] and evidence["exit"] not in (0, None)
    events = _cold_trace(tmp_path, environment, attempt=evidence["attempt"])
    assert {"spawn", "factory", "exit"} <= {event["step"] for event in events}
    terminal = [event for event in events if event["step"] == "exit"]
    assert terminal[-1]["status"] == status and terminal[-1]["exit_code"] == evidence["exit"]
    observations = tuple((tmp_path / "state").rglob("*.diagnostic.json"))
    original = [json.loads(path.read_bytes()) for path in observations]
    matched = [event for event in original if event["attempt_id"] == evidence["attempt"]]
    assert len(matched) == 1 and matched[0]["run_id"] == "lifecycle-test"
    if mode == "crash":
        assert matched[0]["exceptions"][0]["type"] == "ValueError"
    assert events == _cold_trace(tmp_path, environment, attempt=evidence["attempt"])


def test_plan_never_initializes_a_missing_database(tmp_path, environment):
    db = tmp_path / "missing.db"
    result = _run(tmp_path, environment, "-m", "company_wiki.automation.cli", "plan", "--db", str(db))
    assert not db.exists()
    assert result.returncode != 0
    assert json.loads(result.stdout)["reason"] == "automation_database_missing"


def test_public_plan_and_corrupt_feedback_flush_keep_database_bytes(tmp_path, environment):
    from company_wiki.automation.store import AutomationStore

    db = tmp_path / "valid#plan.db"
    AutomationStore(db)
    before = db.read_bytes()
    result = _run(tmp_path, environment, "-m", "company_wiki.automation.cli", "plan", "--db", str(db))
    assert result.returncode == 0 and json.loads(result.stdout)["events_planned"] == 0
    assert db.read_bytes() == before
    assert not (tmp_path / "valid").exists()
    db_bad = tmp_path / "bad.db"
    db_bad.write_bytes(b"broken sqlite")
    result = _run(tmp_path, environment, "-m", "company_wiki.automation.cli", "feedback-flush", "--db", str(db_bad))
    assert result.returncode == 1 and db_bad.read_bytes() == b"broken sqlite"
    assert json.loads(result.stdout)["error_type"] == "InvalidDatabaseFileError"
    evidence = [json.loads(path.read_bytes()) for path in tmp_path.rglob("*.diagnostic.json")]
    assert any(row["exceptions"][0]["type"] == "InvalidDatabaseFileError" for row in evidence)


def test_source_read_success_stages_are_cold_readable_without_changing_transport(tmp_path, environment):
    seeded = build_catalog(tmp_path)
    ref = seeded.refs["annual-report.txt"].to_dict()
    original = (tmp_path / "companies/Acme/raw/annual-report.txt").read_bytes()
    seeded.catalog.close()
    result = _run(tmp_path, environment, "-m", "company_wiki.source_catalog.source_reader_cli",
                  "--config", str(tmp_path / "config/catalog.json"), "--document-id", ref["document_id"],
                  "--source-id", ref["source_id"], "--content-sha256", ref["content_sha256"])
    assert (result.returncode, result.stdout) == (0, original)
    assert len(result.stderr.splitlines()) == 1 and json.loads(result.stderr)["status"] == "ok"
    events = _cold_trace(tmp_path, environment)
    assert ["invocation", "resolve-source", "verify-original", "deliver-bytes", "invocation"] == [
        event["step"] for event in events
    ]
    assert events[-1]["status"] == "completed" and events[-1]["exit_code"] == 0
    assert any(event.get("source_id") == ref["source_id"] for event in events)
    assert all(event["at_utc"] and len(event["implementation_sha256"]) == 64 for event in events)
    assert not list(tmp_path.rglob("*.ready"))


def test_bad_batch_keeps_real_parse_error_and_preserves_machine_receipt(tmp_path, environment):
    request = tmp_path / "request.json"
    request.write_text("{", encoding="utf-8")
    db = tmp_path / "never.db"
    completed = _run(tmp_path, environment, "-m", "company_wiki.automation.narrative_batch_cli",
                     "--project-root", str(tmp_path), "--catalog-config", str(tmp_path / "config.json"),
                     "--automation-db", str(db), "--work-dir", str(tmp_path / "work"), "--request", str(request))
    assert (completed.returncode, completed.stderr) == (1, b"")
    assert json.loads(completed.stdout)["error"] == "NARRATIVE_BATCH_INVALID_REQUEST"
    assert not db.exists()
    details = [json.loads(path.read_bytes()) for path in tmp_path.rglob("*.diagnostic.json")]
    assert len(details) == 1
    assert details[0]["exceptions"][0]["type"] == "JSONDecodeError"
    assert details[0]["exceptions"][0]["line"] == 1


@pytest.mark.parametrize("state_available", (True, False))
def test_binary_transport_reports_trace_fallback_without_polluting_machine_streams(
    tmp_path, environment, state_available,
):
    unavailable = tmp_path / "occupied"
    unavailable.touch()
    environment.update(
        RESEARCH_FEEDBACK_OUT=str(unavailable / "transport.jsonl"),
        RESEARCH_FEEDBACK_DIR=str(unavailable / "observations"),
    )
    if not state_available:
        Path(environment["LOCALAPPDATA"]).touch()
    missing = tmp_path / "never-config.json"
    result = _run(tmp_path, environment, "-m", "company_wiki.source_catalog.source_reader_cli",
                  "--config", str(missing), "--document-id", "fixture-document", "--source-id", "fixture-source",
                  "--content-sha256", "1" * 64, "--include-runtime-trace")
    assert (result.returncode, result.stdout, len(result.stderr.splitlines())) == (2, b"", 1)
    expected = "available" if state_available else "degraded"
    assert json.loads(result.stderr) == {
        "schema_version": "2.1", "status": "unavailable", "reason": "reader_unavailable",
        "runtime_trace": {"run_id": "lifecycle-test", "attempt_id": "caller-attempt", "status": expected},
    }
    if state_available:
        raw = _run(tmp_path, environment, "-m", "company_wiki.runtime_trace", "--run-id", "lifecycle-test")
        record = json.loads(raw.stdout)
        assert [detail["exceptions"][0]["type"] for detail in record["diagnostics"]] == ["FileNotFoundError"]
        local = Path(environment["LOCALAPPDATA"]) / "company-wiki/logs/runtime_errors.log"
        assert local.is_file()


def test_old_event_schema_can_be_planned_without_migration(tmp_path, environment):
    from contextlib import closing
    import sqlite3
    from company_wiki.automation.migrations import _DDL_V1_STATEMENTS

    db = tmp_path / "legacy.db"
    with closing(sqlite3.connect(db)) as conn, conn:
        for statement in _DDL_V1_STATEMENTS:
            conn.execute(statement)
        conn.execute("PRAGMA user_version=1")
    before = db.read_bytes()
    result = _run(tmp_path, environment, "-m", "company_wiki.automation.cli", "plan", "--db", str(db))
    assert result.returncode == 0 and json.loads(result.stdout)["events_planned"] == 0
    assert db.read_bytes() == before


def test_cold_job_query_does_not_recreate_removed_automation_database(tmp_path):
    import sqlite3
    from company_wiki.automation.store import AutomationStore

    db = tmp_path / "original.db"
    store = AutomationStore(db)
    db.unlink()
    with pytest.raises(sqlite3.OperationalError):
        store.get_job("original-job")
    assert not db.exists()


def test_bad_narrative_transport_has_cold_original_parse_error(tmp_path, environment, monkeypatch, capsys):
    from company_wiki.automation.narrative_transport_cli import main

    for key in ("LOCALAPPDATA", "XDG_STATE_HOME", "RESEARCH_FEEDBACK_RUN_ID", "RESEARCH_FEEDBACK_ATTEMPT_ID"):
        monkeypatch.setenv(key, environment[key])
    for key in ("RESEARCH_FEEDBACK_DIR", "RESEARCH_FEEDBACK_OUT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"{")))
    assert main(["--config", str(tmp_path / "unused.json")]) == 2
    written = capsys.readouterr()
    assert written.out == "" and len(written.err.splitlines()) == 1
    assert json.loads(written.err)["reason"] == "invalid_request"
    packet, = (tmp_path / "state").rglob("*.diagnostic.json")
    assert json.loads(packet.read_bytes())["exceptions"][0]["type"] == "JSONDecodeError"


def test_native_parser_diagnostics_are_retained_without_using_binary_protocol_streams(tmp_path, environment):
    program = """import os, sys
from company_wiki.automation.narrative_transport_cli import _quiet_transport_operation
with _quiet_transport_operation():
    os.write(1, b'native layout parser diagnostic\\n')
    sys.stdout.buffer.write(b'native binary diagnostic\\n')
    sys.stdout.buffer.flush()
    sys.stderr.write('Authorization: ')
    sys.stderr.write('Bearer ' + sys.argv[1] + '\\n')
sys.stdout.buffer.write(b'artifact')
"""
    result = _run(tmp_path, environment, "-c", program, SYNTHETIC_VALUE)
    assert (result.returncode, result.stdout, result.stderr) == (0, b"artifact", b"")
    retained = (Path(environment["LOCALAPPDATA"]) / "company-wiki/logs/runtime_errors.log").read_text()
    assert "native layout parser diagnostic" in retained and "native binary diagnostic" in retained
    assert "<redacted>" in retained
    assert SYNTHETIC_VALUE not in retained
