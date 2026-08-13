"""WU-1.1: AST gate that forbids duplicate test_* definitions (F-030/F-031).

Python module loading lets a later ``def test_x`` silently override an
earlier one; pytest only collects the final binding, so duplicated test
bodies are collected once with the stronger/weaker variant picked by file
order — a silent collection gap that Ruff's F811 ignore used to hide.

This tool parses every ``tests/**/*.py`` file and reports any
``test_*`` function defined more than once at module or class scope.

Exit 0 = no duplicates; 1 = duplicates found (CI gate).
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def duplicates_in_file(path: Path) -> list[tuple[str, int, int]]:
    """Return [(name, first_line, second_line), ...] for duplicate test defs."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        print(f"SYNTAX ERROR {path}: {exc}", file=sys.stderr)
        return [("__syntax_error__", exc.lineno or 0, exc.lineno or 0)]
    found: list[tuple[str, int, int]] = []

    def visit(scope: ast.AST) -> None:
        # Each scope (module or class) tracks its own names: a test_create in
        # ClassA does not collide with a test_create in ClassB.
        seen: dict[str, int] = {}
        for node in ast.iter_child_nodes(scope):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    if node.name in seen:
                        found.append((node.name, seen[node.name], node.lineno))
                    else:
                        seen[node.name] = node.lineno
            elif isinstance(node, ast.ClassDef):
                visit(node)

    visit(tree)
    return found


def main() -> int:
    # FC-1205 (PORT-01): Windows pipes decode with the locale codepage (GBK
    # on Chinese systems) while the parent reads UTF-8 — paths containing
    # non-ASCII user names mojibake/crash the reader.  Force UTF-8 on the
    # child side (the fetch_filing.py pattern); the contract tests stay UTF-8.
    # FC-1205 (PORT-01): Windows pipes decode with the locale codepage (GBK
    # on Chinese systems) while the parent reads UTF-8 — paths containing
    # non-ASCII user names mojibake/crash the reader.  Force UTF-8 on the
    # child side (the fetch_filing.py pattern); the contract tests stay UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict")

    parser = argparse.ArgumentParser(description="Forbid duplicate test_* definitions")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=None,
        help="test files/dirs (default: tests)",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    targets = args.paths or [root / "tests"]
    files: list[Path] = []
    for target in targets:
        if target.is_dir():
            files.extend(sorted(target.rglob("test_*.py")))
        elif target.is_file():
            files.append(target)
    problems = 0
    for path in files:
        dupes = duplicates_in_file(path)
        for name, first, second in dupes:
            problems += 1
            print(f"DUPLICATE {path}:{second}: '{name}' redefines {path}:{first}")
    if problems:
        print(f"FAIL: {problems} duplicate test definition(s) — silent collection gap", file=sys.stderr)
        return 1
    print(f"OK: {len(files)} test file(s), no duplicate test_* definitions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
