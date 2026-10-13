"""Execute the real hook file through a POSIX shell with an isolated PATH."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".githooks" / "pre-commit"


def _shell():
    shell = shutil.which("sh")
    if shell is None:
        pytest.skip("POSIX shell unavailable")
    return shell


def test_precommit_uses_active_path_python_and_preserves_arguments(tmp_path):
    shell = _shell()
    executable = tmp_path / "python"
    executable.write_text('#!/bin/sh\nprintf \'%s\\n\' "$@"\n', encoding="utf-8")
    executable.chmod(0o755)
    result = subprocess.run([shell, str(HOOK), "one arg", "文件"], cwd=tmp_path,
        env={**os.environ, "PATH": str(tmp_path) + os.pathsep + str(Path(shell).parent)},
        capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert result.returncode == 0, result.stderr
    args = result.stdout.splitlines()
    assert args[:6] == ["-m", "pre_commit", "hook-impl", "--config=.pre-commit-config.yaml", "--hook-type=pre-commit", "--hook-dir"]
    assert args[-3:] == ["--", "one arg", "文件"]


def test_precommit_missing_runtime_is_clear_failure(tmp_path):
    result = subprocess.run([_shell(), str(HOOK)], cwd=tmp_path,
        env={**os.environ, "PATH": str(tmp_path)}, capture_output=True, text=True,
        encoding="utf-8", timeout=15)
    assert result.returncode == 1
    assert "pre-commit unavailable" in result.stderr


def test_precommit_contains_only_portable_shell_entry():
    content = HOOK.read_text(encoding="utf-8")
    assert content.startswith("#!/bin/sh\n")
    assert "INSTALL_PYTHON" not in content
    assert "ARGS=(" not in content
    assert "pre_push_gate" not in content
    assert "pytest" not in content
