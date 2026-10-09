"""Mechanical group closure must not pretend to prove proposition entailment."""

import json
import pytest
from company_wiki.automation.narrative_model import (
    ModelResponseError,
    NarrativeModelRequest,
    NarrativeModelResponse,
    decode_model_draft,
)
from company_wiki.automation.narrative_contracts import (
    NarrativeContractError,
    NarrativeSummaryResult,
)
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from company_wiki.automation.models import HandlerOutcome
from support.fresh_summary_fixture import grouped_selection, claim, draft_for, US_TEXT
from unit.test_narrative_summarize_handler import _context


def reply(selected, claims):
    request = NarrativeModelRequest.from_selection(selected)
    return NarrativeModelResponse(
        "offline",
        "fixture",
        request.prompt_version,
        json.dumps(draft_for(selected, claims), ensure_ascii=False).encode(),
    )


def test_model_envelope_has_stable_whole_groups_without_duplicate_text_or_source_changes():
    selected = grouped_selection()
    before = selected.to_dict()
    first = NarrativeModelRequest.from_selection(selected)
    envelope = json.loads(first.data_json)
    assert envelope["evidence_groups"] == [["g1", ["e1", "e2"]], ["g2", ["e3", "e4"]]]
    assert envelope["evidence_group_columns"] == ["id", "evidence_ids"]
    assert len(envelope["evidence"]) == 5
    assert all(
        row[1] == span.raw_text
        for row, span in zip(envelope["evidence"], selected.evidence_spans, strict=True)
    )
    assert (
        first == NarrativeModelRequest.from_selection(selected)
        and selected.to_dict() == before
    )
    assert "mechanical" in first.instruction and "entailment" in first.instruction


@pytest.mark.parametrize("market", ["HK", "US-new-W02", "US-sealed-old-group"])
def test_omitted_hk_service_fee_or_us_previously_azure_tail_cannot_support_a_declared_group(
    market,
):
    if market == "HK":
        selected = grouped_selection()
        ids = ["e1", "e2", "e3"]
        groups = ["g1", "g2"]
        text = "企業服務增長近20%，受雲服務需求及微信小店商家技術服務費增長帶動。"
    else:
        groups_in = (
            ("commercial", "commercial", None)
            if market == "US-new-W02"
            else ("commercial",) * 3
        )
        selected = grouped_selection(
            US_TEXT,
            groups_in,
            language="en",
            page=7,
            first_paragraph=8,
            flags=("ocr_used", "layout_ambiguous"),
        )
        ids = ["e1"]
        groups = ["g1"]
        text = "Microsoft 365 commercial cloud now includes services previously reported in Azure."
    with pytest.raises(NarrativeContractError, match="group coverage is incomplete"):
        decode_model_draft(
            reply(selected, [claim(text, ids, groups)]), selected=selected
        )


def test_complete_multi_proposition_claim_keeps_exact_citations_and_no_group_wire_extensions():
    selected = grouped_selection()
    ids = ["e1", "e2", "e3", "e4"]
    result = decode_model_draft(
        reply(
            selected,
            [
                claim(
                    "金融科技收入增長；企業服務受雲需求和微信小店商家技術服務費帶動。",
                    ids,
                    ["g1", "g2"],
                )
            ],
        ),
        selected=selected,
    )
    assert result["claims"][0]["evidence_ids"] == [
        s.span_id for s in selected.evidence_spans[:4]
    ]
    assert result["claims"][0]["needs_review"] is False and result["status"] == "draft"
    assert "evidence_group_ids" not in result["claims"][0]
    assert selected.evidence_spans[4].span_id not in result["claims"][0]["evidence_ids"]


def test_unrelated_adjacent_paragraph_is_never_added_to_close_the_business_group():
    selected = grouped_selection()
    result = decode_model_draft(
        reply(
            selected,
            [
                claim(
                    "微信小店交易額上升帶動商家技術服務費收入增長。",
                    ["e3", "e4"],
                    ["g2"],
                )
            ],
        ),
        selected=selected,
    )
    assert result["claims"][0]["evidence_ids"] == [
        s.span_id for s in selected.evidence_spans[2:4]
    ]


@pytest.mark.parametrize("declaration", [None, []])
def test_legacy_or_explicit_narrow_claim_can_survive_but_partial_context_is_diagnostic(
    declaration,
):
    selected = grouped_selection()
    result = decode_model_draft(
        reply(selected, [claim("企業服務收入同比增長接近20%。", ["e3"], declaration)]),
        selected=selected,
    )
    assert result["claims"][0]["evidence_ids"] == [selected.evidence_spans[2].span_id]
    assert (
        result["claims"][0]["needs_review"] is True
        and result["status"] == "needs_review"
    )


@pytest.mark.parametrize("declaration", [["g999"], ["g1", "g1"], "g1", [None]])
def test_unknown_duplicate_or_invalid_group_declaration_is_not_silently_stripped(
    declaration,
):
    selected = grouped_selection()
    with pytest.raises(NarrativeContractError, match="summary claim evidence group"):
        decode_model_draft(
            reply(selected, [claim("業務進展", ["e1", "e2"], declaration)]),
            selected=selected,
        )


def test_one_incomplete_group_claim_is_discarded_whole_without_modifying_the_good_claim():
    selected = grouped_selection()
    result = decode_model_draft(
        reply(
            selected,
            [
                claim("技術服務費帶動增長", ["e3"], ["g2"], name="bad"),
                claim("理財及支付服務收入增加", ["e1", "e2"], ["g1"], name="good"),
            ],
        ),
        selected=selected,
    )
    assert [c["claim_id"] for c in result["claims"]] == ["good"] and result[
        "status"
    ] == "needs_review"
    assert result["claims"][0]["evidence_ids"] == [
        s.span_id for s in selected.evidence_spans[:2]
    ]


def test_handler_reports_static_group_reason_and_never_builds_a_success_artifact():
    selected = grouped_selection()

    class Model:
        def generate(self, request):
            return reply(selected, [claim("技術服務費收入增長", ["e3"], ["g2"])])

    result = NarrativeSummarizeHandler(model=Model())(_context(selected))
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE and result.result == {}
    assert (
        result.error.code == "SUMMARY_INVALID"
        and "rule=GROUP_INCOMPLETE" in result.error.detail
    )
    assert result.artifacts == () and result.effects == ()


def test_nine_member_complete_atomic_sentence_is_representable_inside_existing_transport_caps():
    selected = grouped_selection(
        tuple(f"新產品完整句第{i}段" for i in range(9)), ("atomic",) * 9
    )
    request = NarrativeModelRequest.from_selection(selected)
    envelope = json.loads(request.data_json)
    schema = envelope["response_schema"]["properties"]["draft"]["properties"]["claims"][
        "items"
    ]
    assert schema["properties"]["evidence_ids"]["maxItems"] >= 9
    result = decode_model_draft(
        reply(
            selected,
            [
                claim(
                    "新產品進展，但合同可能取消。",
                    [f"e{i}" for i in range(1, 10)],
                    ["g1"],
                )
            ],
        ),
        selected=selected,
    )
    assert (
        len(result["claims"][0]["evidence_ids"]) == 9
        and len(json.dumps(result).encode()) < 64 * 1024
    )


def test_public_summary_result_roundtrips_without_new_group_alias_contract():
    selected = grouped_selection()
    response = reply(
        selected, [claim("雲需求及技術服務費帶動增長", ["e3", "e4"], ["g2"])]
    )
    result = NarrativeSummarizeHandler._completed_result(
        selected, selected.prompt_review, response
    )
    raw = result.to_dict()
    restored = NarrativeSummaryResult.from_dict(raw)
    restored.validate_against(selected)
    assert restored.to_dict() == raw and all(
        "evidence_group_ids" not in c for c in raw["draft"]["claims"]
    )


def test_explicit_null_group_declaration_is_malformed_not_a_legacy_absence():
    selected = grouped_selection()
    raw = claim("理財及支付服務收入增加", ["e1", "e2"])
    raw["evidence_group_ids"] = None
    with pytest.raises(
        NarrativeContractError,
        match="summary claim evidence group declaration is invalid",
    ):
        decode_model_draft(reply(selected, [raw]), selected=selected)
    result = decode_model_draft(
        reply(
            selected,
            [raw, claim("雲需求及技術服務費增長", ["e3", "e4"], ["g2"], name="good")],
        ),
        selected=selected,
    )
    assert [c["claim_id"] for c in result["claims"]] == ["good"] and result[
        "status"
    ] == "needs_review"


@pytest.mark.parametrize("ids", [["e1", "e1"], ["e1", "e2", "e3", "e4", "e5", "e1"]])
def test_duplicate_or_overpinned_citations_cannot_satisfy_a_finite_claim_reference_contract(
    ids,
):
    selected = grouped_selection()
    with pytest.raises(NarrativeContractError, match="summary claim evidence IDs"):
        decode_model_draft(
            reply(selected, [claim("業務進展", ids, [])]), selected=selected
        )


def test_prompt_twenty_claim_and_280_character_limits_are_real_output_contracts():
    selected = grouped_selection()
    many = [
        claim("理財及支付服務收入增加", ["e1", "e2"], ["g1"], name=f"c{i}")
        for i in range(21)
    ]
    with pytest.raises(NarrativeContractError, match="summary claims exceed twenty"):
        decode_model_draft(reply(selected, many), selected=selected)
    with pytest.raises(NarrativeContractError, match="summary claim text exceeds 280"):
        decode_model_draft(
            reply(selected, [claim("業" * 281, ["e1", "e2"], ["g1"])]),
            selected=selected,
        )


def test_foreign_id_after_nine_valid_members_is_rejected_without_padding_or_new_source_identity():
    selected = grouped_selection(
        tuple(f"新產品完整句第{i}段" for i in range(9)), ("atomic",) * 9
    )
    before = selected.to_dict()
    for outside in ("e10", "urn:foreign-source:span"):
        with pytest.raises(
            ModelResponseError, match="citation is not in the pinned selection"
        ):
            decode_model_draft(
                reply(
                    selected,
                    [
                        claim(
                            "產品進展",
                            [f"e{i}" for i in range(1, 10)] + [outside],
                            ["g1"],
                        )
                    ],
                ),
                selected=selected,
            )
    assert selected.to_dict() == before


def test_complete_us_group_closure_does_not_remove_ocr_uncertainty_or_borrow_consumer_bullet():
    selected = grouped_selection(
        US_TEXT,
        ("commercial", "commercial", None),
        language="en",
        page=7,
        first_paragraph=8,
        flags=("ocr_used", "layout_ambiguous"),
    )
    result = decode_model_draft(
        reply(
            selected,
            [
                claim(
                    "Microsoft365commercialcloudnowincludesservicespreviouslyreportedinAzure.",
                    ["e1", "e2"],
                    ["g1"],
                )
            ],
        ),
        selected=selected,
    )
    assert (
        result["status"] == "needs_review"
        and result["claims"][0]["needs_review"] is True
    )
    assert result["claims"][0]["evidence_ids"] == [
        s.span_id for s in selected.evidence_spans[:2]
    ]


def test_group_alias_and_canonical_citation_mixing_cannot_create_duplicate_references():
    selected = grouped_selection()
    canonical = selected.evidence_spans[0].span_id
    with pytest.raises(NarrativeContractError, match="summary claim evidence IDs"):
        decode_model_draft(
            reply(selected, [claim("業務進展", ["e1", canonical], [])]),
            selected=selected,
        )
