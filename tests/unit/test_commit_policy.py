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
