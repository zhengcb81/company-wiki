"""AUTO-1 read-only CLI contract: diagnostics must work before any store exists."""

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = ROOT / "src" / "company_wiki" / "automation" / "cli.py"


def run_cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["MINIMAX_API_KEY"] = "must-not-be-read"
    env["MIMO_API_KEY"] = "must-not-be-read"
    return subprocess.run(
        [sys.executable, "-m", "company_wiki.automation.cli", *args],
        cwd=tmp_path,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=10,
        check=False,
    )


def test_cli_file_exists_before_contract_execution():
    assert CLI_PATH.is_file(), "expected red: AUTO-1 read-only CLI is not implemented"


def test_help_is_available_without_store_or_network(tmp_path):
    result = run_cli(tmp_path, "--help")
    assert result.returncode == 0, result.stderr
    assert "status" in result.stdout
    assert "doctor" in result.stdout
    assert "daemon" not in result.stdout.lower()
    assert "approve" not in result.stdout.lower()


def test_status_json_is_stable_honest_and_read_only(tmp_path):
    before = list(tmp_path.iterdir())
    result = run_cli(tmp_path, "status", "--json")
    after = list(tmp_path.iterdir())
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "database": None,
        "mode": "off",
        "next_work_unit": "AUTO-7",
        "schema_version": 1,
        "status": "not_configured",
        "writes_performed": 0,
    }
    assert before == after == []


def test_doctor_json_requires_no_llm_key_network_or_writes(tmp_path):
    result = run_cli(tmp_path, "doctor", "--json")
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "checks": {
            "automation_store": "not_configured",
            "store_importable": True,
            "registry_importable": True,
            "policy_importable": True,
            "planner_importable": True,
            "retry_importable": True,
            "outbox_importable": True,
            "worker_importable": True,
            "event_sources_importable": True,
            "controller_importable": True,
            "gold_review_handler_importable": True,
            "human_inbox_importable": True,
            "llm_required": False,
            "models_importable": True,
            "network_required": False,
        },
        "overall": "ready_for_auto_7",
        "schema_version": 1,
        "writes_performed": 0,
    }
    assert list(tmp_path.iterdir()) == []


def test_cli_does_not_echo_secret_environment_values(tmp_path):
    for command in (("status", "--json"), ("doctor", "--json"), ("--help",)):
        result = run_cli(tmp_path, *command)
        combined = result.stdout + result.stderr
        assert "must-not-be-read" not in combined


def test_unknown_command_has_argparse_exit_code_and_no_files(tmp_path):
    result = run_cli(tmp_path, "run-daemon")
    assert result.returncode == 2
    assert result.stdout == ""
    assert list(tmp_path.iterdir()) == []


def test_mutating_and_future_commands_are_not_exposed_in_auto_1(tmp_path):
    for command in ("plan", "inbox", "submit-review", "approve-action"):
        result = run_cli(tmp_path, command)
        assert result.returncode == 2
        assert list(tmp_path.iterdir()) == []

