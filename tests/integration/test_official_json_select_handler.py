"""Owned TEMP source import/projection/context/handler; no remote providers or LLMs."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from company_wiki.automation.execution_context import JobExecutionContext
from company_wiki.automation.execution_snapshot import ExecutionSnapshot
from company_wiki.automation.models import (
    Attempt, Event, HandlerOutcome, Job, JobStatus, RiskClass, canonical_json, make_job_key,
)
from company_wiki.automation.narrative_contracts import NarrativeSelectResult, SourceRevisionEventPayload
from company_wiki.automation.narrative_official_json import open_verified_projection
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.official_json_import import import_official_json_source
from company_wiki.source_catalog.official_json_projection import (
    ProjectionError, build_projection_from_refs, persist_projection,
)
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
from company_wiki.source_catalog.store import retire_document

T0 = "2026-10-10T00:00:00Z"
ANSWER = "Our new product has completed customer qualification and overseas shipments begin in the fourth quarter."
QUESTION = "When do the new product qualification and overseas shipments begin?"


class NoRawReader:
    def open_version(self, *args, **kwargs):
        pytest.fail("official projection must use source projection export, never raw anchor reader")

    def describe_version(self, *args, **kwargs):
        pytest.fail("official projection must not verify raw anchor as the entire subject")


@contextmanager
def owned_catalog(tmp_path):
    before = sorted(tmp_path.iterdir())
    with TemporaryDirectory(prefix="official-handler-", dir=tmp_path) as directory:
        root = Path(directory)
        (root / "companies").mkdir()
        catalog = SourceCatalog(CatalogConfig(project_root=root, catalog_dir=root / "catalog",
            roots=(RootSpec("company_raw", root / "companies", "company_raw"),)))
        try:
            yield catalog, root
        finally:
            catalog.close()
    assert sorted(tmp_path.iterdir()) == before


def import_page(catalog, page):
    raw = json.dumps(page, ensure_ascii=False, separators=(",", ":")).encode()
    sha = hashlib.sha256(raw).hexdigest()
    result = import_official_json_source(catalog, original=raw, request={
        "schema_version": "official-source-import-request/2", "request_id": "handler-" + sha,
        "max_bytes": 1048576, "content_sha256": sha, "mime_type": "application/json",
        "document_kind": "investor_relations", "source_subject": {
            "kind": "multi_issuer_event", "event_namespace": "handler-fixture", "event_id": "1",
            "issuer_refs": [], "attribution_status": "partial"},
        "capture_receipt": {"capture_method": "local_document", "tool_name": "offline-handler-test",
            "tool_call_id": sha, "captured_at": T0, "response_bytes": len(raw), "content_sha256": sha}})
    return SourceRef(**result["source_ref"]), raw


def flat_page(number):
    # Native answer deliberately precedes question in both source bytes and JSON insertion order.
    return {"ok": True, "result": {"page": number, "page_size": 1, "page_count": 2,
        "item_total": 2, "items": [{"ref": number, "org_id": 1, "org_name": "Acme",
        "a": ANSWER, "q": QUESTION, "answered": True,
        "created_at": "2026-09-01 10:00:00", "updated_at": "2026-09-02 10:00:00"}]}}


def persist(catalog, refs, *, issuer=1, layout="official-flat-list"):
    projection = build_projection_from_refs(catalog, refs=refs, layout_id=layout,
        issuer={"provider_company_id": issuer}, as_of_date="2026-10-08")
    persist_projection(catalog, projection)
    return projection


def make_context(projection, *, language="en", subject_override=None):
    binding = subject_override or NarrativeSubject.from_projection(projection).to_dict()
    payload = {"schema_version": "source-revision-event/3.0", "subject_binding": binding,
        "source_metadata": {"source_class": "official_json", "title": "Investor relations activity record",
            "document_kind": "investor_relations", "language": language}}
    parsed = SourceRevisionEventPayload.from_dict(payload)
    event = Event(event_id="event-official-select", event_type="source.revision_registered",
        subject_type="narrative_subject", subject_id=parsed.item_key, input_hash=parsed.input_hash,
        payload_json=canonical_json(payload), policy_version="narrative-v1", occurred_at=T0, observed_at=T0)
    job = Job(job_id="job-official-select", job_key=make_job_key("source.narrative_select",
        event.subject_type, event.subject_id, event.input_hash, event.policy_version, "1.0.0"),
        job_type="source.narrative_select", subject_type=event.subject_type, subject_id=event.subject_id,
        input_hash=event.input_hash, policy_version=event.policy_version, handler_version="1.0.0",
        risk_class=RiskClass.LOW, status=JobStatus.RUNNING, priority=0, not_before=T0,
        max_attempts=3, created_from_event_id=event.event_id, created_at=T0, updated_at=T0,
        last_error_code=None, last_error_detail=None)
    attempt = Attempt(attempt_id="attempt-official-select", job_id=job.job_id, attempt_no=1,
        worker_id="worker-official-select", lease_token="lease-official-select",
        lease_until="2026-10-10T00:05:00Z", started_at=T0, heartbeat_at=T0,
        finished_at=None, outcome=None, result_json=None, error_code=None, error_detail=None, runtime_generation=2)
    return JobExecutionContext.from_snapshot(ExecutionSnapshot(job, attempt, event, ()), checkpoint=lambda: None)


def handler(catalog):
    return NarrativeSelectHandler(reader=NoRawReader(), projection_catalog=catalog)


def assert_zero_resources(result):
    assert result.metrics.tokens == 0
    assert result.metrics.cost_usd == 0
    assert result.artifacts == ()
    assert result.effects == ()


def test_real_two_parent_select_public_dto_roles_locators_and_single_export(tmp_path, monkeypatch):
    with owned_catalog(tmp_path) as (catalog, _root):
        refs = [import_page(catalog, flat_page(number))[0] for number in (1, 2)]
        projection = persist(catalog, refs)
        view = open_verified_projection(catalog, projection_id=projection.projection_id,
            expected_projection_sha256=projection.projection_sha256)
        real_open = SourceVersionReader.open_version
        reads = []
        def counted(reader, ref, **kwargs):
            reads.append(ref.content_sha256)
            return real_open(reader, ref, **kwargs)
        monkeypatch.setattr(SourceVersionReader, "open_version", counted)
        result = handler(catalog)(make_context(projection))
        assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
        assert_zero_resources(result)
        assert reads == [ref.content_sha256 for ref in refs]
        dto = NarrativeSelectResult.from_dict(result.result)
        wire = dto.to_dict()
        assert set(wire) == {"schema_version", "subject_binding", "source_metadata", "parser", "selector",
            "selection", "evidence_spans", "prompt_review", "summary_scope"}
        assert wire["schema_version"] == "narrative-select-result/3.0"
        assert dto.subject == view.subject
        assert dto.item_key == projection.projection_id
        assert wire["parser"] == {"name": view.evidence_spans[0].parser_name,
            "version": view.evidence_spans[0].parser_version}
        assert wire["selection"]["coverage_complete"] is True
        assert wire["selection"]["pages_total"] == wire["selection"]["pages_read"] == 2
        assert wire["selection"]["lines_total"] == wire["selection"]["tables_total"] == 0
        spans = wire["evidence_spans"]
        assert {span["source_id"] for span in spans} == {ref.source_id for ref in refs}
        assert {span["raw_text"] for span in spans} == {ANSWER, QUESTION}
        assert len({span["structured_value"]["official_record_group_id"] for span in spans}) == 2
        source_by_id = {span.structured_value["source_evidence_id"]: span for span in view.evidence_spans}
        for span in spans:
            metadata = span["structured_value"]
            original = source_by_id[metadata["source_evidence_id"]]
            assert metadata["source_locator"] == original.structured_value["source_locator"]
            assert metadata["parent_content_sha256"] == original.structured_value["parent_content_sha256"]
            assert metadata["original_role"] == metadata["role"]
            assert metadata["source_role"] == ("investor_question" if metadata["role"] == "investor_question" else "management")
            assert metadata["language"] == "en"
            assert metadata["speaker_known"] is False
        assert wire["prompt_review"] == {"status": "not_reviewed", "source_sha256": None,
            "evidence_sha256": None, "policy_hash": None, "reviewed_at": None}


def test_shared_raw_two_issuers_native_language_and_translation_exclusion(tmp_path):
    chinese = "公司新产品已经完成客户验证，预计第四季度开始批量交付，海外订单持续增长。"
    records = [{"id": 1, "companyId": 1, "content": chinese, "contentEn": ANSWER * 20,
        "questionContent": "新产品验证及海外交付进展如何？", "isAnswered": True,
        "crtTime": "2026-09-01 10:00:00", "updTime": "2026-09-02 10:00:00"},
        {"id": 2, "companyId": 2, "content": ANSWER, "questionContent": QUESTION, "isAnswered": True,
        "crtTime": "2026-09-01 10:00:00", "updTime": "2026-09-02 10:00:00"}]
    page = {"success": True, "code": 200, "datas": [{"current": 1, "size": 2,
        "pages": 1, "total": 2, "records": records}]}
    with owned_catalog(tmp_path) as (catalog, root):
        ref, raw = import_page(catalog, page)
        outputs = []
        for issuer, language, native in ((1, "zh", chinese), (2, "en", ANSWER)):
            projection = persist(catalog, [ref], issuer=issuer, layout="official-paged-qa")
            result = handler(catalog)(make_context(projection, language=language))
            assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
            outputs.append(result.result)
            assert result.result["source_metadata"]["language"] == language
            assert native in {span["raw_text"] for span in result.result["evidence_spans"]}
            assert all(span["structured_value"]["provider_record_id"] == issuer for span in result.result["evidence_spans"])
            assert all("provider_translation" not in span["structured_value"]["role"] for span in result.result["evidence_spans"])
        assert outputs[0]["subject_binding"]["item_key"] != outputs[1]["subject_binding"]["item_key"]
        assert outputs[0]["subject_binding"]["parent_source_refs"] == outputs[1]["subject_binding"]["parent_source_refs"]
        assert SourceVersionReader(catalog).open_version(ref).data == raw
        assert len([p for p in (root / "companies").rglob("*.json") if not p.name.endswith(".source.json")]) == 1


def test_partial_positive_selection_never_signs_full_coverage(tmp_path):
    with owned_catalog(tmp_path) as (catalog, _root):
        ref, _raw = import_page(catalog, flat_page(1))
        result = handler(catalog)(make_context(persist(catalog, [ref])))
        assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
        assert result.result["evidence_spans"]
        assert result.result["selection"]["status"] == "partial"
        assert result.result["selection"]["coverage_complete"] is False
        assert result.result["selection"]["pages_total"] == 1
        assert_zero_resources(result)


@pytest.mark.parametrize("change", ["bytes", "status"])
def test_second_real_parent_current_change_refuses_with_zero_model(tmp_path, change):
    with owned_catalog(tmp_path) as (catalog, root):
        first, _ = import_page(catalog, flat_page(1))
        second, raw = import_page(catalog, flat_page(2))
        context = make_context(persist(catalog, [first, second]))
        if change == "bytes":
            path = next(p for p in (root / "companies").rglob("*.json") if p.read_bytes() == raw)
            path.write_bytes(raw.replace(b"fourth", b"fifth", 1))
            try:
                result = handler(catalog)(context)
            finally:
                path.write_bytes(raw)
            assert handler(catalog)(context).outcome is HandlerOutcome.SUCCEEDED
        else:
            retire_document(catalog.store, document_id=second.document_id,
                reason="owned handler negative control", created_by="offline-test")
            result = handler(catalog)(context)
        assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
        assert result.error is not None
        assert result.result == {}
        assert_zero_resources(result)
        assert SourceVersionReader(catalog).open_version(first).content_sha256 == first.content_sha256


@pytest.mark.parametrize("complete", [True, False])
def test_empty_fields_skip_only_with_complete_capture_never_guess_language(tmp_path, complete):
    page = {"ok": True, "result": {"page": 1, "page_size": 1, "page_count": 1 if complete else 2,
        "item_total": 1 if complete else 2, "items": [{"ref": 1, "org_id": 1, "org_name": "Acme",
        "created_at": "2026-09-01 10:00:00", "updated_at": "2026-09-02 10:00:00"}]}}
    with owned_catalog(tmp_path) as (catalog, _root):
        ref, _raw = import_page(catalog, page)
        projection = persist(catalog, [ref])
        view = open_verified_projection(catalog, projection_id=projection.projection_id,
            expected_projection_sha256=projection.projection_sha256)
        assert view.language is None
        result = handler(catalog)(make_context(projection, language="unknown"))
        if complete:
            assert result.outcome is HandlerOutcome.SUCCEEDED
            assert result.result["selection"]["status"] == "skipped_no_narrative"
            assert result.result["selection"]["coverage_complete"] is True
            assert result.result["source_metadata"]["language"] == "unknown"
            assert result.result["evidence_spans"] == ()
        else:
            assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
            assert result.error.code == "SOURCE_LANGUAGE_UNDETERMINED"
            assert result.result == {}
        assert_zero_resources(result)


@pytest.mark.parametrize("change", ["language", "issuer", "coverage"])
def test_event_cannot_relabel_true_projection_context(tmp_path, change):
    with owned_catalog(tmp_path) as (catalog, _root):
        refs = [import_page(catalog, flat_page(n))[0] for n in (1, 2)]
        projection = persist(catalog, refs)
        binding = NarrativeSubject.from_projection(projection).to_dict()
        language = "en"
        if change == "language":
            language = "zh"
        elif change == "issuer":
            binding["issuer"]["provider_company_id"] = 2
        else:
            binding["coverage"]["issuer_records_selected"] = 500
        result = handler(catalog)(make_context(projection, language=language, subject_override=binding))
        assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
        assert result.error is not None
        assert result.result == {}
        assert_zero_resources(result)


def test_missing_projection_dependency_has_typed_failure_no_transcript_fallback(tmp_path):
    with owned_catalog(tmp_path) as (catalog, _root):
        ref, _ = import_page(catalog, flat_page(1))
        context = make_context(persist(catalog, [ref]))
        result = NarrativeSelectHandler(reader=NoRawReader())(context)
        assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
        assert result.error.code == "SOURCE_UNAVAILABLE"
        assert_zero_resources(result)


def test_unknown_layout_source_port_refusal_has_typed_failure_no_fallback(tmp_path, monkeypatch):
    with owned_catalog(tmp_path) as (catalog, _root):
        ref, _ = import_page(catalog, flat_page(1))
        context = make_context(persist(catalog, [ref]))
        def refuse(*args, **kwargs):
            raise ProjectionError("unknown_layout_id")
        monkeypatch.setattr("company_wiki.automation.narrative_select.open_verified_projection", refuse)
        result = handler(catalog)(context)
        assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
        assert result.error.code == "PARSER_INCOMPLETE"
        assert result.error.detail == "unknown_layout_id"
        assert_zero_resources(result)


def test_output_nested_mutation_does_not_change_event_or_next_select(tmp_path):
    with owned_catalog(tmp_path) as (catalog, _root):
        refs = [import_page(catalog, flat_page(n))[0] for n in (1, 2)]
        context = make_context(persist(catalog, refs))
        runner = handler(catalog)
        first = runner(context)
        assert first.outcome is HandlerOutcome.SUCCEEDED, first.error
        detached = first.to_dict()["result"]
        original = canonical_json(detached)
        with pytest.raises(TypeError):
            first.result["subject_binding"]["issuer"]["provider_company_id"] = 900
        detached["subject_binding"]["issuer"]["provider_company_id"] = 900
        detached["evidence_spans"][0]["structured_value"]["record_times"]["created_at"] = "changed"
        second = runner(context)
        assert second.outcome is HandlerOutcome.SUCCEEDED, second.error
        assert canonical_json(second.to_dict()["result"]) == original
        assert context.source_revision.subject.issuer["provider_company_id"] == 1


def test_complete_projection_with_no_native_fields_skips_without_guessing_language(tmp_path):
    with owned_catalog(tmp_path) as (catalog, _root):
        page = flat_page(1)
        page["result"].update(page_count=1, item_total=1)
        page["result"]["items"][0].update(q="", a="")
        ref, _ = import_page(catalog, page)
        projection = persist(catalog, [ref])
        view = open_verified_projection(catalog, projection_id=projection.projection_id,
            expected_projection_sha256=projection.projection_sha256)
        assert view.coverage_complete and view.language is None
        assert not any(span.raw_text and span.raw_text.strip() for span in view.evidence_spans)
        result = handler(catalog)(make_context(projection, language="unknown"))
        assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
        assert result.result["selection"]["status"] == "skipped_no_narrative"
        assert result.result["source_metadata"]["language"] == "unknown"
        assert result.result["evidence_spans"] == ()
        assert result.result["parser"] == {"name": "cwp_official_json", "version": "1.0.1"}
        assert_zero_resources(result)
