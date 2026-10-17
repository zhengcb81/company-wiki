"""Pre-push checks own their TEMP independently of checkout depth."""
from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import sys
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("pre_push_temp_scope_gate", ROOT / "tools/pre_push_gate.py")
gate = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gate)


@pytest.mark.parametrize("exit_code", [0, 7])
def test_deep_checkout_does_not_reject_checks_or_keep_scratch(tmp_path, monkeypatch, exit_code):
    checkout = tmp_path / ("isolated-checkout-" * 3)
    checkout.mkdir()
    original = checkout / "owner.txt"
    original.write_text("original", encoding="utf-8")
    monkeypatch.setattr(gate, "PROJECT_ROOT", checkout)
    allocated = []
    original_run = gate._run
    def recording_run(cmd, label, **kwargs):
        allocated.append(Path(cmd[cmd.index("--basetemp") + 1]))
        return original_run(cmd, label, **kwargs)
    monkeypatch.setattr(gate, "_run", recording_run)
    probe = ("import json,pathlib,sys; "
             "p=pathlib.Path(sys.argv[sys.argv.index('--basetemp')+1]); "
             "(p/'owned.txt').write_text('temporary',encoding='utf-8'); "
             "print('OWNED_TEMP '+json.dumps(str(p))); "
             f"sys.exit({exit_code})")
    result = gate._run_pytest_gate([sys.executable, "-c", probe], "owned child check")
    assert result == exit_code
    assert len(allocated) == 1
    assert not allocated[0].exists()
    assert list(checkout.iterdir()) == [original]
    assert original.read_text(encoding="utf-8") == "original"


def test_owned_temp_is_removed_on_transport_exception(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    monkeypatch.setattr(gate, "PROJECT_ROOT", checkout)
    paths = []
    def failing(cmd, label, **kwargs):
        path = Path(cmd[cmd.index("--basetemp") + 1])
        paths.append(path)
        (path / "partial.txt").write_text("partial", encoding="utf-8")
        raise TimeoutError("fixture child timeout")
    monkeypatch.setattr(gate, "_run", failing)
    with pytest.raises(TimeoutError, match="fixture child timeout"):
        gate._run_pytest_gate(["fixture"], "timeout")
    assert len(paths) == 1 and not paths[0].exists()
    assert not list(checkout.iterdir())


def test_check_child_does_not_inherit_hook_repository_context(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "PROJECT_ROOT", tmp_path)
    for name in gate.GIT_REPOSITORY_CONTEXT:
        monkeypatch.setenv(name, "parent-repository")
    monkeypatch.setenv("GIT_CONFIG_PARAMETERS", "preserved-user-setting")
    probe = ("import os; "
             f"assert not any(k in os.environ for k in {gate.GIT_REPOSITORY_CONTEXT!r}); "
             "assert os.environ['GIT_CONFIG_PARAMETERS']=='preserved-user-setting'")
    assert gate._run([sys.executable, "-c", probe], "isolated child Git context") == 0


@pytest.mark.parametrize("as_bytes", [False, True])
def test_timed_out_check_preserves_progress_and_returns_red(monkeypatch, capsys, as_bytes):
    progress = "tests/unit/test_reader.py::test_source 原文 PASSED\n"
    error = "last child diagnostic\n"
    def expired(*args, **kwargs):
        assert kwargs["timeout"] == 600
        raise subprocess.TimeoutExpired(args[0], 600,
            output=progress.encode("utf-8") if as_bytes else progress,
            stderr=error.encode("utf-8") if as_bytes else error)
    monkeypatch.setattr(gate.subprocess, "run", expired)
    assert gate._run([sys.executable, "-m", "pytest"], "full bootstrap") == 124
    output = capsys.readouterr().out
    assert progress.strip() in output
    assert error.strip() in output
    assert "600" in output and "FAILED: full bootstrap" in output


def test_timeout_diagnostic_survives_a_legacy_console_encoding(monkeypatch):
    def expired(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 600,
            output="last test: snowman ☃ 原文\n".encode("utf-8"),
            stderr=b"child stderr\n")
    monkeypatch.setattr(gate.subprocess, "run", expired)
    buffer = io.BytesIO()
    console = io.TextIOWrapper(buffer, encoding="gbk", errors="strict")
    with monkeypatch.context() as context:
        context.setattr(gate.sys, "stdout", console)
        code = gate._run([sys.executable, "-m", "pytest"], "full bootstrap")
    console.flush()
    output = buffer.getvalue().decode("gbk")
    assert code == 124
    assert "last test: snowman \\u2603 原文" in output
    assert "child stderr" in output and "FAILED: full bootstrap" in output
