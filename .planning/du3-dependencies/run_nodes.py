"""Reproducible A/B/C node runner for the DU3-DEPENDENCIES lane.

Runs the three big nodes plus the full owned suite, records command / exit code /
elapsed seconds / summary, and writes the small receipts the handoff points at.

    python .planning/du3-dependencies/run_nodes.py

Writes nothing outside ``.planning/du3-dependencies/evidence/``. It does not run the
selector, the registry or any Store; the tests it launches are pure unit tests plus one
read-only replay against the installed reading catalog.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

WORKTREE = Path(__file__).resolve().parents[2]
EVIDENCE = WORKTREE / ".planning" / "du3-dependencies" / "evidence"
OWNED = Path("tests/unit/document_understanding_decision_dependencies")

NODES = [
    (
        "A",
        "TDD counter-examples: decision-dependency mutation matrix + honesty",
        [
            f"{OWNED}/test_a_completeness_honesty.py",
            f"{OWNED}/test_a_mutation_matrix.py",
        ],
    ),
    (
        "B",
        "engineering: schema, finite JSON, cross-process digest, limits, 100-source size",
        [f"{OWNED}/test_b_engineering.py"],
    ),
    (
        "C",
        "independent read-only catalog snapshot replay + receipt",
        [f"{OWNED}/test_c_catalog_replay.py"],
    ),
    ("ALL", "the whole owned lane", [str(OWNED)]),
]


def run(name: str, purpose: str, targets: list[str]) -> dict:
    command = [sys.executable, "-m", "pytest", *targets, "-q", "--no-header", "-p", "no:cacheprovider"]
    started = time.perf_counter()
    completed = subprocess.run(
        command, cwd=WORKTREE, capture_output=True, text=True, encoding="utf-8",
        env={
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
            "DU3_DEP_SIZE_REPORT": str(EVIDENCE / "b_size_report.json"),
            "DU3_DEP_RECEIPT": str(EVIDENCE / "c_replay_receipt.json"),
        },
        check=False,
    )
    elapsed = time.perf_counter() - started
    tail = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    summary = next((line for line in reversed(tail) if "passed" in line or "failed" in line or "error" in line), "")
    print(f"{name} | exit={completed.returncode} | {elapsed:.2f}s | {summary}")
    return {
        "node": name,
        "purpose": purpose,
        "command": " ".join(command[1:]),
        "exit_code": completed.returncode,
        "seconds": round(elapsed, 3),
        "summary": summary,
    }


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    results = [run(*node) for node in NODES]
    payload = {
        "receipt_schema": "du3-dependencies-nodes/1",
        "lane": "dependencies",
        "base_sha": "195aba20b0aecc2d661d7d04c5ba72f982bc02d0",
        "branch": "codex/du3-dependencies-20261014",
        "worktree": str(WORKTREE),
        "python": sys.version.split()[0],
        "nodes": results,
    }
    out = EVIDENCE / "nodes.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out}")
    return 0 if all(item["exit_code"] == 0 for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
