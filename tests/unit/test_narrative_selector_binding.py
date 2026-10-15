"""Frozen selector execution, diagnostics and replay without provider calls."""
from __future__ import annotations

from dataclasses import replace
from functools import partial
import hashlib
import json
from types import SimpleNamespace

import pytest

from company_wiki.automation.models import HandlerOutcome, canonical_json, canonical_json_hash
from company_wiki.automation.narrative_contracts import NarrativeBundle, NarrativeSelectResult
from company_wiki.automation.narrative_runtime import NarrativeRuntimeDependencies, register_narrative_handlers
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from company_wiki.automation import narrative_worker_factory as factory
from company_wiki.automation.narrative_batch import _freeze_generations
from company_wiki.automation.narrative_model import ModelResponseError
from company_wiki.automation.worker_process import WorkerProcessSpec
from company_wiki.source_catalog import narrative_evidence as policy
from company_wiki.source_catalog.narrative_retrieval import NarrativeEvidenceResolver, NarrativeEvidenceResolveError
from company_wiki.source_contract import source_id_for_sha256
from company_wiki.source_catalog.transcript_text_extract import extract_transcript_material
from unit import test_narrative_select_handler as raw_fixture
from unit import test_narrative_verify_handler as verify_fixture
from unit.test_narrative_business_recall import FIXTURE, FIXTURE_SHA, LEGACY_SHA, package_fingerprint
from integration import test_official_json_verify_handler as official


def parsed_fixture():
    data = FIXTURE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == FIXTURE_SHA
    return policy.parse_transcript_text(data.decode(), source_id=source_id_for_sha256(FIXTURE_SHA),
        source_sha256=FIXTURE_SHA, language="en", parser_version="0.3.1")


def raw_selection(version, *, selector=None):
    data = FIXTURE.read_bytes()
    payload = raw_fixture._payload(data, title=FIXTURE.name,
        document_kind="earnings_call_transcript", language="en", mime_type="text/plain")
    handler = NarrativeSelectHandler(reader=raw_fixture.FakeReader(payload, data),
        selector=selector, selector_version=version)
    result = handler(raw_fixture._context(payload, lambda: None))
    assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
    return data, NarrativeSelectResult.from_dict(result.result)


def management_summary(selected):
    management = next(span for span in selected.evidence_spans
        if span.structured_value.get("source_role") == "management")
    ordered = replace(selected, evidence_spans=(management,) + tuple(
        span for span in selected.evidence_spans if span.span_id != management.span_id))
    summary = verify_fixture._summary(ordered)
    summary.validate_against(selected)
    return summary


@pytest.mark.parametrize("version", ["0.6.0", "0.7.0", "0.7.1"])
def test_raw_frozen_policy_executes_actual_spans_and_verifies_under_default_drift(monkeypatch, version):
    monkeypatch.setattr(policy, "NARRATIVE_SELECTOR_VERSION", "0.7.0")
    data, selected = raw_selection(version)
    material = extract_transcript_material(data, mime_type="text/plain")
    material.verify(data)
    parsed = policy.parse_transcript_text(material.text_utf8, source_id=selected.source_ref.source_id,
        source_sha256=selected.source_ref.content_sha256, language="en", parser_version=selected.parser.version)
    expected = policy.select_narrative_evidence(parsed, title=FIXTURE.name,
        existing_kind="earnings_call_transcript", selector_version=version)
    assert [span.to_dict() for span in selected.evidence_spans] == [span.to_dict() for span in expected.evidence_spans]
    assert selected.selector.version == version
    assert ("90% of the tasks" in "\n".join(span.raw_text or "" for span in selected.evidence_spans)) is (version in {"0.7.0", "0.7.1"})
    if version == "0.6.0":
        full = policy.select_narrative_evidence(parsed_fixture(), title=FIXTURE.name,
            existing_kind="investor_call_transcript", selector_version=version)
        assert package_fingerprint(full) == LEGACY_SHA
    summary = management_summary(selected)
    verified = NarrativeVerifyHandler(reader=verify_fixture.FakeReader(selected, data), selector_version=version)(
        verify_fixture._context(selected, summary))
    assert verified.outcome is HandlerOutcome.SUCCEEDED, verified.error
    assert verified.result["versions"]["selector"] == version
    assert NarrativeBundle.from_dict(verified.result).to_dict()["evidence_spans"] == [span.to_dict() for span in expected.evidence_spans]
    mismatched = NarrativeVerifyHandler(reader=verify_fixture.FakeReader(selected, data),
        selector_version="0.7.0" if version == "0.6.0" else "0.6.0")(
        verify_fixture._context(selected, summary))
    assert mismatched.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert mismatched.error.code == "DEPENDENCY_INVALID"


@pytest.mark.parametrize("version", ["0.6.0", "0.7.0", "0.7.1"])
def test_runtime_registers_select_and_verify_with_same_effective_version(version):
    handlers = {}
    class Registrar:
        def register(self, job_type, handler):
            handlers[job_type] = handler
    data, selected = raw_selection(version)
    register_narrative_handlers(Registrar(), NarrativeRuntimeDependencies(
        reader=verify_fixture.FakeReader(selected, data), model=None, selector_version=version))
    actual = handlers["source.narrative_select"](raw_fixture._context(verify_fixture._payload(selected), lambda: None))
    assert actual.result["selector"]["version"] == version
    actual_selected = NarrativeSelectResult.from_dict(actual.result)
    verified = handlers["source.narrative_verify"](verify_fixture._context(actual_selected, management_summary(actual_selected)))
    assert verified.outcome is HandlerOutcome.SUCCEEDED, verified.error
    assert verified.result["versions"]["selector"] == version


def test_custom_legacy_shape_explicit_pin_and_version_aware_partial_are_real(monkeypatch):
    monkeypatch.setattr(policy, "NARRATIVE_SELECTOR_VERSION", "0.7.0")
    calls = []
    def legacy(parsed, *, title, existing_kind="unknown"):
        calls.append(existing_kind)
        return policy.select_narrative_evidence(parsed, title=title, existing_kind=existing_kind, selector_version="0.6.0")
    _, legacy_result = raw_selection("0.6.0", selector=legacy)
    _, aware_result = raw_selection("0.7.0", selector=partial(policy.select_narrative_evidence, selector_version="0.7.0"))
    assert calls == ["earnings_call_transcript"]
    assert legacy_result.selector.version == "0.6.0" and aware_result.selector.version == "0.7.0"
    assert legacy_result.evidence_spans != aware_result.evidence_spans


def test_custom_missing_declaration_conflict_and_internal_typeerror_do_not_retry():
    from company_wiki.automation.narrative_selector_binding import bind_narrative_selector
    calls = []
    def broken(parsed, *, title, existing_kind="unknown"):
        calls.append(title)
        raise TypeError("internal custom failure")
    with pytest.raises(policy.NarrativeSelectorVersionError, match="CUSTOM_SELECTOR_VERSION_REQUIRED"):
        bind_narrative_selector(broken)
    bound = bind_narrative_selector(broken, selector_version="0.6.0")
    with pytest.raises(policy.NarrativeSelectorVersionError, match="SELECTOR_VERSION_CONFLICT"):
        bind_narrative_selector(bound, selector_version="0.7.0")
    with pytest.raises(TypeError, match="internal custom failure"):
        raw_selection("0.6.0", selector=bound)
    assert calls == [FIXTURE.name]


@pytest.mark.parametrize("version", ["0.6.0", "0.7.0", "0.7.1"])
def test_real_transcript_resolver_uses_recorded_version_full_ordered_rows(tmp_path, monkeypatch, version):
    parsed = parsed_fixture()
    package = policy.select_narrative_evidence(parsed, title=FIXTURE.name,
        existing_kind="investor_call_transcript", selector_version=version)
    raw = tmp_path / "actual-call.txt"
    raw.write_bytes(FIXTURE.read_bytes())
    record = {"title": FIXTURE.name, "selection_status": package.status,
        "coverage_complete": package.coverage_complete, "summary_input": package.summary_input(),
        "replay_contract": {"schema_version": "narrative-evidence-replay/0.1.0",
            "source_format": "transcript_txt", "language": "en", "existing_kind": "investor_call_transcript",
            "parser_name": policy.NARRATIVE_PARSER_NAME, "parser_version": "0.3.1",
            "parser_options": {}, "selector_name": policy.NARRATIVE_SELECTOR_NAME,
            "selector_version": version, "max_selected": package.selection_limit}}
    monkeypatch.setattr(policy, "NARRATIVE_SELECTOR_VERSION", "0.7.0")
    replay = NarrativeEvidenceResolver._replay_record(record, raw_path=raw,
        source_id=parsed.source_id, source_sha256=FIXTURE_SHA)
    assert list(replay.values()) == record["summary_input"]["evidence"]
    assert raw.read_bytes() == FIXTURE.read_bytes()
    record["replay_contract"]["selector_version"] = "unknown-policy"
    with pytest.raises(NarrativeEvidenceResolveError, match="unsupported narrative selector version"):
        NarrativeEvidenceResolver._replay_record(record, raw_path=raw, source_id=parsed.source_id, source_sha256=FIXTURE_SHA)


@pytest.mark.parametrize("version", ["0.6.0", "0.7.0", "0.7.1", "unsupported", None])
def test_factory_decodes_frozen_binding_once_and_pins_before_model(tmp_path, monkeypatch, version):
    with official.owned_catalog(tmp_path) as (catalog, root):
        ref, _ = official.import_page(catalog, official.flat_page(1))
        projection = official.persist(catalog, [ref])
        subject = official.NarrativeSubject.from_projection(projection)
        versions = {"projection_prompt": official.PROJECTION_NARRATIVE_PROMPT_VERSION,
            "projection_model_request_schema": official.PROJECTION_MODEL_REQUEST_SCHEMA,
            "official_json_adapter": official.NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION}
        if version is not None:
            versions["selector"] = version
        binding = {"schema_version": "narrative-run-binding/4", "execution_versions": versions,
            "generation_manifests": {subject.item_key: {"generation_sha256": official.GENERATION,
                "source_inputs": {"subject_binding": subject.to_dict()}}}}
        frozen_json = canonical_json(binding)
        run = SimpleNamespace(job_ids=("owned-job",), input_hash="2"*64, model_id="fixture-model",
            prompt_version=official.NARRATIVE_PROMPT_VERSION, blocked=False, binding_json=frozen_json)
        monkeypatch.setattr(factory, "NarrativeRunStore", lambda _path: SimpleNamespace(get_run=lambda _id: run))
        config = root / "factory.json"
        config.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": "catalog", "roots": [{
            "root_id": "company_raw", "path": "companies", "kind": "company_raw", "adapter_id": "company_raw_v1",
            "read_only": True, "reusable_for_filing": True}]}), encoding="utf-8")
        options = {"project_root": str(root), "catalog_config_path": str(config), "run_id": "owned-run",
            "expected_run_input_hash": run.input_hash, "model": {"model_id": run.model_id,
            "endpoint": "https://fixture.invalid/v1/chat/completions", "api_key_env": "UNREAD_KEY"}}
        spec = WorkerProcessSpec(worker_id="owned-child", role="compute" if version in {"0.6.0", "0.7.0", "0.7.1"} else "mixed",
            db_path=str(root/"unused.db"),
            log_dir=str(root/"logs"), runtime_factory_path="company_wiki.automation.narrative_worker_factory:create_runtime",
            runtime_options_json=canonical_json(options), allowed_job_types=("source.narrative_select", "source.narrative_verify"),
            lease_seconds=30, heartbeat_interval_seconds=5, idle_sleep_seconds=0.05,
            child_log_max_bytes=4096, allowed_job_ids=run.job_ids)
        captured, decoded = [], []
        register = factory.register_narrative_handlers
        loads = factory.json.loads
        def decode(value, *args, **kwargs):
            if value == frozen_json:
                decoded.append(value)
            return loads(value, *args, **kwargs)
        def capture(registrar, deps):
            captured.append(deps)
            register(registrar, deps)
        def forbidden(*args, **kwargs):
            pytest.fail("no external model or budget construction")
        monkeypatch.setattr(factory.json, "loads", decode)
        monkeypatch.setattr(factory, "register_narrative_handlers", capture)
        monkeypatch.setattr(factory, "NarrativeHTTPModel", forbidden)
        monkeypatch.setattr(factory, "BudgetedNarrativeCaller", forbidden)
        monkeypatch.setattr(policy, "NARRATIVE_SELECTOR_VERSION", "0.7.0")
        if version in {"0.6.0", "0.7.0", "0.7.1"}:
            factory.create_runtime(spec)
            try:
                assert captured[0].selector_version == version
                assert captured[0].generation_sha256(subject) == official.GENERATION
            finally:
                captured[0].projection_catalog.close()
        else:
            with pytest.raises(policy.NarrativeSelectorVersionError):
                factory.create_runtime(spec)
            assert captured == []
        assert len(decoded) == 1


@pytest.mark.parametrize("projection,role,error", [
    ("missing", "compute", None),
    ("reading-model-input/1", "compute", None),
    ("reading-model-input/1", "mixed", None),
    ("reading-model-input/1", "model", "NARRATIVE_RUN_MODEL_CONFIG_MISMATCH"),
    ("unavailable/99", "mixed", "READING_MODEL_PROJECTION_UNAVAILABLE"),
    (None, "mixed", "READING_MODEL_PROJECTION_UNAVAILABLE"),
    (False, "mixed", "READING_MODEL_PROJECTION_UNAVAILABLE"),
])
def test_factory_new_reading_binding_is_decoded_once_for_every_role_and_rejection(
    tmp_path, monkeypatch, projection, role, error,
):
    """Actual constructed HTTP options and before-model rejection share one parse."""
    with official.owned_catalog(tmp_path) as (catalog, root):
        original = root / "existing-original.txt"
        original.write_bytes(b"keep original fixture")
        ref, _ = official.import_page(catalog, official.flat_page(1))
        projected = official.persist(catalog, [ref])
        subject = official.NarrativeSubject.from_projection(projected)
        model_options = {"model_id": "fixture-model", "endpoint": "https://fixture.invalid/v1/chat/completions",
                         "api_key_env": "UNREAD_KEY", "max_output_tokens": 1024}
        manifest = {"schema_version": "narrative-generation/2", "subject_binding": subject.to_dict(),
                    "source_adapter": "official-json-fixture", "language": "en", "parser_component": {},
                    "model": {key: value for key, value in model_options.items() if key != "api_key_env"}}
        manifest["model"]["output_token_field"] = "max_tokens"
        if projection != "missing":
            manifest["reading_model_projection"] = projection
        frozen = {"schema_version": "narrative-run-binding/4", "execution_versions": {
            "selector": "0.9.0", "projection_prompt": official.PROJECTION_NARRATIVE_PROMPT_VERSION,
            "projection_model_request_schema": official.PROJECTION_MODEL_REQUEST_SCHEMA,
            "official_json_adapter": official.NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION},
            **_freeze_generations({subject.item_key: manifest})}
        frozen_json = canonical_json(frozen)
        run = SimpleNamespace(job_ids=("owned-job",), input_hash="2" * 64, model_id="fixture-model",
                              prompt_version=official.NARRATIVE_PROMPT_VERSION, blocked=False, binding_json=frozen_json)
        monkeypatch.setattr(factory, "NarrativeRunStore", lambda _path: SimpleNamespace(
            get_run=lambda _id: run, final_generations=lambda _id: {subject.item_key: manifest}))
        config = root / "factory.json"
        config.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": "catalog", "roots": [{
            "root_id": "company_raw", "path": "companies", "kind": "company_raw", "adapter_id": "company_raw_v1",
            "read_only": True, "reusable_for_filing": True}]}), encoding="utf-8")
        options = {"project_root": str(root), "catalog_config_path": str(config), "run_id": "owned-run",
                   "expected_run_input_hash": run.input_hash, "model": dict(model_options)}
        if error == "NARRATIVE_RUN_MODEL_CONFIG_MISMATCH":
            options["model"]["max_output_tokens"] = 1025
        jobs = ("source.narrative_summarize",) if role == "model" else (
            ("source.narrative_select", "source.narrative_verify") if role == "compute" else
            ("source.narrative_select", "source.narrative_summarize", "source.narrative_verify"))
        spec = WorkerProcessSpec(worker_id="owned-child", role=role, db_path=str(root / "unused.db"),
            log_dir=str(root / "logs"), runtime_factory_path="company_wiki.automation.narrative_worker_factory:create_runtime",
            runtime_options_json=canonical_json(options), allowed_job_types=jobs,
            lease_seconds=30, heartbeat_interval_seconds=5, idle_sleep_seconds=0.05,
            child_log_max_bytes=4096, allowed_job_ids=run.job_ids)
        decoded, captured, models, callers = [], [], [], []
        loads, register, http_model = factory.json.loads, factory.register_narrative_handlers, factory.NarrativeHTTPModel
        def decode(value, *args, **kwargs):
            if value == frozen_json:
                decoded.append(value)
            return loads(value, *args, **kwargs)
        def capture(registrar, deps):
            captured.append(deps)
            register(registrar, deps)
        def construct(**kwargs):
            model = http_model(**kwargs)
            models.append(model)
            return model
        def caller(**kwargs):
            callers.append(kwargs)
            return SimpleNamespace()
        monkeypatch.setattr(factory.json, "loads", decode)
        monkeypatch.setattr(factory, "register_narrative_handlers", capture)
        monkeypatch.setattr(factory, "NarrativeHTTPModel", construct)
        monkeypatch.setattr(factory, "BudgetedNarrativeCaller", caller)
        monkeypatch.setenv("UNREAD_KEY", "synthetic-no-live-credential")
        try:
            if projection == "unavailable/99":
                # Construction may restore an already completed canonical
                # summary. Only a pending model execution needs its decoder.
                factory.create_runtime(spec)
                deps = captured[0]
                try:
                    assert deps.reading_model_projection(subject) == projection
                    assert deps.validate_model_execution is not None
                    with pytest.raises(ModelResponseError, match=error):
                        deps.validate_model_execution(subject)
                    assert len(models) == len(callers) == 1
                finally:
                    deps.projection_catalog.close()
            elif error is not None:
                kind = ModelResponseError if error == "READING_MODEL_PROJECTION_UNAVAILABLE" else ValueError
                with pytest.raises(kind, match=error):
                    factory.create_runtime(spec)
                assert not captured and not callers
                assert len(models) == (1 if error == "NARRATIVE_RUN_MODEL_CONFIG_MISMATCH" else 0)
            else:
                factory.create_runtime(spec)
                deps = captured[0]
                assert deps.selector_version == "0.9.0"
                assert deps.reading_model_projection(subject) == (None if projection == "missing" else projection)
                assert deps.generation_sha256(subject) == canonical_json_hash(manifest)
                assert len(models) == len(callers) == (0 if role == "compute" else 1)
                if role != "compute":
                    assert callers[0]["model"] is models[0] is deps.model
                deps.projection_catalog.close()
            assert len(decoded) == 1
        finally:
            assert original.read_bytes() == b"keep original fixture"


def test_worker_binding_snapshot_is_immutable_without_redecoding(monkeypatch):
    frozen_json = canonical_json({"execution_versions": {"selector": "0.8.0"},
        "generation_manifests": {"old": {"generation_sha256": "1" * 64,
            "model": {"model_id": "frozen", "endpoint": "https://fixture.invalid"}}}})
    loads = factory.json.loads
    decoded = []
    def decode(value, *args, **kwargs):
        if value == frozen_json:
            decoded.append(value)
        return loads(value, *args, **kwargs)
    monkeypatch.setattr(factory.json, "loads", decode)
    snapshot = factory._worker_binding_snapshot(frozen_json)
    assert snapshot.selector_version == "0.8.0"
    assert snapshot.generation_values["old"] == "1" * 64
    assert snapshot.reading_projections == {}
    assert snapshot.frozen_models[0]["model_id"] == "frozen"
    with pytest.raises(TypeError):
        snapshot.generation_values["old"] = "2" * 64
    with pytest.raises(TypeError):
        snapshot.reading_projections["old"] = "reading-model-input/1"
    with pytest.raises(TypeError):
        snapshot.frozen_models[0]["model_id"] = "changed"
    assert len(decoded) == 1
