"""Completed publications retain historical identity; execution still needs its recipe."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.models import JobStatus, RuntimeState, canonical_json, canonical_json_hash
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_generation import reading_candidate_manifest
from company_wiki.source_catalog.source_read_policy import EXACT_READ_POLICY_FINGERPRINT_SCHEMA_VERSION
from company_wiki.source_catalog.narrative_pdf_reading import PdfReading
from unit.test_narrative_batch import _request


def _manifest():
    recipe = PdfReading().describe_recipe()
    return {
        "schema_version": "narrative-generation/1",
        "source_ref": {"mime_type": "application/pdf"},
        "source_metadata": {"source_class": "filing"},
        "parser_component": {"name": recipe["parser_name"], "version": recipe["parser_version"]},
        "parser_components": recipe,
    }


def _publication(manifest):
    return SimpleNamespace(metadata_json=canonical_json({
        "generation_manifest": manifest,
        "generation_sha256": canonical_json_hash(manifest),
    }))


@pytest.mark.parametrize("field", ["parser_version", "reader_recipe", "runtime", "reader_implementation_sha256", "paragraph_enhancement"])
def test_completed_generation_matches_whole_published_recipe_without_current_sdk(field):
    manifest = _manifest()
    published = _publication(manifest)
    changed = deepcopy(manifest)
    changed["parser_components"][field] = "different"
    batch._validate_published_generation(manifest, published)
    with pytest.raises(batch.BatchResumeError, match="BATCH_FROZEN_BINDING_INVALID"):
        batch._validate_published_generation(changed, published)


def test_completed_generation_rejects_invalid_publication_digest():
    manifest = _manifest()
    published = SimpleNamespace(metadata_json=canonical_json({
        "generation_manifest": manifest, "generation_sha256": "0" * 64,
    }))
    with pytest.raises(batch.BatchResumeError, match="BATCH_FROZEN_BINDING_INVALID"):
        batch._validate_published_generation(manifest, published)


def test_completed_generation_requires_publication_proof_for_recipe():
    with pytest.raises(batch.BatchResumeError, match="BATCH_FROZEN_BINDING_INVALID"):
        batch._validate_published_generation(_manifest(), SimpleNamespace(metadata_json="{}"))


def test_completed_generation_cannot_remove_recipe_and_resign_as_legacy():
    original = _manifest()
    changed = {key: value for key, value in original.items() if key != "parser_components"}
    with pytest.raises(batch.BatchResumeError, match="BATCH_FROZEN_BINDING_INVALID"):
        batch._validate_published_generation(changed, _publication(original))


def test_genuine_pre_generation_history_keeps_legacy_read_contract():
    original = {key: value for key, value in _manifest().items() if key != "parser_components"}
    batch._validate_published_generation(original, SimpleNamespace(metadata_json="{}"))


def test_pinned_base_generation_resolves_final_selection_and_keeps_exact_recipe():
    base = {**_manifest(), "execution_versions": {"selector": "0.9.0"}}
    final = {**base, "selection_generation": {
        "schema_version": "narrative-selection-generation/1",
        "select_result_sha256": "a" * 64, "evidence_sha256": "b" * 64,
        "material_sha256": "c" * 64, "reading_policy_version": "du-sent-policy/1+" + "d" * 64,
    }}
    published = _publication(final)
    batch._validate_published_generation(base, published)
    changed = deepcopy(base)
    changed["parser_components"]["runtime"] = {"pymupdf": "different"}
    with pytest.raises(batch.BatchResumeError, match="BATCH_FROZEN_BINDING_INVALID"):
        batch._validate_published_generation(changed, published)


@pytest.mark.parametrize("metadata", ["[]", "null", "invalid json"])
def test_completed_generation_rejects_malformed_publication_metadata(metadata):
    with pytest.raises(batch.BatchResumeError, match="BATCH_FROZEN_BINDING_INVALID"):
        batch._validate_published_generation(_manifest(), SimpleNamespace(metadata_json=metadata))


@pytest.mark.parametrize("metadata", ["[]", "null", "true", "0", '"text"'])
def test_base_selection_rejects_non_object_metadata_through_owner_and_batch(metadata):
    base = {**_manifest(), "execution_versions": {"selector": "0.9.0"}}
    publication = SimpleNamespace(metadata_json=metadata)
    with pytest.raises(ValueError, match="BATCH_REUSE_MANIFEST_INVALID"):
        reading_candidate_manifest(publication, base)
    with pytest.raises(batch.BatchResumeError, match="BATCH_FROZEN_BINDING_INVALID"):
        batch._validate_published_generation(base, publication)


@pytest.mark.parametrize("changed", ["source", "model", "profile", "limit"])
def test_same_run_changed_request_is_refused_before_recipe_or_job_access(changed):
    request = _request()
    frozen = canonical_json({
        "schema_version": "narrative-run-binding/3",
        "read_policy_schema_version": EXACT_READ_POLICY_FINGERPRINT_SCHEMA_VERSION,
        "request_sha256": request.request_sha256,
    })
    wire = request.to_dict()
    if changed == "source":
        wire["sources"][0]["document_id"] = "different-document"
    elif changed == "model":
        wire["model"]["model_id"] = "different-model"
    elif changed == "profile":
        wire["profile"] = "P1"
    else:
        wire["max_tokens"] += 1
    changed_request = NarrativeBatchRequest.from_dict(wire)
    with pytest.raises(batch.BatchResumeError, match="BATCH_REQUEST_CHANGED"):
        batch._resume_binding(changed_request, None, None, None,
            SimpleNamespace(binding_json=frozen), deadline=None)


@pytest.mark.parametrize("schema", ["narrative-batch-request/1", "narrative-batch-request/2"])
def test_binding_decoder_retains_published_recipe_without_instantiating_current_reader(schema, monkeypatch):
    wire = _request().to_dict()
    wire["sources"][0]["mime_type"] = "application/pdf"
    wire["selector_version"] = "0.8.0"
    if schema.endswith("/2"):
        wire["schema_version"] = schema
        wire["items"] = [{"kind": "raw", "source_ref": ref} for ref in wire.pop("sources")]
    request = NarrativeBatchRequest.from_dict(wire)
    ref = request.work_items[0].source_ref
    from company_wiki.source_catalog.source_reader import SourceRef
    reader = SimpleNamespace(
        query_ref=lambda *args: SourceRef(**ref.to_dict()),
        describe_version=lambda ref: {"title": "Fixture PDF", "document_kind": "investor_relations", "language": "en"},
        read_policy_sha256=lambda ref: "b" * 64,
    )
    prepared = batch._current_sources(request, reader)
    events = batch._events_from_sources(request, *prepared, now="2026-10-26T00:00:00Z")
    versions = batch._execution_versions(request)
    manifest = batch._item_generation(request, prepared[0][0], versions=versions)
    binding = batch.BatchEvents(events.input_hash, events.events, events.source_facts, {ref.document_id: manifest})
    event = events.events[0]
    jobs = tuple(SimpleNamespace(
        job_id="job-" + kind, job_type=kind, subject_id=ref.document_id,
        created_from_event_id=event.event_id, input_hash=event.input_hash,
        policy_version=event.policy_version, handler_version=versions["handlers"][kind],
        status=JobStatus.SUCCEEDED,
    ) for kind in batch._NARRATIVE_JOB_TYPES)
    frozen = batch._frozen_binding(request, binding, jobs=jobs)
    run = SimpleNamespace(
        binding_json=frozen, run_id=request.run_id, input_hash=binding.input_hash,
        job_ids=tuple(job.job_id for job in jobs),
        scope_sha256=canonical_json_hash(sorted(job.job_id for job in jobs)),
        prompt_version=versions["prompt"], model_id=request.model_options["model_id"],
        pricing_version=request.pricing_version,
        input_micro_usd_per_million_tokens=request.input_micro_usd_per_million_tokens,
        output_micro_usd_per_million_tokens=request.output_micro_usd_per_million_tokens,
        max_tokens=request.max_tokens, max_micro_usd=request.max_micro_usd,
        max_output_bytes=min(request.max_final_bytes, request.max_persistent_bytes),
        created_at="2026-10-26T00:00:00Z",
    )
    store = SimpleNamespace(list_jobs=lambda **kwargs: jobs, get_event=lambda key: event)
    runs = SimpleNamespace(job_bindings=lambda run_id: {
        job.job_id: (job.input_hash, job.handler_version) for job in jobs
    })
    def forbidden_reader(*args, **kwargs):
        raise AssertionError("binding decode must not instantiate current PDF software")
    monkeypatch.setattr(PdfReading, "describe_recipe", forbidden_reader)
    restored, restored_versions, restored_jobs = batch._resume_binding(
        request, reader, store, runs, run, deadline=None, prepared_sources=prepared)
    assert restored.generation_manifests == binding.generation_manifests
    assert restored_versions == versions and restored_jobs == jobs
    assert run.binding_json == frozen


def _resume_harness(tmp_path, monkeypatch, *, status, completed):
    request = _request()
    manifest = _manifest()
    # A genuine saved producer can differ in any software detail after install.
    # No historical SDK callback or compatibility table is needed for a final read.
    manifest["parser_components"]["runtime"] = {"pymupdf": "retired-runtime"}
    binding = batch.BatchEvents("a" * 64, (), generation_manifests={"doc-a": manifest})
    run = SimpleNamespace(run_id=request.run_id, job_ids=("job-a",), blocked=False)
    gate = SimpleNamespace(desired_state=RuntimeState.PAUSED)
    store = SimpleNamespace(read_runtime_gate=lambda: gate)
    runs = SimpleNamespace(get_run=lambda _run_id: run)
    jobs = (SimpleNamespace(status=status, last_error_code=None),)
    db = tmp_path / "auto.db"
    db.touch()
    monkeypatch.setattr(batch, "SourceVersionReader", lambda catalog: object())
    monkeypatch.setattr(batch, "AutomationStore", lambda path: store)
    monkeypatch.setattr(batch, "NarrativeRunStore", lambda path: runs)
    monkeypatch.setattr(batch, "_resume_binding", lambda *args, **kwargs: (binding, batch._execution_versions(request), jobs))
    monkeypatch.setattr(batch, "_storage_guard", lambda *args, **kwargs: object())
    monkeypatch.setattr(batch, "_paid_summary_recovery_candidates", lambda *args: ())
    artifacts = SimpleNamespace(close=lambda: None)
    monkeypatch.setattr(batch, "NarrativeArtifactReader", lambda *args: artifacts)
    monkeypatch.setattr(batch, "LocalNarrativeObjectStore", lambda path: object())
    monkeypatch.setattr(batch, "_final_documents", lambda *args, **kwargs: [
        {"status": "completed" if completed else "activation_pending"},
    ])
    monkeypatch.setattr(batch, "_receipt", lambda *args: "read-only receipt")
    catalog = SimpleNamespace(config=SimpleNamespace(database_path=tmp_path / "catalog.db", catalog_dir=tmp_path))
    return lambda: batch._run_prepared(request, catalog, tmp_path, tmp_path / "config.json", db, tmp_path / "work",
        deadline=None, prepared_sources=((), ()), manifests={}, normalization=None,
        effective_versions=batch._execution_versions(request))


def test_completed_restore_does_not_require_current_recipe(tmp_path, monkeypatch):
    restore = _resume_harness(tmp_path, monkeypatch, status=JobStatus.SUCCEEDED, completed=True)
    assert restore() == "read-only receipt"


@pytest.mark.parametrize("status,completed", [(JobStatus.READY, False), (JobStatus.SUCCEEDED, False)])
def test_unfinished_or_unactivated_restore_rejects_recipe_drift_before_execution(tmp_path, monkeypatch, status, completed):
    restore = _resume_harness(tmp_path, monkeypatch, status=status, completed=completed)
    with pytest.raises(batch.BatchResumeError, match="BATCH_FROZEN_BINDING_INVALID"):
        restore()


@pytest.mark.parametrize("field,value", [("parser_version", "99.0.0"), ("runtime", {"pymupdf": "retired"}), ("reader_recipe", "unknown/9")])
def test_new_generation_keeps_strict_recipe_contract(field, value):
    manifest = _manifest()
    manifest["parser_components"][field] = value
    with pytest.raises(batch.BatchResumeError, match="BATCH_FROZEN_BINDING_INVALID"):
        batch._validate_normalization_binding({"doc-a": manifest}, None)
