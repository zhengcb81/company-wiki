"""Headless owner launches must keep both the runtime and its pipe contract."""

import ctypes
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tools.feedback_loop import process_launch


def test_only_uses_windowless_python_from_the_configured_installation(tmp_path, monkeypatch):
    monkeypatch.setattr(process_launch, "BACKGROUND_CREATION_FLAGS", 0x08000000)
    python = tmp_path / "python.exe"
    gui = tmp_path / "pythonw.exe"
    args = [str(python), "-B", "-c", "two words"]
    assert process_launch.background_argv(args) == args
    gui.touch()
    assert process_launch.background_argv(args) == [str(gui), *args[1:]]
    assert process_launch.background_argv(["python.exe", *args[1:]]) == ["python.exe", *args[1:]]
    assert process_launch.background_argv([str(gui), *args[1:]]) == [str(gui), *args[1:]]
    assert args[0] == str(python)
    monkeypatch.setattr(process_launch, "BACKGROUND_CREATION_FLAGS", 0)
    assert process_launch.background_argv(args) == args


@pytest.mark.parametrize(("code_page", "expected"), [(0, 0x08000000), (65001, 0)])
def test_child_keeps_the_callers_console_state(monkeypatch, code_page, expected):
    monkeypatch.setattr(process_launch, "BACKGROUND_CREATION_FLAGS", 0x08000000)
    kernel32 = SimpleNamespace(GetConsoleCP=lambda: code_page)
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(kernel32=kernel32), raising=False)
    assert process_launch.inherit_console_creation_flags() == expected


@pytest.mark.windows_native
@pytest.mark.skipif(os.name != "nt", reason="Windows GUI-launcher and console APIs")
def test_windows_gui_python_runs_a_real_piped_owner_command():
    executable = Path(sys.executable).with_name("python.exe")
    child = (
        "import ctypes,sys; "
        "assert ctypes.windll.kernel32.GetConsoleCP() == 0; "
        "sys.stdout.buffer.write(sys.stdin.buffer.read()); "
        "sys.stderr.buffer.write(b'owner stderr'); "
        "raise SystemExit(19)"
    )
    command = process_launch.background_argv([str(executable), "-B", "-c", child])
    assert Path(command[0]) == executable.with_name("pythonw.exe")
    result = subprocess.run(
        command, input=b"same request bytes\x00", capture_output=True, check=False,
        timeout=15, creationflags=process_launch.BACKGROUND_CREATION_FLAGS,
    )
    assert result.returncode == 19
    assert result.stdout == b"same request bytes\x00"
    assert result.stderr == b"owner stderr"
