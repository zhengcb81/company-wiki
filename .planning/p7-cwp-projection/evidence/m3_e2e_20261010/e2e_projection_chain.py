"""P7-CWP-PROJECTION isolated E2E: import/2 -> builder -> persist -> close/reopen
-> load -> replay -> export, over two declared layouts and two issuers.

Runs entirely in an owned TEMP directory with synthetic pages.  No network,
no model calls, no production catalog, no sealed lake.  Writes a JSON receipt
next to itself and restores its TEMP directory afterwards.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))

from company_wiki.source_catalog.models import CatalogConfig, RootSpec  # noqa: E402
from company_wiki.source_catalog.service import SourceCatalog  # noqa: E402
from company_wiki.source_catalog.official_json_import import (  # noqa: E402
    import_official_json_source,
)
from company_wiki.source_catalog.official_json_projection import (  # noqa: E402
    build_projection_export,
    build_projection_from_refs,
    load_projection,
    persist_projection,
    replay_projection,
)

import company_wiki  # noqa: E402
assert str(Path(company_wiki.__file__).resolve()).startswith(
    str((REPO / "src" / "company_wiki").resolve())), (
    "imported company_wiki outside the worktree source: "
    + str(company_wiki.__file__))

AS_OF = "2026-10-08"
ISSUER_A = {"market": "CN", "security_id": "600000", "provider_company_id": 8001,
            "provider_activity_company_id": 901, "canonical_name": "Alpha Corp"}
ISSUER_B = {"market": "CN", "security_id": "600001", "provider_company_id": 8002,
            "provider_activity_company_id": 902, "canonical_name": "Beta Corp"}


def _record(record_id, *, activity, company, stock, name, question, answer):
    return {"id": record_id, "activityCompanyId": activity, "companyId": company,
            "stockCode": stock, "companyName": name, "questionContent": question,
            "content": answer, "isAnswered": True, "questionId": record_id + 5000,
            "crtTime": "2026-09-01 10:00:00", "updTime": "2026-09-02 10:00:00"}


def paged_pages():
    page1 = {"success": True, "code": 200, "datas": [
        {"current": 1, "size": 2, "pages": 2, "total": 4, "records": [
            _record(101, activity=901, company=8001, stock="600000", name="Alpha Corp",
                    question="Alpha Q1?", answer="Alpha answer one."),
            _record(102, activity=902, company=8002, stock="600001", name="Beta Corp",
                    question="Beta Q1?", answer="Beta answer one.")]}]}
    page2 = {"success": True, "code": 200, "datas": [
        {"current": 2, "size": 2, "pages": 2, "total": 4, "records": [
            _record(103, activity=901, company=8001, stock="600000", name="Alpha Corp",
                    question="Alpha Q2?", answer="Alpha answer two."),
            _record(104, activity=902, company=8002, stock="600001", name="Beta Corp",
                    question="Beta Q2?", answer="Beta answer two.")]}]}
    return [page1, page2]


def flat_pages():
    def one(number, record_id):
        return {"ok": True, "result": {"page": number, "page_size": 1, "page_count": 2,
                "item_total": 2, "items": [
                    {"ref": record_id, "org_id": 8001, "org_name": "Alpha Corp",
                     "q": "Alpha Q?", "a": "Alpha answer.", "answered": True,
                     "created_at": "2026-09-01 10:00:00",
                     "updated_at": "2026-09-02 10:00:00"}]}}
    return [one(1, 601), one(2, 602)]


def page_bytes(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def import_page(catalog, data):
    sha = hashlib.sha256(data).hexdigest()
    result = import_official_json_source(catalog, original=data, request={
        "schema_version": "official-source-import-request/2",
        "request_id": "e2e-" + sha, "max_bytes": 1048576, "content_sha256": sha,
        "mime_type": "application/json", "document_kind": "investor_relations",
        "source_subject": {"kind": "multi_issuer_event", "event_namespace": "e2e",
                           "event_id": "1", "issuer_refs": [],
                           "attribution_status": "partial"},
        "capture_receipt": {"capture_method": "local_document", "tool_name": "e2e",
                            "tool_call_id": sha, "captured_at": "2026-10-10T00:00:00Z",
                            "response_bytes": len(data), "content_sha256": sha},
    })
    return result["source_ref"]


def open_catalog(root):
    (root / "companies").mkdir(parents=True, exist_ok=True)
    return SourceCatalog(CatalogConfig(
        project_root=root, catalog_dir=root / "catalog",
        roots=(RootSpec("company_raw", root / "companies", "company_raw"),),
    ))


def tree_files(root):
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(root)).replace("\\", "/")] = path.stat().st_size
    return out


def main():
    receipt = {"schema_version": "p7-projection-e2e/1", "cases": [], "checks": []}
    temp_root = Path(tempfile.mkdtemp(prefix="p7-cwp-e2e-"))
    receipt["temp_root"] = str(temp_root)
    receipt["temp_initial_files"] = len(tree_files(temp_root))
    try:
        # ---- case 1: official-paged-qa, two issuers, both pages, 1.0.2 canonical
        case1 = temp_root / "paged"
        catalog = open_catalog(case1)
        raws = []
        refs = []
        for value in paged_pages():
            data = page_bytes(value)
            ref = import_page(catalog, data)
            raws.append({"content_sha256": ref["content_sha256"],
                         "byte_size": ref["byte_size"],
                         "sha256_recomputed": hashlib.sha256(data).hexdigest(),
                         "source_id": ref["source_id"]})
            refs.append(ref)
        assert raws[0]["content_sha256"] == raws[0]["sha256_recomputed"]
        assert raws[1]["content_sha256"] == raws[1]["sha256_recomputed"]

        projections = {}
        for issuer_name, issuer in (("alpha", ISSUER_A), ("beta", ISSUER_B)):
            forward = build_projection_from_refs(
                catalog, refs=list(refs), layout_id="official-paged-qa",
                issuer=issuer, as_of_date=AS_OF, projection_version="1.0.2")
            backward = build_projection_from_refs(
                catalog, refs=list(reversed(refs)), layout_id="official-paged-qa",
                issuer=issuer, as_of_date=AS_OF, projection_version="1.0.2")
            assert forward.projection_id == backward.projection_id, issuer_name
            assert [r.provider_record_id for r in forward.records] == [101, 102, 103, 104]
            assert forward.coverage["pagination_complete"] is True
            assert forward.coverage["diagnostics"] == []
            identity = persist_projection(catalog, forward)
            assert persist_projection(catalog, backward) == identity
            projections[issuer_name] = forward
            receipt["cases"].append({
                "case": "paged-" + issuer_name, "producer": forward.adapter["parser"],
                "projection_id": forward.projection_id,
                "projection_sha256": forward.projection_sha256,
                "selected_records": [r.provider_record_id for r in forward.records if r.selected],
                "pages": raws, "pagination_complete": True})
        assert (projections["alpha"].projection_id
                != projections["beta"].projection_id)

        legacy = build_projection_from_refs(
            catalog, refs=list(refs), layout_id="official-paged-qa", issuer=ISSUER_A,
            as_of_date=AS_OF)
        assert legacy.adapter["parser"] == "cwp_official_json/1.0.1"
        legacy_identity = persist_projection(catalog, legacy)
        receipt["cases"].append({
            "case": "paged-alpha-legacy-1.0.1", "producer": legacy.adapter["parser"],
            "projection_id": legacy_identity,
            "projection_sha256": legacy.projection_sha256,
            "selected_records": [r.provider_record_id for r in legacy.records if r.selected],
            "pages": raws, "pagination_complete": True})

        files_before_close = tree_files(case1)
        catalog.close()

        # reopen: load, replay, export for each sealed projection
        catalog = open_catalog(case1)
        for name, expected in list(projections.items()) + [("legacy", legacy)]:
            identity = expected.projection_id
            loaded = load_projection(catalog, identity)
            assert loaded.to_dict() == expected.to_dict()
            replayed = replay_projection(catalog, loaded)
            expected_selected = len([r for r in loaded.records if r.selected])
            assert replayed["verified_records"] == expected_selected
            bundle = build_projection_export(catalog, loaded)
            span_versions = sorted({span["parser_version"]
                                    for span in bundle["evidence_spans"]})
            producer_version = loaded.adapter["parser"].partition("/")[2]
            assert span_versions in ([], [producer_version]), span_versions
            assert bundle["counts"]["evidence_spans"] == sum(
                len(r.fields) for r in loaded.records if r.selected)
            receipt["checks"].append({
                "check": "reopen-load-replay-export", "case": name,
                "projection_id": identity,
                "producer": loaded.adapter["parser"],
                "span_parser_versions": span_versions,
                "verified_records": replayed["verified_records"],
                "evidence_spans": bundle["counts"]["evidence_spans"],
                "bundle_sha256": bundle["bundle_sha256"]})
        files_after_reopen = tree_files(case1)
        assert files_after_reopen == files_before_close, "reopen must not add files"
        catalog.close()
        receipt["paged_catalog_files"] = len(files_after_reopen)
        receipt["paged_catalog_bytes"] = sum(files_after_reopen.values())
        raw_store = sorted(p for p in (case1 / "companies").rglob("*.json")
                           if not p.name.endswith(".source.json"))
        receipt["paged_raw_page_files"] = len(raw_store)
        derived_store = sorted((case1 / "catalog" / "projections").glob("*.json"))
        receipt["paged_derived_files"] = len(derived_store)
        assert receipt["paged_raw_page_files"] == 2
        assert receipt["paged_derived_files"] == 3  # alpha, beta, legacy

        # ---- case 2: official-flat-list layout, order-independence + replay
        case2 = temp_root / "flat"
        catalog = open_catalog(case2)
        flat_refs = [import_page(catalog, page_bytes(value)) for value in flat_pages()]
        forward = build_projection_from_refs(
            catalog, refs=list(flat_refs), layout_id="official-flat-list",
            issuer={"provider_company_id": 8001}, as_of_date=AS_OF,
            projection_version="1.0.2")
        backward = build_projection_from_refs(
            catalog, refs=list(reversed(flat_refs)), layout_id="official-flat-list",
            issuer={"provider_company_id": 8001}, as_of_date=AS_OF,
            projection_version="1.0.2")
        assert forward.projection_id == backward.projection_id
        assert [r.provider_record_id for r in forward.records] == [601, 602]
        assert forward.coverage["pagination_complete"] is True
        persist_projection(catalog, forward)
        catalog.close()
        catalog = open_catalog(case2)
        loaded = load_projection(catalog, forward.projection_id)
        assert replay_projection(catalog, loaded)["verified_records"] == 2
        bundle = build_projection_export(catalog, loaded)
        assert {span["parser_version"] for span in bundle["evidence_spans"]} == {"1.0.2"}
        catalog.close()
        receipt["cases"].append({
            "case": "flat-alpha-1.0.2", "producer": forward.adapter["parser"],
            "projection_id": forward.projection_id,
            "projection_sha256": forward.projection_sha256,
            "selected_records": [r.provider_record_id for r in forward.records if r.selected],
            "pagination_complete": True})

        # ---- permutation proof on the canonical producer over three pages
        case3 = temp_root / "perm"
        catalog = open_catalog(case3)
        page3 = {"success": True, "code": 200, "datas": [
            {"current": 3, "size": 2, "pages": 3, "total": 6, "records": [
                _record(105, activity=901, company=8001, stock="600000",
                        name="Alpha Corp", question="Alpha Q3?",
                        answer="Alpha answer three."),
                _record(106, activity=902, company=8002, stock="600001",
                        name="Beta Corp", question="Beta Q3?",
                        answer="Beta answer three.")]}]}
        values = paged_pages() + [page3]
        refs3 = [import_page(catalog, page_bytes(value)) for value in values]
        identities = set()
        for order in itertools.permutations(range(3)):
            projection = build_projection_from_refs(
                catalog, refs=[refs3[i] for i in order], layout_id="official-paged-qa",
                issuer=ISSUER_A, as_of_date=AS_OF, projection_version="1.0.2")
            identities.add(projection.projection_id)
        assert len(identities) == 1
        receipt["checks"].append({
            "check": "three-page-all-permutations-one-identity",
            "projection_id": next(iter(identities))})
        catalog.close()

        receipt["status"] = "passed"
    finally:
        leftover = tree_files(temp_root)
        shutil.rmtree(temp_root, ignore_errors=True)
        receipt["temp_final_files"] = len(tree_files(temp_root))
        receipt["temp_restored"] = not temp_root.exists()
        receipt["temp_files_removed"] = len(leftover)
    (HERE / "e2e_receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": receipt["status"],
                      "checks": len(receipt["checks"]),
                      "cases": len(receipt["cases"]),
                      "temp_restored": receipt["temp_restored"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
