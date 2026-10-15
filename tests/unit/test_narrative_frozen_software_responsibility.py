"""Recorded model identity is history; execution capabilities belong to a stage."""
from copy import deepcopy
import json

import pytest

from company_wiki.automation import narrative_batch as batch
from company_wiki.automation import narrative_generation as generation
from company_wiki.automation import narrative_worker_factory as factory
from company_wiki.automation.models import HandlerOutcome
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model import ModelResponseError
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from unit.test_narrative_output_language_binding import manifests, selected_english
from unit.test_narrative_summarize_handler import _context


def old_software_manifest():
    value = deepcopy(manifests("reading-model-input/2"))
    value["reading_model_boundary"]["decoder_sha256"] = "a" * 64
    value["summary_validation"]["observer_sha256"] = "b" * 64
    return value


def test_resume_retains_recorded_software_without_claiming_it_is_current():
    recorded = old_software_manifest()
    actual = manifests("reading-model-input/2")
    restored = generation.with_frozen_model_identity(actual, recorded)
    assert restored == recorded
    assert actual != recorded
    assert factory._validate_model_software(actual) == "reading-model-input/2"
    with pytest.raises(ModelResponseError, match="READING_MODEL_BOUNDARY_UNAVAILABLE"):
        factory._validate_model_software(recorded)


@pytest.mark.parametrize("field", ["model", "profile", "source_metadata", "source_ref", "execution_versions"])
def test_preserving_history_does_not_hide_request_source_or_execution_changes(field):
    recorded = old_software_manifest()
    actual = deepcopy(recorded)
    assert field in actual
    actual[field] = ({**actual[field], "selector": "a real selector change"}
                     if field == "execution_versions" else {"changed": "a real semantic change"})
    restored = generation.with_frozen_model_identity(actual, recorded)
    assert restored[field] == actual[field]
    assert generation.generation_sha256(restored) != generation.generation_sha256(recorded)


@pytest.mark.parametrize("kind", ["decoder", "validator", "unknown_renderer"])
def test_snapshot_does_not_execute_finished_siblings_model_software(kind):
    current = manifests("reading-model-input/3")
    old = deepcopy(current)
    if kind == "decoder":
        old["reading_model_boundary"]["decoder_sha256"] = "a" * 64
    elif kind == "validator":
        old["summary_validation"]["observer_sha256"] = "b" * 64
    else:
        old["reading_model_projection"] = "retired-not-installed/99"
    binding = {"execution_versions": {"selector": "0.9.0"},
               **batch._freeze_generations({"current": current, "finished": old})}
    snapshot = factory._worker_binding_snapshot(json.dumps(binding))
    assert set(snapshot.frozen_generations) == {"current", "finished"}
    assert factory._validate_model_software(snapshot.frozen_generations["current"]) == "reading-model-input/3"
    with pytest.raises(ModelResponseError):
        factory._validate_model_software(snapshot.frozen_generations["finished"])


def test_model_stage_checks_its_actual_capability_before_any_paid_call():
    selected = selected_english()
    called = []

    class Caller:
        def generate(self, *args):
            raise AssertionError("unavailable software must not call/reserve a model")

    def unavailable(subject):
        called.append(subject.item_key)
        raise ModelResponseError("READING_MODEL_BOUNDARY_UNAVAILABLE")

    result = NarrativeSummarizeHandler(model=None, model_caller=Caller(),
        reading_model_projection=lambda subject: "reading-model-input/3",
        validate_model_execution=unavailable)(_context(selected))
    assert called == [selected.subject.item_key]
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert result.error.code == "MODEL_GENERATION_UNAVAILABLE"
    assert result.metrics.tokens == 0
    assert result.artifacts == result.effects == ()
    assert "failed_final" not in result.result


def test_no_summary_work_needs_no_model_implementation():
    wire = selected_english().to_dict()
    wire["selection"].update(status="skipped_no_narrative", selected_count=0, coverage_complete=True)
    wire["evidence_spans"] = []
    wire.pop("reading_context", None)
    selected = NarrativeSelectResult.from_dict(wire)

    def unnecessary(subject):
        raise AssertionError("skipped source has no model execution")

    result = NarrativeSummarizeHandler(model=None,
        validate_model_execution=unnecessary)(_context(selected))
    assert result.outcome is HandlerOutcome.SUCCEEDED
    assert result.result["status"] == "summary_not_needed"
