"""Pre-push checks own their TEMP independently of checkout depth."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

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
