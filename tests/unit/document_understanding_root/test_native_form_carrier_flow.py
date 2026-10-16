"""Single native HTML parse through language_structure and carrier projection."""

from __future__ import annotations

from dataclasses import replace
import hashlib
from unittest.mock import patch

from bs4.element import Tag
import pytest

from company_wiki.document_normalization import html_parser
from company_wiki.document_normalization.limits import NormalizationLimits
from company_wiki.document_understanding.observation_adapter import build_observation
from company_wiki.document_understanding.source_signals import collect_source_signals
from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization


def native(html: str, *, source_id: str | None = None):
    data = html.encode("utf-8")
    source_id = source_id or "urn:company-wiki:source:sha256:" + hashlib.sha256(data).hexdigest()
    document = html_parser.parse_html(
        data, source_id=source_id, source_sha256=hashlib.sha256(data).hexdigest(),
        mime_type="text/html", limits=NormalizationLimits(),
    )
    structure = NarrativeNormalization.language_structure(document, "en")
    observation = build_observation(
        structure.units, source_id=source_id, source_sha256=document.source_sha256,
        mime_type="text/html", metadata={"form_type": "10-K"},
    )
    return document, structure, observation


def carriers(observation):
    return [carrier for unit in observation["units"]
            for carrier in unit["hints"].get("native_source_carriers", [])]


def signals(observation):
    units = {
        unit["unit_id"]: {
            "text": unit["text"], "parent_id": unit["hints"]["source_id"],
            "role": unit["role"], "kind": unit["kind"], "locator": unit["locator"],
        }
        for unit in observation["units"]
    }
    return collect_source_signals(
        {"schema_version": "du4-source-signal-observation/1", "units": units,
         "carriers": carriers(observation)},
        work_budget=WorkBudget(max_work_units=100_000),
    )


def test_visible_dei_survives_real_language_structure_with_exact_text_reference():
    document, structure, obs = native(
        '<html><body><p>Cafe\u0301 这里 <ix:nonNumeric name="dei:DocumentType">10-Q</ix:nonNumeric> details.</p></body></html>'
    )
    record = carriers(obs)[0]
    assert record["kind"] == "visible_inline_xbrl_document_type"
    assert record["attributes"] == {"concept": "dei:DocumentType", "visibility": "visible"}
    source_unit = next(unit for unit in structure.units if unit.unit_id == record["unit_ids"][0])
    ref = record["value_refs"][0]
    assert source_unit.raw_text[ref["char_start"]:ref["char_end"]] == "10-Q"
    assert ref["char_start"] == source_unit.raw_text.index("10-Q")
    assert source_unit.metadata["native_source_view"]
    assert document.units[0].unit_id == structure.units[0].unit_id
    assert document.units[0].raw_text == structure.units[0].raw_text
    assert signals(obs)["source_form_evidence"][0]["value"] == "10-Q"


def test_own_form_label_is_a_complete_native_owner_not_a_body_mention():
    _, _, obs = native('<html><body><h1><b>FORM</b> <span>10-Q</span></h1><p>See FORM 10-K filed previously.</p></body></html>')
    found = signals(obs)["source_form_evidence"]
    assert [(row["origin"], row["value"]) for row in found] == [
        ("visible_own_form_label", "FORM 10-Q")
    ]


@pytest.mark.parametrize("hidden", [
    '<p hidden><ix:nonNumeric name="dei:DocumentType">10-K</ix:nonNumeric></p>',
    '<div style="display:none"><ix:nonNumeric name="dei:DocumentType">10-K</ix:nonNumeric></div>',
    '<ix:hidden><ix:nonNumeric name="dei:DocumentType">10-K</ix:nonNumeric></ix:hidden>',
    '<script>FORM 10-K</script>',
    '<!-- FORM 10-K -->',
    '<span name="dei:DocumentType">10-K</span>',
    '<div data-form-type="10-K">Ordinary operations update.</div>',
    '<ix:nonNumeric name="dei:DocumentType" value="10-K"></ix:nonNumeric>',
    '<a href="other-issuer.html">FORM 10-K</a>',
    '<a href="other-issuer.html"><h1>FORM 10-K</h1></a>',
])
def test_hidden_script_declaration_or_link_does_not_create_form_carrier(hidden):
    _, _, obs = native(f'<html><body>{hidden}<p>Business operations progressed.</p></body></html>')
    assert not carriers(obs)
    assert not signals(obs)["source_form_evidence"]


def test_hidden_value_does_not_mask_or_lend_text_to_a_visible_dei():
    _, _, obs = native('<html><body><p><ix:nonNumeric name="dei:DocumentType">10-<span hidden>K</span>Q</ix:nonNumeric></p></body></html>')
    found = signals(obs)["source_form_evidence"]
    assert len(found) == 1
    # The existing normalized owner contains the separating space. Keep it;
    # do not fabricate a printed 10-Q from disjoint/hidden characters.
    assert found[0]["value"] == "10- Q"
    assert found[0]["normalized_value"] != "10-Q"


def test_inline_split_keeps_actual_normalized_spacing_and_no_second_dom_parse():
    actual_parser = html_parser.BeautifulSoup
    actual_get_text = Tag.get_text
    calls = []

    def observed_text(tag, *args, **kwargs):
        calls.append(tag.name)
        assert tag.name not in {"html", "body", "[document]"}
        return actual_get_text(tag, *args, **kwargs)

    with patch.object(html_parser, "BeautifulSoup", wraps=actual_parser) as parser, patch.object(Tag, "get_text", observed_text):
        _, _, obs = native('<html><body><p>Prefix <ix:nonNumeric name="dei:DocumentType"><b>10-</b><span>Q</span></ix:nonNumeric> tail</p></body></html>')
    assert parser.call_count == 1
    assert calls == []
    found = signals(obs)["source_form_evidence"]
    assert len(found) == 1 and found[0]["value"] == "10- Q"


def test_real_table_cell_keeps_visible_dei_value_reference():
    _, structure, obs = native('<html><body><table><tr><td>Filing <ix:nonNumeric name="dei:DocumentType"><span>10-Q</span></ix:nonNumeric></td></tr></table></body></html>')
    record = carriers(obs)[0]
    unit = next(unit for unit in structure.units if unit.unit_id == record["unit_ids"][0])
    assert unit.unit_kind == "html_table_cell"
    ref = record["value_refs"][0]
    assert unit.raw_text[ref["char_start"]:ref["char_end"]] == "10-Q"
    assert signals(obs)["source_form_evidence"][0]["value"] == "10-Q"


def test_dei_split_across_native_owners_stays_unknown_in_existing_collector():
    _, _, obs = native('<html><body><div><ix:nonNumeric name="dei:DocumentType">10-<p>Q</p></ix:nonNumeric></div></body></html>')
    assert carriers(obs)
    result = signals(obs)
    assert not result["source_form_evidence"]
    assert "SPLIT_OWNER_VALUE" in {row["code"] for row in result["diagnostics"]}


def test_parent_and_attachment_carriers_keep_their_actual_source_ids():
    _, _, main = native('<html><body><h1>FORM 8-K</h1></body></html>', source_id="original-main")
    _, _, attachment = native('<html><body><h1>FORM 10-K</h1></body></html>', source_id="original-child")
    together = {**main, "units": main["units"] + attachment["units"]}
    found = signals(together)["source_form_evidence"]
    assert {(row["parent_id"], row["value"]) for row in found} == {
        ("original-main", "FORM 8-K"), ("original-child", "FORM 10-K")
    }


def test_carrier_metadata_does_not_leak_or_change_legacy_evidence_span():
    _, structure, obs = native('<html><body><h1>FORM 10-Q</h1></body></html>')
    assert carriers(obs)
    unit = structure.units[0]
    old = replace(unit, metadata={key: value for key, value in unit.metadata.items() if key != "native_source_view"})
    current_span = unit.to_evidence_span(topics=["business"], selection_reasons=["test"])
    old_span = old.to_evidence_span(topics=["business"], selection_reasons=["test"])
    assert current_span == old_span
    assert "native_source_view" not in current_span.structured_value


def test_adapter_projects_carriers_without_mutating_native_metadata():
    _, structure, obs = native('<html><body><h1>FORM 10-Q</h1></body></html>')
    original = structure.units[0].metadata["native_source_view"]["carriers"][0]
    projected = carriers(obs)[0]
    projected["value_refs"][0]["char_start"] = 999
    assert original["value_refs"][0]["char_start"] == 0


def test_prior_sibling_link_does_not_hide_a_separate_own_form_label():
    _, _, obs = native('<html><body><a href="other.html">Other document</a><h1>FORM 10-Q</h1></body></html>')
    assert [row["value"] for row in signals(obs)["source_form_evidence"]] == ["FORM 10-Q"]


def test_many_facts_in_one_owner_materialize_metadata_once():
    html = '<html><body><p>' + ' '.join(
        '<ix:nonNumeric name="dei:DocumentType">10-Q</ix:nonNumeric>' for _ in range(128)
    ) + '</p></body></html>'
    with patch.object(html_parser, "replace", wraps=replace) as materialize:
        _, _, obs = native(html)
    assert len(carriers(obs)) == 128
    assert materialize.call_count == 1
