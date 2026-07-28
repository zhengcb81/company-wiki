"""WR-1: encoding-safe and precise process inventory for source-catalog worker.

搂10.8.2 contract:
1. PowerShell returning a UTF-8 JSON array containing Chinese paths must not
   crash ``_scan_source_catalog_processes`` and must categorize correctly.
2. Runner raising ``UnicodeDecodeError`` / ``OSError`` / ``TimeoutExpired``
   must NOT propagate; the inventory dict must surface ``inventory_error``.
3. Six command categories (production worker / ignored status / ignored ps1 /
   ignored audit / pytest temp worker / foreign worker / foreign
   other-project worker) must be classified exactly:
   - production / pytest_temp / foreign are real ``worker`` subcommands
   - ``worker-status`` / ``source_catalog_control.ps1`` / ``Get-CimInstance``
     audit commands go to ``ignored_matching_processes`` with a reason.
4. ``inventory_error`` must be consistent between direct inventory calls and
   the ``WorkerController.status()`` JSON output (no exception leaks).
5. ``ignored_matching_processes`` entries contain pid + reason only; full
   command lines (which can contain secrets/PII) are never stored.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess



_PROD_PROJECT = "C:/Users/閮戞浘娉?Projects/company-wiki"
_PROD_CONFIG = f"{_PROD_PROJECT}/config/source_catalog.yaml"
_PROD_WORKER_CONFIG = f"{_PROD_PROJECT}/config/source_catalog_worker.yaml"
_PYTEST_PROJECT = "C:/Users/閮戞浘娉?AppData/Local/Temp/pytest-of-ABC/test_xyz0/project"
_PYTEST_CONFIG = f"{_PYTEST_PROJECT}/config/source_catalog.yaml"
_PYTEST_WORKER_CONFIG = f"{_PYTEST_PROJECT}/config/source_catalog_worker.yaml"
_FOREIGN_PROJECT = "D:/other/company-wiki"
_FOREIGN_CONFIG = f"{_FOREIGN_PROJECT}/config/source_catalog.yaml"
_FOREIGN_WORKER_CONFIG = f"{_FOREIGN_PROJECT}/config/source_catalog_worker.yaml"


def _completed(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["powershell.exe"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def _make_stdout(rows: list[dict]) -> str:
    if not rows:
        return ""
    if len(rows) == 1:
        return json.dumps(rows[0], ensure_ascii=False)
    return json.dumps(rows, ensure_ascii=False)


def _cmd(config: str, worker_config: str, subcommand: str = "worker") -> str:
    return (
        f"python -m company_wiki.source_catalog.cli "
        f"--config {config} {subcommand} --worker-config {worker_config}"
    )


def test_chinese_path_json_array_does_not_raise(tmp_path):
    """Chinese (UTF-8) process inventory must not raise UnicodeDecodeError."""
    from company_wiki.source_catalog import control

    rows = [
        {
            "ProcessId": 12345,
            "ParentProcessId": 1,
            "CreationDate": "/Date(1700000000000)/",
            "CommandLine": _cmd(_PROD_CONFIG, _PROD_WORKER_CONFIG),
        }
    ]
    stdout = _make_stdout(rows)
    def fake_runner(_project_root):
        return _completed(stdout=stdout)
    result = control._scan_source_catalog_processes(
        Path(_PROD_PROJECT),
        config_path=Path(_PROD_CONFIG),
        worker_config_path=Path(_PROD_WORKER_CONFIG),
        runner=fake_runner,
    )
    assert result["inventory_error"] is None
    assert len(result["production_workers"]) == 1
    assert result["production_workers"][0]["pid"] == 12345
    assert result["production_workers"][0]["creation_date"].startswith("/Date")


def test_unicode_decode_error_returns_inventory_error(tmp_path):
    from company_wiki.source_catalog import control

    def fake_runner(_project_root):
        raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid byte")

    result = control._scan_source_catalog_processes(
        Path(_PROD_PROJECT),
        config_path=Path(_PROD_CONFIG),
        worker_config_path=Path(_PROD_WORKER_CONFIG),
        runner=fake_runner,
    )
    assert result["inventory_error"] is not None
    assert "UnicodeDecodeError" in result["inventory_error"]
    assert result["production_workers"] == []
    assert result["foreign_workers"] == []
    assert result["pytest_temp_workers"] == []
    assert result["ignored_matching_processes"] == []


def test_timeout_expired_returns_inventory_error(tmp_path):
    import subprocess

    from company_wiki.source_catalog import control

    def fake_runner(_project_root):
        raise subprocess.TimeoutExpired(cmd="powershell.exe", timeout=15)

    result = control._scan_source_catalog_processes(
        Path(_PROD_PROJECT),
        config_path=Path(_PROD_CONFIG),
        worker_config_path=Path(_PROD_WORKER_CONFIG),
        runner=fake_runner,
    )
    assert "TimeoutExpired" in result["inventory_error"]
    assert result["production_workers"] == []


def test_os_error_returns_inventory_error(tmp_path):
    from company_wiki.source_catalog import control

    def fake_runner(_project_root):
        raise OSError("powershell.exe not found")

    result = control._scan_source_catalog_processes(
        Path(_PROD_PROJECT),
        config_path=Path(_PROD_CONFIG),
        worker_config_path=Path(_PROD_WORKER_CONFIG),
        runner=fake_runner,
    )
    assert "OSError" in result["inventory_error"]


def test_nonzero_powershell_exit_returns_inventory_error(tmp_path):
    from company_wiki.source_catalog import control

    def fake_runner(_pr):
        return _completed(returncode=1, stderr="boom")
    result = control._scan_source_catalog_processes(
        Path(_PROD_PROJECT),
        config_path=Path(_PROD_CONFIG),
        worker_config_path=Path(_PROD_WORKER_CONFIG),
        runner=fake_runner,
    )
    assert result["inventory_error"] is not None
    assert "powershell_exit=1" in result["inventory_error"]


def test_invalid_json_returns_inventory_error(tmp_path):
    from company_wiki.source_catalog import control

    def fake_runner(_pr):
        return _completed(stdout="not-json{")
    result = control._scan_source_catalog_processes(
        Path(_PROD_PROJECT),
        config_path=Path(_PROD_CONFIG),
        worker_config_path=Path(_PROD_WORKER_CONFIG),
        runner=fake_runner,
    )
    assert result["inventory_error"] is not None
    assert "json_decode_error" in result["inventory_error"]


def test_classify_six_command_categories(tmp_path):
    """搂10.8.2 mandatory six process command categories."""
    from company_wiki.source_catalog import control

    chinese_prod = _cmd(_PROD_CONFIG, _PROD_WORKER_CONFIG, subcommand="worker")
    ignored_status = _cmd(_PROD_CONFIG, _PROD_WORKER_CONFIG, subcommand="worker-status")
    ignored_ps1 = (
        f"powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
        f"{_PROD_PROJECT}/scripts/source_catalog_control.ps1 -Action status"
    )
    ignored_audit = (
        "powershell.exe -NoProfile -Command "
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.CommandLine -match 'company_wiki.source_catalog' } | "
        "ForEach-Object { @{...} }"
    )
    pytest_cmd = _cmd(_PYTEST_CONFIG, _PYTEST_WORKER_CONFIG, subcommand="worker")
    foreign_cmd = _cmd(_FOREIGN_CONFIG, _FOREIGN_WORKER_CONFIG, subcommand="worker")

    rows = [
        {"ProcessId": 100, "CommandLine": chinese_prod},
        {"ProcessId": 101, "CommandLine": ignored_status},
        {"ProcessId": 102, "CommandLine": ignored_ps1},
        {"ProcessId": 103, "CommandLine": ignored_audit},
        {"ProcessId": 200, "CommandLine": pytest_cmd},
        {"ProcessId": 300, "CommandLine": foreign_cmd},
    ]
    stdout = _make_stdout(rows)
    def fake_runner(_pr):
        return _completed(stdout=stdout)
    result = control._scan_source_catalog_processes(
        Path(_PROD_PROJECT),
        config_path=Path(_PROD_CONFIG),
        worker_config_path=Path(_PROD_WORKER_CONFIG),
        runner=fake_runner,
    )
    assert result["inventory_error"] is None
    assert [w["pid"] for w in result["production_workers"]] == [100]
    assert [w["pid"] for w in result["pytest_temp_workers"]] == [200]
    assert [w["pid"] for w in result["foreign_workers"]] == [300]
    ignored = {w["pid"]: w["reason"] for w in result["ignored_matching_processes"]}
    assert set(ignored) == {101, 102, 103}
    assert ignored[101] == "subcommand_worker_status"
    assert ignored[102] == "control_ps1"
    assert ignored[103] == "audit_command"


def test_ignored_processes_do_not_carry_full_command_line(tmp_path):
    """ignored_matching_processes must contain only pid + reason (no command line)."""
    from company_wiki.source_catalog import control

    rows = [
        {
            "ProcessId": 777,
            "CommandLine": _cmd(
                _PROD_CONFIG, _PROD_WORKER_CONFIG, subcommand="worker-stop"
            ),
        },
    ]
    stdout = _make_stdout(rows)
    def fake_runner(_pr):
        return _completed(stdout=stdout)
    result = control._scan_source_catalog_processes(
        Path(_PROD_PROJECT),
        config_path=Path(_PROD_CONFIG),
        worker_config_path=Path(_PROD_WORKER_CONFIG),
        runner=fake_runner,
    )
    assert result["ignored_matching_processes"]
    entry = result["ignored_matching_processes"][0]
    assert set(entry.keys()) == {"pid", "reason"}
    assert entry["reason"] == "subcommand_worker_stop"
    # No full command line stored (could contain secrets/PII).
    assert "commandline" not in {k.lower() for k in entry.keys()}


def test_no_matching_processes_returns_empty_inventory(tmp_path):
    from company_wiki.source_catalog import control

    def fake_runner(_pr):
        return _completed(stdout="")
    result = control._scan_source_catalog_processes(
        Path(_PROD_PROJECT),
        config_path=Path(_PROD_CONFIG),
        worker_config_path=Path(_PROD_WORKER_CONFIG),
        runner=fake_runner,
    )
    assert result["production_workers"] == []
    assert result["foreign_workers"] == []
    assert result["pytest_temp_workers"] == []
    assert result["ignored_matching_processes"] == []
    assert result["inventory_error"] is None


def test_single_row_dict_still_classified(tmp_path):
    """ConvertTo-Json emits a bare object when only one row matches."""
    from company_wiki.source_catalog import control

    rows = {
        "ProcessId": 9001,
        "CommandLine": _cmd(_PROD_CONFIG, _PROD_WORKER_CONFIG),
    }
    stdout = json.dumps(rows, ensure_ascii=False)
    def fake_runner(_pr):
        return _completed(stdout=stdout)
    result = control._scan_source_catalog_processes(
        Path(_PROD_PROJECT),
        config_path=Path(_PROD_CONFIG),
        worker_config_path=Path(_PROD_WORKER_CONFIG),
        runner=fake_runner,
    )
    assert [w["pid"] for w in result["production_workers"]] == [9001]


def test_status_exposes_inventory_error_via_provider(tmp_path, monkeypatch):
    """WorkerController.status() JSON must include inventory_error when set."""
    from company_wiki.source_catalog.control import WorkerController

    project = tmp_path / "project"
    project.mkdir()
    config_path = project / "config" / "source_catalog.yaml"
    worker_config_path = project / "config" / "source_catalog_worker.yaml"
    config_path.parent.mkdir()
    config_path.write_text("schema_version: '1.0'\n", encoding="utf-8")
    worker_config_path.write_text("schema_version: '1.0'\n", encoding="utf-8")
    error_inventory = {
        "production_workers": [],
        "foreign_workers": [],
        "pytest_temp_workers": [],
        "ignored_matching_processes": [],
        "inventory_error": "UnicodeDecodeError: invalid",
    }
    controller = WorkerController(
        catalog_dir=project / ".source_catalog",
        project_root=project,
        config_path=config_path,
        worker_config_path=worker_config_path,
        process_inventory_provider=lambda: error_inventory,
    )
    status = controller.status()
    assert status["process_inventory"]["inventory_error"] is not None
    assert "UnicodeDecodeError" in status["process_inventory"]["inventory_error"]


def test_default_inventory_call_uses_real_runner_and_does_not_raise(
    tmp_path, monkeypatch
):
    """Default inventory path must never raise, even when no workers run."""
    from company_wiki.source_catalog import control

    captured = {}

    def fake_runner(project_root):
        captured["project_root"] = project_root
        return _completed(stdout="[]")

    monkeypatch.setattr(control, "_run_powershell_inventory_subprocess", fake_runner)
    result = control._scan_source_catalog_processes(Path(_PROD_PROJECT))
    assert result["inventory_error"] is None
    assert captured["project_root"].resolve().as_posix().lower() == (
        Path(_PROD_PROJECT).resolve(strict=False).as_posix().lower()
    )


def test_default_controller_inventory_uses_default_runner(tmp_path, monkeypatch):
    """The default WorkerController inventory must call _scan_source_catalog_processes."""
    from company_wiki.source_catalog import control

    monkeypatch.setattr(
        control,
        "_run_powershell_inventory_subprocess",
        lambda _pr: _completed(stdout="[]"),
    )
    from company_wiki.source_catalog.control import WorkerController

    project = tmp_path / "project"
    project.mkdir()
    config_path = project / "config" / "source_catalog.yaml"
    worker_config_path = project / "config" / "source_catalog_worker.yaml"
    config_path.parent.mkdir()
    config_path.write_text("schema_version: '1.0'\n", encoding="utf-8")
    worker_config_path.write_text("schema_version: '1.0'\n", encoding="utf-8")
    controller = WorkerController(
        catalog_dir=project / ".source_catalog",
        project_root=project,
        config_path=config_path,
        worker_config_path=worker_config_path,
    )
    status = controller.status()
    inv = status["process_inventory"]
    assert "production_workers" in inv
    assert "ignored_matching_processes" in inv
    assert "inventory_error" in inv


def test_production_match_falls_back_to_project_root_substring(tmp_path):
    """Config flag absent: should fall back to project_root position, but only
    when --worker-config or --config path lives under project_root."""
    from company_wiki.source_catalog import control

    cmd = (
        f"python -m company_wiki.source_catalog.cli worker "
        f"--worker-config {_PROD_WORKER_CONFIG}"
    )
    rows = [{"ProcessId": 505, "CommandLine": cmd}]
    def fake_runner(_pr):
        return _completed(stdout=_make_stdout(rows))
    result = control._scan_source_catalog_processes(
        Path(_PROD_PROJECT),
        config_path=Path(_PROD_CONFIG),
        worker_config_path=Path(_PROD_WORKER_CONFIG),
        runner=fake_runner,
    )
    assert [w["pid"] for w in result["production_workers"]] == [505]


def test_relative_config_path_resolved_against_project_root(tmp_path):
    """Relative --config value must resolve against project_root."""
    from company_wiki.source_catalog import control

    cmd = (
        "python -m company_wiki.source_catalog.cli worker "
        "--config config/source_catalog.yaml "
        "--worker-config config/source_catalog_worker.yaml"
    )
    rows = [{"ProcessId": 606, "CommandLine": cmd}]
    def fake_runner(_pr):
        return _completed(stdout=_make_stdout(rows))
    project_root = Path(_PROD_PROJECT)
    result = control._scan_source_catalog_processes(
        project_root,
        config_path=Path(_PROD_CONFIG),
        worker_config_path=Path(_PROD_WORKER_CONFIG),
        runner=fake_runner,
    )
    assert [w["pid"] for w in result["production_workers"]] == [606]
