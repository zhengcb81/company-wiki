"""A large local gate retains all tests while using two isolated workers."""
import json
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET

import pytest

from unit.test_pre_push_temp_scope import gate


@pytest.mark.parametrize("full", [True, False])
def test_only_full_unit_gate_uses_bounded_file_scheduled_workers(full, monkeypatch):
    observed = []
    monkeypatch.setattr(gate, "_run", lambda cmd, *args, **kwargs: observed.append(cmd) or 0)
    case = "tests/unit" if full else "tests/unit/test_small.py"
    assert gate._run_pytest_gate([sys.executable, "-m", "pytest", case], "unit check") == 0
    command = observed[0]
    assert command.count(case) == 1
    if full:
        assert command[command.index("-n") + 1] == "2"
        assert "--dist=loadfile" in command
    else:
        assert "-n" not in command
    assert not Path(command[command.index("--basetemp") + 1]).exists()


@pytest.mark.parametrize("fail", [False, True])
def test_real_worker_processes_keep_inventory_failure_and_owned_cleanup(tmp_path, monkeypatch, fail):
    sentinel = tmp_path / "existing.txt"
    sentinel.write_text("original", encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="gate-owned-", dir=tmp_path) as temporary:
        root = Path(temporary)
        tests = root / "tests" / "unit"
        tests.mkdir(parents=True)
        results = root / "observed"
        results.mkdir()
        (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        shared = ("import os,json\nfrom pathlib import Path\nimport pytest\n"
            f"OUT=Path({str(results)!r})\n"
            "def observe(name,worker_id):\n"
            "    (OUT/name).write_text(json.dumps({'pid':os.getpid(),'worker':worker_id}))\n")
        (tests / "test_first.py").write_text(shared +
            "@pytest.mark.parametrize('value',[1,2])\n"
            "def test_first(value,worker_id):\n    observe('first'+str(value),worker_id)\n", encoding="utf-8")
        (tests / "test_second.py").write_text(shared +
            "def test_second(worker_id):\n    observe('second',worker_id)\n"
            f"    assert {not fail!r}, 'synthetic failure must propagate'\n"
            "@pytest.mark.skip(reason='synthetic capability skip')\n"
            "def test_capability(): pass\n", encoding="utf-8")
        monkeypatch.setattr(gate, "PROJECT_ROOT", root)
        monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
        report = root / "result.xml"
        code = gate._run_pytest_gate([sys.executable, "-m", "pytest", "tests/unit", "-q",
            "-p", "xdist.plugin", "--tb=short", "--junitxml=" + str(report)], "actual isolated workers")
        assert code == (1 if fail else 0)
        cases = list(ET.parse(report).getroot().iter("testcase"))
        assert len(cases) == 4
        assert sum(c.find("failure") is not None for c in cases) == int(fail)
        assert sum(c.find("skipped") is not None for c in cases) == 1
        observed = [json.loads(path.read_text()) for path in results.iterdir()]
        assert len(observed) == 3
        assert {row["worker"] for row in observed} == {"gw0", "gw1"}
        assert len({row["pid"] for row in observed}) == 2
    assert not root.exists()
    assert list(tmp_path.iterdir()) == [sentinel]
    assert sentinel.read_text(encoding="utf-8") == "original"
