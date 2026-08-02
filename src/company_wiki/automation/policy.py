"""AUTO-3 Policy: deterministic risk computation for planned actions.

This module depends only on the Python standard library and ``registry``.  Risk
is computed from the handler spec and action parameters — a caller cannot
self-report a low risk class.  Actions requiring network, LLM or paths outside
the allowlist are rejected.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import RiskClass
from .registry import HandlerSpec


class PolicyViolationError(Exception):
    """Raised when a proposed action violates the active policy."""


@dataclass(frozen=True)
class PolicyConfig:
    """Frozen policy configuration."""

    allow_network: bool = False
    allow_llm: bool = False
    allowed_effect_paths: tuple[str, ...] = ()  # empty = no path restriction
    max_fan_out: int = 15
    max_priority: int = 100


def compute_risk(
    spec: HandlerSpec,
    *,
    fan_out: int = 1,
    schema_change: bool = False,
    config: PolicyConfig | None = None,
) -> RiskClass:
    """Compute the risk class for a proposed action.

    Raises ``PolicyViolationError`` if the action violates the active policy.
    The risk is derived from the handler spec and action parameters — callers
    cannot self-report or override the computed risk.
    """
    if config is None:
        config = PolicyConfig()

    if spec.network and not config.allow_network:
        raise PolicyViolationError(
            f"handler {spec.job_type} requires network but policy forbids it"
        )
    if spec.llm and not config.allow_llm:
        raise PolicyViolationError(
            f"handler {spec.job_type} requires LLM but policy forbids it"
        )
    if fan_out > config.max_fan_out:
        raise PolicyViolationError(
            f"fan_out {fan_out} exceeds policy maximum {config.max_fan_out}"
        )

    # Effect-path allowlist check (only when policy specifies restrictions).
    if config.allowed_effect_paths and spec.allowed_paths:
        if not _any_path_allowed(spec.allowed_paths, config.allowed_effect_paths):
            raise PolicyViolationError(
                f"handler {spec.job_type} allowed_paths {spec.allowed_paths} "
                f"are not covered by policy allowlist {config.allowed_effect_paths}"
            )

    # Risk derivation (deterministic, no caller override).
    if schema_change:
        return RiskClass.HIGH
    if spec.effect_class == "external_side_effect":
        return RiskClass.HIGH
    if spec.effect_class == "knowledge_write":
        return RiskClass.MEDIUM
    if fan_out > 5:
        return RiskClass.MEDIUM
    return RiskClass.LOW


def _any_path_allowed(
    handler_paths: tuple[str, ...], policy_paths: tuple[str, ...]
) -> bool:
    """Check if at least one handler path is covered by the policy allowlist."""
    import fnmatch

    for hp in handler_paths:
        for pp in policy_paths:
            if fnmatch.fnmatchcase(hp, pp):
                return True
    return False


__all__ = [
    "PolicyConfig",
    "PolicyViolationError",
    "compute_risk",
]
