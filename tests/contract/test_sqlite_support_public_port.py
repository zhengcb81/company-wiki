"""SQLite compatibility behavior is shared through one public infrastructure port."""

from __future__ import annotations

import ast
import sqlite3
from pathlib import Path

from company_wiki.source_catalog.sqlite_support import (
    configure_tolerant_sqlite_text_decoding,
)


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"


def test_tolerant_text_decoding_keeps_malformed_text_readable():
    connection = sqlite3.connect(":memory:")
    try:
        configure_tolerant_sqlite_text_decoding(connection)
        value = connection.execute("SELECT CAST(X'FFFE' AS TEXT)").fetchone()[0]
        assert value == "��"
    finally:
        connection.close()


def test_catalog_layers_do_not_import_the_private_store_decoder():
    imports: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module == "store" and any(
                alias.name == "_tolerate_undecodable_text" for alias in node.names
            ):
                imports.append(f"{path.relative_to(SOURCE_ROOT)}:{node.lineno}")

    assert not imports, (
        "SQLite layers must share the public sqlite_support port: "
        + ", ".join(imports)
    )
