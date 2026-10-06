"""CLI subprocess E2E for the N6-FOOTPRINT storage scan.

Runs ``tools/storage_footprint/run.py`` as a real child process against fixture
roots, asserts JSON/stdout/exit codes, proves zero original body reads through
the ``sitecustomize`` audit hook, and verifies the fixture tree is restored
byte- and mtime-identical afterwards.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fixtures import snapshot_tree, write_tree  # noqa: E402

pytestmark = pytest.mark.e2e

TESTS_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = TESTS_DIR.parent
RUN_PY = PACKAGE_DIR / "run.py"
HOOK_DIR = TESTS_DIR / "e2e_hook"

SPEC = {
    "companies/acme/brief.txt": "0123456789",
    "companies/acme/wiki/page.md": "abcdef",
    ".source_catalog/catalog.sqlite3": "y" * 16,
    "tmp/scratch/log.txt": "log",
    "docs/plans/p.md": "#p",
    "src/mod.py": "V=1",
}


def _cli_env(root: Path, open_log: Path | None = None) -> dict[str, str]:
    env = dict(os.environ)
    hook_path = str(HOOK_DIR)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = hook_path if not existing else hook_path + os.pathsep + existing
    if open_log is not None:
        env["N6_E2E_ROOT"] = str(root)
        env["N6_E2E_OPEN_LOG"] = str(open_log)
    else:
        env.pop("N6_E2E_ROOT", None)
        env.pop("N6_E2E_OPEN_LOG", None)
    env["PYTHON_DOTENV_DISABLED"] = "1"
    env["COMPANY_WIKI_NETWORK"] = "blocked"
    env["COMPANY_WIKI_REAL_LLM"] = "0"
    for secret in (
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "MINIMAX_API_KEY",
        "MIMO_API_KEY",
        "TAVILY_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        env.pop(secret, None)
    return env


def _run(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RUN_PY), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(PACKAGE_DIR.parents[1]),
        timeout=120,
        check=False,
    )


def _stdout_json(proc: subprocess.CompletedProcess) -> dict:
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    assert len(lines) == 1, proc.stdout
    return json.loads(lines[0])


def test_sitecustomize_hook_catches_a_deliberate_read(tmp_path):
    root = write_tree(tmp_path / "root", SPEC)
    open_log = tmp_path / "opens.json"
    env = _cli_env(root, open_log)
    target = root / "companies" / "acme" / "brief.txt"
    code = f"import io; io.open({str(target)!r}, 'rb').read()"
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    records = json.loads(open_log.read_text(encoding="utf-8"))
    assert records, "audit hook must record the deliberate read"
    assert records[0]["path"].replace("\\", "/") == "companies/acme/brief.txt"


def test_cli_scan_writes_report_with_zero_body_reads(tmp_path):
    root = write_tree(tmp_path / "root", SPEC)
    before = snapshot_tree(root)
    open_log = tmp_path / "opens.json"
    output = tmp_path / "out" / "report.json"
    env = _cli_env(root, open_log)
    proc = _run(
        [
            "--project-root",
            str(root),
            "--max-files",
            "10000",
            "--max-seconds",
            "60",
            "--output",
            str(output),
        ],
        env,
    )
    assert proc.returncode == 0, proc.stderr
    stdout = _stdout_json(proc)
    assert stdout["status"] == "written"
    assert stdout["schema_version"] == "cwp-storage-footprint/1"
    assert stdout["complete"] is True
    assert stdout["stop_reason"] == "complete"

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "cwp-storage-footprint/1"
    assert payload["totals"]["files_measured"] == len(SPEC)
    assert payload["calls"] == {
        "original_body_reads": 0,
        "llm": 0,
        "network": 0,
        "deleted": 0,
    }
    assert output.stat().st_size <= 256 * 1024

    records = json.loads(open_log.read_text(encoding="utf-8"))
    assert records == [], records
    assert snapshot_tree(root) == before
    assert [path.name for path in output.parent.iterdir()] == ["report.json"]
    assert not any(path.name.endswith(".tmp") for path in output.parent.iterdir())


def test_cli_budget_stop_reports_partial(tmp_path):
    root = write_tree(
        tmp_path / "root",
        {f"docs/plans/note-{index}.md": f"note-{index}" for index in range(6)},
    )
    before = snapshot_tree(root)
    output = tmp_path / "out" / "report.json"
    proc = _run(
        [
            "--project-root",
            str(root),
            "--max-files",
            "2",
            "--max-seconds",
            "60",
            "--output",
            str(output),
        ],
        _cli_env(root),
    )
    assert proc.returncode == 0, proc.stderr
    stdout = _stdout_json(proc)
    assert stdout["complete"] is False
    assert stdout["stop_reason"] == "budget"
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["scope"]["complete"] is False
    assert payload["totals"]["files_measured"] == 2
    assert snapshot_tree(root) == before


def test_cli_refuses_unknown_existing_output(tmp_path):
    root = write_tree(tmp_path / "root", SPEC)
    output = tmp_path / "out" / "report.json"
    output.parent.mkdir(parents=True)
    foreign = json.dumps({"schema_version": "foreign/1"}).encode("utf-8")
    output.write_bytes(foreign)
    proc = _run(
        [
            "--project-root",
            str(root),
            "--max-files",
            "100",
            "--max-seconds",
            "30",
            "--output",
            str(output),
        ],
        _cli_env(root),
    )
    assert proc.returncode == 2, proc.stderr
    stdout = _stdout_json(proc)
    assert stdout["status"] == "refused"
    assert stdout["reason"] == "output_exists_unknown"
    assert output.read_bytes() == foreign


def test_cli_refuses_output_inside_scanned_root(tmp_path):
    root = write_tree(tmp_path / "root", SPEC)
    before = snapshot_tree(root)
    output = root / "report.json"
    proc = _run(
        [
            "--project-root",
            str(root),
            "--max-files",
            "100",
            "--max-seconds",
            "30",
            "--output",
            str(output),
        ],
        _cli_env(root),
    )
    assert proc.returncode == 2, proc.stderr
    stdout = _stdout_json(proc)
    assert stdout["reason"] == "report_path_overlaps_data"
    assert not output.exists()
    assert snapshot_tree(root) == before


def test_cli_refuses_invalid_limits(tmp_path):
    root = write_tree(tmp_path / "root", SPEC)
    output = tmp_path / "out" / "report.json"
    proc = _run(
        [
            "--project-root",
            str(root),
            "--max-files",
            "0",
            "--max-seconds",
            "30",
            "--output",
            str(output),
        ],
        _cli_env(root),
    )
    assert proc.returncode == 2, proc.stderr
    assert _stdout_json(proc)["reason"] == "invalid_limits"
    assert not output.exists()


def test_cli_missing_required_argument_exits_two(tmp_path):
    root = write_tree(tmp_path / "root", SPEC)
    proc = _run(
        ["--project-root", str(root), "--max-files", "10", "--max-seconds", "5"],
        _cli_env(root),
    )
    assert proc.returncode == 2
    assert proc.stderr
    assert not (root / "report.json").exists()


def test_cli_missing_root_is_refused(tmp_path):
    output = tmp_path / "out" / "report.json"
    proc = _run(
        [
            "--project-root",
            str(tmp_path / "absent-root"),
            "--max-files",
            "10",
            "--max-seconds",
            "5",
            "--output",
            str(output),
        ],
        _cli_env(tmp_path),
    )
    assert proc.returncode == 2, proc.stderr
    assert _stdout_json(proc)["reason"] == "invalid_root"
    assert not output.exists()
