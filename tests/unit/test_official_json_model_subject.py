"""Projection model data and citations preserve subject and per-field roles."""

from copy import deepcopy
import hashlib
import json

import pytest

from company_wiki.automation import narrative_model as model
from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_contracts import (
    NarrativeSelectResult,
    NarrativeContractError,
)
from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan


def binding():
    parents = [
        {
            "schema_version": "2.0",
            "document_id": "doc-" + m,
            "source_id": "urn:company-wiki:source:sha256:" + m * 64,
            "content_sha256": m * 64,
            "byte_size": 123,
            "mime_type": "application/json",
        }
        for m in ("a", "b")
    ]
    return {
        "kind": "official_json",
        "item_key": "urn:company-wiki:source-projection:sha256:" + "c" * 64,
        "subject_sha256": "c" * 64,
        "parent_source_refs": parents,
        "issuer": {
            "provider_company_id": 901,
            "canonical_name": "First Org",
            "market": "CN",
        },
        "as_of_date": "2026-10-10",
        "adapter": {
            "parser": "cwp_official_json/1.0.1",
            "structure_parser_version": "1.0.1",
            "layout_id": "official-flat-list",
            "layout_version": "1.0.0",
            "layout_fingerprint": "d" * 64,
        },
        "coverage": {
            "pagination_complete": True,
            "page_envelope_complete": True,
            "pages": [{"records": 1}, {"records": 1}],
            "diagnostics": [],
        },
    }


def selection(
    *,
    subject=None,
    language="en",
    empty=False,
    skipped=False,
    flags=(),
    same_groups=False,
):
    subject = deepcopy(subject or binding())
    spans = []
    if not empty and not skipped:
        for index, (parent, role, text) in enumerate(
            [
                (
                    0,
                    "investor_question",
                    "Has the company launched new products overseas?",
                ),
                (0, "management", "We launched a new product for overseas customers."),
                (1, "management", "We expanded our customer qualification capacity."),
            ]
        ):
            spans.append(
                EvidenceSpan.create(
                    source_id=subject["parent_source_refs"][parent]["source_id"],
                    coordinates=EvidenceCoordinates(paragraph_index=index),
                    raw_text=text,
                    structured_value={
                        "source_role": role,
                        "language": language,
                        "selection_group_id": "shared-label"
                        if same_groups
                        else "record-a"
                        if parent == 0
                        else "record-b",
                        "record_pointer": "/data/0",
                        "field_pointer": "/data/0/" + str(index),
                        "projection_id": subject["item_key"],
                        "parent_content_sha256": subject["parent_source_refs"][parent][
                            "content_sha256"
                        ],
                    },
                    parser_name="cwp_official_json",
                    parser_version="1.0.1",
                    parse_status="parsed",
                    quality_flags=flags,
                ).to_dict()
            )
    return NarrativeSelectResult.from_dict(
        {
            "schema_version": "narrative-select-result/3.0",
            "subject_binding": subject,
            "source_metadata": {
                "source_class": "official_json",
                "title": "Official business Q&A",
                "document_kind": "investor_relations",
                "language": language,
            },
            "parser": {"name": "cwp_official_json", "version": "1.0.1"},
            "selector": {"name": "narrative-selector", "version": "1.3.0"},
            "selection": {
                "status": "skipped_no_narrative"
                if skipped
                else "partial"
                if empty
                else "selected",
                "coverage_complete": not empty,
                "source_units": 3,
                "candidate_count": len(spans),
                "selected_count": len(spans),
                "omitted_candidate_count": 0,
                "dropped_financial_count": 0,
                "pages_total": 0,
                "pages_read": 0,
                "lines_total": 0,
                "tables_total": 0,
                "tables_scanned": 0,
            },
            "evidence_spans": spans,
            "prompt_review": {
                "status": "not_reviewed",
                "source_sha256": None,
                "evidence_sha256": None,
                "policy_hash": None,
                "reviewed_at": None,
            },
            "summary_scope": "selected_evidence_only",
        }
    )


def claim(*, ids=None, kind="company_statement", modality="actual", groups=None):
    value = {
        "claim_id": "claim-one",
        "text": "The company launched an overseas product.",
        "evidence_ids": ids or ["e2"],
        "claim_type": kind,
        "modality": modality,
    }
    if groups is not None:
        value["evidence_group_ids"] = groups
    return value


def response(selected, *, claims=None, prompt=None, **overrides):
    header = {
        "subject_id": selected.subject.item_key,
        "subject_sha256": selected.subject.subject_sha256,
        "language": selected.source_metadata.language,
        "claims": claims or [claim()],
    }
    header.update(overrides)
    return model.NarrativeModelResponse(
        "fixture",
        "configured-flash",
        prompt or "official-json/1.0.0",
        canonical_json({"draft": header}).encode("utf-8"),
    )


def test_projection_versions_are_explicit_and_raw_versions_unchanged():
    assert model.PROJECTION_MODEL_REQUEST_SCHEMA == "narrative-model-request/2"
    assert model.PROJECTION_NARRATIVE_PROMPT_VERSION == "official-json/1.0.0"
    assert model.MODEL_REQUEST_SCHEMA == "narrative-model-request/1.4"
    assert model.NARRATIVE_PROMPT_VERSION == "1.7.0"


def test_subject_header_is_explicit_multi_parent_and_no_fake_raw_identity():
    selected = selection()
    before = selected.to_dict()
    request = model.NarrativeModelRequest.from_selection(selected)
    data = json.loads(request.data_json)
    assert data["schema_version"] == "narrative-model-request/2"
    assert request.prompt_version == "official-json/1.0.0"
    assert data["subject"] == {
        "subject_id": selected.subject.item_key,
        "subject_sha256": selected.subject.subject_sha256,
        "language": "en",
        "title": "Official business Q&A",
        "document_kind": "investor_relations",
    }
    assert "source" not in data
    assert set(data["response_schema"]["properties"]["draft"]["required"]) == {
        "subject_id",
        "subject_sha256",
        "language",
        "claims",
    }
    assert selected.to_dict() == before
    assert len({s.source_id for s in selected.evidence_spans}) == 2


@pytest.mark.parametrize(
    "mutation", ["issuer", "as_of", "parent_two", "layout", "parser"]
)
def test_full_subject_binding_changes_model_request_even_if_same_anchor_and_text(
    mutation,
):
    original = selection()
    changed = binding()
    if mutation == "issuer":
        changed["issuer"]["provider_company_id"] = 902
    elif mutation == "as_of":
        changed["as_of_date"] = "2026-10-09"
    elif mutation == "layout":
        changed["adapter"]["layout_version"] = "1.0.2"
    elif mutation == "parser":
        changed["adapter"]["structure_parser_version"] = "1.0.2"
    else:
        changed["parent_source_refs"][1]["byte_size"] = 124
    other = selection(subject=changed)
    assert original.source_ref.to_dict() == other.source_ref.to_dict()
    assert (
        model.NarrativeModelRequest.from_selection(original).input_sha256
        != model.NarrativeModelRequest.from_selection(other).input_sha256
    )


def test_rows_preserve_every_field_role_and_groups_only_list_members():
    data = json.loads(model.NarrativeModelRequest.from_selection(selection()).data_json)
    roles = [
        row[2] if len(row) > 2 else data["default_source_role"]
        for row in data["evidence"]
    ]
    assert roles == ["investor_question", "management", "management"]
    assert data["evidence_group_columns"] == ["id", "evidence_ids"]
    assert data["evidence_groups"] == [["g1", ["e1", "e2"]], ["g2", ["e3"]]]
    assert all(len(row) == 2 for row in data["evidence_groups"])
    assert (
        "question"
        in model.NarrativeModelRequest.from_selection(selection()).instruction.lower()
    )


def test_alias_restore_uses_actual_parent_spans_and_question_preserves_modality():
    selected = selection()
    claims = [
        claim(ids=["e1"], kind="analyst_question", modality="question"),
        dict(claim(ids=["e3"]), claim_id="claim-two"),
    ]
    draft = model.decode_model_draft(
        response(selected, claims=claims), selected=selected
    )
    assert draft["subject_id"] == selected.subject.item_key and "source_id" not in draft
    assert draft["claims"][0]["evidence_ids"] == [selected.evidence_spans[0].span_id]
    assert draft["claims"][1]["evidence_ids"] == [selected.evidence_spans[2].span_id]
    assert draft["claims"][0]["modality"] == "question"


@pytest.mark.parametrize(
    "ids,kind,modality,groups,message",
    [
        (["e1"], "company_statement", "actual", [], "non-company evidence"),
        (["e1", "e2"], "company_statement", "actual", ["g1"], "non-company evidence"),
        (["e1"], "analyst_question", "actual", [], "question modality"),
        (
            ["not-a-citation"],
            "company_statement",
            "actual",
            [],
            "not in the pinned selection",
        ),
        (["e2"], "company_statement", "actual", ["g1"], "group coverage is incomplete"),
    ],
)
def test_invalid_roles_and_context_closure_reject_whole_claim(
    ids, kind, modality, groups, message
):
    selected = selection()
    with pytest.raises(
        (NarrativeContractError, model.ModelResponseError), match=message
    ):
        model.decode_model_draft(
            response(
                selected,
                claims=[claim(ids=ids, kind=kind, modality=modality, groups=groups)],
            ),
            selected=selected,
        )


def test_narrow_answer_is_allowed_but_partial_context_and_quality_are_diagnostics():
    selected = selection(flags=("locator_unstable",))
    draft = model.decode_model_draft(
        response(selected, claims=[claim(groups=[])]), selected=selected
    )
    assert draft["status"] == "needs_review"
    assert draft["claims"][0]["needs_review"] is True
    assert draft["claims"][0]["evidence_ids"] == [selected.evidence_spans[1].span_id]


@pytest.mark.parametrize(
    "override",
    [
        {"subject_id": "different-subject"},
        {"subject_sha256": "f" * 64},
        {"language": "zh"},
    ],
)
def test_global_subject_identity_mismatch_cannot_be_recovered_per_claim(override):
    selected = selection()
    with pytest.raises(NarrativeContractError):
        model.decode_model_draft(response(selected, **override), selected=selected)


def test_decoder_expected_prompt_depends_on_subject_and_rejects_raw_prompt():
    selected = selection()
    assert model.decode_model_draft(response(selected), selected=selected)["claims"]
    with pytest.raises(model.ModelResponseError, match="prompt version"):
        model.decode_model_draft(
            response(selected, prompt=model.NARRATIVE_PROMPT_VERSION), selected=selected
        )


def test_unknown_extensions_drop_but_translation_rejected_globally():
    selected = selection()
    draft = model.decode_model_draft(
        response(selected, provider_secret="not-persisted"), selected=selected
    )
    assert "provider_secret" not in draft
    with pytest.raises(model.ModelResponseError, match="untranslated"):
        model.decode_model_draft(response(selected, translate=True), selected=selected)


def test_configured_output_budget_applies_to_new_schema_without_model_call():
    request = model.NarrativeModelRequest.from_selection(selection())
    bound = request.with_output_budget(1200)
    assert (
        json.loads(bound.data_json)["output_plan"]["configured_output_tokens"] == 1200
    )
    assert bound.input_sha256 != request.input_sha256
    assert bound.with_output_budget(1200) == bound


@pytest.mark.parametrize("options", [{"empty": True}, {"language": "unknown"}])
def test_no_model_request_without_evidence_or_real_language(options):
    with pytest.raises(model.ModelResponseError, match="SUMMARY_INPUT_UNAVAILABLE"):
        model.NarrativeModelRequest.from_selection(selection(**options))


@pytest.mark.parametrize("language", ["zh", "en", "mixed"])
def test_actual_language_bound_to_request_and_draft(language):
    selected = selection(language=language)
    request = model.NarrativeModelRequest.from_selection(selected)
    assert json.loads(request.data_json)["subject"]["language"] == language
    assert (
        model.decode_model_draft(response(selected), selected=selected)["language"]
        == language
    )


def test_same_record_group_label_on_two_parents_cannot_merge_context():
    selected = selection(same_groups=True)
    request = model.NarrativeModelRequest.from_selection(selected)
    assert json.loads(request.data_json)["evidence_groups"] == [
        ["g1", ["e1", "e2"]],
        ["g2", ["e3"]],
    ]
    draft = model.decode_model_draft(
        response(selected, claims=[claim(ids=["e3"], groups=["g2"])]), selected=selected
    )
    assert draft["claims"][0]["evidence_ids"] == [selected.evidence_spans[2].span_id]
    assert draft["claims"][0]["needs_review"] is False


def test_explicit_complete_mixed_role_group_never_uses_first_role_as_company_statement():
    selected = selection()
    draft = model.decode_model_draft(
        response(
            selected,
            claims=[
                claim(
                    ids=["e1", "e2"],
                    kind="uncertain",
                    modality="uncertain",
                    groups=["g1"],
                )
            ],
        ),
        selected=selected,
    )
    assert draft["claims"][0]["claim_type"] == "uncertain"
    assert draft["claims"][0]["needs_review"] is True
    assert draft["claims"][0]["evidence_ids"] == [
        s.span_id for s in selected.evidence_spans[:2]
    ]


def test_existing_http_adapter_serializes_projection_prompt_and_configured_limit_offline():
    from company_wiki.automation.narrative_http_model import NarrativeHTTPModel

    selected = selection()
    request = model.NarrativeModelRequest.from_selection(selected)
    adapter = NarrativeHTTPModel(
        model_id="configured-flash",
        endpoint="https://example.invalid/v1/chat/completions",
        api_key_env="UNUSED_TEST_KEY",
        max_output_tokens=1200,
    )
    body = json.loads(adapter.request_bytes(request))
    assert body["model"] == "configured-flash" and body["max_tokens"] == 1200
    data = json.loads(body["messages"][1]["content"])
    assert data["schema_version"] == "narrative-model-request/2"
    assert data["subject"]["subject_id"] == selected.subject.item_key
    assert data["output_plan"]["configured_output_tokens"] == 1200
    assert body["messages"][0]["content"] == request.instruction


_RAW_BEFORE = [
    {
        "count": 1,
        "role": "company_filing",
        "flags": [],
        "prompt_version": "1.7.0",
        "input_sha256": "62335658a349f454f5bc0ac701b4ca78185e69ae4ca8b4cac5254c006ccc2e1f",
        "data_sha256": "6fcd741b867c9af85c36719a68857ec15dd04c9d358a849535062c92aa1f9c56",
        "instruction_sha256": "3fe540d3e9977921c42aeaf5c73e6952975991096cc7942db9ab4f932b6b5255",
        "draft_sha256": "e2600747e64ccad2cb1193c57a2301516c9fe07aac447d72a017539ea0aeda93",
    },
    {
        "count": 3,
        "role": "analyst",
        "flags": ["locator_unstable"],
        "prompt_version": "1.7.0",
        "input_sha256": "a3632680ba09c8a600b9d78efa43554173dac945e38cf8d05acb9ea7e8c928fd",
        "data_sha256": "7ed74c3dbe44f43ee8a39e02717a60e8144280533f63bdd8894faba9b3a4cdd4",
        "instruction_sha256": "3fe540d3e9977921c42aeaf5c73e6952975991096cc7942db9ab4f932b6b5255",
        "draft_sha256": "b527469b4a6e48e30b47d7fa4922ca9bdb2e798905f8d73e3c6e5fbd6356861f",
    },
    {
        "count": 160,
        "role": "company_filing",
        "flags": [],
        "prompt_version": "1.7.0",
        "input_sha256": "2508a64812acff984a413e060e54285902ca35f4807ec1e213687d8a8e7c34d4",
        "data_sha256": "92e5b7862e867b78782baf2aabd997a786f21d21b5fffc9f846552cfc5f1cb70",
        "instruction_sha256": "3fe540d3e9977921c42aeaf5c73e6952975991096cc7942db9ab4f932b6b5255",
        "draft_sha256": "e2600747e64ccad2cb1193c57a2301516c9fe07aac447d72a017539ea0aeda93",
    },
]


@pytest.mark.parametrize("expected", _RAW_BEFORE)
def test_original_raw_model_input_and_decoder_remain_byte_canonical(expected):
    from support.narrative_model_request_fixture import (
        selection as raw_selection,
        response_draft,
    )

    selected = raw_selection(
        expected["count"], role=expected["role"], flags=tuple(expected["flags"])
    )
    request = model.NarrativeModelRequest.from_selection(selected)
    raw = model.NarrativeModelResponse(
        "fixture",
        "fixture",
        model.NARRATIVE_PROMPT_VERSION,
        canonical_json(response_draft(json.loads(request.data_json))).encode(),
    )
    draft = model.decode_model_draft(raw, selected=selected)
    assert request.prompt_version == expected["prompt_version"]
    assert request.input_sha256 == expected["input_sha256"]
    assert (
        hashlib.sha256(request.data_json.encode()).hexdigest()
        == expected["data_sha256"]
    )
    assert (
        hashlib.sha256(request.instruction.encode()).hexdigest()
        == expected["instruction_sha256"]
    )
    assert (
        hashlib.sha256(canonical_json(draft).encode()).hexdigest()
        == expected["draft_sha256"]
    )
