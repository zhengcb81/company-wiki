"""Optional AST complexity report. Values are diagnostics, never release gates."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


def report(paths: list[Path]) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            score = 1
            for node in ast.walk(function):
                if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While,
                                     ast.ExceptHandler, ast.comprehension, ast.IfExp)):
                    score += 1
                elif isinstance(node, ast.BoolOp):
                    score += len(node.values) - 1
            entries.append({"path": path.as_posix(), "function": function.name,
                            "line": function.lineno, "score": score})
    return sorted(entries, key=lambda item: (-int(item["score"]), str(item["path"]),
                                            int(item["line"])))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Python files or directories")
    args = parser.parse_args()
    paths = sorted({file for path in args.paths
                    for file in (path.rglob("*.py") if path.is_dir() else [path])})
    print(json.dumps({"diagnostic_only": True, "functions": report(paths)},
                     ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
