"""ROOT acceptance harness for the document-understanding plan.

Runs the whole verification in one place and prints a machine-readable summary.
It deliberately separates three things that must not be conflated:

* **static/offline** checks that always run (lane unit suites, ruff);
* **real-data** checks that need the owner's originals and skip honestly when
  they are absent;
* **network/model** checks, which this harness never runs, so a green result
  here can never be mistaken for "the paid path was validated".

Usage:
    python -X utf8 .planning/du-root/acceptance.py [--bindings <json>]

Exit code is 0 only when every check that actually ran passed.  A skipped
real-data check is reported as ``skipped``, never as ``passed``.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

LANE_SUITES = (
    ("profiles", "tests/unit/document_understanding_profiles"),
    ("structure", "tests/unit/document_understanding_structure"),
    ("root", "tests/unit/document_understanding_root"),
)

BENCH_SUITE = "tools/document_understanding_benchmark/tests"

RUFF_TARGETS = (
    "src/company_wiki/document_understanding",
    "tests/unit/document_understanding_root",
)


def _run(args: list[str], *, env: dict[str, str]) -> tuple[int, str, float]:
    start = time.perf_counter()
    completed = subprocess.run(
        args,
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.perf_counter() - start
    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode, output, elapsed


def _tail(text: str, lines: int = 3) -> str:
    stripped = [line for line in text.strip().splitlines() if line.strip()]
    return " | ".join(stripped[-lines:]) if stripped else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bindings", default="")
    args = parser.parse_args()

    env = dict(os.environ)
    src = str(REPO / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    if args.bindings:
        env["DU_ROOT_BINDINGS"] = args.bindings

    results: list[dict] = []

    for lane, path in LANE_SUITES:
        if not (REPO / path).exists():
            results.append(
                {"check": f"pytest:{lane}", "status": "absent", "detail": f"{path} not present"}
            )
            continue
        code, output, elapsed = _run(
            [sys.executable, "-X", "utf8", "-m", "pytest", path, "-q", "-p", "no:randomly"],
            env=env,
        )
        results.append(
            {
                "check": f"pytest:{lane}",
                "status": "passed" if code == 0 else "failed",
                "exit_code": code,
                "seconds": round(elapsed, 2),
                "detail": _tail(output),
            }
        )

    if (REPO / BENCH_SUITE).exists():
        code, output, elapsed = _run(
            [sys.executable, "-X", "utf8", "-m", "pytest", BENCH_SUITE, "-q", "-p", "no:randomly"],
            env=env,
        )
        results.append(
            {
                "check": "pytest:benchmark",
                "status": "passed" if code == 0 else "failed",
                "exit_code": code,
                "seconds": round(elapsed, 2),
                "detail": _tail(output),
            }
        )

    # Real-data checks are run separately so a skip is visible as a skip.
    root_suite = REPO / "tests" / "unit" / "document_understanding_root"
    if root_suite.exists():
        code, output, elapsed = _run(
            [
                sys.executable, "-X", "utf8", "-m", "pytest",
                "tests/unit/document_understanding_root", "-q", "-p", "no:randomly",
                "-m", "real_data", "-rs",
            ],
            env=env,
        )
        detail = _tail(output, 2)
        skipped = "skipped" in detail and "passed" not in detail
        results.append(
            {
                "check": "pytest:real_data",
                "status": "skipped" if skipped else ("passed" if code == 0 else "failed"),
                "exit_code": code,
                "seconds": round(elapsed, 2),
                "detail": detail,
            }
        )

    code, output, elapsed = _run(
        [sys.executable, "-X", "utf8", "-m", "ruff", "check", *RUFF_TARGETS], env=env
    )
    results.append(
        {
            "check": "ruff",
            "status": "passed" if code == 0 else "failed",
            "exit_code": code,
            "seconds": round(elapsed, 2),
            "detail": _tail(output, 1),
        }
    )

    results.append(
        {
            "check": "paid_path",
            "status": "not_run",
            "detail": (
                "this harness never calls a model or the network; a green result "
                "here is not evidence about the paid summary path"
            ),
        }
    )

    failed = [item for item in results if item["status"] == "failed"]
    summary = {
        "schema_version": "du-acceptance/1",
        "repo": str(REPO),
        "checks": results,
        "passed": sum(1 for item in results if item["status"] == "passed"),
        "skipped": sum(1 for item in results if item["status"] == "skipped"),
        "failed": len(failed),
        "not_run": sum(1 for item in results if item["status"] == "not_run"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
