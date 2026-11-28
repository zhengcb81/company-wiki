"""Prove the company-wiki CI entrypoint uses executed, rather than collected, nodes."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPOSITORY = Path(__file__).resolve().parents[2]


def _offline_environment() -> dict[str, str]:
    env = {
        name: value for name, value in os.environ.items()
        if name.upper() in {"SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC", "PATH",
                            "PATHEXT", "TEMP", "TMP", "TMPDIR", "USERNAME", "USERPROFILE"}
    }
    env.update(PYTHONPATH=str(REPOSITORY), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
               PYTEST_PLUGINS="pytest_timeout", PYTHONUTF8="1")
    return env


def _invoke(tmp_path: Path, *command: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", "-m", *command],
        env=_offline_environment(), cwd=tmp_path, stdin=subprocess.DEVNULL, capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=60,
    )


def _write_policy(tmp_path: Path) -> Path:
    platform = "windows" if sys.platform == "win32" else sys.platform
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"schema": "s6-test-policy/1", "platforms": {
        platform: {"roots": ["tests"], "markexpr": ""},
    }}), encoding="utf-8")
    return policy


@pytest.mark.parametrize("omits_execution", [False, True])
def test_ci_runner_never_counts_a_skipped_case_as_executed(tmp_path, omits_execution):
    source = tmp_path / "tests"
    source.mkdir()
    (source / "test_examples.py").write_text(
        "import pytest\n"
        "def test_first():\n"
        "    assert True\n"
        "def test_second():\n"
        + ("    pytest.skip('fixture skip')\n" if omits_execution else "    assert True\n"),
        encoding="utf-8",
    )
    policy = _write_policy(tmp_path)
    evidence = tmp_path / "evidence"
    outcome = _invoke(
        tmp_path, "tools.run_ci_evidence", "--revision", "a" * 40,
        "--policy", str(policy), "--output", str(evidence),
    )
    assert outcome.returncode == int(omits_execution), outcome.stdout + outcome.stderr
    collected = json.loads((evidence / "collected.json").read_bytes())
    executed = json.loads((evidence / "executed.json").read_bytes())
    assert collected["role"] == "inventory" and len(collected["node_ids"]) == 2
    assert executed["role"] == "execution" and len(executed["node_ids"]) == 2 - int(omits_execution)
    if omits_execution:
        assert b"unexecuted:tests/test_examples.py::test_second" in outcome.stdout


def test_ci_shards_execute_each_inventory_case_exactly_once(tmp_path):
    source = tmp_path / "tests"
    source.mkdir()
    for index in range(12):
        (source / f"test_example_{index}.py").write_text(
            "def test_case():\n    assert True\n", encoding="utf-8"
        )
    policy = _write_policy(tmp_path)
    common = ("tools.run_ci_evidence", "--revision", "b" * 40, "--policy", str(policy))
    inventory_outcome = _invoke(tmp_path, *common, "--collect", "--output", "inventory")
    assert inventory_outcome.returncode == 0, inventory_outcome.stdout + inventory_outcome.stderr
    inventory = json.loads((tmp_path / "inventory" / "collected.json").read_bytes())
    assert len(inventory["node_ids"]) == 12
    executed = set()
    for index in range(2):
        output = f"shard-{index}"
        shard_outcome = _invoke(tmp_path, *common, "--shard", f"{index}/2", "--output", output)
        assert shard_outcome.returncode == 0, shard_outcome.stdout + shard_outcome.stderr
        report = json.loads((tmp_path / output / "executed.json").read_bytes())
        assert report["node_ids"]
        assert executed.isdisjoint(report["node_ids"])
        executed.update(report["node_ids"])
    assert executed == set(inventory["node_ids"])
