"""Causal cache prechecks; injected dependency comparators are explicit stubs.

These tests do not certify the external dependency canonicalizer. Production
worker/public transport coverage lives in test_shared_reading_production_e2e.
"""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from company_wiki.automation import narrative_generation as generation
from company_wiki.automation.models import canonical_json, canonical_json_hash
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model import NARRATIVE_PROMPT_VERSION, NarrativeModelResponse
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from company_wiki.automation.narrative_selection_generation import reading_material_sha256
from company_wiki.document_understanding import decision_inventory as inventory
from company_wiki.document_understanding.profiles import registry
from unit.test_narrative_reading_generation_store import _selected


PORT = "company_wiki.document_understanding.decision_dependencies"


def _trace():
    return inventory.build_decision_trace({
        "source_ref": {"source_id": "urn:company-wiki:source:sha256:" + "a" * 64},
        "route": {"regime": "cn_exchange", "family": "offering"},
        "observation": {"metadata": {"form_type": "unknown", "mime_type": "text/plain"}},
        "reading_plan": {"used_profiles": [{"profile_id": "offering"}]},
    })


def _stub_freeze(trace, *, status=None):
    """Test-only fixture shape; never substitutes the external production lane."""
    value = {key: deepcopy(trace[key]) for key in ("scopes", "components", "candidates", "versions")}
    value.update(schema_version="du-decision-dependencies/1",
                 status=status or ("complete" if trace["inventory_complete"] else "partial"),
                 decision_digest=canonical_json_hash(value), diagnostics=[])
    return value


def _stub_port(monkeypatch, *, compare=None):
    def stub_compare(frozen, current):
        if not current.get("inventory_complete"):
            return {"status": "unavailable"}
        return {"status": "same" if _stub_freeze(current)["decision_digest"] == frozen["decision_digest"] else "changed"}
    port = SimpleNamespace(compare_decision_dependencies=compare or stub_compare)
    original = generation.import_module
    monkeypatch.setattr(generation, "import_module", lambda name: port if name == PORT else original(name))
    return port


def _base():
    selected = _selected().to_dict()["result"]
    return {"schema_version": "narrative-generation/1", "source_ref": selected["source_ref"],
            "source_metadata": selected["source_metadata"], "parser_component": selected["parser"],
            "execution_versions": {"selector": "0.9.0"}}


def _final(*, dependencies=True):
    selected = _selected().to_dict()["result"]
    final = {**_base(), "selection_generation": {
        "schema_version": "narrative-selection-generation/1",
        "select_result_sha256": canonical_json_hash(selected),
        "reading_policy_version": selected["reading_context"]["reading_policy_version"],
        "evidence_sha256": canonical_json_hash(selected["evidence_spans"]),
        "material_sha256": reading_material_sha256(NarrativeSelectResult.from_dict(selected)),
    }}
    if dependencies:
        final["reading_dependencies"] = _stub_freeze(_trace())
        final["selection_generation"]["decision_digest"] = final["reading_dependencies"]["decision_digest"]
    return final


def _version(final):
    return SimpleNamespace(
        metadata_json=canonical_json({"generation_manifest": final,
                                      "generation_sha256": generation.generation_sha256(final),
                                      "base_generation_sha256": generation.generation_sha256(_base())}),
        artifact_version_id="narrative-fixture", content_sha256="f" * 64, byte_size=1200,
        document_id=_base()["source_ref"]["document_id"], source_id=_base()["source_ref"]["source_id"],
        source_sha256=_base()["source_ref"]["content_sha256"],
    )


@pytest.mark.parametrize("state", ["missing", "partial", "complete-module-missing"])
def test_unavailable_decision_trace_is_a_miss_without_original_or_model_io(monkeypatch, state):
    final = _final(dependencies=state != "missing")
    if state == "partial":
        final["reading_dependencies"]["status"] = "partial"
        final["reading_dependencies"]["decision_digest"] = None
        final["selection_generation"].pop("decision_digest")
    def missing(name):
        raise ModuleNotFoundError("external dependency lane absent", name=PORT)
    monkeypatch.setattr(generation, "import_module", missing)
    class Artifacts:
        def visible_base_generation_candidates(self, **kwargs):
            return (_version(final),)
    def forbidden(*args, **kwargs):
        pytest.fail("cache precheck must not read originals or call a model when dependencies are unavailable")
    monkeypatch.setattr(generation, "read_reuse_pin", forbidden)
    payload = SimpleNamespace(subject=SimpleNamespace(kind="raw"))
    assert generation.find_reuse_pin(Artifacts(), None, payload, _base(), {}) is None


@pytest.mark.parametrize("digest", [None, "", "short", "g" * 64])
def test_complete_dependency_requires_real_full_digest_before_compare(monkeypatch, digest):
    final = _final()
    final["reading_dependencies"]["decision_digest"] = digest
    final["selection_generation"]["decision_digest"] = digest
    calls = []
    _stub_port(monkeypatch, compare=lambda *args: calls.append(args) or {"status": "same"})
    with pytest.raises(ValueError, match="(?i)digest|manifest|generation|sha256"):
        generation.current_reading_decision_matches(final)
    assert calls == []


def test_missing_digest_on_both_complete_objects_cannot_become_none_equals_none(monkeypatch):
    final = _final()
    final["reading_dependencies"].pop("decision_digest")
    final["selection_generation"].pop("decision_digest")
    _stub_port(monkeypatch, compare=lambda *args: {"status": "same"})
    with pytest.raises(ValueError, match="(?i)digest|manifest|generation|sha256"):
        generation.current_reading_decision_matches(final)


def test_current_partial_inventory_is_never_same_even_with_broken_stub_compare(monkeypatch):
    final = _final()
    calls = []
    _stub_port(monkeypatch, compare=lambda *args: calls.append(args) or {"status": "same"})
    current = inventory.current_decision_trace(final["reading_dependencies"])
    current["inventory_complete"] = False
    monkeypatch.setattr(inventory, "current_decision_trace", lambda frozen: current)
    assert generation.current_reading_decision_matches(final) is False
    assert calls == []


@pytest.mark.parametrize("module", ["generation", "source-selector"])
def test_optional_import_does_not_hide_dependency_internal_module_failure(monkeypatch, module):
    failure = ModuleNotFoundError("lane's own import failed", name="missing_internal_dependency")
    def broken(name):
        raise failure
    if module == "generation":
        _final_value = _final()
        monkeypatch.setattr(generation, "import_module", broken)
        with pytest.raises(ModuleNotFoundError) as error:
            generation.current_reading_decision_matches(_final_value)
    else:
        from company_wiki.source_catalog import narrative_reading
        from company_wiki.source_catalog.narrative_evidence import parse_transcript_text
        text = b"Full Conference Call Transcript\nCEO: We launched a new product and expanded overseas capacity.\n"
        sha = hashlib.sha256(text).hexdigest()
        parsed = parse_transcript_text(text.decode(), source_id="urn:company-wiki:source:sha256:" + sha,
                                       source_sha256=sha, language="en")
        monkeypatch.setattr(narrative_reading, "import_module", broken)
        with pytest.raises(ModuleNotFoundError) as error:
            narrative_reading.select_reading_evidence(parsed, title="Acme earnings call",
                                                     existing_kind="investor_call_transcript")
    assert error.value is failure


def test_current_inventory_tracks_relevant_losing_policy_content_and_eligibility(monkeypatch):
    frozen = _stub_freeze(_trace())
    relevant = [row for row in frozen["candidates"] if "offering_cn_equity" in row["candidate_id"]]
    assert relevant and relevant[0]["eligible"]
    changed = deepcopy(registry._CATALOG)
    loser = next(record for record in changed["families"] if record["id"] == "offering_cn_equity")
    loser["sections"][0]["priority"] += 1
    monkeypatch.setattr(registry, "_CATALOG", changed)
    assert _stub_freeze(inventory.current_decision_trace(frozen))["decision_digest"] != frozen["decision_digest"]
    loser["applies_to"]["regimes"] = ["other"]
    current = inventory.current_decision_trace(frozen)
    row = next(row for row in current["candidates"] if "offering_cn_equity" in row["candidate_id"])
    assert row["eligible"] is False


def test_unrelated_family_instruction_change_does_not_invalidate_source_scope(monkeypatch):
    frozen = _stub_freeze(_trace())
    changed = deepcopy(registry._CATALOG)
    unrelated = next(record for record in changed["families"] if record["id"] == "sec_10k")
    unrelated["sections"][0]["priority"] += 1
    monkeypatch.setattr(registry, "_CATALOG", changed)
    assert _stub_freeze(inventory.current_decision_trace(frozen))["decision_digest"] == frozen["decision_digest"]


def test_inventory_uses_actual_interim_family_instead_of_legacy_periodic_default():
    trace = inventory.build_decision_trace({
        "source_ref": {"source_id": "urn:company-wiki:source:sha256:" + "a" * 64},
        "route": {"regime": "hkex", "family": "interim"},
        "observation": {"metadata": {"form_type": "unknown"}},
        "reading_plan": {"used_profiles": [{"profile_id": "hk_periodic"}], "unit_profiles": {
            "actual-interim-unit": {"profile_id": "hk_periodic", "family": "interim",
                                     "reading_profile_key": None},
        }},
    })
    assert trace["scopes"][0]["family"] == "interim"
    assert any("hk_interim_report" in row["candidate_id"] for row in trace["candidates"])
    assert not any("hk_annual_report" in row["candidate_id"] for row in trace["candidates"])


@pytest.mark.parametrize("mutate", ["missing-selection-hash", "wrong-selection-schema", "missing-evidence-hash", "missing-material-hash", "wrong-final-hash"])
def test_matching_artifact_metadata_corruption_is_an_error_not_spend_permission(mutate):
    final = _final()
    if mutate == "missing-selection-hash":
        final["selection_generation"].pop("select_result_sha256")
    elif mutate == "wrong-selection-schema":
        final["selection_generation"]["schema_version"] = "unknown/1"
    elif mutate == "missing-evidence-hash":
        final["selection_generation"].pop("evidence_sha256")
    elif mutate == "missing-material-hash":
        final["selection_generation"].pop("material_sha256")
    version = _version(final)
    if mutate == "wrong-final-hash":
        metadata = json.loads(version.metadata_json)
        metadata["generation_sha256"] = "e" * 64
        version.metadata_json = canonical_json(metadata)
    with pytest.raises(ValueError, match="(?i)digest|manifest|generation|sha256"):
        generation.reading_candidate_manifest(version, _base())


def _bundle():
    selected = NarrativeSelectResult.from_dict(_selected().to_dict()["result"])
    draft = {"draft": {"source_id": selected.source_ref.source_id,
                       "source_sha256": selected.source_ref.content_sha256, "language": "zh",
                       "claims": [{"claim_id": "one", "text": selected.evidence_spans[0].raw_text,
                                   "evidence_ids": ["e1"], "claim_type": "company_statement", "modality": "actual"}]}}
    response = NarrativeModelResponse("openai-compatible-http/1", "stub-model", NARRATIVE_PROMPT_VERSION,
                                      json.dumps(draft, ensure_ascii=False).encode())
    summary = NarrativeSummarizeHandler._completed_result(selected, selected.prompt_review, response)
    return NarrativeVerifyHandler._bundle(selected, summary, selected.prompt_review)


def test_bundle_generation_recomputes_real_shared_material_and_retains_select_hash_audit():
    bundle = _bundle()
    final = _final(dependencies=False)
    generation.verify_reading_bundle_generation(bundle, final)
    assert final["selection_generation"]["material_sha256"] == reading_material_sha256(bundle)
    select_hash = final["selection_generation"]["select_result_sha256"]
    changed = replace(bundle, source_metadata=replace(bundle.source_metadata, title="Changed actual source title"))
    with pytest.raises(ValueError, match="GENERATION"):
        generation.verify_reading_bundle_generation(changed, final)
    assert final["selection_generation"]["select_result_sha256"] == select_hash
    final["selection_generation"]["material_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="GENERATION"):
        generation.verify_reading_bundle_generation(bundle, final)


def test_same_run_pinned_manifest_is_frozen_without_current_registry_resigning(monkeypatch):
    final = _final()
    class Artifacts:
        def visible_subject_metadata(self, **kwargs):
            return _version(final)
    def forbidden(*args, **kwargs):
        pytest.fail("pinned same-run read must not re-sign with current registry")
    monkeypatch.setattr(generation, "current_reading_decision_matches", forbidden)
    pin = {"artifact_version_id": "narrative-fixture", "content_sha256": "f" * 64, "byte_size": 1200}
    assert generation.pinned_reading_manifest(Artifacts(), SimpleNamespace(subject="bound-subject"), pin, _base()) == final


def test_one_hundred_base_bindings_keep_shared_settings_without_original_or_decision_copies():
    from unit.test_narrative_batch import _request, Reader, _module
    module = _module()
    request = replace(_request(), selector_version="0.9.0")
    request = replace(request, sources=tuple(replace(request.sources[0],
        document_id="urn:company-wiki:document:sha256:" + format(index, "064x")) for index in range(100)))
    binding = module.build_batch_events(request, Reader(), now="2026-10-14T00:00:00Z")
    manifests = {}
    for event in binding.events:
        from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
        payload = SourceRevisionEventPayload.from_dict(json.loads(event.payload_json))
        manifests[event.subject_id] = generation.generation_manifest(request, payload,
            execution_versions=module._execution_versions(request))
    encoded = module._frozen_binding(request, replace(binding, generation_manifests=manifests))
    frozen = json.loads(encoded)
    assert len(encoded.encode()) <= 262144
    assert len(frozen["generation_settings"]) == 1
    assert module._thaw_generations(frozen) == manifests
    assert "raw_text" not in encoded and "evidence_spans" not in encoded and "reading_dependencies" not in encoded


@pytest.mark.parametrize("partial_digest", [None, "a" * 64], ids=["no-digest", "diagnostic-only-digest"])
def test_legitimate_partial_dependencies_do_not_block_final_summary_generation(tmp_path, partial_digest):
    from unit.test_narrative_reading_generation_store import _state, _claim, _finish
    from company_wiki.automation.models import HandlerResult
    auto, runs, jobs, generation_number, selected, _ = _state(tmp_path)
    wire = selected.to_dict()["result"]
    dependencies = _stub_freeze(_trace(), status="partial")
    dependencies["decision_digest"] = partial_digest
    wire["reading_dependencies"] = dependencies
    partial = HandlerResult(selected.outcome, wire, (), (), selected.metrics, None)
    _finish(auto, _claim(auto, jobs[0], generation_number), partial)
    final = runs.final_generation_for_job(jobs[1].job_id)
    assert final["reading_dependencies"] == dependencies
    assert generation.current_reading_decision_matches(final) is False


@pytest.fixture
def published_reuse(tmp_path):
    """Real publication owner; only the original-source read is stubbed below."""
    from company_wiki.automation import narrative_batch as batch
    from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
    from company_wiki.source_catalog.narrative_artifact_store import (
        LocalNarrativeObjectStore, NarrativeArtifactDraft, NarrativeArtifactStore,
    )
    from company_wiki.source_catalog.store import CatalogStore
    from unit.test_narrative_batch import _request

    selected = _selected().to_dict()["result"]
    ref = selected["source_ref"]
    now = "2026-10-14T00:00:00Z"
    catalog = CatalogStore(tmp_path / "catalog.sqlite3")
    with catalog.transaction() as connection:
        connection.execute(
            "INSERT INTO sources (source_id, content_sha256, byte_size, mime_type, first_seen_at) VALUES (?,?,?,?,?)",
            (ref["source_id"], ref["content_sha256"], ref["byte_size"], ref["mime_type"], now),
        )
        connection.execute(
            "INSERT INTO documents (document_id, primary_source_id, title, source_type, document_kind, "
            "source_status, metadata_priority, metadata_json, first_seen_at, last_seen_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (ref["document_id"], ref["source_id"], selected["source_metadata"]["title"], "file",
             selected["source_metadata"]["document_kind"], "active", 10, "{}", now, now),
        )
    objects = LocalNarrativeObjectStore(tmp_path / "objects")
    writer = NarrativeArtifactStore(catalog, objects)
    bundle = _bundle()
    draft = NarrativeArtifactDraft(
        effect_id="fixture-effect", work_key=canonical_json_hash(_base()),
        document_id=ref["document_id"], source_id=ref["source_id"], source_sha256=ref["content_sha256"],
        producer_name="company_wiki.narrative_bundle", producer_version=bundle.versions.bundle_producer,
        policy_sha256=selected["expected_read_policy_sha256"], selection_status=bundle.selection.status,
        quality_status="verified", metadata_json=_version(_final()).metadata_json, created_at=now,
    )
    prepared = writer.prepare(draft, canonical_json(bundle.to_dict()).encode("utf-8"))
    visible = writer.activate(prepared.effect_id, verified_after_hash=prepared.content_sha256, activated_at=now)
    artifacts = writer.for_reading(catalog.database_path, objects)
    payload = SourceRevisionEventPayload.from_dict({
        "schema_version": "source-revision-event/2.0", "source_ref": selected["source_ref"],
        "source_metadata": selected["source_metadata"],
        "expected_read_policy_sha256": selected["expected_read_policy_sha256"],
    })
    key = payload.item_key
    request = _request()
    binding = batch._events_from_sources(request, [payload], ({"document_id": key, "document_kind": "prospectus"},),
                                         now="2026-10-14T00:00:00Z")
    pin = generation.artifact_pin(visible)
    binding = replace(binding, generation_manifests={key: _base()}, reused_artifact_pins={key: pin},
                      verified_reuse_keys=frozenset())
    try:
        yield SimpleNamespace(artifacts=artifacts, catalog=catalog, visible=visible, pin=pin,
                              payload=payload, request=request, binding=binding, key=key)
    finally:
        artifacts.close()


@pytest.mark.parametrize("already_verified,read_only,expected_reads", [(True, False, 0), (False, False, 1), (False, True, 1)])
def test_reuse_final_receipt_has_one_owner_read_per_operation(monkeypatch, published_reuse, already_verified, read_only, expected_reads):
    from company_wiki.automation import narrative_batch as batch
    request, payload, pin = published_reuse.request, published_reuse.payload, published_reuse.pin
    binding = replace(published_reuse.binding,
                      verified_reuse_keys=frozenset({payload.item_key}) if already_verified else frozenset())
    calls = []
    monkeypatch.setattr(batch, "read_reuse_pin", lambda *args, **kwargs: calls.append(args) or True)
    ledger = SimpleNamespace(reservations_for_run=lambda run_id: (), final_generations=lambda run_id: {})
    store = SimpleNamespace(list_jobs=lambda **kwargs: ())
    output = batch._final_documents(request, binding, store, ledger, published_reuse.artifacts, read_only=read_only,
                                    reader=object())
    assert len(calls) == expected_reads
    assert output[0]["status"] == "completed" and output[0]["generation_status"] == "reused"
    assert output[0]["artifact_ref"] == pin
    # These same-operation observations never enter the durable run binding.
    durable = json.loads(batch._frozen_binding(replace(request, sources=(payload.source_ref,)), binding))
    assert "verified_reuse_keys" not in durable


def test_new_operation_rejects_changed_reused_original_before_new_fee(monkeypatch, published_reuse):
    from company_wiki.automation import narrative_batch as batch
    request, binding = published_reuse.request, published_reuse.binding
    calls = []
    monkeypatch.setattr(batch, "read_reuse_pin", lambda *args, **kwargs: calls.append(args) or False)
    ledger = SimpleNamespace(reservations_for_run=lambda run_id: (), final_generations=lambda run_id: {})
    store = SimpleNamespace(list_jobs=lambda **kwargs: ())
    with pytest.raises(batch.BatchResumeError, match="BATCH_REUSE_ARTIFACT_INVALID"):
        batch._final_documents(request, binding, store, ledger, published_reuse.artifacts, read_only=True, reader=object())
    assert len(calls) == 1


def test_same_operation_verified_source_cannot_bypass_publication_proof(monkeypatch, published_reuse):
    from company_wiki.automation import narrative_batch as batch
    metadata = json.loads(published_reuse.visible.metadata_json)
    metadata["generation_sha256"] = "0" * 64
    with published_reuse.catalog.transaction() as connection:
        connection.execute("UPDATE narrative_artifact_versions SET metadata_json=? WHERE artifact_version_id=?",
                           (canonical_json(metadata), published_reuse.pin["artifact_version_id"]))
    binding = replace(published_reuse.binding, verified_reuse_keys=frozenset({published_reuse.key}))
    def forbidden(*args, **kwargs):
        pytest.fail("publication proof must reject corruption before another original-source read")
    monkeypatch.setattr(batch, "read_reuse_pin", forbidden)
    ledger = SimpleNamespace(reservations_for_run=lambda run_id: (), final_generations=lambda run_id: {})
    store = SimpleNamespace(list_jobs=lambda **kwargs: ())
    with pytest.raises(batch.BatchResumeError, match="BATCH_FROZEN_BINDING_INVALID"):
        batch._final_documents(published_reuse.request, binding, store, ledger,
                               published_reuse.artifacts, read_only=True, reader=object())
