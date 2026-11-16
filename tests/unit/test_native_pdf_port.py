import ast
from pathlib import Path

import pymupdf
import pytest

from company_wiki.parser_adapters import (
    NativePdfError,
    read_native_pdf_pages,
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


def test_complete_native_pdf_port_preserves_empty_pages_and_rejects_partial_results():
    with pymupdf.open() as document:
        document.new_page().insert_text((72, 72), "First")
        document.new_page()
        document.new_page().insert_text((72, 72), "Third")
        data = document.tobytes()
        encrypted = document.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="fixture")
    assert read_native_pdf_pages(data, max_pages=3, max_text_characters=12) == ("First\n", "", "Third\n")

    for body, page_limit, text_limit, reason in (
        (data, 2, 100, "page_limit"),
        (data, 3, 11, "text_limit"),
        (encrypted, 3, 100, "encrypted"),
    ):
        with pytest.raises(NativePdfError) as exc_info:
            read_native_pdf_pages(body, max_pages=page_limit, max_text_characters=text_limit)
        assert exc_info.value.reason == reason


@pytest.mark.parametrize("module", ["local_reconcile", "official_source_flow", "narrative_language", "cn_primary_issuer"])
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
