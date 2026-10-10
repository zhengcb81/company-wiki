"""The AUTO adapter consumes one verified source export, without source reapproval."""
import hashlib
import json

import pytest

from company_wiki.automation import narrative_official_json as adapter
from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.source_catalog.official_json_projection import (
    ProjectionError, build_source_projection, evidence_span_for_field,
)
from company_wiki.source_catalog.official_json_structure import parse_json_structure


CHINESE_UPDATE = "公司新产品已经完成客户验证，预计第四季度开始批量交付，海外订单持续增长。"
QUESTION = "新产品客户验证和海外交付计划目前进展如何？"


def source_export(*, translation=True, answered=True, complete=True, only_empty=False, native_text=CHINESE_UPDATE):
    # Actual declared source parser and roles; only catalog persistence is outside this unit.
    record = {"id": 9, "companyId": 1, "isAnswered": answered,
              "crtTime": "2026-09-01 10:00:00", "updTime": "2026-09-02 10:00:00"}
    if not only_empty:
        record.update({"content": native_text, "questionContent": QUESTION})
        if translation:
            record["contentEn"] = "The overseas product shipment pipeline has grown rapidly. " * 20
    raw = json.dumps({"success": True, "code": 200, "datas": [{
        "current": 1, "size": 1, "pages": 1 if complete else 2,
        "total": 1 if complete else 2, "records": [record]}]},
        ensure_ascii=False, separators=(",", ":")).encode()
    doc = parse_json_structure(raw)
    sha = hashlib.sha256(raw).hexdigest()
    projection = build_source_projection(parent_pages=[(sha, len(raw), doc)],
        layout_id="official-paged-qa", issuer={"provider_company_id": 1}, as_of_date="2026-10-08")
    spans = []
    # Use source's real field constructor and lexical ordinals, not a fake JSON parser.
    strings = []
    def walk(node):
        if node.kind == "string":
            strings.append(node.pointer)
        elif node.kind == "object":
            for child in node.members().values():
                walk(child)
        elif node.kind == "array":
            for child in node.items():
                walk(child)
    walk(doc.root)
    for item in projection.records:
        if not item.selected:
            continue
        for binding in item.fields:
            pointer = item.record_pointer + "/" + binding.field
            spans.append(evidence_span_for_field(projection, item, binding,
                paragraph_index=strings.index(pointer) + 1,
                decoded_text=doc.at_pointer(pointer).decoded).to_dict())
    payload = {"schema_version": "source-projection-export/1",
        "source_refs": [dict(ref) for ref in projection.parent_source_refs],
        "projection": projection.to_dict(), "evidence_spans": spans,
        "counts": {"source_refs": 1, "evidence_spans": len(spans), "selected_records": 1}}
    sha = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    payload.update(bundle_sha256=sha, export_id="urn:company-wiki:source-projection-export:sha256:" + sha)
    return projection, payload


def open_fixture(monkeypatch, **kwargs):
    projection, payload = source_export(**kwargs)
    calls = []
    monkeypatch.setattr(adapter, "load_projection", lambda catalog, identity:
        calls.append(("load", catalog, identity)) or projection)
    monkeypatch.setattr(adapter, "build_projection_export", lambda catalog, value:
        calls.append(("export", catalog, value.projection_id)) or payload)
    catalog = object()
    view = adapter.open_verified_projection(catalog, projection_id=projection.projection_id,
        expected_projection_sha256=projection.projection_sha256)
    return view, projection, payload, calls, catalog


def test_consumes_exactly_one_export_and_uses_neutral_subject(monkeypatch):
    view, projection, _payload, calls, catalog = open_fixture(monkeypatch)
    assert [entry[0] for entry in calls] == ["load", "export"]
    assert all(entry[1] is catalog for entry in calls)
    assert isinstance(view.subject, NarrativeSubject)
    assert view.subject.item_key == projection.projection_id
    assert view.subject.subject_sha256 == projection.projection_sha256
    assert view.subject.parent_source_refs == projection.parent_source_refs
    assert view.language == "zh", "JSON keys and provider translation cannot change native language"
    assert view.coverage_complete is True
    assert {span.structured_value["role"] for span in view.evidence_spans} == {
        "management_answer", "investor_question"}


def test_export_input_and_all_returned_context_are_deeply_detached(monkeypatch):
    view, projection, payload, _calls, _catalog = open_fixture(monkeypatch)
    original = view.export_dict()
    payload["projection"]["issuer"]["provider_company_id"] = 999
    payload["projection"]["coverage"]["pages"][0]["pagination"]["pages"] = 999
    payload["evidence_spans"][0]["raw_text"] = "mutated"
    with pytest.raises(TypeError):
        projection.issuer["provider_company_id"] = 888
    exported = view.export_dict()
    exported["projection"]["issuer"]["provider_company_id"] = 777
    exported["source_refs"][0]["byte_size"] = 0
    metadata = view.adapter
    metadata["layout_id"] = "invented"
    issuer = view.subject.issuer
    issuer["provider_company_id"] = 666
    assert view.export_dict() == original
    assert view.adapter["layout_id"] == "official-paged-qa"
    assert view.subject.issuer["provider_company_id"] == 1
    with pytest.raises(TypeError):
        view.evidence_spans[0].structured_value["role"] = "management_answer"


def test_wrong_expected_projection_hash_never_exports(monkeypatch):
    projection, _ = source_export()
    monkeypatch.setattr(adapter, "load_projection", lambda *_: projection)
    def forbidden(*_):
        raise AssertionError("mismatched identity must not reach export")
    monkeypatch.setattr(adapter, "build_projection_export", forbidden)
    with pytest.raises(adapter.OfficialProjectionAdapterError, match="projection_hash_mismatch"):
        adapter.open_verified_projection(object(), projection_id=projection.projection_id,
            expected_projection_sha256="0" * 64)


@pytest.mark.parametrize("sha", ["", "A" * 64, "0" * 63, None, 5])
def test_invalid_hash_is_named_before_source_calls(monkeypatch, sha):
    monkeypatch.setattr(adapter, "load_projection", lambda *_:
        pytest.fail("invalid request must not load source"))
    with pytest.raises(adapter.OfficialProjectionAdapterError, match="invalid_projection_identity"):
        adapter.open_verified_projection(object(), projection_id="urn:company-wiki:source-projection:sha256:" + "1" * 64,
            expected_projection_sha256=sha)


def test_source_port_refusal_is_preserved_without_transcript_fallback(monkeypatch):
    def refused(*_):
        raise ProjectionError("unsupported_json_layout")
    monkeypatch.setattr(adapter, "load_projection", refused)
    with pytest.raises(ProjectionError, match="unsupported_json_layout"):
        adapter.open_verified_projection(object(), projection_id="urn:company-wiki:source-projection:sha256:" + "1" * 64,
            expected_projection_sha256="1" * 64)


def test_no_native_fields_have_no_guessed_language_or_summary(monkeypatch):
    view, *_ = open_fixture(monkeypatch, only_empty=True)
    assert view.language is None
    assert view.evidence_spans == ()
    def forbidden(*_args, **_kwargs):
        raise AssertionError("empty/undetermined source must not run selector or model")
    package = adapter.select_verified_projection(view, title="Investor relations", selector=forbidden)
    assert not package.evidence_spans
    assert package.status == "skipped_no_narrative"
    assert package.coverage_complete is True


def test_partial_coverage_is_never_promoted_by_nonempty_units(monkeypatch):
    view, *_ = open_fixture(monkeypatch, complete=False)
    package = adapter.select_verified_projection(view, title="公司投资者关系活动记录")
    assert package.evidence_spans
    assert package.coverage_complete is False
    assert package.status == "partial"


def test_each_qa_field_retains_its_role_and_stable_record_link(monkeypatch):
    view, *_ = open_fixture(monkeypatch)
    package = adapter.select_verified_projection(view, title="公司投资者关系活动记录")
    by_role = {span.structured_value["role"]: span for span in package.evidence_spans}
    assert {"management_answer", "investor_question"} <= by_role.keys()
    answer, question = by_role["management_answer"], by_role["investor_question"]
    assert answer.structured_value["source_role"] == "management"
    assert question.structured_value["source_role"] == "investor_question"
    assert answer.structured_value["language"] == question.structured_value["language"] == "zh"
    assert answer.structured_value["qa_group_id"] == question.structured_value["qa_group_id"]
    assert answer.structured_value["speaker_known"] is False
    assert question.raw_text == QUESTION
    assert answer.raw_text == CHINESE_UPDATE
    assert all(not span.structured_value.get("selection_group_id") for span in package.evidence_spans)
    assert all("provider_translation" not in span.structured_value["role"] for span in package.evidence_spans)
    original_by_pointer = {span.structured_value["pointer"]: span for span in view.evidence_spans}
    for span in package.evidence_spans:
        original = original_by_pointer[span.structured_value["pointer"]]
        assert span.source_id == original.source_id
        assert span.coordinates == original.coordinates
        assert span.structured_value["source_locator"] == original.structured_value["source_locator"]
        assert span.structured_value["decoded_sha256"] == original.structured_value["decoded_sha256"]
        assert span.structured_value["source_evidence_id"] == original.structured_value["source_evidence_id"]


def test_view_rejects_nonfinite_export_instead_of_retaining_json_nan(monkeypatch):
    projection, payload = source_export()
    payload["projection"]["coverage"]["unexpected"] = float("nan")
    monkeypatch.setattr(adapter, "load_projection", lambda *_: projection)
    monkeypatch.setattr(adapter, "build_projection_export", lambda *_: payload)
    with pytest.raises(adapter.OfficialProjectionAdapterError, match="invalid_projection_export"):
        adapter.open_verified_projection(object(), projection_id=projection.projection_id,
            expected_projection_sha256=projection.projection_sha256)


def test_real_selector_still_uses_legacy_pdf_txt_entrypoint():
    from company_wiki.source_catalog.narrative_evidence import parse_transcript_text, select_narrative_evidence
    raw = ("Full Conference Call Transcript\nCEO: Our new product has completed customer qualification and overseas shipments "
           "will begin in the fourth quarter. We are expanding production capacity.\n").encode()
    sha = hashlib.sha256(raw).hexdigest()
    parsed = parse_transcript_text(raw.decode(), source_id="urn:company-wiki:source:sha256:" + sha,
        source_sha256=sha, language="en")
    package = select_narrative_evidence(parsed, title="Earnings call", existing_kind="investor_call_transcript")
    assert package.evidence_spans
    assert all(span.parser_name != "cwp_official_json" for span in package.evidence_spans)


def test_whitespace_display_keeps_original_json_binding(monkeypatch):
    view, *_ = open_fixture(monkeypatch, native_text="  " + CHINESE_UPDATE + "  ")
    package = adapter.select_verified_projection(view, title="公司投资者关系活动记录")
    answer = next(span for span in package.evidence_spans
                  if span.structured_value["role"] == "management_answer")
    assert answer.raw_text == "  " + CHINESE_UPDATE + "  "
    assert answer.structured_value["decoded_sha256"] == hashlib.sha256(
        ("  " + CHINESE_UPDATE + "  ").encode()).hexdigest()
    original = next(span for span in view.evidence_spans
                    if span.structured_value["role"] == "management_answer")
    assert answer.structured_value["source_locator"] == original.structured_value["source_locator"]


def test_view_exposes_per_field_role_and_original_export_stays_unchanged(monkeypatch):
    view, _projection, payload, *_ = open_fixture(monkeypatch)
    assert view.export_dict() == payload
    for span in view.evidence_spans:
        assert span.structured_value["original_role"] == span.structured_value["role"]
        assert span.structured_value["source_role"] in {"management", "investor_question"}
        assert span.structured_value["language"] == "zh"
        assert span.structured_value["official_record_group_id"] == span.structured_value["qa_group_id"]
    assert all("source_role" not in span["structured_value"] for span in view.export_dict()["evidence_spans"])


def test_narrative_adapter_version_is_distinct_from_source_parser():
    assert adapter.NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION == "1.0.1"
