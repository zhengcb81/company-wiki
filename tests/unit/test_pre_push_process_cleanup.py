"""A timed-out gate owns descendants before its scratch root is removed."""
import json
import os
import sys
import time

import pytest

from company_wiki._bounded_process import pid_is_alive
from tools import pre_push_gate as gate


@pytest.mark.skipif(os.name != "nt", reason="Windows Job descendant lifetime regression")
def test_timeout_stops_the_owned_grandchild_before_return(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gate, "PROJECT_ROOT", tmp_path)
    record, stop = tmp_path / "pid.json", tmp_path / "stop"
    # The descendant has no inherited output pipes, so waiting for EOF cannot
    # accidentally hide a leaked process. Its stop file also bounds RED cleanup.
    child = ("import os,time,pathlib; "
             f"record=pathlib.Path({str(record)!r}); "
             "pending=record.with_suffix('.pending'); pending.write_text(str(os.getpid())); "
             "os.replace(pending,record); "
             f"stop=pathlib.Path({str(stop)!r}); "
             "deadline=time.monotonic()+12; "
             "exec('while not stop.exists() and time.monotonic()<deadline: time.sleep(.02)')")
    parent = ("import subprocess,sys,time,pathlib; "
              f"p=subprocess.Popen([sys.executable,'-c',{child!r}],"
              "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
              f"record=pathlib.Path({str(record)!r}); "
              "exec('while not record.exists(): time.sleep(.01)'); "
              "print('owned grandchild ready',flush=True); time.sleep(12)")
    # Use the installed interpreter directly for the outer parent; the child is
    # still a real additional process, independent of the venv launcher layer.
    executable = getattr(sys, "_base_executable", sys.executable)
    started = time.monotonic()
    try:
        # Cold Windows interpreter startup is part of the bound; leave enough
        # room to exercise an actual ready descendant, rather than timing out
        # before the fixture exists. Its own 12s lifetime must not mask a leak.
        assert gate._run([executable, "-c", parent], "owned timeout", timeout=8) == 124
        assert record.exists(), "the descendant must have started before timeout"
        pid = json.loads(record.read_text())
        assert not pid_is_alive(pid), "gate returned while its owned descendant was alive"
        assert time.monotonic() - started < 13
        output = capsys.readouterr().out
        assert "owned grandchild ready" in output and "timeout" in output
    finally:
        stop.write_text("stop")
        if record.exists():
            pid = json.loads(record.read_text())
            until = time.monotonic() + 3
            while pid_is_alive(pid) and time.monotonic() < until:
                time.sleep(.02)


def test_child_failure_keeps_actual_exit_code_and_diagnostic(capsys):
    assert gate._run([sys.executable, "-c",
                      "import sys;print('before failure');sys.stderr.write('failure detail');sys.exit(7)"],
                     "actual failure") == 7
    output = capsys.readouterr().out
    assert "before failure" in output and "failure detail" in output


@pytest.mark.parametrize("pipe", ["stdout", "stderr"])
def test_output_overflow_is_bounded_red_with_retained_progress(monkeypatch, capsys, pipe):
    monkeypatch.setattr(gate, "STDOUT_CAP_BYTES", 4096)
    monkeypatch.setattr(gate, "STDERR_CAP_BYTES", 4096)
    code = (f"import sys,time;stream=sys.{pipe};stream.write('last progress\\n');"
            "stream.flush();stream.write('x'*8192);stream.flush();time.sleep(12)")
    assert gate._run([sys.executable, "-c", code], "output flood", timeout=4) == 125
    output = capsys.readouterr().out
    assert "last progress" in output and "output truncated" in output
    assert "stdout cap=4096" in output and len(output) < 4600


@pytest.mark.skipif(os.name != "nt", reason="Windows launcher and open-file deletion regression")
def test_venv_timeout_releases_descendant_file_before_scratch_cleanup(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    record = tmp_path / "owned.pid"
    stop = tmp_path / "stop"
    monkeypatch.setattr(gate, "PROJECT_ROOT", checkout)
    run = gate._run
    monkeypatch.setattr(gate, "_run", lambda cmd, label, **kwargs:
                        run(cmd, label, **{**kwargs, "timeout": 8}))
    child = ("import os,pathlib,time,sys; "
             "held=open(sys.argv[1],'w'); "
             f"record=pathlib.Path({str(record)!r}); "
             "pending=record.with_suffix('.pending'); pending.write_text(str(os.getpid())); "
             "os.replace(pending,record); "
             f"stop=pathlib.Path({str(stop)!r}); "
             "deadline=time.monotonic()+12; "
             "exec('while not stop.exists() and time.monotonic()<deadline: time.sleep(.02)')")
    parent = ("import pathlib,subprocess,sys,time; "
              "scratch=pathlib.Path(sys.argv[sys.argv.index('--basetemp')+1]); "
              f"p=subprocess.Popen([sys.executable,'-c',{child!r},str(scratch/'held.txt')]); "
              "p.wait()")
    try:
        assert gate._run_pytest_gate([sys.executable, "-c", parent], "scratch timeout") == 124
        assert record.exists()
        assert not pid_is_alive(int(record.read_text()))
        assert not list(checkout.iterdir())
    finally:
        stop.write_text("stop")
        if record.exists():
            until = time.monotonic() + 3
            while pid_is_alive(int(record.read_text())) and time.monotonic() < until:
                time.sleep(.02)
