"""Real importer/source ports/selector in restored owned TEMP catalogs; no provider."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unicodedata

import pytest

from company_wiki.automation.narrative_official_json import (
    open_verified_projection, select_verified_projection,
)
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.official_json_import import import_official_json_source
from company_wiki.source_catalog.official_json_projection import (
    ProjectionError, build_projection_from_refs, persist_projection, replay_projection,
)
from company_wiki.source_catalog.source_reader import SourceReadError, SourceRef, SourceVersionReader
from company_wiki.source_catalog.store import retire_document


ANSWER = "Our new product has completed customer qualification and overseas shipments begin in the fourth quarter."
QUESTION = "When do the new product qualification and overseas shipments begin?"


@contextmanager
def catalog_fixture(root):
    (root / "companies").mkdir()
    catalog = SourceCatalog(CatalogConfig(project_root=root, catalog_dir=root / "catalog",
        roots=(RootSpec("company_raw", root / "companies", "company_raw"),)))
    try:
        yield catalog
    finally:
        catalog.close()


def import_page(catalog, value):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    sha = hashlib.sha256(raw).hexdigest()
    result = import_official_json_source(catalog, original=raw, request={
        "schema_version": "official-source-import-request/2", "request_id": "adapter-" + sha,
        "max_bytes": 1048576, "content_sha256": sha, "mime_type": "application/json",
        "document_kind": "investor_relations", "source_subject": {
            "kind": "multi_issuer_event", "event_namespace": "adapter-fixture", "event_id": "1",
            "issuer_refs": [], "attribution_status": "partial"},
        "capture_receipt": {"capture_method": "local_document", "tool_name": "offline-adapter-test",
            "tool_call_id": sha, "captured_at": "2026-10-10T00:00:00Z",
            "response_bytes": len(raw), "content_sha256": sha}})
    return SourceRef(**result["source_ref"]), raw


def flat_page(number, *, company=1, record_id=None, created="2026-09-01 10:00:00", updated="2026-09-02 10:00:00"):
    record = {"ref": record_id or number * 100 + company, "org_id": company,
        "org_name": "Acme" if company == 1 else "Other", "a": ANSWER, "q": QUESTION,
        "answered": True, "created_at": created}
    if updated is not None:
        record["updated_at"] = updated
    return {"ok": True, "result": {"page": number, "page_size": 1, "page_count": 2,
        "item_total": 2, "items": [record]}}


def persisted(catalog, refs, *, issuer=1, layout="official-flat-list", cutoff="2026-10-08"):
    projection = build_projection_from_refs(catalog, refs=refs, layout_id=layout,
        issuer={"provider_company_id": issuer}, as_of_date=cutoff)
    persist_projection(catalog, projection)
    return projection


def open_view(catalog, projection):
    return open_verified_projection(catalog, projection_id=projection.projection_id,
        expected_projection_sha256=projection.projection_sha256)


def test_two_real_parents_once_per_export_and_restore_owned_directory(tmp_path, monkeypatch):
    before = sorted(tmp_path.iterdir())
    with TemporaryDirectory(prefix="official-adapter-", dir=tmp_path) as owned:
        with catalog_fixture(Path(owned)) as catalog:
            first, original_first = import_page(catalog, flat_page(1))
            second, original_second = import_page(catalog, flat_page(2))
            projection = persisted(catalog, [first, second])
            real_open = SourceVersionReader.open_version
            opened = []
            def counted_open(reader, ref, **kwargs):
                opened.append(ref.content_sha256)
                return real_open(reader, ref, **kwargs)
            monkeypatch.setattr(SourceVersionReader, "open_version", counted_open)
            view = open_view(catalog, projection)
            assert opened == [first.content_sha256, second.content_sha256]
            assert view.coverage_complete is True
            assert view.language == "en"
            package = select_verified_projection(view, title="Investor relations activity record")
            assert package.evidence_spans
            assert package.coverage_complete is True
            assert set(span.source_id for span in package.evidence_spans) == {first.source_id, second.source_id}
            assert set(span.structured_value["parent_content_sha256"] for span in package.evidence_spans) == {
                first.content_sha256, second.content_sha256}
            assert len({span.structured_value["qa_group_id"] for span in package.evidence_spans}) == 2
            # Selection reuses the immutable view and does not open/parse parents again.
            assert opened == [first.content_sha256, second.content_sha256]
            assert real_open(SourceVersionReader(catalog), first).data == original_first
            assert real_open(SourceVersionReader(catalog), second).data == original_second
    assert sorted(tmp_path.iterdir()) == before


def test_projection_persist_close_reopen_keeps_adapter_identity(tmp_path):
    root = tmp_path / "owned"
    root.mkdir()
    with catalog_fixture(root) as catalog:
        refs = [import_page(catalog, flat_page(n))[0] for n in (1, 2)]
        projection = persisted(catalog, refs)
        original = open_view(catalog, projection).export_dict()
        config = catalog.config
    reopened = SourceCatalog(config)
    try:
        view = open_view(reopened, projection)
        assert view.export_dict() == original
        assert view.subject.item_key == projection.projection_id
    finally:
        reopened.close()


@pytest.mark.parametrize("change", ["bytes", "status"])
def test_second_parent_current_bytes_or_status_refusal(tmp_path, change):
    with catalog_fixture(tmp_path) as catalog:
        first, _ = import_page(catalog, flat_page(1))
        second, raw = import_page(catalog, flat_page(2))
        projection = persisted(catalog, [first, second])
        assert open_view(catalog, projection).evidence_spans
        if change == "bytes":
            target = next(path for path in (tmp_path / "companies").rglob("*.json")
                if not path.name.endswith(".source.json") and path.read_bytes() == raw)
            target.write_bytes(raw.replace(b"fourth", b"fifth", 1))
            try:
                with pytest.raises(SourceReadError):
                    open_view(catalog, projection)
            finally:
                target.write_bytes(raw)
            assert open_view(catalog, projection).evidence_spans
        else:
            retire_document(catalog.store, document_id=second.document_id,
                reason="owned integration negative control", created_by="offline-test")
            with pytest.raises(SourceReadError):
                open_view(catalog, projection)
        assert SourceVersionReader(catalog).open_version(first).content_sha256 == first.content_sha256


def test_one_shared_raw_two_issuers_keep_distinct_subject_and_native_language(tmp_path):
    chinese = "公司新产品已经完成客户验证，预计第四季度开始批量交付，海外订单持续增长。"
    records = [{"id": 1, "companyId": 1, "content": chinese,
                "contentEn": ANSWER * 20, "isAnswered": True,
                "questionContent": "新产品客户验证及出海订单的交付情况如何？",
                "crtTime": "2026-09-01 10:00:00", "updTime": "2026-09-02 10:00:00"},
               {"id": 2, "companyId": 2, "content": ANSWER * 10, "isAnswered": True,
                "crtTime": "2026-09-01 10:00:00", "updTime": "2026-09-02 10:00:00"}]
    page = {"success": True, "code": 200, "datas": [{"current": 1, "size": 2, "pages": 1,
        "total": 2, "records": records}]}
    with catalog_fixture(tmp_path) as catalog:
        ref, raw = import_page(catalog, page)
        one = open_view(catalog, persisted(catalog, [ref], issuer=1, layout="official-paged-qa"))
        two = open_view(catalog, persisted(catalog, [ref], issuer=2, layout="official-paged-qa"))
        assert one.subject.item_key != two.subject.item_key
        assert one.subject.parent_source_refs == two.subject.parent_source_refs
        assert one.language == "zh"
        assert two.language == "en"
        assert all(span.structured_value["provider_record_id"] == 1 for span in one.evidence_spans)
        assert all(span.structured_value["provider_record_id"] == 2 for span in two.evidence_spans)
        assert all("provider_translation" not in span.structured_value["role"] for span in one.evidence_spans)
        assert len([p for p in (tmp_path / "companies").rglob("*.json")
                    if not p.name.endswith(".source.json")]) == 1
        assert SourceVersionReader(catalog).open_version(ref).data == raw


@pytest.mark.parametrize("updated", ["2026-10-09 10:00:00", "unparseable"])
def test_after_cutoff_or_unknown_time_is_not_selected(tmp_path, updated):
    with catalog_fixture(tmp_path) as catalog:
        ref, _ = import_page(catalog, flat_page(1, updated=updated))
        view = open_view(catalog, persisted(catalog, [ref]))
        assert view.evidence_spans == ()
        assert view.language is None
        assert view.coverage_complete is False
        package = select_verified_projection(view, title="Investor relations")
        assert not package.evidence_spans
        assert not package.coverage_complete
        assert package.status == "partial"


def test_company_precollected_answer_and_unknown_statement_roles(tmp_path):
    records = [{"id": 36395, "companyId": 1, "question": QUESTION, "answer": ANSWER,
        "crtTime": "2026-09-01 10:00:00", "updTime": "2026-09-02 10:00:00"},
        {"id": 7, "companyId": 1, "content": ANSWER,
        "crtTime": "2026-09-01 10:00:00", "updTime": "2026-09-02 10:00:00"}]
    page = {"success": True, "code": 200, "datas": [{"current": 1, "size": 2, "pages": 1,
        "total": 2, "records": records}]}
    with catalog_fixture(tmp_path) as catalog:
        ref, _ = import_page(catalog, page)
        view = open_view(catalog, persisted(catalog, [ref], layout="official-paged-qa"))
        package = select_verified_projection(view, title="Investor relations activity record")
        fields = {span.structured_value["provider_record_id"]: span for span in package.evidence_spans
                  if span.structured_value["role"] != "investor_question"}
        assert fields[36395].structured_value["source_role"] == "company_filing"
        assert fields[7].structured_value["source_role"] == "unknown"
        assert fields[36395].structured_value["speaker_known"] is False
        assert all(span.raw_text in {ANSWER, QUESTION} for span in package.evidence_spans)


def test_legal_unknown_layout_retains_original_and_refuses_projection(tmp_path):
    with catalog_fixture(tmp_path) as catalog:
        ref, raw = import_page(catalog, {"unregistered": {"rows": [{"value": ANSWER}]}})
        assert SourceVersionReader(catalog).open_version(ref).data == raw
        with pytest.raises(ProjectionError):
            persisted(catalog, [ref])


@pytest.mark.parametrize("prefix,suffix", [("  ", "  "), ("\t", "\r\n"), ("\n\u00a0", "\u00a0\n")])
def test_original_field_whitespace_survives_selector_and_real_replay(tmp_path, prefix, suffix):
    original_answer = prefix + ANSWER + " Our café product line is expanding." + suffix
    original_question = suffix + QUESTION + prefix
    page = flat_page(1)
    page["result"]["page_count"] = 1
    page["result"]["item_total"] = 1
    record = page["result"]["items"][0]
    record["a"] = original_answer
    record["q"] = original_question
    with catalog_fixture(tmp_path) as catalog:
        ref, raw = import_page(catalog, page)
        projection = persisted(catalog, [ref])
        view = open_view(catalog, projection)
        package = select_verified_projection(view, title="Investor relations activity record")
        source_replay = replay_projection(catalog, projection)
        actual_fields = {(item["parent_content_sha256"], field["locator"]): field
            for item in source_replay["records"] for field in item["fields"]}
        assert {span.raw_text for span in package.evidence_spans} == {original_answer, original_question}
        for span in package.evidence_spans:
            metadata = span.structured_value
            actual = actual_fields[(metadata["parent_content_sha256"], metadata["source_locator"])]
            assert span.raw_text == actual["text"]
            assert metadata["decoded_sha256"] == hashlib.sha256(span.raw_text.encode()).hexdigest()
            assert metadata["text_sha256"] == metadata["decoded_sha256"]
            assert metadata["role"] == actual["role"]
            assert span.source_id == ref.source_id
        assert SourceVersionReader(catalog).open_version(ref).data == raw


def test_source_owned_nfc_display_and_original_decoded_identity_are_distinct(tmp_path):
    original_answer = "  " + ANSWER + " Our cafe\u0301 product line is expanding.\n"
    display = unicodedata.normalize("NFC", original_answer)
    assert display != original_answer
    page = flat_page(1)
    page["result"]["page_count"] = 1
    page["result"]["item_total"] = 1
    page["result"]["items"][0]["a"] = original_answer
    with catalog_fixture(tmp_path) as catalog:
        ref, original_bytes = import_page(catalog, page)
        projection = persisted(catalog, [ref])
        view = open_view(catalog, projection)
        original_span = next(span for span in view.evidence_spans if span.structured_value["role"] == "management_answer")
        assert original_span.raw_text == display
        assert original_span.structured_value["decoded_sha256"] == hashlib.sha256(original_answer.encode()).hexdigest()
        package = select_verified_projection(view, title="Investor relations activity record")
        selected = next(span for span in package.evidence_spans if span.structured_value["role"] == "management_answer")
        assert selected.raw_text == original_span.raw_text
        assert selected.structured_value["decoded_sha256"] == original_span.structured_value["decoded_sha256"]
        assert selected.structured_value["text_sha256"] == hashlib.sha256(display.encode()).hexdigest()
        replay = replay_projection(catalog, projection)
        actual = next(field for record in replay["records"] for field in record["fields"] if field["field"] == "a")
        assert actual["text"] == original_answer
        assert actual["decoded_sha256"] == selected.structured_value["decoded_sha256"]
        assert unicodedata.normalize("NFC", actual["text"]) == selected.raw_text
        assert actual["locator"] == selected.structured_value["source_locator"]
        assert SourceVersionReader(catalog).open_version(ref).data == original_bytes
