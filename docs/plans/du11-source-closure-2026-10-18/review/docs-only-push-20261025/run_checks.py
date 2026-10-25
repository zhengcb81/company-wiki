"""Run focused gate checks in an owned, cleaned test environment."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[5]
EVIDENCE = Path(__file__).resolve().parent


def main() -> int:
    phase, *targets = sys.argv[1:]
    if phase not in {"red", "green", "scope-red", "final", "environment-rerun"}:
        raise ValueError("unsupported evidence phase")
    start = time.monotonic()
    receipt = {"phase": phase, "targets": targets}
    with tempfile.TemporaryDirectory(prefix="cwdoc-", dir=ROOT) as scratch:
        owned = Path(scratch).resolve()
        if owned.parent != ROOT:
            raise ValueError("unexpected test root")
        receipt["owned_test_root"] = str(owned)
        env = dict(os.environ, TEMP=scratch, TMP=scratch, TMPDIR=scratch,
                   SQLITE_TMPDIR=scratch, PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
                   CW_BASETEMP_FALLBACK_ROOT=str(owned / "short"),
                   CW_BASETEMP_DECISION_FILE=str(owned / "decisions.jsonl"))
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=short", "--timeout=180",
             "-p", "no:cacheprovider", "--basetemp", str(owned / "pytest"), *targets],
            cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=420,
        )
        (EVIDENCE / f"{phase}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        receipt["exit_code"] = result.returncode
        receipt["elapsed_seconds"] = round(time.monotonic() - start, 2)
        decisions = owned / "decisions.jsonl"
        receipt["temp_decisions"] = [json.loads(line) for line in
                                     decisions.read_text(encoding="utf-8").splitlines()] if decisions.exists() else []
    receipt["owned_test_root_restored_to_absent"] = not owned.exists()
    (EVIDENCE / f"{phase}-receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))
    print(result.stdout[-2500:])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
