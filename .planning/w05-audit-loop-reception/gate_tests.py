"""Run the one gate-classification scope in a self-restoring test directory."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
OUT = PROJECT / "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-audit-loop-acceptance"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", choices=("red", "green"), required=True)
    args = parser.parse_args()
    log_path = OUT / f"gate-{args.attempt}.log"
    assert not log_path.exists()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONPATH=str(PROJECT / "src"))
    start = datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix="gate-owned-", dir=OUT) as root:
        assert Path(root).resolve().is_relative_to(OUT.resolve())
        command = [sys.executable, "-X", "utf8", "-B", "-m", "pytest", "tests/unit/test_ci_push_selection.py",
                   "tests/unit/test_pre_push_temp_scope.py", "-q", "--tb=short", "--basetemp", root, "-p", "no:cacheprovider"]
        result = subprocess.run(command, cwd=PROJECT, env=env, capture_output=True, timeout=120)
        log_path.write_bytes(result.stdout + result.stderr)
    record = {"command": command, "exit_code": result.returncode,
              "elapsed_seconds": (datetime.now(timezone.utc) - start).total_seconds(),
              "scratch": root, "restored_initial_absent": not Path(root).exists(), "fees_usd": 0}
    (OUT / f"gate-{args.attempt}.json").write_bytes((json.dumps(record, indent=2) + "\n").encode())
    assert record["restored_initial_absent"]
    assert result.returncode == (1 if args.attempt == "red" else 0), record
    print(json.dumps(record))


if __name__ == "__main__":
    main()
