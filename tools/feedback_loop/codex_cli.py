"""Launch the installed Codex CLI without pinning a desktop package version."""

import os
from pathlib import Path
import subprocess
import sys

from .process_launch import BACKGROUND_CREATION_FLAGS, inherit_console_creation_flags


_WINDOWS = os.name == "nt"


def _can_launch(path: Path) -> bool:
    try:
        return path.is_file() and os.access(path, os.X_OK)
    except OSError:
        return False


def _registered_windows_codex(environ) -> Path | None:
    system_root = Path(environ.get("SystemRoot") or environ.get("WINDIR") or "")
    if not system_root.is_absolute():
        return None
    powershell = system_root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if not _can_launch(powershell):
        return None
    query = (
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
        "Get-AppxPackage -Name 'OpenAI.Codex' -ErrorAction Stop | "
        "Select-Object -ExpandProperty InstallLocation"
    )
    try:
        result = subprocess.run(
            [str(powershell), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", query],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            encoding="utf-8-sig",
            errors="replace",
            timeout=10,
            check=False,
            creationflags=BACKGROUND_CREATION_FLAGS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode == 0:
        for location in result.stdout.splitlines():
            root = Path(location.strip())
            candidate = root / "app" / "resources" / "codex.exe"
            if root.is_absolute() and _can_launch(candidate):
                return candidate
    return None


def resolve_codex(environ=None) -> Path | None:
    environ = os.environ if environ is None else environ
    executable = "codex.exe" if _WINDOWS else "codex"
    # Use explicitly configured PATH directories and exclude implicit cwd lookup.
    for directory in os.get_exec_path(environ):
        root = Path(directory.strip('"') if _WINDOWS else directory)
        candidate = root / executable
        if root.is_absolute() and _can_launch(candidate):
            return candidate
    return _registered_windows_codex(environ) if _WINDOWS else None


def main(argv=None) -> int:
    executable = resolve_codex()
    if executable is None:
        print("Codex CLI executable not found.", file=sys.stderr)
        return 127
    command = [str(executable), *(sys.argv[1:] if argv is None else argv)]
    try:
        if not _WINDOWS:
            os.execv(command[0], command)
        return subprocess.run(command, check=False, creationflags=inherit_console_creation_flags()).returncode
    except OSError:
        print("Codex CLI executable could not be started.", file=sys.stderr)
        return 126


if __name__ == "__main__":
    raise SystemExit(main())
