"""Consumer-level regressions found at the M3-JSON acceptance node.

All originals and derived outputs live in pytest-owned TEMP catalogs.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import os

import pytest

from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.official_json_import import import_official_json_source
from company_wiki.source_catalog.official_json_projection import (
    ProjectionError, build_projection_from_refs, persist_projection, load_projection,
    replay_projection, build_projection_export, projection_from_dict,
)


@contextmanager
def catalog_for(tmp_path):
    (tmp_path / "companies").mkdir()
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path, catalog_dir=tmp_path / "catalog",
        roots=(RootSpec("company_raw", tmp_path / "companies", "company_raw"),),
    ))
    try:
        yield catalog
    finally:
        catalog.close()


def import_page(catalog, value):
    data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    sha = hashlib.sha256(data).hexdigest()
    result = import_official_json_source(catalog, original=data, request={
        "schema_version": "official-source-import-request/2", "request_id": "accept-" + sha,
        "max_bytes": 1048576, "content_sha256": sha, "mime_type": "application/json",
        "document_kind": "investor_relations", "source_subject": {
            "kind": "multi_issuer_event", "event_namespace": "fixture", "event_id": "1",
            "issuer_refs": [], "attribution_status": "partial",
        }, "capture_receipt": {
            "capture_method": "local_document", "tool_name": "acceptance",
            "tool_call_id": sha, "captured_at": "2026-10-10T00:00:00Z",
            "response_bytes": len(data), "content_sha256": sha,
        },
    })
    return result["source_ref"]


def flat_page(number=1, *, record_id=101, answered=False, created="2026-09-01 10:00:00", updated="2026-09-01 10:00:00"):
    record = {"ref": record_id, "org_id": 1, "org_name": "Acme", "q": "When do shipments begin?",
              "answered": answered, "created_at": created}
    if updated is not None:
        record["updated_at"] = updated
    if answered:
        record["a"] = "Shipments start in Q4."
    return {"ok": True, "result": {"page": number, "page_size": 1, "page_count": 2,
                                   "item_total": 2, "items": [record]}}


def projection(catalog, refs, *, cutoff="2026-10-08"):
    return build_projection_from_refs(catalog, refs=refs, layout_id="official-flat-list",
                                     issuer={"provider_company_id": 1}, as_of_date=cutoff)


def rehash(payload):
    body = {k: v for k, v in payload.items() if k not in {"projection_id", "projection_sha256"}}
    sha = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    payload["projection_sha256"] = sha
    payload["projection_id"] = "urn:company-wiki:source-projection:sha256:" + sha
    return projection_from_dict(payload)


def test_persisted_projection_is_loadable_and_idempotent(tmp_path):
    with catalog_for(tmp_path) as catalog:
        ref = import_page(catalog, flat_page())
        original = projection(catalog, [ref])
        identity = persist_projection(catalog, original)
        loaded = load_projection(catalog, identity)
        assert loaded.to_dict() == original.to_dict()
        assert persist_projection(catalog, loaded) == identity
        assert replay_projection(catalog, loaded)["verified_records"] == 1


def test_public_cli_reloads_by_projection_id(tmp_path):
    with catalog_for(tmp_path) as catalog:
        ref = import_page(catalog, flat_page())
        original = projection(catalog, [ref])
        identity = persist_projection(catalog, original)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": "catalog", "roots": [
        {"root_id": "company_raw", "path": "companies", "kind": "company_raw"}]}))
    request = tmp_path / "request.json"
    repo = Path(__file__).resolve().parents[2]
    for operation, schema in (("replay", "official-json-replay-request/1"),
                              ("export", "source-projection-export-request/1")):
        request.write_text(json.dumps({"schema_version": schema, "projection_id": identity}))
        result = subprocess.run([sys.executable, "-X", "utf8", "-B", "-m",
            "company_wiki.source_catalog.official_source_cli", "--operation", operation,
            "--config", str(config), "--project-root", str(tmp_path), "--request", str(request)],
            cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(repo / "src")}, capture_output=True, timeout=60)
        assert result.returncode == 0, result.stderr


def test_multi_page_spans_are_bound_to_their_own_parent(tmp_path):
    with catalog_for(tmp_path) as catalog:
        first = import_page(catalog, flat_page())
        second = import_page(catalog, flat_page(2, record_id=202, answered=True))
        derived = projection(catalog, [first, second])
        bundle = build_projection_export(catalog, derived)
        sources = {span["structured_value"]["provider_record_id"]: span["source_id"]
                   for span in bundle["evidence_spans"]}
        assert sources == {101: first["source_id"], 202: second["source_id"]}
        assert replay_projection(catalog, derived)["verified_records"] == 2


@pytest.mark.parametrize("updated", ["2026-10-09 10:00:00", "unparseable"])
def test_latest_record_revision_cannot_leak_past_as_of(tmp_path, updated):
    with catalog_for(tmp_path) as catalog:
        ref = import_page(catalog, flat_page(answered=True, updated=updated))
        derived = projection(catalog, [ref])
        assert not derived.records[0].selected
        assert derived.records[0].answer_first_publication_known is False
        assert not build_projection_export(catalog, derived)["evidence_spans"]


def test_precollected_answer_without_answer_availability_stays_unknown(tmp_path):
    value = {"success": True, "code": 200, "datas": [{"current": 1, "size": 1, "pages": 1, "total": 1,
        "records": [{"id": 9, "companyId": 1, "question": "Question submitted earlier?",
                     "answer": "Undated answer added later", "crtTime": "2026-09-01 10:00:00"}]}]}
    with catalog_for(tmp_path) as catalog:
        ref = import_page(catalog, value)
        derived = build_projection_from_refs(catalog, refs=[ref], layout_id="official-paged-qa",
            issuer={"provider_company_id": 1}, as_of_date="2026-10-08")
        assert derived.records[0].as_of_eligibility == "unknown"
        assert not derived.records[0].selected


@pytest.mark.parametrize("operation", [replay_projection, build_projection_export])
@pytest.mark.parametrize("changed", ["role", "selected", "times", "issuer"])
def test_self_hashed_derivative_claims_must_match_parent_semantics(tmp_path, operation, changed):
    with catalog_for(tmp_path) as catalog:
        ref = import_page(catalog, flat_page())
        payload = projection(catalog, [ref]).to_dict()
        if changed == "role":
            payload["records"][0]["fields"][0]["role"] = "management_answer"
        elif changed == "selected":
            payload["records"][0]["selected"] = False
        elif changed == "times":
            payload["records"][0]["times"]["created_at"] = "2020-01-01 00:00:00"
        else:
            payload["records"][0]["issuer_observed"]["provider_company_id"] = 999
        forged = rehash(payload)
        with pytest.raises(ProjectionError):
            operation(catalog, forged)


def test_distinct_question_and_answer_issuers_are_not_merged(tmp_path):
    value = {"success": True, "code": 200, "datas": [{"current": 1, "size": 1, "pages": 1, "total": 1,
        "records": [{"id": 303, "activityCompanyId": 22, "aactivityCompanyId": 22,
                     "qactivityCompanyId": 11, "content": "Company 22 answer",
                     "questionContent": "Company 11 question", "isAnswered": True,
                     "questionId": 99, "crtTime": "2026-09-01 10:00:00",
                     "updTime": "2026-09-01 10:00:00"}]}]}
    with catalog_for(tmp_path) as catalog:
        ref = import_page(catalog, value)
        try:
            derived = build_projection_from_refs(catalog, refs=[ref], layout_id="official-paged-qa",
                issuer={"provider_activity_company_id": 11}, as_of_date="2026-10-08")
        except ProjectionError as error:
            assert error.code == "issuer_not_on_page"
        else:
            assert not derived.records[0].selected


@pytest.mark.parametrize("raw,pointer", [
    (b'{"left":{"x":1},"right":{"x":2}}', "/left"),
    (b'{"left":{"x":1},"right":{"x":2}}', "/right"),
    (b'{"rows":[1,2]}', "/rows"),
    (b'{"rows":[]}', "/rows"),
    (b'{"rows":{}}', "/rows"),
    (b'{"rows":[{"inner":{"x":1}},[]]}', ""),
    (b'{"rows":[{"inner":{"x":1}},[]]}', "/rows"),
    (b'{"rows":[{"inner":{"x":1}},[]]}', "/rows/0"),
    (b'{"rows":[{"inner":{"x":1}},[]]}', "/rows/0/inner"),
    (b'{"rows":[{"inner":{"x":1}},[]]}', "/rows/1"),
])
def test_container_sha_matches_its_final_token_bytes(raw, pointer):
    from company_wiki.source_catalog.official_json_structure import parse_json_structure
    node = parse_json_structure(raw).at_pointer(pointer)
    start, end = node.token_range
    assert node.encoded_token_sha256 == hashlib.sha256(raw[start:end]).hexdigest()


def test_sealed_parser_100_payload_is_typed_unsupported_without_upgrade(tmp_path):
    with catalog_for(tmp_path) as catalog:
        ref = import_page(catalog, flat_page())
        payload = projection(catalog, [ref]).to_dict()
        payload["adapter"]["structure_parser_version"] = "1.0.0"
        payload["adapter"]["parser"] = "cwp_official_json/1.0.0"
        del payload["records"][0]["parent_content_sha256"]
        before = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with pytest.raises(ProjectionError) as error:
            projection_from_dict(payload)
        assert error.value.code == "unsupported_parser_version"
        assert json.dumps(payload, ensure_ascii=False, sort_keys=True) == before
        from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
        assert SourceVersionReader(catalog).open_version(SourceRef(**ref), purpose="source_export").data


@pytest.mark.parametrize("changed", [{"page_count": 999, "item_total": 999}, {"page_size": 99}])
def test_pagination_metadata_drift_is_partial_without_losing_originals(tmp_path, changed):
    with catalog_for(tmp_path) as catalog:
        first = import_page(catalog, flat_page())
        second_page = flat_page(2, record_id=202)
        second_page["result"].update(changed)
        second = import_page(catalog, second_page)
        derived = projection(catalog, [first, second])
        assert derived.coverage["pagination_complete"] is False
        assert "pagination_metadata_conflict" in derived.coverage["diagnostics"]
        assert derived.coverage["total_records"] == 2
        assert len(derived.coverage["pages"]) == 2
        assert len(build_projection_export(catalog, derived)["evidence_spans"]) == 2
        from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
        for ref in [first, second]:
            raw = SourceVersionReader(catalog).open_version(SourceRef(**ref), purpose="source_export").data
            assert hashlib.sha256(raw).hexdigest() == ref["content_sha256"]


def test_repeated_record_across_adjacent_pages_is_not_complete_or_double_selected(tmp_path):
    with catalog_for(tmp_path) as catalog:
        first = import_page(catalog, flat_page())
        second = import_page(catalog, flat_page(2))
        derived = projection(catalog, [first, second])
        assert derived.coverage["pagination_complete"] is False
        assert derived.coverage["total_records"] == 2
        assert derived.coverage["unique_record_ids"] == 1
        assert derived.coverage["duplicate_record_occurrences"] == 1
        assert derived.coverage["conflicting_record_ids"] == 0
        assert derived.coverage["issuer_records_selected"] == 1
        assert derived.records[1].selection_reason == "duplicate_record_overlap"
        assert len(derived.records) == 2
        assert len(build_projection_export(catalog, derived)["evidence_spans"]) == 1


def test_conflicting_revisions_under_one_record_id_do_not_select_arbitrary_version(tmp_path):
    with catalog_for(tmp_path) as catalog:
        first = import_page(catalog, flat_page())
        second = import_page(catalog, flat_page(2, answered=True))
        derived = projection(catalog, [first, second])
        assert derived.coverage["pagination_complete"] is False
        assert derived.coverage["unique_record_ids"] == 1
        assert derived.coverage["duplicate_record_occurrences"] == 1
        assert derived.coverage["conflicting_record_ids"] == 1
        assert derived.coverage["issuer_records_selected"] == 0
        assert all(r.selection_reason == "record_id_conflict" for r in derived.records)
        assert not build_projection_export(catalog, derived)["evidence_spans"]


def test_missing_record_id_is_observed_but_cannot_prove_full_page_coverage(tmp_path):
    with catalog_for(tmp_path) as catalog:
        first = import_page(catalog, flat_page())
        value = flat_page(2, record_id=202)
        del value["result"]["items"][0]["ref"]
        second = import_page(catalog, value)
        derived = projection(catalog, [first, second])
        assert derived.coverage["pagination_complete"] is False
        assert derived.coverage["missing_record_ids"] == 1
        assert derived.coverage["total_records"] == 2
        assert derived.coverage["issuer_records_selected"] == 2


def test_consistent_complete_collection_can_arrive_in_either_page_order(tmp_path):
    with catalog_for(tmp_path) as catalog:
        first = import_page(catalog, flat_page())
        second = import_page(catalog, flat_page(2, record_id=202))
        for refs in ([first, second], [second, first]):
            derived = projection(catalog, refs)
            assert derived.coverage["pagination_complete"] is True
            assert derived.coverage["diagnostics"] == []
            assert derived.coverage["unique_record_ids"] == 2
            assert derived.coverage["issuer_records_selected"] == 2


@pytest.mark.parametrize("numeric", ["1.9", "true", "1.0", "1e0", "9.007199254740993e15", "1e30"])
def test_non_integer_numeric_forms_never_become_issuer_identity_proof(tmp_path, numeric):
    raw = ('{"ok":true,"result":{"page":1,"page_size":1,"page_count":1,"item_total":1,"items":'
           '[{"ref":101,"org_id":' + numeric + ',"q":"Q","created_at":"2026-09-01 10:00:00","answered":false}]}}').encode()
    with catalog_for(tmp_path) as catalog:
        ref = import_page(catalog, raw)
        with pytest.raises(ProjectionError) as error:
            projection(catalog, [ref])
        assert error.value.code == "issuer_not_on_page"
        from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
        assert SourceVersionReader(catalog).open_version(SourceRef(**ref), purpose="source_export").data == raw


@pytest.mark.parametrize("numeric", [1, 9007199254740993, 2 ** 100])
def test_lexical_integer_issuer_ids_keep_exact_arbitrary_precision(tmp_path, numeric):
    value = flat_page()
    value["result"]["items"][0]["org_id"] = numeric
    with catalog_for(tmp_path) as catalog:
        ref = import_page(catalog, value)
        derived = build_projection_from_refs(catalog, refs=[ref], layout_id="official-flat-list",
            issuer={"provider_company_id": numeric}, as_of_date="2026-10-08")
        assert derived.records[0].issuer_observed["provider_company_id"] == numeric
        assert type(derived.records[0].issuer_observed["provider_company_id"]) is int
        assert derived.records[0].selected


@pytest.mark.parametrize("field", ["page", "page_size", "page_count", "item_total"])
def test_fractional_pagination_cannot_become_complete(tmp_path, field):
    with catalog_for(tmp_path) as catalog:
        value = flat_page()
        value["result"][field] = float(value["result"][field])
        first = import_page(catalog, value)
        second = import_page(catalog, flat_page(2, record_id=202))
        derived = projection(catalog, [first, second])
        assert derived.coverage["pagination_complete"] is False
        assert "pagination_metadata_invalid" in derived.coverage["diagnostics"]
