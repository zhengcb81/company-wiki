"""Collect or execute the owner CI suite and preserve same-version pytest evidence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from .ci_shards import parse_shard


def collect_tests(base: list[str], roots: list[str], output: Path) -> int:
    inventory = output / "collected.json"
    collection_log = output / "collection.log"
    with collection_log.open("wb") as log:
        collected = subprocess.run(
            [*base, "--collect-only", "--s6-evidence", str(inventory), *roots],
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    if collected.returncode:
        lines = collection_log.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[-30:]:
            print(line, file=sys.stderr)
        return collected.returncode
    count = len(json.loads(inventory.read_bytes())["node_ids"])
    print(f"Collected {count} applicable pytest nodes", flush=True)
    return 0


def execute_tests(base: list[str], roots: list[str], output: Path, shard: str | None) -> int:
    partition = [] if shard is None else ["-p", "tools.ci_shards", "--cwp-ci-shard", shard]
    result = subprocess.run(
        [*base, *partition, "--s6-evidence", str(output / "executed.json"),
         "--timeout=180", "--junitxml", str(output / "tests.xml"), *roots],
        stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default=os.environ.get("GITHUB_SHA"), required="GITHUB_SHA" not in os.environ)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=Path(".github/ci-test-policy.json"))
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--collect", action="store_true")
    operation.add_argument("--shard", metavar="SHARD/COUNT", type=parse_shard)
    args = parser.parse_args(argv)
    platform = {"win32": "windows", "darwin": "macos"}.get(sys.platform, sys.platform)
    selection = json.loads(args.policy.read_bytes())["platforms"][platform]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    base = [
        sys.executable, "-B", "-m", "pytest",
        "-p", "tools.anti_trick_gate_spec.pytest_probe",
        "--s6-revision", args.revision, "-m", selection["markexpr"],
        "--capture=sys", "-q", "--tb=short",
    ]
    if args.shard:
        index, count = args.shard
        return execute_tests(base, selection["roots"], output, f"{index}/{count}")
    result = collect_tests(base, selection["roots"], output)
    if result or args.collect:
        return result
    result = execute_tests(base, selection["roots"], output, None)
    if result:
        return result
    print(f"Check executed inventory for {platform} at {args.revision}", flush=True)
    return subprocess.run(
        [sys.executable, "-B", "-m", "tools.anti_trick_gate_spec", "coverage",
         "--revision", args.revision, "--policy", str(args.policy), "--platform", platform,
         str(output / "collected.json"), str(output / "executed.json")],
        stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
