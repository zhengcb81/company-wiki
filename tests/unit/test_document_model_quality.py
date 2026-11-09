"""Regressions for the neutral evidence and literal source-shape owner."""

from dataclasses import replace
from hashlib import sha256

import pytest

from company_wiki.document_model.form_fields import has_inline_form_response
from company_wiki.document_model.narrative import NarrativeUnit, selected_summary_input
from company_wiki.document_model.table_shapes import has_tabular_value_tail, observe_value_cells
from company_wiki.document_model.turns import declared_speaker_role
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


def _unit(text: str, *, source_id: str, start: int, metadata=None) -> NarrativeUnit:
    return NarrativeUnit(
        unit_id="urn:company-wiki:narrative-unit:sha256:" + sha256(text.encode()).hexdigest(),
        source_id=source_id, parser_name="selective_narrative_parser", parser_version="0.1.2",
        coordinates=EvidenceCoordinates(
            page_number=7, table_index=1, row_index=3, column_index=1,
            char_start=start, char_end=start + len(text),
        ),
        raw_text=text, unit_kind="pdf_table_qa_fragment", source_role="management",
        language="en", metadata=metadata or {},
    )


def test_grouped_excerpt_follows_original_ranges_in_same_cell():
    first_text = "We plan to expand after certification."
    second_text = "No capacity has been added yet."
    original_text = first_text + " " + second_text
    original_sha = sha256(original_text.encode()).hexdigest()
    source_id = source_id_for_sha256(original_sha)
    first = _unit(first_text, source_id=source_id, start=0)
    second = _unit(second_text, source_id=source_id, start=len(first_text) + 1)
    members = tuple(unit.to_evidence_span(
        topics=("capacity",), selection_reasons=("qa_answer",), selection_group_id="one-answer",
    ) for unit in (second, first))

    result = selected_summary_input(
        source_id=source_id, source_sha256=original_sha,
        document_kind="investor_relations", evidence_spans=members,
    )
    row, = result["evidence"]
    assert row["raw_text"] == original_text
    assert row["raw_text_sha256"] == original_sha
    assert row["evidence_ids"] == [members[1].span_id, members[0].span_id]
    assert row["locators"] == [first.coordinates.locator(), second.coordinates.locator()]
    assert [span.raw_text for span in members] == [second_text, first_text]


def test_transient_native_layout_does_not_change_evidence_metadata_or_identity():
    source_id = source_id_for_sha256("a" * 64)
    unit = _unit("The expansion is conditional.", source_id=source_id, start=9,
                 metadata={"source_locator": "page:7/row:3/column:1"})
    enhanced = replace(unit, metadata={**unit.metadata,
        "reading_layout": {"column": 2}, "native_source_view": {"boxes": [[1, 2, 3, 4]]},
    })
    assert enhanced.evidence_metadata() == unit.evidence_metadata()
    arguments = {"topics": ("capacity",), "selection_reasons": ("plan",)}
    assert enhanced.to_evidence_span(**arguments) == unit.to_evidence_span(**arguments)


@pytest.mark.parametrize("cells", [
    ("（１，２３４．５０）", "＋９００．００", "４０．８５％"),
    ("($1,234.50*)", "€900.00", "40.85%¹"),
    ("−£1,234.50", "1 200,00 €", "40.85%"),
])
def test_tabular_formatting_does_not_hide_visible_numeric_cells(cells):
    source = "期末餘額\n" + "\n".join(cells)
    assert has_tabular_value_tail("4. " + source)
    observed = observe_value_cells(source)
    assert observed.unbound_numeric_cells and observed.complete_value_row


@pytest.mark.parametrize("cell", ["1$2", "€$250", "2026$07$30", "USD 250"])
def test_currency_glyphs_or_codes_inside_material_do_not_fabricate_values(cell):
    source = f"3. Expansion plan\n{cell}\n500"
    assert not has_tabular_value_tail(source)
    observed = observe_value_cells(source)
    assert not observed.unbound_numeric_cells and not observed.complete_value_row


@pytest.mark.parametrize("name,title,role", [
    ("Avery Chief", "", "unknown"),
    ("Robin President", "", "unknown"),
    ("Casey Analyst", "Chief Operating Officer", "management"),
    ("CFO", "", "management"),
    ("Jane Doe", "Senior Research Analyst", "analyst"),
    ("Operator", "", "operator"),
])
def test_role_comes_from_printed_label_or_title_not_part_of_name(name, title, role):
    assert declared_speaker_role(name, title) == role


def test_pdf_transcript_does_not_turn_persons_name_into_management_support():
    from unit.test_pdf_transcript_turns import _select_pdf

    original = "Avery Chief: We launched a new product and expanded overseas capacity for customers."
    _, _, _, parsed, package = _select_pdf(original)
    assert [unit.raw_text for unit in parsed.units] == [original]
    assert not package.evidence_spans


@pytest.mark.parametrize("text", [
    "2. 關聯交易 ☒適用 ☐不適用",
    "3. 经营计划 □适用 ×不适用",
])
def test_printed_x_checkbox_pair_is_not_an_inferred_heading(text):
    from company_wiki.document_understanding.observation_adapter import _heading_level

    assert has_inline_form_response(text)
    assert _heading_level(text, {"heading_like": True}) is None
    assert _heading_level(text, {"heading_level": 2}) == 2


def test_applicability_words_in_prose_are_not_printed_form_controls():
    assert not has_inline_form_response("該安排適用於新客戶，不適用於原合約。")
