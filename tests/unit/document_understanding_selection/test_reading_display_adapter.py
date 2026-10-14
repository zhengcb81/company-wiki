"""Source-owned typed representations, observed without inventing quote bytes."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan, source_id_for_sha256
from tools.document_understanding_benchmark.closed_group_support import score_facts

SOURCE = source_id_for_sha256("d" * 64)


def row(cells, *, raw=None, page=3, table=1, index=4, role="company_filing", source=SOURCE):
    return EvidenceSpan.create(source_id=source,
        coordinates=EvidenceCoordinates(page_number=page, table_index=table, row_index=index),
        raw_text=" | ".join(cell for cell in cells if cell) if raw is None else raw,
        structured_value={"unit_kind": "pdf_table_row", "source_role": role,
            "row_cells": cells, "table_headers": ["Measure", "2026", "2025"]},
        parser_name="selective_narrative_parser", parser_version="0.1.1", parse_status="parsed", quality_flags=())


def native(text, *, kind="pdf_native_range", page=3):
    return EvidenceSpan.create(source_id=SOURCE,
        coordinates=EvidenceCoordinates(page_number=page, char_start=0, char_end=len(text)),
        raw_text=text, structured_value={"source_role": "company_filing", "unit_kind": kind},
        parser_name="native_pdf_range_parser" if kind == "pdf_native_range" else "selective_narrative_parser",
        parser_version="0.1.0", parse_status="parsed", quality_flags=())


def context(rows):
    ids = [s.span_id for s in rows]
    digest = sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()
    return {"schema_version": "du-production-reading/1", "groups": [{
        "group_id": "urn:company-wiki:reading-group:sha256:" + digest,
        "kind": "operating_table", "section_role": "business", "evidence_ids": ids}]}


def supported(quote, rows, *, ctx=None, page=3, source=SOURCE, role="company_filing", extra=(), **coordinates):
    anchor = {"exact_quote": quote, "page": page, "source_id": source, **coordinates}
    fact = {"id": "source-display", "role": role, "any_support_sets": [[anchor, *extra]]}
    return score_facts([fact], evidence_spans=rows, reading_context=ctx, source_id=SOURCE)[0]["supported"]


@pytest.mark.parametrize("quote", ["Inventory days 41 36", "Inventory days | 41 | 36", "41 36"])
def test_real_typed_row_supports_complete_contiguous_cells_without_changing_original(quote):
    actual = row(["Inventory days", "41", "36", "5"])
    before = deepcopy(actual.to_dict())
    assert supported(quote, [actual])
    assert actual.to_dict() == before


def test_empty_columns_keep_original_positions_and_nfc_source_renderer_is_observed():
    actual = row(["Café inventory days", "", "41", "36"], raw="Café inventory days | 41 | 36")
    assert supported("Café inventory days 41 36", [actual], table_index=1, row_index=4)
    assert actual.structured_value["row_cells"][1] == ""


@pytest.mark.parametrize("quote,kwargs", [
    ("Inventory days 42 36", {}),
    ("Inventory days 36 41", {}),
    ("Inventory days 2026 2025", {}),
    ("Inventory days 41 36", {"page": 4}),
    ("Inventory days 41 36", {"source": source_id_for_sha256("e" * 64)}),
    ("Inventory days 41 36", {"role": "management"}),
    ("Inventory days | 41 | 36", {"table_index": 2}),
    ("Inventory days | 41 | 36", {"row_index": 5}),
    ("Inventory days | 41 | 36", {"table_index": True}),
    ("Inventory days 4 36", {}),
    ("Inventory days 41 3", {}),
    ("Inventory days | 41 | 3", {}),
])
def test_row_values_order_coordinates_role_and_complete_cell_tokens_are_exact(quote, kwargs):
    assert not supported(quote, [row(["Inventory days", "41", "36"])], **kwargs)


@pytest.mark.parametrize("cells,raw,quote", [
    (["Inventory days", "41", "36"], "Inventory days 41 36", "Inventory days 41 36"),
    (["Other measure", "41", "36"], "Inventory days | 41 | 36", "Inventory days | 41 | 36"),
    (["Inventory days", "42", "36"], "Inventory days | 41 | 36", "Inventory days | 41 | 36"),
    (["Inventory days", "36", "41"], "Inventory days | 41 | 36", "Inventory days | 41 | 36"),
])
def test_declared_row_with_mismatched_body_metadata_cannot_fall_through_to_literal_support(cells, raw, quote):
    assert not supported(quote, [row(cells, raw=raw)])


@pytest.mark.parametrize("cells", ["Inventory days", None, ["Inventory days", 41, "36"], [], ["", ""]])
def test_malformed_cells_are_not_a_canonical_typed_row(cells):
    actual = EvidenceSpan.create(source_id=SOURCE,
        coordinates=EvidenceCoordinates(page_number=3, table_index=1, row_index=4),
        raw_text="Inventory days | 41 | 36", structured_value={"unit_kind": "pdf_table_row",
            "source_role": "company_filing", "row_cells": cells},
        parser_name="selective_narrative_parser", parser_version="0.1.1", parse_status="parsed", quality_flags=())
    assert not supported("Inventory days | 41 | 36", [actual])


def test_headers_and_other_rows_cannot_supply_missing_values_even_in_one_closed_group():
    rows = [row(["Measure", "2026", "2025"], index=0),
        row(["Inventory days", "41"], index=4), row(["Other measure", "36"], index=5)]
    assert not supported("Inventory days 41 36", rows, ctx=context(rows))
    assert not supported("Inventory days 2026 2025", rows, ctx=context(rows))


def test_period_context_remains_an_independent_same_group_support_requirement():
    rows = [row(["Measure", "2026", "2025"], index=0), row(["Inventory days", "41", "36"])]
    extra = [{"exact_quote": "2026 2025", "page": 3}]
    assert supported("Inventory days 41 36", rows, ctx=context(rows), extra=extra)
    assert not supported("Inventory days 41 36", rows, extra=extra)


def test_literal_pipe_inside_a_cell_is_preserved():
    actual = row(["Brand A | B", "41", "36"])
    assert supported("Brand A | B 41 36", [actual])
    assert not supported("Brand A B 41 36", [actual])


@pytest.mark.parametrize("raw,quote", [
    ("品牌包括NorthPeak、\nHarborSport及CedarActive。", "品牌包括NorthPeak、HarborSport及CedarActive。"),
    ("品牌包括NorthPeak、\r\n  HarborSport及CedarActive。", "品牌包括NorthPeak、HarborSport及CedarActive。"),
])
def test_verified_native_range_observes_actual_list_delimiter_line_wrap_only(raw, quote):
    actual = native(raw)
    before = deepcopy(actual.to_dict())
    assert supported(quote, [actual])
    assert actual.to_dict() == before


@pytest.mark.parametrize("raw,quote", [
    ("owner\nship", "ownership"),
    ("8.\n2", "8.2"),
    ("41\n36", "4136"),
    ("Company’s manufacturing", "Company's manufacturing"),
    ("NorthPeak、 HarborSport", "NorthPeak、HarborSport"),
    ("NorthPeak、\nHarborSport", "NorthPeak,HarborSport"),
])
def test_native_quote_observation_cannot_invent_words_numbers_or_punctuation(raw, quote):
    assert not supported(quote, [native(raw)])


def test_plain_prose_does_not_get_native_range_or_table_projection():
    assert not supported("NorthPeak、HarborSport", [native("NorthPeak、\nHarborSport", kind="pdf_text_block")])
    assert not supported("Inventory days 41 36", [native("Inventory days | 41 | 36", kind="pdf_text_block")])
