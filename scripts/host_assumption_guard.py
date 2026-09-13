"""Host-assumption guard (FC-1307-a): catch the three defect classes that passed
every local hook and failed only on CI.

History (phase-B run 2026-09-11, findings F-B01-9): four CI failures got through
the pre-commit hook and the pre-push gate.  One was a test CLASS the local gate
never runs (a taxonomy registry check); the other three were host assumptions
that are GREEN on the machine that runs the hook:

  1. an absolute host path baked into a test (``C:\\Windows\\win.ini``) - on
     Linux that is a relative name, so the assertion inverts;
  2. a host CAPABILITY used without a skip (symlink creation) - the case skips on
     Windows and really runs on Linux;
  3. a machine-scoped value frozen as a constant (a policy-export payload hash
     that embeds each root's absolute path) - it can only be asserted on the
     machine that produced it.

The guard is AST-based on purpose: comments and docstrings may DISCUSS such
paths (the fix notes do), so only runtime string literals count.

Usage:
    python scripts/host_assumption_guard.py            # report and exit 1 on violations
    python scripts/host_assumption_guard.py --report   # report only (exit 0)
    python scripts/host_assumption_guard.py --roots tests src
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DEFAULT_ROOTS = ("tests", "src")
REGISTRY = REPO / "tests" / "contract" / "host_assumption_allowlist.json"
BASELINE = REPO / "tests" / "contract" / "host_assumption_baseline.json"

WIN_ABS = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\[^\\/]|\\\\\?\\|\\\\\.\\)")
POSIX_ABS = re.compile(r"^/(?:etc|tmp|usr|var|home|opt|root|proc|sys|dev|mnt|media)(?:/|$)")
URL = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CAPABILITY_CALLS = ("symlink_to", "os.symlink", "os.link", "os.mkfifo")
SKIP_MARKERS = ("pytest.skip", "skipif", "pytest.importorskip")

RULE_PATHS = "host-absolute-path"
RULE_CAPABILITY = "host-capability-without-skip"
RULE_FROZEN_HASH = "unregistered-frozen-hash"


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """Line numbers of docstrings (they may discuss such paths)."""
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                value = body[0].value
                if isinstance(value.value, str):
                    for lineno in range(value.lineno, (value.end_lineno or value.lineno) + 1):
                        lines.add(lineno)
    return lines


def _string_literals(tree: ast.AST, doc_lines: set[int]) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.lineno in doc_lines:
                continue
            out.append((node.value, node.lineno))
        elif isinstance(node, ast.JoinedStr):
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    if part.lineno in doc_lines:
                        continue
                    out.append((part.value, part.lineno))
    return out


def _calls(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                names.add(func.attr)
                if isinstance(func.value, ast.Name):
                    names.add(f"{func.value.id}.{func.attr}")
            elif isinstance(func, ast.Name):
                names.add(func.id)
    return names


def scan_file(path: Path) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:  # a file that does not parse is not this gate's business
        return [{"rule": "syntax-error", "file": str(path), "line": exc.lineno or 0, "value": str(exc)}]
    doc_lines = _docstring_nodes(tree)
    violations: list[dict[str, Any]] = []
    in_tests = "tests" in path.parts
    for value, lineno in _string_literals(tree, doc_lines):
        stripped = value.strip()
        if not stripped or URL.match(stripped):
            continue
        # Rule A is scoped to TESTS on purpose: product code legitimately detects
        # the host (lock.py reads /proc/stat, startup.py probes C:/Windows), and a
        # path literal there is a deliberate platform branch.  In a test it is
        # almost always a portability bug - the class that failed CI.
        if in_tests and (WIN_ABS.match(stripped) or POSIX_ABS.match(stripped)):
            violations.append({"rule": RULE_PATHS, "file": str(path), "line": lineno,
                               "value": stripped[:80]})
        if HEX64.match(stripped):
            violations.append({"rule": RULE_FROZEN_HASH, "file": str(path), "line": lineno,
                               "value": stripped})
    if in_tests:
        calls = _calls(tree)
        used = sorted(name for name in CAPABILITY_CALLS if name.split(".")[-1] in
                      {c.split(".")[-1] for c in calls})
        if used:
            text = path.read_text(encoding="utf-8")
            if not any(marker in text for marker in SKIP_MARKERS):
                violations.append({"rule": RULE_CAPABILITY, "file": str(path), "line": 0,
                                   "value": ", ".join(used)})
    return violations


def load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", nargs="*", default=list(DEFAULT_ROOTS))
    parser.add_argument("--report", action="store_true", help="report only, never fail")
    parser.add_argument("--write-baseline", action="store_true",
                        help="record the CURRENT violations as the ratchet baseline "
                             "(pre-existing offenders only; new ones still fail)")
    args = parser.parse_args(argv)

    registry = load_json(REGISTRY, {"registered_hashes": {}})
    registered = registry.get("registered_hashes", {})
    baseline = set(load_json(BASELINE, {"baseline": []}).get("baseline", []))

    violations: list[dict[str, Any]] = []
    for root in args.roots:
        base = REPO / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            violations.extend(scan_file(path))

    def key(item: dict[str, Any]) -> str:
        rel = Path(item["file"]).resolve().relative_to(REPO).as_posix()
        return f"{item['rule']}|{rel}|{item['value'][:40]}"

    if args.write_baseline:
        recorded = sorted(
            {key(item) for item in violations if item["rule"] in (RULE_PATHS, RULE_CAPABILITY)}
            | baseline
        )
        BASELINE.write_text(
            json.dumps(
                {
                    "note": ("Ratchet baseline for the host-assumption guard.  These entries are "
                             "PRE-EXISTING: absolute-path literals in tests that are deliberate "
                             "inputs (a path that must be rejected) and capability uses that already "
                             "skip.  The gate fails on anything NEW, so a new absolute path or an "
                             "un-skipped capability use must be fixed rather than silently added."),
                    "baseline": recorded,
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {BASELINE.relative_to(REPO).as_posix()} with {len(recorded)} entries")
        return 0

    new: list[dict[str, Any]] = []
    for item in violations:
        if item["rule"] == RULE_PATHS and key(item) in baseline:
            continue  # recorded pre-existing offender (ratchet: only NEW ones fail)
        if item["rule"] == RULE_CAPABILITY and key(item) in baseline:
            continue
        if item["rule"] == RULE_FROZEN_HASH:
            digest = item["value"]
            if digest in registered:
                continue
            if key(item) in baseline:
                continue
        new.append(item)

    for item in new:
        rel = Path(item["file"]).resolve().relative_to(REPO).as_posix()
        print(f"VIOLATION {item['rule']}: {rel}:{item['line']}  {item['value']}")
    print(f"scanned roots={args.roots}; violations={len(violations)}; "
          f"new(not baselined/registered)={len(new)}; "
          f"baseline={len(baseline)}; registered_hashes={len(registered)}")
    if new:
        print("\nFix the assertion to be host-neutral (tmp_path.anchor, pytest.skip on the "
              "capability, or a platform-independent property).  If a frozen digest is "
              "genuinely host-independent, register it with a rationale in "
              f"{REGISTRY.relative_to(REPO).as_posix()}.")
    if args.report:
        return 0
    return 1 if new else 0


if __name__ == "__main__":
    raise SystemExit(main())
