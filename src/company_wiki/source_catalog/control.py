"""Persistent, single-instance controls for the Windows source-catalog worker."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Callable
from uuid import uuid4

from .code_identity import source_bundle_fingerprint


CONTROL_SCHEMA_VERSION = "1.0"
RUNTIME_SCHEMA_VERSION = "1.0"
HEARTBEAT_INTERVAL_SECONDS = 10.0


_INVENTORY_NULL_RESULT: dict[str, Any] = {
    "production_workers": [],
    "foreign_workers": [],
    "pytest_temp_workers": [],
    "production_supervisors": [],
    "foreign_supervisors": [],
    "pytest_temp_supervisors": [],
    "ignored_matching_processes": [],
    "inventory_error": None,
}


# Subcommands that include the word "worker" but are NOT the long-running
# background worker subprocess. Used to ensure we never count `worker-status`,
# `worker-start`, etc. as the actual running worker.
_NON_WORKER_SUBCOMMANDS = (
    "worker-status",
    "worker-start",
    "worker-stop",
    "worker-pause",
    "worker-resume",
)

# Standalone `worker` token (surrounded by whitespace or string end). Verified
# after excluding the subcommands above so `worker-status` is not matched.
_WORKER_TOKEN_RE = re.compile(r"(?:^|\s)worker(?:\s|$)")
_CLI_MODULE_MARKER = "company_wiki.source_catalog.cli"
_CONTROL_PS1_MARKER = "source_catalog_control.ps1"
_SUPERVISOR_PS1_MARKERS = (
    "source_catalog_worker.ps1",
    "source_catalog_worker_at_logon.ps1",
)
_AUDIT_MARKER = "get-ciminstance win32_process"
_CONFIG_FLAG_RE = re.compile(
    r"--config(?:=|\s+)(?:[\"']?)(?P<value>[^\s\"']+)",
    re.IGNORECASE,
)
_WORKER_CONFIG_FLAG_RE = re.compile(
    r"--worker-config(?:=|\s+)(?:[\"']?)(?P<value>[^\s\"']+)",
    re.IGNORECASE,
)
_PROJECT_ROOT_FLAG_RE = re.compile(
    r"-projectroot(?:=|\s+)(?P<value>\"[^\"]+\"|'[^']+'|[^\s]+)",
    re.IGNORECASE,
)


def _run_powershell_inventory_subprocess(
    project_root: Path,
) -> subprocess.CompletedProcess[str]:
    """Run the inventory PowerShell command and return the completed process.

    Uses ``encoding='utf-8'`` / ``errors='replace'`` so that non-ASCII (e.g.
    Chinese) command lines do not raise ``UnicodeDecodeError`` in the
    caller's subprocess pipe reader thread.
    """
    ps_command = (
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
        "$rows = Get-CimInstance Win32_Process | Where-Object { "
        "$_.CommandLine -match "
        "'company_wiki\\.source_catalog|source_catalog_worker(?:_at_logon)?\\.ps1' "
        "} | ForEach-Object { "
        "[pscustomobject]@{ ProcessId=$_.ProcessId; ParentProcessId=$_.ParentProcessId; "
        "CreationDate=$_.CreationDate; CommandLine=$_.CommandLine } }; "
        "@($rows) | ConvertTo-Json -Compress -Depth 4"
    )
    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            ps_command,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        cwd=project_root,
    )


def _normalize_path(value: str, project_root: Path) -> str | None:
    if not value:
        return None
    value = value.strip().strip("\"'")
    try:
        path = Path(value)
        # Windows-style ``C:/...`` paths appear in PowerShell CommandLine rows
        # and must be treated as absolute on every host, even though
        # Path.is_absolute() only reports True on Windows.
        if not _looks_absolute(value) and not path.is_absolute():
            path = project_root / path
        resolved = path.resolve(strict=False)
    except (OSError, ValueError):
        return None
    return resolved.as_posix().lower()


def _looks_absolute(value: str) -> bool:
    """True for ``/...`` or ``<drive>:/...`` path forms regardless of host OS."""
    stripped = value.strip()
    return bool(re.match(r"^(?:[A-Za-z]:)?[/\\]", stripped))


def _classify_supervisor_command(cmd: str, project_root: Path) -> str | None:
    cmd_lower = cmd.lower()
    if not any(marker in cmd_lower for marker in _SUPERVISOR_PS1_MARKERS):
        return None
    if _AUDIT_MARKER in cmd_lower:
        return "audit_command"
    match = _PROJECT_ROOT_FLAG_RE.search(cmd)
    if match is None:
        return "supervisor_no_project_root"
    resolved = _normalize_path(match.group("value"), project_root)
    if resolved is None:
        return "supervisor_no_project_root"

    temp_dirs = [os.environ.get("TEMP", ""), os.environ.get("TMP", "")]
    for temp_dir in temp_dirs:
        normalized_temp = temp_dir.replace("\\", "/").rstrip("/").lower()
        if normalized_temp and (
            resolved == normalized_temp or resolved.startswith(normalized_temp + "/")
        ):
            return "supervisor_pytest_temp"
    if "\\pytest-of-" in resolved or "/pytest-of-" in resolved:
        return "supervisor_pytest_temp"

    production_root = project_root.resolve(strict=False).as_posix().lower()
    if resolved == production_root:
        return "supervisor_production"
    return "supervisor_foreign"


def _classify_worker_command(
    cmd: str,
    project_root: Path,
    config_path: Path | None,
    worker_config_path: Path | None,
) -> str:
    """Return ``production`` / ``pytest_temp`` / ``foreign`` or an ignored reason.

    Ignored reasons (returned as a snake_case string) explain why a matching
    process should NOT be treated as a real production/test/foreign worker:
    ``empty_command``, ``audit_command``, ``control_ps1``, ``not_cli_module``,
    ``subcommand_worker_status``/``subcommand_worker_start``/...,
    ``not_worker_subcommand``, ``no_config_path``.
    """
    if not cmd:
        return "empty_command"
    cmd_lower = cmd.lower()

    # The audit command that this inventory itself issued to enumerate workers.
    # It contains `company_wiki.source_catalog` because of the regex match, but
    # it is the inventory call, not a real worker.
    if _AUDIT_MARKER in cmd_lower and "company_wiki" in cmd_lower:
        return "audit_command"

    # The PowerShell control panel itself (it imports nothing from the package
    # but the script name still matches the regex via the parent directory).
    if _CONTROL_PS1_MARKER in cmd_lower:
        return "control_ps1"

    # Must be an invocation of the source-catalog CLI module.
    if _CLI_MODULE_MARKER not in cmd_lower:
        return "not_cli_module"

    # Exclude all the non-worker subcommands first.
    for sub in _NON_WORKER_SUBCOMMANDS:
        sub_token_re = re.compile(r"(?:^|\s)" + re.escape(sub) + r"(?:\s|$)")
        if sub_token_re.search(cmd_lower):
            return "subcommand_" + sub.replace("-", "_")

    # Require the bare `worker` token (worker-status etc. are excluded above).
    if not _WORKER_TOKEN_RE.search(cmd_lower):
        return "not_worker_subcommand"

    # Extract --config / --worker-config paths.
    flags: list[str] = []
    for pattern in (_CONFIG_FLAG_RE, _WORKER_CONFIG_FLAG_RE):
        match = pattern.search(cmd)
        if match:
            flags.append(match.group("value"))
    if not flags:
        return "no_config_path"

    resolved = [_normalize_path(p, project_root) for p in flags]
    resolved = [p for p in resolved if p]
    if not resolved:
        return "no_config_path"

    temp_dirs = [
        os.environ.get("TEMP", ""),
        os.environ.get("TMP", ""),
    ]
    temp_dirs_posix = [d.replace("\\", "/").rstrip("/").lower() for d in temp_dirs if d]

    is_pytest_temp = False
    for rp in resolved:
        if "\\pytest-of-" in rp or "/pytest-of-" in rp:
            is_pytest_temp = True
            break
        for td in temp_dirs_posix:
            if rp.startswith(td + "/") or rp == td:
                is_pytest_temp = True
                break
        if is_pytest_temp:
            break

    if is_pytest_temp:
        return "pytest_temp"

    proj_root_posix = project_root.resolve(strict=False).as_posix().lower()
    proj_config_posix = (
        config_path.resolve(strict=False).as_posix().lower()
        if config_path is not None
        else f"{proj_root_posix}/config/source_catalog.yaml"
    )
    proj_worker_config_posix = (
        worker_config_path.resolve(strict=False).as_posix().lower()
        if worker_config_path is not None
        else f"{proj_root_posix}/config/source_catalog_worker.yaml"
    )

    for rp in resolved:
        if rp == proj_config_posix or rp == proj_worker_config_posix:
            return "production"
        if rp.startswith(proj_root_posix + "/") or rp == proj_root_posix:
            return "production"

    return "foreign"


def _scan_source_catalog_processes(
    project_root: Path,
    *,
    config_path: Path | None = None,
    worker_config_path: Path | None = None,
    runner: Callable[[Path], subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    """Return inventory of all company_wiki.source_catalog worker processes.

    The result shape is::

        {
          "production_workers": [{pid, creation_date?}, ...],
          "foreign_workers": [{pid, creation_date?}, ...],
          "pytest_temp_workers": [{pid, creation_date?}, ...],
          "production_supervisors": [{pid, creation_date?}, ...],
          "foreign_supervisors": [{pid, creation_date?}, ...],
          "pytest_temp_supervisors": [{pid, creation_date?}, ...],
          "ignored_matching_processes": [{pid, reason}, ...],
          "inventory_error": str | None,
        }

    Rules (§10.8.2):
      - Uses ``encoding='utf-8'`` / ``errors='replace'`` so Chinese paths do
        not crash the subprocess reader thread.
      - Catches ``UnicodeDecodeError`` / ``json.JSONDecodeError`` / ``OSError``
        / ``subprocess.TimeoutExpired`` and reports them via
        ``inventory_error`` instead of raising to the caller.
      - Classifies a row as ``production`` / ``pytest_temp`` / ``foreign`` only
        when the row is a real ``worker`` subcommand invoking the
        ``company_wiki.source_catalog.cli`` module; ``worker-status`` /
        ``worker-start`` / ``worker-stop`` / ``worker-pause`` /
        ``worker-resume`` and the ``source_catalog_control.ps1`` /
        ``Get-CimInstance`` audit commands are reported via
        ``ignored_matching_processes``.
    """
    result: dict[str, Any] = {
        "production_workers": [],
        "foreign_workers": [],
        "pytest_temp_workers": [],
        "production_supervisors": [],
        "foreign_supervisors": [],
        "pytest_temp_supervisors": [],
        "ignored_matching_processes": [],
        "inventory_error": None,
    }
    inventory_runner = runner or _run_powershell_inventory_subprocess
    try:
        completed = inventory_runner(project_root)
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError) as exc:
        result["inventory_error"] = f"{type(exc).__name__}: {exc}"
        return result
    if completed.returncode != 0:
        result["inventory_error"] = (
            f"powershell_exit={completed.returncode}; stderr={(completed.stderr or '').strip()[:200]}"
        )

    stdout = (completed.stdout or "") or ""
    # Strip UTF-8 BOM if present.
    if stdout.startswith("\ufeff"):
        stdout = stdout.lstrip("\ufeff")
    stdout = stdout.strip()
    if not stdout:
        return result
    try:
        rows = json.loads(stdout)
    except json.JSONDecodeError as exc:
        result["inventory_error"] = f"json_decode_error: {exc.msg}"
        return result
    # ConvertTo-Json returns a bare dict when there is exactly one row.
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        result["inventory_error"] = "json_shape_error: expected array or object"
        return result

    for row in rows:
        if not isinstance(row, dict):
            continue
        pid = row.get("ProcessId")
        cmd = row.get("CommandLine") or ""
        if not pid or not cmd:
            continue
        supervisor_category = _classify_supervisor_command(cmd, project_root)
        if supervisor_category is not None:
            supervisor_info: dict[str, Any] = {"pid": pid}
            if row.get("CreationDate"):
                supervisor_info["creation_date"] = row["CreationDate"]
            supervisor_key = {
                "supervisor_production": "production_supervisors",
                "supervisor_pytest_temp": "pytest_temp_supervisors",
                "supervisor_foreign": "foreign_supervisors",
            }.get(supervisor_category)
            if supervisor_key is not None:
                result[supervisor_key].append(supervisor_info)
            else:
                result["ignored_matching_processes"].append(
                    {"pid": pid, "reason": supervisor_category}
                )
            continue
        category = _classify_worker_command(
            cmd, project_root, config_path, worker_config_path
        )
        worker_info: dict[str, Any] = {"pid": pid}
        if row.get("CreationDate"):
            worker_info["creation_date"] = row["CreationDate"]
        if category == "production":
            result["production_workers"].append(worker_info)
        elif category == "pytest_temp":
            result["pytest_temp_workers"].append(worker_info)
        elif category == "foreign":
            result["foreign_workers"].append(worker_info)
        else:
            result["ignored_matching_processes"].append(
                {"pid": pid, "reason": category}
            )
    return result


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        for attempt in range(6):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.02 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any] | None:
    for attempt in range(4):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            if attempt == 3:
                return None
            time.sleep(0.01 * (2**attempt))
    return None


def _normal_executable(value: object) -> str:
    return os.path.normcase(os.path.abspath(str(value))).replace("\\", "/")


def _same_identity(left: dict[str, Any] | None, right: dict[str, Any] | None) -> bool:
    if not left or not right:
        return False
    return (
        int(left.get("pid", -1)) == int(right.get("pid", -2))
        and str(left.get("creation_time")) == str(right.get("creation_time"))
        and _normal_executable(left.get("executable", ""))
        == _normal_executable(right.get("executable", ""))
    )


def _windows_process_identity(pid: int) -> dict[str, Any] | None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    process_query_limited_information = 0x1000
    handle = kernel32.OpenProcess(process_query_limited_information, False, int(pid))
    if not handle:
        return None
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(size)
        ):
            return None
        creation = wintypes.FILETIME()
        exit_time = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            return None
        creation_ticks = (int(creation.dwHighDateTime) << 32) | int(
            creation.dwLowDateTime
        )
        return {
            "pid": int(pid),
            "executable": buffer.value,
            "creation_time": creation_ticks,
        }
    finally:
        kernel32.CloseHandle(handle)


def _portable_process_identity(pid: int) -> dict[str, Any] | None:
    try:
        os.kill(int(pid), 0)
    except (OSError, ProcessLookupError, ValueError):
        return None
    executable = sys.executable
    creation_time: str | int = "unknown"
    proc = Path("/proc") / str(pid)
    try:
        executable = str((proc / "exe").resolve(strict=True))
        creation_time = (proc / "stat").read_text(encoding="utf-8").split()[21]
    except (OSError, IndexError):
        if int(pid) != os.getpid():
            return None
    return {"pid": int(pid), "executable": executable, "creation_time": creation_time}


def process_identity(pid: int) -> dict[str, Any] | None:
    """Return identity fields strong enough to detect Windows PID reuse."""

    if os.name == "nt":
        return _windows_process_identity(pid)
    return _portable_process_identity(pid)


def terminate_matching_process(expected: dict[str, Any]) -> bool:
    """Terminate only when PID, executable and creation time still match."""

    pid = int(expected["pid"])
    if not _same_identity(process_identity(pid), expected):
        return False
    if os.name != "nt":
        return False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    process_terminate = 0x0001
    process_query_limited_information = 0x1000
    handle = kernel32.OpenProcess(
        process_terminate | process_query_limited_information, False, pid
    )
    if not handle:
        return False
    try:
        if not _same_identity(process_identity(pid), expected):
            return False
        return bool(kernel32.TerminateProcess(handle, 2))
    finally:
        kernel32.CloseHandle(handle)


class WorkerSession:
    """The owned runtime lease used by one worker process."""

    def __init__(
        self, controller: "WorkerController", token: str, identity: dict[str, Any]
    ):
        self.controller = controller
        self.token = token
        self.identity = identity
        self.closed = False

    def heartbeat(self, status: str, **details: Any) -> None:
        if self.closed:
            return
        current = _read_json(self.controller.runtime_path)
        if not current or current.get("token") != self.token:
            return
        heartbeat_at = self.controller.clock()
        new_path = details.get("current_path")
        prev_path = current.get("current_path")
        if new_path and new_path != prev_path:
            details["current_path_started_at"] = heartbeat_at
        elif new_path and new_path == prev_path:
            started = current.get("current_path_started_at")
            if started is not None:
                details["current_path_started_at"] = started
                details["current_path_elapsed_seconds"] = round(
                    heartbeat_at - float(started), 1
                )
        update = {
            "heartbeat_at": heartbeat_at,
            "updated_at": heartbeat_at,
            "worker_status": status,
            "current_path": None,
            "current_path_started_at": None,
            "current_path_elapsed_seconds": None,
            "progress_current": 0,
            "progress_total": 0,
            "progress_percent": None,
            "progress_detail": None,
            "parser_pid": None,
            "parser_elapsed_seconds": None,
            "parser_timeout_seconds": None,
            "parser_ownership": None,
        }
        if status != "waiting":
            update.update(
                {
                    "cycle_productive": None,
                    "next_wait_seconds": None,
                    "next_wake_reason": None,
                    "next_wake_at": None,
                }
            )
        update.update(details)
        current.update(update)
        _atomic_write_json(self.controller.runtime_path, current)

    def should_stop(self) -> bool:
        control = self.controller._read_control()
        return (
            control["desired_state"] == "paused"
            or control.get("stop_requested_for") == self.token
        )

    def wait(self, seconds: float) -> bool:
        """Wait in small slices; return False as soon as stop is requested."""

        remaining = max(0.0, float(seconds))
        until_heartbeat = HEARTBEAT_INTERVAL_SECONDS
        while remaining > 0:
            if self.should_stop():
                return False
            step = min(0.5, remaining)
            self.controller.sleeper(step)
            remaining -= step
            until_heartbeat -= step
            if until_heartbeat <= 0:
                self.heartbeat("waiting", progress_detail="waiting for next cycle")
                until_heartbeat = HEARTBEAT_INTERVAL_SECONDS
        return not self.should_stop()

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        runtime = _read_json(self.controller.runtime_path)
        if runtime and runtime.get("token") == self.token:
            self.controller.runtime_path.unlink(missing_ok=True)
        lock = _read_json(self.controller.lock_path)
        if lock and lock.get("token") == self.token:
            self.controller.lock_path.unlink(missing_ok=True)

    def __enter__(self) -> "WorkerSession":
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        self.close()


class WorkerController:
    """Persist user intent and manage one safe background worker instance."""

    def __init__(
        self,
        *,
        catalog_dir: Path,
        project_root: Path,
        config_path: Path,
        worker_config_path: Path,
        python_executable: Path = Path(sys.executable),
        process_identity: Callable[[int], dict[str, Any] | None] = process_identity,
        terminate_process: Callable[
            [dict[str, Any]], bool
        ] = terminate_matching_process,
        popen: Callable[..., Any] = subprocess.Popen,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        process_inventory_provider: Callable[[], dict[str, Any]] | None = None,
        launcher_path: Path | None = None,
    ):
        self.catalog_dir = catalog_dir.resolve(strict=False)
        self.project_root = project_root.resolve(strict=False)
        self.config_path = config_path.resolve(strict=False)
        self.worker_config_path = worker_config_path.resolve(strict=False)
        self.python_executable = python_executable.resolve(strict=False)
        self.control_path = self.catalog_dir / "worker_control.json"
        self.runtime_path = self.catalog_dir / "worker_runtime.json"
        self.lock_path = self.catalog_dir / "worker_instance.lock"
        self.console_log_path = self.catalog_dir / "worker_console.log"
        project_launcher = self.project_root / "scripts" / "source_catalog_worker.ps1"
        package_launcher = (
            Path(__file__).resolve().parents[3]
            / "scripts"
            / "source_catalog_worker.ps1"
        )
        self.launcher_path = (
            launcher_path
            if launcher_path is not None
            else project_launcher
            if project_launcher.is_file()
            else package_launcher
        ).resolve(strict=False)
        self.process_identity = process_identity
        self.terminate_process = terminate_process
        self.popen = popen
        self.sleeper = sleeper
        self.clock = clock
        if process_inventory_provider is not None:
            self._inventory = process_inventory_provider
        else:
            self._inventory_cache: tuple[float, dict[str, Any]] | None = None

            def _default_inventory() -> dict[str, Any]:
                now = self.clock()
                if self._inventory_cache is not None:
                    cached_at, cached = self._inventory_cache
                    if now - cached_at < 30.0:
                        return cached
                result = _scan_source_catalog_processes(
                    self.project_root,
                    config_path=self.config_path,
                    worker_config_path=self.worker_config_path,
                )
                self._inventory_cache = (now, result)
                return result

            self._inventory = _default_inventory

    def _read_control(self) -> dict[str, Any]:
        loaded = _read_json(self.control_path)
        if not loaded or loaded.get("schema_version") != CONTROL_SCHEMA_VERSION:
            return {
                "schema_version": CONTROL_SCHEMA_VERSION,
                "desired_state": "enabled",
                "updated_at": None,
                "stop_requested_for": None,
            }
        desired = loaded.get("desired_state")
        if desired not in {"enabled", "paused"}:
            loaded["desired_state"] = "enabled"
        return loaded

    def _write_control(self, **changes: Any) -> dict[str, Any]:
        value = self._read_control()
        value.update(changes)
        value["schema_version"] = CONTROL_SCHEMA_VERSION
        value["updated_at"] = self.clock()
        _atomic_write_json(self.control_path, value)
        return value

    @staticmethod
    def _runtime_identity(runtime: dict[str, Any] | None) -> dict[str, Any] | None:
        if not runtime:
            return None
        try:
            return {
                "pid": int(runtime["pid"]),
                "executable": str(runtime["executable"]),
                "creation_time": runtime["creation_time"],
            }
        except (KeyError, TypeError, ValueError):
            return None

    def _runtime_is_live(self, runtime: dict[str, Any] | None) -> bool:
        expected = self._runtime_identity(runtime)
        if not expected:
            return False
        current = None
        for attempt in range(3):
            current = self.process_identity(int(expected["pid"]))
            if current is not None:
                break
            # QueryFullProcessImageName/GetProcessTimes can transiently fail while a
            # newly spawned Windows process is publishing or closing its lease.
            if attempt < 2:
                self.sleeper(0.02)
        return _same_identity(current, expected)

    def _clear_stale_runtime(self) -> None:
        # CW-3.5 / Phase 10 — watchdog: only heal when deliberately enabled.
        # Paused / manual stop must never auto-restart.
        control = self._read_control()
        if control.get("desired_state") != "enabled":
            return
        runtime = _read_json(self.runtime_path)
        if not self._runtime_is_live(runtime):
            self.runtime_path.unlink(missing_ok=True)
        lock = _read_json(self.lock_path)
        if not self._runtime_is_live(lock):
            self.lock_path.unlink(missing_ok=True)

    def read_desired_state(self) -> str:
        """Return ``desired_state`` without touching runtime or process inventory.

        Used by ``cli.py worker`` and by ``worker.run_forever(control=...)``
        to check persistent pause without triggering PowerShell subprocess
        inventory (which can hang/decode-fail on Chinese Windows before the
        worker has even opened its session). Always returns ``enabled`` or
        ``paused``.
        """
        return self._read_control().get("desired_state") or "enabled"

    def status(self) -> dict[str, Any]:
        control = self._read_control()
        runtime = _read_json(self.runtime_path)
        live = self._runtime_is_live(runtime)
        current_code = source_bundle_fingerprint(self.project_root)
        loaded_fingerprint = runtime.get("loaded_code_fingerprint") if runtime else None
        loaded_error = runtime.get("loaded_code_fingerprint_error") if runtime else None
        current_fingerprint = current_code["fingerprint"]
        fingerprint_errors = [
            str(value) for value in (loaded_error, current_code["error"]) if value
        ]
        result: dict[str, Any] = {
            "schema_version": "1.0",
            "status_generated_at": self.clock(),
            "desired_state": control["desired_state"],
            "runtime_state": "running" if live else "stopped",
            "control_path": str(self.control_path),
            "runtime_path": str(self.runtime_path),
            "process_inventory": self._inventory(),
            "loaded_code_fingerprint": loaded_fingerprint,
            "current_code_fingerprint": current_fingerprint,
            "code_match": (
                loaded_fingerprint == current_fingerprint
                if loaded_fingerprint and current_fingerprint
                else None
            ),
            "code_fingerprint_error": (
                "; ".join(fingerprint_errors) if fingerprint_errors else None
            ),
        }
        if runtime:
            stale = not live
            now = self.clock()
            heartbeat_age = None
            if runtime.get("heartbeat_at"):
                heartbeat_age = round(now - float(runtime["heartbeat_at"]), 1)
            result.update(
                {
                    "pid": runtime.get("pid"),
                    "started_at": runtime.get("started_at"),
                    "heartbeat_at": runtime.get("heartbeat_at"),
                    "heartbeat_age_seconds": heartbeat_age,
                    "updated_at": runtime.get(
                        "updated_at", runtime.get("heartbeat_at")
                    ),
                    "stale_runtime": stale,
                }
            )
            if live:
                elapsed = runtime.get("current_path_elapsed_seconds")
                current_path_started_at = runtime.get("current_path_started_at")
                if runtime.get("current_path") and current_path_started_at is not None:
                    elapsed = round(
                        max(0.0, now - float(current_path_started_at)),
                        1,
                    )
                result.update(
                    {
                        "worker_status": runtime.get("worker_status"),
                        "current_path": runtime.get("current_path"),
                        "current_path_started_at": runtime.get(
                            "current_path_started_at"
                        ),
                        "current_path_elapsed_seconds": elapsed,
                        "long_running_document_warning": (
                            isinstance(elapsed, (int, float)) and elapsed > 180
                        ),
                        "progress_current": runtime.get("progress_current", 0),
                        "progress_total": runtime.get("progress_total", 0),
                        "progress_percent": runtime.get("progress_percent"),
                        "progress_detail": runtime.get("progress_detail"),
                        "parser_pid": runtime.get("parser_pid"),
                        "parser_elapsed_seconds": runtime.get("parser_elapsed_seconds"),
                        "parser_timeout_seconds": runtime.get("parser_timeout_seconds"),
                        "parser_ownership": runtime.get("parser_ownership"),
                        "cycle_productive": runtime.get("cycle_productive"),
                        "next_wait_seconds": runtime.get("next_wait_seconds"),
                        "next_wake_reason": runtime.get("next_wake_reason"),
                        "next_wake_at": runtime.get("next_wake_at"),
                    }
                )
            else:
                result.update(
                    {
                        "worker_status": "stopped",
                        "current_path": None,
                        "progress_current": 0,
                        "progress_total": 0,
                        "progress_percent": None,
                        "progress_detail": None,
                        "parser_pid": None,
                        "parser_elapsed_seconds": None,
                        "parser_timeout_seconds": None,
                        "parser_ownership": None,
                        "cycle_productive": None,
                        "next_wait_seconds": None,
                        "next_wake_reason": None,
                        "next_wake_at": None,
                        "last_worker_status": runtime.get("worker_status"),
                        "last_current_path": runtime.get("current_path"),
                        "last_progress_detail": runtime.get("progress_detail"),
                    }
                )
        return result

    def open_session(self) -> WorkerSession:
        if self._read_control()["desired_state"] == "paused":
            raise RuntimeError("source-catalog worker is paused")
        self._clear_stale_runtime()
        existing = _read_json(self.lock_path)
        if self._runtime_is_live(existing):
            raise RuntimeError("source-catalog worker is already running")
        token = uuid4().hex
        identity = self.process_identity(os.getpid())
        if not identity:
            raise RuntimeError("could not identify the worker process")
        started_at = self.clock()
        payload = {
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "token": token,
            **identity,
            "project_root": str(self.project_root),
            "started_at": started_at,
            "heartbeat_at": started_at,
            "updated_at": started_at,
            "worker_status": "starting",
            "current_path": None,
            "progress_current": 0,
            "progress_total": 0,
            "progress_percent": None,
            "progress_detail": None,
            "cycle_productive": None,
            "next_wait_seconds": None,
            "next_wake_reason": None,
            "next_wake_at": None,
        }
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            descriptor = os.open(self.lock_path, flags)
        except FileExistsError as exc:
            raise RuntimeError("source-catalog worker is already running") from exc
        try:
            os.write(
                descriptor,
                (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode(
                    "utf-8"
                ),
            )
        finally:
            os.close(descriptor)
        try:
            _atomic_write_json(self.runtime_path, payload)
        except Exception:
            self.lock_path.unlink(missing_ok=True)
            raise
        return WorkerSession(self, token, identity)

    def stop(
        self, *, graceful_timeout_seconds: float = 5.0, force: bool = True
    ) -> dict[str, Any]:
        runtime = _read_json(self.runtime_path)
        if not self._runtime_is_live(runtime):
            self._clear_stale_runtime()
            return {**self.status(), "forced": False, "stop_requested": False}
        expected = self._runtime_identity(runtime)
        assert expected is not None
        self._write_control(stop_requested_for=runtime.get("token"))
        deadline = time.monotonic() + max(0.0, graceful_timeout_seconds)
        consecutive_not_live = 0
        while time.monotonic() < deadline:
            if self._runtime_is_live(runtime):
                consecutive_not_live = 0
            else:
                consecutive_not_live += 1
                if consecutive_not_live >= 2:
                    break
            self.sleeper(min(0.2, max(0.0, deadline - time.monotonic())))
        forced = False
        if self._runtime_is_live(runtime) and force:
            for attempt in range(3):
                if not self._runtime_is_live(runtime):
                    break
                forced = bool(self.terminate_process(expected))
                if forced:
                    break
                if attempt < 2:
                    self.sleeper(0.05)
            if forced:
                exit_wait_attempts = max(
                    20, int(max(0.0, graceful_timeout_seconds) / 0.1)
                )
                for _ in range(exit_wait_attempts):
                    if not self._runtime_is_live(runtime):
                        break
                    self.sleeper(0.1)
        if not self._runtime_is_live(runtime):
            self.runtime_path.unlink(missing_ok=True)
            self.lock_path.unlink(missing_ok=True)
        return {**self.status(), "forced": forced, "stop_requested": True}

    def pause(
        self, *, graceful_timeout_seconds: float = 5.0, force: bool = True
    ) -> dict[str, Any]:
        self._write_control(desired_state="paused")
        return self.stop(
            graceful_timeout_seconds=graceful_timeout_seconds,
            force=force,
        )

    def _read_console_tail(self, max_lines: int = 40) -> str:
        """Return the last ``max_lines`` lines of the worker console log.

        Returns an empty string if the log does not exist or cannot be read.
        """
        if max_lines <= 0:
            return ""
        try:
            if not self.console_log_path.is_file():
                return ""
        except OSError:
            return ""
        try:
            content = self.console_log_path.read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError:
            return ""
        lines = content.splitlines()
        if not lines:
            return ""
        tail = lines[-max_lines:]
        return "\n".join(tail)

    def _read_recent_process_event(
        self,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Return ``(last_event, error)`` from ``worker_process_events.jsonl``.

        JSONL parse failure returns ``(None, "<error_msg>")`` — never raises.
        """
        events_path = self.catalog_dir / "worker_process_events.jsonl"
        try:
            if not events_path.is_file():
                return (None, None)
            raw = events_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return (None, f"OSError: {exc}")
        if raw.startswith("\ufeff"):
            raw = raw.lstrip("\ufeff")
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        if not lines:
            return (None, None)
        last = lines[-1].strip()
        try:
            event = json.loads(last)
        except json.JSONDecodeError as exc:
            return (None, f"JSONDecodeError: {exc.msg}")
        return (event, None)

    def _classify_start_failure_reason(
        self, *, spawned_pid, exit_code, runtime_state
    ) -> str:
        if exit_code is None:
            return (
                "worker_spawned_without_runtime_and_no_exit_code; "
                "the child process may have been killed before it could write "
                "worker_runtime.json. Check antivirus, login-session teardown, "
                "or external kill signals."
            )
        if exit_code == 0:
            return (
                "worker_exited_clean_before_writing_runtime; the worker may "
                "have observed desired_state=paused or a startup-delay "
                "control request. Open worker_process_events.jsonl for the "
                "process_exiting reason."
            )
        prefix = (
            "worker_exited_with_nonzero_code_before_writing_runtime; "
            f"exit_code={exit_code}; "
        )
        if spawned_pid is not None:
            prefix += f"pid={spawned_pid}; "
        prefix += (
            "see console_tail and worker_process_events.jsonl for the "
            "underlying module import / encoding / config error."
        )
        return prefix

    def start(
        self, *, wait_seconds: float = 5.0, startup_delay_seconds: int = 0
    ) -> dict[str, Any]:
        if self._read_control()["desired_state"] == "paused":
            return {"started": False, "reason": "paused; use resume"}
        current_runtime = _read_json(self.runtime_path)
        if self._runtime_is_live(current_runtime):
            return {"started": False, "reason": "already_running"}
        self._clear_stale_runtime()
        if os.name == "nt":
            command = [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.launcher_path),
                "-PythonExe",
                str(self.python_executable),
                "-ProjectRoot",
                str(self.project_root),
                "-ConfigPath",
                str(self.config_path),
                "-WorkerConfigPath",
                str(self.worker_config_path),
                "-CatalogDir",
                str(self.catalog_dir),
                "-StartupDelaySeconds",
                str(startup_delay_seconds),
            ]
        else:
            command = [
                str(self.python_executable),
                "-m",
                "company_wiki.source_catalog.cli",
                "--config",
                str(self.config_path),
                "worker",
                "--worker-config",
                str(self.worker_config_path),
            ]
            if startup_delay_seconds > 0:
                command.extend(["--startup-delay-seconds", str(startup_delay_seconds)])
        self.console_log_path.parent.mkdir(parents=True, exist_ok=True)
        environment = os.environ.copy()
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        creationflags = 0
        if os.name == "nt":
            # DETACHED_PROCESS makes Windows PowerShell exit 0 without
            # executing its -File script. CREATE_NO_WINDOW keeps the
            # supervisor hidden while the new process group isolates control
            # signals from the CLI process that launched it.
            creationflags = 0x08000000 | 0x00000200
        # Give the child its own binary append handle. A PIPE keeps the CLI
        # caller's capture pipe open for the worker lifetime on Windows, so
        # `worker-start` never returns even though the worker is healthy.
        with self.console_log_path.open("ab", buffering=0) as log:
            process = self.popen(
                command,
                cwd=self.project_root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                close_fds=True,
                creationflags=creationflags,
            )
        deadline = time.monotonic() + max(0.0, wait_seconds)
        spawned_pid = getattr(process, "pid", None)
        runtime_state = "stopped"
        while time.monotonic() < deadline:
            runtime = _read_json(self.runtime_path)
            if self._runtime_is_live(runtime):
                runtime_state = "running"
                break
            if getattr(process, "poll", lambda: None)() is not None:
                runtime_state = "stopped"
                break
            self.sleeper(0.1)

        if runtime_state == "running":
            runtime = _read_json(self.runtime_path) or {}
            return {
                "started": True,
                "spawned_pid": spawned_pid,
                "supervisor_pid": spawned_pid if os.name == "nt" else None,
                "worker_pid": runtime.get("pid"),
            }

        # Worker exited before publishing a runtime file. Provide explicit
        # boot-failure diagnostics per §10.8.3.
        spawned_exit_code = None
        try:
            spawned_exit_code = process.poll()
        except Exception:
            spawned_exit_code = None
        recent_event, _event_error = self._read_recent_process_event()
        console_tail = self._read_console_tail(max_lines=40)
        failure_reason = self._classify_start_failure_reason(
            spawned_pid=spawned_pid,
            exit_code=spawned_exit_code,
            runtime_state=runtime_state,
        )
        result: dict[str, Any] = {
            "runtime_state": runtime_state,
            "started": False,
            "spawned_pid": spawned_pid,
            "spawned_exit_code": spawned_exit_code,
            "startup_failure_reason": failure_reason,
            "console_tail": console_tail,
            "recent_process_event": recent_event,
        }
        if recent_event is None:
            result["recent_process_event_error"] = _event_error
        else:
            result["recent_process_event_error"] = None
        return result

    def resume(
        self,
        *,
        wait_seconds: float = 5.0,
        startup_delay_seconds: int = 0,
    ) -> dict[str, Any]:
        self._write_control(desired_state="enabled", stop_requested_for=None)
        return self.start(
            wait_seconds=wait_seconds,
            startup_delay_seconds=startup_delay_seconds,
        )


__all__ = [
    "WorkerController",
    "WorkerSession",
    "process_identity",
    "terminate_matching_process",
]
