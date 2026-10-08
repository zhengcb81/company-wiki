"""OS boundary properties: pipes, deadline and nested owned-process scopes."""

import os
from pathlib import Path
import sys

import pytest

from company_wiki._bounded_process import ChildTimeout, OutputLimitExceeded, run_bounded, run_json_process


@pytest.mark.parametrize("pipe", ["stdout", "stderr"])
def test_child_output_is_stopped_during_read_at_cap(pipe):
    code = f"import sys,time;sys.{pipe}.write('x'*4097);sys.{pipe}.flush();time.sleep(30)"
    with pytest.raises(OutputLimitExceeded):
        run_bounded([sys.executable, "-B", "-c", code], timeout_seconds=5,
                    stdout_cap_bytes=4096, stderr_cap_bytes=4096)


def test_nonreading_stdin_is_inside_whole_deadline():
    with pytest.raises(ChildTimeout):
        run_bounded([sys.executable, "-B", "-c", "import time;time.sleep(30)"],
                    input_bytes=b"x" * 131072, timeout_seconds=0.3)


def test_nested_process_ownership_succeeds_without_neighbor_import(tmp_path):
    # Represents FF's outer job and CWP's nested SDK job on Windows.
    code = "from company_wiki._bounded_process import run_json_process;import os,sys;" \
        "r=run_json_process([sys.executable,'-B','-c',\"print('nested result')\"]," \
        "input='',cwd=os.getcwd(),env=dict(os.environ),timeout_seconds=5);" \
        "sys.stdout.write(r.stdout);sys.exit(r.returncode)"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    result = run_json_process([sys.executable, "-B", "-c", code], input="",
                             cwd=tmp_path, env=env, timeout_seconds=10)
    assert result.returncode == 0
    assert result.stdout.strip() == "nested result"
