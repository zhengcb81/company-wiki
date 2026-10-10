"""P7-CWP-PROJECTION: projection identity, snapshot ownership, producer versions.

Contract tests over small synthetic pages.  They pin the behaviour the
implementation card requires, not one particular sort implementation:

- the same legal page set must yield one canonical projection identity for
  the opt-in ``1.0.2`` producer, whatever order the pages arrive in;
- the legacy ``1.0.1`` producer keeps its exact historical identity;
- projections are deeply immutable snapshots: no reachable mutation of the
  object graph, the caller's inputs, or a decoded dict can change an
  already-published identity;
- spans carry the real producer version, and unknown producers are named
  refusals instead of being silently reinterpreted.
"""

from collections.abc import Mapping
import hashlib
import itertools
import json

import pytest

from company_wiki.source_catalog.official_json_projection import (
    PROJECTION_ID_PREFIX,
    FieldBinding,
    ProjectionError,
    build_source_projection,
    evidence_span_for_field,
    projection_from_dict,
)
from company_wiki.source_catalog.official_json_structure import (
    parse_json_structure,
)


ISSUER_A = {"market": "CN", "security_id": "600000", "provider_company_id": 8001,
            "provider_activity_company_id": 901, "canonical_name": "Alpha Corp"}
ISSUER_B = {"market": "CN", "security_id": "600001", "provider_company_id": 8002,
            "provider_activity_company_id": 902, "canonical_name": "Beta Corp"}
AS_OF = "2026-10-08"

# Fixed historical identity of the legacy 1.0.1 producer over
# standard_two_pages() with ISSUER_A.  Computed from the accepted M3 code;
# any drift in the 1.0.1 algorithm must fail here.
GOLDEN_TWO_PAGE_1_0_1 = "df3f6502845450a90d28e82d1690e3bbd42dc326002ee19595917ca50fdbcee5"


def _record(record_id, *, activity, company, stock, name, question, answer,
            created="2026-09-01 10:00:00", updated="2026-09-02 10:00:00"):
    return {"id": record_id, "activityCompanyId": activity, "companyId": company,
            "stockCode": stock, "companyName": name, "questionContent": question,
            "content": answer, "isAnswered": True, "questionId": record_id + 5000,
            "crtTime": created, "updTime": updated}


def _page(current, records, *, total, pages, size=2):
    return {"success": True, "code": 200,
            "datas": [{"current": current, "size": size, "pages": pages,
                       "total": total, "records": records}]}


def _alpha(number, record_id, question, answer):
    return _record(record_id, activity=901, company=8001, stock="600000",
                   name="Alpha Corp", question=question, answer=answer)


def _beta(number, record_id, question, answer):
    return _record(record_id, activity=902, company=8002, stock="600001",
                   name="Beta Corp", question=question, answer=answer)


def standard_two_pages():
    page1 = _page(1, [_alpha(1, 101, "Alpha Q1?", "Alpha answer one."),
                      _beta(1, 102, "Beta Q1?", "Beta answer one.")], total=4, pages=2)
    page2 = _page(2, [_alpha(2, 103, "Alpha Q2?", "Alpha answer two."),
                      _beta(2, 104, "Beta Q2?", "Beta answer two.")], total=4, pages=2)
    return [page1, page2]


def standard_three_pages():
    page3 = _page(3, [_alpha(3, 105, "Alpha Q3?", "Alpha answer three."),
                      _beta(3, 106, "Beta Q3?", "Beta answer three.")], total=6, pages=3)
    return standard_two_pages() + [page3]


def _page_bytes(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def build(pages, issuer, *, version):
    triples = []
    for value in pages:
        data = _page_bytes(value)
        triples.append((hashlib.sha256(data).hexdigest(), len(data),
                        parse_json_structure(data, limits=None)))
    kwargs = {} if version is None else {"projection_version": version}
    return build_source_projection(
        parent_pages=triples, layout_id="official-paged-qa", issuer=issuer,
        as_of_date=AS_OF, **kwargs)


def _rehash(payload):
    body = {k: v for k, v in payload.items()
            if k not in {"projection_id", "projection_sha256"}}
    sha = hashlib.sha256(json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode("utf-8")).hexdigest()
    payload["projection_sha256"] = sha
    payload["projection_id"] = PROJECTION_ID_PREFIX + sha
    return payload


# --- canonical identity ------------------------------------------------------


def test_two_page_projection_identity_is_input_order_independent():
    pages = standard_two_pages()
    forward = build(pages, ISSUER_A, version="1.0.2")
    backward = build(list(reversed(pages)), ISSUER_A, version="1.0.2")
    assert forward.projection_id == backward.projection_id
    assert forward.projection_sha256 == backward.projection_sha256
    assert forward.canonical_json() == backward.canonical_json()


def test_three_page_all_permutations_share_one_canonical_identity():
    base = standard_three_pages()
    identities = {build(list(order), ISSUER_A, version="1.0.2").projection_id
                  for order in itertools.permutations(base)}
    assert len(identities) == 1


def test_new_version_changes_identity_and_old_default_is_pinned():
    pages = standard_two_pages()
    legacy = build(pages, ISSUER_A, version=None)
    canonical = build(pages, ISSUER_A, version="1.0.2")
    assert legacy.adapter["parser"] == "cwp_official_json/1.0.1"
    assert canonical.adapter["parser"] == "cwp_official_json/1.0.2"
    assert legacy.projection_sha256 == GOLDEN_TWO_PAGE_1_0_1
    assert canonical.projection_sha256 != legacy.projection_sha256


def test_unknown_projection_version_is_named_refusal():
    with pytest.raises(ProjectionError) as error:
        build(standard_two_pages(), ISSUER_A, version="1.0.3")
    assert error.value.code == "unsupported_projection_version"


def test_declared_pages_order_first_and_unreliable_pages_last():
    good = _page(1, [_alpha(1, 111, "Alpha Q?", "Alpha answer.")], total=2, pages=2, size=1)
    broken = _page(0, [_beta(1, 222, "Beta Q?", "Beta answer.")], total=2, pages=2, size=1)
    forward = build([good, broken], ISSUER_A, version="1.0.2")
    backward = build([broken, good], ISSUER_A, version="1.0.2")
    assert forward.projection_id == backward.projection_id
    assert [r.provider_record_id for r in forward.records] == [111, 222]
    assert "pagination_metadata_invalid" in forward.coverage["diagnostics"]
    assert forward.coverage["pagination_complete"] is False


def test_exact_duplicate_record_selects_canonical_first_copy():
    first = _page(1, [_alpha(1, 401, "Alpha Q?", "Same answer.")], total=1, pages=2, size=1)
    second = _page(2, [_alpha(2, 401, "Alpha Q?", "Same answer.")], total=1, pages=2, size=1)
    forward = build([first, second], ISSUER_A, version="1.0.2")
    backward = build([second, first], ISSUER_A, version="1.0.2")
    assert forward.projection_id == backward.projection_id
    selected = [r for r in forward.records if r.selected]
    assert len(selected) == 1
    assert selected[0].parent_content_sha256 == hashlib.sha256(
        _page_bytes(first)).hexdigest()
    others = [r.selection_reason for r in forward.records if not r.selected]
    assert others == ["duplicate_record_overlap"]


def test_conflicting_record_ids_stay_unselected_with_diagnostics():
    first = _page(1, [_alpha(1, 301, "Alpha Q?", "Version one.")], total=2, pages=2, size=1)
    second = _page(2, [_alpha(2, 301, "Alpha Q?", "Version two different.")],
                   total=2, pages=2, size=1)
    forward = build([first, second], ISSUER_A, version="1.0.2")
    backward = build([second, first], ISSUER_A, version="1.0.2")
    assert forward.projection_id == backward.projection_id
    assert all(not r.selected for r in forward.records)
    assert {r.selection_reason for r in forward.records} == {"record_id_conflict"}
    assert "pagination_record_id_conflict" in forward.coverage["diagnostics"]
    assert forward.coverage["conflicting_record_ids"] == 1


def test_missing_record_id_stays_reported_not_invented():
    record = {"activityCompanyId": 901, "companyId": 8001, "stockCode": "600000",
              "companyName": "Alpha Corp", "questionContent": "Alpha Q?",
              "content": "Alpha answer.", "isAnswered": True, "questionId": 7,
              "crtTime": "2026-09-01 10:00:00", "updTime": "2026-09-02 10:00:00"}
    page = _page(1, [record], total=1, pages=1, size=1)
    projection = build([page], ISSUER_A, version="1.0.2")
    assert "pagination_record_ids_missing" in projection.coverage["diagnostics"]
    assert projection.coverage["missing_record_ids"] == 1
    assert projection.coverage["pagination_complete"] is False


def test_records_and_fields_keep_real_page_order():
    page = _page(1, [_alpha(1, 501, "Alpha Q1?", "Alpha answer one."),
                     _beta(1, 502, "Beta Q1?", "Beta answer one."),
                     _alpha(1, 503, "Alpha Q2?", "Alpha answer two.")],
                 total=3, pages=1, size=3)
    projection = build([page], ISSUER_A, version="1.0.2")
    assert [r.provider_record_id for r in projection.records] == [501, 502, 503]
    alpha = next(r for r in projection.records if r.provider_record_id == 501)
    assert [f.field for f in alpha.fields] == ["content", "questionContent"]
    assert [f.role for f in alpha.fields] == ["management_answer", "investor_question"]


def test_same_pages_two_issuers_independent_and_wrong_issuer_refused():
    pages = standard_two_pages()
    alpha = build(pages, ISSUER_A, version="1.0.2")
    beta = build(pages, ISSUER_B, version="1.0.2")
    assert alpha.projection_id != beta.projection_id
    assert {r.provider_record_id for r in alpha.records if r.selected} == {101, 103}
    assert {r.provider_record_id for r in beta.records if r.selected} == {102, 104}
    with pytest.raises(ProjectionError) as error:
        build(pages, {"provider_company_id": 999999}, version="1.0.2")
    assert error.value.code == "issuer_not_on_page"


# --- snapshot ownership ------------------------------------------------------


def test_projection_objects_refuse_deep_mutation():
    projection = build(standard_two_pages(), ISSUER_A, version="1.0.2")
    with pytest.raises(TypeError):
        projection.issuer["market"] = "US"
    with pytest.raises(TypeError):
        projection.adapter["parser"] = "tampered"
    with pytest.raises(TypeError):
        projection.coverage["diagnostics"] = ()
    with pytest.raises(TypeError):
        projection.parent_source_refs[0]["byte_size"] = 0
    with pytest.raises(TypeError):
        projection.records[0].times["crtTime"] = "1999-01-01 00:00:00"
    with pytest.raises(TypeError):
        projection.records[0].state["isAnswered"] = False
    with pytest.raises(TypeError):
        projection.records[0].issuer_observed["company_names"] = []
    with pytest.raises(AttributeError):
        projection.coverage["pages"].append({})
    assert hashlib.sha256(projection.canonical_json().encode("utf-8")).hexdigest() == (
        projection.projection_sha256)


def test_to_dict_is_plain_independent_json():
    projection = build(standard_two_pages(), ISSUER_A, version="1.0.2")
    dto = projection.to_dict()
    assert type(dto) is dict
    assert type(dto["coverage"]) is dict
    assert type(dto["coverage"]["pages"]) is list
    assert type(dto["records"][0]["times"]) is dict
    assert type(dto["records"][0]["issuer_observed"]["company_names"]) is list
    dto["issuer"]["market"] = "US"
    dto["adapter"]["parser"] = "cwp_official_json/9.9.9"
    dto["coverage"]["pages"][0]["byte_size"] = 0
    dto["coverage"]["diagnostics"].append("injected")
    dto["records"][0]["state"]["isAnswered"] = False
    dto["records"][0]["issuer_observed"]["company_names"].append("Injected")
    again = projection.to_dict()
    assert again["issuer"]["market"] == "CN"
    assert again["adapter"]["parser"] == "cwp_official_json/1.0.2"
    assert again["coverage"]["diagnostics"] == []
    assert again["records"][0]["issuer_observed"]["company_names"] == ["Alpha Corp"]
    assert hashlib.sha256(projection.canonical_json().encode("utf-8")).hexdigest() == (
        projection.projection_sha256)


def test_decoded_payload_is_isolated_from_input_dict():
    projection = build(standard_two_pages(), ISSUER_A, version="1.0.2")
    payload = projection.to_dict()
    decoded = projection_from_dict(payload)
    payload["issuer"]["market"] = "US"
    payload["records"][0]["times"]["crtTime"] = "2000-01-01 00:00:00"
    payload["coverage"]["pages"][0]["records"] = 999
    assert decoded.canonical_json() == projection.canonical_json()
    assert decoded.projection_id == projection.projection_id


def test_builder_input_containers_are_copied():
    issuer = dict(ISSUER_A)
    pages = standard_two_pages()
    projection = build(pages, issuer, version="1.0.2")
    snapshot = projection.canonical_json()
    issuer["canonical_name"] = "Changed"
    issuer["injected"] = True
    pages[0]["datas"][0]["records"][0]["content"] = "Tampered after build"
    assert projection.canonical_json() == snapshot


# --- producer identity on decoded payloads and spans -------------------------


def test_unknown_producer_payload_is_refused_not_reinterpreted():
    projection = build(standard_two_pages(), ISSUER_A, version="1.0.2")
    payload = _rehash({**projection.to_dict(),
                       "adapter": {**projection.adapter,
                                   "parser": "cwp_official_json/9.9.9"}})
    with pytest.raises(ProjectionError) as error:
        projection_from_dict(payload)
    assert error.value.code == "unsupported_producer_version"


def test_structure_100_remains_unsupported():
    projection = build(standard_two_pages(), ISSUER_A, version=None)
    payload = _rehash({**projection.to_dict(),
                       "adapter": {**projection.adapter,
                                   "structure_parser_version": "1.0.0"}})
    with pytest.raises(ProjectionError) as error:
        projection_from_dict(payload)
    assert error.value.code == "unsupported_parser_version"


def test_evidence_span_records_real_producer_version():
    projection = build(standard_two_pages(), ISSUER_A, version="1.0.2")
    record = next(r for r in projection.records if r.selected)
    span = evidence_span_for_field(
        projection, record, record.fields[0], paragraph_index=1,
        decoded_text="Alpha answer one.")
    assert span.parser_name == "cwp_official_json"
    assert span.parser_version == "1.0.2"
    legacy = build(standard_two_pages(), ISSUER_A, version=None)
    legacy_record = next(r for r in legacy.records if r.selected)
    legacy_span = evidence_span_for_field(
        legacy, legacy_record, legacy_record.fields[0], paragraph_index=1,
        decoded_text="Alpha answer one.")
    assert legacy_span.parser_version == "1.0.1"


def test_field_binding_ranges_are_frozen_even_when_built_from_lists():
    binding = FieldBinding(
        field="content", role="management_answer", locator="loc",
        token_range=[1, 2], encoded_body_range=[3, 4],
        encoded_token_sha256="a" * 64, decoded_sha256="b" * 64,
        decoded_character_count=1, speaker_known=False, translation_of=None)
    with pytest.raises(AttributeError):
        binding.token_range.append(999)
    with pytest.raises(AttributeError):
        binding.encoded_body_range.append(999)
    assert list(binding.token_range) == [1, 2]
    assert list(binding.encoded_body_range) == [3, 4]


def test_projection_payload_mapping_roundtrip_is_json_only():
    """DTO payloads decoded from JSON keep identical identity through freeze."""
    projection = build(standard_two_pages(), ISSUER_A, version="1.0.2")
    decoded = projection_from_dict(json.loads(
        json.dumps(projection.to_dict(), ensure_ascii=False)))
    assert decoded.projection_id == projection.projection_id
    assert isinstance(decoded.issuer, Mapping)
