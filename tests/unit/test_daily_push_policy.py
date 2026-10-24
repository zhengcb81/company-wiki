"""Daily pushes stay bounded; full validation remains an explicit local mode.

The selection functions may still recommend the full suite; this policy layer
decides what a push actually runs, defers the rest to CI, and reports that
deferral instead of silently starting every unit test. Real Git repositories
drive the hook end to end: a genuine failure inside the ran scope must block
the push, a green fast pass must stay honest about what it did not run, and a
missing gate runner must block instead of silently passing.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools import pre_push_gate as gate  # noqa: E402

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
HOOK_AND_GATE_FILES = (".githooks/pre-push", "tools/pre_push_gate.py",
                       "tools/changed_unit_tests.py")


def _push_gate(monkeypatch, selected, reason, push_input="fixture push range"):
    monkeypatch.setattr(gate, "PROJECT_ROOT", Path.cwd())
    monkeypatch.setattr(gate.sys, "stdin", type("Input", (), {"read": lambda self: push_input})())
    monkeypatch.setattr(gate, "changed_paths", lambda root, data: {"fixture"})
    monkeypatch.setattr(gate, "select_unit_tests", lambda root, files: (selected, reason))


def _capture_gates(monkeypatch):
    observed = []
    monkeypatch.setattr(
        gate, "_run_pytest_gate",
        lambda cmd, label: observed.append((cmd, label)) or 0)
    return observed


def _targets(command):
    return command[command.index("--timeout=180") + 1:]


@pytest.mark.parametrize("selected,reason", [
    (["tests/unit"], "unknown push range"),
    (["tests/unit"], "configuration or test entrypoint changed"),
    (["tests/unit"], "shared or unknown tooling changed"),
    (["tests/unit"], "resource dependency scope unknown"),
    (["tests/unit"], "dynamic execution changed"),
])
def test_a_full_recommendation_defers_to_ci_instead_of_running_it(
        monkeypatch, capsys, selected, reason):
    _push_gate(monkeypatch, selected, reason)
    observed = _capture_gates(monkeypatch)
    assert gate.main(["--push-checks"]) == 0
    assert len(observed) == 1
    targets = _targets(observed[0][0])
    assert "tests/unit" not in targets
    assert targets == list(gate.FAST_CONTRACT_CASES)
    output = capsys.readouterr().out
    assert "full_validation_pending" in output
    assert "local_fast_pass" in output


def test_empty_stdin_is_an_unknown_range_that_defers(monkeypatch, capsys):
    monkeypatch.setattr(gate, "PROJECT_ROOT", Path.cwd())
    monkeypatch.setattr(gate.sys, "stdin", type("Input", (), {"read": lambda self: ""})())
    observed = _capture_gates(monkeypatch)
    assert gate.main(["--push-checks"]) == 0
    assert len(observed) == 1
    targets = _targets(observed[0][0])
    assert targets == list(gate.FAST_CONTRACT_CASES)
    output = capsys.readouterr().out
    assert "unknown push range" in output
    assert "full_validation_pending" in output


@pytest.mark.parametrize("selected,reason", [
    ([], "no behavior changes"),
    (["tests/unit/test_reader.py"], "affected unit tests"),
    (["tests/unit/test_a.py", "tests/contract/test_shared.py"],
     "affected test modules"),
])
def test_a_small_explainable_set_runs_those_files_and_reports_the_ran_scope(
        monkeypatch, capsys, selected, reason):
    _push_gate(monkeypatch, selected, reason)
    observed = _capture_gates(monkeypatch)
    assert gate.main(["--push-checks"]) == 0
    assert len(observed) == 1
    targets = _targets(observed[0][0])
    assert targets[:len(selected)] == selected
    smoke = [case for case in gate.FAST_CONTRACT_CASES
             if not any(case.split("::")[0] == path for path in selected)]
    assert targets[len(selected):] == smoke
    assert len(targets) == len(set(targets))
    output = capsys.readouterr().out
    assert "ran" in output and str(len(targets)) in output
    assert "full_validation_pending" in output
    assert "local_fast_pass" in output


def test_push_targets_never_expand_to_the_whole_unit_directory(monkeypatch):
    for selected in (["tests/unit"], ["tests/unit/test_a.py", "tests/unit"],
                     [], ["tests/unit/du/test_x.py"]):
        _push_gate(monkeypatch, selected, "fixture reason")
        observed = _capture_gates(monkeypatch)
        assert gate.main(["--push-checks"]) == 0
        targets = _targets(observed[0][0])
        assert "tests/unit" not in targets
        assert all(item in gate.FAST_CONTRACT_CASES or item in selected
                   for item in targets)


def test_fast_contract_members_stay_shared_and_deduplicated(monkeypatch):
    selected = ["tests/unit/test_narrative_evidence.py"]
    _push_gate(monkeypatch, selected, "affected unit tests")
    observed = _capture_gates(monkeypatch)
    assert gate.main(["--push-checks"]) == 0
    targets = _targets(observed[0][0])
    assert targets[0] == selected[0]
    for case in gate.FAST_CONTRACT_CASES:
        if case.startswith("tests/unit/test_narrative_evidence.py"):
            assert case not in targets  # the whole file run covers the node
        else:
            assert case in targets
    assert len(targets) == len(set(targets))


def test_a_real_failure_in_the_ran_scope_blocks_the_push(monkeypatch, capsys):
    _push_gate(monkeypatch, ["tests/unit/test_reader.py"], "affected unit tests")
    observed = []
    monkeypatch.setattr(gate, "_run_pytest_gate",
                        lambda cmd, label: observed.append(cmd) or 3)
    assert gate.main(["--push-checks"]) == 3
    assert len(observed) == 1
    assert "PUSH CHECKS RED" in capsys.readouterr().out


def test_runner_start_failure_returns_nonzero(monkeypatch, capsys):
    _push_gate(monkeypatch, ["tests/unit/test_reader.py"], "affected unit tests")

    def broken(cmd, label):
        raise OSError("spawn failed")

    monkeypatch.setattr(gate, "_run_pytest_gate", broken)
    assert gate.main(["--push-checks"]) == 1
    assert "spawn failed" in capsys.readouterr().out


def test_green_full_local_mode_keeps_its_own_wording(monkeypatch, capsys):
    codes = iter([0] * 7)
    monkeypatch.setattr(gate, "_run", lambda *args, **kwargs: next(codes))
    monkeypatch.setattr(gate, "_run_pytest_gate", lambda *args, **kwargs: next(codes))
    assert gate.main([]) == 0
    output = capsys.readouterr().out
    assert "full local gate GREEN" in output
    assert "local_fast_pass" not in output
    assert "safe to push" not in output


def test_green_push_mode_never_claims_full_or_safe(monkeypatch, capsys):
    _push_gate(monkeypatch, [], "no behavior changes")
    _capture_gates(monkeypatch)
    assert gate.main(["--push-checks"]) == 0
    output = capsys.readouterr().out
    assert "local_fast_pass" in output
    assert "safe to push" not in output
    assert "full local gate GREEN" not in output


@pytest.mark.parametrize("entrypoint,extra", [
    ("--push-checks", []),
    ("--fast-contracts-only", []),
    ("--fast-contracts-only", ["--junitxml", "w13-fixture.xml"]),
])
def test_remote_and_full_mode_sets_are_unchanged_by_the_push_policy(
        monkeypatch, entrypoint, extra):
    _push_gate(monkeypatch, [], "no behavior changes")
    observed = _capture_gates(monkeypatch)
    assert gate.main([entrypoint, *extra]) == 0
    assert len(observed) == 1
    command = observed[0][0]
    expected = list(gate.FAST_CONTRACT_CASES)
    if extra:
        expected.append(f"--junitxml={extra[-1]}")
    assert command[command.index("--timeout=180") + 1:] == expected


def test_full_local_mode_runs_every_existing_stage_in_order(monkeypatch):
    order = []
    monkeypatch.setattr(gate, "_run",
                        lambda cmd, label, **kwargs: order.append(label) or 0)
    monkeypatch.setattr(gate, "_run_pytest_gate",
                        lambda cmd, label: order.append(label) or 0)
    assert gate.main([]) == 0
    assert order == [
        "ruff (CI WU-1.2 full scope)", "compileall",
        "config_doctor (CI WU-7.1)",
        "host assumption guard (FC-1307-a; the class that broke CI in F-B01-9)",
        "unit tests (CI Unit tests)",
        "focused contracts, recent CI regressions, and gate regression tests",
    ]


def test_hook_keeps_the_push_entrypoint_and_adds_no_bypass():
    hook = (REPOSITORY_ROOT / ".githooks/pre-push").read_text(encoding="utf-8")
    assert "--push-checks" in hook
    assert "--fast-contracts-only" not in hook
    assert "SKIP" not in hook.upper().replace("SKIPPING", "")


def test_hook_blocks_and_reports_a_missing_gate_runner(tmp_path):
    hooks = tmp_path / ".githooks"
    hooks.mkdir()
    shutil.copyfile(REPOSITORY_ROOT / ".githooks/pre-push", hooks / "pre-push")
    proc = subprocess.run(["sh", str(hooks / "pre-push")], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=60)
    assert proc.returncode != 0
    assert "missing" in (proc.stdout + proc.stderr).lower()


def _git(cwd, *command):
    proc = subprocess.run(("git", *command), cwd=str(cwd), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=120)
    assert proc.returncode == 0, proc.stderr
    return proc


def _write_smoke_stubs(root: Path) -> None:
    """Materialise every fast-contract node so the fixture repo can run them."""
    cases: dict[str, list[str]] = {}
    for case in gate.FAST_CONTRACT_CASES:
        path, _, node = case.partition("::")
        cases.setdefault(path, []).append(node)
    for path, nodes in cases.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        lines = ["import pytest", ""]
        for node in nodes:
            name = node or "test_w13_fixture_stub"
            parameter = ""
            if "[" in name:
                name, parameter = name.split("[", 1)
                parameter = parameter.rstrip("]")
            if parameter:
                lines.append(f"@pytest.mark.parametrize('value', ['{parameter}'])")
                lines.append(f"def {name}(value): pass")
            else:
                lines.append(f"def {name}(): pass")
            lines.append("")
        target.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def _fixture_repository(tmp_path: Path):
    work = tmp_path / "work"
    work.mkdir()
    for relative in HOOK_AND_GATE_FILES:
        target = work / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY_ROOT / relative, target)
    _write_smoke_stubs(work)
    probe = work / "tests/unit/test_gate_probe.py"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("def test_probe(): pass\n", encoding="utf-8", newline="\n")
    # The gate process byte-compiles its own imported tools; keep that noise
    # out of the pushed ranges so the diff reflects the intended change only.
    (work / ".gitignore").write_text("__pycache__/\n", encoding="utf-8", newline="\n")
    _git(work, "init", "-q", "-b", "master")
    _git(work, "config", "user.email", "w13-e2e@example.invalid")
    _git(work, "config", "user.name", "w13-e2e")
    _git(work, "config", "core.hooksPath", ".githooks")
    _git(work, "add", "-A")
    _git(work, "commit", "-qm", "fixture baseline")
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    _git(work, "remote", "add", "origin", str(remote))
    return work, remote, probe


def _push(work: Path):
    return subprocess.run(["git", "push", "origin", "master"], cwd=str(work),
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=600)


def _remote_head(work: Path) -> str:
    listing = _git(work, "ls-remote", "origin", "refs/heads/master").stdout.split()
    return listing[0] if listing else ""


def test_real_push_green_fast_pass_then_blocked_by_a_ran_failure(tmp_path):
    work, _remote, probe = _fixture_repository(tmp_path)
    green = _push(work)
    assert green.returncode == 0, green.stdout + green.stderr
    output = green.stdout + green.stderr
    assert "local_fast_pass" in output
    assert "full_validation_pending" in output
    probe.write_text("def test_probe(): assert False, 'probe failure'\n",
                     encoding="utf-8", newline="\n")
    _git(work, "add", "tests/unit/test_gate_probe.py")
    _git(work, "commit", "-qm", "red probe")
    local_head = _git(work, "rev-parse", "HEAD").stdout.strip()
    blocked = _push(work)
    assert blocked.returncode != 0
    combined = blocked.stdout + blocked.stderr
    assert "PUSH CHECKS RED" in combined
    assert "test_gate_probe" in combined
    assert _remote_head(work) != local_head


def test_real_push_with_missing_gate_runner_is_blocked(tmp_path):
    work, _remote, _probe = _fixture_repository(tmp_path)
    (work / "tools/pre_push_gate.py").unlink()
    _git(work, "add", "tools/pre_push_gate.py")
    _git(work, "commit", "-qm", "remove runner")
    blocked = _push(work)
    assert blocked.returncode != 0
    combined = blocked.stdout + blocked.stderr
    assert "missing" in combined.lower()
    assert _remote_head(work) == ""


def test_real_push_defers_wide_scope_and_full_run_still_finds_the_failure(tmp_path):
    work, _remote, _probe = _fixture_repository(tmp_path)
    assert _push(work).returncode == 0
    hidden = work / "tests/unit/test_hidden_failure.py"
    hidden.write_text("def test_hidden(): assert False, 'outside the fast set'\n",
                      encoding="utf-8", newline="\n")
    (work / "pyproject.toml").write_text("[project]\nname = 'w13-fixture'\n",
                                         encoding="utf-8", newline="\n")
    _git(work, "add", "tests/unit/test_hidden_failure.py", "pyproject.toml")
    _git(work, "commit", "-qm", "wide config change with a hidden failure")
    deferred = _push(work)
    assert deferred.returncode == 0, deferred.stdout + deferred.stderr
    combined = deferred.stdout + deferred.stderr
    assert "full_validation_pending" in combined
    assert "test_hidden_failure" not in combined
    full = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/unit"],
                          cwd=str(work), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=600)
    assert full.returncode != 0
    assert "test_hidden" in full.stdout
