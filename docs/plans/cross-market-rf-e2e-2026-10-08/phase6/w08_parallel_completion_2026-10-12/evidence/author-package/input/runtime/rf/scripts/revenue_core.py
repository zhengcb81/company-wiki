"""Core validation and calculation primitives for revenue-only forecasts."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
from pathlib import Path
from typing import Any

from model_registry import (  # noqa: E402  re-export
    MODEL_RATIO_DRIVERS as REGISTERED_MODEL_RATIO_DRIVERS,
    MODEL_SPECS as REGISTERED_MODEL_SPECS,
    ModelRegistryError,
    calculate_registered_model,
)
from contracts.evidence import (  # noqa: E402, F811  re-export
    Collector,
    ForecastInputError,
    MultiValidationError,
    build_host_receipt,  # noqa: F401  re-export for consumers
    canonical_sha256,
    collect_mode,
    finite_number,
    parse_iso_date,
    period_year,
    require,
    text_sha256,
    valid_source_url,
    validate_claim_ids,
    validate_source_capture,
)

from revenue_constraints import (  # noqa: E402  re-export
    RevenueConstraintError,
    apply_revenue_constraints,
    constraint_parameter_ids,
    validate_revenue_constraints,
)


from contracts.constants import SKILL_VERSION
# Compatibility name retained in serialized forecasts and snapshots.
ENGINE_VERSION = SKILL_VERSION

MODEL_SPECS = REGISTERED_MODEL_SPECS
MODEL_RATIO_DRIVERS = REGISTERED_MODEL_RATIO_DRIVERS



def _build_forecast_draft(data: dict[str, Any]) -> dict[str, Any]:
    """Compute the revenue forecast result without a publication receipt.

    The draft carries the execution receipt (what the runtime actually ran) but
    no ``publication_receipt`` and no ``result_sha256``. It is private and must
    never be handed to invest-* consumers; only ``run_forecast`` publishes it.
    """
    validated = validate_document(data)
    result = _run_forecast_core(data)
    result["schema_version"] = data["schema_version"]
    result["engine_version"] = ENGINE_VERSION
    result["research_coverage"] = {
        "dimensions": validated["research_coverage"]["records"],
        "counts": validated["research_coverage"]["counts"],
    }
    result["management_target_coverage"] = add_management_target_analysis(
        validated, result
    )
    add_scenario_analysis(data, validated, result)
    result["growth_driver_analysis"] = calculate_growth_driver_analysis(
        validated, result
    )
    sensitivities = calculate_sensitivities(data, result)
    result["sensitivities"] = sensitivities
    result["theme_analysis"] = calculate_theme_analysis(data, validated, result)
    result["confidence"] = calculate_confidence(data, validated, result, sensitivities)
    result["forecast_version"] = data.get(
        "forecast_version", f"{data['as_of_date']}-v1"
    )
    result["data_gaps"] = list(
        dict.fromkeys(
            [
                *data.get("data_gaps", []),
                *validated["research_coverage"]["gap_messages"],
                *validated["growth_driver_tree"]["gap_messages"],
                *validated["management_target_coverage"]["gap_messages"],
            ]
        )
    )
    # R1.1 (N-01): anchor and embed the input only after every engine step has
    # run — normalization mutates ``data``, so hashing earlier would bind the
    # artifact to a state that no longer exists at validation time (and lets a
    # forged artifact carry an input_document that hashes to nothing).
    result["input_sha256"] = canonical_sha256(data)
    result["input_document"] = copy.deepcopy(data)
    result["disconfirming_indicators"] = list(data.get("disconfirming_indicators", []))
    result["parameter_trace"] = data["parameters"]
    result["sources"] = list(validated["source_index"].values())
    result["evidence_claims"] = list(validated["claim_index"].values())
    result["historical_accuracy_records"] = copy.deepcopy(
        data.get("historical_accuracy_records", [])
    )
    result["workflow_compliance_receipt"] = build_workflow_compliance_receipt(
        result["input_sha256"],
        result["sources"],
        result["evidence_claims"],
        result["parameter_trace"],
        result["data_gaps"],
    )
    return result


def attestation_capability() -> bool:
    """True only when an attestation provider has PROVEN signing capability.

    (B1 / REM-01(b), I-08-A rule R-PROV-1.)  File existence is explicitly **not**
    capability: a plain ``.txt``, a bare ``.py`` with no protocol response, or
    ``sys.executable`` all resolve to existing files and all grant nothing.  The
    provider is named by ``REVENUE_ATTESTATION_PROVIDER`` (a command on PATH or
    an absolute path) and must complete a bounded one-shot handshake — one JSON
    request on stdin, exactly one JSON response on stdout — whose ``fingerprint``
    resolves in the trust domain and whose Ed25519 signature verifies over the
    echoed request.  Without that, the runtime can only publish ``"unattested"``
    formal artifacts.

    The provider file is never read, imported or executed as a script by the
    host; it is only spawned, and only when the path exists.  A module-level
    diagnostic is exposed by :func:`attestation_last_failure`.
    """
    global _ATTESTATION_LAST_FAILURE
    _ATTESTATION_LAST_FAILURE = None
    from revenue_publication import (
        publication_attestation_request,
    )

    request = publication_attestation_request(
        request_id=secrets.token_hex(32),
        payload_sha256=hashlib.sha256(b"capability-probe").hexdigest(),
    )
    response = _run_attestation_provider(request)
    if response is None:
        return False
    try:
        _validate_attestation_response(request, response)
    except ForecastInputError as exc:
        _record_attestation_failure(str(exc))
        return False
    return True


def attestation_last_failure() -> dict[str, str] | None:
    """Diagnostic for the most recent capability/signing failure, or None.

    Read-only reporting aid: it carries no authority and is never consulted by a
    validation path.  Its presence never decides a label by itself.
    """
    return dict(_ATTESTATION_LAST_FAILURE) if _ATTESTATION_LAST_FAILURE else None


# --- Provider handshake (B1 / REM-01) ---------------------------------------
# `T` (timeout) and `L` (stdout bound) are PARAMETERS, not frozen constants:
# I-08-A OPEN-D7 owns their values.  These two are this implementation's
# defaults, recorded in this attempt's binding.json and NOT claimed normative.
ATTESTATION_PROVIDER_TIMEOUT_SECONDS = 10.0
ATTESTATION_PROVIDER_MAX_STDOUT_BYTES = 65536

ATTESTATION_RESPONSE_FIELDS = (
    "attestation_response_schema_version",
    "request_id",
    "payload_sha256",
    "domain_separator",
    "issuer",
    "key_id",
    "fingerprint",
    "algorithm",
    "signature",
    "signed_at",
)

_ATTESTATION_LAST_FAILURE: dict[str, str] | None = None


def _record_attestation_failure(message: str) -> None:
    """Store ``{"code": <I-08-A code>, "message": <str>}`` for a coded message."""
    global _ATTESTATION_LAST_FAILURE
    failure = parse_attestation_failure(message)
    _ATTESTATION_LAST_FAILURE = failure


def parse_attestation_failure(message: str) -> dict[str, str]:
    """Split a coded rejection message into ``{"code", "message"}``."""
    match = re.match(r"^([a-z][a-z0-9_]*):\s*(.*)$", message, re.DOTALL)
    if match is None:
        return {"code": "provider_protocol_violation", "message": message}
    return {"code": match.group(1), "message": match.group(2).strip()}


def _run_attestation_provider(request: dict[str, Any]) -> dict[str, Any] | None:
    """One-shot provider handshake.  Returns the response object, or None.

    Every failure path records a coded diagnostic and returns None; nothing here
    raises, because a publication that cannot be signed must degrade to an honest
    ``unattested`` publication rather than fail the research result.
    """
    provider = os.environ.get("REVENUE_ATTESTATION_PROVIDER")
    if not provider:
        _record_attestation_failure(
            "provider_absent: REVENUE_ATTESTATION_PROVIDER is not set"
        )
        return None
    resolved = shutil.which(provider) or Path(provider).expanduser()
    if resolved is None or not os.path.isfile(resolved):
        _record_attestation_failure(
            f"provider_path_unopenable: {provider!r} does not resolve to a file"
        )
        return None
    try:
        completed = subprocess.run(
            [str(resolved)],
            input=json.dumps(request, sort_keys=True).encode("utf-8"),
            capture_output=True,
            timeout=ATTESTATION_PROVIDER_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        _record_attestation_failure(
            "provider_timeout: provider exceeded "
            f"{ATTESTATION_PROVIDER_TIMEOUT_SECONDS}s and was terminated"
        )
        return None
    except OSError as exc:
        _record_attestation_failure(f"provider_path_unopenable: {exc}")
        return None
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip()[:200]
        if "cannot sign" in detail or "no private key" in detail:
            _record_attestation_failure(
                f"provider_signing_unavailable: {detail or 'provider refused to sign'}"
            )
        else:
            _record_attestation_failure(
                f"provider_exit_nonzero: exit code {completed.returncode}; {detail}"
            )
        return None
    raw = completed.stdout
    if len(raw) > ATTESTATION_PROVIDER_MAX_STDOUT_BYTES:
        _record_attestation_failure(
            "provider_output_too_large: provider wrote "
            f"{len(raw)} bytes, above the {ATTESTATION_PROVIDER_MAX_STDOUT_BYTES} "
            "byte bound"
        )
        return None
    text = raw.decode("utf-8", "replace").strip()
    if not text:
        _record_attestation_failure(
            "provider_protocol_violation: provider wrote no response"
        )
        return None
    try:
        response = json.loads(text)
    except json.JSONDecodeError as exc:
        _record_attestation_failure(f"provider_invalid_json: {exc}")
        return None
    if not isinstance(response, dict):
        _record_attestation_failure(
            "provider_schema_mismatch: response must be a single JSON object"
        )
        return None
    _ATTESTATION_LAST_FAILURE = None
    return response


def _validate_attestation_response(
    request: dict[str, Any], response: dict[str, Any]
) -> dict[str, str]:
    """Validate one provider response; raise ``ForecastInputError`` if untrusted.

    Returns the identity fields on success so the caller can assemble the
    binding record.
    """
    from revenue_publication import (
        PUBLICATION_ATTESTATION_ALGORITHM,
        PUBLICATION_ATTESTATION_SCHEMA_VERSION,
        verify_ed25519_signature,
    )

    missing = [field for field in ATTESTATION_RESPONSE_FIELDS if field not in response]
    extra = sorted(set(response) - set(ATTESTATION_RESPONSE_FIELDS))
    if missing or extra:
        raise ForecastInputError(
            "provider_schema_mismatch: response field set mismatch "
            f"(missing={missing}, extra={extra})"
        )
    if (
        response["attestation_response_schema_version"]
        != PUBLICATION_ATTESTATION_SCHEMA_VERSION
    ):
        raise ForecastInputError(
            "provider_schema_mismatch: attestation_response_schema_version mismatch"
        )
    for field in ("request_id", "payload_sha256", "domain_separator"):
        if response[field] != request[field]:
            raise ForecastInputError(
                f"provider_binding_mismatch: response.{field} does not echo the request"
            )
    if response["algorithm"] != PUBLICATION_ATTESTATION_ALGORITHM:
        raise ForecastInputError(
            "provider_schema_mismatch: response.algorithm must be "
            f"{PUBLICATION_ATTESTATION_ALGORITHM!r}"
        )
    for field in ("issuer", "key_id"):
        if not isinstance(response[field], str) or not response[field].strip():
            raise ForecastInputError(
                f"provider_schema_mismatch: response.{field} must be a non-empty string"
            )
    if (
        not isinstance(response["fingerprint"], str)
        or re.fullmatch(r"[0-9a-f]{32}", response["fingerprint"]) is None
    ):
        raise ForecastInputError(
            "provider_schema_mismatch: response.fingerprint must be 32 lowercase hex"
        )
    if not isinstance(response["signature"], str) or not response["signature"]:
        raise ForecastInputError(
            "attestation_missing_signature: provider returned no signature (E12)"
        )
    if re.fullmatch(r"[0-9a-f]{128}", response["signature"]) is None:
        raise ForecastInputError(
            "attestation_malformed_signature: response.signature must be 128 "
            "lowercase hex (E13)"
        )
    if (
        not isinstance(response["signed_at"], str)
        or re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", response["signed_at"]
        )
        is None
    ):
        raise ForecastInputError(
            "provider_schema_mismatch: response.signed_at must be RFC3339 UTC 'Z'"
        )
    # The signing target is the request object as the provider received it, so a
    # signature cannot be moved onto a different request.
    message = canonical_sha256(request).encode("ascii")
    verify_ed25519_signature(
        response["fingerprint"], response["signature"], message
    )
    return {
        "issuer": response["issuer"],
        "key_id": response["key_id"],
        "fingerprint": response["fingerprint"],
        "signature": response["signature"],
        "signed_at": response["signed_at"],
    }


def request_publication_attestation(
    result: dict[str, Any],
) -> dict[str, Any] | None:
    """Run the provider handshake for a concrete publication.

    Returns the binding record to attach to the receipt, or ``None`` when the
    publication cannot be attested (the caller then publishes ``"unattested"``).
    The record deliberately omits the result digest and the receipt's own hash:
    both cover the receipt, which contains the record, so citing them inside the
    record would be a fixpoint.  The artifact is still bound — see
    ``revenue_publication.publication_attestation_request``.
    """
    global _ATTESTATION_LAST_FAILURE
    from revenue_publication import (
        PUBLICATION_ATTESTATION_ALGORITHM,
        PUBLICATION_ATTESTATION_DOMAIN,
        PUBLICATION_ATTESTATION_SCHEMA_VERSION,
        publication_attestation_request,
    )

    request = publication_attestation_request(
        request_id=secrets.token_hex(32),
        payload_sha256=canonical_sha256(
            {
                key: value
                for key, value in result.items()
                if key not in ("result_sha256", "publication_receipt")
            }
        ),
    )
    response = _run_attestation_provider(request)
    if response is None:
        return None
    try:
        identity = _validate_attestation_response(request, response)
    except ForecastInputError as exc:
        # A response that cannot be trusted means "not attested", not "fail the
        # publication": the research result is still valid, and a bare label is
        # exactly what this fix removes.
        _record_attestation_failure(str(exc))
        return None
    _ATTESTATION_LAST_FAILURE = None
    return {
        "attestation_payload_schema_version": PUBLICATION_ATTESTATION_SCHEMA_VERSION,
        "domain_separator": PUBLICATION_ATTESTATION_DOMAIN,
        "issuer": identity["issuer"],
        "key_id": identity["key_id"],
        "algorithm": PUBLICATION_ATTESTATION_ALGORITHM,
        "fingerprint": identity["fingerprint"],
        "request_id": request["request_id"],
        "payload_sha256": request["payload_sha256"],
        "signed_at": identity["signed_at"],
        "signature": identity["signature"],
    }


def run_forecast(data: dict[str, Any], *, mode: str = "formal") -> dict[str, Any]:
    """Run the complete revenue forecast and return the published result.

    The result is computed as a private draft and only published after passing
    the self-contained output validator; any validation failure raises before a
    caller ever sees a publication receipt.

    *mode* may be ``"formal"`` (default — all hard gates must pass) or
    ``"draft"`` (unresolved data gaps are recorded as structured limitations
    but the result is returned with ``formal_output_mode="draft"``).
    invest-* consumers must only accept ``"formal"`` artifacts.

    Formal publications carry an ``attestation_status`` (R2.1): ``"host_signed"``
    only when a provider completed a verified signing handshake (B1 / REM-01),
    otherwise ``"unattested"``.  The label is never set from a boolean: it is set
    only when :func:`request_publication_attestation` returned a record whose
    signature verifies against the trust domain, and that record is attached to
    the receipt.
    """
    from revenue_publication import (
        build_publication_receipt,
        build_draft_receipt,
        validate_publication_receipt,
    )
    from revenue_report import validate_published_forecast

    if mode not in {"formal", "draft"}:
        raise ValueError("mode must be 'formal' or 'draft'")
    result = _build_forecast_draft(data)
    # Phase 6 A1: validate BEFORE signing. The draft has no publication receipt
    # and no result hash; the strong validator recomputes every gate (including
    # input-gated sensitivity shocks) from the embedded input document. Only a
    # strong-validation verification context may issue a formal receipt.
    context = validate_published_forecast(result, data)
    if mode == "draft":
        result.setdefault("draft_limitations", []).append(
            "formal publication gates passed; draft mode requested"
        )
        result["publication_receipt"] = build_draft_receipt(result)
    else:
        # R2.1 + B1/REM-01: host_signed requires a completed, trust-verified
        # signing handshake.  A configured-but-unproven provider yields an
        # honest `unattested` publication, never a bare label.
        attestation_record = request_publication_attestation(result)
        attestation_status = (
            "host_signed" if attestation_record is not None else "unattested"
        )
        result["publication_receipt"] = build_publication_receipt(
            result,
            context,
            attestation_status=attestation_status,
            publication_attestation=attestation_record,
        )
    result["result_sha256"] = canonical_sha256(result)
    if mode == "formal":
        validate_publication_receipt(result)
        # R1.2 (N-01): a formal publication is only real once it is registered —
        # the registry is the artifact-external authority.  A missing or
        # unwritable registry fails the whole publication (fail closed).
        from publication_registry import RegistryError, register_publication

        try:
            register_publication(result)
        except RegistryError as exc:
            raise ForecastInputError(
                f"formal publication failed: registry unavailable: {exc}"
            ) from exc
    return result


def build_workflow_compliance_receipt(
    input_sha256: str,
    sources: list[dict[str, Any]],
    evidence_claims: list[dict[str, Any]],
    parameters: list[dict[str, Any]],
    data_gaps: list[str],
) -> dict[str, Any]:
    """Recompute the formal workflow receipt from validated revenue artifacts."""
    capture_hashes = sorted(source["capture"]["receipt_sha256"] for source in sources)
    receipt = {
        "receipt_schema_version": WORKFLOW_RECEIPT_SCHEMA_VERSION,
        "status": "pass",
        "workflow": "revenue_forecast_nine_dimension_driver_model",
        "execution_mode": "deterministic_runtime",
        "gate_ids": [
            "input_contract",
            "source_capture",
            "evidence_claims",
            "research_coverage",
            "management_targets",
            "growth_driver_tree",
            "revenue_model",
        ],
        "input_sha256": input_sha256,
        "source_capture_receipt_sha256s": capture_hashes,
        "source_capture_count": len(capture_hashes),
        "checked_claim_count": len(evidence_claims),
        "assumption_parameter_ids": sorted(
            parameter["parameter_id"]
            for parameter in parameters
            if parameter["kind"] in {"analyst_assumption", "scenario_stress"}
        ),
        "data_gap_count": len(data_gaps),
        "data_gaps_sha256": canonical_sha256(data_gaps),
        "prompt_injection_flagged_source_ids": sorted(
            source["source_id"]
            for source in sources
            if source["capture"]["prompt_injection_status"] == "detected_and_ignored"
        ),
        "untrusted_content_treatment": "data_only_never_instructions",
        "formal_output_authority": "validated_runtime_renderer_only",
        "freeform_formal_output_allowed": False,
    }
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    return receipt


from forecast.calc import (  # noqa: E402  re-export
    MODEL_DRIVER_DIMENSIONS,
    evaluate_derived_formula,
    parameter_values,
    resolve_driver_series,
    calculate_cagr,
    referenced_parameter_ids,
    parameter_driver_roles,
    collect_parameter_roles,
    base_forecast_parameter_ids,
    base_segment_parameter_ids,
)


from contracts.document import (  # noqa: E402  re-export
    validate_top_level,
    validate_historical_revenue,
    validate_sources,
    validate_parameters,
    validate_evidence_claims,
    validate_scenario_probabilities,
    validate_historical_accuracy_records,
    validate_source_coverage,
    validate_base_reconciliation,
    validate_document,
)


from contracts.constants import (  # noqa: E402  re-export
    ADJUSTMENT_CATEGORIES,
    DATED_CONTRIBUTION_SCHEMA_VERSION,
    FORECAST_SCHEMA_VERSION,
    GROWTH_DRIVER_COUNTEREVIDENCE_STATUSES,
    GROWTH_DRIVER_INFERENCE_DISTANCES,
    GROWTH_DRIVER_PERSISTENCE,
    GROWTH_DRIVER_TREE_STATUSES,
    MANAGEMENT_COMMUNICATION_CATEGORIES,
    MANAGEMENT_COMMUNICATION_STATUSES,
    MANAGEMENT_TARGET_COMPARISONS,
    MANAGEMENT_TARGET_MEASUREMENT_BASES,
    MANAGEMENT_TARGET_PERIMETERS,
    MANAGEMENT_TARGET_TREATMENTS,
    MECHANISM_ROLE_SCHEMA_VERSIONS,
    MONETARY_DIMENSIONS,
    OPT_IN_SCHEMA_VERSION,
    PARAMETER_DIMENSIONS,
    PARAMETER_KINDS,
    PERIOD_FLOW_SCHEMA_VERSIONS,
    PRESENTATIONS,
    PUBLICATION_RECEIPT_SCHEMA_VERSION,
    RECOGNITION_MODES,
    RECOGNITION_TIMING,
    RESEARCH_COVERAGE_STATUSES,
    RESEARCH_DIMENSIONS,
    SCENARIOS,
    SOURCE_RANKS,
    SUPPORTED_FORECAST_SCHEMA_VERSIONS,
    TIME_BASES,
    WORKFLOW_RECEIPT_SCHEMA_VERSION,
)


from research.drivers import (  # noqa: E402  re-export
    validate_growth_driver_tree,
    calculate_growth_driver_analysis,
)


from research.targets import (  # noqa: E402  re-export
    validate_management_target_coverage,
    add_management_target_analysis,
)


from research.coverage import (  # noqa: E402  re-export
    validate_research_coverage,
)


from analysis.sensitivity import (  # noqa: E402  re-export
    calculate_sensitivities,
    calculate_theme_analysis,
)


from analysis.confidence import (  # noqa: E402  re-export
    parameter_revenue_weights,
    calculate_confidence,
)


from forecast.segments import (  # noqa: E402  re-export
    calculate_model_path,
    calculate_segment_forecasts,
    validate_recognition_metadata,
    apply_revenue_recognition,
    resolve_adjustments,
    calculate_company_forecast,
    _run_forecast_core,
    add_scenario_analysis,
)


__all__ = [
    'ADJUSTMENT_CATEGORIES',
    'Collector',
    'DATED_CONTRIBUTION_SCHEMA_VERSION',
    'FORECAST_SCHEMA_VERSION',
    'GROWTH_DRIVER_COUNTEREVIDENCE_STATUSES',
    'GROWTH_DRIVER_INFERENCE_DISTANCES',
    'GROWTH_DRIVER_PERSISTENCE',
    'GROWTH_DRIVER_TREE_STATUSES',
    'MANAGEMENT_COMMUNICATION_CATEGORIES',
    'MANAGEMENT_COMMUNICATION_STATUSES',
    'MANAGEMENT_TARGET_COMPARISONS',
    'MANAGEMENT_TARGET_MEASUREMENT_BASES',
    'MANAGEMENT_TARGET_PERIMETERS',
    'MANAGEMENT_TARGET_TREATMENTS',
    'MECHANISM_ROLE_SCHEMA_VERSIONS',
    'MODEL_DRIVER_DIMENSIONS',
    'MONETARY_DIMENSIONS',
    'OPT_IN_SCHEMA_VERSION',
    'ModelRegistryError',
    'MultiValidationError',
    'PARAMETER_DIMENSIONS',
    'PARAMETER_KINDS',
    'PERIOD_FLOW_SCHEMA_VERSIONS',
    'PRESENTATIONS',
    'PUBLICATION_RECEIPT_SCHEMA_VERSION',
    'RECOGNITION_MODES',
    'RECOGNITION_TIMING',
    'RESEARCH_COVERAGE_STATUSES',
    'RESEARCH_DIMENSIONS',
    'RevenueConstraintError',
    'SCENARIOS',
    'SOURCE_RANKS',
    'SUPPORTED_FORECAST_SCHEMA_VERSIONS',
    'TIME_BASES',
    'apply_revenue_constraints',
    'apply_revenue_recognition',
    'base_forecast_parameter_ids',
    'base_segment_parameter_ids',
    'calculate_cagr',
    'calculate_company_forecast',
    'calculate_model_path',
    'calculate_registered_model',
    'calculate_segment_forecasts',
    'collect_mode',
    'collect_parameter_roles',
    'constraint_parameter_ids',
    'evaluate_derived_formula',
    'finite_number',
    'parameter_driver_roles',
    'parameter_revenue_weights',
    'parameter_values',
    'parse_iso_date',
    'period_year',
    'referenced_parameter_ids',
    'require',
    'resolve_adjustments',
    'resolve_driver_series',
    'text_sha256',
    'valid_source_url',
    'validate_base_reconciliation',
    'validate_claim_ids',
    'validate_evidence_claims',
    'validate_growth_driver_tree',
    'validate_historical_accuracy_records',
    'validate_historical_revenue',
    'validate_management_target_coverage',
    'validate_parameters',
    'validate_recognition_metadata',
    'validate_research_coverage',
    'validate_revenue_constraints',
    'validate_scenario_probabilities',
    'validate_source_capture',
    'validate_source_coverage',
    'validate_sources',
    'validate_top_level',
]
