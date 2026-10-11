"""One bounded final engineering node; all scratch ownership is recorded and restored."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid

LEAF = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures-root")
OUT = Path(__file__).resolve().parent
TEMP_BASE = Path(tempfile.gettempdir()).resolve()
OWNED = TEMP_BASE / ("cwpa-w06-measures-final-" + uuid.uuid4().hex[:8])
assert OWNED.parent == TEMP_BASE and not OWNED.exists()

def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def snapshot():
    rows = []
    for directory in (LEAF / "skills/revenue-forecast-audit", LEAF / "tests", LEAF / "tools"):
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            data = path.read_bytes()
            rows.append({"path": path.relative_to(LEAF).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    return rows

before = snapshot()
write("source-before-final.json", before)
OWNED.mkdir()
env = dict(os.environ, TEMP=str(OWNED), TMP=str(OWNED), PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
runs = []

def run(name, argv, timeout):
    started = time.monotonic()
    logfile = OUT / (name + ".log")
    with logfile.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(argv, cwd=LEAF, env=env, stdout=stream, stderr=subprocess.STDOUT)
        try:
            exit_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=15)
            else:
                process.kill()
            process.wait(timeout=15)
            exit_code = "TIMEOUT"
    result = {"phase": name, "argv": argv, "exit_code": exit_code,
              "elapsed_seconds": round(time.monotonic() - started, 6), "log": logfile.name,
              "log_sha256": hashlib.sha256(logfile.read_bytes()).hexdigest()}
    runs.append(result)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result

failure = None
cli_rows = []
try:
    # Complete current main + W05 closure + W06 + ROOT regression suite, once.
    assert run("final-full-unit", [sys.executable, "-B", "-X", "utf8", "-m", "unittest", "discover", "-s", "tests", "-v"], 180)["exit_code"] == 0
    # Original numeric helper has not been edited; explicit unchanged-helper receipt.
    assert run("final-numeric-unchanged", [sys.executable, "-B", "-X", "utf8", "-m", "unittest", "discover", "-s", "tests", "-p", "test_numeric_audit.py", "-v"], 20)["exit_code"] == 0
    e2e_root = OWNED / "cwpa-real-financial-e2e"
    assert run("final-offline-e2e", [sys.executable, "-B", "-X", "utf8", str(LEAF / "tools/run_financial_measure_e2e.py"), "--owned-root", str(e2e_root), "--receipt", str(OUT / "final-offline-e2e.json")], 30)["exit_code"] == 0
    assert not e2e_root.exists()
    cases = json.loads((LEAF / "tests/fixtures/financial_measures/root_acceptance_regressions.json").read_text(encoding="utf-8"))["cases"]
    expected = {"conversion_result_missing_source_ref": (3, "UNRESOLVED"),
                "sum_output_silently_relabels_currency_entity_definition": (2, "INVALID"),
                "difference_one_operand_should_diagnose_not_crash": (2, "INVALID")}
    sentinel = OWNED / "cli-sentinel.txt"
    sentinel.write_bytes(b"root-final-cli-initial")
    sentinel_sha = hashlib.sha256(sentinel.read_bytes()).hexdigest()
    for case in cases:
        if case["id"] not in expected:
            continue
        ledger_file = OWNED / (case["id"] + ".json")
        ledger_file.write_text(json.dumps(case["ledger"], ensure_ascii=False), encoding="utf-8")
        argv = [sys.executable, "-B", "-X", "utf8", str(LEAF / "skills/revenue-forecast-audit/scripts/financial_measure_audit.py"), "--ledger", str(ledger_file), "--out-root", str(OWNED / "cli-attempts")]
        proc = subprocess.run(argv, cwd=LEAF, env=env, capture_output=True, encoding="utf-8", timeout=15)
        receipt = json.loads(proc.stdout)
        report_file = Path(receipt["output_file"])
        report = json.loads(report_file.read_text(encoding="utf-8"))
        assert proc.returncode == expected[case["id"]][0] and report["overall"] == expected[case["id"]][1]
        assert report["source_truth_verified"] is False and report["economic_reasonableness"] == "not_evaluated"
        cli_rows.append({"id": case["id"], "argv": argv, "exit_code": proc.returncode, "receipt": receipt,
                         "report_sha256": hashlib.sha256(report_file.read_bytes()).hexdigest(), "report": report})
    assert len(cli_rows) == 3 and hashlib.sha256(sentinel.read_bytes()).hexdigest() == sentinel_sha
    write("final-real-cli-regressions.json", {"cases": cli_rows, "sentinel_unchanged": True})
except Exception as exc:
    failure = f"{type(exc).__name__}: {exc}"
finally:
    after = snapshot()
    write("source-after-final.json", after)
    cleanup_entries = []
    for path in [OWNED, *OWNED.rglob("*")]:
        assert path.resolve().is_relative_to(OWNED) and not path.is_symlink()
        if os.name == "nt":
            assert not path.stat(follow_symlinks=False).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
        if path.is_file():
            cleanup_entries.append({"path": path.relative_to(OWNED).as_posix(), "bytes": path.stat().st_size})
    assert OWNED.parent == TEMP_BASE and OWNED.name.startswith("cwpa-w06-measures-final-")
    shutil.rmtree(OWNED)
    assert not OWNED.exists()
    result = {"schema_version": "w06-root-measures-final-node/1", "status": "PASS" if failure is None and before == after else "FAIL",
              "failure": failure, "source_bytes_unchanged_during_test": before == after, "runs": runs,
              "owned_root": str(OWNED), "before": "absent", "after": "absent", "restored": True,
              "remaining_scratch_before_cleanup": cleanup_entries, "actual_cli_checks": len(cli_rows),
              "provider_calls": 0, "model_calls": 0, "paid_usd": 0,
              "source_truth_verified": False, "economic_reasonableness": "not_evaluated"}
    write("final-node.json", result)
    print(json.dumps({"status": result["status"], "failure": failure, "restored": True,
                      "source_bytes_unchanged": before == after, "actual_cli_checks": len(cli_rows)}, ensure_ascii=False), flush=True)
sys.exit(0 if result["status"] == "PASS" else 1)
