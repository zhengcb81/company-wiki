"""Scanner diagnostics must invoke the public facade, not implementation helpers."""

from __future__ import annotations

import ast
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"


def test_parity_tools_use_only_the_scanner_facade():
    violations: list[str] = []
    for relative in ("shadow_parity.py", "trace_parity.py"):
        path = SOURCE_ROOT / relative
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module == "scanner" and any(
                alias.name.startswith("_") for alias in node.names
            ):
                violations.append(f"{relative}:{node.lineno}")

    assert not violations, (
        "parity and trace diagnostics must use scan_root_strategy: "
        + ", ".join(violations)
    )
