"""Independent bounded shutdown diagnostic; production timeout remains 600."""
from pathlib import Path
import contextlib
import ctypes
import hashlib
import importlib.util
import inspect
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).with_name("full-unit-workers-timeout-control.json")
minimal = {key: os.environ[key] for key in (
    "SystemRoot", "WINDIR", "COMSPEC", "PATH", "TEMP", "TMP", "PATHEXT",
    "SYSTEMDRIVE", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
) if key in os.environ}
minimal.update(PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1",
    PYTHON_DOTENV_DISABLED="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONIOENCODING="utf-8")
os.environ.clear()
os.environ.update(minimal)
spec = importlib.util.spec_from_file_location("independent_worker_gate", ROOT / "tools/pre_push_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
record = {"gate_sha": hashlib.sha256(Path(gate.__file__).read_bytes()).hexdigest(),
    "production_timeout_default": inspect.signature(gate._run).parameters["timeout"].default,
    "diagnostic_timeout": 5}
owned = Path(tempfile.mkdtemp(prefix="du11-worker-timeout-"))
original = gate._run
try:
    record["narrow_and_nonzero_controls"] = []
    for scope in ("tests/unit/test_small.py", "tests/contract/test_small.py", "tests/unitary"):
        commands = []
        gate._run = lambda cmd, *args, **kwargs: commands.append(cmd) or 7
        assert gate._run_pytest_gate([sys.executable, "-m", "pytest", scope], scope) == 7
        assert "-n" not in commands[0]
        assert not Path(commands[0][commands[0].index("--basetemp") + 1]).exists()
        record["narrow_and_nonzero_controls"].append(scope)
    project = owned / "project"
    (project / "tests/unit").mkdir(parents=True)
    (project / "pids").mkdir()
    (project / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    for index in (1, 2):
        body = (
            "import json,os,time,sqlite3\nfrom pathlib import Path\n"
            "def test_blocking(tmp_path,worker_id):\n"
            "    con=sqlite3.connect(tmp_path/'held.db')\n"
            "    con.execute('create table t(x)')\n"
            f"    target=Path(__file__).resolve().parents[2]/'pids'/'{index}'\n"
            "    target.write_text(json.dumps({'pid':os.getpid(),'worker':worker_id}),encoding='utf-8')\n"
            "    time.sleep(30)\n    con.close()\n"
        )
        (project / f"tests/unit/test_{index}.py").write_text(body, encoding="utf-8")
    gate.PROJECT_ROOT = project
    allocated = []
    def shortened(cmd, label, **kwargs):
        allocated.append(Path(cmd[cmd.index("--basetemp") + 1]))
        return original(cmd, label, timeout=5, **kwargs)
    gate._run = shortened
    capture = io.StringIO()
    started = time.monotonic()
    try:
        with contextlib.redirect_stdout(capture):
            record["returncode"] = gate._run_pytest_gate([
                sys.executable, "-m", "pytest", "tests/unit", "-p", "xdist.plugin", "-q",
            ], "diagnostic blocked workers")
    except BaseException as exc:
        record["exception"] = type(exc).__name__ + ": " + str(exc)
    record["elapsed_seconds"] = time.monotonic() - started
    record["controller_output"] = capture.getvalue()
    record["pids"] = [json.loads(path.read_text(encoding="utf-8")) for path in (project / "pids").iterdir()]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    def alive(pid):
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = kernel.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel.CloseHandle(handle)
        return bool(ok and code.value == 259)
    record["workers_live_on_return"] = [row["pid"] for row in record["pids"] if alive(row["pid"])]
    record["gate_temps_removed"] = [not path.exists() for path in allocated]
    if record["workers_live_on_return"]:
        for pid in record["workers_live_on_return"]:
            result = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
            record.setdefault("owned_forced_cleanup", []).append({"pid": pid, "returncode": result.returncode})
finally:
    assert owned.resolve().parent == Path(tempfile.gettempdir()).resolve()
    assert owned.name.startswith("du11-worker-timeout-")
    shutil.rmtree(owned)
    record["owned_temp_removed"] = not owned.exists()
    OUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in record.items() if key != "controller_output"}))
