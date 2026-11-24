"""S1-05 regression tests: CWP P0 logging blackholes and stderr=DEVNULL removal."""

from __future__ import annotations

import logging
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from company_wiki import runtime_feedback
from company_wiki.automation import narrative_projection
from company_wiki.document_normalization import isolated_ocr
from tools.feedback_loop import diagnostics, intake, local_host


def test_narrative_projection_logs_skipped_activation_error(caplog):
    from contextlib import nullcontext
    from company_wiki.automation.models import RuntimeState

    projector = narrative_projection.NarrativeEffectDispatcher.__new__(
        narrative_projection.NarrativeEffectDispatcher
    )
    projector._allowed_job_ids = None
    fake_artifact = SimpleNamespace(
        effect_id="eff-s1-1",
        status="prepared",
        metadata_json="{}",
        content_sha256="abc",
    )
    projector._artifacts = MagicMock()
    projector._artifacts.prepared_effects.return_value = [fake_artifact]
    projector._artifacts.operation_lock.return_value = nullcontext()
    projector._automation = MagicMock()
    projector._automation.read_runtime_gate.return_value = SimpleNamespace(
        desired_state=RuntimeState.ENABLED
    )
    projector._automation.get_effect.side_effect = RuntimeError("db-activation-boom")

    with caplog.at_level(logging.ERROR, logger="company_wiki.automation.narrative_projection"):
        activated = projector.reconcile_prepared(activated_at="2026-11-24T00:00:00Z")

    assert activated == ()
    assert any(
        "eff-s1-1" in rec.getMessage() and "RuntimeError: db-activation-boom" in rec.getMessage()
        for rec in caplog.records
    )


def test_runtime_feedback_logs_warning_when_all_destinations_fail(tmp_path, monkeypatch, caplog):
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("file-blocking-mkdir", encoding="utf-8")
    monkeypatch.setenv("RESEARCH_FEEDBACK_OUT", str(blocker / "obs.jsonl"))
    monkeypatch.setenv("RESEARCH_FEEDBACK_DIR", str(blocker / "inbox"))
    monkeypatch.setattr(runtime_feedback, "_directory", lambda: blocker / "default_inbox")

    with caplog.at_level(logging.WARNING, logger="company_wiki.runtime_feedback"):
        runtime_feedback.record(
            "s1_probe",
            "failed_probe",
            error=RuntimeError("synthetic-failure"),
        )

    assert any("runtime_feedback" in rec.getMessage() for rec in caplog.records)


def test_intake_run_observed_logs_warning_on_broken_settings(tmp_path, caplog):
    bad_settings = tmp_path / "bad.json"
    bad_settings.write_text("{not-json", encoding="utf-8")
    hosts = tmp_path / "hosts.json"
    hosts.write_text("{}", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="tools.feedback_loop.intake"):
        rc = intake.run_observed(
            bad_settings,
            hosts,
            "company-wiki",
            ["python", "-c", "raise SystemExit(0)"],
            0,
        )

    assert rc == 0
    assert any("observation capture" in rec.getMessage().lower() for rec in caplog.records)


def test_local_host_owner_command_persists_redacted_stderr_on_failure(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "host"
    cfg_dir.mkdir()
    cfg = cfg_dir / "settings.json"
    db_path = cfg_dir / "actions.sqlite"
    cfg.write_text("{}", encoding="utf-8")

    host = local_host.LocalHost.__new__(local_host.LocalHost)
    host.config = cfg
    host.db = db_path
    host.native_dir = cfg_dir / "native"
    host.native_dir.mkdir()
    host.owners = {
        "demo": {
            "kind": "owner-json",
            "argv": ["fake-cmd"],
            "cwd": str(tmp_path),
            "timeout": 10,
        }
    }
    import json as _json

    row = {
        "action_id": "act-s1-1",
        "state": "queued",
        "request_digest": "dig-1",
        "request": '{"owner": "demo", "action_id": "act-s1-1"}',
        "route": _json.dumps(
            {
                "mode": "owner-json",
                "argv": ["fake-cmd"],
                "cwd": str(tmp_path),
                "timeout": 10,
            }
        ),
    }
    host._native_path = lambda key: host.native_dir / f"{key}.json"
    host._get = lambda key: row
    host._claim_native = lambda r, t: True
    host._unconfirmed = MagicMock()

    def _fake_run(argv, **kwargs):
        assert kwargs.get("stderr") is not subprocess.DEVNULL, "owner-json must capture stderr"
        return subprocess.CompletedProcess(
            argv,
            returncode=2,
            stdout=b"",
            stderr=(
                b'RuntimeError: failed with api_key=SECRET999\n'
                b'{"api_key":"SYNTHETIC_JSON","Authorization":"Bearer SYNTHETIC_HEADER","code":"down"}\n'
                b'Authorization: Bearer SYNTHETIC_BEARER\n'
                b'GET /?token=SYNTHETIC_QUERY&view=owner\n'
                + json.dumps(json.dumps({"api_key": 'SYNTHETIC_NESTED"tail', "status": "nested"})).encode()
            ),
        )

    monkeypatch.setattr(local_host.subprocess, "run", _fake_run)
    host._owner_command("act-s1-1")

    stderr_log = cfg_dir / "logs" / "host_subprocess_failures.log"
    assert stderr_log.is_file()
    content = stderr_log.read_text(encoding="utf-8")
    assert "act-s1-1" in content
    assert "RuntimeError" in content
    assert '"code":"down"' in content and "view=owner" in content
    assert "nested" in content
    for marker in ("SECRET999", "SYNTHETIC_JSON", "SYNTHETIC_HEADER", "SYNTHETIC_BEARER",
                   "SYNTHETIC_QUERY", "SYNTHETIC_NESTED"):
        assert marker not in content


def test_feedback_write_warning_redacts_the_formatted_exception(tmp_path, monkeypatch, caplog):
    monkeypatch.delenv("RESEARCH_FEEDBACK_OUT", raising=False)
    monkeypatch.setenv("RESEARCH_FEEDBACK_DIR", str(tmp_path))
    monkeypatch.setattr(runtime_feedback, "_directory", lambda: tmp_path)

    def fail(*args):
        try:
            raise ValueError('{"api_key":"SYNTHETIC_CAUSE","field":"fixture"}')
        except ValueError as cause:
            raise OSError("Authorization: Bearer SYNTHETIC_IO") from cause

    monkeypatch.setattr(runtime_feedback, "_atomic", fail)
    runtime_feedback.record("test", "failed")

    assert 'ValueError' in caplog.text and 'OSError' in caplog.text
    assert '"field":"fixture"' in caplog.text
    assert "SYNTHETIC_CAUSE" not in caplog.text and "SYNTHETIC_IO" not in caplog.text


def test_background_intake_persists_a_safe_real_startup_failure(tmp_path):
    settings = tmp_path / "token=SYNTHETIC_STARTUP.json"
    hosts = tmp_path / "hosts.json"
    hosts.write_text("{}", encoding="utf8")
    log = tmp_path / "intake.log"
    command = [sys.executable, "-B", "-m", "tools.feedback_loop.intake", "--settings", str(settings),
               "--hosts", str(hosts), "drain"]
    result = subprocess.run(command, check=False, capture_output=True, timeout=15,
                            env={**os.environ, "CWP_F4_ERROR_LOG": str(log)})
    assert result.returncode == 1 and not result.stdout
    text = log.read_text(encoding="utf8")
    assert "SYNTHETIC_STARTUP" not in text and b"SYNTHETIC_STARTUP" not in result.stderr
    assert "FileNotFoundError" in text


def test_background_diagnostic_survives_rotation_failure(tmp_path, monkeypatch):
    path = tmp_path / "background.log"
    path.write_bytes(b"previous\n" * (256 * 1024))
    monkeypatch.setenv("CWP_F4_ERROR_LOG", str(path))

    def locked(*args):
        raise PermissionError("reader holds the old log")

    monkeypatch.setattr(diagnostics.RotatingFileHandler, "rotate", locked)

    def report():
        logging.warning('case preserved {"token":"SYNTHETIC_ROTATION"}')
        return 7

    assert diagnostics.run_background(report) == 7
    with path.open("rb") as stream:
        stream.seek(-256, os.SEEK_END)
        tail = stream.read()
    assert b"case preserved" in tail and b"SYNTHETIC_ROTATION" not in tail


def test_isolated_ocr_source_has_no_devnull_stderr():
    src = Path(isolated_ocr.__file__).read_text(encoding="utf-8")
    assert "stderr=subprocess.DEVNULL" not in src
