"""Filesystem discovery and sidecar parsing have explicit owner modules."""

from __future__ import annotations

import ast
from pathlib import Path

from company_wiki.source_catalog.acquisition_sidecar import (
    ACQUISITION_SIDECAR_SUFFIX,
    read_acquisition_sidecar,
)
from company_wiki.source_catalog.filesystem_discovery import walk_document_files
from company_wiki.source_catalog.source_location import relative_source_path


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"


def test_walk_document_files_owns_shared_skip_policy(tmp_path):
    root = tmp_path / "raw"
    (root / "reports").mkdir(parents=True)
    (root / ".git").mkdir()
    (root / "reports" / "annual.pdf").write_bytes(b"pdf")
    (root / "reports" / "notes.py").write_text("text", encoding="utf-8")
    (root / ".git" / "ignored.pdf").write_bytes(b"ignored")

    assert list(walk_document_files(root)) == [root / "reports" / "annual.pdf"]


def test_relative_source_path_uses_one_normalized_location_contract(tmp_path):
    root = tmp_path / "raw"
    path = root / "reports" / "Å.pdf"

    assert relative_source_path(path, root) == "reports/Å.pdf"


def test_acquisition_sidecar_reader_owns_suffix_and_malformed_value_handling(tmp_path):
    sidecar = tmp_path / f"report{ACQUISITION_SIDECAR_SUFFIX}"
    sidecar.write_text('{"provider":"example"}', encoding="utf-8")
    assert read_acquisition_sidecar(sidecar) == {"provider": "example"}

    sidecar.write_text("not json", encoding="utf-8")
    assert read_acquisition_sidecar(sidecar) == {"meta_parse_error": True}


def test_scanner_and_adapters_do_not_import_private_common_helpers():
    imports: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module == "common" and any(
                alias.name.startswith("_") for alias in node.names
            ):
                imports.append(f"{path.relative_to(SOURCE_ROOT)}:{node.lineno}")

    assert not imports, "private adapter-common imports remain: " + ", ".join(imports)
