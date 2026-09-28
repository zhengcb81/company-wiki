from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile

import pytest

from company_wiki.source_catalog.narrative_evidence import (
    parse_pdf,
    parse_pdf_bytes,
    select_narrative_evidence,
    verify_pdf_evidence_spans,
    verify_pdf_evidence_spans_bytes,
)
from company_wiki.source_contract import source_id_for_sha256


def _pdf_fixture(tmp_path: Path) -> tuple[Path, bytes, str, str]:
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "bytes-facade.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Company launched a new product and expanded overseas capacity.",
    )
    document.save(path)
    document.close()
    data = path.read_bytes()
    source_sha256 = hashlib.sha256(data).hexdigest()
    return path, data, source_id_for_sha256(source_sha256), source_sha256


def test_pdf_bytes_parse_and_replay_equal_path_facades(tmp_path: Path) -> None:
    path, data, source_id, source_sha256 = _pdf_fixture(tmp_path)

    by_path = parse_pdf(
        path,
        source_id=source_id,
        source_sha256=source_sha256,
        language="en",
    )
    by_bytes = parse_pdf_bytes(
        data,
        source_id=source_id,
        source_sha256=source_sha256,
        language="en",
    )
    assert by_bytes == by_path

    selected = select_narrative_evidence(
        by_path,
        title="annual-report.pdf",
        existing_kind="annual_report",
    )
    assert selected.evidence_spans
    expected = verify_pdf_evidence_spans(
        path,
        source_id=source_id,
        source_sha256=source_sha256,
        evidence_spans=selected.evidence_spans,
    )
    actual = verify_pdf_evidence_spans_bytes(
        data,
        source_id=source_id,
        source_sha256=source_sha256,
        evidence_spans=selected.evidence_spans,
    )
    assert actual == expected


def test_pdf_bytes_facades_reject_hash_drift_without_writing_temp_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, data, source_id, source_sha256 = _pdf_fixture(tmp_path)
    parsed = parse_pdf_bytes(
        data,
        source_id=source_id,
        source_sha256=source_sha256,
        language="en",
    )
    selected = select_narrative_evidence(
        parsed,
        title="annual-report.pdf",
        existing_kind="annual_report",
    )

    def forbid_write(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("PDF bytes facade attempted a temporary-file write")

    monkeypatch.setattr(Path, "write_bytes", forbid_write)
    monkeypatch.setattr(Path, "write_text", forbid_write)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", forbid_write)
    monkeypatch.setattr(tempfile, "TemporaryDirectory", forbid_write)
    monkeypatch.setattr(tempfile, "mkstemp", forbid_write)

    reparsed = parse_pdf_bytes(
        data,
        source_id=source_id,
        source_sha256=source_sha256,
        language="en",
    )
    assert reparsed == parsed
    verified, failed = verify_pdf_evidence_spans_bytes(
        data,
        source_id=source_id,
        source_sha256=source_sha256,
        evidence_spans=selected.evidence_spans,
    )
    assert verified
    assert failed == ()

    wrong_sha = "0" * 64
    with pytest.raises(ValueError, match="changed"):
        parse_pdf_bytes(
            data,
            source_id=source_id,
            source_sha256=wrong_sha,
            language="en",
        )
    with pytest.raises(ValueError, match="changed"):
        verify_pdf_evidence_spans_bytes(
            data,
            source_id=source_id,
            source_sha256=wrong_sha,
            evidence_spans=selected.evidence_spans,
        )
