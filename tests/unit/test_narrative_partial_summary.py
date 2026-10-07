"""R6 recovers individual model claims; canonical source contracts stay strict."""

from copy import deepcopy
import json

import pytest

from company_wiki.automation.narrative_contracts import (
    NarrativeContractError, NarrativeSummaryResult,
)
from company_wiki.automation.narrative_model import (
    NARRATIVE_PROMPT_VERSION, ModelResponseError, NarrativeModelResponse,
)
from company_wiki.automation.narrative_summarize import (
    NarrativeSummarizeHandler, _SummaryFailure,
)
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from support.narrative_model_request_fixture import selection


def _claim(claim_id="good", evidence_ids=None):
    return {"claim_id": claim_id, "text": "公司已完成海外客户认证。",
            "evidence_ids": ["e1"] if evidence_ids is None else evidence_ids,
            "claim_type": "company_statement", "modality": "planned", "needs_review": False}


def _payload(selected, claims):
    return {"draft": {"source_id": selected.source_ref.source_id,
                      "source_sha256": selected.source_ref.content_sha256,
                      "language": selected.source_metadata.language,
                      "claims": claims, "status": "draft"}}


def _complete(selected, payload):
    response = NarrativeModelResponse("offline-r6", "offline-r6", NARRATIVE_PROMPT_VERSION,
                                      json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                      input_tokens=7, output_tokens=11)
    return NarrativeSummarizeHandler._completed_result(selected, selected.prompt_review, response)


@pytest.mark.parametrize("bad", [
    _claim("bad", ["e404"]),
    _claim("bad", ["e1", "e404"]),
    {**_claim("bad"), "text": " "},
    {**_claim("bad"), "evidence_ids": []},
    {**_claim("bad"), "evidence_ids": "e1"},
    {**_claim("bad"), "claim_type": "analyst_question", "modality": "question"},
    {**_claim("bad"), "claim_type": "invented_type"},
    {**_claim("bad"), "modality": "invented_modality"},
    {**_claim("bad"), "needs_review": "false"},
    {k: v for k, v in _claim("bad").items() if k != "text"},
    "not a claim",
], ids=["unknown", "mixed-citations", "blank", "no-citations", "bad-citation-shape",
        "wrong-role", "bad-type", "bad-modality", "bad-review-type",
        "missing-field", "scalar"])
def test_one_bad_claim_preserves_valid_claim_and_visible_quality(bad):
    selected = selection(2)
    before = selected.to_dict()
    payload = _payload(selected, [_claim(), deepcopy(bad)])
    result = _complete(selected, payload)
    result.validate_against(selected)
    assert result.draft is not None and result.draft.status == "needs_review"
    assert len(result.draft.claims) == 1
    claim = result.draft.claims[0]
    assert claim.claim_id == "good" and claim.text == _claim()["text"]
    assert claim.modality == "planned" and claim.needs_review is False
    assert claim.evidence_ids == (selected.evidence_spans[0].span_id,)
    bundle = NarrativeVerifyHandler._bundle(selected, result, selected.prompt_review)
    assert bundle.quality_status == "needs_review"  # Compatible partial-summary diagnostic.
    assert bundle.selection == selected.selection
    assert bundle.evidence_spans == selected.evidence_spans
    assert selected.to_dict() == before


def test_ambiguous_duplicate_ids_are_dropped_without_renaming_or_discarding_good_claim():
    selected = selection(2)
    result = _complete(selected, _payload(selected, [_claim(), _claim("duplicate"),
                                                  _claim("duplicate", ["e2"])]))
    assert result.draft is not None and result.draft.status == "needs_review"
    assert [c.claim_id for c in result.draft.claims] == ["good"]


@pytest.mark.parametrize("level", ["root", "draft", "claim"])
def test_unused_provider_extra_is_ignored_without_persisting_key_or_value(level):
    selected = selection()
    payload = _payload(selected, [_claim()])
    target = payload if level == "root" else payload["draft"] if level == "draft" else payload["draft"]["claims"][0]
    target["secret-provider-field-do-not-log"] = {"opaque-provider-body": "unused"}
    result = _complete(selected, payload)
    result.validate_against(selected)
    assert result.draft is not None and result.draft.status == "draft"
    encoded = json.dumps(result.to_dict(), ensure_ascii=False)
    assert "secret-provider-field" not in encoded and "opaque-provider-body" not in encoded


@pytest.mark.parametrize("field,value", [
    ("source_id", "wrong-source"), ("source_sha256", "0" * 64),
    ("source_sha256", "not-a-sha"), ("language", "en"),
    ("status", "completed"), ("claims", []), ("claims", "not-an-array"),
])
def test_global_source_or_shape_errors_cannot_be_salvaged(field, value):
    selected = selection()
    payload = _payload(selected, [_claim()])
    payload["draft"][field] = value
    with pytest.raises((ModelResponseError, NarrativeContractError, _SummaryFailure)):
        _complete(selected, payload)


@pytest.mark.parametrize("level", ["root", "draft", "claim"])
def test_explicit_translation_request_is_not_an_ignorable_extension(level):
    selected = selection()
    payload = _payload(selected, [_claim()])
    target = payload if level == "root" else payload["draft"] if level == "draft" else payload["draft"]["claims"][0]
    target["translate"] = True
    with pytest.raises((ModelResponseError, NarrativeContractError, _SummaryFailure)):
        _complete(selected, payload)


def test_no_usable_claim_does_not_publish_an_empty_or_fabricated_summary():
    selected = selection()
    with pytest.raises((ModelResponseError, NarrativeContractError, _SummaryFailure)):
        _complete(selected, _payload(selected, [_claim("bad", ["e404"])]))


def test_canonical_reader_still_rejects_unknown_fields():
    selected = selection()
    result = _complete(selected, _payload(selected, [_claim()])).to_dict()
    result["draft"]["unused"] = "must-not-enter-public-wire"
    with pytest.raises(NarrativeContractError):
        NarrativeSummaryResult.from_dict(result)


def test_question_role_cannot_be_marked_actual_in_the_canonical_contract():
    selected = selection(role="analyst")
    value = _payload(selected, [{**_claim(), "claim_type": "analyst_question", "modality": "actual"}])["draft"]
    value["claims"][0]["evidence_ids"] = [selected.evidence_spans[0].span_id]
    result = NarrativeSummaryResult.from_dict({
        "schema_version": "narrative-summary-result/2.0", "source_ref": selected.source_ref.to_dict(),
        "language": "zh", "translate": False, "status": "completed", "draft": value,
        "model": {"adapter_id": "offline", "model_id": "offline", "prompt_version": NARRATIVE_PROMPT_VERSION,
                  "response_sha256": "1" * 64}, "prompt_review": selected.prompt_review.to_dict(),
    })
    with pytest.raises(NarrativeContractError):
        result.validate_against(selected)


def test_old_long_summary_policy_is_not_a_reader_rejection_threshold():
    selected = selection()
    claims = [{**_claim(str(i)), "text": "来源已说明新业务项目进展。" * 40} for i in range(25)]
    result = _complete(selected, _payload(selected, claims))
    assert result.draft is not None and len(result.draft.claims) == 25
    assert result.draft.status == "draft"


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_non_json_numeric_extensions_are_not_accepted_as_harmless_fields(literal):
    from company_wiki.automation.narrative_model import decode_model_draft

    selected = selection()
    payload = json.dumps(_payload(selected, [_claim()]))
    response_bytes = (payload[:-1] + ',"unused":' + literal + '}').encode()
    response = NarrativeModelResponse("offline", "offline", NARRATIVE_PROMPT_VERSION, response_bytes)
    with pytest.raises(ModelResponseError):
        decode_model_draft(response, selected=selected)
