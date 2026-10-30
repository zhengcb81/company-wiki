"""CWP fidelity wiring checks using only local DTOs and captured JSON.

No RF, live provider, source fetch, PDF parser, publication store or production writes.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
import gzip
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.models import canonical_json, canonical_json_hash
from company_wiki.automation.narrative_contracts import NarrativeSelectResult, NarrativeBundle, SourceRevisionEventPayload
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_model_runtime import build_model_request
from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler, _success
from company_wiki.automation.narrative_summary_assessment import assess_summary
from company_wiki.automation.narrative_summary_execution import wrap_summary, parse_summary_job_result
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from unit.test_narrative_batch import _request
from unit.test_narrative_extractive_runtime import selected
from unit.test_narrative_source_owned_model_boundary import official_reading

VERSION = "reading-model-input/6"


def bundle(source, summary, version=VERSION):
    kwargs = {}
    if "reading_projection_version" in inspect.signature(NarrativeVerifyHandler._bundle).parameters:
        kwargs["reading_projection_version"] = version
    return NarrativeVerifyHandler._bundle(source, summary, source.prompt_review, **kwargs)


def payload(source):
    if source.subject.kind == "official_json":
        return SourceRevisionEventPayload.from_dict({"schema_version": "source-revision-event/3.0",
            "subject_binding": source.subject.to_dict(), "source_metadata": source.source_metadata.to_dict()})
    return SourceRevisionEventPayload.from_dict({"schema_version": "source-revision-event/2.0",
        "source_ref": source.source_ref.to_dict(), "source_metadata": source.source_metadata.to_dict(),
        "expected_read_policy_sha256": source.expected_read_policy_sha256})


def manifest(source, version=VERSION):
    request = replace(_request(), selector_version="0.9.0", reading_model_projection=version)
    if source.subject.kind == "official_json":
        from company_wiki.automation.narrative_batch_request import NarrativeBatchItem, PROJECTED_BATCH_REQUEST_SCHEMA
        request = replace(request, sources=(), schema_version=PROJECTED_BATCH_REQUEST_SCHEMA,
                          items=(NarrativeBatchItem("official_json", projection_id=source.subject.item_key,
                                                   projection_sha256=source.subject.subject_sha256),))
    return batch._item_generation(request, payload(source), parser_components={
        "parser_name": source.parser.name, "parser_version": source.parser.version})


def completed(source, version=VERSION, *, warn=False):
    request = build_model_request(source, reading_projection_version=version)
    view = compile_scoped_model_view(source, max_claims=40)
    task = view.model_tasks[0]
    sid = task.support_ids[0]
    text = next(span.raw_text for span in source.evidence_spans if span.span_id == sid) or ""
    if warn:
        text = "该事项涉及家电产品。"
    part = "p" + str(task.member_ids.index(sid) + 1)
    # Entirely synthetic test bytes; never a live model or relabeled paid response.
    response = NarrativeModelResponse("offline-test", "synthetic-fixture", request.prompt_version,
        canonical_json({"drafts_by_task": {task.key: [{"text": text[:280], "basis_parts": [part],
                                                    "modality": "actual"}]}}).encode())
    report = {}
    summary = NarrativeSummarizeHandler._completed_result(source, source.prompt_review, response,
        reading_projection_version=version, execution_report=report)
    return summary, report


def skipped(source):
    wire = source.to_dict()
    wire["evidence_spans"] = []
    wire["selection"].update(status="skipped_no_narrative", selected_count=0)
    wire["reading_context"]["groups"] = []
    return NarrativeSelectResult.from_dict(wire)


def skip_probe(source):
    source = skipped(source)
    summary = NarrativeSummarizeHandler._skip_result(source)
    output = bundle(source, summary)
    planned = manifest(source)
    wire = output.to_dict()
    return {"kind": source.subject.kind, "bundle_schema": output.schema_version,
            "producer": output.versions.bundle_producer,
            "manifest_bundle_schema": planned["bundle_schema"], "manifest_producer": planned["bundle_producer"],
            "format_matches_manifest": output.schema_version == planned["bundle_schema"]
                and output.versions.bundle_producer == planned["bundle_producer"],
            "quality_status": output.quality_status, "summary_status": summary.status,
            "summary_model": wire["summary"]["model"], "declared_prompt": wire["versions"]["prompt"],
            "versions_model": wire["versions"]["model"],
            "assessment_field_present": "summary_assessment" in wire,
            "assessment": wire.get("summary_assessment"),
            "exact_roundtrip": NarrativeBundle.from_dict(wire).to_dict() == wire}


def rejects(call):
    try:
        call()
    except (ValueError, TypeError, KeyError):
        return True
    return False


def run():
    out = Path(__file__).parent
    source = selected(2, text_suffix="根据新闻报道，该事项涉及家电产品。")
    summary, report = completed(source, warn=True)
    output = bundle(source, summary)
    wire = output.to_dict()
    wrapper = wrap_summary(summary, report)
    cases = {}
    for mutation in ["missing_report", "legacy_schema", "wrong_producer", "forged_plan", "forged_admitted_set",
                     "quality_erased", "bare_summary", "wrapper1_downgrade", "wrapper_source_forgery"]:
        bad = deepcopy(wire)
        if mutation == "missing_report":
            bad.pop("summary_assessment")
        elif mutation == "legacy_schema":
            bad["schema_version"] = "narrative-bundle/2.0"
        elif mutation == "wrong_producer":
            bad["versions"]["bundle_producer"] = "1.0.0"
        elif mutation == "forged_plan":
            bad["summary_assessment"]["source_plan_sha256"] = "f" * 64
        elif mutation == "forged_admitted_set":
            r = bad["summary_assessment"]
            r.update(source_admitted_task_keys=["t1"], requested_task_keys=["t1"], emitted_task_keys=["t1"],
                     missing_requested_task_keys=[], budget_deferred_task_keys=[],
                     requested_emission_complete=True, admitted_emission_complete=True)
        elif mutation == "quality_erased":
            for claim in bad["summary"]["draft"]["claims"]:
                claim["needs_review"] = False
            bad["summary_assessment"]["claims_sha256"] = canonical_json_hash(bad["summary"]["draft"]["claims"])
        elif mutation == "bare_summary":
            cases[mutation] = rejects(lambda: parse_summary_job_result(summary.to_dict(), selected=source))
            continue
        elif mutation == "wrapper1_downgrade":
            altered = {"schema_version": "narrative-summary-execution/1", "summary": summary.to_dict(), "execution": {}}
            cases[mutation] = rejects(lambda: parse_summary_job_result(altered, selected=source))
            continue
        else:
            altered = deepcopy(wrapper)
            altered["assessment"]["source_plan_sha256"] = "f" * 64
            cases[mutation] = rejects(lambda: parse_summary_job_result(altered, selected=source))
            continue
        cases[mutation] = rejects(lambda: NarrativeBundle.from_dict(bad))

    result = _success(summary, execution=report)
    raw = canonical_json(result.to_dict())
    store = SimpleNamespace(list_attempts=lambda _: [SimpleNamespace(attempt_id="offline", result_json=raw)])
    observations = batch._attempt_model_diagnostics(store, {}, SimpleNamespace(job_id="job"))

    historical = deepcopy(wire)
    deps = historical["summary_assessment"]["validator"]["dependencies"]
    historical["summary_assessment"]["validator"]["dependencies"] = {key: "1" * 64 for key in deps}
    historical["summary_assessment"]["validator"]["implementation_sha256"] = canonical_json_hash(
        historical["summary_assessment"]["validator"]["dependencies"])
    history_read = NarrativeBundle.from_dict(historical).to_dict()

    capture = ROOT / ".planning/source-description-20261030/real-summary-v3"
    captured_bytes = gzip.open(next(capture.glob("*.bundle.json.gz")), "rb").read()
    old = NarrativeBundle.from_dict(json.loads(captured_bytes)).to_dict()
    legacy = ModuleType("company_wiki.automation._fidelity_audit_legacy_scoped")
    legacy.__package__ = "company_wiki.automation"
    legacy.__file__ = str(ROOT / "src/company_wiki/automation/narrative_model_scoped.py")
    sys.modules[legacy.__name__] = legacy
    exec(subprocess.check_output(["git", "show", "6c129706:src/company_wiki/automation/narrative_model_scoped.py"],
                                cwd=ROOT, text=True, encoding="utf-8"), legacy.__dict__)
    before = legacy.build_scoped_request(source).with_output_budget(8192)
    after = build_model_request(source, reading_projection_version="reading-model-input/4").with_output_budget(8192)
    legacy_extractive = ModuleType("company_wiki.automation._fidelity_audit_legacy_extractive")
    legacy_extractive.__package__ = "company_wiki.automation"
    legacy_extractive.__file__ = str(ROOT / "src/company_wiki/automation/narrative_model_extractive.py")
    sys.modules[legacy_extractive.__name__] = legacy_extractive
    exec(subprocess.check_output(["git", "show", "6c129706:src/company_wiki/automation/narrative_model_extractive.py"],
                                cwd=ROOT, text=True, encoding="utf-8"), legacy_extractive.__dict__)
    legacy_extractive.compile_scoped_model_view = legacy.compile_scoped_model_view
    extractive_before = legacy_extractive.build_extractive_request(source).with_output_budget(8192)
    extractive_after = build_model_request(source, reading_projection_version="reading-model-input/5").with_output_budget(8192)

    projected = official_reading()
    psummary, _ = completed(projected)
    poutput = bundle(projected, psummary)
    pmanifest = manifest(projected)
    legacy_projected_summary, _ = completed(projected, version="reading-model-input/4")
    legacy_projected_wire = bundle(projected, legacy_projected_summary, version="reading-model-input/4").to_dict()
    planned = manifest(source)
    default_planned = manifest(source, version=None)
    new_request = build_model_request(source, reading_projection_version=VERSION).with_output_budget(8192)
    request_wire = json.loads(new_request.data_json)
    data = {
        "schema_version": "independent-fidelity-wiring-probe/1", "offline_only_no_paid_no_pdf": True,
        "new_request": {"prompt": new_request.prompt_version, "schema": request_wire["schema_version"],
                        "material_cap": request_wire["material"]["max_claims"], "output_cap": request_wire["output_plan"]["max_claims"]},
        "raw": {"schema": output.schema_version, "producer": output.versions.bundle_producer,
                "manifest_matches": output.schema_version == planned["bundle_schema"]
                    and output.versions.bundle_producer == planned["bundle_producer"],
                "wrapper_schema": wrapper["schema_version"],
                "wrapper_rechecks": parse_summary_job_result(wrapper, selected=source) == summary,
                "risk_flags_retained": all(c.needs_review for c in summary.draft.claims),
                "draft_status": summary.draft.status, "semantic_status": wire["summary_assessment"]["semantic_status"]},
        "projected": {"schema": poutput.schema_version, "manifest_matches": poutput.schema_version == pmanifest["bundle_schema"]
            and poutput.versions.bundle_producer == pmanifest["bundle_producer"]},
        "legacy_projected": {"schema": legacy_projected_wire["schema_version"],
                             "producer": legacy_projected_wire["versions"]["bundle_producer"],
                             "assessment_absent": "summary_assessment" not in legacy_projected_wire,
                             "exact_roundtrip": NarrativeBundle.from_dict(legacy_projected_wire).to_dict() == legacy_projected_wire},
        "forgery_rejections": cases,
        "batch_assessment_visible_without_reasoning_meter": bool(observations and observations[0].get("execution")),
        "historical_recipe_preserved_as_descriptive_metadata": history_read == historical,
        "legacy_actual_capture_roundtrip_exact_bytes": canonical_json(old).encode() == captured_bytes,
        "legacy_actual_capture_sha256": hashlib.sha256(captured_bytes).hexdigest(),
        "legacy4_request_data_unchanged": before.data_json == after.data_json,
        "legacy4_instruction_unchanged": before.instruction == after.instruction,
        "legacy4_request_hash_unchanged": before.input_sha256 == after.input_sha256,
        "legacy5_request_data_unchanged": extractive_before.data_json == extractive_after.data_json,
        "legacy5_instruction_unchanged": extractive_before.instruction == extractive_after.instruction,
        "legacy5_request_hash_unchanged": extractive_before.input_sha256 == extractive_after.input_sha256,
        "default_generation": {"projection": default_planned.get("reading_model_projection"),
                               "schema": default_planned["bundle_schema"],
                               "prompt": default_planned["execution_versions"]["prompt"]},
        "raw_skip": skip_probe(selected(1)), "projected_skip": skip_probe(projected),
    }
    (out / "probe-result.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
