"""Compact model inputs retain all text, roles, flags and canonical citations."""

from dataclasses import replace
import json

import pytest

from config import LLMConfig
from company_wiki.automation.narrative_http_model import NarrativeHTTPModel, model_options_from_config
from company_wiki.automation.narrative_model import (
    ModelResponseError, NarrativeModelRequest, NarrativeModelResponse, decode_model_draft,
)
from support.narrative_model_request_fixture import response_draft, selection
from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan


def _span(base, *, page_number, role=None, flags=None):
    return EvidenceSpan.create(
        source_id=base.source_id, coordinates=EvidenceCoordinates(page_number=page_number, paragraph_index=0),
        raw_text=base.raw_text,
        structured_value={**base.structured_value, **({"source_role": role} if role else {})},
        parser_name=base.parser_name, parser_version=base.parser_version,
        parse_status=base.parse_status, quality_flags=base.quality_flags if flags is None else flags,
    )


def _reply(selected, evidence_ids):
    request = NarrativeModelRequest.from_selection(selected)
    value = response_draft(json.loads(request.data_json))
    value["draft"]["claims"][0]["evidence_ids"] = evidence_ids
    return NarrativeModelResponse("fixture", "fixture", request.prompt_version,
                                  json.dumps(value, ensure_ascii=False).encode())


def test_all_160_spans_keep_text_flags_and_restore_full_citations_with_configured_output_limit():
    selected = selection(160, flags=("locator_unstable",))
    before = selected.to_dict()
    request = NarrativeModelRequest.from_selection(selected)
    envelope = json.loads(request.data_json)
    assert envelope["evidence_columns"] == ["id", "raw_text", "source_role", "quality_flags"]
    model = NarrativeHTTPModel(**model_options_from_config(LLMConfig()))
    assert model.max_output_tokens == 8192
    assert len(model.request_bytes(request)) + 128 + model.max_output_tokens < 30_000
    assert len(envelope["evidence"]) == 160
    aliases = []
    for projected, span in zip(envelope["evidence"], selected.evidence_spans, strict=True):
        alias = projected[0]
        assert len(alias) <= 8 and alias != span.span_id
        assert projected[1] == span.raw_text
        assert (projected[3] if len(projected) > 3 else envelope["default_quality_flags"]) == list(span.quality_flags)
        assert (projected[2] if len(projected) > 2 else envelope["default_source_role"]) == "company_filing"
        decoded = decode_model_draft(_reply(selected, [alias]), selected=selected)
        assert decoded["claims"][0]["evidence_ids"] == [span.span_id]
        aliases.append(alias)
    assert len(set(aliases)) == 160
    assert selected.to_dict() == before


def test_mixed_roles_and_empty_flag_overrides_never_change_evidence_semantics():
    selected = selection(3, flags=("locator_unstable",))
    changed = _span(selected.evidence_spans[1], page_number=2, role="analyst", flags=())
    selected = replace(selected, evidence_spans=(selected.evidence_spans[0], changed, selected.evidence_spans[2]))
    envelope = json.loads(NarrativeModelRequest.from_selection(selected).data_json)
    actual = [(span[2] if len(span) > 2 else envelope["default_source_role"],
               span[3] if len(span) > 3 else envelope["default_quality_flags"]) for span in envelope["evidence"]]
    assert actual == [("company_filing", ["locator_unstable"]), ("analyst", []),
                      ("company_filing", ["locator_unstable"])]


@pytest.mark.parametrize("unknown", ["e999999", "s1", "../../../raw.pdf", "urn:absent"])
def test_unknown_citations_are_rejected_before_final_draft(unknown):
    selected = selection()
    with pytest.raises(ModelResponseError, match="citation"):
        decode_model_draft(_reply(selected, [unknown]), selected=selected)


def test_full_canonical_citation_from_a_pinned_test_port_remains_valid():
    selected = selection()
    span_id = selected.evidence_spans[0].span_id
    assert decode_model_draft(_reply(selected, [span_id]), selected=selected)["claims"][0]["evidence_ids"] == [span_id]


def test_hash_binds_the_full_mapping_even_when_the_http_body_is_identical():
    selected = selection()
    span = _span(selected.evidence_spans[0], page_number=2)
    changed = replace(selected, evidence_spans=(span,))
    first = NarrativeModelRequest.from_selection(selected)
    second = NarrativeModelRequest.from_selection(changed)
    assert first.data_json == second.data_json
    assert first.input_sha256 != second.input_sha256


def test_duplicate_canonical_span_ids_cannot_form_an_ambiguous_alias_map():
    selected = selection(2)
    selected = replace(selected, evidence_spans=(selected.evidence_spans[0], selected.evidence_spans[0]))
    with pytest.raises(ModelResponseError, match="duplicate"):
        NarrativeModelRequest.from_selection(selected)
