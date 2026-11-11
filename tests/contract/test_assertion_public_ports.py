"""Source-fact and availability owners expose stable cross-module ports."""

from __future__ import annotations

import ast
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"
PRIVATE_OWNER_MODULES = {"assertion_service", "source_availability"}


def test_source_fact_consumers_do_not_import_private_owner_helpers():
    violations: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module is None:
                continue
            imported_owner = node.module.rsplit(".", 1)[-1]
            if imported_owner not in PRIVATE_OWNER_MODULES:
                continue
            for alias in node.names:
                if alias.name.startswith("_"):
                    violations.append(f"{path.relative_to(SOURCE_ROOT)}:{node.lineno}:{alias.name}")

    assert not violations, (
        "consumers must use source-fact/availability owner ports: "
        + ", ".join(violations)
    )
