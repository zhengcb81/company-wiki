"""The feedback launcher follows the current installation and keeps native streams."""

import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from tools.feedback_loop import codex_cli, process_launch


def _executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    path.chmod(0o700)
    return path


def test_path_ignores_removed_version_workdir_and_relative_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(codex_cli, "_WINDOWS", True)
    _executable(tmp_path / "codex.exe")
    _executable(tmp_path / "relative" / "codex.exe")
    fresh = _executable(tmp_path / "current" / "codex.exe")
    monkeypatch.chdir(tmp_path)
    env = {"PATH": os.pathsep.join([str(tmp_path / "removed"), "", "relative", str(fresh.parent)])}

    assert codex_cli.resolve_codex(env) == fresh


def test_windows_uses_the_current_registered_install_when_path_is_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(codex_cli, "_WINDOWS", True)
    system = tmp_path / "system"
    powershell = _executable(system / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe")
    registered = tmp_path / "新版本"
    codex = _executable(registered / "app" / "resources" / "codex.exe")
    calls = []

    def appx(argv, **options):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout=str(registered) + "\n")

    monkeypatch.setattr(codex_cli.subprocess, "run", appx)
    env = {"PATH": str(tmp_path / "removed"), "SystemRoot": str(system)}

    assert codex_cli.resolve_codex(env) == codex
    assert len(calls) == 1 and calls[0][0] == str(powershell)
    assert "-NoProfile" in calls[0] and "Get-AppxPackage -Name 'OpenAI.Codex'" in calls[0][-1]


def test_missing_codex_has_a_startup_error(monkeypatch, capsys):
    monkeypatch.setattr(codex_cli, "resolve_codex", lambda: None)
    assert codex_cli.main(["--version"]) == 127
    assert capsys.readouterr().err == "Codex CLI executable not found.\n"


def test_windows_codex_child_preserves_the_callers_console_policy(monkeypatch):
    calls = []

    def launch(argv, **options):
        calls.append((argv, options))
        return subprocess.CompletedProcess(argv, 19)

    monkeypatch.setattr(codex_cli, "_WINDOWS", True)
    monkeypatch.setattr(codex_cli, "resolve_codex", lambda: Path("codex.exe"))
    monkeypatch.setattr(process_launch, "sys", SimpleNamespace(
        stdin=SimpleNamespace(fileno=lambda: 10),
        stdout=SimpleNamespace(fileno=lambda: 11),
        stderr=SimpleNamespace(fileno=lambda: 12),
    ))
    monkeypatch.setattr(codex_cli.subprocess, "run", launch)

    monkeypatch.setattr(process_launch, "inherit_console_creation_flags", lambda: 0)
    assert codex_cli.main(["exec", "--flag=exact"]) == 19
    monkeypatch.setattr(process_launch, "inherit_console_creation_flags", lambda: 0x08000000)
    assert codex_cli.main(["exec", "--flag=exact"]) == 19
    assert calls == [
        (["codex.exe", "exec", "--flag=exact"], {"check": False, "creationflags": 0}),
        (["codex.exe", "exec", "--flag=exact"], {
            "check": False, "creationflags": 0x08000000, "stdin": 10, "stdout": 11, "stderr": 12,
        }),
    ]


def test_native_argv_streams_and_exit_code_are_transparent():
    bootstrap = (
        "import sys; from tools.feedback_loop import codex_cli; "
        "codex_cli.resolve_codex=lambda: sys.executable; "
        "raise SystemExit(codex_cli.main(sys.argv[1:]))"
    )
    child = (
        "import sys; "
        "assert sys.argv[1:]==['two words','--flag=exact']; "
        "sys.stdout.buffer.write(sys.stdin.buffer.read()+b'\\xff'); "
        "sys.stderr.buffer.write(b'child stderr\\r\\n'); "
        "raise SystemExit(23)"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", bootstrap, "-B", "-c", child, "two words", "--flag=exact"],
        input=b"raw\x00payload\r\n",
        capture_output=True,
        check=False,
        timeout=10,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert result.returncode == 23
    assert result.stdout == b"raw\x00payload\r\n\xff"
    assert result.stderr == b"child stderr\r\n"
