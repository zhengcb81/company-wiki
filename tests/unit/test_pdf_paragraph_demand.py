"""Physical gap demand must not treat complete rows or words as fractures."""
from collections import Counter
from dataclasses import replace
from hashlib import sha256

import pytest

from company_wiki.document_normalization import table_shapes
from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_pdf_enhancement import ParagraphEnhancement
from company_wiki.source_catalog.narrative_pdf_paragraphs import triage_paragraph_gaps
from unit.test_pdf_paragraph_alignment import document
from unit.test_pdf_paragraph_runtime import config


@pytest.mark.parametrize("parts", (
    ("Installed equipment capacity\n100\n200\n300", "commissioned capacity\n90\n180\n270"),
    ("公司设备产能\n10000\n20000\n30000", "其他\n152\n–\n–"),
    ("Operating expense amounts\n(30000)\n(40000)\n(50000)", "gross profit\n11111\n22222\n33333"),
))
def test_two_complete_rows_are_not_a_prose_fracture_or_sdk_demand(parts):
    original = b"synthetic source, not a provider receipt"
    parsed = replace(document(parts), source_sha256=sha256(original).hexdigest())
    assert all(table_shapes.observe_value_cells(text).complete_value_row for text in parts)
    assert triage_paragraph_gaps(parsed, work_budget=WorkBudget(10000)).pages == ()

    def forbidden(*args, **kwargs):
        pytest.fail("Complete rows must not start a paragraph converter")

    result = ParagraphEnhancement(config(), runner=forbidden).enhance(
        original, parsed, work_budget=WorkBudget(10000), deadline=None
    )
    assert result.units == parsed.units
    assert result.layout_diagnostics[-1]["status"] == "not_needed"


@pytest.mark.parametrize("heading", ("其他資料", "其它事项"))
def test_pronoun_prefix_inside_an_independent_word_is_not_a_dependent_tail(heading):
    parsed = document(("Interim report 18", heading))
    assert triage_paragraph_gaps(parsed, work_budget=WorkBudget(10000)).pages == ()


@pytest.mark.parametrize("parts", (
    ("The new product generated revenue of 12.4", "million dollars; rollout is not yet approved."),
    ("产品新增收入达到12.4", "百萬元，仍须客户完成验收。"),
    ("Developed the platform", "其交付计划尚未获批准。"),
    ("Developed the platform", "其中两项功能仍在客户验证。"),
    ("We delivered the equipment", "because the customer completed qualification."),
))
def test_true_amount_and_dependent_prose_still_demand_enhancement(parts):
    parsed = document(parts)
    before = tuple((u.unit_id, u.raw_text, u.coordinates) for u in parsed.units)
    assert triage_paragraph_gaps(parsed, work_budget=WorkBudget(10000)).pages == (1,)
    assert tuple((u.unit_id, u.raw_text, u.coordinates) for u in parsed.units) == before


@pytest.mark.parametrize("parts", (
    ("Unexplained source prose remains here\nOther\n123\n456", "other observed data\n333\n444"),
    ("Installed equipment capacity\n100\n200", "million units, subject to customer acceptance."),
    ("The production equipment is now available to customers in", "other regions, subject to local qualification."),
))
def test_mixed_material_or_one_row_cannot_dispose_of_unexplained_prose(parts):
    parsed = document(parts)
    assert not all(table_shapes.observe_value_cells(text).complete_value_row for text in parts)
    assert triage_paragraph_gaps(parsed, work_budget=WorkBudget(10000)).pages == (1,)


@pytest.mark.parametrize("parts", (
    ("The installed production equipment generated revenue of\n12.4",
     "million dollars and remains subject to customer acceptance\n125\n160"),
    ("The other matters are still being examined\n125\n160",
     "which are subject to customer acceptance\n175\n200"),
))
def test_positive_tail_evidence_precedes_ambiguous_row_shape(parts):
    parsed = document(parts)
    assert all(table_shapes.observe_value_cells(text).complete_value_row for text in parts)
    assert triage_paragraph_gaps(parsed, work_budget=WorkBudget(10000)).pages == (1,)


def test_shared_shape_observation_is_prepared_at_most_once_per_unit(monkeypatch):
    observed = []
    actual = table_shapes.observe_value_cells

    def counting(text):
        observed.append(text)
        return actual(text)

    monkeypatch.setattr(table_shapes, "observe_value_cells", counting)
    parsed = document((
        "Installed equipment capacity\n100\n200\n300",
        "commissioned capacity\n90\n180\n270",
        "other capacity\n80\n170\n260",
    ))
    triage_paragraph_gaps(parsed, work_budget=WorkBudget(10000))
    assert observed and max(Counter(observed).values()) == 1


def test_actual_shared_shape_bytes_are_bound_by_the_reading_recipe(tmp_path, monkeypatch):
    from pathlib import Path

    before = config().recipe()
    target = tmp_path / "table_shapes.py"
    target.write_bytes(Path(table_shapes.__file__).read_bytes() + b"\n# changed deployed helper\n")
    monkeypatch.setattr(table_shapes, "__file__", str(target))
    assert config().recipe() != before
