"""Replay only the corrected E2E fixture and restore every owned scratch."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
OUT = PROJECT / "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-audit-loop-acceptance"
SOURCE = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop-root")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode())


def cleanup(root):
    assert root.resolve().is_relative_to(OUT.resolve()) and root.name == "scratch"
    if not root.exists():
        return {"initial": "absent", "restored": True, "removed": 0}
    assert not root.is_symlink()
    files, dirs = [], []
    for path in root.rglob("*"):
        assert not path.is_symlink() and path.resolve().is_relative_to(root.resolve())
        if path.is_file():
            files.append({"relative": path.relative_to(root).as_posix(), "sha256": sha(path), "bytes": path.stat().st_size})
        elif path.is_dir():
            dirs.append(path)
    # Failure-state facts are retained; generated observations are not copied wholesale.
    state = root / "campaign/state.json"
    if state.exists():
        write(root.parent / "failed-state-summary.json", {"sha256": sha(state), "state": json.loads(state.read_bytes())})
    write(root.parent / "scratch-cleanup-manifest.json", files)
    for row in files:
        path = root / row["relative"]
        assert sha(path) == row["sha256"]
        path.unlink()
    for path in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        path.rmdir()
    root.rmdir()
    return {"initial": "absent", "restored": not root.exists(), "removed": len(files)}


def main():
    previous = OUT / "20261011T101209544274Z"
    write(previous / "failure-scratch-restoration.json", cleanup(previous / "scratch"))
    script = SOURCE / "tools/run_pool_progress_e2e.py"
    text = script.read_text(encoding="utf-8")
    old = 'attempt="initial", findings=[]),\n                      expect="select_next_company")'
    new = 'attempt="initial", findings=[],\n                                          refs=[f"synthetic/{run_id}/expert/diagnosis.json"]),\n                      expect="select_next_company")'
    assert text.count(old) == 1
    script.write_bytes(text.replace(old, new).encode())
    attempt = OUT / ("final-e2e-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    attempt.mkdir()
    scratch = attempt / "scratch"
    before = sha(SOURCE / "skills/revenue-forecast-audit/scripts/pool_progress.py")
    command = [sys.executable, "-B", str(script), "--owned-root", str(scratch), "--receipt", str(attempt / "receipt.json")]
    code = None
    try:
        with (attempt / "run.log").open("wb") as log:
            done = subprocess.run(command, cwd=SOURCE, stdout=log, stderr=subprocess.STDOUT, timeout=90)
            code = done.returncode
    finally:
        restored = cleanup(scratch)
        write(attempt / "root-receipt.json", {"command": command, "exit_code": code, "producer_sha_before": before,
              "producer_sha_after": sha(SOURCE / "skills/revenue-forecast-audit/scripts/pool_progress.py"),
              "e2e_script_sha": sha(script), "cleanup": restored, "http_calls": 0, "llm_calls": 0,
              "status": "PASS" if code == 0 and restored["restored"] else "FAIL"})
    print(json.dumps({"attempt": str(attempt), "exit_code": code, "cleanup": restored}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
