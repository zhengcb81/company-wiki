"""The runtime mutex is automatic OS ownership, including process death."""

import importlib
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
    script = "from company_wiki._file_mutex import os_file_mutex\nimport sys,time\nfrom pathlib import Path\nwith os_file_mutex(Path(sys.argv[1])):\n print('ready',flush=True)\n time.sleep(30)\n"
    process = subprocess.Popen([sys.executable, "-c", script, str(path)], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    try:
        assert process.stdout.readline().strip() == "ready"
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
