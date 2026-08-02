from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


PROJECT = Path(__file__).resolve().parents[2]
CONTROL = PROJECT / "scripts" / "source_catalog_control.ps1"
HIDDEN_HOST = PROJECT / "scripts" / "source_catalog_worker_at_logon.vbs"


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows startup contract")


def _powershell() -> str:
    return str(Path(os.environ.get("WINDIR", "C:/Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe")


def _wscript() -> str:
    return str(Path(os.environ.get("WINDIR", "C:/Windows")) / "System32" / "wscript.exe")


def _write_fake_cli(root: Path) -> Path:
    package = root / "company_wiki" / "source_catalog"
    package.mkdir(parents=True)
    (root / "company_wiki" / "__init__.py").write_text("", encoding="utf-8")
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "cli.py").write_text(
        """
import json
import os
import sys
import time
from pathlib import Path

mode = os.environ.get("FAKE_CONTROL_MODE", "success")
command = next(
    (
        value
        for value in (
            "worker-status",
            "worker-start",
            "worker-pause",
            "worker-resume",
            "worker-stop",
            "duplicates",
        )
        if value in sys.argv
    ),
    "",
)
if command == "duplicates":
    argv_path = os.environ.get("FAKE_CONTROL_ARGV_PATH")
    if argv_path:
        Path(argv_path).write_text(json.dumps(sys.argv), encoding="utf-8")
    print(json.dumps({
        "groups": [],
        "total_groups": 0,
        "total_reclaimable_copies": 0,
        "total_reclaimable_bytes": 0,
    }))
    raise SystemExit(0)
if mode == "action_then_status_failure":
    if command == "worker-start":
        print("{}")
        raise SystemExit(0)
    if command == "worker-status":
        print("synthetic post-action status failure", file=sys.stderr)
        raise SystemExit(7)
if mode == "slow":
    time.sleep(float(os.environ.get("FAKE_CONTROL_DELAY", "4")))
elif mode == "timeout":
    time.sleep(30)
elif mode == "malformed":
    print("not-json")
    raise SystemExit(0)
elif mode == "nonzero":
    print("synthetic status failure", file=sys.stderr)
    raise SystemExit(7)
elif mode == "llm_semantics":
    print(json.dumps({
        "startup": {"installed": True, "method": "fixture"},
        "desired_state": "enabled",
        "runtime_state": "running",
        "pid": 123,
        "status_generated_at": time.time(),
        "heartbeat_age_seconds": 0.1,
        "stale_runtime": False,
        "current_path": "C:/incoming/slow.pdf",
        "current_path_elapsed_seconds": 12.5,
        "parser_pid": 4321,
        "parser_elapsed_seconds": 12.5,
        "parser_timeout_seconds": 3600,
        "parser_ownership": "windows_job",
        "loaded_code_fingerprint": "a" * 64,
        "current_code_fingerprint": "b" * 64,
        "code_match": False,
        "code_fingerprint_error": None,
        "scheduler": {
            "last_cycle_at": time.time(),
            "last_error": None,
            "parse_timeout_total": 2,
            "last_parse_timeout_path": "C:/incoming/retry.pdf",
        },
        "process_inventory": {
            "production_workers": [{"pid": 123}],
            "production_supervisors": [{"pid": 122}],
            "pytest_temp_workers": [],
            "pytest_temp_supervisors": [],
            "foreign_workers": [],
            "foreign_supervisors": [],
        },
        "pipeline": {
            "available": True,
            "last_scan": {
                "completed_at": time.time(),
                "status": "completed_with_errors",
                "files_seen": 10,
                "files_reused": 9,
                "files_hashed": 0,
                "files_excluded": 0,
                "errors": 1,
                "new_errors": 0,
                "known_quarantined": 1,
                "new_documents": 0,
                "new_sources": 0,
                "error_details": [{
                    "root_id": "dropbox_stock",
                    "relative_path": "data/Product_Revenue_Forecast_Model.xlsx",
                    "error": "SourceManifestError: source file is empty",
                    "unchanged": True,
                }],
            },
            "index": {},
            "markdown": {
                "eligible": 9,
                "pending": 9,
                "in_progress": 0,
                "blocked": 1,
                "blocked_quarantined": 1,
                "blocked_incomplete": 0,
                "blocked_other": 0,
                "completed": 0,
                "partial": 0,
                "unsupported": 0,
                "failed": 0,
                "retryable_failed": 2,
                "terminal_failed": 1,
            },
            "llm_summary": {
                "pending": 20,
                "in_progress": 0,
                "completed": 5,
                "failed": 131,
                "retryable_failed": 0,
                "permanent": 131,
                "legacy_scope_mismatch": 131,
                "last_permanent_document_id": "urn:permanent:last",
                "next_document_retry_after": None,
                "last_failed_document_id": None,
                "deferred": True,
                "global_deferred": True,
                "global_retry_after": time.time() + 3600,
                "global_error": "LLMProviderError: HTTP 429 quota exhausted",
            },
            "health": {
                "scan": {},
                "locks": {"operation_lock": "absent"},
                "artifacts": {},
            },
            "explanations": {},
            "current": {},
            "recent_batches": {},
        },
    }))
    raise SystemExit(0)

print(json.dumps({
    "startup": {"installed": True, "method": "fixture"},
    "desired_state": "enabled",
    "runtime_state": "running",
    "pid": 123,
    "status_generated_at": time.time(),
    "heartbeat_age_seconds": 0.1,
    "stale_runtime": False,
    "process_inventory": {
        "production_workers": [{"pid": 123}],
        "production_supervisors": [{"pid": 122}],
        "pytest_temp_workers": [],
        "pytest_temp_supervisors": [],
        "foreign_workers": [],
        "foreign_supervisors": [],
    },
    "pipeline": {"available": False, "error": "fixture omits catalog SQL"},
}))
""".lstrip(),
        encoding="utf-8",
    )
    return root


def _control_command(
    project: Path,
    *,
    action: str = "menu",
    timeout: int | None = None,
    interactive: bool = False,
) -> list[str]:
    command = [
        _powershell(),
        "-NoProfile",
    ]
    if not interactive:
        command.append("-NonInteractive")
    command.extend(
        [
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(CONTROL),
            "-Action",
            action,
            "-PythonExe",
            sys.executable,
            "-ProjectRoot",
            str(project),
        ]
    )
    if timeout is not None:
        command.extend(["-StatusTimeoutSeconds", str(timeout)])
    return command


def _control_environment(fake_package: Path, mode: str) -> dict[str, str]:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONPATH"] = str(fake_package)
    environment["FAKE_CONTROL_MODE"] = mode
    return environment


def _terminate_tree(process: subprocess.Popen[str]) -> None:
    subprocess.run(
        ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
        capture_output=True,
        check=False,
        timeout=10,
    )
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def _read_first_nonempty_line(stream) -> str:
    for line in stream:
        if line.strip():
            return line.strip()
    return ""


def _read_until_menu(stream) -> str:
    lines: list[str] = []
    for line in stream:
        lines.append(line)
        if "0. Exit" in line:
            return "".join(lines)
    return "".join(lines)


def test_control_first_paints_before_slow_worker_status(tmp_path):
    project = tmp_path / "project with spaces"
    (project / "config").mkdir(parents=True)
    fake_package = _write_fake_cli(tmp_path / "fake package")
    process = subprocess.Popen(
        _control_command(project, action="status"),
        cwd=PROJECT,
        env=_control_environment(fake_package, "slow"),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert process.stdout is not None
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_read_first_nonempty_line, process.stdout)
    started = time.monotonic()
    try:
        first_line = future.result(timeout=4)
    except FutureTimeout:
        _terminate_tree(process)
        pytest.fail("control panel produced no visible first paint within four seconds")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    assert time.monotonic() - started < 4
    assert first_line == "Company Wiki Source Catalog"
    _terminate_tree(process)


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("timeout", "timed out after 1 seconds"),
        ("malformed", "invalid JSON"),
        ("nonzero", "exit code 7"),
    ],
)
def test_control_status_failure_keeps_menu_available(tmp_path, mode, expected):
    project = tmp_path / "project with spaces"
    (project / "config").mkdir(parents=True)
    fake_package = _write_fake_cli(tmp_path / "fake package")

    process = subprocess.Popen(
        _control_command(project, timeout=1),
        cwd=PROJECT,
        env=_control_environment(fake_package, mode),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_read_until_menu, process.stdout)
    try:
        stdout = future.result(timeout=8)
    except FutureTimeout:
        _terminate_tree(process)
        pytest.fail("control panel did not expose its menu after status failure")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    _terminate_tree(process)

    assert "Reading worker status" in stdout
    assert expected in stdout
    assert "1. Refresh status" in stdout
    assert "0. Exit" in stdout


def test_control_renders_structured_llm_failure_semantics(tmp_path):
    project = tmp_path / "project with spaces"
    (project / "config").mkdir(parents=True)
    fake_package = _write_fake_cli(tmp_path / "fake package")

    result = subprocess.run(
        _control_command(project, action="status"),
        cwd=PROJECT,
        env=_control_environment(fake_package, "llm_semantics"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        check=False,
    )

    assert result.returncode == 0
    assert "retryable 0 | permanent 131" in result.stdout
    assert "Global retry" in result.stdout
    assert "HTTP 429 quota exhausted" in result.stdout
    assert "Legacy scope mismatch: 131" in result.stdout
    assert "Code       : MISMATCH" in result.stdout
    assert "loaded aaaaaaaaaaaa | current bbbbbbbbbbbb" in result.stdout
    assert "total 1 | new 0 | known quarantine 1" in result.stdout
    assert "dropbox_stock/data/Product_Revenue_Forecast_Model.xlsx" in result.stdout
    assert "SourceManifestError: source file is empty" in result.stdout
    assert "Blocked  : quarantined 1 | incomplete 0 | other 0" in result.stdout
    assert "Parser   : PID 4321 | elapsed 12.5s / timeout 3600s | owner windows_job" in result.stdout
    assert "MD retry : retryable 2 | terminal 1" in result.stdout
    assert "Parse timeouts: total 2" in result.stdout
    assert "Last path: C:/incoming/retry.pdf" in result.stdout


@pytest.mark.parametrize("search", ["C:\\\\", 'quoted "value"'])
def test_control_preserves_windows_command_line_arguments(tmp_path, search):
    project = tmp_path / "project with spaces"
    (project / "config").mkdir(parents=True)
    fake_package = _write_fake_cli(tmp_path / "fake package")
    argv_path = tmp_path / "captured-argv.json"
    environment = _control_environment(fake_package, "success")
    environment["FAKE_CONTROL_ARGV_PATH"] = str(argv_path)

    completed = subprocess.run(
        _control_command(project, action="duplicates", interactive=True),
        cwd=PROJECT,
        env=environment,
        input=f"{search}\n\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    arguments = json.loads(argv_path.read_text(encoding="utf-8"))
    text_index = arguments.index("--text")
    assert arguments[text_index + 1] == search


def test_successful_control_action_is_not_failed_by_status_refresh(tmp_path):
    project = tmp_path / "project with spaces"
    (project / "config").mkdir(parents=True)
    fake_package = _write_fake_cli(tmp_path / "fake package")

    completed = subprocess.run(
        _control_command(project, action="start", timeout=1),
        cwd=PROJECT,
        env=_control_environment(fake_package, "action_then_status_failure"),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Unable to read worker status" in completed.stdout
    assert "exit code 7" in completed.stdout


def test_startup_actions_use_wscript_instead_of_a_console_host(tmp_path):
    from company_wiki.source_catalog.startup import (
        build_startup_registry_args,
        build_startup_task_args,
    )

    project = tmp_path / "project with spaces"
    launcher = project / "scripts" / "source_catalog_worker.ps1"
    values = [
        build_startup_task_args(
            project_root=project,
            launcher_path=launcher,
            python_executable=Path("C:/Python/python.exe"),
        ),
        build_startup_registry_args(
            project_root=project,
            launcher_path=launcher,
            python_executable=Path("C:/Python/python.exe"),
        ),
    ]

    actions = [values[0][values[0].index("/TR") + 1], values[1][values[1].index("/D") + 1]]
    for action in actions:
        assert "wscript.exe" in action.lower()
        assert "//B //Nologo" in action
        assert "source_catalog_worker_at_logon.vbs" in action
        assert "powershell.exe" not in action.lower()
        assert "source_catalog_control" not in action.lower()


def _visible_windows_for_pid(pid: int) -> list[int]:
    visible: list[int] = []
    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @enum_proc
    def callback(hwnd, _lparam):
        process_id = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        if process_id.value == pid and ctypes.windll.user32.IsWindowVisible(hwnd):
            visible.append(int(hwnd))
        return True

    ctypes.windll.user32.EnumWindows(callback, 0)
    return visible


def test_wscript_logon_host_launches_powershell_without_a_visible_window(tmp_path):
    project = tmp_path / "project path with spaces"
    scripts = project / "scripts"
    scripts.mkdir(parents=True)
    hidden_host = scripts / HIDDEN_HOST.name
    hidden_host.write_text(HIDDEN_HOST.read_text(encoding="utf-8"), encoding="utf-8")
    marker = project / "child-pid.txt"
    (scripts / "source_catalog_worker_at_logon.ps1").write_text(
        "param([string]$PythonExe, [string]$ProjectRoot)\n"
        "Set-Content -LiteralPath (Join-Path $ProjectRoot 'child-pid.txt') "
        "-Value $PID -Encoding ASCII\n"
        "Start-Sleep -Seconds 2\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [_wscript(), "//B", "//Nologo", str(hidden_host), sys.executable, str(project)],
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert completed.returncode == 0
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not marker.is_file():
        time.sleep(0.05)
    assert marker.is_file()
    child_pid = int(marker.read_text(encoding="ascii").strip())
    assert _visible_windows_for_pid(child_pid) == []
