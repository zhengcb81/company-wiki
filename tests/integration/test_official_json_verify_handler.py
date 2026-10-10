"""Real TEMP source→select→local replay-model→verify; factory seams explicitly isolated."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from company_wiki.automation.execution_context import JobExecutionContext
from company_wiki.automation.execution_snapshot import DependencyExecutionResult, ExecutionSnapshot
from company_wiki.automation.models import (
    Attempt, Event, HandlerOutcome, Job, JobStatus, RiskClass, canonical_json, make_job_key,
)
from company_wiki.automation.narrative_contracts import (
    NarrativeBundle, NarrativeSelectResult, NarrativeSummaryResult, SourceRevisionEventPayload,
)
from company_wiki.automation.narrative_model import (
    NARRATIVE_PROMPT_VERSION, PROJECTION_NARRATIVE_PROMPT_VERSION, PROJECTION_MODEL_REQUEST_SCHEMA,
    NarrativeModelResponse,
)
from company_wiki.automation.narrative_official_json import NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION
from company_wiki.automation.narrative_runtime import NarrativeRuntimeDependencies, register_narrative_handlers
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from company_wiki.automation.worker_process import WorkerProcessSpec
from company_wiki.automation.narrative_official_json import open_verified_projection
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.official_json_import import import_official_json_source
from company_wiki.source_catalog.official_json_projection import (
    build_projection_from_refs, persist_projection,
)
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
from company_wiki.source_catalog.store import retire_document
from company_wiki.source_contract import EvidenceSpan
from types import SimpleNamespace

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


def make_context(projection, *, language="en", subject_override=None, job_type="source.narrative_select", dependencies=None):
    binding = subject_override or NarrativeSubject.from_projection(projection).to_dict()
    payload = {"schema_version": "source-revision-event/3.0", "subject_binding": binding,
        "source_metadata": {"source_class": "official_json", "title": "Investor relations activity record",
            "document_kind": "investor_relations", "language": language}}
    parsed = SourceRevisionEventPayload.from_dict(payload)
    event = Event(event_id="event-official-select", event_type="source.revision_registered",
        subject_type="narrative_subject", subject_id=parsed.item_key, input_hash=parsed.input_hash,
        payload_json=canonical_json(payload), policy_version="narrative-v1", occurred_at=T0, observed_at=T0)
    job = Job(job_id="job-official-select", job_key=make_job_key(job_type,
        event.subject_type, event.subject_id, event.input_hash, event.policy_version, "1.0.0"),
        job_type=job_type, subject_type=event.subject_type, subject_id=event.subject_id,
        input_hash=event.input_hash, policy_version=event.policy_version, handler_version="1.0.0",
        risk_class=RiskClass.LOW, status=JobStatus.RUNNING, priority=0, not_before=T0,
        max_attempts=3, created_from_event_id=event.event_id, created_at=T0, updated_at=T0,
        last_error_code=None, last_error_detail=None)
    attempt = Attempt(attempt_id="attempt-official-select", job_id=job.job_id, attempt_no=1,
        worker_id="worker-official-select", lease_token="lease-official-select",
        lease_until="2026-10-10T00:05:00Z", started_at=T0, heartbeat_at=T0,
        finished_at=None, outcome=None, result_json=None, error_code=None, error_detail=None, runtime_generation=2)
    deps = tuple(DependencyExecutionResult("dep-job-" + str(index), kind, "1.0.0",
        "dep-attempt-" + str(index), 1, result) for index, (kind, result) in enumerate((dependencies or {}).items()))
    return JobExecutionContext.from_snapshot(ExecutionSnapshot(job, attempt, event, deps), checkpoint=lambda: None)



GENERATION = hashlib.sha256(b"explicit-owned-test-generation").hexdigest()


class OfflineProjectionModel:
    """No transport: exercise actual prompt/decode/summary handler contracts."""
    def generate(self, request):
        envelope = json.loads(request.data_json)
        row = envelope["evidence"][0]
        role = row[2] if len(row) > 2 else envelope["default_source_role"]
        question = role == "investor_question"
        draft = {key: envelope["subject"][key] for key in ("subject_id", "subject_sha256", "language")}
        draft.update({"claims": [{"claim_id": "claim-owned-official", "text": row[1].strip(),
            "evidence_ids": [row[0]], "claim_type": "analyst_question" if question else "company_statement",
            "modality": "question" if question else "planned"}], "status": "draft"})
        return NarrativeModelResponse(adapter_id="offline-fixture", model_id="fixture-official",
            prompt_version=request.prompt_version, response_bytes=canonical_json({"draft": draft}).encode())


def dependencies_for(catalog, projection, *, subject_override=None):
    selected = NarrativeSelectHandler(reader=NoRawReader(), projection_catalog=catalog)(make_context(projection))
    assert selected.outcome is HandlerOutcome.SUCCEEDED, selected.error
    if subject_override is not None:
        selected = replace_result(selected, "subject_binding", subject_override)
    summary = NarrativeSummarizeHandler(model=OfflineProjectionModel())(make_context(projection,
        subject_override=subject_override, job_type="source.narrative_summarize",
        dependencies={"source.narrative_select": selected}))
    assert summary.outcome is HandlerOutcome.SUCCEEDED, summary.error
    return {"source.narrative_select": selected, "source.narrative_summarize": summary}


def replace_result(result, key, value):
    from dataclasses import replace
    raw = result.to_dict()["result"]
    raw[key] = value
    return replace(result, result=raw)


def verification_context(projection, dependencies, *, subject_override=None):
    return make_context(projection, subject_override=subject_override,
        job_type="source.narrative_verify", dependencies=dependencies)


def verifier(catalog, generation=GENERATION):
    return NarrativeVerifyHandler(reader=NoRawReader(), projection_catalog=catalog,
        generation_sha256=None if generation is None else lambda _subject: generation)


def test_real_all_parents_replayed_once_and_projection_generation_effect(tmp_path, monkeypatch):
    with owned_catalog(tmp_path) as (catalog, _root):
        refs = [import_page(catalog, flat_page(n))[0] for n in (1, 2)]
        projection = persist(catalog, refs)
        dependencies = dependencies_for(catalog, projection)
        assert dependencies["source.narrative_summarize"].result["model"]["prompt_version"] == PROJECTION_NARRATIVE_PROMPT_VERSION
        reads = []
        real_open = SourceVersionReader.open_version
        def counted(reader, ref, **kwargs):
            reads.append(ref.content_sha256)
            return real_open(reader, ref, **kwargs)
        monkeypatch.setattr(SourceVersionReader, "open_version", counted)
        result = verifier(catalog)(verification_context(projection, dependencies))
        assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
        assert reads == [ref.content_sha256 for ref in refs]
        bundle = NarrativeBundle.from_dict(result.result)
        selected = NarrativeSelectResult.from_dict(dependencies["source.narrative_select"].result)
        summary = NarrativeSummaryResult.from_dict(dependencies["source.narrative_summarize"].result)
        bundle.validate_against(selected, summary)
        assert bundle.subject == selected.subject
        assert bundle.item_key == projection.projection_id
        assert bundle.schema_version == "narrative-bundle/3.0"
        assert {span.source_id for span in bundle.evidence_spans} == {ref.source_id for ref in refs}
        assert not {"source_ref", "expected_read_policy_sha256", "transcript_lineage", "transcript_byte_bindings"} & result.result.keys()
        assert bundle.versions.parser == selected.parser.version
        assert bundle.versions.prompt == PROJECTION_NARRATIVE_PROMPT_VERSION
        assert bundle.replay.locator_count == len(selected.evidence_spans)
        assert result.effects[0].target == "urn:company-wiki:narrative-projection-bundle:" + projection.projection_sha256 + ":" + GENERATION
        assert result.metrics.tokens == result.metrics.cost_usd == 0


@pytest.mark.parametrize("change", ["bytes", "status"])
def test_changed_second_parent_after_select_refuses_no_effect(tmp_path, change):
    with owned_catalog(tmp_path) as (catalog, root):
        first, _ = import_page(catalog, flat_page(1))
        second, raw = import_page(catalog, flat_page(2))
        projection = persist(catalog, [first, second])
        dependencies = dependencies_for(catalog, projection)
        context = verification_context(projection, dependencies)
        if change == "bytes":
            target = next(p for p in (root / "companies").rglob("*.json") if p.read_bytes() == raw)
            target.write_bytes(raw.replace(b"fourth", b"fifth", 1))
            try:
                result = verifier(catalog)(context)
            finally:
                target.write_bytes(raw)
            assert verifier(catalog)(context).outcome is HandlerOutcome.SUCCEEDED
        else:
            retire_document(catalog.store, document_id=second.document_id,
                reason="owned verify negative control", created_by="offline-test")
            result = verifier(catalog)(context)
        assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
        assert result.error is not None
        assert result.effects == ()
        assert result.metrics.tokens == result.metrics.cost_usd == 0
        assert SourceVersionReader(catalog).open_version(first).content_sha256 == first.content_sha256


def test_renamed_issuer_in_event_and_dependencies_cannot_alias_same_raw_anchor(tmp_path):
    with owned_catalog(tmp_path) as (catalog, _root):
        ref, _ = import_page(catalog, flat_page(1))
        projection = persist(catalog, [ref])
        binding = NarrativeSubject.from_projection(projection).to_dict()
        binding["issuer"]["provider_company_id"] = 99
        dependencies = dependencies_for(catalog, projection, subject_override=binding)
        result = verifier(catalog)(verification_context(projection, dependencies, subject_override=binding))
        assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
        assert result.error.code == "DEPENDENCY_INVALID"
        assert result.effects == ()


@pytest.mark.parametrize("change", ["parser", "prompt", "text", "role"])
def test_selected_or_summary_semantic_tampering_refuses_projection_publish(tmp_path, change):
    with owned_catalog(tmp_path) as (catalog, _root):
        ref, _ = import_page(catalog, flat_page(1))
        projection = persist(catalog, [ref])
        dependencies = dependencies_for(catalog, projection)
        selected = dependencies["source.narrative_select"]
        if change == "prompt":
            model = dependencies["source.narrative_summarize"].to_dict()["result"]["model"]
            model["prompt_version"] = NARRATIVE_PROMPT_VERSION
            dependencies["source.narrative_summarize"] = replace_result(dependencies["source.narrative_summarize"], "model", model)
        elif change == "parser":
            parser = selected.to_dict()["result"]["parser"]
            parser["version"] = "9.9.9"
            dependencies["source.narrative_select"] = replace_result(selected, "parser", parser)
        else:
            spans = selected.to_dict()["result"]["evidence_spans"]
            source = EvidenceSpan.from_dict(spans[0])
            metadata = source.to_dict()["structured_value"]
            text = source.raw_text
            if change == "text":
                text += " This invented change has no source."
                metadata["text_sha256"] = hashlib.sha256(text.encode()).hexdigest()
            else:
                metadata["original_role"] = metadata["role"] = "company_statement"
                metadata["source_role"] = "company_filing"
            span = EvidenceSpan.create(source_id=source.source_id, coordinates=source.coordinates,
                raw_text=text, structured_value=metadata, parser_name=source.parser_name,
                parser_version=source.parser_version, parse_status=source.parse_status, quality_flags=source.quality_flags)
            spans[0] = span.to_dict()
            dependencies["source.narrative_select"] = replace_result(selected, "evidence_spans", spans)
            summary = NarrativeSummarizeHandler(model=OfflineProjectionModel())(make_context(projection,
                job_type="source.narrative_summarize", dependencies={"source.narrative_select": dependencies["source.narrative_select"]}))
            assert summary.outcome is HandlerOutcome.SUCCEEDED, summary.error
            dependencies["source.narrative_summarize"] = summary
        result = verifier(catalog)(verification_context(projection, dependencies))
        assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
        assert result.error.code in {"DEPENDENCY_INVALID", "LOCATOR_REPLAY_FAILED"}
        assert result.effects == ()


@pytest.mark.parametrize("generation", [None, "", "invalid"])
def test_projection_generation_is_required_with_no_anchor_target_fallback(tmp_path, generation):
    with owned_catalog(tmp_path) as (catalog, _root):
        ref, _ = import_page(catalog, flat_page(1))
        projection = persist(catalog, [ref])
        context = verification_context(projection, dependencies_for(catalog, projection))
        result = verifier(catalog, generation)(context)
        assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
        assert result.error.code == "DEPENDENCY_INVALID"
        assert result.effects == ()


def test_new_generation_cannot_reuse_old_projection_effect_target(tmp_path):
    with owned_catalog(tmp_path) as (catalog, _root):
        ref, _ = import_page(catalog, flat_page(1))
        projection = persist(catalog, [ref])
        context = verification_context(projection, dependencies_for(catalog, projection))
        first = verifier(catalog)(context)
        second = verifier(catalog, hashlib.sha256(b"explicit-next-owned-generation").hexdigest())(context)
        assert first.outcome is second.outcome is HandlerOutcome.SUCCEEDED
        assert first.effects[0].target != second.effects[0].target
        assert first.effects[0].effect_key != second.effects[0].effect_key


def test_projection_verify_without_source_port_is_typed_not_raw_dispatch(tmp_path):
    with owned_catalog(tmp_path) as (catalog, _root):
        ref, _ = import_page(catalog, flat_page(1))
        projection = persist(catalog, [ref])
        context = verification_context(projection, dependencies_for(catalog, projection))
        result = NarrativeVerifyHandler(reader=NoRawReader())(context)
        assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
        assert result.error.code == "SOURCE_UNAVAILABLE"
        assert result.effects == ()


def test_runtime_registers_shared_catalog_and_generation_resolver_for_real_handlers(tmp_path):
    class Registrar:
        def __init__(self):
            self.handlers = {}
        def register(self, name, handler):
            self.handlers[name] = handler
    with owned_catalog(tmp_path) as (catalog, _root):
        ref, _ = import_page(catalog, flat_page(1))
        projection = persist(catalog, [ref])
        registrar = Registrar()
        dependencies = NarrativeRuntimeDependencies(reader=NoRawReader(), model=OfflineProjectionModel(),
            projection_catalog=catalog, generation_sha256=lambda _subject: GENERATION)
        register_narrative_handlers(registrar, dependencies)
        selected = registrar.handlers["source.narrative_select"](make_context(projection))
        assert selected.outcome is HandlerOutcome.SUCCEEDED, selected.error
        summary = registrar.handlers["source.narrative_summarize"](make_context(projection,
            job_type="source.narrative_summarize", dependencies={"source.narrative_select": selected}))
        assert summary.outcome is HandlerOutcome.SUCCEEDED, summary.error
        result = registrar.handlers["source.narrative_verify"](verification_context(projection,
            {"source.narrative_select": selected, "source.narrative_summarize": summary}))
        assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
        assert result.effects[0].target.endswith(":" + GENERATION)


@pytest.mark.parametrize("invalid_component", [None, "projection_prompt", "projection_model_request_schema", "official_json_adapter"])
def test_factory_reads_frozen_generation_binding_and_checks_actual_execution_versions(tmp_path, monkeypatch, invalid_component):
    # Explicit composition seam: fake only RunStore retrieval, keep real source config/catalog/handlers.
    from company_wiki.automation import narrative_worker_factory as factory
    with owned_catalog(tmp_path) as (catalog, root):
        ref, _ = import_page(catalog, flat_page(1))
        projection = persist(catalog, [ref])
        subject = NarrativeSubject.from_projection(projection)
        binding = {"schema_version": "narrative-run-binding/4", "execution_versions": {
            "projection_prompt": PROJECTION_NARRATIVE_PROMPT_VERSION,
            "projection_model_request_schema": PROJECTION_MODEL_REQUEST_SCHEMA,
            "official_json_adapter": NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION},
            "generation_manifests": {subject.item_key: {"settings_sha256": "1" * 64,
                "generation_sha256": GENERATION, "source_inputs": {"subject_binding": subject.to_dict()}}}}
        if invalid_component is not None:
            binding["execution_versions"][invalid_component] = "old-version"
        run = SimpleNamespace(job_ids=("owned-factory-job",), input_hash="2" * 64,
            model_id="fixture-model", prompt_version=NARRATIVE_PROMPT_VERSION, blocked=False,
            binding_json=canonical_json(binding))
        monkeypatch.setattr(factory, "NarrativeRunStore", lambda _path: SimpleNamespace(get_run=lambda _id: run))
        config = root / "factory-catalog.json"
        config.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": "catalog", "roots": [{
            "root_id": "company_raw", "path": "companies", "kind": "company_raw",
            "adapter_id": "company_raw_v1", "read_only": True, "reusable_for_filing": True}]}), encoding="utf-8")
        options = {"project_root": str(root), "catalog_config_path": str(config), "run_id": "owned-factory-run",
            "expected_run_input_hash": run.input_hash, "model": {"model_id": "fixture-model",
            "endpoint": "https://fixture.invalid/v1/chat/completions", "api_key_env": "NEVER_READ_OWNED_KEY"}}
        spec = WorkerProcessSpec(worker_id="owned-factory-compute", role="compute", db_path=str(root / "unused.db"),
            log_dir=str(root / "logs"), runtime_factory_path="company_wiki.automation.narrative_worker_factory:create_runtime",
            runtime_options_json=canonical_json(options), allowed_job_types=("source.narrative_select", "source.narrative_verify"),
            lease_seconds=30, heartbeat_interval_seconds=5, idle_sleep_seconds=0.05, child_log_max_bytes=4096,
            allowed_job_ids=run.job_ids)
        captured = []
        register = factory.register_narrative_handlers
        def capture(registrar, deps):
            captured.append(deps)
            register(registrar, deps)
        def forbidden(*args, **kwargs):
            pytest.fail("compute factory must not create external model or budget caller")
        monkeypatch.setattr(factory, "register_narrative_handlers", capture)
        monkeypatch.setattr(factory, "NarrativeHTTPModel", forbidden)
        monkeypatch.setattr(factory, "BudgetedNarrativeCaller", forbidden)
        if invalid_component is not None:
            with pytest.raises(ValueError, match="NARRATIVE_RUN_EXECUTION_MISMATCH"):
                factory.create_runtime(spec)
            assert captured == []
        else:
            runtime = factory.create_runtime(spec)
            assert runtime.model_client is None
            assert len(captured) == 1
            try:
                assert captured[0].generation_sha256(subject) == GENERATION
                view = open_verified_projection(captured[0].projection_catalog,
                    projection_id=subject.item_key, expected_projection_sha256=subject.subject_sha256)
                assert view.subject == subject
            finally:
                captured[0].projection_catalog.close()


def test_native_whitespace_and_source_nfc_display_pass_actual_transport_replay(tmp_path):
    with owned_catalog(tmp_path) as (catalog, _root):
        page = flat_page(1)
        page["result"]["page_count"] = 1
        page["result"]["item_total"] = 1
        page["result"]["items"][0]["a"] = "\t  " + ANSWER + " Our cafe\u0301 product is expanding.\r\n"
        page["result"]["items"][0]["q"] = "\n" + QUESTION + "  "
        ref, raw = import_page(catalog, page)
        projection = persist(catalog, [ref])
        dependencies = dependencies_for(catalog, projection)
        selected = dependencies["source.narrative_select"].result["evidence_spans"]
        assert any(span["raw_text"].startswith("\t  ") for span in selected)
        result = verifier(catalog)(verification_context(projection, dependencies))
        assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
        assert result.result["replay"]["locator_count"] == len(selected)
        assert result.result["evidence_spans"] == dependencies["source.narrative_select"].result["evidence_spans"]
        assert SourceVersionReader(catalog).open_version(ref).data == raw


@pytest.mark.parametrize("effort", [None, "low", "high", "max", "medium", True, 1])
def test_configured_reasoning_effort_reaches_real_model_factory_without_overrides(tmp_path, monkeypatch, effort):
    from company_wiki.automation import narrative_worker_factory as factory
    with owned_catalog(tmp_path) as (_catalog, root):
        run = SimpleNamespace(job_ids=("owned-model-job",), input_hash="3" * 64, model_id="configured-fixture-model",
            prompt_version=NARRATIVE_PROMPT_VERSION, blocked=False, binding_json=None)
        monkeypatch.setattr(factory, "NarrativeRunStore", lambda _path: SimpleNamespace(get_run=lambda _id: run))
        monkeypatch.setenv("OWNED_REASONING_FIXTURE_KEY", "synthetic-not-a-live-credential")
        config = root / "reasoning-catalog.json"
        config.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": "catalog", "roots": [{
            "root_id": "company_raw", "path": "companies", "kind": "company_raw",
            "adapter_id": "company_raw_v1", "read_only": True, "reusable_for_filing": True}]}), encoding="utf-8")
        options = {"project_root": str(root), "catalog_config_path": str(config), "run_id": "owned-model-run",
            "expected_run_input_hash": run.input_hash, "model": {"model_id": run.model_id,
            "endpoint": "https://fixture.invalid/v1/chat/completions", "api_key_env": "OWNED_REASONING_FIXTURE_KEY",
            "reasoning_effort": effort}}
        spec = WorkerProcessSpec(worker_id="owned-model-factory", role="model", db_path=str(root / "unused.db"),
            log_dir=str(root / "logs"), runtime_factory_path="company_wiki.automation.narrative_worker_factory:create_runtime",
            runtime_options_json=canonical_json(options), allowed_job_types=("source.narrative_summarize",),
            lease_seconds=30, heartbeat_interval_seconds=5, idle_sleep_seconds=0.05, child_log_max_bytes=4096,
            allowed_job_ids=run.job_ids)
        parsed_options, parsed_model = factory._options(spec)
        assert parsed_options["model"] == options["model"]
        assert parsed_model["reasoning_effort"] == effort
        captured_catalogs = []
        real_catalog = factory.SourceCatalog
        def capture_catalog(configuration):
            catalog = real_catalog(configuration)
            captured_catalogs.append(catalog)
            return catalog
        monkeypatch.setattr(factory, "SourceCatalog", capture_catalog)
        try:
            if effort in (None, "low", "high", "max"):
                runtime = factory.create_runtime(spec)
                assert isinstance(runtime.model_client, factory.NarrativeHTTPModel)
                assert runtime.model_client.reasoning_effort == effort
                assert runtime.model_client.model_id == run.model_id
            else:
                with pytest.raises(ValueError, match="NARRATIVE_MODEL_CONFIG_INVALID"):
                    factory.create_runtime(spec)
        finally:
            for catalog in captured_catalogs:
                catalog.close()
