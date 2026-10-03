"""The runtime mutex is automatic OS ownership, including process death."""

import importlib
import os
from pathlib import Path
import subprocess
import sys

import pytest


def test_same_path_excludes_another_owner_without_pid_files(tmp_path):
    module = importlib.import_module("company_wiki._file_mutex")
    path = tmp_path / "runtime.lock"
    with module.os_file_mutex(path, timeout_seconds=0.1):
        with pytest.raises(module.FileMutexLockedError):
            with module.os_file_mutex(path, timeout_seconds=0.1):
                pytest.fail("two owners obtained the same mutex")
    with module.os_file_mutex(path, timeout_seconds=0.1):
        assert path.stat().st_size == 1


def test_killed_process_releases_runtime_mutex_immediately(tmp_path, hermetic_runtime):
    module = importlib.import_module("company_wiki._file_mutex")
    path = tmp_path / "runtime.lock"
    script = "import sys,time\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[2])\nfrom company_wiki._file_mutex import os_file_mutex\nwith os_file_mutex(Path(sys.argv[1])):\n print('ready',flush=True)\n time.sleep(30)\n"
    # CI does not install the package. Ignore editable installs and the parent's
    # collection-time sys.path so the child must be bootstrapped explicitly.
    child_env = dict(os.environ)
    child_env.pop("PYTHONPATH", None)
    source_root = Path(__file__).resolve().parents[2] / "src"
    process = subprocess.Popen([sys.executable, "-S", "-c", script, str(path), str(source_root)], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, cwd=tmp_path, env=child_env)
    try:
        assert process.stdout.readline().strip() == "ready", process.stderr.read()
        with pytest.raises(module.FileMutexLockedError):
            with module.os_file_mutex(path, timeout_seconds=0.1):
                pytest.fail("live owner was bypassed")
        process.kill()
        process.communicate(timeout=5)
        with module.os_file_mutex(path, timeout_seconds=0.1):
            assert path.stat().st_size == 1
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)
