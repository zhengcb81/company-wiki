"""Replay and determinism of ``cwp-office-table/1`` (card §5.5, §6 A)."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from .ooxml_support import cell, docx, paragraph, pptx, pptx_cell, pptx_table, row, table

from company_wiki.document_normalization.office_table_structure import (
    OfficeTableLimits,
    parse_office_tables,
    replay_office_tables,
)


def _payload() -> bytes:
    return docx(
        table(
            row(cell(paragraph("项目")), cell(paragraph("金额"))),
            row(cell(paragraph("收入"), grid_span=2)),
        )
    )


def _parse(payload: bytes, **kwargs: object) -> dict[str, object]:
    return parse_office_tables(
        payload, source_sha256=hashlib.sha256(payload).hexdigest(), **kwargs
    )


def test_replay_of_unchanged_structure_passes_with_same_sha():
    payload = _payload()
    structure = _parse(payload)
    replayed = replay_office_tables(payload, structure)
    assert replayed["structure_sha256"] == structure["structure_sha256"]
    assert replayed["tables"] == structure["tables"]


def test_replay_detects_a_changed_column_span():
    payload = _payload()
    structure = _parse(payload)
    tampered = copy.deepcopy(structure)
    tables = tampered["tables"]
    assert isinstance(tables, list)
    target = None
    for table_structure in tables:
        for entry in table_structure["cells"]:  # type: ignore[index]
            if entry["column_span"] == 2:
                target = entry
    assert target is not None, "fixture must contain a spanning cell"
    target["column_span"] = 3

    with pytest.raises(ValueError) as error:
        replay_office_tables(payload, tampered)
    message = str(error.value)
    assert message.startswith("replay mismatch:")
    assert "column_span" in message
    assert "expected 3" in message


def test_replay_detects_a_changed_locator():
    payload = _payload()
    structure = _parse(payload)
    tampered = copy.deepcopy(structure)
    tables = tampered["tables"]
    assert isinstance(tables, list)
    entry = tables[0]["cells"][0]  # type: ignore[index]
    entry["locator"] = "cwp-docx-body/1|t=0|r=9|c=9|p=9"
    with pytest.raises(ValueError, match="replay mismatch"):
        replay_office_tables(payload, tampered)


def test_replay_detects_a_changed_text_even_outside_the_compared_field_set():
    """Every field edit is refused, not only locator/merge/row_span/column_span."""
    payload = _payload()
    structure = _parse(payload)

    changed_text = copy.deepcopy(structure)
    tables = changed_text["tables"]
    assert isinstance(tables, list)
    tables[0]["cells"][0]["text"] = "伪造文本"  # type: ignore[index]
    with pytest.raises(ValueError, match="replay mismatch"):
        replay_office_tables(payload, changed_text)

    changed_grid = copy.deepcopy(structure)
    tables = changed_grid["tables"]
    assert isinstance(tables, list)
    tables[0]["grid"] = {"rows": 99, "columns": 1}
    with pytest.raises(ValueError, match="replay mismatch"):
        replay_office_tables(payload, changed_grid)


def test_replay_charges_the_declared_hash_against_the_supplied_tables():
    """A structure whose stored hash no longer covers its own tables is refused."""
    payload = _payload()
    structure = _parse(payload)
    tampered = copy.deepcopy(structure)
    tables = tampered["tables"]
    assert isinstance(tables, list)
    tables[0]["cells"][0]["column_span"] = 4  # type: ignore[index]
    tampered["structure_sha256"] = structure["structure_sha256"]
    with pytest.raises(ValueError, match="replay mismatch"):
        replay_office_tables(payload, tampered)


def test_replay_rejects_unknown_schema_version():
    payload = _payload()
    structure = _parse(payload)
    tampered = copy.deepcopy(structure)
    tampered["schema_version"] = "cwp-office-table/2"
    with pytest.raises(ValueError, match="unsupported structure version"):
        replay_office_tables(payload, tampered)


def test_replay_rejects_a_structure_from_other_bytes():
    payload = _payload()
    structure = _parse(payload)
    other = docx(table(row(cell(paragraph("别的")))))
    with pytest.raises(ValueError):
        replay_office_tables(other, structure)


def test_structure_is_deterministic_and_inputs_are_not_mutated():
    payload = _payload()
    limits = OfficeTableLimits()
    snapshot = bytes(payload)

    first = parse_office_tables(
        payload, source_sha256=hashlib.sha256(payload).hexdigest(), limits=limits
    )
    second = parse_office_tables(
        payload, source_sha256=hashlib.sha256(payload).hexdigest(), limits=limits
    )

    assert first["structure_sha256"] == second["structure_sha256"]
    assert first == second
    assert payload == snapshot
    assert limits == OfficeTableLimits()


def test_structure_sha256_is_canonical_over_tables_only():
    payload = _payload()
    structure = _parse(payload)
    canonical = json.dumps(
        structure["tables"],
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert structure["structure_sha256"] == hashlib.sha256(canonical).hexdigest()


def test_replay_does_not_mutate_the_supplied_structure():
    payload = _payload()
    structure = _parse(payload)
    before = copy.deepcopy(structure)
    replay_office_tables(payload, structure)
    assert structure == before


def test_pptx_replay_round_trips():
    payload = pptx(pptx_table([2880, 2880], [[pptx_cell("A"), pptx_cell("B")]]))
    structure = _parse(payload)
    replayed = replay_office_tables(payload, structure)
    assert replayed["structure_sha256"] == structure["structure_sha256"]
