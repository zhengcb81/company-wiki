"""Commits stay static; behavior tests run at push/CI and implementation nodes."""

import re
from pathlib import Path

import yaml


def _hooks():
    config = Path(__file__).resolve().parents[2] / ".pre-commit-config.yaml"
    return [hook for repo in yaml.safe_load(config.read_text(encoding="utf-8"))["repos"]
            for hook in repo["hooks"]]


def test_commit_does_not_repeat_behavior_tests():
    for hook in _hooks():
        entry = hook["entry"]
        assert "pytest" not in entry
        assert "pre_push_gate.py" not in entry


def test_config_check_only_runs_for_config_and_loader_changes():
    doctor = next(hook for hook in _hooks() if hook["id"] == "config-doctor")
    assert not doctor.get("always_run", False)
    trigger = re.compile(doctor["files"])
    for filename in ("config.yaml", "config/source_catalog.yaml",
                     "config/source_catalog_worker.yaml", "scripts/config.py",
                     "scripts/config_doctor.py", "src/company_wiki/config.py",
                     "src/company_wiki/source_catalog/config.py"):
        assert trigger.search(filename), filename
    for filename in ("README.md", "docs/plans/current/task_plan.md",
                     "src/company_wiki/automation/worker.py"):
        assert not trigger.search(filename), filename


def test_type_check_covers_changed_runtime_bodies_without_a_fixed_allowlist():
    hook = next(hook for hook in _hooks() if hook["id"] == "mypy-contract")
    trigger = re.compile(hook["files"])
    for filename in ("src/company_wiki/automation/narrative_run_store.py",
                     "src/company_wiki/source_catalog/cli.py",
                     "src/company_wiki/source_catalog/local_reconcile.py",
                     "src/company_wiki/new_runtime_module.py"):
        assert trigger.search(filename), filename
    assert hook.get("pass_filenames", True), "mypy must check each changed body, not only skipped imports"
    assert "src/" not in hook["entry"], "the commit hook must not repeat all-src CI"
    assert not trigger.search("docs/plans/current/progress.md")


def test_ci_runs_the_complete_source_type_check_once():
    workflow = Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"
    config = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    checks = [step["run"] for job in config["jobs"].values() for step in job["steps"]
              if "-m mypy" in step.get("run", "")]
    assert checks == ["python -m mypy src"]
