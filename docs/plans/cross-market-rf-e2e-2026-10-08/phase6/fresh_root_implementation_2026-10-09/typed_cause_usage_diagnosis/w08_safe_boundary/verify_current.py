"""Concentrated existing responsibility checks; no broad unrelated CI rerun."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

from reproduce import CWP, FF, RF, safe_environment, write_json


def main() -> int:
    reports = []
    suite = [
        ("producer", CWP, ["tests/unit/test_acquisition_failure_diagnostic.py", "tests/contract/test_acquisition_failure_return_paths.py", "tests/integration/test_acquisition_failure_cli_e2e.py"]),
        ("ff", FF, ["tests/test_provider_cause_contract.py"]),
        ("rf", RF, ["tests/test_source_failure_cause.py"]),
    ]
    with TemporaryDirectory(prefix="cwp-w08-current-checks-20261009-") as directory:
        temporary = Path(directory)
        for name, root, files in suite:
            env = safe_environment()
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            started = time.monotonic()
            command = [sys.executable, "-X", "utf8", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                       "--basetemp", str(temporary / name), *files]
            result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=90, check=False)
            Path(__file__).with_name(name + "-current.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
            report = {"name": name, "cwd": str(root), "argv": command, "exit_code": result.returncode,
                      "duration_seconds": round(time.monotonic() - started, 3), "log": name + "-current.txt"}
            reports.append(report)
            print(json.dumps(report), flush=True)
    receipt = {"schema_version": "w08-current-contract-check/1", "suites": reports,
               "temp_root_exists_after_cleanup": temporary.exists(), "external_http_requests": 0, "paid_calls": 0}
    write_json(Path(__file__).with_name("current-checks.json"), receipt)
    return int(any(row["exit_code"] for row in reports))


if __name__ == "__main__":
    raise SystemExit(main())
