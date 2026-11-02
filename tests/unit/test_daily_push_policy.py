"""Real isolated Git hook E2Es; scheduling policy has one owner in test_pre_push_gate.

These are actual local pushes into temporary bare repositories. They preserve
failure blocking, full-range changes, documentation skips, missing-runner
failure and the explicit gap between daily feedback and full validation.
"""
from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools import pre_push_gate as gate  # noqa: E402

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
HOOK_AND_GATE_FILES = (".githooks/pre-push", "tools/pre_push_gate.py",
                       "tools/changed_unit_tests.py",
                       "src/company_wiki/_bounded_process.py",
                       "src/company_wiki/_process_tree.py")


def test_hook_blocks_and_reports_a_missing_gate_runner(tmp_path):
    hooks = tmp_path / ".githooks"
    hooks.mkdir()
    shutil.copyfile(REPOSITORY_ROOT / ".githooks/pre-push", hooks / "pre-push")
    proc = subprocess.run(["sh", str(hooks / "pre-push")], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=60)
    assert proc.returncode != 0
    assert "missing" in (proc.stdout + proc.stderr).lower()


def _fixture_environment():
    # A hook exports its parent repository, and the outer test may disable
    # plugin autoload. Neither may silently redefine this isolated Git E2E.
    env = dict(os.environ)
    for name in gate.GIT_REPOSITORY_CONTEXT:
        env.pop(name, None)
    env.pop("PYTEST_ADDOPTS", None)
    env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_PLUGINS="pytest_timeout",
               PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    return env


def _git(cwd, *command):
    proc = subprocess.run(("git", *command), cwd=str(cwd), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=120,
                          env=_fixture_environment())
    assert proc.returncode == 0, proc.stderr
    return proc


def test_pre_push_hook_is_tracked_as_executable_for_linux_worktrees():
    entry = _git(REPOSITORY_ROOT, "ls-files", "--stage", ".githooks/pre-push").stdout
    assert entry.startswith("100755 "), entry


def _write_smoke_stubs(root: Path) -> None:
    """Materialise each actual daily node so the fixture repo can run them."""
    cases: dict[str, list[str]] = {}
    for case in gate.DAILY_PUSH_CASES:
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
        shutil.copy2(REPOSITORY_ROOT / relative, target)
    _write_smoke_stubs(work)
    probe = work / gate.DAILY_PUSH_CASES[0].split("::", 1)[0]
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text(f"def {gate.DAILY_PUSH_CASES[0].split('::', 1)[1]}(): pass\n", encoding="utf-8", newline="\n")
    # The gate process byte-compiles its own imported tools; keep that noise
    # out of the pushed ranges so the diff reflects the intended change only.
    (work / ".gitignore").write_text("__pycache__/\n", encoding="utf-8", newline="\n")
    # Stop pytest discovery at this synthetic repo, including when its owned
    # basetemp sits inside the real checkout. Never inherit production config.
    (work / "pytest.ini").write_text("[pytest]\n", encoding="utf-8", newline="\n")
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
                          errors="replace", timeout=600, env=_fixture_environment())


def _remote_head(work: Path) -> str:
    listing = _git(work, "ls-remote", "origin", "refs/heads/master").stdout.split()
    return listing[0] if listing else ""


def test_real_push_green_fast_pass_then_blocked_by_a_ran_failure(tmp_path, monkeypatch):
    foreign_index = tmp_path / "foreign-index-must-not-be-written"
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "foreign-repository"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "foreign-work-tree"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(foreign_index))
    work, _remote, probe = _fixture_repository(tmp_path)
    green = _push(work)
    assert green.returncode == 0, green.stdout + green.stderr
    output = green.stdout + green.stderr
    assert "local_fast_pass" in output
    assert "full_validation_pending" in output
    probe.write_text(f"def {gate.DAILY_PUSH_CASES[0].split('::', 1)[1]}(): assert False, 'probe failure'\n",
                     encoding="utf-8", newline="\n")
    _git(work, "add", gate.DAILY_PUSH_CASES[0].split("::", 1)[0])
    _git(work, "commit", "-qm", "red probe")
    local_head = _git(work, "rev-parse", "HEAD").stdout.strip()
    blocked = _push(work)
    assert blocked.returncode != 0
    combined = blocked.stdout + blocked.stderr
    assert "PUSH CHECKS RED" in combined
    assert gate.DAILY_PUSH_CASES[0].split("::", 1)[1] in combined
    assert _remote_head(work) != local_head
    assert not foreign_index.exists()


def test_real_docs_push_runs_no_tests_but_does_not_hide_earlier_code(tmp_path):
    work, _remote, probe = _fixture_repository(tmp_path)
    initial = _push(work)
    assert initial.returncode == 0, initial.stdout + initial.stderr
    evidence = work / "docs/plans/fixture/probe.py"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("raise RuntimeError('archived only')\n", encoding="utf-8")
    _git(work, "add", "docs/plans/fixture/probe.py")
    _git(work, "commit", "-qm", "plan evidence only")
    docs = _push(work)
    output = docs.stdout + docs.stderr
    assert docs.returncode == 0, output
    assert "tests_not_run" in output
    assert "local_fast_pass" not in output
    assert "passed" not in output
    assert _remote_head(work) == _git(work, "rev-parse", "HEAD").stdout.strip()

    probe.write_text(f"def {gate.DAILY_PUSH_CASES[0].split('::', 1)[1]}(): assert False, 'earlier code failure'\n",
                     encoding="utf-8", newline="\n")
    _git(work, "add", gate.DAILY_PUSH_CASES[0].split("::", 1)[0])
    _git(work, "commit", "-qm", "unpublished failing code")
    evidence.write_text("# latest commit is still only evidence\n", encoding="utf-8")
    _git(work, "add", "docs/plans/fixture/probe.py")
    _git(work, "commit", "-qm", "docs after code")
    blocked = _push(work)
    combined = blocked.stdout + blocked.stderr
    assert blocked.returncode != 0, combined
    assert "PUSH CHECKS RED" in combined
    assert "earlier code failure" in combined
    assert _remote_head(work) != _git(work, "rev-parse", "HEAD").stdout.strip()


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


def test_real_push_defers_unknown_config_scope_and_full_run_still_finds_the_failure(tmp_path):
    work, _remote, _probe = _fixture_repository(tmp_path)
    assert _push(work).returncode == 0
    hidden = work / "tests/unit/test_hidden_failure.py"
    hidden.write_text("from pathlib import Path\n"
                      "def test_hidden():\n"
                      "    config = Path(__file__).resolve().parents[2] / 'pyproject.toml'\n"
                      "    assert 'ready = true' in config.read_text(), 'outside the fast set'\n",
                      encoding="utf-8", newline="\n")
    config = work / 'pyproject.toml'
    config.write_text("[project]\nname = 'w13-fixture'\n[tool.fixture]\nready = true\n",
                                         encoding="utf-8", newline="\n")
    _git(work, "add", "tests/unit/test_hidden_failure.py", "pyproject.toml")
    _git(work, "commit", "-qm", "green baseline with a known unit consumer")
    baseline = _push(work)
    assert baseline.returncode == 0, baseline.stdout + baseline.stderr
    # Only configuration changes now. No changed Python/import edge proves
    # this dependency. Everything outside fixed smoke belongs to author tests
    # and CI/full validation, whether or not an import consumer is known.
    config.write_text("[project]\nname = 'w13-fixture'\n[tool.fixture]\nready = false\n",
                      encoding="utf-8", newline="\n")
    _git(work, 'add', 'pyproject.toml')
    _git(work, 'commit', '-qm', 'config-only regression outside known static scope')
    deferred = _push(work)
    assert deferred.returncode == 0, deferred.stdout + deferred.stderr
    combined = deferred.stdout + deferred.stderr
    assert "full_validation_pending" in combined
    assert "test_hidden_failure" not in combined
    full = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/unit"],
                          cwd=str(work), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=600,
                          env=_fixture_environment())
    assert full.returncode != 0
    assert "test_hidden" in full.stdout
