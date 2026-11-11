"""Consumers use the parser owner's stable result and runtime interface."""

from __future__ import annotations

import ast
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"


def test_processed_document_uses_public_normalizer_ports_only():
    path = SOURCE_ROOT / "processed_document.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    private_imports = [
        f"line {node.lineno}: normalizer.{alias.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "normalizer"
        for alias in node.names
        if alias.name.startswith("_")
    ]

    assert not private_imports, (
        "processed_document must use stable parser-owner ports:\n"
        + "\n".join(private_imports)
    )


def test_normalizer_exports_its_cross_lane_contracts():
    path = SOURCE_ROOT / "normalizer.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    public_symbols = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    public_symbols.update(
        target.id
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (
            node.targets if isinstance(node, ast.Assign) else [node.target]
        )
        if isinstance(target, ast.Name) and not target.id.startswith("_")
    )
    assert {
        "NormalizedDocument",
        "escape_table_cell",
        "normalize_source_file",
        "run_parser_isolated",
        "unsupported_result",
    } <= public_symbols
    all_assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets)
    )
    exported = ast.literal_eval(all_assignment.value)
    assert {
        "NormalizedDocument",
        "escape_table_cell",
        "normalize_source_file",
        "run_parser_isolated",
        "unsupported_result",
    } <= set(exported)
