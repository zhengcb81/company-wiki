"""P7-CWP-PROJECTION: persist/load/replay/export compatibility in owned TEMP.

Everything runs inside pytest-owned temporary catalogs against synthetic
imported pages.  No network, no model calls, no sealed-run dependency.
"""

from contextlib import contextmanager
import hashlib
import json

import pytest

from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.official_json_import import (
    import_official_json_source,
)
from company_wiki.source_catalog.official_json_projection import (
    PROJECTION_ID_PREFIX,
    FieldBinding,
    ProjectionError,
    ProjectionRecord,
    SourceProjection,
    build_projection_export,
    build_projection_from_refs,
    load_projection,
    persist_projection,
    projection_from_dict,
    replay_projection,
)


AS_OF = "2026-10-08"
ISSUER_A = {"market": "CN", "security_id": "600000", "provider_company_id": 8001,
            "provider_activity_company_id": 901, "canonical_name": "Alpha Corp"}
ISSUER_B = {"market": "CN", "security_id": "600001", "provider_company_id": 8002,
            "provider_activity_company_id": 902, "canonical_name": "Beta Corp"}


@contextmanager
def catalog_for(tmp_path):
    (tmp_path / "companies").mkdir(exist_ok=True)
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path, catalog_dir=tmp_path / "catalog",
        roots=(RootSpec("company_raw", tmp_path / "companies", "company_raw"),),
    ))
    try:
        yield catalog
    finally:
        catalog.close()


def _record(record_id, *, activity, company, stock, name, question, answer):
    return {"id": record_id, "activityCompanyId": activity, "companyId": company,
            "stockCode": stock, "companyName": name, "questionContent": question,
            "content": answer, "isAnswered": True, "questionId": record_id + 5000,
            "crtTime": "2026-09-01 10:00:00", "updTime": "2026-09-02 10:00:00"}


def paged_page(current, records, *, total, pages, size=2):
    return {"success": True, "code": 200,
            "datas": [{"current": current, "size": size, "pages": pages,
                       "total": total, "records": records}]}


def standard_pages():
    page1 = paged_page(1, [
        _record(101, activity=901, company=8001, stock="600000", name="Alpha Corp",
                question="Alpha Q1?", answer="Alpha answer one."),
        _record(102, activity=902, company=8002, stock="600001", name="Beta Corp",
                question="Beta Q1?", answer="Beta answer one.")], total=4, pages=2)
    page2 = paged_page(2, [
        _record(103, activity=901, company=8001, stock="600000", name="Alpha Corp",
                question="Alpha Q2?", answer="Alpha answer two."),
        _record(104, activity=902, company=8002, stock="600001", name="Beta Corp",
                question="Beta Q2?", answer="Beta answer two.")], total=4, pages=2)
    return [page1, page2]


def import_page(catalog, value):
    data = value if isinstance(value, bytes) else json.dumps(
        value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    result = import_official_json_source(catalog, original=data, request={
        "schema_version": "official-source-import-request/2",
        "request_id": "p7-" + sha, "max_bytes": 1048576, "content_sha256": sha,
        "mime_type": "application/json", "document_kind": "investor_relations",
        "source_subject": {"kind": "multi_issuer_event", "event_namespace": "p7",
                           "event_id": "1", "issuer_refs": [],
                           "attribution_status": "partial"},
        "capture_receipt": {"capture_method": "local_document", "tool_name": "p7",
                            "tool_call_id": sha, "captured_at": "2026-10-10T00:00:00Z",
                            "response_bytes": len(data), "content_sha256": sha},
    })
    return result["source_ref"]


def build(catalog, refs, issuer, *, version):
    kwargs = {} if version is None else {"projection_version": version}
    return build_projection_from_refs(
        catalog, refs=refs, layout_id="official-paged-qa", issuer=issuer,
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


def _projection_files(catalog):
    return sorted((catalog.config.catalog_dir / "projections").glob("*.json"))


def _raw_page_files(root):
    return sorted(p for p in (root / "companies").rglob("*.json")
                  if not p.name.endswith(".source.json"))


def test_projection_102_roundtrip_is_order_independent_and_replays(tmp_path):
    with catalog_for(tmp_path) as catalog:
        page1 = import_page(catalog, standard_pages()[0])
        page2 = import_page(catalog, standard_pages()[1])
        forward = build(catalog, [page1, page2], ISSUER_A, version="1.0.2")
        backward = build(catalog, [page2, page1], ISSUER_A, version="1.0.2")
        assert forward.projection_id == backward.projection_id
        assert forward.to_dict() == backward.to_dict()
        assert persist_projection(catalog, forward) == forward.projection_id
        assert persist_projection(catalog, backward) == forward.projection_id
        assert len(_projection_files(catalog)) == 1
        identity = forward.projection_id
        stored_bytes = _projection_files(catalog)[0].read_bytes()

    with catalog_for(tmp_path) as reopened:
        loaded = load_projection(reopened, identity)
        assert loaded.to_dict() == forward.to_dict()
        replayed = replay_projection(reopened, loaded)
        assert replayed["verified_records"] == 2
        bundle = build_projection_export(reopened, loaded)
        assert bundle["counts"]["evidence_spans"] == 4
        spans = bundle["evidence_spans"]
        assert all(span["parser_version"] == "1.0.2" for span in spans)
        by_record = {span["structured_value"]["provider_record_id"]: span
                     for span in spans}
        assert by_record[101]["source_id"] == page1["source_id"]
        assert by_record[103]["source_id"] == page2["source_id"]
        assert _projection_files(reopened)[0].read_bytes() == stored_bytes


def test_sealed_101_roundtrip_unchanged_with_single_raw_copies(tmp_path):
    with catalog_for(tmp_path) as catalog:
        page1 = import_page(catalog, standard_pages()[0])
        page2 = import_page(catalog, standard_pages()[1])
        projection = build(catalog, [page1, page2], ISSUER_A, version=None)
        assert projection.adapter["parser"] == "cwp_official_json/1.0.1"
        identity = persist_projection(catalog, projection)
        stored = _projection_files(catalog)[0].read_bytes()
    with catalog_for(tmp_path) as reopened:
        loaded = load_projection(reopened, identity)
        assert replay_projection(reopened, loaded)["verified_records"] == 2
        bundle = build_projection_export(reopened, loaded)
        assert all(span["parser_version"] == "1.0.1"
                   for span in bundle["evidence_spans"])
        assert persist_projection(reopened, loaded) == identity
        assert _projection_files(reopened)[0].read_bytes() == stored
        assert len(_raw_page_files(reopened.config.project_root)) == 2


def test_persist_refuses_payload_hash_mismatch(tmp_path):
    with catalog_for(tmp_path) as catalog:
        ref = import_page(catalog, standard_pages()[0])
        projection = build(catalog, [ref], ISSUER_A, version=None)
        payload = projection.to_dict()
        payload["coverage"]["issuer_records_selected"] += 1
        tampered = SourceProjection(
            schema_version=payload["schema_version"],
            projection_id=payload["projection_id"],
            projection_sha256=payload["projection_sha256"],
            parent_source_refs=payload["parent_source_refs"],
            adapter=payload["adapter"], issuer=payload["issuer"],
            as_of_date=payload["as_of_date"],
            records=[ProjectionRecord(
                **{**item, "fields": tuple(FieldBinding(**b)
                                           for b in item["fields"])})
                for item in payload["records"]],
            coverage=payload["coverage"])
        with pytest.raises(ProjectionError) as error:
            persist_projection(catalog, tampered)
        assert error.value.code == "projection_payload_mismatch"
        assert not _projection_files(catalog)


def test_forged_binding_cannot_replay_102_even_rehashed(tmp_path):
    with catalog_for(tmp_path) as catalog:
        ref = import_page(catalog, standard_pages()[0])
        projection = build(catalog, [ref], ISSUER_A, version="1.0.2")
        payload = projection.to_dict()
        payload["records"][0]["fields"][0]["role"] = "investor_question"
        payload["records"][0]["times"]["crtTime"] = "2020-01-01 00:00:00"
        forged = projection_from_dict(_rehash(payload))
        with pytest.raises(ProjectionError):
            replay_projection(catalog, forged)
        with pytest.raises(ProjectionError):
            build_projection_export(catalog, forged)


def test_second_page_byte_change_refuses_replay_then_restores(tmp_path):
    with catalog_for(tmp_path) as catalog:
        page1 = import_page(catalog, standard_pages()[0])
        page2 = import_page(catalog, standard_pages()[1])
        projection = build(catalog, [page1, page2], ISSUER_A, version="1.0.2")
        target = next(
            p for p in _raw_page_files(catalog.config.project_root)
            if hashlib.sha256(p.read_bytes()).hexdigest() == page2["content_sha256"])
        original = target.read_bytes()
        target.write_bytes(original.replace(b"Alpha answer two.", b"Alpha answer 3.3.", 1))
        with pytest.raises(Exception):
            replay_projection(catalog, projection)
        target.write_bytes(original)
        assert replay_projection(catalog, projection)["verified_records"] == 2


def test_unknown_producer_file_is_refused_on_load(tmp_path):
    with catalog_for(tmp_path) as catalog:
        ref = import_page(catalog, standard_pages()[0])
        projection = build(catalog, [ref], ISSUER_A, version="1.0.2")
        payload = _rehash({**projection.to_dict(),
                           "adapter": {**projection.adapter,
                                       "parser": "cwp_official_json/9.9.9"}})
        sha = payload["projection_sha256"]
        path = catalog.config.catalog_dir / "projections" / (sha + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        with pytest.raises(ProjectionError) as error:
            load_projection(catalog, PROJECTION_ID_PREFIX + sha)
        assert error.value.code == "unsupported_producer_version"


def test_repeated_canonical_persist_keeps_one_derived_per_projection(tmp_path):
    with catalog_for(tmp_path) as catalog:
        page1 = import_page(catalog, standard_pages()[0])
        page2 = import_page(catalog, standard_pages()[1])
        alpha = build(catalog, [page1, page2], ISSUER_A, version="1.0.2")
        alpha_again = build(catalog, [page2, page1], ISSUER_A, version="1.0.2")
        beta = build(catalog, [page1, page2], ISSUER_B, version="1.0.2")
        assert alpha.projection_id == alpha_again.projection_id
        assert alpha.projection_id != beta.projection_id
        persist_projection(catalog, alpha)
        persist_projection(catalog, alpha_again)
        persist_projection(catalog, beta)
        assert len(_projection_files(catalog)) == 2
        assert len(_raw_page_files(catalog.config.project_root)) == 2


def test_flat_layout_102_is_canonical_and_replays(tmp_path):
    def flat_page(number, record_id):
        return {"ok": True, "result": {"page": number, "page_size": 1,
                                       "page_count": 2, "item_total": 2,
                                       "items": [{"ref": record_id, "org_id": 8001,
                                                  "org_name": "Alpha Corp",
                                                  "q": "Alpha Q?", "a": "Alpha answer.",
                                                  "answered": True,
                                                  "created_at": "2026-09-01 10:00:00",
                                                  "updated_at": "2026-09-02 10:00:00"}]}}
    with catalog_for(tmp_path) as catalog:
        first = import_page(catalog, flat_page(1, 601))
        second = import_page(catalog, flat_page(2, 602))
        forward = build_projection_from_refs(
            catalog, refs=[first, second], layout_id="official-flat-list",
            issuer={"provider_company_id": 8001}, as_of_date=AS_OF,
            projection_version="1.0.2")
        backward = build_projection_from_refs(
            catalog, refs=[second, first], layout_id="official-flat-list",
            issuer={"provider_company_id": 8001}, as_of_date=AS_OF,
            projection_version="1.0.2")
        assert forward.projection_id == backward.projection_id
        assert [r.provider_record_id for r in forward.records] == [601, 602]
        assert {r.provider_record_id for r in forward.records if r.selected} == {601, 602}
        assert replay_projection(catalog, forward)["verified_records"] == 2
