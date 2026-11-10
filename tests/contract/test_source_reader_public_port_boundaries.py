"""The source reader and browse API must cross storage boundaries by ports."""

from __future__ import annotations

import ast
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "company_wiki"


def _calls_on_dotted_owner(tree: ast.AST, owner: tuple[str, ...]) -> list[ast.Call]:
    def dotted(node: ast.AST) -> tuple[str, ...] | None:
        if isinstance(node, ast.Name):
            return (node.id,)
        if isinstance(node, ast.Attribute):
            parent = dotted(node.value)
            return (*parent, node.attr) if parent else None
        return None

    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and dotted(node.func.value) == owner
    ]


def _read_tree(relative: str) -> ast.Module:
    path = SOURCE_ROOT / relative
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_source_reader_uses_only_public_catalog_methods():
    tree = _read_tree("source_catalog/source_reader.py")
    calls = _calls_on_dotted_owner(tree, ("self", "catalog"))

    assert not [
        f"line {call.lineno}: {ast.unparse(call.func)}"
        for call in calls
        if isinstance(call.func, ast.Attribute)
        and call.func.attr.startswith("_")
    ]


def test_document_browser_consumes_typed_catalog_queries_not_sql_storage():
    tree = _read_tree("source_catalog/public_document_browser.py")
    calls = _calls_on_dotted_owner(tree, ("self", "catalog", "reader"))

    assert not [
        f"line {call.lineno}: {ast.unparse(call.func)}"
        for call in calls
        if isinstance(call.func, ast.Attribute)
        and call.func.attr in {"fetchone", "fetchall"}
    ]


def test_source_catalog_publishes_owner_ports_for_reader_and_browser():
    service = _read_tree("source_catalog/service.py")
    public_methods = {
        node.name
        for node in service.body
        if isinstance(node, ast.ClassDef) and node.name == "SourceCatalog"
        for node in node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "source_location_candidates" in public_methods
    assert "browse_entity_records" in public_methods
    assert "browse_document_records" in public_methods
    assert "iter_original_version_identities" in public_methods
