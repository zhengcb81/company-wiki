"""Typed boundary between acquisition producers and pathless projections."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, cast, Literal

from .acquisition import ACQUISITION_SCHEMA_VERSION
from .acquisition_service import SOURCE_ENSURE_SCHEMA_VERSION
from .close_gap import CLOSE_GAP_SCHEMA_VERSION
from .gap_plan import GAP_PLAN_SCHEMA_VERSION
from .resolver import SOURCE_RESOLVER_SCHEMA_VERSION


OperationName = Literal["ensure", "close-gap"]


class SourceOperationProjectionError(ValueError):
    """A producer result cannot be represented by the pathless contract."""


@dataclass(frozen=True)
class SourceOperationInput:
    """Validated producer facts with JSON wrapper details removed."""

    operation: OperationName
    producer_status: str
    resolution_status: str | None
    request_id: str | None
    outcome: str | None
    download_events: int
    policy_hash: str | None
    matches: tuple[dict[str, Any], ...]
    gap_plan: dict[str, Any] | None
    local_preparation: dict[str, Any] | None = None


def _object(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SourceOperationProjectionError(f"{name} must be an object")
    return value


def _optional_object(value: object, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    return _object(value, name)


def _schema(value: dict[str, Any], expected: str, name: str) -> None:
    if value.get("schema_version") != expected:
        raise SourceOperationProjectionError(
            f"{name}.schema_version must be {expected}"
        )


def _producer_result(
    payload: dict[str, Any], operation: OperationName,
) -> dict[str, Any]:
    wrapper = "source_ensure" if operation == "ensure" else "close_gap"
    result = _object(payload[wrapper], wrapper) if wrapper in payload else payload
    expected = (
        SOURCE_ENSURE_SCHEMA_VERSION
        if operation == "ensure"
        else CLOSE_GAP_SCHEMA_VERSION
    )
    _schema(result, expected, wrapper)
    return result


def _resolution(
    payload: dict[str, Any], result: dict[str, Any], operation: OperationName,
) -> dict[str, Any]:
    value = result.get("resolution")
    if value is None and operation == "close-gap":
        value = payload.get("resolution")
    resolution = _optional_object(value, f"{operation}.resolution")
    if resolution:
        _schema(resolution, SOURCE_RESOLVER_SCHEMA_VERSION, "resolution")
    return resolution


def _envelope(
    result: dict[str, Any], resolution: dict[str, Any],
) -> dict[str, Any]:
    value = result.get("envelope")
    if value is None:
        value = resolution.get("resolution_envelope")
    return _optional_object(value, "resolution_envelope")


def _ensure_parts(
    result: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
    acquisition = _object(result.get("acquisition"), "source_ensure.acquisition")
    _schema(acquisition, ACQUISITION_SCHEMA_VERSION, "acquisition")
    acquisition_resolution = _optional_object(
        acquisition.get("resolution"), "acquisition.resolution"
    )
    gap_value = acquisition.get("gap_plan")
    gap = _optional_object(gap_value, "acquisition.gap_plan") if gap_value else None
    if gap is not None:
        _schema(gap, GAP_PLAN_SCHEMA_VERSION, "gap_plan")
    return acquisition, gap, acquisition_resolution


def _validate_gap_status(status: str, gap: dict[str, Any] | None) -> None:
    if status == "gap" and gap is None:
        raise SourceOperationProjectionError(
            "source_ensure gap result is missing acquisition.gap_plan"
        )
    # Discovery diagnostics survive fetch/import/reuse. They describe the
    # selection step, not a second acquisition or an incomplete final result.


def _request_id(values: tuple[object, ...]) -> str | None:
    present = [value for value in values if value is not None]
    if not all(isinstance(value, str) and value for value in present):
        raise SourceOperationProjectionError("request_id must be non-empty text")
    if len(set(present)) > 1:
        raise SourceOperationProjectionError("request_id values do not match")
    return cast(str, present[0]) if present else None


def _matches(resolution: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    value = resolution.get("matches", [])
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise SourceOperationProjectionError("resolution.matches must be an object array")
    return tuple(value)


def _download_events(
    result: dict[str, Any], envelope: dict[str, Any],
) -> int:
    value = envelope.get("download_events")
    if value is None:
        value = result.get("fetch_events", result.get("download_events", 0))
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SourceOperationProjectionError("invalid download event count")
    return cast(int, value)


def _policy_hash(envelope: dict[str, Any]) -> str | None:
    value = envelope.get("policy_hash")
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise SourceOperationProjectionError("invalid policy hash")
    return value


def _optional_text(value: object, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise SourceOperationProjectionError(f"{name} must be non-empty text")
    return value


def _local_read_budget(value: object) -> dict[str, Any] | None:
    """Validate the bounded local-read owner snapshot before projection."""
    if value is None:
        return None
    observation = _object(value, "local_read_budget")
    expected = {
        "schema_version", "operation", "usage_scope", "phase", "reason",
        "limits", "consumed", "triggered_bound",
    }
    if (set(observation) != expected
            or observation["schema_version"] != "local-read-budget/1"
            or observation["operation"] != "local_read_budget"
            or observation["usage_scope"] != "local_original_verification"):
        raise SourceOperationProjectionError("invalid local read budget observation")
    for name in ("phase", "reason"):
        if not isinstance(observation[name], str) or not re.fullmatch(
            r"[a-z][a-z0-9_]{0,79}", observation[name]
        ):
            raise SourceOperationProjectionError("invalid local read budget token")

    limits = _object(observation["limits"], "local_read_budget.limits")
    if set(limits) != {
        "max_candidates", "max_bytes", "timeout_seconds",
        "max_discovery_groups", "max_discovery_entries",
    }:
        raise SourceOperationProjectionError("invalid local read budget limits")
    integer_limits = {
        "max_candidates": (1, 256), "max_bytes": (1, 1073741824),
        "max_discovery_groups": (1, 4096), "max_discovery_entries": (1, 65536),
    }
    for name, (minimum, maximum) in integer_limits.items():
        number = limits[name]
        if type(number) is not int or not minimum <= number <= maximum:
            raise SourceOperationProjectionError("invalid local read budget limits")
    timeout = limits["timeout_seconds"]
    if (type(timeout) not in (int, float) or not math.isfinite(timeout)
            or not 0 < timeout <= 600):
        raise SourceOperationProjectionError("invalid local read budget timeout")

    consumed = _object(observation["consumed"], "local_read_budget.consumed")
    if set(consumed) != {
        "candidates", "charged_read_bytes", "observed_charge_bytes",
        "discovery_groups", "discovery_entries", "elapsed_seconds",
    }:
        raise SourceOperationProjectionError("invalid local read budget counters")
    for name in (
        "candidates", "charged_read_bytes", "observed_charge_bytes",
        "discovery_groups", "discovery_entries",
    ):
        number = consumed[name]
        if type(number) is not int or not 0 <= number <= 2**63 - 1:
            raise SourceOperationProjectionError("invalid local read budget counters")
    elapsed = consumed["elapsed_seconds"]
    if (type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0):
        raise SourceOperationProjectionError("invalid local read budget elapsed time")
    bound = observation["triggered_bound"]
    allowed_bounds = {
        "max_candidates", "max_bytes", "timeout_seconds", "cancelled",
        "max_discovery_groups", "max_discovery_entries",
    }
    if bound is not None and (not isinstance(bound, str) or bound not in allowed_bounds):
        raise SourceOperationProjectionError("invalid local read budget bound")
    return {
        "schema_version": observation["schema_version"],
        "operation": observation["operation"],
        "usage_scope": observation["usage_scope"],
        "phase": observation["phase"],
        "reason": observation["reason"],
        "limits": dict(limits),
        "consumed": dict(consumed),
        "triggered_bound": bound,
    }


def _local_preparation(value):
    if value is None:
        return None
    diagnostic = _object(value,"local_preparation")
    fields = {"status", "reason", "blocks_download", "causes"}
    if (set(diagnostic) not in (fields, fields | {"local_read_budget"})
        or not isinstance(diagnostic["status"], str)
        or diagnostic["status"] not in {"blocked","unavailable","ambiguous"}
        or diagnostic["blocks_download"] is not True
        or not isinstance(diagnostic["causes"],list) or len(diagnostic["causes"]) > 64):
        raise SourceOperationProjectionError("invalid local preparation diagnostic")
    reasons = [diagnostic["reason"],*diagnostic["causes"]]
    if not all(isinstance(reason,str) and re.fullmatch(r"[a-z][a-z0-9_]{0,79}",reason)
               for reason in reasons):
        raise SourceOperationProjectionError("local preparation reason must be a named code")
    result = {"status":diagnostic["status"],"reason":diagnostic["reason"],
              "blocks_download":True,"causes":list(diagnostic["causes"])}
    if "local_read_budget" in diagnostic:
        result["local_read_budget"] = _local_read_budget(diagnostic["local_read_budget"])
    return result


def parse_operation_payload(
    payload: dict[str, Any], *, operation: str,
) -> SourceOperationInput:
    """Validate one current producer payload and discard transport wrappers."""
    if operation not in {"ensure", "close-gap"}:
        raise ValueError("operation must be ensure or close-gap")
    if not isinstance(payload, dict):
        raise TypeError("payload must be an object")
    typed_operation = cast(OperationName, operation)
    result = _producer_result(payload, typed_operation)
    status = _optional_text(result.get("status"), "producer status")
    assert status is not None
    resolution = _resolution(payload, result, typed_operation)
    envelope = _envelope(result, resolution)
    attempt = _optional_object(result.get("attempt"), "attempt")
    gap = acquisition_resolution = None
    acquisition: dict[str, Any] = {}
    if typed_operation == "ensure":
        acquisition, gap, acquisition_resolution = _ensure_parts(result)
        _validate_gap_status(status, gap)
    ids = (
        result.get("request_id"),
        resolution.get("request_id"),
        (acquisition_resolution or {}).get("request_id"),
        (gap or {}).get("request_id"),
        attempt.get("request_id"),
        payload.get("request_id"),
    )
    outcome = envelope.get("outcome", result.get("outcome", attempt.get("outcome")))
    return SourceOperationInput(
        operation=typed_operation,
        producer_status=status,
        resolution_status=_optional_text(
            resolution.get("status"), "resolution status"
        ),
        request_id=_request_id(ids),
        outcome=_optional_text(outcome, "outcome"),
        download_events=_download_events(result, envelope),
        policy_hash=_policy_hash(envelope),
        matches=_matches(resolution),
        gap_plan=gap,
        local_preparation=_local_preparation(acquisition.get("local_preparation")),
    )


__all__ = [
    "OperationName",
    "SourceOperationInput",
    "SourceOperationProjectionError",
    "parse_operation_payload",
]
