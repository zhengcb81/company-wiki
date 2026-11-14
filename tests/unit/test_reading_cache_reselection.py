"""Unknown fast proof triggers current source selection, never blind re-payment."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import json

import pytest

from company_wiki.automation import narrative_generation as generation
from company_wiki.automation.models import canonical_json, canonical_json_hash
from company_wiki.automation.narrative_selection_generation import reading_material_sha256
from company_wiki.source_catalog.narrative_official_json import bind_projection_loader
from unit.test_narrative_extractive_production import new_request
from unit.test_narrative_summarize_handler import _context


def _case():
    selected, request = new_request()
    payload = _context(selected).source_revision
    base = generation.generation_manifest(request, payload, execution_versions=request.execution_versions)
    stored = {**base, "reading_dependencies": {
        "schema_version": "du-decision-dependencies/1", "status": "partial", "decision_digest": None,
    }, "selection_generation": {
        "schema_version": "narrative-selection-generation/1",
        "select_result_sha256": canonical_json_hash(selected.to_dict()),
        "evidence_sha256": canonical_json_hash([span.to_dict() for span in selected.evidence_spans]),
        "material_sha256": reading_material_sha256(selected),
        "reading_policy_version": selected.reading_context["reading_policy_version"],
    }}
    ref = selected.source_ref
    version = SimpleNamespace(artifact_version_id="existing-paid", content_sha256="a" * 64,
        byte_size=123, document_id=ref.document_id, source_id=ref.source_id,
        source_sha256=ref.content_sha256, metadata_json=canonical_json({
            "generation_manifest": stored, "generation_sha256": generation.generation_sha256(stored)}))
    return selected, payload, base, stored, version


@pytest.mark.parametrize("changed", [False, True])
def test_partial_dependency_reuse_requires_actual_current_material_and_one_reselection(monkeypatch, changed):
    selected, payload, base, stored, version = _case()
    original = deepcopy(stored)
    calls, reads = [], []
    current = replace(selected, selection=replace(selected.selection,
                      status="partial", coverage_complete=False)) if changed else selected

    def reselect():
        calls.append("source-select")
        return current

    monkeypatch.setattr(generation, "read_reuse_pin", lambda *a, **kw: reads.append("public-proof") or True)
    artifacts = SimpleNamespace(visible_base_generation_candidates=lambda **kw: (version, version))
    result = generation.find_reuse_pin(artifacts, None, payload, base, {}, reselect=reselect)
    assert (result is not None) is (not changed)
    assert len(calls) == 1
    assert len(reads) == (0 if changed else 1)
    assert json.loads(version.metadata_json)["generation_manifest"] == original
    assert not generation.current_reading_decision_matches(stored)


def test_fast_proven_cache_does_not_reselect(monkeypatch):
    _, payload, base, _, version = _case()
    monkeypatch.setattr(generation, "current_reading_decision_matches", lambda _m: True)
    monkeypatch.setattr(generation, "read_reuse_pin", lambda *a, **kw: True)
    artifacts = SimpleNamespace(visible_base_generation_candidates=lambda **kw: (version,))

    def forbidden():
        pytest.fail("known dependency proof must retain its fast path")

    assert generation.find_reuse_pin(artifacts, None, payload, base, {}, reselect=forbidden)


def test_reselection_failure_is_not_a_cache_miss_or_model_allowance(monkeypatch):
    _, payload, base, _, version = _case()
    artifacts = SimpleNamespace(visible_base_generation_candidates=lambda **kw: (version,))

    def failed():
        raise TimeoutError("bounded source selection deadline")

    with pytest.raises(TimeoutError, match="selection deadline"):
        generation.find_reuse_pin(artifacts, None, payload, base, {}, reselect=failed)


def test_observed_current_material_takes_precedence_over_later_fast_claim(monkeypatch):
    selected, _, _, stored, _ = _case()
    changed = replace(selected, selection=replace(selected.selection, status="partial", coverage_complete=False))
    verifier = generation.ReadingReuseVerifier(lambda: changed)
    monkeypatch.setattr(generation, "current_reading_decision_matches", lambda _m: False)
    assert not verifier.matches(stored)
    monkeypatch.setattr(generation, "current_reading_decision_matches", lambda _m: True)
    assert not verifier.matches(stored), "a fast claim cannot override already observed different source material"


def test_source_port_and_worker_use_identical_selection_and_real_model_wire():
    from unit.test_narrative_select_handler import FakeReader, _payload, _context as select_context
    from company_wiki.automation.narrative_select import NarrativeSelectHandler
    from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload, NarrativeSelectResult
    from company_wiki.automation.narrative_model_runtime import build_model_request
    from company_wiki.automation.narrative_http_model import NarrativeHTTPModel

    data = b"Full Conference Call Transcript\nCEO: We expanded overseas capacity and started a new product launch.\n"
    raw = _payload(data, title="Acme Q2 earnings call", document_kind="earnings_call_transcript",
                   language="en", mime_type="text/plain")
    payload = SourceRevisionEventPayload.from_dict(raw)
    handler = NarrativeSelectHandler(reader=FakeReader(raw, data), selector_version="0.9.0")
    checks = []
    fresh = handler.select_source(payload, checkpoint=lambda: checks.append("read"))
    worker = handler(select_context(raw, lambda: checks.append("worker")))
    selected = NarrativeSelectResult.from_dict(dict(worker.result))
    assert fresh.to_dict() == selected.to_dict() and checks
    assert fresh.evidence_spans
    old_request = build_model_request(selected, reading_projection_version="reading-model-input/5").with_output_budget(8192)
    new_request = build_model_request(fresh, reading_projection_version="reading-model-input/5").with_output_budget(8192)
    adapter = NarrativeHTTPModel(model_id="fixture", endpoint="https://fixture.invalid/v1/chat/completions",
                                 api_key_env="UNUSED_FAKE_KEY", max_output_tokens=8192)
    assert old_request.input_sha256 == new_request.input_sha256
    assert adapter.request_bytes(old_request) == adapter.request_bytes(new_request)


def test_projected_candidates_use_the_same_current_material_fallback(monkeypatch):
    from unit.test_official_json_narrative_adapter import open_fixture
    from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
    from company_wiki.automation.narrative_select import NarrativeSelectHandler
    from company_wiki.automation import narrative_batch as batch

    view, _, _, _, catalog = open_fixture(monkeypatch)
    payload = SourceRevisionEventPayload.from_dict({"schema_version": "source-revision-event/3.0",
        "subject_binding": view.subject.to_dict(), "source_metadata": {"source_class": "official_json",
        "title": "Official business Q&A", "document_kind": "investor_relations", "language": "zh"}})
    handler = NarrativeSelectHandler(reader=None, projection_loader=bind_projection_loader(catalog), selector_version="0.9.0")
    selected = handler.select_source(payload, checkpoint=lambda: None)
    _, request = new_request()
    base = generation.projection_generation_manifest(
        request, payload.subject, language="zh", execution_versions=request.execution_versions,
        bundle_producer="1.0.0", narrative_adapter_version="1.0.1",
        source_metadata=payload.source_metadata.to_dict(), reading_model_projection="reading-model-input/5",
    )
    stored = {**base, "reading_dependencies": {"schema_version": "du-decision-dependencies/1", "status": "partial"},
        "selection_generation": {"schema_version": "narrative-selection-generation/1",
            "select_result_sha256": canonical_json_hash(selected.to_dict()),
            "evidence_sha256": canonical_json_hash([span.to_dict() for span in selected.evidence_spans]),
            "material_sha256": reading_material_sha256(selected),
            "reading_policy_version": selected.reading_context["reading_policy_version"]}}
    version = SimpleNamespace(artifact_version_id="projected-paid", content_sha256="a" * 64, byte_size=123,
        metadata_json=canonical_json({"generation_manifest": stored,
                                      "generation_sha256": generation.generation_sha256(stored)}))
    calls = []
    monkeypatch.setattr(NarrativeSelectHandler, "select_source", lambda *a, **kw: calls.append("source") or selected)
    monkeypatch.setattr(batch, "_read_projected_pin", lambda *a, **kw: True)
    artifacts = SimpleNamespace(visible_base_generation_candidates=lambda **kw: (version,))
    pin = batch._find_item_reuse_pin(artifacts, None, payload, base, {}, projection_loader=bind_projection_loader(catalog))
    assert pin["artifact_version_id"] == "projected-paid" and calls == ["source"]
