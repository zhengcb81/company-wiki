"""W22: push-gate scratch stays writable, path-bounded and per-invocation.

The gate must never depend on a possibly unwritable host TEMP, must not grow
its scratch with checkout depth, must keep every child temp environment inside
one owned root, and must explain itself when no candidate is usable. Candidate
probing is bounded: each listed root is tried once with a real directory and a
real probe file.
"""
import sys
from pathlib import Path

import pytest

from tools import pre_push_gate as gate


def test_candidate_roots_are_deduped_length_ordered_and_explainable(
        tmp_path, monkeypatch):
    env_temp = tmp_path / "env-temp"
    env_temp.mkdir()
    monkeypatch.setenv("TEMP", str(env_temp))
    monkeypatch.setenv("TMP", str(env_temp))  # duplicate of TEMP on purpose
    monkeypatch.delenv("TMPDIR", raising=False)
    checkout = tmp_path / "a-deliberately-long-checkout-directory-name"
    monkeypatch.setattr(gate, "PROJECT_ROOT", checkout)
    candidates = gate._scratch_candidate_roots()
    assert candidates == [str(env_temp), str(checkout)]


def test_without_temp_env_the_standard_tempdir_is_a_candidate(
        tmp_path, monkeypatch):
    import tempfile
    for name in ("TEMP", "TMP", "TMPDIR"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(gate, "PROJECT_ROOT", tmp_path / "checkout")
    candidates = gate._scratch_candidate_roots()
    assert candidates[0] == tempfile.gettempdir()
    assert str(tmp_path / "checkout") in candidates


def test_unwritable_candidate_falls_back_and_records_the_attempt(tmp_path):
    broken = tmp_path / "missing-parent" / "cwpp-candidate"
    good = tmp_path / "good"
    good.mkdir()
    scratch = gate._open_scratch([str(broken), str(good)])
    try:
        assert Path(scratch.name).is_relative_to(good)
        assert list(Path(scratch.name).iterdir()) == []  # probe file removed
    finally:
        scratch.cleanup()
    assert not list(good.iterdir())


def test_all_candidates_unwritable_reports_every_attempt(tmp_path):
    broken_a = tmp_path / "missing-a" / "cwpp-candidate"
    broken_b = tmp_path / "missing-b" / "cwpp-candidate"
    with pytest.raises(RuntimeError) as excinfo:
        gate._open_scratch([str(broken_a), str(broken_b)])
    message = str(excinfo.value)
    assert "missing-a" in message and "missing-b" in message


def test_pytest_gate_isolates_child_temp_env_inside_the_owned_scratch(
        tmp_path, monkeypatch):
    env_root = tmp_path / "env-temp"
    env_root.mkdir()
    monkeypatch.setenv("TEMP", str(env_root))
    monkeypatch.delenv("TMP", raising=False)
    monkeypatch.delenv("TMPDIR", raising=False)
    checkout = tmp_path / "checkout-deep-enough-to-have-mattered"
    checkout.mkdir()
    monkeypatch.setattr(gate, "PROJECT_ROOT", checkout)
    observed = []
    monkeypatch.setattr(gate, "_run", lambda cmd, label, **kwargs:
                        observed.append((cmd, kwargs)) or 0)
    gate._run_pytest_gate(
        [sys.executable, "-m", "pytest", "-q", "tests/unit"], "unit tests")
    command, options = observed[0]
    basetemp = command[command.index("--basetemp") + 1]
    owned = Path(options["env_extra"]["TEMP"])
    assert Path(basetemp) == owned
    for name in ("TMP", "TMPDIR", "SQLITE_TMPDIR"):
        assert options["env_extra"][name] == str(owned)
    assert owned.is_relative_to(env_root)
    assert not list(env_root.iterdir())  # scratch cleaned after the child


def _fake_checkout(tmp_path, body):
    checkout = tmp_path / "checkout"
    (checkout / "tests").mkdir(parents=True)
    (checkout / "tests" / "test_w22_tiny_child.py").write_text(
        body, encoding="utf-8")
    return checkout


def _gate_env(tmp_path, monkeypatch) -> Path:
    env_root = tmp_path / "env-temp"
    env_root.mkdir()
    monkeypatch.setenv("TEMP", str(env_root))
    monkeypatch.delenv("TMP", raising=False)
    monkeypatch.delenv("TMPDIR", raising=False)
    monkeypatch.setattr(gate, "PROJECT_ROOT", _fake_checkout(
        tmp_path, "def test_w22_child():\n    assert True\n"))
    return env_root


def test_real_child_gate_run_is_green_and_cleans_scratch(tmp_path, monkeypatch):
    env_root = _gate_env(tmp_path, monkeypatch)
    code = gate._run_pytest_gate(
        [sys.executable, "-m", "pytest", "-q", "tests/test_w22_tiny_child.py"],
        "w22 gate scratch: one lightweight real child")
    assert code == 0
    assert not list(env_root.iterdir())


def test_real_child_failure_keeps_exit_code_and_cleans_scratch(
        tmp_path, monkeypatch):
    env_root = _gate_env(tmp_path, monkeypatch)
    (tmp_path / "checkout" / "tests" / "test_w22_tiny_child.py").write_text(
        "def test_w22_child():\n    assert False, 'deliberate red'\n",
        encoding="utf-8")
    code = gate._run_pytest_gate(
        [sys.executable, "-m", "pytest", "-q", "tests/test_w22_tiny_child.py"],
        "w22 gate scratch: failing real child")
    assert code == 1
    assert not list(env_root.iterdir())


def test_real_child_timeout_cleans_scratch_and_reports_124(
        tmp_path, monkeypatch):
    env_root = _gate_env(tmp_path, monkeypatch)
    (tmp_path / "checkout" / "tests" / "test_w22_tiny_child.py").write_text(
        "import time\n"
        "def test_w22_child():\n    time.sleep(30)\n",
        encoding="utf-8")
    monkeypatch.setattr(gate, "DAILY_PUSH_TIMEOUT_SECONDS", 2)
    code = gate._run_pytest_gate(
        [sys.executable, "-m", "pytest", "-q", "tests/test_w22_tiny_child.py"],
        f"{gate.DAILY_PUSH_LABEL_PREFIX} w22 timeout cleanup child")
    assert code == 124
    assert not list(env_root.iterdir())
