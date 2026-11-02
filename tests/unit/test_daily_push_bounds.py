"""Daily cost depends on one fixed smoke inventory, never impact-file count."""
import io
from pathlib import Path

import pytest

from tools import changed_unit_tests
from tools import pre_push_gate as gate


@pytest.mark.parametrize("changes", [
    {"src/pkg/core.py"},
    {"config/input.json"},
    {"tests/unit/test_explicit.py"},
    {f"tests/unit/test_changed_{index}.py" for index in range(379)},
    {"README.md", "src/pkg/core.py"},
    {"unknown/runtime.txt"},
    None,
])
def test_daily_main_uses_identical_smoke_without_ast_selection(tmp_path, monkeypatch, changes):
    monkeypatch.setattr(gate, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(gate.sys, "stdin", io.StringIO("fixture push range"))
    monkeypatch.setattr(gate, "changed_paths", lambda *_: changes)

    def no_graph(*_args, **_kwargs):
        pytest.fail("daily push must not construct or consult an AST impact graph")

    monkeypatch.setattr(changed_unit_tests, "select_unit_tests", no_graph)
    monkeypatch.setattr(Path, "rglob", no_graph)
    observed = []
    monkeypatch.setattr(gate, "_run_pytest_gate", lambda cmd, label: observed.append(cmd) or 0)
    assert gate.main(["--push-checks"]) == 0
    assert len(observed) == 1
    assert observed[0][observed[0].index("--timeout=180") + 1:] == list(gate.FAST_CONTRACT_CASES)


@pytest.mark.parametrize("changes", [set(), {"docs/usage.md"},
    {"README.md", "docs/plans/run/probe.py", ".planning/run/result.json"}])
def test_daily_main_proven_nonruntime_range_never_starts_pytest(monkeypatch, capsys, changes):
    monkeypatch.setattr(gate.sys, "stdin", io.StringIO("fixture push range"))
    monkeypatch.setattr(gate, "changed_paths", lambda *_: changes)
    monkeypatch.setattr(gate, "_run_pytest_gate", lambda *_: pytest.fail("no pytest for documentation"))
    assert gate.main(["--push-checks"]) == 0
    output = capsys.readouterr().out
    assert "tests_not_run" in output and "local_fast_pass" not in output


@pytest.mark.parametrize("returncode", [0, 1, 7, 124, 125])
def test_daily_pass_is_reported_only_after_fixed_smoke_success(monkeypatch, capsys, returncode):
    monkeypatch.setattr(gate, "changed_paths", lambda *_: {"source.py"})
    monkeypatch.setattr(gate.sys, "stdin", io.StringIO("fixture range"))

    def execute(command, _label):
        before = capsys.readouterr().out
        assert "local_fast_pass" not in before
        assert "planned" in before
        assert all(target in command for target in gate.FAST_CONTRACT_CASES)
        return returncode

    monkeypatch.setattr(gate, "_run_pytest_gate", execute)
    assert gate.main(["--push-checks"]) == returncode
    after = capsys.readouterr().out
    assert ("local_fast_pass" in after) is (returncode == 0)
