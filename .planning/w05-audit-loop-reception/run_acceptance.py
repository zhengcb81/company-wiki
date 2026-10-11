"""Finite ROOT reception of W05's frozen branch; never alters its code."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
DELIVERY = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop")
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else DELIVERY
assert SOURCE.resolve() in (DELIVERY.resolve(), Path("C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop-root").resolve())
PACKAGE = DELIVERY / "docs/handoffs/w05-audit-loop"
OUT_PARENT = PROJECT / "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-audit-loop-acceptance"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: object) -> None:
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode())


def main() -> int:
    attempt = OUT_PARENT / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    attempt.mkdir(parents=True, exist_ok=False)
    handoff = json.loads((PACKAGE / "handoff.json").read_text(encoding="utf-8"))
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    checks = []
    for row in manifest["files"]:
        path = (PACKAGE / row["path"]).resolve(strict=True)
        if not path.is_relative_to(PACKAGE.resolve()):
            raise ValueError("manifest escaped package")
        actual = {"sha256": digest(path), "bytes": path.stat().st_size}
        checks.append({"kind": "handoff_manifest", "path": row["path"],
                       "expected": row, "actual": actual,
                       "pass": row["sha256"] == actual["sha256"] and row["bytes"] == actual["bytes"]})
    for row in handoff["changed_files"]:
        path = (DELIVERY / row["path"]).resolve(strict=True)
        if not path.is_relative_to(DELIVERY.resolve()):
            raise ValueError("changed file escaped source")
        checks.append({"kind": "changed_file", "path": row["path"],
                       "expected_sha256": row["sha256"], "actual_sha256": digest(path),
                       "pass": row["sha256"] == digest(path)})
    frozen = {row["path"]: digest(SOURCE / row["path"]) for row in handoff["changed_files"]}
    for path in (SOURCE / "skills/revenue-forecast-audit").rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            frozen[path.relative_to(SOURCE).as_posix()] = digest(path)
    regression = SOURCE / "tests/test_w05_progress_closure.py"
    if regression.exists():
        frozen[regression.relative_to(SOURCE).as_posix()] = digest(regression)
    write_json(attempt / "source-freeze.json", frozen)
    write_json(attempt / "intake.json", {"checks": checks, "status": "PASS" if all(row["pass"] for row in checks) else "FAIL"})
    commands = []

    def run(name: str, argv: list[str], timeout: int) -> int:
        started = time.monotonic()
        timed_out = False
        with (attempt / (name + ".log")).open("wb") as log:
            process = subprocess.Popen(argv, cwd=SOURCE, stdout=log, stderr=subprocess.STDOUT)
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                code = process.wait(timeout=10)
                timed_out = True
        receipt = {"argv": argv, "cwd": str(SOURCE), "exit_code": code,
                   "timed_out": timed_out,
                   "elapsed_seconds": round(time.monotonic() - started, 3),
                   "log_sha256": digest(attempt / (name + ".log"))}
        write_json(attempt / (name + ".json"), receipt)
        commands.append(receipt)
        print(json.dumps({"name": name, **receipt}), flush=True)
        return 124 if timed_out else code

    unit_exit = run("unit-full", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"], 150)
    scratch = attempt / "scratch"
    if scratch.exists() or not scratch.resolve().is_relative_to(attempt.resolve()):
        raise ValueError("scratch must be new and owned by this attempt")
    e2e_dir = attempt / "e2e"
    e2e_dir.mkdir()
    e2e_exit = run("offline-e2e", [sys.executable, "-B", "tools/run_pool_progress_e2e.py", "--owned-root", str(scratch), "--receipt", str(e2e_dir / "receipt.json")], 90)
    restored_to_absent = False
    if e2e_exit == 0:
        result = json.loads((e2e_dir / "receipt.json").read_text(encoding="utf-8"))
        if not result["sentinel"]["unchanged"]:
            raise ValueError("E2E sentinel changed")
        expected_files = {"sentinel/keep-a.txt", "sentinel/keep-b.bin"}
        actual_files = {p.relative_to(scratch).as_posix() for p in scratch.rglob("*") if p.is_file()}
        actual_dirs = {p.relative_to(scratch).as_posix() for p in scratch.rglob("*") if p.is_dir()}
        if actual_files != expected_files or actual_dirs != {"sentinel"}:
            raise ValueError("unexpected scratch leftovers; preserve for diagnosis")
        for relative in sorted(expected_files):
            target = (scratch / relative).resolve(strict=True)
            if not target.is_relative_to(scratch.resolve()):
                raise ValueError("cleanup target escaped scratch")
            target.unlink()
        (scratch / "sentinel").rmdir()
        scratch.rmdir()
        restored_to_absent = not scratch.exists()
    after = {relative: digest(SOURCE / relative) for relative in frozen}
    final = {"schema_version": "w05-root-reception/1", "source": str(SOURCE),
             "feature_commit": handoff["head_commit"], "intake_pass": all(row["pass"] for row in checks),
             "commands": commands, "source_sha_before": frozen, "source_sha_after": after,
             "source_unchanged": frozen == after, "scratch_initial": "absent", "scratch_restored": restored_to_absent,
             "provider_calls": 0, "llm_calls": 0, "new_cost_usd": "0", "quality_scope": "offline engineering reception only",
             "independent_review": "PENDING", "status": "PASS" if unit_exit == e2e_exit == 0 and all(row["pass"] for row in checks) and frozen == after and restored_to_absent else "FAIL"}
    write_json(attempt / "receipt.json", final)
    print(json.dumps({"attempt": str(attempt), "status": final["status"]}), flush=True)
    return 0 if final["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
