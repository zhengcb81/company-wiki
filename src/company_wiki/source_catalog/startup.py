"""Windows Task Scheduler integration for the source-catalog worker."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Any, Callable


DEFAULT_TASK_NAME = "CompanyWiki Source Catalog"


def _schtasks_executable() -> str:
    windows_dir = Path(os.environ.get("WINDIR", "C:/Windows"))
    return str(windows_dir / "System32" / "schtasks.exe")


def _reg_executable() -> str:
    windows_dir = Path(os.environ.get("WINDIR", "C:/Windows"))
    return str(windows_dir / "System32" / "reg.exe")


def _registry_value_name(task_name: str) -> str:
    return "".join(character for character in task_name if character.isalnum()) or "CompanyWikiSourceCatalog"


def _run(
    args: list[str],
    *,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    completed = runner(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "returncode": int(completed.returncode),
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "success": completed.returncode == 0,
    }


def uninstall_startup_task(
    *,
    task_name: str = DEFAULT_TASK_NAME,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    if os.name != "nt":
        raise OSError("startup task removal is only supported on Windows")
    task_result = _run(
        [_schtasks_executable(), "/Delete", "/TN", task_name, "/F"], runner=runner
    )
    registry_result = _run(
        [
            _reg_executable(),
            "DELETE",
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
            "/V",
            _registry_value_name(task_name),
            "/F",
        ],
        runner=runner,
    )
    if not task_result["success"] and not registry_result["success"]:
        raise RuntimeError(
            registry_result["stderr"]
            or registry_result["stdout"]
            or task_result["stderr"]
            or "startup removal failed"
        )
    return {
        "success": True,
        "task_name": task_name,
        "task_scheduler_removed": task_result["success"],
        "registry_removed": registry_result["success"],
    }


def startup_task_status(
    *,
    task_name: str = DEFAULT_TASK_NAME,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    if os.name != "nt":
        return {"task_name": task_name, "installed": False, "platform": os.name}
    task_result = _run(
        [_schtasks_executable(), "/Query", "/TN", task_name, "/FO", "LIST", "/V"],
        runner=runner,
    )
    if task_result["success"]:
        return {
            **task_result,
            "task_name": task_name,
            "installed": True,
            "method": "task_scheduler",
        }
    registry_result = _run(
        [
            _reg_executable(),
            "QUERY",
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
            "/V",
            _registry_value_name(task_name),
        ],
        runner=runner,
    )
    return {
        **registry_result,
        "task_name": task_name,
        "installed": registry_result["success"],
        "method": "current_user_run_registry" if registry_result["success"] else None,
    }


__all__ = [
    "DEFAULT_TASK_NAME",
    "startup_task_status",
    "uninstall_startup_task",
]
