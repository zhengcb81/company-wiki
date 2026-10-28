"""Gold observations describe the actual source tasks, never emitted claims."""
from dataclasses import replace
import hashlib
import json

import pytest

from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model_runtime import build_model_request
from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
from tools.document_understanding_benchmark import phase_c_observer as observer
from unit.test_narrative_extractive_runtime import selected


def test_pre_reservation_selection_checkpoint_retains_diagnostics_and_is_immutable(tmp_path):
    import gzip

    source = selected(2)
    before = source.to_dict()
    snapshot = observer.capture_selection_checkpoint(source, tmp_path, 'bounded-run')
    assert json.loads(gzip.decompress((tmp_path / snapshot['file']).read_bytes())) == before
    assert snapshot['sha256'] == hashlib.sha256(json.dumps(before, ensure_ascii=False,
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert observer.capture_selection_checkpoint(source, tmp_path, 'bounded-run') == snapshot
    with pytest.raises(ValueError, match='SELECTION_CHANGED'):
        observer.capture_selection_checkpoint(selected(3), tmp_path, 'bounded-run')
    assert json.loads(gzip.decompress((tmp_path / snapshot['file']).read_bytes())) == before


def _gold(source):
    return {"facts": [{"id": "fact-" + str(index), "target_kind": "required_business",
        "importance": "critical", "any_support_sets": [[{
            "page": span.coordinates.page_number, "exact_quote": span.raw_text,
        }]]} for index, span in enumerate(source.evidence_spans)]}


def _envelope(source, version, sent=None):
    value = json.loads(build_model_request(source, reading_projection_version=version).data_json)
    if sent is not None:
        view = compile_scoped_model_view(source,
            max_claims=20 if version.endswith("/4") else len(source.evidence_spans) * 2)
        value["material"] = replace(view, visible_keys=frozenset(sent)).to_model_dict()
    return value


@pytest.mark.parametrize("version", ["reading-model-input/4", "reading-model-input/5"])
def test_repair_subset_cannot_borrow_gold_from_an_unsent_task(version):
    source = selected(3)
    report = observer.gold_observation(_gold(source), source, _envelope(source, version, ["t2"]))
    assert report["full_selection"]["scope"] == "full_selected_source_availability"
    assert report["full_selection"]["supported_count"] == 3
    sent = report["sent_tasks"]
    assert sent["scope"] == "source_support_in_current_request_tasks"
    assert sent["request_scope"] == "repair_subset"
    assert sent["sent_task_keys"] == ["t2"]
    assert sent["supported_count"] == 1
    assert sent["not_sent_ids"] == ["fact-0", "fact-2"]
    assert sent["facts"][0]["supported_task_keys"] == []
    assert sent["facts"][1]["supported_task_keys"] == ["t2"]
    assert sent["summary_claim_coverage"] == "not_evaluated"


def test_first_request_requires_gold_inside_actual_sent_tasks():
    source = selected(3)
    gold = _gold(source)
    gold["facts"].append({"id": "absent", "target_kind": "required_business",
        "any_support_sets": [[{"page": 1, "exact_quote": "An absent source statement."}]]})
    report = observer.gold_observation(gold, source, _envelope(source, "reading-model-input/4"))
    assert report["sent_tasks"]["request_scope"] == "full_request"
    assert report["sent_tasks"]["missing_ids"] == ["absent"]
    assert observer.gold_admission_missing(report, attempt_no=1) == ["absent"]


def test_repair_reports_unsent_gold_without_requiring_completed_tasks_again():
    source = selected(3)
    report = observer.gold_observation(_gold(source), source,
        _envelope(source, "reading-model-input/4", ["t2"]))
    assert report["sent_tasks"]["missing_ids"] == ["fact-0", "fact-2"]
    assert observer.gold_admission_missing(report, attempt_no=2) == []
    with pytest.raises(ValueError, match="subset.*initial"):
        observer.gold_admission_missing(report, attempt_no=1)


def test_task_shared_references_keep_actual_support_and_context_closure():
    source = selected(3)
    wire = source.to_dict()
    ids = [span.span_id for span in source.evidence_spans]
    groups = []
    for members, support, context in ((ids[:2], ids[:1], ids[1:2]),
                                      (ids[1:], ids[2:], ids[1:2])):
        digest = hashlib.sha256(json.dumps(members, separators=(",", ":")).encode()).hexdigest()
        groups.append({"group_id": "urn:company-wiki:reading-group:sha256:" + digest,
            "kind": "business_progress", "section_role": "business", "evidence_ids": members,
            "citation_views": [{"support_evidence_ids": support, "context_evidence_ids": context}]})
    wire["reading_context"].update(schema_version="du-production-reading/2", groups=groups)
    source = NarrativeSelectResult.from_dict(wire)
    envelope = _envelope(source, "reading-model-input/4")
    assert envelope["material"]["shared_fragments"]
    report = observer.gold_observation(_gold(source), source, envelope)
    assert report["sent_tasks"]["supported_count"] == 3
    assert report["sent_tasks"]["facts"][1]["supported_task_keys"] == ["t1", "t2"]
    assert report["sent_tasks"]["summary_claim_coverage"] == "not_evaluated"


def test_gold_anchors_in_different_tasks_cannot_form_one_task_support_set():
    source = selected(2)
    anchors = [fact["any_support_sets"][0][0] for fact in _gold(source)["facts"]]
    gold = {"facts": [{"id": "one-closed-task", "target_kind": "required_business",
                       "any_support_sets": [anchors]}]}
    report = observer.gold_observation(gold, source, _envelope(source, "reading-model-input/4"))
    assert report["sent_tasks"]["supported_count"] == 0
    assert report["sent_tasks"]["missing_ids"] == ["one-closed-task"]
