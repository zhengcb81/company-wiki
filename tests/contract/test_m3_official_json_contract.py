"""M3-JSON contract: declared layouts, source subjects, and projections.

Anchors come from the sealed run (read-only).  The second declared layout is
exercised with a synthetic unseen fixture to prove the mapping is declarative,
not SSE-specific and never company/ticker/page specific.
"""

import json
from pathlib import Path

import pytest

from company_wiki.source_catalog.official_json_structure import (
    JsonStructureLimits,
    parse_json_structure,
)
from company_wiki.source_catalog.official_json_layout import (
    LAYOUT_DTO_SCHEMA,
    OfficialJsonLayoutError,
    describe_layout_page,
    layout_fingerprint,
    registered_layout,
)
from company_wiki.source_catalog.official_json_subject import (
    SourceSubjectError,
    validate_import_request_v2,
    validate_source_subject,
)
from company_wiki.source_catalog.official_json_projection import (
    build_source_projection,
    projection_from_dict,
)
from company_wiki.source_contract.source_manifest import (
    SourceManifest,
    SourceManifestError,
    SourceSubjectManifest,
)

import os

_REVENUE_FORECAST_AUDIT_RUN = (
    Path.home() / "Projects" / "revenue-forecast-audit"
    / "runs" / "m3-20261009T184946-cn-688012")
SEALED_RUN = Path(os.environ.get(
    "M3_SEALED_RUN", str(_REVENUE_FORECAST_AUDIT_RUN)))
SEALED_SOURCES = SEALED_RUN / "execution" / "sources"
SEALED_AVAILABLE = SEALED_SOURCES.is_dir()


def _page(name: str):
    raw = (SEALED_SOURCES / name).read_bytes()
    return parse_json_structure(raw, limits=JsonStructureLimits())


FLAT_LIST_FIXTURE = {
    "ok": True,
    "error_message": None,
    "result": {
        "items": [
            {"ref": "a-1", "org_id": 901, "org_name": "First Org",
             "q": "What is the plan?", "a": "We will expand.",
             "created_at": "2026-01-05 09:00:00", "updated_at": "2026-01-06 10:00:00",
             "answered": True},
            {"ref": "a-2", "org_id": 902, "org_name": "Second Org",
             "q": "Any orders?", "a": None,
             "created_at": "2026-02-01 09:00:00", "updated_at": "2026-02-01 09:00:00",
             "answered": False},
        ],
        "page": 1,
        "page_size": 2,
        "page_count": 4,
        "item_total": 7,
    },
}


# --- declared layout registry ------------------------------------------------


def test_registered_layouts_are_declared_not_hardcoded():
    layout = registered_layout("official-paged-qa")
    assert layout.layout_id == "official-paged-qa"
    assert layout.layout_version == "1.0.0"
    assert layout.collection_pointer == "/datas/0/records"
    assert layout.schema_version == LAYOUT_DTO_SCHEMA
    assert "公司" not in json.dumps(layout.to_dict(), ensure_ascii=False)
    assert "688012" not in json.dumps(layout.to_dict())
    with pytest.raises(OfficialJsonLayoutError) as raised:
        registered_layout("no-such-layout")
    assert raised.value.code == "unsupported_json_layout"


def test_layout_fingerprint_is_stable_and_version_bound():
    first = layout_fingerprint("official-paged-qa")
    second = layout_fingerprint("official-paged-qa")
    assert first == second and len(first) == 64
    assert layout_fingerprint("official-flat-list") != first


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_paged_qa_layout_describes_sealed_latest_page1():
    page = _page("qa-latest-form-01.raw")
    observation = describe_layout_page("official-paged-qa", page)
    assert observation.envelope["success"] is True
    assert observation.envelope["code"] == 200
    assert observation.pagination == {"current": 1, "size": 3, "pages": 65, "total": 195}
    assert [record.provider_record_id for record in observation.records] == [
        2508509, 2508406, 2508409,
    ]
    first, zhongwei, qingyi = observation.records
    assert first.issuer_observed["provider_company_ids"] == []
    assert first.attributed is False
    assert zhongwei.issuer_observed["provider_company_ids"] == [57790]
    assert zhongwei.issuer_observed["provider_activity_company_id"] == 57790
    assert qingyi.issuer_observed["provider_company_ids"] == [57808]
    content = zhongwei.text_fields["content"]
    assert content.locator.startswith("cwp-json-pointer/1|")
    assert content.token_range == (1450, 1810)
    assert content.encoded_token_sha256 == (
        "03201a3fe9d7c08bf1ca81aef677be50c614846ebedf8268ec7fff5ed1fa23b7"
    )


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_paged_qa_layout_reports_translation_fields_separately():
    page = _page("qa-latest-form-18.raw")
    observation = describe_layout_page("official-paged-qa", page)
    record = observation.records[2]
    assert record.provider_record_id == 2508385
    assert record.state["isAnswered"] is True
    assert record.state["questionId"] == 2508367
    # Provider translation fields are located but never become original
    # language answers.
    assert "contentEn" in record.translation_fields
    assert "contentEn" not in record.text_fields


def test_second_declared_layout_maps_unseen_fixture():
    raw = json.dumps(FLAT_LIST_FIXTURE, ensure_ascii=False).encode("utf-8")
    page = parse_json_structure(raw, limits=JsonStructureLimits())
    observation = describe_layout_page("official-flat-list", page)
    assert observation.pagination == {
        "current": 1, "size": 2, "pages": 4, "total": 7,
    }
    assert [record.provider_record_id for record in observation.records] == ["a-1", "a-2"]
    first = observation.records[0]
    assert first.issuer_observed["provider_company_id"] == 901
    assert first.issuer_observed["company_names"] == ["First Org"]
    assert first.text_fields["q"].decoded == "What is the plan?"
    assert first.text_fields["a"].decoded == "We will expand."
    assert "a" not in observation.records[1].text_fields


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_error_payload_control_is_response_error_not_business_evidence():
    raw = (SEALED_SOURCES / "qa-latest-01.raw").read_bytes()
    page = parse_json_structure(raw, limits=JsonStructureLimits())
    observation = describe_layout_page("official-paged-qa", page)
    assert observation.envelope_status == "response_is_error"
    assert observation.business_evidence is False
    assert observation.records == ()


def test_legal_empty_page_is_honest_zero_coverage():
    raw = json.dumps({
        "success": True, "message": "ok", "code": 200,
        "datas": [{"records": [], "total": 0, "size": 3, "current": 1, "pages": 0}],
    }).encode("utf-8")
    page = parse_json_structure(raw, limits=JsonStructureLimits())
    observation = describe_layout_page("official-paged-qa", page)
    assert observation.envelope_status == "ok"
    assert observation.records == ()
    assert observation.pagination["total"] == 0


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_unseen_envelope_shape_is_unsupported_layout_not_guesswork():
    raw = json.dumps({"data": {"rows": [1, 2]}}).encode("utf-8")
    page = parse_json_structure(raw, limits=JsonStructureLimits())
    with pytest.raises(OfficialJsonLayoutError) as raised:
        describe_layout_page("official-paged-qa", page)
    assert raised.value.code in {"layout_pointer_not_found", "unsupported_json_layout"}


# --- source subject -----------------------------------------------------------


def test_multi_issuer_event_subject_validates_with_event_identity():
    subject = validate_source_subject({
        "kind": "multi_issuer_event",
        "event_namespace": "official-provider-event",
        "event_id": "40766",
        "issuer_refs": [
            {"provider_company_id": 145565, "stock_code": "688012",
             "company_name": "中微半导体设备(上海)股份有限公司"},
        ],
        "attribution_status": "partial",
    })
    assert subject.kind == "multi_issuer_event"
    assert subject.event_id == "40766"
    assert subject.attribution_status == "partial"
    assert subject.to_dict()["issuer_refs"][0]["provider_company_id"] == 145565


@pytest.mark.parametrize("payload", [
    {"kind": "residual_pool"},
    {"kind": "multi_issuer_event", "event_namespace": "x"},
    {"kind": "single_issuer", "issuer_refs": []},
    {"kind": "unattributed", "issuer_refs": [{"provider_company_id": 1}]},
    {"kind": "multi_issuer_event", "event_namespace": "e", "event_id": "1",
     "issuer_refs": [{"provider_company_id": 1}], "owner": "someone"},
])
def test_invalid_subjects_are_named_refusals(payload):
    with pytest.raises(SourceSubjectError):
        validate_source_subject(payload)


def test_import_request_v2_shape():
    request = validate_import_request_v2({
        "schema_version": "official-source-import-request/2",
        "request_id": "req-2",
        "max_bytes": 1048576,
        "content_sha256": "a" * 64,
        "mime_type": "application/json",
        "source_subject": {"kind": "unattributed"},
        "capture_receipt": {
            "capture_method": "local_document", "tool_name": "t",
            "tool_call_id": "c", "captured_at": "2026-10-10T00:00:00Z",
            "response_bytes": 10, "content_sha256": "a" * 64,
        },
    })
    assert request.source_subject.kind == "unattributed"
    with pytest.raises(SourceSubjectError):
        validate_import_request_v2({
            "schema_version": "official-source-import-request/1",
            "request_id": "x", "max_bytes": 10, "content_sha256": "a" * 64,
            "mime_type": "application/json",
            "source_subject": {"kind": "unattributed"},
            "capture_receipt": {"capture_method": "m", "tool_name": "t",
                                "tool_call_id": "c",
                                "captured_at": "2026-10-10T00:00:00Z",
                                "response_bytes": 1, "content_sha256": "a" * 64},
        })


# --- manifest 2.0.0 with unknown attribution ----------------------------------


def test_subject_manifest_allows_unknown_attribution_and_keeps_identity():
    manifest = SourceSubjectManifest(
        schema_version="2.0.0",
        source_id="urn:company-wiki:source:sha256:" + "b" * 64,
        subject={"kind": "multi_issuer_event",
                 "event_namespace": "official-provider-event",
                 "event_id": "40766", "issuer_refs": [],
                 "attribution_status": "partial"},
        original_path="companies/_shared/raw/investor_relations/name.json",
        content_sha256="b" * 64,
        mime_type="application/json",
        byte_size=5119,
        collector_name="official-original-import",
        collector_version="2.0.0",
        retrieved_at="2026-10-10T00:00:00Z",
        published_date=None,
    )
    as_dict = manifest.to_dict()
    assert SourceSubjectManifest.from_dict(as_dict).canonical_json() == manifest.canonical_json()
    with pytest.raises(SourceManifestError):
        SourceSubjectManifest.from_dict({**as_dict, "unexpected": 1})


def test_manifest_v1_still_requires_at_least_one_entity():
    payload = {
        "schema_version": "1.0.0",
        "source_id": "urn:company-wiki:source:sha256:" + "c" * 64,
        "entity_ids": [],
        "original_path": "companies/Acme/raw/news/x.md",
        "content_sha256": "c" * 64,
        "source_type": "original_news",
        "published_date": None,
        "retrieved_at": "2026-10-10T00:00:00Z",
        "collector_name": "scanner",
        "collector_version": "1.0.0",
        "mime_type": "text/markdown",
        "byte_size": 10,
        "immutable_status": "verified",
    }
    with pytest.raises(SourceManifestError):
        SourceManifest.from_dict(payload)


# --- projection DTO ------------------------------------------------------------


def _ref(sha: str, size: int):
    return {
        "document_id": "urn:company-wiki:document:sha256:" + sha,
        "source_id": "urn:company-wiki:source:sha256:" + sha,
        "content_sha256": sha,
        "byte_size": size,
        "mime_type": "application/json",
        "schema_version": "2.0",
    }


LATEST_18_SHA = "fc1c2a8ebb7cb44b3cf6f82a5ecfa5641cf81478ed35e615c0928f36a2a389fe"
LATEST_01_SHA = "416542b0c8f72400800edf69832df1bd3b48e50cf19c0019c647af445b97760b"


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_projection_selects_target_issuer_records_with_roles_and_locators():
    page = _page("qa-latest-form-18.raw")
    projection = build_source_projection(
        parent_pages=[(LATEST_18_SHA, 7316, page)],
        layout_id="official-paged-qa",
        issuer={
            "market": "CN",
            "security_id": "688012",
            "provider_company_id": 145565,
            "provider_activity_company_id": 57790,
        },
        as_of_date="2026-09-10",
    )
    assert projection.schema_version == "source-projection-ref/1"
    assert list(projection.parent_source_refs) == [_ref(LATEST_18_SHA, 7316)]
    assert projection.adapter["layout_id"] == "official-paged-qa"
    assert projection.issuer["provider_company_id"] == 145565
    selected = [record for record in projection.records if record.selected]
    assert [record.provider_record_id for record in selected] == [2508385]
    fields = {field.field: field for field in selected[0].fields}
    assert fields["questionContent"].role == "investor_question"
    assert fields["content"].role == "management_answer"
    assert fields["content"].token_range == (5036, 5558)
    assert fields["questionContent"].token_range == (6702, 6767)
    assert selected[0].record_token_sha256 == hash_of(page, "/datas/0/records/2")
    coverage = projection.coverage
    assert coverage["issuer_records_selected"] == 1
    assert coverage["other_issuer_records"] + coverage["unattributed_records"] >= 0


def hash_of(page, pointer):
    node = page.at_pointer(pointer)
    return node.encoded_token_sha256


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_same_parent_page_two_issuer_projections_do_not_conflict():
    page18 = _page("qa-latest-form-18.raw")
    zhongwei = build_source_projection(
        parent_pages=[(LATEST_18_SHA, 7316, page18)],
        layout_id="official-paged-qa",
        issuer={"market": "CN", "security_id": "688012",
                "provider_company_id": 145565,
                "provider_activity_company_id": 57790},
        as_of_date="2026-09-10",
    )
    page01 = _page("qa-latest-form-01.raw")
    qingyi = build_source_projection(
        parent_pages=[(LATEST_01_SHA, 5119, page01)],
        layout_id="official-paged-qa",
        issuer={"market": "CN", "security_id": "688012",
                "provider_company_id": 152341,
                "provider_activity_company_id": 57808},
        as_of_date="2026-09-10",
    )
    assert zhongwei.projection_id != qingyi.projection_id
    assert zhongwei.parent_source_refs[0]["content_sha256"] == LATEST_18_SHA
    assert qingyi.parent_source_refs[0]["content_sha256"] == LATEST_01_SHA


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_projection_is_deterministic_and_roundtrips():
    page = _page("qa-latest-form-18.raw")
    kwargs = dict(
        parent_pages=[(LATEST_18_SHA, 7316, page)],
        layout_id="official-paged-qa",
        issuer={"market": "CN", "security_id": "688012",
                "provider_company_id": 145565,
                "provider_activity_company_id": 57790},
        as_of_date="2026-09-10",
    )
    first = build_source_projection(**kwargs)
    second = build_source_projection(**kwargs)
    assert first.projection_id == second.projection_id
    assert first.projection_sha256 == second.projection_sha256
    restored = projection_from_dict(first.to_dict())
    assert restored.canonical_json() == first.canonical_json()
    # A different as-of changes the projection identity.
    later = build_source_projection(**{**kwargs, "as_of_date": "2026-12-31"})
    assert later.projection_id != first.projection_id


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_questions_are_not_company_statements_and_times_keep_semantics():
    page = _page("qa-questions-form-01.raw")
    projection = build_source_projection(
        parent_pages=[("509bcbcdde98e1ac46464453ed1a7a339134107b67fb5370269639e8192bb2e0",
                      5925, page)],
        layout_id="official-paged-qa",
        issuer={"market": "CN", "security_id": "688012",
                "provider_company_id": 145565,
                "provider_activity_company_id": 57790},
        as_of_date="2026-09-10",
    )
    selected = [record for record in projection.records if record.selected]
    assert selected, "the unanswered question belongs to the issuer page"
    record = selected[0]
    assert record.provider_record_id == 2508424
    field = {field.field: field for field in record.fields}["content"]
    assert field.role == "investor_question"
    assert record.answer_first_publication_known is False
    assert record.times["crtTime"] == "2026-09-10 16:52:58"
    assert record.times["updTime"] == "2026-09-10 17:06:51"


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_precollect_answer_keeps_speaker_unknown_and_independent_fields():
    page = _page("qa-precollect-form-10.raw")
    projection = build_source_projection(
        parent_pages=[("784217fbfdddc06cd53235b3bef8159250b1d4209761092577d35ebb0f313234",
                      3871, page)],
        layout_id="official-paged-qa",
        issuer={"market": "CN", "security_id": "688012",
                "provider_company_id": 145565},
        as_of_date="2026-09-10",
    )
    selected = {record.provider_record_id: record
                for record in projection.records if record.selected}
    record = selected[36395]
    fields = {field.field: field for field in record.fields}
    assert fields["question"].role == "investor_question"
    assert fields["answer"].role == "company_official_answer"
    assert fields["answer"].speaker_known is False
    assert record.answer_first_publication_known is False
    assert fields["answer"].token_range == (2872, 3384)
    assert fields["question"].token_range == (1672, 2862)


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_future_records_are_excluded_from_selection_but_reported():
    page = _page("qa-latest-form-18.raw")
    projection = build_source_projection(
        parent_pages=[(LATEST_18_SHA, 7316, page)],
        layout_id="official-paged-qa",
        issuer={"market": "CN", "security_id": "688012",
                "provider_company_id": 145565,
                "provider_activity_company_id": 57790},
        as_of_date="2026-09-01",
    )
    assert not [record for record in projection.records if record.selected]
    assert projection.coverage["as_of_excluded_records"] >= 1
    assert projection.coverage["issuer_records_selected"] == 0


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_wrong_issuer_proof_refuses_business_projection():
    page = _page("qa-latest-form-18.raw")
    from company_wiki.source_catalog.official_json_projection import (
        ProjectionError,
    )
    with pytest.raises(ProjectionError) as raised:
        build_source_projection(
            parent_pages=[(LATEST_18_SHA, 7316, page)],
            layout_id="official-paged-qa",
            issuer={"market": "CN", "security_id": "688012",
                    "provider_company_id": 999999,
                    "provider_activity_company_id": 57790},
            as_of_date="2026-09-10",
        )
    assert raised.value.code in {"issuer_not_on_page", "mismatched_issuer_proof"}


@pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")
def test_closing_remark_is_statement_not_answered_qa():
    page01 = _page("qa-latest-form-01.raw")
    projection = build_source_projection(
        parent_pages=[(LATEST_01_SHA, 5119, page01)],
        layout_id="official-paged-qa",
        issuer={"market": "CN", "security_id": "688012",
                "provider_company_id": 145565,
                "provider_activity_company_id": 57790},
        as_of_date="2026-09-10",
    )
    selected = {record.provider_record_id: record
                for record in projection.records if record.selected}
    assert 2508406 in selected
    record = selected[2508406]
    content = {field.field: field for field in record.fields}["content"]
    assert content.role == "company_statement"
    assert record.record_kind == "closing_remark"
    assert 2508509 not in selected  # roadshow remark has no issuer fields


def test_projection_export_payload_lists_projections_without_full_records():
    page = _page("qa-latest-form-01.raw") if SEALED_AVAILABLE else None
    if page is None:
        pytest.skip("sealed run not present")
    projection = build_source_projection(
        parent_pages=[(LATEST_01_SHA, 5119, page)],
        layout_id="official-paged-qa",
        issuer={"market": "CN", "security_id": "688012",
                "provider_company_id": 145565,
                "provider_activity_company_id": 57790},
        as_of_date="2026-09-10",
    )
    payload = projection.to_dict()
    encoded = json.dumps(payload, ensure_ascii=False)
    # Records carry locators and identity, never a second full-text copy of
    # the parent page.
    assert "records" in payload
    assert len(encoded) < 5119 * 2
