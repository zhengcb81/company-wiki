"""Keep narrative persistence below automation orchestration."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STORE_MODULE = (
    ROOT
    / "src"
    / "company_wiki"
    / "source_catalog"
    / "narrative_artifact_store.py"
)


def test_narrative_catalog_store_does_not_depend_on_automation_types() -> None:
    tree = ast.parse(STORE_MODULE.read_text(encoding="utf-8"))
    forbidden: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            forbidden.extend(
                alias.name
                for alias in node.names
                if alias.name.startswith("company_wiki.automation")
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("company_wiki.automation"):
                forbidden.append(module)
            if module.startswith(".automation"):
                forbidden.append(module)

    assert forbidden == []
