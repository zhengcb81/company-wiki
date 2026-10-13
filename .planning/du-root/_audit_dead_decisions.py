"""Audit: is every exported decision actually consumed by a non-test caller?

The defect this looks for is the one found by hand: a decision that is implemented,
documented, exported and unit-tested, while the code paths that matter never consult it. It
looks complete from the outside and does nothing in practice.

This script lists each public symbol of the document-understanding layer and reports whether
it is referenced anywhere in ``src`` outside the module that defines it.

Run: python -X utf8 .planning/du-root/_audit_dead_decisions.py
"""

from __future__ import annotations

import ast
import pathlib
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
PACKAGE = SRC / "company_wiki" / "document_understanding"


def module_symbols(path: pathlib.Path) -> list[str]:
    """Top-level functions defined in a module, plus __all__ entries."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                names.append(node.name)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for element in node.value.elts:
                            if isinstance(element, ast.Constant) and isinstance(
                                element.value, str
                            ):
                                names.append(element.value)
    return sorted(set(names))


def all_references() -> dict[str, set[str]]:
    """Map symbol name -> set of src files that reference it.

    Import statements must be counted, or an exported symbol looks unused simply because the
    only thing that names it is a ``from ... import ...`` line. That false positive would
    hide exactly the defect this audit looks for.
    """
    references: dict[str, set[str]] = defaultdict(set)
    for path in SRC.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                references[node.id].add(str(path))
            elif isinstance(node, ast.Attribute):
                references[node.attr].add(str(path))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    references[alias.name].add(str(path))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    references[alias.name.split(".")[-1]].add(str(path))
    return references


def main() -> int:
    references = all_references()
    print(f"{'symbol':34} {'defined in':30} {'src refs outside module':>8}")
    print("-" * 82)
    unconsumed: list[tuple[str, str]] = []

    for path in sorted(PACKAGE.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        rel = path.relative_to(PACKAGE).as_posix()
        for name in module_symbols(path):
            others = {
                ref
                for ref in references.get(name, set())
                if pathlib.Path(ref).resolve() != path.resolve()
            }
            count = len(others)
            print(f"{name:34} {rel:30} {count:>8}")
            if count == 0:
                unconsumed.append((name, rel))

    print("-" * 82)
    if unconsumed:
        print(f"UNCONSUMED ({len(unconsumed)}) - declared but never referenced outside its module:")
        for name, rel in unconsumed:
            print(f"   {name}  ({rel})")
    else:
        print("every public symbol is referenced outside its own module")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
