"""Collect or execute the owner CI suite and preserve same-version pytest evidence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from .ci_selection import classify, parse_shard, paths_for
from .pytest_scratch import PARENT_BASETEMP_ENV, short_scratch_root


_WINDOWLESS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def collect_tests(base: list[str], roots: list[str], output: Path, policy: dict) -> int:
    inventory = output / "collected.json"
    membership = output / "membership.json"
    collection_log = output / "collection.log"
    with collection_log.open("wb") as log:
        collected = subprocess.run(
            [*base, "--collect-only", "-p", "tools.ci_selection",
             "--cwp-ci-membership", str(membership), "--s6-evidence", str(inventory), *roots],
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, creationflags=_WINDOWLESS,
        )
    if collected.returncode:
        lines = collection_log.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[-30:]:
            print(line, file=sys.stderr)
        return collected.returncode
    distribution = classify(json.loads(inventory.read_bytes()), json.loads(membership.read_bytes()), policy)
    (output / "distribution.json").write_text(json.dumps(distribution, ensure_ascii=True), encoding="utf-8")
    print(f"Collected {distribution['applicable']} applicable and {distribution['deselected']} deferred pytest nodes",
          flush=True)
    return 0


def execute_tests(base: list[str], paths: list[str], output: Path) -> int:
    root = short_scratch_root(Path(__file__).resolve().parents[1])
    with TemporaryDirectory(prefix=".cwci-", dir=root) as scratch:
        basetemp = str(Path(scratch) / "t")
        result = subprocess.run(
            [*base, "--basetemp", basetemp, "--s6-evidence", str(output / "executed.json"),
             "--timeout=180", "--junitxml", str(output / "tests.xml"), *paths],
            env={**os.environ, PARENT_BASETEMP_ENV: basetemp},
            stdin=subprocess.DEVNULL, creationflags=_WINDOWLESS,
        )
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default=os.environ.get("GITHUB_SHA"), required="GITHUB_SHA" not in os.environ)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=Path(".github/ci-test-policy.json"))
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--collect", action="store_true")
    operation.add_argument("--inventory", type=Path, help="Canonical distribution JSON from the inventory job")
    parser.add_argument("--suite", default="native")
    parser.add_argument("--shard", metavar="SHARD/COUNT", type=parse_shard, default=(0, 1))
    args = parser.parse_args(argv)
    platform = {"win32": "windows", "darwin": "macos"}.get(sys.platform, sys.platform)
    policy = json.loads(args.policy.read_bytes())
    selection = policy["platforms"][platform]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    base = [
        sys.executable, "-B", "-m", "pytest",
        "-p", "tools.anti_trick_gate_spec.pytest_probe",
        "--s6-revision", args.revision, "--capture=sys", "-q", "--tb=short",
    ]
    markexpr = selection["markexpr"]
    if args.inventory:
        suites = policy.get("suites", {})
        suite_expr = "not (" + " or ".join(suites.values()) + ")" if suites else ""
        if args.suite != "native":
            suite_expr = suites[args.suite]
        combined = " and ".join(f"({expr})" for expr in (markexpr, suite_expr) if expr)
        files = paths_for(json.loads(args.inventory.read_bytes()), args.suite, args.shard, args.revision, platform)
        return execute_tests([*base, "-m", combined], files, output)
    base += ["-m", markexpr]
    result = collect_tests(base, selection["roots"], output, policy)
    if result or args.collect:
        return result
    result = execute_tests(base, selection["roots"], output)
    if result:
        return result
    return subprocess.run(
        [sys.executable, "-B", "-m", "tools.anti_trick_gate_spec", "coverage",
         "--revision", args.revision, "--policy", str(args.policy), "--platform", platform,
         str(output / "collected.json"), str(output / "executed.json")],
        stdin=subprocess.DEVNULL, creationflags=_WINDOWLESS,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
