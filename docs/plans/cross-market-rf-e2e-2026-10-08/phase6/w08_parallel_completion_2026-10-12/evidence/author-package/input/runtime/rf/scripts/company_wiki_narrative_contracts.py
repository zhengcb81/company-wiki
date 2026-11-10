"""RF-owned wire contract for CWP's bounded, source-oriented narrative export.

No CWP Python implementation is imported. Data is checked against the published
reference, receipt, bundle and EvidenceSpan formats before RF may use a snippet.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import hashlib
import json
import re
from urllib.parse import quote
from typing import Any

BODY_LIMIT = 1_310_720
RECEIPT_LIMIT = 16 * 1024
REQUEST_LIMIT = 16 * 1024
SOURCE_PREFIX = "urn:company-wiki:source:sha256:"
SPAN_PREFIX = "urn:company-wiki:evidence-span:sha256:"
EXPECTED_FIELDS = {"canonical_entity_id", "market", "security_id", "document_kind",
                   "fiscal_year", "fiscal_period"}
PROJECTED_REF_FIELDS = {"schema_version", "artifact_version_id", "artifact_sha256", "byte_size", "generation_sha256", "subject_ref"}
SUBJECT_REF_FIELDS = {"schema_version", "kind", "item_key", "subject_sha256"}
PROJECTION_PREFIX = "urn:company-wiki:source-projection:sha256:"
ISSUER_FIELDS = {"market", "security_id", "provider_company_id", "provider_activity_company_id", "canonical_name", "entity_name"}
PROJECTED_RECEIPT_FIELDS = {"schema_version", "status", "narrative_ref", "as_of_date", "observed_at", "locator_count", "parent_count", "lineage_sha256", "selection_status", "quality_status", "replay_status"}
REF_FIELDS = {"schema_version", "artifact_version_id", "artifact_sha256", "byte_size", "source_ref"}
SOURCE_FIELDS = {"schema_version", "document_id", "source_id", "content_sha256", "byte_size", "mime_type"}
RECEIPT_FIELDS = {"schema_version", "status", "narrative_ref", "as_of_date", "manifest",
                  "source_read_policy_sha256", "read_at", "locator_count", "selection_status",
                  "quality_status", "replay_status"}
MANIFEST_FIELDS = {"document_id", "source_id", "content_sha256", "byte_size", "mime_type",
                   "title", "document_kind", "published_date", "source_url", "retrieved_at",
                   "collector_name", "collector_version", "canonical_entity_id", "display_name",
                   "market", "security_id", "fiscal_year", "fiscal_period", "period_end",
                   "form_type", "provider", "provider_document_id", "language"}
BUNDLE_FIELDS = {"schema_version", "source_ref", "expected_read_policy_sha256",
                 "source_metadata", "quality_status", "selection", "evidence_spans",
                 "summary", "prompt_review", "transcript_lineage", "transcript_byte_bindings",
                 "versions", "replay"}
SPAN_FIELDS = {"schema_version", "span_id", "source_id", "locator", "coordinates", "raw_text",
               "structured_value", "parser_name", "parser_version", "output_sha256",
               "parse_status", "quality_flags"}
COORD_FIELDS = {"page_number", "paragraph_index", "table_index", "row_index",
                "column_index", "char_start", "char_end"}
SELECTION_FIELDS = {"status", "coverage_complete", "source_units", "candidate_count",
                    "selected_count", "omitted_candidate_count", "dropped_financial_count",
                    "pages_total", "pages_read", "lines_total", "tables_total", "tables_scanned"}
QUALITY = {"verified", "needs_review", "skipped_no_narrative"}
SELECTION = {"selected", "partial", "needs_review", "blocked", "skipped_no_narrative"}
# Native containers replay through page/paragraph locators; ET text/JSON
# separately binds extracted lines to original byte ranges.
RICH_DOCUMENT_MIMES = frozenset({
    "application/pdf", "text/html", "application/xhtml+xml",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
})
_PATH_KEYS = {"path", "root", "object_key", "absolute_path", "local_path", "raw_path",
              "root_path", "wiki_root", "catalog_path", "physical_path"}
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")


class NarrativeTransportError(RuntimeError):
    """A bounded diagnostic; never include raw text, secrets or physical paths."""

    def __init__(self, status: str, reason: str):
        self.status, self.reason = status, reason
        super().__init__(f"{status}: {reason}")


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise NarrativeTransportError("blocked", reason)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _pathless(value: Any) -> None:
    if isinstance(value, dict):
        _require(not (_PATH_KEYS & set(value)), "physical_location_forbidden")
        for child in value.values():
            _pathless(child)
    elif isinstance(value, list):
        for child in value:
            _pathless(child)


def _exact(value: Any, fields: set[str], reason: str) -> dict:
    _require(isinstance(value, dict) and set(value) == fields, reason)
    return value


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _sha(value: Any) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _integer(value: Any, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def _pairs(pairs: list[tuple[str, Any]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        _require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def _nonfinite(_value: str) -> None:
    raise NarrativeTransportError("blocked", "nonfinite_json")


def decode_object(raw: bytes, *, limit: int, one_line: bool = False) -> dict:
    _require(isinstance(raw, bytes) and len(raw) <= limit, "wire_size_limit")
    try:
        text = raw.decode("utf-8", errors="strict")
        if one_line:
            _require(text.endswith("\n") and len(text.splitlines()) == 1, "receipt_line_count")
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_nonfinite)
        _require(isinstance(value, dict), "wire_object_required")
        _pathless(value)
        return value
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise NarrativeTransportError("blocked", "invalid_json") from exc


def _date(value: Any) -> date:
    _require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None,
             "invalid_as_of_date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise NarrativeTransportError("blocked", "invalid_as_of_date") from exc


def _utc(value: Any) -> datetime:
    _require(_text(value), "invalid_capture_time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NarrativeTransportError("blocked", "invalid_capture_time") from exc
    _require(parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0), "invalid_capture_time")
    return parsed


def validate_source_ref(value: Any) -> dict:
    ref = _exact(value, SOURCE_FIELDS, "invalid_source_reference")
    _require(ref["schema_version"] == "2.0", "unsupported_source_reference")
    _require(all(_text(ref[key]) for key in ("document_id", "source_id", "mime_type")),
             "invalid_source_reference")
    _require(_sha(ref["content_sha256"]) and ref["source_id"] == SOURCE_PREFIX + ref["content_sha256"],
             "source_hash_binding")
    _require(_integer(ref["byte_size"], 1), "invalid_source_reference")
    return ref


def validate_subject_ref(value: Any) -> dict:
    ref = _exact(value, SUBJECT_REF_FIELDS, "invalid_subject_reference")
    _require(ref["schema_version"] == "narrative-subject-ref/1" and
             ref["kind"] == "official_json" and _sha(ref["subject_sha256"]) and
             ref["item_key"] == PROJECTION_PREFIX + ref["subject_sha256"], "subject_hash_binding")
    return ref


def validate_narrative_ref(value: Any) -> dict:
    projected = isinstance(value, dict) and value.get("schema_version") == "narrative-ref/3"
    ref = _exact(value, PROJECTED_REF_FIELDS if projected else REF_FIELDS, "invalid_narrative_reference")
    _require(ref["schema_version"] == ("narrative-ref/3" if projected else "narrative-ref/1"),
             "unsupported_narrative_reference")
    _require(isinstance(ref["artifact_version_id"], str) and
             _ID.fullmatch(ref["artifact_version_id"]) is not None, "invalid_artifact_id")
    _require(_sha(ref["artifact_sha256"]), "invalid_artifact_sha")
    _require(_integer(ref["byte_size"], 1) and ref["byte_size"] <= BODY_LIMIT, "invalid_artifact_size")
    if projected:
        validate_subject_ref(ref["subject_ref"])
        _require(_sha(ref["generation_sha256"]), "invalid_generation_sha")
    else:
        validate_source_ref(ref["source_ref"])
    _pathless(ref)
    return ref


def _constraints(value: Any) -> dict:
    fields = _exact(value, EXPECTED_FIELDS, "invalid_source_constraints")
    for key, constraint in fields.items():
        if constraint is None:
            continue
        if key == "fiscal_year":
            _require(_integer(constraint, 1900) and constraint <= 9999, "invalid_fiscal_year")
        else:
            _require(_text(constraint) and len(constraint) <= 256, "invalid_source_constraint")
    return fields


def _issuer_constraint(key: str, value: Any) -> None:
    if key in {"provider_company_id", "provider_activity_company_id"} and type(value) is int:
        return
    _require(_text(value) and len(value) <= 256, "invalid_issuer_constraint")


def _issuer_constraints(value: Any) -> dict | None:
    if value is None:
        return None
    _require(isinstance(value, dict) and bool(value) and set(value) <= ISSUER_FIELDS,
             "invalid_issuer_constraints")
    for key, constraint in value.items():
        _issuer_constraint(key, constraint)
    return value


def validate_narrative_request(value: Any) -> dict:
    projected = isinstance(value, dict) and value.get("schema_version") == "narrative-read-request/3"
    constraint_key = "expected_issuer" if projected else "expected_source"
    request = _exact(value, {"schema_version", "narrative_ref", "as_of_date", constraint_key},
                     "invalid_read_request")
    _require(request["schema_version"] == ("narrative-read-request/3" if projected else "narrative-read-request/1"),
             "unsupported_read_request")
    ref = validate_narrative_ref(request["narrative_ref"])
    _require(ref["schema_version"] == ("narrative-ref/3" if projected else "narrative-ref/1"), "request_reference_kind_mismatch")
    if request["as_of_date"] is not None:
        _date(request["as_of_date"])
    (_issuer_constraints if projected else _constraints)(request[constraint_key])
    _pathless(request)
    _require(len(canonical_bytes(request)) + 1 <= REQUEST_LIMIT, "request_size_limit")
    return deepcopy(request)


def validate_reference_request(value: Any) -> dict:
    projected = isinstance(value, dict) and value.get("schema_version") == "narrative-reference-request/3"
    fields = {"schema_version", "subject_ref", "generation_sha256"} if projected else {"schema_version", "source_ref"}
    request = _exact(value, fields, "invalid_reference_request")
    _require(request["schema_version"] == ("narrative-reference-request/3" if projected else "narrative-reference-request/1"),
             "unsupported_reference_request")
    if projected:
        validate_subject_ref(request["subject_ref"])
        _require(_sha(request["generation_sha256"]), "invalid_generation_sha")
    else:
        validate_source_ref(request["source_ref"])
    _pathless(request)
    _require(len(canonical_bytes(request)) + 1 <= REQUEST_LIMIT, "request_size_limit")
    return deepcopy(request)


def _manifest(receipt: dict, request: dict) -> dict:
    manifest = _exact(receipt["manifest"], MANIFEST_FIELDS, "invalid_source_manifest")
    source = request["narrative_ref"]["source_ref"]
    for key in SOURCE_FIELDS - {"schema_version"}:
        _require(type(manifest[key]) is type(source[key]) and manifest[key] == source[key],
                 "manifest_source_mismatch")
    for key, value in request["expected_source"].items():
        if value is not None:
            _require(type(manifest[key]) is type(value) and manifest[key] == value, "manifest_request_mismatch")
    if request["as_of_date"] is not None:
        cutoff = _date(request["as_of_date"])
        _require(manifest["published_date"] is not None, "source_publication_unknown")
        _require(_date(manifest["published_date"]) <= cutoff, "source_after_as_of")
    elif manifest["published_date"] is not None:
        _date(manifest["published_date"])  # Current mode preserves typed metadata.
    if manifest["retrieved_at"] is not None:
        _utc(manifest["retrieved_at"])  # Unknown collection time stays unknown.
    return manifest


def _receipt(receipt: dict, request: dict) -> dict:
    _exact(receipt, RECEIPT_FIELDS, "invalid_read_receipt")
    _require(receipt["schema_version"] == "narrative-read-receipt/1", "unsupported_read_receipt")
    _require(receipt["status"] == "ok" and receipt["replay_status"] == "verified", "unverified_read_receipt")
    validate_narrative_ref(receipt["narrative_ref"])
    _require(receipt["narrative_ref"] == request["narrative_ref"] and
             receipt["as_of_date"] == request["as_of_date"], "receipt_request_mismatch")
    _require(_sha(receipt["source_read_policy_sha256"]), "invalid_read_policy")
    _utc(receipt["read_at"])
    _require(_integer(receipt["locator_count"]), "invalid_locator_count")
    return _manifest(receipt, request)


def _coordinate_shape(value: Any) -> dict:
    coordinates = _exact(value, COORD_FIELDS, "invalid_coordinates")
    for key, number in coordinates.items():
        _require(number is None or _integer(number, 1 if key == "page_number" else 0), "invalid_coordinates")
    _require(any(value is not None for value in coordinates.values()), "invalid_coordinates")
    start, end = coordinates["char_start"], coordinates["char_end"]
    _require((start is None) == (end is None), "invalid_coordinates")
    if start is not None:
        _require(end > start, "invalid_coordinates")
    _coordinate_relations(coordinates)
    return coordinates


def _coordinate_relations(coordinates: dict) -> None:
    _require(not (coordinates["paragraph_index"] is not None and coordinates["table_index"] is not None),
             "invalid_coordinates")
    _require(coordinates["table_index"] is not None or (
        coordinates["row_index"] is None and coordinates["column_index"] is None), "invalid_coordinates")


def _coordinates(value: Any) -> str:
    coordinates = _coordinate_shape(value)
    parts = ["loc:v1"]
    for label, key in (("page", "page_number"), ("paragraph", "paragraph_index"),
                       ("table", "table_index"), ("row", "row_index"), ("column", "column_index")):
        if coordinates[key] is not None:
            parts.append(f"{label}:{coordinates[key]}")
    if coordinates["char_start"] is not None:
        parts.append(f"chars:{coordinates['char_start']}-{coordinates['char_end']}")
    return "/".join(parts)


def _span_core(value: Any) -> dict:
    span = _exact(value, SPAN_FIELDS, "invalid_evidence_span")
    _require(span["schema_version"] == "1.0.0", "unsupported_evidence_span")
    locator = _coordinates(span["coordinates"])
    _require(span["locator"] == locator, "span_locator_mismatch")
    _require(span["raw_text"] is None or isinstance(span["raw_text"], str), "invalid_span_text")
    output_sha = hashlib.sha256(canonical_bytes({
        "raw_text": span["raw_text"], "structured_value": span["structured_value"],
    })).hexdigest()
    _require(span["output_sha256"] == output_sha, "span_output_hash_mismatch")
    span_sha = hashlib.sha256(canonical_bytes({
        "source_id": span["source_id"], "locator": locator, "output_sha256": output_sha,
    })).hexdigest()
    _require(span["span_id"] == SPAN_PREFIX + span_sha, "span_identity_mismatch")
    _span_quality(span)
    return span


def _span(value: Any, source: dict) -> dict:
    span = _span_core(value)
    _require(span["source_id"] == source["source_id"], "span_source_mismatch")
    return span


def _span_quality(span: dict) -> None:
    flags = span["quality_flags"]
    _require(isinstance(flags, list) and all(_text(flag) for flag in flags)
             and len(flags) == len(set(flags)), "invalid_span_quality")
    _require(span["parse_status"] in {"parsed", "partial", "failed", "quarantined"}, "invalid_span_quality")
    _require(_text(span["parser_name"]) and _text(span["parser_version"]), "invalid_span_parser")
    if span["parse_status"] == "partial":
        _require(bool(flags), "invalid_span_quality")


def _selection(value: Any, span_count: int) -> dict:
    selected = _exact(value, SELECTION_FIELDS, "invalid_selection")
    _require(selected["status"] in SELECTION and type(selected["coverage_complete"]) is bool,
             "invalid_selection")
    _require(all(_integer(selected[key]) for key in SELECTION_FIELDS - {"status", "coverage_complete"}),
             "invalid_selection_count")
    _require(selected["selected_count"] == span_count, "selection_count_mismatch")
    _require(selected["pages_read"] <= selected["pages_total"] and
             selected["tables_scanned"] <= selected["tables_total"], "invalid_selection_coverage")
    return selected


def _claim(value: Any, spans: dict[str, dict]) -> dict:
    claim = _exact(value, {"claim_id", "text", "evidence_ids", "claim_type", "modality", "needs_review"},
                   "invalid_summary_claim")
    _require(_text(claim["claim_id"]) and _text(claim["text"]), "invalid_summary_claim")
    ids = claim["evidence_ids"]
    _require(isinstance(ids, list) and bool(ids) and all(isinstance(key, str) and key in spans for key in ids)
             and len(ids) == len(set(ids)), "unbound_summary_citation")
    _require(type(claim["needs_review"]) is bool, "invalid_summary_claim")
    _require(claim["claim_type"] in {"company_statement", "analyst_question", "editorial", "uncertain"},
             "invalid_claim_type")
    _require(claim["modality"] in {"actual", "planned", "forecast", "question", "negation", "uncertain"},
             "invalid_claim_modality")
    _claim_roles(claim, spans)
    return claim


def _claim_roles(claim: dict, spans: dict[str, dict]) -> None:
    roles = {spans[key]["structured_value"].get("source_role")
             for key in claim["evidence_ids"] if isinstance(spans[key]["structured_value"], dict)}
    if claim["claim_type"] == "analyst_question":
        _require(bool(roles) and roles <= {"analyst", "investor_question"} and claim["modality"] == "question",
                 "claim_role_mismatch")
    elif claim["claim_type"] == "company_statement":
        _require(bool(roles) and roles <= {"company_filing", "management"}, "claim_role_mismatch")


def _summary(value: Any, source: dict, spans: dict[str, dict], language: str, skipped: bool) -> dict:
    summary = _exact(value, {"status", "translate", "draft", "model"}, "invalid_summary")
    _require(summary["translate"] is False, "translated_summary_forbidden")
    if skipped:
        _require(summary["status"] == "summary_not_needed" and
                 summary["draft"] is None and summary["model"] is None, "invalid_skip_summary")
        return summary
    _require(summary["status"] == "completed", "invalid_summary_status")
    _summary_draft(summary["draft"], source, spans, language)
    _summary_model(summary["model"])
    return summary


def _summary_draft(value: Any, source: dict, spans: dict[str, dict], language: str) -> None:
    draft = _exact(value, {"source_id", "source_sha256", "language", "claims", "status"},
                   "invalid_summary_draft")
    _require(draft["source_id"] == source["source_id"] and draft["source_sha256"] == source["content_sha256"]
             and draft["language"] == language, "summary_source_mismatch")
    _require(draft["status"] in {"draft", "needs_review"}, "invalid_summary_status")
    _require(isinstance(draft["claims"], list) and bool(draft["claims"]), "invalid_summary_claims")
    claims = [_claim(claim, spans) for claim in draft["claims"]]
    _require(len({claim["claim_id"] for claim in claims}) == len(claims), "duplicate_summary_claim")


def _summary_model(value: Any) -> None:
    model = _exact(value, {"adapter_id", "model_id", "prompt_version", "response_sha256"},
                   "invalid_summary_model")
    _require(_sha(model["response_sha256"]), "invalid_summary_model")
    _require(all(_text(model[key]) for key in ("adapter_id", "model_id", "prompt_version")),
             "invalid_summary_model")


def _lineage(bundle: dict, source: dict, span_ids: set[str]) -> None:
    lineage = bundle["transcript_lineage"]
    bindings = bundle["transcript_byte_bindings"]
    _require(isinstance(bindings, list), "invalid_transcript_bindings")
    if lineage is None:
        _require(not bindings and source["mime_type"] in RICH_DOCUMENT_MIMES,
                 "missing_transcript_lineage")
        return
    _lineage_source(lineage, source)
    _require({binding.get("evidence_id") for binding in bindings if isinstance(binding, dict)} == span_ids
             and len(bindings) == len(span_ids), "incomplete_transcript_bindings")
    for binding in bindings:
        _byte_binding(binding, lineage, source)


def _lineage_source(lineage: Any, source: dict) -> None:
    lineage_fields = {"schema_version", "original_source_id", "original_sha256", "original_byte_size",
                      "original_mime_type", "text_sha256", "text_byte_size", "line_count", "extractor_version"}
    _exact(lineage, lineage_fields, "invalid_transcript_lineage")
    _require(lineage["schema_version"] == "transcript-material/2", "unsupported_transcript_lineage")
    for key, source_key in (("original_source_id", "source_id"), ("original_sha256", "content_sha256"),
                            ("original_byte_size", "byte_size"), ("original_mime_type", "mime_type")):
        _require(type(lineage[key]) is type(source[source_key]) and lineage[key] == source[source_key],
                 "lineage_source_mismatch")
    _require(_sha(lineage["text_sha256"]) and _integer(lineage["text_byte_size"]) and
             _integer(lineage["line_count"]), "invalid_transcript_lineage")


def _byte_binding(binding: Any, lineage: dict, source: dict) -> None:
    _exact(binding, {"evidence_id", "material_line_start", "material_line_end", "source_byte_ranges"},
           "invalid_transcript_binding")
    start, end = binding["material_line_start"], binding["material_line_end"]
    _require(_integer(start, 1) and _integer(end, start) and end <= lineage["line_count"],
             "invalid_transcript_binding")
    ranges = binding["source_byte_ranges"]
    _require(isinstance(ranges, list) and bool(ranges), "invalid_transcript_binding")
    for part in ranges:
        _exact(part, {"start", "end"}, "invalid_transcript_binding")
        _require(_integer(part["start"]) and _integer(part["end"], part["start"] + 1)
                 and part["end"] <= source["byte_size"], "invalid_transcript_binding")


def _diagnostics(bundle: dict, source_sha256: str | None = None) -> None:
    review = _exact(bundle["prompt_review"], {"status", "source_sha256", "evidence_sha256", "policy_hash",
                                            "reviewed_at"}, "invalid_prompt_diagnostic")
    _require(review["status"] in {"not_detected", "detected_and_ignored", "not_reviewed"},
             "invalid_prompt_diagnostic")
    if review["source_sha256"] is not None:
        _require(review["source_sha256"] == (source_sha256 or bundle["source_ref"]["content_sha256"]), "prompt_source_mismatch")
    versions = _exact(bundle["versions"], {"parser", "selector", "material", "model", "prompt",
                                         "bundle_producer"}, "invalid_bundle_versions")
    _require(all(_text(versions[key]) for key in ("parser", "selector", "bundle_producer")),
             "invalid_bundle_versions")


def _bundle(body: bytes, request: dict, receipt: dict, manifest: dict) -> dict:
    ref = request["narrative_ref"]
    _require(len(body) == ref["byte_size"] and hashlib.sha256(body).hexdigest() == ref["artifact_sha256"],
             "artifact_bytes_mismatch")
    bundle = decode_object(body, limit=BODY_LIMIT)
    _require(canonical_bytes(bundle) == body, "noncanonical_bundle")
    _exact(bundle, BUNDLE_FIELDS, "invalid_narrative_bundle")
    _require(bundle["schema_version"] == "narrative-bundle/2.0", "unsupported_narrative_bundle")
    _require(bundle["source_ref"] == ref["source_ref"] and _sha(bundle["expected_read_policy_sha256"]),
             "bundle_source_mismatch")
    _bundle_contents(bundle, receipt, manifest)
    return bundle


def _bundle_contents(bundle: dict, receipt: dict, manifest: dict) -> None:
    metadata = _bundle_metadata(bundle, manifest)
    spans = _bundle_spans(bundle)
    by_id = {span["span_id"]: span for span in spans}
    selection = _selection(bundle["selection"], len(spans))
    _bundle_quality(bundle, receipt, selection, len(spans))
    skipped = selection["status"] == "skipped_no_narrative"
    _summary(bundle["summary"], bundle["source_ref"], by_id, metadata["language"], skipped)
    _replay(bundle["replay"], len(spans))
    _lineage(bundle, bundle["source_ref"], set(by_id))
    _diagnostics(bundle)


def _declared_language(metadata: dict) -> None:
    declared = metadata.get("declared_language")
    if declared is None:
        return
    _require(_text(declared), "invalid_declared_language")
    if declared in {"zh", "en", "mixed"}:
        family = declared
    else:
        family = _locale_family(declared)
    _require(family == metadata["language"], "declared_language_family_mismatch")


def _locale_family(declared: str) -> str:
    match = re.fullmatch(r"(zh|en)(?:-(Hans|Hant|Latn))?(?:-([a-z]{2}|[0-9]{3}))?", declared, re.IGNORECASE)
    _require(match is not None, "invalid_declared_language")
    family, script, _region = match.groups()
    family = family.lower()
    scripts = {"hans", "hant"} if family == "zh" else {"latn"}
    _require(not script or script.lower() in scripts, "invalid_declared_language")
    return family


def _metadata(value: Any, *, projected: bool = False) -> dict:
    fields = {"source_class", "title", "document_kind", "language"}
    if isinstance(value, dict) and "declared_language" in value:
        fields.add("declared_language")
    metadata = _exact(value, fields, "invalid_source_metadata")
    _require(metadata["title"] is None or _text(metadata["title"]), "invalid_source_metadata")
    _require(_text(metadata["document_kind"]), "invalid_source_metadata")
    classes = {"official_json"} if projected else {"filing", "transcript"}
    languages = {"en", "zh", "mixed", "unknown"} if projected else {"en", "zh", "mixed"}
    _require(isinstance(metadata["source_class"], str) and metadata["source_class"] in classes, "invalid_source_metadata")
    _require(isinstance(metadata["language"], str) and metadata["language"] in languages, "invalid_source_metadata")
    _declared_language(metadata)
    return metadata


def _manifest_language_family(value: Any) -> str:
    _require(_text(value), "invalid_manifest_language")
    return value if value in {"en", "zh", "mixed"} else _locale_family(value)


def _bundle_metadata(bundle: dict, manifest: dict) -> dict:
    metadata = _metadata(bundle["source_metadata"])
    _require(metadata["document_kind"] == manifest["document_kind"], "bundle_manifest_mismatch")
    if manifest["language"] is not None:
        _require(metadata["language"] == _manifest_language_family(manifest["language"]), "bundle_manifest_mismatch")
    return metadata


def _bundle_quality(bundle: dict, receipt: dict, selection: dict, count: int) -> None:
    _require(bundle["quality_status"] in QUALITY and bundle["quality_status"] == receipt["quality_status"],
             "quality_status_mismatch")
    _require(receipt["selection_status"] == selection["status"] and receipt["locator_count"] == count,
             "receipt_bundle_mismatch")
    skipped = selection["status"] == "skipped_no_narrative"
    _require(skipped == (bundle["quality_status"] == "skipped_no_narrative") and
             (not skipped or count == 0), "invalid_skip_bundle")


def _bundle_spans(bundle: dict) -> list[dict]:
    _require(isinstance(bundle["evidence_spans"], list), "invalid_evidence_spans")
    spans = [_span(span, bundle["source_ref"]) for span in bundle["evidence_spans"]]
    by_id = {span["span_id"]: span for span in spans}
    _require(len(by_id) == len(spans), "duplicate_evidence")
    return spans


def _replay(value: Any, count: int) -> None:
    replay = _exact(value, {"required", "locator_count"}, "invalid_replay")
    _require(replay["required"] is True and type(replay["locator_count"]) is int
             and replay["locator_count"] == count, "invalid_replay")


@dataclass(frozen=True)
class NarrativeContext:
    """Validated source excerpts and draft claims; never a calculated forecast."""
    value: dict

    def to_dict(self) -> dict:
        return deepcopy(self.value)


def _projection_parents(subject: dict, receipt: dict) -> None:
    parents = subject["parent_source_refs"]
    _require(isinstance(parents, list) and bool(parents), "invalid_parent_references")
    for parent in parents:
        validate_source_ref(parent)
    _require(len({parent["source_id"] for parent in parents}) == len(parents), "duplicate_parent_reference")
    _require(_integer(receipt["parent_count"], 1) and receipt["parent_count"] == len(parents), "projection_parent_count_mismatch")
    _require(_sha(receipt["lineage_sha256"]) and receipt["lineage_sha256"] ==
             hashlib.sha256(canonical_bytes(subject)).hexdigest(), "projection_lineage_mismatch")


def _projection_constraints(subject: dict, request: dict) -> None:
    _date(subject["as_of_date"])
    _require(request["as_of_date"] is None or subject["as_of_date"] == request["as_of_date"],
             "projection_as_of_mismatch")
    for key in ("issuer", "adapter", "coverage"):
        _require(isinstance(subject[key], dict), "invalid_subject_context")
    for key, expected in (request["expected_issuer"] or {}).items():
        actual = subject["issuer"].get(key)
        _require(type(actual) is type(expected) and actual == expected, "projection_issuer_mismatch")


def _projected_subject(value: Any, request: dict, receipt: dict) -> dict:
    subject = _exact(value, {"kind", "item_key", "subject_sha256", "parent_source_refs",
                            "issuer", "as_of_date", "adapter", "coverage"}, "invalid_subject_binding")
    compact = {"schema_version": "narrative-subject-ref/1", **{key: subject[key]
               for key in ("kind", "item_key", "subject_sha256")}}
    _require(compact == request["narrative_ref"]["subject_ref"], "bundle_subject_mismatch")
    validate_subject_ref(compact)
    _projection_parents(subject, receipt)
    _projection_constraints(subject, request)
    return subject


def _span_parent(span: dict, binding: dict, subject: dict) -> dict:
    parent = next((item for item in subject["parent_source_refs"] if
                   item["source_id"] == span["source_id"] and
                   item["content_sha256"] == binding.get("parent_content_sha256")), None)
    _require(parent is not None, "projection_span_parent_mismatch")
    _require(binding.get("projection_id") == subject["item_key"], "projection_span_parent_mismatch")
    return parent


def _projection_pointer(binding: dict) -> str:
    pointer, record = binding.get("pointer"), binding.get("record_pointer")
    _require(_text(pointer) and _text(record), "invalid_projection_pointer")
    _require(record.startswith("/") and pointer.startswith(record + "/"), "invalid_projection_pointer")
    suffix = pointer[len(record) + 1:]
    _require(bool(suffix) and "/" not in suffix, "invalid_projection_pointer")
    _require(not re.search(r"~(?![01])", pointer), "invalid_projection_pointer")
    return pointer


def _projection_range(value: Any, parent: dict) -> list[int]:
    _require(isinstance(value, list) and len(value) == 2, "invalid_projection_byte_range")
    _require(_integer(value[0]) and _integer(value[1], value[0]), "invalid_projection_byte_range")
    _require(value[1] <= parent["byte_size"], "invalid_projection_byte_range")
    return value


def _projection_byte_binding(binding: dict, parent: dict) -> list[int]:
    token = _projection_range(binding.get("token_range"), parent)
    encoded = _projection_range(binding.get("encoded_body_range"), parent)
    _require(token[0] < token[1], "invalid_projection_byte_binding")
    _require(token[0] <= encoded[0] <= encoded[1] <= token[1], "invalid_projection_byte_binding")
    for key in ("encoded_token_sha256", "decoded_sha256"):
        _require(_sha(binding.get(key)), "invalid_projection_byte_binding")
    return token


def _projection_locator(binding: dict, pointer: str, token: list[int]) -> None:
    locator = binding.get("source_locator")
    prefix = "cwp-json-pointer/1|p=" + quote(pointer, safe="") + "|b=" + str(token[0]) + ":" + str(token[1]) + "|d=0:"
    _require(isinstance(locator, str) and locator.startswith(prefix), "projection_pointer_locator_mismatch")
    _require(re.fullmatch(r"[0-9]+\|x=json-string-decode/1", locator[len(prefix):]) is not None,
             "projection_pointer_locator_mismatch")


def _projected_span(value: Any, subject: dict) -> dict:
    """Each field retains its own parent and pointer; the first parent is no anchor."""
    span = _span_core(value)
    binding = span["structured_value"]
    _require(isinstance(binding, dict), "invalid_projection_span_binding")
    parent = _span_parent(span, binding, subject)
    pointer = _projection_pointer(binding)
    token = _projection_byte_binding(binding, parent)
    _projection_locator(binding, pointer, token)
    return span


def _projected_summary_draft(value: Any, subject: dict, spans: dict[str, dict], language: str) -> None:
    draft = _exact(value, {"subject_id", "subject_sha256", "language", "claims", "status"},
                   "invalid_subject_summary_draft")
    _require(draft["subject_id"] == subject["item_key"] and draft["subject_sha256"] == subject["subject_sha256"]
             and draft["language"] == language, "summary_subject_mismatch")
    _require(draft["status"] in {"draft", "needs_review"}, "invalid_summary_status")
    _require(isinstance(draft["claims"], list) and bool(draft["claims"]), "invalid_summary_claims")
    claims = [_claim(claim, spans) for claim in draft["claims"]]
    _require(len({claim["claim_id"] for claim in claims}) == len(claims), "duplicate_summary_claim")


def _projected_summary(value: Any, subject: dict, spans: dict[str, dict], language: str, skipped: bool) -> None:
    summary = _exact(value, {"status", "translate", "draft", "model"}, "invalid_summary")
    _require(summary["translate"] is False, "translated_summary_forbidden")
    if skipped:
        _require(summary["status"] == "summary_not_needed" and summary["draft"] is None and
                 summary["model"] is None, "invalid_skip_summary")
        return
    _require(summary["status"] == "completed", "invalid_summary_status")
    _projected_summary_draft(summary["draft"], subject, spans, language)
    _summary_model(summary["model"])


def _projected_receipt(receipt: dict, request: dict) -> None:
    _exact(receipt, PROJECTED_RECEIPT_FIELDS, "invalid_read_receipt")
    _require(receipt["schema_version"] == "narrative-read-receipt/3" and receipt["status"] == "ok" and
             receipt["replay_status"] == "verified", "unverified_read_receipt")
    validate_narrative_ref(receipt["narrative_ref"])
    _require(receipt["narrative_ref"] == request["narrative_ref"] and
             receipt["as_of_date"] == request["as_of_date"], "receipt_request_mismatch")
    _utc(receipt["observed_at"])
    _require(_integer(receipt["locator_count"]), "invalid_locator_count")


def _projection_bundle(body: bytes, ref: dict) -> dict:
    _require(len(body) == ref["byte_size"] and hashlib.sha256(body).hexdigest() == ref["artifact_sha256"],
             "artifact_bytes_mismatch")
    bundle = decode_object(body, limit=BODY_LIMIT)
    _require(canonical_bytes(bundle) == body, "noncanonical_bundle")
    fields = (BUNDLE_FIELDS - {"source_ref", "expected_read_policy_sha256", "transcript_lineage",
                             "transcript_byte_bindings"}) | {"subject_binding"}
    _exact(bundle, fields, "invalid_narrative_bundle")
    _require(bundle["schema_version"] == "narrative-bundle/3.0", "unsupported_narrative_bundle")
    return bundle


def _projection_spans(bundle: dict, subject: dict) -> tuple[list[dict], dict[str, dict]]:
    _require(isinstance(bundle["evidence_spans"], list), "invalid_evidence_spans")
    spans = [_projected_span(span, subject) for span in bundle["evidence_spans"]]
    by_id = {span["span_id"]: span for span in spans}
    _require(len(by_id) == len(spans), "duplicate_evidence")
    return spans, by_id


def _projected_response(request: dict, body: bytes, receipt: dict) -> NarrativeContext:
    _projected_receipt(receipt, request)
    ref = request["narrative_ref"]
    bundle = _projection_bundle(body, ref)
    subject = _projected_subject(bundle["subject_binding"], request, receipt)
    metadata = _metadata(bundle["source_metadata"], projected=True)
    spans, by_id = _projection_spans(bundle, subject)
    selection = _selection(bundle["selection"], len(spans))
    _require(not selection["coverage_complete"] or (subject["coverage"].get("pagination_complete") is True and
             subject["coverage"].get("page_envelope_complete") is True), "projection_coverage_mismatch")
    _bundle_quality(bundle, receipt, selection, len(spans))
    _projected_summary(bundle["summary"], subject, by_id, metadata["language"],
                       selection["status"] == "skipped_no_narrative")
    _replay(bundle["replay"], len(spans))
    _diagnostics(bundle, subject["parent_source_refs"][0]["content_sha256"])
    return NarrativeContext({"schema_version": "revenue-narrative-context/3", "narrative_ref": ref,
        "subject_binding": subject, "parent_source_refs": subject["parent_source_refs"],
        "as_of_date": request["as_of_date"], "source_metadata": metadata, "selection": selection,
        "quality_status": bundle["quality_status"], "evidence_spans": spans,
        "summary": bundle["summary"], "read_receipt": receipt})


def _validated_response(request: dict, body: bytes, receipt_bytes: bytes) -> NarrativeContext:
    request = validate_narrative_request(request)
    receipt = decode_object(receipt_bytes, limit=RECEIPT_LIMIT, one_line=True)
    if request["schema_version"] == "narrative-read-request/3":
        return _projected_response(request, body, receipt)
    manifest = _receipt(receipt, request)
    bundle = _bundle(body, request, receipt, manifest)
    return NarrativeContext({
        "schema_version": "revenue-narrative-context/1",
        "narrative_ref": request["narrative_ref"], "source_ref": bundle["source_ref"],
        "as_of_date": request["as_of_date"], "manifest": manifest,
        "source_metadata": bundle["source_metadata"], "selection": bundle["selection"],
        "quality_status": bundle["quality_status"], "evidence_spans": bundle["evidence_spans"],
        "summary": bundle["summary"], "read_receipt": receipt,
    })



def validate_narrative_response(request: dict, body: bytes, receipt_bytes: bytes) -> NarrativeContext:
    """Invalid JSON field types are a contract refusal, never a raw exception."""
    try:
        return _validated_response(request, body, receipt_bytes)
    except (TypeError, ValueError, RecursionError) as exc:
        raise NarrativeTransportError("blocked", "invalid_narrative_wire") from exc


def validate_reference_response(request: dict, body: bytes, receipt_bytes: bytes) -> dict:
    request = validate_reference_request(request)
    ref = validate_narrative_ref(decode_object(body, limit=REQUEST_LIMIT))
    receipt = decode_object(receipt_bytes, limit=RECEIPT_LIMIT, one_line=True)
    _exact(receipt, {"schema_version", "status", "narrative_ref"}, "invalid_reference_receipt")
    projected = request["schema_version"] == "narrative-reference-request/3"
    _require(receipt["schema_version"] == ("narrative-read-receipt/3" if projected else "narrative-read-receipt/1") and
             receipt["status"] == "metadata_only" and receipt["narrative_ref"] == ref,
             "invalid_reference_receipt")
    if projected:
        _require(ref["schema_version"] == "narrative-ref/3" and ref["subject_ref"] == request["subject_ref"] and
                 ref["generation_sha256"] == request["generation_sha256"], "reference_subject_mismatch")
    else:
        _require(ref["schema_version"] == "narrative-ref/1" and ref["source_ref"] == request["source_ref"],
                 "reference_source_mismatch")
    return deepcopy(ref)
