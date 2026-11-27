"""Windows process launch policy for the F4 host and its owner transports."""

import ctypes
from io import UnsupportedOperation
from pathlib import Path
import subprocess
import sys


BACKGROUND_CREATION_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def background_argv(argv: list[str]) -> list[str]:
    """Use the same Python installation's GUI launcher for piped background commands."""
    if not BACKGROUND_CREATION_FLAGS or not argv:
        return argv
    executable = Path(argv[0])
    if not executable.is_absolute() or executable.name.lower() != "python.exe":
        return argv
    windowless = executable.with_name("pythonw.exe")
    return [str(windowless), *argv[1:]] if windowless.is_file() else argv


def inherit_console_creation_flags() -> int:
    """Attach to an existing console, but leave a headless caller headless."""
    if not BACKGROUND_CREATION_FLAGS:
        return 0
    windows_dlls = getattr(ctypes, "windll", None)
    return 0 if windows_dlls is not None and windows_dlls.kernel32.GetConsoleCP() else BACKGROUND_CREATION_FLAGS


def inherited_console_options() -> dict:
    flags = inherit_console_creation_flags()
    options = {"creationflags": flags}
    if flags:
        # CREATE_NO_WINDOW alone can detach the inherited pipes. Pass actual
        # standard handles through explicitly when the caller has no console.
        for name in ("stdin", "stdout", "stderr"):
            try:
                options[name] = getattr(sys, name).fileno()
            except (AttributeError, UnsupportedOperation, ValueError, OSError):
                options[name] = subprocess.DEVNULL
    return options
