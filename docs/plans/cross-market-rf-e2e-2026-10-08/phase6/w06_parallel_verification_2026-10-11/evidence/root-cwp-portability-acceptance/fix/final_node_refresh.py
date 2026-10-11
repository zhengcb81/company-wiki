"""Single ROOT-author final synthetic node; evidence immutable, originals absent."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-portability-root")
HERE = Path(__file__).resolve().parent / "final-refresh"
HERE.mkdir(exist_ok=False)
PRODUCTS = [
    *sorted((ROOT / "tools/source_root_portability").glob("*.py")),
    ROOT / "tests/unit/test_w06_root_portability_oracle.py",
    ROOT / "tests/integration/test_w06_root_portability.py",
]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from tools.source_root_portability.runtime import child_env
from tools.source_root_portability import report


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(paths):
    return [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p),
             "byte_size": p.stat().st_size} for p in paths]


def write(name, value):
    path = HERE / name
    assert not path.exists(), path
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def call(name, argv, env, timeout):
    started = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=timeout)
    for side in ("stdout", "stderr"):
        target = HERE / f"{name}-{side}.log"
        assert not target.exists()
        target.write_bytes(getattr(result, side))
    return {"exit": result.returncode, "seconds": round(time.monotonic() - started, 3),
            "summary": re.findall(r"=+ (.*(?:passed|failed|skipped).*) =+",
                                  result.stdout.decode("utf-8", "replace"))[-1:]}


assert not (HERE / "final-node.json").exists()
initial = inventory(PRODUCTS)
production = inventory([ROOT / path for path in report.TRACKED_MODULES])
result = {"schema_version": "root-w06-portability-final-node/1",
          "head": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                         cwd=ROOT, text=True).strip(),
          "products": initial, "production_before": production,
          "network_calls": 0, "provider_calls": 0, "LLM_calls": 0,
          "fees_usd": 0, "real_raw_accessed": 0}
temporary = Path(tempfile.mkdtemp(prefix="w06-port-final-"))
try:
    env = child_env(ROOT, temporary / "launcher-runtime")
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    result["tests"] = call("tests", [
        sys.executable, "-X", "utf8", "-B", "-m", "pytest",
        "tests/unit/test_w06_root_portability_oracle.py",
        "tests/integration/test_w06_root_portability.py",
        "--basetemp", str(temporary / "pytest"), "-q", "--tb=short",
    ], env, 60)
    result["ruff"] = call("ruff", [
        sys.executable, "-X", "utf8", "-B", "-m", "ruff", "check",
        "tools/source_root_portability", "tests/unit/test_w06_root_portability_oracle.py",
        "tests/integration/test_w06_root_portability.py",
    ], env, 15)
    owned, output = temporary / "owned", temporary / "output"
    original_paths = []
    for name in ("cfg", "lake_A", "lake_B", "catalog", "logs", "scratch"):
        path = owned / name / "keep.bin"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"baseline-only-synthetic:" + name.encode())
        (path.parent / "empty").mkdir()
        original_paths.append(path)
    output.mkdir()
    output_sentinel = output / "already-present.bin"
    output_sentinel.write_bytes(b"existing-output")
    (output / "empty").mkdir()
    before = {str(p.relative_to(temporary)): sha(p)
              for p in [*original_paths, output_sentinel]}
    result["runner"] = call("runner", [
        sys.executable, "-X", "utf8", "-B", str(ROOT / "tools/source_root_portability/run.py"),
        "--owned-root", str(owned), "--out-root", str(output),
    ], env, 45)
    reports = list(output.glob("attempt-*/report.json"))
    if reports:
        actual = json.loads(reports[0].read_text(encoding="utf-8"))
        write("real-run-report.json", actual)
        result["runner_report_sha256"] = sha(HERE / "real-run-report.json")
        result["runner_oracle"] = actual["oracle_verdict"]
        result["reader_calls"] = actual["cost"]
        result["bound_identity"] = actual["run"]["code_identity"]
    result["sentinels_before"] = before
    result["sentinels_after"] = {str(p.relative_to(temporary)): sha(p)
                               for p in [*original_paths, output_sentinel] if p.exists()}
    result["existing_empty_directories_preserved"] = all(
        (owned / name / "empty").is_dir()
        for name in ("cfg", "lake_A", "lake_B", "catalog", "logs", "scratch")
    ) and (output / "empty").is_dir()
    result["owned_new_children_remaining"] = [
        path.name for path in owned.iterdir() if path.name.startswith("w06-owned-")
    ]
finally:
    assert temporary.parent == Path(tempfile.gettempdir())
    assert temporary.name.startswith("w06-port-final-")
    shutil.rmtree(temporary)
    result["temporary_restored_absent"] = not temporary.exists()
    result["products_after"] = inventory(PRODUCTS)
    result["production_after"] = inventory([ROOT / path for path in report.TRACKED_MODULES])
    result["status"] = "PASS" if all([
        result.get("tests", {}).get("exit") == 0,
        result.get("ruff", {}).get("exit") == 0,
        result.get("runner", {}).get("exit") == 0,
        result.get("runner_oracle", {}).get("overall") == "PASS",
        result.get("sentinels_before") == result.get("sentinels_after"),
        result.get("existing_empty_directories_preserved"),
        result.get("owned_new_children_remaining") == [],
        result["temporary_restored_absent"],
        result["products"] == result["products_after"],
        result["production_before"] == result["production_after"],
    ]) else "FAIL"
    write("final-node.json", result)
print(json.dumps({key: result.get(key) for key in
                  ("status", "tests", "ruff", "runner", "runner_oracle",
                   "temporary_restored_absent")}, ensure_ascii=False))
raise SystemExit(0 if result["status"] == "PASS" else 1)
