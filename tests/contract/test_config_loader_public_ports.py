"""Versioned catalog loaders consume public config-owner contracts."""

from __future__ import annotations

import ast
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"


def test_policy_2x_uses_public_config_contracts_only():
    path = SOURCE_ROOT / "policy_2x.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    private_imports = [
        f"line {node.lineno}: config.{alias.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "config"
        for alias in node.names
        if alias.name.startswith("_")
    ]

    assert not private_imports, (
        "policy_2x must depend on the config owner's public parsing contract:\n"
        + "\n".join(private_imports)
    )


def test_config_owner_exports_version_neutral_root_parsing_ports():
    path = SOURCE_ROOT / "config.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    public_functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }

    assert {
        "mapping_from_config",
        "expand_config_path",
        "require_boolean_root_fields",
        "unresolved_path_variables",
        "route_spec_from_config",
    } <= public_functions
