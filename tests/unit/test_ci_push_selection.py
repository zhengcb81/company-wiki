"""Pushes include changed behavior across the whole range, with conservative fallbacks."""
from pathlib import Path
import subprocess
import sys

import pytest

from tools.changed_unit_tests import changed_paths, select_unit_tests
from tools import pre_push_gate as gate


def _file(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return name


@pytest.fixture
def project(tmp_path):
    _file(tmp_path, "src/pkg/__init__.py", "")
    _file(tmp_path, "src/pkg/core.py", "value = 1\n")
    _file(tmp_path, "src/pkg/reader.py", "from . import core\n")
    _file(tmp_path, "tests/support/fixture.py", "from pkg import reader\n")
    _file(tmp_path, "tests/unit/test_reader.py", "from support import fixture\n")
    _file(tmp_path, "tests/unit/test_unrelated.py", "def test_other(): pass\n")
    return tmp_path


def test_transitive_relative_import_includes_fixture_consumers(project):
    selected, reason = select_unit_tests(project, {"src/pkg/core.py"})
    assert selected == ["tests/unit/test_reader.py"]
    assert reason == "affected unit tests"


@pytest.mark.parametrize("changed", ["tests/support/fixture.py", "tests/unit/test_reader.py"])
def test_changed_test_or_fixture_is_not_omitted(project, changed):
    assert select_unit_tests(project, {changed})[0] == ["tests/unit/test_reader.py"]


@pytest.mark.parametrize("changed", [
    "config/local_ocr.json", "requirements.txt", "pyproject.toml", "conftest.py",
    "tests/conftest.py", "tools/pre_push_gate.py", ".github/workflows/ci.yml",
    "src/pkg/deleted.py", "tests/fixtures/input.json",
])
def test_environment_entrypoint_deleted_module_or_unknown_fixture_falls_back(project, changed):
    assert select_unit_tests(project, {changed})[0] == ["tests/unit"]


@pytest.mark.parametrize("body", [
    "import importlib\nmodule = importlib.import_module(name)\n",
    "import subprocess\nsubprocess.run(['python', '-m', name])\n",
    "import runpy\nrunpy.run_module(name)\n",
    "exec(name)\n",
    "from subprocess import run as execute\nexecute(argv)\n",
    "import subprocess as sp\nsp.run(argv)\n",
    "from importlib import import_module as load\nload(name)\n",
    "from runpy import run_path as execute\nexecute('scripts/child.py')\n",
])
def test_changed_dynamic_execution_falls_back(project, body):
    _file(project, "src/pkg/core.py", body)
    assert select_unit_tests(project, {"src/pkg/core.py"})[0] == ["tests/unit"]


def test_literal_dynamic_import_is_detected(project):
    _file(project, "tests/unit/test_dynamic.py", "import importlib\nimportlib.import_module('pkg.core')\n")
    assert select_unit_tests(project, {"src/pkg/core.py"})[0] == [
        "tests/unit/test_dynamic.py", "tests/unit/test_reader.py",
    ]


def test_unchanged_computed_import_consumer_is_kept_alongside_static_consumer(project):
    _file(project, "tests/unit/test_runtime.py", "from importlib import import_module as load\nload(name)\n")
    assert select_unit_tests(project, {"src/pkg/core.py"})[0] == [
        "tests/unit/test_reader.py", "tests/unit/test_runtime.py",
    ]


@pytest.mark.parametrize("body", [
    "import importlib\nimportlib.import_module('.core', 'pkg')\n",
    "from runpy import run_path as run\nrun('src/pkg/core.py')\n",
    "from importlib import import_module\nimport_module('core')\n",
])
def test_literal_relative_import_bare_module_or_file_consumer_is_not_lost(project, body):
    _file(project, "tests/unit/test_dynamic.py", body)
    assert "tests/unit/test_dynamic.py" in select_unit_tests(project, {"src/pkg/core.py"})[0]


def test_unknown_source_dependency_falls_back_instead_of_silent_skip(project):
    _file(project, "src/pkg/plugin.py", "value = 1\n")
    assert select_unit_tests(project, {"src/pkg/plugin.py"})[0] == ["tests/unit"]


def test_document_only_push_does_not_run_full_units(project):
    assert select_unit_tests(project, {"docs/report.md", "docs/receipt.json"})[0] == []


def test_git_range_covers_earlier_code_and_final_document_commit(project, monkeypatch):
    commands = []
    def git(cmd, **kwargs):
        commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "src/pkg/core.py\ndocs/report.md\n", "")
    monkeypatch.setattr(subprocess, "run", git)
    old, new = "a" * 40, "b" * 40
    changes = changed_paths(project, f"refs/heads/master {new} refs/heads/master {old}\n")
    assert changes == {"src/pkg/core.py", "docs/report.md"}
    assert commands == [["git", "diff", "--no-renames", "--name-only", old, new, "--"]]


def test_multiple_refs_union_and_branch_deletion(project, monkeypatch):
    values = iter(["src/pkg/core.py\n", "tests/unit/test_unrelated.py\n"])
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, next(values), ""))
    a, b, c, z = "a" * 40, "b" * 40, "c" * 40, "0" * 40
    push = f"refs/heads/a {b} refs/heads/a {a}\nrefs/heads/b {c} refs/heads/b {b}\n(delete) {z} refs/heads/c {c}\n"
    assert changed_paths(project, push) == {"src/pkg/core.py", "tests/unit/test_unrelated.py"}


@pytest.mark.parametrize("push", ["", "bad line", f"a {'a' * 40} b {'0' * 40}"])
def test_no_comparable_push_range_falls_back(project, push):
    assert changed_paths(project, push) is None


def test_git_failure_falls_back(project, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 128, "", "missing object"))
    assert changed_paths(project, f"a {'b' * 40} b {'a' * 40}") is None


def test_hook_and_ci_keep_fast_commit_and_use_correct_entrypoints():
    root = Path(__file__).resolve().parents[2]
    hook = (root / ".githooks/pre-push").read_text(encoding="utf-8")
    assert "--push-checks" in hook
    assert "--fast-contracts-only" not in hook
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "pytest tests/unit" in workflow
    assert "--fast-contracts-only" in workflow


def test_push_failure_is_propagated_and_suites_are_not_duplicated(monkeypatch):
    seen = []
    monkeypatch.setattr(sys, "stdin", type("Input", (), {"read": lambda self: "refs"})())
    monkeypatch.setattr(gate, "changed_paths", lambda root, data: {"test"})
    monkeypatch.setattr(gate, "select_unit_tests", lambda root, files: (["tests/unit"], "fixture fallback"))
    def pytest_gate(cmd, label):
        seen.append(cmd)
        return 7
    monkeypatch.setattr(gate, "_run_pytest_gate", pytest_gate)
    assert gate.main(["--push-checks"]) == 7
    assert len(seen) == 1
    assert seen[0].count("tests/unit") == 1
    assert not any(x.startswith("tests/unit/") for x in seen[0])
    assert any(x.startswith("tests/contract/") for x in seen[0])


@pytest.mark.parametrize("entrypoint", ["--push-checks", "--fast-contracts-only"])
def test_published_summary_contracts_run_in_both_ci_and_push(entrypoint, monkeypatch):
    seen = []
    monkeypatch.setattr(sys, "stdin", type("Input", (), {"read": lambda self: "refs"})())
    monkeypatch.setattr(gate, "changed_paths", lambda root, data: {"docs/report.md"})
    monkeypatch.setattr(gate, "select_unit_tests", lambda root, files: ([], "documents only"))
    monkeypatch.setattr(gate, "_run_pytest_gate", lambda cmd, label: seen.append(cmd) or 0)

    assert gate.main([entrypoint]) == 0
    assert len(seen) == 1
    assert "tests/contract/test_narrative_output_plan.py" in seen[0]
    assert "tests/contract/test_summary_group_coverage.py" in seen[0]
    assert "tests/contract/test_official_transcript_layouts.py" in seen[0]


@pytest.mark.parametrize("entrypoint", ["--push-checks", "--fast-contracts-only"])
def test_source_scope_guard_is_shared_but_full_cache_matrix_is_major_node_only(entrypoint, monkeypatch):
    seen = []
    monkeypatch.setattr(sys, "stdin", type("Input", (), {"read": lambda self: "refs"})())
    monkeypatch.setattr(gate, "changed_paths", lambda root, data: {"docs/report.md"})
    monkeypatch.setattr(gate, "select_unit_tests", lambda root, files: ([], "documents only"))
    monkeypatch.setattr(gate, "_run_pytest_gate", lambda cmd, label: seen.append(cmd) or 0)

    assert gate.main([entrypoint]) == 0
    assert len(seen) == 1
    assert "tests/contract/test_source_scope_qualification.py" in seen[0]
    assert "tests/contract/test_fresh_cache_behavior_receipts.py" not in seen[0]


def test_planning_evidence_only_changes_do_not_schedule_full_ci():
    import yaml
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.load((root / ".github/workflows/ci.yml").read_text(encoding="utf-8"),
                         Loader=yaml.BaseLoader)
    for event in ("push", "pull_request"):
        assert "docs/plans/**" in workflow["on"][event]["paths-ignore"]
        assert "src/**" not in workflow["on"][event]["paths-ignore"]
        assert "tests/**" not in workflow["on"][event]["paths-ignore"]
    assert "pytest tests/unit" in (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")

@pytest.mark.parametrize("archive", [
    "docs/plans/run/evidence/probe.py", "docs/plans/run/conftest.py",
    "docs/plans/run/requirements.txt", "docs/plans/run/evidence/result.json",
    "docs/plans/run/evidence/original.docx",
])
def test_planning_archive_is_not_live_behavior_even_with_code_suffix(project, archive):
    assert select_unit_tests(project, {archive}) == ([], "no behavior changes")


def test_mixed_live_source_and_planning_archive_keeps_actual_consumers(project):
    _file(project, "tests/unit/test_runtime.py", "from importlib import import_module as load\nload(name)\n")
    assert select_unit_tests(project, {
        "src/pkg/core.py", "docs/plans/run/conftest.py", "docs/plans/run/evidence/probe.py",
    }) == (["tests/unit/test_reader.py", "tests/unit/test_runtime.py"], "affected unit tests")


def test_live_unit_change_with_archived_probe_does_not_seed_unrelated_cli_tests(project):
    _file(project, "tests/unit/test_runtime.py", "import subprocess\nsubprocess.run(argv)\n")
    _file(project, "tests/unit/test_reader.py", "import subprocess\nsubprocess.run(argv)\n")
    assert select_unit_tests(project, {
        "tests/unit/test_reader.py", "docs/plans/run/evidence/probe.py",
    }) == (["tests/unit/test_reader.py"], "affected unit tests")


def test_unit_only_change_keeps_known_transitive_test_helper_consumers(project):
    _file(project, "tests/unit/test_helper.py", "import subprocess\nsubprocess.run(argv)\n")
    _file(project, "tests/unit/test_reader.py", "from tests.unit import test_helper\n")
    _file(project, "tests/unit/test_runtime.py", "import subprocess\nsubprocess.run(argv)\n")
    assert select_unit_tests(project, {"tests/unit/test_helper.py"}) == (
        ["tests/unit/test_helper.py", "tests/unit/test_reader.py"], "affected unit tests")
