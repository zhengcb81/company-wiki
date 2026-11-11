"""Acquisition workers share the lock owner through a public port."""

from __future__ import annotations

import ast
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"


def test_catalog_consumers_do_not_import_private_acquisition_mutex():
    violations: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        if path.name == "lock.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module == "lock" and any(
                alias.name == "_acquisition_mutex" for alias in node.names
            ):
                violations.append(f"{path.relative_to(SOURCE_ROOT)}:{node.lineno}")

    assert not violations, (
        "acquisition components must call the public lock owner: "
        + ", ".join(violations)
    )


def test_lock_owner_lists_acquisition_mutex_in_public_exports():
    path = SOURCE_ROOT / "lock.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    all_assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets)
    )
    exported = set(ast.literal_eval(all_assignment.value))

    assert "acquisition_mutex" in exported
