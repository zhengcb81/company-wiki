"""Argument, archive and diagnostic-vocabulary boundaries (card §5, §6 A)."""

from __future__ import annotations

import hashlib

import pytest

from .ooxml_support import (
    cell,
    docx,
    encrypt_member,
    paragraph,
    row,
    table,
)

from company_wiki.document_normalization.office_table_structure import (
    parse_office_tables,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def test_source_sha256_mismatch_is_refused():
    payload = docx(table(row(cell(paragraph("A")))))
    with pytest.raises(ValueError, match="source_sha256 mismatch"):
        parse_office_tables(payload, source_sha256="0" * 64)


def test_non_zip_bytes_are_refused():
    with pytest.raises(ValueError):
        parse_office_tables(b"not a zip archive", source_sha256=_sha(b"not a zip archive"))


def test_zip_without_office_part_is_unsupported():
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("readme.txt", "hello")
    payload = buffer.getvalue()
    with pytest.raises(ValueError, match="unsupported_office_format"):
        parse_office_tables(payload, source_sha256=_sha(payload))


def test_encrypted_member_is_refused():
    payload = encrypt_member(
        docx(table(row(cell(paragraph("A"))))), "word/document.xml"
    )
    with pytest.raises(ValueError):
        parse_office_tables(payload, source_sha256=_sha(payload))


def test_diagnostics_use_only_interface_codes():
    """Every emitted code must be in the P2/shared INTERFACES vocabulary."""
    allowed = {
        "p2_span_out_of_grid",
        "p2_merge_unresolved",
        "p2_footnote_unresolved",
        "p2_continuation_unknown",
        "p2_table_limit",
        "dependency_unavailable",
        "invalid_argument",
        "limit_exceeded",
        "parser_warning",
    }
    payloads = [
        docx(table(row(cell(paragraph("超宽"), grid_span=5)), widths=(2880,))),
        docx(table(row(cell(vmerge="continue")))),
        docx(table(row(cell(paragraph("A"))))),
    ]
    for payload in payloads:
        structure = parse_office_tables(payload, source_sha256=_sha(payload))
        diagnostics = structure["diagnostics"]
        assert isinstance(diagnostics, list)
        for entry in diagnostics:
            assert set(entry) == {"code", "table_id", "detail"}
            assert entry["code"] in allowed, entry
        assert structure["status"] in {"ok", "partial", "unavailable"}


def test_limits_are_frozen_and_default_to_card_values():
    from company_wiki.document_normalization.office_table_structure import (
        OfficeTableLimits,
    )

    limits = OfficeTableLimits()
    assert limits == OfficeTableLimits(
        max_tables=64,
        max_cells=20000,
        max_text_chars=200000,
        max_footnote_chars=20000,
    )
    with pytest.raises(Exception):
        limits.max_tables = 1  # type: ignore[misc]
