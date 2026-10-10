"""Operation-scoped observed acquisition usage; a sibling, not a second ledger.

``acquisition-observation/1`` projects what the shared :class:`AcquisitionBudget`
actually observed for one ensure/close-gap operation: wire body bytes, entity
body bytes, HTTP exchange count, provider-reported cost, and finite HTTP
protocol metadata. It never rewrites ``acquisition_usage/1.0`` (adapter
receipt semantics) or ``acquisition-failure/1`` (the seven-key failure DTO);
both keep their exact closed shapes.

Honesty rules frozen in INTERFACE_CHANGE.md (M3-USAGE, 2026-10-10):

* ``wire_body_bytes`` are HTTP response body bytes after transfer decoding and
  before content decoding; never the disk original and never the decompressed
  entity, which is carried separately as ``entity_body_bytes``.
* ``usage_complete=False`` makes every counter a lower bound (post-send
  timeout, hard kill, mid-body truncation). ``None`` means completeness is
  unknowable, and counters may still be observed values.
* ``cost_usd`` is null unless a provider fee receipt actually arrived. A zero
  cost cap, initial zero counters, or a provider without receipts never prove
  a final fee of zero.
* ``http_exchanges`` always carries a non-negative integer observation;
  ``http_exchanges_complete=None`` means the adapter never reported a count.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

ACQUISITION_OBSERVATION_SCHEMA = "acquisition-observation/1"
USAGE_SCOPE = "operation"

# Producer journal vocabulary; consumers must not re-derive outcomes.
OBSERVATION_OUTCOMES = frozenset({
    "downloaded_new", "deduplicated_after_download",
    "reused_before_download", "reused_after_discovery",
    "missing", "ambiguous", "gap_plan", "gap_plan_provider_unavailable",
    "failed",
})

OBSERVATION_KEYS = frozenset({
    "schema_version", "usage_scope", "outcome", "provider_started",
    "usage_complete", "wire_body_bytes", "wire_usage_complete",
    "entity_body_bytes", "http_exchanges", "http_exchanges_complete",
    "cost_usd", "http_observation",
})

_HTTP_OBSERVATION_KEYS = frozenset({
    "status_code", "mime_type", "content_encoding", "wire_content_length",
})

_TRI_STATE = ("provider_started", "usage_complete", "wire_usage_complete",
              "http_exchanges_complete")


def validated_http_observation(value: Any) -> dict[str, Any] | None:
    """The finite four-field HTTP protocol metadata, or None (fail closed)."""
    if not isinstance(value, dict) or set(value) != _HTTP_OBSERVATION_KEYS:
        return None
    status = value.get("status_code")
    if isinstance(status, bool) or not isinstance(status, int) or status < 0:
        return None
    observation: dict[str, Any] = {"status_code": status}
    for key in ("mime_type", "content_encoding"):
        text = value.get(key)
        if not isinstance(text, str) or not text or len(text) > 128:
            return None
        observation[key] = text
    length = value.get("wire_content_length")
    if length is not None and (isinstance(length, bool)
                               or not isinstance(length, int) or length < 0):
        return None
    observation["wire_content_length"] = length
    return observation


_COST_INVALID = object()


def _validated_cost(value: Any) -> str | None | object:
    # Explicit null is a valid unknown; any malformed figure rejects the DTO.
    if value is None:
        return None
    if not isinstance(value, str):
        return _COST_INVALID
    try:
        amount = Decimal(value)
    except InvalidOperation:
        return _COST_INVALID
    if not amount.is_finite() or amount < 0:
        return _COST_INVALID
    return value


def validated_observation(value: Any) -> dict[str, Any] | None:
    """Only the published closed DTO; any deviation drops the whole value."""
    if not isinstance(value, dict) or set(value) != OBSERVATION_KEYS:
        return None
    if (value.get("schema_version") != ACQUISITION_OBSERVATION_SCHEMA
            or value.get("usage_scope") != USAGE_SCOPE):
        return None
    outcome = value.get("outcome")
    if not isinstance(outcome, str) or outcome not in OBSERVATION_OUTCOMES:
        return None
    result: dict[str, Any] = {
        "schema_version": ACQUISITION_OBSERVATION_SCHEMA,
        "usage_scope": USAGE_SCOPE,
        "outcome": outcome,
    }
    for key in _TRI_STATE:
        flag = value.get(key)
        if flag is not None and not isinstance(flag, bool):
            return None
        result[key] = flag
    for key in ("wire_body_bytes", "entity_body_bytes"):
        count = value.get(key)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            return None
        result[key] = count
    exchanges = value.get("http_exchanges")
    if isinstance(exchanges, bool) or not isinstance(exchanges, int) or exchanges < 0:
        return None
    result["http_exchanges"] = exchanges
    cost = _validated_cost(value.get("cost_usd"))
    if cost is _COST_INVALID:
        return None
    result["cost_usd"] = cost
    http_observation = value.get("http_observation")
    if http_observation is not None:
        http_observation = validated_http_observation(http_observation)
        if http_observation is None:
            return None
    result["http_observation"] = http_observation
    return result


def observation_from_budget(budget, *, outcome: str) -> dict[str, Any] | None:
    """Project the shared operation budget; no budget means no observation.

    The budget is the single accumulator across every invocation of one
    operation, so this can never publish the last adapter invocation as an
    operation total.
    """
    from .download_budget import AcquisitionBudget
    if (not isinstance(budget, AcquisitionBudget) or not isinstance(outcome, str)
            or outcome not in OBSERVATION_OUTCOMES):
        return None
    return {
        "schema_version": ACQUISITION_OBSERVATION_SCHEMA,
        "usage_scope": USAGE_SCOPE,
        "outcome": outcome,
        "provider_started": budget.provider_started,
        # Keep a known fee lower bound when another invocation lacked fee proof.
        # This observation does not change acquisition/retry budget policy.
        "usage_complete": budget.usage_complete and (
            not budget.cost_reported or budget.cost_usage_complete),
        "wire_body_bytes": budget.wire_response_bytes_used,
        "wire_usage_complete": budget.wire_usage_complete,
        "entity_body_bytes": budget.response_bytes_used,
        "http_exchanges": budget.http_exchanges_used,
        "http_exchanges_complete": budget.http_exchanges_complete,
        "cost_usd": str(budget.cost_usd_used) if budget.cost_reported else None,
        "http_observation": validated_http_observation(budget.last_http_observation),
    }


def published_acquisition_observation(exc: BaseException) -> dict[str, Any] | None:
    return validated_observation(getattr(exc, "acquisition_observation", None))


def observation_from_result(payload: Any) -> dict[str, Any] | None:
    """Read only the defined producer shapes; never arbitrary nested text."""
    if not isinstance(payload, dict):
        return None
    for value in (payload, payload.get("source_ensure"), payload.get("close_gap")):
        if not isinstance(value, dict):
            continue
        observation = validated_observation(value.get("acquisition_observation"))
        if observation is not None:
            return observation
        acquisition = value.get("acquisition")
        if isinstance(acquisition, dict):
            observation = validated_observation(acquisition.get("acquisition_observation"))
            if observation is not None:
                return observation
    return None


__all__ = [
    "ACQUISITION_OBSERVATION_SCHEMA",
    "OBSERVATION_OUTCOMES",
    "observation_from_budget",
    "observation_from_result",
    "published_acquisition_observation",
    "validated_http_observation",
    "validated_observation",
]
