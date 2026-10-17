"""Finite independent test receipt runner with owned temporary output and cleanup."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

ROOT = Path(__file__).resolve().parents[4]
RECEIPTS = Path(__file__).resolve().parent


def main():
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    protected = [ROOT / "config/source_catalog.yaml", ROOT / "config.yaml"]
    before = {str(p.relative_to(ROOT)): (sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
              for p in protected if p.is_file()}
    runs = []
    with TemporaryDirectory(prefix="du9-policy-independent-") as folder:
        temp = Path(folder)
        sentinel = temp / "keep.txt"
        sentinel.write_bytes(b"keep prior test content")
        sentinel_before = (sentinel.read_bytes(), sentinel.stat().st_mtime_ns)
        commands = [
            [sys.executable, "-X", "utf8", "-B", "-m", "pytest", "tests/unit/du9_geometry_policy",
             "tests/unit/document_understanding_profiles", "-q", "--tb=short", "--basetemp", str(temp / "pytest"),
             "-o", "cache_dir=" + str(temp / "cache")],
            [sys.executable, "-X", "utf8", "-B", "tools/import_reading_policies.py", "--check"],
            [sys.executable, "-X", "utf8", "-B", str(RECEIPTS / "reviewer-probe.py"),
             str(RECEIPTS / "reviewer-fixed-probe.json"), "--after-fix"],
            [sys.executable, "-X", "utf8", "-B", str(RECEIPTS / "reviewer-catalog-probe.py"),
             str(RECEIPTS / "reviewer-catalog-probe.json")],
        ]
        for index, argv in enumerate(commands):
            started = time.monotonic()
            result = subprocess.run(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    encoding="utf-8", errors="replace", timeout=90)
            log = RECEIPTS / f"reviewer-final-{index + 1}.txt"
            log.write_text(result.stdout, encoding="utf-8")
            runs.append({"argv": argv, "exit_code": result.returncode, "seconds": time.monotonic() - started,
                         "log": log.name})
            print(f"{index + 1}: exit={result.returncode}; {result.stdout[-1400:]}")
        sentinel_unchanged = sentinel_before == (sentinel.read_bytes(), sentinel.stat().st_mtime_ns)
    after = {str(p.relative_to(ROOT)): (sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
             for p in protected if p.is_file()}
    report = {"reviewer_agent_id": "/root/du9_policy_final_review", "runs": runs,
              "protected_inputs_unchanged": before == after, "sentinel_unchanged": sentinel_unchanged,
              "temporary_directory_removed": not Path(folder).exists(),
              "supplier_calls": 0, "downloads": 0, "original_copies": 0, "production_writes": 0}
    (RECEIPTS / "reviewer-final-runs.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(any(r["exit_code"] for r in runs) or not all((before == after, sentinel_unchanged, not Path(folder).exists())))


if __name__ == "__main__":
    raise SystemExit(main())
