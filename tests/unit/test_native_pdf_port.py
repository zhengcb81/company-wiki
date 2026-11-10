import ast
from pathlib import Path

import pymupdf
import pytest

from company_wiki.parser_adapters import (
    NativePdfError,
    read_native_pdf_prefix,
    validate_native_pdf,
)


def test_native_pdf_port_preserves_page_order_and_checks_cancellation():
    with pymupdf.open() as document:
        for value in ("First page", "Second page", "Third page"):
            document.new_page().insert_text((72, 72), value)
        data = document.tobytes()
    validate_native_pdf(data)
    seen = []

    def checkpoint():
        seen.append(len(seen))

    assert read_native_pdf_prefix(
        data, max_pages=2, max_chars_per_page=6, checkpoint=checkpoint,
    ) == ("First ", "Second")
    assert seen == [0, 1, 2]

    def cancelled():
        raise TimeoutError("caller deadline")

    with pytest.raises(TimeoutError, match="caller deadline"):
        read_native_pdf_prefix(
            data, max_pages=2, max_chars_per_page=6, checkpoint=cancelled,
        )


def test_invalid_pdf_is_rejected_by_parser_owner():
    with pytest.raises(NativePdfError):
        validate_native_pdf(b"%PDF-1.4\n%%EOF")


@pytest.mark.parametrize("module", ["local_reconcile", "official_source_flow", "narrative_language"])
def test_source_intake_does_not_import_pdf_backend(module):
    repo = Path(__file__).resolve().parents[2]
    path = repo / "src" / "company_wiki" / "source_catalog" / f"{module}.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = {
        alias.name.split(".")[0]
        for node in ast.walk(tree) if isinstance(node, ast.Import)
        for alias in node.names
    }
    modules.update(
        node.module.split(".")[0] for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert modules.isdisjoint({"pymupdf", "fitz"})
