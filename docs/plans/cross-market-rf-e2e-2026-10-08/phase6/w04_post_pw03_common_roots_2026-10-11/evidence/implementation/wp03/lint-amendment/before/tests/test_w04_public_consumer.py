"""W04 consumer-only contract challenges; these are not producer receipts."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from company_wiki_narrative_contracts import (NarrativeTransportError, canonical_bytes,
    validate_narrative_request, validate_narrative_response, validate_reference_response)
from filing_upstream_cause import failure_observation
from test_company_wiki_narrative_reader import _valid, _resign


def _sha(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def projected_wire():
    request, raw, _ = _valid()
    bundle = json.loads(raw)
    parents = [deepcopy(request["narrative_ref"]["source_ref"])]
    parents[0]["mime_type"] = "application/json"
    other = deepcopy(parents[0])
    other.update(document_id="other-page", source_id="urn:company-wiki:source:sha256:" + "b" * 64,
                 content_sha256="b" * 64, byte_size=4096)
    parents.append(other)
    subject = {"kind": "official_json", "item_key": "urn:company-wiki:source-projection:sha256:" + "c" * 64,
        "subject_sha256": "c" * 64, "parent_source_refs": parents, "issuer": {"market": "US", "security_id": "ACME"},
        "as_of_date": "2026-09-01", "adapter": {"parser": "cwp_official_json/1.0.1"},
        "coverage": {"page_envelope_complete": True, "pagination_complete": True}}
    bundle["schema_version"] = "narrative-bundle/3.0"
    bundle["subject_binding"] = subject
    for key in ("source_ref", "expected_read_policy_sha256", "transcript_lineage", "transcript_byte_bindings"):
        del bundle[key]
    bundle["source_metadata"].update(source_class="official_json", document_kind="investor_relations")
    span = bundle["evidence_spans"][0]
    span["source_id"] = other["source_id"]
    binding = span["structured_value"]
    binding.update(projection_id=subject["item_key"], parent_content_sha256=other["content_sha256"],
        pointer="/records/0/answer", record_pointer="/records/0", source_locator="cwp-json-pointer/1|p=%2Frecords%2F0%2Fanswer|b=4:20|d=0:16|x=json-string-decode/1",
        token_range=[4, 20], encoded_body_range=[5, 19], encoded_token_sha256="e" * 64,
        decoded_sha256=hashlib.sha256(span["raw_text"].encode()).hexdigest())
    span["output_sha256"] = _sha({"raw_text": span["raw_text"], "structured_value": binding})
    span["span_id"] = "urn:company-wiki:evidence-span:sha256:" + _sha({"source_id": span["source_id"],
        "locator": span["locator"], "output_sha256": span["output_sha256"]})
    draft = bundle["summary"]["draft"]
    draft["subject_id"], draft["subject_sha256"] = subject["item_key"], subject["subject_sha256"]
    del draft["source_id"], draft["source_sha256"]
    draft["claims"][0]["evidence_ids"] = [span["span_id"]]
    bundle["prompt_review"]["source_sha256"] = parents[0]["content_sha256"]
    body = canonical_bytes(bundle)
    ref = {"schema_version": "narrative-ref/3", "artifact_version_id": "projection-v1",
        "artifact_sha256": hashlib.sha256(body).hexdigest(), "byte_size": len(body), "generation_sha256": "d" * 64,
        "subject_ref": {"schema_version": "narrative-subject-ref/1", "kind": subject["kind"],
            "item_key": subject["item_key"], "subject_sha256": subject["subject_sha256"]}}
    request = {"schema_version": "narrative-read-request/3", "narrative_ref": ref,
        "as_of_date": subject["as_of_date"], "expected_issuer": subject["issuer"]}
    receipt = {"schema_version": "narrative-read-receipt/3", "status": "ok", "narrative_ref": deepcopy(ref),
        "as_of_date": request["as_of_date"], "observed_at": "2026-09-02T00:00:00Z", "locator_count": 1,
        "parent_count": 2, "lineage_sha256": _sha(subject), "selection_status": bundle["selection"]["status"],
        "quality_status": bundle["quality_status"], "replay_status": "verified"}
    return request, body, canonical_bytes(receipt) + b"\n"


def test_optional_declared_language_is_preserved_and_old_four_keys_read():
    request, body, raw = _valid()
    assert "declared_language" not in validate_narrative_response(request, body, raw).to_dict()["source_metadata"]
    bundle, receipt = json.loads(body), json.loads(raw)
    bundle["source_metadata"]["declared_language"] = "en-US"
    body, raw = _resign(request, bundle, receipt)
    assert validate_narrative_response(request, body, raw).to_dict()["source_metadata"]["declared_language"] == "en-US"


@pytest.mark.parametrize("key,value", [("declared_language", "zh-Hant"), ("declared_language", True),
    ("declared_language", "fr-FR"), ("title", 0), ("unexpected", "value")])
def test_metadata_types_family_and_unknown_fields_refused(key, value):
    request, body, raw = _valid()
    bundle, receipt = json.loads(body), json.loads(raw)
    bundle["source_metadata"][key] = value
    body, raw = _resign(request, bundle, receipt)
    with pytest.raises(NarrativeTransportError):
        validate_narrative_response(request, body, raw)


def test_compact_projected_read_preserves_all_parent_refs_and_original_pointer():
    request, body, receipt = projected_wire()
    context = validate_narrative_response(request, body, receipt).to_dict()
    assert context["schema_version"] == "revenue-narrative-context/3"
    assert "source_ref" not in context
    assert context["subject_binding"] == json.loads(body)["subject_binding"]
    assert len(context["parent_source_refs"]) == 2
    assert context["evidence_spans"][0]["structured_value"]["pointer"] == "/records/0/answer"
    assert context["narrative_ref"] == request["narrative_ref"]


def test_compact_projected_reference_response_and_request_are_bounded():
    request, _, _ = projected_wire()
    ref = request["narrative_ref"]
    lookup = {"schema_version": "narrative-reference-request/3", "subject_ref": ref["subject_ref"],
              "generation_sha256": ref["generation_sha256"]}
    raw = canonical_bytes({"schema_version": "narrative-read-receipt/3", "status": "metadata_only", "narrative_ref": ref}) + b"\n"
    assert validate_reference_response(lookup, canonical_bytes(ref) + b"\n", raw) == ref
    assert len(canonical_bytes(validate_narrative_request(request)) + b"\n") <= 16384


@pytest.mark.parametrize("mutation", ["parent", "pointer", "issuer", "asof", "lineage", "generation"])
def test_projected_binding_or_receipt_drift_refused_even_with_resigned_body(mutation):
    request, body, raw = projected_wire()
    bundle, receipt = json.loads(body), json.loads(raw)
    if mutation == "parent":
        bundle["subject_binding"]["parent_source_refs"].pop()
    elif mutation == "pointer":
        bundle["evidence_spans"][0]["structured_value"]["pointer"] = "/other/answer"
    elif mutation == "issuer":
        bundle["subject_binding"]["issuer"]["security_id"] = "OTHER"
    elif mutation == "asof":
        bundle["subject_binding"]["as_of_date"] = "2026-09-02"
    elif mutation == "lineage":
        receipt["lineage_sha256"] = "0" * 64
    else:
        receipt["narrative_ref"]["generation_sha256"] = "0" * 64
    body, raw = _resign(request, bundle, receipt)
    if mutation == "generation":
        receipt = json.loads(raw)
        receipt["narrative_ref"]["generation_sha256"] = "0" * 64
        raw = canonical_bytes(receipt) + b"\n"
    with pytest.raises(NarrativeTransportError):
        validate_narrative_response(request, body, raw)


def test_ff_typed_request_sibling_survives_without_changing_six_key_cause():
    cause = {"schema_version": "filing-upstream-cause/1", "operation": "resolve", "code": "unknown",
        "provider_started": False, "usage_complete": None, "retry_scope": "none"}
    diagnostic = {"schema_version": "filing-request-diagnostic/1", "reason": "exact_requires_fiscal_year", "field_path": "fiscal_year"}
    seen = failure_observation({"upstream_cause": cause, "request_diagnostic": diagnostic})
    assert seen["upstream_cause"] == cause
    assert seen["request_diagnostic"] == diagnostic
    assert failure_observation({"upstream_cause": cause}) == {"upstream_cause": cause}
    for key, value in (("reason", "secret=value"), ("field_path", "private_path"), ("extra", "x")):
        bad = {**diagnostic, key: value}
        assert "request_diagnostic" not in failure_observation({"request_diagnostic": bad})


@pytest.mark.parametrize("kind", ["investor_presentation", "investor_relations", "broker_research"])
def test_pinned_nonperiod_null_fy_passes_registered_path_without_ff(kind, tmp_path):
    from source_preparation import prepare_registered_source_result
    from test_company_wiki_source_v2 import _inputs, BODY
    ref, receipt, manifest = _inputs()
    manifest.update(document_kind=kind, fiscal_year=None, fiscal_period=None, period_end=None)
    candidate = {"status": "source_candidate", "source_ref": ref,
        "byte_verification": "pending_verified_open", "document_kind": kind, "fiscal_year": None,
        "fiscal_period": None, "resolution_outcome": "reused_existing", "download_events": 0}
    config = tmp_path / "catalog.json"
    config.write_text("{}", encoding="utf-8")
    with patch("company_wiki_source_reader_v2.open_source_version_v2", return_value=(BODY, receipt, manifest)) as opened, \
         patch("source_preparation._run_filing_fetch", side_effect=AssertionError("pinned read must not acquire")):
        result = prepare_registered_source_result(candidate, as_of_date="2026-09-27", company_wiki_catalog_config=config)
    assert opened.call_args.kwargs["expected_fiscal_year"] is None
    assert result["filing_fetch"] is None
    assert result["source"]["capture"]["snapshot_sha256"] == ref["content_sha256"]
    assert result["source"]["source_type"] == {"investor_presentation": "investor_presentation",
        "investor_relations": "company_release", "broker_research": "specialist_research"}[kind]


def test_unknown_kind_never_becomes_regulatory_filing():
    from source_preparation import _revenue_source_type
    with pytest.raises(RuntimeError, match="unsupported_revenue_document_kind"):
        _revenue_source_type({"document_kind": "unknown"})


def _consumption_data(parent):
    return {"as_of_date": "2026-09-01", "sources": [{"source_id": "source-alias",
        "capture": {"snapshot_sha256": parent["content_sha256"], "receipt_sha256": "f" * 64}}],
        "parameters": [{"parameter_id": "qualitative", "kind": "analyst_assumption", "value": 2},
            {"parameter_id": "derived", "kind": "derived_fact", "input_parameter_ids": ["qualitative"]},
            {"parameter_id": "unused", "kind": "analyst_assumption", "value": 9}],
        "segments": [{"name": "A", "scenarios": {"base": {"model": "direct_revenue",
            "driver_parameter_ids": {"revenue": ["derived"]}}}}]}


def test_projected_rationale_reaches_derived_ancestor_and_actual_segment_formula(tmp_path):
    from source_narrative_context import consume_narrative_input
    request, body, raw = projected_wire()
    context = validate_narrative_response(request, body, raw)
    value = context.to_dict()
    data = _consumption_data(value["parent_source_refs"][1])
    binding = {"span_id": value["evidence_spans"][0]["span_id"], "claim_id": "support-mechanism",
        "parameter_id": "qualitative", "support_type": "rationale_support"}
    with patch("source_narrative_context.read_narrative_context", return_value=context):
        _, unread = consume_narrative_input(data, request=request, bindings=[], source_id="source-alias", catalog_config=tmp_path / "catalog.json")
        assert unread["status"] == "not_consumed" and unread["dependencies"] == []
        updated, receipt = consume_narrative_input(data, request=request, bindings=[binding], source_id="source-alias", catalog_config=tmp_path / "catalog.json")
        assert receipt["status"] == "consumed"
        dependency = receipt["dependencies"][0]
        assert dependency["source_sha256"] == value["parent_source_refs"][1]["content_sha256"]
        assert dependency["source_locator"] == value["evidence_spans"][0]["structured_value"]["source_locator"]
        assert dependency["formula_refs"][0]["output"] == "recognized_revenue"
        assert updated["parameters"][0]["value"] == data["parameters"][0]["value"]
        assert updated["evidence_claims"][0]["locator"] == dependency["source_locator"]
        for changed in ({**binding, "parameter_id": "unused"}, {**binding, "support_type": "numeric_support"}):
            with pytest.raises(ValueError):
                consume_narrative_input(data, request=request, bindings=[changed], source_id="source-alias", catalog_config=tmp_path / "catalog.json")
        wrong_source = deepcopy(data)
        wrong_source["sources"][0]["capture"]["snapshot_sha256"] = value["parent_source_refs"][0]["content_sha256"]
        with pytest.raises(ValueError):
            consume_narrative_input(wrong_source, request=request, bindings=[binding], source_id="source-alias", catalog_config=tmp_path / "catalog.json")
        wrong_date = {**data, "as_of_date": "2026-09-02"}
        with pytest.raises(ValueError):
            consume_narrative_input(wrong_date, request=request, bindings=[binding], source_id="source-alias", catalog_config=tmp_path / "catalog.json")


def test_public_registered_candidate_needs_no_filing_fetch_resolution_fields(tmp_path):
    from source_preparation import prepare_registered_source_result
    from test_company_wiki_source_v2 import _inputs, _candidate, BODY
    ref, receipt, manifest = _inputs()
    manifest.update(document_kind="broker_research", fiscal_year=None, fiscal_period=None, period_end=None)
    candidate = _candidate(ref, manifest)
    assert "download_events" not in candidate and "resolution_outcome" not in candidate
    config = tmp_path / "catalog.json"
    config.write_text("{}", encoding="utf-8")
    with patch("company_wiki_source_reader_v2.open_source_version_v2", return_value=(BODY, receipt, manifest)), \
         patch("source_preparation._run_filing_fetch", side_effect=AssertionError("pinned source cannot acquire")):
        prepared = prepare_registered_source_result(candidate, as_of_date="2026-09-27", company_wiki_catalog_config=config)
    assert prepared["source"]["reuse_receipt"]["download_calls"] == 0
    assert prepared["source"]["reuse_receipt"]["outcome"] == "reused_existing"
    assert prepared["filing_fetch"] is None


def test_locale_manifest_and_preserved_declared_language_match_worker_family():
    request, body, raw = _valid()
    bundle, receipt = json.loads(body), json.loads(raw)
    bundle["source_metadata"]["declared_language"] = "en-US"
    receipt["manifest"]["language"] = "en-US"
    body, raw = _resign(request, bundle, receipt)
    value = validate_narrative_response(request, body, raw).to_dict()
    assert value["source_metadata"]["language"] == "en"
    assert value["source_metadata"]["declared_language"] == "en-US"
    assert value["manifest"]["language"] == "en-US"
    receipt["manifest"]["language"] = "zh-CN"
    with pytest.raises(NarrativeTransportError):
        validate_narrative_response(request, body, canonical_bytes(receipt) + b"\n")


@pytest.mark.parametrize("reason,path", [("exact_requires_fiscal_year", "fiscal_year"),
    ("latest_forbids_fiscal_year", "fiscal_year"), ("latest_reuse_requires_acquisition_limits", "acquisition_limits"),
    ("acquisition_limits_invalid", "acquisition_limits.max_cost_usd")])
def test_typed_request_sibling_crosses_both_rf_error_envelopes(reason, path, capsys):
    import filing_fetch_client as client
    import source_preparation as prep
    diagnostic = {"schema_version": "filing-request-diagnostic/1", "reason": reason, "field_path": path}
    cause = {"schema_version": "filing-upstream-cause/1", "operation": "resolve", "code": "unknown",
             "provider_started": False, "usage_complete": None, "retry_scope": "none"}
    exc = client._ClientError("request refused", upstream_cause=cause, request_diagnostic=diagnostic)
    client._emit_error("request_error", str(exc), upstream_cause=exc.upstream_cause, request_diagnostic=exc.request_diagnostic)
    emitted = json.loads(capsys.readouterr().err)
    assert emitted["request_diagnostic"] == diagnostic and emitted["upstream_cause"] == cause
    preparation = prep.FilingSourcePreparationError("request refused", **failure_observation(emitted))
    assert preparation.request_diagnostic == diagnostic
    assert preparation.upstream_cause["provider_started"] is False
    assert preparation.upstream_cause["usage_complete"] is None
