"""R6-RF-INPUT I3/I4: evidence-role binding with real input lineage.

``bind_parameter_evidence`` binds a parameter to checked evidence with an
explicit role (history / mechanism direction / numeric range / peer analogy /
counter comparison / conversion assumption). Direction is never a value, a
peer analogy never counts as company mechanism, and a NarrativeRef span is
only usable once it becomes a formal source+claim dependency of the
parameter — a file that merely exists is not consumption. The machine checks
here are structural; the economic semantics remain with MAIN's independent
review.
"""

from __future__ import annotations

import re
from typing import Any

from contracts.constants import (
    DIRECTIONAL_EVIDENCE_ROLES,
    GROWTH_DRIVER_EVIDENCE_ROLES,
)
from contracts.evidence import (
    ForecastInputError,
    build_host_receipt,
    canonical_sha256,
    require,
    text_sha256,
)
from contracts.source_clock import (
    SourceClockError, iso_date, qualify_source_information, utc_timestamp, validate_source_events,
)
from company_wiki_narrative_contracts import SPAN_PREFIX
import hashlib

VALID_SUPPORT_TYPES = {"exact_value", "rationale_support", "policy_support"}


def bind_parameter_evidence(
    parameter: dict[str, Any],
    *,
    evidence_bindings: list[dict[str, Any]],
    source: dict[str, Any] | None,
    verified_by: str,
    verified_date: str,
) -> dict[str, Any]:
    """Bind *parameter* to role-tagged evidence; returns the updated parameter,
    the emitted claims, any newly created narrative sources, and a lineage list."""
    require(isinstance(parameter, dict), "parameter must be an object")
    require(
        isinstance(verified_by, str) and verified_by.strip(), "verified_by is required"
    )
    require(
        isinstance(verified_date, str) and verified_date.strip(),
        "verified_date is required",
    )
    require(
        isinstance(evidence_bindings, list) and evidence_bindings,
        "evidence_bindings must be a non-empty list",
    )
    parameter_id = parameter.get("parameter_id")
    require(
        isinstance(parameter_id, str) and parameter_id.strip(),
        "parameter_id is required",
    )
    classic_capture = None
    if source is not None:
        classic_capture = _validated_capture(source)

    claims: list[dict[str, Any]] = []
    new_sources: list[dict[str, Any]] = []
    lineage: list[dict[str, Any]] = []
    roles: list[str] = []
    for position, binding in enumerate(evidence_bindings):
        require(isinstance(binding, dict), "evidence binding must be an object")
        role = binding.get("role")
        require(
            role in GROWTH_DRIVER_EVIDENCE_ROLES,
            f"unknown evidence role in binding {position}: {role}",
        )
        support_type = binding.get(
            "support_type", "exact_value" if role == "value_range" else "rationale_support"
        )
        require(
            support_type in VALID_SUPPORT_TYPES,
            f"invalid support_type in binding {position}: {support_type}",
        )
        if role == "recognition_policy":
            raise ForecastInputError(
                f"recognition_policy evidence does not support a forecast parameter: {parameter_id}"
            )
        if support_type == "policy_support":
            raise ForecastInputError(
                f"policy_support is reserved for recognition-policy claims: {parameter_id}"
            )
        if role == "counterevidence":
            raise ForecastInputError(
                f"counterevidence cannot be listed as parameter support: {parameter_id}; "
                "bind it to the growth-driver's contrary evidence node instead"
            )
        extracted_value = binding.get("extracted_value")
        has_value = extracted_value is not None
        if role in DIRECTIONAL_EVIDENCE_ROLES and has_value:
            raise ForecastInputError(
                f"directional evidence role {role} cannot carry a numeric value: {parameter_id}"
            )
        if role == "value_range":
            require(
                has_value and support_type == "exact_value",
                f"value_range evidence requires an exact numeric value: {parameter_id}",
            )
        inference_distance = binding.get("inference_distance")
        if role == "peer_analogy":
            require(
                inference_distance == "analogical",
                f"peer_analogy must use inference_distance analogical, not "
                f"{inference_distance}: {parameter_id}",
            )
        roles.append(role)

        narrative_context = binding.get("narrative_context")
        if narrative_context is not None:
            bound_source, capture = _bind_narrative_span(
                parameter_id, binding, narrative_context
            )
            new_sources.append(bound_source)
            excerpt = capture["excerpt"]
            locator = capture["locator"]
            content_sha = capture["content_sha256"]
            receipt_sha = capture["receipt_sha256"]
            source_label = bound_source["source_id"]
            lineage_entry: dict[str, Any] = {
                "binding": "narrative_span",
                "narrative_span_id": capture["span_id"],
                "narrative_artifact": capture["artifact_version_id"],
            }
        else:
            require(
                source is not None and classic_capture is not None,
                f"classic evidence binding {position} requires a source",
            )
            excerpt = binding.get("excerpt")
            require(
                isinstance(excerpt, str) and 10 <= len(excerpt.strip()) <= 500,
                f"binding {position} excerpt must contain 10-500 characters",
            )
            excerpt = excerpt.strip()
            locator = binding.get("locator")
            require(
                isinstance(locator, str) and locator.strip(),
                f"binding {position} locator is required",
            )
            content_sha = classic_capture["snapshot_sha256"]
            receipt_sha = classic_capture["receipt_sha256"]
            source_label = source["source_id"]
            lineage_entry = {"binding": "classic_excerpt"}
        claim_id = f"claim_{parameter_id}_{position}"
        claim: dict[str, Any] = {
            "claim_id": claim_id,
            "source_id": source_label,
            "target_type": "parameter",
            "target_id": parameter_id,
            "support_type": support_type,
            "evidence_role": role,
            "locator": locator,
            "excerpt": excerpt,
            "excerpt_sha256": text_sha256(excerpt),
            "content_sha256": content_sha,
            "capture_receipt_sha256": receipt_sha,
            "verification_status": "opened_and_checked",
            "verified_by": verified_by,
            "verified_date": verified_date,
        }
        if has_value:
            claim["extracted_value"] = extracted_value
            for field in ("unit", "period"):
                require(
                    isinstance(binding.get(field), str) and binding[field].strip(),
                    f"numeric evidence binding {position} requires {field}",
                )
                claim[field] = binding[field]
        claims.append(claim)
        lineage_entry.update({
            "role": role,
            "claim_id": claim_id,
            "source_id": source_label,
            "content_sha256": content_sha,
            "excerpt": excerpt,
            "excerpt_sha256": text_sha256(excerpt),
        })
        if inference_distance is not None:
            lineage_entry["inference_distance"] = inference_distance
        lineage.append(lineage_entry)

    # A historical base alone never proves a future assumption.
    require(
        any(role != "history_base" for role in roles),
        f"history_base evidence alone cannot support a forecast assumption: {parameter_id}",
    )

    updated = dict(parameter)
    updated["claim_ids"] = list(dict.fromkeys(
        list(parameter.get("claim_ids", [])) + [c["claim_id"] for c in claims]
    ))
    updated["source_ids"] = list(dict.fromkeys(
        list(parameter.get("source_ids", [])) + [c["source_id"] for c in claims]
    ))
    return {"parameter": updated, "claims": claims, "sources": new_sources, "lineage": lineage}


def _validated_capture(source: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(source, dict), "source must be an object")
    capture = source.get("capture")
    require(isinstance(capture, dict), "source capture is required for evidence binding")
    snapshot = capture.get("snapshot_sha256")
    require(
        isinstance(snapshot, str) and re.fullmatch(r"[0-9a-f]{64}", snapshot) is not None,
        "capture snapshot_sha256 must be lowercase SHA-256",
    )
    payload = {k: v for k, v in capture.items() if k != "receipt_sha256"}
    require(
        capture.get("receipt_sha256") == canonical_sha256(payload),
        "capture receipt hash mismatch: cannot bind evidence to an unverified capture",
    )
    return {"snapshot_sha256": snapshot, "receipt_sha256": capture["receipt_sha256"]}


def _canonical_bytes(value: Any) -> bytes:
    import json
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _bind_narrative_span(
    parameter_id: str, binding: dict[str, Any], context: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate a NarrativeRef span against the published wire contract and
    derive a formal revenue source + capture from it."""
    require(isinstance(context, dict), "narrative_context must be an object")
    spans = context.get("evidence_spans")
    require(
        isinstance(spans, list) and spans, "narrative_context has no evidence spans"
    )
    span_id = binding.get("span_id")
    span = next((s for s in spans if s.get("span_id") == span_id), None)
    require(
        span is not None,
        f"span {span_id} is not part of the validated narrative context for {parameter_id}",
    )
    raw_text = span.get("raw_text")
    structured = span.get("structured_value")
    require(
        isinstance(raw_text, str) and 10 <= len(raw_text.strip()) <= 500,
        "narrative span text must contain 10-500 characters",
    )
    output_sha = hashlib.sha256(
        _canonical_bytes({"raw_text": raw_text, "structured_value": structured})
    ).hexdigest()
    require(
        output_sha == span.get("output_sha256"),
        "span_text_hash_mismatch: the excerpt no longer matches the captured span",
    )
    span_sha = hashlib.sha256(_canonical_bytes({
        "source_id": span["source_id"], "locator": span["locator"],
        "output_sha256": output_sha,
    })).hexdigest()
    require(
        span_id == SPAN_PREFIX + span_sha,
        "span_identity_mismatch: span id does not bind its source, locator and text",
    )

    receipt = context.get("read_receipt")
    manifest = context.get("manifest")
    source_ref = context.get("source_ref")
    narrative_ref = context.get("narrative_ref")
    require(isinstance(receipt, dict) and isinstance(manifest, dict),
            "narrative_context is missing its read receipt or manifest")
    require(isinstance(source_ref, dict) and isinstance(narrative_ref, dict),
            "narrative_context is missing its source or narrative reference")
    content_sha256 = source_ref.get("content_sha256")
    require(
        manifest.get("content_sha256") == content_sha256,
        "narrative manifest/source content hash mismatch",
    )
    published_date = manifest.get("published_date")
    read_at = receipt.get("read_at")
    try:
        information = qualify_source_information(source_sha256=content_sha256,
            published_date=published_date, as_of=iso_date(receipt.get("as_of_date"), "narrative as_of_date"))
        captured_date = utc_timestamp(read_at, "narrative read_at").date().isoformat()
        validate_source_events(eligibility=information, current_read_at=read_at,
                               capture_date=captured_date)
    except SourceClockError as exc:
        raise ForecastInputError(str(exc)) from exc
    source_label = binding.get("source_id") or "narrative_transcript"
    require(
        isinstance(source_label, str) and source_label.strip(),
        "narrative source label must be a non-empty string",
    )
    artifact_id = narrative_ref.get("artifact_version_id", "narrative")
    capture_payload = {
        "capture_schema_version": "1.0",
        "capture_method": "structured_connector",
        "tool_name": "company-wiki-narrative-reader",
        "tool_call_id": artifact_id,
        "captured_date": captured_date,
        "snapshot_sha256": content_sha256,
        "content_treatment": "untrusted_data_only",
        "prompt_injection_status": "not_detected",
        "host_receipt": build_host_receipt(
            issuer="company-wiki",
            environment="production",
            tool_name="company-wiki-narrative-reader",
            action="narrative_read",
            event_sha256=hashlib.sha256(artifact_id.encode("utf-8")).hexdigest(),
            timestamp=read_at,
        ),
    }
    capture = dict(capture_payload)
    capture["receipt_sha256"] = canonical_sha256(capture_payload)
    bound_source = {
        "source_id": source_label,
        "source_type": "earnings_transcript",
        "title": manifest.get("title") or "Narrative source",
        "publisher": manifest.get("collector_name") or "company-wiki",
        "url": manifest.get("source_url"),
        "published_date": published_date,
        "accessed_date": captured_date,
        "page_or_section": span["locator"],
        "capture": capture,
    }
    details = {
        "excerpt": raw_text.strip(),
        "locator": span["locator"],
        "content_sha256": content_sha256,
        "receipt_sha256": capture["receipt_sha256"],
        "span_id": span_id,
        "artifact_version_id": narrative_ref.get("artifact_version_id"),
    }
    return bound_source, details
