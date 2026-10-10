"""Safe operation-level acquisition diagnostics; no second accounting ledger.

Only the ensure owner attaches this projection, after accounting in its shared
AcquisitionBudget. Adapter exception usage is invocation-scoped and must never
be published directly as an operation total.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

ACQUISITION_FAILURE_SCHEMA = "acquisition-failure/1"
ACQUISITION_FAILURE_CODES = frozenset({
    "adapter_process_failed", "adapter_timeout", "adapter_output_limit",
    "adapter_response_invalid", "adapter_not_bounded", "upstream_unavailable",
    "network_failed", "budget_exceeded", "provider_failed", "provider_not_configured",
    "invalid_request", "invalid_budget", "invalid_candidate", "missing_scratch",
    "invalid_scratch", "unsupported_language", "unsupported_sec_form", "unsupported_hk_period",
    "identity_mismatch", "invalid_provider_metadata", "primary_missing", "fiscal_period_unresolved",
    "missing_response", "staging_conflict", "sdk_asset_mismatch", "deadline_exceeded",
    "byte_budget_exceeded", "cost_budget_exceeded", "unsupported_content_encoding",
    "incomplete_response", "acquisition_budget_exceeded", "acquisition_validation_failed",
    "canonical_import_failed",
})
_FAILURE_KEYS = frozenset({"schema_version", "code", "retryable", "provider_started",
                           "usage_complete", "acquisition_usage", "usage_scope"})


def validated_usage(value: Any) -> dict[str, Any] | None:
    """A validated existing acquisition_usage/1 value, without extra fields."""
    if not isinstance(value, dict) or set(value) != {"schema_version", "response_bytes", "cost_usd"}:
        return None
    if value.get("schema_version") != "1.0":
        return None
    count, cost = value.get("response_bytes"), value.get("cost_usd")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0 or not isinstance(cost, str):
        return None
    try:
        amount = Decimal(cost)
    except InvalidOperation:
        return None
    if not amount.is_finite() or amount < 0:
        return None
    return {"schema_version": "1.0", "response_bytes": count, "cost_usd": cost}


def _safe_code(value: Any) -> str:
    return value if isinstance(value, str) and value in ACQUISITION_FAILURE_CODES else "adapter_process_failed"


def validated_failure(value: Any) -> dict[str, Any] | None:
    """Allow only the published closed DTO, never messages or arbitrary attrs."""
    if not isinstance(value, dict) or set(value) != _FAILURE_KEYS:
        return None
    if value.get("schema_version") != ACQUISITION_FAILURE_SCHEMA or value.get("usage_scope") != "operation":
        return None
    code = value.get("code")
    if not isinstance(code, str) or code not in ACQUISITION_FAILURE_CODES:
        return None
    if any(value.get(key) is not None and not isinstance(value.get(key), bool)
           for key in ("retryable", "provider_started", "usage_complete")):
        return None
    usage = value.get("acquisition_usage")
    if usage is not None and validated_usage(usage) is None:
        return None
    return dict(value)


def attach_acquisition_failure(exc: BaseException, *, budget=None, code: str | None = None) -> None:
    """Attach only a proved operation projection; absent budget stays unknown.

    ``usage_complete=False`` makes retained counters a lower bound. Null means
    final completeness cannot be established; initial zeros alone are not final
    usage after an invocation with unknown outcome. A true started observation
    from any invocation is never erased by a later pre-launch rejection.
    """
    from .download_budget import AcquisitionBudget, AcquisitionBudgetExceeded
    error_code = getattr(exc, "error_code", None)
    if error_code is None:
        error_code = "acquisition_budget_exceeded" if isinstance(exc, AcquisitionBudgetExceeded) else code
    retryable = getattr(exc, "reported_retryable", getattr(exc, "retryable", None))
    retryable = retryable if isinstance(retryable, bool) else None
    if isinstance(exc, AcquisitionBudgetExceeded):
        retryable = False
    started = complete = usage = None
    if getattr(exc, "provider_started", None) is True:
        started = True  # Existential execution proof does not need usage totals.
    if isinstance(budget, AcquisitionBudget):
        budget_started = budget.provider_started
        started = True if started is True or budget_started is True else budget_started
        complete = budget.failure_usage_complete
        if started is True and budget_started is not True:
            # The caller has existential execution proof not yet accounted by
            # this operation budget. Initial zeros/complete=True are no final
            # receipt for that invocation; never substitute invocation totals.
            complete = False if complete is False else None
        if budget.usage_reported or started is False:
            usage = {"schema_version": "1.0", "response_bytes": budget.response_bytes_used,
                     "cost_usd": str(budget.cost_usd_used)}
    setattr(exc, "acquisition_failure", {"schema_version": ACQUISITION_FAILURE_SCHEMA, "code": _safe_code(error_code),
        "retryable": retryable, "provider_started": started, "usage_complete": complete,
        "acquisition_usage": usage, "usage_scope": "operation"})
    # M3-USAGE: the observed-usage sibling rides the same exception without
    # touching the closed failure DTO above. Budget/cleanup secondary errors
    # only add notes, so this projection is never erased by later failures.
    from .acquisition_observation import observation_from_budget
    observation = observation_from_budget(budget, outcome="failed")
    if observation is not None:
        setattr(exc, "acquisition_observation", observation)


def published_acquisition_failure(exc: BaseException) -> dict[str, Any] | None:
    return validated_failure(getattr(exc, "acquisition_failure", None))


def failure_from_result(payload: Any) -> dict[str, Any] | None:
    """Read only the defined producer shapes; never arbitrary nested text."""
    if not isinstance(payload, dict):
        return None
    for value in (payload, payload.get("source_ensure"), payload.get("close_gap")):
        if not isinstance(value, dict):
            continue
        diagnostic = validated_failure(value.get("acquisition_failure"))
        if diagnostic is not None:
            return diagnostic
        acquisition = value.get("acquisition")
        if isinstance(acquisition, dict):
            diagnostic = validated_failure(acquisition.get("acquisition_failure"))
            if diagnostic is not None:
                return diagnostic
    return None
